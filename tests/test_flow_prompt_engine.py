"""
Tests for scripts/flow_prompt_engine.py
"""

import pytest
from scripts.flow_prompt_engine import (
    build_fallback_prompt,
    expand_prompt_with_gemini,
    CAMERA_TECHNIQUES,
    LIGHTING_PRESETS,
)


def test_build_fallback_prompt_structure():
    prompt = build_fallback_prompt(
        thai_description="ช็อตพาวเวอร์แบงค์ตั้งโต๊ะ เห็นไฟสถานะ LED ติดสว่าง",
        product_name="TTZ Powerbank 30000mAh",
        technique="orbit",
        lighting="studio_clean",
    )
    assert "TTZ Powerbank 30000mAh" in prompt
    assert "360-degree" in prompt
    assert "9:16" in prompt
    assert "No on-screen text" in prompt


def test_camera_techniques_and_lighting_coverage():
    for tech_key in CAMERA_TECHNIQUES:
        prompt = build_fallback_prompt("ทดสอบ", "Gadget", technique=tech_key)
        assert CAMERA_TECHNIQUES[tech_key] in prompt

    for light_key in LIGHTING_PRESETS:
        prompt = build_fallback_prompt("ทดสอบ", "Gadget", lighting=light_key)
        assert LIGHTING_PRESETS[light_key] in prompt


def test_expand_prompt_fallback_when_offline(monkeypatch):
    # Ensure offline fallback returns high quality prompt
    monkeypatch.setenv("DISABLE_ANTIGRAVITY", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)

    prompt = expand_prompt_with_gemini(
        thai_description="กล้องหมุนรอบตัวสินค้า ชัดระดับมาโคร",
        product_name="Smart Watch Ultra",
        technique="macro",
        lighting="dramatic_dark",
    )
    assert "Smart Watch Ultra" in prompt
    assert "macro" in prompt.lower()
    assert "9:16" in prompt
