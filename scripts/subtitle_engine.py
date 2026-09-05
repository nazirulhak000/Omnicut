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
    ass_glyph_scale,
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
    KINETIC_KEYWORDS,
    KINETIC_KEYWORDS_EN,
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

        # 1.1 If input has no spaces (or very few) and is longer than max_line_len:
        # Segment into natural clauses at conjunctions and word boundaries using PyThaiNLP
        if len(raw_parts) <= 1 and len(clean_text) > max_line_len:
            try:
                from pythainlp.tokenize import word_tokenize
                words = word_tokenize(clean_text, engine="newmm")
                clause_chunks = []
                curr = ""
                conjunctions = {"ว่า", "เพราะ", "ถ้า", "และ", "หรือ", "แต่", "เมื่อ", "มัน", "ที่", "ซึ่ง", "จน", "แล้ว", "คือ"}
                for w in words:
                    if (w in conjunctions and len(curr) >= 16) or (len(curr) + len(w) > max_line_len and len(curr) >= 14):
                        clause_chunks.append(curr)
                        curr = w
                    else:
                        curr += w
                if curr:
                    clause_chunks.append(curr)
                if len(clause_chunks) > 1:
                    raw_parts = clause_chunks
            except Exception:
                pass

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
        # every style below sets Bold=1, so libass/fontconfig picks that
        # family's bold weight itself. See _load_font_family_map().
        font_map = _load_font_family_map()
        resolved_font = font_map.get(font_name, DEFAULT_FONT_FAMILY)
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
Style: TikTokSoftShadow,{resolved_font},{font_size},&H00000000,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,{shadow_outline},0,{alignment},{shadow_margin_l},{shadow_margin_r},{shadow_margin_v},1
Style: TikTokWhite,{resolved_font},{font_size},{primary},&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,{front_outline},0,{alignment},60,60,{margin_v},1
Style: TikTokYellow,{resolved_font},{font_size},&H0000E6FF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,{front_outline},0,2,60,60,420,1
Style: TikTokCyan,{resolved_font},{font_size},&H00FFE600,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,{front_outline},0,2,60,60,420,1
Style: TikTokMinimalPill,{resolved_font},{font_size - 6},{primary},&H000000FF,&H00000000,&HCC000000,1,0,0,0,100,100,0.5,0,3,6,0,{alignment},60,60,{margin_v},1
Style: HookHeader,{hook_font},{hook_fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,6.0,0,8,60,60,260,1
Style: HookHeaderShadow,{hook_font},{hook_fs},&H00000000,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,7.0,0,8,62,58,257,1
Style: HookHeaderPill,{hook_font},{hook_fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,3,12,0,8,60,60,260,1
Style: SpecBar,{resolved_font},{font_size - 12},&H00000000,&H000000FF,&H00000000,&H0000E6FF,1,0,0,0,100,100,0.5,0,3,10,0,9,50,50,380,1
Style: TextOverlayMain,{resolved_font},{base_fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,5.0,2,5,60,60,0,1
Style: TextOverlayPill,{resolved_font},{base_fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,5.0,2,5,60,60,0,1

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
            hook_start = float(hook_overlay.get("start") or 0.0)
            hook_end = float(hook_overlay.get("end") or (hook_start + 3.0))
            hook_duration = max(0.1, hook_end - hook_start)
            hook_tier_texts = [
                str((t or {}).get("text") or "") for t in (hook_overlay.get("tiers") or [])
            ]
            while len(hook_tier_texts) < 3:
                hook_tier_texts.append("")
            hook_brand, hook_model, hook_label = hook_tier_texts[:3]
            motion = _resolve_hook_motion(hook_overlay.get("anim"))
            start_t = cls._format_ass_time(hook_start)
            end_t = cls._format_ass_time(hook_end)
            # The exit window every Out preset animates into. `\t` offsets are
            # relative to an event's own Start (0 for every hook line), so
            # they double as absolute ms. Guarded against a hook shorter than
            # the entry animation ever producing exit_start >= exit_end,
            # which a renderer could choke on.
            exit_end_ms = int(hook_duration * 1000)
            exit_start_ms = max(120, exit_end_ms - 150)
            if exit_start_ms >= exit_end_ms:
                exit_start_ms = max(0, exit_end_ms - 50)

            # (raw text, target scale % of hook_fs, Main-layer colour, tier index)
            # tier index also doubles as the stagger slot (0=brand, 1=model,
            # 2=label) and marks which physical line(s) the accent shape
            # attaches to (tier 1, model).
            #
            # Each tier's colour is independently overridable (a brand with
            # green equity shouldn't be forced to white); an unset tier keeps
            # the poster default it had before -- white wordmark, accent
            # model, muted label.
            # The look comes from a template, overridable field by field, with
            # the older per-tier colour map winning last so a project keeps the
            # colours it was saved with. See scripts/hook_styles.py.
            # Each tier's own look, the same one the canvas resolves. The
            # editor writes these directly now, so a size or an outline the
            # user set is the number that gets burned.
            tier_looks = [
                resolve_look(hook_overlay.get("look"), (t or {}).get("look"))
                for t in (hook_overlay.get("tiers") or [])
            ]
            while len(tier_looks) < 3:
                tier_looks.append(resolve_look(hook_overlay.get("look"), None))

            def tier_colour(idx: int, fallback: str) -> str:
                colour = tier_looks[idx]["color"]
                if colour == ACCENT_COLOR:
                    return fallback
                return ass_colour(colour) or fallback

            brand_colour = tier_colour(0, "&H00FFFFFF")
            # An unset model colour still means "use the caption accent".
            model_colour = tier_colour(1, ass_colour(caption_color) or "&H0000E6FF")
            label_colour = tier_colour(2, "&H00E0E0E0")
            hook_tier_specs = [
                (hook_brand, int(tier_looks[0]["size_pct"]), brand_colour, 0),
                (hook_model, int(tier_looks[1]["size_pct"]), model_colour, 1),
                (hook_label, int(tier_looks[2]["size_pct"]), label_colour, 2),
            ]
            tiers = {"brand": tier_looks[0], "model": tier_looks[1], "label": tier_looks[2]}
            tier_key_by_idx = {0: "brand", 1: "model", 2: "label"}

            # Pass 1: wrap each tier at its OWN char width -- a 130%-scale
            # line needs a narrower wrap than a 58%-scale one, or the brand
            # line runs wider than the frame while the label line wraps too
            # early. wrap_text_for_ass is the same balanced-wrap caption
            # already uses below; the hook banner never called it before.
            tier_lines = []  # (line_text, scale_pct, colour, tier_idx)
            model_last_line = None
            for raw_text, scale_pct, colour, tier_idx in hook_tier_specs:
                text = str(raw_text or "").strip()
                if not text:
                    continue
                if tiers[tier_key_by_idx[tier_idx]]["upper"]:
                    text = text.upper()  # a wordmark reads as one; .upper() is a no-op on Thai
                tier_fs = max(20, int(round(hook_fs * scale_pct / 100)))
                dyn_max_chars = max(8, int(round(2600 / tier_fs)))
                wrapped = cls.wrap_text_for_ass(text, max_chars_per_line=dyn_max_chars)
                lines = wrapped.split("\\N")
                for line in lines:
                    tier_lines.append((line, scale_pct, colour, tier_idx))
                if tier_idx == 1:
                    model_last_line = lines[-1]

            if tier_lines:
                # Pass 2: more than ~4 lines total (e.g. a long brand name
                # wrapping twice) starts crowding the sticker badge
                # (top-right, y=140) and reads as clutter for a short
                # banner -- shrink every tier proportionally instead of
                # letting the block grow unbounded. Floor at 0.7 so it never
                # shrinks past reading as a headline.
                HOOK_COMFORTABLE_LINES = 4
                shrink = max(0.7, min(1.0, HOOK_COMFORTABLE_LINES / len(tier_lines)))
                STAGGER_STEP_MS = 150

                # Line-height factor for the manual vertical cursor. Measured
                # directly off a real ffmpeg+libass render (pixel-scanned ink
                # bands per tier), not guessed -- an initial 1.28 guess put
                # the accent bar a full line too low, under the label instead
                # of the model. If it drifts after a font change, remeasure
                # the same way rather than re-guessing.
                x_center = video_width // 2

                in_builder = HOOK_IN_BUILDERS.get(motion["in"], _in_bounce)
                loop_builder = HOOK_LOOP_BUILDERS.get(motion["loop"], _loop_pulse)
                out_builder = HOOK_OUT_BUILDERS.get(motion["out"], _out_fade)
                is_typewriter = motion["in"] == "typewriter"

                # Pass 3: walk the y-cursor once and resolve every line's
                # size, position and entrance up front. Each line becomes its
                # OWN dialogue event (rather than \N-joined into one shared
                # block) because \move, \frz and \clip are per-event state --
                # slide/wave/shake/glitch/typewriter all need to act on one
                # line without dragging its neighbours along.
                cursor_y = 260  # HookHeader style's MarginV: top edge of the block
                line_records = []
                max_entry_end_ms = 0
                model_line_fs = None
                model_y = None
                for idx, (line, scale_pct, colour, tier_idx) in enumerate(tier_lines):
                    # Two percentages, deliberately: `layout_pct` is the design
                    # intent in em (what the canvas preview draws and what every
                    # width/position here is measured against), while `target`
                    # is what actually goes into scx -- boosted by
                    # TEXT_SCALE_BOOST so libass's own line-box scaling cancels
                    # out and the glyphs land at the em size that was intended.
                    layout_pct = round(scale_pct * shrink)
                    target = round(layout_pct * HOOK_SCALE_BOOST)
                    line_fs = max(20, int(round(hook_fs * layout_pct / 100)))
                    t0_ms = tier_idx * STAGGER_STEP_MS if motion["stagger"] else 0
                    if is_typewriter:
                        # its \clip needs this line's resolved width and y,
                        # which only exist once this walk has placed it
                        in_tag, entry_end_ms, move_dy_in = None, t0_ms + 400, None
                    else:
                        in_tag, entry_end_ms, move_dy_in = in_builder(target, t0_ms)
                    max_entry_end_ms = max(max_entry_end_ms, entry_end_ms)
                    line_records.append({
                        "line": line, "target": target, "line_fs": line_fs, "colour": colour,
                        "tier": tier_key_by_idx[tier_idx],
                        "t0_ms": t0_ms, "in_tag": in_tag, "entry_end_ms": entry_end_ms,
                        "move_dy_in": move_dy_in, "y": cursor_y,
                    })
                    if tier_idx == 1:
                        model_line_fs = line_fs
                        model_y = cursor_y
                    cursor_y += round(line_fs * LINE_HEIGHT_FACTOR)

                    # An accent shape is a layout element, not an overlay:
                    # reserve room for it after the model tier's last line so
                    # the label below never has a bar drawn through it (at
                    # LINE_HEIGHT_FACTOR 1.0 consecutive lines touch exactly,
                    # leaving no natural gap to borrow).
                    is_last_model_line = tier_idx == 1 and (
                        idx + 1 >= len(tier_lines) or tier_lines[idx + 1][3] != 1
                    )
                    if is_last_model_line and motion["accent"] != "none":
                        reserve = 0.80 if motion["accent"] != "badge" else 0.45
                        cursor_y += round(line_fs * reserve)

                # One loop chain shared by every line: it depends only on
                # timing, and starts once the LAST tier has finished entering
                # so a stagger never leaves one line pulsing while another is
                # still flying in.
                loop_tag = loop_builder(max_entry_end_ms, exit_start_ms)

                for rec in line_records:
                    out_tag, move_dy_out = out_builder(exit_start_ms, exit_end_ms, rec["target"])

                    if is_typewriter:
                        half_w = _hook_line_width_px(rec["line"], hook_font, rec["line_fs"])
                        top, bot = rec["y"] - 5, rec["y"] + rec["line_fs"] + 5
                        x_from, x_to = x_center - half_w, x_center + half_w
                        in_tag = (
                            f"\\clip({x_from:.0f},{top},{x_from:.0f},{bot})"
                            f"\\t({rec['t0_ms']},{rec['entry_end_ms']},"
                            f"\\clip({x_from:.0f},{top},{x_to:.0f},{bot}))"
                        )
                    else:
                        in_tag = rec["in_tag"]

                    # \move is a single linear segment, so a line can only
                    # truly slide once: a sliding entrance wins the slot over
                    # a sliding exit, which still fades out in place via
                    # out_tag -- it loses the travel, not the exit.
                    if rec["move_dy_in"] is not None:
                        pos_tag = (
                            f"\\move({x_center},{rec['y'] + rec['move_dy_in']},"
                            f"{x_center},{rec['y']},{rec['t0_ms']},{rec['entry_end_ms']})"
                        )
                    elif move_dy_out is not None:
                        pos_tag = (
                            f"\\move({x_center},{rec['y']},{x_center},{rec['y'] + move_dy_out},"
                            f"{exit_start_ms},{exit_end_ms})"
                        )
                    else:
                        pos_tag = f"\\pos({x_center},{rec['y']})"

                    common = f"\\an8{pos_tag}{in_tag}{loop_tag}{out_tag}"
                    events.append(
                        f"Dialogue: 1,{start_t},{end_t},HookHeaderShadow,,0,0,0,,"
                        f"{{{common}\\blur5\\alpha&H40&}}{rec['line']}"
                    )
                    tier_style = tiers[rec["tier"]]
                    outline_colour = ass_colour(tier_style["outline_color"]) or "&H00000000"
                    # \3c is the outline colour and \bord its width; the Style
                    # carries only a default for both, so a tier that wants a
                    # thick pink edge says so here.
                    edge_tag = (
                        f"\\3c{outline_colour}&"
                        f"\\bord{float(tier_style['outline_px']):.1f}"
                    )
                    # A pill is an object now ({fill, border, padding}), the
                    # same shape a text overlay's badge uses -- it was a bare
                    # colour here and two other things elsewhere.
                    pill = tier_style["pill"] or {}
                    pill_colour = ass_colour(pill.get("fill"))
                    if pill_colour:
                        # A filled box behind the line: BorderStyle 3 paints it
                        # with the outline colour, so the pill colour goes
                        # there and the edge width becomes the box's padding.
                        # The padding follows the tier's own size now, instead
                        # of the flat 12px that stayed put when a tier grew.
                        pill_pad = int(round(hook_fs * float(pill.get("pad_x_em") or 0.342)))
                        edge_tag = f"\\3c{pill_colour}&\\bord{pill_pad}\\shad0"
                        events.append(
                            f"Dialogue: 1,{start_t},{end_t},HookHeaderPill,,0,0,0,,"
                            f"{{{common}{edge_tag}\\c{rec['colour']}&}}{rec['line']}"
                        )
                    events.append(
                        f"Dialogue: 2,{start_t},{end_t},HookHeader,,0,0,0,,"
                        f"{{{common}{edge_tag}\\c{rec['colour']}&}}{rec['line']}"
                    )

                    if motion["loop"] == "lightsweep":
                        sweep = _hook_lightsweep_event(
                            rec["line"], rec["line_fs"], rec["y"], x_center, hook_font,
                            start_t, end_t, max_entry_end_ms, exit_start_ms, exit_end_ms,
                            rec["target"],
                        )
                        if sweep:
                            events.append(sweep)

                if motion["accent"] != "none" and model_last_line and model_line_fs:
                    events.extend(_hook_accent_events(
                        motion["accent"], model_last_line, model_line_fs, model_y, model_colour,
                        x_center, hook_font, start_t, end_t,
                        exit_start_ms, exit_end_ms, motion["stagger"],
                    ))

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
            text = cls.wrap_text_for_ass(cue["text"].strip(), max_chars_per_line=dyn_max_chars)
            if not text:
                continue
            # Sync wrapped text with \\N back into cue object for 100% editor preview parity
            cue["text"] = text

            # Kinetic Pop Animation: Snap in 125% -> Settle 100% (or cue.scale) in 70ms
            cue_scale = float(cue.get("scale", 1.0) or 1.0)
            settle_pct = max(50, min(200, int(round(100 * cue_scale))))
            snap_pct = int(round(settle_pct * 1.25))
            # em intent -> what \fscx has to say for libass to draw it (see
            # TEXT_SCALE_BOOST). The preview keeps using the unboosted numbers.
            settle_pct = int(round(settle_pct * TEXT_SCALE_BOOST))
            snap_pct = int(round(snap_pct * TEXT_SCALE_BOOST))
            anim = f"{{\\fscx{snap_pct}\\fscy{snap_pct}\\t(0,70,\\fscx{settle_pct}\\fscy{settle_pct})}}"
            
            # Check for English Translation
            en_wrapped = ""
            if bilingual and idx < len(en_translations):
                candidate_en = (en_translations[idx] or cue.get("translation", "")).strip()
                if candidate_en and not any(sig in candidate_en for sig in ["Error 500", "500.", "That's an error", "<html"]):
                    cue["translation"] = candidate_en
                    dyn_en_chars = max(26, int(round(4000 / max(20, font_size))))
                    en_wrapped = cls.wrap_en_for_ass(candidate_en, max_chars_per_line=dyn_en_chars)
                else:
                    cue["translation"] = ""

            # The English line sits at 68% of the Thai one; that 68 is an em
            # intent like every other size here, so it takes the same boost.
            en_pct = int(round(68 * TEXT_SCALE_BOOST))
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
            spec_from = int(round(110 * TEXT_SCALE_BOOST))
            spec_to = int(round(100 * TEXT_SCALE_BOOST))
            spec_anim = f"{{\\fscx{spec_from}\\fscy{spec_from}\\t(0,100,\\fscx{spec_to}\\fscy{spec_to})}}"
            # Layer 2, above the hook banner (1) and captions (0), in case a
            # long spec bar's footprint ever crosses either at the same time.
            events.append(f"Dialogue: 2,{spec_start},{spec_end},SpecBar,,0,0,0,,{spec_anim}📊 {on_screen}")

        # 4. Custom Text Overlays (Freeform multi-layer text lines)
        if text_items:
            for item in text_items:
                # A text overlay is a one-tier overlay, so its look resolves
                # exactly the way a banner tier's does -- which is what finally
                # lets one carry a coloured outline, a real font, and caps.
                look = resolve_look(item.get("look"), ((item.get("tiers") or [{}])[0] or {}).get("look"))
                txt = str(((item.get("tiers") or [{}])[0] or {}).get("text") or "").strip()
                if look["upper"]:
                    txt = txt.upper()
                if not txt:
                    continue
                try:
                    start_sec = float(item.get("start", 0.0))
                except (TypeError, ValueError):
                    start_sec = 0.0
                try:
                    end_sec = float(item.get("end", start_sec + 2.5))
                except (TypeError, ValueError):
                    end_sec = start_sec + 2.5
                if end_sec <= start_sec:
                    end_sec = start_sec + 1.0

                start_t = cls._format_ass_time(start_sec)
                end_t = cls._format_ass_time(end_sec)

                if "x" in item and item.get("x") is not None and "y" in item and item.get("y") is not None:
                    try:
                        x_pos = int(round(video_width * float(item["x"])))
                        y_pos = int(round(video_height * float(item["y"])))
                    except (TypeError, ValueError):
                        pos = item.get("position", "middle")
                        y_ratio = TEXT_OVERLAY_POSITIONS.get(pos, 0.50)
                        y_pos = int(round(video_height * y_ratio))
                        x_pos = video_width // 2
                else:
                    pos = item.get("position", "middle")
                    y_ratio = TEXT_OVERLAY_POSITIONS.get(pos, 0.50)
                    y_pos = int(round(video_height * y_ratio))
                    x_pos = video_width // 2

                scale = min(2.5, max(0.4, float(look["size_pct"]) / 100.0))

                colour_value = look["color"]
                if colour_value == ACCENT_COLOR:
                    colour_value = caption_color
                color_hex = ass_colour(colour_value) or "&H00FFFFFF"
                # The outline was a Style-level literal -- one black 5.0 for
                # every overlay, which is why a text overlay could never reach
                # the look a banner template could.
                outline_hex = ass_colour(look["outline_color"]) or "&H00000000"
                outline_px = float(look["outline_px"])
                # The font was written by the inspector and read by nobody:
                # this writer never looked at it and the canvas took the
                # caption's. It is the look's font on both sides now.
                item_font = font_map.get(look["font"], look["font"])
                if item_font not in {f["family"] for f in AssetRegistry.fonts()}:
                    item_font = resolved_font
                pill = look["pill"] or None
                anim = (item.get("anim") or {}).get("in") or "snap"

                dur_ms = int(round((end_sec - start_sec) * 1000))
                exit_start_ms = max(50, dur_ms - 150)
                exit_tag = f"\\t({exit_start_ms},{dur_ms},\\alpha&HFF&)"

                target_scale = int(round(100 * scale * TEXT_SCALE_BOOST))
                anim_tag = ""
                pos_tag = f"\\an5\\pos({x_pos},{y_pos})"

                # Preset names, not kinds: `snap`/`pop_zoom`/`quick_fade`/`rise`
                # are what a text overlay's old pop/zoom/fade/slide are called
                # in the shared table, where the banner's own pop and fade
                # already meant different keyframes. Same numbers as before.
                if anim == "snap":
                    snap_from = int(round(target_scale * 1.25))
                    anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,70,\\fscx{target_scale}\\fscy{target_scale})"
                elif anim == "pop_zoom":
                    snap_from = int(round(target_scale * 1.45))
                    anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,100,\\fscx{target_scale}\\fscy{target_scale})"
                elif anim == "stamp":
                    snap_from = int(round(target_scale * 1.65))
                    anim_tag = f"\\fscx{snap_from}\\fscy{snap_from}\\t(0,80,\\fscx{target_scale}\\fscy{target_scale})"
                elif anim == "quick_fade":
                    anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t(0,150,\\alpha&H00&)"
                elif anim == "rise":
                    pos_tag = f"\\an5\\move({x_pos},{y_pos + 40},{x_pos},{y_pos},0,200)"
                    anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}\\alpha&HFF&\\t(0,200,\\alpha&H00&)"
                else:  # none
                    anim_tag = f"\\fscx{target_scale}\\fscy{target_scale}"

                render_fs = int(round(base_fs * scale))
                line_list = [l.strip() for l in txt.split("\n") if l.strip()]
                clean_lines = "\\N".join(line_list)

                # Layer 3: a rounded pill behind the block, when the look has one
                if pill and line_list:
                    # libass advances one full font size per \N (measured, and
                    # LINE_HEIGHT_FACTOR everywhere else), so the 1.2 this used
                    # made every badge 20% taller than the text it wrapped.
                    line_h = round(render_fs * LINE_HEIGHT_FACTOR)
                    total_h = len(line_list) * line_h
                    max_line_w = 0
                    for l in line_list:
                        w = _measure_text_width_px(l, item_font, render_fs)
                        if w is None:
                            w = int(len(l) * render_fs * 0.55)
                        if w > max_line_w:
                            max_line_w = w
                    pad_x = round(render_fs * float(pill.get("pad_x_em") or 0.6))
                    pad_y = round(render_fs * float(pill.get("pad_y_em") or 0.35))
                    pill_w = max_line_w + pad_x * 2
                    pill_h = total_h + pad_y * 2
                    pill_x = x_pos - pill_w / 2
                    pill_y = y_pos - total_h / 2 - pad_y
                    radius = min(round(pill_h / 2), 28)
                    pill_path = _ass_rounded_pill_path(pill_w, pill_h, radius)

                    # The fill is the look's own colour now, and its alpha
                    # comes off the rgba() the canvas paints -- the two used to
                    # be a named bgStyle here and a colour literal there, which
                    # is how the badge ended up twice as opaque in one of them.
                    pill_hex, pill_opacity = _pill_fill_to_ass(pill.get("fill"))
                    base_alpha = f"&H{int(round((1 - pill_opacity) * 255)):02X}&"

                    if anim == "rise":
                        pill_pos = f"\\an7\\move({pill_x:.0f},{pill_y + 40:.0f},{pill_x:.0f},{pill_y:.0f},0,200)"
                        pill_anim = f"\\alpha&HFF&\\t(0,200,\\alpha{base_alpha})"
                    elif anim == "quick_fade":
                        pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
                        pill_anim = f"\\alpha&HFF&\\t(0,150,\\alpha{base_alpha})"
                    elif anim in ("snap", "pop_zoom", "stamp"):
                        pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
                        dur_anim = 70 if anim == "snap" else (100 if anim == "pop_zoom" else 80)
                        pill_anim = f"\\alpha&HFF&\\t(0,{dur_anim},\\alpha{base_alpha})"
                    else:  # none
                        pill_pos = f"\\an7\\pos({pill_x:.0f},{pill_y:.0f})"
                        pill_anim = f"\\alpha{base_alpha}"

                    # A pill can carry a border (the neon badge is a wash plus
                    # a bright edge). The preview drew one and this writer had
                    # no way to say it, so the badge came back as a flat block.
                    border_hex = ass_colour(pill.get("border")) if pill.get("border") else None
                    edge = f"\\bord3\\3c{border_hex}&" if border_hex else "\\bord0"
                    pill_tag = f"{pill_pos}\\p1{edge}\\shad0\\c{pill_hex}&{pill_anim}{exit_tag}"
                    events.append(f"Dialogue: 3,{start_t},{end_t},TextOverlayMain,,0,0,0,,{{{pill_tag}}}{pill_path}")

                # Layer 4: the glyphs, with the look's own font, outline colour
                # and outline width -- all three were Style-level literals, so
                # a text overlay could never look like anything but the default.
                events.append(
                    f"Dialogue: 4,{start_t},{end_t},TextOverlayMain,,0,0,0,,"
                    f"{{{pos_tag}{anim_tag}\\fn{item_font}\\c{color_hex}&"
                    f"\\3c{outline_hex}&\\bord{outline_px:.1f}{exit_tag}}}{clean_lines}"
                )

        content = header + "\n".join(events) + "\n"
        out_path.write_text(content, encoding="utf-8")
        return str(out_path), micro_cues

if __name__ == "__main__":
    print("SubtitleEngine ready.")
