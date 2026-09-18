"""Transparent tests for the ASS/libass half of motion pixel parity."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest
from PIL import Image, ImageDraw

from tests.motion_capture.ass_fixture import (
    ComparisonThresholds,
    FixtureSpec,
    compare_frames,
    render_ass_fixture,
)


SELECTED_PRESETS = ("hook.in.snap", "hook.loop.pulse", "hook.out.fade")


@pytest.mark.render_regression
@pytest.mark.parametrize("preset_id", SELECTED_PRESETS)
def test_selected_ass_fixture_renders_with_metadata_and_no_export_write(tmp_path: Path, preset_id: str):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for ASS fixture rendering")
    role, phase, preset = preset_id.split(".")
    output_dir = tmp_path / "motion_capture"
    paths = render_ass_fixture(FixtureSpec(preset_id, role, phase, sample_ms=250), output_dir)
    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))

    assert paths["ass"].is_file()
    assert paths["png"].is_file()
    assert metadata["renderer"] == "ffmpeg/libass"
    assert metadata["pixel_diff_status"] == "not_compared"
    assert metadata["canvas_capture_required"] is True
    assert metadata["artifacts"]["png"]["sha256"]
    assert "04_Exports" not in str(paths["png"])
    with Image.open(paths["png"]) as frame:
        assert frame.size == (1080, 1920)


def test_comparison_metric_accepts_small_rasterizer_differences_but_rejects_geometry_shift(tmp_path: Path):
    reference_path = tmp_path / "reference.png"
    candidate_path = tmp_path / "candidate.png"
    shifted_path = tmp_path / "shifted.png"
    for path, offset in ((reference_path, 0), (candidate_path, 1), (shifted_path, 30)):
        image = Image.new("RGB", (160, 100), (16, 24, 39))
        draw = ImageDraw.Draw(image)
        draw.rectangle((40 + offset, 30, 90 + offset, 55), fill=(240, 240, 240))
        image.save(path)

    tolerant = compare_frames(reference_path, candidate_path)
    shifted = compare_frames(reference_path, shifted_path)
    assert tolerant.passed is True
    assert tolerant.exact_pixel_match is False
    assert shifted.passed is False
    assert shifted.bbox_edge_delta_px > ComparisonThresholds().bbox_edge_delta_px_max


def test_canvas_golden_seam_skips_instead_of_claiming_pixel_parity(tmp_path: Path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required before the Canvas golden seam can be checked")
    role, phase, preset = "hook.in.snap".split(".")
    paths = render_ass_fixture(FixtureSpec("hook.in.snap", role, phase, sample_ms=250), tmp_path / "fixture")
    golden_path = Path(__file__).parent / "motion_capture" / "golden" / "hook_in_snap_0250ms.png"
    if not golden_path.is_file():
        pytest.skip(
            "Canvas golden frame is not checked in; this is an intentional seam, "
            "not a pixel-parity pass"
        )
    comparison = compare_frames(golden_path, paths["png"])
    assert comparison.passed, comparison.to_dict()

