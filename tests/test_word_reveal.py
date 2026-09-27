# -*- coding: utf-8 -*-
"""Word-level reveal timing for Progressive Ghost Reveal captions."""

import pytest

from scripts.subtitle.word_reveal import (
    MIN_WORD_DUR,
    build_word_reveal,
    reveal_is_usable,
    spoken_weight,
)


class TestSpokenWeight:
    def test_combining_marks_add_no_time(self):
        # "เชื่อม" carries a vowel and a tone mark that take no time to say.
        # Counting them would push the word's highlight late.
        assert spoken_weight("เชื่อม") == spoken_weight("เชอม")

    def test_tone_mark_free_of_charge(self):
        assert spoken_weight("นา") == spoken_weight("น้า")

    def test_plain_letters_count_one_each(self):
        assert spoken_weight("กลอง") == 4.0

    def test_space_counts_partially(self):
        assert spoken_weight("ก ข") == pytest.approx(2.3)

    def test_all_marks_weighs_nothing(self):
        assert spoken_weight("ิ้") == 0.0


class TestProportionalFallback:
    """No word timings from the voice stage -- the common case on gemini_tts."""

    def test_covers_the_whole_cue(self):
        r = build_word_reveal("กล้องคมชัดมาก", 2.0, 5.0)
        assert r
        assert r[0]["start"] == 2.0
        assert r[-1]["end"] == 5.0

    def test_words_advance_without_gaps_or_overlap(self):
        r = build_word_reveal("นี่คือสมาร์ทโฟนรุ่นใหม่", 0.0, 4.0)
        assert len(r) >= 2
        for a, b in zip(r, r[1:]):
            assert a["end"] == pytest.approx(b["start"], abs=1e-3)

    def test_longer_word_gets_more_time(self):
        r = build_word_reveal("ชิป ประมวลผล", 0.0, 6.0)
        by_text = {w["text"].strip(): w["end"] - w["start"] for w in r if w["text"].strip()}
        assert by_text["ประมวลผล"] > by_text["ชิป"]

    def test_stacked_marks_do_not_inflate_a_words_share(self):
        # Same letter count, but the second word stacks marks. Their durations
        # should stay close; the guard is that marks are not counted as speech.
        r = build_word_reveal("เชื่อม กลอง", 0.0, 4.0)
        durs = [w["end"] - w["start"] for w in r if w["text"].strip()]
        assert len(durs) == 2
        assert max(durs) / min(durs) < 1.6


class TestRealTimings:
    """edge-tts hands down WordBoundary offsets on its own tokenization."""

    def test_real_timings_drive_the_spans(self):
        timings = [
            {"text": "นี่", "start": 0.10, "end": 0.30},
            {"text": "คือ", "start": 0.30, "end": 0.55},
            {"text": "กล้อง", "start": 0.55, "end": 1.20},
        ]
        r = build_word_reveal("นี่คือกล้อง", 0.1, 1.2, timings)
        assert r[0]["start"] == pytest.approx(0.1)
        assert r[-1]["end"] == pytest.approx(1.2)
        # The middle boundary should land near the TTS one, not at the midpoint.
        assert 0.2 < r[0]["end"] < 0.6

    def test_divergent_tokenization_falls_back(self):
        # Timings describe a different sentence: the char-count ratio guard
        # should reject them rather than smear the reveal across wrong words.
        timings = [{"text": "ก" * 200, "start": 0.0, "end": 1.0}]
        r = build_word_reveal("สั้น", 0.0, 1.0, timings)
        assert r[0]["start"] == 0.0
        assert r[-1]["end"] == 1.0

    def test_empty_timings_fall_back_silently(self):
        r = build_word_reveal("กล้องคมชัด", 0.0, 2.0, [])
        assert r
        assert r[-1]["end"] == 2.0

    def test_spans_stay_inside_the_cue(self):
        # A TTS end past the cue's own end must be clamped, or the caption would
        # keep a word lit after the line is gone.
        timings = [
            {"text": "กล้อง", "start": 0.0, "end": 0.5},
            {"text": "ชัด", "start": 0.5, "end": 9.9},
        ]
        r = build_word_reveal("กล้องชัด", 0.0, 2.0, timings)
        assert all(w["end"] <= 2.0 + 1e-6 for w in r)


class TestEdgeCases:
    def test_empty_text(self):
        assert build_word_reveal("", 0.0, 2.0) == []
        assert build_word_reveal("   ", 0.0, 2.0) == []

    def test_reversed_bounds_are_normalised(self):
        r = build_word_reveal("กล้องชัด", 3.0, 1.0)
        assert r[0]["start"] == 1.0
        assert r[-1]["end"] == 3.0

    def test_zero_length_cue_still_yields_words(self):
        r = build_word_reveal("กล้องชัด", 2.0, 2.0)
        assert r
        assert all(w["start"] == 2.0 for w in r)

    def test_every_word_gets_a_readable_minimum(self):
        r = build_word_reveal("ก ข ค ง จ ฉ ช ซ", 0.0, 4.0)
        assert all(w["end"] - w["start"] >= MIN_WORD_DUR - 1e-6 for w in r)

    def test_cue_end_wins_over_the_minimum(self):
        # When the cue is far too short for its word count, the words cannot all
        # get MIN_WORD_DUR. The caption's own end must still win: a word lit
        # after the line is gone would bleed onto the next shot.
        r = build_word_reveal("ก ข ค ง จ ฉ ช ซ", 0.0, 0.2)
        assert r[-1]["end"] == 0.2
        assert all(w["end"] <= 0.2 + 1e-6 for w in r)


class TestUsability:
    def test_single_word_is_not_worth_revealing(self):
        assert not reveal_is_usable(build_word_reveal("กล้อง", 0.0, 1.0))

    def test_multi_word_line_is(self):
        assert reveal_is_usable(build_word_reveal("กล้องคมชัดมาก", 0.0, 3.0))

    def test_empty_track_is_not(self):
        assert not reveal_is_usable([])


class TestSplitByLines:
    """A wrapped caption has to hand its words back out across its lines."""

    def _track(self, *words):
        out, t = [], 0.0
        for w in words:
            out.append({"text": w, "start": t, "end": t + 0.5})
            t += 0.5
        return out

    def test_splits_on_the_line_boundary(self):
        from scripts.subtitle.word_reveal import split_reveal_by_lines

        track = self._track("กล้อง", "คมชัด", "แบต", "อึด")
        lines = split_reveal_by_lines(track, ["กล้องคมชัด", "แบตอึด"])
        assert lines is not None
        assert [w["text"] for w in lines[0]] == ["กล้อง", "คมชัด"]
        assert [w["text"] for w in lines[1]] == ["แบต", "อึด"]

    def test_keeps_every_word_and_its_timing(self):
        from scripts.subtitle.word_reveal import split_reveal_by_lines

        track = self._track("กล้อง", "คมชัด", "แบต", "อึด")
        lines = split_reveal_by_lines(track, ["กล้องคมชัด", "แบตอึด"])
        flat = [w for line in lines for w in line]
        assert flat == track

    def test_rejects_a_word_straddling_the_break(self):
        # The wrapper would have to cut inside "คมชัด" to make these lines, and
        # a reveal cannot light half a word -- better to fall back.
        from scripts.subtitle.word_reveal import split_reveal_by_lines

        track = self._track("กล้อง", "คมชัด")
        assert split_reveal_by_lines(track, ["กล้องคม", "ชัด"]) is None

    def test_rejects_text_that_does_not_match(self):
        from scripts.subtitle.word_reveal import split_reveal_by_lines

        track = self._track("กล้อง", "คมชัด")
        assert split_reveal_by_lines(track, ["อย่างอื่น", "ไปเลย"]) is None

    def test_single_line_round_trips(self):
        from scripts.subtitle.word_reveal import split_reveal_by_lines

        track = self._track("กล้อง", "คมชัด")
        lines = split_reveal_by_lines(track, ["กล้องคมชัด"])
        assert lines == [track]

    def test_empty_inputs(self):
        from scripts.subtitle.word_reveal import split_reveal_by_lines

        assert split_reveal_by_lines([], ["ก"]) is None
        assert split_reveal_by_lines(self._track("ก"), []) is None
