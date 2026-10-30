"""
tests/test_copilot_engine.py — Unit & Integration tests for AI Production Co-Pilot & HyperFrames Pipeline.
"""

import json
import os
import shutil
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts.config import BASE_DIR
from scripts import copilot_engine as copilot_mod
from scripts.copilot_engine import CopilotEngine
from scripts.product_store import ProductStore


@pytest.fixture
def mock_product():
    """Create a temporary test product in ProductStore and clean up after test."""
    product = ProductStore.add(
        name="พัดลมตั้งโต๊ะ Hatari Cyclone Max 8 นิ้ว",
        platform="tiktok",
        price_note="฿499",
        specs=["มอเตอร์พลังเทอร์โบ ลมแรง 3 ระดับ", "ประหยัดไฟเบอร์ 5", "รับประกัน 3 ปี"],
        images=["https://p16-oec-sg.ibyteimg.com/test_fan_1.jpg", "https://p16-oec-sg.ibyteimg.com/test_fan_2.jpg"],
        channel_id="main"
    )
    p_id = product["id"]
    yield product
    # Cleanup
    try:
        ProductStore.delete(p_id, force=True, channel_id="main")
    except Exception:
        pass


def test_copilot_session_creation(mock_product):
    """Verify session creation sets up initial welcome, product info, and angles."""
    session = CopilotEngine.create_session(
        product_id=mock_product["id"],
        channel_id="main",
        initial_prompt="ขอคลิปแบบฮาๆ"
    )
    assert session["session_id"].startswith("copilot-")
    assert session["product_name"] == "พัดลมตั้งโต๊ะ Hatari Cyclone Max 8 นิ้ว"
    assert len(session["suggested_angles"]) >= 4
    assert len(session["messages"]) >= 2  # welcome + initial prompt reply
    assert session["selected_angle"] is not None


def test_copilot_session_invalid_product():
    """Verify session creation rejects non-existent product."""
    with pytest.raises(ValueError, match="ไม่พบสินค้า"):
        CopilotEngine.create_session(product_id="non_existent_999", channel_id="main")


def test_copilot_chat_dialogue(mock_product):
    """Verify chat interaction updates creative direction and angle selection."""
    session = CopilotEngine.create_session(product_id=mock_product["id"], channel_id="main")
    s_id = session["session_id"]

    updated = CopilotEngine.chat(
        session_id=s_id,
        user_message="ขอน้องนุ้ยกับพี่บ่าวทะเลาะกันเรื่องพัดลม",
        channel_id="main"
    )
    assert len(updated["messages"]) == 3  # welcome + user + assistant
    last_msg = updated["messages"][-1]
    assert "น้องนุ้ย" in last_msg["content"] or "พี่บ่าว" in last_msg["content"]
    assert updated["selected_angle"]["style"] == "couple_paper_chat"


def test_copilot_generate_script_rules(mock_product):
    """Verify script generator follows strict project guidelines (no ellipses, turn format)."""
    session = CopilotEngine.create_session(product_id=mock_product["id"], channel_id="main")
    s_id = session["session_id"]

    updated = CopilotEngine.generate_script(session_id=s_id, style="couple_paper_chat", channel_id="main")
    script = updated.get("script")
    assert script is not None
    assert script["style"] == "couple_paper_chat"
    assert len(script["turns"]) >= 4
    assert len(script["headlines"]) >= 2

    # Strict Don't #7: No ellipsis in spoken or display script
    for turn in script["turns"]:
        assert turn["speaker"] in ("F", "M")
        for disp, spk in turn["phrases"]:
            assert "..." not in disp
            assert "…" not in disp
            assert "..." not in spk
            assert "…" not in spk


def test_copilot_build_hyperframes_draft(mock_product):
    """Verify full scaffolding of HyperFrames composition and ProductStore status update."""
    session = CopilotEngine.create_session(product_id=mock_product["id"], channel_id="main")
    s_id = session["session_id"]
    test_slug = f"test-hatari-pov-{os.urandom(3).hex()}"

    created_clip_dir = copilot_mod.CLIPS_DIR / test_slug
    created_assets_dir = copilot_mod.STUDIO_DIR / "assets" / "clips" / test_slug

    try:
        updated = CopilotEngine.build_hyperframes_draft(
            session_id=s_id,
            clip_slug=test_slug,
            channel_id="main",
            dry_run_audio=True
        )

        draft_info = updated.get("draft_info")
        assert draft_info is not None
        assert draft_info["status"] == "draft_ready"
        assert draft_info["draft_type"] == "hyperframes"
        assert draft_info["clip_id"] == test_slug

        # Check files on disk
        index_file = created_clip_dir / "index.html"
        meta_file = created_clip_dir / "meta.json"
        vo_file = created_assets_dir / "vo.wav"

        assert index_file.exists()
        assert meta_file.exists()
        assert vo_file.exists()

        # Validate index.html structure
        html_src = index_file.read_text(encoding="utf-8")
        assert f'data-composition-id="{test_slug}"' in html_src
        assert 'id="root"' in html_src
        assert 'video id="paper"' in html_src
        assert 'gsap.timeline' in html_src
        assert 'น้องนุ้ย' in html_src or 'พี่บ่าว' in html_src

        # Validate WAV audio format
        with wave.open(str(vo_file), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 48000
            assert wf.getnframes() > 0

        # Validate ProductStore angle status is in_production and preserves after reconcile
        prod = ProductStore.get(mock_product["id"], channel_id="main")
        matched_angle = next((a for a in prod.get("angles", []) if a.get("clip_id") == test_slug), None)
        assert matched_angle is not None
        assert matched_angle["status"] == "in_production"
        assert matched_angle["draft_type"] == "hyperframes"

    finally:
        # Cleanup test residue completely (Strict Rule #15)
        if created_clip_dir.exists():
            shutil.rmtree(created_clip_dir, ignore_errors=True)
        if created_assets_dir.exists():
            shutil.rmtree(created_assets_dir, ignore_errors=True)


def test_api_copilot_endpoints(mock_product):
    """Test full REST API workflow for Co-Pilot."""
    client = TestClient(app)
    headers = {"X-OmniCut-Channel": "main"}

    # 1. Create session
    resp = client.post(
        "/api/copilot/sessions",
        json={"product_id": mock_product["id"], "initial_prompt": "สร้างคลิปฮาๆ"},
        headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    session_id = data["session"]["session_id"]

    # 2. Get session
    resp_get = client.get(f"/api/copilot/sessions/{session_id}", headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["session"]["session_id"] == session_id

    # 3. Chat in session
    resp_chat = client.post(
        f"/api/copilot/sessions/{session_id}/chat",
        json={"message": "ขอสไตล์คู่รักสายใต้น้องนุ้ยกับพี่บ่าว"},
        headers=headers
    )
    assert resp_chat.status_code == 200
    assert resp_chat.json()["success"] is True

    # 4. Generate script
    resp_script = client.post(
        f"/api/copilot/sessions/{session_id}/generate-script",
        json={"style": "couple_paper_chat"},
        headers=headers
    )
    assert resp_script.status_code == 200
    script = resp_script.json()["session"]["script"]
    assert script["style"] == "couple_paper_chat"

    # 5. Build HyperFrames draft
    test_slug = f"api-test-pov-{os.urandom(3).hex()}"
    created_clip_dir = copilot_mod.CLIPS_DIR / test_slug
    created_assets_dir = copilot_mod.STUDIO_DIR / "assets" / "clips" / test_slug

    try:
        resp_draft = client.post(
            f"/api/copilot/sessions/{session_id}/build-draft",
            json={"clip_slug": test_slug, "dry_run_audio": True},
            headers=headers
        )
        assert resp_draft.status_code == 200, resp_draft.text
        draft_info = resp_draft.json()["session"]["draft_info"]
        assert draft_info["status"] == "draft_ready"
        assert draft_info["clip_id"] == test_slug
        assert (created_clip_dir / "index.html").exists()
    finally:
        # Cleanup
        if created_clip_dir.exists():
            shutil.rmtree(created_clip_dir, ignore_errors=True)
        if created_assets_dir.exists():
            shutil.rmtree(created_assets_dir, ignore_errors=True)
