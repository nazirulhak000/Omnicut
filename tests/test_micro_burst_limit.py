"""
M8: subtitle bursts are capped at 24 characters (was 34).

subtitle_kinetic_rules.md asks for 16-24 characters / 2-4 words per burst; the
code allowed 34. Only where a clause breaks changes: Thai is still cut at
PyThaiNLP word boundaries (so vowels and tone marks stay with their consonant),
and the English line still pairs one-to-one with its Thai burst.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scripts.translator as translator  # noqa: E402
from scripts.subtitle_engine import MICRO_BURST_MAX_CHARS, SubtitleEngine  # noqa: E402

THAI_COMBINING_START = re.compile("^[ัิ-ฺ็-๎]")
LEADING_VOWELS = "เแโใไ"

SENTENCES = [
    "ใครที่ปวดข้อมือตอนพิมพ์งานทั้งวัน ลองดูตัวนี้ก่อนนะ",
    "สายชาร์จแม่เหล็กแรงดูดสูงงานดีมาก จริงๆ",
    "ชาร์จเร็ว 66W ได้ในไม่กี่นาที แถมพกพาง่ายมากเลย",
    "เมาส์ตัวนี้เสียงเงียบมากครับ ใช้ในออฟฟิศได้สบายๆ ไม่รบกวนใคร",
    "พิกัดอยู่ในตะกร้าด้านซ้ายล่างเลยนะครับ",
    "ทุกคน ใครเคยเจอปัญหาแบตหมดไวบ้าง",
    "ชิปประมวลผลรุ่นใหม่แรงกว่าเดิมสองเท่าแถมประหยัดไฟกว่าเยอะ",
    "พัดลมตัวเล็กแต่ลมแรงมากจนผมปลิวเลยทีเดียวเชียว",
]


@pytest.fixture
def recorded_translations(monkeypatch):
    """Offline translator that echoes which Thai clause each English line is for."""
    calls = []

    def fake(cls, phrases, custom_dict=None):
        calls.extend(phrases)
        return [f"EN<{p}>" for p in phrases]

    monkeypatch.setattr(translator.SubtitleTranslator, "translate_batch", classmethod(fake))
    return calls


def _cues(translation=""):
    return [
        {"id": i + 1, "start": float(i * 3), "end": float(i * 3 + 3), "text": text, "translation": translation, "sfx": None}
        for i, text in enumerate(SENTENCES)
    ]


def test_burst_cap_is_the_top_of_the_documented_16_to_24_range():
    assert MICRO_BURST_MAX_CHARS == 24


def test_every_burst_is_at_most_24_characters_on_one_line(recorded_translations):
    bursts = SubtitleEngine.generate_micro_cues(_cues())
    assert len(bursts) > len(SENTENCES), "long sentences must be split"
    for cue in bursts:
        assert len(cue["text"]) <= MICRO_BURST_MAX_CHARS, cue["text"]
        assert "\n" not in cue["text"]


def test_thai_is_cut_only_at_word_boundaries(recorded_translations):
    bursts = SubtitleEngine.generate_micro_cues(_cues())
    for cue in bursts:
        text = cue["text"]
        assert text and not THAI_COMBINING_START.match(text), f"starts on a combining mark: {text!r}"
        assert text.rstrip()[-1] not in LEADING_VOWELS, f"ends on a leading vowel: {text!r}"
    # No Thai character is lost or duplicated by the split.
    joined = "".join(c["text"] for c in bursts).replace(" ", "")
    assert joined == "".join(SENTENCES).replace(" ", "")


def test_a_trailing_particle_neither_overflows_nor_stands_alone(recorded_translations):
    clauses = SubtitleEngine.split_into_smart_clauses(
        "เมาส์ตัวนี้เสียงเงียบมากครับ", max_line_len=MICRO_BURST_MAX_CHARS
    )
    assert all(len(c) <= MICRO_BURST_MAX_CHARS for c in clauses), clauses
    assert "ครับ" not in clauses, "the particle must keep the word before it"
    assert clauses[-1].endswith("ครับ")


def test_english_stays_paired_with_its_own_thai_burst(recorded_translations):
    # One sentence-level English line with no comma to split on: it used to be
    # pinned on burst 1 while the rest were translated separately, so the whole
    # sentence sat under the first clause.
    bursts = SubtitleEngine.generate_micro_cues(
        _cues(translation="Check this one out before you buy anything")
    )
    for cue in bursts:
        assert cue["translation"] == f"EN<{cue['text']}>", (cue["text"], cue["translation"])


def test_matching_clause_count_still_uses_the_authored_translation(recorded_translations):
    cue = {
        "id": 1, "start": 0.0, "end": 3.0, "sfx": None,
        "text": "ใครที่ปวดข้อมือตอนพิมพ์งานทั้งวัน ลองดูตัวนี้ก่อนนะ",
    }
    n = len(SubtitleEngine.split_into_smart_clauses(cue["text"], max_line_len=MICRO_BURST_MAX_CHARS))
    cue["translation"] = ", ".join(f"part {i}" for i in range(n))
    bursts = SubtitleEngine.generate_micro_cues([cue])
    assert [b["translation"] for b in bursts] == [f"part {i}" for i in range(n)]
    assert recorded_translations == []


def test_scaled_up_captions_are_still_bounded_by_their_line_width(recorded_translations):
    # 2.4x caption: a line holds ~26 characters, so the width bound (not the
    # 24-char cap) is the tighter one only when it is below 24.
    bursts = SubtitleEngine.generate_micro_cues(_cues(), max_line_len=18)
    assert all(len(c["text"]) <= 18 + 4 for c in bursts)
