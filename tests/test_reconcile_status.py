import pytest
from scripts.product_store import ProductStore

def test_reconcile_and_status(monkeypatch, tmp_path):
    # Isolated test data to verify that reconcile does NOT arbitrarily hijack new scripts with old projects
    mock_products = [{
        "id": "test_isolated_prod_999",
        "name": "สินค้าทดสอบใหม่",
        "angles": [{
            "angle_id": "isolated_angle_1",
            "status": "scripted",
            "project_name": None,
            "video_url": None,
            "hook_title": "ฮุกทดสอบที่ไม่ตรงกับโปรเจกต์ใดๆ",
            "script_lines": ["ประโยค 1", "ประโยค 2"]
        }]
    }]

    monkeypatch.setattr(ProductStore, "_load", lambda: mock_products)
    saved_state = []
    monkeypatch.setattr(ProductStore, "_save", lambda prods: saved_state.append(prods))

    changed = ProductStore.reconcile_existing_projects()
    target_product = mock_products[0]
    angle = target_product["angles"][0]

    # Newly generated script must remain scripted unless explicitly matched
    assert angle["status"] == "scripted"
    assert angle.get("project_name") is None
    assert angle.get("video_url") is None

