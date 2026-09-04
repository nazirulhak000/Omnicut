"""
Preview/render parity guard.

The canvas preview (SequencePlayer.jsx) and the ASS renderer
(subtitle_engine.py) are two independent implementations of the same
picture. Every constant they must agree on is asserted here by reading it
out of each source file, so a change to one side that isn't mirrored on the
other fails here instead of shipping as "the preview lied about the render".

Values marked "measured" were taken off a real ffmpeg+libass render rather
than derived, and the comment says what was measured.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY_SRC = (ROOT / "scripts" / "subtitle_engine.py").read_text(encoding="utf-8")
JS_SRC = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")


def _grab(text, pattern, cast=float):
    match = re.search(pattern, text, re.S)
    assert match, f"parity probe found nothing for {pattern!r} -- did the code move?"
    return cast(match.group(1))


def _ass_alpha_opacity(hex_str):
    """ASS \\alpha is TRANSPARENCY; canvas globalAlpha is opacity."""
    return 1 - int(hex_str, 16) / 255


# ---------------------------------------------------------------- sizing
def test_hook_and_caption_font_ratios_match():
    """
    Both sides size text as a fraction of frame width, and the canvas is
    exactly half the render's width, so the fractions must be identical.
    """
    assert _grab(PY_SRC, r"hook_fs = int\(round\(video_width \* ([\d.]+)\)\)") == \
           _grab(JS_SRC, r"baseFontSize = Math\.round\(CANVAS_W \* ([\d.]+)\)")
    assert _grab(PY_SRC, r"base_fs = int\(round\(video_width \* ([\d.]+)\)\)") == \
           _grab(JS_SRC, r"baseFs = Math\.round\(CANVAS_W \* ([\d.]+)\)")


def test_line_advance_matches_measured_libass_behaviour():
    """
    Measured: a 72px style stepped exactly 72px to the next \\N line, even
    when that line carried \\fscx68\\fscy68. So both the hook's manual cursor
    and the caption's stacking advance by 1.0 x font size.
    """
    assert _grab(PY_SRC, r"LINE_HEIGHT_FACTOR = ([\d.]+)") == \
           _grab(JS_SRC, r"const lineGap = ([\d.]+)") == 1.0
    assert "const thaiLineH = fontSize;" in JS_SRC
    assert "const enLineH = fontSize;" in JS_SRC


def test_font_size_is_converted_between_the_two_text_engines():
    """
    The one that kept coming back. libass sizes a face so the font's own line
    box (ascender + descender) equals the style's Fontsize; canvas and CSS
    size the EM SQUARE to the px number. Thai faces run line boxes far taller
    than their em -- IBM Plex Sans Thai is 1650 units against a 1000-unit em
    -- so handing the same number to both engines drew preview text about
    1.65x larger than the render, no matter how carefully the ratios matched.

    Measured: libass at Fontsize 100 produced the same ink width as PIL at
    ~60px for that face. So every size crossing into a text engine must be
    converted, and every constant-level "the ratios are equal" check is
    necessary but not sufficient.

    The conversion lives on the ASS side, as a \\fscx/\\fscy boost rather than
    a bigger Fontsize: libass takes line advance from Fontsize alone, so
    touching Fontsize would have stretched every line gap by the same 1.65x.
    The canvas keeps drawing the plain em number.
    """
    assert "usWinAscent + os2.usWinDescent" in PY_SRC
    assert "TEXT_SCALE_BOOST = 1.0 / ass_glyph_scale(resolved_font)" in PY_SRC

    # every text scale that reaches \fscx carries the boost
    for probe in [
        "target = round(layout_pct * TEXT_SCALE_BOOST)",       # hook tiers
        "settle_pct = int(round(settle_pct * TEXT_SCALE_BOOST))",  # caption pop
        "en_pct = int(round(68 * TEXT_SCALE_BOOST))",          # english sub
        "spec_from = int(round(110 * TEXT_SCALE_BOOST))",      # spec bar
    ]:
        assert probe in PY_SRC, f"missing text scale boost: {probe}"

    # Fontsize itself must stay the em number, or line advance drifts
    assert "hook_fs = int(round(video_width * 0.065))" in PY_SRC
    assert "TEXT_SCALE_BOOST" not in PY_SRC.split("hook_fs = int(round(")[1].split("\n")[0]

    # \p drawings are already in PlayRes pixels and must NOT be boosted
    drawing_block = PY_SRC.split("def _hook_accent_events")[1].split("\ndef ")[0]
    assert "TEXT_SCALE_BOOST" not in drawing_block, "accent drawings must not take the text boost"


def test_caption_pop_animation_matches():
    """
    The renderer pops each cue in at 125% and settles over 70ms
    (subtitle_engine.py's per-cue `anim`). The preview had no entrance
    animation at all, so captions appeared already settled.
    """
    assert _grab(PY_SRC, r"snap_pct = int\(round\(settle_pct \* ([\d.]+)\)\)") == \
           _grab(JS_SRC, r"const CAPTION_POP_FROM = ([\d.]+);")
    assert _grab(PY_SRC, r"anim = f\"\{\{\\\\fscx\{snap_pct\}\\\\fscy\{snap_pct\}\\\\t\(0,(\d+),")  == \
           _grab(JS_SRC, r"const CAPTION_POP_MS = (\d+);")


def test_transition_defaults_match():
    """
    Preview and render each keep their own literal for the default/max
    transition duration; they must stay equal or the slider lies.
    """
    js_math = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").read_text(encoding="utf-8")
    py_editor = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    assert _grab(js_math, r"FADE_DURATION = ([\d.]+)") == \
           _grab(py_editor, r"DEFAULT_TRANSITION_DURATION = ([\d.]+)")
    assert _grab(js_math, r"MAX_TRANSITION_DURATION = ([\d.]+)") == \
           _grab(py_editor, r"MAX_TRANSITION_DURATION = ([\d.]+)")


def test_transition_catalogs_are_identical():
    """Every id the Inspector offers must be one the renderer can execute."""
    js_math = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").read_text(encoding="utf-8")
    py_editor = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    js_ids = set(re.findall(r"\{ id: '([a-z]+)'", js_math))
    py_ids = set(re.findall(r'"([a-z]+)"', _grab(py_editor, r"XFADE_TRANSITIONS = \((.*?)\)", str)))
    assert js_ids == py_ids, f"only in preview: {js_ids - py_ids}; only in render: {py_ids - js_ids}"


def test_crossfade_base_layer_is_opaque():
    """
    Draw-plan alphas are paint-order alphas. Giving the outgoing clip
    1 - alpha over a cleared canvas sagged total coverage to 0.75
    mid-transition, a dip to background that ffmpeg's xfade never shows.
    """
    js_math = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").read_text(encoding="utf-8")
    assert "localTime: localTimeAt(prevSeg, t), alpha: 1 }" in js_math


def test_hook_block_top_is_the_same_fraction_of_frame_height():
    ass_top = _grab(PY_SRC, r"cursor_y = (\d+)  # HookHeader") / 1920
    canvas_top = _grab(JS_SRC, r"let y = (\d+); // ~HookHeader") / 960
    assert ass_top == canvas_top


def test_tier_scales_and_shrink_rule_match():
    assert re.findall(r"\(hook_\w+, (\d+), \w+_colour, \d\)", PY_SRC) == \
           re.findall(r"sizePct: (\d+)", JS_SRC)
    assert _grab(PY_SRC, r"HOOK_COMFORTABLE_LINES = (\d+)") == \
           _grab(JS_SRC, r"Math\.max\(0\.7, Math\.min\(1, (\d+) / wrapped\.length\)\)")


# ---------------------------------------------------------------- timing
def test_stagger_and_exit_windows_match():
    assert _grab(PY_SRC, r"STAGGER_STEP_MS = (\d+)") == \
           _grab(JS_SRC, r"HOOK_STAGGER_STEP = ([\d.]+)") * 1000
    assert _grab(PY_SRC, r"exit_start_ms = max\(120, exit_end_ms - (\d+)\)") == \
           _grab(JS_SRC, r"exitStartSec = Math\.max\(0\.12, hookDuration - ([\d.]+)\)") * 1000


@pytest.mark.parametrize(
    "preset, py_pattern",
    [
        ("bounce", r"def _in_bounce.*?end_ms = t0_ms \+ (\d+)"),
        ("pop", r"def _in_pop.*?end_ms = t0_ms \+ (\d+)"),
        ("fade", r"def _in_fade.*?end_ms = t0_ms \+ (\d+)"),
        ("zoom", r"def _in_zoom.*?end_ms = t0_ms \+ (\d+)"),
        ("slide_up", r"def _in_slide_up.*?end_ms = t0_ms \+ (\d+)"),
        ("blur", r"def _in_blur.*?end_ms = t0_ms \+ (\d+)"),
        ("typewriter", r"in_tag, entry_end_ms, move_dy_in = None, t0_ms \+ (\d+)"),
    ],
)
def test_in_preset_durations_match(preset, py_pattern):
    assert _grab(PY_SRC, py_pattern) == \
           _grab(JS_SRC, rf"{preset}: \{{\s*durSec: ([\d.]+)") * 1000


@pytest.mark.parametrize(
    "preset, py_pattern, js_pattern",
    [
        ("pulse", r'_chained_keyframes\("alpha", start_ms, exit_start_ms, (\d+)',
         r"pulse: \(t, s, e\) => \(\{ alpha: hookCycleAt\(t, s, e, ([\d.]+)"),
        ("wave", r'_chained_keyframes\("frz", start_ms, exit_start_ms, (\d+)',
         r"wave: \(t, s, e\) => \(\{ rot: hookCycleAt\(t, s, e, ([\d.]+)"),
        ("shake", r'_chained_keyframes\("frz", start_ms, exit_start_ms, (\d+), \["-3", "3", "-2"',
         r"shake: \(t, s, e\) => \(\{ rot: hookCycleAt\(t, s, e, ([\d.]+)"),
    ],
)
def test_loop_preset_step_lengths_match(preset, py_pattern, js_pattern):
    assert _grab(PY_SRC, py_pattern) == _grab(JS_SRC, js_pattern) * 1000


# ---------------------------------------------------------------- opacity
def test_alpha_values_are_converted_not_copied():
    """
    The recurring trap: ASS \\alpha counts transparency and canvas
    globalAlpha counts opacity, so the same hex means opposite things. The
    badge shipped at 0.69 opacity in preview against 0.31 in render because
    the hex was carried across without inverting.
    """
    js_inverted = re.findall(r"ctx\.globalAlpha \*= 1 - 0x([0-9A-F]+) / 255", JS_SRC)
    assert len(js_inverted) >= 2, "badge and accent glow should both convert explicitly"

    py_badge = _grab(PY_SRC, r'accent_id == "badge".*?\\\\alpha&H([0-9A-F]+)&', str)
    assert _ass_alpha_opacity(py_badge) == _ass_alpha_opacity(js_inverted[0])

    py_glow = _grab(PY_SRC, r"glow_tag = \(.*?\\\\alpha&H([0-9A-F]+)&", str)
    assert _ass_alpha_opacity(py_glow) == _ass_alpha_opacity(js_inverted[1])

    py_dim = _grab(PY_SRC, r'_chained_keyframes\("alpha", start_ms, exit_start_ms, 350, \["&H([0-9A-F]+)&"', str)
    js_dim = _grab(JS_SRC, r"HOOK_DIM_OPACITY = 1 - 0x([0-9A-Fa-f]+) / 255", str)
    assert _ass_alpha_opacity(py_dim) == _ass_alpha_opacity(js_dim)

    py_sweep = _grab(PY_SRC, r"_hook_lightsweep_event.*?\\\\alpha&H([0-9A-F]+)&", str)
    js_sweep = _grab(JS_SRC, r"HOOK_SWEEP_OPACITY = 1 - 0x([0-9A-Fa-f]+) / 255", str)
    assert _ass_alpha_opacity(py_sweep) == _ass_alpha_opacity(js_sweep)


def test_hook_motion_envelope_has_no_double_fading():
    """
    Hook text lines must derive alpha purely from (inFx.alpha * loopFx.alpha * outFx.alpha)
    without an unmodeled artificial 300ms exit ramp or 200ms entry ramp that
    distorts parity with the ASS render.
    """
    assert "ctx.globalAlpha = (inFx.alpha ?? 1) * (loopFx.alpha ?? 1) * (outFx.alpha ?? 1);" in JS_SRC
    assert "ctx.globalAlpha = (outFx.alpha ?? 1) * HOOK_SWEEP_OPACITY;" in JS_SRC
    assert "if (t < 0.2) alpha =" not in JS_SRC
    assert "if (t > hookDuration - 0.3) alpha =" not in JS_SRC


def test_accent_reveal_anchors_wipe_from_left_edge():
    """
    In ASS, \an7 anchors the drawing top-left so \fscx0 -> \fscx100 wipes
    from left to right. The canvas preview must anchor its fillRect at the left
    edge (x - fullBw / 2 for badge, x - modelLineWidth / 2 for bar), not
    expanding symmetrically from the center.
    """
    assert "ctx.fillRect(x - fullBw / 2, modelTopY - padY, bw, modelFontSize + padY * 2);" in JS_SRC
    assert "ctx.fillRect(barX, barY, w, thickness);" in JS_SRC
    assert "const barX = x - modelLineWidth / 2;" in JS_SRC


# ---------------------------------------------------------------- shapes
@pytest.mark.parametrize(
    "name, py_pattern, js_pattern",
    [
        ("bar thickness", r"thickness = max\(4, round\(model_line_fs \* ([\d.]+)\)\)",
         r"thickness = Math\.max\(4, Math\.round\(modelFontSize \* ([\d.]+)\)\)"),
        ("bar gap", r"gap = round\(model_line_fs \* ([\d.]+)\)",
         r"gap = Math\.round\(modelFontSize \* ([\d.]+)\)"),
        ("badge padX", r"pad_x = round\(model_line_fs \* ([\d.]+)\)",
         r"padX = Math\.round\(modelFontSize \* ([\d.]+)\)"),
        ("badge padY", r"pad_y = round\(model_line_fs \* ([\d.]+)\)",
         r"padY = Math\.round\(modelFontSize \* ([\d.]+)\)"),
        ("accent reserve bar", r"reserve = ([\d.]+) if motion\[.accent.\] != .badge.",
         r"settledFs \* \(motion\.accent === 'badge' \? [\d.]+ : ([\d.]+)\)"),
        ("accent reserve badge", r"reserve = [\d.]+ if motion\[.accent.\] != .badge. else ([\d.]+)",
         r"settledFs \* \(motion\.accent === 'badge' \? ([\d.]+)"),
        ("sweep band width", r"band_w = max\(20, int\(half_w \* ([\d.]+)\)\)",
         r"bandW = Math\.max\(10, s\.halfW \* ([\d.]+)\)"),
        ("out zoom grow", r"grown = round\(target \* ([\d.]+)\)",
         r"scale: hookKeyframeAt\(\(t - s\) \* 1000, \[\[0, 1\], \[\(e - s\) \* 1000, ([\d.]+)\]\]\)"),
        ("in slide dy", r"return tag, end_ms, (\d+)  # slides up",
         r"dy: hookKeyframeAt\(ms, \[\[0, (\d+)\], \[300, 0\]\]\)"),
    ],
)
def test_shape_and_motion_factors_match(name, py_pattern, js_pattern):
    assert _grab(PY_SRC, py_pattern) == _grab(JS_SRC, js_pattern), name


def test_outline_widths_match():
    """
    An ASS Outline grows outward only; a canvas strokeText centres its
    stroke. Copying the number across without doubling for that difference
    drew the preview's outlines roughly twice as heavy as the render's.
    """
    ass_hook_outline = float(_grab(PY_SRC, r"Style: HookHeader,[^\n]*?,1,([\d.]+),0,8", str))
    canvas_hook_stroke = _grab(JS_SRC, r"const HOOK_OUTLINE_PX = (\d+);")
    assert canvas_hook_stroke == ass_hook_outline  # 6.0 render px == 6 canvas px of centred stroke

    ass_min, ass_ratio = (
        _grab(PY_SRC, r"front_outline = round\(max\(([\d.]+), font_size \* [\d.]+\), 1\)"),
        _grab(PY_SRC, r"front_outline = round\(max\([\d.]+, font_size \* ([\d.]+)\), 1\)"),
    )
    js_min, js_ratio = (
        _grab(JS_SRC, r"return Math\.max\(([\d.]+), canvasFontSize \* 2 \* [\d.]+\)"),
        _grab(JS_SRC, r"return Math\.max\([\d.]+, canvasFontSize \* 2 \* ([\d.]+)\)"),
    )
    assert (ass_min, ass_ratio) == (js_min, js_ratio)


def test_sweep_band_travels_the_same_distance():
    """
    The renderer sweeps the band's left edge from (centre - halfW - bandW)
    to (centre + halfW - bandW): a travel of exactly 2 * halfW. A preview
    that also adds bandW runs the shimmer past the end of the text.
    """
    assert "phase * (s.halfW * 2)" in JS_SRC


def test_rotation_presets_never_use_wrapped_angles():
    """
    \\t interpolates toward its target, so -3 written as 357 sweeps the long
    way through 180 and flips the line over mid-step.
    """
    for angle in re.findall(r'"(-?\d+)"', _grab(PY_SRC, r"def _loop_wave.*?(\[.*?\])", str) +
                            _grab(PY_SRC, r"def _loop_shake.*?(\[.*?\])", str) +
                            _grab(PY_SRC, r"def _out_glitch.*?(\[.*?\])", str)):
        assert abs(int(angle)) <= 45, f"wrapped angle {angle} will spin the line"


def test_text_overlay_positions_and_styles_match():
    """
    Text Overlay Y coordinates and font size ratios must match between ASS and Canvas 2D.
    """
    assert _grab(PY_SRC, r'TEXT_OVERLAY_POSITIONS\s*=\s*\{[^}]*?"top":\s*([\d.]+)') == \
           _grab(JS_SRC, r'TEXT_OVERLAY_Y\s*=\s*\{[^}]*?top:\s*([\d.]+)')
    assert _grab(PY_SRC, r'TEXT_OVERLAY_POSITIONS\s*=\s*\{[^}]*?"middle":\s*([\d.]+)') == \
           _grab(JS_SRC, r'TEXT_OVERLAY_Y\s*=\s*\{[^}]*?middle:\s*([\d.]+)')
    assert _grab(PY_SRC, r'TEXT_OVERLAY_POSITIONS\s*=\s*\{[^}]*?"bottom":\s*([\d.]+)') == \
           _grab(JS_SRC, r'TEXT_OVERLAY_Y\s*=\s*\{[^}]*?bottom:\s*([\d.]+)')


def test_text_overlay_pill_badge_parity():
    """
    Pill badge background must use vector drawing (never BorderStyle=3 box),
    and padding / opacity / radius metrics must match between Canvas 2D and ASS.
    """
    # 1. TextOverlayMain must use BorderStyle=1 (outline mode), NEVER 3 (opaque box)
    style_line = _grab(PY_SRC, r"Style:\s*TextOverlayMain,([^\n]+)", str)
    # Format: Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, ...
    style_parts = [p.strip() for p in style_line.split(",")]
    assert style_parts[14] == "1", f"TextOverlayMain BorderStyle must be 1, got {style_parts[14]}"

    # 2. Pill padding factors must match between Python and JS
    py_padx = _grab(PY_SRC, r"pad_x\s*=\s*round\(render_fs\s*\*\s*([\d.]+)\)")
    js_padx = _grab(JS_SRC, r"padX\s*=\s*Math\.round\(renderFs\s*\*\s*([\d.]+)\)")
    assert py_padx == js_padx == 0.6

    py_pady = _grab(PY_SRC, r"pad_y\s*=\s*round\(render_fs\s*\*\s*([\d.]+)\)")
    js_pady = _grab(JS_SRC, r"padY\s*=\s*Math\.round\(renderFs\s*\*\s*([\d.]+)\)")
    assert py_pady == js_pady == 0.35

    # 3. Canvas 2D opacity 0.65 -> ASS alpha 1 - 0.65 = 0.35 -> round(0.35 * 255) = 89 = 0x59
    assert "\\alpha&H59&" in PY_SRC
    assert "rgba(0, 0, 0, 0.65)" in JS_SRC

