"""
The hook line: one line of text on screen from the very first frame.

The first thing a viewer used to see was the 3-tier brand / model / label
nameplate, held for 5 seconds. The AI-written hook (`hook_title`) never reached
the screen at all, so the first 2 seconds -- where the swipe decision is made --
carried a product name rather than a reason to stay (M1 of
PLAN_AI_EDITOR_VIRAL_STYLES_20261031, approved by the project owner).

This module adds the missing layer: a single line, 0.0-1.8 s, in the active hook
template's own look, after which the nameplate takes over (1.8 s, 3.0 s long).

It is deliberately an ordinary `kind: "text"` overlay. The ASS writer
(`scripts/subtitle/overlay_events.py`) and the canvas preview
(`SequencePlayer.jsx` via `overlayModel.js`) already draw those from the same
fields, and the manifest persists them, so preview and render agree without a
second code path. Everything here is pure: it takes script data and the overlay
list and returns a new overlay list.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.compliance_lint import lint_opening_line, lint_text, strip_ellipsis, strip_emoji
from scripts.overlay_model import (
    ACCENT_COLOR,
    ANCHOR_MIDDLE,
    DEFAULT_ANIM,
    HOOK_FS_RATIO,
    TEXT_FS_RATIO,
    TEXT_LAYER,
    hook_overlay_from_legacy,
    resolve_look,
)

# The hook line owns the first 1.8 s; the nameplate starts where it ends.
HOOK_LINE_END_SEC = 1.8
# One line, no more characters than this -- long enough for a Thai clause,
# short enough to stay legible at a size a thumb-stopping line needs.
HOOK_LINE_MAX_CHARS = 22
HOOK_LINE_MIN_CHARS = 4
# Never shrink below this share of the template's own largest tier. A line that
# only fits at less is skipped rather than rendered small.
HOOK_LINE_MIN_SIZE_SHARE = 0.70
# Widest the line may be, in render pixels, at 1080 wide. The entrance pop
# starts 25% larger than rest, and that overshoot has to stay inside the frame
# too: 860 * 1.25 = 1075. At rest the margins are (1080 - 860) / 2 = 110 px.
HOOK_LINE_MAX_WIDTH_PX = 860
# Vertical centre as a fraction of frame height: where the nameplate's first
# tier sits (180 px top anchor + half a line), so the nameplate replaces the
# hook line in the same band. 225 px is also well below the TikTok status bar.
HOOK_LINE_CENTER_Y = 225.0 / 1920.0

HOOK_LINE_ROLE = "hook_line"
HOOK_LINE_ID = "ovl_hook_line"
# 70 ms pop that is already on screen at frame 0 (alpha never starts at 0);
# `out: none` so the line cuts straight to the nameplate instead of fading
# through an empty frame.
HOOK_LINE_ANIM: Dict[str, Any] = {**DEFAULT_ANIM, "in": "snap", "loop": "none", "out": "none"}

# A clause that ends on one of these is unfinished ("ถ้าคุณปวดข้อมือที่"), so it
# is trimmed back to the last whole phrase. Exact word matches only, taken from
# the Thai tokenizer, never a suffix test on the raw string.
_DANGLING_WORDS = frozenset({
    "และ", "หรือ", "แต่", "ที่", "ซึ่ง", "ว่า", "เพราะ", "ถ้า", "เมื่อ",
    "กับ", "ของ", "ใน", "จน", "คือ", "ก็", "จะ", "แล้ว", "โดย", "เพื่อ",
})
_KEEP_TRAILING_PUNCT = "!?"
_TRAILING_JUNK = " ,;:-–—\"'“”‘’()[]{}"
_HOOK_LINE_TEXT_KEYS = ("hook_title", "hook")


def _clean(text: Any) -> str:
    """Whitespace-collapsed, emoji- and ellipsis-free single line."""
    if not text:
        return ""
    cleaned = strip_emoji(strip_ellipsis(str(text).replace("\r", "\n")))
    return re.sub(r"\s+", " ", cleaned).strip()


def _tokens(text: str) -> List[str]:
    try:
        from pythainlp.tokenize import word_tokenize
        return [w for w in word_tokenize(text, engine="newmm") if w]
    except Exception:
        return []


def _tidy_tail(text: str) -> str:
    """Drop trailing junk and dangling connectives; keep one '!' or '?'."""
    out = text.strip()
    for _ in range(4):
        out = out.rstrip(_TRAILING_JUNK)
        # Collapse "!!" / "?!" runs to the first mark.
        while len(out) >= 2 and out[-1] in _KEEP_TRAILING_PUNCT and out[-2] in _KEEP_TRAILING_PUNCT:
            out = out[:-1]
        body = out.rstrip(_KEEP_TRAILING_PUNCT)
        mark = out[len(body):]
        if mark:
            # A connective before the mark is just as unfinished.
            words = _tokens(body)
        else:
            words = _tokens(out)
        if len(words) >= 2 and words[-1] in _DANGLING_WORDS:
            trimmed = (body if mark else out)[: -len(words[-1])].rstrip(_TRAILING_JUNK)
            if len(trimmed) >= HOOK_LINE_MIN_CHARS + 2:
                out = trimmed + mark
                continue
        break
    return out.strip()


def _first_fitting_phrase(text: str, max_chars: int) -> str:
    """
    `text` itself when it fits, otherwise its first Thai-safe phrase that does.

    The phrase comes from the same clause splitter the subtitles use, which
    breaks only at PyThaiNLP word boundaries, so no syllable, vowel or tone
    mark is ever separated. Returns "" when nothing fits.
    """
    if len(text) <= max_chars:
        return _tidy_tail(text)
    from scripts.subtitle_engine import SubtitleEngine

    for clause in SubtitleEngine.split_into_smart_clauses(text, max_line_len=max_chars):
        phrase = _tidy_tail(_clean(clause))
        if HOOK_LINE_MIN_CHARS <= len(phrase) <= max_chars:
            return phrase
        # Only the first clause may stand in for the hook: a later one is not
        # what the writer led with.
        break
    return ""


def _source_text(script_data: Optional[Mapping[str, Any]]) -> str:
    """The hook line's source: hook_title, else hook, else the first spoken line."""
    data = script_data or {}
    for key in _HOOK_LINE_TEXT_KEYS:
        value = _clean(data.get(key))
        if value:
            return value
    lines = data.get("lines")
    if isinstance(lines, Sequence) and not isinstance(lines, (str, bytes)):
        for line in lines:
            raw = line.get("text") if isinstance(line, Mapping) else line
            value = _clean(raw)
            if value:
                return value
    return ""


def choose_hook_line(
    script_data: Optional[Mapping[str, Any]],
    max_chars: int = HOOK_LINE_MAX_CHARS,
) -> Optional[str]:
    """
    The one line to show at 0-1.8 s, or None to skip the layer.

    None when there is no source text, nothing fits `max_chars` on one line,
    or the compliance lint (price, exaggerated claim, filler opener, CTA) hits
    -- the layer is a convenience, never worth a compliance risk.
    """
    source = _source_text(script_data)
    if not source:
        return None
    text = _first_fitting_phrase(source, max_chars)
    if not text or len(text) > max_chars or len(text) < HOOK_LINE_MIN_CHARS:
        return None
    if "..." in text or "…" in text:
        return None
    if lint_text(text, field="hook_line") or lint_opening_line(text, field="hook_line"):
        return None
    return text


def _largest_tier_look(hook_overlay: Mapping[str, Any]) -> Tuple[Dict[str, Any], float]:
    """
    The look of the template's largest tier, and its size in render pixels at
    1080 wide (the tier's own size_pct against the banner's base size).
    """
    master = resolve_look(hook_overlay.get("look"), None)
    master_scale = max(0.2, min(3.0, float(master.get("size_pct", 100)) / 100.0))
    best_look: Optional[Dict[str, Any]] = None
    best_pct = -1.0
    for tier in hook_overlay.get("tiers") or []:
        look = resolve_look(hook_overlay.get("look"), (tier or {}).get("look"))
        pct = float(look.get("size_pct") or 0) * master_scale
        if pct > best_pct:
            best_look, best_pct = look, pct
    if best_look is None:
        best_look, best_pct = master, float(master.get("size_pct", 100)) * master_scale
    base_px = round(1080 * float(hook_overlay.get("base_fs_ratio") or HOOK_FS_RATIO))
    return best_look, base_px * best_pct / 100.0


def _writer_family(font: Optional[str]) -> str:
    """
    The family the ASS writer will actually draw `font` in: the editor's id
    mapped to a family, then the caption font when that family is not
    installed -- the same two steps `_text_overlay_events` takes.
    """
    from scripts.asset_registry import AssetRegistry
    from scripts.subtitle.font_metrics import _load_font_family_map
    from scripts.subtitle import DEFAULT_FONT_FAMILY

    name = font or DEFAULT_FONT_FAMILY
    family = _load_font_family_map().get(name, name)
    if family not in {f["family"] for f in AssetRegistry.fonts()}:
        return DEFAULT_FONT_FAMILY
    return family


def _fit_size_pct(text: str, look: Mapping[str, Any], tier_px: float) -> Optional[int]:
    """
    A `size_pct` (against the text overlay's own 50 px base) that puts `text`
    on one line no wider than HOOK_LINE_MAX_WIDTH_PX, outline included, never
    below HOOK_LINE_MIN_SIZE_SHARE of the template's own size. None when it
    cannot fit even at the floor.
    """
    from scripts.subtitle.font_metrics import _measure_text_width_px as measure_text_width_px

    text_base_px = round(1080 * TEXT_FS_RATIO)
    family = _writer_family(look.get("font"))
    outline = 2.0 * float(look.get("outline_px") or 0.0)
    size_px = float(tier_px)
    floor_px = size_px * HOOK_LINE_MIN_SIZE_SHARE
    while True:
        render_px = max(16, int(round(size_px)))
        width = measure_text_width_px(text, family, render_px)
        if width is None:
            # No metrics for this face -- fall back to a conservative advance.
            width = int(len(text) * render_px * 0.62)
        if width + outline <= HOOK_LINE_MAX_WIDTH_PX:
            break
        if size_px <= floor_px:
            return None
        size_px = max(floor_px, size_px - 2.0)
    pct = int(round(size_px / text_base_px * 100.0))
    return max(40, min(250, pct))


def build_hook_line_overlay(
    text: str,
    hook_overlay: Mapping[str, Any],
    end: float = HOOK_LINE_END_SEC,
) -> Optional[Dict[str, Any]]:
    """The text overlay for `text`, dressed in `hook_overlay`'s largest tier."""
    look, tier_px = _largest_tier_look(hook_overlay)
    size_pct = _fit_size_pct(text, look, tier_px)
    if size_pct is None:
        return None
    return {
        "id": HOOK_LINE_ID,
        "kind": "text",
        "role": HOOK_LINE_ROLE,
        # Draw the line as one run, not word by word: see _text_overlay_events.
        "layout_mode": "line",
        "template": None,
        "start": 0.0,
        "end": round(float(end), 3),
        "position": "top",
        "anchor": ANCHOR_MIDDLE,
        "comfortable_lines": None,
        "layer": TEXT_LAYER,
        "x": 0.5,
        "y": round(HOOK_LINE_CENTER_Y, 5),
        "base_fs_ratio": TEXT_FS_RATIO,
        "look": {
            "font": look.get("font"),
            "size_pct": size_pct,
            "color": look.get("color"),
            "outline_color": look.get("outline_color"),
            "outline_px": float(look.get("outline_px") or 0.0),
            "shadow": copy.deepcopy(look.get("shadow")),
            "pill": copy.deepcopy(look.get("pill")),
            # Authored text, never case-folded: a Latin model name in the hook
            # keeps the capitals the writer gave it.
            "upper": False,
        },
        "tiers": [{"text": text, "look": {}}],
        "anim": dict(HOOK_LINE_ANIM),
        "scrim": True,
        "sfx": None,
        "sfx_label": None,
        "template_id": None,
        "hidden": False,
    }


def _has_hook_line(overlays: Sequence[Mapping[str, Any]]) -> bool:
    return any(isinstance(o, Mapping) and o.get("role") == HOOK_LINE_ROLE for o in overlays)


def apply_hook_line(
    overlays: Sequence[Mapping[str, Any]],
    script_data: Optional[Mapping[str, Any]],
    *,
    total_duration: Optional[float] = None,
    style: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    `overlays` with the hook line added and the nameplate moved behind it.

    Returned unchanged (as copies) when a hook line is already present -- a
    re-render of a saved project must not stack a second one -- when no line
    qualifies, or when the clip is too short to hold the line and the
    nameplate after it. `style` is the look to borrow when the project has no
    nameplate to borrow it from: `{template, style_preset, ad_tone, motion,
    colors, style}` as the stage resolves them.
    """
    out = [copy.deepcopy(dict(o)) for o in (overlays or []) if isinstance(o, Mapping)]
    if _has_hook_line(out):
        return out
    try:
        clip_len = float(total_duration) if total_duration is not None else None
    except (TypeError, ValueError):
        clip_len = None
    if clip_len is not None and clip_len < HOOK_LINE_END_SEC + 1.0:
        return out

    text = choose_hook_line(script_data)
    if not text:
        return out

    hook = next((o for o in out if o.get("kind") == "hook" and not o.get("hidden")), None)
    look_source: Optional[Mapping[str, Any]] = hook
    if look_source is None:
        opts = style or {}
        look_source = hook_overlay_from_legacy(
            "-", "", "", HOOK_LINE_END_SEC,
            opts.get("motion"), opts.get("colors"), opts.get("style"),
            style_preset=opts.get("style_preset"), ad_tone=opts.get("ad_tone"),
        )
    if not look_source:
        return out

    line = build_hook_line_overlay(text, look_source, end=HOOK_LINE_END_SEC)
    if line is None:
        return out

    if hook is not None and float(hook.get("start") or 0.0) < HOOK_LINE_END_SEC:
        # The nameplate keeps the length it was given, now measured from where
        # the hook line ends. One a user already placed at or after 1.8 s has
        # nothing to make room for and is left where it is.
        length = max(0.1, float(hook.get("end") or 0.0) - float(hook.get("start") or 0.0))
        hook["start"] = HOOK_LINE_END_SEC
        end = HOOK_LINE_END_SEC + length
        if clip_len is not None:
            end = min(end, clip_len)
        hook["end"] = round(end, 3)

    insert_at = 1 if out and out[0].get("kind") == "hook" else 0
    out.insert(insert_at, line)
    return out


def merge_adjacent_spans(
    spans: Sequence[Tuple[float, float]], gap: float = 0.05,
) -> List[Tuple[float, float]]:
    """
    Scrim spans with touching or overlapping neighbours joined.

    The render lays one gradient per span and each fades out over 0.3 s past its
    end, so the hook line's wash (ending 1.8 s) and the nameplate's (starting
    1.8 s) would stack into a darker band for 0.3 s at the hand-off. One span
    gives one wash.
    """
    ordered = sorted((float(a), float(b)) for a, b in spans if float(b) > float(a))
    merged: List[Tuple[float, float]] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1] + gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
