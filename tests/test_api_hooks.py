import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from scripts.api_server import app

client = TestClient(app)


def test_get_hook_styles():
    resp = client.get("/api/hooks/styles")
    assert resp.status_code == 200
    data = resp.json()
    assert "styles" in data
    assert len(data["styles"]) == 5


def test_generate_hooks_endpoint():
    payload = {
        "product_name": "Logitech MX Master 3S",
        "brand": "Logitech",
        "model": "MX Master 3S",
        "description": "เมาส์ไร้สายเพื่อสุขภาพ",
        "pain_point": "คลิกเสียงดัง ปวดนิ้ว",
        "price_deal": "ลดเหลือ 3,190 บาท",
    }
    resp = client.post("/api/hooks/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_name"] == "Logitech MX Master 3S"
    assert len(data["variations"]) == 5
    for v in data["variations"]:
        assert "..." not in v["hook_title"]
        assert "…" not in v["hook_title"]


def test_generate_hooks_validation_error():
    resp = client.post("/api/hooks/generate", json={"product_name": ""})
    assert resp.status_code == 400


@patch("scripts.api_hooks.ProductStore")
def test_apply_angle_hook(mock_store):
    mock_store.get.return_value = {
        "id": "prod_1",
        "title": "Logitech MX",
        "angles": [
            {
                "angle_id": "ang_1",
                "angle_name": "รีวิวเน้นทำงาน",
                "hook_title": "เก่า",
                "script_lines": ["ประโยคแรกเดิม", "ประโยคสองเดิม"],
            }
        ],
    }
    mock_store.update.return_value = {"id": "prod_1"}

    payload = {
        "product_id": "prod_1",
        "angle_id": "ang_1",
        "hook_variant": {
            "style_id": "curiosity",
            "hook_title": "อย่าเพิ่งซื้อ Logitech MX",
            "hook_brand": "Logitech",
            "hook_model": "MX",
            "hook_label": "อย่าเพิ่งซื้อ",
            "opening_line": "ใครกำลังจะซื้อเมาส์ตัวนี้ ฟังทางนี้ครับ",
        },
        "update_script_first_line": True,
    }
    resp = client.post("/api/hooks/apply-angle", json=payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert res_data["angle"]["hook_title"] == "อย่าเพิ่งซื้อ Logitech MX"
    assert res_data["angle"]["script_lines"][0] == "ใครกำลังจะซื้อเมาส์ตัวนี้ ฟังทางนี้ครับ"


@patch("scripts.api_hooks.ProjectManifest")
def test_apply_project_hook(mock_manifest):
    mock_manifest.load.return_value = {
        "project_name": "test_proj",
        "hook_brand": "OldBrand",
        "hook_model": "OldModel",
        "hook_label": "OldLabel",
        "overlays": [{"kind": "hook", "brand": "OldBrand", "model": "OldModel", "label": "OldLabel"}],
    }

    payload = {
        "project_name": "test_proj",
        "hook_variant": {
            "hook_brand": "Logitech",
            "hook_model": "Wave Keys",
            "hook_label": "คีย์บอร์ดเพื่อสุขภาพ",
            "hook_title": "Logitech Wave Keys ดีจริงไหม",
        },
        "auto_reroll": False,
    }
    resp = client.post("/api/hooks/apply-project", json=payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert res_data["hook_brand"] == "Logitech"
    assert res_data["hook_model"] == "Wave Keys"
    assert res_data["hook_label"] == "คีย์บอร์ดเพื่อสุขภาพ"
    mock_manifest.save.assert_called_once()
