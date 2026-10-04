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
import math
import re
import sys
from pathlib import Path

import pytest
from scripts.config import VIDEO_HEIGHT, VIDEO_WIDTH

ROOT = Path(__file__).resolve().parent.parent
PY_SRC = ""
for _sub in sorted((ROOT / "scripts" / "subtitle").glob("*.py")):
    PY_SRC += _sub.read_text(encoding="utf-8") + "\n"
PY_SRC += (ROOT / "scripts" / "subtitle_engine.py").read_text(encoding="utf-8")
JS_SRC = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
TIMELINE_SRC = (ROOT / "frontend" / "src" / "components" / "editor" / "Timeline.jsx").read_text(encoding="utf-8")
TRACK_LABEL_SRC = (ROOT / "frontend" / "src" / "components" / "editor" / "timeline" / "TrackLabel.jsx").read_text(encoding="utf-8")
RECOLOR_PY_SRC = (ROOT / "scripts" / "overlay_recolor.py").read_text(encoding="utf-8")
RECOLOR_JS_SRC = (ROOT / "frontend" / "src" / "lib" / "overlayRecolor.js").read_text(encoding="utf-8")


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


def test_paused_high_resolution_preview_uses_master_at_render_dimensions():
    logical_width = _grab(JS_SRC, r"const CANVAS_W = (\d+)", int)
    logical_height = _grab(JS_SRC, r"const CANVAS_H = (\d+)", int)
    scale = _grab(JS_SRC, r"const HIGH_RES_PREVIEW_SCALE = (\d+)", int)
    assert logical_width * scale == VIDEO_WIDTH == 1080
    assert logical_height * scale == VIDEO_HEIGHT == 1920
    assert "canvas.width = CANVAS_W * HIGH_RES_PREVIEW_SCALE;" in JS_SRC
    assert "canvas.height = CANVAS_H * HIGH_RES_PREVIEW_SCALE;" in JS_SRC
    capture_start = JS_SRC.index("const captureHighResolutionFrame = async")
    capture_end = JS_SRC.index("  useEffect(() => {", capture_start)
    capture_source = JS_SRC[capture_start:capture_end]
    assert "loadCoverVideo(toMediaUrl(clip.source_path), entry.localTime)" in capture_source
    assert "renderAt(t, { canvas, offscreen, videos, isolated, cutoutMode });" in capture_source
    assert "PlayResX: {video_width}" in PY_SRC
    assert "PlayResY: {video_height}" in PY_SRC
    assert "SequencePlayer's" in PY_SRC and "full export raster" in PY_SRC


def test_playback_quality_changes_raster_without_changing_logical_geometry():
    quality_src = (ROOT / "frontend/src/lib/previewQuality.js").read_text(encoding="utf-8")
    assert "export const MASTER_PREVIEW = 'master1080'" in quality_src
    assert "export const SMOOTH_PREVIEW = 'smooth540'" in quality_src
    assert "=== MASTER_PREVIEW ? 2 : 1" in quality_src
    assert "width={CANVAS_W * backingScale}" in JS_SRC
    assert "height={CANVAS_H * backingScale}" in JS_SRC
    assert "ctx.setTransform(backingScale, 0, 0, backingScale, 0, 0)" in JS_SRC
    assert "previewPlaybackUrl(subjectPickMode ? MASTER_PREVIEW : previewQuality, toMediaUrl(c.source_path), clipSources[c.id])" in JS_SRC
    assert "cutoutPlaybackSource(previewQuality, resolution)" in JS_SRC
    assert "Master playback and paused inspection both rasterize at 1080x1920" in PY_SRC


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

    The conversion USED TO live purely on the ASS side, as a \\fscx/\\fscy
    boost with Fontsize left at the plain em number -- but scaling a glyph up
    via \\fscx/\\fscy after rasterization breaks libass's GPOS mark-to-mark
    anchor delta ั+่ ("นั่ง") depends on, worse the more it scales, regardless
    of Bold (empirically diagnosed 2026-09-08 -- see font_size_boosted's
    comment in subtitle_engine.py). The fix boosts Fontsize itself (so the
    glyph rasterizes fresh at its true final size) and divides \\fscx/\\fscy
    by that same boost instead of multiplying by it -- the two numerically
    cancel to the identical rendered size and line-gap as before (verified
    pixel-identical against the old scheme for both a plain caption line and
    the hook banner), but avoid the post-rasterization transform that broke
    the anchor. The canvas keeps drawing the plain em number either way,
    since canvas text has no such post-rasterization transform to begin with.
    """
    assert "_sfnt_ass_glyph_scale" in PY_SRC
    assert "units_per_em / line_box" in PY_SRC
    assert "TEXT_SCALE_BOOST = 1.0 / ass_glyph_scale(resolved_font)" in PY_SRC
    # The banner has its own face now, so it needs the boost of THAT face: a
    # font's line box against its em is what the boost cancels, and reusing the
    # caption's number would size the banner by the wrong metrics.
    assert "HOOK_SCALE_BOOST = 1.0 / ass_glyph_scale(hook_font)" in PY_SRC

    # Fontsize fields carry the boost now (rasterize fresh at true size)
    assert "font_size_boosted = int(round(font_size * TEXT_SCALE_BOOST))" in PY_SRC
    assert "hook_fs_boosted = int(round(hook_fs * HOOK_SCALE_BOOST))" in PY_SRC

    # every \fscx/\fscy that used to carry the boost now stays at the plain
    # (unboosted) percent, since Fontsize alone accounts for it
    for probe in [
        "target = layout_pct",                    # hook tiers
        "en_pct = 68",                             # english sub
        "spec_from = 110",                         # spec bar
        "spec_to = 100",                           # spec bar settle
    ]:
        assert probe in PY_SRC, f"missing plain (unboosted) fscx/fscy: {probe}"

    # Fontsize itself must stay the em number in the canvas-facing formula;
    # the boosted variant is a separate, explicitly-named value
    assert "hook_fs = int(round(video_width * 0.065))" in PY_SRC

    # \p drawings are already in PlayRes pixels and must NOT be boosted
    drawing_block = PY_SRC.split("def _hook_accent_events")[1].split("\ndef ")[0]
    assert "TEXT_SCALE_BOOST" not in drawing_block, "accent drawings must not take the text boost"


def test_caption_fade_animation_matches_and_is_thai_safe():
    """
    Captions enter with a 70ms alpha fade in both engines. A geometric
    \fscx/\fscy pop is deliberately forbidden here because libass can apply
    it after shaping and collapse stacked Thai marks such as ั + ่ in นั่ง.
    """
    assert 'caption_anim = r"{\\alpha&HFF&\\t(0,70,\\alpha&H00&)}"' in PY_SRC
    assert _grab(JS_SRC, r"const CAPTION_FADE_MS = (\d+);") == 70
    assert "\\\\fscx{snap_pct}" not in PY_SRC
    assert "const CAPTION_POP_FROM" not in JS_SRC


def test_thai_caption_face_is_explicit_and_mirrored():
    """IBM body captions must use the same SemiBold cut in both engines."""
    assert '"IBM Plex Sans Thai": ("IBM Plex Sans Thai SemiBold", 0)' in PY_SRC
    assert 'caption_font, caption_bold = ass_caption_face(resolved_font)' in PY_SRC
    assert 'Style: TikTokWhite,{caption_font}' in PY_SRC
    assert "fontWeight = '600';" in JS_SRC
    assert "function drawCaptionText(ctx, text, x, y, fontSize, drawText, repairThaiMarks = true)" in JS_SRC
    assert "drawText(match[2], toneX" in JS_SRC
    assert "ctx.measureText(base).width;" in JS_SRC
    assert _grab(PY_SRC, r'THAI_UPPER_VOWELS = "([^\"]+)"', str) == _grab(
        JS_SRC, r"const THAI_UPPER_VOWELS = '([^']+)';", str
    ).lower()
    assert _grab(PY_SRC, r'THAI_TONE_MARKS = "([^\"]+)"', str) == _grab(
        JS_SRC, r"const THAI_TONE_MARKS = '([^']+)';", str
    ).lower()
    assert _grab(PY_SRC, r"THAI_STACKED_MARK_RAISE_EM = ([\d.]+)") == _grab(
        JS_SRC, r"const THAI_STACKED_MARK_RAISE_EM = ([\d.]+);"
    )
    assert "fontSize * THAI_STACKED_MARK_RAISE_EM" in JS_SRC
    assert "return repair_thai_stacked_marks(value)" in PY_SRC
    assert "THAI_STACKED_MARK_RE" in JS_SRC
    assert "const repairThaiMarks = true;" in JS_SRC
    assert "hidden_mark_components" in PY_SRC
    assert "caption_mark_overlay(mark_parts" in PY_SRC


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
    assert ass_top == 180.0 / 1920.0
    assert "HOOK_TOP_Y = 180.0 / 1920.0" in OVERLAY_JS
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
        ("bounce_soft", r"def _in_bounce_soft.*?end_ms = t0_ms \+ (\d+)"),
        ("pop", r"def _in_pop.*?end_ms = t0_ms \+ (\d+)"),
        ("pop_soft", r"def _in_pop_soft.*?end_ms = t0_ms \+ (\d+)"),
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


def test_easing_accel_constants_and_byte_identity_parity():
    """
    ACCEL constants must match between motion_effects.py and SequencePlayer.jsx,
    and linear keyframes (accel=1.0) must serialize to byte-identical legacy ASS tags.
    """
    assert _grab(PY_SRC, r"ACCEL_SOFT_OUT = ([\d.]+)") == _grab(JS_SRC, r"const ACCEL_SOFT_OUT = ([\d.]+);")
    assert _grab(PY_SRC, r"ACCEL_SNAP_IN = ([\d.]+)") == _grab(JS_SRC, r"const ACCEL_SNAP_IN = ([\d.]+);")

    from scripts.subtitle.motion_effects import _in_bounce, _in_pop, _in_fade, _in_pop_soft, _in_bounce_soft
    tag_bounce, end_bounce, _ = _in_bounce(236, 0)
    # bounce/pop are eased (round EDITOR-CUT-QUALITY-R2): same keyframe times
    # and values as the old linear version, only the 0.6 accel is added.
    assert tag_bounce == r"\fscx142\fscy142\t(0,150,0.6,\fscx295\fscy295)\t(150,280,0.6,\fscx217\fscy217)\t(280,380,0.6,\fscx248\fscy248)\t(380,450,0.6,\fscx236\fscy236)"
    assert end_bounce == 450

    tag_pop, end_pop, _ = _in_pop(236, 0)
    assert tag_pop == r"\fscx130\fscy130\t(0,120,0.6,\fscx278\fscy278)\t(120,200,0.6,\fscx236\fscy236)"
    assert end_pop == 200

    # The serializer itself still emits byte-identical legacy tags for accel=1.0.
    from scripts.subtitle.motion_effects import serialize_keyframes
    assert serialize_keyframes([(0, {"fscx": 142}, 1.0), (150, {"fscx": 295}, 1.0)]) == r"\fscx142\t(0,150,\fscx295)"

    tag_fade, end_fade, _ = _in_fade(236, 0)
    assert tag_fade == r"\fscx236\fscy236\alpha&HFF&\t(0,250,\alpha&H00&)"
    assert end_fade == 250

    # Verify soft presets carry the accel tag
    tag_pop_soft, _, _ = _in_pop_soft(236, 0)
    assert r"\t(0,120,0.6,\fscx278\fscy278)" in tag_pop_soft
    assert r"\t(120,200,2.2,\fscx236\fscy236)" in tag_pop_soft



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
    Hook text lines must derive alpha purely from (lineInFx.alpha * loopFx.alpha * outFx.alpha)
    without an unmodeled artificial 300ms exit ramp or 200ms entry ramp that
    distorts parity with the ASS render.
    """
    assert "ctx.globalAlpha = (lineInFx.alpha ?? 1) * (loopFx.alpha ?? 1) * (outFx.alpha ?? 1);" in JS_SRC
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
         r"scale: hookKeyframeAt\(\(t - s\) \* 1000, \[\[0, 1\], \[\(e - s\) \* 1000, ([\d.]+)(?:, ACCEL_SNAP_IN)?\]\]\)"),
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
        # Editor ids are transient: save strips them, while scoped Cutout
        # sends them only with the render request to bind active clips.
        leaked = dropped & (_render_clip_fields() - {"id"})
        assert not leaked, f"save path drops fields the renderer reads: {leaked}"
    assert "serializeRenderClips(clipList, effectiveBgIsolation?.scope_mode)" in EDITOR_SRC
    assert "id: clipList[index]?.id" in PROJECT_STATE_SRC


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


def test_project_voice_and_sfx_levels_reach_preview_and_render_alike():
    """
    L4-05: the Track Mix voice/SFX sliders are one value read by both sides.
    The editor sends the clamped level as ``audioStems.voiceVolume/sfxVolume``
    (preview buses) and as ``voice_volume/sfx_volume`` in the saved style
    (manifest -> AudioMixStage -> the ffmpeg ``volume=``). Both clamp to the
    same [0, 1] ceiling and fall back to the same config defaults, checked
    here by running the shipped JS against the shipped Python on one table.
    """
    import json
    import shutil
    import subprocess
    import tempfile

    from scripts.pipeline_context import bus_volume_override
    from scripts.sfx_manager import _clamp_gain

    levels_src = (ROOT / "frontend" / "src" / "lib" / "audioBusLevels.js").read_text(encoding="utf-8")
    assert _grab(levels_src, r"VOICE_VOLUME_DEFAULT = ([\d.]+)") == _grab(CONFIG_SRC, r"VOICE_VOLUME = ([\d.]+)")
    assert _grab(levels_src, r"SFX_VOLUME_DEFAULT = ([\d.]+)") == _grab(CONFIG_SRC, r"SFX_VOLUME = ([\d.]+)")
    assert "BUS_VOLUME_MAX = 1;" in levels_src and "BUS_VOLUME_MIN = 0;" in levels_src

    base = re.search(r"const trackBase = \{(.*?)\};", JS_SRC, re.S).group(1)
    assert "voice: mixBusGain(audioStems?.voiceVolume, AUDIO_MIX.VOICE_GAIN)" in base
    assert "sfx: mixBusGain(audioStems?.sfxVolume, AUDIO_MIX.SFX_GAIN)" in base
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert "voiceVolume: clampBusVolume(style.voiceVolume, VOICE_VOLUME_DEFAULT)" in shell
    assert "sfxVolume: clampBusVolume(style.sfxVolume, SFX_VOLUME_DEFAULT)" in shell
    # A level change has to send the render down the re-mix ("bgm") path.
    assert "clampBusVolume(style.voiceVolume, VOICE_VOLUME_DEFAULT) !== clampBusVolume(base.voiceVolume" in shell
    state_src = (ROOT / "frontend" / "src" / "lib" / "editorProjectState.js").read_text(encoding="utf-8")
    assert "voice_volume: clampBusVolume(style.voiceVolume, VOICE_VOLUME_DEFAULT)" in state_src
    assert "sfx_volume: clampBusVolume(style.sfxVolume, SFX_VOLUME_DEFAULT)" in state_src

    if not shutil.which("node"):
        pytest.skip("needs node")
    inputs = [None, 0, 0.5, 0.28, 1, 1.5, -0.3, "0.4", "abc"]
    runner = """
import { readFileSync } from 'node:fs';
const src = readFileSync(process.argv[2], 'utf8');
const fn = src.match(/function mixBusGain\\([\\s\\S]*?\\n\\}/)[0];
const m = await import('data:text/javascript;base64,' + Buffer.from(fn + '\\nexport { mixBusGain };').toString('base64'));
const lib = await import(new URL('file:///' + process.argv[3].replace(/\\\\/g, '/')).href);
const inputs = JSON.parse(process.argv[4]);
console.log(JSON.stringify(inputs.map((v) => [
  m.mixBusGain(v, 1.0), m.mixBusGain(v, 0.28),
  lib.clampBusVolume(v, 1.0), lib.clampBusVolume(v, 0.28),
])));
"""
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "levels.mjs"
        script.write_text(runner, encoding="utf-8")
        proc = subprocess.run(
            ["node", str(script), str(ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx"),
             str(ROOT / "frontend" / "src" / "lib" / "audioBusLevels.js"), json.dumps(inputs)],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    assert proc.returncode == 0, proc.stderr
    js = json.loads(proc.stdout)
    for value, (pv_voice, pv_sfx, lib_voice, lib_sfx) in zip(inputs, js):
        # What the render's mix stage hands ffmpeg: the override, else default,
        # then the policy's own clamp.
        render_voice = _clamp_gain(_or(bus_volume_override({"voice_volume": value}, "voice_volume"), 1.0), 1.0)
        render_sfx = _clamp_gain(_or(bus_volume_override({"sfx_volume": value}, "sfx_volume"), 0.28), 0.28)
        assert pv_voice == lib_voice == render_voice, (value, pv_voice, lib_voice, render_voice)
        assert pv_sfx == lib_sfx == render_sfx, (value, pv_sfx, lib_sfx, render_sfx)


def _or(value, default):
    return default if value is None else value


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


def test_ducking_depth_is_documented_as_an_approximation():
    """
    The preview's 13.7 dB is a fixed gain over the cue spans; the render's
    sidechaincompress reacts to the voice's actual level, so the two cannot
    match exactly.

    Measured on 2026-09-26 with a validated method (a control applying a known
    0.2065 gain read back as exactly 13.70 dB): the render pulls the music
    down 8.3 dB against a speech-like key and 10.4 dB against a steady one,
    versus the preview's flat 13.7 dB -- a residual of roughly 3.3 to 5.4 dB,
    with the preview always ducking harder.

    This test pins the fact that the gap is known and bounded rather than
    asserting the two are equal, which they are not. If the filter's
    threshold/ratio change, re-measure and update both the figure in
    sfx_manager.py and the range here.
    """
    measured_db = _grab(SFX_SRC, r"pull the music down ([\d.]+) dB")
    preview_db = -20 * math.log10(_js_audio_mix("BGM_DUCK_GAIN"))

    # Preview and render are configured from the same figure...
    assert abs(preview_db - measured_db) < 0.2
    # ...but the render's real depth is lower, because a compressor only
    # reaches its full ratio while the key is loud. Keep the documented
    # residual within the range that was actually measured.
    RENDER_DEPTH_RANGE_DB = (8.3, 10.4)
    residual_low = preview_db - RENDER_DEPTH_RANGE_DB[1]
    residual_high = preview_db - RENDER_DEPTH_RANGE_DB[0]
    assert 3.0 <= residual_low <= 4.0, f"residual floor drifted: {residual_low:.2f} dB"
    assert 5.0 <= residual_high <= 6.0, f"residual ceiling drifted: {residual_high:.2f} dB"


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
    assert "if (isPlaying && !subjectPickMode) startStems()" in body


def test_playback_paints_once_per_export_frame():
    """
    L6-03: a 60/120/144 Hz display used to repaint the whole scene every
    refresh for a 30 fps export. The paint now waits for the next output
    frame of the export rate; audio/drift work still runs every callback.
    """
    from scripts.config import FPS

    rate = re.search(r"const PREVIEW_PAINT_FPS = (\d+);", JS_SRC)
    assert rate and int(rate.group(1)) == FPS
    tick = JS_SRC[JS_SRC.index("const tick = () => {"):JS_SRC.index("rafRef.current = requestAnimationFrame(tick);")]
    assert "const outputFrame = Math.floor(t * PREVIEW_PAINT_FPS);" in tick
    assert "outputFrame === lastPaintedFrameRef.current ? null" in tick
    # Drift correction and SFX scheduling stay ahead of the paint gate.
    assert tick.index("pumpSfx(t)") < tick.index("const outputFrame")
    assert tick.index("v.playbackRate = baseRate") < tick.index("const outputFrame")
    # A frame whose decoder was not ready is retried, not held blank.
    assert "if (framePainted || plan.length === 0) lastPaintedFrameRef.current = outputFrame;" in tick


def test_clip_edits_reload_only_when_the_source_changes():
    """
    L6-01/L6-02 with Phase-2 B2: a slider step on zoom/pan/colour used to
    reload metadata and stop playback (only the picture stopped -- the stems
    played on). The metadata reload is keyed on the source files alone, its
    stop path stops the stems too, and the redraw key covers every clip field
    so nothing that changes the picture (speed, freeze_tail, ...) is missed.
    """
    assert "const clipVisualKey = JSON.stringify(clips);" in JS_SRC
    timing = re.search(r"const clipTimingKey = clips\.map\(c => `([^`]*)`\)", JS_SRC)
    assert timing
    for field in ("trim_start", "trim_end", "speed", "freeze_tail", "transition_in", "transition_duration"):
        assert f"c.{field}" in timing.group(1), field
    assert re.search(r"const clipAudioKey = clips\.map\(c => `[^`]*c\.volume[^`]*`\)", JS_SRC)

    meta = re.search(r"// Load real duration for every clip up front(.*?)\n  \}, \[clipSourceKey\]\);", JS_SRC, re.S)
    assert meta, "metadata effect must be keyed on clipSourceKey"
    assert "stopStems();" in meta.group(1)
    assert "setIsPlaying(false)" not in meta.group(1).replace("stopStems();\n      setIsPlaying(false);", "")
    assert re.search(r"\[clipVisualKey, metadataReady, durations\]", JS_SRC)
    assert re.search(r"if \(audioCtxRef\.current\) wireClipAudio\(\);\n.*\n  \}, \[clipAudioKey\]\);", JS_SRC)


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
    # R2 lane TM: the fitted 1/6 / 0.2667 curve was replaced by vf_xfade.c's
    # own formula (phase 0.2), proven pixel-equal by tests/test_transition_easing.py.
    assert _grab(JS_SRC, r"FADE_BRIDGE_PHASE = ([\d.]+);") == 0.2
    from scripts.video_editor import xfade_custom_body
    assert "clip(((P)-0.8)/0.2,0,1)" in xfade_custom_body("fadeblack", "(P)")
    assert "clip(((P)-0.2)/0.8,0,1)" in xfade_custom_body("fadeblack", "(P)")
    paint = re.search(r"if \(painted && role === 'out' && \(kind === 'fadeblack'(.*?)\n    \}", JS_SRC, re.S)
    assert paint, "the bridge colour is never laid down"
    assert "fadewhite' ? '#FFFFFF' : '#000000'" in paint.group(1)
    # Paint-order alpha: the colour goes over the outgoing clip, and the
    # incoming clip then blends over both -- so its cover has to be rescaled.
    assert "bridge / (1 - wB)" in paint.group(1)


def test_dissolve_reveals_per_pixel_and_never_goes_backwards():
    """
    Measured: the revealed share equals progress, no pixel ever reverts as
    progress grows, and the grain is per-pixel rather than blocky. The preview
    mirrors FFmpeg's single-precision frand hash at export coordinates; a real
    monochrome FFmpeg mask test covers its spatial agreement.
    """
    fn = re.search(r"function dissolveMaskFor\((.*?)\n\}", JS_SRC, re.S)
    assert fn
    body = fn.group(1)
    assert "const threshold = Math.max(0, Math.min(1, progress))" in body, "share must equal progress"
    assert "dissolveNoise[i] < threshold" in body, "a fixed hash with an increasing threshold keeps reveal monotonic"
    assert "const width = CANVAS_W * scale" in body
    assert "const height = CANVAS_H * scale" in body
    assert "Math.fround" in body
    assert "HIGH_RES_PREVIEW_SCALE / scale" in body
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
    tick = re.search(
        r"if \(framePainted\) applyGrade\(ctx, canvas\);\s*\n"
        r"\s*(?:drawSpotlight\(ctx, previewSpotlight\);\s*\n\s*)?drawSticker",
        JS_SRC,
    )
    assert tick, "the grade must run after the video layers and before the badge"
    still = re.search(
        r"applyGrade\(ctx, canvas\);\s*\n"
        r"(?:\s*//[^\n]*\n)*\s*"
        r"(?:drawSpotlight\(ctx, previewSpotlight\);\s*\n\s*)?drawSticker",
        JS_SRC,
    )
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


def test_preview_and_render_use_the_same_overlay_scrim_opacity():
    """The Hook backdrop must dim the same amount in Canvas and FFmpeg."""
    assert "grad.addColorStop(0, `rgba(0,0,0,${0.75 * alpha})`)" in JS_SRC

    editor = (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    assert "OVERLAY_SCRIM_OPACITY = 0.75" in editor
    assert "scrim_alpha = 255 * OVERLAY_SCRIM_OPACITY" in editor
    assert 'f"{scrim_alpha:g}*(1-Y/H)*' in editor


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
    """Preview and Export derive the same audible buses from mute and solo."""
    assert "effectiveAudioMutes(trackMix)" in JS_SRC
    base = re.search(r"const trackBase = \{(.*?)\};", JS_SRC, re.S)
    assert base, "the per-track levels moved"
    for track in ("voice", "bgm", "sfx", "clip"):
        assert f"{track}:" in base.group(1), f"{track} has no level in the track mix"
    assert "AUDIO_MIX.VOICE_GAIN" in base.group(1)
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert "if (kind === 'mute' && turningOn) next.solo[k] = false;" in shell
    assert "if (kind === 'solo' && turningOn) next.mute[k] = false;" in shell
    assert "const audioMutes = effectiveAudioMutes(trackMix);" in shell
    assert "audio_mutes: audioMutes" in shell
    assert "!!audioMutes[track] !== !!baselineMutes[track]" in shell


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
    assert 'style={{ width: slotWidth }}' in TRACK_LABEL_SRC
    assert 'slotWidth = 26' in TRACK_LABEL_SRC, 'the slot needs a default for rows that pass none'
    # Every caller hands the same width in, so no row can indent differently.
    assert TIMELINE_SRC.count('slotWidth={dense ? 14 : 26}') == 8


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
    assert "aria-expanded={!fold.collapsed}" in TRACK_LABEL_SRC


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
    assert "style={{ width: width ?? GUTTER }}" in TRACK_LABEL_SRC
    assert "dot={dense ? undefined : { colour, hollow: silent }}" in TIMELINE_SRC
    # ...and the leading slot narrows with it, so the names stay flush.
    assert TIMELINE_SRC.count("slotWidth={dense ? 14 : 26}") == 8
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
    assert "AUDIO_TRACKS" in SHELL_SRC
    assert "export const AUDIO_TRACKS = Object.freeze(['voice', 'bgm', 'sfx', 'clip']);" in (
        ROOT / "frontend" / "src" / "lib" / "trackMix.js"
    ).read_text(encoding="utf-8")
    # A third chip does not fit beside a name on a phone, and the row's own M
    # already mutes all four once folded.
    assert "{i === 0 && !dense && !audioCollapsed && (" in TIMELINE_SRC


def test_render_baseline_only_commits_after_success_and_save_failure_stops_export():
    assert "await updateProjectState(projectName, projectSavePayload);" in SHELL_SRC
    assert "await updateProjectState(projectName, projectSavePayload).catch(() => {})" not in SHELL_SRC
    completion = SHELL_SRC.split("const handleRenderComplete = useCallback(", 1)[1].split(
        "const handleRenderError = useCallback(", 1
    )[0]
    assert "loadedAudioMutes.current = pending.audioMutes;" in completion
    assert "loadedCaptionStyle.current = pending.captionStyle;" in completion
    assert "pendingRenderBaseline.current = null;" in completion


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
const trackMixSrc = readFileSync(process.argv[3], 'utf8');
const grab = (re, what) => { const m = src.match(re); if (!m) throw new Error('missing ' + what); return m[0]; };
const code = `
${grab(/const AUDIO_MIX = \\{[\\s\\S]*?\\n\\};/, 'AUDIO_MIX')}
${grab(/function mixBusGain\\([\\s\\S]*?\\n\\}/, 'mixBusGain')}
${trackMixSrc.match(/export const AUDIO_TRACKS[^;]*;/)[0].replace('export ', '')}
${trackMixSrc.match(/export function effectiveAudioMutes[\\s\\S]*?\\n}/)[0].replace('export ', '')}
export function scope({ trackMix, bgmVolume, cues, totalDuration }) {
  const audioStems = null;  // project levels absent -> AUDIO_MIX defaults
  const mk = () => ({ gain: { value: 0, cancelScheduledValues() {}, setTargetAtTime(v) { this.value = v; } } });
  const ctx = { currentTime: 0, state: 'running' };
  const audioCtxRef = { current: ctx };
  const audioNodesRef = { current: { bgm: mk(), voice: mk(), sfx: mk(), clip: mk() } };
  ${grab(/const effectiveMutes = [\\s\\S]*?const trackLevel = \\(track\\) => \\([\\s\\S]*?\\);/, 'trackLevel')}
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
        res = subprocess.run(
            ["node", str(path), str(player), str(ROOT / "frontend" / "src" / "lib" / "trackMix.js")],
            capture_output=True, text=True,
        )
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
    blur_branch = VIDEO_EDITOR_SRC[VIDEO_EDITOR_SRC.index("elif use_bg_blur:"):]
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
        assert js_tpl.get("motion") == py_tpl.get("motion"), f"{name}: motion differs"
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


def test_style_preset_visual_palette_reaches_both_preview_and_ass():
    """A selected style must be a live visual input, not manifest metadata only."""
    sequence_src = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
    catalog_src = (ROOT / "frontend" / "src" / "lib" / "stylePresetCatalog.js").read_text(encoding="utf-8")
    policy_src = (ROOT / "scripts" / "style_motion_policy.py").read_text(encoding="utf-8")
    assert "getStylePreset(stylePreset)" in sequence_src
    assert "drawOverlays(ctx, overlaysBehindSubject, t, previewAccentColor" in sequence_src
    assert "drawOverlays(ctx, overlaysInFront, t, previewAccentColor" in sequence_src
    assert "stylePreset={activeStylePreset}" in (
        ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx"
    ).read_text(encoding="utf-8")
    assert "style_preset=ctx.style_preset" in (
        ROOT / "scripts" / "stages" / "subtitle_stage.py"
    ).read_text(encoding="utf-8")
    assert "style_visual_palette(ctx.get(\"style_preset\"))" in (
        ROOT / "scripts" / "subtitle" / "overlay_events.py"
    ).read_text(encoding="utf-8")
    expected_accents = {
        "viral_punch": "#FE2C55",
        "clean_tech_review": "#FFE600",
        "tech_product_showcase": "#FFCC33",
        "smooth_showcase": "#25F4EE",
        "premium_minimal": "#E6C24A",
    }
    for preset_id, accent in expected_accents.items():
        assert f"'{preset_id}'" in catalog_src
        assert f"accent: '{accent}'" in catalog_src
        assert f'"{preset_id}": StyleMotionPolicy(' in policy_src
        assert f'accent_color="{accent}"' in policy_src


def test_baked_overlay_recolor_uses_the_same_explicit_hue_contract():
    """Canvas and FFmpeg must tint only opted-in media with the same source hue."""
    assert "drawMediaWithAccentRecolor" in JS_SRC
    assert "hue-rotate(" in RECOLOR_JS_SRC
    assert "build_overlay_hue_filter" in (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    assert "hue=h=" in RECOLOR_PY_SRC
    assert "DEFAULT_EFFECT_SOURCE_HUE = 205" in RECOLOR_PY_SRC
    assert "DEFAULT_EFFECT_SOURCE_HUE = 205" in RECOLOR_JS_SRC
    assert "recolor: 'accent'" in (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert '"recolor": fx.get("recolor", fx.get("tint"))' in (ROOT / "scripts" / "video_editor.py").read_text(encoding="utf-8")


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
    # Style Fontsize carries the boost now, so \fscx/\fscy divide by it
    # instead of multiplying (see font_size_boosted's comment)
    assert "target = layout_pct" in PY_SRC
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
    assert "overlays," in shell and "serializeOverlays(overlays)" in PROJECT_STATE_SRC
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
    sub_src = PY_SRC
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
    """Parity rule 2.8: ASS MarginV 180/1920 against canvas y 90/960."""
    assert "HOOK_TOP_Y = 180.0 / 1920.0" in OVERLAY_PY
    assert "HOOK_TOP_Y = 180.0 / 1920.0" in OVERLAY_JS
    assert 180.0 / 1920.0 == 90.0 / 960.0


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


def test_text_look_fields_and_defaults_match_on_both_sides():
    py_fields = set(re.findall(r'"([a-z_]+)"', re.search(r"TEXT_LOOK_FIELDS[^=]*= \((.*?)\)", OVERLAY_PY, re.S).group(1)))
    js_fields = set(re.findall(r"'([a-z_]+)'", re.search(r"TEXT_LOOK_FIELDS = \[(.*?)\];", OVERLAY_JS, re.S).group(1)))
    assert py_fields == js_fields, f"TEXT_LOOK_FIELDS mismatch: py {py_fields} vs js {js_fields}"

    py_default = re.search(r"DEFAULT_TEXT_LOOK[^=]*= \{(.*?)\}", OVERLAY_PY, re.S).group(1)
    js_default = re.search(r"DEFAULT_TEXT_LOOK = \{(.*?)\};", OVERLAY_JS, re.S).group(1)
    extract_keys = lambda b: set(re.findall(r'["\']?([a-z_]+)["\']?\s*:', b))
    assert extract_keys(py_default) == extract_keys(js_default)



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


def test_subtitle_engine_styles_spacing_is_zero():
    """Every ASS Style row must declare Spacing=0 (not 0.5) to avoid Thai glyph corruption and preview drift."""
    sub_engine_src = (ROOT / "scripts" / "subtitle_engine.py").read_text(encoding="utf-8")
    style_lines = re.findall(r"^Style:\s*([^\n]+)", sub_engine_src, re.M)
    assert style_lines, "Must have Style declarations in subtitle_engine.py"
    for line in style_lines:
        parts = [p.strip() for p in line.split(",")]
        # Format: Name(0), Fontname(1), Fontsize(2), PrimaryColour(3), SecondaryColour(4),
        # OutlineColour(5), BackColour(6), Bold(7), Italic(8), Underline(9), StrikeOut(10),
        # ScaleX(11), ScaleY(12), Spacing(13)
        assert len(parts) >= 14, f"Malformed style line: {line}"
        spacing = parts[13]
        assert spacing == "0", f"Style {parts[0]} Spacing must be 0, got {spacing}"


def test_font_metrics_advance_width_parity():
    """_measure_text_width_px uses advance width, and prefix_advances returns monotonic cumulative advances."""
    from scripts.subtitle.font_metrics import _measure_text_width_px, prefix_advances

    tokens = ["ทดสอบ", "ข้อความ", "หลายคำ"]
    advances = prefix_advances(tokens, "Kanit", 75)
    assert advances is not None
    assert len(advances) == len(tokens) + 1
    assert advances[0] == 0.0
    for i in range(1, len(advances)):
        assert advances[i] > advances[i - 1], "Cumulative advances must be strictly increasing"

    total_w = _measure_text_width_px("".join(tokens), "Kanit", 75)
    assert abs(advances[-1] - total_w) < 1.0, f"prefix sum {advances[-1]} vs measured {total_w}"


def test_text_overlay_events_wires_loop_out_and_skew():
    """Text overlay ASS events must thread anim.loop, anim.out, and look.skew correctly."""
    from scripts.subtitle.overlay_events import _text_overlay_events

    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "base_fs": 50,
        "resolved_font": "Kanit",
        "font_map": {},
        "caption_color": "#0000E6FF",
    }
    item = {
        "kind": "text",
        "start": 0.0,
        "end": 3.0,
        "x": 0.5,
        "y": 0.5,
        "tiers": [{
            "text": "ข้อความ ทดสอบ",
            "look": {"font": "Kanit", "size_pct": 100, "skew": -0.25},
        }],
        "anim": {
            "in": "snap",
            "loop": "pulse",
            "out": "slide",
            "word_stagger_ms": 50,
        },
    }

    events = _text_overlay_events(item, ctx)
    assert events, "Events must not be empty"

    all_dialogues = "\n".join(events)
    # Check skew tag \fax
    assert r"\fax-0.25" in all_dialogues, "Skew tag \\fax-0.25 must be present in dialogue tags"
    # Check loop pulse (contains alpha oscillation \t(...,\alpha...)
    assert r"\alpha&H" in all_dialogues and r"\t(" in all_dialogues, "Loop animation tags must be generated"
    # Check out slide (contains \move with exit offset dy 60)
    assert r"\move(" in all_dialogues, "Slide out must use \\move tag for exit animation"


def test_hook_overlay_guarded_against_per_word_layout():
    """
    Hook Header (overlay.kind === 'hook') must never be split into words or request
    overlay.layout, which would crush Thai words/kerning horizontally into clumps.
    Only text overlays with word_stagger_ms > 0 may run word layout.
    """
    assert "const isWordStagger = renderProfile.supportsWordStagger && wordStaggerSec > 0;" in JS_SRC
    assert "if (renderProfile.clearLayout && overlay.layout)" in JS_SRC
    assert "if (isWordStagger && !overlay.layout)" in JS_SRC
    assert "if (isWordStagger && lineWords && lineWords.length > 0)" in JS_SRC


def test_hook_overlay_wrap_parity_contract():
    """
    Regression test for HOOK-HEADER-WRAP-PARITY-FIX-1:
    - Text whose width <= safe boundary (85% of video_width) must NOT be wrapped
      into multiple lines (e.g. Thai text with combining vowels/tones or model text
      calibrated to fit on 1 line).
    - Long text that legitimately exceeds safe boundary (e.g. 145px brand) must wrap
      cleanly to prevent overlap.
    """
    from scripts.subtitle.overlay_events import overlay_events
    from scripts.subtitle.font_metrics import _measure_text_width_px, _resolve_family_font_path

    # Verify Bold font path resolution
    kanit_path = _resolve_family_font_path("Kanit")
    assert kanit_path is not None and "bold" in kanit_path.lower() and "extrabold" not in kanit_path.lower()

    # Model text 'K20 Magnetic SSD 1TB' at 90px must fit in safe width 918px
    w_k20 = _measure_text_width_px("K20 Magnetic SSD 1TB", "Kanit", 90)
    assert w_k20 is not None and w_k20 <= 918

    # Category Thai text 'พื้นที่เก็บข้อมูลในโทรศัพท์' at 63px must fit in safe width 918px
    w_thai = _measure_text_width_px("พื้นที่เก็บข้อมูลในโทรศัพท์", "Kanit", 63)
    assert w_thai is not None and w_thai <= 918

    # Hook Overlay with 3 tiers fitting safe width must emit exactly 3 unique line positions
    hook_overlay = {
        "id": "ovl_hook",
        "kind": "hook",
        "start": 0,
        "end": 5,
        "base_fs_ratio": 0.065,
        "look": {"font": "Kanit", "size_pct": 92},
        "tiers": [
            {"text": "ORICO", "look": {"size_pct": 170}},
            {"text": "K20 Magnetic SSD 1TB", "look": {"size_pct": 140}},
            {"text": "พื้นที่เก็บข้อมูลในโทรศัพท์", "look": {"size_pct": 79}},
        ],
        "anim": {"in": "bounce", "loop": "none", "out": "fade", "accent": "none"},
    }
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "hook_fs": 70,
        "hook_font": "Kanit",
        "caption_color": "#FFFFFF",
        "style_preset": "premium_minimal",
    }
    events = overlay_events(hook_overlay, ctx)
    main_dialogues = [e for e in events if e.startswith("Dialogue: 2,") and "HookHeader," in e]
    assert len(main_dialogues) == 3, f"Expected exactly 3 main dialogues for 3-tier hook, got {len(main_dialogues)}"
    assert "ORICO" in main_dialogues[0]
    assert "K20 Magnetic SSD 1TB" in main_dialogues[1]
    assert "พื้นที่เก็บข้อมูลในโทรศัพท์" in main_dialogues[2]


def test_lightsweep_and_motion_preset_parity_contract():
    """
    Parity contract for lightsweep clip height, typewriter clip height,
    and motion preset in-builders (pop_zoom, quick_fade, etc.).
    """
    from scripts.subtitle.overlay_events import overlay_events
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "hook_fs": 75,
        "hook_font": "Kanit",
        "caption_color": "#FFFFFF",
        "style_preset": "neon_cyber",
    }
    hook_overlay = {
        "id": "ovl_hook",
        "kind": "hook",
        "start": 0,
        "end": 5,
        "tiers": [
            {"text": "IWACHI I6", "look": {"size_pct": 170}},
            {"text": "เมาส์ไร้สาย", "look": {"size_pct": 100}},
        ],
        "anim": {"in": "pop_zoom", "loop": "lightsweep", "out": "fade", "accent": "none"},
    }
    events = overlay_events(hook_overlay, ctx)

    # 1. Lightsweep must emit Dialogue 3 events with full vertical clearance (0 to 1920)
    sweep_events = [e for e in events if e.startswith("Dialogue: 3,") and "HookHeader," in e]
    assert len(sweep_events) == 2, f"Expected 2 lightsweep events, got {len(sweep_events)}"
    for sw in sweep_events:
        # Every \clip in lightsweep must have top=0 and bot=1920 so large fonts never get truncated
        clips = re.findall(r"\\clip\((\d+),(\d+),(\d+),(\d+)\)", sw)
        assert len(clips) > 0, f"No \\clip tags in {sw}"
        for c in clips:
            x1, y1, x2, y2 = map(int, c)
            assert y1 == 0 and y2 == 1920, f"Lightsweep clip vertical bounds must be 0..1920, got {y1}..{y2}"

    # 2. In-builder for pop_zoom must produce pop_zoom tags (1.45x scale over 100ms), not bounce fallback
    main_dialogues = [e for e in events if e.startswith("Dialogue: 2,") and "HookHeader," in e]
    assert len(main_dialogues) == 2
    # pop_zoom scales down from 1.45x (e.g. 170 * 1.45 = 246)
    assert "\\t(0,100," in main_dialogues[0], "pop_zoom must emit 100ms transition tag"

    # 3. Typewriter clip must also use full vertical clearance (0 to video_height)
    typewriter_overlay = dict(hook_overlay, anim={"in": "typewriter", "loop": "none", "out": "fade", "accent": "none"})
    tw_events = overlay_events(typewriter_overlay, ctx)
    tw_main = [e for e in tw_events if e.startswith("Dialogue: 2,") and "HookHeader," in e]
    assert len(tw_main) == 2
    for tw in tw_main:
        clips = re.findall(r"\\clip\((\d+),(\d+),(\d+),(\d+)\)", tw)
        assert len(clips) > 0
        for c in clips:
            x1, y1, x2, y2 = map(int, c)
            assert y1 == 0 and y2 == 1920, f"Typewriter clip vertical bounds must be 0..1920, got {y1}..{y2}"


# ---------------------------------------------------------------------------
# Progressive Ghost Reveal (SOP Phase 3)
#
# The reveal currently renders in ASS only; the Canvas preview does not mirror
# it yet, which is why `ghostReveal` ships defaulting to false. These assertions
# pin the render-side contract so the numbers cannot drift before the preview
# catches up, and pin the default itself so the flag cannot be flipped on while
# preview and render still disagree.
# ---------------------------------------------------------------------------

def test_ghost_reveal_colours_match_the_sop():
    """SOP Phase 3: spoken #FFFFFF, active #66FF00. ASS stores &HBBGGRR."""
    assert re.search(r'SPOKEN_HEX = "#FFFFFF"', PY_SRC)
    assert re.search(r'ACTIVE_HEX = "#66FF00"', PY_SRC)


def test_ghost_reveal_active_scale_is_114_percent():
    assert _grab(PY_SRC, r"\nACTIVE_SCALE_PCT = (\d+)\n", int) == 114


def test_ghost_reveal_ghost_is_fully_transparent():
    """A partly-transparent ghost would show the unspoken words as a grey hint."""
    assert re.search(r'GHOST_ALPHA = "&HFF&"', PY_SRC)


def test_ghost_reveal_default_is_the_same_on_both_sides():
    """
    The reveal is on by default, which is only safe because the preview draws it
    too. What must never happen is the two defaulting differently: a project
    with no stored preference would then export something the editor never
    showed. Flip both together or neither.
    """
    editor_state = (ROOT / "frontend" / "src" / "lib" / "editorProjectState.js").read_text(encoding="utf-8")
    js_default = _grab(
        editor_state, r"ghostReveal: firstPresent\([^)]*,\s*(true|false)\)", str
    )
    py_default = _grab(PY_SRC, r"ghost_reveal: bool = (True|False)", str)
    assert js_default == py_default.lower(), (
        f"preview defaults ghostReveal to {js_default} but the ASS generator "
        f"defaults to {py_default} -- an untouched project would export "
        "something the editor never drew"
    )

    # ...and every entry point that reads it out of a params dict has to agree
    # with them, or the default depends on which way the render was started.
    for src_name, pattern in (
        ("api_phase1.py", r'ghost_reveal=bool\(params\.get\("ghost_reveal", (True|False)\)\)'),
        ("batch_render.py", r'ghost_reveal=bool\(options\.get\("ghost_reveal", (True|False)\)\)'),
    ):
        entry_default = _grab((ROOT / "scripts" / src_name).read_text(encoding="utf-8"), pattern, str)
        assert entry_default == py_default, f"{src_name} disagrees: {entry_default}"


def test_ghost_reveal_is_anchored_not_centred():
    """
    libass centres a line on the ink it paints, and a ghosted word paints none,
    so an unanchored reveal drifts sideways as it advances -- 212px, measured.
    The anchor is what holds it still; losing it silently reintroduces the jitter.
    """
    assert "def anchor_tags(" in PY_SRC
    # The f-string writes each ASS backslash doubled, so match it as written.
    assert r"\\an{vertical_align}\\pos(" in PY_SRC, (
        r"anchor_tags must emit both an alignment and an explicit \pos"
    )


def test_mali_is_mapped_in_both_renderers():
    """
    A face in the picker but missing from the Canvas map silently draws Kanit in
    preview while the render uses the real face -- the bug the IBM Plex comment
    in SequencePlayer.jsx documents. Mali is the SOP Phase 3 caption face.
    """
    picker = (
        ROOT / "frontend" / "src" / "components" / "editor" / "inspector" / "CaptionInspector.jsx"
    ).read_text(encoding="utf-8")
    assert "id: 'Mali'" in picker
    assert "fontFamName === 'Mali'" in JS_SRC
    assert "'Mali', sans-serif" in JS_SRC


def test_every_picker_font_reaches_the_canvas():
    """Any id the picker offers must be branched on in drawCaption."""
    picker = (
        ROOT / "frontend" / "src" / "components" / "editor" / "inspector" / "CaptionInspector.jsx"
    ).read_text(encoding="utf-8")
    block = re.search(r"FONT_OPTIONS = \[(.*?)\];", picker, re.S)
    assert block, "FONT_OPTIONS moved -- this probe can no longer see the picker"
    ids = set(re.findall(r"\{ id: '([^']+)'", block.group(1)))
    assert ids, "no font ids parsed out of FONT_OPTIONS"
    # Kanit is the fallback branch, so it needs no explicit comparison.
    for font_id in ids - {"Kanit"}:
        assert f"fontFamName === '{font_id}'" in JS_SRC, (
            f"font '{font_id}' is offered in the picker but never mapped in "
            "SequencePlayer.drawCaption -- preview would silently draw Kanit"
        )


def test_ghost_reveal_constants_are_mirrored_in_the_preview():
    """
    Canvas and libass each hold their own copy of the three reveal numbers, so
    they have to be asserted equal here -- the whole reason this file exists.
    """
    assert "const GHOST_SPOKEN_COLOR = '#FFFFFF';" in JS_SRC
    assert "const GHOST_ACTIVE_COLOR = '#66FF00';" in JS_SRC
    # 1.14 * 100 is not exactly 114 in binary floating point.
    assert abs(
        _grab(JS_SRC, r"const GHOST_ACTIVE_SCALE = ([\d.]+);") * 100
        - _grab(PY_SRC, r"\nACTIVE_SCALE_PCT = (\d+)\n")
    ) < 1e-9


def test_preview_reveals_on_the_same_word_boundaries_as_the_render():
    """
    The browser has only Intl.Segmenter, which does not break Thai where
    pythainlp's newmm does. If the preview tokenized for itself the two engines
    would light different words, so python attaches one `word_reveal` track to
    the cue and both sides read it.
    """
    assert '"word_reveal": build_word_reveal(' in PY_SRC
    assert "cue.word_reveal" in JS_SRC
    assert "ghostRevealSegments(" in JS_SRC
    assert "Intl.Segmenter" not in JS_SRC.split("function ghostRevealSegments")[1].split("\n}")[0]


def test_unspoken_words_are_measured_but_not_painted():
    """
    The ghost holds the line's width. Skipping the measurement (rather than just
    the paint) would let the line reflow under the reveal -- the same 212px
    drift the ASS side had before it was anchored.
    """
    assert "if (seg.ghost) return;" in JS_SRC
    ghost_block = JS_SRC.split("const drawSeg =")[1].split("let curX")[0]
    assert "segmentWidths" not in ghost_block, (
        "widths must be measured for every segment, ghost included"
    )


def test_cue_fields_survive_the_editor_round_trip():
    """
    The cue list used to enumerate its fields, so anything the renderer wrote
    onto a cue and the editor had no opinion about was dropped on load and then
    autosaved away -- exactly how word_reveal would vanish. Same failure the
    clip list had.
    """
    assert re.search(
        r"rawCues\.map\(\(cue, index\) => \(\{\s*(?://[^\n]*\n\s*)*\.\.\.cue,",
        PROJECT_STATE_SRC,
    ), "cue load must spread the stored cue"


def test_the_preview_is_told_about_both_caption_flags():
    """
    captionStyle is built field by field, so a flag missing there never reaches
    drawCaption however well it is plumbed everywhere else -- bilingualSubtitles
    was in that state, and the preview drew the English line regardless.
    """
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    for flag in ("bilingualSubtitles", "ghostReveal"):
        assert shell.count(f"{flag}: style.{flag},") == 2, (
            f"both preview call sites must pass {flag}"
        )
    # ...and a change to either must invalidate the cached caption layer.
    assert "captionStyle.ghostReveal" in JS_SRC
    assert "captionStyle.bilingualSubtitles" in JS_SRC


def test_reveal_anchor_is_measured_at_the_rendered_font_size():
    """
    layout_line() re-applies ass_glyph_scale internally, so it must be handed
    the same Fontsize the ASS style carries -- the boosted one. Passing the
    plain em number measured the line at about half its rendered width and put
    the anchor ~100px left of the text (measured against the Canvas probe:
    102.8px before, 2.8px after, the residual being the 5.2 outline).
    """
    call = _grab(PY_SRC, r"anchor = anchor_tags\((.*?)\)\n", str)
    assert "font_size_boosted" in call, (
        "the reveal anchor must be measured at the boosted Fontsize, not the em size"
    )


def test_multiline_reveal_is_mirrored_on_both_sides():
    """
    A wrapped caption reveals across its lines in both engines, and both deal
    the flat track out the same way -- the split has to agree or the two would
    light different words on different lines.
    """
    assert "def split_reveal_by_lines(" in PY_SRC
    assert "function splitRevealByLines(" in JS_SRC
    # Both reject a word straddling the break rather than guessing.
    assert "straddles the line break" in PY_SRC
    assert "straddles the break" in JS_SRC
    # And both drive the per-line slice off the whole track, so a word lighting
    # up on line two leaves line one white instead of re-ghosting it.
    assert "build_multiline_reveal_events(" in PY_SRC
    assert "ghostRevealSegments(revealTrack, t, revealLines[idx])" in JS_SRC


def test_multiline_reveal_lines_step_by_one_font_size():
    """
    Parity rule 2.7: line advance is exactly 1.0 x font size. The reveal places
    each line itself rather than letting libass stack them, so it has to use the
    same step the Canvas does.
    """
    assert "step = font_size" in PY_SRC
    assert "const thaiLineH = fontSize;" in JS_SRC


def test_reveal_drops_the_whole_caption_shadow():
    """
    The soft shadow draws the caption whole from the cue's first frame, so under
    a reveal it pre-echoes words that have not been spoken -- visible as a grey
    tone mark floating above a second line before its text appears.
    """
    assert "shadow_events: List[str] = []" in PY_SRC
    block = PY_SRC.split("if reveal_events:")[1].split("else:")[0]
    assert "shadow_events" not in block, "the reveal path must not emit the whole-caption shadow"


def test_english_line_resets_alpha_under_a_reveal():
    r"""
    ASS override state carries across \N, so the English line inherits whatever
    the Thai line above it ended on. Under a ghost reveal that is the last
    unspoken word's \alpha&HFF&, which made the whole translation invisible
    until the final word was spoken -- it only appeared on the settle event.
    """
    assert r"\\N{{\\alpha&H00&" in PY_SRC, (
        "the English line must clear the reveal's ghost alpha"
    )


def test_a_bilingual_caption_still_reveals():
    """
    The reveal used to bail out entirely when a translation was present, so
    every bilingual project -- which is the default -- silently got a plain
    caption however the flag was set.
    """
    gate = PY_SRC.split("reveal_events: List[str] = []")[1].split("):")[0]
    assert "en_sub" not in gate, (
        "a stacked English line must not disable the Thai reveal"
    )


def test_emoji_are_stripped_from_captions():
    """
    libass draws emoji through a fallback face whose advance PIL cannot measure,
    so any layout computed before the render -- the reveal's anchor, the
    detached-tone companions -- lands off by the difference (16px, measured,
    enough to put a tone over the wrong glyph).
    """
    assert "def strip_caption_emoji(" in PY_SRC
    # Applied where cues are built AND where they are written, since a cue can
    # reach the writer without passing through generate_micro_cues.
    assert PY_SRC.count("strip_caption_emoji(") >= 3
    # The old keyword-driven auto-emoji table must be gone, not just bypassed.
    assert 'emoji = "⚠️ "' not in PY_SRC


def test_an_emptied_clause_is_not_emitted():
    """A clause that was only an emoji would otherwise hold a blank caption."""
    assert "if not cue_text:" in PY_SRC


def test_reveal_companions_are_built_from_the_whole_line():
    """
    A companion carries the entire caption and hides all but its own tone --
    that is what holds the tone over the right glyph. Building one per word
    leaves it with nothing in front, so libass drew the tone at the start of the
    line instead of above the word it belongs to.
    """
    block = PY_SRC.split("reveal_events: List[str] = []")[1].split("if reveal_events:")[0]
    assert "_, line_marks = repair_caption_text(" in block, (
        "the reveal must repair the whole line for its companions"
    )
    assert "w_body, _ = repair_caption_text(ass_escape_text(word[\"text\"]))" in block, (
        "the body still repairs per word, since each word is drawn separately"
    )


def test_the_english_line_is_centred_independently_of_the_reveal():
    """
    The reveal's events are anchored from their left edge -- its ghosts paint no
    ink for libass to centre on. An English line appended to them inherited that
    left anchor and sat off-centre under a Thai line that is itself centred, so
    the block read as lopsided. Nothing in the English is revealed, so it gets
    its own normally-centred event instead.
    """
    block = PY_SRC.split("reveal_events: List[str] = []")[1].split("if reveal_events:")[0]
    assert "suffix=en_sub" not in block, (
        "the English line must not ride inside the left-anchored reveal events"
    )
    assert "if reveal_events and en_sub:" in PY_SRC
    # A positioned cue centres it on the same point; otherwise the style's own
    # alignment already centres it.
    assert "an5" in PY_SRC.split("if reveal_events and en_sub:")[1][:600]


def test_both_caption_toggles_reach_the_render_request():
    """
    A toggle that only changes the preview is worse than no toggle: the editor
    shows one thing and the export does another. bilingual_subtitles was pinned
    to `true` in the render request and ghost_reveal was not sent at all.
    """
    shell = (ROOT / "frontend" / "src" / "components" / "editor" / "EditorShell.jsx").read_text(encoding="utf-8")
    assert "bilingual_subtitles: true," not in shell, (
        "bilingual_subtitles must come from the project's own style"
    )
    assert "bilingual_subtitles: style.bilingualSubtitles !== false," in shell
    assert "ghost_reveal: !!style.ghostReveal," in shell


def test_both_caption_toggles_survive_a_reload():
    """A toggle read on load but never written back resets on reopen."""
    state = (ROOT / "frontend" / "src" / "lib" / "editorProjectState.js").read_text(encoding="utf-8")
    serialise = state.split("export function serializeStyle(")[1].split("\n}")[0]
    for key in ("ghost_reveal", "ghostReveal", "bilingual_subtitles", "bilingualSubtitles"):
        assert key in serialise, f"serializeStyle drops {key}"


def test_both_caption_toggles_are_in_the_inspector():
    picker = (
        ROOT / "frontend" / "src" / "components" / "editor" / "inspector" / "CaptionInspector.jsx"
    ).read_text(encoding="utf-8")
    assert "ghostReveal: !style.ghostReveal" in picker
    assert "bilingualSubtitles: style.bilingualSubtitles === false" in picker
    # Both go through the shared switch, which carries the role and the label.
    assert picker.count("<CaptionToggle") == 2
    assert 'role="switch"' in picker
    assert picker.count("ariaLabel=") == 2


def test_the_english_line_clears_the_thai_one_under_a_reveal():
    r"""
    Half of each line separates their centres, in the BOOSTED size libass
    actually renders -- Thai faces run line boxes far taller than their em, so
    stepping by the em number left 6px between the two and they read as
    collided. reveal_y has to be converted to the Thai line's middle first,
    since it means the line's bottom under \an1 and its top under \an7, both of
    which sit a descender away from the ink; measuring from those directly put
    the English ~17px too low, which reads as a gap in the block.
    """
    assert "thai_middle = reveal_y" in PY_SRC
    assert "en_y = thai_middle + font_size_boosted * (" in PY_SRC
    assert "en_pct / 100.0" in PY_SRC


def test_the_english_line_is_always_positioned_under_a_reveal():
    """
    The reveal moves the Thai off the style's margin onto its own \\pos, so an
    English line still anchored by that margin lands where the Thai used to be
    -- on top of it. It shipped that way for cues with no stored x/y.
    """
    block = PY_SRC.split("if reveal_events and en_sub:")[1].split("en_pos = (")[1][:200]
    assert "if pos_override" not in block, (
        "the English line must be positioned for every cue, not only placed ones"
    )
    assert "an5" in block and "pos(" in block


# ---------------------------------------------- L3-02 edited caption reveal
_REVEAL_RUNNER = r"""
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
const src = readFileSync(process.argv[2], 'utf8');
const edits = await import(pathToFileURL(process.argv[3]).href);
const input = JSON.parse(readFileSync(process.argv[4], 'utf8'));
const grab = (re, what) => { const m = src.match(re); if (!m) throw new Error('missing ' + what); return m[0]; };
const code = `
${grab(/const GHOST_SPOKEN_COLOR = [^\n]*/, 'spoken')}
${grab(/const GHOST_ACTIVE_COLOR = [^\n]*/, 'active')}
${grab(/const GHOST_ACTIVE_SCALE = [^\n]*/, 'scale')}
${grab(/function splitRevealByLines\([\s\S]*?\n\}/, 'splitRevealByLines')}
${grab(/function ghostRevealSegments\([\s\S]*?\n\}/, 'ghostRevealSegments')}
export const ACTIVE = GHOST_ACTIVE_COLOR;
export function previewSegments(cue, t, style, thaiLines, revealTrackForCue) {
  ${grab(/const revealTrack = [\s\S]*?const revealSingle = [\s\S]*?: null;/, 'revealTrack')}
  return thaiLines.map((line, idx) => {
    ${grab(/const revealSegments = revealLines[\s\S]*?: revealSingle;/, 'revealSegments')}
    return revealSegments;
  });
}`;
const m = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
// What the caption looks like at t: the words the reveal paints and which one
// is lit ('settled' when all are spoken; words null when no reveal is drawn).
const look = (cue, t) => {
  const lines = m.previewSegments(cue, t, { ghostReveal: true }, [String(cue.text)], edits.revealTrackForCue);
  const segs = lines[0];
  if (!segs) return { words: null, active: null };
  const active = segs.findIndex((s) => s.color === m.ACTIVE);
  const settled = active === -1 && segs.every((s) => !s.ghost);
  return { words: segs.map((s) => s.text), active: settled ? 'settled' : active };
};
const out = {};
for (const [name, c] of Object.entries(input.cases)) {
  let cue = c.cue;
  if (c.edit === 'patch') cue = edits.reconcileCueReveal(c.cue, { ...c.cue, ...c.patch });
  if (c.edit === 'split') {
    const [, r2] = edits.splitCueReveal(c.cue, c.text1, c.text2, c.splitTime);
    cue = edits.withReveal({ ...c.cue, start: c.splitTime, text: c.text2 }, r2);
  }
  if (c.edit === 'merge') {
    const merged = { ...c.a, end: c.b.end, text: `${c.a.text} ${c.b.text}` };
    cue = edits.withReveal(merged, edits.mergeCueReveals(c.a, c.b, merged));
  }
  out[name] = { hasTrack: Array.isArray(cue.word_reveal), samples: c.times.map((t) => look(cue, t)) };
}
console.log(JSON.stringify(out));
"""


def _render_reveal(text, start, end):
    """The track the render draws for this cue (generate_ass rebuilds it here)."""
    from scripts.subtitle_engine import SubtitleEngine
    micro = SubtitleEngine.generate_micro_cues(
        [{"start": start, "end": end, "text": text, "translation": "x"}]
    )
    assert len(micro) == 1, "fixture must stay one micro cue"
    return micro[0]["word_reveal"]


def _active(reveal, t):
    """ghostRevealSegments' rule, applied to the render's own track."""
    idx = -1
    for i, word in enumerate(reveal):
        if t >= word["start"]:
            idx = i
    if idx == len(reveal) - 1 and t >= reveal[-1]["end"]:
        return "settled"
    return idx


def test_an_edited_caption_never_reveals_its_old_words(tmp_path):
    """
    L3-02. The stored word_reveal is python's track for the text the cue had
    when the pipeline built it. The render always rebuilds it from the current
    text; the preview drew the stored one as-is, so after an edit the reveal
    lit the old sentence (or the whole sentence on both halves of a split, or
    nothing at all once the cue was dragged to a new time).
    """
    import shutil
    import subprocess

    if not shutil.which("node"):
        pytest.skip("needs node")

    old_text, new_text = "รีวิวหูฟังไร้สายรุ่นใหม่", "ทดสอบลำโพงพกพาเสียงดี"
    old = {"_uid": "c1", "start": 1.0, "end": 4.0, "text": old_text,
           "word_reveal": _render_reveal(old_text, 1.0, 4.0)}
    times = [1.1, 2.0, 2.6, 3.5, 4.0]
    moved_times = [t + 5 for t in times]
    split_time = 2.25
    half_a = {"_uid": "a", "start": 1.0, "end": 2.5, "text": "รีวิวหูฟัง",
              "word_reveal": _render_reveal("รีวิวหูฟัง", 1.0, 2.5)}
    half_b = {"_uid": "b", "start": 2.5, "end": 4.0, "text": "ไร้สายรุ่นใหม่",
              "word_reveal": _render_reveal("ไร้สายรุ่นใหม่", 2.5, 4.0)}
    cases = {
        # A track saved before this fix: words of the old text on the new one.
        "stale_text": {"cue": {**old, "text": new_text}, "times": times},
        # patchCaption({ text }) going through the command layer.
        "typed": {"cue": old, "edit": "patch", "patch": {"text": new_text}, "times": times},
        # Dragged 5 s later: same words, new span (command layer, then stale).
        "moved": {"cue": old, "edit": "patch", "patch": {"start": 6.0, "end": 9.0}, "times": moved_times},
        "moved_stale": {"cue": {**old, "start": 6.0, "end": 9.0}, "times": moved_times},
        "split_second_half": {"cue": old, "edit": "split", "text1": "รีวิวหูฟัง",
                              "text2": "ไร้สายรุ่นใหม่", "splitTime": split_time,
                              "times": [2.3, 3.0, 3.5, 4.0]},
        "merged": {"edit": "merge", "a": half_a, "b": half_b, "cue": half_a, "times": times},
    }
    spec = tmp_path / "reveal_cases.json"
    spec.write_text(json.dumps({"cases": cases}, ensure_ascii=False), encoding="utf-8")
    runner = tmp_path / "reveal.mjs"
    runner.write_text(_REVEAL_RUNNER, encoding="utf-8")
    res = subprocess.run(
        ["node", str(runner),
         str(ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx"),
         str(ROOT / "frontend" / "src" / "lib" / "captionEdits.js"),
         str(spec)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0, res.stderr
    got = json.loads(res.stdout)

    # New text: no reveal is drawn from the old track (the preview falls back
    # to the ordinary caption, which draws cue.text), never the old words.
    for name in ("stale_text", "typed"):
        for sample in got[name]["samples"]:
            assert sample["words"] is None, f"{name}: drew the old track {sample}"
    assert got["typed"]["hasTrack"] is False, "the command layer must drop the stale track"

    # Moved: the reveal still runs, on the same word at the same moment as the
    # render's own track for the new span.
    render_moved = _render_reveal(old_text, 6.0, 9.0)
    for name in ("moved", "moved_stale"):
        for t, sample in zip(moved_times, got[name]["samples"]):
            assert sample["words"] == [w["text"] for w in render_moved], name
            assert sample["active"] == _active(render_moved, t), f"{name} t={t}: {sample}"

    # Split: the second half reveals only its own words, timed like the render.
    render_b = _render_reveal("ไร้สายรุ่นใหม่", split_time, 4.0)
    for t, sample in zip(cases["split_second_half"]["times"], got["split_second_half"]["samples"]):
        assert sample["words"] == [w["text"] for w in render_b]
        assert sample["active"] == _active(render_b, t), f"split t={t}: {sample}"

    # Merge: one reveal over both halves' words, never a stale subset.
    for sample in got["merged"]["samples"]:
        assert sample["words"] == [w["text"] for w in half_a["word_reveal"] + half_b["word_reveal"]]


# ---------------------------------------------- L2-10 mirror + pan direction
_MIRROR_RUNNER = r"""
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
const src = readFileSync(process.argv[2], 'utf8');
const tm = await import(pathToFileURL(process.argv[3]).href);
const input = JSON.parse(readFileSync(process.argv[4], 'utf8'));
const grab = (re, what) => { const m = src.match(re); if (!m) throw new Error('missing ' + what); return m[0]; };
const code = `
${grab(/const CANVAS_W = [^\n]*/, 'W')}
${grab(/const CANVAS_H = [^\n]*/, 'H')}
${grab(/function mirrorFlag\([^\n]*/, 'mirrorFlag')}
let resolveClipTransforms;
export function use(fn) { resolveClipTransforms = fn; }
export ${grab(/function drawVideoFrame\([\s\S]*?\n\}/, 'drawVideoFrame')}
export const SIZE = [CANVAS_W, CANVAS_H];`;
const m = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
m.use(tm.resolveClipTransforms);

// A canvas that keeps the affine transform and every drawImage, then answers
// "which source pixel lands at this screen point" by inverting it.
const mul = (a, b) => [a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1], a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3], a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5]];
function makeCtx() {
  let M = [1, 0, 0, 1, 0, 0]; const stack = []; const draws = [];
  return {
    canvas: { width: m.SIZE[0], height: m.SIZE[1] }, filter: 'none', draws,
    save() { stack.push(M.slice()); }, restore() { M = stack.pop(); },
    translate(x, y) { M = mul(M, [1, 0, 0, 1, x, y]); },
    scale(x, y) { M = mul(M, [x, 0, 0, y, 0, 0]); },
    rotate(r) { const c = Math.cos(r), s = Math.sin(r); M = mul(M, [c, s, -s, c, 0, 0]); },
    drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh) { draws.push({ M: M.slice(), sx, sy, sw, sh, dx, dy, dw, dh }); },
  };
}
function sample(ctx, X, Y) {
  for (let i = ctx.draws.length - 1; i >= 0; i -= 1) {
    const d = ctx.draws[i]; const [a, b, c, dd, e, f] = d.M; const det = a * dd - b * c;
    const u = (dd * (X - e) - c * (Y - f)) / det; const v = (-b * (X - e) + a * (Y - f)) / det;
    if (u < d.dx || v < d.dy || u > d.dx + d.dw || v > d.dy + d.dh) continue;
    return [d.sx + ((u - d.dx) / d.dw) * d.sw, d.sy + ((v - d.dy) / d.dh) * d.sh];
  }
  return null;
}
const out = {};
for (const [name, c] of Object.entries(input.cases)) {
  const ctx = makeCtx();
  const video = { videoWidth: c.source[0], videoHeight: c.source[1], readyState: 4 };
  m.drawVideoFrame(ctx, video, c.clip, c.motionTime ?? 0.5);
  out[name] = input.xs.map((x) => sample(ctx, x, input.y));
}
console.log(JSON.stringify(out));
"""


def _band(value, size):
    """Thirds of a source axis: 0 = R, 1 = G, 2 = B."""
    return min(2, max(0, int(value * 3 // size)))


def _runs(seq):
    out = []
    for item in seq:
        if not out or out[-1][0] != item:
            out.append([item, 1])
        else:
            out[-1][1] += 1
    return [tuple(r) for r in out]


def test_mirrored_pan_frames_the_same_side_as_the_render(tmp_path):
    """
    L2-10. The render flips (hflip) before it crops, so pan_x always moves the
    window the same way on screen. The preview cropped the unflipped frame and
    flipped afterwards, which showed the opposite side of the shot whenever a
    mirrored clip was zoomed and panned. Real FFmpeg frames on one side, the
    real drawVideoFrame on the other, on a source split into three colours.
    """
    import shutil
    import subprocess

    from PIL import Image

    from scripts.video_editor import VideoEditor

    if not shutil.which("node") or not shutil.which("ffmpeg"):
        pytest.skip("needs node and ffmpeg")

    def run(cmd):
        done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert done.returncode == 0, done.stderr

    ff = shutil.which("ffmpeg")
    # Portrait source: R | G | B left to right. Landscape source for the 90
    # degree case: R / G / B top to bottom, so the turn lays them across x.
    portrait = tmp_path / "rgb_portrait.mp4"
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "color=c=0x0000ff:size=1080x1920:rate=30:duration=2",
         "-vf", "drawbox=x=0:y=0:w=360:h=ih:color=0xff0000:t=fill,"
                "drawbox=x=360:y=0:w=360:h=ih:color=0x00ff00:t=fill",
         "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p", str(portrait)])
    landscape = tmp_path / "rgb_landscape.mp4"
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "color=c=0x0000ff:size=1920x1080:rate=30:duration=2",
         "-vf", "drawbox=x=0:y=0:w=iw:h=360:color=0xff0000:t=fill,"
                "drawbox=x=0:y=360:w=iw:h=360:color=0x00ff00:t=fill",
         "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "12", "-pix_fmt", "yuv420p", str(landscape)])

    still_kf = [{"time": 0, "zoom": 2.0, "pan_x": 1.0}, {"time": 1.0, "zoom": 2.0, "pan_x": 1.0}]
    cases = {
        "plain_pan_right": (portrait, {"zoom": 2.0, "pan_x": 1.0}),
        "mirror_pan_left": (portrait, {"zoom": 2.0, "pan_x": -1.0, "mirror": True}),
        "mirror_pan_right": (portrait, {"zoom": 2.0, "pan_x": 1.0, "mirror": True}),
        "mirror_half_pan": (portrait, {"zoom": 1.5, "pan_x": 0.5, "mirror": True}),
        "mirror_keyframes": (portrait, {"zoom": 1.0, "pan_x": 0.0, "mirror": True, "keyframes": still_kf}),
        "mirror_rot180": (portrait, {"zoom": 2.0, "pan_x": 1.0, "mirror": True, "rotation": 180}),
        "mirror_rot90": (landscape, {"zoom": 2.0, "pan_x": 1.0, "mirror": True, "rotation": 90}),
    }
    clip_list = [
        {"source_path": str(src), "trim_start": 0.0, "trim_end": 1.0, "duration": 1.0,
         "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0, "transition_in": "cut", **cfg}
        for src, cfg in cases.values()
    ]
    total = float(len(clip_list))
    audio = tmp_path / "silence.wav"
    run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-t", str(total), str(audio)])
    ass = tmp_path / "empty.ass"
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8", newline="\n",
    )
    rendered = tmp_path / "mirror_pan.mp4"
    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(src) for src, _ in cases.values()],
        total_duration=total, mixed_audio_path=str(audio), ass_subtitle_path=str(ass),
        output_mp4_path=str(rendered), clip_list=clip_list,
        transitions=["cut"] * (len(clip_list) - 1), export_preset="draft",
        auto_blur_landscape=False,
    )

    xs = list(range(5, 540, 10))
    y = 480
    render_bands = {}
    for index, name in enumerate(cases):
        frame = tmp_path / f"render_{index}.png"
        run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(rendered),
             "-ss", f"{index + 0.5:.3f}", "-frames:v", "1",
             "-vf", "scale=540:960:flags=lanczos", "-pix_fmt", "rgb24", str(frame)])
        with Image.open(frame) as img:
            px = img.convert("RGB")
            render_bands[name] = [max(range(3), key=lambda ch: px.getpixel((x, y))[ch]) for x in xs]

    spec = tmp_path / "mirror_cases.json"
    spec.write_text(json.dumps({
        "xs": xs, "y": y,
        "cases": {
            name: {"source": [1080, 1920] if src == portrait else [1920, 1080], "clip": cfg}
            for name, (src, cfg) in cases.items()
        },
    }), encoding="utf-8")
    runner = tmp_path / "mirror.mjs"
    runner.write_text(_MIRROR_RUNNER, encoding="utf-8")
    res = subprocess.run(
        ["node", str(runner),
         str(ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx"),
         str(ROOT / "frontend" / "src" / "lib" / "timelineMath.js"), str(spec)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert res.returncode == 0, res.stderr
    points = json.loads(res.stdout)

    report = {}
    for name, (src, _cfg) in cases.items():
        axis = 0 if src == portrait else 1
        preview = [_band(p[axis], 1080) for p in points[name]]
        report[name] = {"render": _runs(render_bands[name]), "preview": _runs(preview)}
        mismatched = sum(a != b for a, b in zip(render_bands[name], preview))
        # Only a sample straddling a colour edge may disagree.
        assert mismatched <= 2, f"{name}: {report[name]}"
    print(json.dumps(report))


def test_split_clip_camera_keyframes_render_without_a_jump(tmp_path):
    """
    B4 (EDITOR-CUT-QUALITY-R1): the editor's splitClipAt re-bases camera
    keyframes at the played cut. The render has no split logic of its own -- it
    reads each half's keyframes with t=0 at that half's trim_start after speed
    -- so the halves the JS produces, evaluated by video_editor.py's resolver,
    must reproduce the unsplit clip on both sides of the cut.
    """
    import shutil
    import subprocess

    from scripts.video_editor import resolve_clip_transforms

    if not shutil.which("node"):
        pytest.skip("needs node")
    clip = {
        "id": "orig", "trim_start": 1.0, "trim_end": 7.0, "speed": 2.0,
        "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0,
        "keyframes": [
            {"time": 0, "zoom": 1.0, "pan_x": -0.5},
            {"time": 2, "zoom": 2.5, "pan_x": 0.5},
            {"time": 0, "property": "pan_y", "value": -0.2},
            {"time": 3, "property": "pan_y", "value": 0.4},
        ],
    }
    seg = {"clip": clip, "srcDur": 10, "segStart": 4, "segEnd": 7}
    cut = 1.25  # played seconds; 2.5 s of source at 2x
    runner = tmp_path / "split.mjs"
    runner.write_text(
        "const lib = await import(new URL('file:///' + process.argv[2].replace(/\\\\/g, '/')).href);\n"
        "const seg = JSON.parse(process.argv[3]);\n"
        "let n = 0;\n"
        "console.log(JSON.stringify(lib.splitClipAt(seg, seg.segStart + Number(process.argv[4]), () => `p${++n}`)));\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["node", str(runner), str(ROOT / "frontend" / "src" / "lib" / "timelineMath.js"), json.dumps(seg), str(cut)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    left, right = json.loads(proc.stdout)
    assert left["trim_end"] == right["trim_start"] == 3.5

    def close(a, b):
        return all(abs(a[k] - b[k]) < 1e-6 for k in ("zoom", "pan_x", "pan_y"))

    at_cut = resolve_clip_transforms(clip, cut)
    assert close(resolve_clip_transforms(left, cut), at_cut)
    assert close(resolve_clip_transforms(right, 0.0), at_cut)
    for local in (0.0, 0.4, 0.75, 1.5):
        assert close(resolve_clip_transforms(right, local), resolve_clip_transforms(clip, cut + local)), local
    for local in (0.0, 0.6, 1.0):
        assert close(resolve_clip_transforms(left, local), resolve_clip_transforms(clip, local)), local


# ── EDITOR-CUT-QUALITY-R2 E1: camera keyframe easing ──────────────────────────

_EASED_CAMERA_CLIP = {
    "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0,
    "keyframes": [
        {"time": 0.0, "zoom": 1.0, "pan_x": -0.6},
        {"time": 2.0, "zoom": 1.5, "pan_x": 0.4, "easing": "ease_in_out"},
        {"time": 3.0, "zoom": 1.2, "pan_x": 0.4, "easing": "ease_out"},
        {"time": 4.5, "zoom": 3.4, "pan_x": 1.6, "easing": "ease_in"},  # past the clamps
        {"time": 0.5, "property": "pan_y", "value": 0.3},
        {"time": 2.5, "property": "pan_y", "value": -0.5, "easing": "ease_in_out"},
        {"time": 3.5, "property": "pan_y", "value": 0.1, "easing": "bogus"},  # unknown == linear
    ],
}


def _eval_ffmpeg_expr(expr: str, t: float) -> float:
    """Tiny evaluator for the camera expressions video_editor.py emits.

    Only the names below exist (no builtins), so this evaluates exactly the
    if/lt/min/max/ceil arithmetic subset and nothing else.
    """
    source = expr.replace("\\,", ",").replace("if(", "_if(")
    names = {
        "__builtins__": {}, "t": t, "_if": lambda c, a, b: a if c else b,
        "lt": lambda a, b: 1.0 if a < b else 0.0, "min": min, "max": max, "ceil": math.ceil,
    }
    return float(eval(source, names))  # noqa: S307 - restricted namespace above


def _run_timeline_math(tmp_path, body: str, *args: str):
    import shutil
    import subprocess

    if not shutil.which("node"):
        pytest.skip("needs node")
    runner = tmp_path / "e1.mjs"
    runner.write_text(
        "const lib = await import(new URL('file:///' + process.argv[2].replace(/\\\\/g, '/')).href);\n" + body,
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["node", str(runner), str(ROOT / "frontend" / "src" / "lib" / "timelineMath.js"), *args],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_eased_camera_keyframes_match_between_preview_resolver_and_ffmpeg_expression(tmp_path):
    from scripts.video_editor import _camera_track, _ffmpeg_keyframe_expression_live, resolve_clip_transforms

    times = [i * 0.25 for i in range(-1, 22)]  # 23 samples, before/through/after
    preview = _run_timeline_math(
        tmp_path,
        "const clip = JSON.parse(process.argv[3]);\n"
        "console.log(JSON.stringify(JSON.parse(process.argv[4]).map((t) => lib.resolveClipTransforms(clip, t))));\n",
        json.dumps(_EASED_CAMERA_CLIP), json.dumps(times),
    )
    exprs = {
        prop: _ffmpeg_keyframe_expression_live(_camera_track(_EASED_CAMERA_CLIP, prop), 0.0, prop)
        for prop in ("zoom", "pan_x", "pan_y")
    }
    worst = 0.0
    for t, js in zip(times, preview):
        py = resolve_clip_transforms(_EASED_CAMERA_CLIP, t)
        for prop, expr in exprs.items():
            rendered = _eval_ffmpeg_expr(expr, t)
            worst = max(worst, abs(js[prop] - py[prop]), abs(js[prop] - rendered))
    print(json.dumps({"eased_camera_parity_worst": worst}))
    assert worst < 1e-3, worst
    # The curve really is eased: ease_in_out at a quarter of 1.0->1.5 is 1.0625, not 1.125.
    assert abs(resolve_clip_transforms(_EASED_CAMERA_CLIP, 0.5)["zoom"] - 1.0625) < 1e-9
    assert abs(_eval_ffmpeg_expr(exprs["zoom"], 0.5) - 1.0625) < 1e-5


def test_camera_keyframes_without_easing_keep_the_old_linear_expression():
    from scripts.video_editor import _ffmpeg_keyframe_expression_live

    track = [{"time": 0.0, "value": 1.0}, {"time": 2.0, "value": 1.5}]
    assert _ffmpeg_keyframe_expression_live(track, 1.0, "zoom") == (
        "min(3.000000\\,max(1.000000\\,if(lt(t\\,0.000000)\\,1.000000\\,"
        "if(lt(t\\,2.000000)\\,1.000000+(0.500000)*(t-0.000000)/(2.000000)\\,1.500000))))"
    )


def test_split_inside_an_eased_camera_segment_stays_continuous(tmp_path):
    from scripts.video_editor import resolve_clip_transforms

    clip = {
        "id": "orig", "trim_start": 0.0, "trim_end": 4.0, "speed": 1.0,
        "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0,
        "keyframes": [
            {"time": 0.0, "zoom": 1.0, "pan_x": -0.4},
            {"time": 4.0, "zoom": 1.5, "pan_x": 0.4, "easing": "ease_in_out"},
            {"time": 0.0, "property": "pan_y", "value": 0.2},
            {"time": 4.0, "property": "pan_y", "value": -0.2, "easing": "ease_out"},
        ],
    }
    seg = {"clip": clip, "srcDur": 4, "segStart": 0, "segEnd": 4}
    cut = 1.3
    left, right = _run_timeline_math(
        tmp_path,
        "const seg = JSON.parse(process.argv[3]);\nlet n = 0;\n"
        "console.log(JSON.stringify(lib.splitClipAt(seg, seg.segStart + Number(process.argv[4]), () => `p${++n}`)));\n",
        json.dumps(seg), str(cut),
    )
    at_cut = resolve_clip_transforms(clip, cut)
    for prop in at_cut:
        assert abs(resolve_clip_transforms(left, cut)[prop] - at_cut[prop]) < 1e-6
        assert abs(resolve_clip_transforms(right, 0.0)[prop] - at_cut[prop]) < 1e-6
    worst = 0.0
    for i in range(27):
        local = i * 0.1
        r, o = resolve_clip_transforms(right, local), resolve_clip_transforms(clip, cut + local)
        worst = max(worst, *(abs(r[k] - o[k]) for k in o))
    for i in range(14):
        local = i * 0.1
        lv, o = resolve_clip_transforms(left, local), resolve_clip_transforms(clip, local)
        worst = max(worst, *(abs(lv[k] - o[k]) for k in o))
    # Sampled bake: exact at samples, <= ~0.4% of the segment's delta between.
    print(json.dumps({"eased_split_worst": worst}))
    assert worst < 3e-3, worst


def test_camera_easing_survives_editor_save_load(tmp_path):
    import shutil
    import subprocess

    if not shutil.which("node"):
        pytest.skip("needs node")
    runner = tmp_path / "roundtrip.mjs"
    runner.write_text(
        "const lib = await import(new URL('file:///' + process.argv[2].replace(/\\\\/g, '/')).href);\n"
        "const state = lib.manifestToEditorState({ clip_list: JSON.parse(process.argv[3]) });\n"
        "console.log(JSON.stringify(lib.serializeClips(state.clipList)));\n",
        encoding="utf-8",
    )
    clips = [{"source_path": "a.mp4", "trim_start": 0, "trim_end": 3, "keyframes": _EASED_CAMERA_CLIP["keyframes"]}]
    proc = subprocess.run(
        ["node", str(runner), str(ROOT / "frontend" / "src" / "lib" / "editorProjectState.js"), json.dumps(clips)],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    saved = json.loads(proc.stdout)
    assert saved[0]["keyframes"] == _EASED_CAMERA_CLIP["keyframes"]


# --- Sticker/effect entrance + exit animation (lane S, EDITOR-CUT-QUALITY-R2) ---
_OVERLAY_ANIM_CASES = [
    # (start, end) -- long, short (40% cap), very short, open-ended, Canvas sentinel
    (1.0, 4.0),
    (0.5, 0.9),
    (2.0, 2.1),
    (0.5, None),
    (0.0, 999999),
    (1.2345, 3.3),
]


def _overlay_anim_samples(start, end):
    base = [start - 0.1, start, start + 0.02, start + 0.06, start + 0.1, start + 0.15,
            start + 0.2, start + 0.25, start + 0.5]
    if end is not None and end < 99999:
        base += [end - 0.25, end - 0.15, end - 0.1, end - 0.05, end, end + 0.05]
    return base


def test_overlay_anim_constants_and_timing_grid():
    sys.path.insert(0, str(ROOT))
    from scripts.config import FPS
    from scripts.video_editor import (
        OVERLAY_ANIM_IN_FRAMES, OVERLAY_ANIM_OUT_FRAMES, OVERLAY_ANIM_MAX_SHARE,
        OVERLAY_ANIM_SCALE_FROM, overlay_anim_timing,
    )

    src = (ROOT / "frontend" / "src" / "lib" / "stickerAnimation.js").read_text(encoding="utf-8")
    assert f"IN_FRAMES: {OVERLAY_ANIM_IN_FRAMES}," in src
    assert f"OUT_FRAMES: {OVERLAY_ANIM_OUT_FRAMES}," in src
    assert f"MAX_SHARE: {OVERLAY_ANIM_MAX_SHARE}," in src
    assert f"SCALE_FROM: {OVERLAY_ANIM_SCALE_FROM}," in src
    # <= 0.25 s entrance, 0.2 s exit, both whole frames
    assert OVERLAY_ANIM_IN_FRAMES / FPS <= 0.25 and OVERLAY_ANIM_OUT_FRAMES / FPS == pytest.approx(0.2)
    for start, end in _OVERLAY_ANIM_CASES:
        d_in, d_out = overlay_anim_timing(start, end)
        for d in (d_in, d_out):
            assert d * FPS == pytest.approx(round(d * FPS), abs=1e-9)
        if end is not None and end < 99999:
            assert d_in <= 0.4 * (end - start) + 1e-9 and d_out <= 0.4 * (end - start) + 1e-9
    # Canvas no longer fades over the old 0.3 s that render never had (L3-09)
    player = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
    assert "elapsed / 0.3" not in player
    assert player.count("overlayAnimState(") >= 2


def test_overlay_anim_state_js_matches_python():
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("node"):
        pytest.skip("needs node")
    sys.path.insert(0, str(ROOT))
    from scripts.video_editor import overlay_anim_state

    cases = []
    for start, end in _OVERLAY_ANIM_CASES:
        for t in _overlay_anim_samples(start, end):
            for scale_in in (True, False):
                cases.append({"t": t, "start": start, "end": end, "scaleIn": scale_in})
    assert len(cases) >= 8

    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "anim.mjs"
        mod = (ROOT / "frontend" / "src" / "lib" / "stickerAnimation.js").resolve().as_uri()
        runner.write_text(
            f"import {{ overlayAnimState }} from '{mod}';\n"
            "const cases = JSON.parse(process.argv[2]);\n"
            "console.log(JSON.stringify(cases.map(c => overlayAnimState(c.t, c.start, c.end, "
            "{ scaleIn: c.scaleIn }))));\n",
            encoding="utf-8",
        )
        res = subprocess.run(["node", str(runner), json.dumps(cases)],
                             capture_output=True, text=True, encoding="utf-8")
        assert res.returncode == 0, res.stderr
        js_out = json.loads(res.stdout)

    for case, js in zip(cases, js_out):
        alpha, scale = overlay_anim_state(case["t"], case["start"], case["end"], scale_in=case["scaleIn"])
        assert js["alpha"] == pytest.approx(alpha, abs=1e-12), case
        assert js["scale"] == pytest.approx(scale, abs=1e-12), case
        assert 0.0 <= alpha <= 1.0 and 0.88 - 1e-12 <= scale <= 1.0 + 1e-12


def test_overlay_anim_filters_rest_frame_is_untouched():
    sys.path.insert(0, str(ROOT))
    from scripts.video_editor import overlay_anim_filters, overlay_anim_state

    chain = overlay_anim_filters(1.0, 3.0, rest_w=320, rest_h=213)
    # resting scale is the identity and pad restores the exact rest raster
    assert "min(iw," in chain and "min(ih," in chain
    assert "pad=w=320:h=213:" in chain
    assert "fade=t=in:st=1.000000:d=0.233333:alpha=1" in chain
    assert "fade=t=out:st=2.800000:d=0.200000:alpha=1" in chain
    assert overlay_anim_state(2.0, 1.0, 3.0) == (1.0, 1.0)
    # effects: alpha only, and no exit without an explicit end
    fx = overlay_anim_filters(0.5, None)
    assert "scale=" not in fx and "pad=" not in fx and "fade=t=out" not in fx


def _frame_grid_clip_list():
    """24 clips with ms-precision trims, speeds, freeze tails and every kind of
    boundary (cut, built-in, eased, clamped overlong) -- one list, fed both to
    the preview module and to the render builder."""
    types = ["cut", "fade", "wipeleft", "cut", "circleopen", "slideup", "dissolve", "cut",
             "fadeblack", "wipedown", "cut", "slideleft"]
    transition_durations = [0.4, 0.35, 0.3, 2.0, 0.27, 0.5, 0.4, 0.133, 0.45, 0.4, 0.1, 0.37]
    easings = [None, "ease_in_out", "ease_out", None, "ease_in", "ease_in_out", None, None,
               "ease_out", "ease_in", None, "ease_in_out"]
    speeds = [1.0, 1.0, 1.25, 0.8, 1.7, 1.0, 2.0, 0.5]
    freezes = [0, 0, 0.21, 0, 0, 0.5, 0, 0]
    clips = []
    for i in range(24):
        start = round(0.137 * i, 3)
        span = round(0.41 + ((i * 37) % 19) * 0.0971, 3)
        clip = {
            "id": f"c{i}", "trim_start": start, "trim_end": round(start + span, 3),
            "speed": speeds[i % 8], "freeze_tail": freezes[(i * 3) % 8],
        }
        if i > 0:
            clip["transition_in"] = types[(i - 1) % 12]
            clip["transition_duration"] = transition_durations[(i - 1) % 12]
            if easings[(i - 1) % 12]:
                clip["transition_easing"] = easings[(i - 1) % 12]
        clips.append(clip)
    return clips


def test_frame_grid_plan_is_the_same_in_the_preview_and_the_render_builder(tmp_path, monkeypatch):
    """B5 (EDITOR-CUT-QUALITY-R2): the preview's buildSegments() and the
    render's clip chain must put every clip edge and every transition overlap on
    the SAME frame. The JS module runs under node on the list; the Python side
    is the real VideoEditor.assemble_tiktok_video filtergraph (trim=end_frame per
    clip, xfade offset/duration), read back as frame numbers."""
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("node"):
        pytest.skip("needs node")
    sys.path.insert(0, str(ROOT))
    from tests.test_frame_grid_timing import capture_graph, graph_frames
    from scripts.video_editor import plan_sequence_frames, normalize_transitions

    clips = _frame_grid_clip_list()
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "plan.mjs"
        mod = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").resolve().as_uri()
        runner.write_text(
            f"import {{ buildSegments, totalDuration }} from '{mod}';\n"
            "const { clips, durations } = JSON.parse(process.argv[2]);\n"
            "const segs = buildSegments(clips, durations);\n"
            "console.log(JSON.stringify({ frames: segs.map(s => s.frames), total: totalDuration(segs) }));\n",
            encoding="utf-8",
        )
        res = subprocess.run(["node", str(runner), json.dumps({"clips": clips, "durations": {c["id"]: 60 for c in clips}})],
                             capture_output=True, text=True, encoding="utf-8")
        assert res.returncode == 0, res.stderr
        js = json.loads(res.stdout)
    js_plan = {k: [f[k] for f in js["frames"]] for k in ("start", "end", "overlap")}

    render_clips = []
    for i, c in enumerate(clips):
        src = tmp_path / f"s{i}.mp4"
        src.write_bytes(b"fake")
        render_clips.append({"source_path": str(src), "trim_start": c["trim_start"], "trim_end": c["trim_end"],
                             "speed": c["speed"], "freeze_tail": c["freeze_tail"]})
    transitions = []
    for c in clips[1:]:
        entry = {"type": c["transition_in"], "duration": c["transition_duration"]}
        if c.get("transition_easing"):
            entry["easing"] = c["transition_easing"]
        transitions.append(entry)
    total = js["total"]
    graph = capture_graph(tmp_path, monkeypatch, render_clips, transitions, total)

    assert graph_frames(graph) == js_plan
    # the module the builder calls is the same function, on the same list
    durations = [max(0.2, c["trim_end"] - c["trim_start"]) / c["speed"] + c["freeze_tail"] for c in clips]
    assert plan_sequence_frames(durations, normalize_transitions(transitions)) == js_plan
    # whole-frame total, and within half a frame of the exact float timeline
    assert js["total"] * 30 == pytest.approx(js_plan["end"][-1], abs=1e-9)
    assert any(o > 0 for o in js_plan["overlap"]) and any(o == 0 for o in js_plan["overlap"][1:])


def test_transition_easing_curves_are_the_same_in_the_preview_and_the_render():
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("node"):
        pytest.skip("needs node")
    sys.path.insert(0, str(ROOT))
    from scripts.video_editor import XFADE_TRANSITIONS, ease_camera_ratio, transition_easing_name

    cases = [{"kind": k, "easing": e, "p": p / 12}
             for k in XFADE_TRANSITIONS for e in (None, "linear", "ease_in", "ease_out", "ease_in_out", "bogus")
             for p in range(13)]
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "ease.mjs"
        mod = (ROOT / "frontend" / "src" / "lib" / "timelineMath.js").resolve().as_uri()
        runner.write_text(
            "import { readFileSync } from 'node:fs';\n"
            f"import {{ easeTransitionProgress, transitionEasingName }} from '{mod}';\n"
            "const cases = JSON.parse(readFileSync(process.argv[2], 'utf8'));\n"
            "console.log(JSON.stringify(cases.map(c => [easeTransitionProgress(c.kind, c.easing, c.p), "
            "transitionEasingName(c.kind, c.easing)])));\n",
            encoding="utf-8",
        )
        cases_file = Path(tmp) / "cases.json"
        cases_file.write_text(json.dumps(cases), encoding="utf-8")
        res = subprocess.run(["node", str(runner), str(cases_file)], capture_output=True, text=True, encoding="utf-8")
        assert res.returncode == 0, res.stderr
        out = json.loads(res.stdout)
    for case, (value, name) in zip(cases, out):
        py_name = transition_easing_name(case["kind"], case["easing"])
        assert name == py_name, case
        assert value == pytest.approx(ease_camera_ratio(py_name, case["p"]), abs=1e-12), case
