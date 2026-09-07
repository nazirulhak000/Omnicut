"""Regression coverage for cover ownership and refresh recovery."""

import pytest
from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts import api_phase1 as phase1
from scripts import product_store as ps


@pytest.fixture
def isolated_cover_store(tmp_path, monkeypatch):
    covers = tmp_path / "05_Covers_Thumbnails"
    covers.mkdir()
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    monkeypatch.setattr(ps, "COVERS_DIR", covers)
    monkeypatch.setattr(phase1, "BASE_DIR", tmp_path)
    monkeypatch.setattr(phase1, "COVERS_DIR", covers)
    return tmp_path, covers


def test_cover_endpoint_persists_variants_and_products_refresh_returns_urls(isolated_cover_store):
    tmp_path, covers = isolated_cover_store
    product = ps.ProductStore.add(
        name="Logitech Wave Keys",
        angles=[{"angle_id": "a1", "project_name": "wave_review", "status": "scripted"}],
    )
    primary = covers / "wave_review_cover.jpg"
    profile = covers / "wave_review_cover_3x4.jpg"
    primary.write_bytes(b"primary")
    profile.write_bytes(b"profile")

    client = TestClient(app)
    response = client.patch(
        f"/api/products/{product['id']}/angles/a1/cover",
        json={
            "cover_path": str(primary),
            "cover_3x4_path": str(profile),
        },
    )
    assert response.status_code == 200, response.text

    reloaded = client.get("/api/products")
    assert reloaded.status_code == 200, reloaded.text
    angle = reloaded.json()["products"][0]["angles"][0]
    assert angle["cover_path"] == "05_Covers_Thumbnails/wave_review_cover.jpg"
    assert angle["cover_9x16_path"] == "05_Covers_Thumbnails/wave_review_cover.jpg"
    assert angle["cover_3x4_path"] == "05_Covers_Thumbnails/wave_review_cover_3x4.jpg"
    assert angle["cover_url"].endswith("wave_review_cover.jpg")
    assert angle["cover_3x4_url"].endswith("wave_review_cover_3x4.jpg")


def test_products_refresh_recovers_legacy_cover_by_project_name(isolated_cover_store):
    _tmp_path, covers = isolated_cover_store
    product = ps.ProductStore.add(
        name="Legacy Product",
        angles=[{"angle_id": "a1", "project_name": "legacy_project", "status": "scripted"}],
    )
    (covers / "legacy_project_cover.jpg").write_bytes(b"primary")
    (covers / "legacy_project_cover_3x4.jpg").write_bytes(b"profile")

    response = TestClient(app).get("/api/products")
    assert response.status_code == 200, response.text
    angle = response.json()["products"][0]["angles"][0]
    assert angle["cover_path"] == "05_Covers_Thumbnails/legacy_project_cover.jpg"
    assert angle["cover_3x4_path"] == "05_Covers_Thumbnails/legacy_project_cover_3x4.jpg"
    assert angle["cover_3x4_url"].endswith("legacy_project_cover_3x4.jpg")


def test_cover_endpoint_rejects_files_outside_cover_directory(isolated_cover_store, tmp_path):
    product = ps.ProductStore.add(name="Safe Product", angles=[{"angle_id": "a1"}])
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"no")

    response = TestClient(app).patch(
        f"/api/products/{product['id']}/angles/a1/cover",
        json={"cover_path": str(outside)},
    )
    assert response.status_code == 400
