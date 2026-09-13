"""Pure Product Spotlight contract and safe FFmpeg filter builder.

This module describes a deterministic *focus overlay*: the full video is
dimmed and the selected ellipse/rectangle/rounded rectangle remains bright.
It is intentionally not a video cutout or background-removal implementation.
The returned filter graph is only a string; callers decide when and how to
run FFmpeg.  No filesystem, subprocess, rembg, or ONNX dependency is used.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from numbers import Real
from typing import Any


SCHEMA_VERSION = 1
SUPPORTED_SHAPES = ("ellipse", "rectangle", "rounded_rect")
DEFAULT_SHAPE = "ellipse"
DEFAULT_FOCUS = {"x": 0.5, "y": 0.5, "width": 0.62, "height": 0.42}
DEFAULT_DIM_OPACITY = 0.42
DEFAULT_FEATHER = 0.035
DEFAULT_CORNER_RADIUS = 0.08
MAX_DIM_OPACITY = 0.95
MAX_FEATHER = 0.25
MAX_FRAME_DIMENSION = 16384


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def _rounded(value: float) -> float:
    return round(float(value), 6)


def _no_op(reason: str) -> dict[str, Any]:
    """Return a stable disabled contract for missing/invalid input."""

    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": False,
        "shape": DEFAULT_SHAPE,
        "focus": dict(DEFAULT_FOCUS),
        "dim_opacity": DEFAULT_DIM_OPACITY,
        "feather": DEFAULT_FEATHER,
        "corner_radius": DEFAULT_CORNER_RADIUS,
        "reason": reason,
    }


def is_no_op(value: Any) -> bool:
    """Return whether a value normalises to a disabled/no-op effect."""

    return not normalize_spotlight(value)["enabled"]


def _normalise_shape(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    aliases = {
        "rect": "rectangle",
        "rounded-rect": "rounded_rect",
        "rounded-rectangle": "rounded_rect",
    }
    shape = aliases.get(value.strip().lower(), value.strip().lower())
    return shape if shape in SUPPORTED_SHAPES else None


def _normalise_number(mapping: Mapping[str, Any], key: str, default: float) -> float:
    value = mapping.get(key, default)
    return float(value) if _is_finite_number(value) else default


def normalize_spotlight(value: Any) -> dict[str, Any]:
    """Return a canonical, clamped SpotlightV1 dictionary.

    Spotlight is opt-in.  Missing input, an unsupported schema, a non-boolean
    ``enabled`` value, or an unknown shape produces a disabled no-op.  Invalid
    optional numeric fields use safe defaults, while valid extreme numbers are
    clamped to the frame and opacity/feather limits.
    """

    if value is None:
        return _no_op("missing")
    if not isinstance(value, Mapping):
        return _no_op("invalid_config")

    schema_version = value.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        return _no_op("unsupported_schema")

    enabled = value.get("enabled", False)
    if not isinstance(enabled, bool):
        return _no_op("invalid_enabled")
    if not enabled:
        return _no_op("disabled")

    shape = _normalise_shape(value.get("shape", DEFAULT_SHAPE))
    if shape is None:
        return _no_op("invalid_shape")

    raw_focus = value.get("focus", DEFAULT_FOCUS)
    if raw_focus is None:
        raw_focus = DEFAULT_FOCUS
    if not isinstance(raw_focus, Mapping):
        return _no_op("invalid_focus")

    width = _clamp(_normalise_number(raw_focus, "width", DEFAULT_FOCUS["width"]), 0.02, 1.0)
    height = _clamp(_normalise_number(raw_focus, "height", DEFAULT_FOCUS["height"]), 0.02, 1.0)
    half_width = width / 2.0
    half_height = height / 2.0
    center_x = _clamp(_normalise_number(raw_focus, "x", DEFAULT_FOCUS["x"]), half_width, 1.0 - half_width)
    center_y = _clamp(_normalise_number(raw_focus, "y", DEFAULT_FOCUS["y"]), half_height, 1.0 - half_height)

    dim_opacity = _clamp(
        _normalise_number(value, "dim_opacity", DEFAULT_DIM_OPACITY),
        0.0,
        MAX_DIM_OPACITY,
    )
    feather = _clamp(_normalise_number(value, "feather", DEFAULT_FEATHER), 0.0, MAX_FEATHER)
    corner_radius = _clamp(_normalise_number(value, "corner_radius", DEFAULT_CORNER_RADIUS), 0.0, 0.5)
    corner_radius = min(corner_radius, min(width, height) / 2.0)

    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": True,
        "shape": shape,
        "focus": {
            "x": _rounded(center_x),
            "y": _rounded(center_y),
            "width": _rounded(width),
            "height": _rounded(height),
        },
        "dim_opacity": _rounded(dim_opacity),
        "feather": _rounded(feather),
        "corner_radius": _rounded(corner_radius),
    }


def serialize_spotlight(value: Any) -> str:
    """Serialise the canonical contract with stable key ordering."""

    return json.dumps(normalize_spotlight(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deserialize_spotlight(value: Any) -> dict[str, Any]:
    """Parse JSON safely; malformed payloads become a disabled no-op."""

    if not isinstance(value, str):
        return _no_op("invalid_serialized_config")
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return _no_op("invalid_serialized_config")
    return normalize_spotlight(decoded)


def _safe_dimension(value: Any) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value < 1 or value > MAX_FRAME_DIMENSION:
        return None
    return value


def _number(value: float) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".") or "0"


def _mask_condition(effect: Mapping[str, Any], width: int, height: int) -> str:
    focus = effect["focus"]
    cx = float(focus["x"]) * width
    cy = float(focus["y"]) * height
    half_width = float(focus["width"]) * width / 2.0
    half_height = float(focus["height"]) * height / 2.0
    left, right = cx - half_width, cx + half_width
    top, bottom = cy - half_height, cy + half_height

    if effect["shape"] == "ellipse":
        dx = f"(X-{_number(cx)})"
        dy = f"(Y-{_number(cy)})"
        return f"({dx}*{dx}/{_number(half_width * half_width)}+{dy}*{dy}/{_number(half_height * half_height)}<=1)"

    horizontal = f"gte(X\\,{_number(left)})*lte(X\\,{_number(right)})"
    vertical = f"gte(Y\\,{_number(top)})*lte(Y\\,{_number(bottom)})"
    if effect["shape"] == "rectangle":
        return f"({horizontal}*{vertical})"

    radius = min(
        float(effect["corner_radius"]) * min(width, height),
        half_width,
        half_height,
    )
    inner_horizontal = f"gte(X\\,{_number(left + radius)})*lte(X\\,{_number(right - radius)})"
    inner_vertical = f"gte(Y\\,{_number(top + radius)})*lte(Y\\,{_number(bottom - radius)})"
    center_bands = f"({inner_horizontal}*{vertical}+{horizontal}*{inner_vertical})"
    radius_sq = _number(radius * radius)
    corners = (
        f"(lt(X\\,{_number(left + radius)})*lt(Y\\,{_number(top + radius)})*"
        f"lte((X-{_number(left + radius)})*(X-{_number(left + radius)})+"
        f"(Y-{_number(top + radius)})*(Y-{_number(top + radius)})\\,{radius_sq})+"
        f"(gt(X\\,{_number(right - radius)})*lt(Y\\,{_number(top + radius)})*"
        f"lte((X-{_number(right - radius)})*(X-{_number(right - radius)})+"
        f"(Y-{_number(top + radius)})*(Y-{_number(top + radius)})\\,{radius_sq})+"
        f"(lt(X\\,{_number(left + radius)})*gt(Y\\,{_number(bottom - radius)})*"
        f"lte((X-{_number(left + radius)})*(X-{_number(left + radius)})+"
        f"(Y-{_number(bottom - radius)})*(Y-{_number(bottom - radius)})\\,{radius_sq})+"
        f"(gt(X\\,{_number(right - radius)})*gt(Y\\,{_number(bottom - radius)})*"
        f"lte((X-{_number(right - radius)})*(X-{_number(right - radius)})+"
        f"(Y-{_number(bottom - radius)})*(Y-{_number(bottom - radius)})\\,{radius_sq}))"
    )
    return f"({center_bands}+{corners})"


def build_ffmpeg_filter(value: Any, width: Any, height: Any) -> str | None:
    """Build a shell-independent FFmpeg filtergraph fragment or ``None``.

    The fragment expects the source video as ``[0:v]`` and emits the final
    video stream.  All user-controlled values are normalised numbers or a
    fixed shape whitelist, so arbitrary filter directives cannot be injected.
    It dims the source once and applies a static mask to every frame; it does
    not run segmentation, rembg, or ONNX inference.
    """

    frame_width = _safe_dimension(width)
    frame_height = _safe_dimension(height)
    effect = normalize_spotlight(value)
    if frame_width is None or frame_height is None or not effect["enabled"]:
        return None
    if effect["dim_opacity"] <= 0:
        return None

    dim_gain = _number(1.0 - float(effect["dim_opacity"]))
    condition = _mask_condition(effect, frame_width, frame_height)
    mask = f"if({condition}\\,255\\,0)"
    labels = (
        f"[0:v]split=2[spot_src][spot_focus];"
        f"[spot_src]colorchannelmixer=rr={dim_gain}:gg={dim_gain}:bb={dim_gain}[spot_dim];"
        f"color=c=black@0.0:s={frame_width}x{frame_height},format=gray,geq=lum={mask}[spot_mask_raw];"
    )
    if effect["feather"] > 0:
        sigma = _number(float(effect["feather"]) * min(frame_width, frame_height))
        labels += f"[spot_mask_raw]gblur=sigma={sigma}[spot_mask];"
    else:
        labels += "[spot_mask_raw]copy[spot_mask];"
    return labels + "[spot_focus]format=rgba[spot_fg];[spot_fg][spot_mask]alphamerge[spot_cut];[spot_dim][spot_cut]overlay=0:0:format=auto"


def build_spotlight_filter(value: Any, width: Any, height: Any) -> str | None:
    """Compatibility alias with a concise name for future callers."""

    return build_ffmpeg_filter(value, width, height)
