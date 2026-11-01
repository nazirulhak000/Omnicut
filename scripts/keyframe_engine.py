"""
Keyframe Animation Engine (Python Parity Implementation).
Guarantees 100% mathematical parity with frontend/src/lib/keyframeModel.js
for Zoom, Pan, Opacity, and Volume keyframe interpolation across render stages.
Upgraded with CapCut 7.1 Parametric Cubic-Bézier and 9:16 Smart Camera Motion.
"""

from typing import Dict, List, Optional, Tuple, Any, Union


def solve_cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float, t: float) -> float:
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if p1x == p1y and p2x == p2y:
        return t

    cx = 3.0 * p1x
    bx = 3.0 * (p2x - p1x) - cx
    ax = 1.0 - cx - bx

    cy = 3.0 * p1y
    by = 3.0 * (p2y - p1y) - cy
    ay = 1.0 - cy - by

    def sample_x(u: float) -> float:
        return ((ax * u + bx) * u + cx) * u

    def sample_y(u: float) -> float:
        return ((ay * u + by) * u + cy) * u

    def sample_dx(u: float) -> float:
        return (3.0 * ax * u + 2.0 * bx) * u + cx

    # Newton-Raphson iteration
    u = t
    for _ in range(8):
        x_err = sample_x(u) - t
        if abs(x_err) < 1e-7:
            return sample_y(u)
        dx = sample_dx(u)
        if abs(dx) < 1e-6:
            break
        u -= x_err / dx

    # Binary subdivision fallback
    u0 = 0.0
    u1 = 1.0
    u = t
    for _ in range(16):
        x_curr = sample_x(u)
        if abs(x_curr - t) < 1e-7:
            return sample_y(u)
        if x_curr > t:
            u1 = u
        else:
            u0 = u
        u = (u0 + u1) * 0.5

    return sample_y(u)


CUBIC_BEZIER_PRESETS = {
    "linear": [0.0, 0.0, 1.0, 1.0],
    "ease_in": [0.42, 0.0, 1.0, 1.0],
    "ease_out": [0.0, 0.0, 0.58, 1.0],
    "ease_in_out": [0.42, 0.0, 0.58, 1.0],
    "montage": [0.7, 0.0, 0.3, 1.0],
    "hero_in": [0.0, 0.0, 0.2, 1.0],
    "bullet_stop": [0.17, 0.89, 0.32, 1.28],
    "jump_cut": [1.0, 0.0, 0.0, 1.0],
}


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
    "montage": lambda t: solve_cubic_bezier(0.7, 0.0, 0.3, 1.0, t),
    "hero_in": lambda t: solve_cubic_bezier(0.0, 0.0, 0.2, 1.0, t),
    "bullet_stop": lambda t: solve_cubic_bezier(0.17, 0.89, 0.32, 1.28, t),
    "jump_cut": lambda t: solve_cubic_bezier(1.0, 0.0, 0.0, 1.0, t),
}


def resolve_easing_ratio(easing_spec: Any, raw_ratio: float) -> float:
    t = min(1.0, max(0.0, float(raw_ratio)))
    if not easing_spec:
        return t

    if isinstance(easing_spec, str):
        if easing_spec in CUBIC_BEZIER_PRESETS:
            pts = CUBIC_BEZIER_PRESETS[easing_spec]
            return solve_cubic_bezier(pts[0], pts[1], pts[2], pts[3], t)
        if easing_spec in EASING_MAP:
            return EASING_MAP[easing_spec](t)
        return t

    if isinstance(easing_spec, (list, tuple)) and len(easing_spec) == 4:
        return solve_cubic_bezier(easing_spec[0], easing_spec[1], easing_spec[2], easing_spec[3], t)

    if isinstance(easing_spec, dict):
        if easing_spec.get("curve") == "cubic_bezier" and isinstance(easing_spec.get("points"), (list, tuple)):
            pts = easing_spec["points"]
            if len(pts) == 4:
                return solve_cubic_bezier(pts[0], pts[1], pts[2], pts[3], t)

    return t


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
    valid_points = []
    for p in keyframes or []:
        if isinstance(p, dict) and "time" in p and "value" in p:
            try:
                t_val = float(p["time"])
                v_val = float(p["value"])
                easing = p.get("easing") or default_easing
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
            eased_ratio = resolve_easing_ratio(right["easing"], raw_ratio)

            return left["value"] + (right["value"] - left["value"]) * eased_ratio

    return valid_points[-1]["value"]


def resolve_clip_transforms(clip: Dict[str, Any], local_time: float) -> Dict[str, float]:
    keyframes = clip.get("keyframes") if isinstance(clip.get("keyframes"), list) else []

    def extract_track(prop: str) -> List[Dict[str, Any]]:
        track = []
        for k in keyframes:
            if isinstance(k, dict):
                if prop in k:
                    track.append({"time": k.get("time", 0.0), "value": k[prop], "easing": k.get("easing")})
                elif k.get("property") == prop:
                    track.append({"time": k.get("time", 0.0), "value": k.get("value"), "easing": k.get("easing")})
        return track

    zoom_track = extract_track("zoom")
    pan_x_track = extract_track("pan_x")
    pan_y_track = extract_track("pan_y")
    opacity_track = extract_track("opacity")
    volume_track = extract_track("volume")

    base_zoom = float(clip.get("zoom", clip.get("scale", PROPERTY_DEFAULTS["zoom"])))
    base_pan_x = float(clip.get("pan_x", clip.get("x", PROPERTY_DEFAULTS["pan_x"])))
    base_pan_y = float(clip.get("pan_y", clip.get("y", PROPERTY_DEFAULTS["pan_y"])))
    base_opacity = float(clip.get("opacity", PROPERTY_DEFAULTS["opacity"]))
    base_volume = float(clip.get("volume", PROPERTY_DEFAULTS["volume"]))

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


SMART_CAMERA_CONFIG = {
    "vertical_strength": 0.6,
    "horizon_strength": 0.2,
    "base_crop": 0.8,
    "smooth_size": 3,
}


def generate_smart_camera_keyframes(duration: float = 5.0, preset: str = "slow_push") -> List[Dict[str, Any]]:
    dur = max(0.5, float(duration or 5.0))
    base_zoom = 1.0 / SMART_CAMERA_CONFIG["base_crop"]  # 1.25
    vs = SMART_CAMERA_CONFIG["vertical_strength"]  # 0.6
    hs = SMART_CAMERA_CONFIG["horizon_strength"]  # 0.2

    if preset == "slow_push":
        return [
            {"time": 0.0, "zoom": base_zoom, "pan_x": 0.0, "pan_y": 0.0, "easing": "ease_out"},
            {"time": dur, "zoom": base_zoom * 1.15, "pan_x": 0.0, "pan_y": -0.05 * vs, "easing": "linear"},
        ]
    elif preset == "slow_pull":
        return [
            {"time": 0.0, "zoom": base_zoom * 1.15, "pan_x": 0.0, "pan_y": -0.05 * vs, "easing": "ease_out"},
            {"time": dur, "zoom": base_zoom, "pan_x": 0.0, "pan_y": 0.0, "easing": "linear"},
        ]
    elif preset == "pan_left":
        return [
            {"time": 0.0, "zoom": base_zoom * 1.05, "pan_x": 0.1 * hs, "pan_y": 0.0, "easing": "ease_in_out"},
            {"time": dur, "zoom": base_zoom * 1.05, "pan_x": -0.1 * hs, "pan_y": 0.0, "easing": "linear"},
        ]
    elif preset == "pan_right":
        return [
            {"time": 0.0, "zoom": base_zoom * 1.05, "pan_x": -0.1 * hs, "pan_y": 0.0, "easing": "ease_in_out"},
            {"time": dur, "zoom": base_zoom * 1.05, "pan_x": 0.1 * hs, "pan_y": 0.0, "easing": "linear"},
        ]

    return [
        {"time": 0.0, "zoom": base_zoom, "pan_x": 0.0, "pan_y": 0.0, "easing": "linear"},
        {"time": dur, "zoom": base_zoom, "pan_x": 0.0, "pan_y": 0.0, "easing": "linear"},
    ]
