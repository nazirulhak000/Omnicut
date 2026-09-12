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
