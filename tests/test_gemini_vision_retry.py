"""
Tests for GeminiVisionMatcher.match_script_to_video()'s retry/backoff/timeout
hardening (mirrors scripts/ai_bridge.py's classify_genai_error): a 429 must
retry the same model before falling through, a quota AppError must never be
retried, and the generate_content() call must carry an explicit timeout.

All network/file-upload calls are mocked -- no real Gemini traffic, no real
video files, no real sleeps -- per .agents/rules/testing_standard.md.
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

from scripts import gemini_vision_matcher as gvm
from scripts.error_handler import AppError, ErrorCategory


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
    calls = []
    monkeypatch.setattr(time, "sleep", lambda s: calls.append(s))
    return calls


@pytest.fixture(autouse=True)
def _isolate_cache_and_budget(monkeypatch, tmp_path):
    """Keep this test off the real .vision_cache.json and the real quota
    gate, and give match_script_to_video an API key to work with."""
    monkeypatch.setattr(gvm, "VISION_CACHE_FILE", tmp_path / ".vision_cache.json")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    # No cache hit and no prior cached match -- forces the real call path.
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, path, cues: None))
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_or_upload_video", classmethod(lambda cls, client, path: MagicMock(name="remote_video")))
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)


_CUES = [{"start": 0.0, "end": 2.0, "text": "หนึ่ง"}]


def _ok_response() -> MagicMock:
    resp = MagicMock()
    resp.text = '```json\n{"matched_shots": [{"cue_id": 1, "start_time": 0.0, "end_time": 2.0}]}\n```'
    return resp


def _fake_client_factory(behaviors):
    created = []

    def factory(*, api_key, http_options=None):
        client = MagicMock()
        created.append(client)

        def generate_content(*, model, contents, config=None):
            behavior = behaviors.pop(0)
            if isinstance(behavior, BaseException):
                raise behavior
            return behavior

        client.models.generate_content.side_effect = generate_content
        return client

    factory.created = created
    return factory


def test_429_retries_same_model_before_succeeding(tmp_path, _no_real_sleep):
    behaviors = [_client_error(429), _ok_response()]
    factory = _fake_client_factory(behaviors)
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake")

    with patch("google.genai.Client", side_effect=factory):
        result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw_video), _CUES, raw_duration=10.0)

    assert result, "must have succeeded on the retried attempt"
    assert len(behaviors) == 0
    assert _no_real_sleep, "must back off before retrying the same model"


def test_quota_error_from_check_budget_is_never_retried(tmp_path, _no_real_sleep):
    """check_budget() runs before the try/generate_content block -- a quota
    AppError must propagate straight out, never treated as a model failure
    to retry or fall back from."""
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake")

    quota_err = _quota_app_error()
    with patch("scripts.quota.check_budget", side_effect=quota_err):
        with patch("google.genai.Client") as mock_client_cls:
            with pytest.raises(AppError) as exc_info:
                gvm.GeminiVisionMatcher.match_script_to_video(str(raw_video), _CUES, raw_duration=10.0)

    assert exc_info.value is quota_err
    mock_client_cls.assert_not_called()


def test_generate_content_receives_explicit_timeout(tmp_path, _no_real_sleep):
    from scripts.gemini_vision_matcher import VISION_GENERATE_TIMEOUT_SECONDS

    behaviors = [_ok_response()]
    factory = _fake_client_factory(behaviors)
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake")

    with patch("google.genai.Client", side_effect=factory):
        gvm.GeminiVisionMatcher.match_script_to_video(str(raw_video), _CUES, raw_duration=10.0)

    client = factory.created[0]
    _, kwargs = client.models.generate_content.call_args
    assert "config" in kwargs
    assert kwargs["config"].http_options.timeout == VISION_GENERATE_TIMEOUT_SECONDS * 1000


def test_all_models_failing_falls_back_to_empty_list(tmp_path, _no_real_sleep):
    """Vision matching is a quality enhancement, not a hard dependency --
    exhausting every model/retry must degrade to [] (the caller falls back
    to rhythmic cuts), not raise, when there is no prior cache to reuse."""
    behaviors = [
        _client_error(429), _client_error(429),      # gemini-2.5-flash: rate-limited twice
        _client_error(403, "invalid"),                # gemini-2.5-flash-lite: auth, no retry
    ]
    factory = _fake_client_factory(behaviors)
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"fake")

    with patch("google.genai.Client", side_effect=factory):
        result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw_video), _CUES, raw_duration=10.0)

    assert result == []
