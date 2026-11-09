"""Edge-TTS engine: exact rate, no truncated takes, flagged gTTS fallback
(audit S2-09, S2-10, S2-11). Everything mocked -- no network, no real ffmpeg.
"""

import asyncio
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

import scripts.voice_engine as ve_mod
from scripts.voice_engine import VoiceEngine

SR = 44100


def _tone(seconds):
    t = np.linspace(0, seconds, int(seconds * SR), endpoint=False, dtype=np.float32)
    return (0.5 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)


def _fake_ffmpeg_and_cli(edge_cli_ok: bool, seen_rates: list):
    def run(cmd, **kwargs):
        if cmd[0] == "edge-tts":
            seen_rates.append(cmd[cmd.index("--rate") + 1])
            if edge_cli_ok:
                Path(cmd[cmd.index("--write-media") + 1]).write_bytes(b"FAKE_MP3")
                return MagicMock(returncode=0, stderr=b"")
            return MagicMock(returncode=1, stderr=b"network down")
        if cmd[0] == "ffmpeg":
            import soundfile as sf
            in_path = Path(cmd[cmd.index("-i") + 1])
            if in_path.exists() and in_path.stat().st_size > 0:
                sf.write(str(cmd[-1]), _tone(1.0), SR)
                return MagicMock(returncode=0, stderr=b"")
            return MagicMock(returncode=1, stderr=b"no input")
        raise AssertionError(f"unexpected command {cmd}")
    return run


# --- S2-09 -------------------------------------------------------------------

@pytest.mark.parametrize("speed, expected", [(1.15, "+15%"), (1.20, "+20%"), (1.10, "+10%")])
def test_requested_rate_is_sent_exactly(monkeypatch, tmp_path, speed, expected):
    rates = []
    monkeypatch.setattr(VoiceEngine, "_synthesize_line_with_word_timing",
                        classmethod(lambda cls, *a: None))
    monkeypatch.setattr(ve_mod.subprocess, "run", _fake_ffmpeg_and_cli(True, rates))
    # Neutral beat profile so the line's rate equals the base rate.
    monkeypatch.setattr(VoiceEngine, "detect_beat_type", classmethod(lambda cls, *a: "flat"))
    monkeypatch.setattr(VoiceEngine, "BEAT_PROFILES", {
        "flat": {"rate_offset": 0, "pitch": "+0Hz", "pause_after_s": 0.1, "sfx": None},
        "benefit": {"rate_offset": 0, "pitch": "+0Hz", "pause_after_s": 0.1, "sfx": None},
    })

    VoiceEngine.generate_crystal_voice(["ทดสอบเสียง"], str(tmp_path / "v.wav"), speed=speed)
    assert rates == [expected]


# --- S2-10 -------------------------------------------------------------------

def test_stream_that_dies_mid_line_leaves_no_partial_file(monkeypatch, tmp_path):
    class FakeCommunicate:
        def __init__(self, *a, **k):
            pass

        async def stream(self):
            yield {"type": "audio", "data": b"x" * 1500}
            raise ConnectionError("stream dropped")

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=FakeCommunicate))
    out_mp3 = tmp_path / "raw_0.mp3"

    words = VoiceEngine._synthesize_line_with_word_timing("ทดสอบ", "th-TH-NiwatNeural", "+15%", "+0Hz", out_mp3)

    assert words is None
    # The caller falls back to the CLI only when the file is missing/empty.
    assert not out_mp3.exists()


# --- S2-11 -------------------------------------------------------------------

def test_gtts_fallback_is_flagged_not_silent(monkeypatch, tmp_path):
    rates = []
    monkeypatch.setattr(VoiceEngine, "_synthesize_line_with_word_timing",
                        classmethod(lambda cls, *a: None))
    monkeypatch.setattr(ve_mod.subprocess, "run", _fake_ffmpeg_and_cli(False, rates))

    import gtts

    def fake_init(self, text, lang="th"):
        self.text = text

    def fake_save(self, path):
        Path(path).write_bytes(b"GTTS_MP3")

    monkeypatch.setattr(gtts.gTTS, "__init__", fake_init)
    monkeypatch.setattr(gtts.gTTS, "save", fake_save)

    res = VoiceEngine.generate_crystal_voice(["บรรทัดหนึ่ง"], str(tmp_path / "v.wav"), speed=1.15)

    assert res["gtts_line_count"] == 1
    assert res["gtts_line_indices"] == [0]
    assert res["cues"][0]["fallback_engine"] == "gtts"
    assert "gTTS" in res["gtts_warning_th"]


def test_no_fallback_means_no_flag(monkeypatch, tmp_path):
    monkeypatch.setattr(VoiceEngine, "_synthesize_line_with_word_timing",
                        classmethod(lambda cls, *a: None))
    monkeypatch.setattr(ve_mod.subprocess, "run", _fake_ffmpeg_and_cli(True, []))

    res = VoiceEngine.generate_crystal_voice(["บรรทัดหนึ่ง"], str(tmp_path / "v.wav"), speed=1.15)

    assert res["gtts_line_count"] == 0 and res["gtts_warning_th"] == ""
    assert "fallback_engine" not in res["cues"][0]
