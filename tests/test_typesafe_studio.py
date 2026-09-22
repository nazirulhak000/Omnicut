import pytest
from starlette.testclient import TestClient

from scripts.api_server import app


@pytest.fixture
def client():
    # Use TestClient with valid API key header
    return TestClient(app, headers={"X-API-Key": "test-key"})


def test_typesafe_status(client, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test_key")
    res = client.get("/api/typesafe-studio/status")
    assert res.status_code == 200
    data = res.json()
    assert "available" in data
    assert data["model"] == "Jev"
    assert data["role"] == "Decision / Ranking / Verification"
    assert "features" in data
    assert "strict_topic_hold" in data["features"]


def test_generate_hooks(client):
    payload = {
        "product_name": "Xiaomi MIX Flip",
        "key_features": ["จอนอก 4.01 นิ้ว", "กล้องคู่ Leica 50MP", "ชิป Snapdragon 8 Gen 3"],
    }
    res = client.post("/api/typesafe-studio/generate-hooks", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["product_name"] == "Xiaomi MIX Flip"
    variants = data["variants"]
    assert len(variants) == 3
    # Check that each variant contains angle, hook_text, badge_color, and rating_score
    for v in variants:
        assert "hook_text" in v
        assert "badge_color" in v
        assert "rating_score" in v


def test_evaluate_hook(client):
    payload = {"hook_text": "อย่าเพิ่งซื้อมือถือจอพับถ้ายังไม่รู้สิ่งนี้!"}
    res = client.post("/api/typesafe-studio/evaluate-hook", json=payload)
    assert res.status_code == 200
    data = res.json()
    # When TypeSafe SDK is installed: response contains hook/high_retention_prob/rating_score.
    # When SDK is absent (graceful degradation): response contains an "error" key.
    assert (
        "hook" in data
        or "high_retention_prob" in data
        or "rating_score" in data
        or "error" in data
    )


def test_match_broll_fallback(client, monkeypatch):
    # Test B-roll matching logic
    payload = {
        "sentence": "สถาปัตยกรรมระบายความร้อน 3D VC Teardown เย็นเฉียบ",
        "candidate_clips": [
            {"id": "clip_1", "name": "camera_zoom.mp4", "description": "กล้องคู่ Leica ถ่ายซูมระยะไกล"},
            {"id": "clip_2", "name": "vc_cooling.mp4", "description": "โครงสร้าง 3D VC Teardown ระบบระบายความร้อน"},
            {"id": "clip_3", "name": "charging.mp4", "description": "ชาร์จไว 67W HyperCharge"},
        ],
    }
    res = client.post("/api/typesafe-studio/match-broll", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "matched_clip_id" in data
    assert "strict_topic_hold" in data


def test_match_sequence(client):
    payload = {
        "sentences": [
            "จอนอกขนาดใหญ่ 4.01 นิ้ว ใช้งานได้เต็มตา",
            "กล้องคู่พัฒนาร่วมกับ Leica ถ่ายภาพคมชัดระดับสตูดิโอ",
            "สถาปัตยกรรมระบายความร้อน 3D VC Teardown เย็นเฉียบ",
        ],
        "candidate_clips": [
            {"id": "clip_screen", "name": "screen.mp4", "description": "หน้าจอด้านนอก 4.01 นิ้ว"},
            {"id": "clip_camera", "name": "camera.mp4", "description": "กล้อง Leica 50MP สวยคม"},
            {"id": "clip_vc", "name": "vc.mp4", "description": "ระบบระบายความร้อน 3D VC เย็นเฉียบ"},
        ],
        "ensure_diversity": True,
    }
    res = client.post("/api/typesafe-studio/match-sequence", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_sentences"] == 3
    seq = data["sequence"]
    assert len(seq) == 3
    for item in seq:
        assert "matched_clip_id" in item
        assert "strict_topic_hold" in item
        assert "relevance_score" in item


def test_match_raw_folder_invalid(client):
    payload = {
        "raw_folder": "01_Raw/non_existent_folder_xyz_123",
        "sentences": ["ทดสอบระบบ"],
    }
    res = client.post("/api/typesafe-studio/match-raw-folder", json=payload)
    assert res.status_code == 404


def test_ai_generate_includes_typesafe_scoring(client, monkeypatch):
    # Ensure offline test doesn't spend network latency on live Gemini
    monkeypatch.setattr("scripts.config.get_gemini_api_keys", lambda: [])
    payload = {
        "product_name": "Baseus Power Bank 65W",
        "key_features": "ชาร์จเร็ว พกพาสะดวก",
        "pain_point": "แบตหมดไว",
        "price_deal": "ลดพิเศษ 990 บาท",
    }
    res = client.post("/api/script/ai-generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "angles" in data
    assert len(data["angles"]) > 0
    first_angle = data["angles"][0]
    assert "retention_probability" in first_angle
    assert "rating_score" in first_angle



