import subprocess
import shutil
from pathlib import Path
import pytest
from scripts.tiktok_enhancer import enhance_video_for_tiktok, probe_audio_codec


def create_dummy_clip(destination: Path, duration: float = 1.0):
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", f"color=c=blue:s=1080x1920:d={duration}:r=30",
        "-f", "lavfi", "-i", f"sine=frequency=1000:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(destination)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def test_enhance_video_for_tiktok(tmp_path):
    src_clip = tmp_path / "sample_clip.mp4"
    create_dummy_clip(src_clip, duration=0.5)

    assert src_clip.is_file()
    assert probe_audio_codec(src_clip) == "aac"

    enhanced = enhance_video_for_tiktok(src_clip)
    assert enhanced.is_file()
    assert enhanced.name == "sample_clip_tiktok_sharp.mp4"
    assert enhanced.stat().st_size > 0


def test_enhance_video_missing_file(tmp_path):
    missing_file = tmp_path / "does_not_exist.mp4"
    with pytest.raises(FileNotFoundError):
        enhance_video_for_tiktok(missing_file)
