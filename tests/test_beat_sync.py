"""Behavioral tests for scripts/beat_sync.py.

BeatSync feeds cut timing into scripts/pipeline.py, which snaps auto-generated
video cut boundaries onto detected beat/RMS-energy timestamps before they
reach scripts/video_editor.py's filter-graph construction. A bad value here
(NaN, a negative time, an unbounded list) flows straight into an ffmpeg
command with only min/max clamps as a backstop -- so these tests focus on
degenerate audio inputs and on the numeric sanity of what comes back.

No real audio assets are used: every WAV is synthesized in-memory with numpy
and written to tmp_path. The module-level BEAT_CACHE_FILE binding (read from
scripts.config at import time) is monkeypatched directly on the beat_sync
module -- patching scripts.config alone would not affect the already-bound
name.
"""
import json
import math
import warnings

import numpy as np
import pytest

soundfile = pytest.importorskip("soundfile")
pytest.importorskip("librosa")

from scripts import beat_sync as beat_sync_mod
from scripts.beat_sync import BeatSync


def _write_wav(path, samples, sr=22050):
    soundfile.write(str(path), samples, sr)
    return path


def _silence(dur_s, sr=22050):
    return np.zeros(int(sr * dur_s), dtype=np.float64)


def _tone(dur_s, freq=440.0, sr=22050, amplitude=0.3):
    t = np.linspace(0, dur_s, int(sr * dur_s), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float64)


def _click_track(dur_s, interval_s=0.5, sr=22050, seed=0):
    """Percussive bursts at a fixed interval -- gives librosa's beat
    tracker something real to lock onto, unlike a pure sine tone."""
    rng = np.random.default_rng(seed)
    n = int(sr * dur_s)
    y = np.zeros(n, dtype=np.float64)
    burst_len = int(sr * 0.02)
    t = 0.0
    while t < dur_s:
        idx = int(t * sr)
        end = min(n, idx + burst_len)
        length = end - idx
        if length > 0:
            burst = rng.standard_normal(length) * np.exp(-np.linspace(0, 10, length))
            y[idx:end] += burst
        t += interval_s
    peak = np.max(np.abs(y)) or 1.0
    return (y / peak * 0.8).astype(np.float64)


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    """Redirect the beat cache to tmp_path so tests never touch or create
    02_Assets/Music/.beat_cache.json in the real repo tree."""
    cache_file = tmp_path / ".beat_cache.json"
    monkeypatch.setattr(beat_sync_mod, "BEAT_CACHE_FILE", cache_file)
    return cache_file


def _finite_floats(values):
    return all(isinstance(v, float) and math.isfinite(v) for v in values)


# ---------------------------------------------------------------------------
# get_beat_times: missing / no-file inputs
# ---------------------------------------------------------------------------

def test_get_beat_times_returns_empty_for_none():
    assert BeatSync.get_beat_times(None) == []


def test_get_beat_times_returns_empty_for_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.wav"
    assert BeatSync.get_beat_times(missing) == []


def test_get_beat_times_never_raises_on_corrupt_bytes(tmp_path):
    """A file that merely looks like audio (has a RIFF-ish header) but has
    no decodable payload must degrade to [], not raise -- this is the same
    'RIFF fake wav' shape already produced by test_phase1_smoke.py's mixed
    audio fixture, which triggers this exact fallback path today."""
    bogus = tmp_path / "corrupt.wav"
    bogus.write_bytes(b"RIFF fake wav not real audio data at all")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = BeatSync.get_beat_times(bogus)
    assert result == []


# ---------------------------------------------------------------------------
# get_beat_times: degenerate real audio
# ---------------------------------------------------------------------------

def test_get_beat_times_on_silence_is_empty_not_crashing(tmp_path):
    """Silence has no onsets -- current behavior is an empty beat list, not
    fabricated timestamps. Documents current behavior."""
    wav = _write_wav(tmp_path / "silence.wav", _silence(3.0))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        beats = BeatSync.get_beat_times(wav)
    assert beats == []


def test_get_beat_times_on_audio_shorter_than_one_beat_interval(tmp_path):
    """A 0.1s clip is shorter than any plausible beat interval. Must not
    raise, and whatever it returns must be finite, non-negative, and inside
    the clip's own duration -- a beat time past the end of the audio would
    be a fabricated value flowing straight to a cut boundary."""
    wav = _write_wav(tmp_path / "tiny.wav", _tone(0.1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        beats = BeatSync.get_beat_times(wav)
    assert isinstance(beats, list)
    assert _finite_floats(beats)
    assert all(0.0 <= b <= 0.1 + 1e-6 for b in beats)


def test_get_beat_times_on_click_track_has_bounded_drift(tmp_path):
    """A synthetic click track at a fixed 0.5s interval gives librosa's beat
    tracker something real to lock onto. Beat estimation is not exact, but
    successive detected beats should track the true interval without runaway
    drift -- if pipeline.py trusts these for cut placement, accumulating
    drift across a long track would walk cuts progressively further from
    the music."""
    wav = _write_wav(tmp_path / "clicks.wav", _click_track(6.0, interval_s=0.5))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        beats = BeatSync.get_beat_times(wav)

    assert len(beats) >= 3, "click track should yield multiple detected beats"
    assert _finite_floats(beats)
    assert beats == sorted(beats), "beat times must be monotonically increasing"

    diffs = [b2 - b1 for b1, b2 in zip(beats, beats[1:])]
    # True spacing is 0.5s; allow generous tracking error but rule out
    # unbounded/accumulating drift (e.g. off by a growing multiple).
    for d in diffs:
        assert 0.1 <= d <= 1.5, f"inter-beat gap {d} far outside plausible range"
    # No systematic drift: the spread of gaps should stay small relative to
    # the interval itself, not grow across the file.
    assert max(diffs) - min(diffs) < 0.5


def test_get_beat_times_caches_by_name_and_size(tmp_path, monkeypatch):
    """Second call for the same file must hit the cache rather than
    re-invoking librosa -- pipeline.py relies on this to avoid re-analyzing
    the same BGM track on every reroll."""
    wav = _write_wav(tmp_path / "clicks.wav", _click_track(2.0, interval_s=0.5))

    calls = {"n": 0}

    import librosa
    orig_beat_track = librosa.beat.beat_track

    def counting_beat_track(*args, **kwargs):
        calls["n"] += 1
        return orig_beat_track(*args, **kwargs)

    monkeypatch.setattr(librosa.beat, "beat_track", counting_beat_track)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        first = BeatSync.get_beat_times(wav)
        second = BeatSync.get_beat_times(wav)

    assert calls["n"] == 1, "second call should be served from cache"
    assert first == second


def test_get_beat_times_cache_file_written_under_tmp_path(tmp_path, _isolate_cache):
    """Confirms the cache write lands in the monkeypatched location, not the
    real 02_Assets/Music tree -- guards against the earlier-round mistake of
    a test polluting a real asset folder."""
    wav = _write_wav(tmp_path / "clicks.wav", _click_track(2.0, interval_s=0.5))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        BeatSync.get_beat_times(wav)
    assert _isolate_cache.exists()
    data = json.loads(_isolate_cache.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and len(data) == 1


# ---------------------------------------------------------------------------
# get_rms_energy
# ---------------------------------------------------------------------------

def test_get_rms_energy_returns_empty_for_none_or_missing(tmp_path):
    assert BeatSync.get_rms_energy(None) == ([], [])
    assert BeatSync.get_rms_energy(tmp_path / "missing.wav") == ([], [])


def test_get_rms_energy_never_raises_on_corrupt_bytes(tmp_path):
    bogus = tmp_path / "corrupt.wav"
    bogus.write_bytes(b"RIFF fake wav not real audio data at all")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        times, rms = BeatSync.get_rms_energy(bogus)
    assert times == []
    assert rms == []


def test_get_rms_energy_on_silence_is_finite_and_flat(tmp_path):
    wav = _write_wav(tmp_path / "silence.wav", _silence(1.0))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        times, rms = BeatSync.get_rms_energy(wav)
    assert _finite_floats(times)
    assert _finite_floats(rms)
    # Silence should not produce negative or NaN energy.
    assert all(r >= 0.0 for r in rms)


def test_get_rms_energy_on_very_short_audio_has_at_least_one_sample(tmp_path):
    """0.1s of audio is shorter than most hop-length windows would suggest,
    but librosa still yields a handful of RMS frames -- confirm it degrades
    gracefully (not an empty result, not a crash) rather than assuming a
    minimum-length precondition that isn't actually enforced."""
    wav = _write_wav(tmp_path / "tiny.wav", _tone(0.1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        times, rms = BeatSync.get_rms_energy(wav)
    assert len(times) == len(rms)
    assert _finite_floats(times)
    assert _finite_floats(rms)


# ---------------------------------------------------------------------------
# segment_mean_energy
# ---------------------------------------------------------------------------

def test_segment_mean_energy_none_when_no_data():
    assert BeatSync.segment_mean_energy([], [], 0.0, 1.0) is None


def test_segment_mean_energy_averages_values_in_window():
    times = [0.0, 0.5, 1.0, 1.5, 2.0]
    rms = [1.0, 2.0, 3.0, 4.0, 5.0]
    # window [0.5, 1.5) -> indices at t=0.5 and t=1.0 -> mean(2.0, 3.0)
    result = BeatSync.segment_mean_energy(times, rms, 0.5, 1.5)
    assert result == pytest.approx(2.5)


def test_segment_mean_energy_falls_back_to_nearest_sample_when_window_too_narrow():
    """A window narrower than the sampling step (here: no timestamp lies in
    [0.24, 0.26)) must fall back to the single nearest sample rather than
    returning None -- callers rely on always getting a number back when
    there is any data at all."""
    times = [0.0, 0.5, 1.0]
    rms = [10.0, 20.0, 30.0]
    result = BeatSync.segment_mean_energy(times, rms, 0.24, 0.26)
    assert result == 10.0  # nearest to midpoint 0.25 is t=0.0


def test_segment_mean_energy_result_is_finite():
    times = [0.0, 0.25, 0.5]
    rms = [0.1, 0.2, 0.3]
    result = BeatSync.segment_mean_energy(times, rms, 0.0, 0.5)
    assert result is not None
    assert math.isfinite(result)
