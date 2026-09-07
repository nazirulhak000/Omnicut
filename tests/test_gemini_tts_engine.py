"""
Behavioral coverage for scripts/gemini_tts_engine.py beyond the retry/backoff
paths already covered in tests/test_gemini_tts_retry.py: voice resolution,
API-key discovery from environment and .env, malformed/truncated response
handling, and the generate_speech() success path's real side effects (a WAV
file actually written, non-silent PCM makes it to disk, speed adjustment
invoked, token analytics recorded).

All network calls and ffmpeg subprocess calls are mocked -- no real Gemini
traffic, offline, no real ffmpeg binary required -- per
.agents/rules/testing_standard.md. GEMINI_API_KEY and .env parsing are
isolated with monkeypatch/tmp_path; PROJECT_ROOT itself is not touched since
get_api_keys() only reads it, never writes.
"""
import base64
import json
import sys
import time
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gemini_tts_engine import GeminiFlashTTSEngine, GEMINI_VOICE_PRESETS


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)


@pytest.fixture(autouse=True)
def _isolate_quota_and_tracker(monkeypatch):
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")


def _out_path(tmp_path) -> str:
    return str(tmp_path / "out.wav")


def _ok_payload_bytes(pcm: bytes = None) -> bytes:
    pcm = pcm if pcm is not None else (b"\x10\x02" * 500)
    payload = {
        "candidates": [{
            "content": {"parts": [{"inlineData": {"data": base64.b64encode(pcm).decode("ascii")}}]}
        }]
    }
    return json.dumps(payload).encode("utf-8")


def _fake_urlopen(behavior_bytes: bytes):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = behavior_bytes
    cm.__exit__.return_value = False
    return cm


# ------------------------------------------------------------- resolve_voice

def test_resolve_voice_known_preset_returns_its_gemini_voice_name():
    for preset, cfg in GEMINI_VOICE_PRESETS.items():
        assert GeminiFlashTTSEngine.resolve_voice(preset=preset) == cfg["voice"]


def test_resolve_voice_raw_voice_name_passes_through():
    assert GeminiFlashTTSEngine.resolve_voice(preset="Charon") == "Charon"


def test_resolve_voice_tolerates_case_insensitive_raw_voice_name():
    assert GeminiFlashTTSEngine.resolve_voice(preset="puck") == "Puck"
    assert GeminiFlashTTSEngine.resolve_voice(preset="  FENRIR  ") == "Fenrir"


def test_resolve_voice_unknown_preset_falls_back_to_gender():
    assert GeminiFlashTTSEngine.resolve_voice(preset="not_a_real_preset", gender="female") == "Kore"
    assert GeminiFlashTTSEngine.resolve_voice(preset="not_a_real_preset", gender="male") == "Puck"


def test_resolve_voice_no_preset_uses_gender_only():
    assert GeminiFlashTTSEngine.resolve_voice(gender="female") == "Kore"
    assert GeminiFlashTTSEngine.resolve_voice(gender="male") == "Puck"


def test_resolve_voice_nothing_given_defaults_to_kore():
    assert GeminiFlashTTSEngine.resolve_voice() == "Kore"
    assert GeminiFlashTTSEngine.resolve_voice(preset=None, gender=None) == "Kore"


# ------------------------------------------------------------- get_api_keys

def test_get_api_keys_reads_from_process_environment(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda self: False)  # no .env file
    monkeypatch.setenv("GEMINI_API_KEY", "env-key-1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "env-key-2")
    monkeypatch.delenv("GEMINI_API_KEY_OLD", raising=False)
    keys = GeminiFlashTTSEngine.get_api_keys()
    assert keys == ["env-key-1", "env-key-2"]


def test_get_api_keys_reads_dotenv_file_before_process_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=dotenv-key\n# comment line\nOTHER=ignored\n", encoding="utf-8")

    import scripts.gemini_tts_engine as tts_mod
    monkeypatch.setattr(tts_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_OLD", raising=False)

    keys = GeminiFlashTTSEngine.get_api_keys()
    assert keys == ["dotenv-key"]


def test_get_api_keys_deduplicates_across_dotenv_and_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=shared-key\n", encoding="utf-8")

    import scripts.gemini_tts_engine as tts_mod
    monkeypatch.setattr(tts_mod, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "shared-key")
    monkeypatch.delenv("GEMINI_API_KEY_2", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_OLD", raising=False)

    keys = GeminiFlashTTSEngine.get_api_keys()
    assert keys.count("shared-key") == 1


def test_is_available_true_only_when_a_key_exists(monkeypatch):
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: []))
    assert GeminiFlashTTSEngine.is_available() is False
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["k"]))
    assert GeminiFlashTTSEngine.is_available() is True


# --------------------------------------------------------- malformed response

def test_missing_parts_in_response_raises_runtime_error(monkeypatch, tmp_path):
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))
    empty_payload = json.dumps({"candidates": [{"content": {"parts": []}}]}).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=_fake_urlopen(empty_payload)):
        with pytest.raises(RuntimeError, match="no audio inline data"):
            GeminiFlashTTSEngine.generate_speech(
                text="test", output_path=_out_path(tmp_path), speed=1.0
            )


def test_missing_inline_data_key_raises_runtime_error(monkeypatch, tmp_path):
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))
    payload = json.dumps({"candidates": [{"content": {"parts": [{"text": "not audio"}]}}]}).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=_fake_urlopen(payload)):
        with pytest.raises(RuntimeError, match="no audio inline data"):
            GeminiFlashTTSEngine.generate_speech(
                text="test", output_path=_out_path(tmp_path), speed=1.0
            )


def test_truncated_json_response_raises_and_does_not_write_output(monkeypatch, tmp_path):
    """A truncated/corrupt HTTP body must fail loudly (json.JSONDecodeError
    propagating out, since there's no candidate JSON to parse), not silently
    produce an empty or partial audio file."""
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))
    truncated = b'{"candidates": [{"content": {"pa'

    out_path = _out_path(tmp_path)
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(truncated)):
        with pytest.raises(RuntimeError, match="All Gemini Flash TTS keys and models failed"):
            GeminiFlashTTSEngine.generate_speech(text="test", output_path=out_path, speed=1.0)

    assert not Path(out_path).exists()


def test_missing_api_key_raises_value_error_before_any_network_call(monkeypatch, tmp_path):
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: []))
    with patch("urllib.request.urlopen") as mock_urlopen:
        with pytest.raises(ValueError, match="GEMINI_API_KEY is missing"):
            GeminiFlashTTSEngine.generate_speech(
                text="test", output_path=_out_path(tmp_path), speed=1.0
            )
    mock_urlopen.assert_not_called()


# --------------------------------------------------- success path side effects

def test_successful_generation_writes_a_real_playable_wav_file(monkeypatch, tmp_path):
    """The class bug this whole audit is watching for: a NameError or silent
    swallow after a successful API call means the cache/output is never
    written even though the caller thinks it succeeded. Assert the actual
    file lands on disk with real 16-bit mono 24kHz PCM audio in it."""
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))
    from scripts import token_tracker
    recorded = {}
    monkeypatch.setattr(
        token_tracker.TokenTracker, "record_event",
        lambda **kw: recorded.update(kw),
    )

    pcm = b"\x10\x02" * 1000
    out_path = _out_path(tmp_path)
    with patch("urllib.request.urlopen", return_value=_fake_urlopen(_ok_payload_bytes(pcm))):
        result = GeminiFlashTTSEngine.generate_speech(
            text="สวัสดีครับ", output_path=out_path, speed=1.0,
        )

    result_path = Path(result)
    assert result_path.exists()
    assert result_path.stat().st_size > 44  # more than just a WAV header

    with wave.open(str(result_path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 24000
        assert wf.getnframes() > 0

    # cache/analytics side effect actually ran
    assert recorded.get("task") == "tts"
    assert recorded.get("input_tokens", 0) > 0
    assert recorded.get("output_tokens", 0) > 0


def test_successful_generation_at_default_speed_invokes_atempo_ffmpeg(monkeypatch, tmp_path):
    """speed=1.15 is the documented default in generate_speech()'s signature
    -- confirm the atempo path actually runs (not just the no-speed-change
    rename branch) and still produces the final file, without a real ffmpeg
    binary."""
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)

    out_path = Path(_out_path(tmp_path))

    def fake_run(cmd, **kwargs):
        # Simulate ffmpeg by producing the requested output file from the
        # raw wav that's already on disk (the real ffmpeg call is mocked
        # away, but the caller-visible contract -- "an output file appears
        # at out_wav" -- must still hold).
        assert cmd[0] == "ffmpeg"
        assert "atempo=1.15" in cmd[cmd.index("-filter:a") + 1] if "-filter:a" in cmd else True
        out_wav = Path(cmd[-1])
        out_wav.write_bytes(b"RIFF....WAVEfmt fake")
        return MagicMock(returncode=0)

    with patch("urllib.request.urlopen", return_value=_fake_urlopen(_ok_payload_bytes())):
        with patch("subprocess.run", side_effect=fake_run) as mock_run:
            result = GeminiFlashTTSEngine.generate_speech(
                text="test", output_path=str(out_path), speed=1.15,
            )

    mock_run.assert_called_once()
    called_cmd = mock_run.call_args[0][0]
    assert "atempo=1.15" in called_cmd
    assert Path(result).exists()
    # the intermediate raw wav must be cleaned up
    assert not out_path.with_suffix(".raw.wav").exists()


def test_ad_tone_prompt_uses_requested_tone_and_falls_back_for_unknown(monkeypatch, tmp_path):
    """AD_TONE_PRESETS.get(ad_tone, ...premium) -- an unknown tone must not
    raise, it silently uses the premium prompt. Documented current behavior:
    a typo'd ad_tone degrades quietly rather than erroring."""
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _fake_urlopen(_ok_payload_bytes())

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        GeminiFlashTTSEngine.generate_speech(
            text="test", output_path=_out_path(tmp_path),
            ad_tone="not_a_real_tone", speed=1.0,
        )

    prompt_text = captured["body"]["contents"][0]["parts"][0]["text"]
    assert "Premium commercial" in prompt_text  # commercial_premium's own prompt text


def test_voice_name_argument_overrides_preset(monkeypatch, tmp_path):
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _fake_urlopen(_ok_payload_bytes())

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        GeminiFlashTTSEngine.generate_speech(
            text="test", output_path=_out_path(tmp_path),
            voice_preset="gemini_kore_female_bright", voice_name="Fenrir", speed=1.0,
        )

    voice_cfg = captured["body"]["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]
    assert voice_cfg["voiceName"] == "Fenrir"
