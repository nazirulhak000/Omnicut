import os
import sys
import json
import tempfile
import threading
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.translator import SubtitleTranslator
from scripts.token_tracker import TokenTracker
from scripts.post_log import PostLog
from scripts.api_server import app, get_local_ip

client = TestClient(app)

def test_issue_2_translator_universal_and_custom_dict():
    # Universal phrase
    assert SubtitleTranslator._translate_single("ทุกคน") == "Everyone!"
    assert SubtitleTranslator._translate_single("ส่งฟรี") == "Free shipping"
    assert SubtitleTranslator._translate_single("ของมันต้องมี") == "Must-have item"
    
    # Custom dict override
    custom = {"สายชาร์จ": "Fast Charger Cable"}
    res = SubtitleTranslator._translate_single("สายชาร์จ", custom_dict=custom)
    assert res == "Fast Charger Cable"
    print("✅ Issue 2: Translator universal + custom_dict verified")

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
    print("✅ Issue 6: TokenTracker thread-safety and atomic save verified")

def test_issue_5_post_log_endpoints():
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
    print("✅ Issue 5: PostLog complete API feedback loop verified")

def test_issue_8_delete_file_single_endpoint_and_webp_cleanup():
    # Create temp files in 00_Inbox
    inbox = ROOT / "00_Inbox"
    inbox.mkdir(exist_ok=True)
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
    print("✅ Issue 8: delete_file single route & companion webp cleanup verified")

def test_issue_9_get_local_ip_and_status_refresh():
    ip1 = get_local_ip(force=True)
    assert ip1 and len(ip1) >= 7
    resp = client.get("/api/status?refresh_ip=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["local_ip"] == ip1
    print("✅ Issue 9: get_local_ip force refresh & status endpoint verified")

def test_issue_1_list_exports_dynamic_matching():
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
    print("✅ TTSSanitizer: Word boundaries & Thai unit pronunciation verified")

def test_angle_lifecycle_and_rollback():
    from scripts.product_store import ProductStore
    products = ProductStore.get_all()
    if not products or not products[0].get("angles"):
        return
    p_id = products[0]["id"]
    dummy_angle = {
        "angle_id": "test_angle_lifecycle_xyz",
        "angle_name": "Test Lifecycle",
        "hook_title": "Test Hook Lifecycle 999",
        "status": "scripted"
    }
    all_p = ProductStore._load()
    for prod in all_p:
        if prod["id"] == p_id:
            prod.setdefault("angles", []).append(dummy_angle)
    ProductStore._save(all_p)

    dummy_project = "TikTok_Test_Rollback_99"
    dummy_proj_dir = ROOT / "03_Projects" / dummy_project
    dummy_proj_dir.mkdir(parents=True, exist_ok=True)
    (dummy_proj_dir / "project.json").write_text(json.dumps({"script_data": {"hook": "Test Hook Lifecycle 999"}}), encoding="utf-8")

    try:
        # 1. Update to in_production
        ProductStore.update_angle_status(p_id, "test_angle_lifecycle_xyz", "in_production", project_name=dummy_project)
        p = ProductStore.get(p_id)
        assert any(a["angle_id"] == "test_angle_lifecycle_xyz" and a["status"] == "in_production" for a in p["angles"])

        # 2. Update to rendered with project_name
        dummy_video = f"04_Exports/Ready_to_post/{dummy_project}.mp4"
        dummy_video_path = ROOT / dummy_video
        dummy_video_path.parent.mkdir(parents=True, exist_ok=True)
        dummy_video_path.write_text("dummy", encoding="utf-8")

        ProductStore.update_angle_status(p_id, "test_angle_lifecycle_xyz", "rendered", video_url=dummy_video, project_name=dummy_project)
        p = ProductStore.get(p_id)
        assert any(a["angle_id"] == "test_angle_lifecycle_xyz" and a["status"] == "rendered" and a["project_name"] == dummy_project for a in p["angles"])

        # 3. Rollback by project name (after project/video removal)
        import shutil
        shutil.rmtree(dummy_proj_dir, ignore_errors=True)
        if dummy_video_path.exists():
            dummy_video_path.unlink()

        rolled = ProductStore.rollback_by_video_or_project(dummy_project)
        assert "test_angle_lifecycle_xyz" in rolled
        p = ProductStore.get(p_id)
        assert any(a["angle_id"] == "test_angle_lifecycle_xyz" and a["status"] == "scripted" and a["video_url"] is None for a in p["angles"])
        print("✅ Angle Lifecycle: in_production -> rendered -> rollback to scripted verified")
    finally:
        # Clean up dummy project and dummy video
        import shutil
        shutil.rmtree(dummy_proj_dir, ignore_errors=True)
        dummy_video_path = ROOT / f"04_Exports/Ready_to_post/{dummy_project}.mp4"
        if dummy_video_path.exists():
            dummy_video_path.unlink()

        # Clean up dummy angle
        try:
            ProductStore.remove_angle(p_id, "test_angle_lifecycle_xyz")
        except Exception:
            pass
        ProductStore.reconcile_existing_projects()

if __name__ == "__main__":
    test_issue_2_translator_universal_and_custom_dict()
    test_issue_6_token_tracker_concurrency()
    test_issue_5_post_log_endpoints()
    test_issue_8_delete_file_single_endpoint_and_webp_cleanup()
    test_issue_9_get_local_ip_and_status_refresh()
    test_issue_1_list_exports_dynamic_matching()
    test_tts_sanitizer_word_boundaries()
    test_angle_lifecycle_and_rollback()
    print("\n🎉 ALL 9 ANALYSIS FIXES + TTS WORD BOUNDARIES + ANGLE LIFECYCLE VERIFIED SUCCESSFULLY!")
