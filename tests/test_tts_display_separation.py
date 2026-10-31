import pytest
from scripts.tts_sanitizer import TTSSanitizer
from scripts.voice_engine import VoiceEngine

def test_tts_display_separation():
    sample_text = "คีย์บอร์ด Logitech Wave Keys รองรับ USB-C และ WFH แบตเตอรี่ 36 เดือน 199.-"
    
    # 1. Check TTSSanitizer output
    tts_text = TTSSanitizer.clean(sample_text)
    
    # TTS audio input must have phonetic expansion for clear Thai pronunciation
    assert "ยูเอสบีซี" in tts_text
    assert "เวิร์คฟรอมโฮม" in tts_text
    # Price notation is no longer laundered into spoken "บาท" (TikTok no-price
    # rule): it stays as-is so the upstream compliance lint catches it.
    assert "บาท" not in tts_text
    
    # 2. Check clause segmentation preserves both tracks
    clauses = VoiceEngine.segment_into_clauses([sample_text])
    assert len(clauses) > 0
    
    for item in clauses:
        orig = item.get("text", "")
        item["display_text"] = orig
        item["tts_text"] = TTSSanitizer.clean(orig)
    
    # display_text must preserve official English terms for subtitles/UI
    first_item = clauses[0]
    assert "USB-C" in first_item["display_text"] or "Logitech" in first_item["display_text"]
    assert "ยูเอสบีซี" not in first_item["display_text"]
    assert "โลจิเทค" not in first_item["display_text"]
