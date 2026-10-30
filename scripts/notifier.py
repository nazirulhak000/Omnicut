"""
Mobile push notification helper for OmniCut Pro Studio (Phase 5.5).

Supports:
1. Primary: LINE Messaging API (`LINE_CHANNEL_ACCESS_TOKEN` + `LINE_USER_ID`)
2. Fallback: Telegram Bot API (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`)

Key guarantees:
- Deep links open directly to the mobile view (`/?mode=mobile&tab=...`).
- Batch coalescing: only 1 notification is sent per `(job_id, event_type)` for
  batch completion or checkpoint events.
- Failure rate-limiting: error/failure notifications are throttled to at most
  1 message per 10 minutes (`600s` window) per `(product_code, job_id)` key.
- Graceful degradation: when no credentials are configured, logs cleanly and
  returns `{"sent": False, "reason": "not_configured"}` without raising.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Mapping, Optional, Set, Tuple

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
TELEGRAM_API_BASE = "https://api.telegram.org"
FAILURE_RATE_LIMIT_SECONDS = 600.0  # 10 minutes

_FAILURE_EVENT_TYPES = frozenset({
    "failure",
    "failed",
    "error",
    "batch_failed",
    "render_failed",
    "tts_failed",
})


def build_deep_link(
    public_origin: str,
    tab: str = "today",
    job_id: Optional[str] = None,
    queue_id: Optional[str] = None,
) -> str:
    """
    Builds a clean mobile deep link: `https://.../?mode=mobile&tab=...`
    Preserves optional `job` and `queue` query parameters.
    """
    origin = str(public_origin or "").strip().rstrip("/")
    clean_tab = str(tab or "today").strip() or "today"

    params: list[Tuple[str, str]] = [
        ("mode", "mobile"),
        ("tab", clean_tab),
    ]
    if job_id is not None and str(job_id).strip():
        params.append(("job", str(job_id).strip()))
    if queue_id is not None and str(queue_id).strip():
        params.append(("queue", str(queue_id).strip()))

    query = urllib.parse.urlencode(params)
    if not origin:
        return f"/?{query}"
    return f"{origin}/?{query}"


def _is_failure_event(event_type: str) -> bool:
    norm = str(event_type or "").strip().lower()
    if norm in _FAILURE_EVENT_TYPES:
        return True
    return norm.startswith(("fail", "error", "err_"))


def _format_event_header(event_type: str, product_code: str) -> str:
    norm = str(event_type or "").strip().lower()
    prod = str(product_code or "").strip() or "OmniCut"
    if _is_failure_event(norm):
        return f"⚠️ [{prod}] แจ้งเตือนข้อผิดพลาด"
    if "checkpoint" in norm or "approval" in norm or "review" in norm:
        return f"🔔 [{prod}] รอตรวจอนุมัติบนมือถือ"
    if "complete" in norm or "done" in norm or "finish" in norm or "ready" in norm:
        return f"✅ [{prod}] งานผลิตเสร็จสมบูรณ์"
    return f"📱 [{prod}] อัปเดตสถานะ ({event_type})"


class Notifier:
    """Stateful notification dispatcher with batch coalescing and failure rate-limiting."""

    def __init__(
        self,
        *,
        rate_limit_seconds: float = FAILURE_RATE_LIMIT_SECONDS,
        clock: Callable[[], float] = time.time,
        urlopen: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self.rate_limit_seconds = float(rate_limit_seconds)
        self._clock = clock
        self._urlopen = urlopen
        self._lock = threading.Lock()
        self._coalesced_events: Set[Tuple[str, str]] = set()
        self._failure_timestamps: Dict[Tuple[str, str], float] = {}

    def reset(self) -> None:
        """Clears coalescing and rate-limit memory (primarily for deterministic tests)."""
        with self._lock:
            self._coalesced_events.clear()
            self._failure_timestamps.clear()

    def _failure_key(self, product_code: Optional[str], job_id: Optional[str]) -> Tuple[str, str]:
        prod = str(product_code or "").strip().upper()
        jid = str(job_id or "").strip()
        return (prod, jid)

    def _send_line(
        self,
        token: str,
        user_id: str,
        text: str,
        *,
        urlopen: Callable[..., Any],
    ) -> Dict[str, Any]:
        payload = json.dumps(
            {
                "to": user_id,
                "messages": [{"type": "text", "text": text}],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            LINE_PUSH_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        with urlopen(req, timeout=10) as resp:
            status = getattr(resp, "status", 200)
            return {
                "sent": 200 <= int(status) < 300,
                "provider": "line",
                "status_code": int(status),
            }

    def _send_telegram(
        self,
        bot_token: str,
        chat_id: str,
        text: str,
        *,
        urlopen: Callable[..., Any],
    ) -> Dict[str, Any]:
        url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10) as resp:
            status = getattr(resp, "status", 200)
            return {
                "sent": 200 <= int(status) < 300,
                "provider": "telegram",
                "status_code": int(status),
            }

    def _dispatch_message(
        self,
        text: str,
        *,
        env: Mapping[str, str],
        urlopen: Callable[..., Any],
    ) -> Dict[str, Any]:
        line_token = str(env.get("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
        line_user = str(env.get("LINE_USER_ID") or "").strip()
        tg_token = str(env.get("TELEGRAM_BOT_TOKEN") or "").strip()
        tg_chat = str(env.get("TELEGRAM_CHAT_ID") or "").strip()

        if not (line_token and line_user) and not (tg_token and tg_chat):
            logger.info("[notifier] Push notification skipped (no LINE or Telegram token configured).")
            return {"sent": False, "reason": "not_configured"}

        last_error: Optional[str] = None
        if line_token and line_user:
            try:
                res = self._send_line(line_token, line_user, text, urlopen=urlopen)
                if res.get("sent"):
                    return res
                last_error = f"line_status_{res.get('status_code')}"
            except Exception as exc:
                last_error = str(exc)
                logger.warning("[notifier] LINE push failed: %s", exc)

        if tg_token and tg_chat:
            try:
                res = self._send_telegram(tg_token, tg_chat, text, urlopen=urlopen)
                if res.get("sent"):
                    return res
                last_error = f"telegram_status_{res.get('status_code')}"
            except Exception as exc:
                last_error = str(exc)
                logger.warning("[notifier] Telegram push failed: %s", exc)

        return {
            "sent": False,
            "reason": "send_error",
            "error": last_error or "unknown_error",
        }

    def notify_batch_event(
        self,
        event_type: str,
        product_code: str,
        job_id: str,
        summary: str,
        public_origin: str = "",
        *,
        tab: str = "today",
        queue_id: Optional[str] = None,
        now: Optional[float] = None,
        env: Optional[Mapping[str, str]] = None,
        urlopen: Optional[Callable[..., Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends a push notification for a batch event or error.
        - Non-failure events are coalesced per `(job_id, event_type)`.
        - Failure/error events are rate-limited to 1 per `rate_limit_seconds` (600s)
          per `(product_code, job_id)`.
        """
        effective_env = env if env is not None else os.environ
        effective_urlopen = urlopen if urlopen is not None else self._urlopen
        current_time = float(now) if now is not None else float(self._clock())

        norm_event = str(event_type or "update").strip().lower()
        clean_job_id = str(job_id or "").strip()
        clean_product = str(product_code or "").strip()
        is_failure = _is_failure_event(norm_event)

        deep_link = build_deep_link(
            public_origin=public_origin,
            tab=tab,
            job_id=clean_job_id or None,
            queue_id=queue_id,
        )
        header = _format_event_header(norm_event, clean_product)
        body_lines = [header]
        if summary and str(summary).strip():
            body_lines.append(str(summary).strip())
        body_lines.append(f"เปิดดูงาน: {deep_link}")
        message_text = "\n".join(body_lines)

        with self._lock:
            if is_failure:
                fkey = self._failure_key(clean_product, clean_job_id)
                # Also check product-level rate limit if product_code is present
                prod_only_key = (fkey[0], "")
                last_sent = max(
                    self._failure_timestamps.get(fkey, -1e12),
                    self._failure_timestamps.get(prod_only_key, -1e12) if fkey[0] else -1e12,
                )
                elapsed = current_time - last_sent
                if elapsed < self.rate_limit_seconds:
                    retry_after = round(self.rate_limit_seconds - elapsed, 2)
                    logger.info(
                        "[notifier] Failure notification rate-limited for %s (retry_after=%.1fs)",
                        fkey,
                        retry_after,
                    )
                    return {
                        "sent": False,
                        "reason": "rate_limited",
                        "retry_after": retry_after,
                        "deep_link": deep_link,
                    }
            else:
                coalesce_key = (clean_job_id, norm_event)
                if clean_job_id and coalesce_key in self._coalesced_events:
                    logger.info(
                        "[notifier] Coalesced duplicate batch event (%s, %s)",
                        clean_job_id,
                        norm_event,
                    )
                    return {
                        "sent": False,
                        "reason": "coalesced",
                        "job_id": clean_job_id,
                        "event_type": norm_event,
                        "deep_link": deep_link,
                    }

        result = self._dispatch_message(
            message_text,
            env=effective_env,
            urlopen=effective_urlopen,
        )
        result["deep_link"] = deep_link
        result["message"] = message_text

        if result.get("sent"):
            with self._lock:
                if is_failure:
                    fkey = self._failure_key(clean_product, clean_job_id)
                    self._failure_timestamps[fkey] = current_time
                    if fkey[0]:
                        self._failure_timestamps[(fkey[0], "")] = current_time
                elif clean_job_id:
                    self._coalesced_events.add((clean_job_id, norm_event))

        return result

    def notify_failure(
        self,
        product_code: str,
        job_id: Optional[str] = None,
        summary: str = "",
        public_origin: str = "",
        *,
        now: Optional[float] = None,
        env: Optional[Mapping[str, str]] = None,
        urlopen: Optional[Callable[..., Any]] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper for rate-limited error/failure notifications."""
        return self.notify_batch_event(
            event_type="failure",
            product_code=product_code,
            job_id=job_id or "",
            summary=summary,
            public_origin=public_origin,
            now=now,
            env=env,
            urlopen=urlopen,
        )


_DEFAULT_NOTIFIER = Notifier()


def notify_batch_event(
    event_type: str,
    product_code: str,
    job_id: str,
    summary: str,
    public_origin: str = "",
    *,
    tab: str = "today",
    queue_id: Optional[str] = None,
    now: Optional[float] = None,
    env: Optional[Mapping[str, str]] = None,
    urlopen: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Module-level entry point for batch/checkpoint/failure push notifications."""
    return _DEFAULT_NOTIFIER.notify_batch_event(
        event_type=event_type,
        product_code=product_code,
        job_id=job_id,
        summary=summary,
        public_origin=public_origin,
        tab=tab,
        queue_id=queue_id,
        now=now,
        env=env,
        urlopen=urlopen,
    )


def notify_failure(
    product_code: str,
    job_id: Optional[str] = None,
    summary: str = "",
    public_origin: str = "",
    *,
    now: Optional[float] = None,
    env: Optional[Mapping[str, str]] = None,
    urlopen: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """Module-level entry point for rate-limited error/failure push notifications."""
    return _DEFAULT_NOTIFIER.notify_failure(
        product_code=product_code,
        job_id=job_id,
        summary=summary,
        public_origin=public_origin,
        now=now,
        env=env,
        urlopen=urlopen,
    )


def reset_notifier_state() -> None:
    """Resets the module-level notifier state (used in unit tests)."""
    _DEFAULT_NOTIFIER.reset()
