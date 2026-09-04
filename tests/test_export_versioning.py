import pytest
from scripts.api_server import list_exports, LinkAngleRequest, link_export_to_angle
from scripts.product_store import ProductStore

def test_export_versioning_grouping():
    """Verify list_exports correctly classifies latest vs previous version vs unlinked."""
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

def test_link_export_to_angle_flow():
    """Verify linking an export video to a product angle updates status."""
    products = ProductStore.get_all()
    if not products:
        return
    prod = products[0]
    angles = prod.get("angles", [])
    if not angles:
        return
    angle = angles[0]
    aid = angle.get("angle_id") or angle.get("id")
    assert aid is not None

    # Test link_export_to_angle
    req = LinkAngleRequest(
        video_path="04_Exports/Ready_to_post/test_sample_video.mp4",
        product_id=prod["id"],
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


