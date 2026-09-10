"""Regression tests for invalidating stale subtitle artifacts."""

import builtins
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
