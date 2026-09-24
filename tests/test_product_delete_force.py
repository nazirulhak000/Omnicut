import pytest
from scripts.product_store import ProductStore


def test_product_delete_posted_angle_blocks_without_force():
    # 1. Create a dummy product with a posted angle
    p = ProductStore.add(
        name="Test Block Delete Product",
        url="https://shopee.co.th/test-block-delete-12345",
        angles=[
            {"angle_id": "a1", "status": "posted", "script_lines": ["test line"]},
            {"angle_id": "a2", "status": "scripted", "script_lines": ["test line 2"]},
        ]
    )
    product_id = p["id"]
    assert ProductStore.get(product_id) is not None

    try:
        # 2. Attempt delete without force - should fail
        with pytest.raises(ValueError, match="ไม่อนุญาตให้ลบสินค้า"):
            ProductStore.delete(product_id, force=False)

        # Ensure product still exists
        assert ProductStore.get(product_id) is not None

        # 3. Delete with force=True - should succeed
        ProductStore.delete(product_id, force=True)
        assert ProductStore.get(product_id) is None
    finally:
        # Cleanup in case of failure
        if ProductStore.get(product_id) is not None:
            ProductStore.delete(product_id, force=True)


def test_product_delete_unposted_succeeds_without_force():
    # Product without posted angles should delete normally without force
    p = ProductStore.add(
        name="Test Normal Delete Product",
        url="https://shopee.co.th/test-normal-delete-12345",
        angles=[
            {"angle_id": "a1", "status": "scripted", "script_lines": ["test line"]},
        ]
    )
    product_id = p["id"]
    assert ProductStore.get(product_id) is not None

    ProductStore.delete(product_id, force=False)
    assert ProductStore.get(product_id) is None
