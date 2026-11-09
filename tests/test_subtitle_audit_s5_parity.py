"""Preview = Render guards for audit 20261109 section 5 (S5-03..S5-16).

Values SequencePlayer.jsx mirrored by hand with no assertion until this audit,
plus ASS-level behaviour for the reveal/SpecBar fixes. Pixel checks for the
same fixes live in test_preview_render_behavior.py.
"""

import inspect
import re
from pathlib import Path

import pytest

from scripts.config import VIDEO_WIDTH

ROOT = Path(__file__).resolve().parent.parent
JS_SRC = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
ENGINE_SRC = (ROOT / "scripts" / "subtitle_engine.py").read_text(encoding="utf-8")
INSPECTOR_SRC = (
    ROOT / "frontend" / "src" / "components" / "editor" / "inspector" / "CaptionInspector.jsx"
).read_text(encoding="utf-8")


def _grab(text, pattern, cast=float):
    match = re.search(pattern, text, re.S)
    assert match, f"parity probe found nothing for {pattern!r} -- did the code move?"
    return cast(match.group(1))


def _events(path):
    return [l for l in Path(path).read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue")]


def _drawing_body(text):
    return text.split(",,", 1)[1] if ",," in text else text


# --------------------------------------------------------------- S5-07
def test_caption_top_position_matches_render_margin():
    from scripts.subtitle_engine import CAPTION_POSITIONS

    assert _grab(JS_SRC, r"const CAPTION_Y = \{[^}]*top: (\d+) / 1920") == CAPTION_POSITIONS["top"][1]
    assert _grab(JS_SRC, r"const CAPTION_Y = \{ bottom: 1 - (\d+) / 1920") == 420


# --------------------------------------------------------------- S5-10
def test_watermark_alpha_outline_and_face_match_render():
    from scripts.subtitle import ass_glyph_scale
    from scripts.subtitle_engine import (
        WATERMARK_ALPHA,
        WATERMARK_FONT_FAMILY,
        WATERMARK_FS_RATIO,
        WATERMARK_OUTLINE_RATIO,
    )

    alpha_hex = re.search(r"&H([0-9A-Fa-f]{2})&", WATERMARK_ALPHA).group(1)
    js_alpha = re.search(r"const WATERMARK_ALPHA = \(255 - 0x([0-9A-Fa-f]{2})\) / 255;", JS_SRC)
    assert js_alpha, "preview watermark alpha must be derived from the ASS byte"
    assert js_alpha.group(1).upper() == alpha_hex.upper()

    watermark_fs = max(14, int(round(VIDEO_WIDTH * WATERMARK_FS_RATIO)))
    boosted = int(round(watermark_fs / ass_glyph_scale(WATERMARK_FONT_FAMILY)))
    render_outline = round(max(2.0, boosted * WATERMARK_OUTLINE_RATIO), 1)
    assert _grab(JS_SRC, r"const WATERMARK_OUTLINE_PX = ([\d.]+);") == render_outline
    assert "ctx.lineWidth = WATERMARK_OUTLINE_PX;" in JS_SRC
    assert WATERMARK_FONT_FAMILY == "IBM Plex Sans Thai"
    assert "ctx.font = `600 ${fontSize}px 'IBM Plex Sans Thai', sans-serif`;" in JS_SRC


@pytest.mark.parametrize("font", ["IBMPlex", "Kanit", "Prompt"])
def test_watermark_style_uses_fixed_ibm_face_for_any_caption_font(tmp_path, font):
    from scripts.subtitle_engine import SubtitleEngine

    out = tmp_path / "wm.ass"
    SubtitleEngine.generate_ass(cues=[], output_ass_path=str(out), font_name=font, bilingual=False)
    style = next(l for l in out.read_text(encoding="utf-8").splitlines() if l.startswith("Style: Watermark,"))
    fields = style.split(",")
    assert fields[1] == "IBM Plex Sans Thai SemiBold", style
    assert fields[2] == "68" and fields[16] == "3.4", style


# --------------------------------------------------------------- S5-08
def test_kanit_and_prompt_caption_weight_is_bold_700():
    from scripts.subtitle import ass_caption_face

    assert ass_caption_face("Kanit")[1] == 1
    assert ass_caption_face("Prompt")[1] == 1
    start = JS_SRC.index("function drawSingleCue(")
    body = JS_SRC[start:JS_SRC.index("const repairThaiMarks = true;", start)]
    assert "let fontWeight = '700';" in body
    prompt = body[body.index("fontFamName === 'Prompt'"):body.index("fontFamName === 'Mali'")]
    assert "fontWeight = '700';" in prompt
    assert "'900'" not in body and "'800'" not in body


# --------------------------------------------------------------- S5-09
def test_ghost_reveal_has_no_shadow_on_either_side(tmp_path):
    from scripts.subtitle_engine import SubtitleEngine

    assert "ctx.shadowColor = revealSegments ? 'transparent' : 'rgba(0, 0, 0, 0.9)';" in JS_SRC
    out = tmp_path / "reveal_shadow.ass"
    SubtitleEngine.generate_ass(
        cues=[{"start": 0.0, "end": 1.5, "text": "ชาร์จไวมาก", "translation": ""}],
        output_ass_path=str(out), font_name="IBMPlex", bilingual=False, ghost_reveal=True,
    )
    events = _events(out)
    assert any(",TikTokWhite,," in l for l in events)
    assert not any(",TikTokSoftShadow,," in l for l in events)


# --------------------------------------------------------------- S5-06
def test_per_cue_scale_position_font_are_clip_wide_on_both_sides(tmp_path):
    from scripts.subtitle_engine import SubtitleEngine

    base = {"start": 0.0, "end": 1.5, "text": "ชาร์จไวมาก", "translation": ""}
    plain, overridden = tmp_path / "plain.ass", tmp_path / "overridden.ass"
    SubtitleEngine.generate_ass(cues=[dict(base)], output_ass_path=str(plain), font_name="IBMPlex", bilingual=False)
    SubtitleEngine.generate_ass(
        cues=[{**base, "scale": 1.6, "position": "top", "fontName": "Kanit"}],
        output_ass_path=str(overridden), font_name="IBMPlex", bilingual=False,
    )
    # The render does not read these per-cue fields...
    assert plain.read_text(encoding="utf-8") == overridden.read_text(encoding="utf-8")
    # ...so the preview must not draw them either,
    start = JS_SRC.index("function drawSingleCue(")
    body = JS_SRC[start:JS_SRC.index("// Draw English lines", start)]
    body = re.sub(r"//[^\n]*", "", body)  # code only, not the comments explaining it
    for field in ("cue.scale", "cue.fontName", "cue.position"):
        assert field not in body, f"preview still draws per-cue {field}"
    # ...and the editor does not offer them per caption.
    assert "if (selectedBox.type === 'caption' && !(applyToAllCaptions && onUpdateAllCaptions)) return;" in JS_SRC
    assert "const clipWideControls = !!effectiveApplyToAll;" in INSPECTOR_SRC
    assert INSPECTOR_SRC.count("{clipWideControls && (") == 5  # font, size, position, colour, presets


# --------------------------------------------------------------- S5-11
def test_format_ass_time_matches_reveal_formatter_every_centisecond():
    from scripts.subtitle.ghost_reveal_ass import _ass_time
    from scripts.subtitle_engine import SubtitleEngine

    for cs in range(0, 1001):
        t = cs / 100.0
        expected = f"0:00:{cs // 100:02d}.{cs % 100:02d}"
        assert SubtitleEngine._format_ass_time(t) == _ass_time(t) == expected, t
    assert SubtitleEngine._format_ass_time(0.29) == "0:00:00.29"
    assert SubtitleEngine._format_ass_time(3725.999) == "1:02:06.00"


# --------------------------------------------------------------- S5-04
def test_ghost_reveal_no_pop_rule_matches_on_both_sides():
    from scripts.subtitle import THAI_STACKED_MARK_RE

    js = re.search(r"const GHOST_NO_POP_RE = /(.+?)/;", JS_SRC).group(1)
    js_re = re.compile(js.encode("ascii").decode("unicode_escape"))
    for word in ("ที่", "นั่ง", "เปลี่ยน", "ชาร์จ", "กล้อง", "ซื้อ", "ได้"):
        assert bool(js_re.search(word)) == bool(THAI_STACKED_MARK_RE.search(word)), word
    assert "GHOST_NO_POP_RE.test(word.text) ? 1 : GHOST_ACTIVE_SCALE" in JS_SRC


def test_reveal_tone_companion_is_green_while_its_word_is_active(tmp_path):
    from scripts.subtitle.ghost_reveal_ass import ACTIVE_COLOUR, _ass_time
    from scripts.subtitle_engine import SubtitleEngine

    out = tmp_path / "tones.ass"
    _, micro = SubtitleEngine.generate_ass(
        cues=[{"start": 0.0, "end": 3.0, "text": "ที่นี่ นั่ง เปลี่ยน", "translation": ""}],
        output_ass_path=str(out), font_name="IBMPlex", bilingual=False, ghost_reveal=True,
    )
    caption = [l for l in _events(out) if ",TikTokWhite,," in l]
    body = [l for l in caption if "\\1a&HFF&" not in l]
    companions = [l for l in caption if "\\1a&HFF&" in l]
    # Every word here has a detached tone: active, but never popped to 114%.
    assert body and not any("\\fscx114" in l for l in body)
    # 4 detached tones, each with a green phase then a white phase.
    green = [l for l in companions if f"\\c{ACTIVE_COLOUR}" in l]
    assert len(green) == 4 and len(companions) == 8
    first = micro[0]["word_reveal"][0]
    assert any(l.startswith(f"Dialogue: 1,{_ass_time(first['start'])},{_ass_time(first['end'])},") for l in green)
    # Companions are laid out on the same (space-free) string as the body.
    body_text = re.sub(r"\{[^}]*\}", "", _drawing_body(body[-1]))
    for line in companions:
        assert " " not in re.sub(r"\{[^}]*\}", "", _drawing_body(line)), line
    assert " " not in body_text


def test_wrapped_reveal_caption_keeps_its_tone_companions(tmp_path):
    """A wrapped reveal scanned already-repaired words and emitted no tones."""
    from scripts.subtitle_engine import SubtitleEngine

    out = tmp_path / "wrapped.ass"
    SubtitleEngine.generate_ass(
        cues=[{"start": 0.0, "end": 3.0, "text": "ที่นี่เปลี่ยน\nนั่งได้ที่นี่", "translation": ""}],
        output_ass_path=str(out), font_name="IBMPlex", bilingual=False, ghost_reveal=True,
    )
    companions = [l for l in _events(out) if ",TikTokWhite,," in l and "\\1a&HFF&" in l]
    # ที่ นี่ เปลี่ยน | นั่ง ที่ นี่ -> 6 detached tones (ได้'s tone sits on a consonant).
    assert len(companions) == 12


# --------------------------------------------------------------- S5-05
def test_last_reveal_word_leaves_a_white_settle(tmp_path):
    from scripts.subtitle.word_reveal import SETTLE_SEC, build_word_reveal
    from scripts.subtitle_engine import SubtitleEngine

    reveal = build_word_reveal("ชาร์จไวมาก", 0.0, 2.0)
    assert reveal[-1]["end"] <= 2.0 - SETTLE_SEC + 1e-9
    timed = build_word_reveal(
        "ชาร์จไว", 0.0, 2.0,
        [{"text": "ชาร์จ", "start": 0.0, "end": 0.5}, {"text": "ไว", "start": 0.5, "end": 1.1}],
    )
    assert timed[-1]["end"] == pytest.approx(1.1)

    out = tmp_path / "settle.ass"
    SubtitleEngine.generate_ass(
        cues=[{"start": 0.0, "end": 2.0, "text": "ชาร์จไวมาก", "translation": ""}],
        output_ass_path=str(out), font_name="IBMPlex", bilingual=False, ghost_reveal=True,
    )
    body = [l for l in _events(out) if ",TikTokWhite,," in l and "\\1a&HFF&" not in l]
    settle = body[-1]
    assert settle.startswith("Dialogue: 1,0:00:01.80,0:00:02.00,")
    assert "66&" not in settle  # no neon green in the settle event
    assert "const settled = activeIdx === reveal.length - 1 && t >= reveal[reveal.length - 1].end;" in JS_SRC


# --------------------------------------------------------- S5-03 / S5-14
def test_specbar_box_is_yellow_with_black_ink_left_of_button_rail():
    from scripts import subtitle_engine as eng

    assert eng.SPECBAR_BOX_COLOUR == "&H0000E6FF"
    assert eng.SPECBAR_TEXT_COLOUR == "&H00000000"
    assert VIDEO_WIDTH - eng.SPECBAR_MARGIN_R + eng.SPECBAR_BOX_PAD <= 960
    fields = re.search(r"Style: SpecBar,[^\n]*", ENGINE_SRC).group(0).split(",")
    # Primary, Secondary, Outline, Back -- BorderStyle 3 paints the box with Outline.
    assert fields[3:7] == ["{SPECBAR_TEXT_COLOUR}", "&H000000FF", "{SPECBAR_BOX_COLOUR}", "{SPECBAR_BOX_COLOUR}"]
    assert fields[15] == "3"


# --------------------------------------------------------------- S5-16
def test_generate_ass_default_font_is_the_pipeline_default():
    from scripts.pipeline_context import PipelineContext
    from scripts.subtitle_engine import SubtitleEngine

    default = inspect.signature(SubtitleEngine.generate_ass).parameters["font_name"].default
    assert default == "IBMPlex"
    assert PipelineContext.__dataclass_fields__["font_name"].default == default
    assert "'IBMPlex'" in JS_SRC[JS_SRC.index("function drawSingleCue("):][:2000]


# --------------------------------------------------------------- S5-12
def test_thai_only_render_never_calls_the_translator(tmp_path, monkeypatch):
    from scripts import translator
    from scripts.subtitle_engine import SubtitleEngine

    def boom(*_a, **_k):
        raise AssertionError("translator called for a Thai-only render")

    monkeypatch.setattr(translator.SubtitleTranslator, "translate_batch", staticmethod(boom))
    cues = [{"start": 0.0, "end": 2.0, "text": "ชาร์จไวมาก ใช้ได้ทั้งวัน", "translation": ""}]
    micro = SubtitleEngine.generate_micro_cues([dict(c) for c in cues], translate=False)
    assert micro and all(m["translation"] == "" for m in micro)
    SubtitleEngine.generate_ass([dict(c) for c in cues], str(tmp_path / "th.ass"), font_name="IBMPlex", bilingual=False)


# --------------------------------------------------------------- S5-15
def test_single_word_burst_folds_into_its_neighbour_when_it_fits():
    from scripts.subtitle_engine import SubtitleEngine as S

    assert S._merge_single_word_bursts(["ถ่ายสวยมาก", "กล้อง"], 24) == ["ถ่ายสวยมาก กล้อง"]
    assert S._merge_single_word_bursts(["กล้อง", "ถ่ายสวยมาก"], 24) == ["กล้อง ถ่ายสวยมาก"]
    # Never past the line: a full neighbour keeps the word on its own.
    full = "ถ่ายภาพสวยคมชัดทุกมุมเลย"
    assert S._merge_single_word_bursts([full, "กล้อง"], 24) == [full, "กล้อง"]
    # Multi-word bursts are left alone.
    assert S._merge_single_word_bursts(["ชาร์จไว", "ใช้ได้ทั้งวัน"], 24) == ["ชาร์จไว", "ใช้ได้ทั้งวัน"]


def test_micro_cues_have_no_lone_word_burst_when_the_previous_has_room():
    from scripts.subtitle_engine import SubtitleEngine as S

    micro = S.generate_micro_cues(
        [{"start": 0.0, "end": 3.0, "text": "ถ่ายสวยมาก กล้อง", "translation": ""}], translate=False,
    )
    assert [m["text"] for m in micro] == ["ถ่ายสวยมาก กล้อง"]


# ---------------------------------------------- S5-03 / S5-04 / S5-05 pixels
def test_specbar_and_reveal_tones_render_correctly_in_real_frames(tmp_path):
    """Burned with libass + the project fonts: yellow box with black ink left of
    the button rail, green tone over the active word, no green in the settle."""
    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the render regression")
    from PIL import Image

    from scripts.subtitle_engine import SubtitleEngine

    ass_path = tmp_path / "s5.ass"
    SubtitleEngine.generate_ass(
        cues=[{"start": 0.0, "end": 3.0, "text": "ที่นี่ นั่ง เปลี่ยน", "translation": "", "on_screen": "5000mAh"}],
        output_ass_path=str(ass_path), font_name="IBMPlex", bilingual=False,
        ghost_reveal=True, show_watermark=False,
    )
    ass_filter = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    for t in ("0.30", "2.90"):
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=0x3a6ea5:s=1080x1920:r=30:d=3",
            "-vf", f"subtitles='{ass_filter}':fontsdir='02_Assets/Fonts'",
            "-ss", t, "-frames:v", "1", str(tmp_path / f"f{t}.png"),
        ], check=True, capture_output=True)

    active = Image.open(tmp_path / "f0.30.png").convert("RGB")
    px = active.load()
    yellow = [(x, y) for y in range(250, 700) for x in range(active.width)
              if px[x, y][0] > 220 and px[x, y][1] > 200 and px[x, y][2] < 60]
    assert yellow, "SpecBar box was not painted yellow"
    assert max(x for x, _ in yellow) < 960, "SpecBar box reaches TikTok's button rail"
    x0, x1 = min(x for x, _ in yellow), max(x for x, _ in yellow)
    y0, y1 = min(y for _, y in yellow), max(y for _, y in yellow)
    ink = sum(1 for y in range(y0, y1) for x in range(x0, x1) if sum(px[x, y]) < 120)
    assert ink > 300, "SpecBar text is not visible on its box"

    def green_rows(image):
        p = image.load()
        return [y for y in range(1300, 1600) for x in range(image.width)
                if p[x, y][1] > 200 and p[x, y][0] < 150 and p[x, y][2] < 100]

    assert green_rows(active), "active word is not green"
    # At t=0.30 only the first word (ที่นี่, active) is visible, so the caption
    # band must hold no white ink: its detached tones used to stay white.
    white = sum(1 for y in range(1300, 1600) for x in range(active.width)
                if min(px[x, y]) > 230)
    assert white == 0, f"{white} white px in the active word -- tone companions not green"
    assert not green_rows(Image.open(tmp_path / "f2.90.png").convert("RGB")), "settle frame still green"
