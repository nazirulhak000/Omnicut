"""
Unit tests for Analytics Hub API endpoints:
- GET /api/analytics/production
- GET /api/analytics/storage
- POST /api/analytics/storage/purge-safe-cache
- GET /api/analytics/inventory
"""

import pytest
from fastapi.testclient import TestClient
from scripts.api_server import app
import scripts.api_analytics as analytics

client = TestClient(app)


def test_production_analytics_endpoint():
    resp = client.get("/api/analytics/production")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    summary = data["summary"]
    assert "total_products" in summary
    assert "total_angles" in summary
    assert "scripted" in summary
    assert "in_production" in summary
    assert "rendered" in summary
    assert "posted" in summary
    assert "angle_types" in data
    assert "recent_productions" in data


def test_storage_analytics_endpoint():
    resp = client.get("/api/analytics/storage")
    assert resp.status_code == 200
    data = resp.json()
    assert "drive" in data
    assert "total_bytes" in data["drive"]
    assert "directories" in data
    assert len(data["directories"]) >= 4
    assert "safe_purge_mb" in data
    assert "posted_archive_potential" in data
    archive = data["posted_archive_potential"]
    assert "posted_clips_count" in archive
    assert "posted_angles_count" in archive
    assert "total_reclaimable_mb" in archive
    assert "items" in archive

    recommendation = data["archive_recommendation"]
    assert "ready_count" in recommendation
    assert "ready_mb" in recommendation
    assert "ready_items" in recommendation
    assert isinstance(recommendation["disk_alert"], bool)
    assert isinstance(recommendation["should_notify"], bool)


def test_inventory_health_endpoint():
    resp = client.get("/api/analytics/inventory")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    summary = data["summary"]
    assert "total_products" in summary
    assert "coverage_percentage" in summary
    assert "products" in data


def test_safe_purge_storage_cache_endpoint():
    resp = client.post("/api/analytics/storage/purge-safe-cache")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "purged_files" in data
    assert "purged_bytes" in data


def test_cutout_cache_endpoints():
    # Test GET
    get_resp = client.get("/api/analytics/storage/cutout-cache")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert "bytes" in get_data
    assert "mb" in get_data
    assert "count" in get_data

    # Test POST purge
    purge_resp = client.post("/api/analytics/storage/purge-cutout-cache")
    assert purge_resp.status_code == 200
    purge_data = purge_resp.json()
    assert purge_data["success"] is True
    assert "purged_files" in purge_data
    assert "purged_bytes" in purge_data



def test_production_analytics_exposes_snapshot_not_cohort_conversion(monkeypatch):
    products = [{
        "id": "product-1",
        "created_at": "2026-09-01T00:00:00",
        "angles": [
            {
                "angle_id": "angle-posted",
                "status": "posted",
                "created_at": "2026-09-01T00:00:00",
                "posted_at": "2026-09-02T00:00:00",
            },
            {
                "angle_id": "angle-scripted",
                "status": "scripted",
                "created_at": "2026-09-03T00:00:00",
            },
        ],
    }]
    monkeypatch.setattr(analytics.ProductStore, "get_all", classmethod(lambda cls: products))

    data = analytics.get_production_analytics()
    summary = data["summary"]

    assert summary["published_percentage"] == 50.0
    assert summary["current_state_percentages"]["posted"] == 50.0
    assert summary["lifecycle"]["cohort_conversion_available"] is False
    assert summary["lifecycle"]["created_to_posted_observations"] == 1
    assert summary["lifecycle"]["created_to_posted_observed_rate"] == 50.0


def test_storage_archive_candidates_are_unique_and_path_safe(tmp_path, monkeypatch):
    raw_dir = tmp_path / "01_Raw"
    assets_dir = tmp_path / "02_Assets"
    projects_dir = tmp_path / "03_Projects"
    exports_ready = tmp_path / "04_Exports" / "Ready_to_post"
    posted_dir = exports_ready.parent / "Posted"
    covers_dir = tmp_path / "05_Covers_Thumbnails"
    archive_dir = tmp_path / "06_Archive"
    capcut_dir = tmp_path / "CapCutDraft"
    project_dir = projects_dir / "shared-project"
    raw_product_dir = raw_dir / "P1-footage"
    unsafe_project_dir = tmp_path / "outside-project"

    for directory in (raw_dir, assets_dir, projects_dir, exports_ready, posted_dir, covers_dir, archive_dir, capcut_dir, project_dir, raw_product_dir, unsafe_project_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (project_dir / "draft.json").write_bytes(b"12345")
    (raw_product_dir / "clip.mp4").write_bytes(b"1234567")
    (unsafe_project_dir / "draft.json").write_bytes(b"outside")
    (posted_dir / "one.mp4").write_bytes(b"123")
    (posted_dir / "two.mp4").write_bytes(b"1234")

    products = [{
        "id": "product-1",
        "product_code": "P1",
        "angles": [
            {"angle_id": "a1", "status": "posted", "project_name": "shared-project", "posted_at": "2026-01-01T00:00:00"},
            {"angle_id": "a2", "status": "posted", "project_name": "shared-project", "posted_at": "2026-01-02T00:00:00"},
            {"angle_id": "unsafe", "status": "posted", "project_name": "../outside-project", "posted_at": "2026-01-03T00:00:00"},
        ],
    }]

    monkeypatch.setattr(analytics, "BASE_DIR", tmp_path)
    monkeypatch.setattr(analytics, "RAW_DIR", raw_dir)
    monkeypatch.setattr(analytics, "ASSETS_DIR", assets_dir)
    monkeypatch.setattr(analytics, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(analytics, "EXPORTS_DIR", exports_ready)
    monkeypatch.setattr(analytics, "COVERS_DIR", covers_dir)
    monkeypatch.setattr(analytics, "ARCHIVE_DIR", archive_dir)
    monkeypatch.setattr(analytics, "CAPCUT_DRAFT_DIR", capcut_dir)
    monkeypatch.setattr(analytics.ProductStore, "get_all", classmethod(lambda cls: products))
    monkeypatch.setattr(analytics, "scan_safe_reclaimable_cache", lambda: {"total_bytes": 11, "items": []})
    usage_type = type(analytics.shutil.disk_usage(str(tmp_path)))
    monkeypatch.setattr(analytics.shutil, "disk_usage", lambda _: usage_type(total=1000, used=500, free=500))
    monkeypatch.setitem(analytics._STORAGE_CACHE, "data", None)
    monkeypatch.setitem(analytics._STORAGE_CACHE, "timestamp", 0.0)

    data = analytics.get_storage_analytics(force_scan=True)
    archive = data["posted_archive_potential"]

    assert archive["posted_angles_count"] == 3
    assert archive["posted_projects_count"] == 1
    assert archive["posted_projects_bytes"] == 5
    assert archive["completed_products_raw_count"] == 1
    assert archive["completed_products_raw_bytes"] == 7
    assert archive["posted_exports_bytes"] == 7
    assert archive["archive_candidate_bytes"] == 19
    assert archive["total_reclaimable_bytes"] == 11
    assert archive["reclaim_estimate_is_safe_delete"] is True
    assert data["safe_purge_bytes"] == 11
    assert all(item["name"] != "outside-project" for item in archive["items"])
    assert sum(item["size_bytes"] for item in archive["items"]) == 19
