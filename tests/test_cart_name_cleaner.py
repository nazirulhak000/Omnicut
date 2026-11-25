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

    # Unknown id must NOT substring-match curated names; only sanitize raw_name
    raw = "พัดลมตั้งโต๊ะ Hatari Cyclone Max 8 นิ้ว (PS8M1)"
    assert get_clean_cart_name(raw_name=raw) == sanitize_cart_name(raw)
    assert get_clean_cart_name(raw_name=raw) != "Hatari Cyclone Max 8 นิ้ว"


def test_get_clean_cart_name_strict_product_id_only():
    # B5: ambiguous substrings must never resolve to unrelated curated products
    assert get_clean_cart_name(raw_name="สายชาร์จ") == "สายชาร์จ"
    assert get_clean_cart_name(raw_name="Hatari พัดลมตั้งโต๊ะ") == "Hatari พัดลมตั้งโต๊ะ"
    assert get_clean_cart_name(raw_name="รางปลั๊กไฟ Toshino 1000W") == "รางปลั๊กไฟ Toshino 1000W"
    assert get_clean_cart_name(raw_name="USB Type-C Flash Drive") == "USB Type-C Flash Drive"
    assert get_clean_cart_name(product_id="unknown-id", raw_name="สายชาร์จเร็ว") == "สายชาร์จเร็ว"


def test_bluetooth_rule_and_no_transliteration():
    # B8: Rule 3.9 forbids Thai transliteration "บลูทูธ" in curated names & prompt examples
    for pid, name in CURATED_CART_NAMES.items():
        assert "บลูทูธ" not in name, f"Found บลูทูธ in {pid}: {name}"
    assert "Bluetooth" in CURATED_CART_NAMES["b0137078e2ff4c089b60131f60168b54"]
    assert "Bluetooth" in CURATED_CART_NAMES["jee01"]

    from pathlib import Path
    scraper_src = Path("scripts/product_scraper.py").read_text(encoding="utf-8")
    assert "#คีย์บอร์ดบลูทูธ" not in scraper_src
    assert "#คีย์บอร์ดBluetooth" in scraper_src


def test_thai_word_boundary_and_combining_mark_truncation():
    # B10: never slice mid-word (e.g. "สำหรับโทรศัพ") or leave orphaned combining mark
    from scripts.product_scraper import _short_name

    long_thai = "เคสกันกระแทกสำหรับโทรศัพท์มือถือรุ่นใหม่ล่าสุด"
    res = sanitize_cart_name(long_thai)
    assert len(res) <= 30
    assert "โทรศัพ" not in res or "โทรศัพท์" in res
    assert res[-1] not in "\u0E31\u0E34\u0E35\u0E36\u0E37\u0E38\u0E39\u0E3A\u0E47\u0E48\u0E49\u0E4A\u0E4B\u0E4C\u0E4D\u0E4E"

    short_res = _short_name(long_thai, limit=30)
    assert len(short_res) <= 30
    assert "โทรศัพ" not in short_res or "โทรศัพท์" in short_res
