"""Channel-owned schedule queue + templates (multi-channel P2.2, plan AC03/AC04).

* the same slot time in channel A and B is allowed; inside one channel the
  existing collision rules apply unchanged (create, move, auto-fill);
* items are addressed by (channel, id): another channel's id is 404 and its
  row stays byte-identical; a batch with one foreign item writes nothing;
* templates are ``<channel>:default`` / ``<channel>:week:<date>``; legacy
  ``default`` / ``week:<date>`` rows are main's in compat mode only;
  copy/reset/auto-fill work inside one channel;
* auto-fill preview -> commit carries a revision token: a stale preview is
  refused with 409, a change in ANOTHER channel does not stale it;
* compat requests without a header equal explicit ``main`` on legacy data.

Offline + tmp_path only (same isolation fixture as test_channel_exports_posts).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import api_exports, api_schedule_queue, config, db, export_registry, media_service
from scripts import channel_store as cs
from scripts import post_log as post_log_module
from scripts import product_store as ps
from scripts import schedule_store, shot_lists_store
from scripts.channel_scope import CHANNEL_HEADER
from scripts.channel_store import ChannelError
from scripts.export_registry import ExportRegistry
from scripts.post_log import PostLog
from scripts.product_store import ProductStore
from scripts.schedule_store import ScheduleQueueStore, ScheduleTemplateStore

STRICT_ENV = config.MULTI_CHANNEL_STRICT_ENV
DEFAULT_TIMES = ["09:00", "12:30", "16:00", "19:00", "21:30"]


class FakeMetrics:
    def width_px(self, text, font_file, size):
        return float(len(text) * 10)

    def unsupported_chars(self, text, font_file):
        return cs._fallback_unsupported(text)


def _write(root: Path, rel: str, data: bytes = b"img") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture()
def env(tmp_path, monkeypatch):
    root = tmp_path / "project"
    docs = root / "_Docs"
    docs.mkdir(parents=True)
    ready = root / "04_Exports" / "Ready_to_post"
    posted = root / "04_Exports" / "Posted"
    covers = root / "05_Covers_Thumbnails"
    for folder in (root / "03_Projects", ready, posted, covers):
        folder.mkdir(parents=True)

    real_conn = db._connection_for
    tmp_root = tmp_path.resolve()

    def guarded(db_path):
        resolved = Path(db_path).resolve()
        assert tmp_root in resolved.parents, f"opened a non-tmp database: {resolved}"
        return real_conn(db_path)

    monkeypatch.setattr(db, "_connection_for", guarded)
    monkeypatch.setattr(ps, "STORE_PATH", docs / "products.json")
    monkeypatch.setattr(ps, "BASE_DIR", root)
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", docs / "export_registry.json")
    monkeypatch.setattr(export_registry, "BASE_DIR", root)
    monkeypatch.setattr(ExportRegistry, "_path_index", None)
    monkeypatch.setattr(shot_lists_store, "STORE_PATH", docs / "shot_lists.json")
    monkeypatch.setattr(post_log_module, "LOG_PATH", docs / "post_log.json")
    monkeypatch.setattr(schedule_store, "SCHEDULE_QUEUE_PATH", docs / "schedule_queue.json")
    monkeypatch.setattr(schedule_store, "SCHEDULE_TEMPLATE_PATH", docs / "schedule_templates.json")
    for module in (api_exports, api_schedule_queue):
        monkeypatch.setattr(module, "BASE_DIR", root)
        monkeypatch.setattr(module, "EXPORTS_DIR", ready)
        monkeypatch.setattr(module, "POSTED_DIR", posted)
    monkeypatch.setattr(api_exports, "COVERS_DIR", covers)
    monkeypatch.setattr(media_service, "BASE_DIR", root)
    monkeypatch.setattr(media_service, "COVERS_DIR", covers)
    monkeypatch.setattr(ProductStore, "_last_reconcile_scope", None)
    monkeypatch.delenv(STRICT_ENV, raising=False)
    from scripts import api_tiktok_autopost

    monkeypatch.setattr(api_tiktok_autopost, "_pending", None)

    _write(root, cs.MAIN_SEED["avatar_asset_path"])
    _write(root, "assets/second.jpg")
    _write(root, "assets/old.jpg")
    monkeypatch.setattr(config, "CHANNELS_FILE", docs / "channels.json")
    monkeypatch.setattr(config, "CHANNELS_PROJECT_ROOT", root)
    monkeypatch.setattr(cs, "_DEFAULT_METRICS", FakeMetrics())
    store = cs.get_default_store()
    store.seed()
    profile = {"display_name": "ช่องรอง", "watermark_text": "สงวนลิขสิทธิ์ช่องรอง", "follow_title": "กดติดตาม"}
    store.create({"id": "second", "handle": "@second_shop", "avatar_asset_path": "assets/second.jpg", **profile})
    store.activate("second")
    store.create({"id": "draft1", "display_name": "ร่าง"})
    store.create({"id": "old", "handle": "@old_shop", "avatar_asset_path": "assets/old.jpg", **profile})
    store.activate("old")
    store.archive("old")
    return root


@pytest.fixture()
def client(env):
    from scripts.api_server import app

    return TestClient(app)


def H(channel: str) -> dict:
    return {CHANNEL_HEADER: channel}


def _rows(root: Path, table: str) -> dict:
    conn = sqlite3.connect(str(root / "_Docs" / "store.db"))
    try:
        return {row[0]: row[1] for row in conn.execute(f"SELECT id, data FROM {table}")}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def _clip(env, name: str, channel: str) -> tuple[Path, str]:
    """An export file registered to ``channel`` (non-main channels need a registered file)."""
    path = _write(env, f"04_Exports/Ready_to_post/{name}", name.encode())
    record = ExportRegistry.ensure(path, channel_id=channel)
    return path, record["id"]


def _item(path: Path, export_id: str, when: str, **extra) -> dict:
    return {"video_path": str(path), "export_id": export_id, "scheduled_at": when,
            "product_name": extra.pop("product_name", path.stem), "hook_title": path.stem, **extra}


# =========================================================================== queue: slots + ids


def test_same_slot_time_is_per_channel(client, env):
    a1, ea1 = _clip(env, "a1.mp4", "main")
    a2, ea2 = _clip(env, "a2.mp4", "main")
    b1, eb1 = _clip(env, "b1.mp4", "second")
    b2, eb2 = _clip(env, "b2.mp4", "second")
    when = "2030-01-07T09:00:00+07:00"
    assert client.post("/api/schedule-queue", json=_item(a1, ea1, when), headers=H("main")).status_code == 200
    resp_b = client.post("/api/schedule-queue", json=_item(b1, eb1, when), headers=H("second"))
    assert resp_b.status_code == 200, resp_b.text
    assert resp_b.json()["items"][0]["channel_id"] == "second"
    # same channel keeps the existing collision rule
    assert client.post("/api/schedule-queue", json=_item(a2, ea2, when), headers=H("main")).status_code == 409
    assert client.post("/api/schedule-queue", json=_item(b2, eb2, when), headers=H("second")).status_code == 409
    # moving a row into a time used only by the other channel is fine; into its own, 409
    b2_item = client.post("/api/schedule-queue", json=_item(b2, eb2, "2030-01-07T10:00:00+07:00"),
                          headers=H("second")).json()["items"][0]
    a2_item = client.post("/api/schedule-queue", json=_item(a2, ea2, "2030-01-07T12:00:00+07:00"),
                          headers=H("main")).json()["items"][0]
    assert client.patch(f"/api/schedule-queue/{a2_item['id']}", json={"scheduled_at": "2030-01-07T10:00:00+07:00"},
                        headers=H("main")).status_code == 200
    assert client.patch(f"/api/schedule-queue/{b2_item['id']}", json={"scheduled_at": when},
                        headers=H("second")).status_code == 409
    assert ScheduleQueueStore.occupied_times(channel_id="main") == {"2030-01-07T09:00+07:00", "2030-01-07T10:00+07:00"}
    assert ScheduleQueueStore.occupied_times(channel_id="second") == {"2030-01-07T09:00+07:00", "2030-01-07T10:00+07:00"}
    listed = client.get("/api/schedule-queue", headers=H("second")).json()["items"]
    assert {row["video_path"] for row in listed} == {"04_Exports/Ready_to_post/b1.mp4", "04_Exports/Ready_to_post/b2.mp4"}


def test_foreign_item_ids_are_404_and_untouched(client, env, monkeypatch):
    b1, eb1 = _clip(env, "b1.mp4", "second")
    item = client.post("/api/schedule-queue", json=_item(b1, eb1, "2030-01-07T09:00:00+07:00"),
                       headers=H("second")).json()["items"][0]
    monkeypatch.setattr(api_schedule_queue, "prepare", lambda req: pytest.fail("prepare must not run"))
    before = _rows(env, "schedule_queue")
    for method, url, kwargs in (
        ("patch", f"/api/schedule-queue/{item['id']}", {"json": {"status": "posted"}}),
        ("delete", f"/api/schedule-queue/{item['id']}", {}),
        ("post", f"/api/schedule-queue/{item['id']}/prepare", {}),
    ):
        response = getattr(client, method)(url, headers=H("main"), **kwargs)
        assert response.status_code == 404, (url, response.text)
        assert response.json()["code"] == "resource_not_found"
    missing = client.patch("/api/schedule-queue/nope", json={"status": "posted"}, headers=H("main"))
    assert missing.status_code == 404 and missing.json() == {"detail": "ไม่พบรายการในคิว"}
    assert _rows(env, "schedule_queue") == before
    # the owner still reaches it
    assert client.delete(f"/api/schedule-queue/{item['id']}", headers=H("second")).status_code == 200


def test_batch_with_one_foreign_item_writes_nothing(client, env):
    a1, ea1 = _clip(env, "a1.mp4", "main")
    a2, ea2 = _clip(env, "a2.mp4", "main")
    b1, eb1 = _clip(env, "b1.mp4", "second")
    loose = _write(env, "04_Exports/Ready_to_post/loose.mp4", b"l")  # unregistered: no provable owner for B
    before = {t: _rows(env, t) for t in ("schedule_queue", "export_registry")}
    response = client.post("/api/schedule-queue", headers=H("second"), json={"items": [
        _item(b1, eb1, "2030-01-07T09:00:00+07:00"),
        _item(a1, ea1, "2030-01-07T09:05:00+07:00"),
        {"video_path": str(a2), "scheduled_at": "2030-01-07T09:10:00+07:00"},
        {"video_path": str(loose), "scheduled_at": "2030-01-07T09:15:00+07:00"},
    ]})
    assert response.status_code == 404, response.text
    body = response.json()
    assert body["code"] == "resource_not_found"
    assert [f["index"] for f in body["foreign_items"]] == [1, 2, 3]
    assert {t: _rows(env, t) for t in ("schedule_queue", "export_registry")} == before
    # same batch through auto-fill commit is refused the same way
    commit = client.post("/api/schedule-queue/auto-fill", headers=H("second"), json={"items": [
        _item(b1, eb1, "2030-01-07T09:00:00+07:00"), _item(a1, ea1, "2030-01-07T09:05:00+07:00")]})
    assert commit.status_code == 404 and [f["index"] for f in commit.json()["foreign_items"]] == [1]
    assert _rows(env, "schedule_queue") == before["schedule_queue"]


def test_status_gates(client, env):
    d1, ed1 = _clip(env, "d1.mp4", "draft1")
    o1, eo1 = _clip(env, "o1.mp4", "old")
    assert client.post("/api/schedule-queue", json=_item(d1, ed1, "2030-01-07T09:00:00+07:00"),
                       headers=H("draft1")).json()["code"] == "channel_not_active"
    assert client.post("/api/schedule-queue", json=_item(o1, eo1, "2030-01-07T09:00:00+07:00"),
                       headers=H("old")).json()["code"] == "channel_not_active"
    response = client.put("/api/schedule-queue/template", json={"week_start": "2030-01-07", "days": {}}, headers=H("old"))
    assert response.status_code == 409 and response.json()["code"] == "channel_archived"
    assert client.get("/api/schedule-queue", headers=H("old")).status_code == 200
    assert _rows(env, "schedule_queue") == {} and _rows(env, "schedule_templates") == {}


def test_concurrent_channel_writers_lose_no_update(env):
    errors = []

    def worker(channel, prefix):
        try:
            for i in range(10):
                owner = ScheduleQueueStore.new_owner(channel_id=channel)
                with ScheduleQueueStore.transaction(channel_id=channel) as records:
                    records.append({"id": f"{prefix}{i}", "channel_id": owner, "scheduled_at": f"2030-01-07T09:{i:02d}+07:00",
                                    "status": "planned"})
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=args)
               for args in (("main", "a"), ("second", "b"), ("main", "c"), ("second", "d"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not errors, errors
    assert len(ScheduleQueueStore.list_items(channel_id="main")) == 20
    assert len(ScheduleQueueStore.list_items(channel_id="second")) == 20
    # a transaction cannot write a row for another channel
    with pytest.raises(Exception):
        with ScheduleQueueStore.transaction(channel_id="main") as records:
            records.append({"id": "evil", "channel_id": "second", "scheduled_at": "x"})
    assert ScheduleQueueStore.get_item("evil", all_channels=True) is None


# =========================================================================== templates


def _legacy_week_template():
    """Real-data shape (P0-B): one legacy override, no channel_id."""
    return {"id": "week:2026-09-07", "week_start": "2026-09-07", "timezone": "Asia/Bangkok",
            "days": {str(i): {"enabled": True, "times": DEFAULT_TIMES} for i in range(7)},
            "updated_at": "2026-09-14T15:11:37+00:00"}


def test_template_ids_are_per_channel(client, env):
    custom = {"enabled": True, "times": ["06:00", "15:00"]}
    saved = client.put("/api/schedule-queue/template", json={"week_start": "2030-01-07", "days": {"0": custom}},
                       headers=H("second"))
    assert saved.status_code == 200
    assert saved.json()["id"] == "week:2030-01-07"  # channel-local id in the response (old shape)
    stored = {json.loads(v)["id"]: json.loads(v) for v in _rows(env, "schedule_templates").values()}
    assert list(stored) == ["second:week:2030-01-07"] and stored["second:week:2030-01-07"]["channel_id"] == "second"
    main_view = client.get("/api/schedule-queue/template", params={"week_start": "2030-01-07"}).json()
    assert main_view["id"] == "default" and main_view["has_override"] is False
    assert main_view["days"]["0"]["times"] == DEFAULT_TIMES
    # copy + default inside one channel only
    client.put("/api/schedule-queue/template", json={"days": {"1": custom}}, headers=H("main"))
    copied = client.post("/api/schedule-queue/template/copy",
                         json={"source_week_start": "2030-01-07", "target_week_start": "2030-01-14"}, headers=H("second"))
    assert copied.json()["days"]["0"]["times"] == ["06:00", "15:00"]
    assert copied.json()["days"]["1"]["times"] == DEFAULT_TIMES  # main's default never leaks into second
    ids = sorted(json.loads(v)["id"] for v in _rows(env, "schedule_templates").values())
    assert ids == ["main:default", "second:week:2030-01-07", "second:week:2030-01-14"]
    main_before = {k: v for k, v in _rows(env, "schedule_templates").items() if k.startswith("main:")}
    reset = client.delete("/api/schedule-queue/template/2030-01-07", headers=H("second"))
    assert reset.json()["id"] == "default"
    assert {k: v for k, v in _rows(env, "schedule_templates").items() if k.startswith("main:")} == main_before
    assert sorted(_rows(env, "schedule_templates")) == ["main:default", "second:week:2030-01-14"]


def test_legacy_templates_are_main_compat_only(client, env, monkeypatch):
    ScheduleTemplateStore._save([_legacy_week_template()])
    plain = client.get("/api/schedule-queue/template", params={"week_start": "2026-09-07"})
    explicit = client.get("/api/schedule-queue/template", params={"week_start": "2026-09-07"}, headers=H("main"))
    assert plain.content == explicit.content
    assert plain.json()["id"] == "week:2026-09-07" and plain.json()["has_override"] is True
    assert client.get("/api/schedule-queue/template", params={"week_start": "2026-09-07"},
                      headers=H("second")).json()["has_override"] is False
    # main edits the legacy row in place: it keeps its legacy id and stays unowned (P2.3 renames it)
    client.put("/api/schedule-queue/template",
               json={"week_start": "2026-09-07", "days": {"0": {"enabled": True, "times": ["07:00"]}}})
    stored = json.loads(_rows(env, "schedule_templates")["week:2026-09-07"])
    assert "channel_id" not in stored and stored["days"]["0"]["times"] == ["07:00"]
    assert list(_rows(env, "schedule_templates")) == ["week:2026-09-07"]
    # strict: legacy rows are invisible to main until migrated
    monkeypatch.setenv(STRICT_ENV, "1")
    strict_view = client.get("/api/schedule-queue/template", params={"week_start": "2026-09-07"}, headers=H("main"))
    assert strict_view.json()["has_override"] is False
    assert client.get("/api/schedule-queue/template").status_code == 422


# =========================================================================== auto-fill revision (AC04)


def _autofill(client, clips, channel, **extra):
    body = {"start_date": "2030-01-07", "end_date": "2030-01-07", "clips": clips, "seed": 3, **extra}
    return client.post("/api/schedule-queue/auto-fill/preview", json=body, headers=H(channel))


def test_autofill_preview_commit_revision(client, env, monkeypatch):
    a1, ea1 = _clip(env, "a1.mp4", "main")
    a2, ea2 = _clip(env, "a2.mp4", "main")
    a3, ea3 = _clip(env, "a3.mp4", "main")
    b1, eb1 = _clip(env, "b1.mp4", "second")
    clips = [{"video_path": str(a1), "export_id": ea1, "product_id": "P1", "product_name": "P1"},
             {"video_path": str(a2), "export_id": ea2, "product_id": "P2", "product_name": "P2"}]
    preview = _autofill(client, clips, "main").json()
    token = preview["preview_revision"]
    assert token.startswith("sq1:") and len(preview["items"]) == 2
    # unchanged state -> same token
    assert _autofill(client, clips, "main").json()["preview_revision"] == token
    # a change in ANOTHER channel does not stale main's preview
    assert client.post("/api/schedule-queue", json=_item(b1, eb1, "2030-01-07T09:00:00+07:00"),
                       headers=H("second")).status_code == 200
    ScheduleTemplateStore.upsert_template("2030-01-07", {}, updated_at="x", channel_id="second")
    PostLog.add_post(product_name="B", clip_file="b.mp4", channel_id="second")
    assert _autofill(client, clips, "main").json()["preview_revision"] == token
    # a change in main stales it: the commit is refused and writes nothing
    assert client.post("/api/schedule-queue", json=_item(a3, ea3, "2030-01-08T09:00:00+07:00"),
                       headers=H("main")).status_code == 200
    before = _rows(env, "schedule_queue")
    stale = client.post("/api/schedule-queue/auto-fill", json={"items": preview["items"], "preview_revision": token},
                        headers=H("main"))
    assert stale.status_code == 409 and stale.json()["code"] == "revision_conflict"
    assert stale.json()["current_revision"] != token
    assert _rows(env, "schedule_queue") == before
    # fresh preview commits; the rows are main's
    fresh = _autofill(client, clips, "main").json()
    ok = client.post("/api/schedule-queue/auto-fill", json={"items": fresh["items"],
                                                            "preview_revision": fresh["preview_revision"]})
    assert ok.status_code == 200, ok.text
    assert {row["channel_id"] for row in ok.json()["items"]} == {"main"}
    # strict mode: the token is mandatory
    monkeypatch.setenv(STRICT_ENV, "1")
    missing = client.post("/api/schedule-queue/auto-fill", json={"items": fresh["items"]}, headers=H("main"))
    assert missing.status_code == 422 and missing.json()["code"] == "expected_revision_required"


def test_autofill_slots_and_history_are_per_channel(client, env):
    a1, ea1 = _clip(env, "a1.mp4", "main")
    b1, eb1 = _clip(env, "b1.mp4", "second")
    b2, eb2 = _clip(env, "b2.mp4", "second")
    # main fills 09:00 and has the product P posted that day; neither blocks second
    assert client.post("/api/schedule-queue", json=_item(a1, ea1, "2030-01-07T09:00:00+07:00", product_id="P",
                                                         product_name="P"), headers=H("main")).status_code == 200
    PostLog.add_post(product_name="Q", clip_file="b2.mp4", posted_at="2030-01-07T08:00:00", channel_id="main")
    preview = _autofill(client, [
        {"video_path": str(b1), "export_id": eb1, "product_id": "P", "product_name": "P"},
        {"video_path": str(b2), "export_id": eb2, "product_id": "Q", "product_name": "Q"},
    ], "second").json()
    assert preview["skipped_invalid"] == []
    times = [row["scheduled_at"] for row in preview["items"]]
    assert times[0] == "2030-01-07T09:00+07:00" and len(times) == 2
    # main's clip offered to second is reported as skipped, never queued
    cross = _autofill(client, [{"video_path": str(a1), "export_id": ea1, "product_id": "P", "product_name": "P"}],
                      "second")
    assert cross.status_code == 200, cross.text
    assert cross.json()["items"] == [] and len(cross.json()["skipped_invalid"]) == 1


# =========================================================================== compat on legacy data


def test_compat_queue_byte_identical_on_legacy_data(client, env):
    clip = _write(env, "04_Exports/Posted/LOG01-pain_1_20260908_201928.mp4", b"v")
    legacy_export = {"id": "exp_3b4b", "path": "04_Exports/Posted/LOG01-pain_1_20260908_201928.mp4",
                     "path_key": "04_Exports/Posted/LOG01-pain_1_20260908_201928.mp4", "product_id": "20260904233315_1",
                     "angle_id": "pain_point", "project_name": "LOG01-pain_1", "status": "posted",
                     "created_at": "2026-09-08T20:19:28", "updated_at": "2026-09-10T12:30:00", "posted_at": "2026-09-10T12:30:00"}
    export_registry._TABLE.save([legacy_export])
    legacy_rows = [
        {"id": "781b", "video_path": "04_Exports/Posted/LOG01-pain_1_20260908_201928.mp4", "video_key": "export:exp_3b4b",
         "export_id": "exp_3b4b", "scheduled_at": "2026-09-10T12:30+07:00", "status": "posted",
         "product_id": "20260904233315_1", "angle_id": "pain_point", "product_name": "Logitech Wave Keys",
         "project_name": "LOG01-pain_1", "hook_title": "hook", "cover_path": None, "cover_url": None, "caption": "c",
         "hashtags": "#a", "tiktok_product_id": None, "created_at": "2026-09-08T20:00:00+00:00",
         "updated_at": "2026-09-10T05:30:00+00:00", "extension_prepared_at": None, "posted_at": "2026-09-10T05:30:00+00:00"},
        {"id": "plan1", "video_path": "04_Exports/Posted/LOG01-pain_1_20260908_201928.mp4", "video_key": "04_exports/x.mp4",
         "export_id": None, "scheduled_at": "2030-02-01T12:30+07:00", "status": "planned", "product_id": None,
         "angle_id": None, "product_name": "X", "project_name": None, "hook_title": "x", "cover_path": None,
         "cover_url": None, "caption": "", "hashtags": "", "tiktok_product_id": None, "created_at": "2026-09-08T20:00:00+00:00",
         "updated_at": "2026-09-08T20:00:00+00:00", "extension_prepared_at": None, "posted_at": None},
    ]
    ScheduleQueueStore._save(legacy_rows)
    ScheduleTemplateStore._save([_legacy_week_template()])
    plain = client.get("/api/schedule-queue")
    explicit = client.get("/api/schedule-queue", headers=H("main"))
    assert plain.status_code == 200 and plain.content == explicit.content
    items = plain.json()["items"]
    assert [row["id"] for row in items] == ["781b", "plan1"]
    assert items[1]["export_id"] == "exp_3b4b"  # enriched from main's (legacy) registry path index
    assert {k: v for k, v in items[0].items() if k != "is_overdue"} == legacy_rows[0]
    assert client.get("/api/schedule-queue", headers=H("second")).json()["items"] == []
    # a no-op scoped write leaves every legacy row byte-identical
    before = {t: _rows(env, t) for t in ("schedule_queue", "schedule_templates", "export_registry")}
    with ScheduleQueueStore.transaction(channel_id="main"):
        pass
    assert ScheduleQueueStore.update_item("plan1", lambda row, rows: None, channel_id="main") is not None
    assert {t: _rows(env, t) for t in ("schedule_queue", "schedule_templates", "export_registry")} == before
    assert clip.exists()
