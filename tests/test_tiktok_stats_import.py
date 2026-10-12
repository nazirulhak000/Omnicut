"""TikTok Studio stats import — offline tests with tmp storage only."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import post_log as post_log_module
from scripts import tiktok_pending as pending_module
from scripts.api_server import app


@pytest.fixture
def isolated_log(tmp_path, monkeypatch):
    target = tmp_path / "post_log.json"
    monkeypatch.setattr(post_log_module, "LOG_PATH", target)
    monkeypatch.setattr(post_log_module._TABLE, "_json_path_fn", lambda: target)
    monkeypatch.setattr(post_log_module._TABLE, "_db_path_fn", lambda: tmp_path / "store.db")

    pending_target = tmp_path / "tiktok_pending.json"
    monkeypatch.setattr(pending_module, "PENDING_PATH", pending_target)
    monkeypatch.setattr(pending_module._TABLE, "_json_path_fn", lambda: pending_target)
    monkeypatch.setattr(pending_module._TABLE, "_db_path_fn", lambda: tmp_path / "store.db")

    ignored_target = tmp_path / "tiktok_ignored.json"
    monkeypatch.setattr(pending_module, "IGNORED_PATH", ignored_target)
    monkeypatch.setattr(pending_module._IGNORED_TABLE, "_json_path_fn", lambda: ignored_target)
    monkeypatch.setattr(pending_module._IGNORED_TABLE, "_db_path_fn", lambda: tmp_path / "store.db")

    return target


@pytest.fixture
def client():
    # Existing matching tests represent a positively identified Studio account.
    # Unknown-account quarantine is tested separately without this default.
    from scripts.channel_store import MAIN_SEED
    class AccountClient(TestClient):
        def post(self, url, **kwargs):
            if url == "/api/tiktok-stats/import" and "json" in kwargs:
                kwargs["json"] = {"source_account": MAIN_SEED["handle"], **kwargs["json"]}
            return super().post(url, **kwargs)
    return AccountClient(app)


def test_unknown_account_does_not_merge_and_quarantine_survives_ignore_restore(isolated_log, client):
    post = post_log_module.PostLog.add_post(product_name="Known clip",clip_file="known.mp4")
    stored=post_log_module.PostLog.list_posts()
    stored[0]["tiktok_video_id"]="123456789"
    stored[0]["metrics"]={"views":10}
    post_log_module.PostLog._save(stored)
    response=client.post("/api/tiktok-stats/import",json={"source_account":None,"rows":[{"video_id":"123456789","title":"Known clip","views":999}]})
    assert response.status_code == 200
    assert response.json()["matched"] == response.json()["updated"] == response.json()["registered"] == 0
    assert post_log_module.PostLog.list_posts()[0]["metrics"]["views"] == 10
    pending=pending_module.TikTokPending.list_rows(channel_id="main")[0]
    assert pending["account_unverified"] is True
    ignored=pending_module.TikTokPending.ignore(pending["id"],channel_id="main")
    restored=pending_module.TikTokPending.restore(ignored["id"],channel_id="main")
    assert restored["account_unverified"] is True
    attached=client.post("/api/tiktok-stats/attach",json={"pending_id":restored["id"],"post_id":stored[0]["id"]})
    assert attached.status_code == 409
    verified=client.post("/api/tiktok-stats/import",json={"rows":[{"video_id":"123456789","title":"Known clip","views":999}]})
    assert verified.status_code == 200 and verified.json()["updated"] == 1
    assert pending_module.TikTokPending.list_rows(channel_id="main") == []


def test_import_matches_exact_video_id(isolated_log, client, monkeypatch):
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [{
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [{
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [{
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: cands_list)
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
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])
    client.post("/api/tiktok-stats/import", json={"rows": [{"title": "คลิปคนอื่น xyz", "views": 3}]})
    pending = client.get("/api/tiktok-stats/pending").json()["rows"]
    assert len(pending) == 1

    bad = client.post("/api/tiktok-stats/attach", json={"pending_id": pending[0]["id"]})
    assert bad.status_code == 400

    ign = client.post("/api/tiktok-stats/pending/ignore", json={"pending_id": pending[0]["id"]})
    assert ign.status_code == 200
    assert ign.json()["remaining"] == 0
    assert client.get("/api/tiktok-stats/pending").json()["count"] == 0


def test_viral_milestones_endpoint(isolated_log, client):
    """Test /api/tiktok-stats/milestones returns clips exceeding thresholds."""
    # Add regular clip (< 1000 views)
    post_log_module.PostLog.add_post(
        product_name="Product Low",
        clip_file="low.mp4",
        angle_title="Low Angle",
    )
    posts = post_log_module.PostLog.list_posts()
    posts[0]["metrics"] = {"views": 450, "likes": 20, "comments": 2, "shares": 1}
    posts[0]["tiktok_synced_at"] = "2026-09-14T10:00:00"

    # Add viral clip (15,000 views)
    post_log_module.PostLog.add_post(
        product_name="Product High Viral",
        clip_file="high.mp4",
        angle_title="Viral Angle",
    )
    posts = post_log_module.PostLog.list_posts()
    high = next(post for post in posts if post["product_name"] == "Product High Viral")
    high["metrics"] = {"views": 15200, "likes": 850, "comments": 45, "shares": 120}
    high["tiktok_synced_at"] = "2026-09-14T10:05:00"
    post_log_module.PostLog._save(posts)

    # Threshold default 1000: only the 15.2k clip should be returned
    resp = client.get("/api/tiktok-stats/milestones")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["has_viral"] is True
    first = data["milestones"][0]
    assert first["product_name"] == "Product High Viral"
    assert first["views"] == 15200
    assert first["tier"] == "10k"
    assert "10K+" in first["tier_label"]

    # Threshold 20000: none returned
    resp2 = client.get("/api/tiktok-stats/milestones?threshold=20000")
    assert resp2.status_code == 200
    assert resp2.json()["count"] == 0


def test_import_matches_via_schedule_queue_caption(isolated_log, client, monkeypatch):
    """Studio row matching exact caption saved in ScheduleQueueStore auto-registers successfully."""
    from scripts.schedule_store import ScheduleQueueStore
    from scripts.product_store import ProductStore

    monkeypatch.setattr(ScheduleQueueStore, "list_items", lambda **scope: [
        {
            "id": "q1",
            "product_name": "BASIKE พัดลมระบายความร้อน",
            "project_name": "BAS01-ปัญหาก่อนใช้_1",
            "hook_title": "🛑 โน้ตบุ๊กร้อนจนค้าง ทำงานต่อไม่ได้ ลองใช้ตัวนี้ดูครับ!",
            "caption": "บอกลาปัญหาเครื่องร้อนจนค้าง! ยืดอายุโน้ตบุ๊กคู่ใจด้วย BASIKE Notebook Cooling Pad ลมแรง ดีไซน์บางเฉียบ พิกัดในตะกร้าเลยครับ 👇",
            "hashtags": "#พัดลมโน๊ตบุ๊ค #พัดลมระบายความร้อนคอมพิวเตอร์ #BASIKE",
            "video_path": "04_Exports/Posted/BAS01-ปัญหาก่อนใช้_1_20260915_105152.mp4",
            "angle_id": "pain_point",
            "status": "posted",
        }
    ])
    monkeypatch.setattr(ProductStore, "get_all", lambda **scope: [])

    resp = client.post("/api/tiktok-stats/import", json={"rows": [{
        "title": "บอกลาปัญหาเครื่องร้อนจนค้าง! ยืดอายุโน้ตบุ๊กคู่ใจด้วย BASIKE Notebook Cooling Pad ลมแรง ดีไซน์บางเฉียบ พิกัดในตะกร้าเลยครับ 👇 #พัดลมโน๊ตบุ๊ค #BASIKE",
        "posted_text": "15 ส.ค. 1:15 PM",
        "views": 420,
        "likes": 8,
        "comments": 1,
        "video_id": "vid_basike_123",
        "video_url": "https://www.tiktok.com/@user/video/vid_basike_123",
    }]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] == 1
    assert data["registered"] == 1
    assert len(data["unmatched"]) == 0

    posts = post_log_module.PostLog.list_posts()
    assert len(posts) == 1
    assert posts[0]["product_name"] == "BASIKE พัดลมระบายความร้อน"
    assert posts[0]["clip_file"] == "BAS01-ปัญหาก่อนใช้_1_20260915_105152.mp4"
    assert posts[0]["tiktok_video_id"] == "vid_basike_123"
    assert posts[0]["metrics"]["views"] == 420


def test_import_matches_via_product_store_tiktok_caption(isolated_log, client, monkeypatch):
    """Studio row matching tiktok_caption from ProductStore auto-registers successfully."""
    from scripts.product_store import ProductStore
    from scripts.schedule_store import ScheduleQueueStore

    monkeypatch.setattr(ScheduleQueueStore, "list_items", lambda **scope: [])
    monkeypatch.setattr(ProductStore, "get_all", lambda **scope: [
        {
            "id": "prod_orashare",
            "name": "Orashare พัดลมมือถือ",
            "angles": [{
                "angle_id": "pain_point",
                "angle_name": "😫 ร้อนเหงื่อท่วม",
                "hook_title": "อากาศร้อนจนทนไม่ไหว มีสิ่งนี้ติดตัวรอดชัวร์",
                "tiktok_caption": "บอกลาความร้อนเหงื่อท่วมตัว! พก Orashare HF04 พัดลมไฮสปีดเทอร์โบ 100 ระดับ เย็นฉ่ำสะใจพกพาง่ายสุดๆ พิกัดในตะกร้าเลยครับ 👇",
                "tiktok_hashtags": "#พัดลมพกพา #Orashare",
                "video_url": "04_Exports/ORA01-ร้อนเหงื่อท่วม_1.mp4",
                "clip_file": "ORA01-ร้อนเหงื่อท่วม_1.mp4",
            }],
        }
    ])

    resp = client.post("/api/tiktok-stats/import", json={"rows": [{
        "title": "บอกลาความร้อนเหงื่อท่วมตัว! พก Orashare HF04 พัดลมไฮสปีดเทอร์โบ 100 ระดับ เย็นฉ่ำสะใจพกพาง่ายสุดๆ พิกัดในตะกร้าเลยครับ 👇 #พัดลมพกพา",
        "posted_text": "15 ส.ค. 9:00 PM",
        "views": 150,
        "likes": 12,
        "video_id": "vid_orashare_456",
    }]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] == 1
    assert data["registered"] == 1
    assert len(data["unmatched"]) == 0

    posts = post_log_module.PostLog.list_posts()
    assert len(posts) == 1
    assert posts[0]["product_name"] == "Orashare พัดลมมือถือ"
    assert posts[0]["tiktok_video_id"] == "vid_orashare_456"
    assert posts[0]["metrics"]["views"] == 150


def test_import_picks_highest_scoring_candidate_over_earlier_candidates(isolated_log, client, monkeypatch):
    """Candidate with the highest token/caption overlap score is picked over an earlier weaker match."""
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [
        {
            # Earlier in candidate list, shares generic word "พัดลม"
            "hook_title": "พัดลมตัวอื่นทั่วไป",
            "product_name": "พัดลมทั่วไป",
            "angle_title": "พัดลมทั่วไป",
            "angle_key": "angle_gen",
            "clip_file": "generic.mp4",
            "caption": "พัดลมเย็นสบาย ทั่วไป",
        },
        {
            # Later in candidate list, exact match
            "hook_title": "🛑 โน้ตบุ๊กร้อนจนค้าง ทำงานต่อไม่ได้ ลองใช้ตัวนี้ดูครับ!",
            "product_name": "BASIKE พัดลมระบายความร้อน",
            "angle_title": "BASIKE Notebook Cooling Pad",
            "angle_key": "pain_point",
            "clip_file": "BAS01-ปัญหาก่อนใช้_1_20260915_105152.mp4",
            "caption": "บอกลาปัญหาเครื่องร้อนจนค้าง! ยืดอายุโน้ตบุ๊กคู่ใจด้วย BASIKE Notebook Cooling Pad ลมแรง ดีไซน์บางเฉียบ พิกัดในตะกร้าเลยครับ 👇",
        },
    ])

    resp = client.post("/api/tiktok-stats/import", json={"rows": [{
        "title": "บอกลาปัญหาเครื่องร้อนจนค้าง! ยืดอายุโน้ตบุ๊กคู่ใจด้วย BASIKE Notebook Cooling Pad ลมแรง ดีไซน์บางเฉียบ พิกัดในตะกร้าเลยครับ 👇 #พัดลมโน๊ตบุ๊ค #BASIKE",
        "posted_text": "15 ส.ค. 1:15 PM",
        "views": 420,
        "video_id": "vid_basike_best",
    }]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] == 1
    assert data["registered"] == 1

    posts = post_log_module.PostLog.list_posts()
    assert len(posts) == 1
    # Must be BASIKE, NOT generic earlier candidate!
    assert posts[0]["product_name"] == "BASIKE พัดลมระบายความร้อน"
    assert posts[0]["clip_file"] == "BAS01-ปัญหาก่อนใช้_1_20260915_105152.mp4"


def test_ignored_pending_clip_persists_and_is_excluded_from_future_imports(isolated_log, client, monkeypatch):
    """When a user ignores an unmatched pending row, it must not reappear on future syncs."""
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])

    unmatched_row = {
        "title": "คลิปสินค้าคนอื่นที่ไม่เกี่ยวเลย 123",
        "posted_text": "20 ส.ค. 10:00 AM",
        "views": 88,
        "likes": 5,
        "video_id": "vid_unrelated_123",
    }

    # 1. Initial import -- unmatched row ends up in pending
    resp = client.post("/api/tiktok-stats/import", json={"rows": [unmatched_row]})
    assert resp.status_code == 200
    assert resp.json()["pending_count"] == 1

    pending_list = client.get("/api/tiktok-stats/pending").json()
    assert pending_list["count"] == 1
    assert pending_list["ignored_count"] == 0
    pending_id = pending_list["rows"][0]["id"]

    # 2. User clicks "ข้ามรายการ" (Ignore)
    ignore_resp = client.post("/api/tiktok-stats/pending/ignore", json={"pending_id": pending_id})
    assert ignore_resp.status_code == 200
    assert ignore_resp.json()["ignored"] is True
    assert ignore_resp.json()["remaining"] == 0
    assert ignore_resp.json()["ignored_count"] == 1

    # Verify pending is empty, ignored has 1 item
    pending_after = client.get("/api/tiktok-stats/pending").json()
    assert pending_after["count"] == 0
    assert pending_after["ignored_count"] == 1

    ignored_list = client.get("/api/tiktok-stats/ignored").json()
    assert ignored_list["count"] == 1
    assert ignored_list["rows"][0]["video_id"] == "vid_unrelated_123"

    # 3. User syncs again from TikTok Studio with the same video
    re_import_resp = client.post("/api/tiktok-stats/import", json={"rows": [unmatched_row]})
    assert re_import_resp.status_code == 200
    # Crucial assertion: pending_count MUST remain 0!
    assert re_import_resp.json()["pending_count"] == 0
    pending_recheck = client.get("/api/tiktok-stats/pending").json()
    assert pending_recheck["count"] == 0


def test_batch_ignore_all_and_restore(isolated_log, client, monkeypatch):
    """Test batch-ignoring all pending rows and restoring a row back to pending."""
    from scripts import api_tiktok_stats
    monkeypatch.setattr(api_tiktok_stats, "_export_clip_candidates", lambda scope=None: [])

    row1 = {"title": "คลิปไม่เกี่ยว 1", "views": 10, "video_id": "vid_ignore_1"}
    row2 = {"title": "คลิปไม่เกี่ยว 2", "views": 20, "video_id": "vid_ignore_2"}

    # 1. Import 2 unmatched rows
    resp = client.post("/api/tiktok-stats/import", json={"rows": [row1, row2]})
    assert resp.status_code == 200
    assert resp.json()["pending_count"] == 2

    # 2. Batch ignore all
    batch_resp = client.post("/api/tiktok-stats/pending/ignore-all")
    assert batch_resp.status_code == 200
    assert batch_resp.json()["ignored_count"] == 2
    assert batch_resp.json()["remaining"] == 0
    assert batch_resp.json()["total_ignored"] == 2

    # 3. Verify future sync doesn't bring them back
    sync_resp = client.post("/api/tiktok-stats/import", json={"rows": [row1, row2]})
    assert sync_resp.status_code == 200
    assert sync_resp.json()["pending_count"] == 0

    # 4. Restore row 1
    ignored_items = client.get("/api/tiktok-stats/ignored").json()["rows"]
    target_item = next(item for item in ignored_items if item["video_id"] == "vid_ignore_1")
    restore_resp = client.post("/api/tiktok-stats/ignored/restore", json={"ignored_id": target_item["id"]})
    assert restore_resp.status_code == 200
    assert restore_resp.json()["restored"] is True
    assert restore_resp.json()["remaining"] == 1
    assert restore_resp.json()["ignored_count"] == 1

    # 5. Check pending list now contains the restored item
    pending_now = client.get("/api/tiktok-stats/pending").json()
    assert pending_now["count"] == 1
    assert pending_now["rows"][0]["video_id"] == "vid_ignore_1"



