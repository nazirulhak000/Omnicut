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

