"""Pytest collection guard for manual rendering and external-service scripts.

The ignored modules are runnable diagnostics kept in ``tests/`` for historical
reasons.  They execute work at import time, so collecting them can render media
or call an external API before pytest starts the automated test suite.
"""

collect_ignore = [
    "test_all_thai_fonts.py",
    "test_all_vowels.py",
    "test_bilingual_ass.py",
    "test_bilingual_subtitles.py",
    "test_clause_segmenter.py",
    "test_clean_trans.py",
    "test_drawtext.py",
    "test_fixed_thai_fonts.py",
    "test_full_vision_render.py",
    "test_gemini_vision_match.py",
    "test_noto.py",
    "test_perfect_sync_voice.py",
    "test_pillow_thai.py",
    "test_script_lab_ai.py",
    "test_thai_chunking.py",
    "test_translator_script.py",
    "test_unicode_thai.py",
    "test_voice_pacing.py",
    "test_vowel_rendering.py",
]
