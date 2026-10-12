"""Channel-owned products (multi-channel P2.1, plan AC01/AC03).

Store level: two channels with the same product URL, angle label and
angle_id stay two independent products; every write in channel A leaves B's
serialized row byte-identical; URL dedup is per channel while product_code
stays globally unique; legacy rows behave as ``main`` only in compat mode.

API level (``scripts/api_products.py`` through the real app + middleware):
another channel's product is 404 before any side effect, new products are
stamped with the scope, a conflicting body ``channel_id`` is rejected, and
draft/archived channels cannot start new work.

Offline + tmp_path only: products/shot-lists/export-registry/channel registry
are redirected to tmp_path, and every sqlite file opened is asserted to be
under tmp_path.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import api_products, config, db, export_registry, shot_lists_store
from scripts import channel_store as cs
from scripts import product_store as ps
from scripts.channel_scope import CHANNEL_HEADER
from scripts.channel_store import ChannelError
from scripts.product_scraper import ProductScraper
from scripts.product_store import ProductStore

STRICT_ENV = config.MULTI_CHANNEL_STRICT_ENV
URL = "https://shop.tiktok.com/view/product/1729000000000000001"


class FakeMetrics:
    def width_px(self, text, font_file, size):
        return float(len(text) * 10)

    def unsupported_chars(self, text, font_file):
        return cs._fallback_unsupported(text)


def _write(root: Path, rel: str, data: bytes = b"img") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolated stores + registry: main/second active, draft1 draft, old archived."""
    root = tmp_path / "project"
    docs = root / "_Docs"
    docs.mkdir(parents=True)
    (root / "03_Projects").mkdir()
    (root / "04_Exports" / "Ready_to_post").mkdir(parents=True)
    (root / "04_Exports" / "Posted").mkdir(parents=True)

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
    monkeypatch.setattr(export_registry.ExportRegistry, "_path_index", None, raising=False)
    monkeypatch.setattr(shot_lists_store, "STORE_PATH", docs / "shot_lists.json")
    monkeypatch.setattr(api_products, "BASE_DIR", root)
    monkeypatch.setattr(api_products, "RAW_DIR", root / "01_Raw")
    monkeypatch.setattr(ProductStore, "_last_reconcile_scope", None)
    monkeypatch.delenv(STRICT_ENV, raising=False)

    # channel registry (P1 test pattern)
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


def _rows(root: Path) -> dict:
    conn = sqlite3.connect(str(root / "_Docs" / "store.db"))
    try:
        return {row[0]: row[1] for row in conn.execute("SELECT id, data FROM products")}
    finally:
        conn.close()


def _mirror(root: Path) -> dict:
    data = json.loads((root / "_Docs" / "products.json").read_text(encoding="utf-8"))
    return {r["id"]: json.dumps(r, ensure_ascii=False, sort_keys=True) for r in data}


def _angle(angle_id="pain_point", **extra):
    return {"angle_id": angle_id, "angle_name": "ปัญหาก่อนใช้", "script_lines": ["บรรทัดแรก"], **extra}


def _pair(root: Path):
    a = ProductStore.add("JBL Go 4", url=URL, angles=[_angle()], channel_id="main")
    b = ProductStore.add("JBL Go 4", url=URL, angles=[_angle()], channel_id="second")
    return a, b


# =========================================================================== store level


def test_same_url_label_and_angle_id_are_two_products(env):
    a, b = _pair(env)
    assert a["id"] != b["id"]
    assert (a["channel_id"], b["channel_id"]) == ("main", "second")
    assert a["angles"][0]["angle_id"] == b["angles"][0]["angle_id"] == "pain_point"
    # product_code unique across channels
    assert {a["product_code"], b["product_code"]} == {"JBL01", "JBL02"}
    # per-channel URL dedup: re-adding in B returns B's product and never touches A
    before_a = _rows(env)[a["id"]]
    again = ProductStore.add("JBL Go 4", url=URL, angles=[_angle("unboxing")], channel_id="second")
    assert again["id"] == b["id"]
    assert [x["angle_id"] for x in again["angles"]] == ["unboxing"]
    assert _rows(env)[a["id"]] == before_a
    assert [x["id"] for x in ProductStore.list(channel_id="main")] == [a["id"]]
    assert [x["id"] for x in ProductStore.list(channel_id="second")] == [b["id"]]


@pytest.mark.parametrize(
    "operation",
    [
        "update",
        "update_angle_status",
        "update_angle_status_same_video",
        "replace_angle_content",
        "append_angles",
        "update_angle_videos",
        "update_angle_voice",
        "manual_shot_map",
        "batch_manual_shot_maps",
        "default_videos",
        "add_video",
        "remove_video",
        "remove_angle",
        "remove_last_angle",
        "rollback",
        "attach_project",
        "delete",
    ],
)
def test_writes_in_one_channel_leave_the_other_byte_identical(env, operation):
    a, b = _pair(env)
    video = "04_Exports/Ready_to_post/JBL01-pain_1.mp4"
    # B's angle claims the same rendered file name as the one A is about to bind
    ProductStore.update_angle_status(b["id"], "pain_point", "rendered", video_url=video, channel_id="second")
    ProductStore.add_video_to_product(b["id"], {"path": "01_Raw/clip.mp4"}, channel_id="second")
    ProductStore.add_video_to_product(a["id"], {"path": "01_Raw/clip.mp4"}, channel_id="main")
    if operation == "rollback":
        ProductStore.update_angle_status(a["id"], "pain_point", "rendered", video_url=video, channel_id="main")
    if operation == "remove_angle":
        ProductStore.append_angles(a["id"], [_angle("unboxing")], channel_id="main")
    b_before = _rows(env)[b["id"]]
    b_mirror_before = _mirror(env)[b["id"]]

    pid = a["id"]
    calls = {
        "update": lambda: ProductStore.update(pid, name="ใหม่", status="scripted", channel_id="main"),
        "update_angle_status": lambda: ProductStore.update_angle_status(pid, "pain_point", "in_production", channel_id="main"),
        "update_angle_status_same_video": lambda: ProductStore.update_angle_status(
            pid, "pain_point", "rendered", video_url=video, channel_id="main"
        ),
        "replace_angle_content": lambda: ProductStore.replace_angle_content(
            pid, "pain_point", {"script_lines": ["ใหม่"]}, channel_id="main"
        ),
        "append_angles": lambda: ProductStore.append_angles(pid, [_angle("pain_point")], channel_id="main"),
        "update_angle_videos": lambda: ProductStore.update_angle_videos(pid, "pain_point", ["01_Raw/x.mp4"], channel_id="main"),
        "update_angle_voice": lambda: ProductStore.update_angle_voice(pid, "pain_point", voice_preset="Fenrir", channel_id="main"),
        "manual_shot_map": lambda: ProductStore.update_angle_manual_shot_map(
            pid, "pain_point", [{"beat_index": 0, "video_path": "01_Raw/x.mp4"}], channel_id="main"
        ),
        "batch_manual_shot_maps": lambda: ProductStore.batch_update_manual_shot_maps(
            pid, {"pain_point": [{"beat_index": 0}]}, channel_id="main"
        ),
        "default_videos": lambda: ProductStore.set_default_videos_for_all_angles(pid, ["01_Raw/x.mp4"], channel_id="main"),
        "add_video": lambda: ProductStore.add_video_to_product(pid, {"path": "01_Raw/y.mp4"}, channel_id="main"),
        "remove_video": lambda: ProductStore.remove_video_from_product(pid, "01_Raw/clip.mp4", channel_id="main"),
        "remove_angle": lambda: ProductStore.remove_angle(pid, "unboxing_b2", channel_id="main"),
        "remove_last_angle": lambda: ProductStore.remove_angle(pid, "pain_point", channel_id="main"),
        "rollback": lambda: ProductStore.rollback_by_video_or_project("JBL01-pain_1.mp4", channel_id="main"),
        "attach_project": lambda: ProductStore.attach_project(pid, "JBL01-pain_1", channel_id="main"),
        "delete": lambda: ProductStore.delete(pid, channel_id="main"),
    }
    calls[operation]()
    assert _rows(env)[b["id"]] == b_before
    assert _mirror(env)[b["id"]] == b_mirror_before
    if operation == "update_angle_status_same_video":
        # the "one rendered file -> one angle" unbind stays inside the channel
        assert json.loads(b_before)["angles"][0]["video_url"] == video
    if operation == "rollback":
        assert ProductStore.find(pid, channel_id="main")["angles"][0]["video_url"] is None


def test_other_channel_ids_look_missing(env):
    a, b = _pair(env)
    before = _rows(env)
    assert ProductStore.get(b["id"], channel_id="main") is None
    assert ProductStore.find(b["id"], channel_id="main") is None
    assert ProductStore.get_product_videos(b["id"], channel_id="main") == []
    for call in (
        lambda: ProductStore.update(b["id"], name="x", channel_id="main"),
        lambda: ProductStore.update_angle_status(b["id"], "pain_point", "scripted", channel_id="main"),
        lambda: ProductStore.append_angles(b["id"], [_angle("x")], channel_id="main"),
        lambda: ProductStore.remove_angle(b["id"], "pain_point", channel_id="main"),
        lambda: ProductStore.delete(b["id"], channel_id="main"),
        lambda: ProductStore.attach_project(b["id"], "p", channel_id="main"),
    ):
        with pytest.raises(ValueError, match="ไม่พบ"):
            call()
    assert ProductStore.rollback_by_video_or_project("x", product_id=b["id"], angle_id="pain_point", channel_id="main") == []
    assert ProductStore.find_by_project("JBL02-x_1", product_id=b["id"], channel_id="main") == (None, None)
    assert _rows(env) == before
    assert ProductStore.owner_of(b["id"]) == (True, "second")
    assert ProductStore.owner_of("nope") == (False, None)


def test_child_owner_must_match_parent(env):
    a, _b = _pair(env)
    before = _rows(env)
    with pytest.raises(ChannelError) as info:
        ProductStore.update(a["id"], angles=[_angle(channel_id="second")], channel_id="main")
    assert info.value.code == "channel_child_mismatch"
    with pytest.raises(ChannelError):
        ProductStore.append_angles(a["id"], [_angle("y", channel_id="second")], channel_id="main")
    with pytest.raises(ChannelError):
        ProductStore.add("ใหม่", url="https://shop.tiktok.com/view/product/1729000000000000999",
                         angles=[_angle(channel_id="second")], channel_id="main")
    assert _rows(env) == before
    # repeating the parent's own owner on a child is fine
    ProductStore.update(a["id"], angles=[_angle(channel_id="main")], channel_id="main")


def test_scope_is_never_a_writable_field(env):
    a, _b = _pair(env)
    # channel_id is consumed as the SCOPE keyword: passing B's id as "data"
    # just scopes the call to B, where A's product does not exist.
    with pytest.raises(ValueError):
        ProductStore.update(a["id"], **{"channel_id": "second", "name": "x"})
    assert ProductStore.find(a["id"], channel_id="main")["channel_id"] == "main"
    with pytest.raises(ValueError):
        ProductStore.apply_to_each_product(lambda p: p.update(channel_id="second"), channel_id="main")
    assert ProductStore.find(a["id"], channel_id="main")["channel_id"] == "main"


def test_canonical_product_fields(env):
    a = ProductStore.add("JBL Go 4", url=URL, canonical_product_key="jbl-go-4", channel_id="main")
    b = ProductStore.add(
        "JBL Go 4", url=URL, canonical_product_key="jbl-go-4", source_product_id=a["id"], channel_id="second"
    )
    assert a["canonical_product_key"] == b["canonical_product_key"] == "jbl-go-4"
    assert b["source_product_id"] == a["id"] and "source_product_id" not in a
    plain = ProductStore.add("Other", channel_id="main")
    assert "canonical_product_key" not in plain and "source_product_id" not in plain
    with pytest.raises(ValueError):
        ProductStore.add("Bad", canonical_product_key=123, channel_id="main")
    with pytest.raises(ValueError):
        ProductStore.update(a["id"], canonical_product_key="x" * 201, channel_id="main")


def test_code_generation_counts_every_channel_and_legacy(env):
    ps._TABLE.save([{"id": "legacy", "name": "Anker", "product_code": "ANK07", "angles": []}])
    first = ProductStore.add("Anker Nano", channel_id="second")
    assert first["product_code"] == "ANK08"
    ProductStore._save(ProductStore._load() + [
        {"id": "nocode1", "channel_id": "main", "name": "Anker A", "created_at": "2026-01-01"},
        {"id": "nocode2", "channel_id": "second", "name": "Anker B", "created_at": "2026-01-02"},
    ])
    preview = ProductStore.backfill_missing_product_codes(all_channels=True, dry_run=True)
    assert [x["product_code"] for x in preview] == ["ANK09", "ANK10"]
    assert ProductStore.find("nocode1", channel_id="main").get("product_code") is None
    assert ProductStore.backfill_missing_product_codes(all_channels=True) == preview
    codes = [p["product_code"] for p in ProductStore.snapshot(all_channels=True)]
    assert len(codes) == len(set(codes))


def test_compat_legacy_rows_belong_to_main_only_without_strict(env, monkeypatch):
    legacy = {"id": "legacy1", "name": "Old", "url": URL, "angles": [_angle()], "status": "scripted"}
    ps._TABLE.save([legacy])
    assert ProductStore.snapshot(channel_id="main") == ProductStore.snapshot() == [legacy]
    assert ProductStore.snapshot(channel_id="second") == []
    # main (compat) may edit a legacy row; it stays legacy (no owner stamped)
    ProductStore.update_angle_status("legacy1", "pain_point", "in_production", channel_id="main")
    stored = json.loads(_rows(env)["legacy1"])
    assert "channel_id" not in stored
    # same URL in compat main dedups into the legacy row; in B it is a new product
    assert ProductStore.add("Old", url=URL, channel_id="main")["id"] == "legacy1"
    assert ProductStore.add("Old", url=URL, channel_id="second")["id"] != "legacy1"
    # compat channel_id=None still sees everything (old behaviour) and creates main rows
    assert len(ProductStore.snapshot()) == 2
    created = ProductStore.add("New", url="https://shop.tiktok.com/view/product/1729000000000000002")
    assert created["channel_id"] == "main"

    monkeypatch.setenv(STRICT_ENV, "1")
    with pytest.raises(ChannelError) as info:
        ProductStore.list()
    assert info.value.code == "channel_scope_missing"
    with pytest.raises(ChannelError):
        ProductStore.update("legacy1", name="x")
    assert [p["id"] for p in ProductStore.snapshot(channel_id="main")] == [created["id"]]
    before = _rows(env)["legacy1"]
    with pytest.raises(ValueError):
        ProductStore.update("legacy1", name="x", channel_id="main")
    assert _rows(env)["legacy1"] == before
    assert len(ProductStore.snapshot(all_channels=True)) == 3


def test_reconcile_is_scoped(env):
    a, b = _pair(env)
    projects = env / "03_Projects"
    # a folder whose manifest names B's product
    folder_b = projects / "JBL02-pain_1"
    folder_b.mkdir()
    (folder_b / "project.json").write_text(
        json.dumps({"render_params": {"product_id": b["id"], "angle_id": "pain_point"}}), encoding="utf-8"
    )
    # an id-less folder that BOTH channels' angles claim by project_name
    shared = projects / "Shared_1"
    shared.mkdir()
    (shared / "project.json").write_text("{}", encoding="utf-8")
    ProductStore.update_angle_status(a["id"], "pain_point", "in_production", project_name="Shared_1", channel_id="main")
    ProductStore.update_angle_status(b["id"], "pain_point", "in_production", project_name="Shared_1", channel_id="second")
    b_before = _rows(env)[b["id"]]
    ProductStore._last_reconcile_scope = None
    ProductStore.reconcile_existing_projects(channel_id="main")
    assert _rows(env)[b["id"]] == b_before
    a_after = ProductStore.find(a["id"], channel_id="main")
    assert a_after["angles"][0]["project_name"] == "Shared_1"
    assert "JBL02-pain_1" not in (a_after.get("projects") or [])
    # B's own reconcile links its own manifest folder
    ProductStore._last_reconcile_scope = None
    ProductStore.reconcile_existing_projects(channel_id="second")
    assert "JBL02-pain_1" in ProductStore.find(b["id"], channel_id="second")["projects"]


def test_update_invalidates_shot_list_after_commit(env):
    """P0-B nested-write hazard: the shot-list delete used to run inside the
    products transaction on the same connection, fail, and be swallowed."""
    from scripts.shot_lists_store import ShotListsStore

    a, _b = _pair(env)
    ShotListsStore.upsert({"product_id": a["id"], "angle_id": "pain_point", "shots": [1]}, batch=1)
    assert ShotListsStore.get(a["id"], "pain_point", batch=1) is not None
    ProductStore.update(a["id"], angles=[_angle(script_lines=["เปลี่ยนบท"])], channel_id="main")
    assert ShotListsStore.get(a["id"], "pain_point", batch=1) is None


def test_hand_edited_mirror_import_keeps_channels(env):
    a, b = _pair(env)
    mirror = env / "_Docs" / "products.json"
    data = json.loads(mirror.read_text(encoding="utf-8"))
    data.append({"id": "imported", "channel_id": "second", "name": "Imported", "angles": [], "url": "u"})
    mirror.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert sorted(p["id"] for p in ProductStore.snapshot(channel_id="second")) == sorted([b["id"], "imported"])
    assert [p["id"] for p in ProductStore.snapshot(channel_id="main")] == [a["id"]]


def test_maintenance_helpers(env):
    a, b = _pair(env)
    ProductStore.add_video_to_product(a["id"], {"path": "01_Raw/old.mp4"}, channel_id="main")
    ProductStore.add_video_to_product(b["id"], {"path": "01_Raw/old.mp4"}, channel_id="second")
    b_before = _rows(env)[b["id"]]
    info = {"path": "01_Raw/new.mp4", "rel_path": "01_Raw/new.mp4", "name": "new.mp4"}
    assert ProductStore.rename_video_references(
        old_abs="nope", old_rel="01_Raw/old.mp4", old_name="old.mp4", new_info=info, channel_id="main"
    ) == 1
    assert _rows(env)[b["id"]] == b_before
    assert ProductStore.remove_video_references(lambda v: v.get("rel_path") == "01_Raw/old.mp4", channel_id="main") == 0
    assert ProductStore.remove_video_references(lambda v: v.get("rel_path") == "01_Raw/old.mp4", all_channels=True) == 1
    ProductStore.update_angle_status(b["id"], "pain_point", "posted", project_name="P_1",
                                     export_id=None, channel_id="second")
    assert ProductStore.has_posted_angle_for_project("P_1", channel_id="second")
    assert not ProductStore.has_posted_angle_for_project("P_1", channel_id="main")
    assert ProductStore.has_posted_angle_for_project("P_1")  # compat None = all rows


# =========================================================================== API level


def H(channel: str) -> dict:
    return {CHANNEL_HEADER: channel}


@pytest.fixture()
def client(env, monkeypatch):
    def fake_scrape(url):
        return {"title": "JBL Go 4", "url": url, "platform": "tiktok", "description": "ลำโพง",
                "raw_text": "ลำโพง", "price_note": "", "images": [], "metadata_source": "html"}

    def fake_matrix(product_info, count=10, **kwargs):
        return [_angle()]

    monkeypatch.setattr(ProductScraper, "scrape_url", staticmethod(fake_scrape))
    monkeypatch.setattr(ProductScraper, "generate_content_matrix", staticmethod(fake_matrix))
    from scripts.api_server import app

    return TestClient(app)


def test_api_create_stamps_owner_and_dedups_per_channel(client, env):
    second = client.post("/api/products/scrape-and-plan", json={"url": URL}, headers=H("second"))
    assert second.status_code == 200, second.text
    saved_b = second.json()["saved_product"]
    assert saved_b["channel_id"] == "second"
    main = client.post("/api/products/scrape-and-plan", json={"url": URL})
    assert main.status_code == 200
    saved_a = main.json()["saved_product"]
    assert saved_a["channel_id"] == "main" and saved_a["id"] != saved_b["id"]
    assert {saved_a["product_code"], saved_b["product_code"]} == {"JBL01", "JBL02"}


def test_api_body_channel_mismatch_is_rejected(client, env):
    response = client.post("/api/products/scrape-and-plan", json={"url": URL, "channel_id": "main"}, headers=H("second"))
    assert response.status_code == 422
    assert response.json()["code"] == "channel_scope_conflict"
    assert ProductStore.snapshot(all_channels=True) == []


@pytest.mark.parametrize("channel,code", [("draft1", "channel_not_active"), ("old", "channel_not_active")])
def test_api_new_work_needs_active_channel(client, env, channel, code):
    response = client.post("/api/products/scrape-and-plan", json={"url": URL}, headers=H(channel))
    assert response.status_code == 409
    assert response.json()["code"] == code
    assert ProductStore.snapshot(all_channels=True) == []


def test_api_archived_channel_is_read_only(client, env):
    product = ProductStore.add("Old", angles=[_angle()], channel_id="old")
    before = _rows(env)
    response = client.patch(
        f"/api/products/{product['id']}/angles/pain_point", json={"status": "scripted"}, headers=H("old")
    )
    assert response.status_code == 409 and response.json()["code"] == "channel_archived"
    assert client.get(f"/api/products/{product['id']}/scene-catalogs", headers=H("old")).status_code == 200
    assert _rows(env) == before


def test_api_other_channel_product_is_404_without_side_effects(client, env):
    a, b = _pair(env)
    raw_dir = env / "01_Raw" / b["id"]
    raw_dir.mkdir(parents=True)
    clip = raw_dir / "clip.mp4"
    clip.write_bytes(b"x")
    before = _rows(env)
    attempts = [
        ("patch", f"/api/products/{b['id']}/angles/pain_point", {"json": {"status": "scripted"}}),
        ("post", f"/api/products/{b['id']}/angles", {"json": {"angle": _angle("x")}}),
        ("delete", f"/api/products/{b['id']}/angles/pain_point", {}),
        ("delete", f"/api/products/{b['id']}/videos", {"params": {"video_path": str(clip)}}),
        ("post", f"/api/products/{b['id']}/default-videos", {"json": {"selected_videos": []}}),
        ("post", f"/api/products/{b['id']}/angles/pain_point/videos", {"json": {"selected_videos": []}}),
        ("get", f"/api/products/{b['id']}/scene-catalogs", {}),
        ("post", f"/api/products/{b['id']}/generate-batch", {"json": {}}),
        ("post", f"/api/products/{b['id']}/angles/pain_point/reroll-script", {"json": {}}),
        ("post", f"/api/products/{b['id']}/preview-source", {"json": {}}),
        ("post", f"/api/products/{b['id']}/refresh-source", {"json": {}}),
    ]
    for method, url, kwargs in attempts:
        response = getattr(client, method)(url, headers=H("main"), **kwargs)
        assert response.status_code == 404, (url, response.text)
        assert response.json()["code"] == "resource_not_found", url
    assert clip.exists()  # the unlink route never moved B's file
    assert _rows(env) == before
    # the owner still reaches its product
    ok = client.patch(f"/api/products/{b['id']}/angles/pain_point", json={"status": "in_production"}, headers=H("second"))
    assert ok.status_code == 200 and ok.json()["product"]["channel_id"] == "second"
    assert _rows(env)[a["id"]] == before[a["id"]]


def test_api_compat_no_header_equals_explicit_main_on_legacy_data(client, env):
    legacy = {"id": "legacy1", "name": "Old", "url": URL, "status": "scripted",
              "angles": [_angle(status="scripted")], "videos": [], "projects": []}
    ps._TABLE.save([legacy])
    plain = client.post("/api/products/legacy1/angles/pain_point/videos", json={"selected_videos": ["01_Raw/a.mp4"]})
    assert plain.status_code == 200
    assert CHANNEL_HEADER.lower() not in {k.lower() for k in plain.headers}
    ps._TABLE.save([legacy])
    scoped = client.post(
        "/api/products/legacy1/angles/pain_point/videos", json={"selected_videos": ["01_Raw/a.mp4"]}, headers=H("main")
    )
    strip = lambda body: json.dumps({**body, "product": {**body["product"], "updated_at": None,  # noqa: E731
                                     "angles": [{**x, "updated_at": None} for x in body["product"]["angles"]]}},
                                    sort_keys=True, ensure_ascii=False)
    assert strip(plain.json()) == strip(scoped.json())
    assert "channel_id" not in plain.json()["product"]  # legacy row not stamped
    assert client.post("/api/products/legacy1/angles/pain_point/videos", json={"selected_videos": []},
                       headers=H("second")).status_code == 404


def test_api_strict_mode(client, env, monkeypatch):
    a, _b = _pair(env)
    monkeypatch.setenv(STRICT_ENV, "1")
    response = client.get(f"/api/products/{a['id']}/scene-catalogs")
    assert response.status_code == 422 and response.json()["code"] == "channel_scope_missing"
    assert client.get(f"/api/products/{a['id']}/scene-catalogs", headers=H("main")).status_code == 200
    assert client.get(f"/api/products/{a['id']}/scene-catalogs", headers=H("second")).status_code == 404


def test_api_angle_child_channel_mismatch(client, env):
    a, _b = _pair(env)
    response = client.post(
        f"/api/products/{a['id']}/angles", json={"angle": _angle("x", channel_id="second")}, headers=H("main")
    )
    assert response.status_code == 422 and response.json()["code"] == "channel_child_mismatch"
