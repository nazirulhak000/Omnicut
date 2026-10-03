"""On-demand 540p editing proxies for timeline playback.

Editing a 4K/60fps master over HTTP range requests makes scrubbing and seeking
expensive: the browser decodes far more pixels than a 1080x1920 preview can
show. This module builds a small H.264 stand-in per source clip -- scaled to
cover the 540x960 preview frame, keeping the source's aspect -- so the
timeline stays responsive, while Render keeps reading the untouched master.

Two rules hold this together, and breaking either silently degrades the
product:

1. **Render never reads a proxy.** A proxy is a preview artifact only. Nothing
   here is wired into scripts/video_editor.py, and `is_proxy_path` exists so a
   render-side guard can assert that cheaply.
2. **Timing always comes from the master.** A proxy is re-encoded, so its
   duration can differ from the master's by a frame. Trim/in/out/speed values
   must be computed against the master; the proxy is pixels for the eye, never
   a clock.

Proxies are disposable: they live under `03_Projects/.cache/<namespace>/` and
may be deleted at any time (see scripts/storage_cleaner.py). A missing proxy
means "play the master", never an error.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from scripts.config import PROJECTS_DIR

# Kept distinct from the Background Isolation namespaces that share
# 03_Projects/.cache so the two caches can be scanned and purged apart.
PROXY_CACHE_NAMESPACE = "editing-proxies"

# 540x960 is the 9:16 preview frame named in the master plan. The proxy is
# scaled to *cover* it with the source's own aspect (a 16:9 source becomes
# 1706x960), never padded and never stretched -- a padded or distorted proxy
# would make the user reframe against a picture the render does not produce.
PROXY_WIDTH = 540
PROXY_HEIGHT = 960
PROXY_CRF = 26
PROXY_PRESET = "ultrafast"

# Bumped whenever the encode settings change, so proxies built by an older
# version are not reused under the new settings.
# v2: cover-scale with the source aspect instead of fit + black pad (L6-18).
PROXY_VERSION = "v2"

# A proxy encode that runs longer than this is abandoned: the master is always
# a working fallback, so a pathological source must not wedge a worker.
PROXY_TIMEOUT_S = 900


class ProxyError(RuntimeError):
    """Raised when a proxy cannot be produced. Callers fall back to master."""


def proxy_cache_root() -> Path:
    """Root of the proxy cache. Read through a function, not bound at import,
    so tests can monkeypatch PROJECTS_DIR."""
    return PROJECTS_DIR / ".cache" / PROXY_CACHE_NAMESPACE


def _fingerprint(master: Path) -> str:
    """
    Identity of a master file: absolute path + size + mtime, hashed.

    Content hashing a 4K file would cost more than the encode it guards. Path
    plus size plus mtime catches the realistic cases -- a re-exported or
    replaced source changes at least one of them -- and a stale proxy is a
    visual artifact in preview only, never a wrong render.
    """
    stat = master.stat()
    raw = f"{master.resolve()}|{stat.st_size}|{int(stat.st_mtime)}|{PROXY_VERSION}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def proxy_path_for(master: Path) -> Path:
    """Where `master`'s proxy lives. Pure path math -- no filesystem writes."""
    return proxy_cache_root() / f"{_fingerprint(Path(master))}.mp4"


def is_proxy_path(path: Any) -> bool:
    """
    True when `path` points inside the proxy cache.

    Render-side guards use this to fail loudly rather than quietly export a
    540p frame as if it were the master. Accepts anything path-like and never
    raises -- a guard that throws on odd input is a guard that gets removed.
    """
    if not path:
        return False
    try:
        candidate = Path(str(path)).resolve()
        root = proxy_cache_root().resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    return candidate == root or root in candidate.parents


def has_proxy(master: Path) -> bool:
    """True when a usable proxy already exists for `master`."""
    try:
        target = proxy_path_for(Path(master))
    except OSError:
        return False
    return target.is_file() and target.stat().st_size > 0


def get_proxy(master: Path) -> Optional[Path]:
    """The existing proxy for `master`, or None. Never builds one: callers on
    a request path must not block on an encode."""
    return proxy_path_for(Path(master)) if has_proxy(Path(master)) else None


def _encode(master: Path, destination: Path) -> None:
    """
    Encode `master` into `destination` via a temp file in the same directory,
    then move it into place with os.replace.

    Staging matters for two reasons: a crashed or killed encode leaves no
    half-written .mp4 that a later call would treat as a finished proxy, and
    two workers racing on the same master both produce a complete file, with
    the last replace winning. os.replace is atomic within a filesystem, and
    the temp file is deliberately created in the destination directory to keep
    it on one.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, staged_name = tempfile.mkstemp(
        prefix=".proxy-", suffix=".mp4", dir=str(destination.parent)
    )
    os.close(fd)
    staged = Path(staged_name)

    # Scale so the source *covers* 540x960 and keep its own aspect -- no pad.
    # The preview cover-crops whatever frame it is given (drawVideoFrame in
    # SequencePlayer.jsx), exactly like the render cover-crops the master
    # (frame_geometry in video_editor.py). A padded proxy is already 9:16, so
    # a 16:9 clip was drawn as a letterboxed band while the render filled the
    # frame (L6-18). An unpadded proxy has the master's shape, so the same
    # crop, zoom, pan and rotation math lands on the same picture.
    # force_divisible_by=2 keeps H.264 happy (1920x1080 -> 1706x960).
    #
    # setsar=1 is load-bearing, not tidying: force_original_aspect_ratio
    # preserves the source's display aspect by writing a non-square pixel
    # aspect into the stream (a 640x360 source came out with SAR 1216:1215).
    # A player honoring that SAR would show the proxy at slightly different
    # proportions than the master, so the user would frame against a picture
    # the render will not reproduce.
    vf = (
        f"scale={PROXY_WIDTH}:{PROXY_HEIGHT}:force_original_aspect_ratio=increase"
        ":force_divisible_by=2:flags=bilinear,"
        "setsar=1,"
        "format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(master),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", PROXY_PRESET,
        "-crf", str(PROXY_CRF),
        # Frequent keyframes: scrubbing seeks constantly, and a sparse GOP
        # makes every seek decode a long run of frames.
        "-g", "30",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        str(staged),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=PROXY_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        staged.unlink(missing_ok=True)
        raise ProxyError(
            f"สร้าง Proxy ไม่สำเร็จ (เกินเวลา {PROXY_TIMEOUT_S}s): {master.name}"
        ) from exc
    except OSError as exc:
        staged.unlink(missing_ok=True)
        raise ProxyError(f"สร้าง Proxy ไม่สำเร็จ (เรียก ffmpeg ไม่ได้): {exc}") from exc

    if result.returncode != 0 or not staged.exists() or staged.stat().st_size == 0:
        detail = (result.stderr or "").strip()[:300]
        staged.unlink(missing_ok=True)
        raise ProxyError(f"สร้าง Proxy ไม่สำเร็จสำหรับ {master.name}: {detail}")

    os.replace(staged, destination)


def ensure_proxy(master: Path, *, force: bool = False) -> Path:
    """
    Return the proxy for `master`, building it if absent.

    Blocking and slow -- callers belong on a background task, not a request
    handler. Raises ProxyError on failure so the caller can fall back to the
    master rather than showing the user an empty player.
    """
    source = Path(master)
    if not source.is_file():
        raise ProxyError(f"ไม่พบไฟล์ต้นฉบับ: {source}")

    target = proxy_path_for(source)
    if not force and target.is_file() and target.stat().st_size > 0:
        return target

    _encode(source, target)
    return target


def scan_proxy_cache() -> Dict[str, Any]:
    """Size and file count of the proxy cache, shaped like the other
    scanners in scripts/storage_cleaner.py."""
    root = proxy_cache_root()
    total = 0
    count = 0
    if root.is_dir():
        for item in root.rglob("*"):
            try:
                if item.is_file():
                    total += item.stat().st_size
                    count += 1
            except OSError:
                continue
    return {"bytes": total, "count": count, "path": str(root)}


def purge_proxy_cache() -> Dict[str, Any]:
    """
    Delete every proxy.

    Safe by construction: proxies are derived from masters that are never
    touched here, so the worst case is that the next timeline session
    re-encodes them. Only the proxy namespace is removed -- never the shared
    `03_Projects/.cache` parent, which other caches live in.
    """
    root = proxy_cache_root()
    summary = scan_proxy_cache()
    if root.is_dir() and not root.is_symlink():
        shutil.rmtree(root, ignore_errors=True)
    return {
        "status": "ok",
        "freed_bytes": summary["bytes"],
        "freed_mb": round(summary["bytes"] / (1024 * 1024), 2),
        "removed_count": summary["count"],
    }
