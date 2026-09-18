"""
Tests for scripts/token_tracker.py -- the budget-enforcement dependency.

scripts/quota.py's check_budget() reads TokenTracker.get_usage_today()
before every paid AI/TTS/vision call. If this module miscounts, either
every AI call is wrongly blocked, or -- worse and silently -- the daily
cost cap never trips and spending runs unbounded. This file has never had
direct test coverage; test_quota_enforcement.py only exercises it
incidentally through scripts/quota.py.

Isolated / offline per .agents/rules/testing_standard.md: every test
monkeypatches scripts.token_tracker.ANALYTICS_FILE to a tmp_path file and
resets the class-level cache, so the real _Docs/.token_analytics.json (in
this repo it actually lives under 03_Projects/, see ANALYTICS_FILE) is
never read or written.
"""
import datetime
import json
import os
import subprocess
import sys
import threading
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.token_tracker as tt_module
from scripts.token_tracker import TokenTracker


@pytest.fixture(autouse=True)
def isolated_analytics(tmp_path, monkeypatch):
    """Point TokenTracker at a scratch file and blow away its in-memory
    class-level cache so no state leaks between tests or from the real
    project file."""
    analytics_file = tmp_path / ".token_analytics.json"
    monkeypatch.setattr(tt_module, "ANALYTICS_FILE", analytics_file)
    monkeypatch.setattr(TokenTracker, "_cache", None)
    monkeypatch.setattr(TokenTracker, "_cache_mtime", 0.0)
    monkeypatch.setattr(TokenTracker, "_cache_stamp", (0, -1))
    yield analytics_file


# ---------------------------------------------------------------------------
# record_event()
# ---------------------------------------------------------------------------

def test_record_event_writes_all_token_fields_and_sums_total(isolated_analytics):
    event = TokenTracker.record_event(
        task="script_gen", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=100, output_tokens=50, thinking_tokens=25,
        latency_seconds=1.2345, project_name="Proj A",
    )
    assert event["input_tokens"] == 100
    assert event["output_tokens"] == 50
    assert event["thinking_tokens"] == 25
    assert event["total_tokens"] == 175  # 100 + 50 + 25
    assert event["task"] == "script_gen"
    assert event["model"] == "gemini-2.5-flash"
    assert event["provider"] == "gemini_api"
    assert event["project_name"] == "Proj A"
    # latency is rounded to 2dp, not truncated
    assert event["latency_seconds"] == 1.23

    # And it was actually persisted to disk, not just returned.
    on_disk = json.loads(isolated_analytics.read_text(encoding="utf-8"))
    assert len(on_disk["events"]) == 1
    assert on_disk["events"][0]["id"] == event["id"]
    assert on_disk["events"][0]["total_tokens"] == 175


def test_record_event_defaults_project_name_and_metadata(isolated_analytics):
    event = TokenTracker.record_event(
        task="tts", model="gemini-3.1-flash-tts", provider="gemini_api",
        input_tokens=10, output_tokens=10,
    )
    assert event["project_name"] == "General Studio Task"
    assert event["metadata"] == {}


def test_record_event_coerces_token_counts_to_int(isolated_analytics):
    """Callers occasionally pass floats through from API responses; the
    stored fields should still be plain ints so downstream sums behave."""
    event = TokenTracker.record_event(
        task="script", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=10.0, output_tokens=5.0, thinking_tokens=0.0,
    )
    assert isinstance(event["input_tokens"], int)
    assert isinstance(event["output_tokens"], int)
    assert isinstance(event["total_tokens"], int)


def test_record_event_caps_history_at_1000_events(isolated_analytics):
    """events list is capped at 1000 to bound disk/memory -- verify the
    cap actually trims from the front (oldest first), keeping the newest."""
    for i in range(1005):
        TokenTracker.record_event(
            task=f"t{i}", model="gemini-2.5-flash", provider="gemini_api",
            input_tokens=1, output_tokens=0,
        )
    events = TokenTracker._load()["events"]
    assert len(events) == 1000
    # The oldest 5 (t0..t4) must have been dropped; newest (t1004) kept.
    assert events[0]["task"] == "t5"
    assert events[-1]["task"] == "t1004"


def test_daily_usage_survives_1000_event_trim_and_legacy_migration(isolated_analytics):
    """Daily quota usage must include calls no longer present in events.

    The fixture starts as a pre-daily_usage analytics file with exactly 1,000
    events. The first new write both migrates the retained history and trims
    one old event; all 1,005 calls must still count toward today's quota.
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    legacy = TokenTracker._get_default_structure()
    legacy.pop("daily_usage", None)
    legacy["events"] = [
        {
            "date": today,
            "total_tokens": 2_000,
            "input_tokens": 1_000,
            "output_tokens": 1_000,
            "thinking_tokens": 0,
            "cost_saved_thb": 0.5,
        }
        for _ in range(1_000)
    ]
    isolated_analytics.write_text(json.dumps(legacy), encoding="utf-8")
    TokenTracker._cache = None
    TokenTracker._cache_stamp = (0, -1)

    for _ in range(5):
        TokenTracker.record_event(
            task="quota", model="claude-sonnet-4-6", provider="test",
            input_tokens=1_000, output_tokens=1_000,
        )

    usage = TokenTracker.get_usage_today()
    assert usage["total_tokens"] == 2_010_000
    assert usage["calls"] == 1_005
    assert usage["cost_thb"] == 503.15

    data = json.loads(isolated_analytics.read_text(encoding="utf-8"))
    assert len(data["events"]) == 1_000
    assert data["daily_usage"][today]["calls"] == 1_005
    assert data["daily_usage"][today]["total_tokens"] == 2_010_000


def test_record_event_totals_track_sum_of_events(isolated_analytics):
    """The hand-maintained `totals` running aggregate must agree with an
    independent sum over `events` -- this is the field quota.py trusts
    implicitly through get_usage_today() (which sums events itself, but
    get_summary() trusts `totals` directly)."""
    TokenTracker.record_event(
        task="a", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=100, output_tokens=200, thinking_tokens=10,
    )
    TokenTracker.record_event(
        task="b", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=50, output_tokens=25, thinking_tokens=5,
    )
    data = TokenTracker._load()
    events = data["events"]
    totals = data["totals"]

    assert totals["input_tokens"] == sum(e["input_tokens"] for e in events)
    assert totals["output_tokens"] == sum(e["output_tokens"] for e in events)
    assert totals["thinking_tokens"] == sum(e["thinking_tokens"] for e in events)
    assert totals["total_tokens"] == sum(e["total_tokens"] for e in events)
    assert totals["total_calls"] == len(events)


def test_record_event_totals_survive_the_1000_event_trim(isolated_analytics):
    """FIXED (was BUG CANDIDATE): `totals` accumulates on every write and is
    never trimmed, while `events` is capped at 1000 and drops old entries.
    Past 1000 lifetime events, totals["total_tokens"] necessarily stops
    equaling sum(events) -- it becomes a lifetime counter while events is a
    rolling window, and get_summary() reported the lifetime number directly
    with no way for a reader to verify it against what's stored.

    Fix: whatever record_event() trims off the front of `events` is folded
    into data["trimmed_aggregate"], so lifetime `totals` is no longer an
    unverifiable hand-kept counter -- it is exactly reconstructable as
    trimmed_aggregate + sum(events). This test now asserts that identity
    instead of merely documenting the drift."""
    for i in range(1005):
        TokenTracker.record_event(
            task=f"t{i}", model="gemini-2.5-flash", provider="gemini_api",
            input_tokens=1, output_tokens=0,
        )
    data = TokenTracker._load()
    events_sum = sum(e["total_tokens"] for e in data["events"])
    totals_total = data["totals"]["total_tokens"]
    trimmed_total = data["trimmed_aggregate"]["total_tokens"]

    # events window only has 1000 of the 1005 recorded -> sum(events) < totals.
    assert events_sum == 1000
    assert totals_total == 1005
    assert totals_total != events_sum  # lifetime vs. retained-window drift is real

    # ...but it's no longer unverifiable: the 5 trimmed events (t0..t4, 1
    # token each) are captured in trimmed_aggregate, so totals is exactly
    # reconstructable from what's actually stored on disk.
    assert trimmed_total == 5
    assert totals_total == trimmed_total + events_sum

    calls_trimmed = data["trimmed_aggregate"]["total_calls"]
    assert calls_trimmed == 5
    assert data["totals"]["total_calls"] == calls_trimmed + len(data["events"])


# ---------------------------------------------------------------------------
# get_usage_today() -- the function quota.py's check_budget() depends on
# ---------------------------------------------------------------------------

def test_get_usage_today_sums_only_todays_events(isolated_analytics, monkeypatch):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    data = TokenTracker._load()
    data["events"] = [
        {"date": today, "total_tokens": 100, "cost_saved_thb": 1.0},
        {"date": today, "total_tokens": 50, "cost_saved_thb": 0.5},
        {"date": yesterday, "total_tokens": 999999, "cost_saved_thb": 999.0},
    ]
    TokenTracker._save(data)

    usage = TokenTracker.get_usage_today()
    assert usage["date"] == today
    assert usage["total_tokens"] == 150
    assert usage["cost_thb"] == 1.5
    assert usage["calls"] == 2


def test_get_usage_today_excludes_event_at_2359_from_a_different_day(isolated_analytics):
    """An event recorded at 23:59 yesterday must not bleed into today's
    total -- get_usage_today() keys strictly off the stored `date` field
    (local wall-clock date at record time), not off timestamp proximity."""
    yesterday_2359 = (datetime.datetime.now() - datetime.timedelta(days=1)).replace(
        hour=23, minute=59, second=0, microsecond=0
    )
    data = TokenTracker._load()
    data["events"] = [{
        "date": yesterday_2359.strftime("%Y-%m-%d"),
        "timestamp": yesterday_2359.isoformat(),
        "total_tokens": 5000,
        "cost_saved_thb": 10.0,
    }]
    TokenTracker._save(data)

    usage = TokenTracker.get_usage_today()
    assert usage["total_tokens"] == 0
    assert usage["calls"] == 0


def test_get_usage_today_includes_event_at_0001_today(isolated_analytics):
    """Symmetric case: an event at 00:01 today counts fully towards today,
    even though it happened moments after midnight."""
    today_0001 = datetime.datetime.now().replace(hour=0, minute=1, second=0, microsecond=0)
    today_str = today_0001.strftime("%Y-%m-%d")
    data = TokenTracker._load()
    data["events"] = [{
        "date": today_str,
        "timestamp": today_0001.isoformat(),
        "total_tokens": 42,
        "cost_saved_thb": 1.0,
    }]
    TokenTracker._save(data)

    usage = TokenTracker.get_usage_today()
    assert usage["date"] == today_str
    assert usage["total_tokens"] == 42
    assert usage["calls"] == 1


def test_get_usage_today_treats_missing_date_field_as_not_today(isolated_analytics):
    """An event with no `date` key at all (malformed/older schema) must not
    silently count as today via some fallback -- get_usage_today() does
    `ev.get('date') != today`, so a missing key (None) never equals a real
    date string and the event is correctly excluded. This guards against a
    regression where someone "helpfully" defaults missing date to today."""
    data = TokenTracker._load()
    data["events"] = [{"total_tokens": 12345, "cost_saved_thb": 50.0}]  # no "date" key
    TokenTracker._save(data)

    usage = TokenTracker.get_usage_today()
    assert usage["total_tokens"] == 0
    assert usage["calls"] == 0


def test_get_usage_today_treats_malformed_date_string_as_not_today(isolated_analytics):
    """A garbage/malformed date string (e.g. wrong format, empty string)
    simply won't equal today's "%Y-%m-%d" string, so it is excluded rather
    than raising. Verifies no exception leaks out of the pre-flight budget
    check on dirty data."""
    data = TokenTracker._load()
    data["events"] = [
        {"date": "not-a-date", "total_tokens": 10, "cost_saved_thb": 1.0},
        {"date": "", "total_tokens": 20, "cost_saved_thb": 2.0},
        {"date": None, "total_tokens": 30, "cost_saved_thb": 3.0},
    ]
    TokenTracker._save(data)

    usage = TokenTracker.get_usage_today()
    assert usage["total_tokens"] == 0
    assert usage["calls"] == 0


def test_get_usage_today_defaults_missing_numeric_fields_to_zero(isolated_analytics):
    """An event dated today but missing total_tokens/cost_saved_thb (e.g.
    hand-edited or from a future schema) must not raise a KeyError -- the
    pre-flight budget check runs before every paid call and cannot crash
    the caller."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    data = TokenTracker._load()
    data["events"] = [{"date": today}]
    TokenTracker._save(data)

    usage = TokenTracker.get_usage_today()
    assert usage["total_tokens"] == 0
    assert usage["cost_thb"] == 0.0
    assert usage["calls"] == 1  # the event still counts as a "call" today


# ---------------------------------------------------------------------------
# class-level cache (_cache / _cache_stamp) invalidation
# ---------------------------------------------------------------------------

def test_cache_invalidates_on_same_mtime_but_different_size(isolated_analytics, monkeypatch):
    """FIXED (was BUG CANDIDATE): _load() used to key invalidation purely off
    st_mtime, so a competing writer whose update landed with an mtime no
    newer than the cached one (real on coarse-resolution filesystems --
    Windows is the platform here) would be served stale data forever. _load()
    now compares (st_mtime_ns, st_size) -- content that changes (a new event
    appended) almost always changes the byte length too, so a same-mtime
    concurrent write is now caught via the size half of the pair even when
    the mtime half looks unchanged."""
    TokenTracker.record_event(
        task="a", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=1, output_tokens=1,
    )
    cached_mtime_ns = TokenTracker._cache_stamp[0]

    # Simulate another process writing a materially different (and
    # differently-sized) file, but force its mtime to look no newer than
    # what's cached -- the coarse-filesystem-resolution scenario.
    other_data = TokenTracker._get_default_structure()
    other_data["events"] = [{"date": "2000-01-01", "total_tokens": 777777, "task": "external"}]
    isolated_analytics.write_text(json.dumps(other_data), encoding="utf-8")
    import os
    cached_mtime_s = cached_mtime_ns / 1e9
    os.utime(isolated_analytics, (cached_mtime_s, cached_mtime_s))

    data = TokenTracker._load()
    # Picks up the rewritten file because its size differs from the cache's,
    # even though its mtime does not look newer.
    assert data["events"][0]["task"] == "external"
    assert data["events"][0]["total_tokens"] == 777777


def test_cache_serves_cached_data_when_stamp_is_truly_unchanged(isolated_analytics):
    """Sanity check for the other direction: when the on-disk (mtime_ns,
    size) stamp genuinely has not changed, _load() must still serve the
    cache rather than re-reading on every call -- this is what keeps the
    per-call cost cheap for check_budget(), which reads on every paid call."""
    TokenTracker.record_event(
        task="a", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=1, output_tokens=1,
    )
    cached_events_obj = TokenTracker._cache["events"]

    data = TokenTracker._load()
    # Same object identity -- proves this was served from cache, not
    # re-parsed from disk.
    assert data["events"] is cached_events_obj


def test_cache_invalidates_when_disk_file_changes_underneath(isolated_analytics, monkeypatch):
    """The intended, common case: another process/worker writes the file
    with a strictly newer mtime -- _load() must pick up the new content
    rather than returning a stale cached total (this is exactly the
    silent-under-count failure mode the audit is worried about)."""
    TokenTracker.record_event(
        task="a", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=1, output_tokens=1,
    )

    other_data = TokenTracker._get_default_structure()
    other_data["events"] = [{"date": "2000-01-01", "total_tokens": 777777, "task": "external"}]
    isolated_analytics.write_text(json.dumps(other_data), encoding="utf-8")
    import os
    future = TokenTracker._cache_mtime + 5.0
    os.utime(isolated_analytics, (future, future))

    data = TokenTracker._load()
    assert data["events"][0]["task"] == "external"
    assert data["events"][0]["total_tokens"] == 777777


def test_cache_falls_back_to_default_structure_on_corrupt_json(isolated_analytics):
    """A truncated/corrupt analytics file must not crash callers -- _load()
    catches the JSON error and returns a fresh default structure instead."""
    isolated_analytics.write_text("{not valid json!!", encoding="utf-8")
    data = TokenTracker._load()
    assert data["events"] == []
    assert data["totals"]["total_tokens"] == 0


# ---------------------------------------------------------------------------
# get_summary()
# ---------------------------------------------------------------------------

def test_get_summary_breaks_down_by_model_task_and_provider(isolated_analytics):
    TokenTracker.record_event(
        task="script", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=100, output_tokens=100, latency_seconds=1.0,
    )
    TokenTracker.record_event(
        task="script", model="gemini-2.5-flash", provider="gemini_api",
        input_tokens=100, output_tokens=100, latency_seconds=3.0,
    )
    TokenTracker.record_event(
        task="tts", model="gemini-3.1-flash-tts", provider="gemini_free_tier",
        input_tokens=10, output_tokens=10, latency_seconds=2.0,
    )

    summary = TokenTracker.get_summary()
    assert summary["tokens_by_model"]["gemini-2.5-flash"] == 400
    assert summary["calls_by_model"]["gemini-2.5-flash"] == 2
    assert summary["tokens_by_task"]["script"] == 400
    assert summary["calls_by_task"]["tts"] == 1
    assert summary["calls_by_provider"]["gemini_free_tier"] == 1
    assert summary["totals"]["avg_latency_seconds"] == 2.0  # (1+3+2)/3


def test_get_summary_recent_events_returns_last_50_newest_first(isolated_analytics):
    for i in range(60):
        TokenTracker.record_event(
            task=f"t{i}", model="gemini-2.5-flash", provider="gemini_api",
            input_tokens=1, output_tokens=0,
        )
    summary = TokenTracker.get_summary()
    recent = summary["recent_events"]
    assert len(recent) == 50
    assert recent[0]["task"] == "t59"   # newest first
    assert recent[-1]["task"] == "t10"  # oldest of the kept window


def test_get_summary_exposes_trimmed_aggregate_for_audit(isolated_analytics):
    """get_summary()'s totals are a lifetime figure that can outlive the
    retained 1000-event window; it now also surfaces trimmed_aggregate so a
    reader can verify totals == trimmed_aggregate + sum(recent window),
    rather than trusting totals as an opaque, unverifiable number."""
    for i in range(1005):
        TokenTracker.record_event(
            task=f"t{i}", model="gemini-2.5-flash", provider="gemini_api",
            input_tokens=1, output_tokens=0,
        )
    summary = TokenTracker.get_summary()
    assert summary["trimmed_aggregate"]["total_tokens"] == 5
    assert summary["trimmed_aggregate"]["total_calls"] == 5
    # get_summary() doesn't return raw events, but _load() does -- confirm
    # the identity holds against the same underlying data get_summary() read.
    events_sum = sum(e["total_tokens"] for e in TokenTracker._load()["events"])
    assert summary["totals"]["total_tokens"] == summary["trimmed_aggregate"]["total_tokens"] + events_sum


def test_get_summary_daily_stats_sorted_ascending_and_capped_at_14_days(isolated_analytics):
    data = TokenTracker._load()
    events = []
    base = datetime.date(2026, 1, 1)
    for i in range(20):
        d = base + datetime.timedelta(days=i)
        events.append({
            "date": d.isoformat(), "model": "m", "task": "t", "provider": "p",
            "total_tokens": 10, "latency_seconds": 0.0, "cost_saved_thb": 0.1,
        })
    data["events"] = events
    TokenTracker._save(data)

    summary = TokenTracker.get_summary()
    daily = summary["daily_stats"]
    assert len(daily) == 14
    # Ascending order, and it's the LAST (most recent) 14 days kept.
    dates = [d["date"] for d in daily]
    assert dates == sorted(dates)
    assert dates[0] == (base + datetime.timedelta(days=6)).isoformat()
    assert dates[-1] == (base + datetime.timedelta(days=19)).isoformat()


def test_get_summary_on_empty_history_has_zeroed_totals_and_no_divide_by_zero(isolated_analytics):
    summary = TokenTracker.get_summary()
    assert summary["totals"]["total_tokens"] == 0
    assert summary["totals"]["avg_latency_seconds"] == 0.0
    assert summary["recent_events"] == []
    assert summary["daily_stats"] == []


# ---------------------------------------------------------------------------
# get_history() -- limit and reversal logic
# ---------------------------------------------------------------------------

def test_get_history_returns_newest_first_respecting_limit(isolated_analytics):
    for i in range(10):
        TokenTracker.record_event(
            task=f"t{i}", model="m", provider="p", input_tokens=1, output_tokens=0,
        )
    history = TokenTracker.get_history(limit=3)
    assert [e["task"] for e in history] == ["t9", "t8", "t7"]


def test_get_history_default_limit_is_50(isolated_analytics):
    for i in range(60):
        TokenTracker.record_event(
            task=f"t{i}", model="m", provider="p", input_tokens=1, output_tokens=0,
        )
    history = TokenTracker.get_history()
    assert len(history) == 50
    assert history[0]["task"] == "t59"


def test_get_history_limit_larger_than_available_returns_all(isolated_analytics):
    TokenTracker.record_event(task="only", model="m", provider="p", input_tokens=1, output_tokens=0)
    history = TokenTracker.get_history(limit=999)
    assert len(history) == 1
    assert history[0]["task"] == "only"


def test_get_history_page_uses_cursor_and_preserves_newest_first_order(isolated_analytics):
    for i in range(5):
        TokenTracker.record_event(
            task=f"t{i}", model="m", provider="p", input_tokens=1, output_tokens=0,
        )

    first = TokenTracker.get_history_page(limit=2)
    assert [event["task"] for event in first["events"]] == ["t4", "t3"]
    assert first["has_more"] is True
    assert first["total"] == 5

    second = TokenTracker.get_history_page(limit=2, before=first["next_cursor"])
    assert [event["task"] for event in second["events"]] == ["t2", "t1"]
    assert second["has_more"] is True


def test_get_history_page_filters_before_applying_cursor(isolated_analytics):
    for task in ("script", "tts", "script", "tts"):
        TokenTracker.record_event(
            task=task, model="m", provider="p", input_tokens=1, output_tokens=0,
        )

    first = TokenTracker.get_history_page(limit=1, task="script")
    assert [event["task"] for event in first["events"]] == ["script"]

    second = TokenTracker.get_history_page(
        limit=1, before=first["next_cursor"], task="script",
    )
    assert [event["task"] for event in second["events"]] == ["script"]


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

def test_reset_clears_events_and_totals(isolated_analytics):
    TokenTracker.record_event(task="a", model="m", provider="p", input_tokens=100, output_tokens=100)
    TokenTracker.reset()

    data = TokenTracker._load()
    assert data["events"] == []
    assert data["totals"]["total_tokens"] == 0
    assert data["totals"]["total_calls"] == 0

    # And get_usage_today reflects the reset, which is what quota.py relies on.
    usage = TokenTracker.get_usage_today()
    assert usage["total_tokens"] == 0


def test_reset_persists_to_disk_not_just_memory(isolated_analytics):
    TokenTracker.record_event(task="a", model="m", provider="p", input_tokens=5, output_tokens=5)
    TokenTracker.reset()

    on_disk = json.loads(isolated_analytics.read_text(encoding="utf-8"))
    assert on_disk["events"] == []
    assert on_disk["totals"]["total_tokens"] == 0


# ---------------------------------------------------------------------------
# Concurrency: record_event() claims to be thread-safe via cls._lock
# ---------------------------------------------------------------------------

def test_concurrent_record_event_calls_do_not_lose_updates(isolated_analytics):
    """Fire many record_event() calls from multiple threads concurrently.
    If the lock/read-modify-write cycle around totals were broken, some
    increments would be lost and totals["total_calls"] would end up less
    than the number of successful calls -- exactly the kind of silent
    undercount that would let the budget cap fail open."""
    N_THREADS = 8
    CALLS_PER_THREAD = 25
    errors = []

    def worker():
        try:
            for _ in range(CALLS_PER_THREAD):
                TokenTracker.record_event(
                    task="concurrent", model="gemini-2.5-flash", provider="gemini_api",
                    input_tokens=1, output_tokens=1,
                )
        except Exception as e:  # pragma: no cover - failure path
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    data = TokenTracker._load()
    expected_calls = N_THREADS * CALLS_PER_THREAD
    assert data["totals"]["total_calls"] == expected_calls
    assert len(data["events"]) == expected_calls
    assert data["totals"]["total_tokens"] == expected_calls * 2


def test_cross_process_record_event_calls_do_not_lose_updates(isolated_analytics):
    """The JSON read-modify-write must be safe across OS processes too."""
    child_code = textwrap.dedent(
        """
        import sys
        from pathlib import Path
        import scripts.token_tracker as tt_module
        from scripts.token_tracker import TokenTracker

        tt_module.ANALYTICS_FILE = Path(sys.argv[1])
        TokenTracker._cache = None
        TokenTracker._cache_stamp = (0, -1)
        for _ in range(int(sys.argv[2])):
            TokenTracker.record_event(
                task="process", model="m", provider="p",
                input_tokens=1, output_tokens=1,
            )
        """
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", child_code, str(isolated_analytics), "20"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    results = [process.communicate(timeout=30) for process in processes]

    for returncode, (stdout, stderr) in zip((p.returncode for p in processes), results):
        assert returncode == 0, f"child failed: stdout={stdout!r} stderr={stderr!r}"

    data = json.loads(isolated_analytics.read_text(encoding="utf-8"))
    assert len(data["events"]) == 40
    assert data["totals"]["total_calls"] == 40
    assert data["totals"]["total_tokens"] == 80
    assert data["daily_usage"][datetime.datetime.now().strftime("%Y-%m-%d")]["calls"] == 40
