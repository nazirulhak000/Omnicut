"""
Font Metrics and Font Family Mapping for Subtitle Engine.
Handles fontTools-based vertical glyph scaling, PIL-based pixel text measurement,
and font family resolution against AssetRegistry and typography presets.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from scripts.config import FONTS_DIR
from scripts.asset_registry import AssetRegistry

TYPOGRAPHY_PRESETS_PATH = FONTS_DIR.parent / "Templates" / "typography_presets.json"
DEFAULT_FONT_FAMILY = "IBM Plex Sans Thai"

# Backward-compat aliases for UI ids
_LEGACY_FONT_ALIASES = {
    "IBMPlex": "IBM Plex Sans Thai",
    "ibm_tech": "IBM Plex Sans Thai",
    "ChakraPetch": "Chakra Petch",
    "Minimal Dark Capsule Pill": "capsule_pill",
}


def _load_font_family_map() -> Dict[str, str]:
    """
    UI font_name -> real embedded font family, built from
    typography_presets.json (each preset's `id` and `font_name`) resolved
    against AssetRegistry's fontTools-verified family names, not guessed
    from a filename.
    """
    family_by_filename = {f["name"]: f["family"] for f in AssetRegistry.fonts()}
    font_map: Dict[str, str] = {}

    try:
        presets = json.loads(TYPOGRAPHY_PRESETS_PATH.read_text(encoding="utf-8"))["presets"]
    except (OSError, json.JSONDecodeError, KeyError):
        presets = []

    for preset in presets:
        family = family_by_filename.get(preset.get("font_file", ""), DEFAULT_FONT_FAMILY)
        font_map[preset["id"]] = family
        font_map[preset["font_name"]] = family

    for family in family_by_filename.values():
        font_map.setdefault(family, family)

    for alias, target in _LEGACY_FONT_ALIASES.items():
        font_map[alias] = font_map.get(target, DEFAULT_FONT_FAMILY)

    return font_map


def _measure_text_width_px(text: str, resolved_font: str, font_size_px: int) -> Optional[int]:
    """
    Real rendered width of `text` at `font_size_px` in the family ASS will
    actually draw it in, via the same physical font files AssetRegistry
    already indexes (family -> path).
    """
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    try:
        family_to_path = {f["family"]: f["path"] for f in AssetRegistry.fonts()}
        font_path = family_to_path.get(resolved_font)
        if not font_path:
            return None
        bbox = ImageFont.truetype(font_path, font_size_px).getbbox(text)
        return int(bbox[2] - bbox[0])
    except Exception:
        return None


_ASS_GLYPH_SCALE_CACHE: Dict[str, float] = {}


def ass_glyph_scale(resolved_font: str) -> float:
    """
    How much smaller libass draws a glyph than its Fontsize number suggests.
    Scale = unitsPerEm / (usWinAscent + usWinDescent)
    """
    if resolved_font in _ASS_GLYPH_SCALE_CACHE:
        return _ASS_GLYPH_SCALE_CACHE[resolved_font]
    scale = 1.0
    try:
        from fontTools.ttLib import TTFont

        path = {f["family"]: f["path"] for f in AssetRegistry.fonts()}.get(resolved_font)
        if path:
            face = TTFont(path, lazy=True)
            upem = face["head"].unitsPerEm
            os2 = face["OS/2"]
            line_box = os2.usWinAscent + os2.usWinDescent
            if upem and line_box:
                scale = upem / line_box
    except Exception:
        scale = 1.0
    _ASS_GLYPH_SCALE_CACHE[resolved_font] = scale
    return scale


def _hook_line_width_px(line: str, resolved_font: str, line_fs: int) -> float:
    """
    Half-width of a hook line in PlayRes pixels.
    """
    measured = _measure_text_width_px(line.replace("\\N", " "), resolved_font, line_fs)
    if measured is None:
        measured = int(len(line) * line_fs * 0.55)
    return max(20, measured) / 2
