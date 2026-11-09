# -*- coding: utf-8 -*-
"""Central MP4 gate (audit S6-02/S6-03/X-05): every resume/finalize gate rejects
a +faststart file cut in half and a fake ftyp+zeros file."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import batch_render, media_validation
from scripts.couple_engine import render as couple_render

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                                reason="ffmpeg/ffprobe required")


def make_clip(path: Path, *, seconds: float = 2.0, size: str = "1080x1920", rate: int = 30,
              faststart: bool = True) -> Path:
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={rate}:duration={seconds}",
        "-f", "lavfi", "-i", f"sine=frequency=800:duration={seconds}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k", "-shortest",
    ]
    if faststart:
        cmd += ["-movflags", "+faststart"]
    subprocess.run(cmd + [str(path)], check=True, capture_output=True, timeout=120)
    return path


def truncate_half(src: Path, dst: Path) -> Path:
    data = src.read_bytes()
    dst.write_bytes(data[: len(data) // 2])
    return dst


def synthetic_ftyp(path: Path, size: int = 128 * 1024) -> Path:
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom\x00\x00\x00\x08mdat"
    path.write_bytes(header + b"\x00" * (size - len(header)))
    return path


GATES = [
    ("media_validation", media_validation.is_valid_mp4),
    ("batch_render", batch_render.is_valid_mp4),
    ("couple_engine", couple_render.is_valid_mp4),
]


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    root = tmp_path_factory.mktemp("mp4")
    good = make_clip(root / "good.mp4")
    return {
        "good": good,
        "half": truncate_half(good, root / "half.mp4"),
        "fake": synthetic_ftyp(root / "fake.mp4"),
        "landscape": make_clip(root / "landscape.mp4", size="1920x1080"),
        "fps60": make_clip(root / "fps60.mp4", rate=60),
    }


@pytest.mark.parametrize("name, gate", GATES)
def test_gate_accepts_complete_spec_clip(clips, name, gate):
    assert gate(clips["good"]) is True


@pytest.mark.parametrize("name, gate", GATES)
def test_gate_rejects_faststart_cut_in_half(clips, name, gate):
    # moov at the front still reports the full duration; only the tail decode catches it.
    assert media_validation.probe_duration(clips["half"]) is not None
    assert gate(clips["half"]) is False


@pytest.mark.parametrize("name, gate", GATES)
def test_gate_rejects_fake_ftyp_file(clips, name, gate):
    assert gate(clips["fake"]) is False


def test_gate_rejects_off_spec_clips(clips):
    assert media_validation.validate_mp4(clips["landscape"]).ok is False
    assert media_validation.validate_mp4(clips["fps60"]).ok is False
    # Spec dimensions can be relaxed explicitly (draft / enhancer source checks).
    assert media_validation.validate_mp4(clips["landscape"], width=None, height=None).ok is True


def test_missing_file_is_invalid(tmp_path):
    assert media_validation.is_valid_mp4(tmp_path / "nope.mp4") is False


def test_finalize_partial_moves_valid_and_drops_invalid(tmp_path, clips):
    final = tmp_path / "out.mp4"
    partial = media_validation.partial_path_for(final)
    assert partial.name == "out.partial.mp4"
    shutil.copy2(clips["good"], partial)
    media_validation.finalize_partial(partial, final)
    assert final.is_file() and not partial.exists()

    bad_final = tmp_path / "bad.mp4"
    bad_partial = media_validation.partial_path_for(bad_final)
    shutil.copy2(clips["half"], bad_partial)
    with pytest.raises(media_validation.MediaValidationError):
        media_validation.finalize_partial(bad_partial, bad_final)
    assert not bad_partial.exists() and not bad_final.exists()


def test_nvenc_open_failure_detection():
    assert media_validation.is_nvenc_open_failure("[h264_nvenc @ 0x1] OpenEncodeSessionEx failed: out of memory (10)")
    assert not media_validation.is_nvenc_open_failure("Invalid argument")
