"""Regression tests for the shared numeric keyframe interpolation contract."""

from scripts.video_editor import interpolate_keyframes, resolve_clip_transforms


def test_interpolates_and_clamps_numeric_points():
    points = [{"time": 2, "value": 3}, {"time": 0, "value": 1}]
    assert interpolate_keyframes(points, -1, 99) == 1
    assert interpolate_keyframes(points, 1, 99) == 2
    assert interpolate_keyframes(points, 4, 99) == 3


def test_invalid_points_do_not_break_fallback():
    points = [{"time": "bad", "value": 1}, {"time": 0, "value": "bad"}]
    assert interpolate_keyframes(points, 1, 7) == 7


def test_duplicate_times_are_deterministic():
    points = [{"time": 0, "value": 1}, {"time": 0, "value": 4}, {"time": 1, "value": 6}]
    assert interpolate_keyframes(points, 0.5, 0) == 5


def test_live_camera_transform_contract_clamps_and_interpolates():
    clip = {
        "zoom": 1.2,
        "keyframes": [
            {"time": 0, "zoom": 0.2, "pan_x": -4, "pan_y": 0.25},
            {"time": 2, "zoom": 2.2, "pan_x": 4, "pan_y": 1.5},
        ],
    }
    assert resolve_clip_transforms(clip, 0) == {"zoom": 1.0, "pan_x": -1.0, "pan_y": 0.25}
    assert resolve_clip_transforms(clip, 1) == {"zoom": 1.2, "pan_x": 0.0, "pan_y": 0.875}
    assert resolve_clip_transforms(clip, 2) == {"zoom": 2.2, "pan_x": 1.0, "pan_y": 1.0}


def test_live_camera_transform_accepts_property_value_keyframes_and_ignores_bad_points():
    clip = {
        "zoom": 1.1,
        "keyframes": [
            {"time": "bad", "zoom": 1.5},
            {"time": 0, "property": "zoom", "value": 1.1},
            {"time": 2, "property": "zoom", "value": 1.5},
        ],
    }
    assert resolve_clip_transforms(clip, 1)["zoom"] == 1.3
