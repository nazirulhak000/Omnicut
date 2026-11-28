import asyncio
import datetime as dt

import pytest

from scripts import config
import scripts.api_schedule_queue as queue_api
import scripts.api_tiktok_autopost as autopost
import scripts.autopost_scheduler as scheduler_mod
import scripts.export_registry as export_registry_mod
import scripts.schedule_store as queue_store
from scripts.autopost_scheduler import (
    AutomationSettingsStore,
    AutopostScheduler,
    is_due_now,
    is_in_schedule_window,
)
from scripts.schedule_store import ScheduleQueueStore


@pytest.fixture
def scheduler_workspace(tmp_path, monkeypatch):
    exports = tmp_path / "04_Exports" / "Ready_to_post"
    posted = tmp_path / "04_Exports" / "Posted"
    covers = tmp_path / "05_Covers_Thumbnails"
    docs = tmp_path / "_Docs"
    exports.mkdir(parents=True)
    posted.mkdir(parents=True)
    covers.mkdir(parents=True)
    docs.mkdir(parents=True)

    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "EXPORTS_DIR", exports)
    monkeypatch.setattr(autopost, "BASE_DIR", tmp_path)
    monkeypatch.setattr(autopost, "EXPORTS_DIR", exports)
    monkeypatch.setattr(autopost, "POSTED_DIR", posted)
    monkeypatch.setattr(autopost, "COVERS_DIR", covers)
    monkeypatch.setattr(queue_api, "BASE_DIR", tmp_path)
    monkeypatch.setattr(queue_api, "EXPORTS_DIR", exports)
    monkeypatch.setattr(queue_api, "POSTED_DIR", posted)
    monkeypatch.setattr(queue_store, "SCHEDULE_QUEUE_PATH", docs / "schedule_queue.json")
    monkeypatch.setattr(queue_store, "SCHEDULE_TEMPLATE_PATH", docs / "schedule_templates.json")
    monkeypatch.setattr(export_registry_mod, "REGISTRY_PATH", docs / "export_registry.json")
    monkeypatch.setattr(scheduler_mod, "_conductor_proc", None)
    return tmp_path, exports


def test_due_window_and_schedule_window_helpers():
    now = dt.datetime(2026, 11, 28, 12, 0, tzinfo=scheduler_mod.PROJECT_TZ)
    assert is_due_now({"status": "planned", "scheduled_at": "2026-11-28T11:55+07:00"}, now=now, before_min=5, after_min=30)
    assert is_due_now({"status": "ready_for_extension", "scheduled_at": "2026-11-28T12:30+07:00"}, now=now, before_min=5, after_min=30)
    assert not is_due_now({"status": "planned", "scheduled_at": "2026-11-28T11:50+07:00"}, now=now, before_min=5, after_min=30)
    assert not is_due_now({"status": "posted", "scheduled_at": "2026-11-28T12:00+07:00"}, now=now, before_min=5, after_min=30)

    assert is_in_schedule_window({"status": "planned", "scheduled_at": "2026-11-28T12:20+07:00"}, now=now)
    assert not is_in_schedule_window({"status": "planned", "scheduled_at": "2026-11-28T12:10+07:00"}, now=now)


def test_scheduler_hybrid_triggers_due_now_first_then_schedule(scheduler_workspace):
    tmp_path, exports = scheduler_workspace
    store = AutomationSettingsStore(tmp_path)
    store.put("main", {"enabled": True, "mode": "hybrid", "due_window_before_min": 5, "due_window_after_min": 30})
    store.put("ch2", {"enabled": False})

    now = dt.datetime(2026, 11, 28, 12, 0, tzinfo=scheduler_mod.PROJECT_TZ)
    v1 = exports / "v1.mp4"
    v2 = exports / "v2.mp4"
    v1.write_bytes(b"v1")
    v2.write_bytes(b"v2")

    ScheduleQueueStore._save([
        {
            "id": "q-due",
            "channel_id": "main",
            "video_path": "04_Exports/Ready_to_post/v1.mp4",
            "scheduled_at": "2026-11-28T12:05+07:00",
            "status": "planned",
            "caption": "Due item",
            "hashtags": "#test",
        },
        {
            "id": "q-future",
            "channel_id": "main",
            "video_path": "04_Exports/Ready_to_post/v2.mp4",
            "scheduled_at": "2026-11-29T12:00+07:00",
            "status": "planned",
            "caption": "Future item",
            "hashtags": "#test",
        },
        {
            "id": "q-ch2",
            "channel_id": "ch2",
            "video_path": "04_Exports/Ready_to_post/v2.mp4",
            "scheduled_at": "2026-11-28T12:05+07:00",
            "status": "planned",
            "caption": "Disabled channel",
            "hashtags": "#test",
        },
    ])

    prepared_calls = []
    spawn_calls = []

    def fake_prepare(item, ch):
        prepared_calls.append((item["id"], ch))

    def fake_spawn(*, mode, channel_id, limit, all_channels=False):
        spawn_calls.append((mode, channel_id, limit))
        return {"started": True, "reason": "started", "pid": 999}

    sched = AutopostScheduler(
        settings_store_factory=lambda: store,
        spawner=fake_spawn,
        channel_lister=lambda: ["ch2", "main"],
        prepare_due_item=fake_prepare,
    )

    actions = asyncio.run(sched.run_once(now=now, allow_in_pytest=True))
    assert prepared_calls == [("q-due", "main")]
    assert spawn_calls == [("due_now", "main", 1)]
    assert len(actions) == 1
    assert actions[0]["mode"] == "due_now"

    # Once due item is posted, next tick triggers schedule mode
    ScheduleQueueStore.update_item("q-due", lambda row, _: row.__setitem__("status", "posted"), channel_id="main")
    prepared_calls.clear()
    spawn_calls.clear()

    actions2 = asyncio.run(sched.run_once(now=now, allow_in_pytest=True))
    assert prepared_calls == []
    assert spawn_calls == [("schedule", "main", 3)]
    assert actions2[0]["mode"] == "schedule"


def test_scheduler_respects_pytest_guard(scheduler_workspace):
    tmp_path, _ = scheduler_workspace
    store = AutomationSettingsStore(tmp_path)
    store.put("main", {"enabled": True, "mode": "hybrid"})
    spawn_calls = []
    sched = AutopostScheduler(
        settings_store_factory=lambda: store,
        spawner=lambda **kw: spawn_calls.append(kw) or {"started": True, "pid": 1},
        channel_lister=lambda: ["main"],
    )
    actions = asyncio.run(sched.run_once())
    assert actions == []
    assert spawn_calls == []
