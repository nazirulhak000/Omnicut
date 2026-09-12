import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from scripts import product_store as ps
from scripts.product_store import ProductStore
from scripts.product_scraper import ProductScraper
from scripts.api_server import app
from scripts.db import DocumentTable

client = TestClient(app)


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    store_json = tmp_path / "_Docs" / "products.json"
    store_db = tmp_path / "_Docs" / "store.db"
    store_json.parent.mkdir(parents=True, exist_ok=True)
    table = DocumentTable("products", lambda: store_db, lambda: store_json)
    monkeypatch.setattr(ps, "STORE_PATH", store_json)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    monkeypatch.setattr(ps, "_TABLE", table)
    return tmp_path


def test_append_angles_batches(isolated_store):
    # 1. Create a product with 3 angles (initial batch 1)
    prod = ProductStore.add(
        name="Test Gadget Batch 1",
        angles=[
            {"angle_id": "a1", "angle_name": "Angle 1", "status": "posted"},
            {"angle_id": "a2", "angle_name": "Angle 2", "status": "rendered"},
            {"angle_id": "a3", "angle_name": "Angle 3", "status": "scripted"},
        ]
    )
    assert len(prod["angles"]) == 3

    # 2. Append new batch
    new_batch_angles = [
        {"angle_name": "Angle 4 (Batch 2)", "hook_title": "Hook 4"},
        {"angle_name": "Angle 5 (Batch 2)", "hook_title": "Hook 5"},
    ]
    updated = ProductStore.append_angles(prod["id"], new_batch_angles)

    assert len(updated["angles"]) == 5
    # Verify existing angles retained their status
    assert updated["angles"][0]["status"] == "posted"
    assert updated["angles"][1]["status"] == "rendered"
    assert updated["angles"][2]["status"] == "scripted"
    assert updated["angles"][0].get("batch") == 1

    # Verify new angles got assigned batch 2 and status scripted
    assert updated["angles"][3]["batch"] == 2
    assert updated["angles"][3]["status"] == "scripted"
    assert updated["angles"][3].get("angle_id") is not None
    assert updated["angles"][4]["batch"] == 2


def test_add_single_angle(isolated_store):
    prod = ProductStore.add(
        name="Single Angle Test",
        angles=[{"angle_id": "a1", "angle_name": "Initial"}]
    )

    custom_angle = {
        "angle_name": "Custom User Angle",
        "hook_title": "Custom Hook",
        "script_lines": ["Line 1", "Line 2"],
    }
    updated = ProductStore.add_single_angle(prod["id"], custom_angle)

    assert len(updated["angles"]) == 2
    added = updated["angles"][1]
    assert added["angle_name"] == "Custom User Angle"
    assert added["status"] == "scripted"
    assert added["angle_id"].startswith("ang_")


def test_api_add_angle_and_generate_batch(isolated_store, monkeypatch):
    monkeypatch.setattr(
        ProductScraper,
        "generate_content_matrix",
        lambda info, count=10, **kwargs: [
            {
                "angle_name": f"Mock Angle {i}",
                "hook_title": f"Hook {i}",
                "script_lines": ["Line 1", "Line 2"],
                "tts_lines": ["Line 1", "Line 2"],
            }
            for i in range(count)
        ]
    )

    prod = ProductStore.add(
        name="API Angle Test",
        angles=[{"angle_id": "a1", "angle_name": "Initial", "batch": 1}]
    )

    # Test POST /api/products/{id}/angles
    res = client.post(f"/api/products/{prod['id']}/angles", json={
        "angle": {
            "angle_name": "API Cloned Angle",
            "hook_title": "Hook from clone",
        }
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["product"]["angles"]) == 2

    # Test POST /api/products/{id}/generate-batch
    res2 = client.post(f"/api/products/{prod['id']}/generate-batch", json={
        "angle_count": 10,
        "duration": "60s"
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["success"] is True
    assert "task_id" in data2
