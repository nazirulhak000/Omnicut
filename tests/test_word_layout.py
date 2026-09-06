"""
Unit tests for word_layout module.
Tests tokenization, combining mark protection, advance calculations,
and coordinate normalization.
"""

import pytest
from scripts.subtitle.word_layout import (
    is_combining_char,
    tokenize_text,
    layout_line,
    layout_overlay,
)

def test_is_combining_char():
    # Thai upper/lower vowels and tone marks
    assert is_combining_char('\u0e31')  # Mai Han-Akat
    assert is_combining_char('\u0e34')  # Sara I
    assert is_combining_char('\u0e48')  # Mai Ek
    assert is_combining_char('\u0e49')  # Mai Tho
    assert is_combining_char('\u0e4c')  # Thanthakhat (Garan)

    # Base consonants should NOT be combining marks
    assert not is_combining_char('\u0e01')  # Ko Kai
    assert not is_combining_char('\u0e25')  # Lo Ling
    assert not is_combining_char('A')
    assert not is_combining_char('1')
    assert not is_combining_char(' ')


def test_tokenize_text_preserves_combining_marks():
    text = "เพิ่งเปิด ตัวสิ่งนี้ ดีลพิเศษ 1 แถม 1"
    tokens = tokenize_text(text)
    
    # Verify no token begins with an orphan combining mark
    for tok in tokens:
        if not tok.isspace():
            assert not is_combining_char(tok[0]), f"Token '{tok}' starts with an orphan combining mark!"
            
    # Verify the joined tokens reproduce the original string
    assert "".join(tokens) == text


def test_tokenize_text_latin_and_mixed():
    text = "Logitech Wave Keys รีวิว 2026"
    tokens = tokenize_text(text)
    assert "".join(tokens) == text
    assert any("Logitech" in t for t in tokens)
    assert any("2026" in t for t in tokens)


def test_layout_line_coordinates_and_centering():
    text = "ลดกระหน่ำ ดีลลับ 1 แถม 1"
    result = layout_line(text, "Kanit", 75, norm_x=0.5, video_w=1080)
    
    words = result["words"]
    assert len(words) > 0
    assert result["line_width"] > 0
    assert result["abs_line_width"] > 0
    
    # Verify all words have valid coordinates within [0, 1]
    for w in words:
        assert 0.0 <= w["x"] <= 1.0
        assert 0.0 < w["w"] <= 1.0
        assert w["abs_x"] > 0
        assert w["abs_w"] > 0

    # Verify words are strictly ordered from left to right
    for i in range(len(words) - 1):
        assert words[i]["abs_x"] < words[i + 1]["abs_x"]
        assert words[i]["abs_x"] + words[i]["abs_w"] <= words[i + 1]["abs_x"] + 1.0  # allow 1px rounding


def test_layout_overlay_multiline():
    text = "หัวข้อแถวแรก\nแถวที่สองชัดเจน"
    res = layout_overlay(text, "Kanit", 75, norm_x=0.5, video_w=1080, video_h=1920)
    
    assert res["total_lines"] == 2
    assert len(res["lines"]) == 2
    assert res["lines"][0]["line_idx"] == 0
    assert res["lines"][1]["line_idx"] == 1
    assert len(res["lines"][0]["words"]) > 0
    assert len(res["lines"][1]["words"]) > 0


def test_api_overlay_layout_endpoint():
    from fastapi.testclient import TestClient
    from scripts.api_server import app
    client = TestClient(app)
    resp = client.post("/api/editor/overlay/layout", json={
        "text": "ข้อความทดสอบ 1 2 3",
        "font_name": "Kanit",
        "font_size_px": 75.0,
        "norm_x": 0.5,
        "norm_y": 0.5,
        "video_w": 1080,
        "video_h": 1920,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "lines" in data
    assert len(data["lines"]) == 1
    assert len(data["lines"][0]["words"]) > 0
    first_word = data["lines"][0]["words"][0]
    assert "x" in first_word and "w" in first_word
