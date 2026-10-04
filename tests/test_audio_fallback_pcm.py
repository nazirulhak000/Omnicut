"""A degraded render still respects the saved voice mute/gain and timeline length."""

import array
import math
import shutil
import wave
from types import SimpleNamespace

import pytest

from scripts import sfx_manager


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg required for PCM verification")
@pytest.mark.parametrize("voice_gain", [0.0, 0.25])
def test_voice_only_fallback_preserves_gain_and_duration(tmp_path, monkeypatch, voice_gain):
    source = tmp_path / "voice.wav"
    sample_rate = 22050
    samples = array.array("h", [round(6000 * math.sin(2 * math.pi * 440 * i / sample_rate))
                               for i in range(sample_rate * 3)])
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(samples.tobytes())
    monkeypatch.setattr(sfx_manager.SFXManager, "resolve_bgm_path", classmethod(lambda cls, name=None: None))
    original_run = sfx_manager.subprocess.run
    previous_status = sfx_manager.SFXManager.last_mix_status
    calls = []

    def fail_advanced_mix(command, **kwargs):
        calls.append(command)
        if "-filter_complex" in command:
            return SimpleNamespace(returncode=1, stderr="Simulated advanced filter failure")
        return original_run(command, **kwargs)

    monkeypatch.setattr(sfx_manager.subprocess, "run", fail_advanced_mix)
    output = tmp_path / "fallback.wav"
    try:
        sfx_manager.SFXManager.mix_audio_track(
            voice_audio_path=str(source), cues=[], total_duration=1.0,
            output_audio_path=str(output), voice_vol=voice_gain,
        )
        status = sfx_manager.SFXManager.last_mix_status
        assert status["fallback"] is True
        assert "fallback_error" not in status
        assert len(calls) == 2
        with wave.open(str(output), "rb") as audio:
            assert audio.getnchannels() == 2
            assert audio.getframerate() == 44100
            assert audio.getnframes() / audio.getframerate() == pytest.approx(1.2, abs=0.001)
            pcm = array.array("h", audio.readframes(audio.getnframes()))
        if voice_gain == 0.0:
            assert max(abs(sample) for sample in pcm) == 0
        else:
            rms = math.sqrt(sum(sample * sample for sample in pcm) / len(pcm))
            # Mono -> stereo conversion distributes amplitude by sqrt(2).
            expected_rms = 6000 / 2 * voice_gain
            assert rms == pytest.approx(expected_rms, rel=0.03)
    finally:
        sfx_manager.SFXManager.last_mix_status = previous_status
