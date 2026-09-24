"""Live production-path parity gates for timing, transforms, framing and cuts."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import compare_clip_pair, create_clip_source


def _assert_pairs_pass(result):
    assert result.live_contracts, "the live fixture did not expose clip contracts"
    for index, comparison in enumerate(result.comparisons):
        assert comparison["passed"] is True, f"frame {index}: {comparison}"
        assert comparison["mask_iou"] >= 0.90, f"frame {index}: {comparison}"
        assert comparison["bbox_edge_delta_px"] <= 6, f"frame {index}: {comparison}"
        assert comparison["centroid_delta_px"] <= 4, f"frame {index}: {comparison}"
        assert comparison["mean_abs_error"] <= 0.08, f"frame {index}: {comparison}"


def _base_url(motion_fixture_url: str) -> str:
    return urlsplit(motion_fixture_url)._replace(query="").geturl()


def test_live_clip_trim_speed_and_freeze_tail_match_render(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    config = {"trim_start": 0.5, "trim_end": 2.5, "speed": 2, "freeze_tail": 0.5}
    with temp_capture_dir("clip-timing-pair-") as temp_root:
        root = Path(temp_root)
        source = create_clip_source(root)
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=(source,),
            clip_configs=(config,),
            duration=1.5,
            sample_times=(0.2, 0.7, 1.2, 1.4),
        )
        _assert_pairs_pass(result)


def test_live_static_zoom_and_pan_match_render(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    config = {"zoom": 1.4, "pan_x": 0.25, "pan_y": -0.1}
    with temp_capture_dir("clip-static-camera-pair-") as temp_root:
        root = Path(temp_root)
        source = create_clip_source(root)
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=(source,),
            clip_configs=(config,),
            duration=2,
            sample_times=(0.6,),
        )
        _assert_pairs_pass(result)


@pytest.mark.parametrize("mirror", [False, True], ids=["mirror-off", "mirror-on"])
@pytest.mark.parametrize(
    "animated_properties",
    [("zoom",), ("pan_x",), ("pan_y",), ("zoom", "pan_x", "pan_y")],
    ids=["zoom-only", "pan-x-only", "pan-y-only", "all-camera-tracks"],
)
def test_live_zoom_pan_mirror_and_camera_keyframes_match_render(
    motion_fixture_url: str, monkeypatch, mirror: bool, animated_properties: tuple[str, ...],
):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    start = {"zoom": 1.1, "pan_x": -0.25, "pan_y": 0.1}
    end = {"zoom": 1.75, "pan_x": 0.25, "pan_y": -0.1}
    config = {
        **start,
        "mirror": mirror,
        "keyframes": [
            {"time": 0, **{prop: start[prop] for prop in animated_properties}},
            {"time": 2, **{prop: end[prop] for prop in animated_properties}},
        ],
    }
    with temp_capture_dir("clip-keyframes-pair-") as temp_root:
        root = Path(temp_root)
        source = create_clip_source(root)
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=(source,),
            clip_configs=(config,),
            duration=2,
            sample_times=(0.5,),
        )
        _assert_pairs_pass(result)


def test_live_rotation_and_mirror_match_render(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    config = {"zoom": 1.25, "pan_x": 0.2, "rotation": 90, "mirror": True}
    with temp_capture_dir("clip-rotation-pair-") as temp_root:
        root = Path(temp_root)
        source = create_clip_source(root)
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=(source,),
            clip_configs=(config,),
            duration=2,
            sample_times=(0.6,),
        )
        _assert_pairs_pass(result)


def test_live_fit_blur_framing_matches_render(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    config = {"fit_mode": "blur", "zoom": 1.0, "pan_x": 0, "pan_y": 0}
    with temp_capture_dir("clip-blur-pair-") as temp_root:
        root = Path(temp_root)
        source = create_clip_source(root, landscape=True)
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=(source,),
            clip_configs=(config,),
            duration=2,
            sample_times=(0.6, 1.2),
        )
        _assert_pairs_pass(result)


def test_live_fill_framing_matches_render_for_landscape_source(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    with temp_capture_dir("clip-fill-pair-") as temp_root:
        root = Path(temp_root)
        source = create_clip_source(root, landscape=True)
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=(source,),
            clip_configs=({},),
            duration=2,
            sample_times=(0.6, 1.2),
        )
        _assert_pairs_pass(result)


def test_live_blur_framing_with_rotation_matches_render(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    with temp_capture_dir("clip-rotated-blur-pair-") as temp_root:
        root = Path(temp_root)
        source = create_clip_source(root, landscape=True)
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=(source,),
            clip_configs=({"fit_mode": "blur", "rotation": 90},),
            duration=2,
            sample_times=(0.6,),
        )
        _assert_pairs_pass(result)


def test_live_timeline_cut_boundary_selects_the_matching_clip(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    first = {"trim_start": 0, "trim_end": 1, "speed": 1, "transition_in": "cut"}
    second = {"trim_start": 0, "trim_end": 1, "speed": 1, "transition_in": "cut"}
    with temp_capture_dir("timeline-cut-pair-") as temp_root:
        root = Path(temp_root)
        sources = (create_clip_source(root, variant=0), create_clip_source(root, variant=2))
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=sources,
            clip_configs=(first, second),
            duration=2,
            sample_times=(0.967, 1.0, 1.033),
            transitions=("cut",),
        )
        _assert_pairs_pass(result)


def test_live_timeline_fade_overlap_matches_render(motion_fixture_url: str, monkeypatch):
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    first = {"trim_start": 0, "trim_end": 1.2, "transition_in": "cut"}
    second = {
        "trim_start": 0,
        "trim_end": 1.2,
        "transition_in": "fade",
        "transition_duration": 0.4,
    }
    with temp_capture_dir("timeline-fade-pair-") as temp_root:
        root = Path(temp_root)
        sources = (create_clip_source(root, variant=0), create_clip_source(root, variant=2))
        result = compare_clip_pair(
            base_url=_base_url(motion_fixture_url),
            output_dir=root / "pair",
            sources=sources,
            clip_configs=(first, second),
            duration=2,
            sample_times=(0.767, 0.833, 0.967, 1.1, 1.233),
            transitions=({"type": "fade", "duration": 0.4},),
        )
        _assert_pairs_pass(result)
