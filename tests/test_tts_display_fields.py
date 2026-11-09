"""Display fields keep official English; phonetic Thai only goes to TTS fields
(audit S2-04 ai-generate, S2-05 hook opening line). Offline: no AI call.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts.api_voice import sanitize_generated_angle
from scripts.hook_generator import HookVariationEngine


# --- S2-04: /api/script/ai-generate -----------------------------------------

def test_ai_generated_angle_keeps_english_in_display_fields():
    ang = {
        "script_text": "สาย USB-C ชาร์จไว\nเชื่อม Bluetooth 5.3 ได้ทันที",
        "hook_title": "หูฟัง Bluetooth ที่คุ้มสุด",
        "caption": "รีวิวสาย USB-C #รีวิว #ของดี",
    }
    sanitize_generated_angle(ang)

    assert ang["script_text"].split("\n") == ["สาย USB-C ชาร์จไว", "เชื่อม Bluetooth 5.3 ได้ทันที"]
    assert "Bluetooth" in ang["hook_title"]
    assert "#รีวิว" in ang["caption"] and "#ของดี" in ang["caption"]
    assert "USB-C" in ang["caption"]
    for field in ("script_text", "hook_title", "caption"):
        assert "บลูทูธ" not in ang[field] and "ยูเอสบีซี" not in ang[field]

    # The spoken form lives in its own keys.
    assert ang["tts_lines"][0] == "สาย ยูเอสบีซี ชาร์จไว"
    assert "บลูทูธ" in ang["tts_lines"][1]
    assert "บลูทูธ" in ang["tts_hook_title"]


# --- S2-05: hook opening line ------------------------------------------------

def test_hook_variant_opening_line_is_display_text():
    variant = HookVariationEngine.sanitize_variant({
        "style_id": "curiosity",
        "hook_title": "หูฟัง Bluetooth",
        "opening_line": "หูฟัง Bluetooth ตัวนี้ชาร์จผ่าน USB-C ครับ",
    })
    assert "Bluetooth" in variant["opening_line"] and "USB-C" in variant["opening_line"]
    assert "บลูทูธ" in variant["tts_opening_line"]


@patch("scripts.api_hooks.ProductStore")
def test_apply_hook_writes_display_to_script_lines_and_phonetic_to_tts_lines(mock_store):
    from scripts.api_server import app

    mock_store.get.return_value = {
        "id": "prod_1",
        "angles": [{
            "angle_id": "ang_1",
            "hook_title": "เก่า",
            "script_lines": ["ประโยคแรกเดิม", "เชื่อม Bluetooth ไว"],
            "tts_lines": ["ประโยคแรกเดิม", "เชื่อม บลูทูธ ไว"],
        }],
    }
    mock_store.update.return_value = {"id": "prod_1"}

    resp = TestClient(app).post("/api/hooks/apply-angle", json={
        "product_id": "prod_1",
        "angle_id": "ang_1",
        "hook_variant": {"style_id": "curiosity", "hook_title": "ใหม่",
                         "opening_line": "หูฟัง Bluetooth ตัวนี้ดีมากครับ"},
        "update_script_first_line": True,
    })
    assert resp.status_code == 200
    angle = resp.json()["angle"]
    assert angle["script_lines"][0] == "หูฟัง Bluetooth ตัวนี้ดีมากครับ"
    assert "บลูทูธ" in angle["tts_lines"][0]
    assert angle["tts_lines"][1] == "เชื่อม บลูทูธ ไว"          # rest of the TTS lines kept
    assert angle["script_text"].split("\n")[0] == "หูฟัง Bluetooth ตัวนี้ดีมากครับ"
