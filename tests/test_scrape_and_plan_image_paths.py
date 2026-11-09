"""Reference images and linked videos must stay inside the media folders
(audit S1-09 / S1-17). No network, no Gemini: generation is stubbed."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import scripts.api_products as api_products
from scripts.api_server import app
from scripts.product_scraper import ProductScraper, _safe_local_image_path
from scripts.product_store import ProductStore


def _stub_generation(monkeypatch, seen):
    def fake_matrix(product_info, count=10, image_paths=None, **_k):
        seen.append(list(image_paths or []))
        return []

    monkeypatch.setattr(ProductScraper, "generate_content_matrix", staticmethod(fake_matrix))


@pytest.mark.parametrize("bad", [".env", "../../.env", "scripts/config.py"])
def test_scrape_and_plan_rejects_paths_outside_upload_folders(monkeypatch, bad):
    seen = []
    _stub_generation(monkeypatch, seen)

    response = TestClient(app).post(
        "/api/products/scrape-and-plan",
        json={"custom_keyword": "หูฟัง", "image_paths": [bad]},
    )

    assert response.status_code == 400
    assert "00_Inbox" in response.json()["detail"]
    assert seen == []


def test_scrape_and_plan_rejects_absolute_image_outside_roots(monkeypatch, tmp_path):
    seen = []
    _stub_generation(monkeypatch, seen)
    outside = tmp_path / "secret.png"
    outside.write_bytes(b"x")

    response = TestClient(app).post(
        "/api/products/scrape-and-plan",
        json={"custom_keyword": "หูฟัง", "image_paths": [str(outside)]},
    )

    assert response.status_code == 400
    assert seen == []


def test_scrape_and_plan_accepts_inbox_image_and_stores_relative_path(monkeypatch):
    seen = []
    _stub_generation(monkeypatch, seen)
    inbox = Path(api_products.INBOX_DIR)
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "ref_photo.jpg").write_bytes(b"\xff\xd8\xff")

    response = TestClient(app).post(
        "/api/products/scrape-and-plan",
        json={"custom_keyword": "หูฟัง Sony WH-1000XM5", "image_paths": ["00_Inbox/ref_photo.jpg"]},
    )

    assert response.status_code == 200, response.text
    saved = ProductStore.get(response.json()["saved_product"]["id"])
    image = saved["images"][0]
    assert image["rel_path"] == "00_Inbox/ref_photo.jpg"
    assert image["local_path"] == "00_Inbox/ref_photo.jpg"
    assert not Path(image["local_path"]).is_absolute()
    assert seen == [["00_Inbox/ref_photo.jpg"]]


def test_scraper_never_reads_non_image_or_outside_files(tmp_path):
    with pytest.raises(ValueError):
        _safe_local_image_path(".env")
    outside = tmp_path / "x.png"
    outside.write_bytes(b"x")
    with pytest.raises(ValueError):
        _safe_local_image_path(str(outside))


def test_attach_video_refuses_path_outside_raw_roots(monkeypatch, tmp_path):
    product = ProductStore.add(name="Sony WH-1000XM5")
    outside = tmp_path / "elsewhere.mp4"
    outside.write_bytes(b"x")
    monkeypatch.setattr(api_products, "get_file_info", lambda p: {"name": Path(p).name, "path": str(p)})

    response = TestClient(app).post(
        f"/api/products/{product['id']}/videos",
        json={"video_path": str(outside)},
    )

    assert response.status_code == 403
    assert ProductStore.get(product["id"])["videos"] == []


def test_attach_video_accepts_raw_footage(monkeypatch):
    product = ProductStore.add(name="Sony WH-1000XM5")
    raw_dir = Path(api_products.RAW_DIR) / product["id"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "take.mp4").write_bytes(b"x")
    monkeypatch.setattr(
        api_products,
        "get_file_info",
        lambda p: {"name": Path(p).name, "path": f"01_Raw/{product['id']}/take.mp4", "type": "video"},
    )

    response = TestClient(app).post(
        f"/api/products/{product['id']}/videos",
        json={"video_path": f"01_Raw/{product['id']}/take.mp4"},
    )

    assert response.status_code == 200, response.text
