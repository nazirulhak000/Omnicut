"""Spec-number highlight tier (roadmap Q7) + no Thai transliterations (Q1).

Only WHICH word gets the existing highlight changes: the colour is the one the
dictionary already used for 66W/100W/120Hz, and a burst keeps one highlight.
"""

import re

from scripts.subtitle.translation_service import (
    KINETIC_KEYWORDS,
    SPEC_HIGHLIGHT_COLOR,
    apply_bilingual_kinetic_highlighting,
    apply_kinetic_highlighting,
    apply_kinetic_highlighting_en,
    find_spec_number,
)

TAG = re.compile(r"\{\\c(&H[0-9A-Fa-f]+&)\}")


def _highlighted(res):
    m = re.search(r"\{\\c&H[0-9A-Fa-f]+&\}([^{]+)\{\\c", res)
    return m.group(1) if m else None


def _highlight_count(res, primary="&H00FFFFFF&"):
    return sum(1 for c in TAG.findall(res) if c != primary)


def test_spec_regex_matches_units():
    for text, want in [
        ("แบต 5000mAh อึดมาก", "5000mAh"),
        ("ชาร์จไว 65W", "65W"),
        ("จอ 120 Hz ลื่น", "120 Hz"),
        ("ใช้ได้ 30 ชั่วโมง", "30 ชั่วโมง"),
        ("เล่นได้ 8 ชม. เต็ม", "8 ชม."),
        ("ความจุ 1.5 TB", "1.5 TB"),
        ("หน้าจอ 6.7 นิ้ว", "6.7 นิ้ว"),
        ("ดีเลย์ 40ms", "40ms"),
    ]:
        assert find_spec_number(text) == want, text


def test_spec_regex_ignores_non_specs():
    for text in ["ราคา 199 บาท", "USB3 ก็ได้", "10 Watts", "ปี 2026", "ลดไป 20%"]:
        assert find_spec_number(text) is None, text


def test_spec_number_beats_hype_dictionary():
    res = apply_kinetic_highlighting("แบต 5000mAh ดีมาก")
    assert _highlighted(res) == "5000mAh"
    assert _highlight_count(res) == 1
    assert SPEC_HIGHLIGHT_COLOR in res


def test_explicit_marker_and_custom_keyword_still_win():
    assert _highlighted(apply_kinetic_highlighting("*สุดปัง* แบต 5000mAh")) == "สุดปัง"
    res = apply_kinetic_highlighting("Logitech แบต 5000mAh", custom_keywords=["Logitech"])
    assert _highlighted(res) == "Logitech"


def test_spec_tier_respects_color_hint():
    res = apply_kinetic_highlighting("แบต 5000mAh", color_hint="&H0000E6FF&")
    assert "{\\c&H0000E6FF&}5000mAh" in res


def test_english_spec_and_bilingual_sync():
    en = apply_kinetic_highlighting_en("5000mAh battery is amazing")
    assert _highlighted(en) == "5000mAh"
    th, en = apply_bilingual_kinetic_highlighting("แบต 5000mAh ดีมาก", "5000mAh battery, really good")
    th_colors = {c for c in TAG.findall(th) if c != "&H00FFFFFF&"}
    en_colors = {c for c in TAG.findall(en) if c != "&H00EAEAEA&"}
    assert th_colors == en_colors and len(th_colors) == 1


def test_no_thai_transliteration_of_tech_terms_in_dictionary():
    all_kw = [kw for kws in KINETIC_KEYWORDS.values() for kw in kws]
    for banned in ("บลูทูธ", "ฟาสชาร์จ"):
        assert banned not in all_kw
    assert "Bluetooth" in all_kw and "Fast Charge" in all_kw
