"""
Regression tests for Round BUG-3.3 (tiktok_product_id can now be set via
API, not just by hand-editing products.json) and the clear_conflict_note
path added alongside the BUG-3.1 collision fix.

Uses tmp_path + monkeypatch throughout, per .agents/rules/testing_standard.md
rule 3 -- never touches the real _Docs/products.json.
"""
import json
import sys
from pathlib import Path

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


def _seed_one_angle(tmp_path, *, with_conflict_note):
    products = [{
        "id": "demo_product",
        "name": "Demo Product",
        "tiktok_product_id": None,
        "angles": [{
            "angle_id": "angle1",
            "id": "angle1",
            "status": "scripted",
            "video_url": None,
            "project_name": None,
            **({"data_conflict_note": "ปลดออกจาก 'x' อัตโนมัติ — ชนกับ angle อื่น (2026-01-01)"} if with_conflict_note else {}),
        }],
    }]
    (tmp_path / "_Docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_Docs" / "products.json").write_text(
        json.dumps(products, ensure_ascii=False), encoding="utf-8",
    )


def test_patch_product_sets_tiktok_product_id(isolated_store):
    tmp_path = isolated_store
    _seed_one_angle(tmp_path, with_conflict_note=False)
    client = TestClient(app)

    r = client.patch("/api/products/demo_product", json={"tiktok_product_id": "1737088044189583209"})
    assert r.status_code == 200
    assert r.json()["product"]["tiktok_product_id"] == "1737088044189583209"

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    assert products[0]["tiktok_product_id"] == "1737088044189583209"


def test_clear_conflict_note_via_angle_patch(isolated_store):
    tmp_path = isolated_store
    _seed_one_angle(tmp_path, with_conflict_note=True)
    client = TestClient(app)

    r = client.patch(
        "/api/products/demo_product/angles/angle1",
        json={"status": "scripted", "clear_conflict_note": True},
    )
    assert r.status_code == 200
    angle = r.json()["product"]["angles"][0]
    assert angle.get("data_conflict_note") is None

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    assert products[0]["angles"][0].get("data_conflict_note") is None
