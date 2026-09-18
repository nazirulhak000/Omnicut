"""Tests for the P1-A deterministic browser Canvas capture seam."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.motion_capture.capture import (
    MOTION_PRESETS,
    capture_motion,
    compare_capture_runs,
    probe_browser,
    temp_capture_dir,
)


SAMPLE_PRESETS = ("hook.in.bounce", "hook.loop.pulse", "hook.out.fade")


def _run_capture(prefer_browser: bool, preset_ids=SAMPLE_PRESETS):
    tmp = temp_capture_dir()
    output = Path(tmp.name) / "run"
    manifest = capture_motion(output, preset_ids=preset_ids, prefer_browser=prefer_browser)
    return tmp, output, manifest


def test_fallback_calls_sample_canvas_motion_and_writes_deterministic_pngs():
    tmp, output, manifest = _run_capture(False, ("hook.in.bounce",))
    try:
        assert manifest["mode"] == "sampleCanvasMotion_raster_fallback"
        assert manifest["pixel_parity_claim"] is False
        assert len(manifest["frames"]) == 5
        assert all((output / frame["path"]).read_bytes().startswith(b"\x89PNG") for frame in manifest["frames"])
        assert json.loads((output / "manifest.json").read_text(encoding="utf-8"))["ass_plans"]
    finally:
        tmp.cleanup()


def test_same_fallback_capture_is_byte_deterministic():
    left_tmp, _left_output, left = _run_capture(False, ("hook.loop.pulse", "hook.out.fade"))
    right_tmp, _right_output, right = _run_capture(False, ("hook.loop.pulse", "hook.out.fade"))
    try:
        comparison = compare_capture_runs(left, right)
        assert comparison["deterministic"] is True
        assert comparison["mismatches"] == []
    finally:
        left_tmp.cleanup()
        right_tmp.cleanup()


def test_browser_capture_is_real_or_reports_an_explicit_blocker():
    probe = probe_browser()
    tmp, output, manifest = _run_capture(True, ("hook.in.bounce",))
    try:
        assert manifest["mode"] in {"browser_canvas", "sampleCanvasMotion_raster_fallback"}
        if probe.available:
            assert manifest["mode"] == "browser_canvas", manifest["blockers"]
            assert manifest["browser"]["available"] is True
        else:
            assert manifest["mode"] == "sampleCanvasMotion_raster_fallback"
            assert manifest["blockers"]
        assert manifest["pixel_parity_claim"] is False
        assert (output / "manifest.json").exists()
    finally:
        tmp.cleanup()


@pytest.mark.parametrize("bad_path", [Path(".tmp2") / "capture", Path("04_Exports") / "capture"])
def test_capture_rejects_non_tmp_output(bad_path: Path):
    with pytest.raises(ValueError, match="must be under"):
        capture_motion(bad_path, preset_ids=("hook.in.bounce",), prefer_browser=False)


def test_catalog_manifest_has_ass_reference_for_every_captured_preset():
    tmp, _output, manifest = _run_capture(False, tuple(sorted(MOTION_PRESETS)))
    try:
        assert manifest["preset_count"] == len(MOTION_PRESETS)
        assert set(manifest["ass_plans"]) == set(MOTION_PRESETS)
        assert all(not str(frame["path"]).startswith("04_Exports") for frame in manifest["frames"])
    finally:
        tmp.cleanup()
