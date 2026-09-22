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
    assert "hook" in data or "high_retention_prob" in data or "rating_score" in data


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
