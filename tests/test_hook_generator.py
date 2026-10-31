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


# ---------------------------------------------------------------------------
# API-key path: used to call AIBridge.call_direct_gemini, which never existed,
# so every API-key-only run silently fell back to the offline templates.
# ---------------------------------------------------------------------------
import json as _json

from scripts.ai_bridge import AIBridge

_STYLE_IDS = ("curiosity", "warning", "social_proof", "deal_promo", "pain_point")
_AI_VARIANTS = [
    {"style_id": s, "hook_brand": "Anker", "hook_model": "Nano",
     "hook_title": f"AI {s}", "hook_label": f"AI ป้าย {s}", "opening_line": f"AI เปิดคลิป {s} ชาร์จเต็มไว"}
    for s in _STYLE_IDS
]


def _api_key_only_bridge(monkeypatch, keys=("k1",)):
    monkeypatch.setattr(AIBridge, "is_available", classmethod(lambda cls: True))
    monkeypatch.setattr(AIBridge, "has_antigravity_cli", classmethod(lambda cls: False))
    monkeypatch.setattr(AIBridge, "has_api_key", classmethod(lambda cls: bool(keys)))
    monkeypatch.setattr(AIBridge, "get_api_keys", classmethod(lambda cls: list(keys)))
    monkeypatch.setattr("scripts.quota.check_budget", lambda task="": None)


def test_ai_bridge_has_no_call_direct_gemini_and_generator_does_not_use_it():
    import inspect
    import scripts.hook_generator as hg
    assert not hasattr(AIBridge, "call_direct_gemini")
    assert "AIBridge.call_direct_gemini" not in inspect.getsource(hg)


def test_api_key_path_uses_gemini_results_not_offline_templates(monkeypatch):
    _api_key_only_bridge(monkeypatch)
    calls = []

    def fake_call(prompt):
        calls.append(prompt)
        return _json.dumps(_AI_VARIANTS, ensure_ascii=False)

    monkeypatch.setattr(HookVariationEngine, "call_gemini_api", staticmethod(fake_call))
    out = HookVariationEngine.generate_variations("Anker Nano", brand="Anker", model="Nano")
    assert len(calls) == 1
    assert [v["hook_title"] for v in out] == [f"AI {s}" for s in _STYLE_IDS]


def test_cli_failure_falls_through_to_api_key(monkeypatch):
    _api_key_only_bridge(monkeypatch)
    monkeypatch.setattr(AIBridge, "has_antigravity_cli", classmethod(lambda cls: True))

    def broken_cli(cls, prompt, **kwargs):
        raise RuntimeError("agy crashed")

    monkeypatch.setattr(AIBridge, "call_antigravity_cli", classmethod(broken_cli))
    monkeypatch.setattr(
        HookVariationEngine, "call_gemini_api",
        staticmethod(lambda prompt: _json.dumps(_AI_VARIANTS, ensure_ascii=False)),
    )
    out = HookVariationEngine.generate_variations("Anker Nano", brand="Anker", model="Nano")
    assert out[0]["hook_title"] == "AI curiosity"


def test_call_gemini_api_rotates_keys_through_genai_client(monkeypatch):
    _api_key_only_bridge(monkeypatch, keys=("bad", "good"))
    import google.genai as genai
    from scripts.ai_bridge import DEFAULT_MODEL

    seen = []

    class FakeModels:
        def __init__(self, key):
            self.key = key

        def generate_content(self, model, contents):
            seen.append((self.key, model))
            if self.key == "bad":
                raise RuntimeError("401 invalid key")
            return type("R", (), {"text": _json.dumps(_AI_VARIANTS, ensure_ascii=False)})()

    class FakeClient:
        def __init__(self, api_key, http_options=None):
            self.models = FakeModels(api_key)

    monkeypatch.setattr(genai, "Client", FakeClient)
    raw = HookVariationEngine.call_gemini_api("prompt")
    assert [k for k, _ in seen] == ["bad", "good"]
    assert all(m == DEFAULT_MODEL for _, m in seen)
    assert _json.loads(raw)[0]["style_id"] == "curiosity"

    # End to end through generate_variations with the same fake client.
    out = HookVariationEngine.generate_variations("Anker Nano", brand="Anker", model="Nano")
    assert out[0]["hook_title"] == "AI curiosity"


def test_call_gemini_api_without_keys_returns_empty(monkeypatch):
    _api_key_only_bridge(monkeypatch, keys=())
    assert HookVariationEngine.call_gemini_api("prompt") == ""
    out = HookVariationEngine.generate_variations("Anker Nano", brand="Anker", model="Nano")
    assert len(out) == 5  # offline templates
