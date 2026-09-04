import pytest
from scripts.product_store import ProductStore

def test_reconcile_and_status():
    # Verify that reconcile does NOT arbitrarily hijack new scripts with old projects
    changed = ProductStore.reconcile_existing_projects()
    products = ProductStore._load()
    assert len(products) > 0
    target_product = products[0]
    angle = target_product["angles"][0]
    
    # Newly generated script must remain scripted unless explicitly rendered
    assert angle["status"] == "scripted"
    assert angle.get("project_name") is None
    assert angle.get("video_url") is None
