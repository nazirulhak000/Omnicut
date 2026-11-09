"""VoiceStage: no double request matrix on 429, a stricter shot-list reuse key,
and a checked human-voice conversion (audit S2-12, S2-15, S2-17).

Offline: every TTS / ffmpeg call is mocked; files live in tmp_path.
"""

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts.error_handler import AppError, ErrorCategory
from scripts.gemini_tts_engine import GeminiTTSError
from scripts.pipeline_context import PipelineContext
from scripts.quota import is_quota_error, is_retry_futile
from scripts.stages.voice_stage import VoiceStage


def _ctx(tmp_path, **overrides):
    values = dict(
        product_name="Gadget", raw_video_path="dummy.mp4", project_name="voice-test",
        voice_engine_type="gemini_tts", voice_preset="gemini_fenrir_male_strong",
    )
    values.update(overrides)
    ctx = PipelineContext(**values)
    ctx.project_dir = tmp_path
    ctx.script_data = {
        "lines": [{"text": "บทที่หนึ่ง", "sfx": None, "on_screen": ""},
                  {"text": "บทที่สอง", "sfx": None, "on_screen": ""}],
        "full_text": "บทที่หนึ่ง บทที่สอง",
    }
    return ctx


# --- S2-12 -------------------------------------------------------------------

def _rate_limited():
    return GeminiTTSError(message_th="ติดลิมิต", suggestion_th="รอสักครู่", code="GEMINI_TTS_RATE_LIMITED")


def test_rate_limit_is_futile_but_not_the_user_quota():
    err = _rate_limited()
    assert is_retry_futile(err)
    assert not is_quota_error(err)
    assert not is_retry_futile(GeminiTTSError(message_th="x", code="GEMINI_TTS_FAILED"))
    assert not is_retry_futile(RuntimeError("boom"))


def test_matrix_wide_429_is_not_retried(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech",
               side_effect=_rate_limited()) as gen, \
            patch("scripts.stages.voice_stage.time.sleep") as sleep:
        with pytest.raises(AppError) as excinfo:
            VoiceStage.run(ctx)
    assert excinfo.value.code == "GEMINI_TTS_RATE_LIMITED"
    assert gen.call_count == 1
    sleep.assert_not_called()


def test_transient_failure_is_still_retried_once(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech",
               side_effect=GeminiTTSError(message_th="ล้ม", code="GEMINI_TTS_FAILED")) as gen, \
            patch("scripts.stages.voice_stage.time.sleep"):
        with pytest.raises(AppError):
            VoiceStage.run(ctx)
    assert gen.call_count == 2


# --- S2-15 -------------------------------------------------------------------

def _record(tmp_path, **voice_params):
    audio = tmp_path / "shot_list_voice.wav"
    audio.write_bytes(b"RIFF-shot-list")
    cues = [{"start": 0.0, "end": 1.0, "text": "บทที่หนึ่ง"}, {"start": 1.0, "end": 2.0, "text": "บทที่สอง"}]
    return {
        "voice_audio_path": str(audio), "cues": cues, "beat_cues": cues, "total_duration": 2.0,
        "custom_script": "บทที่หนึ่ง บทที่สอง",
        "voice_params": {"voice_engine_type": "gemini_tts", "voice_preset": "gemini_fenrir_male_strong",
                         "voice_rate": "+15%", "ad_tone": "commercial_premium", **voice_params},
    }


def _run_with_record(ctx, record):
    def fake_speech(output_path, **_kw):
        Path(output_path).write_bytes(b"RIFF-new")

    with patch("scripts.shot_lists_store.ShotListsStore.get", return_value=record), \
            patch("scripts.gemini_tts_engine.GeminiFlashTTSEngine.generate_speech",
                  side_effect=fake_speech) as gen, \
            patch("scripts.stages.voice_stage._probe_audio_duration", return_value=2.0), \
            patch("scripts.stages.voice_stage._rms_aligned_cues",
                  return_value=[{"start": 0.0, "end": 2.0, "text": "x"}]), \
            patch("scripts.stages.voice_stage._attach_aligned_word_timings", side_effect=lambda p, c, d: c):
        VoiceStage.run(ctx)
    return gen


def test_matching_record_is_reused(tmp_path):
    ctx = _ctx(tmp_path, product_id="p", angle_id="a", voice_rate="+15%", ad_tone="commercial_premium")
    gen = _run_with_record(ctx, _record(tmp_path))
    gen.assert_not_called()


@pytest.mark.parametrize("overrides", [
    {"voice_rate": "+30%"},
    {"ad_tone": "commercial_hype"},
])
def test_changed_rate_or_tone_resynthesizes(tmp_path, overrides):
    values = {"voice_rate": "+15%", "ad_tone": "commercial_premium", **overrides}
    ctx = _ctx(tmp_path, product_id="p", angle_id="a", **values)
    gen = _run_with_record(ctx, _record(tmp_path))
    gen.assert_called_once()


def test_empty_recorded_script_is_a_mismatch(tmp_path):
    ctx = _ctx(tmp_path, product_id="p", angle_id="a", voice_rate="+15%", ad_tone="commercial_premium")
    record = _record(tmp_path)
    record["custom_script"] = ""
    record["cues"] = record["beat_cues"] = [{"start": 0.0, "end": 2.0, "text": ""}]
    with patch("scripts.product_store.ProductStore.get", return_value=None):
        gen = _run_with_record(ctx, record)
    gen.assert_called_once()


# --- S2-17 -------------------------------------------------------------------

def test_failed_human_voice_conversion_raises_thai_error(tmp_path, monkeypatch):
    src = tmp_path / "human.m4a"
    src.write_bytes(b"not audio")
    ctx = _ctx(tmp_path, human_voice_audio_path=str(src))

    def fake_run(cmd, *a, **k):
        if cmd[0] == "ffmpeg":
            return SimpleNamespace(returncode=1, stdout="", stderr="Invalid data found when processing input")
        raise AssertionError(f"unexpected call after a failed conversion: {cmd}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(AppError) as excinfo:
        VoiceStage.run(ctx)
    err = excinfo.value
    assert err.category == ErrorCategory.FFMPEG
    assert err.code == "HUMAN_VOICE_CONVERT_FAILED"
    assert "แปลงไฟล์เสียง" in err.message_th
    assert "Invalid data found" in (err.details or "")
