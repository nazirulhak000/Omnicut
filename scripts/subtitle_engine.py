"""
TikTok Style Subtitle Generator (Advanced SubStation Alpha .ass)
Produces rapid-fire 2-3 word micro-burst subtitles with Kanit-Black font, emojis, and pop animation.
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple

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

        # 2. First pass: merge tiny orphan fragments into preceding clause
        merged_parts = []
        for p in raw_parts:
            if not merged_parts:
                merged_parts.append(p)
            elif (
                len(p) <= 4
                or p.startswith("ๆ")
                or p.startswith("...")
                or p in ["บ้าง", "บ้าง...", "นะ", "ครับ", "ค่ะ", "เลย", "ด้วย", "อ่ะ", "น้า", "จ้า", "ล่ะ"]
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

    @classmethod
    def generate_micro_cues(cls, cues: List[Dict]) -> List[Dict]:
        """
        Converts sentence-level cues into smart clause cues, translating each into English
        and maintaining exact proportional audio timestamps.
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
            total_chars = max(1, sum(len(cl) for cl in clauses))
            current_t = start

            for idx, cl in enumerate(clauses):
                cl_dur = (len(cl) / total_chars) * total_dur
                cl_end = min(end, current_t + cl_dur)
                if idx == len(clauses) - 1:
                    cl_end = end

                # Only assign SFX on the very first beat of a major phrase
                sfx = None
                if idx == 0 and c.get("sfx"):
                    sfx = c["sfx"]

                # Assign Emojis selectively (only if not already present)
                emoji = ""
                has_emoji = any(cl.startswith(em) for em in ["⚠️", "🔌", "⚡", "❌", "🛒"])
                if not has_emoji:
                    if any(k in cl for k in ["อย่าเพิ่ง", "หยุด", "เตือน"]):
                        emoji = "⚠️ "
                    elif any(k in cl for k in ["แม่เหล็ก", "ดูดแน่น"]):
                        emoji = "🔌 "
                    elif any(k in cl for k in ["66W", "ชาร์จไว", "เร็ว"]):
                        emoji = "⚡ "
                    elif any(k in cl for k in ["ปัญหา", "พัง"]):
                        emoji = "❌ "
                    elif any(k in cl for k in ["พิกัด", "ตะกร้า", "149"]):
                        emoji = "🛒 "

                cue_text = f"{emoji}{cl}".strip() if emoji else cl.strip()
                cue_trans = c.get("translation", "") if len(clauses) == 1 else ""

                micro_cues.append({
                    "id": cue_id,
                    "start": round(current_t, 3),
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
    def generate_ass(
        cls,
        cues: List[Dict],
        output_ass_path: str,
        font_name: str = "Kanit",
        font_size: int = 78,
        hook_title: str = None,
        hook_duration: float = 3.5,
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
            scale = min(2.0, max(0.5, float(caption_scale or 1.0)))
        except (TypeError, ValueError):
            scale = 1.0
        font_size = max(24, int(round(font_size * scale)))

        header = f"""[Script Info]
Title: TikTok Aesthetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokWhite,{resolved_font},{font_size},{primary},&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.5,2.5,{alignment},60,60,{margin_v},1
Style: TikTokYellow,{resolved_font},{font_size},&H0000E6FF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,420,1
Style: TikTokCyan,{resolved_font},{font_size},&H00FFE600,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.0,2.0,2,60,60,420,1
Style: TikTokMinimalPill,{resolved_font},{font_size - 6},{primary},&H000000FF,&H00000000,&HCC000000,1,0,0,0,100,100,0.5,0,3,6,0,{alignment},60,60,{margin_v},1
Style: HookHeader,{resolved_font},{font_size + 6},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,7.0,3.0,8,60,60,260,1
Style: SpecBar,{resolved_font},{font_size - 12},&H00000000,&H000000FF,&H00000000,&H0000E6FF,1,0,0,0,100,100,0.5,0,3,10,0,9,50,50,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []

        # 1. Top Hook Banner (Frameless Large Minimal Font with Crisp Outline)
        if hook_title:
            start_t = cls._format_ass_time(0.0)
            end_t = cls._format_ass_time(hook_duration)
            hook_text = f"{{\\an8\\fscx115\\fscy115\\t(0,120,\\fscx100\\fscy100)\\bord7\\3c&H00000000&\\shad3\\c&H00FFFFFF&}}{hook_title}"
            events.append(f"Dialogue: 1,{start_t},{end_t},HookHeader,,0,0,0,,{hook_text}")

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

        # 2. Add Rapid-Fire Micro-Cues with Stacked Bilingual Support
        for idx, cue in enumerate(micro_cues):
            start_t = cls._format_ass_time(cue["start"])
            end_t = cls._format_ass_time(cue["end"])
            text = cue["text"].strip()
            if not text:
                continue

            # Kinetic Pop Animation: Snap in 125% -> Settle 100% (or cue.scale) in 70ms
            cue_scale = float(cue.get("scale", 1.0) or 1.0)
            settle_pct = max(50, min(200, int(round(100 * cue_scale))))
            snap_pct = int(round(settle_pct * 1.25))
            anim = f"{{\\fscx{snap_pct}\\fscy{snap_pct}\\t(0,70,\\fscx{settle_pct}\\fscy{settle_pct})}}"
            
            if is_pill_mode:
                style = "TikTokMinimalPill"
            else:
                # Clean Minimal: Pure White by default, Yellow ONLY on crucial high-value words
                style = "TikTokWhite"
                if any(k in text for k in ["66W", "149", "แม่เหล็ก", "ดูดแน่น", "พิเศษ", "โปร", "ลด", "คุ้ม", "พิกัด"]):
                    style = "TikTokYellow"

            # Check for English Translation
            en_sub = ""
            if bilingual and idx < len(en_translations):
                candidate_en = (en_translations[idx] or cue.get("translation", "")).strip()
                if candidate_en and not any(sig in candidate_en for sig in ["Error 500", "500.", "That's an error", "<html"]) and len(candidate_en) < 80:
                    cue["translation"] = candidate_en
                    en_clean = candidate_en.replace("\n", " ").replace("\\", "")
                    en_color = "\\c&H00D8D8D8&" if style == "TikTokWhite" else "\\c&H0080E6FF&"
                    en_sub = f"\\N{{\\fscx60\\fscy60{en_color}}}{en_clean}"
                else:
                    cue["translation"] = ""

            line_entry = f"Dialogue: 0,{start_t},{end_t},{style},,0,0,0,,{anim}{text}{en_sub}"
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
