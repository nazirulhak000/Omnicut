"""Accepted scheduled queue results cannot be silently changed locally."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

import scripts.api_schedule_queue as api
from scripts.channel_scope import ChannelScope, get_channel_scope
from scripts.channel_store import ChannelError
from scripts.db import DocumentTable


@pytest.fixture
def isolated_queue(tmp_path, monkeypatch):
    table = DocumentTable("schedule_queue", lambda: tmp_path / "store.db", lambda: tmp_path / "queue.json")
    table.save([
        {"id": "accepted", "channel_id": "main", "status": "scheduled_on_platform", "scheduled_at": "2026-10-12T09:00:00+07:00", "export_id": "export-old", "posting_job_id": "job-old"},
        {"id": "unknown", "channel_id": "main", "status": "confirmation_unknown", "scheduled_at": "2026-10-12T12:00:00+07:00"},
        {"id": "planned", "channel_id": "main", "status": "planned", "scheduled_at": "2026-10-12T16:00:00+07:00"}])
    class Queue:
        @staticmethod
        def list_items(channel_id=None):
            return table.scoped_load(channel_id)
        @staticmethod
        def update_item(item_id, fn, channel_id=None):
            with table.scoped_mutate(channel_id) as rows:
                row = next((r for r in rows if r["id"] == item_id), None)
                if row is not None:
                    fn(row, rows)
                    return dict(row)
        @staticmethod
        def remove_item(item_id, guard, channel_id=None):
            with table.scoped_mutate(channel_id) as rows:
                row = next((r for r in rows if r["id"] == item_id), None)
                if row is not None:
                    guard(row)
                    rows.remove(row)
                    return row
    monkeypatch.setattr(api, "ScheduleQueueStore", Queue)
    monkeypatch.setattr(api.ExportRegistry, "path_index", lambda **kwargs: {})
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_channel_scope] = lambda: ChannelScope("main", "default", False)
    @app.exception_handler(ChannelError)
    async def errors(request, exc):
        return JSONResponse(status_code=exc.status_code, content=exc.to_body())
    return TestClient(app), table


@pytest.mark.parametrize("state", ["scheduled_on_platform", "confirmation_unknown"])
def test_states_filter_and_labels_truthful(isolated_queue, state):
    client, table = isolated_queue
    response = client.get("/api/schedule-queue", params={"status": state})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["status"] == state
    assert response.json()["items"][0]["is_overdue"] is False
    assert response.json()["status_labels"][state] != response.json()["status_labels"]["posted"]


@pytest.mark.parametrize("item", ["accepted", "unknown"])
@pytest.mark.parametrize("operation", ["reset", "move", "posted", "remove"])
def test_accepted_or_unknown_state_changes_require_platform_review(isolated_queue, item, operation):
    client, table = isolated_queue
    before = table.load()
    path = f"/api/schedule-queue/{item}"
    if operation == "remove":
        response = client.delete(path)
    else:
        payload = {"reset": {"status": "planned"}, "move": {"scheduled_at": "2026-10-13T09:00:00+07:00"}, "posted": {"status": "posted"}}[operation]
        response = client.patch(path, json=payload)
    assert response.status_code == 409
    assert response.json()["code"] == "platform_result_reconciliation_required"
    assert response.json()["action"] == "review_platform_result"
    assert table.load() == before


@pytest.mark.parametrize("state", ["scheduled_on_platform", "confirmation_unknown"])
def test_caller_cannot_invent_platform_accepted_receipt(isolated_queue, state):
    client, table = isolated_queue
    before = table.load()
    response = client.patch("/api/schedule-queue/planned", json={"status": state})
    assert response.status_code == 409
    assert response.json()["code"] == "platform_receipt_required"
    assert table.load() == before


def test_stale_export_requires_explicit_reselect_without_changing_identity(tmp_path, monkeypatch):
    old, new = tmp_path / "old.mp4", tmp_path / "new.mp4"
    old.write_bytes(b"old")
    new.write_bytes(b"new")
    monkeypatch.setattr(api, "resolve_video", lambda path: tmp_path / str(path))
    monkeypatch.setattr(api.ExportRegistry, "lookup", lambda **kwargs: {"id": "export-old", "path": "old.mp4", "status": "ready"})
    monkeypatch.setattr(api.ExportRegistry, "latest_for_angle", lambda *args, **kwargs: {"id": "export-new", "path": "new.mp4"})
    payload = api.QueueItemPayload(video_path="old.mp4", scheduled_at="2026-10-12T09:00:00+07:00", export_id="export-old", product_id="product", angle_id="angle")
    with pytest.raises(ChannelError) as exc:
        api._resolve_payload_export(payload, "main")
    assert exc.value.code == "stale_export"
    assert exc.value.extra == {"action": "reselect_export", "export_id": "export-old", "latest_export_id": "export-new"}
    assert payload.export_id == "export-old" and payload.video_path == "old.mp4"
