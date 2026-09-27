# -*- coding: utf-8 -*-
"""
ASS text for Progressive Ghost Reveal captions (SOP Phase 3).

libass has no per-word colour clock. ASS karaoke tags (`\\k`) only sweep the
line's *primary* colour on a fixed schedule and cannot scale a single word, so
the reveal is built the way `tools/render_sample_gadget_clip.py` proved out: one
Dialogue event per word, each holding the whole line, with the words drawn in
three states.

    already spoken   white               #FFFFFF
    being spoken     neon green at 114%  #66FF00, \\fscx114\\fscy114
    not yet spoken   fully transparent   \\alpha&HFF&

The unspoken words are *drawn* rather than omitted, so the line always holds the
same text. That alone is not enough: a transparent word contributes no ink, and
libass centres a line on the width it actually paints, so a centred reveal still
slides left as its ghosts thin out -- measured at 212px of drift before this was
fixed. The line is therefore pinned with `\\pos` and drawn from its left edge
(`\\an4`/`\\an7`), with the left edge computed once from the full line's width so
it cannot move between events.

Spike C (`_Docs/Reports/SPIKE_C1_GHOST_REVEAL_FEASIBILITY_20260927.md`) confirmed
`\\fscx114\\fscy114` leaves Thai stacked vowels and tone marks intact on the
current libass, contradicting the older warning at `subtitle_engine.py`'s
`caption_anim`. If that ever regresses, `ACTIVE_SCALE_PCT = 100` disables the pop
without touching anything else.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from scripts.subtitle.badge_plate_renderer import ass_colour
from scripts.subtitle.word_layout import layout_line

# SOP Phase 3 colours. Written as hex here and converted, rather than spelled in
# ASS's &HBBGGRR& byte order, so they stay readable against the SOP and cannot
# drift from the rest of the engine's colour handling.
SPOKEN_HEX = "#FFFFFF"   # already spoken
ACTIVE_HEX = "#66FF00"   # being spoken -- neon green

SPOKEN_COLOUR = f"{ass_colour(SPOKEN_HEX)}&"
ACTIVE_COLOUR = f"{ass_colour(ACTIVE_HEX)}&"
GHOST_ALPHA = "&HFF&"    # fully transparent

# How much the word being spoken grows. 100 disables the pop.
ACTIVE_SCALE_PCT = 114


def _ass_time(t: float) -> str:
    """ASS timestamps are H:MM:SS.cc, centiseconds, single-digit hour."""
    t = max(0.0, float(t))
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _state_tags(state: str) -> str:
    if state == "spoken":
        return f"{{\\c{SPOKEN_COLOUR}\\alpha&H00&\\fscx100\\fscy100}}"
    if state == "active":
        scale = ""
        if ACTIVE_SCALE_PCT != 100:
            scale = f"\\fscx{ACTIVE_SCALE_PCT}\\fscy{ACTIVE_SCALE_PCT}"
        return f"{{\\c{ACTIVE_COLOUR}\\alpha&H00&{scale}}}"
    # ghost: still drawn, so it holds its width and the line cannot reflow.
    return f"{{\\alpha{GHOST_ALPHA}}}"


def build_reveal_line(words: Sequence[str], active_idx: int) -> str:
    """
    The whole line as ASS text, with word `active_idx` lit.

    Words are concatenated with no separator: `word_layout.tokenize_text` keeps
    whitespace as its own token, so the spacing already in `words` is the
    spacing the line should have. Joining with a space here would wedge gaps
    into Thai, which does not write them.
    """
    parts: List[str] = []
    for i, w in enumerate(words):
        if i < active_idx:
            state = "spoken"
        elif i == active_idx:
            state = "active"
        else:
            state = "ghost"
        parts.append(f"{_state_tags(state)}{w}")
    return "".join(parts)


def build_settle_line(words: Sequence[str]) -> str:
    """Every word white -- the hold after the last word is spoken."""
    return f"{_state_tags('spoken')}{''.join(words)}"


def anchor_tags(
    text: str,
    font_name: str,
    font_size_px: float,
    centre_x: float,
    baseline_y: float,
    video_w: int = 1080,
    vertical_align: int = 4,
) -> str:
    """
    `\\pos` + `\\an` tags that pin the line's left edge for the whole reveal.

    The left edge is derived from the *complete* line's measured width, so it is
    the same for every event no matter how many words are currently transparent.
    Without this the line drifts as its ghosts stop contributing ink.

    `vertical_align` is an ASS left-column alignment: 4 centres the line on
    `baseline_y`, 7 hangs it below, 1 sits it above.
    """
    layout = layout_line(text, font_name, font_size_px, norm_x=0.5, video_w=video_w)
    width = float(layout.get("abs_line_width") or 0.0)
    left_x = centre_x - (width / 2.0)
    return f"{{\\an{vertical_align}\\pos({left_x:.1f},{baseline_y:.1f})}}"


def build_ghost_reveal_events(
    reveal: Sequence[Dict],
    cue_end: float,
    style: str = "TikTokWhite",
    layer: int = 1,
    prefix_tags: str = "",
) -> List[str]:
    """
    Dialogue lines rendering `reveal` as a progressive ghost reveal.

    `reveal` is what `word_reveal.build_word_reveal` returns: one
    `{"text", "start", "end"}` per word, in order, spanning the cue. Emits one
    event per word plus a final settle event holding the finished line in white
    until `cue_end`, so the viewer can still read it after the voice moves on.

    `prefix_tags` leads every event's text. Pass `anchor_tags(...)` here: without
    a `\\pos` anchor the line slides sideways as its ghosts stop painting ink.
    """
    if not reveal:
        return []

    words = [r["text"] for r in reveal]
    events: List[str] = []

    for i, r in enumerate(reveal):
        start, end = float(r["start"]), float(r["end"])
        if end <= start:
            # A zero-width span would be a Dialogue libass drops; letting it
            # through would make that word never light up at all.
            continue
        text = build_reveal_line(words, i)
        events.append(
            f"Dialogue: {layer},{_ass_time(start)},{_ass_time(end)},{style},,0,0,0,,{prefix_tags}{text}"
        )

    last_end = float(reveal[-1]["end"])
    if cue_end > last_end:
        events.append(
            f"Dialogue: {layer},{_ass_time(last_end)},{_ass_time(cue_end)},{style},,0,0,0,,"
            f"{prefix_tags}{build_settle_line(words)}"
        )

    return events
