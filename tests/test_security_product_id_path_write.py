"""
Regression tests for the P0.5 4a security fix: `product_id` flowed straight
into `RAW_DIR / product_id` with zero validation in three places in
scripts/api_videos.py (list_raw_videos, upload_file, reassign_raw_video).

Because CORS is `allow_origins=["*"]` and no endpoint has authentication,
this was a remotely-reachable arbitrary file write: a relative traversal
(`..\\..\\Windows\\Temp`) escapes RAW_DIR, and an absolute path
(`C:\\Users\\Public`) makes `Path.__truediv__` discard RAW_DIR entirely,
letting the caller create directories (and, via /api/upload, write files)
anywhere the process has permission to write.

Fix: `_safe_product_dir()` resolves `RAW_DIR / product_id` and enforces
containment with `Path.relative_to()`, raising HTTP 400 on escape.

Isolated with tmp_path + monkeypatch per .agents/rules/testing_standard.md
rule 3 -- never touches the real 01_Raw/ or _Docs/products.json.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.api_videos as api_videos_mod
import scripts.media_service as media_service_mod
from scripts.api_server import app
from scripts import product_store as ps


def _valid_mp4_bytes():
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    """Redirects api_videos' module-level BASE_DIR/RAW_DIR/INBOX_DIR (bound
    at import time via `from scripts.config import ...`) into tmp_path, and
    ProductStore's STORE_PATH/BASE_DIR too since /api/upload calls
    ProductStore.add_video_to_product on success."""
    raw_dir = tmp_path / "01_Raw"
    inbox_dir = tmp_path / "00_Inbox"
    raw_dir.mkdir()
    inbox_dir.mkdir()

    monkeypatch.setattr(api_videos_mod, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_videos_mod, "RAW_DIR", raw_dir)
    monkeypatch.setattr(api_videos_mod, "INBOX_DIR", inbox_dir)
    monkeypatch.setattr(media_service_mod, "BASE_DIR", tmp_path)

    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)

    return {"base": tmp_path, "raw": raw_dir, "inbox": inbox_dir}


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# _safe_product_dir unit tests (no HTTP, fast, exact exploit inputs from the
# audit doc)
# ---------------------------------------------------------------------------

def test_safe_product_dir_accepts_legit_id(isolated_dirs):
    raw_dir = isolated_dirs["raw"]
    result = api_videos_mod._safe_product_dir(raw_dir, "20260907153012_1")
    assert result == (raw_dir / "20260907153012_1").resolve()


def test_safe_product_dir_rejects_relative_traversal(isolated_dirs):
    raw_dir = isolated_dirs["raw"]
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        api_videos_mod._safe_product_dir(raw_dir, "..\\..\\..\\Windows\\Temp")
    assert exc_info.value.status_code == 400


def test_safe_product_dir_rejects_absolute_path_escape(isolated_dirs, tmp_path):
    raw_dir = isolated_dirs["raw"]
    outside = tmp_path / "somewhere_else_entirely"
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        api_videos_mod._safe_product_dir(raw_dir, str(outside))
    assert exc_info.value.status_code == 400
    # Confirm the escape target was never created.
    assert not outside.exists()


# ---------------------------------------------------------------------------
# /api/upload -- the primary exploit target (arbitrary file WRITE)
# ---------------------------------------------------------------------------

def test_upload_rejects_absolute_product_id_arbitrary_write(isolated_dirs, client, tmp_path):
    evil_target = tmp_path / "attacker_controlled_dir"
    assert not evil_target.exists()

    resp = client.post(
        "/api/upload",
        data={"target_dir": "raw", "product_id": str(evil_target)},
        files={"file": ("clip.mp4", b"fake video bytes", "video/mp4")},
    )
    assert resp.status_code == 400
    # The core exploit: before the fix this directory would exist and
    # contain the uploaded file. It must not exist at all now.
    assert not evil_target.exists()


def test_upload_rejects_relative_traversal_product_id(isolated_dirs, client):
    resp = client.post(
        "/api/upload",
        data={"target_dir": "raw", "product_id": "..\\..\\..\\Windows\\Temp"},
        files={"file": ("clip.mp4", b"fake video bytes", "video/mp4")},
    )
    assert resp.status_code == 400
    # Nothing should have been written outside the sandboxed tmp_path tree.
    windows_temp_escape = Path(isolated_dirs["base"]).parent.parent.parent / "Windows" / "Temp"
    assert not windows_temp_escape.exists()


def test_upload_with_legit_product_id_still_works(isolated_dirs, client):
    # Upload now requires an existing product owned by the request's channel.
    ps._TABLE.save([{"id": "20260907153012_1", "name": "Upload fixture", "channel_id": "main", "videos": []}])
    resp = client.post(
        "/api/upload",
        data={"target_dir": "raw", "product_id": "20260907153012_1"},
        files={"file": ("clip.mp4", _valid_mp4_bytes(), "video/mp4")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Upload successful"
    dest_dir = isolated_dirs["raw"] / "20260907153012_1"
    assert dest_dir.exists()
    assert any(dest_dir.iterdir())


def test_upload_without_product_id_still_works(isolated_dirs, client):
    resp = client.post(
        "/api/upload",
        data={"target_dir": "inbox"},
        files={"file": ("clip.mp4", _valid_mp4_bytes(), "video/mp4")},
    )
    assert resp.status_code == 200
    inbox = isolated_dirs["inbox"]
    assert any(inbox.iterdir())


# ---------------------------------------------------------------------------
# /api/videos -- read-side variant (GET, product_id as query param)
# ---------------------------------------------------------------------------

def test_list_raw_videos_rejects_absolute_product_id(isolated_dirs, client, tmp_path):
    evil_target = tmp_path / "read_escape_dir"
    resp = client.get("/api/videos", params={"product_id": str(evil_target)})
    assert resp.status_code == 400
    assert not evil_target.exists()


def test_list_raw_videos_with_legit_product_id_still_works(isolated_dirs, client):
    resp = client.get("/api/videos", params={"product_id": "20260907153012_1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "videos" in data
    assert data["product_id"] == "20260907153012_1"


def test_list_raw_videos_without_product_id_still_works(isolated_dirs, client):
    resp = client.get("/api/videos")
    assert resp.status_code == 200
    data = resp.json()
    assert "videos" in data


# ---------------------------------------------------------------------------
# /api/raw-vault/reassign -- target_product_id has the same join-then-mkdir
# (then shutil.move) pattern; confirmed while auditing this file for other
# unsanitized product_id uses.
# ---------------------------------------------------------------------------

def test_reassign_rejects_absolute_target_product_id(isolated_dirs, client, tmp_path):
    raw_dir = isolated_dirs["raw"]
    src_video = raw_dir / "clip_to_move.mp4"
    src_video.write_bytes(b"dummy")

    evil_target = tmp_path / "reassign_escape_dir"
    resp = client.post(
        "/api/raw-vault/reassign",
        json={"video_path": str(src_video), "target_product_id": str(evil_target)},
    )
    assert resp.status_code == 400
    assert not evil_target.exists()
    # The source file must not have been moved anywhere.
    assert src_video.exists()


def test_reassign_with_legit_target_product_id_still_works(isolated_dirs, client):
    raw_dir = isolated_dirs["raw"]
    src_video = raw_dir / "clip_to_move2.mp4"
    src_video.write_bytes(b"dummy")

    product = ps.ProductStore.add(name="Test Product")
    target_id = product["id"]

    resp = client.post(
        "/api/raw-vault/reassign",
        json={"video_path": str(src_video), "target_product_id": target_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    dest_dir = raw_dir / target_id
    assert dest_dir.exists()
    assert (dest_dir / "clip_to_move2.mp4").exists()
