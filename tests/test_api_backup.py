"""Unit tests for /api/backup endpoints using isolated temporary directories."""
from pathlib import Path
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.api_backup import router


@pytest.fixture
def backup_test_client(tmp_path: Path, monkeypatch):
    """Sets up an isolated FastAPI test client with mocked directories."""
    docs_dir = tmp_path / "_Docs"
    projects_dir = tmp_path / "03_Projects"
    backup_dir = tmp_path / "06_Archive" / "Backups"

    docs_dir.mkdir(parents=True)
    projects_dir.mkdir(parents=True)
    backup_dir.mkdir(parents=True)

    (docs_dir / "products.json").write_text(json.dumps({"products": []}), encoding="utf-8")
    proj = projects_dir / "PROJ_TEST"
    proj.mkdir()
    (proj / "project.json").write_text(json.dumps({"title": "Test"}), encoding="utf-8")

    monkeypatch.setattr("scripts.backup_engine.BASE_DIR", tmp_path)
    monkeypatch.setattr("scripts.backup_engine.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("scripts.backup_engine.DOCS_DIR", docs_dir)
    monkeypatch.setattr("scripts.backup_engine.PROJECTS_DIR", projects_dir)

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_api_backup_create_and_list(backup_test_client):
    # Initially list is empty
    res = backup_test_client.get("/api/backup/list")
    assert res.status_code == 200
    assert len(res.json()["backups"]) == 0

    # Create backup
    create_res = backup_test_client.post("/api/backup/create")
    assert create_res.status_code == 200
    data = create_res.json()
    assert data["status"] == "ok"
    fname = data["backup"]["backup_name"]
    assert fname.startswith("omnicut_backup_")

    # List shows 1 backup
    list_res = backup_test_client.get("/api/backup/list")
    assert list_res.status_code == 200
    backups = list_res.json()["backups"]
    assert len(backups) == 1
    assert backups[0]["backup_name"] == fname


def test_api_backup_download_and_verify(backup_test_client):
    create_res = backup_test_client.post("/api/backup/create")
    fname = create_res.json()["backup"]["backup_name"]

    # Verify endpoint
    verify_res = backup_test_client.get(f"/api/backup/verify/{fname}")
    assert verify_res.status_code == 200
    assert verify_res.json()["verification"]["is_valid"] is True

    # Download endpoint
    dl_res = backup_test_client.get(f"/api/backup/download/{fname}")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/zip"
    assert len(dl_res.content) > 0


def test_api_backup_traversal_prevention(backup_test_client):
    # Download with traversal should return 400
    res = backup_test_client.get("/api/backup/download/..%2Fetc%2Fpasswd")
    assert res.status_code in (400, 404)


def test_api_backup_delete(backup_test_client):
    create_res = backup_test_client.post("/api/backup/create")
    fname = create_res.json()["backup"]["backup_name"]

    # Delete
    del_res = backup_test_client.delete(f"/api/backup/{fname}")
    assert del_res.status_code == 200

    # Verify not found now
    res_404 = backup_test_client.get(f"/api/backup/verify/{fname}")
    assert res_404.status_code == 404
