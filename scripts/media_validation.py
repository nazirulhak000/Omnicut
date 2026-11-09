# -*- coding: utf-8 -*-
"""Single MP4 integrity gate + shared NVENC session pool + disk guard.

Every place that decides "this MP4 is a finished clip" (resume gates, render
finalizers, the export listing, the TikTok enhancer) calls :func:`validate_mp4`
/ :func:`is_valid_mp4` from here instead of keeping its own size/header check
(audit 20261109 S6-02/S6-03/X-05). A file is valid only when ALL of these hold:

1. it exists and is larger than ``min_bytes``;
2. ``ffprobe -v error`` reads it with no error output, it has a video stream
   and a positive container duration;
3. the video stream matches the delivery spec (default 1080x1920 @ 30 FPS;
   pass ``width/height/fps=None`` to skip a dimension);
4. decoding the last second (``ffmpeg -v error -sseof -1 ... -f null -``)
   prints nothing on stderr. A ``+faststart`` file cut in half still reports
   its full duration from the moov atom at the front, so only a real decode of
   the tail catches it ("Invalid NAL unit size", exit code 0).

Renders write to ``<stem>.partial.mp4`` next to the final path and call
:func:`finalize_partial`, which validates and ``os.replace``-s it into place, so
a half-written file is never visible under its final name.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple, Union

logger = logging.getLogger("omnicut.media_validation")

SPEC_WIDTH = 1080
SPEC_HEIGHT = 1920
SPEC_FPS = 30.0
FPS_TOLERANCE = 0.5
MIN_VALID_MP4_BYTES = 1024
PROBE_TIMEOUT_SEC = 30
TAIL_DECODE_TIMEOUT_SEC = 90
TAIL_DECODE_SECONDS = 1.0
PARTIAL_SUFFIX = ".partial.mp4"

PathLike = Union[str, Path]


class MediaValidationError(RuntimeError):
    """Raised when a freshly rendered file fails the integrity gate."""


@dataclass
class MediaCheck:
    ok: bool
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return self.ok


# --------------------------------------------------------------------- tools
def _ffprobe_binary() -> Optional[str]:
    return shutil.which("ffprobe")


def _ffmpeg_binary() -> Optional[str]:
    return shutil.which("ffmpeg")


def _run(cmd, timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )


def _parse_rate(raw: Any) -> Optional[float]:
    text = str(raw or "").strip()
    if not text or text in {"0/0", "N/A"}:
        return None
    try:
        if "/" in text:
            num, den = text.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else None
        return float(text)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- cache
_CACHE_LOCK = threading.Lock()
_CACHE: Dict[Tuple[Any, ...], MediaCheck] = {}
_CACHE_MAX = 4096


def _cache_key(p: Path, st: os.stat_result, spec: Tuple[Any, ...]) -> Tuple[Any, ...]:
    return (str(p.resolve()), st.st_size, st.st_mtime_ns, spec)


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


# ------------------------------------------------------------- validation
def probe_streams(path: PathLike, timeout: float = PROBE_TIMEOUT_SEC) -> Dict[str, Any]:
    """ffprobe JSON (streams + format). Raises MediaValidationError on any error output."""
    ffprobe = _ffprobe_binary()
    if not ffprobe:
        raise MediaValidationError("ไม่พบ ffprobe ในเครื่อง — ตรวจไฟล์วิดีโอไม่ได้")
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate:format=duration",
        "-of", "json", str(path),
    ]
    try:
        proc = _run(cmd, timeout)
    except subprocess.TimeoutExpired as exc:
        raise MediaValidationError(f"ffprobe ค้างเกิน {timeout:.0f} วินาที") from exc
    except OSError as exc:
        raise MediaValidationError(f"เรียก ffprobe ไม่สำเร็จ: {exc}") from exc
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0 or stderr:
        raise MediaValidationError(f"ffprobe อ่านไฟล์ไม่ผ่าน (exit {proc.returncode}): {stderr[-300:]}")
    try:
        return json.loads(proc.stdout or "{}")
    except ValueError as exc:
        raise MediaValidationError("ffprobe ส่งผลลัพธ์ที่อ่านไม่ได้") from exc


def probe_duration(path: PathLike, timeout: float = PROBE_TIMEOUT_SEC) -> Optional[float]:
    """Container duration in seconds, or None when it cannot be read."""
    try:
        data = probe_streams(path, timeout=timeout)
        value = float((data.get("format") or {}).get("duration") or 0)
        return value if value > 0 else None
    except (MediaValidationError, TypeError, ValueError):
        return None


def _tail_decode_errors(path: Path, seconds: float, timeout: float) -> str:
    ffmpeg = _ffmpeg_binary()
    if not ffmpeg:
        return "ไม่พบ ffmpeg ในเครื่อง — ถอดรหัสท้ายไฟล์ไม่ได้"
    cmd = [
        ffmpeg, "-nostdin", "-hide_banner", "-v", "error",
        "-sseof", f"-{seconds:g}", "-i", str(path),
        "-f", "null", "-",
    ]
    try:
        proc = _run(cmd, timeout)
    except subprocess.TimeoutExpired:
        return f"ถอดรหัสท้ายไฟล์ค้างเกิน {timeout:.0f} วินาที"
    except OSError as exc:
        return f"เรียก ffmpeg ไม่สำเร็จ: {exc}"
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0 and not stderr:
        stderr = f"ffmpeg exit {proc.returncode}"
    return stderr


def validate_mp4(
    path: PathLike,
    *,
    width: Optional[int] = SPEC_WIDTH,
    height: Optional[int] = SPEC_HEIGHT,
    fps: Optional[float] = SPEC_FPS,
    min_bytes: int = MIN_VALID_MP4_BYTES,
    tail_seconds: float = TAIL_DECODE_SECONDS,
    use_cache: bool = True,
) -> MediaCheck:
    """Full integrity + spec check. Never raises; ``reason`` is Thai."""
    try:
        p = Path(path)
        st = p.stat()
        if not p.is_file():
            return MediaCheck(False, "ไม่ใช่ไฟล์")
    except (OSError, TypeError, ValueError):
        return MediaCheck(False, "ไม่พบไฟล์")
    if st.st_size <= min_bytes:
        return MediaCheck(False, f"ไฟล์เล็กผิดปกติ ({st.st_size} ไบต์)")

    spec = (width, height, fps, tail_seconds)
    key = _cache_key(p, st, spec + (min_bytes,))
    if use_cache:
        with _CACHE_LOCK:
            cached = _CACHE.get(key)
        if cached is not None:
            return cached

    result = _validate_uncached(p, width=width, height=height, fps=fps, tail_seconds=tail_seconds)
    if use_cache:
        with _CACHE_LOCK:
            if len(_CACHE) >= _CACHE_MAX:
                _CACHE.clear()
            _CACHE[key] = result
    return result


def _validate_uncached(
    p: Path, *, width: Optional[int], height: Optional[int], fps: Optional[float], tail_seconds: float
) -> MediaCheck:
    try:
        data = probe_streams(p)
    except MediaValidationError as exc:
        return MediaCheck(False, str(exc))
    streams = data.get("streams") or []
    video = next((s for s in streams if (s or {}).get("codec_type") == "video"), None)
    if not video:
        return MediaCheck(False, "ไม่มีสตรีมภาพในไฟล์")
    try:
        duration = float((data.get("format") or {}).get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        return MediaCheck(False, "ความยาวไฟล์เป็นศูนย์")
    v_w, v_h = video.get("width"), video.get("height")
    v_fps = _parse_rate(video.get("avg_frame_rate")) or _parse_rate(video.get("r_frame_rate"))
    details = {
        "width": v_w, "height": v_h, "fps": v_fps, "duration": duration,
        "has_audio": any((s or {}).get("codec_type") == "audio" for s in streams),
    }
    if width is not None and v_w != width:
        return MediaCheck(False, f"ความกว้าง {v_w} ไม่ตรงสเปก {width}", details)
    if height is not None and v_h != height:
        return MediaCheck(False, f"ความสูง {v_h} ไม่ตรงสเปก {height}", details)
    if fps is not None and (v_fps is None or abs(v_fps - float(fps)) > FPS_TOLERANCE):
        return MediaCheck(False, f"เฟรมเรต {v_fps} ไม่ตรงสเปก {fps:g}", details)
    tail = min(float(tail_seconds), max(duration / 2.0, 0.05))
    errors = _tail_decode_errors(p, tail, TAIL_DECODE_TIMEOUT_SEC)
    if errors:
        details["stderr_tail"] = errors[-300:]
        return MediaCheck(False, f"ถอดรหัสท้ายไฟล์ไม่ผ่าน (ไฟล์อาจขาด): {errors[-200:]}", details)
    return MediaCheck(True, "", details)


def is_valid_mp4(path: PathLike, **kwargs: Any) -> bool:
    """True only for a complete, decodable MP4 matching the spec (see validate_mp4)."""
    return validate_mp4(path, **kwargs).ok


# ------------------------------------------------------------- atomic finalize
def partial_path_for(final_path: PathLike) -> Path:
    final = Path(final_path)
    return final.with_name(f"{final.stem}{PARTIAL_SUFFIX}")


def is_partial_name(path: PathLike) -> bool:
    return Path(path).name.lower().endswith(PARTIAL_SUFFIX)


def finalize_partial(partial: PathLike, final: PathLike, **spec: Any) -> MediaCheck:
    """Validate ``partial`` and atomically move it to ``final``.

    On failure the partial file is removed and MediaValidationError is raised;
    ``final`` is left untouched.
    """
    src, dst = Path(partial), Path(final)
    check = validate_mp4(src, use_cache=False, **spec)
    if not check.ok:
        with contextlib.suppress(OSError):
            src.unlink()
        raise MediaValidationError(f"ไฟล์ที่เรนเดอร์ไม่ผ่านการตรวจ ({dst.name}): {check.reason}")
    os.replace(src, dst)
    return check


def discard_partial(partial: PathLike) -> None:
    with contextlib.suppress(OSError):
        Path(partial).unlink()


# ------------------------------------------------------------ NVENC sessions
# GeForce drivers cap concurrent NVENC sessions per system (5 on 2023 drivers,
# 8 on current ones). Every in-process NVENC encode (final timeline encode,
# TikTok enhancer, couple_engine enhancer) takes one session from this single
# pool, so 4 renders + 4 enhancements + couple_engine cannot together exceed
# the driver limit (audit S6-09).
NVENC_SESSIONS_ENV = "OMNICUT_NVENC_SESSIONS"
NVENC_SESSIONS_DEFAULT = 4
NVENC_SESSIONS_MAX = 8

NVENC_OPEN_FAILURE_MARKERS = (
    "openencodesessionex failed",
    "no capable devices found",
    "no nvenc capable devices",
    "cannot load nvencodeapi",
    "cannot load nvcuda",
    "initializeencoder failed",
    "nvenc_initializeencoder",
    "incompatible client key",
    "out of memory",
    "unknown encoder 'h264_nvenc'",
    "error while opening encoder",
    "driver does not support the required nvenc api version",
)


def resolve_nvenc_sessions(raw: Optional[str] = None) -> int:
    """NVENC session cap from env (clamped 1..8, default 4)."""
    if raw is None:
        raw = os.environ.get(NVENC_SESSIONS_ENV)
    try:
        value = int(str(raw).strip()) if raw is not None and str(raw).strip() else NVENC_SESSIONS_DEFAULT
    except ValueError:
        value = NVENC_SESSIONS_DEFAULT
    return max(1, min(NVENC_SESSIONS_MAX, value))


NVENC_MAX_SESSIONS = resolve_nvenc_sessions()
NVENC_SESSIONS = threading.BoundedSemaphore(NVENC_MAX_SESSIONS)


@contextlib.contextmanager
def nvenc_session(enabled: bool = True, semaphore: Optional[threading.BoundedSemaphore] = None) -> Iterator[None]:
    """Hold one process-wide NVENC session while ``enabled`` (no-op otherwise)."""
    if not enabled:
        yield
        return
    sem = semaphore or NVENC_SESSIONS
    with sem:
        yield


def is_nvenc_open_failure(stderr: str) -> bool:
    text = (stderr or "").lower()
    return "nvenc" in text and any(marker in text for marker in NVENC_OPEN_FAILURE_MARKERS)


# ------------------------------------------------------------------ disk guard
MIN_FREE_DISK_GB = 3.0
MIN_FREE_DISK_BYTES = int(MIN_FREE_DISK_GB * 1024 ** 3)


class InsufficientDiskSpace(RuntimeError):
    pass


def require_disk_space(path: PathLike, min_bytes: int = MIN_FREE_DISK_BYTES) -> int:
    """Raise InsufficientDiskSpace unless ``path``'s drive has ``min_bytes`` free."""
    target = Path(path)
    while not target.exists() and target != target.parent:
        target = target.parent
    try:
        free = shutil.disk_usage(str(target)).free
    except OSError as exc:
        raise InsufficientDiskSpace(f"ตรวจพื้นที่ดิสก์ไม่ได้ ({target}): {exc}") from exc
    if free < min_bytes:
        raise InsufficientDiskSpace(
            f"พื้นที่ดิสก์เหลือ {free / 1024 ** 3:.1f} GB ต่ำกว่าขั้นต่ำ {min_bytes / 1024 ** 3:.1f} GB — หยุดเรนเดอร์ก่อนไฟล์เสีย"
        )
    return free


# -------------------------------------------------------------- timeouts
def encode_timeout_for(duration_sec: Optional[float], *, floor: float = 180.0, per_second: float = 10.0) -> float:
    """Generous wall-clock cap for one encode of a clip of ``duration_sec``."""
    try:
        d = float(duration_sec or 0)
    except (TypeError, ValueError):
        d = 0.0
    return max(floor, d * per_second + 60.0)
