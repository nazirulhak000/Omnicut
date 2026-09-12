"""
Unit tests for Round POSTED-CLIP-LIFECYCLE-1:
Zero-Risk Archive & Studio Lockout Flow
- ProjectManifest.archive moves a project folder from PROJECTS_DIR to ARCHIVE_DIR/Projects.
- Endpoint POST /projects/{project_name}/archive works as expected.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts.project_manifest import ProjectManifest


@pytest.fixture
def client():
    return TestClient(app)


def test_project_manifest_archive_moves_folder(tmp_path, monkeypatch):
    test_projects = tmp_path / "03_Projects"
    test_projects.mkdir()
    test_archive = tmp_path / "06_Archive"
    test_archive.mkdir()

    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", test_projects)
    monkeypatch.setattr("scripts.project_manifest.ARCHIVE_DIR", test_archive)
    monkeypatch.setattr("scripts.project_manifest.BASE_DIR", tmp_path)

    # Create dummy project folder
    proj_dir = test_projects / "TEST_PROJ_01"
    proj_dir.mkdir()
    manifest_path = proj_dir / "project.json"
    manifest_path.write_text(json.dumps({"project_name": "TEST_PROJ_01", "is_posted": True}), encoding="utf-8")

    # Run archive
    res = ProjectManifest.archive("TEST_PROJ_01")
    assert res["project_name"] == "TEST_PROJ_01"
    assert not proj_dir.exists()

    archived_dest = test_archive / "Projects" / "TEST_PROJ_01"
    assert archived_dest.exists()
    assert (archived_dest / "project.json").exists()


def test_project_manifest_archive_rejects_missing_or_invalid(tmp_path, monkeypatch):
    test_projects = tmp_path / "03_Projects"
    test_projects.mkdir()
    test_archive = tmp_path / "06_Archive"
    test_archive.mkdir()

    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", test_projects)
    monkeypatch.setattr("scripts.project_manifest.ARCHIVE_DIR", test_archive)
    monkeypatch.setattr("scripts.project_manifest.BASE_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        ProjectManifest.archive("NON_EXISTENT")

    with pytest.raises(ValueError, match="อยู่นอกโฟลเดอร์โปรเจกต์"):
        ProjectManifest.archive("../Outside")


def test_api_archive_project_endpoint(client, tmp_path, monkeypatch):
    test_projects = tmp_path / "03_Projects"
    test_projects.mkdir()
    test_archive = tmp_path / "06_Archive"
    test_archive.mkdir()

    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", test_projects)
    monkeypatch.setattr("scripts.project_manifest.ARCHIVE_DIR", test_archive)
    monkeypatch.setattr("scripts.project_manifest.BASE_DIR", tmp_path)

    proj_dir = test_projects / "API_TEST_PROJ"
    proj_dir.mkdir()
    (proj_dir / "project.json").write_text(json.dumps({"project_name": "API_TEST_PROJ"}), encoding="utf-8")

    response = client.post("/api/projects/API_TEST_PROJ/archive")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["project_name"] == "API_TEST_PROJ"
    assert not proj_dir.exists()
    assert (test_archive / "Projects" / "API_TEST_PROJ").exists()
