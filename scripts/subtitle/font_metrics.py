"""
Font Metrics and Font Family Mapping for Subtitle Engine.
Handles SFNT vertical glyph scaling, PIL-based pixel text measurement,
and font family resolution against AssetRegistry and typography presets.
"""

import json
import re
import struct
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


_FAMILY_FONT_PATH_CACHE: Dict[str, Optional[str]] = {}


def _resolve_family_font_path(resolved_font: str) -> Optional[str]:
    """
    Finds the most suitable font file path for a given font family.
    Prioritizes standard Bold (-Bold.ttf / Bold) to match CSS font-weight 700
    and libass defaults, preventing ExtraBold or Black variants from inflating
    text advance widths.
    """
    if resolved_font in _FAMILY_FONT_PATH_CACHE:
        return _FAMILY_FONT_PATH_CACHE[resolved_font]

    fonts = [f for f in AssetRegistry.fonts() if f.get("family") == resolved_font]
    if not fonts:
        _FAMILY_FONT_PATH_CACHE[resolved_font] = None
        return None

    chosen = None
    for kw in ["-bold.", "bold.", "-semibold.", "semibold.", "-regular.", "regular."]:
        for f in fonts:
            if kw in f.get("name", "").lower():
                chosen = f["path"]
                break
        if chosen:
            break
    if not chosen:
        chosen = fonts[0]["path"]

    _FAMILY_FONT_PATH_CACHE[resolved_font] = chosen
    return chosen


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
        font_path = _resolve_family_font_path(resolved_font)
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
        font_path = _resolve_family_font_path(resolved_font)
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
_ASS_VERTICAL_METRICS_CACHE: Dict[str, Optional[Tuple[int, int, int]]] = {}


def _sfnt_ass_vertical_metrics(path: Path) -> Optional[Tuple[int, int, int]]:
    """Read units-per-em and the Windows ascent/descent from a TTF/OTF.

    This intentionally uses the standard library instead of fontTools because
    these values are part of the render contract and cannot depend on an
    optional package being installed.
    """
    try:
        data = path.read_bytes()
        directory_offset = 0
        if data[:4] == b"ttcf":
            if len(data) < 16:
                return None
            directory_offset = struct.unpack_from(">I", data, 12)[0]
        if directory_offset + 12 > len(data):
            return None

        table_count = struct.unpack_from(">H", data, directory_offset + 4)[0]
        tables: Dict[bytes, Tuple[int, int]] = {}
        records_offset = directory_offset + 12
        for index in range(table_count):
            record_offset = records_offset + index * 16
            if record_offset + 16 > len(data):
                return None
            tag, _, table_offset, table_length = struct.unpack_from(
                ">4sIII", data, record_offset
            )
            if table_offset + table_length > len(data):
                return None
            tables[tag] = (table_offset, table_length)

        head_offset, head_length = tables.get(b"head", (0, 0))
        os2_offset, os2_length = tables.get(b"OS/2", (0, 0))
        if head_length < 20 or os2_length < 78:
            return None

        units_per_em = struct.unpack_from(">H", data, head_offset + 18)[0]
        win_ascent, win_descent = struct.unpack_from(">HH", data, os2_offset + 74)
        line_box = win_ascent + win_descent
        if not units_per_em or not line_box:
            return None
        return units_per_em, win_ascent, win_descent
    except (OSError, KeyError, struct.error, TypeError, ValueError):
        return None


def _sfnt_ass_glyph_scale(path: Path) -> Optional[float]:
    metrics = _sfnt_ass_vertical_metrics(path)
    if metrics is None:
        return None
    units_per_em, win_ascent, win_descent = metrics
    line_box = win_ascent + win_descent
    return units_per_em / line_box


def ass_glyph_scale(resolved_font: str) -> float:
    """
    How much smaller libass draws a glyph than its Fontsize number suggests.
    Scale = unitsPerEm / (usWinAscent + usWinDescent)
    """
    if resolved_font in _ASS_GLYPH_SCALE_CACHE:
        return _ASS_GLYPH_SCALE_CACHE[resolved_font]
    scale = 1.0
    try:
        path = _resolve_family_font_path(resolved_font)
        if path:
            parsed_scale = _sfnt_ass_glyph_scale(Path(path))
            if parsed_scale is not None:
                scale = parsed_scale
    except Exception:
        scale = 1.0
    _ASS_GLYPH_SCALE_CACHE[resolved_font] = scale
    return scale


def ass_top_anchor_offset(resolved_font: str, em_size_px: float) -> int:
    """Return the render-pixel correction for ASS top-aligned overlay text.

    Canvas ``textBaseline='top'`` anchors the em square.  libass Alignment 8
    anchors its taller Windows line box.  The production style boosts ASS
    Fontsize so the glyph em is the requested size; without subtracting the
    extra ascent, a hook drifts downward even when both sides store the same
    normalized ``y`` coordinate.
    """

    try:
        requested = max(0.0, float(em_size_px))
    except (TypeError, ValueError):
        return 0
    if requested <= 0:
        return 0
    if resolved_font not in _ASS_VERTICAL_METRICS_CACHE:
        metrics = None
        try:
            path = _resolve_family_font_path(resolved_font)
            if path:
                metrics = _sfnt_ass_vertical_metrics(Path(path))
        except Exception:
            metrics = None
        _ASS_VERTICAL_METRICS_CACHE[resolved_font] = metrics
    metrics = _ASS_VERTICAL_METRICS_CACHE[resolved_font]
    if metrics is None:
        return 0
    units_per_em, win_ascent, win_descent = metrics
    line_box = win_ascent + win_descent
    if units_per_em <= 0 or line_box <= 0:
        return 0
    boosted = round(requested * line_box / units_per_em)
    extra_line_box = max(0.0, boosted - requested)
    return int(round(extra_line_box * win_ascent / line_box))


_HAS_TRUE_BOLD_CACHE: Dict[str, bool] = {}


def has_true_bold_face(resolved_font: str) -> bool:
    """
    Whether asking libass for `resolved_font` at Bold=1 actually lands on a
    genuinely bold outline, rather than triggering synthetic/faux-bold
    emboldening on the one (non-bold) file AssetRegistry has for this family.
    """
    if resolved_font in _HAS_TRUE_BOLD_CACHE:
        return _HAS_TRUE_BOLD_CACHE[resolved_font]
    result = True
    try:
        from fontTools.ttLib import TTFont

        path = _resolve_family_font_path(resolved_font)
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


THAI_UPPER_VOWELS = "\u0e31\u0e34\u0e35\u0e36\u0e37"
THAI_TONE_MARKS = "\u0e48\u0e49\u0e4a\u0e4b"
THAI_STACKED_MARK_RE = re.compile(
    f"([{re.escape(THAI_UPPER_VOWELS)}])([{re.escape(THAI_TONE_MARKS)}])"
)
# Browser Canvas and libass agree on the body advance, but their ink boxes for
# Thai above marks do not share the same optical top.  Hook/motion overlays
# use this bounded line-level correction so the two rasterizers land on the
# same visual baseline without changing the stored text or font size.
# IBM Plex's ``ึ`` + tone and standalone ``็`` are the combinations whose
# browser/libass ink-top delta exceeds the cross-rasterizer tolerance.  The
# common ``ั``/``ิ`` pairs (for example ``นั่ง``) already match after the
# detached-mark repair and must not receive this line-level shift.
THAI_OVERLAY_MARK_CHARS = "\u0e36\u0e47"
THAI_OVERLAY_MARK_RE = re.compile(f"[{re.escape(THAI_OVERLAY_MARK_CHARS)}]")
THAI_STACKED_MARK_RAISE_EM = 0.13


def thai_overlay_line_offset(text: str, line_fs: float) -> int:
    """Return the render-pixel y correction for a Thai motion line."""

    if not THAI_OVERLAY_MARK_RE.search(str(text or "")):
        return 0
    try:
        size = max(0.0, float(line_fs))
    except (TypeError, ValueError):
        return 0
    return -int(round(size * 0.17))


def repair_thai_stacked_marks(ass_text: str) -> Tuple[str, List[Tuple[str, str, str]]]:
    """Detach tones from Thai upper vowels while preserving full line layout.

    Covers all 20 combinations of ``ัิีึื`` + ``่้๊๋``.  The body keeps the
    upper vowel and removes its tone.  Each companion keeps the complete ASS
    line but removes the target upper vowel and exposes only its tone; callers
    hide the surrounding glyphs and raise the companion event.

    Keeping the full line lets libass measure emoji fallback and mixed-font
    runs itself.  The old Pillow-based absolute x estimate drifted by about
    90 PlayRes pixels when a Segoe UI Emoji glyph preceded the Thai word.
    """
    matches = list(THAI_STACKED_MARK_RE.finditer(ass_text))
    if not matches:
        return ass_text, []

    def without_stacked_tones(value: str) -> str:
        return THAI_STACKED_MARK_RE.sub(r"\1", value)

    repaired = without_stacked_tones(ass_text)
    companions: List[Tuple[str, str, str]] = []
    for target in matches:
        before = without_stacked_tones(ass_text[: target.start()])
        tone = target.group(2)
        after = without_stacked_tones(ass_text[target.end() :])
        companions.append((before, tone, after))
    return repaired, companions


# Compatibility alias for callers introduced with subtitle contract v7.
repair_thai_mark_pair = repair_thai_stacked_marks


def _hook_line_width_px(line: str, resolved_font: str, line_fs: int) -> float:
    """
    Half-width of a hook line in PlayRes pixels.
    """
    measured = _measure_text_width_px(line.replace("\\N", " "), resolved_font, line_fs)
    if measured is None:
        measured = int(len(line) * line_fs * 0.55)
    return max(20, measured) / 2
