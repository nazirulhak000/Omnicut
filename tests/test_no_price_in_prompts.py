"""
Guard: AI prompts/templates never nudge a price into a TikTok clip.

Project rule (AGENTS.md + owner memory): clips must never show or say a
price, discount, promo, coupon or price guess -- it breaks TikTok rules.
These tests stay offline: the Gemini client is replaced by a fake that only
captures the prompt, and the fallback templates are checked directly.
"""

import re
from pathlib import Path

import pytest

from scripts.ai_bridge import AIBridge
from scripts.product_scraper import ANGLE_CATALOG, NO_PRICE_PROMPT_RULE, ProductScraper

# Words that would put a price / promo into spoken script, captions or hooks.
PRICE_NUDGE_PATTERN = re.compile(
    r"ราคา|บาท|฿|หลักร้อย|หลักพัน|ส่วนลด|ลดราคา|ลดแรง|ลดพิเศษ|คูปอง|โปรโมช|Flash Sale|flashsale|ส่งฟรี|"
    r"คุ้มเกินราคา|คุ้มค่าเงิน|สตางค์|ก่อนโปรหมด"
)

PRODUCT_WITH_PRICE = {
    "title": "หูฟัง Test Buds",
    "description": "หูฟังไร้สาย ANC",
    "price_note": "฿1,290 ลด 50% วันนี้",
    "raw_text": "R",
}


def _capture_matrix_prompt(monkeypatch, **kwargs):
    captured = {}

    class FakeModels:
        def generate_content(self, model, contents):
            captured["contents"] = contents
            raise RuntimeError("stop -- capturing prompt only")

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    import google.genai as genai
    import scripts.config as config
    import scripts.quota as quota

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(config, "get_gemini_api_keys", lambda: ["fake-key-for-test"])
    monkeypatch.setattr(quota, "check_budget", lambda *a, **k: None)

    angles = ProductScraper.generate_content_matrix(PRODUCT_WITH_PRICE, count=10, **kwargs)
    contents = captured["contents"]
    prompt = contents if isinstance(contents, str) else "\n".join(c for c in contents if isinstance(c, str))
    return prompt, angles


def test_content_matrix_prompt_forbids_price_and_never_receives_price_note(monkeypatch):
    prompt, _ = _capture_matrix_prompt(monkeypatch, duration="30s")

    assert NO_PRICE_PROMPT_RULE in prompt
    # The scraped price is product data, never generation input.
    assert "1,290" not in prompt
    assert "ลด 50%" not in prompt
    assert "ราคา/โปรโมชั่น:" not in prompt
    # No example line in the prompt models a price CTA for the AI to copy.
    assert "ราคาพิเศษ" not in prompt
    assert "129 บาท" not in prompt
    assert "ข้อเสนอราคา" not in prompt


def test_content_matrix_fallback_templates_have_no_price_nudges(monkeypatch):
    # Fake client raises -> generate_content_matrix falls back to templates.
    _, angles = _capture_matrix_prompt(monkeypatch, duration="30s")
    assert len(angles) == 10
    for angle in angles:
        fields = [angle.get("hook_title", ""), angle.get("price_deal", ""),
                  angle.get("pain_point", ""), angle.get("key_features", ""),
                  angle.get("tiktok_caption", ""), angle.get("tiktok_hashtags", "")]
        fields += list(angle.get("script_lines") or [])
        for text in fields:
            assert not PRICE_NUDGE_PATTERN.search(text), (angle.get("angle_id"), text)


def test_angle_catalog_labels_do_not_promise_price_deals():
    for angle_id, meta in ANGLE_CATALOG.items():
        assert not PRICE_NUDGE_PATTERN.search(meta["label"]), angle_id
        assert "โปรไฟลุก" not in meta["label"]


@pytest.mark.parametrize("task", ["script", "caption"])
def test_ai_bridge_drops_price_context_and_forbids_price(task):
    context = {
        "product_name": "หูฟัง",
        "angle_title": "x",
        "hook": "y",
        "specs": [],
        "price_deal": "ลดเหลือ 3,190 บาท",
        "price_note": "฿3,190",
    }
    prompt = AIBridge.build_prompt(task, context)
    assert "3,190" not in prompt
    assert "price_deal" not in prompt
    assert "ราคาโปรโมชั่น" not in prompt
    assert "ห้ามพูด/เขียนถึงราคา" in prompt


def test_ai_bridge_script_task_no_longer_requires_price_deal():
    prompt = AIBridge.build_prompt("script", {
        "product_name": "หูฟัง", "angle_title": "x", "hook": "y", "specs": [],
    })
    assert "หูฟัง" in prompt


def test_mobile_quick_studio_templates_have_no_price_cta():
    from pathlib import Path
    import scripts.mobile_quick_studio as mqs
    src = Path(mqs.__file__).read_text(encoding="utf-8")
    for phrase in ("พิกัดราคาพิเศษ", "พิกัดราคาโปรโมชั่น", "คุ้มค่าเกินราคา", "คุ้มค่าเงิน"):
        assert phrase not in src


# ----------------------------------------------------------------------
# Round 2: legacy script/hook/voice/producer paths and price defaults
# ----------------------------------------------------------------------
def test_script_generator_templates_never_speak_price_deal():
    from scripts.script_generator import ScriptGenerator

    for key in ScriptGenerator.TEMPLATES:
        data = ScriptGenerator.generate(
            "หูฟัง Test Buds", "ANC", "เสียงรบกวน",
            price_deal="ลดเหลือ 159 บาท ส่งฟรี", template_key=key,
        )
        assert "159" not in data["full_text"], key
        assert not PRICE_NUDGE_PATTERN.search(data["full_text"]), (key, data["full_text"])


def test_hook_generator_offline_variants_and_styles_have_no_price():
    from scripts.hook_generator import HOOK_STYLES, HookVariationEngine

    variants = HookVariationEngine.generate_offline_variations(
        "หูฟัง Test Buds", brand="Test", model="Buds", pain_point="เสียงรบกวน",
        price_deal="ลด 20% วันนี้เท่านั้น",
    )
    assert {v["style_id"] for v in variants} >= {"deal_promo"}
    for v in variants:
        for field in ("hook_title", "hook_label", "opening_line"):
            assert "20%" not in v[field]
            assert not PRICE_NUDGE_PATTERN.search(v[field]), (v["style_id"], field, v[field])
    deal_style = next(s for s in HOOK_STYLES if s["style_id"] == "deal_promo")
    assert "ส่วนลด" not in deal_style["style_name"]
    assert "โปร" not in deal_style["style_name"]


def test_hook_generator_ai_prompt_drops_price_and_forbids_it():
    import scripts.hook_generator as hg

    src = Path(hg.__file__).read_text(encoding="utf-8")
    assert "{price_deal}" not in src
    assert "ห้ามพูด/เขียนถึงราคา" in src
    assert "โปรแรง คุ้มค่า ลดกระหน่ำ" not in src


def test_api_voice_and_producer_prompts_have_no_price_input():
    import scripts.api_producer as api_producer
    import scripts.api_voice as api_voice

    voice_src = Path(api_voice.__file__).read_text(encoding="utf-8")
    assert "ราคา/โปร: {req.price_deal}" not in voice_src
    assert "Price Value" not in voice_src
    assert "ห้ามพูด/เขียนถึงราคา" in voice_src

    producer_src = Path(api_producer.__file__).read_text(encoding="utf-8")
    for phrase in ("รีบดูก่อนหมดโปร", "ลดราคาเดือด", "พิกัดของแท้พร้อมโปรพิเศษ", "ทนทานคุ้มราคา"):
        assert phrase not in producer_src


def test_price_deal_defaults_are_empty_and_price_note_not_copied():
    import inspect

    import scripts.api_exports as api_exports
    import scripts.batch_render as batch_render
    from scripts.api_schemas import ScriptGenerateRequest
    from scripts.pipeline import TikTokAutoCutterPipeline
    from scripts.pipeline_context import PipelineContext

    assert ScriptGenerateRequest(product_name="x").price_deal == ""
    assert inspect.signature(TikTokAutoCutterPipeline.run).parameters["price_deal"].default == ""
    assert PipelineContext.__dataclass_fields__["price_deal"].default == ""

    br_src = Path(batch_render.__file__).read_text(encoding="utf-8")
    assert 'latest_prod.get("price_note"' not in br_src
    ex_src = Path(api_exports.__file__).read_text(encoding="utf-8")
    assert 'info["price_deal"] = matched_prod.get("price_note")' not in ex_src


def test_cover_hook_presets_have_no_price():
    import scripts.api_covers as api_covers

    src = Path(api_covers.__file__).read_text(encoding="utf-8")
    assert "ราคาหลักร้อย" not in src
