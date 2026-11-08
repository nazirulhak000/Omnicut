"""Unit tests for Gemini Flash TTS tail silence & digital artifact trimming.

Tests that EOF buffer spikes, digital bursts, and dead trailing silence
are eliminated cleanly without clipping legitimate speech.
"""

import wave
import numpy as np
import pytest
from pathlib import Path

from scripts.gemini_tts_engine import (
    trim_silence_and_tail_artifacts_wav,
    trim_leading_silence_wav,
    GEMINI_TAIL_SILENCE_PAD_S,
    GEMINI_LEAD_SILENCE_MAX_S,
)

RATE = 24000


def _write_wav(path: Path, samples: np.ndarray, channels: int = 1):
    data = np.clip(samples, -1.0, 1.0)
    pcm = (data * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm.tobytes())


def _read_wav(path: Path):
    with wave.open(str(path), "rb") as wf:
        n = wf.getnframes()
        channels = wf.getnchannels()
        rate = wf.getframerate()
        frames = wf.readframes(n)
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32767.0
    return samples.reshape(-1, channels), rate


def test_tail_digital_noise_burst_is_eliminated(tmp_path):
    """An isolated EOF digital noise spike (loud clipping after silence) is cleanly stripped."""
    wav = tmp_path / "burst_take.wav"
    t = np.linspace(0, 1.0, RATE, endpoint=False)
    speech = 0.6 * np.sin(2 * np.pi * 330 * t)  # 1.0s tone
    silence_gap = np.zeros(int(0.20 * RATE))     # 200ms silence
    burst = 0.999 * np.ones(int(0.12 * RATE))    # 120ms clipping burst (Gemini EOF glitch)
    audio = np.concatenate([speech, silence_gap, burst])
    _write_wav(wav, audio)

    head_s, tail_s = trim_silence_and_tail_artifacts_wav(wav)
    out, rate = _read_wav(wav)
    dur = len(out) / rate

    # The 120ms burst and 200ms silence should be stripped; speech + 80ms pad survives
    expected_max_dur = 1.0 + GEMINI_TAIL_SILENCE_PAD_S + 0.02
    assert dur <= expected_max_dur
    assert dur >= 1.0

    # Verify tail has zero clipping samples and smoothly fades out
    tail_samples = np.abs(out[-int(0.01 * rate):, 0])
    assert np.max(tail_samples) < 0.05
    assert tail_samples[-1] == 0.0  # Faded to exact zero at the end


def test_trailing_dead_silence_is_trimmed(tmp_path):
    """Trailing dead silence (>150ms) is trimmed to a tight natural 80ms pad."""
    wav = tmp_path / "trailing_silence.wav"
    t = np.linspace(0, 1.0, RATE, endpoint=False)
    speech = 0.5 * np.sin(2 * np.pi * 440 * t)  # 1.0s speech
    trailing_silence = np.zeros(int(0.50 * RATE)) # 500ms dead silence
    _write_wav(wav, np.concatenate([speech, trailing_silence]))

    head_s, tail_s = trim_silence_and_tail_artifacts_wav(wav)
    out, rate = _read_wav(wav)
    dur = len(out) / rate

    assert tail_s > 0.35  # At least 350ms of dead silence was trimmed
    assert 1.0 <= dur <= 1.0 + GEMINI_TAIL_SILENCE_PAD_S + 0.02


def test_both_head_and_tail_trimmed_simultaneously(tmp_path):
    """Lead silence, tail silence, and burst are all trimmed in one pass."""
    wav = tmp_path / "combo.wav"
    lead = np.zeros(int(0.30 * RATE))           # 300ms lead
    t = np.linspace(0, 1.0, RATE, endpoint=False)
    speech = 0.7 * np.sin(2 * np.pi * 250 * t)  # 1.0s speech
    silence = np.zeros(int(0.18 * RATE))        # 180ms silence
    burst = 0.98 * np.ones(int(0.10 * RATE))    # 100ms burst
    _write_wav(wav, np.concatenate([lead, speech, silence, burst]))

    head_s, tail_s = trim_silence_and_tail_artifacts_wav(wav)
    out, rate = _read_wav(wav)
    dur = len(out) / rate

    assert head_s > 0.20
    assert tail_s > 0.15
    assert 1.0 <= dur <= 1.15
    assert out[-1, 0] == 0.0


def test_stereo_tail_artifact_trimmed_cleanly(tmp_path):
    """Stereo audio preserves channel alignment while stripping tail bursts."""
    wav = tmp_path / "stereo_burst.wav"
    t = np.linspace(0, 0.8, int(0.8 * RATE), endpoint=False)
    left_speech = 0.5 * np.sin(2 * np.pi * 300 * t)
    right_speech = 0.4 * np.sin(2 * np.pi * 400 * t)
    silence = np.zeros(int(0.15 * RATE))
    burst = 0.95 * np.ones(int(0.10 * RATE))

    left = np.concatenate([left_speech, silence, burst])
    right = np.concatenate([right_speech, silence, burst])
    stereo = np.stack([left, right], axis=1)

    with wave.open(str(wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
        wf.writeframes(pcm.tobytes())

    head_s, tail_s = trim_silence_and_tail_artifacts_wav(wav)
    out, rate = _read_wav(wav)

    assert out.shape[1] == 2
    assert len(out) / rate <= 0.8 + GEMINI_TAIL_SILENCE_PAD_S + 0.02
    assert out[-1, 0] == 0.0
    assert out[-1, 1] == 0.0
