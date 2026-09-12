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


def test_import_matches_exact_video_id(isolated_log, client):
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


def test_import_fuzzy_matches_title_and_skips_unknown(isolated_log, client):
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


def test_latest_returns_synced_first(isolated_log, client):
    post_log_module.PostLog.add_post(product_name="A", clip_file="a.mp4")
    post_log_module.PostLog.add_post(product_name="B", clip_file="b.mp4", angle_title="ด่วน BlueWOW X110 Ultra")
    client.post("/api/tiktok-stats/import", json={"rows": [{"title": "ด่วน BlueWOW X110 Ultra", "views": 268}]})
    resp = client.get("/api/tiktok-stats/latest")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1
