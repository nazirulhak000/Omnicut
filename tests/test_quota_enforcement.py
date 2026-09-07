"""
Regression tests for the P1 item 7 / plan item 19 security fix:
scripts/token_tracker.py recorded usage after every AI/TTS call but never
enforced any limit -- a runaway loop could burn unlimited Gemini/TTS quota.

Fix: scripts/quota.py adds a pre-flight check_budget() called immediately
before each paid network call (scripts/ai_bridge.py, gemini_tts_engine.py,
gemini_vision_matcher.py), raising AppError(AI_QUOTA_EXCEEDED) -- wired
into the existing scripts/error_handler.py taxonomy rather than a parallel
error path. Limits are configured via DAILY_TOKEN_LIMIT / DAILY_COST_THB_LIMIT
env vars; 0 disables a cap.

Critical placement requirement: in gemini_vision_matcher.py the check must
sit OUTSIDE (after) the existing hash-based cache check -- a cache hit costs
nothing and must not consume quota. Covered here by
test_vision_cache_hit_does_not_consume_or_check_quota.

Isolated / offline per .agents/rules/testing_standard.md: TokenTracker is
monkeypatched to point at a tmp_path analytics file, no real network/AI
calls are made anywhere in this file.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.quota as quota_module
from scripts.error_handler import AppError, ErrorCategory
from scripts.token_tracker import TokenTracker


@pytest.fixture(autouse=True)
def isolated_analytics(tmp_path, monkeypatch):
    """Point TokenTracker at a scratch file and reset its in-memory cache
    so events from other tests / the real project can never leak in."""
    analytics_file = tmp_path / ".token_analytics.json"
    monkeypatch.setattr(TokenTracker, "_cache", None)
    monkeypatch.setattr(TokenTracker, "_cache_mtime", 0.0)
    import scripts.token_tracker as tt_module
    monkeypatch.setattr(tt_module, "ANALYTICS_FILE", analytics_file)

    # Default: disable both caps unless a test opts in, so unrelated tests
    # of check_budget() start from "no limit configured".
    monkeypatch.delenv("DAILY_TOKEN_LIMIT", raising=False)
    monkeypatch.delenv("DAILY_COST_THB_LIMIT", raising=False)
    yield


def test_check_budget_noop_when_explicitly_disabled(monkeypatch):
    """Both limits explicitly set to 0 -> never raises, regardless of usage."""
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    TokenTracker.record_event(
        task="script", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=10_000_000, output_tokens=10_000_000,
    )
    quota_module.check_budget(task="script")  # must not raise


def test_check_budget_uses_generous_defaults_when_unset():
    """Unset (not explicitly 0) -> falls back to the built-in generous
    defaults, which a single ordinary call must stay well under."""
    assert quota_module.get_daily_token_limit() == quota_module.DEFAULT_DAILY_TOKEN_LIMIT
    assert quota_module.get_daily_cost_thb_limit() == quota_module.DEFAULT_DAILY_COST_THB_LIMIT
    TokenTracker.record_event(
        task="script", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=500, output_tokens=500,
    )
    quota_module.check_budget(task="script")  # must not raise


def test_check_budget_allows_when_under_token_limit(monkeypatch):
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "1000")
    TokenTracker.record_event(
        task="script", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=100, output_tokens=100,
    )
    quota_module.check_budget(task="script")  # 200 < 1000, must not raise


def test_check_budget_blocks_when_over_token_limit(monkeypatch):
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "1000")
    TokenTracker.record_event(
        task="script", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=800, output_tokens=800,
    )

    with pytest.raises(AppError) as exc_info:
        quota_module.check_budget(task="script")

    assert exc_info.value.category == ErrorCategory.AI_PROVIDER
    assert exc_info.value.code == "AI_QUOTA_EXCEEDED"


def test_check_budget_blocks_when_over_cost_limit(monkeypatch):
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0.01")
    # claude-sonnet-4-6 rate is expensive enough that a small call already
    # exceeds a 0.01 THB cap.
    TokenTracker.record_event(
        task="script", model="claude-sonnet-4-6", provider="gemini_api",
        input_tokens=10_000, output_tokens=10_000,
    )

    with pytest.raises(AppError) as exc_info:
        quota_module.check_budget(task="script")

    assert exc_info.value.code == "AI_QUOTA_EXCEEDED"


def test_check_budget_classifies_via_error_handler():
    """classify_exception() must pass an AppError through unchanged (it
    already is one) rather than re-wrapping it into a generic INTERNAL
    error -- this is what makes it 'wired into error_handler.py' rather
    than a parallel error path."""
    from scripts.error_handler import classify_exception

    monkeypatch_env_token_limit = quota_module.get_daily_token_limit
    try:
        import os
        os.environ["DAILY_TOKEN_LIMIT"] = "10"
        TokenTracker.record_event(
            task="script", model="gemini-2.5-flash", provider="gemini_api",
            input_tokens=100, output_tokens=100,
        )
        try:
            quota_module.check_budget(task="script")
            assert False, "expected AppError"
        except AppError as app_err:
            classified = classify_exception(app_err)
            assert classified is app_err
            assert classified.code == "AI_QUOTA_EXCEEDED"
    finally:
        os.environ.pop("DAILY_TOKEN_LIMIT", None)


def test_vision_cache_hit_does_not_consume_or_check_quota(monkeypatch, tmp_path):
    """The single most important placement requirement in this task: a
    cache hit in gemini_vision_matcher.py must short-circuit BEFORE
    check_budget() is ever called, even when the daily limit is already
    exhausted."""
    import scripts.gemini_vision_matcher as gvm

    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "1")  # already effectively exhausted
    TokenTracker.record_event(
        task="vision_match", model="gemini-2.5-flash", provider="gemini_free_tier",
        input_tokens=1000, output_tokens=1000,
    )

    # Prove the limit really is exhausted for a cache-miss caller.
    with pytest.raises(AppError):
        quota_module.check_budget(task="vision_match")

    # Now prove a cache hit sails through anyway: stub get_cached_matches to
    # simulate a hit, and make check_budget a trap that fails the test if
    # it is ever reached from match_script_to_video's cache-hit path.
    monkeypatch.setattr(
        gvm.GeminiVisionMatcher, "get_cached_matches",
        classmethod(lambda cls, path, cues: [{"cue_id": 1, "start_time": 0.0, "end_time": 1.0}]),
    )

    def _trap(*args, **kwargs):
        raise AssertionError("check_budget() must not be called on a cache hit")

    monkeypatch.setattr(quota_module, "check_budget", _trap)
    # match_script_to_video imports check_budget lazily inside the function
    # (`from scripts.quota import check_budget`), so patching the quota
    # module's attribute is what a real cache-hit-vs-miss code path would
    # observe too.

    result = gvm.GeminiVisionMatcher.match_script_to_video(
        raw_video_path=str(tmp_path / "does_not_need_to_exist.mp4"),
        cues=[{"start": 0.0, "end": 1.0, "text": "hello"}],
        raw_duration=10.0,
    )

    assert result == [{"cue_id": 1, "start_time": 0.0, "end_time": 1.0}]
