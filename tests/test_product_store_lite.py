import pytest
from fastapi.testclient import TestClient
from scripts.api_server import app
from scripts.product_store import ProductStore


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_product():
    angle = {
        "angle_id": "test_angle_1",
        "angle_name": "Test Angle",
        "badge": "Hot",
        "status": "draft",
        "hook_title": "Hook 1",
        "script_lines": [{"speaker": "A", "text": "Hello world"}],
        "tts_lines": [{"speaker": "A", "text": "Hello world audio"}],
        "script_text": "Hello world long text",
        "tiktok_caption": "Check this out",
        "tiktok_hashtags": "#gadget #test",
    }
    prod = ProductStore.add(
        name="Test Ultra Lite Powerbank",
        url="https://shop.tiktok.com/view/product/1729000000000000099",
        raw_text="Long description text that is heavy",
        angles=[angle],
        channel_id="main",
    )
    return prod


def test_product_store_lite_compact_strips_heavy_fields(sample_product):
    products = ProductStore.list(lite="compact", all_channels=True)
    assert len(products) > 0
    first = [p for p in products if p["id"] == sample_product["id"]][0]
    assert "id" in first
    assert "name" in first
    assert "angles_count" in first
    assert first["angles_count"] == 1
    assert "raw_text" not in first

    angles = first.get("angles", [])
    assert len(angles) == 1
    a0 = angles[0]
    assert a0["angle_id"] == "test_angle_1"
    assert a0["status"] == "draft"
    assert "script_lines" not in a0
    assert "tts_lines" not in a0
    assert "script_text" not in a0
    assert a0["tiktok_caption"] == "Check this out"


def test_product_store_lite_summary_returns_angles_count_only(sample_product):
    products = ProductStore.list(lite="summary", all_channels=True)
    assert len(products) > 0
    first = [p for p in products if p["id"] == sample_product["id"]][0]
    assert "id" in first
    assert "name" in first
    assert "angles_count" in first
    assert first["angles_count"] == 1
    assert "angles" not in first


def test_api_products_default_preserves_full_backward_compatibility(client, sample_product):
    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.json()
    assert "products" in data
    assert "summary" in data
    first = [p for p in data["products"] if p["id"] == sample_product["id"]][0]
    assert "angles" in first
    assert len(first["angles"]) == 1
    assert "script_lines" in first["angles"][0]


def test_api_products_lite_compact_query_param(client, sample_product):
    res = client.get("/api/products?lite=compact")
    assert res.status_code == 200
    data = res.json()
    first = [p for p in data["products"] if p["id"] == sample_product["id"]][0]
    assert "raw_text" not in first
    assert "angles" in first
    a0 = first["angles"][0]
    assert a0["angle_id"] == "test_angle_1"
    assert "script_lines" not in a0
    assert "tts_lines" not in a0


def test_api_products_lite_summary_query_param(client, sample_product):
    res = client.get("/api/products?lite=summary")
    assert res.status_code == 200
    data = res.json()
    first = [p for p in data["products"] if p["id"] == sample_product["id"]][0]
    assert "angles_count" in first
    assert "angles" not in first


def test_api_products_reconcile_flag(client, sample_product):
    res = client.get("/api/products?reconcile=0&lite=summary")
    assert res.status_code == 200
    data = res.json()
    assert "products" in data
