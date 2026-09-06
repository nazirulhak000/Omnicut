import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.api_server import list_exports, LinkAngleRequest, link_export_to_angle
from scripts import product_store as ps


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Redirects ProductStore's STORE_PATH and BASE_DIR into tmp_path.
    Per .agents/rules/testing_standard.md rule 3 -- never touches the real
    _Docs/products.json. link_export_to_angle() calls
    ProductStore.update_angle_status() under the hood, which used to run
    against the real product store here with no seed/cleanup at all,
    permanently rewriting the first real product's first angle to
    status="rendered" every time this test ran."""
    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    return tmp_path


def test_export_versioning_grouping():
    """Verify list_exports correctly classifies latest vs previous version vs unlinked.

    Read-only against whatever real exports/products currently exist on
    disk -- list_exports() never writes, so no isolation is needed here.
    """
    res = list_exports()
    exports = res.get("exports", [])
    assert isinstance(exports, list)

    for item in exports:
        assert "is_latest" in item
        assert "is_previous_version" in item
        assert "is_unlinked" in item
        # Ensure mutually consistent flags
        if item["is_latest"]:
            assert not item["is_previous_version"]
            assert not item["is_unlinked"]
        if item["is_previous_version"]:
            assert not item["is_latest"]
            assert not item["is_unlinked"]
        if item["is_unlinked"]:
            assert not item["is_latest"]
            assert not item["is_previous_version"]


def test_link_export_to_angle_flow(isolated_store):
    """Verify linking an export video to a product angle updates status.

    Uses a seeded fake product inside isolated_store instead of mutating
    whatever real product happened to be first in the user's real
    products.json.
    """
    product = ps.ProductStore.add(name="ทดสอบลิงก์ export", url="https://x.test/link-export")
    ps.ProductStore.update(product["id"], angles=[
        {"angle_id": "pain_point", "hook_title": "Test angle"},
    ])
    prod_id = product["id"]
    aid = "pain_point"

    req = LinkAngleRequest(
        video_path="04_Exports/Ready_to_post/test_sample_video.mp4",
        product_id=prod_id,
        angle_id=aid
    )
    res = link_export_to_angle(req)
    assert res.get("status") == "success"
    updated_prod = res.get("product")
    assert updated_prod is not None
    updated_angle = next((a for a in updated_prod.get("angles", []) if (a.get("angle_id") or a.get("id")) == aid), None)
    assert updated_angle is not None
    assert updated_angle.get("video_url") == "04_Exports/Ready_to_post/test_sample_video.mp4"
    assert updated_angle.get("status") == "rendered"
