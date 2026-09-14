"""Regression coverage for product-level reference images and source metadata.

All storage is redirected into pytest's temporary directory.  The PATCH
contract must accept both legacy scraped URL strings and newer upload records,
and changing images must not discard the rest of the product source material.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_store as ps
from scripts.api_products import _merge_product_source_images, _with_product_source_fallback
from scripts.product_scraper import (
    _extract_html_product_text,
    _looks_like_browser_challenge,
    _normalise_rendered_text,
    _normalise_image_metadata,
    _source_text_without_duplicate,
    ProductScraper,
)
from scripts.api_server import app


def test_patch_product_images_preserves_all_source_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)

    product = ps.ProductStore.add(
        name="Logitech Wave Keys",
        url="https://example.test/wave-keys",
        platform="general",
        category="IT / Gadget",
        specs=[{"การเชื่อมต่อ": "Bluetooth"}],
        pain_points=["เสียงดัง"],
        selling_points=["พิมพ์เงียบ"],
        price_note="ราคาพิเศษ",
        target_buyer="คนทำงานหน้าคอม",
        description="คีย์บอร์ด ergonomic",
        raw_text="ข้อมูลจากหน้าสินค้าและสเปกเต็ม",
        images=["https://cdn.example.test/og-image.jpg"],
    )
    client = TestClient(app)
    uploaded = {
        "path": "00_Inbox/wave-spec.png",
        "rel_path": "00_Inbox/wave-spec.png",
        "name": "wave-spec.png",
        "source": "user_upload",
    }

    response = client.patch(
        f"/api/products/{product['id']}",
        json={"images": ["https://cdn.example.test/og-image.jpg", uploaded]},
    )

    assert response.status_code == 200
    saved = response.json()["product"]
    assert saved["images"] == ["https://cdn.example.test/og-image.jpg", uploaded]
    assert saved["description"] == "คีย์บอร์ด ergonomic"
    assert saved["raw_text"] == "ข้อมูลจากหน้าสินค้าและสเปกเต็ม"
    assert saved["specs"] == [{"การเชื่อมต่อ": "Bluetooth"}]
    assert ps.ProductStore.get(product["id"])["images"] == saved["images"]


def test_patch_product_images_can_clear_only_the_reference_list(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    product = ps.ProductStore.add(
        name="Reference product",
        description="ต้องไม่หาย",
        images=[{"rel_path": "00_Inbox/reference.png", "name": "reference.png"}],
    )

    response = TestClient(app).patch(
        f"/api/products/{product['id']}",
        json={"images": []},
    )

    assert response.status_code == 200
    saved = response.json()["product"]
    assert saved["images"] == []
    assert saved["description"] == "ต้องไม่หาย"


def test_legacy_product_source_fallback_is_derived_from_existing_angles():
    legacy = {
        "name": "Logitech Wave Keys",
        "description": "",
        "raw_text": "",
        "selling_points": [],
        "pain_points": [],
        "angles": [
            {
                "key_features": "ดีไซน์โค้งรับสรีระ, เบาะรองข้อมือ Memory Foam",
                "pain_point": "พิมพ์งานนานแล้วปวดข้อมือ",
            },
            {
                "key_features": "เชื่อมต่อ Bluetooth และ Logi Bolt",
                "pain_point": "พิมพ์งานนานแล้วปวดข้อมือ",
            },
        ],
    }

    enriched = _with_product_source_fallback(legacy)

    assert enriched["metadata_source"] == "derived_from_angles"
    assert enriched["description"] == "ดีไซน์โค้งรับสรีระ, เบาะรองข้อมือ Memory Foam · เชื่อมต่อ Bluetooth และ Logi Bolt"
    assert enriched["selling_points"] == [
        "ดีไซน์โค้งรับสรีระ, เบาะรองข้อมือ Memory Foam",
        "เชื่อมต่อ Bluetooth และ Logi Bolt",
    ]
    assert enriched["pain_points"] == ["พิมพ์งานนานแล้วปวดข้อมือ"]
    assert "พิมพ์งานนานแล้วปวดข้อมือ" in enriched["raw_text"]
    assert legacy["description"] == ""


def test_product_list_exposes_legacy_fallback_to_metadata_inspector(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    product = ps.ProductStore.add(name="Legacy keyboard")
    ps.ProductStore.update(product["id"], angles=[{
        "angle_id": "pain_point",
        "key_features": "ที่พักข้อมือ Memory Foam",
        "pain_point": "พิมพ์นานแล้วเมื่อย",
    }])

    listed = TestClient(app).get("/api/products")

    assert listed.status_code == 200
    visible = next(item for item in listed.json()["products"] if item["id"] == product["id"])
    assert visible["metadata_source"] == "derived_from_angles"
    assert visible["description"] == "ที่พักข้อมือ Memory Foam"
    assert visible["selling_points"] == ["ที่พักข้อมือ Memory Foam"]
    assert visible["pain_points"] == ["พิมพ์นานแล้วเมื่อย"]


def test_legacy_fallback_ignores_angles_from_another_product():
    legacy = {
        "name": "Logitech Wave Keys",
        "angles": [
            {"product_name": "Logitech Wave Keys", "key_features": "ดีไซน์โค้งรับสรีระ"},
            {"product_name": "GoChek GC-ULTRA S24", "key_features": "ตัดเสียงรบกวน"},
        ],
    }

    enriched = _with_product_source_fallback(legacy)

    assert enriched["description"] == "ดีไซน์โค้งรับสรีระ"
    assert "ตัดเสียงรบกวน" not in enriched["description"]


def test_rendered_source_text_is_compacted_and_challenge_is_rejected():
    text = _normalise_rendered_text("  ชื่อสินค้า  \n\n  ชื่อสินค้า  \n  ระบบตัดเสียงรบกวน  ")

    assert text == "ชื่อสินค้า\nระบบตัดเสียงรบกวน"
    assert _looks_like_browser_challenge("Verify to continue")
    assert not _looks_like_browser_challenge("ชื่อสินค้า\nระบบตัดเสียงรบกวน")


def test_html_product_description_is_preferred_over_navigation_and_reviews():
    html = """
    <html><body>
      <nav>Shop Log in Customer support</nav>
      <div>Displaying reviews</div>
      <section>About this product</section>
      <h2>Product description</h2>
      <div>รับประกัน 12 เดือน</div>
      <div>·</div><div>มีหัวต่อ Type-C และ Lightning</div>
      <div>·</div><div>Smart CSC 2.0 ลดเสียงรบกวนได้ถึง 90%</div>
      <div>ข้อมูลทางเทคนิค</div>
      <div>·</div><div>ความถี่: 50Hz - 18 KHz</div>
      <div>ข้อควรระวัง</div><div>View more</div><div>Video</div>
    </body></html>
    """

    result = _extract_html_product_text(html)

    assert result.startswith("รับประกัน 12 เดือน")
    assert "Smart CSC 2.0" in result
    assert "View more" not in result
    assert "Shop Log in" not in result


def test_refresh_source_persists_rendered_metadata_without_replacing_existing_assets(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    product = ps.ProductStore.add(
        name="GoChek GC-ULTRA S24",
        url="https://shop.tiktok.com/th/pdp/1731628390379587684",
        images=[{"rel_path": "00_Inbox/user-reference.png", "name": "user-reference.png"}],
        angles=[{"angle_id": "pain_point", "hook_title": "เดิม"}],
    )
    monkeypatch.setattr(
        ProductScraper,
        "scrape_url",
        lambda url: {
            "title": "GoChek GC-ULTRA S24",
            "url": url,
            "platform": "tiktok",
            "price_note": "ราคาพิเศษ",
            "description": "ระบบ Smart CSC 2.0 ลดเสียงรบกวน",
            "raw_text": "คำอธิบายสินค้า\nระบบ Smart CSC 2.0 ลดเสียงรบกวน\nแบตเตอรี่ 35 ชั่วโมง",
            "images": ["https://cdn.example.test/gochek-detail.jpg"],
            "specs": ["ความถี่: 50Hz - 18 KHz"],
            "selling_points": ["Smart CSC 2.0 ลดเสียงรบกวนได้ถึง 90%"],
            "metadata_source": "browser_dom",
        },
    )

    response = TestClient(app).post(f"/api/products/{product['id']}/refresh-source")

    assert response.status_code == 200
    saved = response.json()["product"]
    assert saved["metadata_source"] == "browser_dom"
    assert saved["description"] == "ระบบ Smart CSC 2.0 ลดเสียงรบกวน"
    assert "แบตเตอรี่ 35 ชั่วโมง" in saved["raw_text"]
    assert saved["specs"] == ["ความถี่: 50Hz - 18 KHz"]
    assert saved["selling_points"] == ["Smart CSC 2.0 ลดเสียงรบกวนได้ถึง 90%"]
    assert len(saved["images"]) == 2
    assert saved["angles"] == [{"angle_id": "pain_point", "hook_title": "เดิม"}]


def test_scraper_uses_rendered_source_when_shallow_html_has_no_description(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def geturl(self):
            return "https://shop.tiktok.com/th/pdp/1731628390379587684"

        def read(self, *_):
            return b"<html><head><title>GoChek</title></head><body></body></html>"

    class FakeOpener:
        def open(self, *_args, **_kwargs):
            return FakeResponse()

    import scripts.product_scraper as scraper_module
    monkeypatch.setattr(scraper_module, "_validate_scrape_url", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scraper_module, "_build_safe_opener", lambda *_args: FakeOpener())
    monkeypatch.setattr(
        scraper_module,
        "_scrape_rendered_page",
        lambda _url: {
            "title": "GoChek GC-ULTRA S24",
            "raw_text": "คำอธิบายสินค้า\nระบบ Smart CSC 2.0 ลดเสียงรบกวน\nแบตเตอรี่ 35 ชั่วโมง",
            "images": ["https://cdn.example.test/detail.jpg"],
        },
    )

    result = ProductScraper.scrape_url("https://shop.tiktok.com/th/pdp/1731628390379587684")

    assert result["metadata_source"] == "browser_dom"
    assert "Smart CSC 2.0" in result["description"]
    assert "แบตเตอรี่ 35 ชั่วโมง" in result["raw_text"]
    assert result["images"] == ["https://cdn.example.test/detail.jpg"]


def test_scraper_extracts_html_body_specs_before_browser_fallback(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def geturl(self):
            return "https://shop.tiktok.com/th/pdp/1731628390379587684"

        def read(self, *_):
            return """
            <html><head><title>GoChek</title></head><body>
              <div>About this product</div><div>Product description</div>
              <div>คุณสมบัติเด่นของ GoChek</div>
              <div>·</div><div>Smart CSC 2.0 ลดเสียงรบกวนได้ถึง 90%</div>
              <div>ตัวเลือกสินค้า</div><div>ข้อมูลทางเทคนิค</div>
              <div>·</div><div>ความถี่: 50Hz - 18 KHz</div>
              <div>ข้อควรระวัง</div><div>View more</div>
            </body></html>
            """.encode("utf-8")

    class FakeOpener:
        def open(self, *_args, **_kwargs):
            return FakeResponse()

    import scripts.product_scraper as scraper_module
    monkeypatch.setattr(scraper_module, "_validate_scrape_url", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scraper_module, "_build_safe_opener", lambda *_args: FakeOpener())
    monkeypatch.setattr(
        scraper_module,
        "_scrape_rendered_page",
        lambda _url: (_ for _ in ()).throw(AssertionError("HTML body should avoid browser fallback")),
    )

    result = ProductScraper.scrape_url("https://shop.tiktok.com/th/pdp/1731628390379587684")

    assert result["metadata_source"] == "html_body"
    assert result["selling_points"] == [
        "GoChek",
        "Smart CSC 2.0 ลดเสียงรบกวนได้ถึง 90%",
    ]
    assert result["specs"] == ["ความถี่: 50Hz - 18 KHz"]


def test_source_preview_is_read_only_and_reports_diffs(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    product = ps.ProductStore.add(
        name="ชื่อเดิม",
        url="https://shop.tiktok.com/th/pdp/1111111111111111111",
        description="คำอธิบายเดิม",
        images=["https://cdn.example.test/old.jpg"],
    )
    monkeypatch.setattr(
        ProductScraper,
        "scrape_url",
        lambda url: {
            "title": "ชื่อใหม่",
            "url": url,
            "platform": "tiktok",
            "description": "คำอธิบายใหม่",
            "raw_text": "รายละเอียดใหม่",
            "specs": ["50Hz"],
            "selling_points": ["ลดเสียงรบกวน"],
            "images": ["https://cdn.example.test/new.jpg"],
            "metadata_source": "html_body",
        },
    )

    response = TestClient(app).post(
        f"/api/products/{product['id']}/preview-source",
        json={"url": "https://shop.tiktok.com/th/pdp/2222222222222222222"},
    )

    assert response.status_code == 200
    preview = response.json()
    assert preview["incoming"]["name"] == "ชื่อใหม่"
    assert "description" in preview["changed_fields"]
    assert ps.ProductStore.get(product["id"])["name"] == "ชื่อเดิม"
    assert ps.ProductStore.get(product["id"])["url"] == "https://shop.tiktok.com/th/pdp/1111111111111111111"


def test_refresh_source_applies_only_selected_fields_and_dedupes_images(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    product = ps.ProductStore.add(
        name="ชื่อเดิม",
        url="https://shop.tiktok.com/th/pdp/1111111111111111111",
        description="คำอธิบายเดิม",
        images=["https://cdn.example.test/photo.jpg?width=720"],
    )
    monkeypatch.setattr(
        ProductScraper,
        "scrape_url",
        lambda url: {
            "title": "ชื่อใหม่",
            "url": url,
            "platform": "tiktok",
            "description": "คำอธิบายใหม่",
            "raw_text": "รายละเอียดใหม่",
            "specs": ["50Hz"],
            "selling_points": ["ลดเสียงรบกวน"],
            "images": [
                "https://cdn.example.test/photo.jpg?width=1080",
                "https://cdn.example.test/second.jpg",
            ],
            "metadata_source": "html_body",
        },
    )

    response = TestClient(app).post(
        f"/api/products/{product['id']}/refresh-source",
        json={
            "url": "https://shop.tiktok.com/th/pdp/2222222222222222222",
            "fields": ["url", "name", "specs", "selling_points", "images"],
        },
    )

    assert response.status_code == 200
    saved = response.json()["product"]
    assert saved["name"] == "ชื่อใหม่"
    assert saved["url"].endswith("2222222222222222222")
    assert saved["description"] == "คำอธิบายเดิม"
    assert saved["specs"] == ["50Hz"]
    assert saved["selling_points"] == ["ลดเสียงรบกวน"]
    assert len(saved["images"]) == 2


def test_product_metadata_patch_accepts_editable_source_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    product = ps.ProductStore.add(name="ชื่อยาวมาก", url="https://shop.tiktok.com/th/pdp/1111111111111111111")

    response = TestClient(app).patch(
        f"/api/products/{product['id']}",
        json={
            "name": "ชื่อสั้น",
            "url": "https://shop.tiktok.com/th/pdp/3333333333333333333",
            "description": "คำอธิบายที่แก้เอง",
            "raw_text": "ต้นฉบับที่แก้เอง",
            "specs": ["50Hz"],
            "selling_points": ["จุดขายที่แก้เอง"],
        },
    )

    assert response.status_code == 200
    saved = response.json()["product"]
    assert saved["name"] == "ชื่อสั้น"
    assert saved["url"].endswith("3333333333333333333")
    assert saved["description"] == "คำอธิบายที่แก้เอง"
    assert saved["raw_text"] == "ต้นฉบับที่แก้เอง"
    assert saved["specs"] == ["50Hz"]


def test_image_merge_dedupes_query_variants_without_dropping_local_assets():
    merged = _merge_product_source_images(
        [
            {"rel_path": "02_Assets/user.png", "name": "user.png"},
            "https://cdn.example.test/photo.jpg?width=720",
        ],
        [
            "https://cdn.example.test/photo.jpg?width=1080",
            "https://cdn.example.test/second.jpg",
        ],
    )

    assert len(merged) == 3
    assert merged[0]["rel_path"] == "02_Assets/user.png"


def test_product_metadata_patch_rejects_non_marketplace_url(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    product = ps.ProductStore.add(name="สินค้า", url="https://shop.tiktok.com/th/pdp/1111111111111111111")

    response = TestClient(app).patch(
        f"/api/products/{product['id']}",
        json={"url": "https://example.com/not-a-product"},
    )

    assert response.status_code == 400


def test_normalise_image_metadata_rejects_unstructured_or_keeps_visible_facts():
    assert _normalise_image_metadata({
        "name": "BlueWow X300 Pro Max",
        "description": "พัดลมระบายความร้อน",
        "raw_text": "27W",
        "specs": ["27W", {"label": "รุ่น", "value": "X300"}],
        "selling_points": ["Suction cooling"],
        "pain_points": [],
        "source_warning": "ตัวเลขบางจุดเล็ก",
    })["metadata_source"] == "vision_image"

    with pytest.raises(ValueError):
        _normalise_image_metadata(["not", "an", "object"])


def test_preview_image_metadata_is_read_only_and_returns_source_diff(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    image_path = tmp_path / "reference.png"
    image_path.write_bytes(b"fake-image")
    product = ps.ProductStore.add(
        name="BlueWow",
        images=[{"rel_path": "reference.png", "name": "reference.png"}],
        description="เดิม",
    )
    monkeypatch.setattr(
        ProductScraper,
        "extract_metadata_from_images",
        classmethod(lambda cls, image_paths, product_name: {
            "name": "BlueWow X300 Pro Max",
            "description": "พัดลมระบายความร้อน 27W",
            "raw_text": "AI GAMING COOLING SERIES",
            "specs": ["27W"],
            "selling_points": ["Suction cooling"],
            "pain_points": [],
            "source_warning": "ตัวเลขบางจุดเล็ก",
            "metadata_source": "vision_image",
        }),
    )

    response = TestClient(app).post(f"/api/products/{product['id']}/preview-image-metadata")

    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "vision_image"
    assert "description" in body["changed_fields"]
    assert ps.ProductStore.get(product["id"])["description"] == "เดิม"


def test_async_preview_image_metadata_returns_persistent_task_with_preview_result(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    product = ps.ProductStore.add(
        name="BlueWow",
        images=[{"rel_path": "reference.png", "name": "reference.png"}],
        description="เดิม",
    )
    monkeypatch.setattr(
        ProductScraper,
        "extract_metadata_from_images",
        classmethod(lambda cls, image_paths, product_name: {
            "name": "BlueWow X300 Pro Max",
            "description": "พัดลมระบายความร้อน 27W",
            "raw_text": "AI GAMING COOLING SERIES",
            "specs": ["27W"],
            "selling_points": ["Suction cooling"],
            "pain_points": [],
            "source_warning": "",
            "metadata_source": "vision_image",
        }),
    )

    client = TestClient(app)
    response = client.post(f"/api/products/{product['id']}/preview-image-metadata-async")

    assert response.status_code == 200, response.text
    task_id = response.json()["task_id"]
    task = client.get(f"/api/tasks/{task_id}").json()
    assert task["type"] == "image_metadata"
    assert task["status"] == "completed", task.get("error")
    assert task["target_id"] == product["id"]
    assert task["result"]["product_id"] == product["id"]
    assert task["result"]["preview"]["source_type"] == "vision_image"
    assert ps.ProductStore.get(product["id"])["description"] == "เดิม"


def test_source_text_without_duplicate_keeps_only_raw_lines_not_already_in_description():
    assert _source_text_without_duplicate(
        "รับประกัน 12 เดือน\nมีหัวต่อ Type-C และ Lightning",
        "GoChek GC-ULTRA S24\nรับประกัน 12 เดือน\nมีหัวต่อ Type-C และ Lightning\nข้อมูลจากร้าน",
    ) == "GoChek GC-ULTRA S24\nข้อมูลจากร้าน"


def test_refresh_source_applies_edited_preview_values_and_respects_selected_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    product = ps.ProductStore.add(
        name="ชื่อเดิม",
        url="https://shop.tiktok.com/th/pdp/1111111111111111111",
        description="คำอธิบายเดิม",
        specs=["สเปกเดิม"],
    )
    monkeypatch.setattr(
        ProductScraper,
        "scrape_url",
        lambda url: {
            "title": "ชื่อใหม่",
            "url": url,
            "platform": "tiktok",
            "description": "คำอธิบายจากเว็บ",
            "raw_text": "ข้อความจากเว็บ",
            "specs": ["สเปกใหม่"],
            "selling_points": ["จุดขายใหม่"],
            "images": [],
            "metadata_source": "html_body",
        },
    )

    response = TestClient(app).post(
        f"/api/products/{product['id']}/refresh-source",
        json={
            "url": "https://shop.tiktok.com/th/pdp/2222222222222222222",
            "fields": ["description", "raw_text"],
            "overrides": {
                "description": "คำอธิบายสรรพคุณที่แก้แล้ว",
                "raw_text": "ข้อความต้นฉบับที่แก้แล้ว",
            },
        },
    )

    assert response.status_code == 200
    saved = response.json()["product"]
    assert saved["description"] == "คำอธิบายสรรพคุณที่แก้แล้ว"
    assert saved["raw_text"] == "ข้อความต้นฉบับที่แก้แล้ว"
    assert saved["specs"] == ["สเปกเดิม"]
    assert saved["selling_points"] == []
    assert ps.ProductStore.get(product["id"])["url"].endswith("1111111111111111111")


def test_product_hook_header_sync_to_angles(tmp_path, monkeypatch):
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    product = ps.ProductStore.add(
        name="BCD LOOP Smartband",
        angles=[
            {"angle_id": "ang_1", "angle_name": "มุมที่ 1", "hook_brand": "Old", "hook_model": "OldM"},
            {"angle_id": "ang_2", "angle_name": "มุมที่ 2"},
        ],
    )

    # Patch product with hook header and apply_to_angles = True
    response = TestClient(app).patch(
        f"/api/products/{product['id']}",
        json={
            "hook_brand": "BCD",
            "hook_model": "LOOP Smartband",
            "hook_label": "สายรัดข้อมือ",
            "apply_to_angles": True,
        },
    )

    assert response.status_code == 200
    saved = response.json()["product"]
    assert saved["hook_brand"] == "BCD"
    assert saved["hook_model"] == "LOOP Smartband"
    assert saved["hook_label"] == "สายรัดข้อมือ"
    assert len(saved["angles"]) == 2
    assert saved["angles"][0]["hook_brand"] == "BCD"
    assert saved["angles"][0]["hook_model"] == "LOOP Smartband"
    assert saved["angles"][0]["hook_label"] == "สายรัดข้อมือ"
    assert saved["angles"][1]["hook_brand"] == "BCD"
    assert saved["angles"][1]["hook_model"] == "LOOP Smartband"
    assert saved["angles"][1]["hook_label"] == "สายรัดข้อมือ"

