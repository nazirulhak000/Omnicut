"""TikTok Pro Sharpness Enhancement Service for OmniCut Pro Studio.

Optimizes 1080x1920 (9:16) video for TikTok's aggressive transcoder pipeline:
- Pre-sharpening (unsharp mask) to counteract compression blur
- Color & contrast calibration (BT.709 color primaries + slight vibrance)
- H.264 High Profile Level 4.2 with optimal GOP (g=60 for 30fps)
- +faststart moov atom header placement for instantaneous streaming
"""

import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import threading
from typing import Dict, List, Optional, Union

logger = logging.getLogger("omnicut.tiktok_enhancer")


def check_nvenc_support() -> bool:
    """Check if NVIDIA NVENC hardware encoder is available."""
    try:
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        res = subprocess.run([ffmpeg_bin, "-encoders"], capture_output=True, text=True, check=False)
        return "h264_nvenc" in res.stdout
    except Exception:
        return False


HAS_NVENC = check_nvenc_support()
if HAS_NVENC:
    logger.info("NVIDIA NVENC hardware acceleration is active.")
else:
    logger.info("NVIDIA NVENC not available, using libx264 CPU fallback.")

# GeForce drivers cap concurrent NVENC sessions per system (5 on drivers from
# 2023, 8 on current ones) and the pipeline's own final encodes already use up
# to four (render_jobs slot pool). Batch enhancement runs on four workers
# (AGENTS rule 24), so enhancer encodes take a session from this small pool
# rather than racing for the driver limit; a session that still fails to open
# falls back to libx264 below instead of failing the export.
NVENC_SESSIONS_ENV = "OMNICUT_NVENC_SESSIONS"
NVENC_SESSIONS_DEFAULT = 4
NVENC_SESSIONS_MAX = 8


def resolve_nvenc_sessions(raw: Optional[str] = None) -> int:
    """Enhancer NVENC session cap from env (clamped 1..8, default 4)."""
    if raw is None:
        raw = os.environ.get(NVENC_SESSIONS_ENV)
    try:
        value = int(str(raw).strip()) if raw is not None and str(raw).strip() else NVENC_SESSIONS_DEFAULT
    except ValueError:
        value = NVENC_SESSIONS_DEFAULT
    return max(1, min(NVENC_SESSIONS_MAX, value))


NVENC_MAX_SESSIONS = resolve_nvenc_sessions()
_NVENC_SESSIONS = threading.BoundedSemaphore(NVENC_MAX_SESSIONS)


def probe_audio_codec(input_path: Path) -> Optional[str]:
    """Check if the first audio stream is AAC."""
    ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_bin, "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "json",
        str(input_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if streams:
            return streams[0].get("codec_name")
    except Exception as e:
        logger.warning("Could not probe audio codec for %s: %s", input_path, e)
    return None


def enhance_video_for_tiktok(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    *,
    crf: int = 18,
    unsharp: str = "5:5:0.8:5:5:0.3",
    contrast: float = 1.04,
    brightness: float = -0.015,
    saturation: float = 1.04,
    preset: str = "medium",
    gop: int = 60,
) -> Path:
    """Enhance a video file with TikTok-optimized encoding parameters.

    Returns the Path to the enhanced video file.
    """
    in_file = Path(input_path).resolve()
    if not in_file.is_file():
        raise FileNotFoundError(f"Source video not found: {in_file}")

    if output_path is None:
        out_file = in_file.with_name(f"{in_file.stem}_tiktok_sharp.mp4")
    else:
        out_file = Path(output_path).resolve()

    out_file.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    audio_codec = probe_audio_codec(in_file)
    audio_args = ["-c:a", "copy"] if audio_codec == "aac" else ["-c:a", "aac", "-b:a", "192k"]

    vf_filter = f"unsharp={unsharp},eq=contrast={contrast}:brightness={brightness}:saturation={saturation}"

    nvenc_args = [
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-rc", "vbr",
        "-cq", str(crf + 1),
        "-b:v", "0",
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
        "-g", str(gop),
        "-bf", "2",
    ]
    x264_args = [
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "4.2",
        "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
        "-crf", str(crf),
        "-preset", preset,
        "-g", str(gop),
        "-bf", "2",
    ]

    def build_cmd(video_codec_args: List[str]) -> List[str]:
        return [
            ffmpeg_bin, "-y",
            "-i", str(in_file),
            "-vf", vf_filter,
            *video_codec_args,
            *audio_args,
            "-movflags", "+faststart",
            str(out_file)
        ]

    logger.info("Enhancing video for TikTok: %s -> %s", in_file.name, out_file.name)
    proc = None
    if HAS_NVENC:
        with _NVENC_SESSIONS:
            proc = subprocess.run(build_cmd(nvenc_args), capture_output=True, text=True)
        if proc.returncode != 0:
            logger.warning(
                "h264_nvenc ล้มเหลว (exit %s) — สลับไปใช้ libx264 บน CPU แทน: %s",
                proc.returncode, (proc.stderr or "")[-300:],
            )
            proc = None
    if proc is None:
        proc = subprocess.run(build_cmd(x264_args), capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("FFmpeg enhancement failed:\n%s", proc.stderr)
        raise RuntimeError(f"FFmpeg failed with exit code {proc.returncode}: {proc.stderr[-500:]}")

    return out_file


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="TikTok Pro Sharpness Enhancement CLI")
    parser.add_argument("input", help="Path to input MP4 video file")
    parser.add_argument("output", nargs="?", default=None, help="Path to output enhanced MP4 (optional)")
    parser.add_argument("--crf", type=int, default=18, help="CRF value (default: 18)")
    parser.add_argument("--unsharp", default="5:5:0.8:5:5:0.3", help="Unsharp filter parameters")
    parser.add_argument("--contrast", type=float, default=1.04, help="Contrast boost (default: 1.04)")
    parser.add_argument("--saturation", type=float, default=1.04, help="Saturation boost (default: 1.04)")
    args = parser.parse_args()

    try:
        enhanced = enhance_video_for_tiktok(
            args.input,
            args.output,
            crf=args.crf,
            unsharp=args.unsharp,
            contrast=args.contrast,
            saturation=args.saturation,
        )
        print(f"✓ Successfully enhanced for TikTok: {enhanced} ({round(enhanced.stat().st_size / 1024 / 1024, 2)} MB)")
    except Exception as e:
        print(f"✗ Enhancement failed: {e}", file=sys.stderr)
        sys.exit(1)
