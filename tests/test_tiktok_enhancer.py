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


# ---------------------------------------------------------------- S6-04/S6-05
from scripts import tiktok_enhancer


def _fake_encoder(monkeypatch, write_bytes, returncode=0):
    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if "-c:v" in cmd:  # the enhancement encode (probes still run for real)
            Path(cmd[-1]).write_bytes(write_bytes)
            return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr="killed" if returncode else "")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(tiktok_enhancer.subprocess, "run", fake_run)


def test_failed_or_killed_encode_leaves_no_output(tmp_path, monkeypatch):
    src = tmp_path / "src.mp4"
    create_dummy_clip(src, duration=1.0)
    _fake_encoder(monkeypatch, b"\x00" * 48, returncode=-9)
    with pytest.raises(RuntimeError):
        enhance_video_for_tiktok(src)
    assert not (tmp_path / "src_tiktok_sharp.mp4").exists()
    assert not list(tmp_path.glob("*.partial.mp4"))


def test_output_shorter_than_source_is_rejected(tmp_path, monkeypatch):
    src = tmp_path / "src.mp4"
    create_dummy_clip(src, duration=1.0)
    short = tmp_path / "short.mp4"
    create_dummy_clip(short, duration=0.5)
    _fake_encoder(monkeypatch, short.read_bytes())
    with pytest.raises(RuntimeError):
        enhance_video_for_tiktok(src)
    assert not (tmp_path / "src_tiktok_sharp.mp4").exists()
    assert not list(tmp_path.glob("*.partial.mp4"))


def test_truncated_source_is_rejected(tmp_path):
    src = tmp_path / "src.mp4"
    create_dummy_clip(src, duration=2.0)
    cut = tmp_path / "cut.mp4"
    data = src.read_bytes()
    cut.write_bytes(data[: len(data) // 2])
    with pytest.raises(RuntimeError):
        enhance_video_for_tiktok(cut)
    assert not (tmp_path / "cut_tiktok_sharp.mp4").exists()


def test_real_enhance_keeps_duration(tmp_path):
    src = tmp_path / "src.mp4"
    create_dummy_clip(src, duration=1.0)
    out = enhance_video_for_tiktok(src)
    from scripts import media_validation
    assert abs(media_validation.probe_duration(out) - media_validation.probe_duration(src)) <= 0.1
