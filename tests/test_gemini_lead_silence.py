"""Gemini TTS lead-silence trim (roadmap Q7): speech within <=50 ms, onset intact.

Synthetic 16-bit 24 kHz WAVs in tmp_path; no network, no ffmpeg.
"""

import wave

import numpy as np

from scripts.gemini_tts_engine import GEMINI_LEAD_SILENCE_MAX_S, trim_leading_silence_wav

RATE = 24000


def _write(path, samples, channels=1):
    data = np.clip(samples, -1.0, 1.0)
    pcm = (data * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm.tobytes())


def _read(path):
    with wave.open(str(path), "rb") as wf:
        return np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32767


def _speech(lead_s, speech_s=0.5, onset_ramp_s=0.02):
    lead = np.zeros(int(lead_s * RATE))
    t = np.arange(int(speech_s * RATE)) / RATE
    tone = 0.5 * np.sin(2 * np.pi * 220 * t)
    ramp = np.minimum(1.0, t / onset_ramp_s)  # soft onset, like a fricative
    return np.concatenate([lead, tone * ramp]), len(lead)


def _first_loud(samples, threshold_db=-42.0):
    idx = np.flatnonzero(np.abs(samples) > 10 ** (threshold_db / 20))
    return int(idx[0]) if len(idx) else None


def test_long_lead_is_trimmed_to_at_most_50ms(tmp_path):
    wav = tmp_path / "take.wav"
    samples, _ = _speech(0.35)
    _write(wav, samples)
    removed = trim_leading_silence_wav(wav)
    out = _read(wav)
    lead_after = _first_loud(out) / RATE
    assert lead_after <= GEMINI_LEAD_SILENCE_MAX_S
    assert 0.25 < removed < 0.35


def test_speech_onset_is_not_clipped(tmp_path):
    wav = tmp_path / "take.wav"
    samples, lead_n = _speech(0.3)
    _write(wav, samples)
    removed = trim_leading_silence_wav(wav)
    out = _read(wav)
    # Everything from the true onset (including the quiet ramp start) survives.
    cut_n = int(round(removed * RATE))
    assert cut_n <= lead_n
    original = (np.clip(samples, -1, 1) * 32767).astype("<i2").astype(np.float32) / 32767
    np.testing.assert_array_equal(out, original[cut_n:])
    assert len(out) == len(original) - cut_n


def test_tight_take_and_silent_take_are_untouched(tmp_path):
    tight = tmp_path / "tight.wav"
    samples, _ = _speech(0.01)
    _write(tight, samples)
    before = tight.read_bytes()
    assert trim_leading_silence_wav(tight) == 0.0
    assert tight.read_bytes() == before

    silent = tmp_path / "silent.wav"
    _write(silent, np.zeros(RATE))
    before = silent.read_bytes()
    assert trim_leading_silence_wav(silent) == 0.0
    assert silent.read_bytes() == before


def test_stereo_take_keeps_channels_aligned(tmp_path):
    wav = tmp_path / "stereo.wav"
    mono, _ = _speech(0.2)
    stereo = np.stack([mono, mono * 0.5], axis=1).reshape(-1)
    _write(wav, stereo, channels=2)
    trim_leading_silence_wav(wav)
    with wave.open(str(wav), "rb") as wf:
        assert wf.getnchannels() == 2
        frames = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").reshape(-1, 2)
    first = _first_loud(frames[:, 0].astype(np.float32) / 32767)
    assert first / RATE <= GEMINI_LEAD_SILENCE_MAX_S
