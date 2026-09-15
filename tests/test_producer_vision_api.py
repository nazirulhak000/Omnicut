"""
Tests for AI Gemini Vision & Multimodal synthesis in AI Producer Hub
Tests POST /api/producer/ai-idea-to-angle with both Gemini Vision and Heuristic fallback.
"""

import os
import json
import base64
import socket
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from scripts.api_server import app
import scripts.api_producer as api_producer


@pytest.fixture
def client():
    return TestClient(app)


def test_ai_idea_to_angle_heuristic_fallback(client, monkeypatch):
    """When no API key is present or AI is unavailable, falls back cleanly to heuristic."""
    # Ensure no API keys exist
    monkeypatch.setattr(api_producer, "_generate_angle_with_gemini", lambda *args, **kwargs: None)

    payload = {
        "idea_text": "อยากได้คลิปเตือนภัยคนใช้สายชาร์จปลอม ระวังไฟไหม้",
        "ref_url": "https://tiktok.com/@example/video/123",
        "product_id": None,
    }
    res = client.post("/api/producer/ai-idea-to-angle", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["analysis"]["method"] == "heuristic_fallback"
    assert data["analysis"]["used_ref_url"] is True

    proposal = data["proposal"]
    assert "angle_name" in proposal
    assert "hook_title" in proposal
    assert "shoot_angle_brief" in proposal
    assert "script_brief" in proposal
    assert "visual_insights" in proposal
    # Project rule: No dots/ellipses in script or hook
    assert "..." not in proposal["hook_title"]
    assert "…" not in proposal["hook_title"]
    assert "..." not in proposal["script_brief"]
    assert "…" not in proposal["script_brief"]


def test_ai_idea_to_angle_multimodal_gemini_vision(client, monkeypatch, tmp_path):
    """When Gemini Vision returns valid multimodal analysis, parse and sanitize properly."""
    # Treat the test fixture directory as the configured assets root; arbitrary
    # host paths are intentionally rejected by the resolver.
    monkeypatch.setattr(api_producer, "ASSETS_DIR", tmp_path)
    # Create a dummy image
    test_img = tmp_path / "test_screenshot.png"
    # 1x1 transparent PNG
    png_bytes = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    test_img.write_bytes(png_bytes)

    mock_gemini_response = {
        "angle_name": "มุมเตือนภัยจากภาพเรฟ",
        "visual_insights": "พบภาพแคปหน้าจอโชว์พาดหัวเตือนภัยสีเหลือง และการซูมสินค้าโชว์ดีไซน์พอร์ต USB-C",
        "hook_title": "อย่าเพิ่งซื้อสายชาร์จใหม่ถ้ายังไม่รู้สิ่งนี้เด็ดขาด",
        "target_audience": "กลุ่มลูกค้าที่มองหาของแท้ ปลอดภัย ไม่เสี่ยงไฟลัดวงจร",
        "pain_point": "กลัวสายชาร์จไม่ได้มาตรฐาน ทำเครื่องพัง",
        "shoot_angle_brief": "1. 0-3 วิ: โชว์หัวชาร์จพร้อมสีหน้าตกใจ\n2. 3-15 วิ: ซูมให้เห็นวงจรความปลอดภัย\n3. 15-30 วิ: ปิดการขายพร้อมชี้ตะกร้า",
        "script_brief": "ใครที่ยังใช้สายชาร์จโนเนมอยู่ต้องระวังให้ดีนะครับ ตัวนี้รองรับ Fast Charge พิกัดในตะกร้าด้านล่างได้เลยครับ",
        "duration": "30s",
    }

    monkeypatch.setattr(
        api_producer,
        "_generate_angle_with_gemini",
        lambda idea, url, product, resolved_images: mock_gemini_response if resolved_images else None,
    )

    payload = {
        "idea_text": "ไอเดียสายชาร์จ",
        "ref_url": "https://tiktok.com/@tech/video/999",
        "ref_images": [str(test_img)],
        "product_id": None,
    }

    res = client.post("/api/producer/ai-idea-to-angle", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["analysis"]["method"] == "gemini_vision"
    assert data["analysis"]["used_ref_images"] is True
    assert data["analysis"]["image_count"] == 1

    proposal = data["proposal"]
    assert proposal["angle_name"] == "มุมเตือนภัยจากภาพเรฟ"
    assert "USB-C" in proposal["visual_insights"]
    assert proposal["hook_title"] == "อย่าเพิ่งซื้อสายชาร์จใหม่ถ้ายังไม่รู้สิ่งนี้เด็ดขาด"
    assert "..." not in proposal["script_brief"]
    # Aliases
    assert proposal["hook"] == proposal["hook_title"]
    assert proposal["shoot_brief"] == proposal["shoot_angle_brief"]
    assert proposal["script"] == proposal["script_brief"]


def test_resolve_image_bytes_helper(tmp_path, monkeypatch):
    """Test image resolution for data URL, local files, and invalid paths."""
    monkeypatch.setattr(api_producer, "REFS_DIR", tmp_path)
    # 1. Data URL
    data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    res1 = api_producer._resolve_image_bytes(data_url)
    assert res1 is not None
    bytes_out, mime_out = res1
    assert mime_out == "image/png"
    assert len(bytes_out) > 0

    # 2. Local file
    test_file = tmp_path / "sample.jpg"
    test_file.write_bytes(b"dummy jpeg content")
    res2 = api_producer._resolve_image_bytes(str(test_file))
    assert res2 is not None
    assert res2[1] == "image/jpeg"
    assert res2[0] == b"dummy jpeg content"

    # 3. Non-existent file
    res3 = api_producer._resolve_image_bytes("non_existent_image_12345.jpg")
    assert res3 is None


def test_resolve_image_bytes_rejects_private_remote_address(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))],
    )
    assert api_producer._resolve_image_bytes("http://example.test/ref.png") is None


def test_resolve_image_bytes_rejects_redirects(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))],
    )

    class RedirectResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _limit):
            return b""

    class NoRedirectOpener:
        def open(self, *_args, **_kwargs):
            raise RuntimeError("redirect blocked")

    import urllib.request
    monkeypatch.setattr(urllib.request, "build_opener", lambda *_args: NoRedirectOpener())
    assert api_producer._resolve_image_bytes("https://example.test/ref.png") is None


def test_resolve_image_bytes_rejects_absolute_path_outside_allowed_roots(tmp_path):
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"private")
    assert api_producer._resolve_image_bytes(str(outside)) is None


def test_generate_angle_with_gemini_multimodal_client_call(monkeypatch):
    """Test that _generate_angle_with_gemini correctly builds contents with Part and calls Gemini Client."""
    class DummyResponse:
        text = json.dumps({
            "angle_name": "มุมแกะกล่องสินค้าตัวจริง",
            "visual_insights": "เห็นตัวกล่องแพ็กเกจจิ้งสีเขียวสะดุดตา และการเปิดฝาแบบสโลว์โมชั่น",
            "hook_title": "ของเพิ่งมาส่งสดๆ ร้อนๆ ลองแกะดูไปพร้อมกันเลยครับ",
            "target_audience": "สายชอบแกะกล่องรีวิว",
            "pain_point": "อยากเห็นสินค้าจริงก่อนตัดสินใจซื้อ",
            "shoot_angle_brief": "1. ถือกล่อง 2. เปิดฝาซูม 3. โชว์ของแถม",
            "script_brief": "เพิ่งได้ของมาสดๆ ร้อนๆ เลยครับ งานประกอบเนียนกริบ คุ้มเกินราคาจริงๆ พิกัดในตะกร้าด้านล่างได้เลยครับ",
            "duration": "30s",
        })

    class DummyModels:
        def generate_content(self, model, contents):
            # Verify contents structure
            assert len(contents) >= 2  # [system_prompt, Part]
            return DummyResponse()

    class DummyClient:
        def __init__(self, api_key):
            self.api_key = api_key
            self.models = DummyModels()

    import google.genai as genai_module
    monkeypatch.setattr(genai_module, "Client", DummyClient)
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_test_key_123")

    dummy_image = (b"image_bytes_here", "image/png")
    result = api_producer._generate_angle_with_gemini(
        idea="แกะกล่องของใหม่",
        url="https://tiktok.com",
        product={"name": "หูฟัง Bluetooth", "brand": "TechPro"},
        resolved_images=[dummy_image],
    )

    assert result is not None
    assert result["angle_name"] == "มุมแกะกล่องสินค้าตัวจริง"
    assert "แพ็กเกจจิ้ง" in result["visual_insights"]
    assert "..." not in result["hook_title"]


def test_ref_media_endpoint_only_serves_generated_reference_files(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_producer, "REFS_DIR", tmp_path)
    (tmp_path / "playbook_notes.json").write_text("private", encoding="utf-8")
    valid = tmp_path / "ref_0123456789ab.png"
    valid.write_bytes(b"not-a-real-png")

    assert client.get("/api/producer/ref-media/playbook_notes.json").status_code == 404
    assert client.get("/api/producer/ref-media/../playbook_notes.json").status_code == 404
    response = client.get("/api/producer/ref-media/ref_0123456789ab.png")
    assert response.status_code == 200
    assert response.content == b"not-a-real-png"
