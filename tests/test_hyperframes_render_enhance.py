import math
from pathlib import Path
import pytest
import shutil
import subprocess

from scripts.tiktok_enhancer import enhance_video_for_tiktok


def create_dummy_clip(destination: Path, duration: float = 0.5):
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", f"color=c=purple:s=1080x1920:d={duration}:r=30",
        "-f", "lavfi", "-i", f"sine=frequency=1200:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(destination)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def test_hyperframes_target_enhanced_inplace(tmp_path):
    target = tmp_path / "composition.mp4"
    create_dummy_clip(target, duration=0.5)

    original_size = target.stat().st_size
    assert original_size > 0

    # Emulate the hook in hyperframes_render.py:
    enhanced = target.with_name(f".{target.stem}-sharp.mp4")
    enhance_video_for_tiktok(target, enhanced)
    assert enhanced.is_file()
    enhanced.replace(target)

    assert target.is_file()
    assert target.stat().st_size > 0
