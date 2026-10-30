"""Unit and API tests for Phase 6 mobile posting handoff, .ics alerts, and Google Drive bridge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_mobile_posting as mobile_post_api
from scripts import api_schedule_queue as queue_api
from scripts import api_tiktok_autopost as autopost_api
from scripts import config
from scripts import export_registry as export_reg_mod
from scripts import schedule_store as queue_store
from scripts.posting_jobs import PostingJobStore


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(mobile_post_api.router)
    app.include_router(queue_api.router)
    app.include_router(autopost_api.router)
    return app


@pytest.fixture
def mobile_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    posted_dir = tmp_path / "04_Exports" / "Posted"
    covers_dir = tmp_path / "05_Covers_Thumbnails"
    gdrive_root = tmp_path / "GDrive_Exports"
    ready_gdrive = gdrive_root / "01_Ready_to_post"
    archive_gdrive = gdrive_root / "02_Posted_Archive"

    for d in (exports_dir, posted_dir, covers_dir, ready_gdrive, archive_gdrive):
        d.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "EXPORTS_DIR", exports_dir)
    monkeypatch.setattr(queue_api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(queue_api, "EXPORTS_DIR", exports_dir)
    monkeypatch.setattr(queue_api, "POSTED_DIR", posted_dir)
    monkeypatch.setattr(autopost_api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(autopost_api, "EXPORTS_DIR", exports_dir)
    monkeypatch.setattr(autopost_api, "POSTED_DIR", posted_dir)
    monkeypatch.setattr(autopost_api, "COVERS_DIR", covers_dir)
    monkeypatch.setattr(
        queue_store,
        "SCHEDULE_QUEUE_PATH",
        tmp_path / "_Docs" / "schedule_queue.json",
    )
    monkeypatch.setattr(
        queue_store,
        "SCHEDULE_TEMPLATE_PATH",
        tmp_path / "_Docs" / "schedule_templates.json",
    )
    monkeypatch.setattr(
        export_reg_mod,
        "REGISTRY_PATH",
        tmp_path / "_Docs" / "export_registry.json",
    )
    monkeypatch.setenv("OMNICUT_GDRIVE_EXPORT_ROOT", str(gdrive_root))
    autopost_api._pending = None

    app = _build_test_app()
    client = TestClient(app)
    return {
        "client": client,
        "tmp_path": tmp_path,
        "exports_dir": exports_dir,
        "covers_dir": covers_dir,
        "gdrive_root": gdrive_root,
        "ready_gdrive": ready_gdrive,
        "archive_gdrive": archive_gdrive,
    }


def _seed_queue_item(
    queue_id: str = "q-001",
    stem: str = "20261030_TTZ01_s01_v1",
    scheduled_at: str = "2026-10-30T09:20+07:00",
    status: str = "planned",
    export_id: str = "exp-001",
) -> dict:
    row = {
        "id": queue_id,
        "channel_id": "main",
        "video_path": f"04_Exports/Ready_to_post/{stem}.mp4",
        "video_key": f"04_exports/{stem}.mp4",
        "export_id": export_id,
        "clip_id": stem,
        "product_code": "TTZ01",
        "product_id": "TTZ01",
        "product_name": "ขาตั้งมือถือแม่เหล็ก TTZ K106",
        "tiktok_product_id": "1732773678254262244",
        "scheduled_at": scheduled_at,
        "status": status,
        "caption": "ขาตั้งแม่เหล็กพับได้ พกพาสะดวก",
        "hashtags": "#ขาตั้งมือถือ #TTZK106 #รีวิวแกดเจ็ต",
        "cover_path": f"05_Covers_Thumbnails/{stem}_cover.webp",
        "created_at": "2026-10-30T07:00:00+00:00",
        "updated_at": "2026-10-30T07:00:00+00:00",
        "claimed_by": None,
        "posted_at": None,
    }
    with queue_store.ScheduleQueueStore.transaction(channel_id="main") as records:
        records.append(row)
    return row


def test_next_due_handoff_lock_and_extension_pending_skip(mobile_workspace):
    client: TestClient = mobile_workspace["client"]
    tmp_path: Path = mobile_workspace["tmp_path"]

    _seed_queue_item(
        queue_id="q-early",
        stem="20261030_TTZ01_s01_v1",
        scheduled_at="2026-10-30T09:20+07:00",
        export_id="exp-early",
    )
    _seed_queue_item(
        queue_id="q-late",
        stem="20261030_TTZ01_s02_v1",
        scheduled_at="2026-10-30T11:40+07:00",
        export_id="exp-late",
    )

    # Seed a prepared desktop extension job for q-early to verify handoff fences /pending
    job_store = PostingJobStore(tmp_path)
    prepared_job = job_store.prepare(
        "main",
        {
            "export_id": "exp-early",
            "video_path": "04_Exports/Ready_to_post/20261030_TTZ01_s01_v1.mp4",
            "target_handle": "@mainuser",
            "channel_revision": 1,
            "account_binding": {"status": "verified"},
            "strict_mode": False,
            "video_sha256": "abc123",
            "caption": "test",
            "cover_path": None,
            "queue_id": "q-early",
        },
        idempotency_key="prep-q-early",
    )
    job_store.mark_prepare_effects("main", prepared_job["job_id"])
    assert job_store.pending("main") is not None

    # 1. GET /api/mobile-post/next-due returns the earliest planned item
    res = client.get("/api/mobile-post/next-due?device_id=iphone-A")
    assert res.status_code == 200
    body = res.json()
    assert body["queue_id"] == "q-early"
    assert body["product_code"] == "TTZ01"
    assert body["tiktok_product_id"] == "1732773678254262244"
    assert body["status"] == "planned"
    assert body["video_url"].endswith("20261030_TTZ01_s01_v1.mp4")
    assert body["cover_9x16_url"].endswith("20261030_TTZ01_s01_v1_cover.webp")
    assert body["cover_3x4_url"].endswith("20261030_TTZ01_s01_v1_cover_3x4.webp")

    # 2. POST /api/mobile-post/handoff claims for phone:iphone-A
    handoff_res = client.post(
        "/api/mobile-post/handoff",
        json={"queue_id": "q-early", "device_id": "iphone-A"},
    )
    assert handoff_res.status_code == 200
    claimed = handoff_res.json()
    assert claimed["status"] == "awaiting_post"
    assert claimed["claimed_by"] == "phone:iphone-A"

    # While awaiting_post, desktop extension pending() must skip it
    assert PostingJobStore(tmp_path).pending("main") is None

    # Calling handoff again from the same device is allowed (re-entrant)
    same_res = client.post(
        "/api/mobile-post/handoff",
        json={"queue_id": "q-early", "device_id": "iphone-A"},
    )
    assert same_res.status_code == 200

    # 3. Second device attempting to claim the same item receives HTTP 409
    conflict_res = client.post(
        "/api/mobile-post/handoff",
        json={"queue_id": "q-early", "device_id": "android-B"},
    )
    assert conflict_res.status_code == 409


def test_abandon_releases_claim_back_to_planned(mobile_workspace):
    client: TestClient = mobile_workspace["client"]
    _seed_queue_item(queue_id="q-abandon", scheduled_at="2026-10-30T14:00+07:00")

    client.post(
        "/api/mobile-post/handoff",
        json={"queue_id": "q-abandon", "device_id": "iphone-A"},
    )

    # Another device cannot abandon iphone-A's active claim
    wrong_dev = client.post(
        "/api/mobile-post/abandon",
        json={"queue_id": "q-abandon", "device_id": "android-B"},
    )
    assert wrong_dev.status_code == 409

    # Owner abandons -> status returns to planned and claimed_by is cleared
    abandon_res = client.post(
        "/api/mobile-post/abandon",
        json={"queue_id": "q-abandon", "device_id": "iphone-A"},
    )
    assert abandon_res.status_code == 200
    data = abandon_res.json()
    assert data["status"] == "planned"
    assert data["claimed_by"] is None


def test_confirm_is_idempotent_preserves_scheduled_at_and_auto_archives_gdrive(mobile_workspace):
    client: TestClient = mobile_workspace["client"]
    ready_gdrive: Path = mobile_workspace["ready_gdrive"]
    archive_gdrive: Path = mobile_workspace["archive_gdrive"]

    stem = "20261030_TTZ01_s05_v1"
    scheduled_slot = "2026-10-30T16:20+07:00"
    _seed_queue_item(queue_id="q-confirm", stem=stem, scheduled_at=scheduled_slot)

    # Create companion files in Google Drive 01_Ready_to_post
    (ready_gdrive / f"{stem}.mp4").write_bytes(b"fake-mp4-bytes")
    (ready_gdrive / f"{stem}.txt").write_text("แคปชันทดสอบ\n#TTZ01", encoding="utf-8")
    (ready_gdrive / f"{stem}.json").write_text(
        json.dumps({"tiktok_product_id": "1732773678254262244", "schedule_time": scheduled_slot}),
        encoding="utf-8",
    )
    (ready_gdrive / f"{stem}_cover.webp").write_bytes(b"fake-webp")

    client.post(
        "/api/mobile-post/handoff",
        json={"queue_id": "q-confirm", "device_id": "iphone-A"},
    )

    # First confirm call
    confirm_1 = client.post(
        "/api/mobile-post/confirm",
        json={
            "queue_id": "q-confirm",
            "device_id": "iphone-A",
            "mode": "posted",
            "evidence_url": "https://www.tiktok.com/@user/video/123456",
        },
    )
    assert confirm_1.status_code == 200
    c1 = confirm_1.json()
    assert c1["status"] == "posted"
    assert c1["posted_at"] == scheduled_slot
    assert c1["evidence_type"] == "manual_user_confirmation"
    assert c1["idempotent"] is False
    assert c1["gdrive_archive"]["archived"] is True

    # Companion files moved from 01_Ready_to_post to 02_Posted_Archive
    assert not (ready_gdrive / f"{stem}.mp4").exists()
    assert (archive_gdrive / f"{stem}.mp4").is_file()
    assert (archive_gdrive / f"{stem}.txt").is_file()
    assert (archive_gdrive / f"{stem}.json").is_file()
    assert (archive_gdrive / f"{stem}_cover.webp").is_file()

    # Second confirm call is idempotent (200 OK with existing receipt)
    confirm_2 = client.post(
        "/api/mobile-post/confirm",
        json={
            "queue_id": "q-confirm",
            "device_id": "iphone-A",
            "mode": "posted",
        },
    )
    assert confirm_2.status_code == 200
    c2 = confirm_2.json()
    assert c2["idempotent"] is True
    assert c2["posted_at"] == scheduled_slot
    assert c2["receipt"] == c1["receipt"]


def test_agenda_reschedule_and_calendar_ics_feed(mobile_workspace):
    client: TestClient = mobile_workspace["client"]
    _seed_queue_item(
        queue_id="q-slot-1",
        stem="20261030_TTZ01_s07_v1",
        scheduled_at="2026-10-30T07:00+07:00",
    )

    # Reschedule to one of the 7 standard slots (18:40)
    resched = client.post(
        "/api/mobile-post/reschedule",
        json={"queue_id": "q-slot-1", "scheduled_at": "2026-10-30T18:40:00+07:00"},
    )
    assert resched.status_code == 200
    assert resched.json()["scheduled_at"].startswith("2026-10-30T18:40")

    # Non-standard slot is rejected with 422
    bad_slot = client.post(
        "/api/mobile-post/reschedule",
        json={"queue_id": "q-slot-1", "scheduled_at": "2026-10-30T18:45:00+07:00"},
    )
    assert bad_slot.status_code == 422

    # 7-day agenda contains the rescheduled item in the 18:40 slot
    agenda = client.get("/api/mobile-post/agenda?start_date=2026-10-30").json()
    assert len(agenda["days"]) == 7
    day0 = agenda["days"][0]
    assert day0["date"] == "2026-10-30"
    slot_1840 = next(s for s in day0["slots"] if s["time"] == "18:40")
    assert slot_1840["occupied"] is True
    assert slot_1840["item"]["queue_id"] == "q-slot-1"

    # Calendar .ics feed includes VCALENDAR, VEVENT, VALARM (-PT10M), and deep link
    ics_res = client.get("/api/mobile-post/calendar.ics?base_url=https://studio.example.com")
    assert ics_res.status_code == 200
    assert ics_res.headers["content-type"].startswith("text/calendar")
    ics_text = ics_res.text
    assert "BEGIN:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "BEGIN:VALARM" in ics_text
    assert "TRIGGER:-PT10M" in ics_text
    assert "?mode=mobile&tab=post&queue=q-slot-1" in ics_text


def test_gdrive_ready_and_gdrive_archive_endpoints(mobile_workspace):
    client: TestClient = mobile_workspace["client"]
    ready_gdrive: Path = mobile_workspace["ready_gdrive"]
    archive_gdrive: Path = mobile_workspace["archive_gdrive"]

    stem = "20261030_HAT01_s03_v1"
    (ready_gdrive / f"{stem}.mp4").write_bytes(b"mp4-content")
    (ready_gdrive / f"{stem}.txt").write_text(
        "พัดลมคล้องคอ Hatari เย็นจริงไม่ง้อมือจับ\n#Hatari #พัดลมคล้องคอ",
        encoding="utf-8",
    )
    (ready_gdrive / f"{stem}.json").write_text(
        json.dumps({
            "product_code": "HAT01",
            "product_name": "Hatari พัดลมคล้องคอ",
            "tiktok_product_id": "173999888777666555",
            "schedule_time": "2026-10-30T21:00+07:00",
        }),
        encoding="utf-8",
    )
    (ready_gdrive / f"{stem}_cover.webp").write_bytes(b"webp-cover")

    # 1. GET /api/mobile-post/gdrive-ready scans 01_Ready_to_post
    ready_res = client.get("/api/mobile-post/gdrive-ready")
    assert ready_res.status_code == 200
    ready_data = ready_res.json()
    assert ready_data["count"] == 1
    item = ready_data["items"][0]
    assert item["stem"] == stem
    assert item["product_code"] == "HAT01"
    assert item["tiktok_product_id"] == "173999888777666555"
    assert "พัดลมคล้องคอ Hatari" in item["caption"]
    assert "#Hatari" in item["hashtags"]

    # 2. POST /api/mobile-post/gdrive-archive moves all companion files to 02_Posted_Archive
    arch_res = client.post(
        "/api/mobile-post/gdrive-archive",
        json={"stem": stem, "evidence_url": "https://www.tiktok.com/@test/video/999"},
    )
    assert arch_res.status_code == 200
    arch_body = arch_res.json()
    assert arch_body["archived"] is True
    assert arch_body["status"] == "posted"
    assert len(arch_body["moved_files"]) == 4

    assert not (ready_gdrive / f"{stem}.mp4").exists()
    assert not (ready_gdrive / f"{stem}.txt").exists()
    assert not (ready_gdrive / f"{stem}.json").exists()
    assert not (ready_gdrive / f"{stem}_cover.webp").exists()

    assert (archive_gdrive / f"{stem}.mp4").is_file()
    assert (archive_gdrive / f"{stem}.txt").is_file()
    assert (archive_gdrive / f"{stem}.json").is_file()
    assert (archive_gdrive / f"{stem}_cover.webp").is_file()

    archived_meta = json.loads((archive_gdrive / f"{stem}.json").read_text(encoding="utf-8"))
    assert archived_meta["status"] == "posted"
    assert archived_meta["evidence_type"] == "manual_user_confirmation"
