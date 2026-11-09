"""Same product link with different tracking params is one product (audit S1-14)."""

import pytest

from scripts.api_intake import _find_duplicate_product
from scripts.product_store import ProductStore, product_url_key

PDP = "https://shop.tiktok.com/th/pdp/1731628390379587684"


@pytest.mark.parametrize("variant", [
    PDP + "?source=share",
    PDP + "/?utm_source=line&utm_medium=chat",
    "https://www.tiktok.com/view/product/1731628390379587684?_d=eed51&og_info=%7B%7D",
    "https://shop.tiktok.com/th/pdp/hatari-cyclone-max/1731628390379587684",
])
def test_tiktok_variants_share_one_key(variant):
    assert product_url_key(variant) == product_url_key(PDP) == "tiktok:1731628390379587684"


def test_shopee_variants_share_one_key():
    a = "https://shopee.co.th/Hatari-Fan-i.123456.7890123?sp_atk=abc&xptdk=1"
    b = "https://shopee.co.th/product/123456/7890123"
    assert product_url_key(a) == product_url_key(b) == "shopee:123456.7890123"


def test_generic_links_keep_meaningful_query():
    assert product_url_key("https://x.test/item?id=1&utm_source=a") == product_url_key("https://x.test/item?id=1")
    assert product_url_key("https://x.test/item?id=1") != product_url_key("https://x.test/item?id=2")


def test_add_with_share_query_returns_existing_product():
    first = ProductStore.add(name="Hatari Cyclone Max", url=PDP)
    second = ProductStore.add(name="Hatari Cyclone Max", url=PDP + "?source=share")

    assert second["id"] == first["id"]
    assert len(ProductStore.snapshot()) == 1
    assert ProductStore.get(first["id"])["url"] == PDP  # stored link untouched


def test_add_dedups_by_tiktok_product_id():
    first = ProductStore.add(name="Hatari Cyclone Max", url="https://vt.tiktok.com/ZSabc/", tiktok_product_id="1731628390379587684")
    second = ProductStore.add(name="Hatari Cyclone Max", url="https://vt.tiktok.com/ZSxyz/", tiktok_product_id="1731628390379587684")

    assert second["id"] == first["id"]
    assert len(ProductStore.snapshot()) == 1


def test_different_products_stay_separate():
    a = ProductStore.add(name="A", url=PDP)
    b = ProductStore.add(name="B", url="https://shop.tiktok.com/th/pdp/1731628390379587999")
    assert a["id"] != b["id"]


def test_intake_duplicate_finder_ignores_tracking_params():
    product = ProductStore.add(name="Hatari Cyclone Max", url=PDP)
    found = _find_duplicate_product(PDP + "?source=share&utm_campaign=x", None)
    assert found is not None and found["id"] == product["id"]
