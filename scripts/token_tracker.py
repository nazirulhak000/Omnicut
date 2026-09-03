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
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def _get_default_structure(cls) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "events": [],
            "totals": {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "thinking_tokens": 0,
                "total_calls": 0,
                "total_cost_saved_thb": 0.0,
            }
        }

    @classmethod
    def _load(cls) -> Dict[str, Any]:
        if cls._cache is not None:
            return cls._cache
        if ANALYTICS_FILE.exists():
            try:
                data = json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
                cls._cache = data
                return data
            except Exception:
                pass
        data = cls._get_default_structure()
        cls._cache = data
        return data

    @classmethod
    def _save(cls, data: Dict[str, Any]) -> None:
        try:
            ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = datetime.datetime.now().isoformat()
            ANALYTICS_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            cls._cache = data
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

            # Keep max 1,000 historical events to preserve disk and memory
            events = data.get("events", [])
            events.append(event)
            if len(events) > 1000:
                events = events[-1000:]
            data["events"] = events

            # Accumulate totals
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
                "total_tokens": totals.get("total_tokens", 0),
                "input_tokens": totals.get("input_tokens", 0),
                "output_tokens": totals.get("output_tokens", 0),
                "thinking_tokens": totals.get("thinking_tokens", 0),
                "total_calls": totals.get("total_calls", 0),
                "total_cost_saved_thb": round(totals.get("total_cost_saved_thb", 0.0), 2),
                "avg_latency_seconds": avg_latency,
            },
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
        data = cls._load()
        events = data.get("events", [])
        return list(reversed(events[-limit:]))

    @classmethod
    def reset(cls) -> None:
        """Reset all analytics."""
        new_data = cls._get_default_structure()
        cls._save(new_data)
