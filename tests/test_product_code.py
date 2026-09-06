"""
Regression tests for product_code: a short scannable per-product code (e.g.
"ESS01") auto-generated so many concurrently-edited CapCut projects can be
told apart at a glance, without reading the full Thai product name.

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


def test_generate_product_code_fresh_prefix():
    code = ps.ProductStore._generate_product_code("ESSAGER สายชาร์จแม่เหล็ก", products=[])
    assert code == "ESS01"


def test_generate_product_code_increments_within_same_prefix():
    existing = [{"product_code": "ESS01"}]
    code = ps.ProductStore._generate_product_code("ESSAGER Cable v2", products=existing)
    assert code == "ESS02"


def test_generate_product_code_different_brands_do_not_collide():
    existing = [{"product_code": "ESS01"}]
    code = ps.ProductStore._generate_product_code("Logitech Wave Keys", products=existing)
    assert code == "LOG01"


def test_generate_product_code_pure_thai_name_falls_back_to_gen():
    code = ps.ProductStore._generate_product_code("สายชาร์จแม่เหล็ก", products=[])
    assert code == "GEN01"


def test_add_auto_assigns_code_when_none_passed(isolated_store):
    product = ps.ProductStore.add(name="ESSAGER สายชาร์จแม่เหล็ก")
    assert product["product_code"] == "ESS01"


def test_add_respects_explicitly_passed_code(isolated_store):
    product = ps.ProductStore.add(name="ESSAGER สายชาร์จแม่เหล็ก", product_code="ESG01")
    assert product["product_code"] == "ESG01"


def test_update_persists_manually_edited_product_code(isolated_store):
    product = ps.ProductStore.add(name="ESSAGER สายชาร์จแม่เหล็ก")
    updated = ps.ProductStore.update(product["id"], product_code="ESG01")
    assert updated["product_code"] == "ESG01"


def test_patch_product_code_round_trips_via_api(isolated_store):
    """update() (used by PATCH) must uppercase product_code the same way
    add() does -- a code's casing should not depend on whether it was set
    at creation or edited later via the API."""
    tmp_path = isolated_store
    (tmp_path / "_Docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_Docs" / "products.json").write_text(
        json.dumps([{"id": "demo_product", "name": "Demo Product", "product_code": "ESS01"}], ensure_ascii=False),
        encoding="utf-8",
    )
    client = TestClient(app)

    r = client.patch("/api/products/demo_product", json={"product_code": "esg01"})
    assert r.status_code == 200
    assert r.json()["product"]["product_code"] == "ESG01"

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    assert products[0]["product_code"] == "ESG01"
