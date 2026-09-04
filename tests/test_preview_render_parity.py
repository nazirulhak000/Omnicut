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
import sys
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



# ------------------------------------------------- per-clip field survival
EDITOR_SRC = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
VIDEO_EDITOR_SRC = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")


def _render_clip_fields():
    """Every per-clip key the renderer reads, straight from its own source."""
    fields = set(re.findall(r'clip\.get\("([a-z_]+)"', VIDEO_EDITOR_SRC))
    fields |= set(re.findall(r'clip\["([a-z_]+)"\]', VIDEO_EDITOR_SRC))
    # frame_geometry reads pan_x/pan_y through a loop variable, and the eq
    # filter reads the colour keys out of EQ_LIMITS the same way
    fields |= {"pan_x", "pan_y"}
    fields |= set(re.findall(r'^\s+"([a-z]+)": \(', _grab(VIDEO_EDITOR_SRC, r"EQ_LIMITS = \{(.*?)\}", str), re.M))
    return fields - {"source_path"}


def test_editor_preserves_every_field_the_renderer_reads():
    """
    The editor used to rebuild each clip from an explicit field list on load,
    so anything the renderer understood but that list didn't mention was
    dropped -- and the autosave then wrote the stripped clip back, destroying
    it in the manifest. That is how a punch-zoom written by pipeline.py
    vanished and left the render zoomed while the preview drew flat.

    Spreading the stored clip keeps unknown fields alive, so this asserts the
    spread is there rather than trying to enumerate fields the editor never
    needs to know about individually.
    """
    load_block = EDITOR_SRC.split("const clips = rawClips.map(")[1].split("}));")[0]
    assert "...c," in load_block, (
        "clip load must spread the stored clip; listing fields explicitly "
        "silently drops everything the renderer reads but the editor doesn't"
    )
    # and the save path must not re-strip them
    for serialise in re.findall(r"clipList\.map\(\(\{([^}]*)\}\)", EDITOR_SRC):
        dropped = {f.strip() for f in serialise.split(",") if f.strip() and "..." not in f}
        leaked = dropped & _render_clip_fields()
        assert not leaked, f"save path drops fields the renderer reads: {leaked}"


@pytest.mark.parametrize("field", sorted(_render_clip_fields()))
def test_every_render_clip_field_is_visible_somewhere_in_the_editor(field):
    """
    A field that changes the rendered picture but appears nowhere in the
    editor is invisible state: the user cannot see it, cannot change it, and
    cannot tell why the export differs from the preview. Each one has to be
    drawn in the preview, or at minimum exposed in the Inspector.
    """
    preview_src = JS_SRC
    inspector_src = (ROOT / "frontend" / "src" / "components" / "editor" / "Inspector.jsx").read_text(encoding="utf-8")
    seen = field in preview_src or field in inspector_src
    assert seen, f"'{field}' affects the render but is neither drawn nor editable"


# ------------------------------------------------------- transition filling
def test_all_cut_transitions_are_treated_as_undecided():
    """
    The tiered auto-wiring only runs when the pipeline cuts the shots itself,
    so once a project had been opened in the editor -- which always sends a
    clip_list plus a transitions array built from its own all-cut default --
    it could never regain transitions. A real project sat at 21 boundaries,
    21 hard cuts, with no path back.

    An array that is entirely "cut" therefore means "nothing decided yet" and
    gets filled; one non-cut entry marks the whole array as deliberate.
    """
    src = (ROOT / "scripts" / "pipeline.py").read_text(encoding="utf-8")
    assert "_every_boundary_is_a_cut" in src
    assert "boundary_count and _every_boundary_is_a_cut(transitions)" in src

    # the filler must also stamp the clips, since the editor reads those
    filler = src.split("if boundary_count and _every_boundary_is_a_cut(transitions):")[1].split("# Opt-in LUT")[0]
    assert 'clip["transition_in"]' in filler
    assert 'clip["transition_duration"]' in filler

    # and the tiered path must never fall back to a bare cut any more
    tiered = src.split("if tone == \"major\":")[1].split("if not transitions")[0]
    assert '"cut"' not in tiered, "auto-wiring still has a hard-cut fallback"


def test_transitions_follow_the_framing_and_never_repeat():
    """
    A fixed pattern (fade everywhere, dissolve every fourth) reads as
    automated. The boundary effect should follow what the framing does across
    it, and the same effect must not land twice in a row.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.pipeline import choose_transition

    # pushing in vs pulling back get opposite-reading effects
    assert choose_transition(1.0, 1.3, 0)["type"] == "circleopen"
    assert choose_transition(1.3, 1.0, 0)["type"] == "circleclose"

    # a boundary the framing barely crosses still gets something deliberate
    assert choose_transition(1.1, 1.1, 0)["type"].startswith(("slide", "fade"))

    # never the same effect twice running
    picks, previous = [], None
    for i, (a, b) in enumerate([(1.0, 1.3), (1.3, 1.6), (1.6, 1.0), (1.0, 1.0), (1.0, 1.0)]):
        p = choose_transition(a, b, i, previous)
        previous = p["type"]
        picks.append(p["type"])
    assert all(picks[i] != picks[i - 1] for i in range(1, len(picks))), picks

    # and a cut is never a valid answer -- every boundary gets an effect
    assert "cut" not in picks


def test_transitions_do_not_shorten_the_video_against_the_audio():
    """
    A transition overlaps its two clips, so the finished video runs shorter
    than the clips add up to -- by the sum of every transition. The shots are
    cut to match the voiceover exactly, so putting a transition on all 12
    boundaries of a real clip left the picture ending 3.1s before the audio
    and subtitles did. Each outgoing clip has to get that time back.
    """
    src = (ROOT / "scripts" / "pipeline.py").read_text(encoding="utf-8")
    block = src.split("# A transition overlaps its two clips")[1].split("# Opt-in LUT")[0]
    assert 'clip["duration"] = round(float(clip.get("duration") or 0.0) + overlap, 3)' in block
    assert 'clip["trim_end"]' in block, "the source out-point has to move too"
    assert 'kind == "cut"' in block, "a plain cut costs no time and must be skipped"

    # arithmetic: compensating each boundary restores the original length
    clips = [{"duration": 2.0, "trim_end": 2.0} for _ in range(5)]
    transitions = [{"type": "fade", "duration": 0.25} for _ in range(4)]
    audio = sum(c["duration"] for c in clips)          # shots were cut to the voiceover
    for i, b in enumerate(transitions):
        clips[i]["duration"] += b["duration"]
        clips[i]["trim_end"] += b["duration"]
    rendered = sum(c["duration"] for c in clips) - sum(b["duration"] for b in transitions)
    assert abs(rendered - audio) < 1e-6, f"video {rendered} vs audio {audio}"


def test_voice_engine_records_what_actually_ran():
    """
    render_params only ever stored the engine that was REQUESTED, so a Gemini
    TTS failure silently swapped the whole clip to Edge-TTS with nothing
    anywhere saying so -- the giveaway was the wav being 44.1kHz stereo
    instead of Gemini's 24kHz mono.
    """
    src = (ROOT / "scripts" / "pipeline.py").read_text(encoding="utf-8")
    assert '"voice_engine_used": voice_engine_used' in src
    assert 'voice_engine_used = "edge_tts"' in src, "the fallback must record itself"
    assert "ลองใหม่อีกครั้ง" in src, "one transient failure should not decide the voice"


def test_every_transition_has_its_own_timeline_glyph():
    """
    The timeline drew the same Waves icon for every boundary, so the strip
    said only "something happens here" -- not which effect, and not whether
    two neighbouring boundaries differed. Each id needs its own glyph, and no
    two ids may share one or the strip is still ambiguous.
    """
    icons_src = (ROOT / "frontend" / "src" / "lib" / "transitionIcons.jsx").read_text(encoding="utf-8")
    mapped = dict(re.findall(r"^  (\w+): (\w+),$", icons_src, re.M))

    js_math = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").read_text(encoding="utf-8")
    catalog = set(re.findall(r"\{ id: '([a-z]+)'", js_math)) | {"cut"}

    missing = catalog - set(mapped)
    assert not missing, f"transitions with no glyph of their own: {sorted(missing)}"

    duplicates = [g for g in set(mapped.values()) if list(mapped.values()).count(g) > 1]
    assert not duplicates, f"glyph reused across different transitions: {duplicates}"

    # and the timeline must actually use the map rather than a fixed icon
    timeline_src = (ROOT / "frontend" / "src" / "components" / "editor" / "Timeline.jsx").read_text(encoding="utf-8")
    assert "<TransitionIcon type={currentTransition}" in timeline_src


# ------------------------------------------------------------------ audio
# The preview no longer plays a baked mix: pipeline.py skips the mix unless a
# video is actually being exported, and SequencePlayer.jsx plays the same stems
# the renderer will mix (voice element + looped BGM element + one
# AudioBufferSourceNode per SFX). Every level and every fire time therefore has
# to agree with sfx_manager.py's ffmpeg graph, or "it sounded right in the
# preview" stops meaning anything.
SFX_SRC = (ROOT / "scripts" / "sfx_manager.py").read_text(encoding="utf-8")
CONFIG_SRC = (ROOT / "scripts" / "config.py").read_text(encoding="utf-8")


def _js_audio_mix(field):
    return _grab(JS_SRC, rf"AUDIO_MIX = \{{.*?{field}: ([\d.]+)")


def test_stem_gains_match_the_mix():
    """voice/BGM/SFX levels are the mix's own defaults, not preview guesses."""
    assert _js_audio_mix("VOICE_GAIN") == _grab(CONFIG_SRC, r"VOICE_VOLUME = ([\d.]+)")
    assert _js_audio_mix("BGM_GAIN") == _grab(CONFIG_SRC, r"BGM_VOLUME = ([\d.]+)")
    assert _js_audio_mix("SFX_GAIN") == _grab(CONFIG_SRC, r"SFX_VOLUME = ([\d.]+)")
    # ...and the mix takes its defaults from that same place, rather than
    # repeating the literals as it used to while config.py said something else.
    for param, const in (("bgm_vol", "BGM_VOLUME"), ("voice_vol", "VOICE_VOLUME"), ("sfx_vol", "SFX_VOLUME")):
        assert re.search(rf"{param}: float = {const}", SFX_SRC), \
            f"{param} should default to config.{const}"


def test_sfx_pre_roll_matches_and_reads_the_resolved_filename():
    """
    A transition whoosh starts 120ms early so its peak lands on the cut. The
    render decides that from the resolved *filename*, so the preview must be
    handed the filename too -- a cue tagged with a legacy alias ("whoosh")
    resolves to sfx_whoosh_fast.wav, and testing the tag alone would still
    work by luck while "boom" -> sfx_vine_boom.wav would not.
    """
    assert _js_audio_mix("SFX_PRE_ROLL") == _grab(SFX_SRC, r"pre_roll = ([\d.]+) if is_transition_sfx")
    assert _js_audio_mix("SFX_MIN_TIME") == _grab(SFX_SRC, r"delay_ms = int\(max\(([\d.]+),")

    py_words = re.search(r'is_transition_sfx = any\(w in sfx_name_low for w in \[(.*?)\]', SFX_SRC, re.S)
    js_words = re.search(r"TRANSITION_SFX_WORDS = \[(.*?)\]", JS_SRC, re.S)
    assert py_words and js_words
    assert re.findall(r"[a-z]+", py_words.group(1)) == re.findall(r"[a-z]+", js_words.group(1))

    # ...and the preview is given entry.name (the file), not just the cue tag.
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert "name: entry.name" in shell, "SFX pre-roll needs the resolved filename, not the cue tag"


def test_sfx_fire_time_floors_to_whole_milliseconds_like_adelay():
    """
    adelay takes integer milliseconds (int(secs * 1000)), so the preview floors
    the same way instead of keeping float seconds -- otherwise the two disagree
    by a sub-millisecond step that grows into a visible mismatch on report.
    """
    assert "int(max(" in SFX_SRC and "* 1000)" in SFX_SRC
    assert re.search(r"Math\.floor\(secs \* 1000\) / 1000", JS_SRC), \
        "sfxFireTime must floor to ms to match adelay"


def test_bgm_tail_fade_and_tempo_clamp_match():
    assert _js_audio_mix("BGM_FADE_OUT") == _grab(SFX_SRC, r"afade=t=out:st=\{fade_start:.3f\}:d=([\d.]+)")
    assert _js_audio_mix("BGM_TEMPO_BASELINE") == _grab(SFX_SRC, r"BASELINE_CHARS_PER_SEC = ([\d.]+)")
    py_clamp = re.search(r"tempo_ratio = min\(([\d.]+), max\(([\d.]+),", SFX_SRC)
    js_clamp = re.search(r"return Math\.min\(([\d.]+), Math\.max\(([\d.]+),", JS_SRC)
    assert py_clamp and js_clamp
    assert py_clamp.groups() == js_clamp.groups()


def test_ducking_uses_the_measured_reduction_not_a_feel_value():
    """
    WebAudio has no sidechain, so the preview stands in a plain gain envelope.
    sfx_manager.py records that its threshold/ratio were chosen by measuring
    13.7 dB of reduction -- the preview's factor must be that same figure in
    linear gain, and its attack/release must be the filter's own.
    """
    measured_db = _grab(SFX_SRC, r"pull the music down ([\d.]+) dB")
    assert abs(_js_audio_mix("BGM_DUCK_GAIN") - 10 ** (-measured_db / 20)) < 0.002
    assert _js_audio_mix("BGM_DUCK_ATTACK") * 1000 == _grab(SFX_SRC, r"attack=(\d+)")
    assert _js_audio_mix("BGM_DUCK_RELEASE") * 1000 == _grab(SFX_SRC, r"release=(\d+)")


def test_bgm_loops_and_is_speed_matched_on_both_sides():
    assert "-stream_loop" in SFX_SRC and "atempo=" in SFX_SRC
    assert re.search(r"src=\{audioStems\.bgm\.url\}[\s\S]{0,200}?loop", JS_SRC), \
        "BGM element must loop to match -stream_loop -1"
    assert re.search(r"bgm\.playbackRate = audioLiveRef\.current\.bgmRate", JS_SRC),         "BGM must be speed-matched like atempo, from the live tempo"


def test_preview_resolves_the_same_bgm_file_the_render_will_use():
    """
    The picker sends a registry id ("bgm_brass_funk") while resolve_bgm_path
    starts from a filename, so an id-only lookup silently landed on the
    alphabetically-first track: the user picked one bed and rendered another.
    Both sides now resolve ids, and both fall back the same way.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.asset_registry import AssetRegistry
    from scripts.sfx_manager import SFXManager

    beds = AssetRegistry.bgm()
    if len(beds) < 2:
        pytest.skip("needs at least two BGM files to tell a fallback from a hit")
    for entry in beds:
        resolved = SFXManager.resolve_bgm_path(entry["id"])
        assert resolved and resolved.name == entry["name"], \
            f"{entry['id']} resolved to {resolved} instead of its own file"

    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert "m.id === style.bgmName || m.name === style.bgmName" in shell
    default_py = re.search(r'name = bgm_name or "([^"]+)"', SFX_SRC).group(1)
    assert f"DEFAULT_BGM_FILE = '{default_py}'" in shell, \
        "preview must fall back to the same default bed as resolve_bgm_path"


def test_legacy_sfx_aliases_match_on_both_sides():
    """An old manifest saying "boom" must reach the same file in both places."""
    sys.path.insert(0, str(ROOT))
    from scripts.asset_registry import LEGACY_SFX_ALIASES

    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    js_block = re.search(r"LEGACY_SFX_ALIASES = \{(.*?)\}", shell, re.S).group(1)
    js_pairs = dict(re.findall(r"(\w+): '([^']+)'", js_block))
    assert js_pairs == LEGACY_SFX_ALIASES


def test_preview_lays_down_the_boom_the_mix_always_adds():
    """The mix puts a boom on the hook at t=0 whether or not a cue asked."""
    assert "# 2. Add Boom on 0.0s Hook" in SFX_SRC
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert re.search(r"sfxShots\.push\(\{ time: 0, id: 'boom'", shell), \
        "preview must start with the same boom the mix does"


def test_seeking_stops_the_stems_before_repositioning_them():
    """
    seekTo used to pause the videos but leave the audio playing and isPlaying
    set, so a drag issued a seek per frame while the last was still pending,
    the element lagged, and the tick kept reading its stale currentTime as the
    master clock -- the playhead snapped back under the cursor. Stopping first
    also drops queued SFX so they do not re-fire on the way back over a cue.
    """
    seek = re.search(r"const seekTo = \(t\) => \{(.*?)\n  \};", JS_SRC, re.S)
    assert seek, "seekTo moved"
    body = seek.group(1)
    assert "stopStems()" in body and "cueStemsTo(clamped)" in body
    assert body.index("stopStems()") < body.index("cueStemsTo(clamped)")
    assert "if (isPlaying) startStems()" in body


def test_a_late_decoded_one_shot_is_offset_not_played_from_its_start():
    """
    The first pass over a cue is the one that has to wait for a fetch, so a
    buffer can resolve after its moment has passed. WebAudio would then play it
    from sample zero, i.e. audibly late -- so it starts that far into the
    buffer instead, and is abandoned entirely past SFX_LATE_LIMIT.
    """
    assert re.search(r"const late = ctx\.currentTime - when;", JS_SRC)
    assert re.search(r"if \(late > AUDIO_MIX\.SFX_LATE_LIMIT \|\| late > buf\.duration\) return;", JS_SRC)
    assert re.search(r"if \(late > 0\) src\.start\(ctx\.currentTime, late\);", JS_SRC)
    # ...and buffers are warmed as soon as the graph exists so this is the rare
    # path, not the normal one.
    assert "forEach((shot) => loadSfxBuffer(ctx, shot.url))" in JS_SRC


def test_a_fired_one_shot_is_not_rescheduled_while_still_in_its_window():
    """
    A 200ms SFX ends well inside the 500ms lookahead. Clearing its entry on
    `ended` (as the first cut did) let the next tick schedule it again --
    every short SFX double-fired. Entries now live until flushSfx.
    """
    assert "src.onended = () => { entry.node = null; };" in JS_SRC
    assert not re.search(r"onended[\s\S]{0,80}sfxLiveRef\.current = sfxLiveRef\.current\.filter", JS_SRC)


def test_swapping_a_stem_mid_playback_rewires_instead_of_going_silent():
    """
    Each audio element is keyed by URL, so choosing another BGM mounts a fresh
    element the AudioContext has never been given -- without this it plays
    nothing until the user presses play again, and the dead source node stays
    in the map.
    """
    fx = re.search(r"// Swapping BGM(.*?)\}, \[audioStems\?\.voiceUrl, audioStems\?\.bgm\?\.url\]\);", JS_SRC, re.S)
    assert fx, "re-wire effect missing"
    body = fx.group(1)
    assert "ensureAudioGraph()" in body and "startStems()" in body
    assert "src.disconnect()" in body and "mediaSourcesRef.current.delete(el)" in body


def test_mid_playback_audio_changes_reach_the_tick_loop():
    """
    The tick effect re-subscribes on only a few deps, so a BGM level or a new
    SFX read straight from a closure would be a frame from before the change --
    and the stale level would fight the gain effect back down. Everything the
    loop reads goes through audioLiveRef.
    """
    assert "audioLiveRef.current = { bgmVolume, bgmDucking, bgmRate, totalDuration, cues, shots: sfxShots }" in JS_SRC
    tick = re.search(r"const tick = \(\) => \{(.*?)\n      rafRef", JS_SRC, re.S).group(1)
    for stale in ("bgmVolume", "bgmDucking", "sfxShots"):
        assert stale not in tick, f"tick reads {stale} from a stale closure"


def test_audio_and_video_elements_are_torn_down_on_unmount():
    """
    Nothing released media before: elements kept decoding and every editor
    visit leaked an AudioContext (browsers cap how many may exist).
    """
    teardown = re.search(r"// Teardown:(.*?)\n  \}, \[\]\);", JS_SRC, re.S)
    assert teardown, "teardown effect missing"
    body = teardown.group(1)
    for expected in ("flushSfx()", "el.pause()", "removeAttribute('src')", "audioCtxRef.current?.close()"):
        assert expected in body, f"teardown does not {expected}"
