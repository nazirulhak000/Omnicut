import pytest
from scripts.hook_generator import HookVariationEngine, HOOK_STYLES


def test_hook_styles_definition():
    assert len(HOOK_STYLES) == 5
    style_ids = [s["style_id"] for s in HOOK_STYLES]
    assert "curiosity" in style_ids
    assert "warning" in style_ids
    assert "social_proof" in style_ids
    assert "deal_promo" in style_ids
    assert "pain_point" in style_ids


def test_offline_hook_generation():
    variations = HookVariationEngine.generate_offline_variations(
        product_name="Logitech Wave Keys คีย์บอร์ด Ergonomic",
        brand="Logitech",
        model="Wave Keys",
        pain_point="ปวดข้อมือเมื่อพิมพ์งานนานๆ",
        price_deal="ลด 20% วันนี้เท่านั้น",
    )
    assert len(variations) == 5
    for v in variations:
        assert "style_id" in v
        assert "hook_title" in v
        assert "hook_brand" in v
        assert "hook_model" in v
        assert "hook_label" in v
        assert "opening_line" in v
        # Rule 7: NO ellipsis "..." or "…"
        assert "..." not in v["hook_title"]
        assert "…" not in v["hook_title"]
        assert "..." not in v["opening_line"]
        assert "…" not in v["opening_line"]
        # Rule 9: Brand and model retained in English
        assert "Logitech" in v["hook_brand"]
        assert "Wave Keys" in v["hook_model"]


def test_sanitize_variant_rules():
    raw = {
        "style_id": "curiosity",
        "hook_title": "อย่าเพิ่งซื้อ... ถ้ายังไม่รู้… ข้อนี้!",
        "hook_brand": "Sony",
        "hook_model": "WH-1000XM5",
        "hook_label": "อย่าเพิ่งซื้อ...เด็ดขาด",
        "opening_line": "🔥 หูฟังตัวนี้... ดีจริงไหม? มาดูกันครับ",
    }
    sanitized = HookVariationEngine.sanitize_variant(raw, default_brand="Sony", default_model="WH-1000XM5")
    # Rule 7: Ellipses removed
    assert "..." not in sanitized["hook_title"]
    assert "…" not in sanitized["hook_title"]
    assert "..." not in sanitized["hook_label"]
    assert "..." not in sanitized["opening_line"]
    # Spoken opening line must not have emojis
    assert "🔥" not in sanitized["opening_line"]
    assert sanitized["hook_brand"] == "Sony"
    assert sanitized["hook_model"] == "WH-1000XM5"
