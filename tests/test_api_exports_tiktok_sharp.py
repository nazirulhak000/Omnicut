"""Test suite for /api/exports/enhance-tiktok endpoint."""

import shutil
import subprocess
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.api_exports import router


def create_dummy_clip(destination: Path, duration: float = 0.5):
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", f"color=c=green:s=1080x1920:d={duration}:r=30",
        "-f", "lavfi", "-i", f"sine=frequency=800:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        str(destination)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.fixture
def api_client(tmp_path: Path, monkeypatch):
    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    posted_dir = tmp_path / "04_Exports" / "Posted"
    exports_dir.mkdir(parents=True)
    posted_dir.mkdir(parents=True)

    monkeypatch.setattr("scripts.api_exports.BASE_DIR", tmp_path)
    monkeypatch.setattr("scripts.api_exports.EXPORTS_DIR", exports_dir)
    monkeypatch.setattr("scripts.api_exports.POSTED_DIR", posted_dir)

    app = FastAPI()
    app.include_router(router)
    return TestClient(app), exports_dir, tmp_path


def test_api_enhance_tiktok_success(api_client):
    client, exports_dir, base_dir = api_client
    clip = exports_dir / "test_clip.mp4"
    create_dummy_clip(clip, duration=0.5)

    rel_path = str(clip.relative_to(base_dir)).replace("\\", "/")
    response = client.post("/api/exports/enhance-tiktok", json={"path": rel_path})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "test_clip_tiktok_sharp.mp4" in data["enhanced_path"]

    enhanced_file = base_dir / data["enhanced_path"]
    assert enhanced_file.is_file()
    assert enhanced_file.stat().st_size > 0


def test_api_enhance_tiktok_missing_path(api_client):
    client, _, _ = api_client
    response = client.post("/api/exports/enhance-tiktok", json={})
    assert response.status_code == 400


def test_api_enhance_tiktok_not_found(api_client):
    client, _, _ = api_client
    response = client.post("/api/exports/enhance-tiktok", json={"path": "04_Exports/Ready_to_post/none.mp4"})
    assert response.status_code == 404


def test_api_enhance_tiktok_forbidden_path(api_client):
    client, _, base_dir = api_client
    secret = base_dir / "secret.txt"
    secret.write_text("hello", encoding="utf-8")

    response = client.post("/api/exports/enhance-tiktok", json={"path": "secret.txt"})
    assert response.status_code == 403
