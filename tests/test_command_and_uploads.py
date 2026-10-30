"""
tests/test_command_and_uploads.py — Offline deterministic tests for Phase 7 & Phase 8:
- Mobile AI Command Center (`/api/command/plan`, `/api/command/execute`)
- Masked AI Settings (`/api/settings/ai`, `PUT /api/settings/ai/keys`)
- Resumable Chunked Upload API (`/api/uploads/*`) with magic-byte validation & SHA-256 deduplication.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_command, api_uploads, config


@pytest.fixture()
def isolated_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create an isolated FastAPI TestClient using tmp_path for staging, inbox, and temp dirs."""
    staging = tmp_path / "staging_uploads"
    target = tmp_path / "inbox_uploads"
    tmp_dir = tmp_path / ".tmp"
    staging.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(api_uploads, "STAGING_DIR", staging)
    monkeypatch.setattr(api_uploads, "TARGET_DIR", target)
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)

    app = FastAPI()
    app.include_router(api_command.router)
    app.include_router(api_uploads.router)
    return TestClient(app)


# ============================================================================
# 1. Command Center Tests (Phase 7.2)
# ============================================================================

def test_command_plan_maps_thai_prompts_to_whitelist_intents(isolated_app: TestClient):
    res = isolated_app.post(
        "/api/command/plan",
        json={"prompt": "ผลิต 20 คลิปจากลิงก์นี้ https://vt.tiktok.com/ZS12345/", "product_code": "TTZ01"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "produce_couple_20"
    assert data["destructive"] is False
    assert data["requires_confirmation"] is False
    assert data["confirm_token"] is None
    assert data["params"]["product_code"] == "TTZ01"
    assert len(data["steps"]) >= 3

    res_rerender = isolated_app.post(
        "/api/command/plan",
        json={"prompt": "เรนเดอร์ใหม่คลิป s07"},
    )
    assert res_rerender.status_code == 200
    r_data = res_rerender.json()
    assert r_data["intent"] == "rerender_clip"
    assert r_data["params"]["clip_id"] == "s07"


def test_command_execute_enforces_intent_whitelist(isolated_app: TestClient):
    # Arbitrary / shell intent must be rejected with HTTP 400
    res = isolated_app.post(
        "/api/command/execute",
        json={
            "plan_id": "plan_fake",
            "intent": "rm -rf /",
            "params": {},
        },
    )
    assert res.status_code == 400

    # Valid non-destructive intent succeeds with HTTP 200
    ok_res = isolated_app.post(
        "/api/command/execute",
        json={
            "plan_id": "plan_valid",
            "intent": "check_status",
            "params": {},
        },
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["ok"] is True


def test_command_destructive_action_requires_valid_confirm_token(isolated_app: TestClient, tmp_path: Path):
    # Create a dummy file in .tmp to verify cleanup execution after confirmation
    dummy_tmp = tmp_path / ".tmp" / "scratch_probe.txt"
    dummy_tmp.write_text("temp", encoding="utf-8")

    # 1. Plan destructive action
    plan_res = isolated_app.post(
        "/api/command/plan",
        json={"prompt": "ล้างไฟล์ชั่วคราวในระบบ"},
    )
    assert plan_res.status_code == 200
    plan = plan_res.json()
    assert plan["intent"] == "cleanup_temp"
    assert plan["destructive"] is True
    assert plan["requires_confirmation"] is True
    assert plan["confirm_token"]

    # 2. Execute WITHOUT confirm_token -> must return 409
    no_token_res = isolated_app.post(
        "/api/command/execute",
        json={
            "plan_id": plan["plan_id"],
            "intent": plan["intent"],
            "params": plan["params"],
        },
    )
    assert no_token_res.status_code == 409
    err_body = no_token_res.json()
    assert err_body["detail"] == "confirmation_required"
    assert err_body["requires_confirmation"] is True
    assert dummy_tmp.exists()

    # 3. Execute WITH invalid confirm_token -> must return 409
    bad_token_res = isolated_app.post(
        "/api/command/execute",
        json={
            "plan_id": plan["plan_id"],
            "intent": plan["intent"],
            "params": plan["params"],
            "confirm_token": "invalid.token",
        },
    )
    assert bad_token_res.status_code == 409
    assert dummy_tmp.exists()

    # 4. Execute WITH valid confirm_token -> must return 200 and clean .tmp
    valid_res = isolated_app.post(
        "/api/command/execute",
        json={
            "plan_id": plan["plan_id"],
            "intent": plan["intent"],
            "params": plan["params"],
            "confirm_token": plan["confirm_token"],
        },
    )
    assert valid_res.status_code == 200
    v_body = valid_res.json()
    assert v_body["ok"] is True
    assert v_body["result"]["removed_files"] == 1
    assert not dummy_tmp.exists()


# ============================================================================
# 2. Masked AI Settings Tests (Phase 7.3)
# ============================================================================

def test_ai_settings_never_leaks_raw_aiza_keys(isolated_app: TestClient):
    fake_key_1 = "AIzaSyD9876543210abcdefABCDEF_1122"
    fake_key_2 = "AIzaSyD1234567890zyxwvuZYXWVU_9988"

    put_res = isolated_app.put(
        "/api/settings/ai/keys",
        json={"keys": [fake_key_1, fake_key_2]},
    )
    assert put_res.status_code == 200
    put_raw_text = json.dumps(put_res.json())
    assert "AIza" not in put_raw_text
    assert fake_key_1 not in put_raw_text
    assert fake_key_2 not in put_raw_text

    get_res = isolated_app.get("/api/settings/ai")
    assert get_res.status_code == 200
    data = get_res.json()
    raw_json_str = json.dumps(data)

    # Zero secret leakage guarantee
    assert "AIza" not in raw_json_str
    assert "AQ." not in raw_json_str
    assert fake_key_1 not in raw_json_str
    assert fake_key_2 not in raw_json_str

    assert data["key_count"] == 2
    assert len(data["keys_masked"]) == 2
    assert data["keys_masked"][0] == {"index": 1, "last4": "1122", "configured": True}
    assert data["keys_masked"][1] == {"index": 2, "last4": "9988", "configured": True}
    assert "gemini-3.8-flash-tts" in data["tts_models"]
    assert "gemini-3.1-flash-tts-preview" in data["tts_models"]
    assert data["llm_model"] == "gemini-2.5-flash"
    assert isinstance(data["agy_logged_in"], bool)


# ============================================================================
# 3. Resumable Chunked Upload & SHA-256 Deduplication Tests (Phase 8.1)
# ============================================================================

def _make_valid_mp4_bytes(payload_label: bytes = b"scene_01_video_stream") -> bytes:
    # ISO Base Media File Format header: 4-byte box size + 'ftyp' + 'isom'
    header = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41"
    return header + (payload_label * 64)


def test_chunked_upload_multi_patch_resume_and_sha256_dedupe(isolated_app: TestClient, tmp_path: Path):
    mp4_bytes = _make_valid_mp4_bytes(b"gadget_broll_clip_A")
    total_size = len(mp4_bytes)
    expected_sha = hashlib.sha256(mp4_bytes).hexdigest()

    # 1. Init session
    init_res = isolated_app.post(
        "/api/uploads/init",
        json={
            "filename": "broll_shot_01.mp4",
            "total_size": total_size,
            "mime_type": "video/mp4",
            "product_code": "TTZ01",
            "sha256": expected_sha,
        },
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    upload_id = init_data["upload_id"]
    assert init_data["chunk_size"] == 8388608
    assert init_data["offset"] == 0

    # 2. Send Chunk 1 (first 120 bytes)
    chunk1 = mp4_bytes[:120]
    p1 = isolated_app.patch(
        f"/api/uploads/{upload_id}",
        headers={"Upload-Offset": "0"},
        content=chunk1,
    )
    assert p1.status_code == 200
    assert p1.json()["offset"] == 120

    # 3. Simulate network drop: client queries GET /api/uploads/{upload_id} to check offset
    status_res = isolated_app.get(f"/api/uploads/{upload_id}")
    assert status_res.status_code == 200
    assert status_res.json()["offset"] == 120

    # 4. Sending wrong offset returns 409 with authoritative current_offset
    wrong_offset_res = isolated_app.patch(
        f"/api/uploads/{upload_id}",
        headers={"Upload-Offset": "0"},
        content=chunk1,
    )
    assert wrong_offset_res.status_code == 409
    assert wrong_offset_res.json()["current_offset"] == 120

    # 5. Resume from offset 120 with remaining bytes
    chunk2 = mp4_bytes[120:]
    p2 = isolated_app.patch(
        f"/api/uploads/{upload_id}",
        headers={"Upload-Offset": "120"},
        content=chunk2,
    )
    assert p2.status_code == 200
    assert p2.json()["offset"] == total_size

    # 6. Complete upload
    comp_res = isolated_app.post(f"/api/uploads/{upload_id}/complete")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["ok"] is True
    assert comp_data["deduplicated"] is False
    assert comp_data["sha256"] == expected_sha
    saved_path = Path(comp_data["path"])
    assert saved_path.exists()
    assert saved_path.read_bytes() == mp4_bytes

    # 7. Upload identical content again under a different filename -> must deduplicate (Rule 13)
    init_dup = isolated_app.post(
        "/api/uploads/init",
        json={
            "filename": "duplicate_copy_shot_01.mp4",
            "total_size": total_size,
            "mime_type": "video/mp4",
            "product_code": "TTZ01",
        },
    ).json()
    dup_id = init_dup["upload_id"]

    isolated_app.patch(
        f"/api/uploads/{dup_id}",
        headers={"Upload-Offset": "0"},
        content=mp4_bytes,
    )
    comp_dup = isolated_app.post(f"/api/uploads/{dup_id}/complete")
    assert comp_dup.status_code == 200
    dup_data = comp_dup.json()
    assert dup_data["deduplicated"] is True
    assert dup_data["path"] == str(saved_path)
    assert dup_data["sha256"] == expected_sha

    # Ensure only ONE file exists in target directory
    target_files = list(saved_path.parent.glob("*.mp4"))
    assert len(target_files) == 1


def test_chunked_upload_rejects_non_media_magic_bytes_with_415(isolated_app: TestClient):
    exe_payload = b"MZ\x90\x00\x03\x00\x00\x00_fake_windows_executable_payload"
    init_res = isolated_app.post(
        "/api/uploads/init",
        json={
            "filename": "disguised.mp4",
            "total_size": len(exe_payload),
            "mime_type": "video/mp4",
        },
    ).json()
    upload_id = init_res["upload_id"]

    patch_res = isolated_app.patch(
        f"/api/uploads/{upload_id}",
        headers={"Upload-Offset": "0"},
        content=exe_payload,
    )
    assert patch_res.status_code == 200

    comp_res = isolated_app.post(f"/api/uploads/{upload_id}/complete")
    assert comp_res.status_code == 415
