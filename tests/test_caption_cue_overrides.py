"""Audit S5-06: per-caption scale / position / fontName reach the render.

SequencePlayer.drawSingleCue and subtitle_engine.generate_ass (cue_caption_variant
+ caption_metrics) read the same three fields per cue and fall back to the
clip-wide value when a cue has none. These tests pin that pair.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.config import VIDEO_WIDTH
from scripts.subtitle_engine import SubtitleEngine, caption_metrics
from scripts.subtitle import _load_font_family_map

ROOT = Path(__file__).resolve().parent.parent
JS_SRC = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
INSPECTOR_SRC = (
    ROOT / "frontend" / "src" / "components" / "editor" / "inspector" / "CaptionInspector.jsx"
).read_text(encoding="utf-8")

BASE = {"start": 0.0, "end": 1.5, "text": "ชาร์จไวมาก", "translation": ""}


def _gen(tmp_path, cues, name="o.ass", **kwargs):
    path = tmp_path / name
    kwargs.setdefault("font_name", "IBMPlex")
    kwargs.setdefault("bilingual", False)
    kwargs.setdefault("show_watermark", False)
    SubtitleEngine.generate_ass(cues=cues, output_ass_path=str(path), **kwargs)
    return path.read_text(encoding="utf-8")


def _style(text, name):
    line = next(l for l in text.splitlines() if l.startswith(f"Style: {name},"))
    return line.split(",")


def _dialogue_styles(text):
    return [l.split(",")[3] for l in text.splitlines() if l.startswith("Dialogue")]


def test_clip_wide_output_is_unchanged_without_overrides(tmp_path):
    plain = _gen(tmp_path, [dict(BASE)], "a.ass")
    same = _gen(tmp_path, [{**BASE, "scale": 1.0, "position": "bottom", "fontName": "IBMPlex"}], "b.ass")
    assert plain == same, "an override equal to the clip's values must not change the file"
    assert "_c1" not in plain


def test_caption_metrics_match_the_clip_wide_header(tmp_path):
    font_map = _load_font_family_map()
    for font, scale, pos in (("IBMPlex", 1.0, "bottom"), ("Kanit", 1.6, "top"), ("Mali", 0.7, "middle")):
        text = _gen(tmp_path, [dict(BASE)], "m.ass", font_name=font, caption_scale=scale, caption_position=pos)
        m = caption_metrics(font, scale, pos, video_width=VIDEO_WIDTH, font_map=font_map)
        white = _style(text, "TikTokWhite")
        shadow = _style(text, "TikTokSoftShadow")
        assert white[1] == m["caption_font"]
        assert int(white[2]) == m["font_size_boosted"]
        assert float(white[16]) == m["front_outline"]
        assert (int(white[18]), int(white[21])) == (m["alignment"], m["margin_v"])
        assert float(shadow[16]) == m["shadow_outline"]
        assert int(shadow[21]) == m["shadow_margin_v"]


def test_overridden_cue_uses_its_own_style_and_neighbours_keep_the_clip_style(tmp_path):
    text = _gen(tmp_path, [
        {**BASE, "scale": 1.6, "position": "top", "fontName": "Kanit"},
        {**BASE, "start": 1.5, "end": 3.0},
    ], ghost_reveal=False)
    font_map = _load_font_family_map()
    m = caption_metrics("Kanit", 1.6, "top", video_width=VIDEO_WIDTH, font_map=font_map)
    variant = _style(text, "TikTokWhite_c1")
    assert variant[1] == m["caption_font"] == "Kanit"
    assert int(variant[2]) == m["font_size_boosted"]
    assert (int(variant[18]), int(variant[21])) == (8, 180)
    caption_styles = [s for s in _dialogue_styles(text) if s.startswith("TikTok")]
    assert caption_styles == ["TikTokSoftShadow_c1", "TikTokWhite_c1", "TikTokSoftShadow", "TikTokWhite"]
    # the clip's own style lines are untouched
    assert _style(text, "TikTokWhite")[1] != "Kanit"


def test_each_distinct_override_gets_one_style_and_is_reused(tmp_path):
    text = _gen(tmp_path, [
        {**BASE, "scale": 2.0},
        {**BASE, "start": 1.5, "end": 3.0, "scale": 2.0},
        {**BASE, "start": 3.0, "end": 4.5, "position": "middle"},
    ], ghost_reveal=False)
    assert text.count("Style: TikTokWhite_c1,") == 1
    assert text.count("Style: TikTokWhite_c2,") == 1
    assert "TikTokWhite_c3" not in text
    assert int(_style(text, "TikTokWhite_c1")[2]) > int(_style(text, "TikTokWhite")[2])
    assert int(_style(text, "TikTokWhite_c2")[18]) == 5  # middle


def test_override_also_applies_with_ghost_reveal(tmp_path):
    text = _gen(tmp_path, [{**BASE, "scale": 1.5, "position": "top"}], ghost_reveal=True)
    styles = set(_dialogue_styles(text))
    assert "TikTokWhite_c1" in styles
    assert "TikTokWhite" not in styles
    # reveal anchors hang from the top margin (180), not the clip's bottom band
    assert "\\an7\\pos(" in text and ",180.0)" in text


def test_unknown_font_is_reported_and_clip_font_is_kept(tmp_path, capsys):
    plain = _gen(tmp_path, [dict(BASE)], "p.ass")
    bad = _gen(tmp_path, [{**BASE, "fontName": "NoSuchFace"}], "q.ass")
    assert plain == bad
    assert "ไม่รู้จักฟอนต์" in capsys.readouterr().out


def test_scale_is_clamped_like_the_clip_scale(tmp_path):
    huge = _gen(tmp_path, [{**BASE, "scale": 9.0}], "h.ass")
    cap = _gen(tmp_path, [{**BASE, "scale": 2.5}], "c.ass")
    assert huge == cap


def test_xy_position_still_wins_over_named_position(tmp_path):
    text = _gen(tmp_path, [{**BASE, "x": 0.5, "y": 0.3, "position": "top"}], ghost_reveal=False)
    assert "\\pos(540,576)" in text


def test_micro_cues_carry_font_name():
    micro = SubtitleEngine.generate_micro_cues(
        [{**BASE, "fontName": "Kanit", "scale": 1.2, "position": "top"}], translate=False
    )
    assert micro and all(c["fontName"] == "Kanit" and c["scale"] == 1.2 and c["position"] == "top" for c in micro)


def test_preview_draws_the_same_per_cue_fields():
    start = JS_SRC.index("function drawSingleCue(")
    body = re.sub(r"//[^\n]*", "", JS_SRC[start:JS_SRC.index("// Draw English lines", start)])
    for field in ("cue.scale", "cue.fontName", "cue.position"):
        assert field in body, f"preview does not draw per-cue {field}"
    assert "Math.min(2.5, Math.max(0.4, cue.scale))" in body  # the render's clamp


def test_inspector_offers_font_size_position_per_caption_and_colour_clip_wide():
    assert "selectedCaption.fontName || style?.fontName" in INSPECTOR_SRC
    assert "selectedCaption.scale ?? style?.captionScale" in INSPECTOR_SRC
    assert "selectedCaption.position || style?.captionPosition" in INSPECTOR_SRC
    # only colour and the presets stay behind "ปรับทั้งแผง"
    assert INSPECTOR_SRC.count("{clipWideControls && (") == 2
    assert "!(applyToAllCaptions && onUpdateAllCaptions)) return;" not in JS_SRC


def test_scaled_and_repositioned_caption_burns_in_real_frame(tmp_path):
    """libass burn on a 1080x1920 clip: the scaled+top caption sits at the top
    and is clearly wider than the plain bottom caption of the same clip."""
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the render regression")
    from PIL import Image

    ass = tmp_path / "burn.ass"
    ass.write_text(_gen(tmp_path, [
        {**BASE, "start": 0.0, "end": 1.0, "scale": 1.8, "position": "top", "fontName": "Kanit"},
        {**BASE, "start": 1.0, "end": 2.0},
    ], "burn_src.ass", ghost_reveal=False), encoding="utf-8")
    ass_filter = str(ass.resolve()).replace("\\", "/").replace(":", "\\:")
    frames = {}
    for label, t in (("scaled", "0.50"), ("plain", "1.50")):
        out = tmp_path / f"{label}.png"
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=0x3a6ea5:s=1080x1920:r=30:d=2",
            "-vf", f"subtitles='{ass_filter}':fontsdir='02_Assets/Fonts'",
            "-ss", t, "-frames:v", "1", str(out),
        ], check=True, capture_output=True, timeout=120)
        frames[label] = out

    def ink_box(path):
        img = Image.open(path).convert("RGB")
        px = img.load()
        white = [(x, y) for y in range(0, img.height, 2) for x in range(0, img.width, 2) if min(px[x, y]) > 235]
        assert white, f"no white caption ink in {path.name}"
        xs, ys = [p[0] for p in white], [p[1] for p in white]
        return min(xs), min(ys), max(xs), max(ys)

    sx0, sy0, sx1, sy1 = ink_box(frames["scaled"])
    px0, py0, px1, py1 = ink_box(frames["plain"])
    assert sy1 < 700, "the top caption must sit in the upper part of the frame"
    assert py0 > 1200, "the plain caption stays in the bottom band"
    assert (sx1 - sx0) > 1.5 * (px1 - px0), "the 1.8x caption must be clearly wider than the plain one"
    export = os.environ.get("OMNICUT_TEST_FRAME_DIR")
    if export and Path(export).is_dir():
        shutil.copy(frames["scaled"], Path(export) / "s5_06_scaled_top.png")
        shutil.copy(frames["plain"], Path(export) / "s5_06_plain_bottom.png")
