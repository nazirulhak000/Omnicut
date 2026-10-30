"""
Offline unit & API tests for `scripts/couple_jobs.py` and `scripts/api_couple_production.py`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from scripts import config
from scripts.couple_jobs import (
    CoupleJobStore,
    InvalidJobStateError,
    JobConflictError,
    JobNotFoundError,
    RevisionConflictError,
)
from scripts.api_couple_production import (
    router as couple_router,
    set_couple_job_store,
    set_executor_hook,
)


@pytest.fixture()
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CoupleJobStore:
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    store = CoupleJobStore(storage_dir=tmp_path / "_Docs")
    set_couple_job_store(store)
    set_executor_hook(None)
    yield store
    set_couple_job_store(None)
    set_executor_hook(None)


@pytest.fixture()
def client(isolated_store: CoupleJobStore) -> TestClient:
    app = FastAPI()
    app.include_router(couple_router)
    return TestClient(app)


def _parse_sse_frames(raw_text: str) -> List[dict]:
    events = []
    for block in raw_text.split("\n\n"):
        lines = [line for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        if all(line.startswith(":") or line.startswith("retry:") for line in lines):
            continue
        frame = {}
        for line in lines:
            if line.startswith("id:"):
                frame["id"] = int(line.split(":", 1)[1].strip())
            elif line.startswith("event:"):
                frame["event"] = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                frame["data"] = json.loads(line.split(":", 1)[1].strip())
        if frame:
            events.append(frame)
    return events


def test_create_job_and_idempotency(client: TestClient, isolated_store: CoupleJobStore) -> None:
    # 1. Create new job -> 201 Created
    res1 = client.post(
        "/api/couple/jobs",
        json={"product_code": "ttz01", "total_clips": 20, "idempotency_key": "idem-001"},
    )
    assert res1.status_code == 201
    job1 = res1.json()
    assert job1["product_code"] == "TTZ01"
    assert job1["status"] == "queued"
    assert job1["revision"] == 1
    assert job1["total_clips"] == 20
    assert job1["completed_clips"] == 0
    assert job1["current_stage"] == "tts"
    assert len(job1["clips"]) == 20
    assert job1["clips"][0] == {
        "idx": 1,
        "clip_id": "ttz01_01",
        "status": "pending",
        "error": None,
    }
    assert isolated_store.json_path.is_file()

    # 2. Repeat with same idempotency_key -> 200 OK (idempotent hit)
    res2 = client.post(
        "/api/couple/jobs",
        json={"product_code": "TTZ01", "total_clips": 20, "idempotency_key": "idem-001"},
    )
    assert res2.status_code == 200
    assert res2.json()["job_id"] == job1["job_id"]

    # 3. Repeat without idempotency_key while active job for TTZ01 exists -> 200 OK
    res3 = client.post("/api/couple/jobs", json={"product_code": "TTZ01"})
    assert res3.status_code == 200
    assert res3.json()["job_id"] == job1["job_id"]

    # 4. Conflicting active job with different idempotency_key for same product -> 409 Conflict
    res4 = client.post(
        "/api/couple/jobs",
        json={"product_code": "TTZ01", "idempotency_key": "idem-002"},
    )
    assert res4.status_code == 409

    # 5. Reusing existing idempotency_key for a different product -> 409 Conflict
    res5 = client.post(
        "/api/couple/jobs",
        json={"product_code": "HAT01", "idempotency_key": "idem-001"},
    )
    assert res5.status_code == 409


def test_list_and_get_jobs_most_recent_first(client: TestClient) -> None:
    r1 = client.post("/api/couple/jobs", json={"product_code": "HAT01"}).json()
    r2 = client.post("/api/couple/jobs", json={"product_code": "RED01"}).json()

    list_res = client.get("/api/couple/jobs")
    assert list_res.status_code == 200
    body = list_res.json()
    assert body["count"] == 2
    assert [j["job_id"] for j in body["jobs"]] == [r2["job_id"], r1["job_id"]]

    detail_res = client.get(f"/api/couple/jobs/{r1['job_id']}")
    assert detail_res.status_code == 200
    assert detail_res.json()["product_code"] == "HAT01"

    missing_res = client.get("/api/couple/jobs/cjob_nonexistent")
    assert missing_res.status_code == 404


def test_checkpoint_approve_reject_and_revision_conflict(
    client: TestClient,
    isolated_store: CoupleJobStore,
) -> None:
    created = client.post("/api/couple/jobs", json={"product_code": "TTZ01"}).json()
    job_id = created["job_id"]

    isolated_store.start_job(job_id, stage="compose")
    cp_job = isolated_store.open_checkpoint(
        job_id,
        clip_id="ttz01_01",
        chat_snapshot_url="/api/media/review/ttz01_01_chat.webp",
        cta_snapshot_url="/api/media/review/ttz01_01_cta.webp",
    )
    assert cp_job["status"] == "awaiting_approval"
    assert cp_job["current_stage"] == "checkpoint"
    assert cp_job["clips"][0]["status"] == "awaiting_review"
    current_rev = cp_job["revision"]

    # Stale expected_revision -> 409 Conflict
    stale_res = client.post(
        f"/api/couple/jobs/{job_id}/checkpoint",
        json={"decision": "approve", "expected_revision": current_rev - 1, "note": ""},
    )
    assert stale_res.status_code == 409
    assert stale_res.json()["detail"]["code"] == "revision_conflict"

    # Reject checkpoint -> pauses job and marks clip 1 for rework with note
    reject_res = client.post(
        f"/api/couple/jobs/{job_id}/checkpoint",
        json={"decision": "reject", "expected_revision": current_rev, "note": "แก้คำผิดบรรทัดแรก"},
    )
    assert reject_res.status_code == 200
    rejected_job = reject_res.json()
    assert rejected_job["status"] == "paused"
    assert rejected_job["checkpoint"]["approved"] is False
    assert rejected_job["checkpoint"]["note"] == "แก้คำผิดบรรทัดแรก"
    assert rejected_job["clips"][0]["status"] == "pending"
    assert rejected_job["clips"][0]["error"] == "แก้คำผิดบรรทัดแรก"

    # Re-open checkpoint after rework and approve -> running + stage render
    reopened = isolated_store.open_checkpoint(
        job_id,
        clip_id="ttz01_01",
        chat_snapshot_url="/api/media/review/ttz01_01_chat_v2.webp",
        cta_snapshot_url="/api/media/review/ttz01_01_cta_v2.webp",
    )
    approve_res = client.post(
        f"/api/couple/jobs/{job_id}/checkpoint",
        json={"decision": "approve", "expected_revision": reopened["revision"], "note": "ผ่านเลย"},
    )
    assert approve_res.status_code == 200
    approved_job = approve_res.json()
    assert approved_job["status"] == "running"
    assert approved_job["current_stage"] == "render"
    assert approved_job["checkpoint"]["approved"] is True
    assert approved_job["clips"][0]["status"] == "running"


def test_sse_event_replay_with_last_event_id(
    client: TestClient,
    isolated_store: CoupleJobStore,
) -> None:
    created = client.post("/api/couple/jobs", json={"product_code": "ORS01"}).json()
    job_id = created["job_id"]

    isolated_store.start_job(job_id, stage="tts")
    isolated_store.update_stage(job_id, "whisper")
    isolated_store.open_checkpoint(
        job_id,
        chat_snapshot_url="/chat.webp",
        cta_snapshot_url="/cta.webp",
    )

    # Full stream from start
    res_all = client.get(f"/api/couple/jobs/{job_id}/events")
    assert res_all.status_code == 200
    assert res_all.headers["content-type"].startswith("text/event-stream")
    assert ": heartbeat" in res_all.text
    frames_all = _parse_sse_frames(res_all.text)
    assert [f["id"] for f in frames_all] == [1, 2, 3, 4]
    assert [f["event"] for f in frames_all] == [
        "job_created",
        "job_started",
        "stage_changed",
        "checkpoint_opened",
    ]

    # Replay after Last-Event-ID: 2 via header
    res_delta = client.get(
        f"/api/couple/jobs/{job_id}/events",
        headers={"Last-Event-ID": "2"},
    )
    assert res_delta.status_code == 200
    frames_delta = _parse_sse_frames(res_delta.text)
    assert [f["id"] for f in frames_delta] == [3, 4]
    assert [f["event"] for f in frames_delta] == ["stage_changed", "checkpoint_opened"]

    # Replay via query param last_event_id=3
    res_query = client.get(f"/api/couple/jobs/{job_id}/events?last_event_id=3")
    frames_query = _parse_sse_frames(res_query.text)
    assert [f["id"] for f in frames_query] == [4]


def test_pause_quota_resume_cancel_and_clip_retry(
    client: TestClient,
    isolated_store: CoupleJobStore,
) -> None:
    created = client.post("/api/couple/jobs", json={"product_code": "GOO01", "total_clips": 3}).json()
    job_id = created["job_id"]
    isolated_store.start_job(job_id, stage="tts")

    # Pause due to TTS 429 quota exhaustion
    pause_q = client.post(f"/api/couple/jobs/{job_id}/pause", json={"reason": "quota"})
    assert pause_q.status_code == 200
    assert pause_q.json()["status"] == "paused_quota"

    # Resume job
    resumed = client.post(f"/api/couple/jobs/{job_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "running"

    # Mark clip 1 rendered, clip 2 failed
    isolated_store.update_clip(job_id, 1, "rendered")
    failed_state = isolated_store.update_clip(job_id, 2, "failed", error="FFmpeg timeout")
    assert failed_state["completed_clips"] == 1
    assert failed_state["clips"][1]["status"] == "failed"

    # Retry clip 2 via API
    retry_res = client.post(f"/api/couple/jobs/{job_id}/clips/2/retry")
    assert retry_res.status_code == 200
    retried_job = retry_res.json()
    assert retried_job["clips"][1]["status"] == "pending"
    assert retried_job["clips"][1]["error"] is None

    # Render remaining clips -> job auto-completes
    isolated_store.update_clip(job_id, 2, "rendered")
    completed_job = isolated_store.update_clip(job_id, 3, "rendered")
    assert completed_job["status"] == "completed"
    assert completed_job["completed_clips"] == 3
    assert completed_job["current_stage"] == "finalize"

    # Cannot cancel a completed job -> 409
    cancel_completed = client.post(f"/api/couple/jobs/{job_id}/cancel")
    assert cancel_completed.status_code == 409

    # Create a second job and cancel it
    job2 = client.post("/api/couple/jobs", json={"product_code": "GOO02"}).json()
    cancel_res = client.post(f"/api/couple/jobs/{job2['job_id']}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Cannot resume a cancelled job -> 409
    resume_cancelled = client.post(f"/api/couple/jobs/{job2['job_id']}/resume")
    assert resume_cancelled.status_code == 409


def test_startup_recovery_preserves_rendered_clips(tmp_path: Path) -> None:
    storage_dir = tmp_path / "_Docs"
    store1 = CoupleJobStore(storage_dir=storage_dir)
    job, created = store1.create_job("HAT01", total_clips=5)
    assert created is True
    job_id = job["job_id"]

    store1.start_job(job_id, stage="render", executor_pid=999999)
    store1.update_clip(job_id, 1, "rendered")
    store1.update_clip(job_id, 2, "rendered")
    store1.update_clip(job_id, 3, "running")

    # Simulate server reboot with a new CoupleJobStore instance
    store2 = CoupleJobStore(storage_dir=storage_dir)
    recovered = store2.recover_interrupted_jobs()
    assert len(recovered) == 1

    reloaded = store2.get_job(job_id)
    assert reloaded["status"] == "queued"
    assert reloaded["completed_clips"] == 2
    assert reloaded["clips"][0]["status"] == "rendered"
    assert reloaded["clips"][1]["status"] == "rendered"
    assert reloaded["clips"][2]["status"] == "pending"
    assert reloaded["clips"][3]["status"] == "pending"
    assert reloaded["events"][-1]["type"] == "job_recovered"


def test_preflight_endpoint_does_not_leak_raw_keys(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_key_1 = "AIzaSyDUMMY_SECRET_KEY_VALUE_NUMBER_1"
    secret_key_2 = "AIzaSyDUMMY_SECRET_KEY_VALUE_NUMBER_2"
    monkeypatch.setattr(config, "get_gemini_api_keys", lambda: [secret_key_1, secret_key_2])

    res = client.get("/api/couple/preflight")
    assert res.status_code == 200
    data = res.json()

    assert data["gemini_key_count"] == 2
    assert data["checks"]["gemini_api_keys"]["count"] == 2
    assert data["checks"]["gemini_api_keys"]["ready"] is True
    assert "nvenc_available" in data
    assert "node_ready" in data
    assert "hyperframes_ready" in data
    assert "whisper_ready" in data

    raw_payload = res.text
    assert secret_key_1 not in raw_payload
    assert secret_key_2 not in raw_payload
    assert not re.search(r"AIza[0-9A-Za-z_-]+", raw_payload)
