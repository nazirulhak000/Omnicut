"""Pytest collection guard for manual rendering and external-service scripts.

The ignored modules are runnable diagnostics kept in ``tests/`` for historical
reasons.  They execute work at import time, so collecting them can render media
or call an external API before pytest starts the automated test suite.
"""
import pytest

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


@pytest.fixture(autouse=True)
def _no_real_api_key_gate(monkeypatch):
    """Every test starts from a known state: no OMNICUT_API_KEY configured.

    Without this, whatever a developer's real .env happens to set leaks into
    every TestClient request across the whole suite -- scripts/auth.py's
    middleware would then 401 every call that doesn't carry X-API-Key,
    which almost none of the ~19 files with their own `client` fixture do.
    tests/test_api_auth.py already had this exact fixture, file-scoped; this
    promotes the same isolation to the whole suite so passing locally never
    depends on whether OMNICUT_API_KEY happens to be unset in .env.
    """
    monkeypatch.delenv("OMNICUT_API_KEY", raising=False)
