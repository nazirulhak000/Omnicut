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

from scripts import media_validation

logger = logging.getLogger("omnicut.tiktok_enhancer")

# CapCut 7.1 gpu_driver_bug_list.json hardware decoder/encoder blacklist
CAPCUT_GPU_DRIVER_BUG_LIST: Dict[str, List[str]] = {
    "0x8086": ["0x041e", "0x0412", "0x0416", "0x0a26", "0x5912", "0x591b"],
    "0x10de": ["0x0f00", "0x1cb6"],
}


def is_gpu_driver_blacklisted(vendor_id: Optional[str] = None, device_id: Optional[str] = None) -> bool:
    """Return True if the GPU vendor/device is in CapCut 7.1's hardware bug list."""
    v = (vendor_id or os.environ.get("OMNICUT_GPU_VENDOR_ID") or "").strip().lower()
    d = (device_id or os.environ.get("OMNICUT_GPU_DEVICE_ID") or "").strip().lower()
    if not v or not d:
        return False
    if not v.startswith("0x"):
        v = f"0x{v}"
    if not d.startswith("0x"):
        d = f"0x{d}"
    return d in CAPCUT_GPU_DRIVER_BUG_LIST.get(v, [])


def check_nvenc_support() -> bool:
    """Check if NVIDIA NVENC hardware encoder is available."""
    if is_gpu_driver_blacklisted():
        return False
    try:
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        res = subprocess.run([ffmpeg_bin, "-encoders"], capture_output=True, text=True, check=False, timeout=30)
        return "h264_nvenc" in res.stdout
    except Exception:
        return False


HAS_NVENC = check_nvenc_support()
if HAS_NVENC:
    logger.info("เปิดใช้ NVIDIA NVENC เข้ารหัสด้วยการ์ดจอแล้ว")
else:
    logger.info("ไม่พบ NVIDIA NVENC — ใช้ libx264 บน CPU แทน")

# GeForce drivers cap concurrent NVENC sessions per system (5 on drivers from
# 2023, 8 on current ones). The cap now lives in scripts.media_validation and
# is ONE process-wide pool shared with the final timeline encode and the
# couple_engine enhancer (audit S6-09); a session that still fails to open
# falls back to libx264 below instead of failing the export.
NVENC_SESSIONS_ENV = media_validation.NVENC_SESSIONS_ENV
NVENC_SESSIONS_DEFAULT = media_validation.NVENC_SESSIONS_DEFAULT
NVENC_SESSIONS_MAX = media_validation.NVENC_SESSIONS_MAX
resolve_nvenc_sessions = media_validation.resolve_nvenc_sessions
NVENC_MAX_SESSIONS = media_validation.NVENC_MAX_SESSIONS
_NVENC_SESSIONS = media_validation.NVENC_SESSIONS


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
        logger.warning("ตรวจ codec เสียงของ %s ไม่ได้: %s", input_path, e)
    return None


def capcut_splendor_vibrance_saturation(base_saturation: float = 1.04, vibrance: float = 0.0) -> float:
    """CapCut 7.1 Skin-Tone Protected Vibrance multiplier (`AmazingFeature_splendor`)."""
    v = max(-0.5, min(0.5, float(vibrance or 0.0)))
    return round(max(0.2, float(base_saturation) * (1.0 + v * 0.65)), 4)


def enhance_video_for_tiktok(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    *,
    crf: int = 17,
    unsharp: str = "lx=3:ly=3:la=0.8:cx=3:cy=3:ca=0.0",
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
        raise FileNotFoundError(f"ไม่พบไฟล์ต้นฉบับ: {in_file}")

    if output_path is None:
        out_file = in_file.with_name(f"{in_file.stem}_tiktok_sharp.mp4")
    else:
        out_file = Path(output_path).resolve()

    out_file.parent.mkdir(parents=True, exist_ok=True)
    src_check = check_enhancer_source(in_file)
    media_validation.require_disk_space(out_file.parent)

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
        "-bf", "1",
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
        "-bf", "1",
    ]

    def build_cmd(video_codec_args: List[str]) -> List[str]:
        return [
            ffmpeg_bin, "-y",
            "-i", str(in_file),
            "-vf", vf_filter,
            *video_codec_args,
            *audio_args,
            "-movflags", "+faststart",
            str(partial)
        ]

    logger.info("กำลังปรับความคมชัดสำหรับ TikTok: %s -> %s", in_file.name, out_file.name)
    partial = media_validation.partial_path_for(out_file)
    timeout = media_validation.encode_timeout_for(src_check.details.get("duration"))

    def run_encode(video_codec_args: List[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(build_cmd(video_codec_args), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(exc.cmd, -1, stdout="", stderr=f"timeout after {timeout:.0f}s")

    try:
        proc = None
        if HAS_NVENC:
            with _NVENC_SESSIONS:
                proc = run_encode(nvenc_args)
            if proc.returncode != 0:
                logger.warning(
                    "h264_nvenc ล้มเหลว (exit %s) — สลับไปใช้ libx264 บน CPU แทน: %s",
                    proc.returncode, (proc.stderr or "")[-300:],
                )
                media_validation.discard_partial(partial)
                proc = None
        if proc is None:
            proc = run_encode(x264_args)
        if proc.returncode != 0:
            logger.error("FFmpeg ปรับความคมชัดล้มเหลว (exit %s):\n%s", proc.returncode, (proc.stderr or "")[-2000:])
            raise RuntimeError(
                f"FFmpeg ปรับความคมชัดล้มเหลว (exit {proc.returncode}): {(proc.stderr or '')[-500:]}"
            )
        verify_enhanced_output(src_check, partial)
        os.replace(partial, out_file)
    finally:
        # Killed/failed/invalid encodes never leave a half-written file behind.
        media_validation.discard_partial(partial)

    return out_file


def check_enhancer_source(in_file: Path) -> "media_validation.MediaCheck":
    """The source must itself be complete: a truncated source would "enhance"
    successfully into a shorter clip (audit S6-05)."""
    check = media_validation.validate_mp4(in_file, width=None, height=None, fps=None)
    if not check.ok:
        raise RuntimeError(f"ไฟล์ต้นฉบับเสียหรือไม่ครบ ปรับความคมชัดไม่ได้ ({in_file.name}): {check.reason}")
    return check


def verify_enhanced_output(src_check: "media_validation.MediaCheck", partial: Path) -> None:
    """Output keeps the source's geometry/fps and its duration within 0.1s."""
    src = src_check.details
    check = media_validation.validate_mp4(
        partial, width=src.get("width"), height=src.get("height"), fps=src.get("fps"), use_cache=False,
    )
    if not check.ok:
        raise RuntimeError(f"ไฟล์ที่ปรับความคมชัดแล้วไม่ผ่านการตรวจ: {check.reason}")
    src_d, out_d = src.get("duration"), check.details.get("duration")
    if src_d and out_d is not None and abs(float(out_d) - float(src_d)) > 0.1:
        raise RuntimeError(
            f"ความยาวหลังปรับความคมชัด ({out_d:.2f}s) ต่างจากต้นฉบับ ({src_d:.2f}s) เกิน 0.1 วินาที"
        )


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
