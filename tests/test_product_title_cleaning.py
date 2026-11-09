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


# ---------------------------------------------------------------------------
# Audit S1-02: model-name hyphens survive (Rule 9)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw, token", [
    ("หูฟัง Sony WH-1000XM5 ตัดเสียงรบกวน", "WH-1000XM5"),
    ("สายชาร์จ USB-C to USB-C 60W", "USB-C"),
    ("หัวชาร์จ Type-C 20W", "Type-C"),
    ("ลำโพง Sony HT-PF01 - Shopee Thailand", "HT-PF01"),
    ("หัวชาร์จ Type\u2011C 20W", "Type-C"),  # U+2011 non-breaking hyphen
    ("หูฟัง Sony WH\u20131000XM5", "WH-1000XM5"),  # en dash inside a model
])
def test_clean_product_title_keeps_model_hyphens(raw, token):
    assert token in clean_product_title(raw)


def test_clean_product_title_drops_separator_dashes():
    assert clean_product_title("Anker Soundcore — R50i - สีดำ") == "Anker Soundcore R50i สีดำ"


# ---------------------------------------------------------------------------
# Audit S1-03: price / discount / promo / emoji never survive cleaning
# ---------------------------------------------------------------------------
from scripts.compliance_lint import find_price_term  # noqa: E402


@pytest.mark.parametrize("raw, expected", [
    ("🔥ลดราคา 50%🔥 หูฟัง Sony WH-1000XM5 ราคา 299 บาท ฿299", "หูฟัง Sony WH-1000XM5"),
    ("Flash Sale ⚡ เมาส์ Logitech G304 ลด 30% เหลือ ฿890", "เมาส์ Logitech G304"),
    ("Xiaomi Redmi Buds 6 Pro โปรแรง ส่งฟรี คูปอง", "Xiaomi Redmi Buds 6 Pro"),
    ("Big Sale!! พัดลม Hatari 16 นิ้ว ไม่แพง", "พัดลม Hatari 16 นิ้ว"),
    ("Mega Sale หูฟัง Jeep EW011 -50% THB 199", "หูฟัง Jeep EW011"),
])
def test_clean_product_title_strips_price_promo_emoji(raw, expected):
    cleaned = clean_product_title(raw)
    assert cleaned == expected
    assert find_price_term(cleaned) is None
    for junk in ("฿", "บาท", "%", "Sale", "🔥", "⚡"):
        assert junk not in cleaned


def test_clean_product_title_keeps_noise_reduction_wording():
    # "ลดเสียงรบกวน" is a feature, not a discount.
    cleaned = clean_product_title("หูฟัง ลดเสียงรบกวน ANC Soundcore Q20i")
    assert "ลดเสียงรบกวน" in cleaned
    assert "Soundcore Q20i" in cleaned


def test_product_store_add_strips_price_from_name():
    prod = ProductStore.add(name="🔥ลดราคา 50%🔥 หูฟัง Sony WH-1000XM5 ราคา 299 บาท ฿299")
    try:
        assert prod["name"] == "หูฟัง Sony WH-1000XM5"
        assert find_price_term(prod["name"]) is None
        updated = ProductStore.update(prod["id"], name="Sony WH-1000XM5 ลด 20% เหลือ 9,990 บาท")
        assert updated["name"] == "Sony WH-1000XM5"
    finally:
        ProductStore.delete(prod["id"])


def test_product_store_rejects_name_that_is_only_a_price():
    with pytest.raises(ValueError, match="ชื่อสินค้า"):
        ProductStore.add(name="ราคา 299 บาท")
