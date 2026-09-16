"""Regression tests for invalidating stale subtitle artifacts."""

import builtins
import re
from pathlib import Path

import pytest


def test_generated_ass_is_marked_with_current_caption_contract(tmp_path):
    from scripts.subtitle_engine import (
        SubtitleEngine,
        subtitle_artifact_is_current,
    )

    ass_path = tmp_path / "subtitles.ass"
    SubtitleEngine.generate_ass(
        cues=[{"id": 1, "start": 0.0, "end": 1.0, "text": "ทดสอบ"}],
        output_ass_path=str(ass_path),
        font_name="IBMPlex",
        bilingual=False,
    )

    assert subtitle_artifact_is_current(ass_path)
    style = next(
        line for line in ass_path.read_text(encoding="utf-8").splitlines()
        if line.startswith("Style: TikTokWhite,")
    )
    assert int(style.split(",")[2]) == 82


def test_ass_glyph_scale_does_not_depend_on_optional_fonttools(monkeypatch):
    from scripts.subtitle import font_metrics

    real_import = builtins.__import__

    def import_without_fonttools(name, *args, **kwargs):
        if name == "fontTools" or name.startswith("fontTools."):
            raise ModuleNotFoundError("fontTools intentionally unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_fonttools)
    font_metrics._ASS_GLYPH_SCALE_CACHE.clear()

    assert font_metrics.ass_glyph_scale("IBM Plex Sans Thai") == pytest.approx(
        1000 / 1650
    )


def test_legacy_ass_without_contract_marker_is_not_reused(tmp_path):
    from scripts.subtitle_engine import subtitle_artifact_is_current

    ass_path = Path(tmp_path) / "legacy.ass"
    ass_path.write_text(
        "[Script Info]\nPlayResX: 1080\nPlayResY: 1920\n"
        "Style: TikTokWhite,IBM Plex Sans Thai,50\n",
        encoding="utf-8",
    )

    assert not subtitle_artifact_is_current(ass_path)


def test_previous_v3_contract_is_invalidated(tmp_path):
    from scripts.subtitle_engine import subtitle_artifact_is_current

    ass_path = Path(tmp_path) / "v3.ass"
    ass_path.write_text(
        "[Script Info]\n; OmniCutSubtitleContract: v3\n"
        "Style: TikTokWhite,IBM Plex Sans Thai SemiBold,50\n",
        encoding="utf-8",
    )

    assert not subtitle_artifact_is_current(ass_path)


def test_previous_v4_contract_is_invalidated_by_watermark_bump(tmp_path):
    """v5 added the always-on copyright watermark -- old v4 artifacts predate
    it and must regenerate rather than be reused as-is."""
    from scripts.subtitle_engine import subtitle_artifact_is_current

    ass_path = Path(tmp_path) / "v4.ass"
    ass_path.write_text(
        "[Script Info]\n; OmniCutSubtitleContract: v4\n"
        "Style: TikTokWhite,IBM Plex Sans Thai SemiBold,50\n",
        encoding="utf-8",
    )

    assert not subtitle_artifact_is_current(ass_path)


def test_previous_v7_contract_is_invalidated_by_stacked_mark_matrix_bump(tmp_path):
    from scripts.subtitle_engine import subtitle_artifact_is_current

    ass_path = Path(tmp_path) / "v7.ass"
    ass_path.write_text(
        "[Script Info]\n; OmniCutSubtitleContract: v7\n"
        "Style: TikTokWhite,Prompt,76\n",
        encoding="utf-8",
    )

    assert not subtitle_artifact_is_current(ass_path)


def test_generated_ass_always_includes_copyright_watermark(tmp_path):
    """The watermark is a fixed brand-protection mark, not a user overlay --
    it must appear on every render regardless of hook/overlay content, be
    unicode-exact, sit in the right safe-zone column, and be rotated with a
    constant \\frz (no \\t keyframe, unlike the animated wobble effects)."""
    from scripts.subtitle_engine import (
        SubtitleEngine,
        WATERMARK_TEXT,
        WATERMARK_X_RATIO,
        WATERMARK_Y_RATIO,
    )

    ass_path = tmp_path / "subtitles.ass"
    SubtitleEngine.generate_ass(
        cues=[{"id": 1, "start": 0.0, "end": 1.0, "text": "ทดสอบ"}],
        output_ass_path=str(ass_path),
        font_name="IBMPlex",
        bilingual=False,
        hook_brand="", hook_model="", hook_label="",
        overlays=[],
    )
    content = ass_path.read_text(encoding="utf-8")

    style_line = next(
        line for line in content.splitlines() if line.startswith("Style: Watermark,")
    )
    dialogue_line = next(
        line for line in content.splitlines() if ",Watermark,," in line
    )

    assert WATERMARK_TEXT in dialogue_line
    assert "\\frz-90" in dialogue_line
    assert "\\t(" not in dialogue_line  # constant rotation, not an animated keyframe
    expected_x = int(round(1080 * WATERMARK_X_RATIO))
    expected_y = int(round(1920 * WATERMARK_Y_RATIO))
    assert f"\\pos({expected_x},{expected_y})" in dialogue_line
    # Style row's Fontsize field (index 2) is user-tunable (WATERMARK_FS_RATIO)
    # -- just assert it produced a sane positive size, not a specific number.
    style_fontsize = int(style_line.split(",")[2])
    assert style_fontsize > 0


def test_prompt_caption_with_emoji_detaches_stacked_thai_tone_mark(tmp_path):
    """Emoji fallback must not disable the `ั` + `่` render repair.

    This is the production shape from the reported clip. Prompt's bundled
    face collapses the pair under libass, while the leading shopping-cart
    emoji previously caused the repair path to return early.
    """
    from scripts.subtitle.font_metrics import repair_thai_stacked_marks
    from scripts.subtitle_engine import SubtitleEngine

    ass_path = tmp_path / "prompt-emoji.ass"
    SubtitleEngine.generate_ass(
        cues=[{
            "id": 1,
            "start": 0.0,
            "end": 1.0,
            "text": "🛒 บอกเลยว่าโปรโมชั่นนี้",
        }],
        output_ass_path=str(ass_path),
        font_name="Prompt",
        bilingual=False,
        caption_position="middle",
        show_watermark=False,
    )

    caption_lines = [
        line for line in ass_path.read_text(encoding="utf-8").splitlines()
        if ",TikTokWhite,," in line
    ]
    assert len(caption_lines) >= 2
    repaired_word, companions = repair_thai_stacked_marks("โปรโมชั่นนี้")
    assert len(companions) == 2
    assert any(repaired_word in re.sub(r"\{[^{}]*\}", "", line) for line in caption_lines)
    assert all(pair not in line for line in caption_lines for pair in ("ั่", "ี้"))


def test_prompt_caption_detaches_all_upper_vowel_tone_pairs_from_reported_text(tmp_path):
    """The repair must cover ``ื้``/``ื่`` and every Thai upper-vowel/tone pair."""
    from scripts.subtitle_engine import SubtitleEngine

    source_text = "⚡ ปกติซื้อตามช็อปราคาแรงเอาเรื่อง"
    ass_path = tmp_path / "all-stacked-marks.ass"
    SubtitleEngine.generate_ass(
        cues=[{
            "id": 1,
            "start": 0.0,
            "end": 1.0,
            "text": source_text,
        }],
        output_ass_path=str(ass_path),
        font_name="Prompt",
        bilingual=False,
        caption_position="middle",
        show_watermark=False,
    )

    caption_lines = [
        line for line in ass_path.read_text(encoding="utf-8").splitlines()
        if ",TikTokWhite,," in line
    ]
    assert len(caption_lines) >= 3
    assert all(pair not in line for line in caption_lines for pair in ("ื้", "ื่"))
