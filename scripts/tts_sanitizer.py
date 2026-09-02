"""
TTS Script Sanitizer — cleans AI-generated scripts for natural Thai TTS output.

Pipeline: Raw Script → Strip Emoji → Expand Abbreviations → 
          Pronunciation Guide → Remove Symbols → Clean Output

Two output modes:
  - display_text: for UI rendering (keeps Emoji in angle_name/hook_title)
  - tts_text:     for voice synthesis (no Emoji, expanded abbreviations, Thai pronunciation)
"""

import re
import sys
import unicodedata
from typing import List, Dict, Optional

if sys.platform == 'win32' and sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────
# Abbreviation / unit expansion map — Thai pronunciation
# ─────────────────────────────────────────────────────────────────────
ABBREVIATION_MAP = {
    # Power / Electrical
    "W":    "วัตต์",
    "mW":   "มิลลิวัตต์",
    "kW":   "กิโลวัตต์",
    "V":    "โวลต์",
    "A":    "แอมป์",
    "mA":   "มิลลิแอมป์",
    "mAh":  "มิลลิแอมป์อาวเออร์",
    "Wh":   "วัตต์อาวเออร์",

    # Frequency / Audio
    "Hz":   "เฮิรตซ์",
    "kHz":  "กิโลเฮิรตซ์",
    "MHz":  "เมกะเฮิรตซ์",
    "GHz":  "กิกะเฮิรตซ์",
    "dB":   "เดซิเบล",
    "ms":   "มิลลิวินาที",

    # Data / Speed
    "GB":   "กิกะไบต์",
    "MB":   "เมกะไบต์",
    "TB":   "เทราไบต์",
    "KB":   "กิโลไบต์",
    "Gbps": "กิกะบิตต่อวินาที",
    "Mbps": "เมกะบิตต่อวินาที",

    # Length / Weight
    "mm":   "มิลลิเมตร",
    "cm":   "เซนติเมตร",
    "m":    "เมตร",
    "kg":   "กิโลกรัม",
    "g":    "กรัม",
    "ml":   "มิลลิลิตร",

    # Display
    "fps":  "เฟรมต่อวินาที",
    "ppi":  "พิกเซลต่อนิ้ว",
    "nits": "นิต",
}

# Common tech abbreviations → Thai spoken form
WORD_MAP = {
    "USB-C":    "ยูเอสบีซี",
    "USB-A":    "ยูเอสบีเอ",
    "USB":      "ยูเอสบี",
    "Type-C":   "ไทป์ซี",
    "Type C":   "ไทป์ซี",
    "HDMI":     "เอชดีเอ็มไอ",
    "LED":      "แอลอีดี",
    "LCD":      "แอลซีดี",
    "OLED":     "โอแอลอีดี",
    "Wi-Fi":    "ไวไฟ",
    "WiFi":     "ไวไฟ",
    "Wifi":     "ไวไฟ",
    "Bluetooth":"บลูทูธ",
    "BT":       "บลูทูธ",
    "NFC":      "เอ็นเอฟซี",
    "AI":       "เอไอ",
    "WFH":      "เวิร์คฟรอมโฮม",
    "DIY":      "ดีไอวาย",
    "IP67":     "ไอพี หกสิบเจ็ด",
    "IP68":     "ไอพี หกสิบแปด",
    "IPX7":     "ไอพีเอ็กซ์ เจ็ด",
    "IPX8":     "ไอพีเอ็กซ์ แปด",
    "PD":       "พีดี",
    "QC":       "คิวซี",
    "vs":       "เทียบกับ",
    "VS":       "เทียบกับ",
    "Vs":       "เทียบกับ",
    "3-in-1":   "สามอินวัน",
    "2-in-1":   "สองอินวัน",
    "4-in-1":   "สี่อินวัน",
    "5-in-1":   "ห้าอินวัน",
    "iOS":      "ไอโอเอส",
    "Android":  "แอนดรอยด์",
    "ANC":      "เอเอ็นซี",
    "ENC":      "อีเอ็นซี",
    "RGB":      "อาร์จีบี",
    "FPS":      "เอฟพีเอส",
    "SSD":      "เอสเอสดี",
    "HDD":      "เอชดีดี",
    "RAM":      "แรม",
    "ROM":      "รอม",
    "CPU":      "ซีพียู",
    "GPU":      "จีพียู",
    "OTG":      "โอทีจี",
    "SD":       "เอสดี",
    "TF":       "ทีเอฟ",
}


class TTSSanitizer:
    """Cleans script text for natural-sounding Thai TTS output."""

    # Regex to match Emoji characters (covers most Unicode emoji ranges)
    _EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
        "\U0001F680-\U0001F6FF"  # Transport & Map
        "\U0001F1E0-\U0001F1FF"  # Flags
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed chars
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols Extended-A
        "\U00002600-\U000026FF"  # Misc Symbols
        "\U0000FE00-\U0000FE0F"  # Variation Selectors
        "\U0000200D"             # Zero Width Joiner
        "\U00000023\U0000FE0F\U000020E3"  # Keycap
        "]+",
        flags=re.UNICODE
    )

    # Pattern to match numbers followed by unit abbreviations (e.g., "66W", "100mAh")
    _NUM_UNIT_PATTERN = re.compile(
        r'(\d+(?:\.\d+)?)\s*(' + '|'.join(
            re.escape(k) for k in sorted(ABBREVIATION_MAP.keys(), key=len, reverse=True)
        ) + r')(?=\s|$|[,.\)!?])',
        flags=re.IGNORECASE
    )

    @classmethod
    def strip_emoji(cls, text: str) -> str:
        """Remove all emoji characters from text."""
        return cls._EMOJI_PATTERN.sub('', text).strip()

    @classmethod
    def expand_abbreviations(cls, text: str) -> str:
        """Replace tech abbreviations with Thai pronunciation equivalents."""
        result = text

        # First: expand number+unit combos (e.g., "66W" → "66 วัตต์")
        def _replace_num_unit(m):
            num = m.group(1)
            unit_raw = m.group(2)
            # Find the correct case-insensitive match
            for key, val in ABBREVIATION_MAP.items():
                if unit_raw.lower() == key.lower():
                    return f"{num} {val}"
            return m.group(0)

        result = cls._NUM_UNIT_PATTERN.sub(_replace_num_unit, result)

        # Second: expand standalone word abbreviations (longer first to avoid partial matches)
        for abbr, thai in sorted(WORD_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            # Use word boundary-aware replacement
            pattern = re.compile(re.escape(abbr), re.IGNORECASE)
            result = pattern.sub(thai, result)

        return result

    @classmethod
    def clean_symbols(cls, text: str) -> str:
        """Clean up symbols that TTS can't handle well."""
        # Remove hashtags entirely from spoken text
        text = re.sub(r'#\S+', '', text)

        # Remove stray markdown/formatting
        text = re.sub(r'[*_~`]', '', text)

        # Normalize multiple spaces
        text = re.sub(r'\s{2,}', ' ', text)

        # Trim
        return text.strip()

    @classmethod
    def clean(cls, text: str) -> str:
        """
        Full sanitization pipeline for TTS.
        
        Returns text suitable for direct TTS input:
        - No emoji
        - Abbreviations expanded to Thai pronunciation
        - No hashtags or markdown
        - Clean spacing
        """
        if not text:
            return ""

        result = text
        result = cls.strip_emoji(result)
        result = cls.expand_abbreviations(result)
        result = cls.clean_symbols(result)
        return result

    @classmethod
    def clean_script_lines(cls, lines: List[str]) -> List[str]:
        """Clean a list of script lines for TTS."""
        return [cls.clean(line) for line in lines if line.strip()]

    @classmethod
    def process_angle(cls, angle: Dict) -> Dict:
        """
        Process a full angle dict, adding tts_lines alongside script_lines.
        
        - script_lines: kept as-is for UI display (may contain emoji)
        - tts_lines: cleaned for TTS synthesis
        """
        result = dict(angle)

        # Clean script_lines → tts_lines
        script_lines = angle.get("script_lines", [])
        if isinstance(script_lines, list):
            result["tts_lines"] = cls.clean_script_lines(script_lines)
        elif isinstance(script_lines, str):
            result["tts_lines"] = cls.clean_script_lines(script_lines.split('\n'))

        # Clean hook_title for TTS (but keep original for display)
        hook = angle.get("hook_title", "")
        if hook:
            result["tts_hook_title"] = cls.clean(hook)

        return result

    @classmethod
    def process_angles(cls, angles: List[Dict]) -> List[Dict]:
        """Process all angles in a list, adding tts_lines to each."""
        return [cls.process_angle(a) for a in angles]


if __name__ == "__main__":
    # Quick demo
    test_cases = [
        "🔥 ใครเจอปัญหานี้อยู่ หยุดดูด่วน!",
        "สายชาร์จ 66W USB-C แม่เหล็กหมุน 540 องศา",
        "ราคาแค่ 129 บาท vs ของเดิมราคาหลักพัน",
        "ไอเทมลับชาว WFH ที่ต้องมีติดโต๊ะ #รีวิวของดี #tiktokป้ายยา",
        "แบตเตอรี่ 5000mAh ชาร์จเร็ว 3-in-1 รองรับ iOS และ Android",
        "ลดเสียงรบกวนด้วย ANC 45dB ต่อเนื่อง 40Hz - 20kHz",
    ]

    print("=" * 60)
    print("TTS Sanitizer Demo")
    print("=" * 60)
    for t in test_cases:
        cleaned = TTSSanitizer.clean(t)
        print(f"\n  IN:  {t}")
        print(f"  OUT: {cleaned}")
