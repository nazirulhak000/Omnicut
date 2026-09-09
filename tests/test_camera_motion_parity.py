"""Source-level contracts for the live camera-motion preview/render seam."""

from pathlib import Path

from scripts.video_editor import CAMERA_MOTION_LIMITS, dynamic_camera_filter


ROOT = Path(__file__).resolve().parents[1]
JS_MATH = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").read_text(encoding="utf-8")
JS_PLAYER = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")


def test_live_camera_limits_match_between_python_and_canvas_contracts():
    assert CAMERA_MOTION_LIMITS == {
        "zoom": (1.0, 3.0),
        "pan_x": (-1.0, 1.0),
        "pan_y": (-1.0, 1.0),
    }
    assert "zoom: { min: 1.0, max: 3.0 }" in JS_MATH
    assert "pan_x: { min: -1.0, max: 1.0 }" in JS_MATH
    assert "pan_y: { min: -1.0, max: 1.0 }" in JS_MATH


def test_preview_evaluates_motion_time_in_every_clip_draw_path():
    assert "resolveClipTransforms" in JS_PLAYER
    assert "function drawVideoFrame(ctx, video, clip, motionTime = 0)" in JS_PLAYER
    assert "drawVideoFrame(ctx, video, clip, motionTime)" in JS_PLAYER
    assert "motionTime: motionTimeAt" in JS_MATH


def test_renderer_uses_per_frame_camera_filter_only_for_camera_keyframes():
    clip = {
        "zoom": 1.0,
        "keyframes": [
            {"time": 0.0, "zoom": 1.0, "pan_x": -0.2},
            {"time": 1.0, "zoom": 1.2, "pan_x": 0.2},
        ],
    }
    dynamic = dynamic_camera_filter(clip, 1.0)
    assert dynamic is not None
    assert "eval=frame" in dynamic
    assert "crop=1080:1920" in dynamic
    assert dynamic_camera_filter({"zoom": 1.0}, 1.0) is None
