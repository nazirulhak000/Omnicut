# -*- coding: utf-8 -*-
"""
Per-word reveal timing for Progressive Ghost Reveal captions.

SOP Phase 3 (`_Docs/GADGET_VIDEO_PRODUCTION_SOP.md`) asks each word of a caption
to light up as it is spoken: words already said stay white, the word being said
pops to neon green at 114%, and words not yet said are held fully transparent so
the line never shifts sideways.

That needs a (start, end) per *word*, which the pipeline does not have. The
default voice path (`gemini_tts`) produces no word timings at all, and the
edge-tts path only produces them as a best-effort bonus. So this module derives
word timings the same way `subtitle_engine._clause_boundaries_from_word_timings`
derives clause boundaries -- by walking character counts -- and uses real word
timings when the voice stage happens to have handed some down.

Spike C (`_Docs/Reports/SPIKE_C1_GHOST_REVEAL_FEASIBILITY_20260927.md`) measured
both inputs before this module existed: `\\fscx114\\fscy114` does not break Thai
stacked vowels or tone marks on the current libass, and edge-tts's WordBoundary
stream reassembles to the source text exactly.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from scripts.subtitle.word_layout import tokenize_text

# A word's share of the line is measured by how much ink it carries, not by how
# many code points it has: Thai stacks vowels and tone marks above and below the
# consonant, and those marks take no extra time to say. Counting them would make
# "เชื่อม" look nearly twice as long as "กลอง" and drag its highlight late.
_THAI_COMBINING_RANGES = (
    (0x0E31, 0x0E31),  # MAI HAN AKAT
    (0x0E34, 0x0E3A),  # upper/lower vowels, PHINTHU
    (0x0E47, 0x0E4E),  # tone marks, THANTHAKHAT, NIKHAHIT
)

# Below this, a word is too short to read even if it were spoken instantly.
MIN_WORD_DUR = 0.06


def _is_combining(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _THAI_COMBINING_RANGES)


def spoken_weight(word: str) -> float:
    """
    How long `word` should take to say, relative to other words on its line.

    Combining marks carry no weight of their own, and whitespace carries a small
    one so a natural pause between phrases does not collapse to nothing.
    """
    weight = 0.0
    for ch in word:
        if ch.isspace():
            weight += 0.3
        elif _is_combining(ch):
            continue
        else:
            weight += 1.0
    return weight


def _proportional_spans(
    words: Sequence[str], start: float, end: float
) -> List[Tuple[float, float]]:
    """Split `start`..`end` across `words` by spoken weight."""
    total = sum(spoken_weight(w) for w in words)
    span = max(0.0, end - start)
    if total <= 0 or span <= 0:
        # Degenerate line (all marks, or a zero-length cue): hand every word the
        # same instant so the caller still gets one entry per word.
        return [(start, end) for _ in words]

    out: List[Tuple[float, float]] = []
    cursor = start
    for i, w in enumerate(words):
        if i == len(words) - 1:
            w_end = end
        else:
            w_end = cursor + (spoken_weight(w) / total) * span
        out.append((cursor, max(cursor, w_end)))
        cursor = w_end
    return out


def _spans_from_real_timings(
    words: Sequence[str], timings: Sequence[Dict], start: float, end: float
) -> Optional[List[Tuple[float, float]]]:
    """
    Map TTS word timings onto our own tokenization.

    The two never agree on where words break -- edge-tts splits "วันนี้" into
    "วัน"+"นี้" while pythainlp keeps it whole -- so we walk both streams by
    cumulative character position, the same divergence-tolerant trick
    `_clause_boundaries_from_word_timings` uses. Returns `None` when the streams
    describe too different a string to trust a shared cursor.
    """
    if not timings:
        return None
    our_chars = sum(len(w) for w in words)
    tts_chars = sum(len(t.get("text", "")) for t in timings)
    if our_chars == 0 or tts_chars == 0:
        return None
    if not (0.6 <= tts_chars / our_chars <= 1.6):
        return None

    spans: List[Tuple[float, float]] = []
    cursor_chars = 0
    prev_end = start
    for i, w in enumerate(words):
        cursor_chars += len(w)
        target = (cursor_chars / our_chars) * tts_chars
        running = 0
        w_end = timings[-1].get("end", end)
        for t in timings:
            running += len(t.get("text", ""))
            if running >= target:
                w_end = t.get("end", end)
                break
        w_start = prev_end if i > 0 else start
        w_end = max(w_start, min(end, float(w_end)))
        spans.append((w_start, w_end))
        prev_end = w_end

    if spans:
        spans[0] = (start, spans[0][1])
        spans[-1] = (spans[-1][0], end)
    return spans


def build_word_reveal(
    text: str,
    start: float,
    end: float,
    word_timings: Optional[Sequence[Dict]] = None,
) -> List[Dict]:
    """
    Split `text` into words with a (start, end) each, covering `start`..`end`.

    Uses `word_timings` (from the voice stage) when they line up with this text;
    otherwise falls back to splitting the cue's own duration by spoken weight.
    Tokenization comes from `word_layout.tokenize_text`, the same one the caption
    layout uses, so a word's timing box and its pixel box always agree -- and it
    already glues stray Thai combining marks back onto their base, which is what
    keeps vowels from being revealed a beat before the consonant they sit on.

    Returns `[{"text", "start", "end"}, ...]`; empty when there is nothing to say.
    """
    if not text or not text.strip():
        return []
    if end < start:
        start, end = end, start

    words = [w for w in tokenize_text(text) if w.strip()]
    if not words:
        return []

    spans = _spans_from_real_timings(words, word_timings or [], start, end)
    if spans is None:
        spans = _proportional_spans(words, start, end)

    reveal: List[Dict] = []
    for w, (w_start, w_end) in zip(words, spans):
        # Stretch a too-brief word to something readable, but never past the
        # cue's own end -- a word still lit after the caption leaves would bleed
        # onto the next shot. On a cue too short for its word count the minimum
        # is simply unreachable, and the cue boundary wins.
        w_end = min(end, max(w_start + MIN_WORD_DUR, w_end))
        reveal.append({
            "text": w,
            "start": round(w_start, 3),
            "end": round(max(w_start, w_end), 3),
        })

    # The last word owns the tail of the cue: the line stays fully white until
    # the caption leaves, which is the "settle" the SOP asks for.
    if reveal:
        reveal[-1]["end"] = round(max(reveal[-1]["start"], end), 3)
    return reveal


def reveal_is_usable(reveal: Sequence[Dict]) -> bool:
    """
    Whether a reveal track is worth rendering word-by-word.

    A single word has nothing to reveal progressively, and a track whose spans do
    not advance would just flash the whole line at once -- in both cases the
    plain whole-line caption is the better render.
    """
    if len(reveal) < 2:
        return False
    return any(r["end"] > r["start"] for r in reveal)
