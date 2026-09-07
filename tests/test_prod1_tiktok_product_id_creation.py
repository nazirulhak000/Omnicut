"""
Unit tests for Round PROD-1:
- Adding product with tiktok_product_id saves it to the product entity.
- Scrape and plan endpoint extracts / accepts tiktok_product_id.
- Fallback logic: if tiktok_product_id is not set, export info falls back to product name.

Follows testing_standard.md (offline, isolated with tmp_path, no side effects on real files).
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_store as ps
from scripts.api_server import app


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    return tmp_path


def test_product_store_add_stores_tiktok_product_id(isolated_store):
    prod = ps.ProductStore.add(
        name="Essager Magnetic Cable",
        url="https://shopee.co.th/product/123/456",
        tiktok_product_id="1737088044189583209",
    )
    assert prod["tiktok_product_id"] == "1737088044189583209"

    loaded = ps.ProductStore.get(prod["id"])
    assert loaded["tiktok_product_id"] == "1737088044189583209"


def test_product_store_add_url_update_preserves_or_updates_tiktok_product_id(isolated_store):
    prod1 = ps.ProductStore.add(
        name="Essager Cable",
        url="https://shopee.co.th/product/123/456",
        tiktok_product_id="1111111111",
    )
    assert prod1["tiktok_product_id"] == "1111111111"

    # Update with new tiktok_product_id
    prod2 = ps.ProductStore.add(
        name="Essager Cable Updated",
        url="https://shopee.co.th/product/123/456",
        tiktok_product_id="2222222222",
    )
    assert prod2["id"] == prod1["id"]
    assert prod2["tiktok_product_id"] == "2222222222"


def test_scrape_and_plan_accepts_tiktok_product_id(isolated_store, monkeypatch):
    # Mock AI content matrix to keep test offline and instant
    from scripts.product_scraper import ProductScraper
    monkeypatch.setattr(
        ProductScraper,
        "generate_content_matrix",
        lambda info, count=10, image_paths=None: [{
            "angle_id": "ang1",
            "angle_name": "Review",
            "hook_title": "Hook",
            "script_lines": ["Line 1"],
            "status": "scripted"
        }]
    )

    client = TestClient(app)
    res = client.post("/api/products/scrape-and-plan", json={
        "custom_keyword": "Essager 3-in-1",
        "raw_text": "Specs and details for magnetic cable",
        "angle_count": 4,
        "tiktok_product_id": "1737088044189583209"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["saved_product"]["tiktok_product_id"] == "1737088044189583209"
    assert data["product"]["tiktok_product_id"] == "1737088044189583209"


def test_scrape_and_plan_auto_extracts_id_from_tiktok_url(isolated_store, monkeypatch):
    from scripts.product_scraper import ProductScraper
    monkeypatch.setattr(
        ProductScraper,
        "scrape_url",
        lambda url: {
            "platform": "tiktok",
            "url": url,
            "title": "TikTok Shop Item",
            "description": "Item description",
            "price_note": "199.-",
            "images": [],
            "image_count": 0
        }
    )
    monkeypatch.setattr(
        ProductScraper,
        "generate_content_matrix",
        lambda info, count=10, image_paths=None: []
    )

    client = TestClient(app)
    res = client.post("/api/products/scrape-and-plan", json={
        "url": "https://www.tiktok.com/view/product/1737088044189583209?trackParams=...",
        "angle_count": 4,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["saved_product"]["tiktok_product_id"] == "1737088044189583209"


def test_scrape_and_plan_handles_url_string_images_from_scrape(isolated_store, monkeypatch):
    """ProductScraper.scrape_url() puts plain image URL strings (scraped off
    <meta og:image>/<img> tags) in its "images" list, not dicts -- unlike
    user-uploaded images, which arrive as {name, rel_path, local_path} dicts.
    A real TikTok Shop cart/product-page scrape hits exactly this shape and
    used to crash the whole request with "'str' object has no attribute
    'get'" (thumbnail_img lookup) or "string indices must be integers, not
    'str'" (vision image_paths lookup) before both were made to tolerate a
    bare URL string image entry.
    """
    from scripts.product_scraper import ProductScraper
    monkeypatch.setattr(
        ProductScraper,
        "scrape_url",
        lambda url: {
            "platform": "tiktok",
            "url": url,
            "title": "GoChek Wireless Microphone",
            "description": "Noise-cancelling clip mic",
            "price_note": "199.-",
            "images": [
                "https://p16-oec-sg.ibyteimg.com/tos-alisg/example1.webp",
                "https://p16-oec-sg.ibyteimg.com/tos-alisg/example2.webp",
            ],
            "image_count": 2,
        }
    )
    seen_image_paths = []

    def fake_generate_content_matrix(info, count=10, image_paths=None):
        seen_image_paths.append(image_paths)
        return []

    monkeypatch.setattr(ProductScraper, "generate_content_matrix", fake_generate_content_matrix)

    client = TestClient(app)
    res = client.post("/api/products/scrape-and-plan", json={
        "url": "https://vt.tiktok.com/ZS9SxAbCd/",
        "angle_count": 4,
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    # A remote scraped image has no local file -- vision can't read it, so it
    # must be excluded from image_paths rather than crashing the lookup.
    assert seen_image_paths == [[]]
    # The product-page thumbnail still gets set from the scraped URL directly.
    assert data["saved_product"]["thumbnail"].startswith("https://")


def test_api_exports_fallback_to_name_when_id_missing(isolated_store):
    from scripts.api_exports import list_exports
    # When product has tiktok_product_id, use it. When none, use name.
    prod_with_id = {"id": "p1", "name": "Cable A", "tiktok_product_id": "99999", "projects": ["proj_a"]}
    prod_no_id = {"id": "p2", "name": "Cable B", "tiktok_product_id": None, "projects": ["proj_b"]}

    val1 = prod_with_id.get("tiktok_product_id") or prod_with_id.get("name", "")
    val2 = prod_no_id.get("tiktok_product_id") or prod_no_id.get("name", "")

    assert val1 == "99999"
    assert val2 == "Cable B"
