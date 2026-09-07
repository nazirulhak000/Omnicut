"""
Tests keyframe interpolation parity between Python and JavaScript models.
Ensures mathematical consistency at 0%, 25%, 50%, 75%, and 100% time points.

NOTE: as of 2026-09-07, scripts/keyframe_engine.py and its JS twin
frontend/src/lib/keyframeModel.js are both dormant (Phase 9 scaffolding,
never wired into a live caller on either side). This test locks their
mutual parity, not their correctness against production behavior — see
the STATUS note atop scripts/keyframe_engine.py before assuming otherwise.
"""

from scripts.keyframe_engine import (
    EASING_MAP,
    clamp_property,
    interpolate_numeric_keyframes,
    resolve_clip_transforms,
)


def test_easing_functions_match_contract():
    for name, fn in EASING_MAP.items():
        assert fn(0.0) == 0.0, f"{name} at 0.0"
        assert fn(1.0) == 1.0, f"{name} at 1.0"

    assert EASING_MAP["linear"](0.5) == 0.5
    assert EASING_MAP["ease_in"](0.5) == 0.25
    assert EASING_MAP["ease_out"](0.5) == 0.75
    assert EASING_MAP["ease_in_out"](0.5) == 0.5


def test_clamp_property_parity():
    assert clamp_property("zoom", 0.2) == 0.5
    assert clamp_property("zoom", 3.5) == 3.0
    assert clamp_property("pan_x", -1.5) == -1.0
    assert clamp_property("pan_x", 2.0) == 1.0
    assert clamp_property("opacity", -0.1) == 0.0
    assert clamp_property("opacity", 1.2) == 1.0
    assert clamp_property("volume", -0.5) == 0.0
    assert clamp_property("volume", 3.0) == 2.0


def test_keyframe_interpolation_at_cardinal_points():
    kf = [
        {"time": 0.0, "value": 1.0, "easing": "linear"},
        {"time": 4.0, "value": 3.0, "easing": "linear"},
    ]

    # Cardinal checkpoints: 0%, 25%, 50%, 75%, 100%
    assert round(interpolate_numeric_keyframes(kf, 0.0), 4) == 1.0000
    assert round(interpolate_numeric_keyframes(kf, 1.0), 4) == 1.5000
    assert round(interpolate_numeric_keyframes(kf, 2.0), 4) == 2.0000
    assert round(interpolate_numeric_keyframes(kf, 3.0), 4) == 2.5000
    assert round(interpolate_numeric_keyframes(kf, 4.0), 4) == 3.0000

    # Outside boundaries hold
    assert round(interpolate_numeric_keyframes(kf, -1.0), 4) == 1.0000
    assert round(interpolate_numeric_keyframes(kf, 5.0), 4) == 3.0000


def test_resolve_clip_transforms_parity():
    clip = {
        "zoom": 1.0,
        "keyframes": [
            {"time": 0.0, "zoom": 1.0, "pan_x": 0.0, "volume": 1.0},
            {"time": 2.0, "zoom": 1.5, "pan_x": 0.5, "volume": 0.0},
        ],
    }

    t0 = resolve_clip_transforms(clip, 0.0)
    assert t0["zoom"] == 1.0
    assert t0["pan_x"] == 0.0
    assert t0["volume"] == 1.0

    t_mid = resolve_clip_transforms(clip, 1.0)
    assert t_mid["zoom"] == 1.25
    assert t_mid["pan_x"] == 0.25
    assert t_mid["volume"] == 0.5

    t_end = resolve_clip_transforms(clip, 2.0)
    assert t_end["zoom"] == 1.5
    assert t_end["pan_x"] == 0.5
    assert t_end["volume"] == 0.0
