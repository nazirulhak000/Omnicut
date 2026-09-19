import pytest
from scripts.api_videos import _sanitize_media_filename


def test_sanitize_media_filename_preserves_thai_vowels_and_tones():
    # Names from user report where tone marks and vowels were previously stripped
    cases = [
        ("ปลั๊กไฟ TOSHINO มี 2345.mov", "ปลั๊กไฟ TOSHINO มี 2345.mov"),
        ("Toshino ปลั๊กไฟ 2300w.mov", "Toshino ปลั๊กไฟ 2300w.mov"),
        ("พัดลม hatari.mov", "พัดลม hatari.mov"),
        ("Teleson ขาตั้ง.mov", "Teleson ขาตั้ง.mov"),
        ("Easseger 100w สายชาร์จ.mov", "Easseger 100w สายชาร์จ.mov"),
        ("Orphan พัดลมมือถือ.mov", "Orphan พัดลมมือถือ.mov"),
        ("รีวิวไมค์ไร้สาย (ตัวท็อป) [V1].mp4", "รีวิวไมค์ไร้สาย (ตัวท็อป) [V1].mp4"),
    ]
    for raw_input, expected in cases:
        assert _sanitize_media_filename(raw_input) == expected, f"Failed for {raw_input}"


def test_sanitize_media_filename_strips_dangerous_characters():
    # Windows forbidden characters and directory traversal characters
    dangerous = "ปลั๊กไฟ: <test>*?\"|/\\..mov"
    cleaned = _sanitize_media_filename(dangerous)
    # Dangerous chars should be stripped, but Thai and safe punctuation kept
    assert ":" not in cleaned
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "*" not in cleaned
    assert "?" not in cleaned
    assert '"' not in cleaned
    assert "|" not in cleaned
    assert "/" not in cleaned
    assert "\\" not in cleaned
    assert "ปลั๊กไฟ" in cleaned
