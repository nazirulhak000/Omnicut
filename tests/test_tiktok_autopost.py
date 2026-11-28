import datetime as dt
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from scripts import config
from scripts.api_server import app
import scripts.api_schedule_queue as queue_api
import scripts.api_tiktok_autopost as autopost
import scripts.autopost_scheduler as scheduler_mod
import scripts.channel_store as channel_store_mod
import scripts.export_registry as export_registry_mod
import scripts.schedule_store as queue_store


client = TestClient(app)


@pytest.fixture
def isolated_autopost(tmp_path, monkeypatch):
    exports = tmp_path / "04_Exports" / "Ready_to_post"
    posted = tmp_path / "04_Exports" / "Posted"
    covers = tmp_path / "05_Covers_Thumbnails"
    docs = tmp_path / "_Docs"
    conductor_dir = tmp_path / "tools" / "autopost_conductor"
    exports.mkdir(parents=True)
    posted.mkdir(parents=True)
    covers.mkdir(parents=True)
    docs.mkdir(parents=True)
    conductor_dir.mkdir(parents=True)
    (conductor_dir / "run.js").write_text("// stub", encoding="utf-8")

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
    monkeypatch.setattr(export_registry_mod, "BASE_DIR", tmp_path)
    monkeypatch.setattr(export_registry_mod, "REGISTRY_PATH", docs / "export_registry.json")
    monkeypatch.setattr(scheduler_mod, "_conductor_proc", None)

    avatar = tmp_path / "02_Assets" / "ch2_avatar.png"
    avatar.parent.mkdir(parents=True, exist_ok=True)
    avatar.write_bytes(b"\x89PNG\r\n\x1a\n")
    store = channel_store_mod.ChannelStore(project_root=tmp_path)
    store.create({
        "id": "ch2",
        "display_name": "Channel Two",
        "handle": "@channeltwo",
        "watermark_text": "ChannelTwo",
        "follow_title": "Follow ch2",
        "avatar_asset_path": "02_Assets/ch2_avatar.png",
    })
    store.activate("ch2")
    monkeypatch.setattr(channel_store_mod, "_DEFAULT_STORE", store, raising=False)
    monkeypatch.setattr(channel_store_mod, "get_default_store", lambda: store)

    autopost._pending = None
    return tmp_path, exports, conductor_dir


def test_automation_settings_multi_channel_isolation(isolated_autopost):
    res_main = client.get("/api/tiktok-autopost/automation-settings")
    assert res_main.status_code == 200
    assert res_main.json()["channel_id"] == "main"
    assert res_main.json()["enabled"] is False
    assert res_main.json()["mode"] == "hybrid"

    upd = client.put(
        "/api/tiktok-autopost/automation-settings",
        headers={"X-OmniCut-Channel": "ch2"},
        json={"enabled": True, "mode": "due_now", "poll_interval_sec": 30, "due_window_before_min": 10},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["channel_id"] == "ch2"
    assert upd.json()["enabled"] is True
    assert upd.json()["mode"] == "due_now"
    assert upd.json()["poll_interval_sec"] == 30
    assert upd.json()["due_window_before_min"] == 10

    # main remains untouched
    res_main_after = client.get("/api/tiktok-autopost/automation-settings")
    assert res_main_after.json()["enabled"] is False
    assert res_main_after.json()["mode"] == "hybrid"

    # Also accepts matching channel_id in JSON body (as sent by frontend/src/api.js)
    upd_body = client.put(
        "/api/tiktok-autopost/automation-settings",
        headers={"X-OmniCut-Channel": "ch2"},
        json={"channel_id": "ch2", "enabled": False},
    )
    assert upd_body.status_code == 200, upd_body.text
    assert upd_body.json()["channel_id"] == "ch2"
    assert upd_body.json()["enabled"] is False


def test_automation_status_counts_and_conductor_state(isolated_autopost):
    tmp_path, exports, conductor_dir = isolated_autopost
    video = exports / "clip1.mp4"
    video.write_bytes(b"video-data")
    exp1 = export_registry_mod.ExportRegistry.ensure(video, channel_id="ch2")

    now = dt.datetime.now(queue_api.PROJECT_TZ).replace(second=0, microsecond=0)
    # Round to nearest 5 min within [+5m, +10m] so it is due_now
    minute = ((now.minute // 5) * 5 + 5) % 60
    due_dt = now.replace(minute=minute)
    if due_dt < now:
        due_dt += dt.timedelta(hours=1)
    far_dt = now + dt.timedelta(days=1)
    far_dt = far_dt.replace(minute=(far_dt.minute // 5) * 5)

    r1 = client.post(
        "/api/schedule-queue",
        headers={"X-OmniCut-Channel": "ch2"},
        json={"video_path": str(video), "export_id": exp1["id"], "scheduled_at": due_dt.isoformat(timespec="minutes"), "caption": "Due clip"},
    )
    assert r1.status_code == 200, r1.text

    video2 = exports / "clip2.mp4"
    video2.write_bytes(b"video-data-2")
    exp2 = export_registry_mod.ExportRegistry.ensure(video2, channel_id="ch2")
    r2 = client.post(
        "/api/schedule-queue",
        headers={"X-OmniCut-Channel": "ch2"},
        json={"video_path": str(video2), "export_id": exp2["id"], "scheduled_at": far_dt.isoformat(timespec="minutes"), "caption": "Future clip"},
    )
    assert r2.status_code == 200, r2.text

    (conductor_dir / "state.json").write_text(
        json.dumps({"running": False, "last_result": "ok", "channel_id": "ch2"}),
        encoding="utf-8",
    )

    status = client.get("/api/tiktok-autopost/automation-status", headers={"X-OmniCut-Channel": "ch2"})
    assert status.status_code == 200, status.text
    data = status.json()
    assert data["channel_id"] == "ch2"
    assert data["queue_counts"]["planned"] == 2
    assert data["queue_counts"]["due_now_count"] >= 1
    assert data["conductor_state"]["last_result"] == "ok"

    # main has 0 items
    status_main = client.get("/api/tiktok-autopost/automation-status")
    assert status_main.status_code == 200
    assert status_main.json()["queue_counts"]["planned"] == 0


def test_trigger_run_spawns_and_guards_already_running(isolated_autopost, monkeypatch):
    spawned = []

    class FakeProc:
        def __init__(self, pid=4242, alive=True):
            self.pid = pid
            self._alive = alive

        def poll(self):
            return None if self._alive else 0

    def fake_popen(cmd, **kwargs):
        proc = FakeProc(pid=4242, alive=True)
        spawned.append((cmd, kwargs, proc))
        return proc

    monkeypatch.setattr(scheduler_mod.subprocess, "Popen", fake_popen)

    res = client.post(
        "/api/tiktok-autopost/trigger-run",
        headers={"X-OmniCut-Channel": "ch2"},
        json={"mode": "hybrid", "limit": 3},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["started"] is True
    assert body["pid"] == 4242
    assert "--mode" in spawned[0][0]
    assert "hybrid" in spawned[0][0]
    assert "--channel" in spawned[0][0]
    assert "ch2" in spawned[0][0]

    # Second call while alive -> already_running
    res2 = client.post(
        "/api/tiktok-autopost/trigger-run",
        headers={"X-OmniCut-Channel": "ch2"},
        json={"mode": "due_now", "limit": 1},
    )
    assert res2.status_code == 200
    assert res2.json()["started"] is False
    assert res2.json()["reason"] == "already_running"
    assert res2.json()["pid"] == 4242


def test_schedule_queue_prepare_supports_post_now_for_due_or_past_slot(isolated_autopost):
    _, exports, _ = isolated_autopost
    video = exports / "due_clip.mp4"
    video.write_bytes(b"due-clip-bytes")
    exp = export_registry_mod.ExportRegistry.ensure(video, channel_id="main")

    # Slot 5 minutes in the past (would be rejected by 15m schedule window)
    past_dt = (dt.datetime.now(queue_api.PROJECT_TZ) - dt.timedelta(minutes=5)).replace(second=0, microsecond=0)
    past_dt = past_dt.replace(minute=(past_dt.minute // 5) * 5)

    created = client.post(
        "/api/schedule-queue",
        json={
            "video_path": str(video),
            "export_id": exp["id"],
            "scheduled_at": past_dt.isoformat(timespec="minutes"),
            "caption": "Post right now",
        },
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["items"][0]["id"]

    # Default intent="schedule" fails due to 15m min lead
    fail_sched = client.post(f"/api/schedule-queue/{item_id}/prepare")
    assert fail_sched.status_code == 422, fail_sched.text

    # Explicit intent="post_now" succeeds
    ok_now = client.post(f"/api/schedule-queue/{item_id}/prepare", json={"intent": "post_now"})
    assert ok_now.status_code == 200, ok_now.text
    row = ok_now.json()
    assert row["status"] == "ready_for_extension"
    assert row["posting_job_id"]
    job = autopost._jobs().get("main", row["posting_job_id"])
    assert job["intent"] == "post_now"
