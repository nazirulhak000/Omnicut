"""
Tests for the AIBridge.generate() API-key retry/backoff/timeout hardening.

Findings this covers (see scripts/ai_bridge.py classify_genai_error and the
retry loop in generate()):

- a 429 (rate_limit) retries the SAME key once, with backoff, before
  rotating to the next key
- an auth error (401/403) rotates to the next key immediately, no retry
- a quota AppError (scripts/quota.py check_budget()) is never retried and
  never rotated -- it is the user's own daily cap, not a provider failure,
  and must surface unchanged
- when every configured key ultimately fails, generate() still raises
  ManualModeRequired carrying the built prompt
- the API-key path passes an explicit request timeout to the genai client

All network calls are mocked -- no real Gemini/API traffic, no real sleeps
(time.sleep is monkeypatched to a no-op so the suite stays fast), per
.agents/rules/testing_standard.md.
"""
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from google.genai import errors as genai_errors

from scripts.ai_bridge import AIBridge, ManualModeRequired, classify_genai_error
from scripts.error_handler import AppError, ErrorCategory


_CONTEXT = {
    "product_name": "หูฟังบลูทูธ",
    "angle_title": "เทียบราคา",
    "hook": "199 กับ 899 ต่างกันยังไง",
    "specs": [{"label": "จุดเด่น", "value": "เบสหนัก"}],
    "price_deal": "ลด 50%",
}


def _client_error(code: int, message: str = "err") -> genai_errors.ClientError:
    return genai_errors.ClientError(code, {"error": {"message": message, "status": "X"}}, None)


def _quota_app_error() -> AppError:
    return AppError(
        category=ErrorCategory.AI_PROVIDER,
        code="AI_QUOTA_EXCEEDED",
        message_th="เกินโควต้าการใช้งาน AI ที่ตั้งไว้ต่อวันแล้ว",
        suggestion_th="รอถึงวันถัดไป",
    )


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Retry backoff must not slow the suite down; also lets us assert on
    what durations were requested without actually waiting them out."""
    calls = []
    monkeypatch.setattr(time, "sleep", lambda s: calls.append(s))
    return calls


@pytest.fixture(autouse=True)
def _disable_antigravity_and_quota(monkeypatch):
    """Force generate() straight to the API-key path: no Antigravity CLI,
    no daily budget cap in effect."""
    monkeypatch.setattr(AIBridge, "has_antigravity_cli", classmethod(lambda cls: False))
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")


@pytest.fixture(autouse=True)
def _no_token_tracker_io(monkeypatch, tmp_path):
    """record_event does real file I/O; keep it a no-op so tests don't touch
    the real usage log."""
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)


def _fake_client_factory(behaviors):
    """Builds a stand-in for `genai.Client` whose `.models.generate_content`
    pops the next behavior off `behaviors` each call: an exception instance
    to raise, or a MagicMock response to return."""
    created_clients = []

    def factory(*, api_key, http_options=None):
        client = MagicMock()
        client._api_key = api_key
        client._http_options = http_options

        def generate_content(*, model, contents):
            behavior = behaviors.pop(0)
            if isinstance(behavior, BaseException):
                raise behavior
            return behavior

        client.models.generate_content.side_effect = generate_content
        created_clients.append(client)
        return client

    factory.created_clients = created_clients
    return factory


def _ok_response(task: str = "caption") -> MagicMock:
    resp = MagicMock()
    resp.text = '{"caption": "ลองแล้วติดใจ", "hashtags": ["#มือถือ"]}'
    return resp


# ----------------------------------------------------------------------
# classify_genai_error()
# ----------------------------------------------------------------------
def test_classify_429_as_rate_limit():
    assert classify_genai_error(_client_error(429)) == "rate_limit"


def test_classify_401_and_403_as_auth():
    assert classify_genai_error(_client_error(401)) == "auth"
    assert classify_genai_error(_client_error(403)) == "auth"


def test_classify_other_client_error_as_other():
    assert classify_genai_error(_client_error(400)) == "other"


def test_classify_httpx_timeout_as_transient():
    import httpx
    assert classify_genai_error(httpx.ConnectTimeout("timed out")) == "transient"


def test_classify_quota_app_error_as_quota():
    assert classify_genai_error(_quota_app_error()) == "quota"


def test_classify_falls_back_to_message_matching_for_untyped_errors():
    assert classify_genai_error(RuntimeError("HTTP 429 Too Many Requests")) == "rate_limit"
    assert classify_genai_error(RuntimeError("API key not valid")) == "auth"
    assert classify_genai_error(RuntimeError("Connection timeout")) == "transient"
    assert classify_genai_error(RuntimeError("something odd")) == "other"


# ----------------------------------------------------------------------
# generate() retry/rotation behavior on the API-key path
# ----------------------------------------------------------------------
def test_429_retries_same_key_before_succeeding(monkeypatch, _no_real_sleep):
    """A 429 on key #1's first attempt must retry key #1 again (not rotate
    to key #2) before succeeding."""
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: ["key-1", "key-2"]))

    behaviors = [_client_error(429), _ok_response()]
    factory = _fake_client_factory(behaviors)

    with patch("google.genai.Client", side_effect=factory):
        result = AIBridge.generate("caption", _CONTEXT, prefer_antigravity=False)

    assert result["caption"]
    assert len(factory.created_clients) == 1, "must not have rotated to key #2"
    assert factory.created_clients[0]._api_key == "key-1"
    assert _no_real_sleep, "must back off before the same-key retry"


def test_429_exhausted_on_same_key_then_rotates(monkeypatch, _no_real_sleep):
    """If key #1 is rate-limited on both allowed attempts, the call must
    rotate to key #2 rather than giving up."""
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: ["key-1", "key-2"]))

    behaviors = [_client_error(429), _client_error(429), _ok_response()]
    factory = _fake_client_factory(behaviors)

    with patch("google.genai.Client", side_effect=factory):
        result = AIBridge.generate("caption", _CONTEXT, prefer_antigravity=False)

    assert result["caption"]
    assert len(factory.created_clients) == 2
    assert factory.created_clients[0]._api_key == "key-1"
    assert factory.created_clients[1]._api_key == "key-2"


def test_auth_error_rotates_immediately_without_retry(monkeypatch, _no_real_sleep):
    """An auth failure (401/403) must rotate to the next key on the FIRST
    failure -- no wasted retry against a dead key."""
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: ["dead-key", "key-2"]))

    behaviors = [_client_error(403, "API key not valid"), _ok_response()]
    factory = _fake_client_factory(behaviors)

    with patch("google.genai.Client", side_effect=factory):
        result = AIBridge.generate("caption", _CONTEXT, prefer_antigravity=False)

    assert result["caption"]
    assert len(behaviors) == 0, "only one call should have been made against the dead key"
    assert len(factory.created_clients) == 2
    assert not _no_real_sleep, "an auth failure must add no backoff delay"


def test_quota_error_is_never_retried_or_rotated(monkeypatch, _no_real_sleep):
    """check_budget() runs before the key loop even starts, so a quota
    AppError must propagate straight out of generate() -- untouched by the
    per-key retry/rotation logic, and no genai client should be constructed
    at all."""
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: ["key-1", "key-2"]))

    quota_err = _quota_app_error()
    with patch("scripts.quota.check_budget", side_effect=quota_err):
        with patch("google.genai.Client") as mock_client_cls:
            with pytest.raises(AppError) as exc_info:
                AIBridge.generate("caption", _CONTEXT, prefer_antigravity=False)

    assert exc_info.value is quota_err
    mock_client_cls.assert_not_called()


def test_quota_error_raised_mid_loop_is_not_swallowed(monkeypatch, _no_real_sleep):
    """Belt-and-suspenders: even if a quota AppError were somehow raised by
    the generate_content() call itself (not just check_budget), the broad
    `except Exception` inside the retry loop must re-raise it rather than
    treating it as a rotate-worthy provider failure."""
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: ["key-1", "key-2"]))

    quota_err = _quota_app_error()
    behaviors = [quota_err]
    factory = _fake_client_factory(behaviors)

    with patch("google.genai.Client", side_effect=factory):
        with pytest.raises(AppError) as exc_info:
            AIBridge.generate("caption", _CONTEXT, prefer_antigravity=False)

    assert exc_info.value is quota_err
    assert len(factory.created_clients) == 1, "must not have rotated to key #2"


def test_all_keys_failed_still_reaches_manual_mode_required(monkeypatch, _no_real_sleep):
    """When every key exhausts its retries, generate() must fall through to
    ManualModeRequired carrying the built prompt -- never raise the raw
    provider exception to the caller."""
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: ["key-1", "key-2"]))

    behaviors = [
        _client_error(429), _client_error(429),   # key-1: rate-limited twice
        _client_error(403, "invalid"),             # key-2: auth, no retry
    ]
    factory = _fake_client_factory(behaviors)

    with patch("google.genai.Client", side_effect=factory):
        with pytest.raises(ManualModeRequired) as exc_info:
            AIBridge.generate("caption", _CONTEXT, prefer_antigravity=False)

    assert exc_info.value.task == "caption"
    assert exc_info.value.prompt


def test_transient_error_retries_same_key_then_succeeds(monkeypatch, _no_real_sleep):
    """A transient network/timeout error must retry the SAME key once
    before giving up on it."""
    import httpx
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: ["key-1"]))

    behaviors = [httpx.ConnectTimeout("timed out"), _ok_response()]
    factory = _fake_client_factory(behaviors)

    with patch("google.genai.Client", side_effect=factory):
        result = AIBridge.generate("caption", _CONTEXT, prefer_antigravity=False)

    assert result["caption"]
    assert len(factory.created_clients) == 1, "must retry the same key, not rotate"


# ----------------------------------------------------------------------
# Timeout is actually passed to the client
# ----------------------------------------------------------------------
def test_api_key_path_passes_explicit_timeout_to_client(monkeypatch, _no_real_sleep):
    from scripts.ai_bridge import API_REQUEST_TIMEOUT_SECONDS

    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: ["key-1"]))
    behaviors = [_ok_response()]
    factory = _fake_client_factory(behaviors)

    with patch("google.genai.Client", side_effect=factory) as mock_client_cls:
        AIBridge.generate("caption", _CONTEXT, prefer_antigravity=False)

    assert mock_client_cls.call_count == 1
    _, kwargs = mock_client_cls.call_args
    assert "http_options" in kwargs
    http_options = kwargs["http_options"]
    assert http_options.timeout == API_REQUEST_TIMEOUT_SECONDS * 1000
