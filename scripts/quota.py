"""
Pre-flight budget check for paid AI/TTS calls.

scripts/token_tracker.py records usage AFTER every call succeeds -- it has
never enforced a limit. This module adds the missing pre-flight check,
called immediately before the network call at each of the 3 places usage
gets recorded:

- scripts/ai_bridge.py (Antigravity CLI + Google AI Studio text generation)
- scripts/gemini_tts_engine.py (Gemini Flash TTS)
- scripts/gemini_vision_matcher.py (Gemini Vision scene matching)

Scope note: this is daily, process-local, single-shared-budget enforcement
-- not per-tenant. Per-tenant budgets are a P2 multi-tenancy concern (see
_Docs/SAAS_READINESS_PLAN.md item 19) that requires a tenant_id to key on,
which does not exist yet.

Race note: check-then-call is NOT atomic. Two concurrent requests can both
call check_budget() and both see "under budget" before either one's
record_event() lands, so a burst of concurrent calls can overshoot the
limit by roughly (concurrency count) worth of usage. This is a known,
accepted gap for a single local user clicking one button at a time --
building a real reservation/debit system (reserve estimated tokens before
the call, reconcile after) is out of scope for this pass. Worth revisiting
if/when this becomes multi-tenant with real concurrent traffic.
"""

import os
from pathlib import Path
from typing import Optional

from scripts.error_handler import AppError, ErrorCategory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def _load_env_file() -> None:
    """Same manual .env convention as ai_bridge.py / gemini_tts_engine.py."""
    if not ENV_FILE.exists():
        return
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

# Defaults are generous on purpose -- this is a safety net against a runaway
# loop or a script gone wrong, not a tight cost control. 0 (or unset/blank)
# disables that particular cap entirely.
DEFAULT_DAILY_TOKEN_LIMIT = 5_000_000
DEFAULT_DAILY_COST_THB_LIMIT = 500.0


def _read_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        val = int(float(raw))
    except ValueError:
        return default
    return val


def _read_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def get_daily_token_limit() -> int:
    """0 means disabled. Re-read each call so tests/env changes take effect."""
    return _read_int_env("DAILY_TOKEN_LIMIT", DEFAULT_DAILY_TOKEN_LIMIT)


def get_daily_cost_thb_limit() -> float:
    """0 means disabled."""
    return _read_float_env("DAILY_COST_THB_LIMIT", DEFAULT_DAILY_COST_THB_LIMIT)


def _quota_error(reason: str, usage: dict, limit_desc: str) -> AppError:
    return AppError(
        category=ErrorCategory.AI_PROVIDER,
        code="AI_QUOTA_EXCEEDED",
        message_th="เกินโควต้าการใช้งาน AI ที่ตั้งไว้ต่อวันแล้ว",
        suggestion_th=(
            f"{reason} วันนี้ใช้ไปแล้ว {usage.get('total_tokens', 0):,} tokens "
            f"(~{usage.get('cost_thb', 0):.2f} บาทเทียบเท่าราคาตลาด) เกิน {limit_desc}. "
            "รอถึงวันถัดไป หรือปรับค่า DAILY_TOKEN_LIMIT / DAILY_COST_THB_LIMIT ใน .env"
        ),
        details=f"quota_exceeded: {reason}",
    )


def check_budget(task: str = "") -> None:
    """Raise AppError(AI_QUOTA_EXCEEDED) if today's usage is already over
    either configured cap. Call this immediately before the paid network
    call, never after -- and never inside a cache-hit path (a cache hit
    costs nothing and must not consume quota).

    No-op (never raises) when both limits are 0/disabled.
    """
    token_limit = get_daily_token_limit()
    cost_limit = get_daily_cost_thb_limit()
    if token_limit <= 0 and cost_limit <= 0:
        return

    # Imported lazily to avoid a hard import-time dependency loop between
    # token_tracker and quota for callers that only need one of the two.
    from scripts.token_tracker import TokenTracker
    usage = TokenTracker.get_usage_today()

    if token_limit > 0 and usage.get("total_tokens", 0) >= token_limit:
        raise _quota_error(
            f"โควต้า token ต่อวัน ({token_limit:,} tokens) เต็มแล้ว ({task or 'AI call'} ถูกระงับ).",
            usage,
            f"{token_limit:,} tokens/วัน",
        )

    if cost_limit > 0 and usage.get("cost_thb", 0.0) >= cost_limit:
        raise _quota_error(
            f"โควต้าค่าใช้จ่ายเทียบเท่าต่อวัน ({cost_limit:.2f} บาท) เต็มแล้ว ({task or 'AI call'} ถูกระงับ).",
            usage,
            f"{cost_limit:.2f} บาท/วัน",
        )
