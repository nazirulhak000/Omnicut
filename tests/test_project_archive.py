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


def _setup_archive_dirs(tmp_path, monkeypatch):
    test_projects = tmp_path / "03_Projects"
    test_projects.mkdir()
    test_archive = tmp_path / "06_Archive"
    test_archive.mkdir()
    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", test_projects)
    monkeypatch.setattr("scripts.project_manifest.ARCHIVE_DIR", test_archive)
    monkeypatch.setattr("scripts.project_manifest.BASE_DIR", tmp_path)
    return test_projects, test_archive / "Projects"


def test_archive_same_name_twice_keeps_both(tmp_path, monkeypatch):
    projects, archive = _setup_archive_dirs(tmp_path, monkeypatch)

    first = projects / "DUP"
    first.mkdir()
    (first / "a.txt").write_text("first", encoding="utf-8")
    res1 = ProjectManifest.archive("DUP")

    second = projects / "DUP"
    second.mkdir()
    (second / "b.txt").write_text("second", encoding="utf-8")
    res2 = ProjectManifest.archive("DUP")

    assert res1["archived_to"] != res2["archived_to"]
    dest1 = tmp_path / res1["archived_to"]
    dest2 = tmp_path / res2["archived_to"]
    assert (dest1 / "a.txt").read_text(encoding="utf-8") == "first"
    assert (dest2 / "b.txt").read_text(encoding="utf-8") == "second"
    assert res2["project_name"] == "DUP"


def test_archive_move_failure_keeps_old_archive(tmp_path, monkeypatch):
    projects, archive = _setup_archive_dirs(tmp_path, monkeypatch)
    old = archive / "KEEP"
    old.mkdir(parents=True)
    (old / "old.txt").write_text("old", encoding="utf-8")
    proj = projects / "KEEP"
    proj.mkdir()
    (proj / "new.txt").write_text("new", encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise OSError("simulated move failure")

    monkeypatch.setattr("scripts.project_manifest.shutil.move", boom)
    with pytest.raises(OSError):
        ProjectManifest.archive("KEEP")

    assert (old / "old.txt").read_text(encoding="utf-8") == "old"
    assert (proj / "new.txt").exists()
