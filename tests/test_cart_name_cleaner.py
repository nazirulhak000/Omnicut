"""
tests/test_cart_name_cleaner.py
Unit tests for TikTok Shop cart name cleaner & sanitizer.
"""

import pytest
from scripts.cart_name_cleaner import clean_cart_name, sanitize_cart_name, get_clean_cart_name, CURATED_CART_NAMES

def test_roman_numerals_sanitized():
    # OKDO Balance II test case from user screenshot
    raw = "OKDO Balance Ⅱ เก้าอี้สุขภาพ ปรับเอนได้ 165° เก้าอี้เกมมิ่ง"
    res = sanitize_cart_name(raw)
    assert "Ⅱ" not in res
    assert "II" in res
    assert len(res) <= 30
    assert not res.endswith(" ป")
    assert res == "OKDO Balance II เก้าอี้สุขภาพ"

def test_all_curated_names_valid_for_tiktok():
    for pid, name in CURATED_CART_NAMES.items():
        assert len(name) <= 30, f"Name too long for pid {pid}: {name} ({len(name)})"
        assert "Ⅱ" not in name, f"Roman numeral found in {pid}: {name}"
        assert "°" not in name, f"Degree symbol found in {pid}: {name}"
        assert not name.endswith(" "), f"Trailing space in {pid}: {name}"

def test_get_clean_cart_name():
    # Known product id
    okdo_id = "ecc3e8df937945ffa7ce60695f4d336d"
    assert get_clean_cart_name(product_id=okdo_id) == "OKDO Balance II เก้าอี้สุขภาพ"
    
    # Unknown id but matching raw text
    assert get_clean_cart_name(raw_name="พัดลมตั้งโต๊ะ Hatari Cyclone Max 8 นิ้ว (PS8M1)") == "Hatari Cyclone Max 8 นิ้ว"
