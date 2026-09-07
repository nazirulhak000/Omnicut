"""
Keyframe Animation Engine (Python Parity Implementation).
Guarantees 100% mathematical parity with frontend/src/lib/keyframeModel.js
for Zoom, Pan, Opacity, and Volume keyframe interpolation across render stages.

STATUS (2026-09-07): Scaffolded in Phase 9 (per-clip Zoom/Pan/Opacity/Volume
keyframe tracks on Timeline v2) and accepted as PASS at the data-model layer,
but never wired into a live caller. `scripts/video_editor.py` still uses its
own, simpler `interpolate_keyframes` (linear only, no easing/clamping/tier
resolution) for the actual render pipeline; the JS twin
`frontend/src/lib/keyframeModel.js` is likewise not imported by any live
frontend component (only by its own test). Only `tests/test_keyframe_parity.py`
currently exercises this module, so it verifies parity between two modules
that are both dormant, not a guarantee about production behavior.

Do not assume this module is on the render or preview path. If you want to
actually wire it in (e.g. give video_editor.py real easing/clamping), that is
still a live TODO — this file is ready to be the Python half of that, but
nothing has connected it yet. If you are looking for the numeric keyframe
interpolation that actually runs in the pipeline today, see
`interpolate_keyframes` in `scripts/video_editor.py`; for the live per-clip
timeline keyframe math, see `interpolateKeyframes` in
`frontend/src/lib/timelineMath.js`; for live hook/text-overlay easing, see
`hookKeyframeAt`-style power-law easing in `frontend/src/components/SequencePlayer.jsx`.
"""

from typing import Dict, List, Optional, Tuple, Any


def ease_linear(t: float) -> float:
    return t


def ease_in(t: float) -> float:
    return t * t


def ease_out(t: float) -> float:
    return t * (2.0 - t)


def ease_in_out(t: float) -> float:
    return 2.0 * t * t if t < 0.5 else -1.0 + (4.0 - 2.0 * t) * t


EASING_MAP = {
    "linear": ease_linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
}

PROPERTY_DEFAULTS = {
    "zoom": 1.0,
    "pan_x": 0.0,
    "pan_y": 0.0,
    "opacity": 1.0,
    "volume": 1.0,
}

PROPERTY_BOUNDS = {
    "zoom": (0.5, 3.0),
    "pan_x": (-1.0, 1.0),
    "pan_y": (-1.0, 1.0),
    "opacity": (0.0, 1.0),
    "volume": (0.0, 2.0),
}


def clamp_property(prop: str, value: float) -> float:
    bounds = PROPERTY_BOUNDS.get(prop)
    if not bounds:
        return value
    return max(bounds[0], min(bounds[1], value))


def interpolate_numeric_keyframes(
    keyframes: List[Dict[str, Any]],
    time: float,
    fallback: float = 1.0,
    default_easing: str = "linear",
) -> float:
    """
    Interpolates numeric keyframes at `time` seconds using specified or default easing.
    Parity matched with frontend JavaScript implementation.
    """
    valid_points = []
    for p in keyframes or []:
        if isinstance(p, dict) and "time" in p and "value" in p:
            try:
                t_val = float(p["time"])
                v_val = float(p["value"])
                easing = str(p.get("easing") or default_easing)
                valid_points.append({"time": t_val, "value": v_val, "easing": easing})
            except (ValueError, TypeError):
                continue

    if not valid_points:
        return fallback

    valid_points.sort(key=lambda x: x["time"])

    if time <= valid_points[0]["time"]:
        return valid_points[0]["value"]
    if time >= valid_points[-1]["time"]:
        return valid_points[-1]["value"]

    for i in range(1, len(valid_points)):
        right = valid_points[i]
        if time <= right["time"]:
            left = valid_points[i - 1]
            span = right["time"] - left["time"]
            if span <= 0:
                return right["value"]
            raw_ratio = (time - left["time"]) / span
            easing_fn = EASING_MAP.get(right["easing"], ease_linear)
            eased_ratio = easing_fn(max(0.0, min(1.0, raw_ratio)))
            return left["value"] + (right["value"] - left["value"]) * eased_ratio

    return valid_points[-1]["value"]


def resolve_clip_transforms(clip: Dict[str, Any], local_time: float) -> Dict[str, float]:
    """
    Resolves Zoom, Pan X/Y, Opacity, and Volume for a clip at local clip time.
    """
    keyframes = clip.get("keyframes") or []

    def extract_track(prop: str) -> List[Dict[str, Any]]:
        points = []
        for k in keyframes:
            if not isinstance(k, dict):
                continue
            if prop in k:
                points.append({"time": k["time"], "value": k[prop], "easing": k.get("easing")})
            elif k.get("property") == prop and "value" in k:
                points.append({"time": k["time"], "value": k["value"], "easing": k.get("easing")})
        return points

    zoom_track = extract_track("zoom")
    pan_x_track = extract_track("pan_x")
    pan_y_track = extract_track("pan_y")
    opacity_track = extract_track("opacity")
    volume_track = extract_track("volume")

    base_zoom = float(clip.get("zoom") or clip.get("scale") or PROPERTY_DEFAULTS["zoom"])
    base_pan_x = float(clip.get("pan_x") or clip.get("x") or PROPERTY_DEFAULTS["pan_x"])
    base_pan_y = float(clip.get("pan_y") or clip.get("y") or PROPERTY_DEFAULTS["pan_y"])
    base_opacity = float(clip.get("opacity") or PROPERTY_DEFAULTS["opacity"])
    base_volume = float(clip.get("volume") or PROPERTY_DEFAULTS["volume"])

    raw_zoom = interpolate_numeric_keyframes(zoom_track, local_time, base_zoom) if zoom_track else base_zoom
    raw_pan_x = interpolate_numeric_keyframes(pan_x_track, local_time, base_pan_x) if pan_x_track else base_pan_x
    raw_pan_y = interpolate_numeric_keyframes(pan_y_track, local_time, base_pan_y) if pan_y_track else base_pan_y
    raw_opacity = interpolate_numeric_keyframes(opacity_track, local_time, base_opacity) if opacity_track else base_opacity
    raw_volume = interpolate_numeric_keyframes(volume_track, local_time, base_volume) if volume_track else base_volume

    return {
        "zoom": clamp_property("zoom", raw_zoom),
        "pan_x": clamp_property("pan_x", raw_pan_x),
        "pan_y": clamp_property("pan_y", raw_pan_y),
        "opacity": clamp_property("opacity", raw_opacity),
        "volume": clamp_property("volume", raw_volume),
    }
