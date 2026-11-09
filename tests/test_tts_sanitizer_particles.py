"""Thai particle rewriting must never break real words (audit S2-03, S2-06, S2-14, S2-16, S2-21).

Pure text, offline, no files.
"""

import pytest

from scripts.couple_script_generator import enforce_speaker_persona
from scripts.script_rules import THAI_TECH_REPLACEMENTS, sanitize_text_for_rules
from scripts.tts_sanitizer import OFFICIAL_ENGLISH_MAP, TTSSanitizer

REAL_WORDS = ["คะแนน", "จ้าง", "หน้าจอ", "บังคับ", "คับแคบ", "ข้างหน้า", "เจ้าของ", "แสงจ้า"]
SENTENCE = "หน้าจอใหญ่ คะแนนเต็มสิบ จ้างช่างได้ บังคับใช้ ห้องคับแคบ ข้างหน้า เจ้าของ แสงจ้า"


# --- S2-03: male-tone particles only at clause end -------------------------

@pytest.mark.parametrize("word", REAL_WORDS)
def test_real_words_survive_display_and_tts(word):
    assert word in TTSSanitizer.clean_display_text(SENTENCE)
    assert word in TTSSanitizer.clean(SENTENCE)


def test_audit_repro_sentence_is_untouched():
    text = "หน้าจอใหญ่ คะแนนเต็มสิบ จ้างช่างได้"
    assert TTSSanitizer.clean_display_text(text) == text
    assert TTSSanitizer.clean(text) == text
    assert "ครับแนน" not in TTSSanitizer.clean(text)
    assert "หนะจอ" not in TTSSanitizer.clean(text)


@pytest.mark.parametrize("raw, expected", [
    ("ดีมากค่ะ", "ดีมากครับ"),
    ("ใช่ไหมคะ", "ใช่ไหมครับ"),
    ("ดีไหมคะ?", "ดีไหมครับ?"),
    ("ลองดูนะคะ แล้วจะรู้", "ลองดูนะครับ แล้วจะรู้"),
    ("ได้เลยจ้า", "ได้เลยครับ"),
    ("ไปกันน้า!", "ไปกันนะ!"),
    ("มีอะไรบ้างคะ", "มีอะไรบ้างครับ"),
])
def test_clause_final_particles_still_become_male(raw, expected):
    assert TTSSanitizer.enforce_male_tone(raw) == expected


# --- S2-16: a female voice is not forced to say ครับ ------------------------

def test_female_voice_keeps_female_particles():
    text = "ดีมากค่ะ ใช่ไหมคะ ดีจ้า"
    assert TTSSanitizer.clean(text, gender="female") == text
    assert "ครับ" in TTSSanitizer.clean(text)            # default (male) unchanged
    assert "ครับ" in TTSSanitizer.clean(text, gender="male")


# --- S2-06: 5G / 4G are not grams -------------------------------------------

def test_network_generation_is_not_grams():
    out = TTSSanitizer.clean("รองรับ 5G และ 4G")
    assert "กรัม" not in out
    assert "ไฟว์จี" in out and "โฟร์จี" in out


@pytest.mark.parametrize("raw, spoken", [
    ("หนัก 5g", "5 กรัม"),
    ("ชาร์จ 66W", "66 วัตต์"),
    ("ชาร์จ 66w", "66 วัตต์"),
    ("แบต 5000mAh", "5000 มิลลิแอมป์"),
    ("ซีพียู 2GHz", "2 กิกะเฮิรตซ์"),
])
def test_units_still_expand(raw, spoken):
    assert spoken in TTSSanitizer.clean(raw)


# --- S2-14: Nui persona guard keeps บังคับ / คับแคบ --------------------------

@pytest.mark.parametrize("fn", [
    lambda t: sanitize_text_for_rules(t, speaker="nui"),
    lambda t: enforce_speaker_persona(t, "nui"),
])
def test_nui_guard_keeps_real_words(fn):
    out = fn("บังคับให้ใช้ ห้องคับแคบ ดีมากเลยนะครับ ได้คับ")
    assert "บังคับ" in out
    assert "คับแคบ" in out
    assert "บังนะพี่บ่าว" not in out and "นะพี่บ่าวแคบ" not in out
    assert "ดีมากเลยนะพี่บ่าว" in out and "ได้นะพี่บ่าว" in out
    assert "ครับ" not in out


# --- S2-21: one Thai->English map ------------------------------------------

def test_lint_map_values_come_from_the_canonical_map():
    plain = {thai: eng for thai, eng in OFFICIAL_ENGLISH_MAP if not thai.startswith("(?")}
    assert set(THAI_TECH_REPLACEMENTS) == {"บลูทูธ", "ไทป์ซี", "ฟาสต์ชาร์จ", "ไวร์เลส", "ยูเอสบี", "พีดี"}
    for thai, eng in THAI_TECH_REPLACEMENTS.items():
        assert plain[thai] == eng


def test_couple_repair_uses_the_full_canonical_map():
    # The old 6-entry map turned ยูเอสบีซี into "USBซี".
    out = sanitize_text_for_rules("สาย ยูเอสบีซี กับ บลูทูธ ไวร์เลส", speaker="bao")
    assert out == "สาย USB-C กับ Bluetooth Wireless"
