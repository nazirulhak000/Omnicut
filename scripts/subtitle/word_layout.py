"""
Word Layout Engine for Subtitles and Overlays.
Computes per-word static layout positioning (x, y, w) in normalized coordinates (0.0 to 1.0)
ensuring 100% pixel parity between libass ASS Dialogue events and Canvas 2D preview.
"""

import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from PIL import ImageFont
from pythainlp.tokenize import word_tokenize

from scripts.asset_registry import AssetRegistry
from scripts.subtitle.font_metrics import (
    DEFAULT_FONT_FAMILY,
    _load_font_family_map,
    ass_glyph_scale,
)

# Thai combining marks: vowels and tone marks (U+0E31, U+0E34-U+0E3A, U+0E47-U+0E4E)
THAI_COMBINING_RANGE = (
    set(range(0x0E31, 0x0E32))
    | set(range(0x0E34, 0x0E3B))
    | set(range(0x0E47, 0x0E4F))
)


def is_combining_char(ch: str) -> bool:
    """Returns True if the character is a non-spacing combining mark."""
    if not ch:
        return False
    return unicodedata.combining(ch) != 0 or ord(ch) in THAI_COMBINING_RANGE


def tokenize_text(text: str) -> List[str]:
    """
    Tokenizes text into words and whitespace segments.
    Uses pythainlp newmm for Thai and whitespace for Latin/numbers.
    Guarantees combining marks are never detached into standalone tokens.
    """
    if not text:
        return []

    clean = str(text).replace("\r", "")
    raw_tokens = word_tokenize(clean, engine="newmm")

    # Pass 1: Attach orphan combining marks to previous token
    sanitized: List[str] = []
    for tok in raw_tokens:
        if not tok:
            continue
        if sanitized and is_combining_char(tok[0]):
            sanitized[-1] += tok
        else:
            sanitized.append(tok)

    # Pass 2: Group consecutive whitespace tokens
    grouped: List[str] = []
    for tok in sanitized:
        if tok.isspace():
            if grouped and grouped[-1].isspace():
                grouped[-1] += tok
            else:
                grouped.append(tok)
        else:
            grouped.append(tok)

    return grouped


def get_scaled_font(font_name: str, font_size_px: float) -> Tuple[Optional[ImageFont.FreeTypeFont], float]:
    """
    Resolves the physical font file from AssetRegistry and scales the point size
    by ass_glyph_scale() to match libass's line-box scaling behavior.
    """
    font_map = _load_font_family_map()
    resolved_font = font_map.get(font_name, font_name)
    family_to_path = {f["family"]: f["path"] for f in AssetRegistry.fonts()}
    path = family_to_path.get(resolved_font)
    if not path:
        resolved_font = DEFAULT_FONT_FAMILY
        path = family_to_path.get(resolved_font)
    if not path:
        return None, 1.0

    scale = ass_glyph_scale(resolved_font)
    scaled_fs = max(1.0, float(font_size_px) * scale)
    try:
        font = ImageFont.truetype(path, scaled_fs)
        return font, scale
    except Exception:
        return None, scale


def layout_line(
    text: str,
    font_name: str,
    font_size_px: float,
    norm_x: float = 0.5,
    video_w: int = 1080,
) -> Dict[str, Any]:
    """
    Computes per-word static positions for a single line of text.
    Returns words with normalized (0..1) and absolute PlayRes coordinates.
    """
    clean_text = str(text).strip()
    if not clean_text:
        return {
            "text": "",
            "line_width": 0.0,
            "abs_line_width": 0.0,
            "words": [],
        }

    tokens = tokenize_text(clean_text)
    font, scale = get_scaled_font(font_name, font_size_px)

    if font is None:
        # Fallback approximation if font loading fails
        est_char_w = font_size_px * 0.55
        words = []
        cur_x = 0.0
        for tok in tokens:
            w_px = len(tok) * est_char_w
            if not tok.isspace():
                words.append({
                    "text": tok,
                    "x": (cur_x) / video_w,
                    "w": w_px / video_w,
                    "abs_x": cur_x,
                    "abs_w": w_px,
                })
            cur_x += w_px
        total_w = cur_x
        x_start = (video_w * norm_x) - (total_w / 2.0)
        for w in words:
            w["abs_x"] += x_start
            w["x"] = w["abs_x"] / video_w
        return {
            "text": clean_text,
            "line_width": total_w / video_w,
            "abs_line_width": total_w,
            "words": words,
        }

    # Cumulative advances at every token boundary
    advances = [0.0]
    cumulative = ""
    for tok in tokens:
        cumulative += tok
        advances.append(float(font.getlength(cumulative)))

    # Find non-whitespace tokens
    non_space_indices = [i for i, tok in enumerate(tokens) if not tok.isspace()]
    if not non_space_indices:
        return {
            "text": clean_text,
            "line_width": 0.0,
            "abs_line_width": 0.0,
            "words": [],
        }

    first_idx = non_space_indices[0]
    last_idx = non_space_indices[-1]

    # Content width spans from start of first word to end of last word
    content_start_adv = advances[first_idx]
    content_end_adv = advances[last_idx + 1]
    content_width = max(1.0, content_end_adv - content_start_adv)

    x_center = float(video_w) * float(norm_x)
    base_x = (x_center - content_width / 2.0) - content_start_adv

    words = []
    for i in non_space_indices:
        tok = tokens[i]
        abs_x = base_x + advances[i]
        abs_w = max(1.0, advances[i + 1] - advances[i])
        words.append({
            "text": tok,
            "x": abs_x / float(video_w),
            "w": abs_w / float(video_w),
            "abs_x": abs_x,
            "abs_w": abs_w,
        })

    return {
        "text": clean_text,
        "line_width": content_width / float(video_w),
        "abs_line_width": content_width,
        "words": words,
    }


@lru_cache(maxsize=256)
def _layout_overlay_cached(
    text: str,
    font_name: str,
    font_size_px: float,
    norm_x: float = 0.5,
    norm_y: float = 0.5,
    video_w: int = 1080,
    video_h: int = 1920,
) -> Dict[str, Any]:
    """Cached implementation of overlay layout."""
    raw_lines = str(text).replace("\\N", "\n").split("\n")
    clean_lines = [l.strip() for l in raw_lines if l.strip()]

    if not clean_lines:
        return {
            "lines": [],
            "total_lines": 0,
            "max_line_width": 0.0,
        }

    lines_layout = []
    max_line_w = 0.0

    for idx, line_str in enumerate(clean_lines):
        line_data = layout_line(
            text=line_str,
            font_name=font_name,
            font_size_px=font_size_px,
            norm_x=norm_x,
            video_w=video_w,
        )
        line_data["line_idx"] = idx
        lines_layout.append(line_data)
        if line_data["line_width"] > max_line_w:
            max_line_w = line_data["line_width"]

    return {
        "lines": lines_layout,
        "total_lines": len(lines_layout),
        "max_line_width": max_line_w,
    }


def layout_overlay(
    text: str,
    font_name: str,
    font_size_px: float,
    norm_x: float = 0.5,
    norm_y: float = 0.5,
    video_w: int = 1080,
    video_h: int = 1920,
) -> Dict[str, Any]:
    """
    Public facade for computing static per-word overlay layout.
    """
    return _layout_overlay_cached(
        text=str(text or ""),
        font_name=str(font_name or "Kanit"),
        font_size_px=float(font_size_px or 75.0),
        norm_x=float(norm_x if norm_x is not None else 0.5),
        norm_y=float(norm_y if norm_y is not None else 0.5),
        video_w=int(video_w or 1080),
        video_h=int(video_h or 1920),
    )
