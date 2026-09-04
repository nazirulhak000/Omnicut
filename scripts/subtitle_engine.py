"""
TikTok Style Subtitle Generator (Advanced SubStation Alpha .ass)
Produces rapid-fire 2-3 word micro-burst subtitles with Kanit-Black font, emojis, and pop animation.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import FONTS_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from scripts.asset_registry import AssetRegistry

TYPOGRAPHY_PRESETS_PATH = FONTS_DIR.parent / "Templates" / "typography_presets.json"
DEFAULT_FONT_FAMILY = "IBM Plex Sans Thai"

# Backward-compat aliases for UI ids that don't match a typography_presets.json
# entry's own font_name/id (old space-free spellings, and capsule_pill's
# display name). Anything not found here or in the presets file falls back
# to DEFAULT_FONT_FAMILY, so an unrecognized font_name never errors.
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

    Every ASS style here already sets Bold=1, so libass/fontconfig picks the
    bold weight of whichever family this resolves to -- naming the family is
    enough, the style doesn't need a specific weight-suffixed name.
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

    # Every real family on disk maps to itself, not just the 5 that have a
    # typography_presets.json entry -- so a font_name picker built straight
    # off AssetRegistry.fonts() (e.g. "Tahoma", "Noto Sans Thai") works too,
    # not only the curated preset ids.
    for family in family_by_filename.values():
        font_map.setdefault(family, family)

    for alias, target in _LEGACY_FONT_ALIASES.items():
        font_map[alias] = font_map.get(target, DEFAULT_FONT_FAMILY)

    return font_map


# Full CapCut-style motion preset system: one choice per category (In /
# Loop / Out), each independently swappable, plus a separate Accent shape --
# not tied to In/Loop/Out at all. Replaces the earlier 4-boolean-toggle
# version (bounce/stagger/pulse/underline); an old-shaped saved dict simply
# won't match any of these keys and silently falls back to the default
# preset below, so no migration code is needed.
DEFAULT_HOOK_MOTION = {"in": "bounce", "stagger": True, "loop": "pulse", "out": "fade", "accent": "underline"}


def _resolve_hook_motion(hook_motion: Optional[Dict[str, object]]) -> Dict[str, object]:
    resolved = dict(DEFAULT_HOOK_MOTION)
    if hook_motion:
        for k in DEFAULT_HOOK_MOTION:
            v = hook_motion.get(k)
            if v is not None:
                resolved[k] = v
    resolved["stagger"] = bool(resolved["stagger"])
    return resolved


def _chained_keyframes(prop: str, start_ms: int, end_ms: int, seg_ms: int, values: List[str]) -> str:
    """
    Generic cycling \\t chain animating a single ASS property (e.g. "alpha"
    or "frz") through `values` in order, `seg_ms` per step, from start_ms
    until end_ms -- the shared engine behind pulse/wave/shake/flicker.
    Emits nothing if not even one step fits, rather than a single
    stub keyframe that would read as a glitch instead of a loop.
    """
    segs = []
    t = start_ms
    i = 0
    while t + seg_ms <= end_ms:
        segs.append(f"\\t({t},{t + seg_ms},\\{prop}{values[i % len(values)]})")
        t += seg_ms
        i += 1
    return "".join(segs)


# ---- In (entrance) builders -------------------------------------------
# Each takes (target_scale_pct, t0_ms) and returns (tag_fragment,
# entry_end_ms, move_dy_px). move_dy_px is None for every preset except
# slide_up, where it tells the per-line assembler to use \move instead of
# a static \pos (see the "why not \move for wave/shake" note further down
# -- ASS \move is a single linear segment, so only true one-shot slides can
# use it; looping motion uses \frz rotation via _chained_keyframes instead).

def _in_bounce(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Elastic overshoot/undershoot/settle via \\fscx/\\fscy, ~450ms."""
    target = round(target_scale_pct)
    over = round(target * 1.25)
    under = round(target * 0.92)
    settle_over = round(target * 1.05)
    t1, t2, t3, t4 = t0_ms, t0_ms + 150, t0_ms + 280, t0_ms + 380
    end_ms = t0_ms + 450
    entry_from = round(target * 0.6)
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}"
        f"\\t({t1},{t2},\\fscx{over}\\fscy{over})"
        f"\\t({t2},{t3},\\fscx{under}\\fscy{under})"
        f"\\t({t3},{t4},\\fscx{settle_over}\\fscy{settle_over})"
        f"\\t({t4},{end_ms},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_pop(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    """Snappier one-bounce version of bounce -- single overshoot, ~200ms."""
    target = round(target_scale_pct)
    over = round(target * 1.18)
    entry_from = round(target * 0.55)
    end_ms = t0_ms + 200
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}"
        f"\\t({t0_ms},{t0_ms + 120},\\fscx{over}\\fscy{over})"
        f"\\t({t0_ms + 120},{end_ms},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_fade(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 250
    tag = f"\\fscx{target}\\fscy{target}\\alpha&HFF&\\t({t0_ms},{end_ms},\\alpha&H00&)"
    return tag, end_ms, None


def _in_zoom(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    entry_from = round(target * 1.8)
    end_ms = t0_ms + 300
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}\\alpha&HFF&"
        f"\\t({t0_ms},{t0_ms + 150},\\alpha&H00&)"
        f"\\t({t0_ms},{end_ms},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms, None


def _in_slide_up(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 300
    tag = f"\\fscx{target}\\fscy{target}\\alpha&HFF&\\t({t0_ms},{end_ms},\\alpha&H00&)"
    return tag, end_ms, 60  # slides up from 60px below its final position


def _in_blur(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    end_ms = t0_ms + 350
    tag = (
        f"\\fscx{target}\\fscy{target}\\alpha&HFF&\\blur12"
        f"\\t({t0_ms},{end_ms},\\alpha&H00&\\blur0)"
    )
    return tag, end_ms, None


def _in_none(target_scale_pct: float, t0_ms: int) -> Tuple[str, int, Optional[int]]:
    target = round(target_scale_pct)
    return f"\\fscx{target}\\fscy{target}", t0_ms, None


# typewriter is handled specially in the assembler (needs each line's real
# rendered width + resolved (x,y), which aren't known until the y-cursor and
# font-metrics pass has already run) -- not registered as a plain builder.
HOOK_IN_BUILDERS = {
    "bounce": _in_bounce, "pop": _in_pop, "fade": _in_fade, "zoom": _in_zoom,
    "slide_up": _in_slide_up, "blur": _in_blur, "none": _in_none,
}


# ---- Loop (hold-period) builders ---------------------------------------
# Each takes (start_ms, exit_start_ms) and returns a \\t chain fragment
# (or "" if nothing fits/none selected). lightsweep is handled specially in
# the assembler -- it's a separate overlay event, not a tag on the base line.

def _loop_pulse(start_ms: int, exit_start_ms: int) -> str:
    """Breathing alpha oscillation, opaque <-> dim (~85% opacity), 350ms/step."""
    return _chained_keyframes("alpha", start_ms, exit_start_ms, 350, ["&H25&", "&H00&"])


def _loop_wave(start_ms: int, exit_start_ms: int) -> str:
    """
    Gentle sway via small \\frz rotation, 400ms/step.

    Angles are written signed ("-3"), never as their 0-360 equivalent
    ("357"): \\t interpolates linearly between the current value and the
    target, so animating 0 -> 357 sweeps the long way round through 180
    and spins the line upside down mid-step.
    """
    return _chained_keyframes("frz", start_ms, exit_start_ms, 400, ["-3", "3", "0"])


def _loop_shake(start_ms: int, exit_start_ms: int) -> str:
    """Sharp jitter via \\frz, 90ms/step -- same technique as wave, faster/bigger."""
    return _chained_keyframes("frz", start_ms, exit_start_ms, 90, ["-3", "3", "-2", "2", "0"])


def _loop_flicker(start_ms: int, exit_start_ms: int) -> str:
    """Uneven alpha flicker (irregular step lengths, unlike pulse's steady breathing)."""
    pattern = [(80, "&H30&"), (150, "&H00&"), (60, "&H45&"), (200, "&H00&"), (90, "&H20&"), (180, "&H00&")]
    segs = []
    t = start_ms
    i = 0
    while True:
        dur, alpha = pattern[i % len(pattern)]
        if t + dur > exit_start_ms:
            break
        segs.append(f"\\t({t},{t + dur},\\alpha{alpha})")
        t += dur
        i += 1
    return "".join(segs)


def _loop_none(start_ms: int, exit_start_ms: int) -> str:
    return ""


HOOK_LOOP_BUILDERS = {
    "pulse": _loop_pulse, "wave": _loop_wave, "shake": _loop_shake,
    "flicker": _loop_flicker, "lightsweep": _loop_none, "none": _loop_none,
}


# ---- Out (exit) builders -------------------------------------------------
# Each takes (exit_start_ms, exit_end_ms, target_scale_pct) and returns
# (tag_fragment, move_dy_px). move_dy_px is None except for slide.

def _out_fade(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    return f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)", None


def _out_slide(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    return f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)", 60  # slides down 60px while fading


def _out_zoom(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    target = round(target_scale_pct)
    grown = round(target * 1.4)
    return f"\\t({exit_start_ms},{exit_end_ms},\\fscx{grown}\\fscy{grown}\\alpha&HFF&)", None


def _out_glitch(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    """Quick \\frz jitter steps packed into the short exit window, then a hard cut."""
    jitter = _chained_keyframes("frz", exit_start_ms, max(exit_start_ms + 1, exit_end_ms - 40), 40, ["-3", "3", "0"])
    return f"{jitter}\\t({exit_end_ms - 40},{exit_end_ms},\\frz0\\alpha&HFF&)", None


def _out_none(exit_start_ms: int, exit_end_ms: int, target_scale_pct: float) -> Tuple[str, Optional[int]]:
    return f"\\t({max(exit_start_ms, exit_end_ms - 1)},{exit_end_ms},\\alpha&HFF&)", None


HOOK_OUT_BUILDERS = {
    "fade": _out_fade, "slide": _out_slide, "zoom": _out_zoom,
    "glitch": _out_glitch, "none": _out_none,
}


def _measure_text_width_px(text: str, resolved_font: str, font_size_px: int) -> Optional[int]:
    """
    Real rendered width of `text` at `font_size_px` in the family ASS will
    actually draw it in, via the same physical font files AssetRegistry
    already indexes (family -> path), not a filename guess. Returns None if
    that family has no resolvable file on disk -- callers fall back to a
    char-count estimate rather than dropping the caller's feature.
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

    libass sizes a face so the font's own line box (ascender + descender)
    equals Fontsize, while PIL and CSS size the em square to that number.
    Thai faces carry vertical metrics far taller than their em -- IBM Plex
    Sans Thai is 1650 units of line box against a 1000-unit em -- so the same
    number comes out about 40% smaller in libass than in a browser canvas.
    Anything that measures text in order to place something next to it has to
    measure at the size libass will really draw.
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
    Half-width of a hook line in PlayRes pixels, real font metrics where
    available and a char-count estimate (the same avg-char-width assumption
    the wrap step is built on) where the font file can't be resolved -- so a
    width-dependent effect degrades in size rather than disappearing.
    """
    # line_fs is the em size the text is drawn at (the \fscx boost applied
    # when writing the tags cancels libass's own line-box scaling), so PIL's
    # em-based measurement lines up 1:1 with what gets rendered.
    measured = _measure_text_width_px(line.replace("\\N", " "), resolved_font, line_fs)
    if measured is None:
        measured = int(len(line) * line_fs * 0.55)
    return max(20, measured) / 2


def _hook_lightsweep_event(
    line: str, line_fs: int, y: int, x_center: int, resolved_font: str,
    start_t: str, end_t: str, sweep_start_ms: int, exit_start_ms: int, exit_end_ms: int,
    target_scale_pct: float,
) -> Optional[str]:
    """
    Shimmer sweep: a second, brighter copy of the line drawn on top and
    clipped to a narrow vertical band that travels across it, repeatedly,
    for the whole hold period.

    Why an extra event rather than a tag on the base line: \\clip is a
    single state per line, and the typewriter In preset already animates it
    for its reveal -- a sweep sharing that line would fight it. A separate
    overlay owns its own \\clip outright.
    """
    half_w = _hook_line_width_px(line, resolved_font, line_fs)
    band_w = max(20, int(half_w * 0.7))
    left = x_center - half_w - band_w
    right = x_center + half_w
    top, bot = y - 5, y + line_fs + 5

    SWEEP_MS = 500
    segs = []
    t = sweep_start_ms
    while t + SWEEP_MS <= exit_start_ms:
        segs.append(f"\\t({t},{t + SWEEP_MS},\\clip({right - band_w:.0f},{top},{right:.0f},{bot}))")
        t += SWEEP_MS
        # 1ms snap back to the left so the next cycle sweeps again instead of
        # easing backwards -- \t always interpolates from wherever the last
        # one ended, so a cycle needs an explicit near-instant reset.
        if t + 1 <= exit_start_ms:
            segs.append(f"\\t({t},{t + 1},\\clip({left:.0f},{top},{left + band_w:.0f},{bot}))")
            t += 1
    if not segs:
        return None

    # The overlay MUST carry the same \fscx/\fscy the line it shadows uses.
    # Without it the copy renders at the style's 100% while the brand tier
    # sits at 130% and the label at 58%, and the mismatch reads on screen as
    # a second, differently-sized ghost of the text rather than a shimmer.
    target = round(target_scale_pct)
    tag = (
        f"{{\\an8\\pos({x_center},{y})\\fscx{target}\\fscy{target}"
        f"\\bord0\\shad0\\c&H00FFFFFF&\\alpha&H60&"
        f"\\clip({left:.0f},{top},{left + band_w:.0f},{bot})"
        f"{''.join(segs)}"
        f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)}}"
    )
    return f"Dialogue: 3,{start_t},{end_t},HookHeader,,0,0,0,,{tag}{line}"


def _ass_rounded_pill_path(w: float, h: float, r: float) -> str:
    """
    Constructs a smooth vector rounded rectangle for ASS \\p1 drawing mode.
    Exact parity with HTML5 Canvas roundRect(x, y, w, h, radius).
    Uses standard cubic bezier curve approximation for 90-degree corner arcs:
    k = r * 0.5522847498.
    All coordinates are positive and anchored at top-left (\\an7).
    """
    r = max(1.0, min(r, w / 2, h / 2))
    k = r * 0.5522847498
    p = [
        f"m {r:.1f} 0",
        f"l {w - r:.1f} 0",
        f"b {w - r + k:.1f} 0 {w:.1f} {r - k:.1f} {w:.1f} {r:.1f}",
        f"l {w:.1f} {h - r:.1f}",
        f"b {w:.1f} {h - r + k:.1f} {w - r + k:.1f} {h:.1f} {w - r:.1f} {h:.1f}",
        f"l {r:.1f} {h:.1f}",
        f"b {r - k:.1f} {h:.1f} 0 {h - r + k:.1f} 0 {h - r:.1f}",
        f"l 0 {r:.1f}",
        f"b 0 {r - k:.1f} {r - k:.1f} 0 {r:.1f} 0",
    ]
    return " ".join(p)


def _hook_accent_events(
    accent_id: str, model_line: str, model_line_fs: int, model_y: int, model_colour: str,
    x_center: int, resolved_font: str, start_t: str, end_t: str,
    exit_start_ms: int, exit_end_ms: int, stagger: bool,
) -> List[str]:
    """
    Decorative shape tied to the model tier: an accent bar under it, or a
    filled badge behind it. Both reveal by scaling out from the centre and
    both sit on layers below the text (drawn first), so neither ever covers
    the words it's decorating.
    """
    half_w = _hook_line_width_px(model_line, resolved_font, model_line_fs)
    reveal_start = 300 if stagger else 0
    reveal_end = reveal_start + 300
    exit_tag = f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)"

    # Every shape below is drawn from an all-positive path anchored top-left
    # (\an7) at its own left edge, NOT a centre-anchored path with negative
    # coordinates: libass mis-anchors a negative-coordinate \p drawing (it
    # lands with its right edge on \pos, off-centre by its own half-width,
    # under every alignment tested) -- measured directly against a reference
    # render. Scaling \fscx from 0 then reads as a left-to-right wipe, which
    # is also what the reveal should look like.
    if accent_id == "badge":
        pad_x = round(model_line_fs * 0.38)
        pad_y = round(model_line_fs * 0.20)
        bw = (half_w + pad_x) * 2
        bh = model_line_fs + pad_y * 2
        draw = f"m 0 0 l {bw:.0f} 0 l {bw:.0f} {bh:.0f} l 0 {bh:.0f}"
        tag = (
            f"{{\\an7\\pos({x_center - bw / 2:.0f},{model_y - pad_y})\\p1\\bord0\\shad0"
            f"\\c{model_colour}&\\alpha&HB0&\\fscx0"
            f"\\t({reveal_start},{reveal_end},\\fscx100){exit_tag}}}"
        )
        return [f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{tag}{draw}"]

    # Accent bar (default). Thicker and further from the text than the first
    # version, plus a blurred copy behind it for glow: at a 0.06 gap and a
    # 0.06 thickness it read as a plain text-decoration underline squeezed
    # between two lines rather than a deliberate poster element.
    # Boosted glyphs overflow the line box libass reserves, so the ink
    # runs lower than the nominal box bottom the cursor tracks. Measured
    # against a real render: at 0.26 the bar touched the descenders.
    gap = round(model_line_fs * 0.50)
    underline_y = model_y + model_line_fs + gap
    thickness = max(4, round(model_line_fs * 0.10))
    bar_w = half_w * 2
    left_x = x_center - half_w
    draw = f"m 0 0 l {bar_w:.0f} 0 l {bar_w:.0f} {thickness} l 0 {thickness}"
    reveal = f"\\fscx0\\t({reveal_start},{reveal_end},\\fscx100)"
    glow_tag = (
        f"{{\\an7\\pos({left_x:.0f},{underline_y})\\p1\\bord0\\shad0\\blur7"
        f"\\c{model_colour}&\\alpha&H60&{reveal}{exit_tag}}}"
    )
    bar_tag = (
        f"{{\\an7\\pos({left_x:.0f},{underline_y})\\p1\\bord0\\shad0"
        f"\\c{model_colour}&{reveal}{exit_tag}}}"
    )
    return [
        f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{glow_tag}{draw}",
        f"Dialogue: 0,{start_t},{end_t},HookHeader,,0,0,0,,{bar_tag}{draw}",
    ]

# Where the caption block sits: (ASS alignment, vertical margin).
# 2 = bottom centre, 5 = middle centre, 8 = top centre.
CAPTION_POSITIONS = {
    "bottom": (2, 420),
    "middle": (5, 0),
    "top": (8, 260),
}

# Where custom text overlays sit vertically as a fraction of frame height.
# top (0.20), middle (0.50), bottom (0.72 - above bottom caption safe zone).
TEXT_OVERLAY_POSITIONS = {
    "top": 0.20,
    "middle": 0.50,
    "bottom": 0.72,
}


def ass_colour(hex_colour: str) -> str:
    """#RRGGBB -> &H00BBGGRR. Returns "" for anything unparseable."""
    if not hex_colour:
        return ""
    value = str(hex_colour).strip().lstrip("#")
    if len(value) != 6:
        return ""
    try:
        r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return ""
    return f"&H00{b:02X}{g:02X}{r:02X}"


class SubtitleEngine:
    """Creates rapid-fire TikTok subtitles with pop animations, Kanit font, and highlights."""

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Convert float seconds to ASS timestamp format: H:MM:SS.cs"""
        seconds = max(0.0, seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        cs = int((s - int(s)) * 100)
        return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"

    @classmethod
    def split_into_smart_clauses(cls, text: str, short_clause_max: int = 18, max_line_len: int = 34) -> List[str]:
        """
        Splits Thai text into natural grammatical clauses delimited by spaces and punctuation:
        - Short clauses (< 18 chars): Combines up to 2 short clauses per line (<= 34 chars).
        - Long clauses (>= 18 chars): Stays as 1 single sentence/clause per line.
        - Orphan words / punctuation (like 'บ้าง...', 'ๆ', 'นะ', 'ครับ', '<= 4 chars'): Merged into preceding clause.
        - Never cuts mid-word or creates isolated single-word meaningless frames.
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        # 1. Split into space-delimited clauses / phrases
        raw_parts = [p.strip() for p in clean_text.replace("\n", " ").split(" ") if p.strip()]
        if not raw_parts:
            return [clean_text]

        # 1.1 If input has no spaces (or very few) and is longer than max_line_len:
        # Segment into natural clauses at conjunctions and word boundaries using PyThaiNLP
        if len(raw_parts) <= 1 and len(clean_text) > max_line_len:
            try:
                from pythainlp.tokenize import word_tokenize
                words = word_tokenize(clean_text, engine="newmm")
                clause_chunks = []
                curr = ""
                conjunctions = {"ว่า", "เพราะ", "ถ้า", "และ", "หรือ", "แต่", "เมื่อ", "มัน", "ที่", "ซึ่ง", "จน", "แล้ว", "คือ"}
                for w in words:
                    if (w in conjunctions and len(curr) >= 16) or (len(curr) + len(w) > max_line_len and len(curr) >= 14):
                        clause_chunks.append(curr)
                        curr = w
                    else:
                        curr += w
                if curr:
                    clause_chunks.append(curr)
                if len(clause_chunks) > 1:
                    raw_parts = clause_chunks
            except Exception:
                pass

        # 2. First pass: merge tiny orphan fragments into preceding clause
        merged_parts = []
        for p in raw_parts:
            if not merged_parts:
                merged_parts.append(p)
            elif (
                len(p) <= 4
                or p.startswith("ๆ")
                or p in ["บ้าง", "นะ", "ครับ", "ค่ะ", "เลย", "ด้วย", "อ่ะ", "น้า", "จ้า", "ล่ะ"]
            ):
                merged_parts[-1] += " " + p
            else:
                merged_parts.append(p)

        # 3. Second pass: Pair short clauses (2 per line) or keep long clause alone
        final_lines = []
        i = 0
        while i < len(merged_parts):
            curr = merged_parts[i]

            # Check if we can pair with the next clause (2 short clauses per line)
            if i + 1 < len(merged_parts):
                next_part = merged_parts[i + 1]
                combined_len = len(curr) + 1 + len(next_part)
                # Combine 2 short clauses if both are <= short_clause_max (or first is very short) and total fits
                if ((len(curr) <= short_clause_max and len(next_part) <= short_clause_max) or len(curr) <= 12) and combined_len <= max_line_len:
                    final_lines.append(f"{curr} {next_part}".strip())
                    i += 2
                    continue

            # Long clause or single remaining clause: 1 complete sentence per line
            final_lines.append(curr)
            i += 1

        return final_lines if final_lines else [clean_text]

    @classmethod
    def split_into_short_bursts(cls, text: str, max_chars: int = 34, max_words: int = 2) -> List[str]:
        """Backward-compatible alias for split_into_smart_clauses."""
        return cls.split_into_smart_clauses(text, max_line_len=max_chars)

    @staticmethod
    def _clause_boundaries_from_word_timings(
        clauses: List[str], word_timings: List[Dict]
    ) -> Optional[List[Tuple[float, float]]]:
        """
        Best-effort real (start, end) per entry in `clauses`, derived from
        `word_timings` (edge-tts's own word tokenization of the same text --
        it doesn't necessarily split the same way `split_into_smart_clauses`
        does, e.g. it may split "วันนี้" into "วัน"+"นี้") by walking both
        streams' cumulative character position together. `clauses` must be
        in-order substrings of the same text `word_timings` was measured
        against.

        Returns `None` when there's no word data, or when the two
        tokenizations cover too different a character count to trust a
        shared cursor -- a divergence guard, not the common case since both
        read the same underlying string.
        """
        if not word_timings:
            return None
        total_clause_chars = sum(len(cl) for cl in clauses)
        total_word_chars = sum(len(w.get("text", "")) for w in word_timings)
        if total_clause_chars == 0 or total_word_chars == 0:
            return None
        if not (0.6 <= total_word_chars / total_clause_chars <= 1.6):
            return None

        boundary_times = [word_timings[0]["start"]]
        clause_char_cursor = 0
        for cl in clauses:
            clause_char_cursor += len(cl)
            target = (clause_char_cursor / total_clause_chars) * total_word_chars
            running = 0
            end_time = word_timings[-1]["end"]
            for w in word_timings:
                running += len(w.get("text", ""))
                if running >= target:
                    end_time = w["end"]
                    break
            boundary_times.append(end_time)

        return list(zip(boundary_times[:-1], boundary_times[1:]))

    @classmethod
    def generate_micro_cues(cls, cues: List[Dict]) -> List[Dict]:
        """
        Converts sentence-level cues into smart clause cues, translating each into English.
        Uses real per-word timestamps (`cue["word_timings"]`, from edge-tts's streaming API
        in voice_engine.py) when available; falls back to proportional character-count
        splitting of the parent cue's duration otherwise -- same as before this existed.
        """
        micro_cues = []
        cue_id = 1

        for c in cues:
            start = c["start"]
            end = c["end"]
            total_dur = max(0.4, end - start)
            text = c["text"].strip()
            if not text:
                continue

            clauses = cls.split_into_smart_clauses(text)
            real_boundaries = cls._clause_boundaries_from_word_timings(
                clauses, c.get("word_timings") or []
            )
            total_chars = max(1, sum(len(cl) for cl in clauses))
            current_t = start

            for idx, cl in enumerate(clauses):
                if real_boundaries:
                    cl_start, cl_end = real_boundaries[idx]
                    cl_start = max(start, min(end, cl_start))
                    cl_end = max(cl_start, min(end, cl_end))
                else:
                    cl_dur = (len(cl) / total_chars) * total_dur
                    cl_start = current_t
                    cl_end = min(end, current_t + cl_dur)
                if idx == 0:
                    cl_start = start
                if idx == len(clauses) - 1:
                    cl_end = end

                # Only assign SFX on the very first beat of a major phrase
                sfx = None
                if idx == 0 and c.get("sfx"):
                    sfx = c["sfx"]

                # Assign Emojis selectively (only if not already present)
                emoji = ""
                has_emoji = any(cl.startswith(em) for em in ["⚠️", "🔌", "⚡", "❌", "🛒", "🌿", "💧", "🧪", "✨"])
                if not has_emoji:
                    if any(k in cl for k in ["อย่าเพิ่ง", "หยุด", "เตือน", "ห้าม", "ระวัง"]):
                        emoji = "⚠️ "
                    elif any(k in cl for k in ["สารสกัด", "สมุนไพร", "ธรรมชาติ", "ออร์แกนิก"]):
                        emoji = "🌿 "
                    elif any(k in cl for k in ["สรรพคุณ", "ผิวใส", "หน้าเด็ก", "ชุ่มชื้น", "กู้ผิว", "เซรั่ม", "คอลลาเจน", "เนียนนุ่ม"]):
                        emoji = "💧 "
                    elif any(k in cl for k in ["ส่วนผสม", "วิจัย", "ทดสอบ", "อย.", "รับรอง", "หมอ"]):
                        emoji = "🧪 "
                    elif any(k in cl for k in ["จุดเด่น", "ฟังก์ชัน", "ไฮไลต์", "พรีเมียม", "แม่เหล็ก"]):
                        emoji = "✨ "
                    elif any(k in cl for k in ["ชาร์จไว", "เร็ว", "แรง", "สปีด", "fast"]):
                        emoji = "⚡ "
                    elif any(k in cl for k in ["ปัญหา", "พัง", "เบื่อ", "แย่", "ยาก", "สิว", "ฝ้า", "ปวด"]):
                        emoji = "❌ "
                    elif any(k in cl for k in ["พิกัด", "ตะกร้า", "ราคา", "โปร", "สั่งซื้อ", "กดเลย", "ช้อป", "คุ้ม"]):
                        emoji = "🛒 "

                raw_c = f"{emoji}{cl}".strip() if emoji else cl.strip()
                cue_text = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', raw_c)).strip()
                trans = (c.get("translation") or "").strip()
                if len(clauses) == 1:
                    cue_trans = trans
                else:
                    trans_parts = [t.strip() for t in re.split(r'[,.]\s+', trans) if t.strip()]
                    if len(trans_parts) == len(clauses):
                        cue_trans = trans_parts[idx]
                    elif idx == 0:
                        cue_trans = trans
                    else:
                        cue_trans = ""

                micro_cues.append({
                    "id": cue_id,
                    "start": round(cl_start, 3),
                    "end": round(cl_end, 3),
                    "text": cue_text,
                    "translation": cue_trans,
                    "sfx": sfx
                })
                cue_id += 1
                current_t = cl_end

        # Batch translate all smart clauses into English automatically
        try:
            from scripts.translator import SubtitleTranslator
            texts_to_trans = [mc["text"] for mc in micro_cues if not mc.get("translation")]
            if texts_to_trans:
                en_translations = SubtitleTranslator.translate_batch(texts_to_trans)
                trans_idx = 0
                for mc in micro_cues:
                    if not mc.get("translation") and trans_idx < len(en_translations):
                        mc["translation"] = en_translations[trans_idx] or ""
                        trans_idx += 1
        except Exception as e:
            print(f"Subtitle translation warning: {e}")

        return micro_cues

    @classmethod
    def wrap_text_for_ass(cls, text: str, max_chars_per_line: int = 40) -> str:
        """
        Wraps long Thai text into multiple balanced lines using ASS \\N,
        preventing single-line horizontal font compression or overflow.
        """
        clean = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', text)).strip().replace("\r", "")
        if not clean or "\\N" in clean or "\n" in clean or len(clean) <= max_chars_per_line:
            return clean.replace("\n", "\\N")

        try:
            from pythainlp.tokenize import word_tokenize
            raw_words = word_tokenize(clean, engine="newmm")
        except Exception:
            raw_words = clean.split(" ")

        # Glue Thai grammatical prefixes so they never hang alone at line ends
        prefixes = {"ผู้", "การ", "ความ", "นัก", "ชาว", "จาก"}
        words = []
        i = 0
        while i < len(raw_words):
            w = raw_words[i]
            if w in prefixes and i + 1 < len(raw_words):
                words.append(w + raw_words[i + 1])
                i += 2
            else:
                words.append(w)
                i += 1

        # If length fits in 2 balanced lines:
        if len(clean) <= max_chars_per_line * 2 and len(words) > 2:
            target_mid = len(clean) / 2.0
            best_idx = 1
            best_diff = 99999
            accum = 0
            for idx, w in enumerate(words[:-1]):
                accum += len(w)
                diff = abs(accum - target_mid)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = idx + 1
            l1 = "".join(words[:best_idx]).strip()
            l2 = "".join(words[best_idx:]).strip()
            return f"{l1}\\N{l2}"

        # Otherwise chunk greedily
        lines = []
        curr = ""
        for w in words:
            if len(curr) + len(w) > max_chars_per_line and len(curr) >= 12:
                lines.append(curr)
                curr = w
            else:
                curr += w
        if curr:
            lines.append(curr)

        return "\\N".join(lines) if len(lines) > 1 else clean

    @classmethod
    def wrap_en_for_ass(cls, text: str, max_chars_per_line: int = 58) -> str:
        """Wraps long English subtitles neatly at word boundaries."""
        clean = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', text)).strip().replace("\r", "").replace("\n", " ")
        if len(clean) <= max_chars_per_line:
            return clean
        words = clean.split(" ")
        lines = []
        curr = ""
        for w in words:
            if len(curr) + len(w) + 1 > max_chars_per_line and len(curr) >= 14:
                lines.append(curr)
                curr = w
            else:
                curr = f"{curr} {w}".strip()
        if curr:
            lines.append(curr)
        return "\\N".join(lines) if len(lines) > 1 else clean

    # Dynamic Kinetic Highlighting keywords (ASS color mapped)
    # 🟡 &H0000E6FF& = Neon Yellow (Pain points, prices, deals, primary punch)
    # 🔵 &H00FFE600& = Electric Cyan (Features, tech, ergonomics, certifications)
    # 🔴 &H00303BFF& = Alert Red (Urgency, warnings)
    KINETIC_KEYWORDS: Dict[str, List[str]] = {
        "&H0000E6FF&": [  # 🟡 Neon Yellow (Pain points, prices, deals, primary punch, positive reactions)
            # 1. Physical Discomfort & Pain Points
            "ออฟฟิศซินโดรม", "ปวดข้อมือ", "ปวดหลัง", "ปวดคอ", "ปวดหัว", "ปวดไหล่", "ปวดขา", "ปวดเมื่อย",
            "ปวดมือ", "ปวดตัว", "ปวด", "เมื่อยล้า", "เมื่อย", "ทรมาน", "เหนื่อยล้า", "เหนื่อย",
            # 2. Tech & Everyday Frustrations
            "สายพันกัน", "สายขาด", "แบตหมดไว", "แบตเสื่อม", "กระตุก", "เครื่องค้าง", "ค้าง", "ช้ามาก", "ช้า",
            "พังง่าย", "พัง", "หักง่าย", "หัก", "เสียเงินฟรี", "เสียดายเงิน", "เสีย", "หลุดบ่อย", "หลุด",
            # 3. Beauty, Skin & Personal Care Problems
            "สิวบุก", "สิวเห่อ", "สิวขึ้น", "เป็นสิว", "รอยสิว", "รอยดำ", "รอยแดง", "หน้ามัน", "หน้าหมอง", "หมองคล้ำ",
            "ผิวแห้ง", "ผิวลอก", "เหนียวเหนอะหนะ", "เหนอะหนะ", "คราบฝังลึก", "สกปรก", "กลิ่นอับ", "เหม็นอับ", "เหม็น",
            # 4. Fashion, Body & Confidence
            "อึดอัด", "แน่นพุง", "พุงยื่น", "ขาใหญ่", "ดูอ้วน", "เชยๆ", "เชย", "ล้าสมัย", "ไม่มั่นใจ", "ไม่สวย",
            "ปัญหา", "ยุ่งยาก", "เสียเวลา", "เปลืองแรง", "เปลืองเงิน", "หงุดหงิด",
            # 5. Price, Deals, Vouchers & E-Commerce CTA
            "ราคาพิเศษ", "ลดราคา", "ลดกระหน่ำ", "ลดแรง", "ดีลพิเศษ", "ดีลลับ", "โปรเด็ด", "โปรแรง", "โปรโมชั่น",
            "แฟลชเซล", "flash sale", "โค้ดลด", "โค้ดลับ", "คูปอง", "ส่งฟรี", "1 แถม 1", "หนึ่งแถมหนึ่ง",
            "ของแถม", "แจกฟรี", "ฟรี", "บาท", "หลักสิบ", "หลักร้อย", "ราคาดี", "ราคาโดน", "ถูกและดี",
            "ถูกสุดๆ", "ถูกมาก", "คุ้มสุดๆ", "คุ้มค่า", "คุ้มราคา", "เกินคุ้ม", "คุ้ม", "ประหยัด", "ตกใจราคา",
            "ตะกร้าส้ม", "ตะกร้าซ้ายล่าง", "ตะกร้า", "ใส่ตะกร้า", "จิ้มตะกร้า", "จิ้มเลย", "จิ้มตรงนี้", "กดตรงนี้",
            "พิกัดในคอมเมนต์", "พิกัดในโปรไฟล์", "พิกัด", "ปักหมุด", "อย่ารอ", "อย่าช้า", "ช้าหมด",
            "รีบตำ", "รีบจัด", "ด่วนเลย", "ด่วน", "ต้องมี", "ของมันต้องมี", "ขาดไม่ได้",
            # 6. Viral Praise & Reviewer Hype
            "ป้ายยา", "ตัวท็อป", "ตัวแม่", "ยืนหนึ่ง", "ตัวตึง", "ของดีบอกต่อ", "ใช้ดีบอกต่อ", "ของดี",
            "ดีจริง", "ดูดีมาก", "ดีมาก", "ดีเกินคาด", "ดีเกินราคา", "ว้าวมาก", "ว้าว", "ตาแตก", "ตะลึง",
            "สุดปัง", "ปังมาก", "จึ้งมาก", "จึ้ง", "เลิศมาก", "เลิศ", "เอาเรื่อง", "ของแทร่", "เปลี่ยนชีวิต",
            "ยกระดับ", "หลงรักเลย", "หลงรัก", "ชอบมาก", "ติดใจ", "ไม่ผิดหวัง", "ไม่จกตา", "รีวิวจริง",
            "ใช้จริง", "หมดปัญหา", "ลืมแบบเก่าไปเลย", "โคตรดี", "โคตรคุ้ม", "ฟินมาก", "ช็อค", "น่ารักกว่าในรูป", "ของที่รอคอย"
        ],
        "&H00FFE600&": [  # 🔵 Electric Cyan (Features, tech, ergonomics, certifications, comfort)
            # 1. Tech, Gadgets & Hardware
            "Logitech Wave Keys", "Logitech", "Wave Keys", "คีย์บอร์ดในฝัน", "คีย์บอร์ด", "ไร้สาย", "บลูทูธ",
            "แม่เหล็ก", "แรงดูดสูง", "ดูดแน่น", "540 องศา", "360 องศา", "ชาร์จไว", "ฟาสชาร์จ", "66W", "100W",
            "แบตอึด", "แบตทน", "ทนทาน", "แข็งแรง", "ประกันศูนย์", "ของแท้", "แท้ 100%", "จอสวย", "จอลื่น",
            "120Hz", "คมชัด", "กล้องชัด", "เสียงดี", "เบสแน่น", "ตัดเสียงรบกวน", "กันน้ำ", "ชิปเร็ว",
            "ลื่นไหล", "ไม่สะดุด", "เชื่อมต่อง่าย", "เสียบปุ๊บติดปั๊บ", "พกพาสะดวก", "น้ำหนักเบา", "กะทัดรัด",
            "ปรับระดับได้", "พับเก็บได้", "ประหยัดพื้นที่", "ประกอบง่าย", "ใช้งานง่าย",
            # 2. Ergonomics, Comfort, Softness & Apparel
            "สรีรศาสตร์", "เมมโมรี่โฟม", "ที่รองข้อมือ", "พิมพ์สบาย", "นั่งสบาย", "นอนสบาย", "ใส่สบาย",
            "สบายมาก", "นุ่มสบาย", "สบายมือ", "สบายหลัง", "สบายตา", "สบายตัว", "สบาย", "นุ่มนิ่ม", "นุ่มฟู",
            "นุ่มมาก", "นุ่มๆ", "นุ่ม", "ยืดหยุ่น", "สัมผัสนุ่ม", "ไม่ระคายเคือง", "ไม่บาดผิว", "ทรงสวย",
            "ทรงเป๊ะ", "พอดีตัว", "เข้ารูป", "ทิ้งตัวสวย", "พรางหุ่น", "เก็บพุง", "ระบายอากาศ", "ไม่อับชื้น",
            "ไม่ร้อน", "เย็นสบาย", "มินิมอล", "ดีไซน์แบบคลื่นๆ", "แบบคลื่นๆ", "คลื่น", "ดีไซน์สวย",
            # 3. Skincare, Beauty & Quality Efficacy
            "ผิวฉ่ำวาว", "ผิวฉ่ำน้ำ", "ผิวฉ่ำ", "หน้าใส", "ผิวเนียน", "ผิวกระจก", "ผิวนุ่มเด้ง", "หน้าเด็ก",
            "ซึมไว", "ซึมเร็ว", "แห้งไว", "บางเบา", "ไม่เหนอะหนะ", "คุมมัน", "ผิวกระชับ", "รูขุมขนกระชับ",
            "กลิ่นหอม", "หอมละมุน", "หอมฟุ้ง", "ติดทน", "ติดทนนาน", "ไม่ติดแมสก์", "กันเหงื่อ", "กันน้ำกันเหงื่อ",
            "ปกปิดเนียน", "กลบเนียน", "ไม่วอก", "ไม่ลอย", "อ่อนโยน", "แพ้ง่ายใช้ได้", "สารสกัดธรรมชาติ",
            "ออร์แกนิก", "พรีเมียมสุดๆ", "พรีเมียม", "หรูหรา", "ดูแพง", "สะอาดหมดจด", "ฆ่าเชื้อ", "กรองฝุ่น",
            "รับรอง", "ผู้เชี่ยวชาญ", "แพทย์ผิวหนัง", "สุขภาพดี", "ปลอดภัย"
        ],
        "&H00303BFF&": [  # 🔴 Alert Red (Urgency, warnings)
            "อย่าเพิ่งซื้อ", "อย่าเพิ่ง", "หยุดก่อน", "หยุดดูคลิปนี้", "ฟังทางนี้", "เตือนภัย", "เตือน",
            "ระวังของปลอม", "ระวัง", "อันตราย", "เสี่ยง", "ห้ามทำ", "อย่าหาทำ", "อย่าพลาด",
            "ห้ามพลาด", "ห้ามเลื่อนผ่าน", "ของปลอมระบาด", "ซื้อผิดรุ่น", "ดูให้จบ", "ข้อเสีย", "สิ่งที่ควรรู้"
        ]
    }

    # Dynamic Kinetic Highlighting keywords for English (ASS color mapped)
    KINETIC_KEYWORDS_EN: Dict[str, List[str]] = {
        "&H0000E6FF&": [  # 🟡 Neon Yellow (Pain points, prices, deals, primary punch, positive reactions)
            # 1. Pain Points & Discomfort
            "office syndrome", "wrist pain", "back pain", "neck pain", "shoulder pain", "headache", "leg pain",
            "body pain", "hand hurts", "hurts", "painful", "pain", "tight", "sore", "exhausted",
            "tiring", "tired", "suffering",
            # 2. Product/Usage Frustrations
            "tangled", "broken cord", "dead battery", "low battery", "laggy", "lagging", "freezing", "too slow", "slow",
            "breaks easily", "broken", "waste of money", "waste of time", "wasted", "annoying",
            "acne breakout", "breakouts", "pimples", "dark spots", "redness", "oily skin", "dull skin",
            "dry skin", "peeling skin", "sticky", "greasy", "deep stains", "dirty", "bad odor", "smelly",
            "uncomfortable", "stuffy", "bloated", "tight fit", "outdated", "unconfident", "insecure",
            "problems", "problem", "frustrating", "troublesome", "not sure",
            # 3. Price, Promotions & Commerce CTA
            "special price", "huge discount", "discount", "special deal", "secret deal", "best promo", "promotion",
            "flash sale", "promo code", "voucher", "coupon", "free shipping", "buy 1 get 1", "bogo",
            "free gift", "giveaway", "free", "baht", "super cheap", "cheap", "affordable", "best price",
            "best value", "great value", "worth every penny", "worth it", "save money", "shocking price",
            "yellow basket", "orange basket", "cart", "add to cart", "click cart", "click now", "click here",
            "pinned link", "link in bio", "coordinates", "don't wait", "don't delay", "almost gone",
            "buy now", "grab it now", "hurry up", "must have", "essential",
            # 4. Viral Praise & Sensational Reactions
            "holy grail", "game changer", "life-changing", "top tier", "the best", "highly recommend",
            "really good", "looks really good", "looks good", "so good", "very good", "good", "exceeded expectations",
            "unbelievable", "very wow", "wow", "mind blowing", "stunning", "gorgeous", "slay",
            "aesthetic", "next level", "fell in love", "obsessed", "love it", "no regret", "won't be disappointed",
            "real review", "tried and tested", "problem solved", "insanely good", "super worth it", "so satisfying",
            "much cuter", "long-awaited", "recommend"
        ],
        "&H00FFE600&": [  # 🔵 Electric Cyan (Features, tech, ergonomics, certifications, comfort)
            # 1. Tech, Hardware & Gadget Specs
            "logitech wave keys", "wave keys", "logitech", "dream keyboard", "keyboard", "wireless", "bluetooth",
            "magnetic", "strong magnet", "540 degrees", "360 degrees", "fast charging", "quick charge", "66w", "100w",
            "long battery", "battery life", "durable", "sturdy", "warranty", "genuine", "authentic", "smooth screen",
            "120hz", "crystal clear", "sharp camera", "great sound", "deep bass", "noise cancelling", "waterproof",
            "fast chip", "ultra smooth", "easy connect", "plug and play", "portable", "lightweight", "compact",
            "adjustable", "foldable", "space saving", "easy to assemble", "easy to use",
            # 2. Comfort, Ergonomics & Fabric/Design
            "ergonomic", "ergonomics", "memory foam", "wrist rest", "typing comfortable", "sit comfortably",
            "comfortable fit", "comfortable", "comfy", "super comfy", "soft and comfy", "extra soft", "pillow soft",
            "very soft", "soft", "flexible", "gentle touch", "non-irritating", "flattering fit",
            "perfect fit", "slim fit", "tummy control", "breathable", "airy", "cool and fresh",
            "minimalist", "minimal", "wavy design", "wavy", "sleek design", "beautiful design",
            # 3. Skincare, Beauty & Clean Living
            "glass skin", "glowy skin", "glowing skin", "clear skin", "smooth skin", "bouncy skin", "youthful",
            "fast absorbing", "quick absorb", "quick drying", "lightweight texture", "non-sticky", "non-greasy", "oil control",
            "firming", "pore tightening", "nice scent", "pleasant smell", "long lasting", "transfer-proof", "sweat-proof",
            "water resistant", "full coverage", "natural finish", "no white cast", "gentle formula", "sensitive skin friendly",
            "natural extracts", "organic", "very premium", "premium", "luxury", "looks expensive",
            "deep clean", "antibacterial", "hepa filter", "certified", "experts", "expert",
            "dermatologist", "healthy", "safe"
        ],
        "&H00303BFF&": [  # 🔴 Alert Red (Urgency, warnings)
            "don't buy yet", "don't buy", "stop scrolling", "wait a minute", "listen to this", "urgent warning", "warning",
            "beware of fake", "beware", "danger", "risky", "don't do this", "don't miss out",
            "don't miss", "watch till the end", "counterfeit", "fake products", "cons", "must know",
            "look at this", "watch this", "warn", "stop"
        ]
    }

    @classmethod
    def apply_kinetic_highlighting(
        cls,
        text: str,
        primary_color_ass: str = "&H00FFFFFF&",
        color_hint: Optional[str] = None,
        custom_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Scans text for power keywords with 3-tier intelligence:
        Tier 1: Explicit manual markers *keyword* or [keyword] (100% user & AI control)
        Tier 2: Dynamic Project Keywords (Product names, brand, specific hook keywords)
        Tier 3: Reviewer Mega-Dictionary (500+ affiliate phrases across all niches)
        """
        if not text:
            return text

        clean_primary = primary_color_ass if primary_color_ass.endswith("&") else f"{primary_color_ass}&"
        result = text
        chosen_color = color_hint or "&H0000E6FF&"  # Default to Neon Yellow

        # Tier 1: Manual Markers (*word* or [word])
        marker_pattern = re.compile(r"(\*([^*]+)\*|\[([^\]]+)\])")
        if marker_pattern.search(result):
            def _replace_marker(m):
                kw = m.group(2) or m.group(3)
                return f"{{\\c{chosen_color}}}{kw}{{\\c{clean_primary}}}"
            return marker_pattern.sub(_replace_marker, result)

        if "{\\c" in text:
            return text

        # Tier 2: Dynamic Project Keywords (injected into Electric Cyan features)
        if custom_keywords:
            for ckw in sorted(custom_keywords, key=len, reverse=True):
                if len(ckw) >= 2 and ckw in result:
                    cyan_color = color_hint or "&H00FFE600&"
                    replacement = f"{{\\c{cyan_color}}}{ckw}{{\\c{clean_primary}}}"
                    return result.replace(ckw, replacement, 1)

        # Tier 3: Reviewer Mega-Dictionary
        # A colour hint means the other language already committed to one of
        # the meaning groups (pain point / product / warning), so this line has
        # to stay in that group. Merely trying it FIRST let a line fall through
        # to a different group when the hinted one had no match -- Thai lit
        # "ด่วนเลย" yellow from the pain-point list while English lit "look at
        # this" red from the warning list, on the same cue. When the hinted
        # group has nothing, the caller's salient-word fallback colours it in
        # that same colour instead of switching groups.
        color_order = [color_hint] if color_hint else list(cls.KINETIC_KEYWORDS.keys())
        for color_tag in color_order:
            kw_list = cls.KINETIC_KEYWORDS.get(color_tag, [])
            for kw in sorted(kw_list, key=len, reverse=True):
                if kw in result and f"{{\\c{color_tag}}}" not in result:
                    replacement = f"{{\\c{color_tag}}}{kw}{{\\c{clean_primary}}}"
                    result = result.replace(kw, replacement, 1)
                    return result

        return result

    @classmethod
    def apply_kinetic_highlighting_en(
        cls,
        text: str,
        primary_color_ass: str = "&H00EAEAEA&",
        color_hint: Optional[str] = None,
        custom_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Scans English text with 3-tier intelligence matching Thai.
        """
        if not text:
            return text

        clean_primary = primary_color_ass if primary_color_ass.endswith("&") else f"{primary_color_ass}&"
        result = text
        chosen_color = color_hint or "&H0000E6FF&"

        # Tier 1: Manual Markers (*word* or [word])
        marker_pattern = re.compile(r"(\*([^*]+)\*|\[([^\]]+)\])")
        if marker_pattern.search(result):
            def _replace_marker(m):
                kw = m.group(2) or m.group(3)
                return f"{{\\c{chosen_color}}}{kw}{{\\c{clean_primary}}}"
            return marker_pattern.sub(_replace_marker, result)

        if "{\\c" in text:
            return text

        # Tier 2: Dynamic Project Keywords
        if custom_keywords:
            for ckw in sorted(custom_keywords, key=len, reverse=True):
                if len(ckw) >= 2:
                    pattern = re.compile(rf"(?i)\b{re.escape(ckw)}\b")
                    match = pattern.search(result)
                    if match:
                        matched_str = match.group(0)
                        start, end = match.span()
                        cyan_color = color_hint or "&H00FFE600&"
                        return result[:start] + f"{{\\c{cyan_color}}}{matched_str}{{\\c{clean_primary}}}" + result[end:]

        # Tier 3: Reviewer Mega-Dictionary
        # A colour hint means the other language already committed to one of
        # the meaning groups (pain point / product / warning), so this line has
        # to stay in that group. Merely trying it FIRST let a line fall through
        # to a different group when the hinted one had no match -- Thai lit
        # "ด่วนเลย" yellow from the pain-point list while English lit "look at
        # this" red from the warning list, on the same cue. When the hinted
        # group has nothing, the caller's salient-word fallback colours it in
        # that same colour instead of switching groups.
        color_order = [color_hint] if color_hint else list(cls.KINETIC_KEYWORDS_EN.keys())
        for color_tag in color_order:
            kw_list = cls.KINETIC_KEYWORDS_EN.get(color_tag, [])
            for kw in sorted(kw_list, key=len, reverse=True):
                pattern = re.compile(rf"(?i)\b{re.escape(kw)}\b")
                match = pattern.search(result)
                if match and f"{{\\c{color_tag}}}" not in result:
                    matched_str = match.group(0)
                    start, end = match.span()
                    result = result[:start] + f"{{\\c{color_tag}}}{matched_str}{{\\c{clean_primary}}}" + result[end:]
                    return result

        return result

    # Words too functional to be worth emphasising if we have to pick one.
    _EN_STOPWORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "of", "to", "in",
        "on", "at", "for", "with", "and", "or", "but", "if", "it", "its", "this", "that",
        "these", "those", "as", "by", "from", "up", "out", "so", "than", "then", "too",
        "very", "can", "will", "just", "not", "no", "do", "does", "did", "you", "your",
        "i", "my", "we", "our", "they", "their", "he", "she", "his", "her", "how", "what",
        "who", "why", "when", "where", "all", "any", "more", "most", "some", "such", "own",
        "about", "into", "over", "also", "have", "has", "had", "would", "could", "should",
    }
    _TH_PARTICLES = {
        "ครับ", "ค่ะ", "คะ", "นะ", "น่ะ", "จ้า", "เลย", "ก็", "ที่", "ซึ่ง", "และ", "หรือ",
        "แต่", "กับ", "ของ", "ใน", "จะ", "ได้", "ให้", "มา", "ไป", "อยู่", "คือ", "ว่า",
        "เป็น", "มี", "ไม่", "แล้ว", "ด้วย", "อีก", "มัน", "เรา", "เขา", "ทั้ง", "ทุก",
    }

    @classmethod
    def _salient_word_en(cls, text: str) -> Optional[str]:
        """Longest non-stopword token, as the thing worth colouring."""
        best = None
        for raw in re.findall(r"[A-Za-z][A-Za-z'-]*", text):
            if raw.lower() in cls._EN_STOPWORDS or len(raw) < 3:
                continue
            if best is None or len(raw) > len(best):
                best = raw
        return best

    @classmethod
    def _salient_word_th(cls, text: str) -> Optional[str]:
        """Longest non-particle Thai token; falls back to the longest run of Thai letters."""
        candidates: List[str] = []
        try:
            from pythainlp.tokenize import word_tokenize

            candidates = [w.strip() for w in word_tokenize(text, engine="newmm") if w.strip()]
        except Exception:
            candidates = re.findall(r"[฀-๿]+", text)
        best = None
        for w in candidates:
            if w in cls._TH_PARTICLES or len(w) < 3:
                continue
            if not re.search(r"[฀-๿]", w):
                continue  # skip emoji/punctuation/latin
            if best is None or len(w) > len(best):
                best = w
        return best

    @classmethod
    def _force_highlight(cls, text: str, word: Optional[str], colour: str, primary: str) -> str:
        """Colour `word` inside `text` using the same wrapper the matchers use."""
        if not word or word not in text:
            return text
        clean_primary = primary if primary.endswith("&") else f"{primary}&"
        return text.replace(word, f"{{\\c{colour}}}{word}{{\\c{clean_primary}}}", 1)

    @classmethod
    def apply_bilingual_kinetic_highlighting(
        cls,
        th_text: str,
        en_text: str,
        primary_th: str = "&H00FFFFFF&",
        primary_en: str = "&H00EAEAEA&",
        custom_keywords: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """
        Guarantees 100% color synchronization between stacked Thai and English subtitles:
        - If Thai triggers a color, English prioritizes matching the same color category.
        - If English triggers a color, Thai is re-checked against that color category.
        """
        th_res = cls.apply_kinetic_highlighting(th_text, primary_color_ass=primary_th, custom_keywords=custom_keywords)
        th_color = None
        if "{\\c" in th_res:
            m = re.search(r"\{\\c(&H[0-9A-Fa-f]+&)\}", th_res)
            if m:
                th_color = m.group(1)

        en_res = cls.apply_kinetic_highlighting_en(en_text, primary_color_ass=primary_en, color_hint=th_color, custom_keywords=custom_keywords)
        en_color = None
        if "{\\c" in en_res:
            m = re.search(r"\{\\c(&H[0-9A-Fa-f]+&)\}", en_res)
            if m:
                en_color = m.group(1)

        if not th_color and en_color:
            th_res = cls.apply_kinetic_highlighting(th_text, primary_color_ass=primary_th, color_hint=en_color, custom_keywords=custom_keywords)
            th_color = en_color if "{\\c" in th_res else None

        # Matching the colour is not the same as both lines actually having
        # one. Re-running the other side with a colour hint only changes which
        # dictionary is tried first -- if that line contains no listed keyword
        # it still comes out plain, which is what left a highlighted Thai line
        # sitting above an all-white English one (and the reverse). Measured on
        # a real 28-cue project: 10 of them were lopsided this way.
        #
        # So when exactly one side found something, colour the other side's
        # most salient word in the same colour rather than leaving the pair
        # visibly inconsistent.
        if th_color and not en_color:
            en_res = cls._force_highlight(en_res, cls._salient_word_en(en_text), th_color, primary_en)
        elif en_color and not th_color:
            th_res = cls._force_highlight(th_res, cls._salient_word_th(th_text), en_color, primary_th)

        return th_res, en_res

    @classmethod
    def generate_ass(
        cls,
        cues: List[Dict],
        output_ass_path: str,
        font_name: str = "Kanit",
        font_size: int = 78,
        hook_brand: str = None,
        hook_model: str = None,
        hook_label: str = None,
        hook_duration: float = 3.5,
        hook_motion: Optional[Dict[str, object]] = None,
        hook_colors: Optional[Dict[str, str]] = None,
        bilingual: bool = True,
        video_width: int = VIDEO_WIDTH,
        video_height: int = VIDEO_HEIGHT,
        caption_position: str = "bottom",
        caption_color: str = None,
        caption_scale: float = 1.0,
        text_overlays: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Generate TikTok style ASS subtitle file with rapid-fire micro-bursts, 
        aesthetic fonts, and stacked bilingual English subtitles.
        """
        out_path = Path(output_ass_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        micro_cues = cls.generate_micro_cues(cues)

        # Real embedded family name for whichever font the UI selected --
        # every style below sets Bold=1, so libass/fontconfig picks that
        # family's bold weight itself. See _load_font_family_map().
        font_map = _load_font_family_map()
        resolved_font = font_map.get(font_name, DEFAULT_FONT_FAMILY)
        # libass sizes a face so its line box (ascender + descender) equals the
        # style's Fontsize, while the canvas preview -- and every font size in
        # this file -- means the em square. Thai faces run line boxes far
        # taller than their em, so the same number rendered ~40% smaller than
        # intended. Boosting \fscx/\fscy (never Fontsize) cancels that out:
        # glyphs land at the intended em while line advance, which libass
        # takes from Fontsize alone, stays untouched -- and \p drawings, whose
        # coordinates are already PlayRes pixels, must NOT be boosted.
        TEXT_SCALE_BOOST = 1.0 / ass_glyph_scale(resolved_font)
        is_pill_mode = font_name in ["capsule_pill", "Minimal Dark Capsule Pill"]

        # Caption placement and colour. ASS wants &HAABBGGRR, i.e. the reverse
        # byte order of an HTML hex, which is why the picker's #RRGGBB cannot
        # be pasted in directly.
        alignment, margin_v = CAPTION_POSITIONS.get(
            caption_position, CAPTION_POSITIONS["bottom"]
        )
        primary = ass_colour(caption_color) or "&H00FFFFFF"
        try:
            scale = min(2.5, max(0.4, float(caption_scale or 1.0)))
        except (TypeError, ValueError):
            scale = 1.0
        # Exact 1-to-1 pixel calibration with CapCut & SequencePlayer Canvas:
        # Standard TikTok Subtitle: 100% (scale=1.0) calibrated to exactly 50pt on 1080w
        # Matches SequencePlayer Canvas baseFs (25px on 540w) perfectly
        base_fs = int(round(video_width * 0.0463))
        font_size = max(20, int(round(base_fs * scale)))
        hook_fs = int(round(video_width * 0.065))

        # Dynamic Soft Shadow & Outline metrics (Zero hardcoding: scales with any font, scale, and resolution)
        front_outline = round(max(1.8, font_size * 0.040), 1)
        shadow_outline = round(max(2.2, font_size * 0.050), 1)
        shadow_blur = round(max(2.5, font_size * 0.055), 1)
        shadow_dx = int(round(max(1.0, font_size * 0.030)))
        shadow_dy = int(round(max(1.5, font_size * 0.045)))
        
        shadow_margin_l = 60 + shadow_dx
        shadow_margin_r = 60 - shadow_dx
        shadow_margin_v = margin_v - shadow_dy if alignment in (1, 2, 3) else margin_v + shadow_dy

        header = f"""[Script Info]
Title: TikTok Aesthetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokSoftShadow,{resolved_font},{font_size},&H00000000,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,{shadow_outline},0,{alignment},{shadow_margin_l},{shadow_margin_r},{shadow_margin_v},1
Style: TikTokWhite,{resolved_font},{font_size},{primary},&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,{front_outline},0,{alignment},60,60,{margin_v},1
Style: TikTokYellow,{resolved_font},{font_size},&H0000E6FF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,{front_outline},0,2,60,60,420,1
Style: TikTokCyan,{resolved_font},{font_size},&H00FFE600,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,{front_outline},0,2,60,60,420,1
Style: TikTokMinimalPill,{resolved_font},{font_size - 6},{primary},&H000000FF,&H00000000,&HCC000000,1,0,0,0,100,100,0.5,0,3,6,0,{alignment},60,60,{margin_v},1
Style: HookHeader,{resolved_font},{hook_fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,6.0,0,8,60,60,260,1
Style: HookHeaderShadow,{resolved_font},{hook_fs},&H00000000,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,7.0,0,8,62,58,257,1
Style: SpecBar,{resolved_font},{font_size - 12},&H00000000,&H000000FF,&H00000000,&H0000E6FF,1,0,0,0,100,100,0.5,0,3,10,0,9,50,50,380,1
Style: TextOverlayMain,{resolved_font},{base_fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,5.0,2,5,60,60,0,1
Style: TextOverlayPill,{resolved_font},{base_fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,5.0,2,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []

        # 1. Top Hook Banner -- 3-tier product-poster composition (brand
        # largest / model mid / label smallest), replacing the old single
        # free-text hook_title line. All three tiers live in ONE dialogue
        # event per layer (Shadow, Main), \N-joined, each line carrying its
        # own override block -- same stacking pattern the bilingual caption
        # block below already uses, so every property (\fscx/\fscy/\c) that
        # matters is re-declared per line and nothing leaks across a \N.
        if hook_brand or hook_model or hook_label:
            motion = _resolve_hook_motion(hook_motion)
            start_t = cls._format_ass_time(0.0)
            end_t = cls._format_ass_time(hook_duration)
            # The exit window every Out preset animates into. `\t` offsets are
            # relative to an event's own Start (0 for every hook line), so
            # they double as absolute ms. Guarded against a hook shorter than
            # the entry animation ever producing exit_start >= exit_end,
            # which a renderer could choke on.
            exit_end_ms = int(hook_duration * 1000)
            exit_start_ms = max(120, exit_end_ms - 150)
            if exit_start_ms >= exit_end_ms:
                exit_start_ms = max(0, exit_end_ms - 50)

            # (raw text, target scale % of hook_fs, Main-layer colour, tier index)
            # tier index also doubles as the stagger slot (0=brand, 1=model,
            # 2=label) and marks which physical line(s) the accent shape
            # attaches to (tier 1, model).
            #
            # Each tier's colour is independently overridable (a brand with
            # green equity shouldn't be forced to white); an unset tier keeps
            # the poster default it had before -- white wordmark, accent
            # model, muted label.
            colours = hook_colors or {}
            brand_colour = ass_colour(colours.get("brand")) or "&H00FFFFFF"
            model_colour = ass_colour(colours.get("model")) or ass_colour(caption_color) or "&H0000E6FF"
            label_colour = ass_colour(colours.get("label")) or "&H00E0E0E0"
            hook_tier_specs = [
                (hook_brand, 130, brand_colour, 0),
                (hook_model, 100, model_colour, 1),
                (hook_label, 58, label_colour, 2),
            ]

            # Pass 1: wrap each tier at its OWN char width -- a 130%-scale
            # line needs a narrower wrap than a 58%-scale one, or the brand
            # line runs wider than the frame while the label line wraps too
            # early. wrap_text_for_ass is the same balanced-wrap caption
            # already uses below; the hook banner never called it before.
            tier_lines = []  # (line_text, scale_pct, colour, tier_idx)
            model_last_line = None
            for raw_text, scale_pct, colour, tier_idx in hook_tier_specs:
                text = str(raw_text or "").strip()
                if not text:
                    continue
                if scale_pct == 130:
                    text = text.upper()  # brand reads as a wordmark; .upper() is a no-op on Thai
                tier_fs = max(20, int(round(hook_fs * scale_pct / 100)))
                dyn_max_chars = max(8, int(round(2600 / tier_fs)))
                wrapped = cls.wrap_text_for_ass(text, max_chars_per_line=dyn_max_chars)
                lines = wrapped.split("\\N")
                for line in lines:
                    tier_lines.append((line, scale_pct, colour, tier_idx))
                if tier_idx == 1:
                    model_last_line = lines[-1]

            if tier_lines:
                # Pass 2: more than ~4 lines total (e.g. a long brand name
                # wrapping twice) starts crowding the sticker badge
                # (top-right, y=140) and reads as clutter for a short
                # banner -- shrink every tier proportionally instead of
                # letting the block grow unbounded. Floor at 0.7 so it never
                # shrinks past reading as a headline.
                HOOK_COMFORTABLE_LINES = 4
                shrink = max(0.7, min(1.0, HOOK_COMFORTABLE_LINES / len(tier_lines)))
                STAGGER_STEP_MS = 150

                # Line-height factor for the manual vertical cursor. Measured
                # directly off a real ffmpeg+libass render (pixel-scanned ink
                # bands per tier), not guessed -- an initial 1.28 guess put
                # the accent bar a full line too low, under the label instead
                # of the model. If it drifts after a font change, remeasure
                # the same way rather than re-guessing.
                LINE_HEIGHT_FACTOR = 1.0
                x_center = video_width // 2

                in_builder = HOOK_IN_BUILDERS.get(motion["in"], _in_bounce)
                loop_builder = HOOK_LOOP_BUILDERS.get(motion["loop"], _loop_pulse)
                out_builder = HOOK_OUT_BUILDERS.get(motion["out"], _out_fade)
                is_typewriter = motion["in"] == "typewriter"

                # Pass 3: walk the y-cursor once and resolve every line's
                # size, position and entrance up front. Each line becomes its
                # OWN dialogue event (rather than \N-joined into one shared
                # block) because \move, \frz and \clip are per-event state --
                # slide/wave/shake/glitch/typewriter all need to act on one
                # line without dragging its neighbours along.
                cursor_y = 260  # HookHeader style's MarginV: top edge of the block
                line_records = []
                max_entry_end_ms = 0
                model_line_fs = None
                model_y = None
                for idx, (line, scale_pct, colour, tier_idx) in enumerate(tier_lines):
                    # Two percentages, deliberately: `layout_pct` is the design
                    # intent in em (what the canvas preview draws and what every
                    # width/position here is measured against), while `target`
                    # is what actually goes into scx -- boosted by
                    # TEXT_SCALE_BOOST so libass's own line-box scaling cancels
                    # out and the glyphs land at the em size that was intended.
                    layout_pct = round(scale_pct * shrink)
                    target = round(layout_pct * TEXT_SCALE_BOOST)
                    line_fs = max(20, int(round(hook_fs * layout_pct / 100)))
                    t0_ms = tier_idx * STAGGER_STEP_MS if motion["stagger"] else 0
                    if is_typewriter:
                        # its \clip needs this line's resolved width and y,
                        # which only exist once this walk has placed it
                        in_tag, entry_end_ms, move_dy_in = None, t0_ms + 400, None
                    else:
                        in_tag, entry_end_ms, move_dy_in = in_builder(target, t0_ms)
                    max_entry_end_ms = max(max_entry_end_ms, entry_end_ms)
                    line_records.append({
                        "line": line, "target": target, "line_fs": line_fs, "colour": colour,
                        "t0_ms": t0_ms, "in_tag": in_tag, "entry_end_ms": entry_end_ms,
                        "move_dy_in": move_dy_in, "y": cursor_y,
                    })
                    if tier_idx == 1:
                        model_line_fs = line_fs
                        model_y = cursor_y
                    cursor_y += round(line_fs * LINE_HEIGHT_FACTOR)

                    # An accent shape is a layout element, not an overlay:
                    # reserve room for it after the model tier's last line so
                    # the label below never has a bar drawn through it (at
                    # LINE_HEIGHT_FACTOR 1.0 consecutive lines touch exactly,
                    # leaving no natural gap to borrow).
                    is_last_model_line = tier_idx == 1 and (
                        idx + 1 >= len(tier_lines) or tier_lines[idx + 1][3] != 1
                    )
                    if is_last_model_line and motion["accent"] != "none":
                        reserve = 0.80 if motion["accent"] != "badge" else 0.45
                        cursor_y += round(line_fs * reserve)

                # One loop chain shared by every line: it depends only on
                # timing, and starts once the LAST tier has finished entering
                # so a stagger never leaves one line pulsing while another is
                # still flying in.
                loop_tag = loop_builder(max_entry_end_ms, exit_start_ms)

                for rec in line_records:
                    out_tag, move_dy_out = out_builder(exit_start_ms, exit_end_ms, rec["target"])

                    if is_typewriter:
                        half_w = _hook_line_width_px(rec["line"], resolved_font, rec["line_fs"])
                        top, bot = rec["y"] - 5, rec["y"] + rec["line_fs"] + 5
                        x_from, x_to = x_center - half_w, x_center + half_w
                        in_tag = (
                            f"\\clip({x_from:.0f},{top},{x_from:.0f},{bot})"
                            f"\\t({rec['t0_ms']},{rec['entry_end_ms']},"
                            f"\\clip({x_from:.0f},{top},{x_to:.0f},{bot}))"
                        )
                    else:
                        in_tag = rec["in_tag"]

                    # \move is a single linear segment, so a line can only
                    # truly slide once: a sliding entrance wins the slot over
                    # a sliding exit, which still fades out in place via
                    # out_tag -- it loses the travel, not the exit.
                    if rec["move_dy_in"] is not None:
                        pos_tag = (
                            f"\\move({x_center},{rec['y'] + rec['move_dy_in']},"
                            f"{x_center},{rec['y']},{rec['t0_ms']},{rec['entry_end_ms']})"
                        )
                    elif move_dy_out is not None:
                        pos_tag = (
                            f"\\move({x_center},{rec['y']},{x_center},{rec['y'] + move_dy_out},"
                            f"{exit_start_ms},{exit_end_ms})"
                        )
                    else:
                        pos_tag = f"\\pos({x_center},{rec['y']})"

                    common = f"\\an8{pos_tag}{in_tag}{loop_tag}{out_tag}"
                    events.append(
                        f"Dialogue: 1,{start_t},{end_t},HookHeaderShadow,,0,0,0,,"
                        f"{{{common}\\blur5\\alpha&H40&}}{rec['line']}"
                    )
                    events.append(
                        f"Dialogue: 2,{start_t},{end_t},HookHeader,,0,0,0,,"
                        f"{{{common}\\c{rec['colour']}&}}{rec['line']}"
                    )

                    if motion["loop"] == "lightsweep":
                        sweep = _hook_lightsweep_event(
                            rec["line"], rec["line_fs"], rec["y"], x_center, resolved_font,
                            start_t, end_t, max_entry_end_ms, exit_start_ms, exit_end_ms,
                            rec["target"],
                        )
                        if sweep:
                            events.append(sweep)

                if motion["accent"] != "none" and model_last_line and model_line_fs:
                    events.extend(_hook_accent_events(
                        motion["accent"], model_last_line, model_line_fs, model_y, model_colour,
                        x_center, resolved_font, start_t, end_t,
                        exit_start_ms, exit_end_ms, motion["stagger"],
                    ))

        # Batch-translate whatever is still missing an English line.
        #
        # This used to reuse the stored translations whenever ANY cue had one
        # (`any(...)`), so a batch that came back with gaps -- the free
        # translation endpoint drops lines under load -- kept those gaps
        # forever: every later render and re-roll saw "some translations
        # exist" and never retried the empty ones. Measured across the
        # project folders: one clip was missing English on 16 of 25 cues.
        en_translations = []
        if bilingual:
            en_translations = [(c.get("translation") or "") for c in micro_cues]
            missing_idx = [i for i, t in enumerate(en_translations) if not t.strip()]
            if missing_idx:
                try:
                    try:
                        from scripts.translator import SubtitleTranslator
                    except Exception:
                        from translator import SubtitleTranslator
                    fresh = SubtitleTranslator.translate_batch(
                        [micro_cues[i]["text"] for i in missing_idx]
                    )
                    for i, translated in zip(missing_idx, fresh):
                        if translated:
                            en_translations[i] = translated
                except Exception as err:
                    print(f"   ⚠️  แปลอังกฤษไม่สำเร็จ ({err}) — ซับจะเป็นไทยอย่างเดียว")
        else:
            en_translations = [""] * len(micro_cues)

        # Collect dynamic project keywords from the hook banner or product
        # hints -- feeds the kinetic-highlighting pass below so brand/model
        # words get the same colour treatment wherever they show up in the
        # captions, not just in the banner. Joins all three tiers; must stay
        # in sync with whatever the banner actually displays above.
        hook_combined = " ".join(filter(None, [hook_brand, hook_model, hook_label])).strip()
        proj_keywords = []
        if hook_combined:
            proj_keywords.append(hook_combined)
            for t in hook_combined.split():
                if len(t.strip()) >= 3 and t.strip() not in proj_keywords:
                    proj_keywords.append(t.strip())

        # 2. Add Rapid-Fire Micro-Cues with Stacked Bilingual Support & 2-Layer Soft Shadow
        for idx, cue in enumerate(micro_cues):
            start_t = cls._format_ass_time(cue["start"])
            end_t = cls._format_ass_time(cue["end"])
            # Exact line wrap calibration matching SequencePlayer.jsx maxLineW = 464px (86% of 1080w = 928px)
            dyn_max_chars = max(24, int(round(3100 / max(20, font_size))))
            text = cls.wrap_text_for_ass(cue["text"].strip(), max_chars_per_line=dyn_max_chars)
            if not text:
                continue
            # Sync wrapped text with \\N back into cue object for 100% editor preview parity
            cue["text"] = text

            # Kinetic Pop Animation: Snap in 125% -> Settle 100% (or cue.scale) in 70ms
            cue_scale = float(cue.get("scale", 1.0) or 1.0)
            settle_pct = max(50, min(200, int(round(100 * cue_scale))))
            snap_pct = int(round(settle_pct * 1.25))
            # em intent -> what \fscx has to say for libass to draw it (see
            # TEXT_SCALE_BOOST). The preview keeps using the unboosted numbers.
            settle_pct = int(round(settle_pct * TEXT_SCALE_BOOST))
            snap_pct = int(round(snap_pct * TEXT_SCALE_BOOST))
            anim = f"{{\\fscx{snap_pct}\\fscy{snap_pct}\\t(0,70,\\fscx{settle_pct}\\fscy{settle_pct})}}"
            
            # Check for English Translation
            en_wrapped = ""
            if bilingual and idx < len(en_translations):
                candidate_en = (en_translations[idx] or cue.get("translation", "")).strip()
                if candidate_en and not any(sig in candidate_en for sig in ["Error 500", "500.", "That's an error", "<html"]):
                    cue["translation"] = candidate_en
                    dyn_en_chars = max(26, int(round(4000 / max(20, font_size))))
                    en_wrapped = cls.wrap_en_for_ass(candidate_en, max_chars_per_line=dyn_en_chars)
                else:
                    cue["translation"] = ""

            # The English line sits at 68% of the Thai one; that 68 is an em
            # intent like every other size here, so it takes the same boost.
            en_pct = int(round(68 * TEXT_SCALE_BOOST))
            # Apply Synchronized Bilingual Kinetic Highlighting (guaranteeing exact color parity)
            if en_wrapped:
                highlighted_text, en_highlighted = cls.apply_bilingual_kinetic_highlighting(
                    th_text=text,
                    en_text=en_wrapped,
                    primary_th=primary,
                    primary_en="&H00EAEAEA&",
                    custom_keywords=proj_keywords
                )
                en_sub = f"\\N{{\\fscx{en_pct}\\fscy{en_pct}\\c&H00EAEAEA&}}{en_highlighted}"
            else:
                highlighted_text = cls.apply_kinetic_highlighting(text, primary_color_ass=primary, custom_keywords=proj_keywords)
                en_sub = ""

            style = "TikTokMinimalPill" if is_pill_mode else "TikTokWhite"

            # Layer 0: Natural Soft Feathered Shadow (Gaussian Blur matching Canvas preview)
            if not is_pill_mode:
                en_sub_shadow = f"\\N{{\\fscx{en_pct}\\fscy{en_pct}}}{en_wrapped}" if en_wrapped else ""
                shadow_tag = f"{{\\blur{shadow_blur}\\alpha&H38&}}"
                events.append(f"Dialogue: 0,{start_t},{end_t},TikTokSoftShadow,,0,0,0,,{anim}{shadow_tag}{text}{en_sub_shadow}")

            # Layer 1: Crisp Foreground Text with dynamic kinetic highlights
            line_entry = f"Dialogue: 1,{start_t},{end_t},{style},,0,0,0,,{anim}{highlighted_text}{en_sub}"
            events.append(line_entry)

        # 3. Spec-Bar Overlays (IT vertical: the number goes on screen, not
        # just in the voiceover). These read from the original sentence-level
        # `cues`, not micro_cues -- a spec stays up for the whole line it
        # belongs to, not just one 2-3 word burst. `on_screen` is filled in by
        # pipeline.py from the AI script's per-line overlay text (see
        # ai_bridge.py's `script` task); a line with nothing to show just has
        # an empty/missing value and gets no bar.
        for cue in cues:
            on_screen = (cue.get("on_screen") or "").strip()
            if not on_screen:
                continue
            spec_start = cls._format_ass_time(cue["start"])
            spec_end = cls._format_ass_time(cue["end"])
            spec_from = int(round(110 * TEXT_SCALE_BOOST))
            spec_to = int(round(100 * TEXT_SCALE_BOOST))
            spec_anim = f"{{\\fscx{spec_from}\\fscy{spec_from}\\t(0,100,\\fscx{spec_to}\\fscy{spec_to})}}"
            # Layer 2, above the hook banner (1) and captions (0), in case a
            # long spec bar's footprint ever crosses either at the same time.
            events.append(f"Dialogue: 2,{spec_start},{spec_end},SpecBar,,0,0,0,,{spec_anim}📊 {on_screen}")

        # 4. Custom Text Overlays (Freeform multi-layer text lines)
        if text_overlays:
            for item in text_overlays:
                txt = str(item.get("text") or "").strip()
                if not txt:
                    continue
                try:
                    start_sec = float(item.get("start", 0.0))
                except (TypeError, ValueError):
                    start_sec = 0.0
                try:
                    end_sec = float(item.get("end", start_sec + 2.5))
                except (TypeError, ValueError):
                    end_sec = start_sec + 2.5
                if end_sec <= start_sec:
                    end_sec = start_sec + 1.0

                start_t = cls._format_ass_time(start_sec)
                end_t = cls._format_ass_time(end_sec)

                pos = item.get("position", "middle")
                y_ratio = TEXT_OVERLAY_POSITIONS.get(pos, 0.50)
                y_pos = int(round(video_height * y_ratio))
                x_pos = video_width // 2

                try:
                    scale = float(item.get("scale", 1.0) or 1.0)
                except (TypeError, ValueError):
                    scale = 1.0
                scale = min(2.5, max(0.4, scale))

                color_hex = ass_colour(item.get("color")) or "&H00FFFFFF"
                bg_style = item.get("bgStyle", "none")
                anim = item.get("anim", "pop")

                dur_ms = int(round((end_sec - start_sec) * 1000))
                exit_start_ms = max(50, dur_ms - 150)
                exit_tag = f"\\t({exit_start_ms},{dur_ms},\\alpha&HFF&)"

                target_scale = int(round(100 * scale * TEXT_SCALE_BOOST))
                anim_tag = ""
                pos_tag = f"\\an5\\pos({x_pos},{y_pos})"

                if anim == "pop":
                    snap_from = int(round(target_scale * 1.25))
                    anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,70,\\fscx{target_scale}\\fscy{target_scale})"
                elif anim == "fade":
                    anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t(0,150,\\alpha&H00&)"
                elif anim == "slide":
                    pos_tag = f"\\an5\\move({x_pos},{y_pos + 40},{x_pos},{y_pos},0,200)"
                    anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t(0,200,\\alpha&H00&)"
                else:  # none
                    anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}"

                render_fs = int(round(base_fs * scale))
                line_list = [l.strip() for l in txt.split("\n") if l.strip()]
                clean_lines = "\\N".join(line_list)

                # Layer 3: If bg_style == 'pill', draw smooth semi-transparent rounded pill badge
                if bg_style == "pill" and line_list:
                    line_h = round(render_fs * 1.2)
                    total_h = len(line_list) * line_h
                    max_line_w = 0
                    for l in line_list:
                        w = _measure_text_width_px(l, resolved_font, render_fs)
                        if w is None:
                            w = int(len(l) * render_fs * 0.55)
                        if w > max_line_w:
                            max_line_w = w
                    pad_x = round(render_fs * 0.6)
                    pad_y = round(render_fs * 0.35)
                    pill_w = max_line_w + pad_x * 2
                    pill_h = total_h + pad_y * 2
                    pill_x = x_pos - pill_w / 2
                    pill_y = y_pos - total_h / 2 - pad_y
                    radius = min(round(pill_h / 2), 28)
                    pill_path = _ass_rounded_pill_path(pill_w, pill_h, radius)

                    if anim == "slide":
                        pill_pos = f"\\an7\\move({pill_x:.0f},{pill_y + 40:.0f},{pill_x:.0f},{pill_y:.0f},0,200)"
                        pill_anim = f"\\alpha&HFF&\\t(0,200,\\alpha&H59&)"
                    elif anim == "fade":
                        pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
                        pill_anim = f"\\alpha&HFF&\\t(0,150,\\alpha&H59&)"
                    elif anim == "pop":
                        pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
                        pill_anim = f"\\alpha&HFF&\\t(0,70,\\alpha&H59&)"
                    else:  # none
                        pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
                        pill_anim = f"\\alpha&H59&"

                    pill_tag = f"{pill_pos}\\p1\\bord0\\shad0\\c&H000000&{pill_anim}{exit_tag}"
                    events.append(f"Dialogue: 3,{start_t},{end_t},TextOverlayMain,,0,0,0,,{{{pill_tag}}}{pill_path}")

                # Layer 4: Text itself (clean TextOverlayMain with outline and shadow, never ugly BorderStyle=3 box)
                events.append(
                    f"Dialogue: 4,{start_t},{end_t},TextOverlayMain,,0,0,0,,"
                    f"{{{pos_tag}{anim_tag}\\c{color_hex}&{exit_tag}}}{clean_lines}"
                )

        content = header + "\n".join(events) + "\n"
        out_path.write_text(content, encoding="utf-8")
        return str(out_path), micro_cues

if __name__ == "__main__":
    print("SubtitleEngine ready.")
