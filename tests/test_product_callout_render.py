"""Focused Preview/Render contract tests for semantic Product Callouts."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JS_SOURCE = (ROOT / "frontend" / "src" / "components" / "SequencePlayer.jsx").read_text(encoding="utf-8")
PY_SOURCE = (ROOT / "scripts" / "subtitle" / "overlay_events.py").read_text(encoding="utf-8")


def _callout():
    return {
        "id": "callout-thai-stack",
        "kind": "text",
        "role": "product_callout",
        "callout_type": "feature",
        "start": 0.0,
        "end": 1.2,
        "x": 0.5,
        "y": 0.5,
        "tiers": [{"text": "กั่ก", "look": {}}],
        "look": {
            "font": "Prompt",
            "size_pct": 100,
            "color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_px": 2,
            "shadow": None,
        },
        "anim": {"in": "none", "loop": "none", "out": "fade"},
    }


def test_canvas_and_ass_share_the_callout_only_thai_repair_contract():
    assert "overlay.role === 'product_callout'" in JS_SOURCE
    assert "function drawProductCalloutText" in JS_SOURCE
    assert "drawProductCalloutText(" in JS_SOURCE
    assert '_is_product_callout' in PY_SOURCE
    assert 'repair_thai_stacked_marks(text)' in PY_SOURCE
    assert 'THAI_STACKED_MARK_RAISE_EM' in PY_SOURCE
    assert 'Math.max(4, Math.round(fontSize * THAI_STACKED_MARK_RAISE_EM))' in JS_SOURCE
    assert 'max(6, int(round(render_fs * THAI_STACKED_MARK_RAISE_EM)))' in PY_SOURCE


def test_product_callout_event_adapter_detaches_tone_without_duplicate_body():
    from scripts.subtitle.overlay_events import _text_overlay_events

    events = _text_overlay_events(
        _callout(),
        {
            "video_width": 1080,
            "video_height": 1920,
            "base_fs": 50,
            "resolved_font": "Prompt",
            "font_map": {},
        },
    )

    assert len(events) == 4, "shadow/main body plus shadow/main detached-tone events"
    assert sum("กัก" in event for event in events) == 2
    assert all("กั่ก" not in event for event in events)
    companions = [event for event in events if r"\1a&HFF&" in event]
    assert len(companions) == 2
    assert all(r"\pos(518.0,929.0)" in event for event in companions if "TextOverlayMain" in event)


def test_legacy_text_overlay_does_not_opt_into_callout_repair():
    from scripts.subtitle.overlay_events import _text_overlay_events

    legacy = {**_callout(), "role": None}
    events = _text_overlay_events(
        legacy,
        {
            "video_width": 1080,
            "video_height": 1920,
            "base_fs": 50,
            "resolved_font": "Prompt",
            "font_map": {},
        },
    )

    assert len(events) == 2
    assert all("กั่ก" in event for event in events)
    assert all(r"\1a&HFF&" not in event for event in events)


def test_product_callout_replaces_matching_legacy_spec_bar(tmp_path):
    from scripts.subtitle_engine import SubtitleEngine

    ass_path = tmp_path / "product-callout-dedupe.ass"
    SubtitleEngine.generate_ass(
        cues=[{"start": 0.0, "end": 1.0, "text": "ทดสอบ", "on_screen": "20000mAh"}],
        overlays=[{**_callout(), "tiers": [{"text": "20000mAh", "look": {}}]}],
        output_ass_path=str(ass_path),
        font_name="Prompt",
        bilingual=False,
        show_watermark=False,
    )
    generated = ass_path.read_text(encoding="utf-8")
    assert not any(
        line.startswith("Dialogue:") and ",SpecBar," in line
        for line in generated.splitlines()
    )
    assert sum(",TextOverlayMain," in line for line in generated.splitlines()) >= 2


@pytest.mark.render_regression
def test_product_callout_real_render_has_enter_hold_exit_frames(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the Product Callout render regression")

    from PIL import Image
    from scripts.subtitle_engine import SubtitleEngine

    ass_path = tmp_path / "product_callout.ass"
    SubtitleEngine.generate_ass(
        cues=[],
        overlays=[_callout()],
        output_ass_path=str(ass_path),
        font_name="Prompt",
        bilingual=False,
        show_watermark=False,
    )
    generated = ass_path.read_text(encoding="utf-8")
    assert sum(line.startswith("Dialogue: 4,") and ",TextOverlayMain," in line for line in generated.splitlines()) == 2
    assert "กั่ก" not in generated
    assert generated.count("กัก") == 2
    assert generated.count(r"\1a&HFF&") >= 2

    ass_filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    frames_pattern = str(tmp_path / "frame-%02d.png")
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-threads", "1", "-f", "lavfi",
            "-i", "color=c=0x303030:s=1080x1920:r=30:d=1.2",
            "-vf", f"subtitles='{ass_filter_path}':fontsdir='02_Assets/Fonts'",
            "-frames:v", "36", frames_pattern,
        ],
        cwd=ROOT,
        check=True,
    )

    def ink_count(path):
        image = Image.open(path).convert("RGB")
        pixels = image.load()
        points = 0
        for y in range(760, 1120):
            for x in range(250, 830):
                red, green, blue = pixels[x, y]
                points += red > 150 and green > 150 and blue > 150
        return points

    enter = ink_count(tmp_path / "frame-02.png")
    hold = ink_count(tmp_path / "frame-16.png")
    exit_frame = ink_count(tmp_path / "frame-35.png")
    assert enter > 0
    assert hold > enter, (enter, hold, exit_frame)
    assert exit_frame < hold, (enter, hold, exit_frame)
