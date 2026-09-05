"""Regression tests for the shared numeric keyframe interpolation contract."""

from scripts.video_editor import interpolate_keyframes


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
