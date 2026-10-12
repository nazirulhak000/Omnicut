"""Channel-owned exports + post log (multi-channel P2.2, plan AC01/AC03/AC12 groundwork).

Store level: the same basename / path / angle label in channel A and B stay
independent export rows; scoped latest/find/path_index never return the other
channel's row; every write in A leaves B's serialized rows byte-identical; an
export can only be linked inside its product's channel; post idempotency is
(channel, export identity) and the legacy basename fallback matches only when
exactly one row of the same channel qualifies (real-data shape: legacy rows
without export_id, a duplicated basename and seven generic ``clip.mp4``).

API level (real app + middleware, ``X-OmniCut-Channel``): another channel's
file/export/product/post is 404 before any file move or write; compat requests
without a header behave exactly like explicit ``main`` on legacy data; strict
mode fails closed for callers that are not converted yet.

Offline + tmp_path only: every store/registry/export folder is redirected to
tmp_path and every sqlite file opened is asserted to live under tmp_path.
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
    """Isolated stores + export folders + registry: main/second active, draft1 draft, old archived."""
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


def _rows(root: Path, table: str) -> dict:
    conn = sqlite3.connect(str(root / "_Docs" / "store.db"))
    try:
        return {row[0]: row[1] for row in conn.execute(f"SELECT id, data FROM {table}")}
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()


def _all_rows(root: Path) -> dict:
    return {t: _rows(root, t) for t in ("products", "export_registry", "posts", "schedule_queue", "schedule_templates")}


def _angle(angle_id="pain_point", **extra):
    return {"angle_id": angle_id, "angle_name": "ปัญหาก่อนใช้", "script_lines": ["บรรทัดแรก"], **extra}


def _products():
    a = ProductStore.add("JBL Go 4", url="https://shop.tiktok.com/view/product/1", angles=[_angle()], channel_id="main")
    b = ProductStore.add("JBL Go 4", url="https://shop.tiktok.com/view/product/1", angles=[_angle()], channel_id="second")
    return a, b


def H(channel: str) -> dict:
    return {CHANNEL_HEADER: channel}


# =========================================================================== ExportRegistry


def test_same_basename_two_channels_are_independent_rows(env):
    a, b = _products()
    file_a = _write(env, "04_Exports/Ready_to_post/JBL01-pain_1.mp4", b"a")
    file_b = _write(env, "04_Exports/second_dir/JBL01-pain_1.mp4", b"b")  # same basename, other folder
    rec_a = ExportRegistry.ensure(file_a, product_id=a["id"], angle_id="pain_point", channel_id="main")
    rec_b = ExportRegistry.ensure(file_b, product_id=b["id"], angle_id="pain_point", channel_id="second")
    assert rec_a["id"] != rec_b["id"]
    assert (rec_a["channel_id"], rec_b["channel_id"]) == ("main", "second")
    # scoped reads never return the other channel's row
    assert ExportRegistry.find_by_path(file_a, channel_id="second") is None
    assert ExportRegistry.find_by_path(file_b, channel_id="main") is None
    assert ExportRegistry.get(rec_b["id"], channel_id="main") is None
    assert ExportRegistry.find_for_angle(b["id"], "pain_point", channel_id="main") == []
    assert ExportRegistry.latest_for_angle(a["id"], "pain_point", channel_id="main")["id"] == rec_a["id"]
    assert ExportRegistry.latest_for_angle(b["id"], "pain_point", channel_id="second")["id"] == rec_b["id"]
    assert ExportRegistry.latest_for_angle(b["id"], "pain_point", channel_id="main") is None
    assert set(ExportRegistry.path_index(channel_id="main").values()) == {rec_a["id"]}
    assert set(ExportRegistry.path_index(channel_id="second").values()) == {rec_b["id"]}
    assert set(ExportRegistry.path_index().values()) == {rec_a["id"], rec_b["id"]}  # compat None = all
    # re-ensuring in A enriches A only (idempotent) and never merges into B
    b_before = _rows(env, "export_registry")[rec_b["id"]]
    again = ExportRegistry.ensure(file_a, project_name="JBL01-pain_1", status="posted", channel_id="main")
    assert again["id"] == rec_a["id"] and again["status"] == "posted"
    assert _rows(env, "export_registry")[rec_b["id"]] == b_before
    # B cannot claim A's file: 404 and nothing written
    before = _rows(env, "export_registry")
    with pytest.raises(ChannelError) as info:
        ExportRegistry.ensure(file_a, channel_id="second")
    assert (info.value.status_code, info.value.code) == (404, "resource_not_found")
    with pytest.raises(ChannelError):
        ExportRegistry.lookup(path=file_a, channel_id="second")
    with pytest.raises(ChannelError):
        ExportRegistry.lookup(export_id=rec_a["id"], channel_id="second")
    assert ExportRegistry.lookup(export_id="exp_missing", channel_id="second") is None
    assert _rows(env, "export_registry") == before


def test_same_path_rows_in_both_channels_never_cross(env):
    """Migration-shaped data: A and B each own a row with the SAME path."""
    path = _write(env, "04_Exports/Ready_to_post/shared.mp4", b"x")
    rows = [
        {"id": "exp_a", "channel_id": "main", "path": "04_Exports/Ready_to_post/shared.mp4",
         "path_key": "04_Exports/Ready_to_post/shared.mp4", "product_id": "pa", "angle_id": "hook", "status": "rendered"},
        {"id": "exp_b", "channel_id": "second", "path": "04_Exports/Ready_to_post/shared.mp4",
         "path_key": "04_Exports/Ready_to_post/shared.mp4", "product_id": "pb", "angle_id": "hook", "status": "rendered"},
    ]
    export_registry._TABLE.save(rows)
    assert ExportRegistry.find_by_path(path, channel_id="main")["id"] == "exp_a"
    assert ExportRegistry.find_by_path(path, channel_id="second")["id"] == "exp_b"
    assert list(ExportRegistry.path_index(channel_id="second").values()) == ["exp_b"]
    b_before = _rows(env, "export_registry")["exp_b"]
    # A posts its row onto a Posted path: B's row is not merged/collapsed/drifted
    ExportRegistry.ensure(path, status="rendered", channel_id="main")
    moved = ExportRegistry.move_and_mark_posted("exp_a", env / "04_Exports/Posted/shared.mp4", channel_id="main")
    assert moved["status"] == "posted"
    assert _rows(env, "export_registry")["exp_b"] == b_before
    assert ExportRegistry.get("exp_b", channel_id="second")["status"] == "rendered"
    # A cannot move/rename onto B's path, nor touch B's id
    with pytest.raises(ChannelError) as info:
        ExportRegistry.update_path("exp_a", path, channel_id="main")
    assert info.value.code == "export_path_conflict"
    with pytest.raises(KeyError):
        ExportRegistry.move_and_mark_posted("exp_b", env / "04_Exports/Posted/x.mp4", channel_id="main")
    assert ExportRegistry.update_path("exp_b", env / "04_Exports/x.mp4", channel_id="main") is None
    ExportRegistry.remove("exp_b", channel_id="main")
    assert ExportRegistry.apply_to_each(lambda row: row.update(note="x"), channel_id="main") == 1
    assert _rows(env, "export_registry")["exp_b"] == b_before
    with pytest.raises(ValueError):
        ExportRegistry.apply_to_each(lambda row: row.update(channel_id="second"), channel_id="main")


def test_export_must_match_parent_product_channel(env):
    a, b = _products()
    file_a = _write(env, "04_Exports/Ready_to_post/a.mp4", b"a")
    before = _rows(env, "export_registry")
    with pytest.raises(ChannelError) as info:
        ExportRegistry.ensure(file_a, product_id=b["id"], angle_id="pain_point", channel_id="main")
    assert (info.value.status_code, info.value.code) == (409, "channel_child_mismatch")
    assert _rows(env, "export_registry") == before
    rec_b = ExportRegistry.ensure(_write(env, "04_Exports/Ready_to_post/b.mp4", b"b"), product_id=b["id"],
                                  angle_id="pain_point", channel_id="second")
    # update_angle_status: an export of another channel is refused (scoped and compat None)
    b_rows = _rows(env, "products")
    for kwargs in ({"channel_id": "main"}, {}):
        with pytest.raises(ChannelError) as info:
            ProductStore.update_angle_status(a["id"], "pain_point", "rendered",
                                             video_url="04_Exports/Ready_to_post/b.mp4",
                                             export_id=rec_b["id"], **kwargs)
        assert info.value.code == "channel_child_mismatch"
    assert _rows(env, "products") == b_rows
    ok = ProductStore.update_angle_status(b["id"], "pain_point", "rendered", video_url="04_Exports/Ready_to_post/b.mp4",
                                          export_id=rec_b["id"], channel_id="second")
    assert ok["angles"][0]["export_id"] == rec_b["id"]


def test_legacy_export_rows_are_main_only_in_compat(env, monkeypatch):
    path = _write(env, "04_Exports/Ready_to_post/old.mp4", b"o")
    legacy = {"id": "exp_old", "path": "04_Exports/Ready_to_post/old.mp4", "path_key": "04_Exports/Ready_to_post/old.mp4",
              "product_id": None, "angle_id": None, "project_name": "OLD_1", "status": "rendered",
              "created_at": "2026-09-01T10:00:00", "updated_at": "2026-09-01T10:00:00", "posted_at": None}
    export_registry._TABLE.save([legacy])
    assert ExportRegistry.all(channel_id="main") == ExportRegistry.all() == [legacy]
    assert ExportRegistry.all(channel_id="second") == []
    # main (compat) may enrich it; it stays legacy (no owner stamped)
    ExportRegistry.ensure(path, angle_id="hook", channel_id="main")
    assert "channel_id" not in json.loads(_rows(env, "export_registry")["exp_old"])
    with pytest.raises(ChannelError):
        ExportRegistry.ensure(path, channel_id="second")
    created = ExportRegistry.ensure(_write(env, "04_Exports/Ready_to_post/new.mp4", b"n"))
    assert created["channel_id"] == "main"  # compat None stamps main

    monkeypatch.setenv(STRICT_ENV, "1")
    for call in (lambda: ExportRegistry.all(), lambda: ExportRegistry.get("exp_old"),
                 lambda: ExportRegistry.find_by_path(path), lambda: ExportRegistry.path_index()):
        with pytest.raises(ChannelError) as info:
            call()
        assert info.value.code == "channel_scope_missing"
    assert [r["id"] for r in ExportRegistry.all(channel_id="main")] == [created["id"]]
    before = _rows(env, "export_registry")
    with pytest.raises(ChannelError):  # strict main cannot claim an unmigrated legacy file
        ExportRegistry.ensure(path, channel_id="main")
    assert _rows(env, "export_registry") == before
    assert len(ExportRegistry.all(all_channels=True)) == 2
    with pytest.raises(ValueError):  # all_channels never creates rows
        ExportRegistry.ensure(_write(env, "04_Exports/Ready_to_post/x.mp4", b"x"), all_channels=True)


# =========================================================================== PostLog


def _legacy_posts():
    """Shaped like the real post_log rows (P0-B): no channel_id/export_id/product_id."""
    base = {"product_url": "", "angle_key": "pain_point", "platform": "tiktok", "hashtags": [],
            "metrics": {"views": 101, "likes": 8, "comments": 0}, "metrics_filled_at": "2026-09-26T18:24:28",
            "source": "tiktok_stats_auto", "tiktok_url": "", "tiktok_synced_at": "2026-09-26T18:24:28"}
    rows = [
        {**base, "id": "uniq", "product_name": "Logitech Wave Keys", "angle_title": "ปวดข้อมือ", "hook": "ปวดข้อมือ",
         "clip_file": "LOG01-ปัญหาก่อนใช้_1_20260908_201928.mp4", "caption": "Wave Keys", "posted_at": "2026-09-10T12:30:00",
         "tiktok_video_id": "v1"},
        {**base, "id": "dup1", "product_name": "Bluewow", "angle_title": "โปรไฟลุก", "hook": "โปรไฟลุก",
         "clip_file": "BLU01-โปรไฟลุก_1_20260910_171055.mp4", "caption": "a", "posted_at": "2026-09-11T19:00:00",
         "tiktok_video_id": "v2"},
        {**base, "id": "dup2", "product_name": "Bluewow", "angle_title": "โปรไฟลุก", "hook": "โปรไฟลุก",
         "clip_file": "BLU01-โปรไฟลุก_1_20260910_171055.mp4", "caption": "b", "posted_at": "2026-09-12T19:00:00",
         "tiktok_video_id": "v3"},
    ]
    for i in range(7):
        rows.append({**base, "id": f"generic{i}", "product_name": "Logitech Lift", "angle_title": f"มุม {i}",
                     "hook": f"มุม {i}", "clip_file": "clip.mp4", "caption": f"Lift {i}",
                     "posted_at": f"2026-09-1{i}T09:00:00", "tiktok_video_id": f"g{i}"})
    return rows


def test_post_idempotency_is_channel_plus_export(env):
    a = PostLog.record_posted_export(product_name="A", clip_file="JBL01-pain_1.mp4", export_id="exp_a", channel_id="main")
    b = PostLog.record_posted_export(product_name="B", clip_file="JBL01-pain_1.mp4", export_id="exp_b", channel_id="second")
    assert (a["status"], b["status"]) == ("created", "created")
    assert a["post"]["id"] != b["post"]["id"]
    assert (a["post"]["channel_id"], b["post"]["channel_id"]) == ("main", "second")
    a_before = _rows(env, "posts")[a["post"]["id"]]
    again = PostLog.record_posted_export(product_name="B", clip_file="JBL01-pain_1.mp4", export_id="exp_b",
                                         hook="ฮุค", channel_id="second")
    assert again["status"] == "matched_export" and again["post"]["id"] == b["post"]["id"]
    assert len(_rows(env, "posts")) == 2
    assert _rows(env, "posts")[a["post"]["id"]] == a_before
    # B's export id is never matched from A's scope
    third = PostLog.record_posted_export(product_name="A", clip_file="other.mp4", export_id="exp_b", channel_id="main")
    assert third["status"] == "created"
    assert _rows(env, "posts")[b["post"]["id"]] == json.dumps(again["post"], ensure_ascii=False)


def test_legacy_basename_fallback_never_guesses(env, monkeypatch):
    post_log_module._TABLE.save(_legacy_posts())
    before = _rows(env, "posts")
    # exactly one legacy row with that basename in main -> enriched, stays legacy
    one = PostLog.record_posted_export(product_name="Logitech Wave Keys",
                                       clip_file="LOG01-ปัญหาก่อนใช้_1_20260908_201928.mp4",
                                       export_id="exp_1", style_preset="clean", channel_id="main")
    assert one["status"] == "matched_legacy" and one["post"]["id"] == "uniq"
    stored = json.loads(_rows(env, "posts")["uniq"])
    assert stored["export_id"] == "exp_1" and stored["style_preset"] == "clean" and "channel_id" not in stored
    # two legacy rows with the same basename -> ambiguous, nothing written
    snapshot = _rows(env, "posts")
    amb = PostLog.record_posted_export(product_name="Bluewow", clip_file="BLU01-โปรไฟลุก_1_20260910_171055.mp4",
                                       export_id="exp_2", channel_id="main")
    assert amb == {"status": "ambiguous", "post": None, "candidate_post_ids": ["dup1", "dup2"]}
    assert PostLog.register_posted_export(product_name="Bluewow", clip_file="BLU01-โปรไฟลุก_1_20260910_171055.mp4",
                                          export_id="exp_2", channel_id="main") is None
    assert _rows(env, "posts") == snapshot
    # generic clip.mp4 never matches anything -> a new row
    gen = PostLog.record_posted_export(product_name="Logitech Lift", clip_file="clip.mp4", export_id="exp_3", channel_id="main")
    assert gen["status"] == "created" and gen["post"]["channel_id"] == "main"
    # another channel never sees legacy rows
    other = PostLog.record_posted_export(product_name="x", clip_file="LOG01-ปัญหาก่อนใช้_1_20260908_201928.mp4",
                                         export_id="exp_9", channel_id="second")
    assert other["status"] == "created" and other["post"]["channel_id"] == "second"
    for rid in ("dup1", "dup2", *(f"generic{i}" for i in range(7))):
        assert _rows(env, "posts")[rid] == before[rid]
    # strict: legacy rows are invisible to main until migrated
    monkeypatch.setenv(STRICT_ENV, "1")
    strict = PostLog.record_posted_export(product_name="Bluewow", clip_file="BLU01-โปรไฟลุก_1_20260910_171055.mp4",
                                          export_id="exp_2", channel_id="main")
    assert strict["status"] == "created"
    for rid in ("dup1", "dup2"):
        assert _rows(env, "posts")[rid] == before[rid]


def test_stats_matching_is_channel_scoped_and_unambiguous(env):
    PostLog.add_post(product_name="Orbit", clip_file="orbit.mp4", angle_title="Orbit gadget quick review", channel_id="main")
    a_before = _rows(env, "posts")
    # the same title imported for channel B never fuzzy-matches A's post
    res = PostLog.upsert_tiktok_stats([{"title": "Orbit gadget quick review", "views": 9, "video_id": "77"}], channel_id="second")
    assert res["matched"] == 0 and len(res["unmatched"]) == 1
    assert _rows(env, "posts") == a_before
    # two B posts share the candidate's clip basename -> stays unmatched, no duplicate registered
    PostLog.add_post(product_name="Zed", clip_file="zed.mp4", channel_id="second")
    PostLog.add_post(product_name="Zed", clip_file="zed.mp4", channel_id="second")
    count = len(_rows(env, "posts"))
    res = PostLog.upsert_tiktok_stats(
        [{"title": "Totally unrelated words here", "views": 5, "video_id": "88"}],
        register_missing=True,
        clip_candidates=[{"clip_file": "zed.mp4", "product_name": "Totally unrelated", "hook_title": "Totally unrelated words here"}],
        channel_id="second",
    )
    assert res["registered"] == 0 and res["matched"] == 0
    assert len(res["unmatched"][0]["ambiguous_post_ids"]) == 2
    assert len(_rows(env, "posts")) == count
    # a registered post is stamped with the scope
    res = PostLog.upsert_tiktok_stats(
        [{"title": "Brand new gadget review", "views": 5, "video_id": "99"}],
        register_missing=True,
        clip_candidates=[{"clip_file": "new.mp4", "product_name": "Brand new gadget", "hook_title": "Brand new gadget review"}],
        channel_id="second",
    )
    assert res["registered"] == 1
    new_rows = [json.loads(v) for v in _rows(env, "posts").values() if json.loads(v)["clip_file"] == "new.mp4"]
    assert [r["channel_id"] for r in new_rows] == ["second"]


def test_attach_and_metrics_are_channel_scoped(env):
    a = PostLog.add_post(product_name="A", clip_file="a.mp4", hook="hook a", channel_id="main")
    b = PostLog.add_post(product_name="B", clip_file="b.mp4", hook="hook b", channel_id="second")
    before = _rows(env, "posts")
    with pytest.raises(ValueError):
        PostLog.update_metrics(a["id"], {"views": 5}, channel_id="second")
    with pytest.raises(ValueError):
        PostLog.attach_manual({"video_id": "1", "views": 3}, post_id=a["id"], channel_id="second")
    # a candidate whose clip/hook exists only in A creates a NEW B post, never A's
    attached = PostLog.attach_manual({"video_id": "2", "views": 3}, candidate={"clip_file": "a.mp4", "hook_title": "hook a"},
                                     channel_id="second")
    assert attached["id"] != a["id"] and attached["channel_id"] == "second"
    assert _rows(env, "posts")[a["id"]] == before[a["id"]]
    # ambiguous hook inside one channel -> refuse instead of guessing
    PostLog.add_post(product_name="B", clip_file="b2.mp4", hook="hook b", channel_id="second")
    with pytest.raises(ValueError):
        PostLog.attach_manual({"video_id": "3"}, candidate={"clip_file": "clip.mp4", "hook_title": "hook b"}, channel_id="second")
    PostLog.update_metrics(b["id"], {"views": 50}, channel_id="second")
    assert PostLog.summary(channel_id="second")["total_views"] == 50 + 3  # b + the attached B post
    assert PostLog.summary(channel_id="main")["total_views"] == 0
    assert [p["id"] for p in PostLog.list_posts(channel_id="main")] == [a["id"]]
    assert {r["angle_key"] for r in PostLog.angle_performance(channel_id="main")} == set()
    assert len(PostLog.list_posts()) == 4  # compat None = every row


def test_concurrent_channels_lose_no_update(env):
    errors = []

    def worker(channel, n):
        try:
            for i in range(n):
                PostLog.add_post(product_name=channel, clip_file=f"{channel}{i}.mp4", channel_id=channel)
                ExportRegistry.ensure(_write(env, f"04_Exports/Ready_to_post/{channel}{i}.mp4", b"x"), channel_id=channel)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(c, 8)) for c in ("main", "second", "main", "second")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not errors, errors
    assert len(PostLog.list_posts(channel_id="main")) == 16
    assert len(PostLog.list_posts(channel_id="second")) == 16
    # 8 distinct files per channel (both main workers ensure the same 8 paths -> idempotent)
    assert len(ExportRegistry.all(channel_id="main")) == 8
    assert len(ExportRegistry.all(channel_id="second")) == 8


def test_strict_mode_fails_closed_for_unscoped_callers(env, monkeypatch):
    monkeypatch.setenv(STRICT_ENV, "1")
    calls = [
        lambda: PostLog.list_posts(), lambda: PostLog.summary(), lambda: PostLog.add_post("x", "x.mp4"),
        lambda: PostLog.upsert_tiktok_stats([]), lambda: ScheduleQueueStore.list_items(),
        lambda: ScheduleQueueStore.update_item("x", lambda r, rs: None), lambda: ScheduleTemplateStore.find_template(None),
        lambda: ExportRegistry.latest_for_angle("p", "a"),
    ]
    for call in calls:
        with pytest.raises(ChannelError) as info:
            call()
        assert info.value.code == "channel_scope_missing"


# =========================================================================== API


@pytest.fixture()
def client(env):
    from scripts.api_server import app

    return TestClient(app)


def _two_channel_exports(env):
    a, b = _products()
    file_a = _write(env, "04_Exports/Ready_to_post/a1.mp4", b"a1")
    file_b = _write(env, "04_Exports/Ready_to_post/b1.mp4", b"b1")
    rec_a = ExportRegistry.ensure(file_a, product_id=a["id"], angle_id="pain_point", channel_id="main")
    rec_b = ExportRegistry.ensure(file_b, product_id=b["id"], angle_id="pain_point", channel_id="second")
    return a, b, file_a, file_b, rec_a, rec_b


def test_api_mark_posted_foreign_file_is_404_before_moving(client, env):
    a, b, file_a, file_b, rec_a, rec_b = _two_channel_exports(env)
    before = _all_rows(env)
    attempts = [
        {"file_path": str(file_b)},
        {"file_path": str(file_b), "export_id": rec_b["id"]},
        {"file_path": str(file_a), "product_id": b["id"], "angle_id": "pain_point"},
    ]
    for body in attempts:
        response = client.post("/api/exports/mark-posted", json=body, headers=H("main"))
        assert response.status_code == 404, (body, response.text)
        assert response.json()["code"] == "resource_not_found"
    assert file_a.exists() and file_b.exists()
    assert _all_rows(env) == before
    # the owner channel can post it; its queue row and post log row are closed in B only
    q_b = client.post("/api/schedule-queue", json={"video_path": str(file_b), "scheduled_at": "2030-01-07T09:00:00+07:00",
                                                   "export_id": rec_b["id"], "product_id": b["id"], "angle_id": "pain_point"},
                      headers=H("second"))
    assert q_b.status_code == 200, q_b.text
    q_a = client.post("/api/schedule-queue", json={"video_path": str(file_a), "scheduled_at": "2030-01-07T09:00:00+07:00",
                                                   "export_id": rec_a["id"]})
    assert q_a.status_code == 200, q_a.text
    a_queue_before = _rows(env, "schedule_queue")[q_a.json()["items"][0]["id"]]
    ok = client.post("/api/exports/mark-posted", json={"file_path": str(file_b), "export_id": rec_b["id"],
                                                       "product_id": b["id"], "angle_id": "pain_point"}, headers=H("second"))
    assert ok.status_code == 200, ok.text
    assert ok.json()["product"]["channel_id"] == "second"
    assert not file_b.exists() and (env / "04_Exports/Posted/b1.mp4").exists()
    assert ExportRegistry.get(rec_b["id"], channel_id="second")["status"] == "posted"
    assert ScheduleQueueStore.get_item(q_b.json()["items"][0]["id"], channel_id="second")["status"] == "posted"
    assert _rows(env, "schedule_queue")[q_a.json()["items"][0]["id"]] == a_queue_before
    posts = PostLog.list_posts(channel_id="second")
    assert [(p["channel_id"], p["export_id"]) for p in posts] == [("second", rec_b["id"])]
    assert PostLog.list_posts(channel_id="main") == []
    assert _rows(env, "export_registry")[rec_a["id"]] == before["export_registry"][rec_a["id"]]


def test_api_mark_posted_reports_ambiguous_legacy_post(client, env):
    post_log_module._TABLE.save(_legacy_posts())
    clip = _write(env, "04_Exports/Ready_to_post/BLU01-โปรไฟลุก_1_20260910_171055.mp4", b"v")
    before_posts = _rows(env, "posts")
    response = client.post("/api/exports/mark-posted", json={"file_path": str(clip)})
    assert response.status_code == 200, response.text
    warning = response.json()["post_log_warning"]
    assert warning["code"] == "post_log_ambiguous" and warning["candidate_post_ids"] == ["dup1", "dup2"]
    assert _rows(env, "posts") == before_posts  # never guessed


def test_api_posted_destination_owned_by_other_channel_is_409(client, env):
    _write(env, "04_Exports/Posted/same.mp4", b"same")
    export_registry._TABLE.save([{"id": "exp_a_posted", "channel_id": "main", "path": "04_Exports/Posted/same.mp4",
                                  "path_key": "04_Exports/Posted/same.mp4", "status": "posted"}])
    src = _write(env, "04_Exports/Ready_to_post/same.mp4", b"same")  # identical bytes: the file check alone would pass
    ExportRegistry.ensure(src, channel_id="second")
    before = _all_rows(env)
    response = client.post("/api/exports/mark-posted", json={"file_path": str(src)}, headers=H("second"))
    assert response.status_code == 409 and response.json()["code"] == "export_path_conflict"
    assert src.exists()
    assert _all_rows(env) == before


def test_api_link_angle_is_scoped(client, env):
    a, b, file_a, file_b, rec_a, rec_b = _two_channel_exports(env)
    before = _all_rows(env)
    for body in (
        {"video_path": "04_Exports/Ready_to_post/b1.mp4", "product_id": a["id"], "angle_id": "pain_point"},
        {"video_path": "04_Exports/Ready_to_post/a1.mp4", "product_id": b["id"], "angle_id": "pain_point"},
        {"video_path": "04_Exports/Ready_to_post/b1.mp4", "export_id": rec_b["id"], "product_id": a["id"], "angle_id": "pain_point"},
    ):
        response = client.post("/api/exports/link-angle", json=body, headers=H("main"))
        assert response.status_code == 404, response.text
        assert response.json()["code"] == "resource_not_found"
    # an unregistered file cannot be claimed by a non-main channel (no provable owner yet)
    _write(env, "04_Exports/Ready_to_post/loose.mp4", b"l")
    loose = client.post("/api/exports/link-angle", json={"video_path": "04_Exports/Ready_to_post/loose.mp4",
                                                         "product_id": b["id"], "angle_id": "pain_point"}, headers=H("second"))
    assert loose.status_code == 404
    assert _all_rows(env) == before
    ok = client.post("/api/exports/link-angle", json={"video_path": "04_Exports/Ready_to_post/b1.mp4",
                                                      "product_id": b["id"], "angle_id": "pain_point"}, headers=H("second"))
    assert ok.status_code == 200, ok.text
    assert ok.json()["product"]["angles"][0]["export_id"] == rec_b["id"]
    archived = client.post("/api/exports/link-angle", json={"video_path": "04_Exports/Ready_to_post/b1.mp4",
                                                            "product_id": b["id"], "angle_id": "pain_point"}, headers=H("old"))
    assert archived.status_code == 409 and archived.json()["code"] == "channel_archived"


def test_api_list_exports_is_scoped(client, env):
    a, b, file_a, file_b, rec_a, rec_b = _two_channel_exports(env)
    _write(env, "04_Exports/Ready_to_post/legacy_loose.mp4", b"l")
    before_registry = _rows(env, "export_registry")
    second = client.get("/api/exports", headers=H("second")).json()["exports"]
    assert [e["name"] for e in second] == ["b1.mp4"]
    assert second[0]["export_id"] == rec_b["id"] and second[0]["product_id"] == b["id"]
    assert _rows(env, "export_registry") == before_registry  # the loose file was NOT claimed for B
    main = client.get("/api/exports").json()["exports"]
    assert sorted(e["name"] for e in main) == ["a1.mp4", "legacy_loose.mp4"]
    assert {e.get("product_id") for e in main if e["name"] == "a1.mp4"} == {a["id"]}
    hydrated = [json.loads(v) for k, v in _rows(env, "export_registry").items() if k not in before_registry]
    assert [(r["path"], r["channel_id"]) for r in hydrated] == [("04_Exports/Ready_to_post/legacy_loose.mp4", "main")]
    explicit = client.get("/api/exports", headers=H("main")).json()
    assert explicit == client.get("/api/exports").json()
    # media-info of another channel's file
    response = client.get("/api/exports/media-info", params={"path": str(file_b)}, headers=H("main"))
    assert response.status_code == 404 and response.json()["code"] == "resource_not_found"


def test_hyperframes_nested_export_gallery_uses_frozen_package_and_schedule(client, env):
    a, b = _products()
    export = _write(env, "04_Exports/Ready_to_post/main/HF_frozen.mp4", b"offline fixture")
    record = ExportRegistry.ensure(export, product_id=a["id"], angle_id="pain_point", project_name="main/HF_frozen", channel_id="main")
    _write(env, "04_Exports/Ready_to_post/second/unregistered.mp4", b"foreign loose file")
    package = {"export_id": record["id"], "caption": "Frozen caption", "hashtags": ["#frozen"], "tiktok_product_id": "basket-frozen",
               "project_name": "main/HF_frozen", "source_binding": {"type": "product_angle", "product_id": a["id"], "angle_id": "pain_point"}, "composition_revision": "rev_one"}
    _write(env, "03_Projects/main/HF_frozen/project.json", json.dumps({"engine": "hyperframes", "channel_id": "main", "project_name": "main/HF_frozen", "publish_package_refs": [package]}).encode())
    rows = client.get("/api/exports", headers=H("main")).json()["exports"]
    assert [row["name"] for row in rows] == ["HF_frozen.mp4"]
    row = rows[0]
    assert row["export_id"] == record["id"] and row["angle_id"] == "pain_point"
    assert row["tiktok_caption"] == "Frozen caption" and row["tiktok_hashtags"] == "#frozen"
    assert row["tiktok_product_id"] == "basket-frozen" and row["composition_revision"] == "rev_one"
    assert row["cover_path"] is None and not row.get("cover_url")
    from scripts.export_cover_bindings import ExportCoverBindingStore
    cover = _write(env, "05_Covers_Thumbnails/main/selection/exact.jpg", b"selected cover")
    binding = ExportCoverBindingStore(env)
    binding.save("main", record["id"], export, selections={"3:4": cover.relative_to(env).as_posix()})
    reloaded = client.get("/api/exports", headers=H("main")).json()["exports"][0]
    assert reloaded["cover_path"] == cover.relative_to(env).as_posix()
    assert reloaded["cover_sha256"] == binding.get("main", record["id"], format="3:4")["sha256"]
    assert reloaded["tiktok_caption"] == "Frozen caption"
    cover.write_bytes(b"changed after selection")
    invalid = client.get("/api/exports", headers=H("main")).json()["exports"][0]
    assert invalid["cover_path"] is None and not invalid.get("cover_url")
    assert invalid["cover_selection_error"] == "export_cover_selection_changed"
    assert client.get("/api/exports", headers=H("second")).json()["exports"] == []
    payload = api_schedule_queue.QueueItemPayload(video_path=str(export.relative_to(env)), export_id=record["id"], product_id=a["id"], angle_id="pain_point", scheduled_at="2026-10-12T12:30:00+07:00")
    path, export_id = api_schedule_queue._resolve_payload_export(payload, "main")
    assert path == export and export_id == record["id"]


def test_legacy_registered_export_uses_exact_selected_cover_after_reload(client, env):
    from scripts.export_cover_bindings import ExportCoverBindingStore
    product, _ = _products()
    export = _write(env, "04_Exports/Ready_to_post/legacy.mp4", b"legacy fixture")
    record = ExportRegistry.ensure(export, product_id=product["id"], angle_id="pain_point", channel_id="main")
    selected = _write(env, "05_Covers_Thumbnails/main/selection/legacy.jpg", b"explicit legacy cover")
    ExportCoverBindingStore(env).save("main", record["id"], export, selections={"9:16": selected.relative_to(env).as_posix()})
    row = client.get("/api/exports", headers=H("main")).json()["exports"][0]
    assert row["cover_path"] == selected.relative_to(env).as_posix()
    selected.write_bytes(b"changed")
    row = client.get("/api/exports", headers=H("main")).json()["exports"][0]
    assert row["cover_path"] is None and row["cover_selection_error"] == "export_cover_selection_changed"


def test_gallery_versions_do_not_merge_distinct_angle_id_aliases(client, env):
    product, _ = _products()
    with ProductStore._scoped_mutate(ProductStore._scope("main", False)) as products:
        row = next(p for p in products if p["id"] == product["id"])
        row["angles"] = [{"id": angle, "script_lines": ["Saved"], "project_name": f"main/HF_{angle}"} for angle in ("a", "b")]
    for angle in ("a", "b"):
        video = _write(env, f"04_Exports/Ready_to_post/main/HF_{angle}.mp4", angle.encode())
        ExportRegistry.ensure(video, product_id=product["id"], angle_id=angle, project_name=f"main/HF_{angle}", channel_id="main")
    rows = client.get("/api/exports", headers=H("main")).json()["exports"]
    assert {row["angle_id"] for row in rows} == {"a", "b"}
    assert all(row["is_latest"] and not row["is_previous_version"] for row in rows)


def test_api_post_log_routes_are_scoped(client, env):
    a = PostLog.add_post(product_name="A", clip_file="a.mp4", channel_id="main")
    b = PostLog.add_post(product_name="B", clip_file="b.mp4", channel_id="second")
    listed = client.get("/api/post-log", headers=H("second")).json()
    assert [p["id"] for p in listed["posts"]] == [b["id"]] and listed["summary"]["total_posted"] == 1
    before = _rows(env, "posts")
    for method, url in (("patch", f"/api/post-log/{a['id']}/metrics"), ("post", f"/api/post-log/{a['id']}/metrics"),
                        ("patch", f"/api/posts/{a['id']}/metrics")):
        response = getattr(client, method)(url, json={"views": 9}, headers=H("second"))
        assert response.status_code == 404 and response.json()["code"] == "resource_not_found"
    missing = client.patch("/api/post-log/nope/metrics", json={"views": 1}, headers=H("second"))
    assert missing.status_code == 404 and "code" not in missing.json()  # unknown id keeps the old response
    assert _rows(env, "posts") == before
    conflict = client.post("/api/post-log", json={"product_name": "x", "clip_file": "x.mp4", "channel_id": "main"},
                           headers=H("second"))
    assert conflict.status_code == 422 and conflict.json()["code"] == "channel_scope_conflict"
    for channel in ("draft1", "old"):
        blocked = client.post("/api/post-log", json={"product_name": "x", "clip_file": "x.mp4"}, headers=H(channel))
        assert blocked.status_code == 409 and blocked.json()["code"] == "channel_not_active"
    assert _rows(env, "posts") == before
    created = client.post("/api/post-log", json={"product_name": "x", "clip_file": "x.mp4"}, headers=H("second"))
    assert created.json()["post"]["channel_id"] == "second"
    assert client.get("/api/posts/summary", headers=H("main")).json()["total_posted"] == 1
    assert client.get("/api/post-log/pending", headers=H("second")).json()["count"] == 0
    # metrics of a post that already happened can still be recorded after archive (ADR §10.4)
    old_post = PostLog.add_post(product_name="O", clip_file="o.mp4", channel_id="old")
    assert client.patch(f"/api/post-log/{old_post['id']}/metrics", json={"views": 3}, headers=H("old")).status_code == 200


def test_api_compat_post_log_byte_identical_on_legacy_data(client, env):
    post_log_module._TABLE.save(_legacy_posts())
    plain = client.get("/api/post-log")
    explicit = client.get("/api/post-log", headers=H("main"))
    assert plain.content == explicit.content
    assert CHANNEL_HEADER.lower() not in {k.lower() for k in plain.headers}
    # identical to the legacy unscoped read
    legacy_rows = sorted(post_log_module._TABLE.load(), key=lambda p: p.get("posted_at", ""), reverse=True)
    assert plain.json()["posts"] == legacy_rows
    assert client.get("/api/post-log", headers=H("second")).json()["posts"] == []


def test_api_strict_mode_requires_scope_and_stats_filter_owner(client, env, monkeypatch):
    row = PostLog.add_post(product_name="A", clip_file="a.mp4", channel_id="main")
    PostLog.update_metrics(row["id"], {"views": 1}, channel_id="main")
    monkeypatch.setenv(STRICT_ENV, "1")
    assert client.get("/api/post-log").status_code == 422
    assert client.get("/api/post-log", headers=H("main")).status_code == 200
    # Converted stats still require a scope and never expose another channel.
    assert client.get("/api/tiktok-stats/latest").status_code == 422
    response = client.get("/api/tiktok-stats/latest", headers=H("main"))
    assert response.status_code == 200
    assert [row["product_name"] for row in response.json()["posts"]] == ["A"]
    assert client.get("/api/tiktok-stats/latest", headers=H("second")).json()["posts"] == []
