"""Unit tests for hashtag normalization and TikTok standards (scripts/hashtag_utils.py)."""
import pytest
from scripts.hashtag_utils import (
    clean_single_tag,
    extract_hashtag_list,
    normalize_tiktok_hashtags,
    MAX_TIKTOK_HASHTAGS,
    DEFAULT_BOOSTER_TAGS,
)


def test_clean_single_tag():
    assert clean_single_tag("#test") == "#test"
    assert clean_single_tag("test") == "#test"
    assert clean_single_tag("  ###OrsenS6  ") == "#OrsenS6"
    assert clean_single_tag("🔥สายชาร์จ⚡") == "#สายชาร์จ"
    assert clean_single_tag("") == ""


def test_extract_hashtag_list():
    raw_str = "#OrsenS6 #สายชาร์จเร็ว #TikTokป้ายยา"
    assert extract_hashtag_list(raw_str) == ["#OrsenS6", "#สายชาร์จเร็ว", "#TikTokป้ายยา"]

    raw_list = ["#OrsenS6", "สายชาร์จเร็ว", "#TikTokป้ายยา"]
    assert extract_hashtag_list(raw_list) == ["#OrsenS6", "#สายชาร์จเร็ว", "#TikTokป้ายยา"]

    # Duplicates case-insensitive
    dup_str = "#Orsen #orsen #ORSEN #cable"
    assert extract_hashtag_list(dup_str) == ["#Orsen", "#cable"]


def test_normalize_caps_at_max_5():
    eight_tags = "#tag1 #tag2 #tag3 #tag4 #tag5 #tag6 #tag7 #tag8"
    result = normalize_tiktok_hashtags(eight_tags)
    tags = result.split()
    assert len(tags) == MAX_TIKTOK_HASHTAGS
    assert len(tags) == 5
    assert tags == ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"]


def test_normalize_smart_pruning_preserves_boosters():
    # 6 tags with boosters at the end
    six_tags = "#OrsenS6 #สายชาร์จ240W #สายชาร์จเร็ว #สายชาร์จโน้ตบุ๊ก #TikTokป้ายยา #พิกัดในตะกร้า"
    result = normalize_tiktok_hashtags(six_tags)
    tags = result.split()
    assert len(tags) == 5
    # Must preserve brand/model and both conversion boosters
    assert "#OrsenS6" in tags
    assert "#TikTokป้ายยา" in tags
    assert "#พิกัดในตะกร้า" in tags


def test_normalize_filters_out_price_and_discount_words():
    dirty_tags = "#ลดราคา #โปรโมชั่น #คีย์บอร์ดบลูทูธ #ราคาถูก #พิกัดในตะกร้า"
    result = normalize_tiktok_hashtags(dirty_tags)
    tags = result.split()
    assert "#ลดราคา" not in tags
    assert "#โปรโมชั่น" not in tags
    assert "#ราคาถูก" not in tags
    assert "#คีย์บอร์ดบลูทูธ" in tags
    assert "#พิกัดในตะกร้า" in tags
    assert len(tags) <= 5


def test_normalize_fills_boosters_if_too_few():
    single_tag = "#หูฟังบลูทูธ"
    result = normalize_tiktok_hashtags(single_tag, product_name="Sony WH-1000XM5")
    tags = result.split()
    assert len(tags) >= 3
    assert len(tags) <= 5
    assert "#หูฟังบลูทูธ" in tags
    assert "#TikTokป้ายยา" in tags
    assert "#พิกัดในตะกร้า" in tags


def test_normalize_empty_input_uses_product_name_and_boosters():
    result = normalize_tiktok_hashtags("", product_name="Logitech Wave Keys")
    tags = result.split()
    assert len(tags) >= 3
    assert len(tags) <= 5
    assert any("Logitech" in t for t in tags)
    assert "#TikTokป้ายยา" in tags


def test_product_store_standardize_hashtags_dry_run():
    from scripts.product_store import ProductStore
    res = ProductStore.standardize_hashtags(apply=False, include_posted=False)
    assert "changes" in res
    assert "posted_untouched" in res
    assert res["applied"] is False

