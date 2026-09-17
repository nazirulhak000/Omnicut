"""Focused regression tests for the backend security-boundary agent.

These tests intentionally cover only the files owned by this agent:
``scripts/api_server.py`` and ``scripts/api_videos.py``.  They use temporary
roots and synthetic media signatures; no project media or secrets are read.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import scripts.api_videos as videos
import scripts.media_service as media_service


def _valid_mp4_bytes() -> bytes:
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"


def _configure_video_roots(monkeypatch, tmp_path):
    inbox = tmp_path / "00_Inbox"
    raw = tmp_path / "01_Raw"
    inbox.mkdir()
    raw.mkdir()
    monkeypatch.setattr(videos, "BASE_DIR", tmp_path)
    monkeypatch.setattr(videos, "INBOX_DIR", inbox)
    monkeypatch.setattr(videos, "RAW_DIR", raw)
    monkeypatch.setattr(media_service, "BASE_DIR", tmp_path)
    return inbox, raw


def _api_server_module_or_skip():
    """Load the real app unless unrelated parallel dashboard work is invalid."""
    try:
        import scripts.api_server as api_server
    except IndentationError as error:
        pytest.skip(f"unrelated parallel dashboard syntax error: {error}")
    return api_server


def _video_app():
    app = FastAPI()
    app.include_router(videos.router)
    return app


def test_unconfigured_server_defaults_to_loopback(monkeypatch):
    api_server = _api_server_module_or_skip()
    monkeypatch.delenv("OMNICUT_HOST", raising=False)
    monkeypatch.delenv("OMNICUT_API_KEY", raising=False)
    assert api_server.get_bind_host() == "127.0.0.1"


def test_unconfigured_lan_bind_is_rejected(monkeypatch):
    api_server = _api_server_module_or_skip()
    monkeypatch.setenv("OMNICUT_HOST", "0.0.0.0")
    monkeypatch.delenv("OMNICUT_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OMNICUT_API_KEY"):
        api_server.get_bind_host()


def test_configured_lan_bind_is_allowed(monkeypatch):
    api_server = _api_server_module_or_skip()
    monkeypatch.setenv("OMNICUT_HOST", "0.0.0.0")
    monkeypatch.setenv("OMNICUT_API_KEY", "test-boundary-key")
    assert api_server.get_bind_host() == "0.0.0.0"


def test_query_api_key_is_only_accepted_for_media(monkeypatch):
    api_server = _api_server_module_or_skip()
    monkeypatch.setenv("OMNICUT_API_KEY", "test-boundary-key")
    client = TestClient(api_server.app)

    assert client.get("/api/status?api_key=test-boundary-key").status_code == 401
    assert client.get(
        "/api/status", headers={"X-API-Key": "test-boundary-key"}
    ).status_code != 401
    assert client.get(
        "/api/media/04_Exports/missing.mp4?api_key=test-boundary-key"
    ).status_code != 401


def test_unconfigured_remote_client_is_rejected_even_if_server_was_bound_lan(monkeypatch):
    api_server = _api_server_module_or_skip()
    monkeypatch.delenv("OMNICUT_API_KEY", raising=False)
    client = TestClient(api_server.app, client=("192.168.1.25", 54321))
    assert client.get("/api/status").status_code == 401


@pytest.mark.parametrize(
    "relative",
    ["scripts/fake.mp4", "03_Projects/project/fake.mp4", "02_Assets/fake.mp4"],
)
def test_video_path_helper_rejects_non_raw_roots(monkeypatch, tmp_path, relative):
    _configure_video_roots(monkeypatch, tmp_path)
    outside = tmp_path / relative
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_bytes(_valid_mp4_bytes())

    with pytest.raises(HTTPException) as exc_info:
        videos._resolve_allowed_video_path(str(outside))
    assert exc_info.value.status_code == 403


def test_video_path_helper_rejects_symlink_escape(monkeypatch, tmp_path):
    inbox, _ = _configure_video_roots(monkeypatch, tmp_path)
    secret = tmp_path / "secret.mp4"
    secret.write_bytes(_valid_mp4_bytes())
    link = inbox / "looks-legit.mp4"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("OS account cannot create symbolic links")

    with pytest.raises(HTTPException) as exc_info:
        videos._resolve_allowed_video_path(str(link))
    assert exc_info.value.status_code == 403


def test_scene_catalog_rejects_video_path_outside_raw_roots(monkeypatch, tmp_path):
    _configure_video_roots(monkeypatch, tmp_path)
    outside = tmp_path / "03_Projects" / "secret.mp4"
    outside.parent.mkdir()
    outside.write_bytes(_valid_mp4_bytes())

    with pytest.raises(HTTPException) as exc_info:
        videos.get_raw_vault_scene_catalogs(str(outside))
    assert exc_info.value.status_code == 403


def test_upload_rejects_unknown_extension(monkeypatch, tmp_path):
    inbox, _ = _configure_video_roots(monkeypatch, tmp_path)
    client = TestClient(_video_app())
    response = client.post(
        "/api/upload",
        data={"target_dir": "inbox"},
        files={"file": ("payload.exe", b"MZnot-media", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert not list(inbox.iterdir())


def test_upload_rejects_invalid_magic_bytes(monkeypatch, tmp_path):
    inbox, _ = _configure_video_roots(monkeypatch, tmp_path)
    client = TestClient(_video_app())
    response = client.post(
        "/api/upload",
        data={"target_dir": "inbox"},
        files={"file": ("payload.mp4", b"not-an-mp4", "video/mp4")},
    )
    assert response.status_code == 415
    assert not list(inbox.iterdir())


def test_upload_enforces_configured_size_limit(monkeypatch, tmp_path):
    inbox, _ = _configure_video_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(videos, "MAX_UPLOAD_BYTES", len(_valid_mp4_bytes()) - 1)
    client = TestClient(_video_app())
    response = client.post(
        "/api/upload",
        data={"target_dir": "inbox"},
        files={"file": ("payload.mp4", _valid_mp4_bytes(), "video/mp4")},
    )
    assert response.status_code == 413
    assert not list(inbox.iterdir())


def test_upload_accepts_valid_mp4_and_keeps_existing_contract(monkeypatch, tmp_path):
    inbox, _ = _configure_video_roots(monkeypatch, tmp_path)
    client = TestClient(_video_app())
    response = client.post(
        "/api/upload",
        data={"target_dir": "inbox"},
        files={"file": ("payload.mp4", _valid_mp4_bytes(), "video/mp4")},
    )
    assert response.status_code == 200
    saved = Path(response.json()["file"]["path"])
    assert saved.parent == inbox
    assert saved.read_bytes() == _valid_mp4_bytes()


def test_asset_upload_rejects_invalid_magic_bytes(monkeypatch, tmp_path):
    _configure_video_roots(monkeypatch, tmp_path)
    music_dir = tmp_path / "02_Assets" / "Music"
    music_dir.mkdir(parents=True)
    monkeypatch.setattr(videos, "MUSIC_DIR", music_dir)
    monkeypatch.setattr(videos.AssetRegistry, "rebuild", lambda: None)
    client = TestClient(_video_app())

    response = client.post(
        "/api/assets/upload",
        data={"asset_type": "music"},
        files={"file": ("payload.wav", b"not-a-wav", "audio/wav")},
    )
    assert response.status_code == 415
    assert not list(music_dir.iterdir())
