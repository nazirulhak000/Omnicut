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
    _hook_line_width_px,
    DEFAULT_HOOK_MOTION,
    _resolve_hook_motion,
    _chained_keyframes,
    HOOK_IN_BUILDERS,
    HOOK_LOOP_BUILDERS,
    HOOK_OUT_BUILDERS,
    _in_bounce,
    _in_pop,
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

LINE_HEIGHT_FACTOR = 1.0

# Where the caption block sits: (ASS alignment, vertical margin).
# 2 = bottom centre, 5 = middle centre, 8 = top centre.
CAPTION_POSITIONS = {
    "bottom": (2, 420),
    "middle": (5, 0),
    "top": (8, 260),
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

    @classmethod
    def generate_micro_cues(cls, cues: List[Dict]) -> List[Dict]:
        """
        Converts sentence-level cues into smart clause cues, translating each into English.
        Uses real per-word timestamps (`cue["word_timings"]`, from edge-tts's streaming API
        in voice_engine.py) when available; falls back to proportional character-count
        splitting of the parent cue's duration otherwise -- same as before this existed.
        """
        micro_cues = []
        cue_id = 1

        for c in cues:
            start = c["start"]
            end = c["end"]
            total_dur = max(0.4, end - start)
            text = c["text"].strip()
            if not text:
                continue

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

                # Assign Emojis selectively (only if not already present)
                emoji = ""
                has_emoji = any(cl.startswith(em) for em in ["⚠️", "🔌", "⚡", "❌", "🛒", "🌿", "💧", "🧪", "✨"])
                if not has_emoji:
                    if any(k in cl for k in ["อย่าเพิ่ง", "หยุด", "เตือน", "ห้าม", "ระวัง"]):
                        emoji = "⚠️ "
                    elif any(k in cl for k in ["สารสกัด", "สมุนไพร", "ธรรมชาติ", "ออร์แกนิก"]):
                        emoji = "🌿 "
                    elif any(k in cl for k in ["สรรพคุณ", "ผิวใส", "หน้าเด็ก", "ชุ่มชื้น", "กู้ผิว", "เซรั่ม", "คอลลาเจน", "เนียนนุ่ม"]):
                        emoji = "💧 "
                    elif any(k in cl for k in ["ส่วนผสม", "วิจัย", "ทดสอบ", "อย.", "รับรอง", "หมอ"]):
                        emoji = "🧪 "
                    elif any(k in cl for k in ["จุดเด่น", "ฟังก์ชัน", "ไฮไลต์", "พรีเมียม", "แม่เหล็ก"]):
                        emoji = "✨ "
                    elif any(k in cl for k in ["ชาร์จไว", "เร็ว", "แรง", "สปีด", "fast"]):
                        emoji = "⚡ "
                    elif any(k in cl for k in ["ปัญหา", "พัง", "เบื่อ", "แย่", "ยาก", "สิว", "ฝ้า", "ปวด"]):
                        emoji = "❌ "
                    elif any(k in cl for k in ["พิกัด", "ตะกร้า", "ราคา", "โปร", "สั่งซื้อ", "กดเลย", "ช้อป", "คุ้ม"]):
                        emoji = "🛒 "

                raw_c = f"{emoji}{cl}".strip() if emoji else cl.strip()
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

                micro_cues.append({
                    "id": cue_id,
                    "start": round(cl_start, 3),
                    "end": round(cl_end, 3),
                    "text": cue_text,
                    "translation": cue_trans,
                    "sfx": sfx
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
        video_width: int = VIDEO_WIDTH,
        video_height: int = VIDEO_HEIGHT,
        caption_position: str = "bottom",
        caption_color: str = None,
        caption_scale: float = 1.0,
        text_overlays: Optional[List[Dict[str, Any]]] = None,
        overlays: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Generate TikTok style ASS subtitle file with rapid-fire micro-bursts, 
        aesthetic fonts, and stacked bilingual English subtitles.
        """
        out_path = Path(output_ass_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        micro_cues = cls.generate_micro_cues(cues)

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

        # Dynamic Soft Shadow & Outline metrics (Zero hardcoding: scales with any font, scale, and resolution)
        front_outline = round(max(1.8, font_size * 0.040), 1)
        shadow_outline = round(max(2.2, font_size * 0.050), 1)
        shadow_blur = round(max(2.5, font_size * 0.055), 1)
        shadow_dx = int(round(max(1.0, font_size * 0.030)))
        shadow_dy = int(round(max(1.5, font_size * 0.045)))
        
        shadow_margin_l = 60 + shadow_dx
        shadow_margin_r = 60 - shadow_dx
        shadow_margin_v = margin_v - shadow_dy if alignment in (1, 2, 3) else margin_v + shadow_dy

        header = f"""[Script Info]
Title: TikTok Aesthetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokSoftShadow,{resolved_font},{font_size_boosted},&H00000000,&H00000000,&H00000000,&H00000000,{resolved_bold},0,0,0,100,100,0,0,1,{shadow_outline},0,{alignment},{shadow_margin_l},{shadow_margin_r},{shadow_margin_v},1
Style: TikTokWhite,{resolved_font},{font_size_boosted},{primary},&H000000FF,&H00000000,&H00000000,{resolved_bold},0,0,0,100,100,0,0,1,{front_outline},0,{alignment},60,60,{margin_v},1
Style: TikTokYellow,{resolved_font},{font_size_boosted},&H0000E6FF,&H000000FF,&H00000000,&H00000000,{resolved_bold},0,0,0,100,100,0,0,1,{front_outline},0,2,60,60,420,1
Style: TikTokCyan,{resolved_font},{font_size_boosted},&H00FFE600,&H000000FF,&H00000000,&H00000000,{resolved_bold},0,0,0,100,100,0,0,1,{front_outline},0,2,60,60,420,1
Style: TikTokMinimalPill,{resolved_font},{int(round((font_size - 6) * TEXT_SCALE_BOOST))},{primary},&H000000FF,&H00000000,&HCC000000,{resolved_bold},0,0,0,100,100,0,0,3,6,0,{alignment},60,60,{margin_v},1
Style: HookHeader,{hook_font},{hook_fs_boosted},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,{hook_bold},0,0,0,100,100,0,0,1,6.0,0,8,60,60,260,1
Style: HookHeaderShadow,{hook_font},{hook_fs_boosted},&H00000000,&H00000000,&H00000000,&H00000000,{hook_bold},0,0,0,100,100,0,0,1,7.0,0,8,62,58,257,1
Style: HookHeaderPill,{hook_font},{hook_fs_boosted},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,{hook_bold},0,0,0,100,100,0,0,3,12,0,8,60,60,260,1
Style: SpecBar,{resolved_font},{int(round((font_size - 12) * TEXT_SCALE_BOOST))},&H00000000,&H000000FF,&H00000000,&H0000E6FF,{resolved_bold},0,0,0,100,100,0,0,3,10,0,9,50,50,380,1
Style: TextOverlayMain,{resolved_font},{base_fs_boosted},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,{resolved_bold},0,0,0,100,100,0,0,1,5.0,2,5,60,60,0,1
Style: TextOverlayPill,{resolved_font},{base_fs_boosted},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,{resolved_bold},0,0,0,100,100,0,0,1,5.0,2,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []

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
            dyn_max_chars = max(24, int(round(3100 / max(20, font_size))))
            # cue["text"] is caption text the AI script/translator produced from
            # scraper- and user-controlled product data -- a literal `{`/`}`
            # or `\` in it must render as a literal character, never open an
            # ASS override block (see ass_escape_text). Escaped BEFORE
            # wrapping/highlighting so those only ever see plain text and add
            # their own well-formed \N / {\c...} sequences on top.
            text = cls.wrap_text_for_ass(ass_escape_text(cue["text"].strip()), max_chars_per_line=dyn_max_chars)
            if not text:
                continue
            # Sync wrapped (but NOT escaped) text back into cue object for
            # 100% editor preview parity -- this dict is also what a re-roll
            # feeds back into generate_ass() as ctx.cues, so storing the
            # escaped form here would double-escape on every subsequent run.
            cue["text"] = cls.wrap_text_for_ass(cue["text"].strip(), max_chars_per_line=dyn_max_chars)

            # Kinetic Pop Animation: Snap in 125% -> Settle 100% (or cue.scale) in 70ms
            cue_scale = float(cue.get("scale", 1.0) or 1.0)
            settle_pct = max(50, min(200, int(round(100 * cue_scale))))
            snap_pct = int(round(settle_pct * 1.25))
            anim = f"{{\\fscx{snap_pct}\\fscy{snap_pct}\\t(0,70,\\fscx{settle_pct}\\fscy{settle_pct})}}"
            
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
                    cue["translation"] = ""

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
                en_sub = f"\\N{{\\fscx{en_pct}\\fscy{en_pct}\\c&H00EAEAEA&}}{en_highlighted}"
            else:
                highlighted_text = cls.apply_kinetic_highlighting(text, primary_color_ass=primary, custom_keywords=proj_keywords)
                if "{\\c" in highlighted_text:
                    m = re.search(r"\{\\c(&H[0-9A-Fa-f]+&)\}", highlighted_text)
                    if m:
                        clean_th = re.sub(r"\{\\c&H[0-9A-Fa-f]+&\}", "", text)
                        highlighted_text = f"{{\\c{m.group(1)}}}{clean_th}"
                en_sub = ""

            style = "TikTokMinimalPill" if is_pill_mode else "TikTokWhite"

            pos_override = ""
            if "x" in cue or "y" in cue:
                norm_x = float(cue.get("x", 0.50))
                norm_y = float(cue.get("y", 0.78125))
                px_x = int(round(video_width * norm_x))
                px_y = int(round(video_height * norm_y))
                pos_override = f"\\an5\\pos({px_x},{px_y})"

            # Layer 0: Natural Soft Feathered Shadow (Gaussian Blur matching Canvas preview)
            if not is_pill_mode:
                en_sub_shadow = f"\\N{{\\fscx{en_pct}\\fscy{en_pct}}}{en_wrapped}" if en_wrapped else ""
                shadow_tag = f"{{\\blur{shadow_blur}\\alpha&H38&}}"
                shadow_pos = f"{{{pos_override}}}" if pos_override else ""
                events.append(f"Dialogue: 0,{start_t},{end_t},TikTokSoftShadow,,0,0,0,,{shadow_pos}{anim}{shadow_tag}{text}{en_sub_shadow}")

            # Layer 1: Crisp Foreground Text with dynamic kinetic highlights
            main_pos = f"{{{pos_override}}}" if pos_override else ""
            line_entry = f"Dialogue: 1,{start_t},{end_t},{style},,0,0,0,,{main_pos}{anim}{highlighted_text}{en_sub}"
            events.append(line_entry)

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
                }
                events.extend(overlay_events(item, text_ctx))

        content = header + "\n".join(events) + "\n"
        out_path.write_text(content, encoding="utf-8")
        return str(out_path), micro_cues

if __name__ == "__main__":
    print("SubtitleEngine ready.")
