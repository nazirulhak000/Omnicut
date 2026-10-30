"""
Unit tests for scripts/notifier.py (Phase 5.5 — LINE Messaging API & Telegram Push Notifier).

Offline & deterministic: uses fake urlopen and explicit env/clock parameters.
"""

from __future__ import annotations

import json
import pytest

from scripts.notifier import (
    FAILURE_RATE_LIMIT_SECONDS,
    LINE_PUSH_URL,
    Notifier,
    build_deep_link,
    notify_batch_event,
    notify_failure,
    reset_notifier_state,
)


class _FakeResponse:
    def __init__(self, status: int = 200, body: bytes = b"{}") -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture(autouse=True)
def _clean_notifier_state():
    reset_notifier_state()
    yield
    reset_notifier_state()


def test_build_deep_link_formats_clean_mobile_url():
    assert (
        build_deep_link("https://studio.example.com/", tab="today", job_id="job_123")
        == "https://studio.example.com/?mode=mobile&tab=today&job=job_123"
    )
    assert (
        build_deep_link("https://studio.example.com", tab="review", job_id="job_99", queue_id="q_42")
        == "https://studio.example.com/?mode=mobile&tab=review&job=job_99&queue=q_42"
    )
    assert (
        build_deep_link("", tab="today", job_id="job_1")
        == "/?mode=mobile&tab=today&job=job_1"
    )


def test_unconfigured_graceful_degradation():
    calls = []

    def fake_urlopen(req, timeout=10):
        calls.append(req)
        return _FakeResponse(200)

    res = notify_batch_event(
        event_type="completed",
        product_code="TTZ01",
        job_id="job_001",
        summary="20/20 คลิปเสร็จแล้ว",
        public_origin="https://studio.example.com",
        env={},
        urlopen=fake_urlopen,
    )
    assert res["sent"] is False
    assert res["reason"] == "not_configured"
    assert res["deep_link"] == "https://studio.example.com/?mode=mobile&tab=today&job=job_001"
    assert len(calls) == 0


def test_line_push_sends_expected_payload_and_headers():
    captured = []

    def fake_urlopen(req, timeout=10):
        captured.append(req)
        return _FakeResponse(200)

    env = {
        "LINE_CHANNEL_ACCESS_TOKEN": "line_secret_token_abc",
        "LINE_USER_ID": "U1234567890abcdef",
    }
    res = notify_batch_event(
        event_type="checkpoint",
        product_code="TTZ01",
        job_id="job_abc",
        summary="คลิปแรกพร้อมตรวจแล้ว",
        public_origin="https://studio.example.com",
        env=env,
        urlopen=fake_urlopen,
    )
    assert res["sent"] is True
    assert res["provider"] == "line"
    assert len(captured) == 1

    req = captured[0]
    assert req.full_url == LINE_PUSH_URL
    assert req.headers.get("Authorization") == "Bearer line_secret_token_abc"
    body = json.loads(req.data.decode("utf-8"))
    assert body["to"] == "U1234567890abcdef"
    assert len(body["messages"]) == 1
    text = body["messages"][0]["text"]
    assert "TTZ01" in text
    assert "คลิปแรกพร้อมตรวจแล้ว" in text
    assert "https://studio.example.com/?mode=mobile&tab=today&job=job_abc" in text


def test_batch_coalescing_sends_only_once_per_job_and_event_type():
    captured = []

    def fake_urlopen(req, timeout=10):
        captured.append(req)
        return _FakeResponse(200)

    env = {
        "LINE_CHANNEL_ACCESS_TOKEN": "token_1",
        "LINE_USER_ID": "user_1",
    }

    first = notify_batch_event(
        event_type="completed",
        product_code="TTZ01",
        job_id="job_batch_1",
        summary="เสร็จ 20/20 คลิป",
        public_origin="https://studio.example.com",
        env=env,
        urlopen=fake_urlopen,
    )
    second = notify_batch_event(
        event_type="completed",
        product_code="TTZ01",
        job_id="job_batch_1",
        summary="เสร็จ 20/20 คลิป (ซ้ำ)",
        public_origin="https://studio.example.com",
        env=env,
        urlopen=fake_urlopen,
    )
    # Different event_type on same job_id is allowed once
    checkpoint = notify_batch_event(
        event_type="checkpoint",
        product_code="TTZ01",
        job_id="job_batch_1",
        summary="รอตรวจคลิปที่ 1",
        public_origin="https://studio.example.com",
        env=env,
        urlopen=fake_urlopen,
    )

    assert first["sent"] is True
    assert second["sent"] is False
    assert second["reason"] == "coalesced"
    assert checkpoint["sent"] is True
    assert len(captured) == 2


def test_failure_rate_limiting_600s_window():
    captured = []

    def fake_urlopen(req, timeout=10):
        captured.append(req)
        return _FakeResponse(200)

    env = {
        "LINE_CHANNEL_ACCESS_TOKEN": "token_1",
        "LINE_USER_ID": "user_1",
    }
    notifier = Notifier(rate_limit_seconds=FAILURE_RATE_LIMIT_SECONDS, urlopen=fake_urlopen)

    # First failure at t=1000s -> sent
    r1 = notifier.notify_failure(
        product_code="TTZ01",
        job_id="job_f1",
        summary="TTS quota 429",
        public_origin="https://studio.example.com",
        now=1000.0,
        env=env,
    )
    assert r1["sent"] is True
    assert len(captured) == 1

    # Second failure 120s later (t=1120s < 1600s) -> rate_limited
    r2 = notifier.notify_batch_event(
        event_type="error",
        product_code="TTZ01",
        job_id="job_f1",
        summary="TTS quota 429 retry",
        public_origin="https://studio.example.com",
        now=1120.0,
        env=env,
    )
    assert r2["sent"] is False
    assert r2["reason"] == "rate_limited"
    assert r2["retry_after"] == pytest.approx(480.0)
    assert len(captured) == 1

    # Different product at t=1150s -> not blocked by TTZ01's rate limit
    r_other = notifier.notify_failure(
        product_code="HAT01",
        job_id="job_f2",
        summary="FFmpeg timeout",
        public_origin="https://studio.example.com",
        now=1150.0,
        env=env,
    )
    assert r_other["sent"] is True
    assert len(captured) == 2

    # After 600s window expires for TTZ01 (t=1601s) -> sent again
    r3 = notifier.notify_failure(
        product_code="TTZ01",
        job_id="job_f1",
        summary="New failure after 10 minutes",
        public_origin="https://studio.example.com",
        now=1601.0,
        env=env,
    )
    assert r3["sent"] is True
    assert len(captured) == 3


def test_telegram_fallback_when_line_unconfigured_or_fails():
    captured = []

    def fake_urlopen(req, timeout=10):
        captured.append(req)
        if "api.line.me" in req.full_url:
            raise OSError("LINE network timeout")
        return _FakeResponse(200)

    env = {
        "LINE_CHANNEL_ACCESS_TOKEN": "line_tok",
        "LINE_USER_ID": "line_usr",
        "TELEGRAM_BOT_TOKEN": "tg_bot_123",
        "TELEGRAM_CHAT_ID": "987654321",
    }

    res = notify_batch_event(
        event_type="completed",
        product_code="RED01",
        job_id="job_tg_1",
        summary="เสร็จสมบูรณ์",
        public_origin="https://studio.example.com",
        env=env,
        urlopen=fake_urlopen,
    )
    assert res["sent"] is True
    assert res["provider"] == "telegram"
    assert len(captured) == 2
    assert "api.telegram.org/bottg_bot_123/sendMessage" in captured[1].full_url
