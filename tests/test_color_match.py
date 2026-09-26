"""Behavioral tests for scripts/color_match.py.

The point of this module is that a corrected clip actually lands closer to the
anchor than it started, so the headline test measures real footage, applies
the proposed correction with ffmpeg, and measures again. The rest guard the
arithmetic around it: a proposal too small to see should not be made, a
degenerate clip should not produce an extreme multiplier, and a failed probe
should be reported rather than silently leaving a clip unmatched.

Every clip is synthesized into tmp_path; no real footage is read.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import scripts.color_match as cm
from scripts.color_match import (
    ColorMatchError,
    apply_corrections,
    measure_clip,
    plan_color_match,
    propose_correction,
)
from scripts.video_editor import EQ_LIMITS

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not available on PATH",
)


def _clip(path: Path, *, eq: str = "", seconds: float = 1.0) -> Path:
    """A clip with a deliberate look, so two clips differ in a known way."""
    vf = f"eq={eq}" if eq else "null"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"testsrc2=size=320x240:rate=15:duration={seconds}",
         "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", str(path)],
        capture_output=True, check=True, timeout=120,
    )
    return path


def _apply_eq(src: Path, dst: Path, correction: dict) -> Path:
    eq = ":".join(f"{k}={v}" for k, v in correction.items())
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-vf", f"eq={eq}", "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", str(dst)],
        capture_output=True, check=True, timeout=300,
    )
    return dst


# ---------------------------------------------------------------------------
# The property that matters: correction converges
# ---------------------------------------------------------------------------

def test_correction_moves_a_clip_closer_to_the_anchor(tmp_path, monkeypatch):
    """Measure, correct, re-measure. If the gap does not shrink, the whole
    module is decoration."""
    monkeypatch.chdir(tmp_path)
    anchor = _clip(tmp_path / "anchor.mp4", eq="brightness=0.15:saturation=1.4")
    off = _clip(tmp_path / "off.mp4", eq="brightness=-0.12:saturation=0.6")

    anchor_m = measure_clip(anchor)
    before_m = measure_clip(off)
    correction = propose_correction(before_m, anchor_m)
    assert correction, "clips this different must produce a correction"

    after_m = measure_clip(_apply_eq(off, tmp_path / "fixed.mp4", correction))

    before_gap = abs(before_m["luma"] - anchor_m["luma"])
    after_gap = abs(after_m["luma"] - anchor_m["luma"])
    assert after_gap < before_gap / 2, f"luma gap {before_gap:.4f} -> {after_gap:.4f}"


def test_saturation_correction_converges(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    anchor = _clip(tmp_path / "anchor.mp4", eq="saturation=1.5")
    off = _clip(tmp_path / "off.mp4", eq="saturation=0.5")

    anchor_m, before_m = measure_clip(anchor), measure_clip(off)
    correction = propose_correction(before_m, anchor_m)
    assert "saturation" in correction

    after_m = measure_clip(_apply_eq(off, tmp_path / "fixed.mp4", correction))
    assert abs(after_m["saturation"] - anchor_m["saturation"]) < abs(before_m["saturation"] - anchor_m["saturation"])


# ---------------------------------------------------------------------------
# measure_clip
# ---------------------------------------------------------------------------

def test_measure_returns_normalised_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    m = measure_clip(_clip(tmp_path / "a.mp4"))
    for key in ("luma", "spread", "saturation"):
        assert 0.0 <= m[key] <= 1.0, f"{key}={m[key]} should be normalised to 0-1"
    assert m["frames"] > 0


def test_measure_reads_more_than_one_frame(tmp_path, monkeypatch):
    """Judging a shot from a single frame would let one cutaway or flash
    decide the whole clip's grade."""
    monkeypatch.chdir(tmp_path)
    m = measure_clip(_clip(tmp_path / "a.mp4", seconds=2.0), sample_frames=8)
    assert m["frames"] >= 2


def test_measure_spread_is_tonal_range_not_motion(tmp_path, monkeypatch):
    """A still frame has zero frame-to-frame difference but plenty of tonal
    range -- using the former would report no contrast at all."""
    monkeypatch.chdir(tmp_path)
    m = measure_clip(_clip(tmp_path / "a.mp4"), sample_frames=1)
    assert m["spread"] > 0.0


def test_measure_missing_file_raises(tmp_path):
    with pytest.raises(ColorMatchError):
        measure_clip(tmp_path / "nope.mp4")


def test_measure_undecodable_file_raises(tmp_path, monkeypatch):
    """A clip that never decoded must not read as a legitimate measurement."""
    monkeypatch.chdir(tmp_path)
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video at all")
    with pytest.raises(ColorMatchError):
        measure_clip(junk)


def test_measure_handles_a_path_with_a_drive_letter(tmp_path, monkeypatch):
    """lavfi treats ':' as an option separator, so a Windows absolute path
    broke the probe until it was made relative."""
    monkeypatch.chdir(tmp_path)
    clip = _clip(tmp_path / "a.mp4")
    assert measure_clip(clip.resolve())["frames"] > 0


# ---------------------------------------------------------------------------
# propose_correction
# ---------------------------------------------------------------------------

def test_identical_clips_need_no_correction():
    m = {"luma": 0.5, "spread": 0.4, "saturation": 0.3}
    assert propose_correction(m, dict(m)) == {}


def test_a_difference_too_small_to_see_is_not_corrected():
    """A correction nobody can see is still a diff the user must review."""
    src = {"luma": 0.500, "spread": 0.400, "saturation": 0.300}
    anchor = {"luma": 0.505, "spread": 0.405, "saturation": 0.302}
    assert propose_correction(src, anchor) == {}


def test_corrections_stay_inside_the_renderer_limits():
    """A wildly different clip is pulled closer, not pushed to a value the
    renderer would reject."""
    src = {"luma": 0.02, "spread": 0.02, "saturation": 0.02}
    anchor = {"luma": 0.98, "spread": 0.9, "saturation": 0.95}
    out = propose_correction(src, anchor)
    for key, value in out.items():
        low, high, _ = EQ_LIMITS[key]
        assert low <= value <= high, f"{key}={value} outside {low}..{high}"


def test_a_flat_clip_does_not_produce_a_runaway_ratio():
    """Near-zero spread is noise; dividing by it would yield an enormous
    contrast multiplier driven by nothing."""
    src = {"luma": 0.5, "spread": 0.0005, "saturation": 0.0005}
    anchor = {"luma": 0.5, "spread": 0.5, "saturation": 0.5}
    out = propose_correction(src, anchor)
    assert "contrast" not in out
    assert "saturation" not in out


def test_brightness_is_signed_toward_the_anchor():
    darker = propose_correction({"luma": 0.2, "spread": 0.4, "saturation": 0.3},
                                {"luma": 0.6, "spread": 0.4, "saturation": 0.3})
    brighter = propose_correction({"luma": 0.6, "spread": 0.4, "saturation": 0.3},
                                  {"luma": 0.2, "spread": 0.4, "saturation": 0.3})
    assert darker["brightness"] > 0
    assert brighter["brightness"] < 0


# ---------------------------------------------------------------------------
# plan_color_match
# ---------------------------------------------------------------------------

def test_plan_uses_the_first_clip_as_the_anchor_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clips = [
        {"id": "a", "source_path": str(_clip(tmp_path / "a.mp4", eq="brightness=0.15"))},
        {"id": "b", "source_path": str(_clip(tmp_path / "b.mp4", eq="brightness=-0.15"))},
    ]
    plan = plan_color_match(clips)
    assert plan["anchor_id"] == "a"
    assert "a" not in plan["corrections"], "the anchor must not correct itself"
    assert "b" in plan["corrections"]


def test_plan_honors_an_explicit_anchor(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clips = [
        {"id": "a", "source_path": str(_clip(tmp_path / "a.mp4", eq="brightness=0.15"))},
        {"id": "b", "source_path": str(_clip(tmp_path / "b.mp4", eq="brightness=-0.15"))},
    ]
    plan = plan_color_match(clips, anchor_id="b")
    assert plan["anchor_id"] == "b"
    assert "b" not in plan["corrections"]


def test_plan_reports_a_clip_it_could_not_measure(tmp_path, monkeypatch):
    """A failed probe must be visible, not a clip quietly left unmatched."""
    monkeypatch.chdir(tmp_path)
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"nope")
    clips = [
        {"id": "a", "source_path": str(_clip(tmp_path / "a.mp4"))},
        {"id": "b", "source_path": str(broken)},
    ]
    plan = plan_color_match(clips)
    assert [s["id"] for s in plan["skipped"]] == ["b"]
    assert "b" not in plan["corrections"]


def test_plan_reports_when_the_anchor_itself_cannot_be_measured(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"nope")
    clips = [
        {"id": "a", "source_path": str(broken)},
        {"id": "b", "source_path": str(_clip(tmp_path / "b.mp4"))},
    ]
    plan = plan_color_match(clips)
    assert plan["corrections"] == {}
    assert any("อ้างอิง" in s["reason"] for s in plan["skipped"])


def test_plan_on_an_empty_list_is_empty():
    plan = plan_color_match([])
    assert plan["anchor_id"] is None and plan["corrections"] == {}


def test_plan_ignores_clips_without_a_source():
    plan = plan_color_match([{"id": "a"}, {"id": "b", "source_path": ""}])
    assert plan["anchor_id"] is None


# ---------------------------------------------------------------------------
# apply_corrections
# ---------------------------------------------------------------------------

def test_apply_merges_only_the_corrected_clips():
    clips = [{"id": "a", "zoom": 1.2}, {"id": "b"}]
    out = apply_corrections(clips, {"b": {"brightness": 0.1}})
    assert out[0] is clips[0], "an uncorrected clip should keep its identity"
    assert out[1]["brightness"] == 0.1


def test_apply_preserves_unrelated_clip_settings():
    clips = [{"id": "a", "zoom": 1.4, "volume": 0.5, "saturation": 1.8}]
    out = apply_corrections(clips, {"a": {"brightness": 0.1}})
    assert out[0]["zoom"] == 1.4 and out[0]["volume"] == 0.5
    assert out[0]["saturation"] == 1.8, "a key not being corrected must survive"


def test_apply_overwrites_only_the_corrected_keys():
    clips = [{"id": "a", "saturation": 1.8}]
    out = apply_corrections(clips, {"a": {"saturation": 1.1}})
    assert out[0]["saturation"] == 1.1


def test_apply_without_corrections_returns_the_clips_unchanged():
    clips = [{"id": "a"}]
    assert apply_corrections(clips, {}) == clips


def test_apply_does_not_mutate_the_input():
    clips = [{"id": "a"}]
    apply_corrections(clips, {"a": {"brightness": 0.2}})
    assert "brightness" not in clips[0], "planning must stay previewable"
