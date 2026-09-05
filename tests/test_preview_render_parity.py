"""
Preview/render source-contract guard.

The canvas preview (SequencePlayer.jsx) and the ASS renderer
(subtitle_engine.py) are two independent implementations of the same
picture. Every constant they must agree on is asserted here by reading it
out of each source file, so a change to one side that isn't mirrored on the
other fails here instead of shipping as "the preview lied about the render".

Values marked "measured" were taken off a real ffmpeg+libass render rather
than derived, and the comment says what was measured.

Black-box FFmpeg checks live in test_preview_render_behavior.py so a source
layout change and a real output change can be diagnosed independently.
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY_SRC = ""
for _sub in sorted((ROOT / "scripts" / "subtitle").glob("*.py")):
    PY_SRC += _sub.read_text(encoding="utf-8") + "\n"
PY_SRC += (ROOT / "scripts" / "subtitle_engine.py").read_text(encoding="utf-8")
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
    # The banner's ratio rides on the overlay now (base_fs_ratio), so the
    # canvas reads it off the item; the number itself is asserted equal on
    # both sides in test_overlay_geometry_constants_match_on_both_sides.
    assert "Math.round(CANVAS_W * (overlay.base_fs_ratio || TEXT_FS_RATIO))" in JS_SRC
    assert _grab(PY_SRC, r"hook_fs = int\(round\(video_width \* ([\d.]+)\)\)") == \
           _grab(OVERLAY_PY, r"\nHOOK_FS_RATIO = ([\d.]+)\n")
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
    # The banner has its own face now, so it needs the boost of THAT face: a
    # font's line box against its em is what the boost cancels, and reusing the
    # caption's number would size the banner by the wrong metrics.
    assert "HOOK_SCALE_BOOST = 1.0 / ass_glyph_scale(hook_font)" in PY_SRC

    # every text scale that reaches \fscx carries the boost
    for probe in [
        "target = round(layout_pct * HOOK_SCALE_BOOST)",       # hook tiers, in the hook's own face
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
    assert "localTime: localTimeAt(prevSeg, t), alpha: 1, role: 'out'" in js_math


def test_hook_block_top_is_the_same_fraction_of_frame_height():
    # The anchor is a field on the overlay now (HOOK_TOP_Y), and the canvas
    # positions every overlay from it rather than a literal 130.
    ass_top = _grab(PY_SRC, r"cursor_y = (\d+)  # HookHeader") / 1920
    assert ass_top == 260.0 / 1920.0
    assert "HOOK_TOP_Y = 260.0 / 1920.0" in OVERLAY_JS
    assert "overlay.anchor === ANCHOR_TOP" in JS_SRC


def test_tier_scales_and_shrink_rule_match():
    assert re.findall(r"\(hook_\w+, (\d+), \w+_colour, \d\)", PY_SRC) == \
           re.findall(r"sizePct: (\d+)", JS_SRC)
    assert _grab(PY_SRC, r"HOOK_COMFORTABLE_LINES = (\d+)") == \
           _grab(OVERLAY_JS, r"HOOK_COMFORTABLE_LINES = (\d+);")


# ---------------------------------------------------------------- timing
def test_stagger_and_exit_windows_match():
    assert _grab(PY_SRC, r"STAGGER_STEP_MS = (\d+)") == \
           _grab(JS_SRC, r"HOOK_STAGGER_STEP = ([\d.]+)") * 1000
    assert _grab(PY_SRC, r"exit_start_ms = max\(120, exit_end_ms - (\d+)\)") == \
           _grab(JS_SRC, r"exitStartSec = Math\.max\(0\.12, duration - ([\d.]+)\)") * 1000


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
    assert "ctx.fillRect(x - fullBw / 2, modelLine.y - padY, bw, modelFontSize + padY * 2);" in JS_SRC
    assert "ctx.fillRect(barX, barY, w, thickness);" in JS_SRC
    assert "const barX = x - modelLine.width / 2;" in JS_SRC


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
    # The banner's outline is per tier now, out of the template table, so the
    # number itself is asserted where it lives -- see
    # test_hook_templates_are_identical_on_both_sides. What still has to hold
    # here is that both sides read that same field, and neither doubles it.
    assert "ctx.lineWidth = w.look.outline_px;" in JS_SRC
    assert "bord{float(tier_style['outline_px']):.1f}" in PY_SRC

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
    # The table lives in the shared model now; the canvas reads TEXT_POSITIONS
    # from it rather than keeping a second copy that could drift.
    for key in ("top", "middle", "bottom"):
        assert _grab(PY_SRC, rf'TEXT_OVERLAY_POSITIONS\s*=\s*\{{[^}}]*?"{key}":\s*([\d.]+)') == \
               _grab(OVERLAY_PY, rf'TEXT_POSITIONS[^=]*=\s*\{{[^}}]*?"{key}":\s*([\d.]+)') == \
               _grab(OVERLAY_JS, rf'TEXT_POSITIONS\s*=\s*\{{[^}}]*?{key}:\s*([\d.]+)')
    assert "TEXT_POSITIONS[overlay.position" in JS_SRC


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

    # 2. The padding is a property of the pill now, so both sides read the
    #    same em multiples off the look instead of hardcoding a pair each.
    assert _grab(PY_SRC, r'pad_x = round\(render_fs \* float\(pill\.get\("pad_x_em"\) or ([\d.]+)\)\)') == \
           _grab(OVERLAY_PY, r"\nPILL_PAD_X_EM = ([\d.]+)\n") == 0.6
    assert _grab(PY_SRC, r'pad_y = round\(render_fs \* float\(pill\.get\("pad_y_em"\) or ([\d.]+)\)\)') == \
           _grab(OVERLAY_PY, r"\nPILL_PAD_Y_EM = ([\d.]+)\n") == 0.35
    assert 'pill.pad_x_em ?? PILL_PAD_X_EM' in JS_SRC
    assert 'pill.pad_y_em ?? PILL_PAD_Y_EM' in JS_SRC

    # 3. The badge's opacity comes off the fill the preview paints, instead of
    #    a hand-tuned \\alpha per named style. Dark glass is the one that used
    #    to agree: 0.65 opacity -> 1 - 0.65 = 0.35 -> round(0.35 * 255) = 0x59.
    sys.path.insert(0, str(ROOT))
    from scripts.overlay_model import LEGACY_BG_STYLES
    from scripts.subtitle_engine import _pill_fill_to_ass

    for name, preset in LEGACY_BG_STYLES.items():
        if not preset:
            continue
        _, opacity = _pill_fill_to_ass(preset["fill"])
        js_fill = _grab(OVERLAY_JS, rf"{name}: \{{ fill: '([^']+)'", str)
        assert js_fill == preset["fill"], f"{name}: python {preset['fill']!r} vs js {js_fill!r}"
        if name == "pill":
            assert round((1 - opacity) * 255) == 0x59

    # A pill can carry a border, which the writer had no way to say before --
    # the neon badge came back as a flat block without it.
    assert 'ass_colour(pill.get("border"))' in PY_SRC
    assert "if (pill.border) {" in JS_SRC



# ------------------------------------------------- per-clip field survival
EDITOR_SRC = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
PROJECT_STATE_SRC = (ROOT / "frontend" / "src" / "lib" / "editorProjectState.js").read_text(encoding="utf-8")
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
    clip_src = PROJECT_STATE_SRC if "sourceClips.map(" in PROJECT_STATE_SRC else EDITOR_SRC
    if "const clipList = sourceClips.map(" in clip_src:
        load_block = clip_src.split("const clipList = sourceClips.map(")[1].split("\n  });")[0]
        assert "...clip," in load_block, (
            "clip load must spread the stored clip; listing fields explicitly "
            "silently drops everything the renderer reads but the editor doesn't"
        )
    else:
        load_block = clip_src.split("const clips = rawClips.map(")[1].split("}));")[0]
        assert "...c," in load_block, (
            "clip load must spread the stored clip; listing fields explicitly "
            "silently drops everything the renderer reads but the editor doesn't"
        )
    # and the save path must not re-strip them
    for serialise in re.findall(r"clipList\.map\(\(\{([^}]*)\}\)", clip_src):
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
    rendered = sum(c["duration"] for c in clips) - sum(b["duration"] for c in transitions)
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
    # The default is one constant now, checked in
    # test_one_default_bgm_across_render_mix_and_editor; here it only matters
    # that the preview takes it from the server instead of keeping a copy.
    assert "name = bgm_name or DEFAULT_BGM" in SFX_SRC
    assert "m.id === assets.default_bgm || m.name === assets.default_bgm" in shell, \
        "preview must take the default from the server, not hold its own"


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
    live = re.search(r"audioLiveRef\.current = \{(.*?)\n  \};", JS_SRC, re.S)
    assert live, "the live ref moved"
    for field in ("bgmVolume", "bgmDucking", "bgmRate", "totalDuration", "cues", "shots: sfxShots"):
        assert field in live.group(1), f"the tick cannot see {field}"
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


# ------------------------------------------------------- transitions in preview
# Every boundary used to preview as a crossfade whatever it was, so a wipe, a
# slide and a circle looked identical until the file came out of ffmpeg. The
# geometry below was measured off real xfade renders (two inputs carrying their
# own coordinates in the red and blue channels), not guessed -- see
# .agents/rules/preview_render_parity.md section 7.
TIMELINE_MATH = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").read_text(encoding="utf-8")


def test_draw_plan_carries_the_boundary_type_and_progress():
    """The painter cannot do a wipe if the plan only says 'blend this much'."""
    assert "transition = seg.clip.transition_in || 'fade'" in TIMELINE_MATH
    assert "role: 'solo'" in TIMELINE_MATH
    # BOTH sides of a boundary need the type and the progress -- a slide moves
    # the outgoing clip too, so carrying it on the incoming entry alone leaves
    # the outgoing frame standing still under a sliding one.
    for role in ("out", "in"):
        assert re.search(rf"role: '{role}', transition, progress: alpha", TIMELINE_MATH),             f"the {role} entry does not carry the transition and progress"
    assert "Every transition type previews as a crossfade" not in TIMELINE_MATH, \
        "the crossfade-only note should be gone with the crossfade-only behaviour"


@pytest.mark.parametrize("kind,expected", [
    ("wipeleft", r"ctx\.rect\(\(1 - p\) \* CANVAS_W, 0, CANVAS_W, CANVAS_H\)"),
    ("wiperight", r"ctx\.rect\(0, 0, p \* CANVAS_W, CANVAS_H\)"),
    ("wipeup", r"ctx\.rect\(0, \(1 - p\) \* CANVAS_H, CANVAS_W, CANVAS_H\)"),
    ("wipedown", r"ctx\.rect\(0, 0, CANVAS_W, p \* CANVAS_H\)"),
])
def test_wipe_edges_match_the_measured_direction(kind, expected):
    """
    Measured at progress 0.5 on a 120x200 frame: wipeleft left the incoming
    clip holding x >= 61 (it enters from the right), wiperight x <= 60, wipeup
    y >= 101, wipedown y <= 100 -- and none of them displaced either clip.
    """
    block = re.search(rf"case '{kind}':(.*?)return true;", JS_SRC, re.S)
    assert block, f"{kind} is no longer mask-based"
    assert re.search(expected, block.group(1)), f"{kind} wipes the wrong way"


@pytest.mark.parametrize("kind,out_off,in_off", [
    ("slideleft", "-p * CANVAS_W, 0", "(1 - p) * CANVAS_W, 0"),
    ("slideright", "p * CANVAS_W, 0", "-(1 - p) * CANVAS_W, 0"),
    ("slideup", "0, -p * CANVAS_H", "0, (1 - p) * CANVAS_H"),
    ("slidedown", "0, p * CANVAS_H", "0, -(1 - p) * CANVAS_H"),
])
def test_slides_move_both_clips_as_one_strip(kind, out_off, in_off):
    """
    Measured: at progress 0.5 slideleft displaced the outgoing clip by -60px on
    a 120px-wide frame (-p*W) and the incoming clip entered from the right --
    the pair travels together, which is what separates a slide from a wipe.
    """
    line = re.search(rf"case '{kind}':\s*return \[\[(.*?)\], \[(.*?)\]\];", JS_SRC)
    assert line, f"{kind} missing from slideOffsets"
    assert line.group(1) == out_off and line.group(2) == in_off


def test_circles_use_the_measured_radial_curve():
    """
    Fitted against real frames at every progress from 0.1 to 0.9 and across the
    whole radius: the incoming clip's weight is
    smoothstep((1 - r/z) + 3*(progress - 0.5)) for circleopen, and the same
    with r/z for circleclose. Max error 0.017 of weight.
    """
    fn = re.search(r"function circleWeightAt\((.*?)\n\}", JS_SRC, re.S)
    assert fn
    body = fn.group(1)
    assert "3 * (p - 0.5)" in body, "the 3x progress term is what the fit needed"
    assert "SMOOTHSTEP((1 - dNorm) + shifted)" in body
    assert "SMOOTHSTEP(dNorm + shifted)" in body


def test_bridge_fades_dip_through_a_colour_instead_of_crossfading():
    """
    fadeblack/fadewhite are not crossfades: measured on a 30-frame transition,
    the outgoing frame is fully black by progress 0.167 and the incoming one
    only starts appearing around 0.267. Crossfading them showed both clips at
    once through the middle, which the render never does.
    """
    assert _grab(JS_SRC, r"FADE_BRIDGE_OUT = 1 / (\d)") == 6
    assert abs(_grab(JS_SRC, r"FADE_BRIDGE_IN = ([\d.]+)") - 0.2667) < 1e-6
    paint = re.search(r"if \(painted && role === 'out' && \(kind === 'fadeblack'(.*?)\n    \}", JS_SRC, re.S)
    assert paint, "the bridge colour is never laid down"
    assert "fadewhite' ? '#FFFFFF' : '#000000'" in paint.group(1)
    # Paint-order alpha: the colour goes over the outgoing clip, and the
    # incoming clip then blends over both -- so its cover has to be rescaled.
    assert "bridge / (1 - wB)" in paint.group(1)


def test_dissolve_reveals_per_pixel_and_never_goes_backwards():
    """
    Measured: the revealed share equals progress, no pixel ever reverts as
    progress grows, and the grain is per-pixel rather than blocky. ffmpeg's own
    pattern is not the common sin-hash (tested: 59% agreement, a coin flip), so
    the pixels differ while the character and the share match.
    """
    fn = re.search(r"function dissolveMaskFor\((.*?)\n\}", JS_SRC, re.S)
    assert fn
    body = fn.group(1)
    assert "1 - Math.max(0, Math.min(1, progress))" in body, "share must equal progress"
    assert "dissolveNoise[i] >= threshold" in body, "a fixed threshold keeps the reveal monotonic"
    assert "Uint32Array" in body, "per-pixel work needs the 32-bit write, not four 8-bit ones"


# --------------------------------------------------------------- colour grade
def test_the_filter_picker_resolves_to_a_real_file_on_both_sides():
    """
    The picker stores a registry id ("lut_warm_cozy_lifestyle") while the
    pipeline joined that id onto LUTS_DIR, where only the .cube filename
    exists -- so `lut_path` never existed, the grade was skipped without a
    word, and choosing a filter did nothing at all.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.asset_registry import AssetRegistry

    luts = AssetRegistry.luts()
    if not luts:
        pytest.skip("no LUTs installed")
    for entry in luts:
        for key in ("id", "name"):
            resolved = AssetRegistry.resolve_lut_path(entry[key])
            assert resolved and resolved.name == entry["name"], \
                f"{entry[key]} resolved to {resolved}"
    assert AssetRegistry.resolve_lut_path("does_not_exist") is None

    pipeline = (ROOT / "scripts" / "pipeline.py").read_text(encoding="utf-8")
    assert "AssetRegistry.resolve_lut_path(lut_name)" in pipeline
    assert "str(LUTS_DIR / lut_name)" not in pipeline, "the id-joined path is what was broken"

    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert "l.id === style.lutName || l.name === style.lutName" in shell


def test_preview_grades_at_the_same_point_in_the_chain_as_the_render():
    """
    The render applies lut3d before the sticker overlay and the subtitle burn,
    so a brand-coloured badge and the caption colours are never re-graded. The
    preview has to grade in the same place or those colours shift.
    """
    tick = re.search(r"if \(framePainted\) applyGrade\(ctx, canvas\);\s*\n\s*drawSticker", JS_SRC)
    assert tick, "the grade must run after the video layers and before the badge"
    still = re.search(r"applyGrade\(ctx, canvas\);\s*\n(?:\s*//[^\n]*\n)*\s*drawSticker", JS_SRC)
    assert still, "the paused frame must grade too, at the same point"

    editor = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    lut_at = editor.index("lut3d=")
    assert lut_at < editor.index("sticker_scaled"), "render order changed; preview order must follow"


def test_preview_layers_the_badge_scrim_and_subtitles_in_the_renders_order():
    """
    ffmpeg burns the badge, then the hook's gradient over it, then everything
    libass draws. The preview used to paint the gradient first of all and the
    badge after the banner, so a badge stayed bright in the editor and came
    back dimmed in the file, and the banner sat under a badge it renders over.
    """
    editor = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    assert editor.index("sticker_scaled") < editor.index("grad_alpha_") < editor.index("subtitles='")

    for block in re.findall(r"drawSticker\(ctx.*?boundsRef\.current = bounds;", JS_SRC, re.S):
        assert block.index("drawSticker(") < block.index("drawOverlayScrims("), block
        assert block.index("drawOverlayScrims(") < block.index("drawOverlays("), block


def test_partial_grade_strength_blends_the_same_way_as_the_render():
    """ffmpeg blends the graded frame over the original at all_opacity=strength."""
    editor = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    assert "blend=all_mode=normal:all_opacity={strength}" in editor
    lut_js = (ROOT / "frontend" / "src" / "lib" / "lut3d.js").read_text(encoding="utf-8")
    assert "mix(src.rgb, graded, uStrength)" in lut_js


def test_lut_sampling_matches_ffmpeg_on_every_installed_cube():
    """
    Grades a probe that visits the whole RGB cube with the preview's own
    parseCube + sampleLut and compares against ffmpeg's lut3d. Measured max
    difference across all four installed LUTs: 1 level out of 255.
    """
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("node") or not shutil.which("ffmpeg"):
        pytest.skip("needs node and ffmpeg")
    sys.path.insert(0, str(ROOT))
    from scripts.asset_registry import AssetRegistry

    luts = AssetRegistry.luts()
    if not luts:
        pytest.skip("no LUTs installed")

    n = 8
    levels = [round(i * 255 / (n - 1)) for i in range(n)]
    pixels = bytearray()
    for r in levels:
        for g in levels:
            for b in levels:
                pixels += bytes((r, g, b))
    width, height = n * n, n

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        raw = tmp / "probe.raw"
        raw.write_bytes(bytes(pixels))
        runner = tmp / "grade.mjs"
        lut_mod = (ROOT / "frontend" / "src" / "lib" / "lut3d.js").resolve().as_uri()
        runner.write_text(
            "import { readFileSync, writeFileSync } from 'node:fs';\n"
            f"import {{ parseCube, sampleLut }} from '{lut_mod}';\n"
            "const [,, cube, src, w, h, out] = process.argv;\n"
            "const lut = parseCube(readFileSync(cube, 'utf8'));\n"
            "const inp = readFileSync(src); const px = Number(w) * Number(h);\n"
            "const buf = Buffer.alloc(px * 3);\n"
            "for (let i = 0; i < px; i++) {\n"
            "  const v = sampleLut(lut, inp[i*3]/255, inp[i*3+1]/255, inp[i*3+2]/255);\n"
            "  for (let c = 0; c < 3; c++) buf[i*3+c] = Math.round(Math.min(1, Math.max(0, v[c])) * 255);\n"
            "}\n"
            "writeFileSync(out, buf);\n",
            encoding="utf-8",
        )

        for entry in luts:
            cube = Path(entry["path"])
            ff_out = tmp / "ff.raw"
            lut_arg = str(cube.resolve()).replace("\\", "/").replace(":", r"\:")
            subprocess.run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-i", str(raw),
                "-vf", f"lut3d='{lut_arg}'",
                "-f", "rawvideo", "-pix_fmt", "rgb24", str(ff_out),
            ], check=True)
            js_out = tmp / "js.raw"
            subprocess.run(["node", str(runner), str(cube), str(raw),
                            str(width), str(height), str(js_out)], check=True)
            a = ff_out.read_bytes()
            b = js_out.read_bytes()
            worst = max(abs(x - y) for x, y in zip(a, b))
            assert worst <= 3, f"{entry['id']} differs from ffmpeg by {worst}/255"


# ----------------------------------------------------------- per-clip audio
def test_clip_audio_is_placed_where_the_clip_sits_not_end_to_end():
    """
    Each clip's own audio was concatenated from zero instead of delayed to its
    timeline position. Clip volume defaults to 0, so the ordinary case --
    raising the volume on one clip in the middle -- played that clip's sound at
    the very start of the video. Verified on a real render: a middle clip's
    tone moved from 0.00s to its true 2.00s once delayed.
    """
    editor = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    block = editor[editor.index("if raw_audio_nodes:"):editor.index("final_audio_map = \"[a_final]\"")]
    assert "adelay=" in block, "clip audio must be delayed to its own start"
    assert "concat=n=" not in block, "concatenating lays every clip's audio from zero"
    assert "clip_starts[clip_idx]" in block
    assert "amix=inputs=" in block and "duration=longest" in block
    # The starts have to come from the same arithmetic as the video's xfade
    # offsets, or the audio and the picture disagree at every transition.
    assert "clip_starts.append(offset)" in editor
    assert "raw_audio_nodes.append((a_node, duration, idx))" in editor


def test_preview_plays_a_clips_own_audio_at_its_own_volume():
    """
    The decode elements are muted -- they exist for frames -- so a clip with
    volume > 0 was silent in the preview while the render mixed it in. The
    volume slider moved a number nothing could hear.
    """
    assert "muted={!(Number(c.volume) > 0)}" in JS_SRC
    fn = re.search(r"const wireClipAudio = \(\) => \{(.*?)\n  \};", JS_SRC, re.S)
    assert fn, "wireClipAudio missing"
    body = fn.group(1)
    assert "createMediaElementSource(el)" in body
    assert "entry.gain.gain.setTargetAtTime(vol" in body
    assert "clip: bus(trackLevel('clip'))" in JS_SRC
    assert "clip: AUDIO_MIX.CLIP_GAIN" in JS_SRC


def test_per_track_mute_and_solo_reach_the_gain_nodes():
    """Soloing one stem must silence the others, and solo has to beat mute."""
    assert "soloedTracks.length ? soloedTracks.includes(track) : !trackMix?.mute?.[track]" in JS_SRC
    base = re.search(r"const trackBase = \{(.*?)\};", JS_SRC, re.S)
    assert base, "the per-track levels moved"
    for track in ("voice", "bgm", "sfx", "clip"):
        assert f"{track}:" in base.group(1), f"{track} has no level in the track mix"
    assert "AUDIO_MIX.VOICE_GAIN" in base.group(1)
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert "if (kind === 'mute' && turningOn) next.solo[k] = false;" in shell
    assert "if (kind === 'solo' && turningOn) next.mute[k] = false;" in shell
    # Playback-only: soloing to check a level must never change what renders.
    payload_keys = re.findall(r"trackMix", shell)
    assert payload_keys, "trackMix state missing"
    assert "trackMix" not in re.sub(r"\s+", " ", shell[shell.index("bgm_ducking: !!style.bgmDucking"):][:2000])


def test_timeline_draws_one_lane_per_stem_from_the_stems_own_file():
    """
    The single waveform decoded the mixed file, which 1-Click no longer writes:
    the lane went blank with nothing to say why. Each stem now draws from its
    own file and carries its own mute/solo.
    """
    tl = (ROOT / "frontend" / "src" / "components" / "editor" / "Timeline.jsx").read_text(encoding="utf-8")
    stems = re.search(r"const STEMS = \[(.*?)\];", tl, re.S)
    assert stems
    assert [k for k in ("voice", "bgm", "sfx", "clip") if f"key: '{k}'" in stems.group(1)] == \
        ["voice", "bgm", "sfx", "clip"]
    assert "getAudioPeaks(url, WAVE_COLUMNS)" in tl
    assert "waveInfo" not in tl, "the merged-mix waveform should be gone"
    assert "onTrackMix?.(mixKey, 'mute')" in tl and "onTrackMix?.(mixKey, 'solo')" in tl


# ------------------------------------------------------------ timeline layout
# The label gutter and the lanes are two columns describing the same rows. They
# used to space themselves differently -- `gap-1` on the gutter against
# per-lane `mt-1` -- so any row that forgot its margin slid every label below it
# out from under its lane. With four audio lanes the drift reached 12px and the
# track names no longer sat beside their own waveforms.
TIMELINE_SRC = (ROOT / "frontend" / "src" / "components" / "editor" / "Timeline.jsx").read_text(encoding="utf-8")
SHELL_SRC = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")


def test_both_timeline_columns_take_their_geometry_from_one_row_list():
    """
    Every row's height and top margin comes from `rowStyle(key)`, which both
    columns spread. Two spacing mechanisms for the same rows is what broke it.
    """
    assert "function layoutRows(" in TIMELINE_SRC
    for key in ("video", "hook", "caption", "text"):
        assert TIMELINE_SRC.count(f"rowStyle('{key}')") == 2, \
            f"{key} should be spaced by rowStyle in both the gutter and the lane"
    # The stem rows are rendered in loops, one per column.
    assert TIMELINE_SRC.count("rowStyle(key)") == 2

    # No row may carry its own spacing any more.
    tracks = TIMELINE_SRC[TIMELINE_SRC.index("{/* Track lanes */}"):]
    assert "mt-1" not in tracks, "a per-row margin is how the columns drifted apart"
    assert "flex-col gap-" not in tracks, "a gap on one column only is the other half of the same bug"


def test_row_spacing_separates_the_groups_instead_of_repeating_one_gap():
    """
    Eight rows at one gap read as a single undifferentiated stack -- the
    grouping had to be inferred rather than seen. Rows inside a group sit close;
    picture, overlays and audio are pushed apart.
    """
    row_gap = _grab(TIMELINE_SRC, r"const ROW_GAP = (\d+);")
    group_gap = _grab(TIMELINE_SRC, r"const GROUP_GAP = (\d+);")
    assert group_gap >= row_gap * 3, "the group separation has to read as deliberate"
    groups = set(re.findall(r"group: '(\w+)'", TIMELINE_SRC))
    assert groups == {"picture", "overlay", "audio"}


def test_the_dock_height_is_derived_from_the_rows_it_has_to_show():
    """
    The dock's min and default heights were hand-tuned for a five-row timeline,
    so the four audio lanes pushed the video track below a hidden overflow --
    unreachable, with nothing on screen to say it was there.
    """
    assert "export function tracksFitHeight(" in TIMELINE_SRC
    assert "import Timeline, { tracksFitHeight }" in SHELL_SRC
    assert "TIMELINE_DEFAULT_H = TIMELINE_CHROME_H + tracksFitHeight()" in SHELL_SRC
    assert "tracksFitHeight({ audioCollapsed: true })" in SHELL_SRC
    assert not re.search(r"TIMELINE_(MIN|DEFAULT)_H = \d+", SHELL_SRC), \
        "a literal dock height goes stale the moment a row is added"
    # ...and a row can never be clipped away regardless of the dock's height.
    assert "overflow-x-auto overflow-y-auto" in TIMELINE_SRC
    assert "overflow-y-hidden" not in TIMELINE_SRC


def test_every_track_label_starts_at_the_same_x():
    """
    Rows lead with different things -- an icon, or a fold and a colour dot -- so
    the leading area is a fixed-width slot. Without it the audio labels sat 12px
    right of the others and the gutter's left edge read as ragged.
    """
    assert 'style={{ width: slotWidth }}' in TIMELINE_SRC
    assert 'slotWidth = 26' in TIMELINE_SRC, 'the slot needs a default for rows that pass none'
    # Every caller hands the same width in, so no row can indent differently.
    assert TIMELINE_SRC.count('slotWidth={dense ? 14 : 26}') == 6


def test_a_silent_track_says_so_without_relying_on_colour():
    """A red chip alone fails anyone who cannot separate the hues."""
    assert "line-through decoration-" in TIMELINE_SRC
    assert "hollow: silent" in TIMELINE_SRC


def test_mute_reports_what_it_is_not_how_it_looks():
    """
    A track silenced because another is soloed looks silent, but its mute
    button is not pressed -- announcing otherwise tells a screen reader the user
    muted something they never touched.
    """
    assert "aria-pressed={pressed ?? active}" in TIMELINE_SRC
    assert re.search(r"active=\{silent\}\s*\n\s*pressed=\{isMute\}", TIMELINE_SRC)


def test_mix_chips_have_a_hit_area_and_a_focus_ring():
    """The marks are small because the gutter is narrow; the targets are not."""
    chip = re.search(r"function MixButton\((.*?)\n\}", TIMELINE_SRC, re.S).group(1)
    assert "h-[18px] w-[18px]" in chip
    assert "focus-visible:outline" in chip


def test_the_folded_audio_group_can_be_unfolded_from_where_it_was_folded():
    """A group that folds away its own handle cannot be brought back."""
    assert "if (collapsed[row.group] && prevGroup === row.group) continue;" in TIMELINE_SRC
    assert "visibleStems = audioCollapsed ? STEMS.slice(0, 1) : STEMS" in TIMELINE_SRC
    assert "aria-expanded={!fold.collapsed}" in TIMELINE_SRC


def test_the_clip_audio_lane_explains_itself_when_empty():
    """Clip volume defaults to 0, so this lane is blank for most projects."""
    assert "ยังไม่ได้เปิดเสียงในคลิป" in TIMELINE_SRC


# --------------------------------------------------------------- phone layout
def test_the_gutter_gives_up_width_on_a_phone():
    """
    144px of names is 29% of a 500px screen, leaving the clips almost nothing.
    The width comes from the caller so the two layout trees can differ, and the
    colour dot goes on a phone -- the lane band already carries the colour, and
    those 12px are the difference between a name that fits and an ellipsis.
    """
    dense = _grab(TIMELINE_SRC, r"const GUTTER_DENSE = (\d+);")
    wide = _grab(TIMELINE_SRC, r"const GUTTER = (\d+);")
    assert dense < wide
    assert "const gutterW = dense ? GUTTER_DENSE : GUTTER;" in TIMELINE_SRC
    assert "style={{ width: width ?? GUTTER }}" in TIMELINE_SRC
    assert "dot={dense ? undefined : { colour, hollow: silent }}" in TIMELINE_SRC
    # ...and the leading slot narrows with it, so the names stay flush.
    assert TIMELINE_SRC.count("slotWidth={dense ? 14 : 26}") == 6
    assert "dense={isMobileView}" in SHELL_SRC


def test_the_phone_timeline_is_sized_by_its_rows_not_by_a_literal():
    """
    It was a fixed 215px with a comment claiming a snug fit. Once the audio
    lanes existed that showed three rows, clipped the other four, and left a
    black void below itself; filling the space instead only moved the void
    under the tracks.
    """
    assert "mobileTimelineH = MOBILE_TOOLBAR_H + tracksFitHeight({" in SHELL_SRC
    assert "audioCollapsed," in SHELL_SRC
    assert "h-[215px]" not in SHELL_SRC
    # The dock takes that height but may shrink, and the preview grows into
    # whatever the rows do not need while keeping a floor of its own.
    assert "style={{ flex: '0 1 auto', height: mobileTimelineH, maxHeight: mobileTimelineH }}" in SHELL_SRC
    assert "style={{ flex: '1 1 auto', height: mobilePreviewH, minHeight: MOBILE_PREVIEW_MIN_H }}" in SHELL_SRC
    assert "flex: `1 0 ${mobilePreviewH}px`" not in SHELL_SRC, \
        "an unshrinkable preview crushed the tracks to 82px on a shorter window"
    # The drag clamp has to reserve the timeline's real height, not a guess.
    assert "const reserve = MOBILE_TAB_ROW_H + (Number.isFinite(mobileTimelineH) ? mobileTimelineH : 0);" in SHELL_SRC


def test_a_phone_starts_with_the_audio_group_folded():
    """Four stem lanes are a desk-sized amount of detail; one tap opens them."""
    assert re.search(r"useState\(\s*\n?\s*\(\) => \(typeof window !== 'undefined' \? window\.innerWidth < LAYOUT_BREAKPOINT : false\)\s*\n?\s*\)", SHELL_SRC)


def test_the_folded_row_mutes_the_group_it_is_labelled_for():
    """
    Folded, the visible row says "เสียง" but its chips were still pointed at the
    voice stem: it read as a group control and muted one track of four.
    """
    assert "const mixKey = group ? 'all' : key;" in TIMELINE_SRC
    assert "onTrackMix?.(mixKey, 'mute')" in TIMELINE_SRC
    assert "onTrackMix?.(mixKey, 'solo')" in TIMELINE_SRC
    # ...and the group state reads from every stem, not just the visible one.
    assert "STEMS.every((s) => trackMix?.mute?.[s.key])" in TIMELINE_SRC
    assert "STEMS.every((s) => trackMix?.solo?.[s.key])" in TIMELINE_SRC
    # EditorShell resolves 'all' to every stem.
    assert "const targets = track === 'all' ? AUDIO_TRACKS : [track];" in SHELL_SRC
    assert re.search(r"const AUDIO_TRACKS = \['voice', 'bgm', 'sfx', 'clip'\];", SHELL_SRC)
    # A third chip does not fit beside a name on a phone, and the row's own M
    # already mutes all four once folded.
    assert "{i === 0 && !dense && !audioCollapsed && (" in TIMELINE_SRC


# ------------------------------------------------------------- mute holds
def test_muting_a_track_survives_graph_creation_and_the_tick():
    """
    "Every M is lit and the music still plays." Two separate causes: the buses
    were created at their raw levels, so muting before the first play left
    nothing to apply the mute to and the effect does not re-run for a graph
    that did not exist when it last fired; and the tick rewrote the BGM's gain
    from the level alone every frame, so a mute that did land was undone within
    16ms. Both now read one function.

    Run against the shipped code with a stubbed AudioContext, because the bug
    was in the interaction between three writers of the same gain -- which
    reading any one of them cannot show.
    """
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("node"):
        pytest.skip("needs node")

    player = ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx"
    runner = """
import { readFileSync } from 'node:fs';
const src = readFileSync(process.argv[2], 'utf8');
const grab = (re, what) => { const m = src.match(re); if (!m) throw new Error('missing ' + what); return m[0]; };
const code = `
${grab(/const AUDIO_MIX = \\{[\\s\\S]*?\\n\\};/, 'AUDIO_MIX')}
export function scope({ trackMix, bgmVolume, cues, totalDuration }) {
  const mk = () => ({ gain: { value: 0, cancelScheduledValues() {}, setTargetAtTime(v) { this.value = v; } } });
  const ctx = { currentTime: 0, state: 'running' };
  const audioCtxRef = { current: ctx };
  const audioNodesRef = { current: { bgm: mk(), voice: mk(), sfx: mk(), clip: mk() } };
  ${grab(/const soloedTracks = [\\s\\S]*?const trackLevel = \\(track\\) => \\([\\s\\S]*?\\);/, 'trackLevel')}
  const audioLiveRef = { current: { bgmVolume, cues, totalDuration, bgmDucking: false, bgmAudible: trackAudible('bgm') } };
  ${grab(/const applyBgmEnvelope = \\(t\\) => \\{[\\s\\S]*?\\n  \\};/, 'applyBgmEnvelope')}
  return { trackLevel, applyBgmEnvelope, bgm: audioNodesRef.current.bgm };
}`;
const m = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
const cases = {
  none:        { mute: {}, solo: {} },
  bgmMuted:    { mute: { bgm: true }, solo: {} },
  allMuted:    { mute: { voice: true, bgm: true, sfx: true, clip: true }, solo: {} },
  voiceSoloed: { mute: {}, solo: { voice: true } },
  bgmSoloed:   { mute: {}, solo: { bgm: true } },
};
const out = {};
for (const [name, trackMix] of Object.entries(cases)) {
  const s = m.scope({ trackMix, bgmVolume: 0.12, cues: [{ start: 0, end: 5, text: 'x' }], totalDuration: 30 });
  const level = s.trackLevel('bgm');
  s.bgm.gain.value = level;
  s.applyBgmEnvelope(1.0);           // the tick must not undo it
  out[name] = { level, afterTick: s.bgm.gain.value };
}
console.log(JSON.stringify(out));
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mute.mjs"
        path.write_text(runner, encoding="utf-8")
        res = subprocess.run(["node", str(path), str(player)], capture_output=True, text=True)
        assert res.returncode == 0, res.stderr
        got = json.loads(res.stdout)

    assert got["none"] == {"level": 0.12, "afterTick": 0.12}
    for silent in ("bgmMuted", "allMuted", "voiceSoloed"):
        assert got[silent]["level"] == 0, f"{silent}: the bus was built audible"
        assert got[silent]["afterTick"] == 0, f"{silent}: the tick brought the music back"
    assert got["bgmSoloed"] == {"level": 0.12, "afterTick": 0.12}


def test_the_gain_writers_share_one_source_of_truth():
    """Three places set these gains; disagreeing is what the bug was."""
    assert "const trackLevel = (track) => (trackAudible(track) ? trackBase[track] : 0);" in JS_SRC
    for track in ("voice", "bgm", "sfx", "clip"):
        assert f"{track}: bus(trackLevel('{track}'))" in JS_SRC
    assert "nodes[track].gain.setTargetAtTime(trackLevel(track), ctx.currentTime, 0.01);" in JS_SRC
    assert "bgmAudible: trackAudible('bgm')" in JS_SRC
    assert "if (live.bgmAudible === false) {" in JS_SRC


# --------------------------------------------------------- AI Vision upload
def test_ai_vision_uploads_a_proxy_not_the_camera_original():
    """
    A first-time scene match was spending minutes on the upload: this project's
    own clip is 241MB for 91 seconds of 1080p60, which is about six minutes on a
    5 Mbps upstream and matched the ten-minute 1-Click runs. The model samples
    video at roughly a frame a second to answer "which seconds show what", so
    resolution and frame rate buy nothing. Measured: 640px at 6fps came to
    3.7MB, 66x smaller, in 21 seconds of local transcoding.
    """
    src = (ROOT / "scripts" / "gemini_vision_matcher.py").read_text(encoding="utf-8")
    assert "def _vision_proxy(" in src
    assert "upload_file = cls._vision_proxy(video_file, file_hash) or video_file" in src, \
        "a failed transcode must fall back to the original, not skip the match"
    assert "with open(upload_file, \"rb\") as f:" in src, "the proxy has to be the file that is sent"
    # The cache stays keyed on the ORIGINAL, or an already-uploaded clip stops
    # being recognised and pays for the transcode and the upload again.
    assert "file_hash = cls._compute_file_hash(video_file)" in src
    assert 'cache[file_hash] = {' in src
    assert 'proxy_dir / f"{file_hash}.mp4"' in src


def test_the_vision_proxy_keeps_the_timeline_it_reports_against():
    """
    Scene timestamps are read straight off the proxy, so its duration has to be
    the original's. Only the picture is reduced -- no trim, no speed change.
    """
    import shutil

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("needs ffmpeg")
    sys.path.insert(0, str(ROOT))
    from scripts.gemini_vision_matcher import GeminiVisionMatcher, PROXY_FPS, PROXY_WIDTH

    src = next((p for p in (ROOT / "01_Raw").rglob("*") if p.suffix.lower() in (".mov", ".mp4")), None)
    if src is None:
        pytest.skip("no raw footage to probe")

    import subprocess

    def duration(path):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
        return float(r.stdout.strip())

    file_hash = GeminiVisionMatcher._compute_file_hash(src)
    proxy = GeminiVisionMatcher._vision_proxy(src, file_hash)
    assert proxy and proxy.exists()
    # One frame of the proxy's own rate is the most a re-timed tail may differ.
    assert abs(duration(src) - duration(proxy)) <= 1.0 / PROXY_FPS + 0.05
    assert proxy.stat().st_size < src.stat().st_size, "a proxy that is not smaller buys nothing"

    # Cached by the original's hash, so a second run costs nothing.
    again = GeminiVisionMatcher._vision_proxy(src, file_hash)
    assert again == proxy

    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width", "-of", "csv=p=0", str(proxy)],
                           capture_output=True, text=True, check=True)
    assert int(probe.stdout.strip()) == PROXY_WIDTH


# ------------------------------------------------------------- render speed
def test_each_clip_seeks_its_input_instead_of_trimming_after_decode():
    """
    A clip_list gives one ffmpeg input per clip, and each clip wants a few
    seconds from somewhere in a long source. Cutting that with a `trim` filter
    makes the decoder walk the file from frame zero every time: 8 clips spread
    over 91 seconds of 1080p60 decoded roughly ten times more video than the
    render used. Seeking the input decodes only the span.

    Measured through VideoEditor on this project's own footage: 58.6s -> 7.0s,
    with the output bit-identical frame for frame (SSIM 1.0000, PSNR infinite).
    """
    editor = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    assert 'cmd_inputs.extend(["-ss", f"{max(0.0, start):.3f}",' in editor
    assert '"-t", f"{span:.3f}", "-i", video_path])' in editor, \
        "the span must be exact -- padding it slid every later clip out of step"
    assert "input_seeks.append((trim_start, source_span))" in editor

    # The video filters must not seek a second time...
    assert "trim=start={trim_start}" not in editor.split("1-Click Studio path")[0], \
        "the clip_list branch should no longer trim from the start"
    # ...but must still pin the length, so container rounding at the seek point
    # cannot lengthen a clip.
    # Every per-clip branch needs it -- the blurred pillarbox, the two-stage
    # framing and the one-pass framing. Pinning only some leaves the rest free
    # to run long, which slides every later clip out of step.
    assert editor.count("]trim=duration={source_span}") == 3
    assert editor.count("atrim=duration={source_span}") == 1

    # The 1-Click path takes every cut out of one input, so there is no single
    # span to seek to and it keeps its trims.
    legacy = editor.split("1-Click Studio path")[1]
    assert "trim=start=" in legacy, "the single-source path still needs filter trims"


# --------------------------------------------------- encoder + framing


def test_a_hardware_encoder_is_probed_not_assumed_from_the_encoder_list():
    """
    `ffmpeg -encoders` lists NVENC and QSV on this machine, which has neither;
    both fail only when asked to encode. So each candidate gets a real
    one-frame encode, once per process, and libx264 stays the fallback.
    """
    assert "def hardware_encoder(" in VIDEO_EDITOR_SRC
    assert '"-f", "lavfi", "-i", "color=black:s=256x256:d=0.1:r=30"' in VIDEO_EDITOR_SRC
    assert "if probe.returncode == 0:" in VIDEO_EDITOR_SRC
    assert "_hw_encoder_probed" in VIDEO_EDITOR_SRC, "the probe must not run per render"
    # An escape hatch, because a hardware encoder is a quality decision.
    assert 'os.environ.get("OMNICUT_ENCODER"' in VIDEO_EDITOR_SRC
    assert '("cpu", "x264", "libx264", "software")' in VIDEO_EDITOR_SRC


def test_the_software_encoder_settings_are_unchanged_when_it_is_used():
    """Falling back must produce what it always produced."""
    sys.path.insert(0, str(ROOT))
    import importlib
    import scripts.video_editor as ve
    importlib.reload(ve)

    import os
    os.environ["OMNICUT_ENCODER"] = "cpu"
    try:
        args = ve.encoder_args(ve.EXPORT_PRESETS["post"])
    finally:
        os.environ.pop("OMNICUT_ENCODER", None)
    assert args == ["-c:v", "libx264", "-profile:v", "high", "-level", "4.2",
                    "-preset", "medium", "-crf", "18"]


def test_every_export_preset_carries_a_quality_setting_for_both_encoders():
    sys.path.insert(0, str(ROOT))
    from scripts.video_editor import EXPORT_PRESETS
    for name, preset in EXPORT_PRESETS.items():
        for key in ("crf", "x264_preset", "qp_i", "qp_p"):
            assert key in preset, f"{name} has no {key}"
        assert preset["qp_i"] <= preset["qp_p"], f"{name}: I-frames should not be the coarser ones"


def test_the_composed_framing_uses_the_dimensions_the_filters_will_see():
    """
    ffmpeg auto-rotates before the filter graph, so ordinary phone footage
    carrying `rotation -90` arrives as 1080x1920 while the container still says
    1920x1080. Composing the crop from the container numbers put the window in
    the wrong place entirely -- SSIM 0.74, and it looked like a plausible crop
    until it was compared frame by frame.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.video_editor import framing_filters

    rotated = framing_filters({"width": 1920, "height": 1080, "rotation": -90}, 1166, 2074, 43, 77)
    upright = framing_filters({"width": 1080, "height": 1920, "rotation": 0}, 1166, 2074, 43, 77)
    assert rotated == upright, "a rotated clip must frame the same as its rotated size"
    assert rotated and rotated.startswith("crop=")
    assert "scale=1080:1920:flags=lanczos" in rotated

    # No zoom: the whole (already portrait) frame.
    plain = framing_filters({"width": 1080, "height": 1920, "rotation": 0}, 1080, 1920, 0, 0)
    assert plain.startswith("crop=1080:1920:0:0")

    # Unknown or impossible geometry falls back to the two-stage chain, which
    # asks `scale` to work it out and cannot get this wrong.
    assert framing_filters({"rotation": 0}, 1166, 2074, 43, 77) is None
    assert framing_filters({"width": 100, "height": 100, "rotation": 0}, 99999, 99999, 0, 0) is None


def test_one_pass_framing_is_skipped_where_it_would_change_the_picture():
    """
    Mirror and rotate move which source pixels land where, and the blurred
    pillarbox composites two layers -- neither is a single window of the
    source, so both keep the two-stage chain.
    """
    assert "if not rot_filter and not mirror_filter:" in VIDEO_EDITOR_SRC
    blur_branch = VIDEO_EDITOR_SRC[VIDEO_EDITOR_SRC.index("boxblur"):]
    assert "framing_filters" not in blur_branch.split("else:")[0]


# ------------------------------------------------------------ default BGM
def test_one_default_bgm_across_render_mix_and_editor():
    """
    Four places disagreed about which track plays when a project names none:
    the pipeline substituted it_angles.DEFAULT_BGM, resolve_bgm_path had its
    own literal, the editor's stems memo had a third, and the timeline label
    printed a fixed string naming a fourth. The timeline read "เสียงหลักของช่อง"
    while the render played tiktok_upbeat -- confirmed by rebuilding the mix
    once per candidate and scoring each against the project's own mixed file:
    tiktok_upbeat_bgm.wav matched at 0.9993, the next best at 0.9907.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.it_angles import DEFAULT_BGM
    from scripts.sfx_manager import SFXManager

    sfx_src = (ROOT / "scripts" / "sfx_manager.py").read_text(encoding="utf-8")
    assert "name = bgm_name or DEFAULT_BGM" in sfx_src
    assert "bgm_over_loaded_hiphop_instrumental" not in sfx_src, "a second default crept back in"

    resolved = SFXManager.resolve_bgm_path(None)
    assert resolved and resolved.name == DEFAULT_BGM

    # The render records the track it actually used, so the editor never has to
    # guess -- with nothing chosen the pipeline picks by angle mood.
    pipeline = (ROOT / "scripts" / "pipeline.py").read_text(encoding="utf-8")
    assert '"bgm_name": effective_bgm_name or bgm_name,' in pipeline

    # And the editor is told the default rather than keeping a copy.
    api = (ROOT / "scripts" / "api_server.py").read_text(encoding="utf-8")
    assert '"default_bgm": DEFAULT_BGM,' in api
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert "DEFAULT_BGM_FILE" not in shell, "the editor should not hold its own default"
    assert "m.id === assets.default_bgm || m.name === assets.default_bgm" in shell
    assert "'เสียงหลักของช่อง'" not in shell, \
        "the label must name the track that will play, not a fixed string"


def test_the_encoder_choice_is_not_tied_to_one_vendor():
    """
    The first version tried AMD's encoder first, because that is what the
    machine it was written on has. On a laptop with an integrated AMD GPU and a
    discrete NVIDIA one -- an ordinary machine -- that picks the weaker of the
    two. The discrete families lead, and a miss costs a fraction of a second.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.video_editor import HW_ENCODER_CANDIDATES, _hw_args

    assert HW_ENCODER_CANDIDATES.index("h264_nvenc") < HW_ENCODER_CANDIDATES.index("h264_amf")
    assert "h264_qsv" in HW_ENCODER_CANDIDATES
    assert "h264_videotoolbox" in HW_ENCODER_CANDIDATES, "a Mac would otherwise fall back to the CPU"

    # Each family gets its own constant-quality mode, because the knobs are not
    # the same scale: AMF takes cqp with separate I/P values, NVENC's crf
    # equivalent is -cq under VBR, QSV uses -global_quality, and
    # videotoolbox's -q:v runs the other way (higher is better).
    for name in HW_ENCODER_CANDIDATES:
        args = _hw_args(name, 20, 22)
        assert args[:2] == ["-c:v", name]
        assert len(args) > 2, f"{name} has no quality setting"
    assert "-cq" in _hw_args("h264_nvenc", 20, 22)
    assert "-global_quality" in _hw_args("h264_qsv", 20, 22)
    assert "-qp_i" in _hw_args("h264_amf", 20, 22)
    vt = _hw_args("h264_videotoolbox", 20, 22)
    assert int(vt[vt.index("-q:v") + 1]) > 50, "videotoolbox's scale is inverted"


def test_a_hardware_encoder_has_to_prove_its_quality_before_it_is_used():
    """
    Each family's quality knob is on its own scale, and only a machine that has
    the hardware can say whether the number chosen for it is sane -- guessing
    NVENC's from an AMD box is how a render comes out smeared. So a candidate
    that encodes a frame is then made to hold up against libx264 on the same
    frames, and is skipped if it does not.

    Verified live: this machine's h264_amf passes at SSIM 0.974, and raising
    the floor above that makes the render fall back to libx264.
    """
    assert "def _encoder_quality_ok(" in VIDEO_EDITOR_SRC
    assert "HW_QUALITY_FLOOR" in VIDEO_EDITOR_SRC
    assert "if ssim < HW_QUALITY_FLOOR:" in VIDEO_EDITOR_SRC
    assert "if ssim is None:" in VIDEO_EDITOR_SRC, "an unmeasurable candidate must be skipped, not trusted"
    assert '"-lavfi", "[0:v][1:v]ssim"' in VIDEO_EDITOR_SRC

    sys.path.insert(0, str(ROOT))
    from scripts.video_editor import HW_QUALITY_FLOOR
    assert 0.9 <= HW_QUALITY_FLOOR < 1.0


def test_the_probe_runs_once_per_process_not_once_per_render():
    """
    It costs a couple of seconds -- fine at server start, not per export.
    Measured: 2.6s for the probe, then 7.2s and 7.4s for two renders in the
    same process.
    """
    assert "if _hw_encoder_probed:" in VIDEO_EDITOR_SRC
    assert "_hw_encoder_probed = True" in VIDEO_EDITOR_SRC
    # The render path must ask through the cached accessor, never probe itself.
    assert VIDEO_EDITOR_SRC.count("subprocess.run([\n                \"ffmpeg\", \"-hide_banner\", \"-loglevel\", \"error\",\n                \"-f\", \"lavfi\"") == 1


# --------------------------------------------------------- hook header looks
# The banner had exactly one appearance, with every part of it a literal in the
# ASS writer: a black 6px outline on all three tiers, sizes 130/100/58, the
# caption's font, and the brand always upper-cased. A template names a whole
# look and anything in it can still be overridden field by field.
HOOK_PY = (ROOT / "scripts" / "hook_styles.py").read_text(encoding="utf-8")
HOOK_JS = (ROOT / "frontend" / "src" / "lib" / "hookStyles.js").read_text(encoding="utf-8")


def _js_hook_templates():
    """The JS table, parsed. It is JS object literal syntax, close enough to
    JSON once the trailing commas, quotes and `ACCENT` are normalised."""
    block = re.search(r"export const HOOK_TEMPLATES = \{(.*?)\n\};", HOOK_JS, re.S)
    assert block, "HOOK_TEMPLATES not found in the JS table"
    text = "{" + block.group(1) + "}"
    text = text.replace("ACCENT", "null")
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', text)
    text = text.replace("'", '"')
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(text)


def test_hook_templates_are_identical_on_both_sides():
    """
    The ASS writer reads the Python table and the canvas preview reads the JS
    one. A look that exists on only one side, or a tier that differs by a
    single field, is a preview that lies about the render.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.hook_styles import HOOK_TEMPLATES, TIER_FIELDS, TIER_KEYS

    js = _js_hook_templates()
    assert set(js) == set(HOOK_TEMPLATES), \
        f"only in JS: {set(js) - set(HOOK_TEMPLATES)}; only in Python: {set(HOOK_TEMPLATES) - set(js)}"

    for name, py_tpl in HOOK_TEMPLATES.items():
        js_tpl = js[name]
        assert js_tpl["font"] == py_tpl["font"], f"{name}: font differs"
        assert js_tpl["label_th"] == py_tpl["label_th"], f"{name}: label differs"
        for tier in TIER_KEYS:
            for field in TIER_FIELDS:
                a, b = py_tpl["tiers"][tier][field], js_tpl["tiers"][tier][field]
                assert a == b, f"{name}.{tier}.{field}: python {a!r} vs js {b!r}"


def test_both_resolvers_agree_on_templates_overrides_and_colours():
    """
    Resolution order is the contract: template, then per-field overrides, then
    the older colour map -- so a project keeps the colours it was saved with
    whichever look it is on. Both sides are run on the same inputs.
    """
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("node"):
        pytest.skip("needs node")
    sys.path.insert(0, str(ROOT))
    from scripts.hook_styles import resolve_hook_style

    cases = [
        {"template": None, "overrides": None, "colors": None},
        {"template": "cute", "overrides": None, "colors": None},
        {"template": "nonsense", "overrides": None, "colors": None},
        {"template": "cute", "overrides": {"font": "Mitr"}, "colors": None},
        {"template": "bold_pop", "overrides": {"tiers": {"brand": {"outline_px": 2}}}, "colors": None},
        {"template": "plain", "overrides": None, "colors": {"model": "#cc7171"}},
        {"template": "cute", "overrides": {"tiers": {"label": {"color": "#111111"}}},
         "colors": {"label": "#222222"}},
    ]

    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "resolve.mjs"
        mod = (ROOT / "frontend" / "src" / "lib" / "hookStyles.js").resolve().as_uri()
        runner.write_text(
            f"import {{ resolveHookStyle }} from '{mod}';\n"
            "const cases = JSON.parse(process.argv[2]);\n"
            "console.log(JSON.stringify(cases.map(c => resolveHookStyle(c.template, "
            "{ ...(c.overrides || {}), template: c.template }, c.colors))));\n",
            encoding="utf-8",
        )
        res = subprocess.run(["node", str(runner), json.dumps(cases)],
                             capture_output=True, text=True)
        assert res.returncode == 0, res.stderr
        js_out = json.loads(res.stdout)

    for case, js_style in zip(cases, js_out):
        py_style = resolve_hook_style(
            case["template"],
            {**(case["overrides"] or {}), "template": case["template"]},
            case["colors"],
        )
        assert py_style == js_style, f"{case} -> python {py_style} vs js {js_style}"


def test_the_ass_writer_emits_the_per_tier_edge_from_the_template():
    """
    Outline colour and width were a Style-level literal, the same black 6.0 for
    every tier, so "white text with a thick pink edge" was unreachable. \\3c is
    the outline colour and \\bord its width, both per line now.
    """
    # The look is resolved per tier from the overlay itself now, which is what
    # finally lets the editor's own numbers reach the burn.
    assert "resolve_look(hook_overlay.get(\"look\")" in PY_SRC
    assert "\\\\3c{outline_colour}&" in PY_SRC
    assert "\\\\bord{float(tier_style['outline_px']):.1f}" in PY_SRC
    # A pill is BorderStyle 3, which paints its box with the outline colour.
    assert "Style: HookHeaderPill," in PY_SRC
    assert "BorderStyle 3 paints it" in PY_SRC
    # Sizes and the upper-casing come from the look, not from the tier's
    # position or its size being the biggest one.
    assert 'int(tier_looks[0]["size_pct"])' in PY_SRC
    assert 'tiers[tier_key_by_idx[tier_idx]]["upper"]' in PY_SRC
    assert "if scale_pct == 130:" not in PY_SRC, "upper-casing should not key off a size"


def test_the_canvas_draws_the_same_per_tier_edge():
    # One resolveLook on each side, over the same TextLook fields.
    assert "resolveLook(overlay.look, tier.look)" in JS_SRC
    assert "ctx.strokeStyle = w.look.outline_color;" in JS_SRC
    assert "if (w.look.outline_px > 0.01) {" in JS_SRC, "an outline of 0 must draw no stroke"
    # The pill's padding is a multiple of the tier's own size on both sides,
    # so it follows the text instead of staying at a flat 12px.
    assert _grab(OVERLAY_JS, r"HOOK_PILL_PAD_X_EM = ([\d.]+);") == \
           _grab(OVERLAY_PY, r"\nHOOK_PILL_PAD_X_EM = ([\d.]+)\n")
    assert 'pill_pad = int(round(hook_fs * float(pill.get("pad_x_em") or 0.342)))' in PY_SRC


def test_the_banner_is_measured_in_its_own_face():
    """
    The banner can use a different font from the captions now. A font's line box
    against its em is exactly what the \\fscx boost cancels, so the banner needs
    the boost of ITS face -- and every width it measures has to use that face,
    or the wrap and the accent geometry are computed against the wrong glyphs.
    """
    assert "HOOK_SCALE_BOOST = 1.0 / ass_glyph_scale(hook_font)" in PY_SRC
    assert "target = round(layout_pct * HOOK_SCALE_BOOST)" in PY_SRC
    assert "Style: HookHeader,{hook_font}," in PY_SRC
    assert "Style: HookHeaderShadow,{hook_font}," in PY_SRC
    # A template naming a font that is not installed falls back rather than
    # handing libass a name it will silently substitute.
    assert 'hook_font = resolved_font' in PY_SRC
    assert 'if hook_font not in {f["family"] for f in AssetRegistry.fonts()}:' in PY_SRC


def test_every_template_names_an_installed_font():
    """A look whose font is missing renders in something else entirely."""
    sys.path.insert(0, str(ROOT))
    from scripts.asset_registry import AssetRegistry
    from scripts.hook_styles import HOOK_TEMPLATES

    families = {f["family"] for f in AssetRegistry.fonts()}
    if not families:
        pytest.skip("no fonts installed")
    for name, tpl in HOOK_TEMPLATES.items():
        assert tpl["font"] in families, f"{name} wants {tpl['font']}, which is not installed"


def test_the_browser_loads_every_font_the_templates_use():
    """
    The canvas can only draw a face the page has actually loaded; without it the
    preview silently falls back and stops matching the render.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.hook_styles import HOOK_TEMPLATES

    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    for name, tpl in HOOK_TEMPLATES.items():
        family = tpl["font"].replace(" ", "+")
        assert f"family={family}" in html, \
            f"{name} uses {tpl['font']}, which index.html does not load"


def test_the_overlay_look_survives_the_round_trip_to_a_render():
    """A look that cannot reach the renderer is a preview-only decoration."""
    for src, label in (
        ((ROOT / "scripts" / "pipeline.py").read_text(encoding="utf-8"), "pipeline"),
        ((ROOT / "scripts" / "api_server.py").read_text(encoding="utf-8"), "api_server"),
        ((ROOT / "scripts" / "api_phase1.py").read_text(encoding="utf-8"), "api_phase1"),
    ):
        assert "overlays" in src, f"{label} drops overlays"
    pipeline = (ROOT / "scripts" / "pipeline.py").read_text(encoding="utf-8")
    assert "overlays=effective_overlays," in pipeline, "the subtitle writer never receives them"
    assert '"overlays": effective_overlays,' in pipeline
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    # Saved, and handed to both players plus both inspectors and timelines.
    assert "overlays," in shell and "overlays: Array.isArray(overlays)" in PROJECT_STATE_SRC
    assert shell.count("overlays={overlays}") == 6, \
        "both players, both timelines and both inspectors need them"

    # The legacy keys are still READ (an old project has to open) but must
    # never be written again, or the two representations drift apart.
    assert "migrateToOverlays(manifest)" in PROJECT_STATE_SRC or "migrateToOverlays(data)" in shell
    for dead in ("hook_brand:", "hook_model:", "hook_label:", "text_overlays:"):
        assert dead not in shell, f"{dead} is still being written"


def test_text_overlay_sfx_is_supported_in_both_preview_and_render():
    """
    SFX linked to text overlays must be mixed in both SequencePlayer.jsx (via audioStems)
    and in sfx_manager.py (via mix_audio_track) at the same volume SFX_VOLUME = 0.28.
    """
    sfx_src = (ROOT / "scripts" / "sfx_manager.py").read_text(encoding="utf-8")
    shell_src = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")

    assert "overlays: Optional[List[Dict]] = None" in sfx_src
    assert "sfx_txt_" in sfx_src, "sfx_manager does not mix overlay SFX nodes"
    assert "overlayId: o.id" in shell_src, "EditorShell does not mix overlays into audioStems.sfx"
    # A banner is an overlay too, so its own SFX has to reach the mix.
    pipeline = (ROOT / "scripts" / "pipeline.py").read_text(encoding="utf-8")
    assert "overlays=effective_overlays," in pipeline


def test_text_overlay_animations_match_in_preview_and_render():
    """
    Animation scales and durations for pop, zoom, stamp in subtitle_engine.py (ASS tags)
    must match SequencePlayer.jsx (canvas drawing).
    """
    sub_src = (ROOT / "scripts" / "subtitle_engine.py").read_text(encoding="utf-8")
    player_src = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")

    # The three names a text overlay shared with the banner were renamed
    # rather than merged, so both sets of keyframes survive.
    assert 'anim == "pop_zoom"' in sub_src
    assert "pop_zoom: {" in player_src
    assert 'anim == "stamp"' in sub_src
    assert "stamp: {" in player_src


# ------------------------------------------------------------ overlay model
# The banner and the text overlays were two spellings of one picture: `scale`
# against `size_pct`, `bgStyle`+`badgeColor` against `pill`, one `anim` string
# against four motion channels -- and no outline fields at all on the text
# side, so a text overlay could never reach the look a hook template could.
# scripts/overlay_model.py is the single spelling; overlayModel.js mirrors it.
OVERLAY_PY = (ROOT / "scripts" / "overlay_model.py").read_text(encoding="utf-8")
OVERLAY_JS = (ROOT / "frontend" / "src" / "lib" / "overlayModel.js").read_text(encoding="utf-8")

_QUOTES_AND_SPACE = re.compile(r"""['"\s]""")


def _js_const(name, cast=float):
    return _grab(OVERLAY_JS, rf"export const {name} = ([\d.]+);", cast)


def _py_const(name, cast=float):
    # _grab runs with re.S, not re.M, so anchor on the newlines themselves.
    return _grab(OVERLAY_PY, rf"\n{name}(?:: [^=]+)? = ([\d.]+)\n", cast)


def _squash(text):
    """Compare two object literals without caring about quoting or layout."""
    return _QUOTES_AND_SPACE.sub("", text)


def test_overlay_geometry_constants_match_on_both_sides():
    """
    Font-size ratios, the canvas/render halving, and the pill padding all
    decide where ink lands. Each is one number that both engines read.
    """
    for name in ("CANVAS_SCALE", "HOOK_FS_RATIO", "TEXT_FS_RATIO",
                 "PILL_PAD_X_EM", "PILL_PAD_Y_EM", "PILL_RADIUS_MAX_PX",
                 "HOOK_PILL_PAD_X_EM", "HOOK_PILL_PAD_Y_EM"):
        assert _py_const(name) == _js_const(name), f"{name} differs across the two sides"

    # The ratios are the ones the two renderers already agreed on before they
    # moved into the model, so nothing shifted on the way in.
    assert _py_const("HOOK_FS_RATIO") == \
        _grab(PY_SRC, r"hook_fs = int\(round\(video_width \* ([\d.]+)\)\)")
    assert _py_const("TEXT_FS_RATIO") == \
        _grab(PY_SRC, r"base_fs = int\(round\(video_width \* ([\d.]+)\)\)")


def test_hook_block_anchor_is_the_same_fraction_of_the_frame():
    """Parity rule 2.8: ASS MarginV 260/1920 against canvas y 130/960."""
    assert "HOOK_TOP_Y = 260.0 / 1920.0" in OVERLAY_PY
    assert "HOOK_TOP_Y = 260.0 / 1920.0" in OVERLAY_JS
    assert 260.0 / 1920.0 == 130.0 / 960.0


def test_a_text_overlays_outline_is_now_the_renders_number_not_the_previews():
    """
    The ASS style burned Outline 5.0 while the canvas derived its own
    max(2, fs*0.12) -- 3px at 100%, 6px at 210%, never the same picture twice.
    One number now, and the render's is the one that was true.
    """
    ass_outline = _grab(PY_SRC, r"Style: TextOverlayMain,[^\n]*?,1,([\d.]+),2,5,")
    assert ass_outline == 5.0
    assert _grab(OVERLAY_PY, r'"outline_px": ([\d.]+),\n    "shadow": DEFAULT_SHADOW') == ass_outline
    assert _grab(OVERLAY_JS, r"outline_px: ([\d.]+),\n  shadow: DEFAULT_SHADOW") == ass_outline


def test_shadow_defaults_match_on_both_sides():
    for name in ("DEFAULT_SHADOW", "HOOK_SHADOW"):
        py = re.search(rf"{name}[^=]*= (\{{[^}}]*\}})", OVERLAY_PY).group(1)
        js = re.search(rf"{name} = (\{{[^}}]*\}})", OVERLAY_JS).group(1)
        assert _squash(py) == _squash(js), f"{name} differs: python {py} vs js {js}"


def test_anim_defaults_match_on_both_sides():
    for name in ("DEFAULT_ANIM", "HOOK_ANIM"):
        py = re.search(rf"{name}[^=]*= \{{(.*?)\}}", OVERLAY_PY, re.S).group(1)
        js = re.search(rf"{name} = \{{(.*?)\}}", OVERLAY_JS, re.S).group(1)
        fields = lambda block: sorted(
            t.lower() for t in _squash(block).strip(",").split(",") if t
        )
        assert fields(py) == fields(js), f"{name} differs: python {py} vs js {js}"


def test_ad_tone_to_template_matches_on_both_sides_and_names_real_templates():
    """
    The tone is picked per angle by the script AI. A first render dresses the
    banner to match the voice instead of landing on 'tech' every time, so the
    map has to name looks that actually exist.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.hook_styles import HOOK_TEMPLATES
    from scripts.overlay_model import AD_TONE_TO_TEMPLATE

    js_block = re.search(r"export const AD_TONE_TO_TEMPLATE = \{(.*?)\};", OVERLAY_JS, re.S).group(1)
    js_map = dict(re.findall(r"(\w+):\s*'([^']+)'", js_block))
    assert js_map == AD_TONE_TO_TEMPLATE, f"python {AD_TONE_TO_TEMPLATE} vs js {js_map}"

    for tone, template in AD_TONE_TO_TEMPLATE.items():
        assert template in HOOK_TEMPLATES, f"{tone} points at a look that does not exist"

    # Every tone the TTS engine offers gets a look; a new tone must choose one.
    tts = (ROOT / "scripts" / "gemini_tts_engine.py").read_text(encoding="utf-8")
    tones = set(re.findall(r'^    "(\w+)": \{$', tts, re.M))
    assert tones == set(AD_TONE_TO_TEMPLATE), \
        f"tones without a banner look: {tones - set(AD_TONE_TO_TEMPLATE)}"


# ------------------------------------------------------ migration behaviour
LEGACY_CASES = [
    # nothing at all -- no overlay, which is what showHookHeader was for
    {},
    {"hook_brand": "", "hook_model": "", "hook_label": "", "text_overlays": []},
    # banner only, on each look
    {"hook_brand": "Logitech", "hook_model": "Wave Keys", "hook_label": "Keyboard"},
    {"hook_brand": "L", "hook_model": "W", "hook_label": "K", "hook_style": {"template": "cute"}},
    {"hook_brand": "L", "hook_model": "W", "hook_label": "K", "hook_style": {"template": "bold_pop"}},
    {"hook_brand": "L", "hook_model": "W", "hook_label": "K", "hook_style": {"template": "plain"}},
    {"hook_brand": "L", "hook_model": "W", "hook_label": "K", "hook_style": {"template": "clean"}},
    {"hook_brand": "L", "hook_model": "W", "hook_label": "K", "hook_style": {"template": "nonsense"}},
    # a banner with no brand still exists -- the old !!brand check dropped it,
    # then autosave wrote "" over the model and label it had not looked at
    {"hook_model": "Wave Keys", "hook_label": "Keyboard"},
    # per-tier overrides and the older colour map
    {"hook_brand": "L", "hook_model": "W", "hook_label": "K", "hook_duration": 4.5,
     "hook_style": {"template": "tech", "tiers": {"brand": {"size_pct": 160, "outline_px": 12}}},
     "hook_colors": {"model": "#cc7171"}, "hook_motion": {"in": "typewriter", "loop": "none"}},
    # text overlays, one per background style
    {"text_overlays": [{"id": "a", "text": "x", "start": 0, "end": 2, "position": "middle",
                        "x": 0.5, "y": 0.5, "scale": 1.0, "color": "#FFF", "bgStyle": "none",
                        "anim": "pop"}]},
    {"text_overlays": [{"id": "b", "text": "y", "start": 1, "end": 3, "position": "top",
                        "x": None, "y": None, "scale": 2.1, "color": "#25F4EE",
                        "fontName": "Prompt", "bgStyle": "badge_cyan", "anim": "slide",
                        "sfx": "sfx_whoosh_fast", "sfxLabel": "W", "templateId": "t"}]},
    {"text_overlays": [{"id": "c", "text": "z", "start": 0, "end": 1, "bgStyle": "badge_red",
                        "badgeColor": "#FE2C55", "anim": "stamp", "scale": 1.35}]},
    {"text_overlays": [{"id": "d", "text": "w", "start": 0, "end": 1, "bgStyle": "pill"}]},
    # a badgeColor matching no preset is an arbitrary fill
    {"text_overlays": [{"id": "e", "text": "v", "start": 0, "end": 1, "bgStyle": "none",
                        "badgeColor": "#123456"}]},
    # both kinds together, and the render_params fallback the editor reads
    {"hook_brand": "L", "hook_model": "W", "hook_label": "K",
     "text_overlays": [{"id": "f", "text": "u", "start": 0, "end": 1}]},
    {"render_params": {"hook_brand": "L", "hook_model": "W", "hook_label": "K",
                       "text_overlays": [{"id": "g", "text": "t", "start": 0, "end": 1}]}},
]


def test_both_migrations_produce_the_same_overlays():
    """
    The editor migrates on load and the pipeline migrates on read. They are
    two implementations of one conversion; a project that opens differently
    from the way it renders is the bug this whole model exists to remove.
    """
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("node"):
        pytest.skip("needs node")
    sys.path.insert(0, str(ROOT))
    from scripts.overlay_model import migrate_to_overlays

    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "migrate.mjs"
        mod = (ROOT / "frontend" / "src" / "lib" / "overlayModel.js").resolve().as_uri()
        runner.write_text(
            f"import {{ migrateToOverlays }} from '{mod}';\n"
            "const cases = JSON.parse(process.argv[2]);\n"
            "console.log(JSON.stringify(cases.map(c => migrateToOverlays(c))));\n",
            encoding="utf-8",
        )
        out = subprocess.run(
            ["node", str(runner), json.dumps(LEGACY_CASES)],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT),
        )
        assert out.returncode == 0, out.stderr
        js_results = json.loads(out.stdout)

    for case, js_overlays in zip(LEGACY_CASES, js_results):
        py_overlays = migrate_to_overlays(case)
        assert json.loads(json.dumps(py_overlays)) == js_overlays, \
            f"migration differs for {case}"


def test_migration_is_idempotent_and_survives_a_round_trip_through_legacy():
    """
    Legacy keys are read forever and never written again, so an old project
    opens without anyone touching the file on disk. Converting what came back
    out must land on the same overlays, or a save would drift the picture.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.overlay_model import migrate_to_overlays, overlays_to_legacy

    for case in LEGACY_CASES:
        once = migrate_to_overlays(case)
        # an already-migrated manifest passes straight through
        assert migrate_to_overlays({"overlays": once}) == once, f"passthrough changed {case}"
        # legacy -> overlays -> legacy -> overlays is a fixed point
        twice = migrate_to_overlays(overlays_to_legacy(once))
        assert twice == once, f"round trip drifted for {case}"


def test_every_saved_project_on_disk_still_opens():
    """
    The fixture is whatever is actually in 03_Projects: these are the files a
    user would lose if the conversion missed a shape.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.overlay_model import migrate_to_overlays

    projects = sorted((ROOT / "03_Projects").glob("*/project.json"))
    if not projects:
        pytest.skip("no saved projects to migrate")
    for path in projects:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for overlay in migrate_to_overlays(manifest):
            assert overlay["kind"] in ("hook", "text"), path.name
            assert overlay["tiers"], f"{path.name}: an overlay with no tiers draws nothing"
            assert overlay["end"] >= overlay["start"], path.name
            # a banner keeps all three tiers even when only one carries text
            if overlay["kind"] == "hook":
                assert len(overlay["tiers"]) == 3, path.name


def test_font_weights_match_and_lose_nothing_from_the_banners_old_table():
    """
    Asking a face for a weight it does not ship gets a synthesised bold that
    is heavier than the render's, so the weight per family is a table, not a
    guess. It used to live in SequencePlayer.jsx as HOOK_FONT_WEIGHTS and
    covered only the banner; the shared one has to keep every family that
    table knew, or a banner regresses the moment the old copy goes away.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.overlay_model import DEFAULT_FONT_WEIGHT, FONT_WEIGHTS

    def _weights(source, pattern):
        block = re.search(pattern, source, re.S).group(1)
        found = {}
        for key, value in re.findall(r"[\"']?([A-Za-z][A-Za-z ]*)[\"']?\s*:\s*(\d+)", block):
            found[key.strip()] = int(value)
        return found

    js = _weights(OVERLAY_JS, r"export const FONT_WEIGHTS = \{(.*?)\n\};")
    assert js == FONT_WEIGHTS, f"python {FONT_WEIGHTS} vs js {js}"

    legacy = _weights(JS_SRC, r"const HOOK_FONT_WEIGHTS = \{(.*?)\n\};") if \
        "HOOK_FONT_WEIGHTS" in JS_SRC else {}
    for family, weight in legacy.items():
        assert FONT_WEIGHTS.get(family) == weight, \
            f"{family} was {weight} for the banner and is {FONT_WEIGHTS.get(family)} now"

    # The ids the editor actually stores must resolve, not fall through to the
    # default: fontName 'IBMPlex' is what a text overlay saves.
    for stored_id in ("Kanit", "Prompt", "IBMPlex", "NotoSansThai"):
        assert stored_id in FONT_WEIGHTS, f"{stored_id} would fall back to {DEFAULT_FONT_WEIGHT}"
