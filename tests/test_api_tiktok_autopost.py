import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from scripts.api_server import app
from scripts.config import EXPORTS_DIR
import scripts.api_tiktok_autopost as tap

client = TestClient(app)

def test_prepare_and_get_pending_with_schedule_time(tmp_path, monkeypatch):
    # Ensure pending is cleared first
    tap._pending = None

    # Create dummy mp4 file under EXPORTS_DIR
    dummy_video = EXPORTS_DIR / "dummy_test_schedule.mp4"
    dummy_video.write_bytes(b"dummy")

    try:
        res = client.post("/api/tiktok-autopost/prepare", json={
            "video_path": str(dummy_video),
            "caption": "Test caption",
            "hashtags": "#test",
            "product_id": "p123",
            "angle_id": "a456",
            "tiktok_product_id": "1737088044189583209",
            "schedule_time": "12:30",
        })
        assert res.status_code == 200
        assert res.json() == {"success": True}

        # Check pending
        pending_res = client.get("/api/tiktok-autopost/pending")
        assert pending_res.status_code == 200
        data = pending_res.json()
        assert data["caption"] == "Test caption"
        assert data["schedule_time"] == "12:30"
        assert data["tiktok_product_id"] == "1737088044189583209"

        # Clear pending
        clear_res = client.post("/api/tiktok-autopost/clear")
        assert clear_res.status_code == 200

        # Should now be 404
        assert client.get("/api/tiktok-autopost/pending").status_code == 404
    finally:
        if dummy_video.exists():
            dummy_video.unlink()
