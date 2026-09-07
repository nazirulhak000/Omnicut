"""
Regression test for SAAS_READINESS_PLAN.md 11a:

When one script line fails to synthesize (all TTS paths -- edge-tts streaming
API, edge-tts CLI, gTTS -- fail, or the line sanitizes to empty text), the
line must NOT simply vanish. It must get a timed silence stand-in so every
SUBSEQUENT line's cue keeps pointing at its true audio position instead of
drifting permanently earlier by the missing line's duration.

Everything here is mocked: no real network call, no real edge-tts/gTTS/ffmpeg
invocation, no real _Docs/ or asset directory touched. All I/O happens under
tmp_path.
"""

import types
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from scripts.voice_engine import VoiceEngine


def _fake_wav_bytes_for(seconds: float, sample_rate: int = 44100) -> np.ndarray:
    """A loud-enough (above the -42dB trim threshold) sine-ish buffer so
    `_trim_silence` doesn't eat it away to nothing."""
    n = int(seconds * sample_rate)
    t = np.linspace(0, seconds, n, endpoint=False, dtype=np.float32)
    return (0.5 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)


def test_line_failure_inserts_silence_and_keeps_later_cues_aligned(monkeypatch, tmp_path):
    """
    Two lines. Line 0 (idx 0) fails every TTS engine. Line 1 (idx 1) succeeds
    with a known, fixed duration. Line 1's cue "start" must equal the actual
    sample position where its audio begins in the concatenated track --
    i.e. current_time must have advanced by *something* for the failed line,
    not stayed frozen at 0.0.
    """
    import scripts.voice_engine as ve_mod

    sample_rate = 44100
    line1_real_audio = _fake_wav_bytes_for(1.2, sample_rate)

    # Never produce word-level timing via the streaming API -- forces the
    # CLI fallback path for every line (simpler to control deterministically).
    monkeypatch.setattr(VoiceEngine, "_synthesize_line_with_word_timing", classmethod(
        lambda cls, text, voice_name, rate_str, pitch_str, out_mp3: None
    ))

    call_state = {"edge_calls": 0}

    def fake_subprocess_run(cmd, **kwargs):
        call_state["edge_calls"] += 1
        if cmd[0] == "edge-tts":
            # "--text" is followed by the line text; recover which line this is
            # from the temp filename via --write-media so behavior is
            # deterministic instead of relying on call order.
            write_media = cmd[cmd.index("--write-media") + 1]
            if "raw_0" in write_media:
                # Line 0 (idx 0): edge-tts CLI fails outright -- no file, bad returncode.
                return MagicMock(returncode=1, stderr=b"network error: getaddrinfo failed")
            else:
                # Any other line: edge-tts CLI "succeeds" -- write a real mp3-ish
                # placeholder (content doesn't matter; ffmpeg step is also mocked).
                Path(write_media).write_bytes(b"FAKE_MP3_BYTES_NOT_EMPTY")
                return MagicMock(returncode=0, stderr=b"")
        elif cmd[0] == "ffmpeg":
            # Locate the -i (input) and trailing output path.
            in_path = Path(cmd[cmd.index("-i") + 1])
            out_path = Path(cmd[-1])
            if in_path.exists() and in_path.stat().st_size > 0:
                import soundfile as sf
                sf.write(str(out_path), line1_real_audio, sample_rate)
                return MagicMock(returncode=0, stderr=b"")
            return MagicMock(returncode=1, stderr=b"ffmpeg: no input")
        raise AssertionError(f"unexpected subprocess command: {cmd}")

    monkeypatch.setattr(ve_mod.subprocess, "run", fake_subprocess_run)

    # gTTS fallback also fails for every line, so line 0 has truly no audio path left.
    import gtts
    def fake_gtts_init(self, text, lang="th"):
        raise RuntimeError("gTTS: simulated network failure")
    monkeypatch.setattr(gtts.gTTS, "__init__", fake_gtts_init)

    out_wav = tmp_path / "voice_out.wav"
    result = VoiceEngine.generate_crystal_voice(
        text_or_lines=["สวัสดีครับ ทดสอบบรรทัดแรก", "บรรทัดสองพากย์ได้จริง"],
        output_audio_path=str(out_wav),
        speed=1.0,
        voice_gender="male",
    )

    cues = result["cues"]
    assert len(cues) == 2, "both lines must still produce a cue -- the failed line must not vanish"

    cue0, cue1 = cues[0], cues[1]

    # Line 0 failed -> substituted with silence, not simply dropped.
    assert cue0.get("substituted") is True
    assert cue0["start"] == 0.0
    assert cue0["end"] > 0.0, "failed line must still occupy nonzero time on the timeline"

    # Line 1 succeeded -> its cue must start where line 0's silence (+ breathing
    # gap) actually ends, NOT at 0.0 (which is what the old bug produced,
    # since current_time never advanced past the skipped line).
    assert cue1.get("substituted") is False
    assert cue1["start"] == pytest.approx(cue0["end"], abs=0.005) or cue1["start"] > cue0["end"] - 0.01, \
        "line 1's cue must start after line 0's (silence) duration, proving current_time advanced"
    assert cue1["start"] > 0.05, "line 1 must not start at ~0.0 -- that would mean line 0 vanished silently"

    # The audio actually written to disk must be at least as long as line 1's
    # own real duration plus the lead-in silence for line 0 -- i.e. the
    # concatenated audio's length matches the claimed cue timing, not shorter
    # (which would reproduce the desync where captions outrun the real audio).
    import soundfile as sf
    written, sr = sf.read(str(out_wav))
    written_duration = len(written) / sr
    assert written_duration >= cue1["end"] - 0.05

    # Caller-visible signal that a substitution happened (additive field;
    # existing callers reading only audio_path/duration/cues are unaffected).
    assert result["substituted_line_count"] == 1
    assert result["substituted_line_indices"] == [0]


def test_all_lines_succeed_reports_no_substitutions(monkeypatch, tmp_path):
    """Sanity check: the happy path is unaffected by the new bookkeeping --
    no substitutions reported when every line synthesizes fine."""
    import scripts.voice_engine as ve_mod

    sample_rate = 44100
    audio = _fake_wav_bytes_for(0.8, sample_rate)

    monkeypatch.setattr(VoiceEngine, "_synthesize_line_with_word_timing", classmethod(
        lambda cls, text, voice_name, rate_str, pitch_str, out_mp3: None
    ))

    def fake_subprocess_run(cmd, **kwargs):
        if cmd[0] == "edge-tts":
            write_media = cmd[cmd.index("--write-media") + 1]
            Path(write_media).write_bytes(b"FAKE_MP3_BYTES_NOT_EMPTY")
            return MagicMock(returncode=0, stderr=b"")
        elif cmd[0] == "ffmpeg":
            in_path = Path(cmd[cmd.index("-i") + 1])
            out_path = Path(cmd[-1])
            import soundfile as sf
            sf.write(str(out_path), audio, sample_rate)
            return MagicMock(returncode=0, stderr=b"")
        raise AssertionError(f"unexpected subprocess command: {cmd}")

    monkeypatch.setattr(ve_mod.subprocess, "run", fake_subprocess_run)

    out_wav = tmp_path / "voice_out.wav"
    result = VoiceEngine.generate_crystal_voice(
        text_or_lines=["บรรทัดหนึ่งพากย์ได้ปกติ", "บรรทัดสองก็พากย์ได้ปกติเช่นกัน"],
        output_audio_path=str(out_wav),
        speed=1.0,
        voice_gender="male",
    )

    assert result["substituted_line_count"] == 0
    assert result["substituted_line_indices"] == []
    for cue in result["cues"]:
        assert cue.get("substituted") is False
