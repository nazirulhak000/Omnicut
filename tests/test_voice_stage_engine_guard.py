"""Regression coverage for VoiceStage's explicit TTS engine contract."""

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.pipeline_context import PipelineContext
from scripts.stages.voice_stage import VoiceStage


def _context(tmp_path: Path, engine):
    ctx = PipelineContext(
        product_name="Gadget",
        raw_video_path="dummy.mp4",
        project_name="voice-guard",
        voice_engine_type=engine,
        voice_preset="gemini_puck_male_hype",
        voice_rate=None,
    )
    ctx.project_dir = tmp_path
    ctx.script_data = {
        "lines": [{"text": "พูดทดสอบ", "sfx": None, "on_screen": ""}],
        "full_text": "พูดทดสอบ",
    }
    return ctx


def _gemini_success(output_path, **_kwargs):
    Path(output_path).write_bytes(b"RIFF-gemini")


@pytest.mark.parametrize("engine", [None, "", "   "])
def test_missing_or_blank_engine_uses_gemini_without_edge_fallback(tmp_path, engine):
    ctx = _context(tmp_path, engine)

    with patch(
        "scripts.gemini_tts_engine.GeminiFlashTTSEngine.resolve_voice",
        return_value="Puck",
    ), patch(
        "scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech",
        side_effect=_gemini_success,
    ) as gemini, patch(
        "scripts.voice_engine.VoiceEngine.generate_voiceover"
    ) as edge, patch(
        "scripts.stages.voice_stage._probe_audio_duration", return_value=1.0
    ), patch(
        "scripts.stages.voice_stage._rms_aligned_cues",
        return_value=[{"start": 0.0, "end": 1.0, "text": "พูดทดสอบ"}],
    ):
        VoiceStage.run(ctx)

    assert ctx.voice_engine_type == "gemini_tts"
    assert ctx.voice_engine_used == "gemini_tts"
    gemini.assert_called_once()
    edge.assert_not_called()


def test_edge_engine_is_only_used_when_explicitly_requested(tmp_path, capsys):
    ctx = _context(tmp_path, "edge_tts")
    voice_result = {
        "cues": [{"start": 0.0, "end": 1.0, "text": "พูดทดสอบ", "line_idx": 0}],
        "duration": 1.0,
    }

    with patch(
        "scripts.voice_engine.VoiceEngine.generate_voiceover",
        return_value=voice_result,
    ) as edge, patch(
        "scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech"
    ) as gemini:
        VoiceStage.run(ctx)

    assert ctx.voice_engine_used == "edge_tts"
    edge.assert_called_once()
    gemini.assert_not_called()
    assert "explicitly requested" in capsys.readouterr().out


def test_unknown_engine_fails_closed_without_invoking_tts(tmp_path):
    ctx = _context(tmp_path, "not-a-provider")

    with patch("scripts.voice_engine.VoiceEngine.generate_voiceover") as edge, patch(
        "scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech"
    ) as gemini:
        with pytest.raises(ValueError, match="Unknown or unsupported voice engine"):
            VoiceStage.run(ctx)

    edge.assert_not_called()
    gemini.assert_not_called()
