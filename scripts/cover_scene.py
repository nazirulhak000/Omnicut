"""Pure Cover Scene contract for layered cover composition.

The module deliberately has no filesystem, image, rembg, Pillow, or API
dependencies.  A scene is a JSON-shaped dictionary that can be shared by a
future cover preview and renderer.  Coordinates are always normalized to the
output frame and layer bounds use a top-left origin.

This is a contract module only.  It does not render a cover or resolve an
asset path.  ``normalize_scene`` is the only place where legacy cover fields
are translated into the canonical shape.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from numbers import Real
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = 1
DEFAULT_OUTPUT = "9:16"
SUPPORTED_OUTPUTS: Tuple[str, ...] = ("9:16", "3:4")
LAYOUT_PRODUCT_FRONT_TEXT_UNDER = "product_front_text_under"
SUPPORTED_LAYOUTS: Tuple[str, ...] = (LAYOUT_PRODUCT_FRONT_TEXT_UNDER,)

# The bottom edge for 9:16 leaves 420 render pixels for platform controls and
# captions.  The profile grid has a taller usable area, but keeps the same
# horizontal inset.  These values are contract data, not renderer pixels.
SAFE_ZONES: Dict[str, Dict[str, float]] = {
    "9:16": {"x": 0.06, "y": 0.06, "width": 0.88, "height": 0.72125},
    "3:4": {"x": 0.06, "y": 0.06, "width": 0.88, "height": 0.82125},
}

CONTENT_LAYER_TYPES = {"text", "badge", "callout", "shape"}
BACKGROUND_LAYER_TYPES = {"background", "frame"}
PRODUCT_LAYER_TYPES = {"product", "image", "product_image"}

DEFAULT_BOUNDS: Dict[str, Dict[str, float]] = {
    "background": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
    "frame": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
    "product": {"x": 0.10, "y": 0.20, "width": 0.80, "height": 0.52},
    "image": {"x": 0.10, "y": 0.20, "width": 0.80, "height": 0.52},
    "product_image": {"x": 0.10, "y": 0.20, "width": 0.80, "height": 0.52},
    "text": {"x": 0.06, "y": 0.68, "width": 0.88, "height": 0.08},
    "callout": {"x": 0.06, "y": 0.68, "width": 0.88, "height": 0.08},
    "badge": {"x": 0.06, "y": 0.06, "width": 0.24, "height": 0.08},
    "shape": {"x": 0.06, "y": 0.68, "width": 0.88, "height": 0.08},
}


class CoverSceneValidationError(ValueError):
    """Raised when a scene cannot be represented by the contract."""

    def __init__(self, errors: Sequence[str]):
        self.errors = tuple(errors)
        super().__init__("Invalid cover scene: " + "; ".join(self.errors))


def _is_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(float(value))


def _round(value: float) -> float:
    """Keep JSON output stable without losing useful normalized precision."""
    return round(float(value), 6)


def _as_mapping(value: Any, label: str, errors: List[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        errors.append(f"{label} must be an object")
        return {}
    return value


def _normalise_output(value: Any, errors: List[str]) -> List[str]:
    if value is None:
        return [DEFAULT_OUTPUT]
    if value == "both":
        return list(SUPPORTED_OUTPUTS)
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        errors.append("outputs must be a string or a list")
        return [DEFAULT_OUTPUT]
    result: List[str] = []
    for item in values:
        if item not in SUPPORTED_OUTPUTS:
            errors.append(f"unsupported output: {item!r}")
        elif item not in result:
            result.append(item)
    return result or [DEFAULT_OUTPUT]


def _normalise_bounds(
    raw: Any,
    layer_type: str,
    errors: List[str],
) -> Dict[str, float]:
    source = _as_mapping(raw, "layer.bounds", errors) if raw is not None else {}
    defaults = DEFAULT_BOUNDS.get(layer_type, DEFAULT_BOUNDS["text"])
    bounds: Dict[str, float] = {}
    for key in ("x", "y", "width", "height"):
        value = source.get(key, defaults[key])
        if not _is_number(value):
            errors.append(f"layer.bounds.{key} must be a finite number")
            value = defaults[key]
        bounds[key] = _round(float(value))

    if bounds["width"] <= 0 or bounds["height"] <= 0:
        errors.append("layer.bounds width and height must be greater than zero")
    if bounds["x"] < 0 or bounds["y"] < 0:
        errors.append("layer.bounds x and y must be greater than or equal to zero")
    if bounds["x"] + bounds["width"] > 1 or bounds["y"] + bounds["height"] > 1:
        errors.append("layer.bounds must stay inside normalized frame bounds")
    return bounds


def _normalise_z_index(value: Any, errors: List[str]) -> int:
    if not _is_number(value) or int(float(value)) != float(value):
        errors.append("layer.z_index must be a finite integer")
        return 0
    result = int(value)
    if result < -1000 or result > 1000:
        errors.append("layer.z_index must be between -1000 and 1000")
        return max(-1000, min(1000, result))
    return result


def _layer_id(raw: Mapping[str, Any], index: int, layer_type: str, role: str) -> str:
    value = raw.get("id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"{role or layer_type}-{index + 1:02d}"


def _normalise_layer(raw: Any, index: int, errors: List[str]) -> Dict[str, Any]:
    item = _as_mapping(raw, f"layers[{index}]", errors)
    raw_type = item.get("type", item.get("kind", "text"))
    layer_type = raw_type.strip().lower() if isinstance(raw_type, str) else ""
    if layer_type not in DEFAULT_BOUNDS:
        errors.append(f"layers[{index}].type is unsupported: {raw_type!r}")
        layer_type = "text"

    role_value = item.get("role", "")
    role = role_value.strip() if isinstance(role_value, str) else ""
    if role_value and not role:
        errors.append(f"layers[{index}].role must be a non-empty string")

    opacity = item.get("opacity", 1.0)
    if not _is_number(opacity) or not 0 <= float(opacity) <= 1:
        errors.append(f"layers[{index}].opacity must be between 0 and 1")
        opacity = 1.0

    text = item.get("text")
    if text is not None and not isinstance(text, str):
        errors.append(f"layers[{index}].text must be a string")
        text = str(text)

    source = item.get("source")
    if source is not None and not isinstance(source, Mapping):
        errors.append(f"layers[{index}].source must be an object")
        source = None

    bounds_raw = item.get("bounds")
    if bounds_raw is None and any(key in item for key in ("x", "y", "width", "height")):
        # Accept the flat normalized spelling at the input boundary, but
        # always emit the nested canonical ``bounds`` object.
        bounds_raw = item

    layer: Dict[str, Any] = {
        "id": _layer_id(item, index, layer_type, role),
        "type": layer_type,
        "role": role or None,
        "bounds": _normalise_bounds(bounds_raw, layer_type, errors),
        "z_index": _normalise_z_index(item.get("z_index", index), errors),
        "opacity": _round(float(opacity)),
        "visible": item.get("visible", True),
    }
    if not isinstance(layer["visible"], bool):
        errors.append(f"layers[{index}].visible must be boolean")
        layer["visible"] = bool(layer["visible"])
    if text is not None:
        layer["text"] = text
    if source is not None:
        layer["source"] = deepcopy(dict(source))
    for key in ("color_role", "placement", "fit", "asset_path"):
        if key in item:
            layer[key] = deepcopy(item[key])
    return layer


def _legacy_position(value: Any) -> float:
    return {"top": 0.20, "center": 0.46, "bottom": 0.68}.get(value, 0.20)


def _legacy_layers(raw: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Translate the old RenderProCover fields without touching assets."""
    aspect = raw.get("aspect_ratio", raw.get("output", DEFAULT_OUTPUT))
    source_path = raw.get("custom_image_path") or raw.get("video_path")
    layers: List[Dict[str, Any]] = [
        {
            "id": "legacy-background",
            "type": "background",
            "role": "background",
            "bounds": DEFAULT_BOUNDS["background"],
            "z_index": 0,
            "source": {"kind": "legacy_frame", "path": source_path} if source_path else None,
        }
    ]
    position = _legacy_position(raw.get("hook_position"))
    hook_text = raw.get("hook_text", "")
    if hook_text:
        layers.append({
            "id": "legacy-hook",
            "type": "text",
            "role": "model",
            "text": hook_text,
            "bounds": {"x": 0.06, "y": position, "width": 0.88, "height": 0.12},
            "z_index": 20,
            "color_role": "primary",
            "placement": "under",
        })
    sub_text = raw.get("sub_text")
    if sub_text:
        layers.append({
            "id": "legacy-sub",
            "type": "text",
            "role": "feature",
            "text": sub_text,
            "bounds": {"x": 0.06, "y": min(position + 0.13, 0.83), "width": 0.88, "height": 0.08},
            "z_index": 30,
            "color_role": "secondary",
        })
    return layers


def _validate_safe_zones(scene: Mapping[str, Any], errors: List[str]) -> None:
    safe_zones = scene["safe_zones"]
    for output in scene["outputs"]:
        safe = safe_zones[output]
        for layer in scene["layers"]:
            if not layer["visible"] or layer["type"] not in CONTENT_LAYER_TYPES:
                continue
            bounds = layer["bounds"]
            inside = (
                bounds["x"] >= safe["x"]
                and bounds["y"] >= safe["y"]
                and bounds["x"] + bounds["width"] <= safe["x"] + safe["width"]
                and bounds["y"] + bounds["height"] <= safe["y"] + safe["height"]
            )
            if not inside:
                errors.append(f"layer {layer['id']!r} exceeds safe zone for output {output}")


def _build_scene(raw: Any) -> Tuple[Dict[str, Any], List[str]]:
    errors: List[str] = []
    if not isinstance(raw, Mapping):
        return {}, ["scene must be an object"]

    has_layers = "layers" in raw
    layout_raw = raw.get("layout", {})
    layout = _as_mapping(layout_raw, "layout", errors)
    preset = layout.get("preset", raw.get("layout_preset", LAYOUT_PRODUCT_FRONT_TEXT_UNDER))
    if preset not in SUPPORTED_LAYOUTS:
        errors.append(f"unsupported layout preset: {preset!r}")
        preset = LAYOUT_PRODUCT_FRONT_TEXT_UNDER

    aspect = raw.get("aspect_ratio")
    outputs_raw = raw.get("outputs", raw.get("output", aspect))
    outputs = _normalise_output(outputs_raw, errors)

    raw_layers = raw.get("layers") if has_layers else _legacy_layers(raw)
    if not isinstance(raw_layers, Sequence) or isinstance(raw_layers, (str, bytes)):
        errors.append("layers must be a list")
        raw_layers = []
    layers = [_normalise_layer(layer, index, errors) for index, layer in enumerate(raw_layers)]
    ids = [layer["id"] for layer in layers]
    if len(ids) != len(set(ids)):
        errors.append("layer ids must be unique")

    theme_raw = _as_mapping(raw.get("theme", {}), "theme", errors)
    theme: Dict[str, Any] = {}
    for key in ("primary", "secondary", "neutral", "ink"):
        if key in theme_raw:
            value = theme_raw[key]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"theme.{key} must be a non-empty string")
            else:
                theme[key] = value.strip()

    scene: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "outputs": outputs,
        "layout": {"preset": preset},
        "safe_zones": {output: deepcopy(SAFE_ZONES[output]) for output in outputs},
        "theme": theme,
        "layers": sorted(layers, key=lambda layer: (layer["z_index"], layer["id"])),
        "legacy_fallback": not has_layers,
    }
    scene["layer_order"] = [layer["id"] for layer in scene["layers"]]
    _validate_safe_zones(scene, errors)

    if preset == LAYOUT_PRODUCT_FRONT_TEXT_UNDER:
        product_layers = [layer for layer in layers if layer["type"] in PRODUCT_LAYER_TYPES]
        behind_layers = [layer for layer in layers if layer.get("placement") == "behind"]
        if behind_layers and not product_layers:
            errors.append("product_front_text_under requires a product layer for behind text")
        if product_layers and behind_layers:
            product_z = min(layer["z_index"] for layer in product_layers)
            if any(layer["z_index"] >= product_z for layer in behind_layers):
                errors.append("behind layers must have a lower z_index than the product layer")
    return scene, errors


def validate_scene(scene: Any) -> List[str]:
    """Return deterministic validation messages; an empty list means valid."""
    _, errors = _build_scene(scene)
    return errors


def normalize_scene(scene: Any) -> Dict[str, Any]:
    """Validate and return a detached, canonical scene dictionary."""
    normalized, errors = _build_scene(scene)
    if errors:
        raise CoverSceneValidationError(errors)
    return normalized


def bounds_for_output(scene: Mapping[str, Any], output: str) -> Dict[str, int]:
    """Return the canonical pixel canvas size for a supported output."""
    if output not in SUPPORTED_OUTPUTS:
        raise ValueError(f"unsupported output: {output!r}")
    return {"width": 1080, "height": 1920 if output == "9:16" else 1440}
