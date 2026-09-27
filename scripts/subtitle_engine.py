"""
TikTok Style Subtitle Generator (Advanced SubStation Alpha .ass)
Produces rapid-fire 2-3 word micro-burst subtitles with Kanit-Black font, emojis, and pop animation.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import FONTS_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from scripts.asset_registry import AssetRegistry
from scripts.hook_styles import resolve_hook_style
from scripts.overlay_model import (
    ACCENT_COLOR,
    ASS_ALIGNMENT,
    hook_overlay_from_legacy,
    resolve_look,
    text_overlay_from_legacy,
)

from scripts.subtitle import (
    TYPOGRAPHY_PRESETS_PATH,
    DEFAULT_FONT_FAMILY,
    _LEGACY_FONT_ALIASES,
    _load_font_family_map,
    _measure_text_width_px,
    prefix_advances,
    ass_glyph_scale,
    has_true_bold_face,
    ass_caption_face,
    THAI_STACKED_MARK_RAISE_EM,
    repair_thai_stacked_marks,
    _hook_line_width_px,
    DEFAULT_HOOK_MOTION,
    _resolve_hook_motion,
    _chained_keyframes,
    HOOK_IN_BUILDERS,
    HOOK_LOOP_BUILDERS,
    HOOK_OUT_BUILDERS,
    _in_bounce,
    _in_bounce_soft,
    _in_elastic_bounce,
    _in_pop,
    _in_pop_soft,
    _in_slam,
    _in_fade,
    _in_zoom,
    _in_slide_up,
    _in_blur,
    _in_none,
    _loop_pulse,
    _loop_wave,
    _loop_shake,
    _loop_flicker,
    _loop_none,
    _out_fade,
    _out_slide,
    _out_zoom,
    _out_glitch,
    _out_none,
    ass_colour,
    _pill_fill_to_ass,
    _ass_rounded_pill_path,
    _hook_lightsweep_event,
    _hook_accent_events,
    overlay_events,
    KINETIC_KEYWORDS,
    KINETIC_KEYWORDS_EN,
    ass_escape_text,
    wrap_text_for_ass,
    wrap_en_for_ass,
    apply_kinetic_highlighting,
    apply_kinetic_highlighting_en,
    apply_bilingual_kinetic_highlighting,
    _EN_STOPWORDS,
    _TH_PARTICLES,
    _salient_word_en,
    _salient_word_th,
    _force_highlight,
)
from scripts.subtitle.ghost_reveal_ass import (
    anchor_tags,
    build_ghost_reveal_events,
    build_multiline_reveal_events,
)
from scripts.subtitle.word_reveal import (
    build_word_reveal,
    reveal_is_usable,
    split_reveal_by_lines,
)

# Longest a micro-burst clause may be, in characters. This is the clause
# splitter's own historical default, kept here so the caller that now bounds it
# by the rendered line width cannot silently widen it: a line at the default
# font size fits ~62 characters, and filling that would turn rapid-fire bursts
# back into subtitle paragraphs.
#
# Note this is above the 16-24 that subtitle_kinetic_rules.md asks for. That
# gap predates the per-size bound added here and is left alone deliberately --
# narrowing it changes the pacing of every caption in every clip, which is a
# decision for the project owner, not a side effect of this change.
MICRO_BURST_MAX_CHARS = 34

# Emoji and pictographs, plus the variation selector and zero-width joiner that
# bind them into sequences. Captions are stripped of these: libass renders them
# through a fallback face (Segoe UI Emoji on Windows) whose advance width PIL
# cannot measure, so any layout computed ahead of the render -- the ghost
# reveal's anchor, the detached-tone companions -- lands off by the difference.
# Measured on a real render: a caption's anchor was 16px out with one emoji in
# the line, which put a tone mark over the wrong glyph. The SOP's caption spec
# does not call for emoji in the first place.
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # pictographs, symbols, transport, supplemental
    "←-⇿"           # arrows
    "⌀-⏿"           # technical (⌚, ⏰)
    "①-➿"           # enclosed alphanumerics, dingbats (❌, ✨)
    "⬀-⯿"           # extra symbols (⭐)
    "︀-️"           # variation selectors
    "‍"                  # zero-width joiner
    "]+"
)


def strip_caption_emoji(text: str) -> str:
    """Remove emoji from caption text and tidy the space they leave behind."""
    if not text:
        return text
    cleaned = _EMOJI_RE.sub("", str(text))
    # Collapse the gap an emoji leaves, without touching line breaks.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return "\n".join(line.strip() for line in cleaned.split("\n")).strip()

SUBTITLE_RENDER_CONTRACT_VERSION = "v8"
SUBTITLE_RENDER_CONTRACT_MARKER = (
    f"; OmniCutSubtitleContract: {SUBTITLE_RENDER_CONTRACT_VERSION}"
)


def subtitle_artifact_is_current(path: Path) -> bool:
    """Return whether an existing ASS file uses the current subtitle contract."""
    try:
        return SUBTITLE_RENDER_CONTRACT_MARKER in path.read_text(
            encoding="utf-8", errors="replace"
        )[:4096]
    except (OSError, TypeError, ValueError):
        return False


LINE_HEIGHT_FACTOR = 1.0

# Permanent copyright watermark -- burned into every rendered clip, always
# on, not part of the user's editable overlay list (unlike kind="text"/
# "hook" overlays above, which live in the project manifest and can be
# moved/deleted from the editor). Runs vertically in the right-edge "safe
# zone" column the editor's preview already reserves for TikTok's own
# like/comment/share buttons (see SequencePlayer.jsx's showSafeZone guide,
# right column: 11.1% width, vertical span ~9.4%-78.1% of frame height) so
# it never covers the clip itself.
WATERMARK_TEXT = "สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง"
WATERMARK_X_RATIO = 0.945   # centre of the 11.1%-wide right safe-zone column
WATERMARK_Y_RATIO = 0.72    # lower safe-zone column (avoids cluttering center product view)
WATERMARK_FS_RATIO = 0.038  # small corner mark -- independent of the 0.0463 caption ratio
WATERMARK_COLOR = "&H000000FF"  # ASS &HAABBGGRR: opaque red
WATERMARK_ALPHA = "&HA0&"       # \alpha override -- faded watermark (~37% opaque, 0xA0/255 ≈ 63% transparent)

# Where the caption block sits: (ASS alignment, vertical margin).
# 2 = bottom centre, 5 = middle centre, 8 = top centre.
CAPTION_POSITIONS = {
    # Canvas anchors the caption block from its line-box centre. libass's
    # bottom alignment leaves the IBM Plex Thai ink a few pixels higher at
    # export scale, so the render margin is optically reduced by 10px while
    # the public safe-zone contract remains 420px.
    "bottom": (2, 410),
    "middle": (5, 0),
    "top": (8, 180),
}

TEXT_OVERLAY_POSITIONS = {
    "top": 0.20,
    "middle": 0.50,
    "bottom": 0.72,
}


class SubtitleEngine:
    """Creates rapid-fire TikTok subtitles with pop animations, Kanit font, and highlights."""

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """Convert float seconds to ASS timestamp format: H:MM:SS.cs"""
        seconds = max(0.0, seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        cs = int((s - int(s)) * 100)
        return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"

    @staticmethod
    def _tokenize_long_part_th(part: str, max_line_len: int) -> List[str]:
        """
        Segments a single over-length Thai run (no reliable inter-word spaces)
        into natural clause chunks at conjunctions and word boundaries using
        PyThaiNLP. Returns `[part]` unchanged if PyThaiNLP is unavailable, the
        tokenizer raises, or tokenization doesn't actually shorten anything
        (e.g. a single unsplittable word) -- callers must treat a length-1
        result as "could not split further", not as a bug.
        """
        try:
            from pythainlp.tokenize import word_tokenize
        except Exception:
            return [part]

        try:
            words = word_tokenize(part, engine="newmm")
            clause_chunks = []
            curr = ""
            conjunctions = {"ว่า", "เพราะ", "ถ้า", "และ", "หรือ", "แต่", "เมื่อ", "มัน", "ที่", "ซึ่ง", "จน", "แล้ว", "คือ"}
            for w in words:
                if (w in conjunctions and len(curr) >= 16) or (len(curr) + len(w) > max_line_len and len(curr) >= 14):
                    if curr:
                        clause_chunks.append(curr)
                    curr = w
                else:
                    curr += w
            if curr:
                clause_chunks.append(curr)
            return clause_chunks if clause_chunks else [part]
        except Exception:
            return [part]

    @classmethod
    def split_into_smart_clauses(cls, text: str, short_clause_max: int = 18, max_line_len: int = 34) -> List[str]:
        """
        Splits Thai text into natural grammatical clauses delimited by spaces and punctuation:
        - Short clauses (< 18 chars): Combines up to 2 short clauses per line (<= 34 chars).
        - Long clauses (>= 18 chars): Stays as 1 single sentence/clause per line.
        - Orphan words / punctuation (like 'บ้าง...', 'ๆ', 'นะ', 'ครับ', '<= 4 chars'): Merged into preceding clause.
        - Never cuts mid-word or creates isolated single-word meaningless frames.
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        # 1. Split into space-delimited clauses / phrases
        raw_parts = [p.strip() for p in clean_text.replace("\n", " ").split(" ") if p.strip()]
        if not raw_parts:
            return [clean_text]

        # 1.1 Thai has no inter-word spaces, so a single over-length run can
        # slip through even when the surrounding line happens to contain an
        # incidental space elsewhere (e.g. "สายชาร์จแม่เหล็กแรงดูดสูงงานดีมาก จริงๆ"
        # has 2 raw_parts, but the first one alone is >34 chars). Tokenize
        # EVERY part that individually exceeds max_line_len, not only when
        # the whole line has no spaces at all -- short parts that already
        # fit are left untouched so pairing/merging below still applies.
        expanded_parts: List[str] = []
        for p in raw_parts:
            if len(p) > max_line_len:
                expanded_parts.extend(cls._tokenize_long_part_th(p, max_line_len))
            else:
                expanded_parts.append(p)
        raw_parts = expanded_parts

        # 2. First pass: merge tiny orphan fragments into preceding clause
        merged_parts = []
        for p in raw_parts:
            if not merged_parts:
                merged_parts.append(p)
            elif (
                len(p) <= 4
                or p.startswith("ๆ")
                or p in ["บ้าง", "นะ", "ครับ", "ค่ะ", "เลย", "ด้วย", "อ่ะ", "น้า", "จ้า", "ล่ะ"]
            ):
                merged_parts[-1] += " " + p
            else:
                merged_parts.append(p)

        # 3. Second pass: Pair short clauses (2 per line) or keep long clause alone
        final_lines = []
        i = 0
        while i < len(merged_parts):
            curr = merged_parts[i]

            # Check if we can pair with the next clause (2 short clauses per line)
            if i + 1 < len(merged_parts):
                next_part = merged_parts[i + 1]
                combined_len = len(curr) + 1 + len(next_part)
                # Combine 2 short clauses if both are <= short_clause_max (or first is very short) and total fits
                if ((len(curr) <= short_clause_max and len(next_part) <= short_clause_max) or len(curr) <= 12) and combined_len <= max_line_len:
                    final_lines.append(f"{curr} {next_part}".strip())
                    i += 2
                    continue

            # Long clause or single remaining clause: 1 complete sentence per line
            final_lines.append(curr)
            i += 1

        return final_lines if final_lines else [clean_text]

    @classmethod
    def split_into_short_bursts(cls, text: str, max_chars: int = 34, max_words: int = 2) -> List[str]:
        """Backward-compatible alias for split_into_smart_clauses."""
        return cls.split_into_smart_clauses(text, max_line_len=max_chars)

    @staticmethod
    def _clause_boundaries_from_word_timings(
        clauses: List[str], word_timings: List[Dict]
    ) -> Optional[List[Tuple[float, float]]]:
        """
        Best-effort real (start, end) per entry in `clauses`, derived from
        `word_timings` (edge-tts's own word tokenization of the same text --
        it doesn't necessarily split the same way `split_into_smart_clauses`
        does, e.g. it may split "วันนี้" into "วัน"+"นี้") by walking both
        streams' cumulative character position together. `clauses` must be
        in-order substrings of the same text `word_timings` was measured
        against.

        Returns `None` when there's no word data, or when the two
        tokenizations cover too different a character count to trust a
        shared cursor -- a divergence guard, not the common case since both
        read the same underlying string.
        """
        if not word_timings:
            return None
        total_clause_chars = sum(len(cl) for cl in clauses)
        total_word_chars = sum(len(w.get("text", "")) for w in word_timings)
        if total_clause_chars == 0 or total_word_chars == 0:
            return None
        if not (0.6 <= total_word_chars / total_clause_chars <= 1.6):
            return None

        boundary_times = [word_timings[0]["start"]]
        clause_char_cursor = 0
        for cl in clauses:
            clause_char_cursor += len(cl)
            target = (clause_char_cursor / total_clause_chars) * total_word_chars
            running = 0
            end_time = word_timings[-1]["end"]
            for w in word_timings:
                running += len(w.get("text", ""))
                if running >= target:
                    end_time = w["end"]
                    break
            boundary_times.append(end_time)

        return list(zip(boundary_times[:-1], boundary_times[1:]))

    @staticmethod
    def _max_line_chars(font_size: int) -> int:
        """
        How many characters fit on one caption line at `font_size`.

        Calibrated against SequencePlayer.jsx's `maxLineW = CANVAS_W * 0.86`, so
        the clause splitter and the ASS line wrapper agree on where a line ends.
        Both must read it from here: when they disagreed, the splitter produced
        clauses the wrapper then broke onto a second line.
        """
        return max(24, int(round(3100 / max(20, font_size))))

    @classmethod
    def generate_micro_cues(
        cls, cues: List[Dict], max_line_len: Optional[int] = None
    ) -> List[Dict]:
        """
        Converts sentence-level cues into smart clause cues, translating each into English.
        Uses real per-word timestamps (`cue["word_timings"]`, from edge-tts's streaming API
        in voice_engine.py) when available; falls back to proportional character-count
        splitting of the parent cue's duration otherwise -- same as before this existed.

        `max_line_len` is how many characters fit on one rendered line. It has to
        come from the caller because it depends on the caption's font size, which
        the user can scale: at the default size a line holds ~62 characters, but
        at 2.4x only ~26. Splitting at a fixed 34 regardless meant a scaled-up
        caption produced clauses too long for their own line, and the ASS writer
        then wrapped them onto a second one. Left unset, the clause splitter's
        own default applies and behaviour is exactly as before.
        """
        micro_cues = []
        cue_id = 1

        for c in cues:
            start = c["start"]
            end = c["end"]
            total_dur = max(0.4, end - start)
            # Strip before splitting, not after: an emoji standing on its own
            # becomes its own clause, which then strips down to an empty cue
            # that renders as a blank caption holding the screen.
            text = strip_caption_emoji(c["text"])
            if not text:
                continue

            # An explicit newline is an editor-authored line break, not a
            # sentence boundary. Keep the whole cue together so Canvas and
            # ASS show all requested lines at the same timestamp; the ASS
            # wrapper below converts each paragraph to `\\N`.
            if "\n" in text or "\r" in text:
                clauses = [text]
            elif max_line_len:
                clauses = cls.split_into_smart_clauses(text, max_line_len=max_line_len)
            else:
                clauses = cls.split_into_smart_clauses(text)
            real_boundaries = cls._clause_boundaries_from_word_timings(
                clauses, c.get("word_timings") or []
            )
            total_chars = max(1, sum(len(cl) for cl in clauses))
            current_t = start

            for idx, cl in enumerate(clauses):
                if real_boundaries:
                    cl_start, cl_end = real_boundaries[idx]
                    cl_start = max(start, min(end, cl_start))
                    cl_end = max(cl_start, min(end, cl_end))
                else:
                    cl_dur = (len(cl) / total_chars) * total_dur
                    cl_start = current_t
                    cl_end = min(end, current_t + cl_dur)
                if idx == 0:
                    cl_start = start
                if idx == len(clauses) - 1:
                    cl_end = end

                # Only assign SFX on the very first beat of a major phrase
                sfx = None
                if idx == 0 and c.get("sfx"):
                    sfx = c["sfx"]

                # Emoji are deliberately absent from captions: libass draws
                # them through a fallback face whose width PIL cannot measure,
                # so every layout computed before the render -- the ghost
                # reveal's anchor, the detached-tone companions -- lands off by
                # the difference (measured at 16px for one emoji, enough to put
                # a tone mark over the wrong glyph). strip_caption_emoji also
                # clears any the script itself carried in.
                raw_c = strip_caption_emoji(cl)
                if "\n" in raw_c or "\r" in raw_c:
                    cue_text = "\n".join(
                        re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', line)).strip()
                        for line in re.split(r'\r\n?|\n', raw_c)
                    ).strip()
                else:
                    cue_text = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', raw_c)).strip()
                trans = (c.get("translation") or "").strip()
                if len(clauses) == 1:
                    cue_trans = trans
                else:
                    trans_parts = [t.strip() for t in re.split(r'[,.]\s+', trans) if t.strip()]
                    if len(trans_parts) == len(clauses):
                        cue_trans = trans_parts[idx]
                    elif idx == 0:
                        cue_trans = trans
                    else:
                        cue_trans = ""

                if not cue_text:
                    # Nothing left to show -- a clause that was only an emoji,
                    # or only punctuation. Emitting it would hold a blank
                    # caption on screen for its whole span.
                    current_t = cl_end
                    continue

                micro_cues.append({
                    "id": cue_id,
                    "start": round(cl_start, 3),
                    "end": round(cl_end, 3),
                    "text": cue_text,
                    "translation": cue_trans,
                    "sfx": sfx,
                    # Per-word timing for Progressive Ghost Reveal, computed
                    # once here so the ASS writer and the Canvas preview reveal
                    # on exactly the same word boundaries. Letting each side
                    # tokenize for itself would not work: python segments Thai
                    # with pythainlp's newmm and the browser has only
                    # Intl.Segmenter, which breaks words differently.
                    "word_reveal": build_word_reveal(
                        cue_text, cl_start, cl_end, c.get("word_timings")
                    ),
                    **{
                        key: c[key]
                        for key in ("x", "y", "position", "scale", "auto_emoji")
                        if key in c and c[key] is not None
                    },
                })
                cue_id += 1
                current_t = cl_end

        # Batch translate all smart clauses into English automatically
        try:
            from scripts.translator import SubtitleTranslator
            texts_to_trans = [mc["text"] for mc in micro_cues if not mc.get("translation")]
            if texts_to_trans:
                en_translations = SubtitleTranslator.translate_batch(texts_to_trans)
                trans_idx = 0
                for mc in micro_cues:
                    if not mc.get("translation") and trans_idx < len(en_translations):
                        mc["translation"] = en_translations[trans_idx] or ""
                        trans_idx += 1
        except Exception as e:
            print(f"Subtitle translation warning: {e}")

        return micro_cues

    KINETIC_KEYWORDS = KINETIC_KEYWORDS
    KINETIC_KEYWORDS_EN = KINETIC_KEYWORDS_EN
    _EN_STOPWORDS = _EN_STOPWORDS
    _TH_PARTICLES = _TH_PARTICLES

    @staticmethod
    def wrap_text_for_ass(text: str, max_chars_per_line: int = 40) -> str:
        return wrap_text_for_ass(text, max_chars_per_line=max_chars_per_line)

    @staticmethod
    def wrap_en_for_ass(text: str, max_chars_per_line: int = 44) -> str:
        return wrap_en_for_ass(text, max_chars_per_line=max_chars_per_line)

    @classmethod
    def apply_kinetic_highlighting(
        cls,
        text: str,
        primary_color_ass: str = "&H00FFFFFF&",
        color_hint: Optional[str] = None,
        custom_keywords: Optional[List[str]] = None,
    ) -> str:
        return apply_kinetic_highlighting(
            text, primary_color_ass=primary_color_ass, color_hint=color_hint, custom_keywords=custom_keywords
        )

    @classmethod
    def apply_kinetic_highlighting_en(
        cls,
        text: str,
        primary_color_ass: str = "&H00EAEAEA&",
        color_hint: Optional[str] = None,
        custom_keywords: Optional[List[str]] = None,
    ) -> str:
        return apply_kinetic_highlighting_en(
            text, primary_color_ass=primary_color_ass, color_hint=color_hint, custom_keywords=custom_keywords
        )

    @classmethod
    def _salient_word_en(cls, text: str) -> Optional[str]:
        return _salient_word_en(text)

    @classmethod
    def _salient_word_th(cls, text: str) -> Optional[str]:
        return _salient_word_th(text)

    @classmethod
    def _force_highlight(cls, text: str, word: Optional[str], colour: str, primary: str) -> str:
        return _force_highlight(text, word, colour, primary)

    @classmethod
    def apply_bilingual_kinetic_highlighting(
        cls,
        th_text: str,
        en_text: str,
        primary_th: str = "&H00FFFFFF&",
        primary_en: str = "&H00EAEAEA&",
        custom_keywords: Optional[List[str]] = None,
    ) -> Tuple[str, str]:
        return apply_bilingual_kinetic_highlighting(
            th_text, en_text, primary_th=primary_th, primary_en=primary_en, custom_keywords=custom_keywords
        )

    @classmethod
    def generate_ass(
        cls,
        cues: List[Dict],
        output_ass_path: str,
        font_name: str = "Kanit",
        font_size: int = 78,
        hook_brand: str = None,
        hook_model: str = None,
        hook_label: str = None,
        hook_duration: float = 3.5,
        hook_motion: Optional[Dict[str, object]] = None,
        hook_colors: Optional[Dict[str, str]] = None,
        hook_style: Optional[Dict[str, object]] = None,
        bilingual: bool = True,
        ghost_reveal: bool = True,
        video_width: int = VIDEO_WIDTH,
        video_height: int = VIDEO_HEIGHT,
        caption_position: str = "bottom",
        caption_color: str = None,
        caption_scale: float = 1.0,
        text_overlays: Optional[List[Dict[str, Any]]] = None,
        overlays: Optional[List[Dict[str, Any]]] = None,
        style_preset: Optional[str] = None,
        show_watermark: bool = True,
        source_credit: Optional[str] = None,
        source_credits: Optional[List[Dict[str, Any]]] = None,
        channel_badge: Optional[str] = None,
    ) -> Tuple[str, List[Dict]]:
        """
        Generate TikTok style ASS subtitle file with rapid-fire micro-bursts, 
        aesthetic fonts, and stacked bilingual English subtitles.
        """
        out_path = Path(output_ass_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # A clause must fit the line it will be rendered on. That width depends
        # on the caption's font size, which the user can scale up past the point
        # where the splitter's own default still fits -- so it is derived here,
        # from the same two arguments the `font_size` below is derived from.
        # The splitter keeps its own ceiling as the upper bound: a line at the
        # default size holds ~62 characters, and letting clauses grow to fill it
        # would undo the micro-burst pacing (subtitle_kinetic_rules.md asks for
        # 2-4 words). Only a scaled-up caption, whose line is narrower than that
        # ceiling, is bounded by the line width instead.
        try:
            _caption_scale = min(2.5, max(0.4, float(caption_scale or 1.0)))
        except (TypeError, ValueError):
            _caption_scale = 1.0
        _caption_fs = max(20, int(round(int(round(video_width * 0.0463)) * _caption_scale)))
        micro_cues = cls.generate_micro_cues(
            cues,
            max_line_len=min(MICRO_BURST_MAX_CHARS, cls._max_line_chars(_caption_fs)),
        )


        # Real embedded family name for whichever font the UI selected --
        # every style below sets Bold=<resolved_bold>, requesting that
        # family's real bold weight from libass/fontconfig ONLY when one
        # actually exists (has_true_bold_face). Noto Sans Thai's registered
        # file is internally mislabeled Regular/weight-400 despite its
        # "SemiBold" filename -- a Bold=1 request against it has no genuine
        # bold face to land on, so libass/DirectWrite synthetically embolden
        # the Regular outline instead, which breaks the GPOS mark-to-mark
        # anchor delta ั+่ ("นั่ง") depends on. See has_true_bold_face()'s
        # docstring for the full empirical diagnosis (2026-09-08).
        font_map = _load_font_family_map()
        resolved_font = font_map.get(font_name, DEFAULT_FONT_FAMILY)
        # Body captions use an explicit physical face so libass and Canvas
        # shape the Thai run with the same IBM Plex cut.  Keep the family name
        # above for metrics and use this face only in TikTok caption styles;
        # custom overlays retain their own look/weight contract.
        caption_font, caption_bold = ass_caption_face(resolved_font)
        resolved_bold = 1 if has_true_bold_face(resolved_font) else 0
        # libass sizes a face so its line box (ascender + descender) equals the
        # style's Fontsize, while the canvas preview -- and every font size in
        # this file -- means the em square. Thai faces run line boxes far
        # taller than their em, so the same number rendered ~40% smaller than
        # intended. Boosting \fscx/\fscy (never Fontsize) cancels that out:
        # glyphs land at the intended em while line advance, which libass
        # takes from Fontsize alone, stays untouched -- and \p drawings, whose
        # coordinates are already PlayRes pixels, must NOT be boosted.
        TEXT_SCALE_BOOST = 1.0 / ass_glyph_scale(resolved_font)

        # The hook's face, and the boost that belongs to it. A font's line box
        # against its em is what TEXT_SCALE_BOOST cancels, so a banner in
        # another face has to be measured with that face's number -- reusing
        # the caption's would size the banner by the wrong metrics.
        # Every overlay, in one shape. A caller that still passes the banner
        # scalars and text_overlays[] is converted here rather than at each
        # place they are read, so there is one vocabulary below this line.
        if overlays is None:
            overlays = []
            _legacy_hook = hook_overlay_from_legacy(
                hook_brand or "", hook_model or "", hook_label or "",
                hook_duration, hook_motion, hook_colors, hook_style,
            )
            if _legacy_hook:
                overlays.append(_legacy_hook)
            overlays.extend(
                text_overlay_from_legacy(t) for t in (text_overlays or []) if isinstance(t, dict)
            )
        live_overlays = [o for o in (overlays or []) if o and not o.get("hidden")]
        hook_overlay = next((o for o in live_overlays if o.get("kind") == "hook"), None)
        text_items = [o for o in live_overlays if o.get("kind") != "hook"]

        # Product callouts are the editable replacement for the legacy
        # sentence-level SpecBar.  Keep the legacy SpecBar fallback for old
        # callers, but suppress it when the same value already exists as a
        # live product-callout overlay so one `on_screen` value cannot be
        # rendered twice.
        product_callout_texts = set()
        for item in text_items:
            if item.get("role") != "product_callout":
                continue
            tiers = item.get("tiers") or []
            first = tiers[0] if tiers and isinstance(tiers[0], dict) else {}
            callout_text = first.get("text") or item.get("text") or item.get("value") or ""
            normalized = " ".join(str(callout_text).split()).strip().casefold()
            if normalized:
                product_callout_texts.add(normalized)

        _hook_look = resolve_look((hook_overlay or {}).get("look"), None)
        hook_font = font_map.get(_hook_look["font"], _hook_look["font"])
        if hook_font not in {f["family"] for f in AssetRegistry.fonts()}:
            hook_font = resolved_font
        hook_bold = 1 if has_true_bold_face(hook_font) else 0
        HOOK_SCALE_BOOST = 1.0 / ass_glyph_scale(hook_font)
        is_pill_mode = font_name in ["capsule_pill", "Minimal Dark Capsule Pill"]

        # Caption placement and colour. ASS wants &HAABBGGRR, i.e. the reverse
        # byte order of an HTML hex, which is why the picker's #RRGGBB cannot
        # be pasted in directly.
        alignment, margin_v = CAPTION_POSITIONS.get(
            caption_position, CAPTION_POSITIONS["bottom"]
        )
        primary = ass_colour(caption_color) or "&H00FFFFFF"
        try:
            scale = min(2.5, max(0.4, float(caption_scale or 1.0)))
        except (TypeError, ValueError):
            scale = 1.0
        # Exact 1-to-1 pixel calibration with CapCut & SequencePlayer Canvas:
        # Standard TikTok Subtitle: 100% (scale=1.0) calibrated to exactly 50pt on 1080w
        # Matches SequencePlayer Canvas baseFs (25px on 540w) perfectly
        base_fs = int(round(video_width * 0.0463))
        font_size = max(20, int(round(base_fs * scale)))
        hook_fs = int(round(video_width * 0.065))

        # Style Fontsize fields below carry each one's OWN em-vs-line-box
        # boost baked in (rather than leaving Fontsize at the unboosted
        # number and pushing the whole boost onto \fscx/\fscy, as this file
        # used to). libass's GPOS mark-to-mark anchor delta that ั+่ ("นั่ง")
        # depends on only stays correct when a glyph is rasterized fresh at
        # its final size -- scaling it up afterward via \fscx/\fscy breaks
        # that anchor, worse the more it scales, regardless of Bold. Every
        # \fscx/\fscy percent written below this point must therefore be
        # divided by the same style's boost (never left at the old boosted
        # number), which numerically cancels against the Fontsize increase
        # and reproduces the exact same rendered size -- verified pixel-
        # identical against the old scheme, both for a plain caption line
        # and for the hook banner (2026-09-08).
        font_size_boosted = int(round(font_size * TEXT_SCALE_BOOST))
        base_fs_boosted = int(round(base_fs * TEXT_SCALE_BOOST))
        hook_fs_boosted = int(round(hook_fs * HOOK_SCALE_BOOST))
        watermark_fs = max(14, int(round(video_width * WATERMARK_FS_RATIO)))
        watermark_fs_boosted = int(round(watermark_fs * TEXT_SCALE_BOOST))
        # A fixed 1.2px outline read as blurry once alpha-faded at this font
        # size -- scale it with the glyph like the caption styles' own
        # front_outline does, instead of a flat constant.
        watermark_outline = round(max(2.0, watermark_fs_boosted * 0.05), 1)

        def repair_caption_text(value: str) -> Tuple[str, List[Tuple[str, str, str]]]:
            # Every upper-vowel/tone pair is repaired for every face.
            # Prompt/Kanit/Mitr/Itim need it because their bundled outlines collapse the stack;
            # applying the same deterministic geometry to the other faces
            # keeps Canvas and ASS output identical.
            return repair_thai_stacked_marks(value)

        # Dynamic Soft Shadow & Outline metrics (Zero hardcoding: scales with any font, scale, and resolution)
        front_outline = round(max(1.8, font_size * 0.040), 1)
        shadow_outline = round(max(2.2, font_size * 0.050), 1)
        shadow_blur = round(max(2.5, font_size * 0.055), 1)
        shadow_dx = int(round(max(1.0, font_size * 0.030)))
        shadow_dy = int(round(max(1.5, font_size * 0.045)))
        
        shadow_margin_l = 60 + shadow_dx
        shadow_margin_r = 60 - shadow_dx
        shadow_margin_v = margin_v - shadow_dy if alignment in (1, 2, 3) else margin_v + shadow_dy

        tone_raise = max(6, int(round(font_size_boosted * THAI_STACKED_MARK_RAISE_EM)))
        hidden_mark_components = r"{\1a&HFF&\3a&HFF&\4a&HFF&}"

        def caption_mark_position(*, shadow: bool) -> str:
            """Anchor a full-layout companion line, raised from its body.

            The companion carries the whole caption, `\\N` and all, so it has to
            be laid out the way the body is -- by margin, growing away from the
            same edge. Pinning it with `\\pos` anchors the entire block on one
            point instead, which matches a single line but leaves a wrapped
            caption's marks stranded: the body grows upward from the bottom
            margin while the pinned companion stays put, so the tone ends up
            below the line it belongs to (measured: body at 1309-1374 and
            1442-1480, companion pinned at 1496).
            """
            if pos_override:
                return f"\\an5\\pos({px_x},{px_y - tone_raise})"

            active_margin = shadow_margin_v if shadow else margin_v
            if alignment == 2:
                # Bottom-anchored: a larger margin lifts the block.
                raised = active_margin + tone_raise
            elif alignment == 8:
                # Top-anchored: a smaller margin lifts it.
                raised = max(0, active_margin - tone_raise)
            else:
                # Centre-anchored captions have no margin to push against, so
                # the companion is pinned -- a centred block is measured from
                # its own middle and does not drift the way an edge-anchored
                # one does.
                anchor_x = int(round(video_width / 2 + (shadow_dx if shadow else 0)))
                anchor_y = int(round(video_height / 2 + (shadow_dy if shadow else 0)))
                return f"\\an{alignment}\\pos({anchor_x},{anchor_y - tone_raise})"
            margin_l = shadow_margin_l if shadow else 60
            margin_r = shadow_margin_r if shadow else 60
            return f"\\an{alignment}\\marginv{raised}\\marginl{margin_l}\\marginr{margin_r}"

        def caption_mark_overlay(parts: Tuple[str, str, str], *, shadow: bool) -> str:
            """Expose one detached tone while all layout-preserving text stays hidden."""
            before, tone, after = parts
            settled_alpha = "38" if shadow else "00"
            blur_tag = f"\\blur{shadow_blur}" if shadow else ""
            visible = (
                "{" + blur_tag + r"\bord1\shad1"
                + r"\1a&HFF&\3a&HFF&\4a&HFF&"
                + rf"\t(0,70,\1a&H{settled_alpha}&\3a&H{settled_alpha}&\4a&H{settled_alpha}&)"
                + "}"
            )
            return f"{hidden_mark_components}{before}{visible}{tone}{hidden_mark_components}{after}"

        header = f"""[Script Info]
Title: TikTok Aesthetic Subtitles
ScriptType: v4.00+
{SUBTITLE_RENDER_CONTRACT_MARKER}
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokSoftShadow,{caption_font},{font_size_boosted},&H00000000,&H00000000,&H00000000,&H00000000,{caption_bold},0,0,0,100,100,0,0,1,{shadow_outline},0,{alignment},{shadow_margin_l},{shadow_margin_r},{shadow_margin_v},1
Style: TikTokWhite,{caption_font},{font_size_boosted},{primary},&H000000FF,&H00000000,&H00000000,{caption_bold},0,0,0,100,100,0,0,1,{front_outline},0,{alignment},60,60,{margin_v},1
Style: TikTokYellow,{caption_font},{font_size_boosted},&H0000E6FF,&H000000FF,&H00000000,&H00000000,{caption_bold},0,0,0,100,100,0,0,1,{front_outline},0,2,60,60,420,1
Style: TikTokCyan,{caption_font},{font_size_boosted},&H00FFE600,&H000000FF,&H00000000,&H00000000,{caption_bold},0,0,0,100,100,0,0,1,{front_outline},0,2,60,60,420,1
Style: TikTokMinimalPill,{caption_font},{int(round((font_size - 6) * TEXT_SCALE_BOOST))},{primary},&H000000FF,&H00000000,&HCC000000,{caption_bold},0,0,0,100,100,0,0,3,6,0,{alignment},60,60,{margin_v},1
Style: HookHeader,{hook_font},{hook_fs_boosted},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,{hook_bold},0,0,0,100,100,0,0,1,6.0,0,8,60,60,180,1
Style: HookHeaderShadow,{hook_font},{hook_fs_boosted},&H00000000,&H00000000,&H00000000,&H00000000,{hook_bold},0,0,0,100,100,0,0,1,7.0,0,8,62,58,177,1
Style: HookHeaderPill,{hook_font},{hook_fs_boosted},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,{hook_bold},0,0,0,100,100,0,0,3,12,0,8,60,60,180,1
Style: SpecBar,{resolved_font},{int(round((font_size - 12) * TEXT_SCALE_BOOST))},&H00000000,&H000000FF,&H00000000,&H0000E6FF,{resolved_bold},0,0,0,100,100,0,0,3,10,0,9,50,50,380,1
Style: TextOverlayMain,{resolved_font},{base_fs_boosted},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,{resolved_bold},0,0,0,100,100,0,0,1,5.0,2,5,60,60,0,1
Style: TextOverlayPill,{resolved_font},{base_fs_boosted},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,{resolved_bold},0,0,0,100,100,0,0,1,5.0,2,5,60,60,0,1
Style: Watermark,{caption_font},{watermark_fs_boosted},{WATERMARK_COLOR},&H000000FF,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,{watermark_outline},0,5,0,0,0,1
Style: SourceCredit,{resolved_font},26,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1.5,1,2,0,0,32,1
Style: ChannelBadge,{resolved_font},26,&H00FFFFFF,&H000000FF,&H00000000,&H000055FF,1,0,0,0,100,100,0,0,3,8,0,9,30,30,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []

        # 0. Copyright watermark -- configurable, burned into right safe-zone
        # column and rotated -90 deg via \frz.
        if show_watermark:
            wm_x = int(round(video_width * WATERMARK_X_RATIO))
            wm_y = int(round(video_height * WATERMARK_Y_RATIO))
            events.append(
                f"Dialogue: 0,{cls._format_ass_time(0)},{cls._format_ass_time(10800)},Watermark,,0,0,0,,"
                f"{{\\an5\\pos({wm_x},{wm_y})\\frz-90\\alpha{WATERMARK_ALPHA}}}{ass_escape_text(WATERMARK_TEXT)}"
            )

        # 0.5. Source Credit overlay (e.g. "Source : Weibo OPPO", "Source : Weibo Xiaomi", "Source : mi.com")
        if source_credits:
            for sc in source_credits:
                sc_start = sc.get("start", 0.0)
                sc_end = sc.get("end", 10800.0)
                sc_text = sc.get("text", "")
                if sc_text:
                    events.append(
                        f"Dialogue: 0,{cls._format_ass_time(sc_start)},{cls._format_ass_time(sc_end)},SourceCredit,,0,0,0,,"
                        f"{{\\an2\\pos({int(video_width / 2)},{int(video_height - 35)})\\alpha&H15&}}{ass_escape_text(sc_text)}"
                    )
        elif source_credit:
            events.append(
                f"Dialogue: 0,{cls._format_ass_time(0)},{cls._format_ass_time(10800)},SourceCredit,,0,0,0,,"
                f"{{\\an2\\pos({int(video_width / 2)},{int(video_height - 35)})\\alpha&H15&}}{ass_escape_text(source_credit)}"
            )

        # 0.6. Channel watermark badge in top right (e.g. "TECH MX" style)
        if channel_badge:
            events.append(
                f"Dialogue: 0,{cls._format_ass_time(0)},{cls._format_ass_time(10800)},ChannelBadge,,0,0,0,,"
                f"{{\\an9\\pos({int(video_width - 40)},55)}}{ass_escape_text(channel_badge)}"
            )

        # 1. Top Hook Banner -- 3-tier product-poster composition (brand
        # largest / model mid / label smallest), replacing the old single
        # free-text hook_title line. All three tiers live in ONE dialogue
        # event per layer (Shadow, Main), \N-joined, each line carrying its
        # own override block -- same stacking pattern the bilingual caption
        # block below already uses, so every property (\fscx/\fscy/\c) that
        # matters is re-declared per line and nothing leaks across a \N.
        if hook_overlay:
            hook_ctx = {
                "video_width": video_width,
                "video_height": video_height,
                "hook_fs": hook_fs,
                "hook_font": hook_font,
                "caption_color": caption_color,
                "style_preset": style_preset,
            }
            events.extend(overlay_events(hook_overlay, hook_ctx))

        # Batch-translate whatever is still missing an English line.
        #
        # This used to reuse the stored translations whenever ANY cue had one
        # (`any(...)`), so a batch that came back with gaps -- the free
        # translation endpoint drops lines under load -- kept those gaps
        # forever: every later render and re-roll saw "some translations
        # exist" and never retried the empty ones. Measured across the
        # project folders: one clip was missing English on 16 of 25 cues.
        en_translations = []
        if bilingual:
            en_translations = [(c.get("translation") or "") for c in micro_cues]
            missing_idx = [i for i, t in enumerate(en_translations) if not t.strip()]
            if missing_idx:
                try:
                    try:
                        from scripts.translator import SubtitleTranslator
                    except Exception:
                        from translator import SubtitleTranslator
                    fresh = SubtitleTranslator.translate_batch(
                        [micro_cues[i]["text"] for i in missing_idx]
                    )
                    for i, translated in zip(missing_idx, fresh):
                        if translated:
                            en_translations[i] = translated
                except Exception as err:
                    print(f"   ⚠️  แปลอังกฤษไม่สำเร็จ ({err}) — ซับจะเป็นไทยอย่างเดียว")
        else:
            en_translations = [""] * len(micro_cues)

        # Collect dynamic project keywords from the hook banner or product
        # hints -- feeds the kinetic-highlighting pass below so brand/model
        # words get the same colour treatment wherever they show up in the
        # captions, not just in the banner. Joins all three tiers; must stay
        # in sync with whatever the banner actually displays above.
        hook_combined = " ".join(filter(None, [hook_brand, hook_model, hook_label])).strip()
        proj_keywords = []
        if hook_combined:
            proj_keywords.append(hook_combined)
            for t in hook_combined.split():
                if len(t.strip()) >= 3 and t.strip() not in proj_keywords:
                    proj_keywords.append(t.strip())

        # 2. Add Rapid-Fire Micro-Cues with Stacked Bilingual Support & 2-Layer Soft Shadow
        for idx, cue in enumerate(micro_cues):
            start_t = cls._format_ass_time(cue["start"])
            end_t = cls._format_ass_time(cue["end"])
            # Exact line wrap calibration matching SequencePlayer.jsx maxLineW = 464px (86% of 1080w = 928px)
            dyn_max_chars = cls._max_line_chars(font_size)
            # cue["text"] is caption text the AI script/translator produced from
            # scraper- and user-controlled product data -- a literal `{`/`}`
            # or `\` in it must render as a literal character, never open an
            # ASS override block (see ass_escape_text). Escaped BEFORE
            # wrapping/highlighting so those only ever see plain text and add
            # their own well-formed \N / {\c...} sequences on top.
            # Strip emoji here as well as in generate_micro_cues: a cue can
            # reach the writer without passing through it -- an older manifest,
            # or a re-roll feeding its own micro_cues back in -- and a single
            # emoji is enough to move the reveal's anchor off the text.
            cue_source_text = strip_caption_emoji(cue["text"])
            text = cls.wrap_text_for_ass(ass_escape_text(cue_source_text), max_chars_per_line=dyn_max_chars)
            if not text:
                continue
            # Sync wrapped (but NOT escaped) text back into cue object for
            # 100% editor preview parity -- this dict is also what a re-roll
            # feeds back into generate_ass() as ctx.cues, so storing the
            # escaped form here would double-escape on every subsequent run.
            cue["text"] = cls.wrap_text_for_ass(cue_source_text, max_chars_per_line=dyn_max_chars)

            # Thai-safe entrance: fade in over 70ms without geometric scaling.
            # Scaling a shaped Thai run with \fscx/\fscy after libass has
            # positioned its marks can collapse the stacked pair ั + ่
            # (for example, นั่ง) during the first frames. Alpha does not
            # alter glyph geometry, so HarfBuzz/libass keeps the mark anchors
            # intact while the caption still enters quickly.
            caption_anim = r"{\alpha&HFF&\t(0,70,\alpha&H00&)}"
            
            # Check for English Translation
            en_wrapped = ""
            if bilingual and idx < len(en_translations):
                candidate_en = (en_translations[idx] or cue.get("translation", "")).strip()
                if candidate_en and not any(sig in candidate_en for sig in ["Error 500", "500.", "That's an error", "<html"]):
                    # Store the raw translation for editor parity / manifest
                    # persistence (same re-roll double-escape hazard as
                    # cue["text"] above); escape only the copy that feeds ASS.
                    cue["translation"] = candidate_en
                    dyn_en_chars = max(26, int(round(4000 / max(20, font_size))))
                    en_wrapped = cls.wrap_en_for_ass(ass_escape_text(candidate_en), max_chars_per_line=dyn_en_chars)
                else:
                    # The translation came back as an error page, so it is not
                    # usable text -- clear it rather than burn it into the ASS.
                    cue["translation"] = ""
            elif bilingual:
                cue["translation"] = ""
            # With bilingual off the translation is simply not drawn. It used to
            # be cleared here too, which meant turning the English line off and
            # back on lost every translation the project had and paid to
            # regenerate them -- not showing something is not a reason to
            # delete it.

            # The English line sits at 68% of the Thai one; \fscx/\fscy stay
            # at the plain percent now that Fontsize carries the boost (see
            # anim's comment above).
            en_pct = 68
            # Apply Synchronized Bilingual Kinetic Highlighting (guaranteeing exact color parity)
            if en_wrapped:
                highlighted_text, en_highlighted = cls.apply_bilingual_kinetic_highlighting(
                    th_text=text,
                    en_text=en_wrapped,
                    primary_th=primary,
                    primary_en="&H00EAEAEA&",
                    custom_keywords=proj_keywords
                )
                # \alpha carries across \N, so the English line has to clear it
                # explicitly: under a ghost reveal the Thai line above ends on
                # whichever tag its last unspoken word set, and without the
                # reset the whole translation inherited \alpha&HFF& and stayed
                # invisible until the final word was spoken.
                en_sub = f"\\N{{\\alpha&H00&\\fscx{en_pct}\\fscy{en_pct}\\c&H00EAEAEA&}}{en_highlighted}"
            else:
                highlighted_text = cls.apply_kinetic_highlighting(text, primary_color_ass=primary, custom_keywords=proj_keywords)
                en_sub = ""

            style = "TikTokMinimalPill" if is_pill_mode else "TikTokWhite"
            # A Canvas caption uses the em-sized font for line advance.  The
            # boosted ASS style above is necessary for a single line's glyph
            # ink, but its line box becomes too tall when explicit `\\N` lines
            # are present.  Reapply the same optical glyph boost from the
            # unboosted font size so libass keeps Canvas's 1.0 line-height.
            multi_line_metric_tag = ""
            if "\\N" in text and not en_sub:
                boost_pct = int(round(TEXT_SCALE_BOOST * 100))
                multi_line_metric_tag = f"{{\\fs{font_size}\\fscx{boost_pct}\\fscy{boost_pct}}}"

            pos_override = ""
            if cue.get("x") is not None or cue.get("y") is not None:
                norm_x = float(cue.get("x") if cue.get("x") is not None else 0.50)
                norm_y = float(cue.get("y") if cue.get("y") is not None else 0.78125)
                px_x = int(round(video_width * norm_x))
                px_y = int(round(video_height * norm_y))
                pos_override = f"\\an5\\pos({px_x},{px_y})"

            # Layer 0: Natural Soft Feathered Shadow (Gaussian Blur matching Canvas preview)
            #
            # Recorded here and only appended once it is known whether the
            # reveal took over: the shadow draws the caption whole from the
            # cue's first frame, so under a reveal it would show the words that
            # have not been spoken yet as a soft grey pre-echo -- invisible
            # enough to miss on one line, obvious as a floating tone mark above
            # a second one.
            shadow_events: List[str] = []
            if not is_pill_mode:
                en_sub_shadow = f"\\N{{\\fscx{en_pct}\\fscy{en_pct}}}{en_wrapped}" if en_wrapped else ""
                shadow_tag = f"{{\\blur{shadow_blur}\\alpha&H38&}}"
                shadow_pos = f"{{{pos_override}}}" if pos_override else ""
                # Keep the fade after the shadow's static alpha tag so the
                # shadow follows the same entrance and is not visible alone
                # on the first frame.
                # Repair the Thai only. A companion mark overlay redraws the
                # whole string it was given and hides everything but its one
                # tone -- but the English line carries its own \fscx/\c tags,
                # which reset that hiding, so an English line inside the
                # repaired text got painted a second time, 14px above the real
                # one. The translation is appended after the repair instead, so
                # it exists once, in the body, and never in an overlay.
                shadow_text, shadow_marks = repair_caption_text(text)
                shadow_text += en_sub_shadow
                shadow_entry = f"Dialogue: 0,{start_t},{end_t},TikTokSoftShadow,,0,0,0,,{shadow_pos}{shadow_tag}{multi_line_metric_tag}{caption_anim}{shadow_text}"
                shadow_events.append(shadow_entry)
                for mark_parts in shadow_marks:
                    shadow_events.append(
                        f"Dialogue: 0,{start_t},{end_t},TikTokSoftShadow,,0,0,0,,"
                        f"{{{caption_mark_position(shadow=True)}}}"
                        f"{caption_mark_overlay(mark_parts, shadow=True)}"
                    )

            # Layer 1: Crisp Foreground Text with dynamic kinetic highlights
            main_pos = f"{{{pos_override}}}" if pos_override else ""
            # Same split as the shadow above: the English line must not reach
            # the mark overlay, which would draw it a second time.
            main_text, main_marks = repair_caption_text(highlighted_text)
            main_text += en_sub

            # Progressive Ghost Reveal (SOP Phase 3) replaces the single
            # foreground event with one per word. It needs a plain line to
            # measure and colour itself, so it only runs where the ordinary
            # caption would have been drawn whole: a multi-line cue, a pill, or
            # an editor-positioned cue each have their own layout contract that
            # a word-by-word rebuild would quietly break.
            reveal_events: List[str] = []
            if (
                ghost_reveal
                and not is_pill_mode
            ):
                # Prefer the track generate_micro_cues already attached, so the
                # ASS and the preview reveal on identical boundaries. Recomputing
                # is only for cues that came from somewhere else (a hand-built
                # list in a test, or an older manifest).
                # A stored track is only usable if it describes the text about
                # to be drawn. An older manifest's track still carries the
                # emoji that have since been stripped, so its words would no
                # longer add up to the line -- recompute instead.
                stored_reveal = cue.get("word_reveal") or []
                stored_matches = "".join(
                    w.get("text", "") for w in stored_reveal
                ).replace(" ", "") == cue_source_text.replace(" ", "").replace("\n", "")
                reveal = stored_reveal if stored_matches else build_word_reveal(
                    cue_source_text,
                    float(cue["start"]),
                    float(cue["end"]),
                    cue.get("word_timings"),
                )
                if reveal_is_usable(reveal):
                    # Stacked Thai marks have to be detached here too. Several
                    # faces collapse an upper vowel against its tone, so the
                    # whole engine strips the tone out of the body and redraws
                    # it as a raised companion glyph -- skipping that on the
                    # reveal path would reintroduce the collision this codebase
                    # has fixed once already.
                    repaired_reveal = []
                    for word in reveal:
                        # The reveal track is built from the cue's raw text, so
                        # each word still has to be escaped before it reaches
                        # the ASS -- exactly as the whole-line path does at
                        # `text = wrap_text_for_ass(ass_escape_text(...))`.
                        # Without this a caption containing a literal override
                        # block reaches libass as markup and can recolour or
                        # reposition itself.
                        w_body, _ = repair_caption_text(ass_escape_text(word["text"]))
                        repaired_reveal.append({**word, "text": w_body})

                    # The companions, though, are built from the WHOLE line at
                    # once. Each one carries the entire caption and hides all of
                    # it but its own tone, which is what holds the tone over the
                    # right glyph -- a companion built from one word has nothing
                    # in front of it, so libass draws its tone at the start of
                    # the line instead of above the word it belongs to.
                    _, line_marks = repair_caption_text(
                        ass_escape_text(cue_source_text.replace("\n", ""))
                    )
                    # A companion appears with the word that owns its tone, so a
                    # mark is timed to the word whose text contains it.
                    reveal_marks: List[Tuple[float, Tuple[str, str, str]]] = []
                    for parts in line_marks:
                        prefix_len = len(parts[0])
                        consumed = 0
                        owner_start = float(reveal[0]["start"])
                        for word in reveal:
                            consumed += len(ass_escape_text(word["text"]))
                            if consumed > prefix_len:
                                owner_start = float(word["start"])
                                break
                        reveal_marks.append((owner_start, parts))

                    # libass centres a line on the ink it actually paints, and a
                    # ghosted word paints none -- so the reveal has to carry its
                    # own anchor or it slides sideways as it advances.
                    # layout_line() re-applies ass_glyph_scale internally, so it
                    # wants the same Fontsize the style carries -- the boosted
                    # one. Handing it the plain em number measures the line at
                    # roughly half its rendered width, which put the anchor
                    # ~100px left of where the text actually lands.
                    # Where the line sits vertically depends on the caption's
                    # alignment, exactly as caption_mark_position works it out:
                    # bottom measures its margin up from the floor, top down
                    # from the ceiling, and middle ignores the margin entirely.
                    # Deriving it as `height - margin_v` regardless put a
                    # middle-positioned caption at y=1920, off the bottom edge.
                    # The anchor's own alignment has to be the left-column
                    # equivalent of the style's, or the line hangs from the
                    # wrong edge: \an4 centres on its y, so using it for a
                    # bottom caption sat the text ~40px low and a top one ~36px
                    # high against the plain caption's position.
                    if pos_override:
                        # The editor writes x/y onto every cue as soon as the
                        # caption is positioned once, so a positioned caption is
                        # the normal case, not an exception -- refusing to
                        # reveal on it left the feature off in real projects.
                        # \an5 centres on the point, so the reveal centres too
                        # and keeps its own left anchor from the line's width.
                        reveal_y = float(px_y)
                        reveal_align = 4
                    elif alignment == 2:
                        reveal_y = video_height - margin_v
                        reveal_align = 1
                    elif alignment == 8:
                        reveal_y = margin_v
                        reveal_align = 7
                    else:
                        reveal_y = video_height / 2.0
                        reveal_align = 4
                    reveal_x = float(px_x) if pos_override else video_width / 2.0

                    def _anchor_for(line_text: str, y: float) -> str:
                        return anchor_tags(
                            line_text,
                            caption_font,
                            font_size_boosted,
                            centre_x=reveal_x,
                            baseline_y=y,
                            video_w=video_width,
                            vertical_align=reveal_align,
                        )

                    # Deal the words out across lines using the UNrepaired
                    # track: repair_caption_text pulls tone marks out of the
                    # body, so a repaired word no longer matches the wrapped
                    # line character for character and every split would be
                    # rejected. The repaired words are then re-split the same
                    # way, which is safe because repair is per word.
                    wrapped_lines = [ln for ln in text.split("\\N") if ln.strip()]
                    raw_lines = (
                        split_reveal_by_lines(
                            [{**w, "text": ass_escape_text(w["text"])} for w in reveal],
                            wrapped_lines,
                        )
                        if len(wrapped_lines) > 1
                        else None
                    )
                    reveal_lines = None
                    if raw_lines:
                        reveal_lines, cursor = [], 0
                        for line in raw_lines:
                            reveal_lines.append(repaired_reveal[cursor:cursor + len(line)])
                            cursor += len(line)

                    if reveal_lines:
                        # A wrapped caption reveals across its lines. Each line
                        # gets its own anchor, stepping by the caption's line
                        # advance -- LINE_HEIGHT_FACTOR is 1.0 (parity rule 2.7),
                        # so one font size per line. The block is positioned the
                        # same way the plain caption's is: bottom alignment grows
                        # upward from the margin, top downward, middle centred.
                        count = len(reveal_lines)
                        step = font_size
                        if alignment == 2:
                            first_y = reveal_y - (count - 1) * step
                        elif alignment == 8:
                            first_y = reveal_y
                        else:
                            first_y = reveal_y - ((count - 1) * step) / 2.0
                        anchors = [
                            _anchor_for("".join(w["text"] for w in line), first_y + i * step)
                            for i, line in enumerate(reveal_lines)
                        ]
                        reveal_events = build_multiline_reveal_events(
                            reveal_lines,
                            float(cue["end"]),
                            anchors,
                            style=style,
                            layer=1,
                        )
                        # Companion glyphs for the stacked marks. caption_mark_
                        # position() anchors on the caption block as a whole,
                        # which is only right for a single line -- here each
                        # line already has its own anchor, so the glyph reuses
                        # it, raised by the same tone_raise. It is re-derived
                        # per line because the overlay draws the whole line and
                        # hides everything but the tone, to keep the layout.
                        for li, line in enumerate(reveal_lines):
                            line_y = first_y + li * step
                            for word in line:
                                _, w_marks = repair_caption_text(
                                    ass_escape_text(word["text"])
                                )
                                for parts in w_marks:
                                    mark_anchor = anchor_tags(
                                        "".join(w["text"] for w in line),
                                        caption_font,
                                        font_size_boosted,
                                        centre_x=reveal_x,
                                        baseline_y=line_y - tone_raise,
                                        video_w=video_width,
                                        vertical_align=reveal_align,
                                    )
                                    reveal_events.append(
                                        f"Dialogue: 1,{cls._format_ass_time(word['start'])},"
                                        f"{cls._format_ass_time(float(cue['end']))},"
                                        f"{style},,0,0,0,,{mark_anchor}"
                                        f"{caption_mark_overlay(parts, shadow=False)}"
                                    )
                    else:
                        body_anchor_text = "".join(w["text"] for w in repaired_reveal)
                        anchor = _anchor_for(body_anchor_text, reveal_y)
                        reveal_events = build_ghost_reveal_events(
                            repaired_reveal,
                            float(cue["end"]),
                            style=style,
                            layer=1,
                            prefix_tags=anchor,
                        )
                        # A companion glyph appears with its own word and then
                        # stays for the rest of the cue, matching the body text
                        # underneath it -- which also stays once revealed.
                        #
                        # It has to hang off the reveal's own anchor, not
                        # caption_mark_position(): that places a mark against
                        # the plain caption's layout, which the reveal has
                        # already replaced with a left-anchored \pos of its own.
                        # Mixing the two put the tone under the wrong glyph.
                        # Measured from the same string the body anchors on:
                        # the companion now carries the whole line too, so both
                        # start at the same x and the tone lands over its glyph.
                        mark_anchor = anchor_tags(
                            body_anchor_text,
                            caption_font,
                            font_size_boosted,
                            centre_x=reveal_x,
                            baseline_y=reveal_y - tone_raise,
                            video_w=video_width,
                            vertical_align=reveal_align,
                        )
                        for m_start, parts in reveal_marks:
                            reveal_events.append(
                                f"Dialogue: 1,{cls._format_ass_time(m_start)},{cls._format_ass_time(float(cue['end']))},"
                                f"{style},,0,0,0,,{mark_anchor}"
                                f"{caption_mark_overlay(parts, shadow=False)}"
                            )

                    # The English line gets its own event, centred normally.
                    # It cannot ride along inside the reveal's: those are
                    # anchored from their left edge (the ghosts paint no ink for
                    # libass to centre on), so an English line appended to them
                    # inherited that left anchor and sat off-centre under a Thai
                    # line that is itself centred -- the block looked lopsided.
                    # Nothing in the English is revealed, so it needs no anchor
                    # of its own and is simply centred like a plain caption.
                    if reveal_events and en_sub:
                        # \an5 measures from each line's own middle, so the step
                        # is half the Thai line plus half the English one. Both
                        # halves are taken from the BOOSTED size, which is what
                        # libass actually renders -- Thai faces run line boxes
                        # far taller than their em, so stepping by the em number
                        # left the two lines 6px apart, close enough to read as
                        # collided. The last term is the gap between them.
                        # One line advance below the Thai, which is exactly what
                        # the plain caption gets: libass steps a \N by 1.0 x
                        # Fontsize (parity rule 2.7), and the reveal places the
                        # English itself, so it has to reproduce that step
                        # rather than invent one. Measured against the plain
                        # caption at two faces and two scales -- a formula built
                        # from half-heights and a hand-picked gap came out ~17px
                        # wider and read as a gap in the block.
                        #
                        # \an1 and \an7 measure the Thai from an edge of its
                        # line box, which sits about a descender below (or
                        # above) the ink; \an4 and \an5 measure from its middle.
                        # Converting to the middle first keeps the step honest
                        # across all of them, since the English is centred.
                        if reveal_align == 1:
                            thai_middle = reveal_y - font_size_boosted * 0.5
                        elif reveal_align == 7:
                            thai_middle = reveal_y + font_size_boosted * 0.5
                        else:
                            thai_middle = reveal_y
                        # The English is drawn at en_pct of the Thai size, so
                        # half of each is what separates their centres.
                        en_y = thai_middle + font_size_boosted * (
                            0.5 + (en_pct / 100.0) * 0.5
                        )
                        # Always positioned, never left to the style's margin.
                        # The reveal has moved the Thai line off that margin and
                        # onto its own \pos, so an English line still anchored
                        # by the style lands where the Thai used to be -- on top
                        # of it. Centre it under wherever the reveal actually
                        # put the Thai.
                        en_pos = (
                            f"{{\\an5\\pos({int(round(reveal_x))},{int(round(en_y))})}}"
                        )
                        # en_sub leads with the \N that stacked it under the
                        # Thai; as its own event it starts at its own position.
                        en_body = en_sub[2:] if en_sub.startswith("\\N") else en_sub
                        reveal_events.append(
                            f"Dialogue: 1,{start_t},{end_t},{style},,0,0,0,,"
                            f"{en_pos}{caption_anim}{en_body}"
                        )

            if reveal_events:
                # The reveal's own events carry the outline; the whole-caption
                # shadow is dropped rather than left pre-echoing the unspoken
                # words. Giving each revealed word its own shadow would need a
                # second full set of events per step, for a blur the reveal's
                # outline already covers.
                events.extend(reveal_events)
            else:
                events.extend(shadow_events)
                line_entry = f"Dialogue: 1,{start_t},{end_t},{style},,0,0,0,,{main_pos}{multi_line_metric_tag}{caption_anim}{main_text}"
                events.append(line_entry)
                # The reveal emits its own companion glyphs, timed to the word
                # each one belongs to; these whole-caption ones would duplicate
                # them and show every mark from the cue's first frame.
                for mark_parts in main_marks:
                    events.append(
                        f"Dialogue: 1,{start_t},{end_t},{style},,0,0,0,,"
                        f"{{{caption_mark_position(shadow=False)}}}"
                        f"{caption_mark_overlay(mark_parts, shadow=False)}"
                    )

        # 3. Spec-Bar Overlays (IT vertical: the number goes on screen, not
        # just in the voiceover). These read from the original sentence-level
        # `cues`, not micro_cues -- a spec stays up for the whole line it
        # belongs to, not just one 2-3 word burst. `on_screen` is filled in by
        # pipeline.py from the AI script's per-line overlay text (see
        # ai_bridge.py's `script` task); a line with nothing to show just has
        # an empty/missing value and gets no bar.
        for cue in cues:
            on_screen = (cue.get("on_screen") or "").strip()
            if not on_screen:
                continue
            if " ".join(on_screen.split()).strip().casefold() in product_callout_texts:
                continue
            spec_start = cls._format_ass_time(cue["start"])
            spec_end = cls._format_ass_time(cue["end"])
            spec_from = 110
            spec_to = 100
            spec_anim = f"{{\\fscx{spec_from}\\fscy{spec_from}\\t(0,100,\\fscx{spec_to}\\fscy{spec_to})}}"
            # Layer 2, above the hook banner (1) and captions (0), in case a
            # long spec bar's footprint ever crosses either at the same time.
            # on_screen is AI-script-generated but ultimately derived from
            # scraped product data, so it gets the same override-tag escaping
            # as every other user/scraper-controlled caption text.
            events.append(f"Dialogue: 2,{spec_start},{spec_end},SpecBar,,0,0,0,,{spec_anim}📊 {ass_escape_text(on_screen)}")

        # 4. Custom Text Overlays (Freeform multi-layer text lines)
        if text_items:
            for item in text_items:
                text_ctx = {
                    "video_width": video_width,
                    "video_height": video_height,
                    "base_fs": base_fs,
                    "resolved_font": resolved_font,
                    "font_map": font_map,
                    "caption_color": caption_color,
                    "style_preset": style_preset,
                }
                events.extend(overlay_events(item, text_ctx))

        content = header + "\n".join(events) + "\n"
        out_path.write_text(content, encoding="utf-8")
        return str(out_path), micro_cues

if __name__ == "__main__":
    print("SubtitleEngine ready.")
