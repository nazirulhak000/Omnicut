import os
import sys
import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.translator import SubtitleTranslator
from scripts.token_tracker import TokenTracker
from scripts import post_log
from scripts import product_store as ps
from scripts.post_log import PostLog
from scripts.api_server import app, get_local_ip


@pytest.fixture
def isolated_post_log(tmp_path, monkeypatch):
    """Redirects PostLog storage into tmp_path -- never the real
    _Docs/post_log.json. Per .agents/rules/testing_standard.md rule 3."""
    target = tmp_path / "_Docs" / "post_log.json"
    monkeypatch.setattr(post_log, "LOG_PATH", target)
    return target


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Redirects ProductStore's STORE_PATH and BASE_DIR (which
    reconcile_existing_projects/03_Projects/04_Exports scanning are all
    derived from) into tmp_path -- never the real _Docs/products.json,
    03_Projects/, or 04_Exports/."""
    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def client():
    return TestClient(app)


def test_issue_2_translator_universal_and_custom_dict():
    # Universal phrase
    assert SubtitleTranslator._translate_single("ทุกคน") == "Everyone!"
    assert SubtitleTranslator._translate_single("ส่งฟรี") == "Free shipping"
    assert SubtitleTranslator._translate_single("ของมันต้องมี") == "Must-have item"

    # Custom dict override
    custom = {"สายชาร์จ": "Fast Charger Cable"}
    res = SubtitleTranslator._translate_single("สายชาร์จ", custom_dict=custom)
    assert res == "Fast Charger Cable"


def test_issue_6_token_tracker_concurrency():
    # Test atomic write and thread-safety
    def worker(idx):
        TokenTracker.record_event(
            model="gemini-2.5-flash",
            task="script_generation",
            input_tokens=100 + idx,
            output_tokens=50 + idx,
            thinking_tokens=10,
            latency_seconds=0.2,
            provider="google"
        )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    summary = TokenTracker.get_summary()
    assert summary["totals"]["total_calls"] >= 10
    assert summary["totals"]["total_tokens"] > 0


def test_issue_5_post_log_endpoints(client, isolated_post_log):
    # Test POST /api/posts
    payload = {
        "product_name": "Test Serum Anti-Aging",
        "clip_file": "20260903_Serum_Hook1_v1.mp4",
        "platform": "tiktok",
        "angle_key": "pain_point",
        "angle_title": "🚫 เตือนห้ามซื้อถ้ายังไม่เห็นคลิปนี้",
        "hook": "อย่าเพิ่งซื้อเซรั่ม",
        "caption": "เซรั่มกู้หน้าใสใน 7 วัน",
        "hashtags": ["#หน้าใส", "#รีวิวสกินแคร์"]
    }
    resp = client.post("/api/posts", json=payload)
    assert resp.status_code == 200, resp.text
    created = resp.json()
    assert created["success"] is True
    post_id = created["post"]["id"]

    # Test GET /api/posts
    resp_list = client.get("/api/posts")
    assert resp_list.status_code == 200
    posts = resp_list.json()["posts"]
    assert any(p["id"] == post_id for p in posts)

    # Test POST /api/posts/{post_id}/metrics
    metrics_payload = {
        "views": 15200,
        "likes": 890,
        "orders": 34,
        "commission_thb": 1020.0
    }
    resp_metrics = client.post(f"/api/posts/{post_id}/metrics", json=metrics_payload)
    assert resp_metrics.status_code == 200
    updated_post = resp_metrics.json()["post"]
    assert updated_post["metrics"]["views"] == 15200
    assert updated_post["metrics"]["commission_thb"] == 1020.0

    # Test GET /api/posts/summary
    resp_sum = client.get("/api/posts/summary")
    assert resp_sum.status_code == 200
    assert resp_sum.json()["total_posted"] >= 1

    # Test GET /api/posts/performance
    resp_perf = client.get("/api/posts/performance")
    assert resp_perf.status_code == 200
    assert "by_angle" in resp_perf.json()

    # The isolated log file must have received the write -- the real
    # _Docs/post_log.json must never see it.
    assert isolated_post_log.exists()
    logged = json.loads(isolated_post_log.read_text(encoding="utf-8"))
    assert any(p["id"] == post_id for p in logged)


def test_issue_8_delete_file_single_endpoint_and_webp_cleanup(client, isolated_store, monkeypatch):
    # delete_file() lives in scripts.api_videos and computes its allowed
    # roots from THAT module's own BASE_DIR name (bound at import time via
    # `from scripts.config import BASE_DIR`), not scripts.config.BASE_DIR --
    # so the module actually used at call time must be patched directly.
    # On success it also calls ProductStore.rollback_by_video_or_project(),
    # which is why isolated_store (redirecting ps.STORE_PATH/ps.BASE_DIR) is
    # used here too -- otherwise that call would still touch the real
    # _Docs/products.json even though this test only means to exercise the
    # file-delete path.
    import scripts.api_videos as api_videos_mod
    tmp_path = isolated_store
    inbox = tmp_path / "00_Inbox"
    inbox.mkdir()
    monkeypatch.setattr(api_videos_mod, "BASE_DIR", tmp_path)

    test_video = inbox / "test_delete_sample.mp4"
    test_webp = inbox / "test_delete_sample.webp"
    test_srt = inbox / "test_delete_sample-sub.srt"

    test_video.write_text("dummy video")
    test_webp.write_text("dummy webp")
    test_srt.write_text("dummy srt")

    assert test_video.exists()
    assert test_webp.exists()
    assert test_srt.exists()

    resp = client.post("/api/delete-file", json={"file_path": str(test_video)})
    assert resp.status_code == 200
    assert not test_video.exists()
    assert not test_webp.exists()
    assert not test_srt.exists()


def test_issue_9_get_local_ip_and_status_refresh(client):
    ip1 = get_local_ip(force=True)
    assert ip1 and len(ip1) >= 7
    resp = client.get("/api/status?refresh_ip=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["local_ip"] == ip1


def test_issue_1_list_exports_dynamic_matching(client):
    # Read-only against whatever exports currently exist on disk -- no
    # writes, so no isolation is required for this one.
    resp = client.get("/api/exports")
    assert resp.status_code == 200
    data = resp.json()
    assert "exports" in data


def test_tts_sanitizer_word_boundaries():
    from scripts.tts_sanitizer import TTSSanitizer
    text = "From Chrome with love, product problem program detail email wait 20,000mAh 65W iPhone 15 Pro with AI chip"
    cleaned = TTSSanitizer.clean(text)
    assert "detail" in cleaned
    assert "email" in cleaned
    assert "wait" in cleaned
    assert "product" in cleaned
    assert "problem" in cleaned
    assert "From" in cleaned
    assert "20000 มิลลิแอมป์" in cleaned
    assert "มิลลิแอมป์อาวเออร์" not in cleaned
    assert "65 วัตต์" in cleaned
    assert "โปร" in cleaned
    assert "เอไอ" in cleaned


def test_angle_lifecycle_and_rollback(isolated_store):
    tmp_path = isolated_store

    product = ps.ProductStore.add(name="ทดสอบ Lifecycle", url="https://x.test/lifecycle")
    p_id = product["id"]
    dummy_angle = {
        "angle_id": "test_angle_lifecycle_xyz",
        "angle_name": "Test Lifecycle",
        "hook_title": "Test Hook Lifecycle 999",
        "status": "scripted"
    }
    all_p = ps.ProductStore._load()
    for prod in all_p:
        if prod["id"] == p_id:
            prod.setdefault("angles", []).append(dummy_angle)
    ps.ProductStore._save(all_p)

    dummy_project = "TikTok_Test_Rollback_99"
    dummy_proj_dir = tmp_path / "03_Projects" / dummy_project
    dummy_proj_dir.mkdir(parents=True, exist_ok=True)
    (dummy_proj_dir / "project.json").write_text(json.dumps({"script_data": {"hook": "Test Hook Lifecycle 999"}}), encoding="utf-8")

    # 1. Update to in_production
    ps.ProductStore.update_angle_status(p_id, "test_angle_lifecycle_xyz", "in_production", project_name=dummy_project)
    p = ps.ProductStore.get(p_id)
    assert any(a["angle_id"] == "test_angle_lifecycle_xyz" and a["status"] == "in_production" for a in p["angles"])

    # 2. Update to rendered with project_name
    dummy_video = f"04_Exports/Ready_to_post/{dummy_project}.mp4"
    dummy_video_path = tmp_path / dummy_video
    dummy_video_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_video_path.write_text("dummy", encoding="utf-8")

    ps.ProductStore.update_angle_status(p_id, "test_angle_lifecycle_xyz", "rendered", video_url=dummy_video, project_name=dummy_project)
    p = ps.ProductStore.get(p_id)
    assert any(a["angle_id"] == "test_angle_lifecycle_xyz" and a["status"] == "rendered" and a["project_name"] == dummy_project for a in p["angles"])

    # 3. Rollback by project name (after project/video removal)
    import shutil
    shutil.rmtree(dummy_proj_dir, ignore_errors=True)
    if dummy_video_path.exists():
        dummy_video_path.unlink()

    rolled = ps.ProductStore.rollback_by_video_or_project(dummy_project)
    assert "test_angle_lifecycle_xyz" in rolled
    p = ps.ProductStore.get(p_id)
    assert any(a["angle_id"] == "test_angle_lifecycle_xyz" and a["status"] == "scripted" and a["video_url"] is None for a in p["angles"])
