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
    # NewClipPanel.jsx's font picker sends this id, which never matched any
    # preset id/font_name/family key below -- it silently fell through to
    # DEFAULT_FONT_FAMILY (IBM Plex), so picking "Noto Sans Thai" in the UI
    # rendered in IBM Plex instead, with no error or indication (found while
    # diagnosing the Kanit/Prompt tone-mark bug, 2026-09-07).
    "NotoSansThai": "Noto Sans Thai",
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
    Real rendered advance width of `text` at `font_size_px` in the family ASS will
    actually draw it in, via the same physical font files AssetRegistry
    already indexes (family -> path).
    Uses font.getlength() (advance width including sidebearings) rather than getbbox() (ink bbox).
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
        font = ImageFont.truetype(font_path, font_size_px)
        return int(round(font.getlength(text)))
    except Exception:
        return None


def prefix_advances(text_tokens: List[str], resolved_font: str, font_size_px: int) -> Optional[List[float]]:
    """
    Cumulative advance width at each token boundary for `text_tokens`.
    Returns [0.0, adv_1, adv_2, ..., adv_total] measured via real font advances.
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
        font = ImageFont.truetype(font_path, font_size_px)
        advances = [0.0]
        cumulative = ""
        for token in text_tokens:
            cumulative += token
            advances.append(float(font.getlength(cumulative)))
        return advances
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


_HAS_TRUE_BOLD_CACHE: Dict[str, bool] = {}


def has_true_bold_face(resolved_font: str) -> bool:
    """
    Whether asking libass for `resolved_font` at Bold=1 actually lands on a
    genuinely bold outline, rather than triggering synthetic/faux-bold
    emboldening on the one (non-bold) file AssetRegistry has for this family.

    Found while diagnosing the "นั่ง" tone-mark collapse bug (2026-09-08):
    every ASS style this engine writes hardcodes Bold=1 on the assumption
    that libass/DirectWrite will resolve it to that family's real bold
    weight (see the comment above resolved_font's assignment in
    subtitle_engine.py). That holds for e.g. IBM Plex Sans Thai, which has
    a separate face whose macStyle bold bit is genuinely set -- but
    02_Assets/Fonts/NotoSansThai-SemiBold.ttf is internally mislabeled as
    Regular/weight-400 in its own name table despite the filename, so a
    Bold=1 request against "Noto Sans Thai" has no real bold face to land
    on. DirectWrite/libass silently substitutes the same Regular-labeled
    file anyway and applies synthetic bold to it -- which breaks GPOS
    mark-to-mark anchor deltas that ั+่ (and only that specific stacked
    pair, empirically) depends on. Detecting "no genuine bold face" from
    the registered file's own OS/2 table lets style generation skip Bold=1
    for exactly the families where it would only do damage.
    """
    if resolved_font in _HAS_TRUE_BOLD_CACHE:
        return _HAS_TRUE_BOLD_CACHE[resolved_font]
    result = True  # fail open -- assume a real bold face exists rather than
    # silently thinning out a caption style, matching every other lookup
    # miss/exception default in this module.
    try:
        from fontTools.ttLib import TTFont

        path = {f["family"]: f["path"] for f in AssetRegistry.fonts()}.get(resolved_font)
        if path:
            face = TTFont(path, lazy=True)
            os2 = face["OS/2"]
            name_table = face["name"]
            subfamily = (name_table.getDebugName(17) or name_table.getDebugName(2) or "").lower()
            fs_selection_bold = bool(os2.fsSelection & 0x20)
            mac_style_bold = bool(face["head"].macStyle & 0x1)
            weight_bold = int(getattr(os2, "usWeightClass", 400) or 400) >= 600
            name_says_bold = "bold" in subfamily
            result = fs_selection_bold or mac_style_bold or weight_bold or name_says_bold
    except Exception:
        result = True
    _HAS_TRUE_BOLD_CACHE[resolved_font] = result
    return result


def _hook_line_width_px(line: str, resolved_font: str, line_fs: int) -> float:
    """
    Half-width of a hook line in PlayRes pixels.
    """
    measured = _measure_text_width_px(line.replace("\\N", " "), resolved_font, line_fs)
    if measured is None:
        measured = int(len(line) * line_fs * 0.55)
    return max(20, measured) / 2
