"""Safe, explicit recolouring policy for baked overlay media.

The source files in ``02_Assets`` are deliberately left untouched.  Only
decorative assets listed here may opt into accent hue rotation; product and
semantic badge artwork stays unchanged unless a manifest item explicitly
requests the ``accent`` mode.
"""

import colorsys
import math
from typing import Any, Dict, Optional


ACCENT_RECOLOR_MODE = "accent"
# The bundled Lottie exports are predominantly blue/cyan around 205 degrees;
# using that measured source hue keeps the clean-tech accent target yellow
# instead of shifting the blue gradients into olive.
DEFAULT_EFFECT_SOURCE_HUE = 205.0

# These are decorative overlays whose colour is part of the visual language,
# rather than product/semantic artwork whose original colours carry meaning.
SAFE_STICKER_SOURCE_HUES = {
    "accent_sparkle_star_3d": 52.0,
    "arrow_pointer_cyan_3d": 180.0,
    "arrow_pointer_yellow_3d": 52.0,
    "arrow_tech_cyan_3d": 180.0,
    "frame_tech_callout_3d": 180.0,
    "frame_tech_callout_hollow_3d": 180.0,
    "hud_callout_bracket_3d": 180.0,
    "plate_banner_coral_3d": 8.0,
    "plate_banner_cyan_3d": 180.0,
    "plate_banner_yellow_3d": 52.0,
}


def _asset_stem(asset_id: Any) -> str:
    value = str(asset_id or "").strip().replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in (".png", ".webp", ".jpg", ".webm", ".mov"):
        if value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def overlay_asset_recolor_metadata(kind: str, asset_id: Any) -> Dict[str, Any]:
    """Return safe opt-in metadata for a registry asset."""
    stem = _asset_stem(asset_id)
    if kind == "sticker" and stem in SAFE_STICKER_SOURCE_HUES:
        return {
            "recolorable": True,
            "recolor_source_hue": SAFE_STICKER_SOURCE_HUES[stem],
        }
    if kind == "effect" and stem.startswith("fx_"):
        return {
            "recolorable": True,
            "recolor_source_hue": DEFAULT_EFFECT_SOURCE_HUE,
        }
    return {"recolorable": False}


def _hex_to_hue(value: Any) -> Optional[float]:
    if not isinstance(value, str):
        return None
    raw = value.strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(char * 2 for char in raw)
    if len(raw) != 6:
        return None
    try:
        rgb = tuple(int(raw[index:index + 2], 16) / 255.0 for index in (0, 2, 4))
    except ValueError:
        return None
    hue, _saturation, _value = colorsys.rgb_to_hsv(*rgb)
    return hue * 360.0


def _finite_hue(value: Any, fallback: Optional[float]) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if math.isfinite(number) else fallback


def _shortest_hue_delta(target: float, source: float) -> float:
    delta = (target - source + 180.0) % 360.0 - 180.0
    return 180.0 if delta == -180.0 else delta


def resolve_overlay_recolor(
    item: Any,
    palette: Dict[str, str],
    *,
    kind: str = "",
    asset_id: Any = None,
) -> Optional[Dict[str, Any]]:
    """Resolve an explicit accent request into a deterministic hue rotation."""
    data = item if isinstance(item, dict) else {}
    requested = data.get("recolor", data.get("tint"))
    if requested is True:
        requested = ACCENT_RECOLOR_MODE
    if str(requested or "").strip().lower() != ACCENT_RECOLOR_MODE:
        return None

    metadata = overlay_asset_recolor_metadata(kind, asset_id)
    source_hue = _finite_hue(
        data.get("recolor_source_hue", data.get("recolorSourceHue")),
        metadata.get("recolor_source_hue"),
    )
    target_hue = _hex_to_hue(palette.get("primary"))
    if source_hue is None or target_hue is None:
        return None
    return {
        "mode": ACCENT_RECOLOR_MODE,
        "source_hue": source_hue,
        "target_hue": target_hue,
        "delta": _shortest_hue_delta(target_hue, source_hue),
    }


def build_overlay_hue_filter(
    input_label: str,
    output_label: str,
    item: Any,
    palette: Dict[str, str],
    *,
    kind: str = "",
    asset_id: Any = None,
) -> str:
    """Build the FFmpeg fragment mirrored by Canvas ``hue-rotate``."""
    recolor = resolve_overlay_recolor(item, palette, kind=kind, asset_id=asset_id)
    if not recolor:
        return ""
    return f"{input_label}hue=h={recolor['delta']:.3f}{output_label};"
