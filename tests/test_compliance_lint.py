"""
Offline fixtures for the central compliance lint (Q1 price/claim, Q3 filler
opener, M3 structure checker) and the call sites that must enforce it.

No network, no paid API: AIBridge generation is driven through a monkeypatched
`_generate_from_prompt`, and every other check is pure.
"""

import pytest

import scripts.compliance_lint as cl
from scripts.ai_bridge import AIBridge
from scripts.hook_generator import HookVariationEngine
from scripts.it_angles import IT_ANGLE_CATALOG, fallback_angles
from scripts.product_callout_builder import CALLOUT_TYPES, build_product_callouts
from scripts.script_generator import ScriptGenerator
from scripts.script_rules import RULE_NO_PRICE, lint_text_field
from scripts.tts_sanitizer import TTSSanitizer


# ---------------------------------------------------------------------------
# Q1: price / discount / price-guess
# ---------------------------------------------------------------------------
PRICE_PHRASES = [
    "ตัวนี้แค่ 199 บาท",
    "เหลือ 199.-",
    "฿1,290 เท่านั้น",
    "1290฿",
    "ราคาดีมาก",
    "ราคาพิเศษวันนี้",
    "มีส่วนลดให้ด้วย",
    "ลดราคาแรงสุด",
    "ลด 50% วันนี้",
    "ถูกกว่าในห้าง",
    "ของถูกกับแพงต่างกันตรงไหน",
    "ประหยัดไปได้ไม่กี่บาท",
    "ทายราคากันหน่อย",
    "คิดว่าหลักร้อยหรือหลักพัน",
    "มีคูปองให้เก็บ",
    "จัดโปร วันนี้",
    "Flash Sale ด่วน",
    "ส่งฟรีทั่วไทย",
]

SPEC_PHRASES_NOT_PRICE = [
    "ลดเสียงรบกวนได้ 98%",
    "ช่วยลดความร้อนตอนชาร์จ",
    "โปรเซสเซอร์ใหม่เร็วขึ้น",
    "AirPods Pro 2 ตัดเสียงดีมาก",
    "ตั้งค่าโปรไฟล์ได้ 3 แบบ",
    "มีโปรเซสเซอร์แรง",
    "ชาร์จไว 20W PD แบต 10,000mAh",
    "แบตอยู่ได้ 36 เดือน",
    "เช็ค 3 จุดนี้ก่อนกดซื้อ",
]


@pytest.mark.parametrize("text", PRICE_PHRASES)
def test_price_phrases_are_caught(text):
    assert cl.find_price_term(text), text
    assert [v["code"] for v in cl.lint_text(text)] == [cl.RULE_NO_PRICE]


@pytest.mark.parametrize("text", SPEC_PHRASES_NOT_PRICE)
def test_spec_and_feature_phrases_are_not_price(text):
    assert cl.find_price_term(text) is None, text
    assert cl.find_claim_term(text) is None, text


# ---------------------------------------------------------------------------
# Q1: exaggerated / fabricated claims (10-sentence fixture per plan AC)
# ---------------------------------------------------------------------------
CLAIM_PHRASES = [
    "ใช้จริงมา 3 เดือนเต็ม สรุปให้ฟัง",
    "หลังจากทดลองใช้มา 3 เดือนเต็ม",
    "ทำไมคนสั่งกันถล่มทลายขนาดนี้",
    "ดีที่สุดในโลกแล้วตัวนี้",
    "ขายดีอันดับ 1 ใน TikTok",
    "เบอร์ 1 ของสายชาร์จ",
    "ทนทาน 100% ไม่พัง",
    "ใช้ยังไงก็ไม่มีวันพัง",
    "ขายไปแล้ว 10,000 ชิ้น",
    "ช่วยรักษาโรคปวดหลังได้",
]


@pytest.mark.parametrize("text", CLAIM_PHRASES)
def test_claim_phrases_are_caught(text):
    assert cl.find_claim_term(text), text
    assert cl.RULE_NO_EXAGGERATED_CLAIM in [v["code"] for v in cl.lint_text(text)]


# ---------------------------------------------------------------------------
# Q3: filler opener + CTA in line 1
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "ทุกคน! อย่าเพิ่งเลื่อนผ่านนะ",
    "หยุดดูก่อน 10 วินาทีครับ",
    "อย่าเลื่อนผ่านคลิปนี้",
    "ใครยังไม่มี ดูคลิปนี้ให้จบ",
    "ทุกคนดูนี่! ตัวนี้มาแรง",
])
def test_filler_openers_are_caught(text):
    codes = [v["code"] for v in cl.lint_opening_line(text)]
    assert cl.RULE_NO_FILLER_OPENER in codes


@pytest.mark.parametrize("text", [
    "กดตะกร้าดูรายละเอียดได้เลย",
    "รีบกดสั่งเลยครับ",
])
def test_cta_in_first_line_is_caught(text):
    assert cl.RULE_NO_CTA_FIRST_LINE in [v["code"] for v in cl.lint_opening_line(text)]


def test_concrete_opener_passes():
    assert cl.lint_opening_line("สายชาร์จพันกันทุกเช้า แก้ได้ด้วยตัวนี้ เดี๋ยวให้ดู") == []
    assert cl.lint_opening_line("เช็ค 3 จุดนี้ก่อนกดซื้อ") == []


# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------
def test_flag_disables_every_lint(monkeypatch):
    monkeypatch.setattr(cl, "COMPLIANCE_LINT_ENABLED", False)
    assert cl.lint_text("ราคา 199 บาท ดีที่สุดในโลก") == []
    assert cl.lint_opening_line("อย่าเพิ่งเลื่อนผ่าน") == []
    data = {"lines": [{"text": "ราคา 199 บาท"}, {"text": "ok"}]}
    assert cl.lint_script(data) == []
    assert cl.enforce_script_compliance(data)[1] == []


# ---------------------------------------------------------------------------
# Couple lint behavior must stay identical
# ---------------------------------------------------------------------------
def test_couple_price_lint_unchanged():
    assert cl.COUPLE_PRICE_KEYWORDS == (
        "บาท", "฿", "ราคา", "โปรโมชั่น", "ลดเหลือ", "คูปอง", "ส่วนลด", "ถูกมาก",
    )
    hit = lint_text_field("ตัวนี้ 99 บ. เอง", 0, "spoken")
    assert [v["code"] for v in hit] == [RULE_NO_PRICE]
    assert "'บ.'" in hit[0]["message"]
    # Couple lint never flagged spec words; keep it that way.
    assert lint_text_field("ลดเสียงรบกวนได้ดี", 0, "spoken") == []


# ---------------------------------------------------------------------------
# Templates / fallbacks are clean (Q1 + Q3 acceptance)
# ---------------------------------------------------------------------------
def test_script_generator_templates_pass_lint():
    for key in ScriptGenerator.TEMPLATES:
        script = ScriptGenerator.generate("Anker Nano 20W", template_key=key)
        assert cl.lint_script(script) == [], key
        for line in script["lines"]:
            assert "..." not in line["text"] and "…" not in line["text"]


def test_offline_hooks_pass_lint_and_have_no_emoji():
    variants = HookVariationEngine.generate_offline_variations(
        "Logitech Wave Keys", brand="Logitech", model="Wave Keys", pain_point="ปวดข้อมือ",
    )
    assert len(variants) == 5
    for v in variants:
        assert cl.lint_hook_variant(v) == [], v["style_id"]
        for key in ("hook_title", "hook_label", "opening_line"):
            assert not cl.EMOJI_RE.search(v[key]), (v["style_id"], key)


def test_sanitize_variant_strips_emoji_from_hook_title():
    v = HookVariationEngine.sanitize_variant({"style_id": "curiosity", "hook_title": "🔥 เพิ่งรู้ ⚡️"})
    assert v["hook_title"] == "เพิ่งรู้"


def test_ai_hook_with_violation_is_replaced_by_offline_template(monkeypatch):
    import json
    bad = [
        {"style_id": s, "hook_title": "t", "hook_label": "l", "opening_line": "ใช้งานดีมาก"}
        for s in ("curiosity", "warning", "social_proof", "deal_promo", "pain_point")
    ]
    bad[2]["opening_line"] = "ใช้จริงมา 3 เดือนเต็ม ราคาแค่ 199 บาท"
    monkeypatch.setattr(AIBridge, "is_available", classmethod(lambda cls: True))
    monkeypatch.setattr(AIBridge, "has_antigravity_cli", classmethod(lambda cls: True))
    monkeypatch.setattr(AIBridge, "call_antigravity_cli", classmethod(lambda cls, prompt, **k: json.dumps(bad, ensure_ascii=False)))
    out = HookVariationEngine.generate_variations("Anker Nano", brand="Anker", model="Nano")
    social = next(v for v in out if v["style_id"] == "social_proof")
    assert cl.lint_hook_variant(social) == []
    assert all(cl.lint_hook_variant(v) == [] for v in out)


def test_it_angle_fallback_hooks_have_no_price_or_claim():
    for angle in fallback_angles("หูฟัง Test Buds"):
        assert cl.lint_text(angle["hook"]) == [], angle
        assert cl.lint_opening_line(angle["hook"]) == [], angle
    assert {a["key"] for a in IT_ANGLE_CATALOG} >= {"spec_compare", "dont_cheap_out"}


# ---------------------------------------------------------------------------
# Callouts
# ---------------------------------------------------------------------------
def _cues():
    return [{"id": "b1", "start": 0.0, "end": 2.0}, {"id": "b2", "start": 2.0, "end": 4.0}]


def test_price_is_not_a_callout_type_and_price_text_is_dropped():
    assert "price" not in CALLOUT_TYPES
    overlays = build_product_callouts(
        _cues(),
        {
            "brand": "Anker",
            "price": "฿1,990",
            "features": ["ลดเสียงรบกวน ANC", "ราคาพิเศษสุดๆ"],
            "proof": "ขายดีอันดับ 1",
        },
        [{"role": "product_callout", "callout_type": "spec", "text": "199.-", "start": 1, "end": 2}],
    )
    texts = [o["tiers"][0]["text"] for o in overlays]
    assert "Anker" in texts
    assert "ลดเสียงรบกวน ANC" in texts
    for bad in ("฿1,990", "ราคาพิเศษสุดๆ", "ขายดีอันดับ 1", "199.-"):
        assert bad not in texts


# ---------------------------------------------------------------------------
# TTS sanitizer no longer speaks a price
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["ตัวนี้ 199.-", "฿199 เอง", "199฿ เท่านั้น"])
def test_tts_sanitizer_does_not_turn_price_into_baht(text):
    out = TTSSanitizer.clean(text)
    assert "บาท" not in out
    assert "ราคาพิเศษ" not in out


def test_tts_sanitizer_other_expansions_still_work():
    out = TTSSanitizer.clean("รองรับ USB-C ลดเสียงได้ 50%")
    assert "ยูเอสบีซี" in out
    assert "เปอร์เซ็นต์" in out


# ---------------------------------------------------------------------------
# AIBridge: parse (manual paste) + generate (regen once, then strip)
# ---------------------------------------------------------------------------
def test_parse_response_strips_on_screen_ellipsis_emoji_and_price_lines():
    import json
    raw = json.dumps({
        "hook_title": "🔥 ชาร์จไว",
        "lines": [
            {"text": "สายชาร์จพันกันทุกเช้า เดี๋ยวให้ดูวิธีแก้", "on_screen": "20W…"},
            {"text": "ราคาแค่ 199 บาทเอง", "on_screen": ""},
            {"text": "ชาร์จไว 20W PD", "on_screen": "ลด 50%"},
            {"text": "กดตะกร้าดูรายละเอียดได้เลยครับ"},
        ],
    }, ensure_ascii=False)
    data = AIBridge.parse_response("script", raw)
    assert data["hook_title"] == "ชาร์จไว"
    texts = [l["text"] for l in data["lines"]]
    assert "ราคาแค่ 199 บาทเอง" not in texts
    assert data["lines"][0]["on_screen"] == "20W"
    assert data["lines"][1]["on_screen"] == ""
    assert cl.lint_script(data) == []


def _good_script():
    return {"lines": [
        {"text": "สายชาร์จพันกันทุกเช้า เดี๋ยวให้ดูวิธีแก้"},
        {"text": "ชาร์จไว 20W PD"},
        {"text": "กดตะกร้าดูรายละเอียดได้เลยครับ"},
    ]}


def _bad_script():
    return {"lines": [
        {"text": "อย่าเพิ่งเลื่อนผ่าน"},
        {"text": "ราคาแค่ 199 บาท"},
        {"text": "ชาร์จไว 20W PD"},
        {"text": "กดตะกร้าดูรายละเอียดได้เลยครับ"},
    ]}


_CTX = {"product_name": "Anker", "angle_title": "x", "hook": "y", "specs": []}


def test_generate_regenerates_once_on_violation(monkeypatch):
    calls = []

    def fake(cls, task, prompt, context, model="m", prefer_antigravity=True):
        calls.append(prompt)
        return _bad_script() if len(calls) == 1 else _good_script()

    monkeypatch.setattr(AIBridge, "_generate_from_prompt", classmethod(fake))
    out = AIBridge.generate("script", _CTX)
    assert len(calls) == 2
    assert "ผิดกฎ" in calls[1]
    assert out == _good_script()


def test_generate_strips_when_retry_still_violates(monkeypatch):
    calls = []

    def fake(cls, task, prompt, context, model="m", prefer_antigravity=True):
        calls.append(prompt)
        return _bad_script()

    monkeypatch.setattr(AIBridge, "_generate_from_prompt", classmethod(fake))
    out = AIBridge.generate("script", _CTX)
    assert len(calls) == 2
    texts = [l["text"] for l in out["lines"]]
    assert texts == ["ชาร์จไว 20W PD", "กดตะกร้าดูรายละเอียดได้เลยครับ"]
    assert cl.lint_script(out) == []


def test_generate_strips_first_result_when_retry_errors(monkeypatch):
    calls = []

    def fake(cls, task, prompt, context, model="m", prefer_antigravity=True):
        calls.append(prompt)
        if len(calls) == 2:
            raise RuntimeError("network down")
        return _bad_script()

    monkeypatch.setattr(AIBridge, "_generate_from_prompt", classmethod(fake))
    out = AIBridge.generate("script", _CTX)
    assert cl.lint_script(out) == []


def test_generate_clean_output_is_single_call(monkeypatch):
    calls = []

    def fake(cls, task, prompt, context, model="m", prefer_antigravity=True):
        calls.append(prompt)
        return _good_script()

    monkeypatch.setattr(AIBridge, "_generate_from_prompt", classmethod(fake))
    AIBridge.generate("script", _CTX)
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Prompt rules (Q3 + M3)
# ---------------------------------------------------------------------------
def test_script_prompt_has_opener_and_beat_rules_and_default_length():
    prompt = AIBridge.build_prompt("script", dict(_CTX))
    assert "ประโยคแรกห้ามขอให้คนดูหยุดเลื่อน" in prompt
    assert "Open loop" in prompt
    assert "ห้ามเป็นคำถามทายราคา" in prompt
    # No target -> today's default length numbers unchanged.
    assert "7–8 บรรทัด (ประมาณ 500–650 ตัวอักษร)" in prompt
    assert "5 บรรทัด (ประมาณ 300–380 ตัวอักษร)" in prompt
    assert "__LENGTH_RULES__" not in prompt
    assert "target_duration" not in prompt


def test_script_prompt_uses_target_duration_when_given():
    prompt = AIBridge.build_prompt("script", dict(_CTX, target_duration=25, story_format="countdown"))
    target = cl.target_char_count(25)
    assert f"{target} ตัวอักษร" in prompt
    assert "500–650" not in prompt
    assert "นับถอยหลัง" in prompt


def test_non_script_prompts_keep_legacy_length_block():
    prompt = AIBridge.build_prompt("caption", {"product_name": "a", "angle_title": "b", "hook": "c"})
    assert AIBridge.LEGACY_LENGTH_RULES in prompt
    assert "__LENGTH_RULES__" not in prompt


# ---------------------------------------------------------------------------
# M3: structure checker
# ---------------------------------------------------------------------------
GOOD_STRUCTURE = [
    {"text": "สายชาร์จพันกันทุกเช้า เดี๋ยวให้ดูวิธีที่จบปัญหานี้"},
    {"text": "ตัวนี้คือสายแม่เหล็ก 3-in-1 ชาร์จไว 20W PD"},
    {"text": "ดูดติดหัวชาร์จเอง ไม่ต้องคลำในที่มืด"},
    {"text": "จากที่พันกันทุกเช้า ตอนนี้ม้วนเก็บเรียบร้อยในวินาทีเดียว"},
    {"text": "ใครใช้สายแบบไหนอยู่ เล่าในคอมเมนต์ได้เลย"},
    {"text": "กดตะกร้าดูรายละเอียดได้เลยครับ"},
]


def test_structure_good_script_passes():
    report = cl.check_script_structure(GOOD_STRUCTURE)
    assert report["ok"], report["warnings"]


def test_structure_flags_missing_open_loop():
    lines = [{"text": "สายชาร์จแม่เหล็กสีดำ"}, {"text": "ชาร์จได้ 20W PD"}] + GOOD_STRUCTURE[2:]
    codes = [w["code"] for w in cl.check_script_structure(lines)["warnings"]]
    assert cl.STRUCT_NO_OPEN_LOOP in codes


def test_structure_flags_filler_last_content_line():
    lines = GOOD_STRUCTURE[:4] + [{"text": "บอกเลยว่าตอบโจทย์ชีวิตมาก"}, GOOD_STRUCTURE[-1]]
    codes = [w["code"] for w in cl.check_script_structure(lines)["warnings"]]
    assert cl.STRUCT_FILLER_ENDING in codes


def test_structure_length_within_target_tolerance():
    chars = cl.count_script_chars(GOOD_STRUCTURE)
    seconds_exact = chars / cl.CHARS_PER_SECOND
    ok = cl.check_script_structure(GOOD_STRUCTURE, target_duration=seconds_exact)
    assert cl.STRUCT_LENGTH_OFF_TARGET not in [w["code"] for w in ok["warnings"]]
    too_long_target = cl.check_script_structure(GOOD_STRUCTURE, target_duration=seconds_exact * 2)
    assert cl.STRUCT_LENGTH_OFF_TARGET in [w["code"] for w in too_long_target["warnings"]]
    no_target = cl.check_script_structure(GOOD_STRUCTURE, target_duration=None)
    assert no_target["target_chars"] is None


def test_structure_checker_never_raises_on_junk():
    assert cl.check_script_structure([])["ok"]
    cl.check_script_structure([None, {"text": None}, "plain string"])
