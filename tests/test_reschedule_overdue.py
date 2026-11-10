"""Overdue clips (planned, or already a draft on TikTok) get new slots without touching their drafts."""
import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app
import scripts.api_schedule_queue as queue_api
import scripts.schedule_store as queue_store

client = TestClient(app)
TZ = ZoneInfo("Asia/Bangkok")


@pytest.fixture
def queue(tmp_path, monkeypatch):
    monkeypatch.setattr(queue_store, "SCHEDULE_QUEUE_PATH", tmp_path / "_Docs" / "schedule_queue.json")
    monkeypatch.setattr(queue_store, "SCHEDULE_TEMPLATE_PATH", tmp_path / "_Docs" / "schedule_templates.json")
    monkeypatch.setattr(queue_api, "_history_posts", lambda channel_id: [])
    return tmp_path


def iso(days, hour=9, minute=0):
    base = dt.datetime.now(TZ).replace(hour=hour, minute=minute, second=0, microsecond=0) + dt.timedelta(days=days)
    return base.isoformat(timespec="minutes")


def seed(*rows):
    with queue_store.ScheduleQueueStore.transaction(channel_id="main") as records:
        for row in rows:
            records.append({"channel_id": "main", "video_path": f"04_Exports/Ready_to_post/{row['id']}.mp4", "hook_title": row["id"], **row})


def get(item_id):
    return queue_store.ScheduleQueueStore.get_item(item_id, channel_id="main")


def listing():
    return {r["id"]: r for r in client.get("/api/schedule-queue").json()["items"]}


def standard_rows():
    seed(
        {"id": "plan-late", "status": "planned", "scheduled_at": iso(-1, 9), "product_id": "prodA", "product_name": "A"},
        {"id": "draft-late-b", "status": "draft_on_platform", "scheduled_at": iso(-1, 12, 30), "product_id": "prodB", "product_name": "B", "posting_job_id": "job-b", "export_id": "exp-b"},
        {"id": "draft-late-a", "status": "draft_on_platform", "scheduled_at": iso(-1, 16), "product_id": "prodA", "product_name": "A", "posting_job_id": "job-a", "export_id": "exp-a"},
        {"id": "plan-future", "status": "planned", "scheduled_at": iso(1, 9), "product_id": "prodC", "product_name": "C"},
        {"id": "done", "status": "posted", "scheduled_at": iso(-3, 9), "product_id": "prodD", "product_name": "D"},
    )


def test_list_flags_overdue_planned_and_drafts_and_labels_the_draft(queue):
    standard_rows()
    items = listing()
    assert items["plan-late"]["needs_reschedule"] is True
    assert items["draft-late-b"]["needs_reschedule"] is True
    assert items["draft-late-b"]["status"] == "draft_on_platform"                       # the stored state is untouched
    assert "ต้องจัดเวลาใหม่" in items["draft-late-b"]["status_label"]
    assert items["plan-future"]["needs_reschedule"] is False
    assert items["done"]["needs_reschedule"] is False


def test_preview_places_everything_in_free_future_slots_with_the_daily_rules_and_writes_nothing(queue):
    standard_rows()
    before = [dict(r) for r in queue_store.ScheduleQueueStore.list_items(channel_id="main")]
    body = client.post("/api/schedule-queue/reschedule-overdue/preview", json={"window_days": 14}).json()
    assert body["overdue_count"] == 3 and not body["unplaced"]
    new = {i["id"]: i["new_scheduled_at"] for i in body["items"]}
    now = dt.datetime.now(TZ)
    assert all(dt.datetime.fromisoformat(v) > now + dt.timedelta(minutes=15) for v in new.values())
    assert len(set(new.values())) == 3 and iso(1, 9) not in new.values()                  # unique, never on another clip's slot
    day = lambda value: value[:10]
    assert day(new["plan-late"]) != day(new["draft-late-a"])                                # same product A: never the same day
    assert [dict(r) for r in queue_store.ScheduleQueueStore.list_items(channel_id="main")] == before


def test_commit_moves_the_slots_but_keeps_planned_as_planned_and_a_draft_as_a_draft(queue):
    standard_rows()
    preview = client.post("/api/schedule-queue/reschedule-overdue/preview", json={}).json()
    commit = client.post("/api/schedule-queue/reschedule-overdue", json={"assignments": [{"id": i["id"], "scheduled_at": i["new_scheduled_at"]} for i in preview["items"]]})
    assert commit.status_code == 200, commit.text
    for item in preview["items"]:
        row = get(item["id"])
        assert row["scheduled_at"] == item["new_scheduled_at"]
        assert row["status"] == item["status"]
    assert get("draft-late-b")["posting_job_id"] == "job-b"                                  # the draft and its job are untouched
    assert not any(r["needs_reschedule"] for r in listing().values())


def test_commit_refuses_what_preview_would_never_offer_and_changes_nothing(queue):
    standard_rows()
    def post(assignments):
        return client.post("/api/schedule-queue/reschedule-overdue", json={"assignments": assignments})
    snapshot = lambda: [dict(r) for r in queue_store.ScheduleQueueStore.list_items(channel_id="main")]
    before = snapshot()
    ok_slot = iso(3, 12, 30)
    assert post([{"id": "plan-future", "scheduled_at": ok_slot}]).status_code == 409                       # not overdue
    assert post([{"id": "plan-late", "scheduled_at": iso(-1, 9)}]).status_code == 422                      # still in the past
    assert post([{"id": "plan-late", "scheduled_at": iso(1, 9)}]).status_code == 409                       # another clip's slot
    assert post([{"id": "plan-late", "scheduled_at": iso(3, 9)}, {"id": "draft-late-a", "scheduled_at": iso(3, 12, 30)}]).status_code == 409  # product A twice on one day
    assert post([{"id": "plan-late", "scheduled_at": iso(3, 9)}, {"id": "plan-late", "scheduled_at": iso(4, 9)}]).status_code == 422          # duplicate id
    assert post([]).status_code == 422
    assert snapshot() == before                                                                               # all-or-nothing


def test_patch_moves_the_slot_of_a_draft_without_touching_the_draft(queue):
    standard_rows()
    target = iso(5, 16)
    res = client.patch("/api/schedule-queue/draft-late-b", json={"scheduled_at": target})
    assert res.status_code == 200, res.text
    row = get("draft-late-b")
    assert row["scheduled_at"] == target and row["status"] == "draft_on_platform" and row["posting_job_id"] == "job-b"
    assert client.patch("/api/schedule-queue/draft-late-b", json={"scheduled_at": iso(-1, 9)}).status_code == 422     # past
    assert client.patch("/api/schedule-queue/draft-late-a", json={"scheduled_at": target}).status_code == 409         # taken
    assert client.patch("/api/schedule-queue/draft-late-b", json={"status": "failed"}).status_code == 409             # other edits stay refused
