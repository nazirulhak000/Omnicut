"""
tests/test_mobile_chunked_upload_parity.py — Deterministic Offline Parity Tests for Mobile Chunked Uploads:
- Multi-part chunked upload with `target_dir="raw"` and `product_id="test_prod_uuid"`.
- Chunk appending via `PATCH /api/uploads/{upload_id}`.
- Offset synchronization query via `GET /api/uploads/{upload_id}` and 409 Conflict on mismatch.
- Completion via `POST /api/uploads/{upload_id}/complete` verifying:
  * File created in target `01_Raw/test_prod_uuid/`.
  * Canonical `file_info` containing `rel_path`, `path`, `size`, and `duration`.
  * Automatic attachment into `ProductStore` videos list.
- Rule 13 SHA-256 Deduplication (Strict Zero-Duplicate Guard).
- Target directory routing (`target_dir="inbox"` fallback).
- Strict cleanup (Rule 11 & 15) using isolated `tmp_path`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_uploads, config
from scripts import product_store as ps
from scripts.product_store import ProductStore


def _make_valid_mp4(label: bytes = b"mobile_raw_camera_roll_clip") -> bytes:
    """Create valid MP4 binary payload passing media magic-byte validation."""
    header = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41"
    return header + (label * 64)


@pytest.fixture()
def isolated_chunked_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """Isolate staging, raw, inbox, and product store entirely inside tmp_path (Rules 11 & 15)."""
    base_dir = tmp_path / "project_root"
    raw_dir = base_dir / "01_Raw"
    inbox_dir = base_dir / "00_Inbox"
    staging_dir = base_dir / "03_Projects" / ".cache" / "uploads"
    docs_dir = base_dir / "_Docs"

    for d in (base_dir, raw_dir, inbox_dir, staging_dir, docs_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Monkeypatch config paths
    monkeypatch.setattr(config, "BASE_DIR", base_dir)
    monkeypatch.setattr(config, "RAW_DIR", raw_dir)
    monkeypatch.setattr(config, "INBOX_DIR", inbox_dir)

    # Monkeypatch api_uploads directory overrides
    monkeypatch.setattr(api_uploads, "STAGING_DIR", staging_dir)
    monkeypatch.setattr(api_uploads, "TARGET_DIR", None)

    # Monkeypatch ProductStore storage
    store_file = docs_dir / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_file)
    monkeypatch.setattr(ps, "BASE_DIR", base_dir)

    # Seed test product in ProductStore
    test_prod_id = "test_prod_uuid"
    with ProductStore._mutate() as prods:
        prods.append({
            "id": test_prod_id,
            "name": "Mobile Test Gadget 1080p",
            "product_code": "MTEST01",
            "videos": [],
            "status": "candidate",
        })

    app = FastAPI()
    app.include_router(api_uploads.router)
    client = TestClient(app)

    return {
        "client": client,
        "base_dir": base_dir,
        "raw_dir": raw_dir,
        "inbox_dir": inbox_dir,
        "staging_dir": staging_dir,
        "product_id": test_prod_id,
    }


def test_chunked_upload_mobile_raw_flow_and_product_attachment(isolated_chunked_env: Dict[str, Any]):
    """Test full multi-part mobile upload lifecycle for raw product footage."""
    client: TestClient = isolated_chunked_env["client"]
    raw_dir: Path = isolated_chunked_env["raw_dir"]
    product_id: str = isolated_chunked_env["product_id"]

    mp4_bytes = _make_valid_mp4(b"test_angle_1_take_1")
    total_size = len(mp4_bytes)
    sha256_hex = hashlib.sha256(mp4_bytes).hexdigest()

    # 1. Initialize upload session
    init_res = client.post(
        "/api/uploads/init",
        json={
            "filename": "mobile_take_01.mp4",
            "total_size": total_size,
            "mime_type": "video/mp4",
            "product_id": product_id,
            "target_dir": "raw",
            "sha256": sha256_hex,
        },
    )
    assert init_res.status_code == 200
    init_data = init_res.json()
    upload_id = init_data["upload_id"]
    assert init_data["offset"] == 0
    assert init_data["total_size"] == total_size

    # 2. Upload Chunk 1 (first 100 bytes)
    chunk1 = mp4_bytes[:100]
    p1 = client.patch(
        f"/api/uploads/{upload_id}",
        headers={"Upload-Offset": "0"},
        content=chunk1,
    )
    assert p1.status_code == 200
    assert p1.json()["offset"] == 100

    # 3. Query offset sync via GET /api/uploads/{upload_id} (simulating client reconnect)
    sync_res = client.get(f"/api/uploads/{upload_id}")
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["offset"] == 100
    assert sync_data["total_size"] == total_size
    assert sync_data["status"] == "uploading"

    # 4. Out-of-order chunk returns 409 with current authoritative offset
    conflict_res = client.patch(
        f"/api/uploads/{upload_id}",
        headers={"Upload-Offset": "0"},
        content=chunk1,
    )
    assert conflict_res.status_code == 409
    assert conflict_res.json()["current_offset"] == 100

    # 5. Send Chunk 2 (remaining bytes from offset 100)
    chunk2 = mp4_bytes[100:]
    p2 = client.patch(
        f"/api/uploads/{upload_id}",
        headers={"Upload-Offset": "100"},
        content=chunk2,
    )
    assert p2.status_code == 200
    assert p2.json()["offset"] == total_size

    # 6. Complete upload
    comp_res = client.post(f"/api/uploads/{upload_id}/complete")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["ok"] is True
    assert comp_data["message"] == "Upload successful"
    assert comp_data["deduplicated"] is False
    assert comp_data["sha256"] == sha256_hex

    # Assert canonical file_info structure
    file_info = comp_data.get("file")
    assert file_info is not None, "Expected 'file' object in complete response"
    assert "rel_path" in file_info
    assert "path" in file_info
    assert "size" in file_info
    assert "duration" in file_info
    assert file_info["size"] == total_size

    # Assert file exists in target 01_Raw/<product_id>/
    target_product_dir = raw_dir / product_id
    assert target_product_dir.exists()
    final_file = Path(file_info["path"])
    assert final_file.exists()
    assert final_file.parent == target_product_dir
    assert final_file.read_bytes() == mp4_bytes

    # Assert product in ProductStore has the video in its videos list
    prod = ProductStore.get(product_id)
    assert prod is not None
    assert len(prod.get("videos", [])) >= 1
    attached_paths = [v.get("path") for v in prod["videos"]]
    assert str(final_file) in attached_paths


def test_chunked_upload_rule13_sha256_deduplication(isolated_chunked_env: Dict[str, Any]):
    """Test Rule 13: Uploading identical bytes under different filenames must deduplicate."""
    client: TestClient = isolated_chunked_env["client"]
    raw_dir: Path = isolated_chunked_env["raw_dir"]
    product_id: str = isolated_chunked_env["product_id"]

    mp4_bytes = _make_valid_mp4(b"unique_sensor_footage_broll")
    total_size = len(mp4_bytes)
    sha256_hex = hashlib.sha256(mp4_bytes).hexdigest()

    # 1. First upload
    init1 = client.post(
        "/api/uploads/init",
        json={
            "filename": "camera_angle_A.mp4",
            "total_size": total_size,
            "product_id": product_id,
            "target_dir": "raw",
        },
    ).json()
    client.patch(
        f"/api/uploads/{init1['upload_id']}",
        headers={"Upload-Offset": "0"},
        content=mp4_bytes,
    )
    comp1 = client.post(f"/api/uploads/{init1['upload_id']}/complete").json()
    assert comp1["deduplicated"] is False
    saved_first_path = comp1["path"]

    # 2. Upload identical content under a different filename
    init2 = client.post(
        "/api/uploads/init",
        json={
            "filename": "camera_angle_A_duplicate.mp4",
            "total_size": total_size,
            "product_id": product_id,
            "target_dir": "raw",
        },
    ).json()
    client.patch(
        f"/api/uploads/{init2['upload_id']}",
        headers={"Upload-Offset": "0"},
        content=mp4_bytes,
    )
    comp2 = client.post(f"/api/uploads/{init2['upload_id']}/complete").json()

    assert comp2["ok"] is True
    assert comp2["deduplicated"] is True
    assert comp2["sha256"] == sha256_hex
    assert comp2["path"] == saved_first_path

    # Assert exactly 1 MP4 file exists in target directory (Zero duplicate on disk)
    target_product_dir = raw_dir / product_id
    target_files = list(target_product_dir.glob("*.mp4"))
    assert len(target_files) == 1


def test_chunked_upload_target_dir_inbox(isolated_chunked_env: Dict[str, Any]):
    """Test chunked upload targeting 'inbox' directory."""
    client: TestClient = isolated_chunked_env["client"]
    inbox_dir: Path = isolated_chunked_env["inbox_dir"]

    mp4_bytes = _make_valid_mp4(b"inbox_broll_sample")
    total_size = len(mp4_bytes)

    init_res = client.post(
        "/api/uploads/init",
        json={
            "filename": "inbox_clip.mp4",
            "total_size": total_size,
            "target_dir": "inbox",
            "product_code": "PROD99",
        },
    ).json()
    upload_id = init_res["upload_id"]

    client.patch(
        f"/api/uploads/{upload_id}",
        headers={"Upload-Offset": "0"},
        content=mp4_bytes,
    )
    comp_res = client.post(f"/api/uploads/{upload_id}/complete").json()
    assert comp_res["ok"] is True

    saved_path = Path(comp_res["path"])
    assert saved_path.exists()
    assert inbox_dir in saved_path.parents
