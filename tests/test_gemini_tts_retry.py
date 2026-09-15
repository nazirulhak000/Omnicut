"""
Tests for GeminiFlashTTSEngine.generate_speech()'s retry/backoff hardening:
a 429 must retry the same key+model before falling through, a quota AppError
must never be retried, all-keys-failed must still raise (not silently
produce no audio), and the existing timeout (already present at
urlopen(..., timeout=75) before this change) stays in place.

All network calls are mocked -- no real Gemini traffic, no real audio files,
no real sleeps -- per .agents/rules/testing_standard.md.
"""
import io
import sys
import time
import base64
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gemini_tts_engine import GeminiFlashTTSEngine
from scripts.error_handler import AppError, ErrorCategory


def _quota_app_error() -> AppError:
    return AppError(
        category=ErrorCategory.AI_PROVIDER,
        code="AI_QUOTA_EXCEEDED",
        message_th="เกินโควต้าการใช้งาน AI ที่ตั้งไว้ต่อวันแล้ว",
        suggestion_th="รอถึงวันถัดไป",
    )


def _http_error(code: int, retry_after: str = None) -> urllib.error.HTTPError:
    headers = {}
    if retry_after:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("http://x", code, "err", headers, None)


def _ok_response_bytes() -> bytes:
    pcm = b"\x00\x01" * 100  # tiny fake 16-bit PCM payload
    payload = {
        "candidates": [{
            "content": {"parts": [{"inlineData": {"data": base64.b64encode(pcm).decode("ascii")}}]}
        }]
    }
    import json
    return json.dumps(payload).encode("utf-8")


def _fake_urlopen_factory(behaviors):
    """Pops the next behavior off `behaviors` per call: an exception
    instance to raise, or bytes to return as the response body."""
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append({"url": req.full_url, "timeout": timeout})
        behavior = behaviors.pop(0)
        if isinstance(behavior, BaseException):
            raise behavior
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = behavior
        cm.__exit__.return_value = False
        return cm

    fake_urlopen.calls = calls
    return fake_urlopen


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    calls = []
    monkeypatch.setattr(time, "sleep", lambda s: calls.append(s))
    return calls


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)


def _out_path(tmp_path) -> str:
    return str(tmp_path / "out.wav")


def test_429_retries_same_key_model_before_succeeding(monkeypatch, tmp_path, _no_real_sleep):
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))

    behaviors = [_http_error(429, retry_after="2"), _ok_response_bytes()]
    fake_urlopen = _fake_urlopen_factory(behaviors)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = GeminiFlashTTSEngine.generate_speech(
            text="สวัสดีครับ", output_path=_out_path(tmp_path), speed=1.0
        )

    assert Path(result).exists()
    assert len(fake_urlopen.calls) == 2
    assert fake_urlopen.calls[0]["url"] == fake_urlopen.calls[1]["url"], "must retry the SAME model URL"
    assert _no_real_sleep == [2.0], "must honor Retry-After from the 429 response"


def test_auth_error_moves_on_without_retry(monkeypatch, tmp_path, _no_real_sleep):
    """401/403 must not be retried against the same key/model -- move
    straight to the next fallback (here, the second model candidate)."""
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))

    behaviors = [_http_error(403), _ok_response_bytes()]
    fake_urlopen = _fake_urlopen_factory(behaviors)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = GeminiFlashTTSEngine.generate_speech(
            text="สวัสดีครับ", output_path=_out_path(tmp_path), speed=1.0
        )

    assert Path(result).exists()
    assert len(fake_urlopen.calls) == 2
    assert fake_urlopen.calls[0]["url"] != fake_urlopen.calls[1]["url"], "must move to the next model, not retry"
    assert not _no_real_sleep, "an auth-style HTTP error must add no backoff delay"


def test_quota_error_is_never_retried(monkeypatch, tmp_path, _no_real_sleep):
    """check_budget() runs before the key/model loop even starts -- a quota
    AppError must propagate straight out of generate_speech(), no urlopen
    call should ever be attempted."""
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))

    quota_err = _quota_app_error()
    with patch("scripts.quota.check_budget", side_effect=quota_err):
        with patch("urllib.request.urlopen") as mock_urlopen:
            with pytest.raises(AppError) as exc_info:
                GeminiFlashTTSEngine.generate_speech(
                    text="สวัสดีครับ", output_path=_out_path(tmp_path), speed=1.0
                )

    assert exc_info.value is quota_err
    mock_urlopen.assert_not_called()


def test_all_keys_and_models_failed_raises_runtime_error(monkeypatch, tmp_path, _no_real_sleep):
    """Exhausting every key/model combination must still raise -- never
    silently return without producing audio."""
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1", "key-2"]))

    behaviors = [
        _http_error(429),                      # model-1, key-1: rate-limited, failover to key-2
        _http_error(429),                      # model-1, key-2: rate-limited, failover to model-2
        _http_error(403),                      # model-2, key-1: auth error, failover to key-2
        _http_error(403),                      # model-2, key-2: auth error, all combinations exhausted
    ]
    fake_urlopen = _fake_urlopen_factory(behaviors)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(RuntimeError, match="All Gemini Flash TTS keys and models failed"):
            GeminiFlashTTSEngine.generate_speech(
                text="สวัสดีครับ", output_path=_out_path(tmp_path), speed=1.0
            )

    assert len(behaviors) == 0


def test_transient_network_error_retries_same_key_model(monkeypatch, tmp_path, _no_real_sleep):
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))

    behaviors = [urllib.error.URLError("connection refused"), _ok_response_bytes()]
    fake_urlopen = _fake_urlopen_factory(behaviors)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = GeminiFlashTTSEngine.generate_speech(
            text="สวัสดีครับ", output_path=_out_path(tmp_path), speed=1.0
        )

    assert Path(result).exists()
    assert len(fake_urlopen.calls) == 2
    assert fake_urlopen.calls[0]["url"] == fake_urlopen.calls[1]["url"]


def test_existing_timeout_still_passed_to_urlopen(monkeypatch, tmp_path, _no_real_sleep):
    """This engine already bounded the request at timeout=75 before this
    hardening pass -- confirm the retry changes did not drop it."""
    monkeypatch.setattr(GeminiFlashTTSEngine, "get_api_keys", classmethod(lambda cls: ["key-1"]))

    behaviors = [_ok_response_bytes()]
    fake_urlopen = _fake_urlopen_factory(behaviors)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        GeminiFlashTTSEngine.generate_speech(
            text="สวัสดีครับ", output_path=_out_path(tmp_path), speed=1.0
        )

    assert fake_urlopen.calls[0]["timeout"] == 75
