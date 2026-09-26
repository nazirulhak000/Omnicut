"""Stream a source window through rembg into one transparent video artifact.

No decoded source or foreground frames are persisted. A completed artifact is
published only after FFmpeg has decoded and verified its alpha channel.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

from scripts.background_isolation import normalize_background_isolation
from scripts.background_isolation_sequence_artifacts import build_sequence_artifact_id
from scripts.background_isolation_worker import BackgroundIsolationWorker, _validate_alpha_quality

VIDEO_NAMESPACE = "background-isolation-videos"
VIDEO_NAME = "cutout.webm"
PREVIEW_NAME = "preview.webm"
VIDEO_SCHEMA_VERSION = 2
WORKER_VERSION = "stream-rembg-v2-proxy"
_ID = re.compile(r"^bgseq1-[0-9a-f]{16}$")


def video_artifact_id(fingerprint: str, config: dict[str, Any], *, start: float,
                      duration: float | None, fps: float, timebase: str,
                      width: int, height: int, rotation: int) -> str:
    normalized = normalize_background_isolation(config)
    return build_sequence_artifact_id(
        fingerprint, algorithm="background-isolation-video-v2",
        engine=normalized["engine"], model=normalized["model"],
        quality=normalized["quality"], worker_version=f"{WORKER_VERSION}-{normalized.get('temporal_mode', 'legacy')}",
        fps=fps, timebase=timebase, width=width, height=height,
        rotation=rotation, source_start=start, source_duration=duration,
    )


def _verify_video(path: Path, *, width: int, height: int, frame_count: int) -> None:
    """Use the VP9 decoder with alpha support; native VP9 can drop alpha."""
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-c:v", "libvpx-vp9",
               "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL) as proc:
        assert proc.stdout is not None
        bytes_per_frame = width * height * 4
        decoded = 0
        saw_transparency = saw_opaque = False
        while True:
            frame = proc.stdout.read(bytes_per_frame)
            if not frame:
                break
            if len(frame) != bytes_per_frame:
                proc.kill()
                raise RuntimeError("cutout video has a truncated decoded frame")
            decoded += 1
            alpha = frame[3::4]
            saw_transparency |= min(alpha) < 32
            saw_opaque |= max(alpha) > 223
        stderr = proc.stderr.read(4096) if proc.stderr else b""
        if proc.wait() != 0 or decoded != frame_count or not saw_transparency or not saw_opaque:
            raise RuntimeError(f"cutout video verification failed: {decoded}/{frame_count} frames, alpha={saw_transparency}/{saw_opaque}, {stderr.decode(errors='replace')[:300]}")


def build_alpha_preview(master: Path, *, width: int, height: int, frame_count: int,
                        fps: float, max_width: int = 540, max_height: int = 960) -> dict[str, Any] | None:
    """Derive every proxy frame from the finalized master, preserving its PTS."""
    scale = min(1.0, max_width / width, max_height / height)
    if scale >= 1:
        return None
    preview_width = max(2, int(width * scale) // 2 * 2)
    preview_height = max(2, int(height * scale) // 2 * 2)
    preview = master.with_name(PREVIEW_NAME)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-c:v", "libvpx-vp9", "-i", str(master), "-an",
               "-vf", f"scale={preview_width}:{preview_height}:flags=lanczos",
               "-fps_mode", "passthrough", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
               "-auto-alt-ref", "0", "-deadline", "good", "-cpu-used", "5",
               "-g", str(max(1, round(fps / 2))), "-crf", "32", "-b:v", "0", str(preview)]
    with tempfile.TemporaryFile() as log:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=log, timeout=600)
        if result.returncode:
            log.seek(0)
            raise RuntimeError(f"สร้าง Cutout Preview ไม่สำเร็จ: {log.read(2048).decode(errors='replace')}")
    _verify_video(preview, width=preview_width, height=preview_height, frame_count=frame_count)
    with preview.open("rb") as handle:
        checksum = hashlib.file_digest(handle, "sha256").hexdigest()
    return {"video_file": PREVIEW_NAME, "codec": "vp9-alpha", "width": preview_width,
            "height": preview_height, "frame_count": frame_count, "sha256": checksum,
            "size_bytes": preview.stat().st_size, "frame_mapping": "identity",
            "derived_from": VIDEO_NAME}


def process_background_isolation_video(
    source: Path, cache_root: Path, config: dict[str, Any], *,
    source_fingerprint: str, start: float, duration: float | None,
    fps: float, timebase: str, width: int, height: int, rotation: int,
    cancel_event: Any = None, progress_callback: Callable[[dict[str, Any]], None] | None = None,
    rembg_worker: BackgroundIsolationWorker | None = None,
) -> dict[str, Any]:
    """Build a complete transparent video without publishing individual PNGs."""
    from PIL import Image, ImageChops

    normalized = normalize_background_isolation(config)
    if not normalized["enabled"]:
        raise ValueError("background isolation is disabled")
    source = Path(source).resolve(strict=True)
    raw_cache_root = Path(cache_root)
    if raw_cache_root.is_symlink():
        raise ValueError("unsafe video cache root")
    cache_root = raw_cache_root.resolve(strict=False)
    namespace = cache_root / VIDEO_NAMESPACE
    artifact_id = video_artifact_id(source_fingerprint, normalized, start=start,
                                    duration=duration, fps=fps, timebase=timebase,
                                    width=width, height=height, rotation=rotation)
    if not _ID.fullmatch(artifact_id) or any(p.is_symlink() for p in (cache_root, namespace)):
        raise ValueError("unsafe video artifact path")
    target = namespace / artifact_id
    if target.is_symlink():
        raise ValueError("unsafe video artifact directory")
    manifest_path = target / "manifest.json"
    if manifest_path.is_file() and (target / VIDEO_NAME).is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("schema_version") == VIDEO_SCHEMA_VERSION
                and manifest.get("source_fingerprint") == source_fingerprint
                and manifest.get("status") == "ready"):
            with (target / VIDEO_NAME).open("rb") as handle:
                current_sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
            if current_sha256 == manifest.get("sha256"):
                preview = manifest.get("preview")
                if preview:
                    preview_path = target / PREVIEW_NAME
                    if preview_path.is_symlink() or not preview_path.is_file():
                        raise RuntimeError("cutout preview missing; rebuild this artifact")
                    with preview_path.open("rb") as handle:
                        preview_sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
                    if preview_sha256 != preview.get("sha256"):
                        raise RuntimeError("cutout preview checksum mismatch; rebuild this artifact")
                return {"status": "ready", "artifact_id": artifact_id,
                        "output_directory": str(target), "frame_count": manifest["frame_count"],
                        "cache_hit": True}
            raise RuntimeError("cutout video cache checksum mismatch; rebuild this artifact")
    if target.exists():
        raise RuntimeError("incomplete video artifact exists; refusing to overwrite it")
    namespace.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{artifact_id}.", dir=namespace))
    decoder = encoder = None
    frame_count = 0
    # Phase 0 baseline: the round has to report real throughput rather than
    # asserting it, so the encode loop is timed and the numbers go into the
    # manifest where a later run can be compared against this one.
    encode_started_at = time.perf_counter()
    fps_ratio = Fraction(str(fps)).limit_denominator(1001000)
    fps_text = f"{fps_ratio.numerator}/{fps_ratio.denominator}"
    frame_size = width * height * 3
    worker = rembg_worker or BackgroundIsolationWorker()
    # Default measured 2026-09-26 (_Docs/Reports/CUTOUT_PHASE4_EDGE_STABILITY_20260926.md):
    # "legacy" only blends pixels differing by less than 24 from the previous
    # frame, so moving edges -- where the jitter actually is -- keep their raw
    # mask, and it measured -0.7% / -0.3% against raw rembg. "motion" tracks
    # those edges with optical flow and measured +20.5% / +12.7%. An explicit
    # temporal_mode in the project still wins; this only changes what a
    # project that never set one gets.
    temporal_mode = normalized.get("temporal_mode", "motion")
    refiner = None
    if temporal_mode == "motion":
        from scripts.cutout_temporal import TemporalAlphaRefiner
        refiner = TemporalAlphaRefiner()
    try:
        rembg, session = worker._get_session(normalized["model"])
        decode_cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                      "-ss", str(start), "-i", str(source)]
        if duration is not None:
            decode_cmd += ["-t", str(duration)]
        decode_cmd += ["-vf", f"fps={fps_text},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
        encode_cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                      "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}",
                      "-r", fps_text, "-i", "pipe:0", "-an", "-c:v", "libvpx-vp9",
                      "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-deadline", "good",
                      "-cpu-used", "4", "-g", str(max(1, round(fps))),
                      "-crf", "28", "-b:v", "0", str(staged / VIDEO_NAME)]
        with tempfile.TemporaryFile() as decoder_log, tempfile.TemporaryFile() as encoder_log:
            decoder = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE,
                                       stderr=decoder_log, stdin=subprocess.DEVNULL)
            encoder = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE,
                                       stdout=subprocess.DEVNULL, stderr=encoder_log)
            assert decoder.stdout is not None and encoder.stdin is not None
            previous_alpha = None
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise RuntimeError("background isolation cancelled")
                raw = decoder.stdout.read(frame_size)
                if not raw:
                    break
                if len(raw) != frame_size:
                    raise RuntimeError("source decoder returned a partial frame")
                rgb = Image.frombytes("RGB", (width, height), raw)
                result = rembg.remove(rgb, session=session) if session is not None else rembg.remove(rgb)
                if isinstance(result, (bytes, bytearray)):
                    with Image.open(io.BytesIO(result)) as decoded:
                        rgba = decoded.convert("RGBA")
                else:
                    rgba = result.convert("RGBA")
                _validate_alpha_quality(rgba, expected_size=(width, height),
                                        quality=normalized["quality"])
                alpha = rgba.getchannel("A")
                if refiner is not None:
                    import numpy as np
                    alpha = Image.fromarray(refiner.refine(np.asarray(rgb), np.asarray(alpha),
                        pts=start + frame_count / float(fps_ratio), fps=float(fps_ratio)))
                    rgba.putalpha(alpha)
                elif previous_alpha is not None and temporal_mode == "legacy":
                    # Smooth small per-pixel fluctuations only; moving edges
                    # with larger differences retain their current mask.
                    difference = ImageChops.difference(previous_alpha, alpha)
                    stable = difference.point(lambda value: 255 if value < 24 else 0)
                    smoothed = Image.blend(previous_alpha, alpha, 0.65)
                    alpha.paste(smoothed, mask=stable)
                    rgba.putalpha(alpha)
                previous_alpha = alpha
                try:
                    encoder.stdin.write(rgba.tobytes())
                except OSError as exc:
                    encoder_log.seek(0)
                    details = encoder_log.read(2048).decode(errors="replace")
                    raise RuntimeError(f"cutout encoder stopped before frame {frame_count + 1}: {details[:400]}") from exc
                frame_count += 1
                if progress_callback and frame_count % 5 == 0:
                    progress_callback({"stage": "isolating", "frame": frame_count,
                                       "progress": min(0.95, frame_count / max(1, round((duration or 60) * fps)))})
            decoder.stdout.close()
            encoder.stdin.close()
            decoder_code = decoder.wait(timeout=30)
            encoder_code = encoder.wait(timeout=120)
            if decoder_code or encoder_code or frame_count == 0:
                decoder_log.seek(0)
                encoder_log.seek(0)
                details = (decoder_log.read(2048) + encoder_log.read(2048)).decode(errors="replace")
                raise RuntimeError(f"cutout video encode failed ({decoder_code}/{encoder_code}, {frame_count} frames): {details[:400]}")
            if duration is not None and abs(frame_count - round(duration * float(fps_ratio))) > 1:
                raise RuntimeError("cutout source ended before the requested video window")
        video_path = staged / VIDEO_NAME
        encode_seconds = time.perf_counter() - encode_started_at
        _verify_video(video_path, width=width, height=height, frame_count=frame_count)
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("background isolation cancelled")
        if progress_callback:
            progress_callback({"stage": "preview", "frame": frame_count, "progress": 0.97})
        preview = build_alpha_preview(video_path, width=width, height=height,
                                      frame_count=frame_count, fps=float(fps_ratio))
        with video_path.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        manifest = {"schema_version": VIDEO_SCHEMA_VERSION, "artifact_id": artifact_id,
                    "status": "ready", "video_file": VIDEO_NAME, "codec": "vp9-alpha",
                    "source_fingerprint": source_fingerprint, "source_start": start,
                    "source_duration": duration if duration is not None else frame_count / float(fps_ratio),
                    "fps": fps_text, "timebase": timebase, "frame_count": frame_count,
                    "width": width, "height": height, "rotation": rotation,
                    "algorithm": "background-isolation-video-v2", "engine": normalized["engine"],
                    "model": normalized["model"], "quality": normalized["quality"],
                    "worker_version": WORKER_VERSION, "sha256": checksum}
        manifest["temporal_mode"] = temporal_mode
        manifest["quality_report"] = {"media_verified": True, "subject_review": "required",
                                      "temporal": refiner.stats if refiner else {"mode": temporal_mode}}
        # Measured, not estimated. source_seconds is the span actually covered
        # by the frames produced, so realtime_factor stays meaningful even when
        # the requested duration was clipped by the end of the source.
        source_seconds = frame_count / float(fps_ratio) if fps_ratio else 0.0
        manifest["performance"] = {
            "encode_seconds": round(encode_seconds, 3),
            "frame_count": frame_count,
            "source_seconds": round(source_seconds, 3),
            "seconds_per_frame": round(encode_seconds / frame_count, 4) if frame_count else None,
            "realtime_factor": round(encode_seconds / source_seconds, 2) if source_seconds else None,
            "width": width, "height": height,
            "output_bytes": video_path.stat().st_size,
            "bytes_per_frame": round(video_path.stat().st_size / frame_count) if frame_count else None,
        }
        if preview:
            manifest["preview"] = {**preview, "master_sha256": checksum, "fps": fps_text}
        (staged / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("background isolation cancelled")
        os.replace(staged, target)
        return {"status": "ready", "artifact_id": artifact_id,
                "output_directory": str(target), "frame_count": frame_count,
                "cache_hit": False}
    finally:
        for proc in (decoder, encoder):
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait()
        if staged.exists():
            shutil.rmtree(staged)
