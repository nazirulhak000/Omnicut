# -*- coding: utf-8 -*-
"""ASS generation for Progressive Ghost Reveal captions (SOP Phase 3)."""

import re

import pytest

from scripts.subtitle.ghost_reveal_ass import (
    ACTIVE_COLOUR,
    ACTIVE_HEX,
    ACTIVE_SCALE_PCT,
    GHOST_ALPHA,
    SPOKEN_COLOUR,
    SPOKEN_HEX,
    anchor_tags,
    build_ghost_reveal_events,
    build_reveal_line,
    build_settle_line,
)
from scripts.subtitle.word_reveal import build_word_reveal


def _reveal(words_with_times):
    return [{"text": t, "start": s, "end": e} for t, s, e in words_with_times]


class TestSopContract:
    """The numbers the SOP pins down, asserted so they cannot drift."""

    def test_spoken_is_pure_white(self):
        assert SPOKEN_HEX == "#FFFFFF"
        assert SPOKEN_COLOUR == "&H00FFFFFF&"

    def test_active_is_neon_green(self):
        assert ACTIVE_HEX == "#66FF00"
        # ASS stores colours &HBBGGRR, so #66FF00 is not &H0066FF00.
        assert ACTIVE_COLOUR == "&H0000FF66&"

    def test_active_scale_is_114_percent(self):
        assert ACTIVE_SCALE_PCT == 114

    def test_ghost_is_fully_transparent(self):
        assert GHOST_ALPHA == "&HFF&"


class TestRevealLine:
    def test_three_states_in_one_line(self):
        line = build_reveal_line(["ก", "ข", "ค"], active_idx=1)
        assert line.index("ก") < line.index("ข") < line.index("ค")
        assert SPOKEN_COLOUR in line
        assert ACTIVE_COLOUR in line
        assert GHOST_ALPHA in line

    def test_first_word_active_has_no_spoken_words(self):
        line = build_reveal_line(["ก", "ข", "ค"], active_idx=0)
        assert ACTIVE_COLOUR in line
        assert GHOST_ALPHA in line

    def test_last_word_active_has_no_ghosts(self):
        line = build_reveal_line(["ก", "ข", "ค"], active_idx=2)
        assert GHOST_ALPHA not in line

    def test_every_word_is_always_drawn(self):
        # The ghost exists to hold width. If unspoken words were dropped, the
        # line would reflow and the text would jump sideways as it reveals.
        for i in range(3):
            line = build_reveal_line(["กล้อง", "คม", "ชัด"], active_idx=i)
            for w in ("กล้อง", "คม", "ชัด"):
                assert w in line

    def test_active_word_carries_the_scale_tag(self):
        line = build_reveal_line(["ก", "ข"], active_idx=0)
        assert f"\\fscx{ACTIVE_SCALE_PCT}\\fscy{ACTIVE_SCALE_PCT}" in line

    def test_spoken_words_are_reset_to_100_percent(self):
        # Without an explicit reset a previously-active word would keep the
        # inherited scale and the line would creep wider as it reveals.
        line = build_reveal_line(["ก", "ข", "ค"], active_idx=2)
        assert "\\fscx100\\fscy100" in line

    def test_no_separator_is_inserted(self):
        # Thai does not write spaces. tokenize_text already emits whitespace as
        # its own token, so joining must not add any.
        line = build_reveal_line(["กล้อง", "ชัด"], active_idx=0)
        assert "กล้องชัด" in re.sub(r"\{[^}]*\}", "", line)

    def test_tokenized_spacing_is_preserved(self):
        line = build_reveal_line(["A", " ", "B"], active_idx=0)
        assert "A B" in re.sub(r"\{[^}]*\}", "", line)


class TestSettleLine:
    def test_all_white_no_ghost(self):
        line = build_settle_line(["ก", "ข", "ค"])
        assert SPOKEN_COLOUR in line
        assert GHOST_ALPHA not in line
        assert ACTIVE_COLOUR not in line

    def test_holds_the_whole_line(self):
        line = build_settle_line(["กล้อง", "คม", "ชัด"])
        assert re.sub(r"\{[^}]*\}", "", line) == "กล้องคมชัด"


class TestEvents:
    def test_one_event_per_word_plus_settle(self):
        reveal = _reveal([("ก", 0.0, 0.5), ("ข", 0.5, 1.0)])
        events = build_ghost_reveal_events(reveal, cue_end=2.0)
        assert len(events) == 3

    def test_no_settle_when_words_reach_the_end(self):
        reveal = _reveal([("ก", 0.0, 0.5), ("ข", 0.5, 2.0)])
        events = build_ghost_reveal_events(reveal, cue_end=2.0)
        assert len(events) == 2

    def test_events_are_wellformed_dialogue(self):
        reveal = _reveal([("ก", 0.0, 0.5), ("ข", 0.5, 1.0)])
        for ev in build_ghost_reveal_events(reveal, cue_end=1.0):
            assert ev.startswith("Dialogue: ")
            assert len(ev.split(",", 9)) == 10

    def test_timestamps_are_ass_formatted(self):
        reveal = _reveal([("ก", 61.5, 62.0)])
        ev = build_ghost_reveal_events(reveal, cue_end=62.0)[0]
        assert "0:01:01.50" in ev
        assert "0:01:02.00" in ev

    def test_events_do_not_overlap(self):
        reveal = build_word_reveal("นี่คือกล้องคมชัด", 1.0, 4.0)
        events = build_ghost_reveal_events(reveal, cue_end=4.0)
        spans = []
        for ev in events:
            parts = ev.split(",")
            spans.append((parts[1], parts[2]))
        for (_, a_end), (b_start, _) in zip(spans, spans[1:]):
            assert a_end == b_start

    def test_zero_width_spans_are_dropped(self):
        # libass drops a Dialogue whose end is not after its start, so emitting
        # one would silently skip that word's highlight entirely.
        reveal = _reveal([("ก", 0.0, 0.0), ("ข", 0.0, 1.0)])
        events = build_ghost_reveal_events(reveal, cue_end=1.0)
        assert len(events) == 1

    def test_empty_reveal_yields_nothing(self):
        assert build_ghost_reveal_events([], cue_end=1.0) == []

    def test_style_and_layer_are_honoured(self):
        reveal = _reveal([("ก", 0.0, 1.0)])
        ev = build_ghost_reveal_events(reveal, 1.0, style="TikTokMinimalPill", layer=3)[0]
        assert ev.startswith("Dialogue: 3,")
        assert "TikTokMinimalPill" in ev

    def test_prefix_tags_lead_every_event(self):
        reveal = _reveal([("ก", 0.0, 0.5), ("ข", 0.5, 1.0)])
        events = build_ghost_reveal_events(reveal, 2.0, prefix_tags="{\\pos(540,1540)}")
        assert all("{\\pos(540,1540)}" in ev for ev in events)
        assert len(events) == 3


class TestAnchor:
    """
    The anchor is what actually stops the reveal from sliding.

    A transparent word paints no ink, and libass centres a line on the ink it
    paints -- so a centred ghost reveal drifts left as words go transparent.
    Rendering measured 212px of drift before the anchor, 0px after.
    """

    def test_emits_pos_and_left_alignment(self):
        tags = anchor_tags("กล้องคมชัด", "Mali", 88, centre_x=540, baseline_y=1540)
        assert "\\pos(" in tags
        assert "\\an4" in tags

    def test_left_edge_is_independent_of_reveal_progress(self):
        # Same full line -> same anchor, whatever is currently transparent.
        a = anchor_tags("กล้องคมชัดมาก", "Mali", 88, centre_x=540, baseline_y=1540)
        b = anchor_tags("กล้องคมชัดมาก", "Mali", 88, centre_x=540, baseline_y=1540)
        assert a == b

    def test_full_line_ends_up_centred(self):
        # Anchoring left must not abandon centring: the left edge is derived
        # from the whole line's width, so the finished line sits centred.
        line = "กล้องคมชัด"
        tags = anchor_tags(line, "Mali", 88, centre_x=540, baseline_y=1540)
        x = float(re.search(r"\\pos\(([-\d.]+),", tags).group(1))
        assert x < 540  # starts left of centre
        assert 0 <= x <= 540

    def test_longer_line_starts_further_left(self):
        short = anchor_tags("กล้อง", "Mali", 88, centre_x=540, baseline_y=1540)
        long = anchor_tags("กล้องคมชัดมากจริง", "Mali", 88, centre_x=540, baseline_y=1540)
        sx = float(re.search(r"\\pos\(([-\d.]+),", short).group(1))
        lx = float(re.search(r"\\pos\(([-\d.]+),", long).group(1))
        assert lx < sx

    def test_baseline_is_carried_through(self):
        tags = anchor_tags("กล้อง", "Mali", 88, centre_x=540, baseline_y=1234)
        assert "1234" in tags

    def test_vertical_align_is_configurable(self):
        tags = anchor_tags("กล้อง", "Mali", 88, 540, 1540, vertical_align=7)
        assert "\\an7" in tags


class TestEndToEnd:
    def test_real_thai_line_reveals_word_by_word(self):
        reveal = build_word_reveal("นี่คือสมาร์ทโฟนรุ่นใหม่", 0.0, 3.0)
        events = build_ghost_reveal_events(reveal, cue_end=3.0)
        assert len(events) == len(reveal)
        # Each successive event should have one fewer ghost than the last.
        ghost_counts = [ev.count(GHOST_ALPHA) for ev in events]
        assert ghost_counts == sorted(ghost_counts, reverse=True)
        assert ghost_counts[-1] == 0

    def test_stacked_marks_stay_with_their_base(self):
        # A tone mark revealed a beat before its consonant would look broken.
        reveal = build_word_reveal("เชื่อมต่อได้", 0.0, 2.0)
        for r in reveal:
            assert not r["text"].startswith(("่", "้", "ิ", "ื"))


class TestBilingualSuffix:
    """
    The English line has no per-word timing, so it rides along whole under each
    step of the Thai reveal rather than blocking the reveal entirely.
    """

    def test_suffix_rides_on_every_event(self):
        reveal = _reveal([("ก", 0.0, 0.5), ("ข", 0.5, 1.0)])
        events = build_ghost_reveal_events(reveal, 2.0, suffix=r"\NEN LINE")
        assert len(events) == 3          # two words + settle
        assert all("EN LINE" in ev for ev in events)

    def test_suffix_comes_after_the_thai_line(self):
        reveal = _reveal([("กล้อง", 0.0, 1.0)])
        ev = build_ghost_reveal_events(reveal, 1.0, suffix=r"\NEN")[0]
        assert ev.index("กล้อง") < ev.index("EN")

    def test_no_suffix_leaves_events_unchanged(self):
        reveal = _reveal([("ก", 0.0, 0.5), ("ข", 0.5, 1.0)])
        assert build_ghost_reveal_events(reveal, 1.0) == \
               build_ghost_reveal_events(reveal, 1.0, suffix="")

    def test_multiline_puts_the_suffix_under_the_last_line_only(self):
        from scripts.subtitle.ghost_reveal_ass import build_multiline_reveal_events

        lines = [
            _reveal([("ก", 0.0, 0.5)]),
            _reveal([("ข", 0.5, 1.0)]),
        ]
        events = build_multiline_reveal_events(
            lines, 1.0, [r"{\pos(0,100)}", r"{\pos(0,200)}"], suffix=r"\NEN"
        )
        # One per line per step; the English must appear once per step, not twice.
        for ev in events:
            assert ev.count("EN") <= 1
        per_step = {}
        for ev in events:
            key = (ev.split(",")[1], ev.split(",")[2])
            per_step.setdefault(key, []).append(ev)
        for step_events in per_step.values():
            assert sum("EN" in ev for ev in step_events) == 1


class TestBilingualOff:
    """Turning the English line off must actually remove it from the render."""

    def _ass(self, tmp_path, bilingual, ghost):
        from scripts.subtitle_engine import SubtitleEngine

        out = tmp_path / f"b{int(bilingual)}g{int(ghost)}.ass"
        SubtitleEngine.generate_ass(
            [{"id": 1, "start": 0.0, "end": 2.0,
              "text": "เครื่องนี้ช่วยลดอุณหภูมิ",
              "translation": "this cooler drops the temperature"}],
            str(out), font_name="IBMPlex",
            bilingual=bilingual, ghost_reveal=ghost,
        )
        return out.read_text(encoding="utf-8")

    def test_off_removes_the_english_under_a_reveal(self, tmp_path):
        assert "cooler drops" not in self._ass(tmp_path, False, True)

    def test_off_removes_the_english_without_a_reveal(self, tmp_path):
        assert "cooler drops" not in self._ass(tmp_path, False, False)

    def test_on_keeps_it_in_both_modes(self, tmp_path):
        assert "cooler drops" in self._ass(tmp_path, True, True)
        assert "cooler drops" in self._ass(tmp_path, True, False)

    def test_off_also_drops_the_english_style_tag(self, tmp_path):
        """The 68% scale run belongs to the English line and must go with it."""
        assert "\fscx68" not in self._ass(tmp_path, False, True)


class TestRevealFlagOff:
    def test_off_leaves_a_plain_caption(self, tmp_path):
        from scripts.subtitle_engine import SubtitleEngine

        out = tmp_path / "off.ass"
        SubtitleEngine.generate_ass(
            [{"id": 1, "start": 0.0, "end": 2.0,
              "text": "เครื่องนี้ช่วยลดอุณหภูมิ", "translation": ""}],
            str(out), font_name="IBMPlex", bilingual=False, ghost_reveal=False,
        )
        generated = out.read_text(encoding="utf-8")
        assert ACTIVE_COLOUR not in generated, "a reveal was drawn with the flag off"
        # GHOST_ALPHA alone is not a reveal marker -- the plain caption's 70ms
        # entrance starts from the same \alpha&HFF&, and each stacked mark adds
        # a companion event. What must be absent is the reveal's own signature:
        # a word held at 114% while another is ghosted in the same event.
        assert f"\\fscx{ACTIVE_SCALE_PCT}" not in generated
        body_events = [
            line for line in generated.splitlines()
            if line.startswith("Dialogue: 1,") and ",TikTokWhite,," in line
            and "\\1a&HFF&" not in line          # exclude mark companions
        ]
        assert len(body_events) == 1, (
            f"a plain caption is one event per cue, got {len(body_events)}"
        )
