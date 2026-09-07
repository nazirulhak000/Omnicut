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
from pathlib import Path
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import PROJECTS_DIR

ANALYTICS_FILE = PROJECTS_DIR / ".token_analytics.json"

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
            }
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
    def _load(cls) -> Dict[str, Any]:
        # Check if disk file was updated by another process/worker. Any
        # difference (not just "newer") invalidates the cache -- mtime_ns
        # and size are independent signals, not a monotonic ordering, so
        # equality is the only safe "unchanged" test.
        disk_stamp = cls._disk_stamp()

        if cls._cache is not None and disk_stamp == cls._cache_stamp:
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
    def _save(cls, data: Dict[str, Any]) -> None:
        try:
            ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = datetime.datetime.now().isoformat()
            tmp_file = ANALYTICS_FILE.with_suffix(".json.tmp")
            tmp_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            tmp_file.replace(ANALYTICS_FILE)
            cls._cache = data
            cls._cache_stamp = cls._disk_stamp()
            cls._cache_mtime = cls._cache_stamp[0] / 1e9 if cls._cache_stamp[0] else time.time()
        except Exception as e:
            print(f"⚠️ [TokenTracker] Failed to persist analytics: {e}")

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
            data = cls._load()
            now = datetime.datetime.now()
            total_tokens = input_tokens + output_tokens + thinking_tokens
            saved_thb = cls.estimate_cost_saved_thb(model, input_tokens, output_tokens, thinking_tokens)

            event = {
                "id": f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                "timestamp": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "task": task,
                "model": model,
                "provider": provider,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "thinking_tokens": int(thinking_tokens),
                "total_tokens": int(total_tokens),
                "latency_seconds": round(float(latency_seconds), 2),
                "cost_saved_thb": saved_thb,
                "project_name": project_name or "General Studio Task",
                "metadata": metadata or {}
            }

            # Keep max 1,000 historical events to preserve disk and memory.
            # Whatever gets trimmed off the front is folded into
            # trimmed_aggregate so `totals` (lifetime) stays exactly equal to
            # trimmed_aggregate + sum(events) -- never a number the stored
            # data can no longer reconstruct or verify.
            events = data.get("events", [])
            events.append(event)
            if len(events) > 1000:
                dropped = events[:-1000]
                events = events[-1000:]
                trimmed = data.setdefault("trimmed_aggregate", {})
                trimmed["total_tokens"] = trimmed.get("total_tokens", 0) + sum(e.get("total_tokens", 0) for e in dropped)
                trimmed["input_tokens"] = trimmed.get("input_tokens", 0) + sum(e.get("input_tokens", 0) for e in dropped)
                trimmed["output_tokens"] = trimmed.get("output_tokens", 0) + sum(e.get("output_tokens", 0) for e in dropped)
                trimmed["thinking_tokens"] = trimmed.get("thinking_tokens", 0) + sum(e.get("thinking_tokens", 0) for e in dropped)
                trimmed["total_calls"] = trimmed.get("total_calls", 0) + len(dropped)
                trimmed["total_cost_saved_thb"] = round(
                    trimmed.get("total_cost_saved_thb", 0.0) + sum(e.get("cost_saved_thb", 0.0) for e in dropped), 2
                )
            data["events"] = events

            # Accumulate totals (lifetime figure; see trimmed_aggregate above)
            totals = data.setdefault("totals", {})
            totals["total_tokens"] = totals.get("total_tokens", 0) + total_tokens
            totals["input_tokens"] = totals.get("input_tokens", 0) + input_tokens
            totals["output_tokens"] = totals.get("output_tokens", 0) + output_tokens
            totals["thinking_tokens"] = totals.get("thinking_tokens", 0) + thinking_tokens
            totals["total_calls"] = totals.get("total_calls", 0) + 1
            totals["total_cost_saved_thb"] = round(totals.get("total_cost_saved_thb", 0.0) + saved_thb, 2)

            cls._save(data)
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

            avg_latency = round(total_latency / len(events), 2) if events else 0.0

            # Sort daily stats by date ascending
            sorted_daily = [
                {"date": k, "tokens": v["tokens"], "calls": v["calls"], "cost_saved_thb": v["cost_saved_thb"]}
                for k, v in sorted(daily_stats.items())
            ]
            # Keep last 14 days for clean chart
            sorted_daily = sorted_daily[-14:]

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
                "tokens_by_model": tokens_by_model,
                "calls_by_model": calls_by_model,
                "tokens_by_task": tokens_by_task,
                "calls_by_task": calls_by_task,
                "calls_by_provider": calls_by_provider,
                "daily_stats": sorted_daily,
                "recent_events": list(reversed(events[-50:]))  # Latest 50 events
            }

    @classmethod
    def get_history(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Return chronological history (newest first)."""
        with cls._lock:
            data = cls._load()
            events = data.get("events", [])
            return list(reversed(events[-limit:]))

    @classmethod
    def reset(cls) -> None:
        """Reset all analytics."""
        with cls._lock:
            new_data = cls._get_default_structure()
            cls._save(new_data)

    @classmethod
    def get_usage_today(cls) -> Dict[str, Any]:
        """Sum tokens and commercial-equivalent cost for events dated today.

        Used by scripts/quota.py as the pre-flight budget check. Today is
        computed from local wall-clock date, same as record_event()'s
        `date` field, so this stays consistent with what get_summary()'s
        daily_stats already show.
        """
        with cls._lock:
            data = cls._load()
            events = data.get("events", [])
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            total_tokens = 0
            cost_thb = 0.0
            calls = 0
            for ev in events:
                if ev.get("date") != today:
                    continue
                total_tokens += ev.get("total_tokens", 0)
                cost_thb += ev.get("cost_saved_thb", 0.0)
                calls += 1
            return {
                "date": today,
                "total_tokens": total_tokens,
                "cost_thb": round(cost_thb, 4),
                "calls": calls,
            }
