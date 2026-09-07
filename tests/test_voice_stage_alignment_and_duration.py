"""
Tests for scripts/stages/voice_stage.py (SAAS_READINESS_PLAN.md sections 11e, 11f).

11f: ffprobe failure/empty/unparseable/non-positive output must raise a hard
error (AppError, category=FFMPEG) instead of silently defaulting to 15.0.

11e: the human-voice path must reuse the same RMS/energy-based acoustic
alignment as the Gemini TTS path instead of an even `total_duration /
num_lines` split, with a proportional fallback (logged) when alignment fails
or looks implausible (fewer detected speech blocks than script lines).

All tests are offline/deterministic: subprocess.run is monkeypatched (no real
ffprobe binary invoked) and audio is synthesized in-memory / written via
soundfile to tmp_path (no real recordings, no network).
"""

import subprocess
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from scripts.error_handler import AppError, ErrorCategory
from scripts.pipeline_context import PipelineContext
from scripts.stages.voice_stage import (
    VoiceStage,
    _probe_audio_duration,
    _rms_speech_blocks,
    _rms_aligned_cues,
    _proportional_fallback_cues,
)


def _fake_completed(stdout="", stderr="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


# ---------------------------------------------------------------------------
# 11f: ffprobe duration must raise, never silently become 15.0
# ---------------------------------------------------------------------------

def test_probe_duration_raises_on_empty_stdout(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _fake_completed(stdout="", stderr="", returncode=0)
    )
    fake_audio = tmp_path / "voice.wav"
    fake_audio.write_bytes(b"not-really-audio")

    with pytest.raises(AppError) as excinfo:
        _probe_audio_duration(fake_audio)
    assert excinfo.value.category == ErrorCategory.FFMPEG
    assert "FFPROBE" in excinfo.value.code


def test_probe_duration_raises_on_nonzero_returncode(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: _fake_completed(stdout="", stderr="Invalid data found", returncode=1),
    )
    fake_audio = tmp_path / "voice.wav"
    fake_audio.write_bytes(b"corrupt")

    with pytest.raises(AppError) as excinfo:
        _probe_audio_duration(fake_audio)
    assert excinfo.value.category == ErrorCategory.FFMPEG
    # stderr should be captured into the error details for diagnosability
    assert "Invalid data found" in (excinfo.value.details or "")


def test_probe_duration_raises_on_unparseable_stdout(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _fake_completed(stdout="N/A", stderr="", returncode=0)
    )
    fake_audio = tmp_path / "voice.wav"
    fake_audio.write_bytes(b"x")

    with pytest.raises(AppError):
        _probe_audio_duration(fake_audio)


def test_probe_duration_raises_on_zero_duration(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _fake_completed(stdout="0.0", stderr="", returncode=0)
    )
    fake_audio = tmp_path / "voice.wav"
    fake_audio.write_bytes(b"x")

    with pytest.raises(AppError):
        _probe_audio_duration(fake_audio)


def test_probe_duration_raises_when_launch_fails(monkeypatch, tmp_path):
    def raise_oserror(*a, **k):
        raise OSError("ffprobe binary not found")

    monkeypatch.setattr(subprocess, "run", raise_oserror)
    fake_audio = tmp_path / "voice.wav"
    fake_audio.write_bytes(b"x")

    with pytest.raises(AppError) as excinfo:
        _probe_audio_duration(fake_audio)
    assert excinfo.value.category == ErrorCategory.FFMPEG


def test_probe_duration_succeeds_on_valid_output(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _fake_completed(stdout="12.345\n", stderr="", returncode=0)
    )
    fake_audio = tmp_path / "voice.wav"
    fake_audio.write_bytes(b"x")

    duration = _probe_audio_duration(fake_audio)
    assert duration == pytest.approx(12.345)


# ---------------------------------------------------------------------------
# 11e: shared RMS alignment must be used for both Gemini TTS and human voice
# ---------------------------------------------------------------------------

def _write_synthetic_speech_wav(path, sr=44100, speech_specs=None, total_dur=6.0):
    """
    Builds a synthetic mono WAV with loud "speech" bursts (sine tone) separated
    by silence gaps long enough (>140ms) to be detected as pauses by
    _rms_speech_blocks, matching real speech/silence energy patterns without
    needing a real recording.
    """
    if speech_specs is None:
        speech_specs = [(0.3, 1.5), (2.0, 3.2), (3.7, 5.5)]  # (start, end) seconds
    n_samples = int(total_dur * sr)
    audio = np.zeros(n_samples, dtype=np.float32)
    t = np.arange(n_samples) / sr
    tone = 0.8 * np.sin(2 * np.pi * 220.0 * t)
    for start, end in speech_specs:
        s_idx = int(start * sr)
        e_idx = int(end * sr)
        audio[s_idx:e_idx] = tone[s_idx:e_idx]
    sf.write(str(path), audio, sr)
    return speech_specs


def test_rms_speech_blocks_detects_bursts_and_gaps():
    sr = 44100
    specs = [(0.3, 1.5), (2.0, 3.2), (3.7, 5.5)]
    total_dur = 6.0
    n_samples = int(total_dur * sr)
    t = np.arange(n_samples) / sr
    audio = np.zeros(n_samples, dtype=np.float32)
    tone = 0.8 * np.sin(2 * np.pi * 220.0 * t)
    for start, end in specs:
        s_idx = int(start * sr)
        e_idx = int(end * sr)
        audio[s_idx:e_idx] = tone[s_idx:e_idx]

    blocks, total = _rms_speech_blocks(audio, sr)
    assert total == pytest.approx(total_dur, abs=0.01)
    assert len(blocks) == len(specs)
    for (b_start, b_end), (s, e) in zip(blocks, specs):
        assert b_start == pytest.approx(s, abs=0.1)
        assert b_end == pytest.approx(e, abs=0.1)


def test_rms_aligned_cues_matches_speech_blocks_for_human_voice(tmp_path):
    """The human-voice path (and Gemini path) both call this helper -- verify
    cues land close to the actual detected speech blocks rather than an even
    split across total_duration."""
    wav_path = tmp_path / "human_voice.wav"
    specs = _write_synthetic_speech_wav(wav_path, speech_specs=[(0.3, 1.5), (2.0, 3.2), (3.7, 5.5)], total_dur=6.0)

    split_items = [
        {"text": "อย่าเพิ่งซื้อสายชาร์จ", "sfx": "boom", "on_screen": ""},
        {"text": "ดูดแน่นชาร์จเร็ว", "sfx": None, "on_screen": ""},
        {"text": "ราคาพิเศษวันนี้", "sfx": "cash", "on_screen": ""},
    ]
    cues = _rms_aligned_cues(wav_path, split_items, total_duration=6.0, log_prefix="[Test]")

    assert len(cues) == 3
    # First cue must start at (near) the first detected speech block, not at 0
    # the way an even total_duration/3 split would misleadingly suggest here
    # (an even split would start all cues at multiples of 2.0s).
    assert cues[0]["start"] == pytest.approx(specs[0][0], abs=0.2)
    # Last cue must end at total_duration exactly (contract preserved from
    # the original inline implementation).
    assert cues[-1]["end"] == pytest.approx(6.0, abs=1e-6)
    # Cues must be monotonically ordered and non-overlapping-ish.
    for i in range(len(cues) - 1):
        assert cues[i]["end"] <= cues[i + 1]["start"] + 0.2


def test_rms_aligned_cues_falls_back_when_fewer_blocks_than_lines(tmp_path, capsys):
    """3 script lines but only 1 continuous speech block (no silence gaps
    long enough to separate them) -- alignment must not fabricate 3 blocks
    out of 1; it must fall back to proportional split and log the fallback."""
    wav_path = tmp_path / "one_block.wav"
    sr = 44100
    total_dur = 4.0
    n_samples = int(total_dur * sr)
    t = np.arange(n_samples) / sr
    audio = (0.8 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)  # continuous speech, no gaps
    sf.write(str(wav_path), audio, sr)

    split_items = [
        {"text": "บรรทัดหนึ่ง", "sfx": None, "on_screen": ""},
        {"text": "บรรทัดสอง", "sfx": None, "on_screen": ""},
        {"text": "บรรทัดสาม", "sfx": None, "on_screen": ""},
    ]
    cues = _rms_aligned_cues(wav_path, split_items, total_duration=total_dur, log_prefix="[Test]")

    assert len(cues) == 3
    expected = _proportional_fallback_cues(split_items, total_dur)
    assert cues == expected

    captured = capsys.readouterr()
    assert "falling back to proportional split" in captured.out


def test_rms_aligned_cues_falls_back_on_unreadable_audio(tmp_path, capsys):
    """A file that isn't valid audio must not raise out of the helper --
    it should log and fall back to the proportional split, same contract as
    the original inline `except Exception as align_err` in the Gemini path."""
    bad_path = tmp_path / "not_audio.wav"
    bad_path.write_bytes(b"this is not a wav file")

    split_items = [
        {"text": "หนึ่ง", "sfx": None, "on_screen": ""},
        {"text": "สอง", "sfx": None, "on_screen": ""},
    ]
    cues = _rms_aligned_cues(bad_path, split_items, total_duration=5.0, log_prefix="[Test]")

    assert len(cues) == 2
    expected = _proportional_fallback_cues(split_items, 5.0)
    assert cues == expected
    captured = capsys.readouterr()
    assert "Acoustic alignment fallback" in captured.out


# ---------------------------------------------------------------------------
# Integration: VoiceStage.run end-to-end for the human-voice path
# ---------------------------------------------------------------------------

def test_voice_stage_human_voice_path_uses_rms_alignment(monkeypatch, tmp_path):
    """End-to-end: VoiceStage.run for a real human-voice file must produce
    cues aligned to detected speech blocks, not an even total_duration/num_lines
    split. We monkeypatch the ffmpeg conversion subprocess call to a no-op
    (it normally re-encodes the source into `voice_audio_path`) and instead
    write our own synthetic speech WAV directly to that path, then let the
    real ffprobe-duration + RMS-alignment code run against it."""
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    human_src = tmp_path / "human_input.wav"
    human_src.write_bytes(b"placeholder-not-real-audio")  # never actually read; ffmpeg call is mocked

    ctx = PipelineContext(
        product_name="Gadget",
        raw_video_path="dummy.mp4",
        project_name="proj",
        human_voice_audio_path=str(human_src),
    )
    ctx.project_dir = project_dir
    ctx.script_data = {
        "lines": [
            {"text": "อย่าเพิ่งซื้อสายชาร์จ", "sfx": "boom", "on_screen": ""},
            {"text": "ดูดแน่นชาร์จเร็ว", "sfx": None, "on_screen": ""},
            {"text": "ราคาพิเศษวันนี้", "sfx": "cash", "on_screen": ""},
        ]
    }

    voice_audio_path = ctx.out_path("voiceover", ".wav")
    specs = [(0.3, 1.5), (2.0, 3.2), (3.7, 5.5)]

    def fake_run(cmd, *args, **kwargs):
        if cmd[0] == "ffmpeg":
            # Stand-in for the real conversion: write synthetic speech audio
            # directly to the destination the real command would have produced.
            _write_synthetic_speech_wav(voice_audio_path, speech_specs=specs, total_dur=6.0)
            return _fake_completed(stdout="", stderr="", returncode=0)
        if cmd[0] == "ffprobe":
            return _fake_completed(stdout="6.0", stderr="", returncode=0)
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    monkeypatch.setattr(subprocess, "run", fake_run)

    VoiceStage.run(ctx)

    assert ctx.total_duration == pytest.approx(6.0)
    assert len(ctx.cues) == 3
    # Aligned to the real (synthetic) speech block, not an even 2.0s/line split.
    assert ctx.cues[0]["start"] == pytest.approx(specs[0][0], abs=0.2)
    assert ctx.cues[0]["start"] != pytest.approx(0.0, abs=0.05)
    assert ctx.cues[-1]["end"] == pytest.approx(6.0, abs=1e-6)


def test_voice_stage_human_voice_path_raises_on_ffprobe_failure(monkeypatch, tmp_path):
    """End-to-end: if ffprobe fails for a human-voice file, VoiceStage.run
    must raise instead of silently defaulting total_duration to 15.0."""
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    human_src = tmp_path / "human_input.wav"
    human_src.write_bytes(b"placeholder-not-real-audio")

    ctx = PipelineContext(
        product_name="Gadget",
        raw_video_path="dummy.mp4",
        project_name="proj",
        human_voice_audio_path=str(human_src),
    )
    ctx.project_dir = project_dir
    ctx.script_data = {"lines": [{"text": "หนึ่ง", "sfx": None, "on_screen": ""}]}

    def fake_run(cmd, *args, **kwargs):
        # ffmpeg "succeeds" (writes nothing useful); ffprobe returns empty stdout.
        return _fake_completed(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(AppError) as excinfo:
        VoiceStage.run(ctx)
    assert excinfo.value.category == ErrorCategory.FFMPEG
    # Must never have silently produced the old 15.0s stand-in duration.
    assert ctx.total_duration != 15.0


def test_proportional_fallback_cues_covers_full_duration_and_preserves_text():
    split_items = [
        {"text": "aa", "sfx": "boom", "on_screen": "x"},
        {"text": "aaaa", "sfx": None, "on_screen": ""},
        {"text": "a", "sfx": None, "on_screen": ""},
    ]
    cues = _proportional_fallback_cues(split_items, total_duration=7.0)
    assert len(cues) == 3
    assert cues[0]["start"] == 0.0
    assert cues[-1]["end"] == 7.0
    for cue, item in zip(cues, split_items):
        assert cue["text"] == item["text"]
        assert cue["sfx"] == item["sfx"]
    # Monotonic non-decreasing timeline
    for i in range(len(cues) - 1):
        assert cues[i]["end"] <= cues[i + 1]["start"] + 1e-9
