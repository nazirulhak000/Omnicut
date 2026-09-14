"""
Tests for AI Cover Image Generation (Round COVER-AI-IMAGEN-1).
Tests POST /api/covers/ai-generate-image with Google GenAI Imagen 3 and Fallback paths.
"""

import os
import io
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from scripts.api_server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_ai_generate_cover_image_fallback(client, tmp_path):
    """Test AI cover generation when no API key is provided, falling back to smart frame hunt or canvas."""
    with patch.dict(os.environ, {}, clear=True):
        resp = client.post(
            "/api/covers/ai-generate-image",
            json={
                "product_name": "ไมค์ไร้สาย K9 Pro",
                "hook_title": "ไมค์ตัวนี้ตัดเสียงรบกวนได้จริงไหม?",
                "style_prompt": "Clean commercial product photo",
                "video_path": None,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "image_path" in data
        assert "media_url" in data
        assert os.path.exists(data["image_path"])
        assert data["method"] in ("clean_gradient", "smart_frame", "imagen_3")


def test_ai_generate_cover_image_imagen_mock(client, tmp_path):
    """Test AI cover generation with mocked Google GenAI Imagen 3 client."""
    dummy_img = Image.new("RGB", (1080, 1920), color=(140, 50, 200))
    buf = io.BytesIO()
    dummy_img.save(buf, format="JPEG")
    fake_bytes = buf.getvalue()

    fake_gen_image = MagicMock()
    fake_gen_image.image.image_bytes = fake_bytes

    fake_response = MagicMock()
    fake_response.generated_images = [fake_gen_image]

    fake_client = MagicMock()
    fake_client.models.generate_images.return_value = fake_response

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_123"}), \
         patch("scripts.api_covers._get_genai_client", return_value=fake_client):
        resp = client.post(
            "/api/covers/ai-generate-image",
            json={
                "product_name": "ครีมกันแดดเนื้อน้ำ",
                "hook_title": "ไม่เหนียว ไม่วอก จริงดิ?",
                "style_prompt": "High-end commercial studio shot, 9:16 vertical",
                "video_path": None,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["method"] == "imagen_3"
        assert os.path.exists(data["image_path"])
        assert data["media_url"].startswith("/api/media/")
