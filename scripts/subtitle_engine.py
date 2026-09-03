"""
TikTok Style Subtitle Generator (Advanced SubStation Alpha .ass)
Produces rapid-fire 2-3 word micro-burst subtitles with Kanit-Black font, emojis, and pop animation.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import FONTS_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from scripts.asset_registry import AssetRegistry

TYPOGRAPHY_PRESETS_PATH = FONTS_DIR.parent / "Templates" / "typography_presets.json"
DEFAULT_FONT_FAMILY = "IBM Plex Sans Thai"

# Backward-compat aliases for UI ids that don't match a typography_presets.json
# entry's own font_name/id (old space-free spellings, and capsule_pill's
# display name). Anything not found here or in the presets file falls back
# to DEFAULT_FONT_FAMILY, so an unrecognized font_name never errors.
_LEGACY_FONT_ALIASES = {
    "IBMPlex": "IBM Plex Sans Thai",
    "ibm_tech": "IBM Plex Sans Thai",
    "ChakraPetch": "Chakra Petch",
    "Minimal Dark Capsule Pill": "capsule_pill",
}


def _load_font_family_map() -> Dict[str, str]:
    """
    UI font_name -> real embedded font family, built from
    typography_presets.json (each preset's `id` and `font_name`) resolved
    against AssetRegistry's fontTools-verified family names, not guessed
    from a filename.

    Every ASS style here already sets Bold=1, so libass/fontconfig picks the
    bold weight of whichever family this resolves to -- naming the family is
    enough, the style doesn't need a specific weight-suffixed name.
    """
    family_by_filename = {f["name"]: f["family"] for f in AssetRegistry.fonts()}
    font_map: Dict[str, str] = {}

    try:
        presets = json.loads(TYPOGRAPHY_PRESETS_PATH.read_text(encoding="utf-8"))["presets"]
    except (OSError, json.JSONDecodeError, KeyError):
        presets = []

    for preset in presets:
        family = family_by_filename.get(preset.get("font_file", ""), DEFAULT_FONT_FAMILY)
        font_map[preset["id"]] = family
        font_map[preset["font_name"]] = family

    # Every real family on disk maps to itself, not just the 5 that have a
    # typography_presets.json entry -- so a font_name picker built straight
    # off AssetRegistry.fonts() (e.g. "Tahoma", "Noto Sans Thai") works too,
    # not only the curated preset ids.
    for family in family_by_filename.values():
        font_map.setdefault(family, family)

    for alias, target in _LEGACY_FONT_ALIASES.items():
        font_map[alias] = font_map.get(target, DEFAULT_FONT_FAMILY)

    return font_map


# Default hook-banner motion: every effect on. Individual toggles arrive from
# the UI as a partial dict (only the keys the user unchecked) -- missing keys
# fall back to True here rather than to a bare `.get(k, True)` scattered
# through the animation code below, so there is exactly one place that
# defines "what happens when nothing was specified".
DEFAULT_HOOK_MOTION = {"bounce": True, "stagger": True, "pulse": True, "underline": True}


def _resolve_hook_motion(hook_motion: Optional[Dict[str, bool]]) -> Dict[str, bool]:
    resolved = dict(DEFAULT_HOOK_MOTION)
    if hook_motion:
        for k in DEFAULT_HOOK_MOTION:
            if k in hook_motion and hook_motion[k] is not None:
                resolved[k] = bool(hook_motion[k])
    return resolved


def _hook_entry_anim(target_scale_pct: float, t0_ms: int, bounce: bool) -> Tuple[str, int]:
    """
    ASS \\t keyframe chain animating a hook-tier line's \\fscx/\\fscy from its
    entry pose up to `target_scale_pct`, starting at `t0_ms` (the tier's
    stagger offset). Returns (tag_string, entry_end_ms) so the caller knows
    when this tier settles -- pulse must not start before every tier has.

    bounce=True: overshoot/undershoot/settle (elastic feel), ~450ms.
    bounce=False: the original single-lerp pop, ~120ms, just shifted by t0.
    """
    target = round(target_scale_pct)
    if not bounce:
        entry_from = round(target * 1.15)
        end_ms = t0_ms + 120
        tag = f"\\fscx{entry_from}\\fscy{entry_from}\\t({t0_ms},{end_ms},\\fscx{target}\\fscy{target})"
        return tag, end_ms

    over = round(target * 1.25)
    under = round(target * 0.92)
    settle_over = round(target * 1.05)
    t1, t2, t3, t4 = t0_ms, t0_ms + 150, t0_ms + 280, t0_ms + 380
    end_ms = t0_ms + 450
    entry_from = round(target * 0.6)  # starts small, snaps up into the overshoot
    tag = (
        f"\\fscx{entry_from}\\fscy{entry_from}"
        f"\\t({t1},{t2},\\fscx{over}\\fscy{over})"
        f"\\t({t2},{t3},\\fscx{under}\\fscy{under})"
        f"\\t({t3},{t4},\\fscx{settle_over}\\fscy{settle_over})"
        f"\\t({t4},{end_ms},\\fscx{target}\\fscy{target})"
    )
    return tag, end_ms


def _hook_pulse_keyframes(start_ms: int, exit_start_ms: int) -> str:
    """
    Breathing alpha oscillation (opaque <-> dim) filling the hold period, as
    a chain of \\t alpha keyframes. Half-cycle = 350ms (full pulse ~700ms).
    Emits nothing if less than one half-cycle actually fits -- a stub
    fragment would read as a single flicker, not a pulse.
    """
    HALF = 350
    segs = []
    t = start_ms
    dim_next = True
    while t + HALF <= exit_start_ms:
        alpha = "&H25&" if dim_next else "&H00&"
        segs.append(f"\\t({t},{t + HALF},\\alpha{alpha})")
        t += HALF
        dim_next = not dim_next
    return "".join(segs)


def _measure_text_width_px(text: str, resolved_font: str, font_size_px: int) -> Optional[int]:
    """
    Real rendered width of `text` at `font_size_px` in the family ASS will
    actually draw it in, via the same physical font files AssetRegistry
    already indexes (family -> path), not a filename guess. Returns None if
    that family has no resolvable file on disk -- callers fall back to a
    char-count estimate rather than dropping the caller's feature.
    """
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    try:
        family_to_path = {f["family"]: f["path"] for f in AssetRegistry.fonts()}
        font_path = family_to_path.get(resolved_font)
        if not font_path:
            return None
        bbox = ImageFont.truetype(font_path, font_size_px).getbbox(text)
        return int(bbox[2] - bbox[0])
    except Exception:
        return None

# Where the caption block sits: (ASS alignment, vertical margin).
# 2 = bottom centre, 5 = middle centre, 8 = top centre.
CAPTION_POSITIONS = {
    "bottom": (2, 420),
    "middle": (5, 0),
    "top": (8, 260),
}


def ass_colour(hex_colour: str) -> str:
    """#RRGGBB -> &H00BBGGRR. Returns "" for anything unparseable."""
    if not hex_colour:
        return ""
    value = str(hex_colour).strip().lstrip("#")
    if len(value) != 6:
        return ""
    try:
        r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return ""
    return f"&H00{b:02X}{g:02X}{r:02X}"


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

    @classmethod
    def wrap_text_for_ass(cls, text: str, max_chars_per_line: int = 40) -> str:
        """
        Wraps long Thai text into multiple balanced lines using ASS \\N,
        preventing single-line horizontal font compression or overflow.
        """
        clean = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', text)).strip().replace("\r", "")
        if not clean or "\\N" in clean or "\n" in clean or len(clean) <= max_chars_per_line:
            return clean.replace("\n", "\\N")

        try:
            from pythainlp.tokenize import word_tokenize
            raw_words = word_tokenize(clean, engine="newmm")
        except Exception:
            raw_words = clean.split(" ")

        # Glue Thai grammatical prefixes so they never hang alone at line ends
        prefixes = {"ผู้", "การ", "ความ", "นัก", "ชาว", "จาก"}
        words = []
        i = 0
        while i < len(raw_words):
            w = raw_words[i]
            if w in prefixes and i + 1 < len(raw_words):
                words.append(w + raw_words[i + 1])
                i += 2
            else:
                words.append(w)
                i += 1

        # If length fits in 2 balanced lines:
        if len(clean) <= max_chars_per_line * 2 and len(words) > 2:
            target_mid = len(clean) / 2.0
            best_idx = 1
            best_diff = 99999
            accum = 0
            for idx, w in enumerate(words[:-1]):
                accum += len(w)
                diff = abs(accum - target_mid)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = idx + 1
            l1 = "".join(words[:best_idx]).strip()
            l2 = "".join(words[best_idx:]).strip()
            return f"{l1}\\N{l2}"

        # Otherwise chunk greedily
        lines = []
        curr = ""
        for w in words:
            if len(curr) + len(w) > max_chars_per_line and len(curr) >= 12:
                lines.append(curr)
                curr = w
            else:
                curr += w
        if curr:
            lines.append(curr)

        return "\\N".join(lines) if len(lines) > 1 else clean

    @classmethod
    def wrap_en_for_ass(cls, text: str, max_chars_per_line: int = 58) -> str:
        """Wraps long English subtitles neatly at word boundaries."""
        clean = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', text)).strip().replace("\r", "").replace("\n", " ")
        if len(clean) <= max_chars_per_line:
            return clean
        words = clean.split(" ")
        lines = []
        curr = ""
        for w in words:
            if len(curr) + len(w) + 1 > max_chars_per_line and len(curr) >= 14:
                lines.append(curr)
                curr = w
            else:
                curr = f"{curr} {w}".strip()
        if curr:
            lines.append(curr)
        return "\\N".join(lines) if len(lines) > 1 else clean

    # Dynamic Kinetic Highlighting keywords (ASS color mapped)
    # 🟡 &H0000E6FF& = Neon Yellow (Pain points, prices, deals, primary punch)
    # 🔵 &H00FFE600& = Electric Cyan (Features, tech, ergonomics, certifications)
    # 🔴 &H00303BFF& = Alert Red (Urgency, warnings)
    KINETIC_KEYWORDS: Dict[str, List[str]] = {
        "&H0000E6FF&": [  # 🟡 Neon Yellow (Pain points, prices, deals, primary punch, positive reactions)
            # 1. Physical Discomfort & Pain Points
            "ออฟฟิศซินโดรม", "ปวดข้อมือ", "ปวดหลัง", "ปวดคอ", "ปวดหัว", "ปวดไหล่", "ปวดขา", "ปวดเมื่อย",
            "ปวดมือ", "ปวดตัว", "ปวด", "เมื่อยล้า", "เมื่อย", "ทรมาน", "เหนื่อยล้า", "เหนื่อย",
            # 2. Tech & Everyday Frustrations
            "สายพันกัน", "สายขาด", "แบตหมดไว", "แบตเสื่อม", "กระตุก", "เครื่องค้าง", "ค้าง", "ช้ามาก", "ช้า",
            "พังง่าย", "พัง", "หักง่าย", "หัก", "เสียเงินฟรี", "เสียดายเงิน", "เสีย", "หลุดบ่อย", "หลุด",
            # 3. Beauty, Skin & Personal Care Problems
            "สิวบุก", "สิวเห่อ", "สิวขึ้น", "เป็นสิว", "รอยสิว", "รอยดำ", "รอยแดง", "หน้ามัน", "หน้าหมอง", "หมองคล้ำ",
            "ผิวแห้ง", "ผิวลอก", "เหนียวเหนอะหนะ", "เหนอะหนะ", "คราบฝังลึก", "สกปรก", "กลิ่นอับ", "เหม็นอับ", "เหม็น",
            # 4. Fashion, Body & Confidence
            "อึดอัด", "แน่นพุง", "พุงยื่น", "ขาใหญ่", "ดูอ้วน", "เชยๆ", "เชย", "ล้าสมัย", "ไม่มั่นใจ", "ไม่สวย",
            "ปัญหา", "ยุ่งยาก", "เสียเวลา", "เปลืองแรง", "เปลืองเงิน", "หงุดหงิด",
            # 5. Price, Deals, Vouchers & E-Commerce CTA
            "ราคาพิเศษ", "ลดราคา", "ลดกระหน่ำ", "ลดแรง", "ดีลพิเศษ", "ดีลลับ", "โปรเด็ด", "โปรแรง", "โปรโมชั่น",
            "แฟลชเซล", "flash sale", "โค้ดลด", "โค้ดลับ", "คูปอง", "ส่งฟรี", "1 แถม 1", "หนึ่งแถมหนึ่ง",
            "ของแถม", "แจกฟรี", "ฟรี", "บาท", "หลักสิบ", "หลักร้อย", "ราคาดี", "ราคาโดน", "ถูกและดี",
            "ถูกสุดๆ", "ถูกมาก", "คุ้มสุดๆ", "คุ้มค่า", "คุ้มราคา", "เกินคุ้ม", "คุ้ม", "ประหยัด", "ตกใจราคา",
            "ตะกร้าส้ม", "ตะกร้าซ้ายล่าง", "ตะกร้า", "ใส่ตะกร้า", "จิ้มตะกร้า", "จิ้มเลย", "จิ้มตรงนี้", "กดตรงนี้",
            "พิกัดในคอมเมนต์", "พิกัดในโปรไฟล์", "พิกัด", "ปักหมุด", "อย่ารอ", "อย่าช้า", "ช้าหมด",
            "รีบตำ", "รีบจัด", "ด่วนเลย", "ด่วน", "ต้องมี", "ของมันต้องมี", "ขาดไม่ได้",
            # 6. Viral Praise & Reviewer Hype
            "ป้ายยา", "ตัวท็อป", "ตัวแม่", "ยืนหนึ่ง", "ตัวตึง", "ของดีบอกต่อ", "ใช้ดีบอกต่อ", "ของดี",
            "ดีจริง", "ดูดีมาก", "ดีมาก", "ดีเกินคาด", "ดีเกินราคา", "ว้าวมาก", "ว้าว", "ตาแตก", "ตะลึง",
            "สุดปัง", "ปังมาก", "จึ้งมาก", "จึ้ง", "เลิศมาก", "เลิศ", "เอาเรื่อง", "ของแทร่", "เปลี่ยนชีวิต",
            "ยกระดับ", "หลงรักเลย", "หลงรัก", "ชอบมาก", "ติดใจ", "ไม่ผิดหวัง", "ไม่จกตา", "รีวิวจริง",
            "ใช้จริง", "หมดปัญหา", "ลืมแบบเก่าไปเลย", "โคตรดี", "โคตรคุ้ม", "ฟินมาก", "ช็อค", "น่ารักกว่าในรูป", "ของที่รอคอย"
        ],
        "&H00FFE600&": [  # 🔵 Electric Cyan (Features, tech, ergonomics, certifications, comfort)
            # 1. Tech, Gadgets & Hardware
            "Logitech Wave Keys", "Logitech", "Wave Keys", "คีย์บอร์ดในฝัน", "คีย์บอร์ด", "ไร้สาย", "บลูทูธ",
            "แม่เหล็ก", "แรงดูดสูง", "ดูดแน่น", "540 องศา", "360 องศา", "ชาร์จไว", "ฟาสชาร์จ", "66W", "100W",
            "แบตอึด", "แบตทน", "ทนทาน", "แข็งแรง", "ประกันศูนย์", "ของแท้", "แท้ 100%", "จอสวย", "จอลื่น",
            "120Hz", "คมชัด", "กล้องชัด", "เสียงดี", "เบสแน่น", "ตัดเสียงรบกวน", "กันน้ำ", "ชิปเร็ว",
            "ลื่นไหล", "ไม่สะดุด", "เชื่อมต่อง่าย", "เสียบปุ๊บติดปั๊บ", "พกพาสะดวก", "น้ำหนักเบา", "กะทัดรัด",
            "ปรับระดับได้", "พับเก็บได้", "ประหยัดพื้นที่", "ประกอบง่าย", "ใช้งานง่าย",
            # 2. Ergonomics, Comfort, Softness & Apparel
            "สรีรศาสตร์", "เมมโมรี่โฟม", "ที่รองข้อมือ", "พิมพ์สบาย", "นั่งสบาย", "นอนสบาย", "ใส่สบาย",
            "สบายมาก", "นุ่มสบาย", "สบายมือ", "สบายหลัง", "สบายตา", "สบายตัว", "สบาย", "นุ่มนิ่ม", "นุ่มฟู",
            "นุ่มมาก", "นุ่มๆ", "นุ่ม", "ยืดหยุ่น", "สัมผัสนุ่ม", "ไม่ระคายเคือง", "ไม่บาดผิว", "ทรงสวย",
            "ทรงเป๊ะ", "พอดีตัว", "เข้ารูป", "ทิ้งตัวสวย", "พรางหุ่น", "เก็บพุง", "ระบายอากาศ", "ไม่อับชื้น",
            "ไม่ร้อน", "เย็นสบาย", "มินิมอล", "ดีไซน์แบบคลื่นๆ", "แบบคลื่นๆ", "คลื่น", "ดีไซน์สวย",
            # 3. Skincare, Beauty & Quality Efficacy
            "ผิวฉ่ำวาว", "ผิวฉ่ำน้ำ", "ผิวฉ่ำ", "หน้าใส", "ผิวเนียน", "ผิวกระจก", "ผิวนุ่มเด้ง", "หน้าเด็ก",
            "ซึมไว", "ซึมเร็ว", "แห้งไว", "บางเบา", "ไม่เหนอะหนะ", "คุมมัน", "ผิวกระชับ", "รูขุมขนกระชับ",
            "กลิ่นหอม", "หอมละมุน", "หอมฟุ้ง", "ติดทน", "ติดทนนาน", "ไม่ติดแมสก์", "กันเหงื่อ", "กันน้ำกันเหงื่อ",
            "ปกปิดเนียน", "กลบเนียน", "ไม่วอก", "ไม่ลอย", "อ่อนโยน", "แพ้ง่ายใช้ได้", "สารสกัดธรรมชาติ",
            "ออร์แกนิก", "พรีเมียมสุดๆ", "พรีเมียม", "หรูหรา", "ดูแพง", "สะอาดหมดจด", "ฆ่าเชื้อ", "กรองฝุ่น",
            "รับรอง", "ผู้เชี่ยวชาญ", "แพทย์ผิวหนัง", "สุขภาพดี", "ปลอดภัย"
        ],
        "&H00303BFF&": [  # 🔴 Alert Red (Urgency, warnings)
            "อย่าเพิ่งซื้อ", "อย่าเพิ่ง", "หยุดก่อน", "หยุดดูคลิปนี้", "ฟังทางนี้", "เตือนภัย", "เตือน",
            "ระวังของปลอม", "ระวัง", "อันตราย", "เสี่ยง", "ห้ามทำ", "อย่าหาทำ", "อย่าพลาด",
            "ห้ามพลาด", "ห้ามเลื่อนผ่าน", "ของปลอมระบาด", "ซื้อผิดรุ่น", "ดูให้จบ", "ข้อเสีย", "สิ่งที่ควรรู้"
        ]
    }

    # Dynamic Kinetic Highlighting keywords for English (ASS color mapped)
    KINETIC_KEYWORDS_EN: Dict[str, List[str]] = {
        "&H0000E6FF&": [  # 🟡 Neon Yellow (Pain points, prices, deals, primary punch, positive reactions)
            # 1. Pain Points & Discomfort
            "office syndrome", "wrist pain", "back pain", "neck pain", "shoulder pain", "headache", "leg pain",
            "body pain", "hand hurts", "hurts", "painful", "pain", "tight", "sore", "exhausted",
            "tiring", "tired", "suffering",
            # 2. Product/Usage Frustrations
            "tangled", "broken cord", "dead battery", "low battery", "laggy", "lagging", "freezing", "too slow", "slow",
            "breaks easily", "broken", "waste of money", "waste of time", "wasted", "annoying",
            "acne breakout", "breakouts", "pimples", "dark spots", "redness", "oily skin", "dull skin",
            "dry skin", "peeling skin", "sticky", "greasy", "deep stains", "dirty", "bad odor", "smelly",
            "uncomfortable", "stuffy", "bloated", "tight fit", "outdated", "unconfident", "insecure",
            "problems", "problem", "frustrating", "troublesome", "not sure",
            # 3. Price, Promotions & Commerce CTA
            "special price", "huge discount", "discount", "special deal", "secret deal", "best promo", "promotion",
            "flash sale", "promo code", "voucher", "coupon", "free shipping", "buy 1 get 1", "bogo",
            "free gift", "giveaway", "free", "baht", "super cheap", "cheap", "affordable", "best price",
            "best value", "great value", "worth every penny", "worth it", "save money", "shocking price",
            "yellow basket", "orange basket", "cart", "add to cart", "click cart", "click now", "click here",
            "pinned link", "link in bio", "coordinates", "don't wait", "don't delay", "almost gone",
            "buy now", "grab it now", "hurry up", "must have", "essential",
            # 4. Viral Praise & Sensational Reactions
            "holy grail", "game changer", "life-changing", "top tier", "the best", "highly recommend",
            "really good", "looks really good", "looks good", "so good", "very good", "good", "exceeded expectations",
            "unbelievable", "very wow", "wow", "mind blowing", "stunning", "gorgeous", "slay",
            "aesthetic", "next level", "fell in love", "obsessed", "love it", "no regret", "won't be disappointed",
            "real review", "tried and tested", "problem solved", "insanely good", "super worth it", "so satisfying",
            "much cuter", "long-awaited", "recommend"
        ],
        "&H00FFE600&": [  # 🔵 Electric Cyan (Features, tech, ergonomics, certifications, comfort)
            # 1. Tech, Hardware & Gadget Specs
            "logitech wave keys", "wave keys", "logitech", "dream keyboard", "keyboard", "wireless", "bluetooth",
            "magnetic", "strong magnet", "540 degrees", "360 degrees", "fast charging", "quick charge", "66w", "100w",
            "long battery", "battery life", "durable", "sturdy", "warranty", "genuine", "authentic", "smooth screen",
            "120hz", "crystal clear", "sharp camera", "great sound", "deep bass", "noise cancelling", "waterproof",
            "fast chip", "ultra smooth", "easy connect", "plug and play", "portable", "lightweight", "compact",
            "adjustable", "foldable", "space saving", "easy to assemble", "easy to use",
            # 2. Comfort, Ergonomics & Fabric/Design
            "ergonomic", "ergonomics", "memory foam", "wrist rest", "typing comfortable", "sit comfortably",
            "comfortable fit", "comfortable", "comfy", "super comfy", "soft and comfy", "extra soft", "pillow soft",
            "very soft", "soft", "flexible", "gentle touch", "non-irritating", "flattering fit",
            "perfect fit", "slim fit", "tummy control", "breathable", "airy", "cool and fresh",
            "minimalist", "minimal", "wavy design", "wavy", "sleek design", "beautiful design",
            # 3. Skincare, Beauty & Clean Living
            "glass skin", "glowy skin", "glowing skin", "clear skin", "smooth skin", "bouncy skin", "youthful",
            "fast absorbing", "quick absorb", "quick drying", "lightweight texture", "non-sticky", "non-greasy", "oil control",
            "firming", "pore tightening", "nice scent", "pleasant smell", "long lasting", "transfer-proof", "sweat-proof",
            "water resistant", "full coverage", "natural finish", "no white cast", "gentle formula", "sensitive skin friendly",
            "natural extracts", "organic", "very premium", "premium", "luxury", "looks expensive",
            "deep clean", "antibacterial", "hepa filter", "certified", "experts", "expert",
            "dermatologist", "healthy", "safe"
        ],
        "&H00303BFF&": [  # 🔴 Alert Red (Urgency, warnings)
            "don't buy yet", "don't buy", "stop scrolling", "wait a minute", "listen to this", "urgent warning", "warning",
            "beware of fake", "beware", "danger", "risky", "don't do this", "don't miss out",
            "don't miss", "watch till the end", "counterfeit", "fake products", "cons", "must know",
            "look at this", "watch this", "warn", "stop"
        ]
    }

    @classmethod
    def apply_kinetic_highlighting(
        cls,
        text: str,
        primary_color_ass: str = "&H00FFFFFF&",
        color_hint: Optional[str] = None,
        custom_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Scans text for power keywords with 3-tier intelligence:
        Tier 1: Explicit manual markers *keyword* or [keyword] (100% user & AI control)
        Tier 2: Dynamic Project Keywords (Product names, brand, specific hook keywords)
        Tier 3: Reviewer Mega-Dictionary (500+ affiliate phrases across all niches)
        """
        if not text:
            return text

        clean_primary = primary_color_ass if primary_color_ass.endswith("&") else f"{primary_color_ass}&"
        result = text
        chosen_color = color_hint or "&H0000E6FF&"  # Default to Neon Yellow

        # Tier 1: Manual Markers (*word* or [word])
        marker_pattern = re.compile(r"(\*([^*]+)\*|\[([^\]]+)\])")
        if marker_pattern.search(result):
            def _replace_marker(m):
                kw = m.group(2) or m.group(3)
                return f"{{\\c{chosen_color}}}{kw}{{\\c{clean_primary}}}"
            return marker_pattern.sub(_replace_marker, result)

        if "{\\c" in text:
            return text

        # Tier 2: Dynamic Project Keywords (injected into Electric Cyan features)
        if custom_keywords:
            for ckw in sorted(custom_keywords, key=len, reverse=True):
                if len(ckw) >= 2 and ckw in result:
                    cyan_color = color_hint or "&H00FFE600&"
                    replacement = f"{{\\c{cyan_color}}}{ckw}{{\\c{clean_primary}}}"
                    return result.replace(ckw, replacement, 1)

        # Tier 3: Reviewer Mega-Dictionary
        color_order = [color_hint] + [c for c in cls.KINETIC_KEYWORDS if c != color_hint] if color_hint else list(cls.KINETIC_KEYWORDS.keys())
        for color_tag in color_order:
            kw_list = cls.KINETIC_KEYWORDS.get(color_tag, [])
            for kw in sorted(kw_list, key=len, reverse=True):
                if kw in result and f"{{\\c{color_tag}}}" not in result:
                    replacement = f"{{\\c{color_tag}}}{kw}{{\\c{clean_primary}}}"
                    result = result.replace(kw, replacement, 1)
                    return result

        return result

    @classmethod
    def apply_kinetic_highlighting_en(
        cls,
        text: str,
        primary_color_ass: str = "&H00EAEAEA&",
        color_hint: Optional[str] = None,
        custom_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Scans English text with 3-tier intelligence matching Thai.
        """
        if not text:
            return text

        clean_primary = primary_color_ass if primary_color_ass.endswith("&") else f"{primary_color_ass}&"
        result = text
        chosen_color = color_hint or "&H0000E6FF&"

        # Tier 1: Manual Markers (*word* or [word])
        marker_pattern = re.compile(r"(\*([^*]+)\*|\[([^\]]+)\])")
        if marker_pattern.search(result):
            def _replace_marker(m):
                kw = m.group(2) or m.group(3)
                return f"{{\\c{chosen_color}}}{kw}{{\\c{clean_primary}}}"
            return marker_pattern.sub(_replace_marker, result)

        if "{\\c" in text:
            return text

        # Tier 2: Dynamic Project Keywords
        if custom_keywords:
            for ckw in sorted(custom_keywords, key=len, reverse=True):
                if len(ckw) >= 2:
                    pattern = re.compile(rf"(?i)\b{re.escape(ckw)}\b")
                    match = pattern.search(result)
                    if match:
                        matched_str = match.group(0)
                        start, end = match.span()
                        cyan_color = color_hint or "&H00FFE600&"
                        return result[:start] + f"{{\\c{cyan_color}}}{matched_str}{{\\c{clean_primary}}}" + result[end:]

        # Tier 3: Reviewer Mega-Dictionary
        color_order = [color_hint] + [c for c in cls.KINETIC_KEYWORDS_EN if c != color_hint] if color_hint else list(cls.KINETIC_KEYWORDS_EN.keys())
        for color_tag in color_order:
            kw_list = cls.KINETIC_KEYWORDS_EN.get(color_tag, [])
            for kw in sorted(kw_list, key=len, reverse=True):
                pattern = re.compile(rf"(?i)\b{re.escape(kw)}\b")
                match = pattern.search(result)
                if match and f"{{\\c{color_tag}}}" not in result:
                    matched_str = match.group(0)
                    start, end = match.span()
                    result = result[:start] + f"{{\\c{color_tag}}}{matched_str}{{\\c{clean_primary}}}" + result[end:]
                    return result

        return result

    @classmethod
    def apply_bilingual_kinetic_highlighting(
        cls,
        th_text: str,
        en_text: str,
        primary_th: str = "&H00FFFFFF&",
        primary_en: str = "&H00EAEAEA&",
        custom_keywords: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """
        Guarantees 100% color synchronization between stacked Thai and English subtitles:
        - If Thai triggers a color, English prioritizes matching the same color category.
        - If English triggers a color, Thai is re-checked against that color category.
        """
        th_res = cls.apply_kinetic_highlighting(th_text, primary_color_ass=primary_th, custom_keywords=custom_keywords)
        th_color = None
        if "{\\c" in th_res:
            m = re.search(r"\{\\c(&H[0-9A-Fa-f]+&)\}", th_res)
            if m:
                th_color = m.group(1)

        en_res = cls.apply_kinetic_highlighting_en(en_text, primary_color_ass=primary_en, color_hint=th_color, custom_keywords=custom_keywords)
        en_color = None
        if "{\\c" in en_res:
            m = re.search(r"\{\\c(&H[0-9A-Fa-f]+&)\}", en_res)
            if m:
                en_color = m.group(1)

        if not th_color and en_color:
            th_res = cls.apply_kinetic_highlighting(th_text, primary_color_ass=primary_th, color_hint=en_color, custom_keywords=custom_keywords)

        return th_res, en_res

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
        hook_motion: Optional[Dict[str, bool]] = None,
        bilingual: bool = True,
        video_width: int = VIDEO_WIDTH,
        video_height: int = VIDEO_HEIGHT,
        caption_position: str = "bottom",
        caption_color: str = None,
        caption_scale: float = 1.0
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
        # CapCut TikTok Standard: 100% (scale=1.0) calibrated to exactly 72pt on 1080w (matches Image 2 perfectly)
        # Matches SequencePlayer Canvas baseFs (26px on 540w)
        base_fs = int(round(video_width * 0.0667))
        font_size = max(24, int(round(base_fs * scale)))
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
Style: HookHeader,{resolved_font},{hook_fs},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,6.0,0,8,60,60,260,1
Style: HookHeaderShadow,{resolved_font},{hook_fs},&H00000000,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0.5,0,1,7.0,0,8,62,58,257,1
Style: SpecBar,{resolved_font},{font_size - 12},&H00000000,&H000000FF,&H00000000,&H0000E6FF,1,0,0,0,100,100,0.5,0,3,10,0,9,50,50,380,1

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
        if hook_brand or hook_model or hook_label:
            motion = _resolve_hook_motion(hook_motion)
            start_t = cls._format_ass_time(0.0)
            end_t = cls._format_ass_time(hook_duration)
            # Exit fade in the last 150ms instead of a hard cut to nothing --
            # `\t` offsets are relative to this event's own Start (0 here),
            # so they double as absolute ms, and every tier shares the same
            # Start -- all pop in / fade out in lockstep. Guarded against a
            # hook shorter than the entry animation ever producing
            # exit_start >= exit_end, which a renderer could choke on.
            exit_end_ms = int(hook_duration * 1000)
            exit_start_ms = max(120, exit_end_ms - 150)
            if exit_start_ms >= exit_end_ms:
                exit_start_ms = max(0, exit_end_ms - 50)
            exit_tag = f"\\t({exit_start_ms},{exit_end_ms},\\alpha&HFF&)"

            # (raw text, target scale % of hook_fs, Main-layer colour, tier index)
            # tier index also doubles as the stagger slot (0=brand, 1=model,
            # 2=label) and marks which physical line(s) the accent underline
            # attaches under (tier 1, model).
            hook_tier_specs = [
                (hook_brand, 130, "&H00FFFFFF", 0),
                (hook_model, 100, ass_colour(caption_color) or "&H0000E6FF", 1),
                (hook_label, 58, "&H00E0E0E0", 2),
            ]
            model_colour = ass_colour(caption_color) or "&H0000E6FF"

            # Pass 1: wrap each tier at its OWN char width -- a 130%-scale
            # line needs a narrower wrap than a 58%-scale one, or the brand
            # line runs wider than the frame while the label line wraps too
            # early. wrap_text_for_ass is the same balanced-wrap caption
            # already uses below; the hook banner never called it before.
            tier_lines = []  # (line_text, scale_pct, colour, tier_idx)
            model_tier_fs_final = None
            model_last_line = None
            for raw_text, scale_pct, colour, tier_idx in hook_tier_specs:
                text = str(raw_text or "").strip()
                if not text:
                    continue
                if scale_pct == 130:
                    text = text.upper()  # brand reads as a wordmark; .upper() is a no-op on Thai
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

                # Line-height factor for the manual vertical cursor the
                # underline drawing needs (ASS has no API to ask libass
                # where a wrapped line actually landed). Measured directly
                # off a real ffmpeg+libass render (pixel-scanned ink bands
                # per tier), not guessed -- an initial 1.28 guess put the
                # underline a full line too low, under the label instead of
                # the model. If it drifts after a font change, remeasure the
                # same way rather than re-guessing.
                LINE_HEIGHT_FACTOR = 1.0

                shadow_parts, main_parts = [], []
                max_entry_end_ms = 0
                for line, scale_pct, colour, tier_idx in tier_lines:
                    target = round(scale_pct * shrink)
                    t0_ms = tier_idx * STAGGER_STEP_MS if motion["stagger"] else 0
                    anim, entry_end_ms = _hook_entry_anim(target, t0_ms, motion["bounce"])
                    max_entry_end_ms = max(max_entry_end_ms, entry_end_ms)
                    shadow_parts.append(f"{{\\an8{anim}\\blur5\\alpha&H40&{exit_tag}}}{line}")
                    main_parts.append(f"{{\\an8{anim}{exit_tag}\\c{colour}&}}{line}")

                    if tier_idx == 1:
                        model_tier_fs_final = max(20, int(round(hook_fs * target / 100)))

                # Pulse/breathing: starts once every tier has settled, runs
                # until the exit fade takes over. Appended after each line's
                # existing tags so it animates alpha on top of the entry/exit
                # keyframes rather than replacing them.
                if motion["pulse"]:
                    pulse_tag = _hook_pulse_keyframes(max_entry_end_ms, exit_start_ms)
                    if pulse_tag:
                        shadow_parts = [p.replace(exit_tag, pulse_tag + exit_tag, 1) for p in shadow_parts]
                        main_parts = [p.replace(exit_tag, pulse_tag + exit_tag, 1) for p in main_parts]

                hook_shadow_text = "\\N".join(shadow_parts)
                hook_main_text = "\\N".join(main_parts)
                events.append(f"Dialogue: 0,{start_t},{end_t},HookHeaderShadow,,0,0,0,,{hook_shadow_text}")
                events.append(f"Dialogue: 1,{start_t},{end_t},HookHeader,,0,0,0,,{hook_main_text}")

                # Accent underline: a separate drawing event, positioned
                # under the model tier's LAST wrapped line by walking the
                # same per-line heights again and stopping once the walk
                # moves past every model-tier line (there can be more than
                # one if it wrapped).
                if motion["underline"] and model_last_line and model_tier_fs_final:
                    underline_y = 260  # HookHeader style's MarginV: top edge of the block
                    seen_model = False
                    for line, scale_pct, colour, tier_idx in tier_lines:
                        if seen_model and tier_idx != 1:
                            break
                        target = round(scale_pct * shrink)
                        line_fs = max(20, int(round(hook_fs * target / 100)))
                        underline_y += round(line_fs * LINE_HEIGHT_FACTOR)
                        if tier_idx == 1:
                            seen_model = True
                    underline_y += round(model_tier_fs_final * 0.06)  # small gap below the text

                    plain_model_line = model_last_line  # wrap_text_for_ass output; no override blocks to strip
                    measured_w = _measure_text_width_px(plain_model_line.replace("\\N", " "), resolved_font, model_tier_fs_final)
                    if measured_w is None:
                        # PIL/font-file lookup unavailable -- fall back to the
                        # same avg-char-width assumption dyn_max_chars above
                        # is built on, so the bar is in the right ballpark
                        # rather than disappearing.
                        measured_w = int(len(plain_model_line) * model_tier_fs_final * 0.55)
                    measured_w = max(20, measured_w)

                    thickness = max(3, round(model_tier_fs_final * 0.06))
                    half_w = measured_w / 2
                    underline_reveal_start = STAGGER_STEP_MS * 2 if motion["stagger"] else 0
                    underline_reveal_end = underline_reveal_start + 300
                    draw_path = f"m {-half_w:.0f} 0 l {half_w:.0f} 0 l {half_w:.0f} {thickness} l {-half_w:.0f} {thickness}"
                    underline_tag = (
                        f"{{\\an8\\pos({video_width // 2},{underline_y})\\p1"
                        f"\\bord0\\shad0\\c{model_colour}&\\fscx0"
                        f"\\t({underline_reveal_start},{underline_reveal_end},\\fscx100)"
                        f"{exit_tag}}}"
                    )
                    events.append(f"Dialogue: 1,{start_t},{end_t},HookHeader,,0,0,0,,{underline_tag}{draw_path}")

        # 1-shot Batch Translation for all micro-cues
        en_translations = []
        if bilingual:
            # Check if cues already have translations
            has_existing = any(bool(c.get("translation")) for c in micro_cues)
            if has_existing:
                en_translations = [c.get("translation", "") for c in micro_cues]
            else:
                try:
                    from scripts.translator import SubtitleTranslator
                    en_translations = SubtitleTranslator.translate_batch([c["text"] for c in micro_cues])
                except Exception:
                    try:
                        from translator import SubtitleTranslator
                        en_translations = SubtitleTranslator.translate_batch([c["text"] for c in micro_cues])
                    except Exception:
                        en_translations = [""] * len(micro_cues)
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

            # Apply Synchronized Bilingual Kinetic Highlighting (guaranteeing exact color parity)
            if en_wrapped:
                highlighted_text, en_highlighted = cls.apply_bilingual_kinetic_highlighting(
                    th_text=text,
                    en_text=en_wrapped,
                    primary_th=primary,
                    primary_en="&H00EAEAEA&",
                    custom_keywords=proj_keywords
                )
                en_sub = f"\\N{{\\fscx68\\fscy68\\c&H00EAEAEA&}}{en_highlighted}"
            else:
                highlighted_text = cls.apply_kinetic_highlighting(text, primary_color_ass=primary, custom_keywords=proj_keywords)
                en_sub = ""

            style = "TikTokMinimalPill" if is_pill_mode else "TikTokWhite"

            # Layer 0: Natural Soft Feathered Shadow (Gaussian Blur matching Canvas preview)
            if not is_pill_mode:
                en_sub_shadow = f"\\N{{\\fscx68\\fscy68}}{en_wrapped}" if en_wrapped else ""
                shadow_tag = f"{{\\blur{shadow_blur}\\alpha&H38&}}"
                events.append(f"Dialogue: 0,{start_t},{end_t},TikTokSoftShadow,,0,0,0,,{anim}{shadow_tag}{text}{en_sub_shadow}")

            # Layer 1: Crisp Foreground Text with dynamic kinetic highlights
            line_entry = f"Dialogue: 1,{start_t},{end_t},{style},,0,0,0,,{anim}{highlighted_text}{en_sub}"
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
            spec_anim = "{\\fscx110\\fscy110\\t(0,100,\\fscx100\\fscy100)}"
            # Layer 2, above the hook banner (1) and captions (0), in case a
            # long spec bar's footprint ever crosses either at the same time.
            events.append(f"Dialogue: 2,{spec_start},{spec_end},SpecBar,,0,0,0,,{spec_anim}📊 {on_screen}")

        content = header + "\n".join(events) + "\n"
        out_path.write_text(content, encoding="utf-8")
        return str(out_path), micro_cues

if __name__ == "__main__":
    print("SubtitleEngine ready.")
