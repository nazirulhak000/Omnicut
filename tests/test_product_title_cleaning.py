"""
Unit tests for concise canonical product title cleaning logic.
Verifies that affiliate marketing junk, parenthetical spec lists,
and SEO keyword spam are stripped while preserving English brand
and model names per project rules.
"""

import pytest
from scripts.product_scraper import clean_product_title
from scripts.product_store import ProductStore


def test_clean_product_title_strips_parenthetical_spec_lists():
    raw = "หูฟังเปิดหู MONSTER AC530 (ตัดเสียงรบกวน / เบสแน่น / กันน้ำ IPX7 / แบตอึด 145 ชม.)"
    cleaned = clean_product_title(raw)
    assert cleaned == "หูฟังเปิดหู MONSTER AC530"
    assert "ตัดเสียงรบกวน" not in cleaned
    assert "145 ชม." not in cleaned


def test_clean_product_title_strips_brackets_and_badges():
    raw = "【พร้อมส่ง】[New] Redmi Buds 8 Active ของแท้ 100% ประกันศูนย์ไทย 1 ปี - Shopee Thailand"
    cleaned = clean_product_title(raw)
    assert "พร้อมส่ง" not in cleaned
    assert "New" not in cleaned
    assert "ของแท้" not in cleaned
    assert "Shopee" not in cleaned
    assert cleaned == "Redmi Buds 8 Active"


def test_clean_product_title_condenses_long_seo_and_compatibility():
    raw = (
        "TRANYOO CC3 สายชาร์จแบบงอถัก 90° สำหรับเล่นเกม 30W Type-C เป็น Lightning "
        "และ 65W Type-C เป็น Type-C สำหรับชาร์จ iPhone เหมาะสำหรับเล่นเกม ความยาว 1.2 เมตร "
        "มีไฟติดสว่างตลอดเวลา ใช้ได้กับโทรศัพท์ Apple และ Android"
    )
    cleaned = clean_product_title(raw)
    assert len(cleaned) <= 55
    assert "TRANYOO CC3" in cleaned
    assert "เหมาะสำหรับ" not in cleaned
    assert "ใช้ได้กับ" not in cleaned


def test_clean_product_title_comma_separated_spec_dump():
    raw = (
        "ฟิล์มกระจกนิรภัย ESSAGER ความคมชัดสูง, ครอบคลุมทั้งหน้าจอ, ความแข็งระดับ 9H, "
        "กันรอยขีดข่วน, ทนต่อการสึกหรอ, แข็งแรงทนทาน, ทนต่อแรงกระแทกได้ดี, ติดตั้งง่าย, "
        "เหมาะสำหรับ iPhone 15/16/17"
    )
    cleaned = clean_product_title(raw)
    assert "ESSAGER" in cleaned
    assert "ฟิล์มกระจกนิรภัย" in cleaned
    assert "9H" in cleaned
    assert "เหมาะสำหรับ" not in cleaned
    assert len(cleaned) <= 50


def test_clean_product_title_preserves_english_brands():
    cases = [
        ("พาวเวอร์แบงค์แม่เหล็ก TTZ K106 Magnetic 30000mAh", ["TTZ K106", "30000mAh"]),
        ("สายชาร์จ 2 in 1 ESSAGER ES X93 60W", ["ESSAGER", "ES X93", "60W"]),
        ("เมาส์ไร้สาย Memzuoix 2.4G RGB", ["Memzuoix", "2.4G", "RGB"]),
        ("หูฟังบลูทูธไร้สาย Jeep EW011 TWS (Bluetooth 5.3 / HiFi Sound / IPX5)", ["Jeep EW011 TWS"]),
    ]
    for raw, expected_tokens in cases:
        cleaned = clean_product_title(raw)
        for token in expected_tokens:
            assert token in cleaned, f"Expected {token} in {cleaned}"


def test_clean_product_title_handles_login_and_challenges():
    assert clean_product_title("Log in") == ""
    assert clean_product_title("Sign in") == ""
    assert clean_product_title("Security Check") == ""
    assert clean_product_title("TikTok") == ""
    assert clean_product_title("") == ""
    assert clean_product_title(None) == ""


def test_product_store_automatically_cleans_names():
    # Calling ProductStore.add with bloated title should store cleaned title
    prod = ProductStore.add(
        name="หูฟังเปิดหู MONSTER AC530 (ตัดเสียงรบกวน / เบสแน่น / กันน้ำ IPX7 / แบตอึด 145 ชม.)",
        channel_id="main",
    )
    try:
        assert prod["name"] == "หูฟังเปิดหู MONSTER AC530"

        # Updating with bloated name should also be cleaned
        updated = ProductStore.update(
            prod["id"],
            channel_id="main",
            name="【ลดราคา】สายชาร์จเล่นเกม TRANYOO CC3 65W (ของแท้ / ส่งฟรี)",
        )
        assert updated["name"] == "สายชาร์จเล่นเกม TRANYOO CC3 65W"
    finally:
        # Cleanup test product
        ProductStore.delete(prod["id"], channel_id="main")
