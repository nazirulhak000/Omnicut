"""
Regression tests for SubtitleEngine.split_into_smart_clauses's Thai-tokenization
guard (SAAS_READINESS_PLAN.md section 11d).

Bug: tokenization via PyThaiNLP only triggered when the whole line had zero
spaces (`len(raw_parts) <= 1`). A line with exactly one incidental space could
still contain an over-length Thai run with no further splitting, overflowing
the 1080px frame. The fix tokenizes any individual part that exceeds
`max_line_len`, regardless of how many spaces the surrounding line has.
"""

import builtins

import pytest

from scripts.subtitle_engine import SubtitleEngine


# The exact repro string from the bug report: exactly one space, and the
# first space-delimited part alone is far longer than max_line_len (34).
ONE_SPACE_LONG_THAI = "สายชาร์จแม่เหล็กแรงดูดสูงงานดีมาก จริงๆ"


def test_one_incidental_space_still_triggers_tokenization():
    """The line has exactly 2 raw_parts (1 space) -- old guard (`len(raw_parts)
    <= 1`) would never tokenize this, letting the long first part overflow.
    The bug-report string's first part is 33 chars; use max_line_len=32 so the
    same guard condition (`part longer than max_line_len`) reproduces exactly
    the scenario described (a part that must be split but wasn't)."""
    raw_parts = [p for p in ONE_SPACE_LONG_THAI.split(" ") if p]
    assert len(raw_parts) == 2
    assert len(raw_parts[0]) > 32  # the part that must be split

    lines = SubtitleEngine.split_into_smart_clauses(ONE_SPACE_LONG_THAI, max_line_len=32)

    assert len(lines) >= 1
    for line in lines:
        assert len(line) <= 32, f"line exceeds max_line_len(32): {len(line)} chars -> {line!r}"

    # Nothing should have been silently dropped: every non-space character
    # from the original text must still be present across the output lines.
    original_chars = ONE_SPACE_LONG_THAI.replace(" ", "")
    joined_chars = "".join(lines).replace(" ", "")
    assert joined_chars == original_chars


def test_one_incidental_space_long_run_default_max_line_len():
    """Same shape of bug (exactly one space, first part far over the limit)
    but with a longer run so it reproduces under the real default
    max_line_len=34 used throughout the subtitle pipeline."""
    text = "สายชาร์จแม่เหล็กแรงดูดสูงงานดีมากจริงๆแนะนำสุดๆ จริงๆนะครับ"
    raw_parts = [p for p in text.split(" ") if p]
    assert len(raw_parts) == 2
    assert len(raw_parts[0]) > 34

    lines = SubtitleEngine.split_into_smart_clauses(text)  # default max_line_len=34

    assert len(lines) >= 1
    for line in lines:
        assert len(line) <= 34, f"line exceeds max_line_len(34): {len(line)} chars -> {line!r}"

    original_chars = text.replace(" ", "")
    joined_chars = "".join(lines).replace(" ", "")
    assert joined_chars == original_chars


def test_multiple_over_length_parts_each_get_split():
    """Two independent over-length Thai runs separated by one space -- both
    must be tokenized down to fit, not just the first."""
    part_a = "โปรโมชั่นพิเศษสุดๆสำหรับลูกค้าใหม่วันนี้เท่านั้น"  # long, no spaces
    part_b = "รีบสั่งซื้อก่อนของหมดภายในคืนนี้เท่านั้นนะครับผม"  # long, no spaces
    text = f"{part_a} {part_b}"
    assert len(part_a) > 34 and len(part_b) > 34

    lines = SubtitleEngine.split_into_smart_clauses(text, max_line_len=34)
    assert len(lines) >= 2
    for line in lines:
        assert len(line) <= 34, f"line exceeds max_line_len(34): {len(line)} chars -> {line!r}"


def test_short_parts_with_spaces_unaffected():
    """Parts that already fit must not be routed through tokenization at all
    -- pairing/merging behavior for normal short clauses stays the same."""
    text = "ลดกระหน่ำ ดีลลับ 1 แถม 1"
    lines = SubtitleEngine.split_into_smart_clauses(text, max_line_len=34)
    assert lines  # non-empty
    for line in lines:
        assert len(line) <= 34


def test_whole_line_no_spaces_still_tokenizes_as_before():
    """Original guard path (zero spaces) must keep working unchanged."""
    text = "สายชาร์จแม่เหล็กแรงดูดสูงงานดีมากจริงๆแนะนำเลยครับ"
    assert " " not in text
    assert len(text) > 34

    lines = SubtitleEngine.split_into_smart_clauses(text, max_line_len=34)
    assert len(lines) >= 1
    for line in lines:
        assert len(line) <= 34


def test_pythainlp_unavailable_falls_back_without_crashing(monkeypatch):
    """If PyThaiNLP can't be imported, the over-length part is returned
    unchanged (best-effort, no crash) rather than raising."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pythainlp.tokenize" or name.startswith("pythainlp"):
            raise ImportError("simulated missing pythainlp")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    lines = SubtitleEngine.split_into_smart_clauses(ONE_SPACE_LONG_THAI, max_line_len=34)
    # No exception raised; the over-length part passes through as-is since
    # there's no tokenizer available to split it further.
    assert lines
    original_chars = ONE_SPACE_LONG_THAI.replace(" ", "")
    joined_chars = "".join(lines).replace(" ", "")
    assert joined_chars == original_chars


def test_tokenizer_exception_falls_back_without_crashing(monkeypatch):
    """If word_tokenize itself raises (e.g. corrupt dictionary data), the
    over-length part is returned unchanged rather than propagating."""
    import pythainlp.tokenize as pt_tokenize

    def raising_tokenize(*args, **kwargs):
        raise RuntimeError("simulated tokenizer failure")

    monkeypatch.setattr(pt_tokenize, "word_tokenize", raising_tokenize)

    lines = SubtitleEngine.split_into_smart_clauses(ONE_SPACE_LONG_THAI, max_line_len=34)
    assert lines
    original_chars = ONE_SPACE_LONG_THAI.replace(" ", "")
    joined_chars = "".join(lines).replace(" ", "")
    assert joined_chars == original_chars


def test_generate_micro_cues_preserves_explicit_editor_line_breaks(monkeypatch):
    """Newlines are layout, not separate timed bursts, in an editor cue."""
    from scripts.translator import SubtitleTranslator

    monkeypatch.setattr(
        SubtitleTranslator,
        "translate_batch",
        staticmethod(lambda texts: [""] * len(texts)),
    )
    cues = SubtitleEngine.generate_micro_cues([{
        "start": 0.0,
        "end": 2.0,
        "text": "บรรทัดหนึ่ง\nLINE TWO\nราคา 9,990 บาท",
        "auto_emoji": False,
    }])

    assert len(cues) == 1
    assert cues[0]["text"] == "บรรทัดหนึ่ง\nLINE TWO\nราคา 9,990 บาท"
    assert cues[0]["start"] == 0.0
    assert cues[0]["end"] == 2.0
