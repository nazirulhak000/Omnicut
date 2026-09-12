"""TikTok Studio stats import — offline tests with tmp storage only."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import post_log as post_log_module
from scripts.api_server import app


@pytest.fixture
def isolated_log(tmp_path, monkeypatch):
    target = tmp_path / "post_log.json"
    monkeypatch.setattr(post_log_module, "LOG_PATH", target)
    monkeypatch.setattr(post_log_module._TABLE, "_json_path_fn", lambda: target)
    monkeypatch.setattr(post_log_module._TABLE, "_db_path_fn", lambda: tmp_path / "store.db")
    return target


@pytest.fixture
def client():
    return TestClient(app)


def test_import_matches_exact_video_id(isolated_log, client, monkeypatch):
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [])
    post_log_module.PostLog.add_post(product_name="Logitech Lift", clip_file="lift.mp4", angle_title="สเปกเทพ Logitech Lift")
    posts = post_log_module.PostLog.list_posts()
    assert len(posts) == 1
    posts[0]["tiktok_video_id"] = "7684239800701816081"
    post_log_module.PostLog._save(posts)

    resp = client.post("/api/tiktok-stats/import", json={"rows": [{
        "title": "สเปกเทพ Logitech Lift", "views": 51, "likes": 3, "comments": 0,
        "video_id": "7684239800701816081", "video_url": "https://www.tiktok.com/@u/video/7684239800701816081",
    }]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] == 1
    assert data["updated"] == 1
    assert data["unmatched"] == []
    stored = post_log_module.PostLog.list_posts()[0]
    assert stored["metrics"]["views"] == 51
    assert stored["tiktok_url"].endswith("7684239800701816081")


def test_import_fuzzy_matches_title_and_skips_unknown(isolated_log, client, monkeypatch):
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [])
    post_log_module.PostLog.add_post(product_name="BlueWOW", clip_file="x110.mp4", angle_title="ด่วน BlueWOW X110 Ultra")

    resp = client.post("/api/tiktok-stats/import", json={"rows": [
        {"title": "ด่วน BlueWOW X110 Ultra ท็อป", "views": 268, "likes": 9, "comments": 0},
        {"title": "คลิปคนอื่นที่ไม่เกี่ยวเลย xyz", "views": 5, "likes": 0},
    ]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] == 1
    assert len(data["unmatched"]) == 1
    assert data["unmatched"][0]["title"].startswith("คลิปคนอื่น")


def test_import_rejects_empty_and_oversized(isolated_log, client):
    resp = client.post("/api/tiktok-stats/import", json={"rows": []})
    assert resp.status_code == 400
    resp = client.post("/api/tiktok-stats/import", json={"rows": [{"title": "", "video_id": ""}]})
    assert resp.status_code == 400
    resp = client.post("/api/tiktok-stats/import", json={"rows": [{"title": f"x{i}"} for i in range(201)]})
    assert resp.status_code == 400


def test_latest_returns_synced_first(isolated_log, client, monkeypatch):
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [])
    post_log_module.PostLog.add_post(product_name="A", clip_file="a.mp4")
    post_log_module.PostLog.add_post(product_name="B", clip_file="b.mp4", angle_title="ด่วน BlueWOW X110 Ultra")
    client.post("/api/tiktok-stats/import", json={"rows": [{"title": "ด่วน BlueWOW X110 Ultra", "views": 268}]})
    resp = client.get("/api/tiktok-stats/latest")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_import_auto_registers_post_from_clip_candidates(isolated_log, client, monkeypatch):
    """Studio caption (tags/emoji included) + Thai posted date + a clip that
    was never marked posted in OmniCut -> auto-register from the candidate."""
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [{
        "hook_title": "แกะกล่องป้ายยา ESSAGER สายชาร์จแม่เหล็ก ทางที่ดีที่สุด",
        "product_name": "ESSAGER ป้ายยาแท็กติดตัว",
        "angle_title": "แกะกล่องป้ายยา ESSAGER สายชาร์จแม่เหล็ก ทางที่ดีที่สุด",
        "angle_key": "angle_1", "clip_file": "20260811_ESSAGER_v1.mp4", "duration_sec": None,
    }])
    resp = client.post("/api/tiktok-stats/import", json={"rows": [{
        "title": "แกะกล่องป้ายยา ESSAGER สายชาร์จแม่เหล็ก งานดีพรีเมียมสุดๆ พิกัดในตะกร้าเลย #แกะกล่องรีวิว #ESSAGER #สายชาร์จแม่เหล็ก",
        "posted_text": "11 ส.ค. 9:30 PM",
        "views": 4, "likes": 1, "comments": 0, "duration_sec": 25,
        "video_id": "7684239800701816081",
        "video_url": "https://www.tiktok.com/@u/video/7684239800701816081",
    }]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["registered"] == 1
    assert data["matched"] == 1
    assert data["updated"] == 1
    assert data["unmatched"] == []
    stored = post_log_module.PostLog.list_posts()
    assert len(stored) == 1
    post = stored[0]
    assert post["product_name"].startswith("ESSAGER")
    assert post["source"] == "tiktok_stats_auto"
    assert post["tiktok_video_id"] == "7684239800701816081"
    assert post["metrics"]["views"] == 4
    assert post["posted_at"].endswith("-08-11T21:30:00")


def test_no_auto_register_when_nothing_matches(isolated_log, client, monkeypatch):
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [{
        "hook_title": "แกะกล่องป้ายยา ESSAGER", "product_name": "ESSAGER",
        "angle_title": "แกะกล่องป้ายยา ESSAGER", "clip_file": "a.mp4",
    }])
    resp = client.post("/api/tiktok-stats/import", json={"rows": [{
        "title": "คลิปของคนอื่นโดยสิ้นเชิง ไม่มีคำซ้อนกันเลย", "views": 3,
    }]})
    data = resp.json()
    assert data["registered"] == 0
    assert data["matched"] == 0
    assert len(data["unmatched"]) == 1
    assert post_log_module.PostLog.list_posts() == []


def test_existing_post_preferred_over_auto_register(isolated_log, client, monkeypatch):
    from scripts import api_tiktok_stats
    post_log_module.PostLog.add_post(product_name="BlueWOW", clip_file="x110.mp4", angle_title="ด่วน BlueWOW X110 Ultra")
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [{
        "hook_title": "ด่วน BlueWOW X110 Ultra", "product_name": "BlueWOW",
        "angle_title": "ด่วน BlueWOW X110 Ultra", "clip_file": "x110_export.mp4",
    }])
    resp = client.post("/api/tiktok-stats/import", json={"rows": [{"title": "ด่วน BlueWOW X110 Ultra", "views": 268}]})
    data = resp.json()
    assert data["matched"] == 1
    assert data["registered"] == 0
    assert len(post_log_module.PostLog.list_posts()) == 1


def test_parse_studio_posted_at_variants():
    parse = post_log_module.PostLog._parse_studio_posted_at
    assert parse("11 ส.ค. 9:30 PM").endswith("-08-11T21:30:00")
    assert parse("10 ส.ค. 7:00 PM").endswith("-08-10T19:00:00")
    assert parse("10 ธ.ค. 12:30 PM").endswith("-12-10T12:30:00")
    assert parse("8 ก.ย. 7:35 AM").endswith("-09-08T07:35:00")
    assert parse("11 ก.ย. 7:00") is not None
    assert parse("") is None
    assert parse("ไม่มีวันที่") is None


def test_import_never_merges_two_similar_rows_into_one_post(isolated_log, client, monkeypatch):
    """Regression (TIKTOK-DASH-DATA-1): two Studio rows with similar captions
    (same product, different clips) used to fuzzy-match the same target and
    the later row's metrics overwrote the first row's real numbers
    (Logitech Lift 59 views -> 370). Each row must own its own post."""
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [
        {"hook_title": "รีวิว Logitech Lift เมาส์แนวตั้ง", "product_name": "Logitech Lift",
         "angle_title": "รีวิว Logitech Lift เมาส์แนวตั้ง", "angle_key": "a1",
         "clip_file": "lift_v1.mp4", "duration_sec": None},
        {"hook_title": "เมาส์แนวตั้ง Logitech Lift ลดราคา", "product_name": "Logitech Lift",
         "angle_title": "เมาส์แนวตั้ง Logitech Lift ลดราคา", "angle_key": "a2",
         "clip_file": "lift_v2.mp4", "duration_sec": None},
    ])
    resp = client.post("/api/tiktok-stats/import", json={"rows": [
        {"title": "รีวิว Logitech Lift เมาส์แนวตั้ง ปวดข้อมือหายทันที",
         "views": 59, "likes": 5, "comments": 0,
         "video_id": "vid_A", "video_url": "https://www.tiktok.com/@u/video/vid_A"},
        {"title": "รีวิว Logitech Lift เมาส์แนวตั้ง ถูกสุดในตลาด",
         "views": 370, "likes": 5, "comments": 0,
         "video_id": "vid_B", "video_url": "https://www.tiktok.com/@u/video/vid_B"},
    ]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] == 2
    assert data["registered"] == 2
    assert data["unmatched"] == []
    posts = post_log_module.PostLog.list_posts()
    assert len(posts) == 2
    views = {p["metrics"]["views"] for p in posts}
    assert views == {59, 370}
    assert {p["tiktok_video_id"] for p in posts} == {"vid_A", "vid_B"}


@pytest.fixture
def isolated_pending(tmp_path, monkeypatch):
    from scripts import tiktok_pending as pend
    from scripts.db import DocumentTable
    p_json = tmp_path / "tiktok_pending.json"
    p_db = tmp_path / "store_pending.db"
    table = DocumentTable("tiktok_pending", lambda: p_db, lambda: p_json)
    monkeypatch.setattr(pend, "_TABLE", table)
    return pend


def test_unmatched_rows_persisted_for_manual_match(isolated_log, isolated_pending, client, monkeypatch):
    """Unmatched Studio rows must survive the side panel closing: they land
    in the pending store, matched rows must not."""
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [])
    post_log_module.PostLog.add_post(product_name="BlueWOW", clip_file="x110.mp4", angle_title="ด่วน BlueWOW X110 Ultra")
    resp = client.post("/api/tiktok-stats/import", json={"rows": [
        {"title": "ด่วน BlueWOW X110 Ultra ท็อป", "views": 268, "likes": 9, "comments": 0,
         "video_id": "vid_ok"},
        {"title": "แกะกล่องป้ายยา ESSAGER สายชาร์จแม่เหล็ก", "views": 12, "likes": 1,
         "video_id": "vid_essager", "video_url": "https://www.tiktok.com/@u/video/vid_essager"},
    ]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] == 1
    assert len(data["unmatched"]) == 1

    pend = client.get("/api/tiktok-stats/pending")
    assert pend.status_code == 200
    rows = pend.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["video_id"] == "vid_essager"
    assert rows[0]["title"].startswith("แกะกล่อง")


def test_attach_registers_post_from_candidate_and_clears_pending(isolated_log, isolated_pending, client, monkeypatch):
    """Manual match: pending row + library clip -> post with real metrics,
    pending row consumed, and the post shows up in /latest."""
    from scripts import api_tiktok_stats
    cands_list = []
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: cands_list)
    client.post("/api/tiktok-stats/import", json={"rows": [{
        "title": "แกะกล่องป้ายยา ESSAGER สายชาร์จแม่เหล็ก #ESSAGER",
        "views": 12, "likes": 1, "comments": 0,
        "video_id": "vid_essager", "video_url": "https://www.tiktok.com/@u/video/vid_essager",
        "posted_text": "11 ส.ค. 9:30 PM",
    }]})
    pending = client.get("/api/tiktok-stats/pending").json()["rows"]
    assert len(pending) == 1
    cands_list.append({
        "hook_title": "แกะกล่องป้ายยา ESSAGER สายชาร์จแม่เหล็ก",
        "product_name": "ESSAGER ป้ายยาแท็กติดตัว",
        "angle_title": "แกะกล่องป้ายยา ESSAGER สายชาร์จแม่เหล็ก",
        "angle_key": "angle_1", "clip_file": "20260811_ESSAGER_v1.mp4", "duration_sec": None,
    })
    cands = client.get("/api/tiktok-stats/clip-candidates").json()["candidates"]
    assert len(cands) == 1

    resp = client.post("/api/tiktok-stats/attach", json={
        "pending_id": pending[0]["id"],
        "candidate": cands[0],
    })
    assert resp.status_code == 200
    assert resp.json()["remaining"] == 0

    stored = post_log_module.PostLog.list_posts()
    assert len(stored) == 1
    post = stored[0]
    assert post["product_name"].startswith("ESSAGER")
    assert post["source"] == "tiktok_stats_manual"
    assert post["tiktok_video_id"] == "vid_essager"
    assert post["metrics"]["views"] == 12
    assert post["posted_at"].endswith("-08-11T21:30:00")

    latest = client.get("/api/tiktok-stats/latest").json()
    assert latest["count"] == 1

    again = client.post("/api/tiktok-stats/attach", json={"pending_id": "nope"})
    assert again.status_code == 404


def test_attach_requires_target_and_ignore_drops_row(isolated_log, isolated_pending, client, monkeypatch):
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda: [])
    client.post("/api/tiktok-stats/import", json={"rows": [{"title": "คลิปคนอื่น xyz", "views": 3}]})
    pending = client.get("/api/tiktok-stats/pending").json()["rows"]
    assert len(pending) == 1

    bad = client.post("/api/tiktok-stats/attach", json={"pending_id": pending[0]["id"]})
    assert bad.status_code == 400

    ign = client.post("/api/tiktok-stats/pending/ignore", json={"pending_id": pending[0]["id"]})
    assert ign.status_code == 200
    assert ign.json()["remaining"] == 0
    assert client.get("/api/tiktok-stats/pending").json()["count"] == 0
