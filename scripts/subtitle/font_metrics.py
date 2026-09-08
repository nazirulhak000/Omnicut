"""
Font Metrics and Font Family Mapping for Subtitle Engine.
Handles fontTools-based vertical glyph scaling, PIL-based pixel text measurement,
and font family resolution against AssetRegistry and typography presets.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.config import FONTS_DIR
from scripts.asset_registry import AssetRegistry

TYPOGRAPHY_PRESETS_PATH = FONTS_DIR.parent / "Templates" / "typography_presets.json"
DEFAULT_FONT_FAMILY = "IBM Plex Sans Thai"

# A family name is not enough to select a stable Thai face when several cuts
# share the same typographic family.  In particular, asking libass for
# `IBM Plex Sans Thai` + Bold=1 selects the Bold face, while the browser's
# caption contract uses the loaded 600 cut.  The Bold cut and the SemiBold cut
# have subtly different mark anchors; the former is the one that makes the
# `ั` + `่` pair in `นั่ง` look fused after the ASS scale conversion.  Keep the
# family for metrics, but pin the caption renderer to the same physical cut as
# Canvas.  This is intentionally caption-only; overlay looks still resolve
# their own requested weight.
_ASS_CAPTION_FACE_OVERRIDES: Dict[str, Tuple[str, int]] = {
    "IBM Plex Sans Thai": ("IBM Plex Sans Thai SemiBold", 0),
}

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


def ass_caption_face(resolved_font: str) -> Tuple[str, int]:
    """Return the explicit ASS face and Bold flag used by body captions.

    ASS font matching is family based, so a family containing multiple Thai
    weights can silently choose a different cut from Canvas.  Returning the
    face and the flag together makes the renderer contract explicit and keeps
    callers from reintroducing synthetic bold on the affected family.
    """
    return _ASS_CAPTION_FACE_OVERRIDES.get(
        resolved_font,
        (resolved_font, 1 if has_true_bold_face(resolved_font) else 0),
    )


def repair_thai_mark_pair(
    ass_text: str,
    resolved_font: str,
    font_size_px: int,
    video_width: int,
    line_anchor_ys: List[float],
    line_center_x: Optional[float] = None,
) -> Tuple[str, List[Tuple[int, int]]]:
    """Remove the fused mai han-akat/tone pair and return tone placements.

    The IBM Plex Thai face currently bundled with the app rasterises
    ``ั่`` in one shared vertical band under libass, even when its real
    SemiBold face and GPOS tables are selected.  ASS has no per-glyph y
    offset, so the stable workaround is to leave ``ั`` in the normal run and
    draw ``่`` as a zero-advance companion event at the same base x, raised by
    a font-relative amount.  The returned coordinates are PlayRes pixels;
    callers can reuse the same style and animation tags for the companion.

    Only the raw adjacent pair is changed.  ASS override blocks and line
    breaks remain untouched, and text without the pair is returned byte-for-
    byte unchanged.
    """
    pair = "\u0e31\u0e48"
    if pair not in ass_text:
        return ass_text, []

    def visible(value: str) -> str:
        return re.sub(r"\{[^{}]*\}", "", value)

    def width(value: str) -> float:
        if not value:
            return 0.0
        measured = _measure_text_width_px(value, resolved_font, font_size_px)
        if measured is not None:
            # Pillow measures the font in its em square, while libass sizes
            # the same face from the OS/2 win ascent+descent line box.  The
            # scale difference is especially visible here: without it the
            # companion tone is placed as if the Thai line were ~1.65x wider
            # than the pixels libass actually draws.
            return float(measured) * ass_glyph_scale(resolved_font)
        return float(len(value) * font_size_px * 0.55) * ass_glyph_scale(resolved_font)

    repaired_lines: List[str] = []
    tone_positions: List[Tuple[int, int]] = []
    for line_idx, segment in enumerate(ass_text.split(r"\N")):
        raw_indices = [match.start() for match in re.finditer(pair, segment)]
        if not raw_indices:
            repaired_lines.append(segment)
            continue

        plain_line = visible(segment)
        line_width = width(plain_line)
        line_center = video_width / 2.0 if line_center_x is None else line_center_x
        line_left = line_center - line_width / 2.0
        for raw_idx in raw_indices:
            plain_before = visible(segment[:raw_idx])
            if not plain_before:
                continue
            base = plain_before[-1]
            prefix = plain_before[:-1]
            # Thai's mark-to-base anchor for this face is at the far side of
            # the base advance, not at its visual midpoint.  Using half the
            # advance leaves the detached tone just left of the consonant
            # (and is particularly obvious after a long centred line).
            base_x = line_left + width(prefix) + width(base)
            anchor_y = line_anchor_ys[min(line_idx, len(line_anchor_ys) - 1)]
            # The detached ASS tone glyph's ink sits ~0.33em above its
            # `\an5` anchor.  Raising the anchor by 0.13em leaves a small
            # optical gap above mai han-akat; 0.23em made it float too far
            # above bilingual captions.
            tone_raise = max(6, int(round(font_size_px * 0.13)))
            tone_positions.append((int(round(base_x)), int(round(anchor_y - tone_raise))))

        repaired = segment
        for raw_idx in reversed(raw_indices):
            repaired = repaired[: raw_idx + 1] + repaired[raw_idx + 2 :]
        repaired_lines.append(repaired)

    return r"\N".join(repaired_lines), tone_positions


def _hook_line_width_px(line: str, resolved_font: str, line_fs: int) -> float:
    """
    Half-width of a hook line in PlayRes pixels.
    """
    measured = _measure_text_width_px(line.replace("\\N", " "), resolved_font, line_fs)
    if measured is None:
        measured = int(len(line) * line_fs * 0.55)
    return max(20, measured) / 2
