"""
Unit tests for Round SAFE-1:
1. Disk Space Guard before render (minimum 3.0 GB check).
2. Rolling 3-version backup snapshots (.bak1, .bak2, .bak3) and recovery in ProjectManifest.
"""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts.api_render import check_disk_space, MIN_FREE_DISK_BYTES
from scripts.project_manifest import ProjectManifest


@pytest.fixture
def client():
    return TestClient(app)


# --------------------------------------------------------------------------
# 1. Disk Space Guard Tests
# --------------------------------------------------------------------------

def test_check_disk_space_real():
    """Verifies that check_disk_space returns valid metrics on the real filesystem."""
    res = check_disk_space()
    assert "free_bytes" in res
    assert "total_bytes" in res
    assert "free_gb" in res
    assert "is_sufficient" in res
    assert res["min_required_gb"] == 3.0
    assert isinstance(res["is_sufficient"], bool)


def test_check_disk_space_simulated_low_disk():
    """Verifies that check_disk_space flags disk as insufficient when < 3GB."""
    fake_usage = shutil._ntuple_diskusage(100 * 1024**3, 98 * 1024**3, 2 * 1024**3)  # 2GB free
    with patch("shutil.disk_usage", return_value=fake_usage):
        res = check_disk_space()
        assert res["is_sufficient"] is False
        assert res["free_gb"] == 2.0


def test_check_disk_space_simulated_sufficient_disk():
    """Verifies that check_disk_space flags disk as sufficient when >= 3GB."""
    fake_usage = shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3)  # 50GB free
    with patch("shutil.disk_usage", return_value=fake_usage):
        res = check_disk_space()
        assert res["is_sufficient"] is True
        assert res["free_gb"] == 50.0


def test_disk_probe_failure_blocks_render_instead_of_failing_open():
    with patch("shutil.disk_usage", side_effect=OSError("disk probe unavailable")):
        res = check_disk_space()
    assert res["is_sufficient"] is False
    assert "disk probe unavailable" in res["error"]


def test_get_render_disk_check_endpoint(client):
    """Verifies GET /api/render/disk-check returns valid response."""
    resp = client.get("/api/render/disk-check")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_sufficient" in data
    assert data["min_required_gb"] == 3.0


def test_trigger_render_blocks_when_disk_space_low(client):
    """Verifies POST /api/render halts with 507 when free space is < 3GB."""
    fake_usage = shutil._ntuple_diskusage(100 * 1024**3, 99 * 1024**3, int(1.5 * 1024**3))  # 1.5GB
    with patch("shutil.disk_usage", return_value=fake_usage):
        resp = client.post("/api/render", json={
            "raw_video_path": "nonexistent.mp4",
            "product_name": "Test Product",
            "project_name": "test_proj_low_disk",
            "key_features": "Feature 1, Feature 2",
            "pain_point": "Pain point description",
            "price_deal": "Special discount",
        })
        assert resp.status_code == 507
        detail = resp.json().get("detail", "")
        assert "พื้นที่ว่างบนดิสก์เหลือน้อยเกินไป" in detail
        assert "1.5 GB" in detail


def test_trigger_render_blocks_when_disk_probe_fails(client):
    with patch("shutil.disk_usage", side_effect=OSError("disk probe unavailable")):
        resp = client.post("/api/render", json={
            "raw_video_path": "nonexistent.mp4",
            "product_name": "Test Product",
            "project_name": "test_proj_disk_probe",
            "key_features": "offline",
            "pain_point": "offline",
            "price_deal": "offline",
        })
    assert resp.status_code == 507
    assert "ตรวจสอบพื้นที่ว่าง" in resp.json()["detail"]


# --------------------------------------------------------------------------
# 2. Rolling 3-Version Snapshots Tests
# --------------------------------------------------------------------------

def test_manifest_rolling_3_snapshots(tmp_path, monkeypatch):
    """Verifies that multiple saves create .bak1, .bak2, .bak3 rolling snapshots."""
    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", tmp_path)
    proj_name = "test_rolling_manifest"

    # Save 1: Initial manifest
    ProjectManifest.save(proj_name, title="Version 1", step="v1")
    p_dir = tmp_path / proj_name
    main_file = p_dir / "project.json"
    assert main_file.exists()
    assert not (p_dir / "project.json.bak1").exists()

    # Save 2: Should back up v1 to .bak1 and .bak
    ProjectManifest.save(proj_name, title="Version 2", step="v2")
    assert (p_dir / "project.json.bak1").exists()
    assert (p_dir / "project.json.bak").exists()
    bak1_data = json.loads((p_dir / "project.json.bak1").read_text(encoding="utf-8"))
    assert bak1_data.get("title") == "Version 1"

    # Save 3: Should shift .bak1 -> .bak2, v2 -> .bak1
    ProjectManifest.save(proj_name, title="Version 3", step="v3")
    assert (p_dir / "project.json.bak2").exists()
    bak2_data = json.loads((p_dir / "project.json.bak2").read_text(encoding="utf-8"))
    assert bak2_data.get("title") == "Version 1"
    bak1_data = json.loads((p_dir / "project.json.bak1").read_text(encoding="utf-8"))
    assert bak1_data.get("title") == "Version 2"

    # Save 4: Should shift .bak2 -> .bak3, .bak1 -> .bak2, v3 -> .bak1
    ProjectManifest.save(proj_name, title="Version 4", step="v4")
    assert (p_dir / "project.json.bak3").exists()
    bak3_data = json.loads((p_dir / "project.json.bak3").read_text(encoding="utf-8"))
    assert bak3_data.get("title") == "Version 1"
    bak2_data = json.loads((p_dir / "project.json.bak2").read_text(encoding="utf-8"))
    assert bak2_data.get("title") == "Version 2"
    bak1_data = json.loads((p_dir / "project.json.bak1").read_text(encoding="utf-8"))
    assert bak1_data.get("title") == "Version 3"

    # Current main should be v4
    curr_data = ProjectManifest.load(proj_name)
    assert curr_data.get("title") == "Version 4"


def test_manifest_recovery_from_backup_when_primary_corrupted(tmp_path, monkeypatch):
    """Verifies that load() seamlessly recovers from .bak1 when project.json is corrupted."""
    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", tmp_path)
    proj_name = "test_corrupt_recovery"

    ProjectManifest.save(proj_name, title="Good Version 1")
    ProjectManifest.save(proj_name, title="Good Version 2")

    p_dir = tmp_path / proj_name
    main_file = p_dir / "project.json"
    # Intentionally corrupt primary file
    main_file.write_text("{ corrupt json !!", encoding="utf-8")

    # load() should automatically fall back to .bak1
    recovered = ProjectManifest.load(proj_name)
    assert recovered is not None
    assert recovered.get("title") == "Good Version 1"


def test_manifest_get_snapshots_and_restore(tmp_path, monkeypatch, client):
    """Verifies get_snapshots() and restore_snapshot() functionality both in class and API."""
    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", tmp_path)
    proj_name = "test_snapshot_api"

    ProjectManifest.save(proj_name, title="Snapshot A")
    ProjectManifest.save(proj_name, title="Snapshot B")
    ProjectManifest.save(proj_name, title="Snapshot C")

    # Check snapshots via class
    snapshots = ProjectManifest.get_snapshots(proj_name)
    assert len(snapshots) >= 2
    snap_ids = [s["id"] for s in snapshots]
    assert "bak1" in snap_ids

    # Check snapshots via API
    resp = client.get(f"/api/projects/{proj_name}/snapshots")
    assert resp.status_code == 200
    api_data = resp.json()
    assert api_data["project_name"] == proj_name
    assert len(api_data["snapshots"]) >= 2

    # Restore from bak2 (which should have Snapshot A)
    restore_resp = client.post(f"/api/projects/{proj_name}/snapshots/bak2/restore")
    assert restore_resp.status_code == 200
    restored_manifest = restore_resp.json()["manifest"]
    assert restored_manifest["title"] == "Snapshot A"

    # Verify primary project.json is now Snapshot A
    current = ProjectManifest.load(proj_name)
    assert current["title"] == "Snapshot A"
