"""
Tests for AI Cover Image Generation (Round COVER-AI-IMAGEN-1).
Tests POST /api/covers/ai-generate-image with Google GenAI Imagen 3 and Fallback paths.
"""

import os
import io
from unittest.mock import MagicMock, patch
import pytest
import urllib.error
from PIL import Image
from fastapi.testclient import TestClient

from scripts.api_server import app

@pytest.fixture(autouse=True)
def offline_cover_providers(monkeypatch):
    monkeypatch.setattr("scripts.api_covers._generate_cover_via_antigravity_cli", lambda *a, **k: None)
    def unavailable(*args, **kwargs):
        raise urllib.error.URLError("offline test")
    monkeypatch.setattr("scripts.api_covers.urllib.request.urlopen", unavailable)

@pytest.fixture
def client():
    return TestClient(app)

def test_ai_generate_cover_image_fallback(client, tmp_path):
    """Test AI cover generation when no API key is provided and Antigravity is disabled."""
    with patch.dict(os.environ, {"DISABLE_ANTIGRAVITY": "1", "GEMINI_API_KEY": ""}):
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
        assert data["method"] in ("antigravity_pro", "clean_gradient", "smart_frame", "imagen_3", "ai_free", "studio_auto", "studio_auto_cutout", "ai_free_cutout")


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

    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_123", "DISABLE_ANTIGRAVITY": "1"}), \
         patch("scripts.ai_bridge.AIBridge.get_api_keys", return_value=["fake_key_123"]), \
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


def test_ai_generate_cover_image_antigravity_mock(client, tmp_path):
    """Test AI cover generation through Antigravity CLI path."""
    fake_out = tmp_path / "mock_agy_cover.jpg"
    dummy_img = Image.new("RGB", (1080, 1920), color=(20, 25, 40))
    dummy_img.save(fake_out, format="JPEG")

    with patch("scripts.api_covers._generate_cover_via_antigravity_cli", return_value=fake_out):
        resp = client.post(
            "/api/covers/ai-generate-image",
            json={
                "product_name": "สายชาร์จ ESSAGER",
                "hook_title": "สายชาร์จตัวท็อป",
                "style_prompt": "High-end 8k commercial studio shot",
                "video_path": None,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["method"] == "antigravity_pro"
        assert "Antigravity" in data["message"]


def test_product_ref_images_endpoint(client):
    """Test POST /api/covers/product-ref-images successfully returns catalog images."""
    resp = client.post(
        "/api/covers/product-ref-images",
        json={
            "product_name": "ESSAGER",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "ref_images" in data
    assert isinstance(data["ref_images"], list)
    if len(data["ref_images"]) > 0:
        first = data["ref_images"][0]
        assert "url" in first
        assert "name" in first


def test_ai_generate_cover_image_with_ref_image(client, tmp_path):
    """Test AI cover generation when passing a local source_image_path reference."""
    from scripts import config
    sample_ref = config.BASE_DIR / "01_Raw/ref_test_img.jpg"
    img = Image.new("RGB", (800, 800), color=(100, 150, 200))
    img.save(sample_ref, format="JPEG")

    fake_out = tmp_path / "mock_ref_cover.jpg"
    Image.new("RGB", (1080, 1920), color=(20, 30, 50)).save(fake_out, format="JPEG")

    with patch("scripts.api_covers._generate_cover_via_antigravity_cli", return_value=fake_out) as mock_cli:
        resp = client.post(
            "/api/covers/ai-generate-image",
            json={
                "product_name": "สายชาร์จแม่เหล็ก",
                "style_prompt": "Top-down flat lay on tech cutting mat",
                "source_image_path": str(sample_ref),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert mock_cli.called
        # Verify ref_image_path was forwarded
        _, kwargs = mock_cli.call_args
        assert kwargs.get("ref_image_path") is not None


def test_clean_backdrop_prompt_handheld():
    """Verify handheld prompts preserve hand and product demonstration, while regular prompts remove people."""
    from scripts.api_covers import _clean_backdrop_prompt

    # Handheld prompt
    hh_prompt = "Commercial hero shot of a hand holding wireless microphone at center"
    cleaned_hh = _clean_backdrop_prompt(hh_prompt)
    assert "hand holding" in cleaned_hh.lower()
    assert "no people" not in cleaned_hh.lower()
    assert "9:16 vertical ratio" in cleaned_hh

    # Empty stage prompt
    empty_prompt = "Podium display on dark marble with spotlight"
    cleaned_empty = _clean_backdrop_prompt(empty_prompt)
    assert "no people" in cleaned_empty
    assert "no humans" in cleaned_empty


def test_render_pro_cover_tech_neon_template():
    """Verify render_pro_cover with template='tech_neon' renders white brand and neon model successfully."""
    from scripts.api_covers import render_pro_cover, COVERS_DIR
    from PIL import Image

    cache_dir = COVERS_DIR / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dummy_img = cache_dir / "test_tech_neon_base.jpg"
    img = Image.new("RGB", (1080, 1920), (30, 30, 40))
    img.save(dummy_img, "JPEG")

    try:
        primary, p_3x4 = render_pro_cover(
            custom_image_str=str(dummy_img),
            aspect_ratio="both",
            enable_hook_text=True,
            template="tech_neon",
            hook_text="BLUEWOW\nCOOLER D12",
            sub_text="พัดลมระบายความร้อน",
            export_stem="test_tech_neon",
        )
        assert primary.exists()
        assert primary.stat().st_size > 0
        assert p_3x4 is not None and p_3x4.exists()
    finally:
        if dummy_img.exists():
            dummy_img.unlink()
        test_out = COVERS_DIR / "test_tech_neon_cover.jpg"
        test_3x4 = COVERS_DIR / "test_tech_neon_cover_3x4.jpg"
        if test_out.exists():
            test_out.unlink()
        if test_3x4.exists():
            test_3x4.unlink()
