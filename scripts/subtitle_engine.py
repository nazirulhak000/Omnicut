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
    def split_into_short_bursts(cls, text: str, max_chars: int = 16, max_words: int = 2) -> List[str]:
        """
        Splits Thai text into natural 2-3 word micro-bursts using PyThaiNLP,
        ensuring compound nouns remain intact and 'ๆ' is NEVER an isolated subtitle frame.
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        from pythainlp.tokenize import word_tokenize

        # Split by punctuation / spaces first
        raw_parts = [p.strip() for p in clean_text.replace("!", "! ").replace("?", "? ").split() if p.strip()]
        bursts = []

        for part in raw_parts:
            if len(part) <= max_chars:
                bursts.append(part)
            else:
                tokens = word_tokenize(part, engine="newmm", keep_whitespace=False)
                curr = []
                for tok in tokens:
                    # Never let 'ๆ' or tone marks start a new token
                    if tok == "ๆ" or tok.startswith("ๆ"):
                        if curr:
                            curr[-1] += tok
                        elif bursts:
                            bursts[-1] += tok
                        else:
                            curr.append(tok)
                        continue

                    curr.append(tok)
                    curr_len = sum(len(x) for x in curr)
                    if len(curr) >= 3 or curr_len >= 12:
                        bursts.append("".join(curr))
                        curr = []
                if curr:
                    curr_str = "".join(curr)
                    if (len(curr_str) <= 3 or curr_str.startswith("ๆ")) and bursts:
                        bursts[-1] += curr_str
                    else:
                        bursts.append(curr_str)

        # Post-process cleanup: merge orphan 'ๆ' and tiny fragments (< 3 chars) into preceding burst
        cleaned_bursts = []
        for b in bursts:
            b_str = b.strip()
            if not b_str:
                continue
            if b_str == "ๆ" or b_str.startswith("ๆ"):
                if cleaned_bursts:
                    cleaned_bursts[-1] += b_str
                else:
                    cleaned_bursts.append(b_str)
            elif len(b_str) <= 2 and cleaned_bursts:
                cleaned_bursts[-1] += " " + b_str
            else:
                cleaned_bursts.append(b_str)

        return cleaned_bursts if cleaned_bursts else [clean_text]

    @classmethod
    def generate_micro_cues(cls, cues: List[Dict]) -> List[Dict]:
        """
        Converts sentence-level cues into rapid-fire 2-3 word micro-cues with SFX tags and emojis.
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

            # If text is already a neat 1-line clause (<= 38 chars), keep exact 100% audio duration!
            if len(text) <= 38:
                bursts = [text]
            else:
                bursts = cls.split_into_short_bursts(text, max_chars=34)

            total_chars = max(1, sum(len(b) for b in bursts))
            current_t = start

            for idx, burst in enumerate(bursts):
                b_dur = (len(burst) / total_chars) * (end - start)
                b_end = min(end, current_t + b_dur)
                if idx == len(bursts) - 1:
                    b_end = end

                # Only assign SFX on the very first beat of a major phrase (No spam)
                sfx = None
                if idx == 0 and c.get("sfx"):
                    sfx = c["sfx"]

                # Assign Emojis selectively
                emoji = ""
                if any(k in burst for k in ["อย่าเพิ่ง", "หยุด", "เตือน"]):
                    emoji = "⚠️ "
                elif any(k in burst for k in ["แม่เหล็ก", "ดูดแน่น"]):
                    emoji = "🔌 "
                elif any(k in burst for k in ["66W", "ชาร์จไว", "เร็ว"]):
                    emoji = "⚡ "
                elif any(k in burst for k in ["ปัญหา", "พัง"]):
                    emoji = "❌ "
                elif any(k in burst for k in ["พิกัด", "ตะกร้า", "149"]):
                    emoji = "🛒 "

                micro_cues.append({
                    "id": cue_id,
                    "start": current_t,
                    "end": b_end,
                    "text": f"{emoji}{burst}".strip(),
                    "sfx": sfx
                })
                cue_id += 1
                current_t = b_end

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

            # Kinetic Pop Animation: Snap in 125% -> Settle 100% in 70ms
            anim = "{\\fscx125\\fscy125\\t(0,70,\\fscx100\\fscy100)}"
            
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
                en_text = en_translations[idx].strip()
                if en_text:
                    en_clean = en_text.replace("\n", " ").replace("\\", "")
                    en_color = "\\c&H00D8D8D8&" if style == "TikTokWhite" else "\\c&H0080E6FF&"
                    en_sub = f"\\N{{\\fscx60\\fscy60{en_color}}}{en_clean}"

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
