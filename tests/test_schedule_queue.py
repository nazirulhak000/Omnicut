from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app
import scripts.api_schedule_queue as queue_api
import scripts.api_tiktok_autopost as autopost
import scripts.schedule_store as queue_store


client = TestClient(app)


@pytest.fixture
def queue_workspace(tmp_path, monkeypatch):
    exports = tmp_path / "04_Exports" / "Ready_to_post"
    posted = tmp_path / "04_Exports" / "Posted"
    covers = tmp_path / "05_Covers_Thumbnails"
    exports.mkdir(parents=True)
    posted.mkdir(parents=True)
    covers.mkdir(parents=True)
    video_a = exports / "a.mp4"
    video_b = exports / "b.mp4"
    video_a.write_bytes(b"a")
    video_b.write_bytes(b"b")
    monkeypatch.setattr(queue_api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(queue_api, "EXPORTS_DIR", exports)
    monkeypatch.setattr(queue_api, "POSTED_DIR", posted)
    monkeypatch.setattr(queue_store, "SCHEDULE_QUEUE_PATH", tmp_path / "_Docs" / "schedule_queue.json")
    monkeypatch.setattr(queue_store, "SCHEDULE_TEMPLATE_PATH", tmp_path / "_Docs" / "schedule_templates.json")
    autopost._pending = None
    return video_a, video_b


def payload(video: Path, when: str):
    return {"video_path": str(video), "scheduled_at": when, "product_name": "Demo", "hook_title": video.stem}


def test_queue_persists_sorted_records_and_blocks_duplicate_video(queue_workspace):
    video_a, video_b = queue_workspace
    first = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-11T12:30:00+07:00"))
    assert first.status_code == 200
    second = client.post("/api/schedule-queue", json=payload(video_b, "2026-09-10T08:30:00+07:00"))
    assert second.status_code == 200
    listed = client.get("/api/schedule-queue").json()["items"]
    assert [row["video_path"] for row in listed] == ["04_Exports/Ready_to_post/b.mp4", "04_Exports/Ready_to_post/a.mp4"]
    duplicate = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-12T08:30:00+07:00"))
    assert duplicate.status_code == 409


def test_bulk_create_is_atomic_on_collision_and_requires_five_minutes(queue_workspace):
    video_a, video_b = queue_workspace
    bad = client.post("/api/schedule-queue", json={"items": [payload(video_a, "2026-09-10T08:31:00+07:00"), payload(video_b, "2026-09-10T08:35:00+07:00")]})
    assert bad.status_code == 422
    assert client.get("/api/schedule-queue").json()["items"] == []
    good = client.post("/api/schedule-queue", json={"items": [payload(video_a, "2026-09-10T08:30:00+07:00"), payload(video_b, "2026-09-10T08:35:00+07:00")]})
    assert good.status_code == 200
    collision = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-10T09:00:00+07:00"))
    assert collision.status_code == 409


def test_reschedule_and_lifecycle_guards(queue_workspace):
    video_a, _ = queue_workspace
    item = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-10T08:30:00+07:00")).json()["items"][0]
    moved = client.patch(f"/api/schedule-queue/{item['id']}", json={"scheduled_at": "2026-09-12T10:00:00+07:00"})
    assert moved.status_code == 200
    ready = client.patch(f"/api/schedule-queue/{item['id']}", json={"status": "ready_for_extension"})
    assert ready.status_code == 200
    blocked = client.patch(f"/api/schedule-queue/{item['id']}", json={"scheduled_at": "2026-09-13T10:00:00+07:00"})
    assert blocked.status_code == 409
    reset = client.patch(f"/api/schedule-queue/{item['id']}", json={"status": "planned"})
    assert reset.status_code == 200
    assert client.patch(f"/api/schedule-queue/{item['id']}", json={"scheduled_at": "2026-09-13T10:00:00+07:00"}).status_code == 200


def test_prepare_marks_one_item_and_sends_date_time_to_extension(queue_workspace, monkeypatch):
    video_a, _ = queue_workspace
    item = client.post("/api/schedule-queue", json=payload(video_a, "2026-09-14T15:25:00+07:00")).json()["items"][0]
    captured = {}

    def fake_prepare(req):
        captured.update(req.model_dump())
        return {"success": True}

    monkeypatch.setattr(queue_api, "prepare", fake_prepare)
    prepared = client.post(f"/api/schedule-queue/{item['id']}/prepare")
    assert prepared.status_code == 200
    assert prepared.json()["status"] == "ready_for_extension"
    assert captured["schedule_date"] == "2026-09-14"
    assert captured["schedule_time"] == "15:25"


def test_weekly_template_upsert_copy_and_reset(queue_workspace):
    custom = {"enabled": True, "times": ["06:00", "15:00", "21:00"]}
    saved = client.put(
        "/api/schedule-queue/template",
        json={"week_start": "2030-01-07", "days": {"0": custom}},
    )
    assert saved.status_code == 200
    assert saved.json()["id"] == "week:2030-01-07"
    assert saved.json()["days"]["0"]["times"] == custom["times"]
    copied = client.post(
        "/api/schedule-queue/template/copy",
        json={"source_week_start": "2030-01-07", "target_week_start": "2030-01-14"},
    )
    assert copied.status_code == 200
    assert copied.json()["days"]["0"]["times"] == custom["times"]
    reset = client.delete("/api/schedule-queue/template/2030-01-14")
    assert reset.status_code == 200
    assert reset.json()["id"] == "default"
    assert reset.json()["days"]["0"]["times"] == ["12:30", "19:00", "21:30"]


def test_legacy_five_slot_template_migrates_to_three_defaults(queue_workspace):
    queue_store.ScheduleTemplateStore._save([{
        "id": "default",
        "week_start": None,
        "days": {str(index): {"enabled": True, "times": ["07:00", "10:00", "12:00", "16:00", "20:00"]} for index in range(7)},
    }])
    response = client.get("/api/schedule-queue/template")
    assert response.status_code == 200
    assert response.json()["days"]["0"]["times"] == ["12:30", "19:00", "21:30"]


def test_autofill_preview_rotates_products_and_commit_is_atomic(queue_workspace):
    video_a, video_b = queue_workspace
    video_c = video_a.parent / "c.mp4"
    video_d = video_a.parent / "d.mp4"
    video_c.write_bytes(b"c")
    video_d.write_bytes(b"d")
    clips = [
        {"video_path": str(video_a), "product_id": "A", "product_name": "A"},
        {"video_path": str(video_b), "product_id": "B", "product_name": "B"},
        {"video_path": str(video_c), "product_id": "A", "product_name": "A"},
        {"video_path": str(video_d), "product_id": "B", "product_name": "B"},
    ]
    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={"start_date": "2030-01-07", "end_date": "2030-01-07", "clips": clips, "seed": 7},
    )
    assert preview.status_code == 200
    rows = preview.json()["items"]
    assert len(rows) == 4
    assert all(a["product_id"] != b["product_id"] for a, b in zip(rows, rows[1:]))
    committed = client.post("/api/schedule-queue/auto-fill", json={"items": rows})
    assert committed.status_code == 200
    collision = client.post("/api/schedule-queue/auto-fill", json={"items": rows[:1]})
    assert collision.status_code == 409
    assert len(client.get("/api/schedule-queue").json()["items"]) == 4


def test_overdue_planned_row_is_annotated_without_changing_status(queue_workspace):
    video_a, _ = queue_workspace
    item = client.post("/api/schedule-queue", json=payload(video_a, "2020-01-06T08:00:00+07:00")).json()["items"][0]
    listed = client.get("/api/schedule-queue").json()["items"][0]
    assert listed["id"] == item["id"]
    assert listed["status"] == "planned"
    assert listed["is_overdue"] is True


def test_autofill_starts_after_latest_queue_timestamp_and_skips_past_slots(queue_workspace):
    video_a, video_b = queue_workspace
    video_c = video_a.parent / "c.mp4"
    video_c.write_bytes(b"c")
    existing = client.post("/api/schedule-queue", json=payload(video_a, "2030-01-07T10:00:00+07:00"))
    assert existing.status_code == 200
    preview = client.post(
        "/api/schedule-queue/auto-fill/preview",
        json={
            "start_date": "2030-01-07",
            "end_date": "2030-01-07",
            "clips": [
                {"video_path": str(video_b), "product_id": "B", "product_name": "B"},
                {"video_path": str(video_c), "product_id": "C", "product_name": "C"},
            ],
            "seed": 11,
        },
    )
    assert preview.status_code == 200
    assert [row["scheduled_at"] for row in preview.json()["items"]] == [
        "2030-01-07T12:30+07:00",
        "2030-01-07T19:00+07:00",
    ]
