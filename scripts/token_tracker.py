"""
Token Tracker Engine
Logs AI token usage, model distribution, latency, and estimated cost savings.
Persists data to 03_Projects/.token_analytics.json.
"""

import os
import sys
import json
import time
import uuid
import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import PROJECTS_DIR

ANALYTICS_FILE = PROJECTS_DIR / ".token_analytics.json"
ANALYTICS_LOCK_SUFFIX = ".lock"

# Commercial API rates for savings estimation (USD per 1M tokens)
# Converted to THB at 35 THB/USD
COMMERCIAL_RATES_USD_PER_1M = {
    "gemini-3.8-flash-high": {"input": 0.15, "output": 0.60},
    "gemini-3.1-pro-high": {"input": 1.25, "output": 5.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-3.1-flash-tts": {"input": 0.15, "output": 1.00},
    "default": {"input": 0.15, "output": 0.60},
}
USD_TO_THB = 35.0


import threading

class TokenTracker:
    """Thread-safe singleton engine for recording and aggregating AI token analytics."""

    _cache: Optional[Dict[str, Any]] = None
    _cache_mtime: float = 0.0  # kept for backward compatibility / introspection
    _cache_stamp: tuple = (0, -1)  # (st_mtime_ns, st_size) -- see _load()
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def _get_default_structure(cls) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "events": [],
            "alerts": [],
            "totals": {
                # Lifetime totals -- must always equal
                # trimmed_aggregate[<field>] + sum(e[<field>] for e in events).
                # See "trimmed_aggregate" below: it absorbs whatever `events`
                # drops on the 1000-event trim so `totals` stays exactly
                # reconstructable from what's actually stored, instead of
                # silently drifting into an unverifiable hand-kept counter.
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "thinking_tokens": 0,
                "total_calls": 0,
                "total_cost_saved_thb": 0.0,
            },
            # Aggregate of exactly the events trimmed off the front of
            # `events` by the 1000-event cap. Kept so `totals` remains
            # auditable: totals[<f>] == trimmed_aggregate[<f>] + sum(events).
            "trimmed_aggregate": {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "thinking_tokens": 0,
                "total_calls": 0,
                "total_cost_saved_thb": 0.0,
            },
            # Per-day lifetime aggregates. Unlike `events`, this map is not
            # subject to the 1,000-event rolling window, so today's quota
            # remains correct after old events are trimmed.
            "daily_usage": {},
        }

    @classmethod
    def _disk_stamp(cls) -> tuple:
        """(st_mtime_ns, st_size) for the analytics file, or (0, -1) if it
        doesn't exist / can't be stat'd.

        Plain st_mtime (float seconds) is not fine-grained enough to trust
        alone: filesystems (Windows/FAT-derived volumes in particular) can
        have coarse mtime resolution, so two writes -- e.g. from the API
        process and a background worker -- can land within the same
        reported mtime tick. A stale cache would then never invalidate,
        which for check_budget()'s pre-flight read is exactly the silent
        under-count the budget gate cannot afford. st_mtime_ns adds
        nanosecond precision, and st_size is a cheap, independent signal --
        content that changed (a new event appended, totals bumped) almost
        always changes the byte length too. Comparing both makes a same-tick
        concurrent write detectable in the realistic case at the cost of a
        single extra stat() field read (stat() is already being called).
        """
        if not ANALYTICS_FILE.exists():
            return (0, -1)
        try:
            st = ANALYTICS_FILE.stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return (0, -1)

    @classmethod
    def _load(cls, force: bool = False) -> Dict[str, Any]:
        # Check if disk file was updated by another process/worker. Any
        # difference (not just "newer") invalidates the cache -- mtime_ns
        # and size are independent signals, not a monotonic ordering, so
        # equality is the only safe "unchanged" test.
        disk_stamp = cls._disk_stamp()

        if not force and cls._cache is not None and disk_stamp == cls._cache_stamp:
            return cls._cache

        if ANALYTICS_FILE.exists():
            try:
                data = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    cls._cache = data
                    cls._cache_stamp = disk_stamp
                    cls._cache_mtime = disk_stamp[0] / 1e9 if disk_stamp[0] else 0.0
                    return data
            except Exception:
                pass

        data = cls._get_default_structure()
        cls._cache = data
        cls._cache_stamp = disk_stamp
        cls._cache_mtime = disk_stamp[0] / 1e9 if disk_stamp[0] else 0.0
        return data

    @classmethod
    @contextmanager
    def _file_lock(cls):
        """Serialize analytics read-modify-write cycles across processes.

        The lock is held on a separate file so the JSON file can continue to
        be replaced atomically. POSIX uses flock(); Windows uses a one-byte
        msvcrt lock. Both locks are released automatically by the OS if a
        process exits unexpectedly, so a stale lock file is harmless.
        """
        lock_path = ANALYTICS_FILE.with_name(ANALYTICS_FILE.name + ANALYTICS_LOCK_SUFFIX)
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        with lock_path.open("a+b") as lock_file:
            if os.name == "nt":
                import msvcrt

                # msvcrt.locking() requires a byte to exist at the position
                # being locked. A concurrent first opener may also create the
                # file; extra initial bytes are harmless because every writer
                # contends on byte zero.
                lock_file.seek(0, os.SEEK_END)
                if lock_file.tell() == 0:
                    lock_file.write(b"\0")
                    lock_file.flush()

                while True:
                    lock_file.seek(0)
                    try:
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.05)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                try:
                    import fcntl
                except ImportError:  # pragma: no cover - unsupported POSIX runtime
                    yield
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @classmethod
    def _save_unlocked(cls, data: Dict[str, Any]) -> None:
        """Write `data` atomically; caller must hold `_file_lock()`."""
        try:
            ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = datetime.datetime.now().isoformat()
            tmp_file = ANALYTICS_FILE.parent / f"{ANALYTICS_FILE.stem}.{os.getpid()}.{threading.get_ident()}.json.tmp"
            try:
                tmp_file.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                tmp_file.replace(ANALYTICS_FILE)
            finally:
                tmp_file.unlink(missing_ok=True)
            cls._cache = data
            cls._cache_stamp = cls._disk_stamp()
            cls._cache_mtime = cls._cache_stamp[0] / 1e9 if cls._cache_stamp[0] else time.time()
        except Exception as e:
            print(f"⚠️ [TokenTracker] Failed to persist analytics: {e}")

    @classmethod
    def _save(cls, data: Dict[str, Any]) -> None:
        """Write `data` atomically, locking when called directly by a reader/test."""
        with cls._file_lock():
            cls._save_unlocked(data)

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _aggregate_events_by_date(cls, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Build daily usage from retained events for schema migration/fallback."""
        daily: Dict[str, Dict[str, Any]] = {}
        events = data.get("events", [])
        if not isinstance(events, list):
            return daily
        for event in events:
            if not isinstance(event, dict):
                continue
            date = event.get("date")
            if not isinstance(date, str) or not date:
                continue
            entry = daily.setdefault(date, {"total_tokens": 0, "cost_thb": 0.0, "calls": 0})
            entry["total_tokens"] += cls._safe_int(event.get("total_tokens", 0))
            entry["cost_thb"] = round(
                entry["cost_thb"] + cls._safe_float(event.get("cost_saved_thb", 0.0)),
                4,
            )
            entry["calls"] += 1
        return daily

    @classmethod
    def _ensure_daily_usage(cls, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Normalise the additive daily ledger and backfill missing dates."""
        daily = data.get("daily_usage")
        if not isinstance(daily, dict):
            daily = {}
            data["daily_usage"] = daily

        for date, entry in list(daily.items()):
            if not isinstance(entry, dict):
                daily.pop(date, None)
                continue
            daily[date] = {
                "total_tokens": cls._safe_int(entry.get("total_tokens", entry.get("tokens", 0))),
                "cost_thb": round(
                    cls._safe_float(entry.get("cost_thb", entry.get("cost_saved_thb", 0.0))),
                    4,
                ),
                "calls": cls._safe_int(entry.get("calls", 0)),
            }

        # Existing analytics files have no daily_usage field. Backfill only
        # dates absent from the new ledger; never add retained events again to
        # an already-tracked date.
        for date, entry in cls._aggregate_events_by_date(data).items():
            daily.setdefault(date, entry)
        return daily

    @classmethod
    def _add_daily_usage(
        cls,
        data: Dict[str, Any],
        date: str,
        total_tokens: int,
        cost_thb: float,
    ) -> None:
        # `_ensure_daily_usage()` is deliberately called before the event is
        # appended. Calling it again after append would backfill the new
        # event and then add it a second time on a legacy/empty file.
        daily = data.get("daily_usage")
        if not isinstance(daily, dict):
            daily = {}
            data["daily_usage"] = daily
        entry = daily.setdefault(date, {"total_tokens": 0, "cost_thb": 0.0, "calls": 0})
        entry["total_tokens"] += cls._safe_int(total_tokens)
        entry["cost_thb"] = round(entry["cost_thb"] + cls._safe_float(cost_thb), 4)
        entry["calls"] += 1

    @classmethod
    def estimate_cost_saved_thb(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0
    ) -> float:
        """Calculate market value saved by using Pro / Free tier."""
        rate = COMMERCIAL_RATES_USD_PER_1M.get(model, COMMERCIAL_RATES_USD_PER_1M["default"])
        in_cost_usd = (input_tokens / 1_000_000.0) * rate["input"]
        out_cost_usd = ((output_tokens + thinking_tokens) / 1_000_000.0) * rate["output"]
        total_usd = in_cost_usd + out_cost_usd
        return round(total_usd * USD_TO_THB, 4)

    @classmethod
    def record_event(
        cls,
        task: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        latency_seconds: float = 0.0,
        thinking_tokens: int = 0,
        project_name: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a single AI execution turn. Thread-safe.
        """
        with cls._lock:
            # The process lock is not enough when the API server and a worker
            # process write the same analytics file. Hold the OS lock from
            # fresh read through atomic replace to prevent lost updates.
            with cls._file_lock():
                data = cls._load(force=True)
                now = datetime.datetime.now()
                input_tokens = int(input_tokens)
                output_tokens = int(output_tokens)
                thinking_tokens = int(thinking_tokens)
                total_tokens = input_tokens + output_tokens + thinking_tokens
                saved_thb = cls.estimate_cost_saved_thb(model, input_tokens, output_tokens, thinking_tokens)

                event = {
                    "id": f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                    "timestamp": now.isoformat(),
                    "date": now.strftime("%Y-%m-%d"),
                    "task": task,
                    "model": model,
                    "provider": provider,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "thinking_tokens": thinking_tokens,
                    "total_tokens": total_tokens,
                    "latency_seconds": round(float(latency_seconds), 2),
                    "cost_saved_thb": saved_thb,
                    "project_name": project_name or "General Studio Task",
                    "metadata": metadata or {}
                }

                # Backfill a legacy file while all of its retained events are
                # still present. This must happen before the 1,000-event trim
                # below, otherwise the first post-migration write could lose
                # the event that is trimmed during that same write.
                cls._ensure_daily_usage(data)

                # Keep max 1,000 historical events to preserve disk and memory.
                # Whatever gets trimmed off the front is folded into
                # trimmed_aggregate so lifetime totals stay auditable.
                events = data.get("events", [])
                if not isinstance(events, list):
                    events = []
                events.append(event)
                if len(events) > 1000:
                    dropped = events[:-1000]
                    events = events[-1000:]
                    trimmed = data.setdefault("trimmed_aggregate", {})
                    trimmed["total_tokens"] = trimmed.get("total_tokens", 0) + sum(
                        cls._safe_int(e.get("total_tokens", 0)) for e in dropped if isinstance(e, dict)
                    )
                    trimmed["input_tokens"] = trimmed.get("input_tokens", 0) + sum(
                        cls._safe_int(e.get("input_tokens", 0)) for e in dropped if isinstance(e, dict)
                    )
                    trimmed["output_tokens"] = trimmed.get("output_tokens", 0) + sum(
                        cls._safe_int(e.get("output_tokens", 0)) for e in dropped if isinstance(e, dict)
                    )
                    trimmed["thinking_tokens"] = trimmed.get("thinking_tokens", 0) + sum(
                        cls._safe_int(e.get("thinking_tokens", 0)) for e in dropped if isinstance(e, dict)
                    )
                    trimmed["total_calls"] = trimmed.get("total_calls", 0) + len(dropped)
                    trimmed["total_cost_saved_thb"] = round(
                        trimmed.get("total_cost_saved_thb", 0.0) + sum(
                            cls._safe_float(e.get("cost_saved_thb", 0.0)) for e in dropped if isinstance(e, dict)
                        ),
                        2,
                    )
                data["events"] = events

                # Daily usage is a separate, compact lifetime ledger. It is
                # deliberately updated before the event-window trim so the
                # quota gate never forgets today's older calls.
                cls._add_daily_usage(data, event["date"], total_tokens, saved_thb)

                # Accumulate totals (lifetime figure; see trimmed_aggregate above)
                totals = data.setdefault("totals", {})
                totals["total_tokens"] = totals.get("total_tokens", 0) + total_tokens
                totals["input_tokens"] = totals.get("input_tokens", 0) + input_tokens
                totals["output_tokens"] = totals.get("output_tokens", 0) + output_tokens
                totals["thinking_tokens"] = totals.get("thinking_tokens", 0) + thinking_tokens
                totals["total_calls"] = totals.get("total_calls", 0) + 1
                totals["total_cost_saved_thb"] = round(totals.get("total_cost_saved_thb", 0.0) + saved_thb, 2)

                cls._save_unlocked(data)
                return event

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """Generate high-level metrics, distribution breakdowns, and recent ledger."""
        with cls._lock:
            data = cls._load()
            events = data.get("events", [])
            totals = data.get("totals", {})

            # Model breakdown
            tokens_by_model = {}
            calls_by_model = {}
            tokens_by_task = {}
            calls_by_task = {}
            calls_by_provider = {}
            daily_stats = {}

            total_latency = 0.0

            for ev in events:
                model = ev.get("model", "unknown")
                task = ev.get("task", "unknown")
                provider = ev.get("provider", "unknown")
                tok = ev.get("total_tokens", 0)
                date = ev.get("date", ev.get("timestamp", "")[:10])
                lat = ev.get("latency_seconds", 0.0)
                thb = ev.get("cost_saved_thb", 0.0)

                total_latency += lat

                tokens_by_model[model] = tokens_by_model.get(model, 0) + tok
                calls_by_model[model] = calls_by_model.get(model, 0) + 1

                tokens_by_task[task] = tokens_by_task.get(task, 0) + tok
                calls_by_task[task] = calls_by_task.get(task, 0) + 1

                calls_by_provider[provider] = calls_by_provider.get(provider, 0) + 1

                if date:
                    d = daily_stats.setdefault(date, {"tokens": 0, "calls": 0, "cost_saved_thb": 0.0})
                    d["tokens"] += tok
                    d["calls"] += 1
                    d["cost_saved_thb"] = round(d["cost_saved_thb"] + thb, 2)

            # Prefer the compact lifetime daily ledger where available. The
            # event-derived values above remain as a backward-compatible
            # fallback for old files and hand-seeded test data.
            stored_daily = data.get("daily_usage")
            if isinstance(stored_daily, dict):
                for date, entry in stored_daily.items():
                    if not isinstance(entry, dict):
                        continue
                    daily_stats[date] = {
                        "tokens": cls._safe_int(entry.get("total_tokens", entry.get("tokens", 0))),
                        "calls": cls._safe_int(entry.get("calls", 0)),
                        "cost_saved_thb": round(
                            cls._safe_float(entry.get("cost_thb", entry.get("cost_saved_thb", 0.0))),
                            2,
                        ),
                    }

            avg_latency = round(total_latency / len(events), 2) if events else 0.0

            # Sort daily stats by date ascending
            sorted_daily = [
                {"date": k, "tokens": v["tokens"], "calls": v["calls"], "cost_saved_thb": v["cost_saved_thb"]}
                for k, v in sorted(daily_stats.items())
            ]
            # Keep last 14 days for clean chart
            sorted_daily = sorted_daily[-14:]

            alerts = data.get("alerts", [])
            recent_alerts = list(reversed(alerts[-20:]))

            # Compute Key Status from configured keys and recent alerts
            key_status = {}
            from scripts.gemini_tts_engine import GeminiFlashTTSEngine
            keys = GeminiFlashTTSEngine.get_api_keys()
            now_dt = datetime.datetime.now()
            for idx, k in enumerate(keys, 1):
                ktag = f"Key #{idx} (..{k[-6:]})"
                status = "healthy"
                last_msg = "พร้อมใช้งานปกติ"
                # Check alerts in last 1 hour
                for alt in recent_alerts:
                    if alt.get("key_tag") == ktag:
                        try:
                            alt_dt = datetime.datetime.fromisoformat(alt.get("timestamp", ""))
                            if (now_dt - alt_dt).total_seconds() < 3600:
                                if alt.get("error_type") == "RATE_LIMIT_429":
                                    status = "rate_limited"
                                    last_msg = alt.get("message", "ติด Rate-Limit 429 ชั่วคราว")
                                elif alt.get("error_type") == "KEY_FAILOVER_SUCCESS" and status != "rate_limited":
                                    status = "healthy"
                                    last_msg = alt.get("message", "พร้อมใช้งานปกติ")
                        except Exception:
                            pass
                key_status[ktag] = {"status": status, "message": last_msg}

            return {
                "totals": {
                    # Lifetime figures. Reconstructable as
                    # trimmed_aggregate[<f>] + sum(e[<f>] for e in events) --
                    # never a number the stored data can't verify. See
                    # data["trimmed_aggregate"], surfaced below for audit.
                    "total_tokens": totals.get("total_tokens", 0),
                    "input_tokens": totals.get("input_tokens", 0),
                    "output_tokens": totals.get("output_tokens", 0),
                    "thinking_tokens": totals.get("thinking_tokens", 0),
                    "total_calls": totals.get("total_calls", 0),
                    "total_cost_saved_thb": round(totals.get("total_cost_saved_thb", 0.0), 2),
                    "avg_latency_seconds": avg_latency,
                },
                # Aggregate of events trimmed off the retained 1000-event
                # window. Not read by the current dashboard; present so
                # totals["total_tokens"] etc. can be audited/reconstructed as
                # trimmed_aggregate + sum(events) instead of trusted blindly.
                "trimmed_aggregate": data.get("trimmed_aggregate", {}),
                "daily_usage": data.get("daily_usage", {}),
                "tokens_by_model": tokens_by_model,
                "calls_by_model": calls_by_model,
                "tokens_by_task": tokens_by_task,
                "calls_by_task": calls_by_task,
                "calls_by_provider": calls_by_provider,
                "daily_stats": sorted_daily,
                "recent_events": list(reversed(events[-50:])),  # Latest 50 events
                "alerts": recent_alerts,
                "key_status": key_status
            }

    @classmethod
    def record_alert(
        cls,
        task: str,
        model: str,
        key_tag: str,
        error_type: str,
        message: str,
        level: str = "warning",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an alert (e.g. 429 Rate-limit, failover, quota warning)."""
        with cls._lock:
            with cls._file_lock():
                data = cls._load(force=True)
                now = datetime.datetime.now()
                alert = {
                    "id": f"alt_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                    "timestamp": now.isoformat(),
                    "task": task,
                    "model": model,
                    "key_tag": key_tag,
                    "error_type": error_type,
                    "level": level,
                    "message": message,
                    "metadata": metadata or {}
                }
                alerts = data.setdefault("alerts", [])
                alerts.append(alert)
                if len(alerts) > 50:
                    data["alerts"] = alerts[-50:]
                cls._save_unlocked(data)
                return alert

    @classmethod
    def get_alerts(cls, limit: int = 20) -> List[Dict[str, Any]]:
        """Return chronological alerts (newest first)."""
        with cls._lock:
            data = cls._load()
            alerts = data.get("alerts", [])
            return list(reversed(alerts[-limit:]))

    @classmethod
    def clear_alerts(cls) -> None:
        """Clear all alerts."""
        with cls._lock:
            with cls._file_lock():
                data = cls._load(force=True)
                data["alerts"] = []
                cls._save_unlocked(data)

    @classmethod
    def get_history(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Return chronological history (newest first)."""
        with cls._lock:
            data = cls._load()
            events = data.get("events", [])
            return list(reversed(events[-limit:]))

    @classmethod
    def get_history_page(
        cls,
        limit: int = 50,
        before: Optional[str] = None,
        task: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a cursor-paginated token history page.

        The cursor is the id of the oldest event returned by the previous
        page. Filtering happens before cursor lookup so changing a filter
        cannot accidentally skip matching events.
        """
        with cls._lock:
            data = cls._load()
            events = list(reversed(data.get("events", [])))
            normalized_task = task.strip().lower() if task else ""
            normalized_query = query.strip().lower() if query else ""

            if normalized_task and normalized_task != "all":
                events = [
                    event for event in events
                    if str(event.get("task", "")).lower() == normalized_task
                ]

            if normalized_query:
                events = [
                    event for event in events
                    if normalized_query in " ".join(
                        str(event.get(field, ""))
                        for field in ("task", "model", "project_name")
                    ).lower()
                ]

            if before:
                cursor_index = next(
                    (index for index, event in enumerate(events)
                     if str(event.get("id", "")) == before),
                    None,
                )
                if cursor_index is None:
                    return {"events": [], "has_more": False, "next_cursor": None, "total": len(events)}
                events = events[cursor_index + 1:]

            page = events[:limit]
            has_more = len(events) > len(page)
            next_cursor = str(page[-1].get("id")) if has_more and page else None
            return {
                "events": page,
                "has_more": has_more,
                "next_cursor": next_cursor,
                "total": len(events) if not before else None,
            }

    @classmethod
    def reset(cls) -> None:
        """Reset all analytics."""
        with cls._lock:
            with cls._file_lock():
                new_data = cls._get_default_structure()
                cls._save_unlocked(new_data)

    @classmethod
    def get_usage_today(cls) -> Dict[str, Any]:
        """Sum tokens and commercial-equivalent cost for events dated today.

        Used by scripts/quota.py as the pre-flight budget check. Today is
        computed from local wall-clock date, same as record_event()'s
        `date` field, so this stays consistent with what get_summary()'s
        daily_stats already show.
        """
        with cls._lock:
            # Quota reads must not use a stale cache while another process is
            # appending an event. The short shared-file critical section also
            # makes the check observe a complete JSON snapshot.
            with cls._file_lock():
                data = cls._load(force=True)
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                daily = data.get("daily_usage")
                entry = daily.get(today) if isinstance(daily, dict) else None

                # Legacy files have no daily_usage. Fall back to their
                # retained events; once a new event is written, the ledger is
                # backfilled and remains independent of the 1,000-event cap.
                if isinstance(entry, dict):
                    total_tokens = cls._safe_int(entry.get("total_tokens", entry.get("tokens", 0)))
                    cost_thb = cls._safe_float(entry.get("cost_thb", entry.get("cost_saved_thb", 0.0)))
                    calls = cls._safe_int(entry.get("calls", 0))
                else:
                    usage = cls._aggregate_events_by_date(data).get(
                        today,
                        {"total_tokens": 0, "cost_thb": 0.0, "calls": 0},
                    )
                    total_tokens = usage["total_tokens"]
                    cost_thb = usage["cost_thb"]
                    calls = usage["calls"]

                return {
                    "date": today,
                    "total_tokens": total_tokens,
                    "cost_thb": round(cost_thb, 4),
                    "calls": calls,
                }
