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
    "mAh":  "มิลลิแอมป์",
    "Wh":   "วัตต์",

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
    # E-Commerce & Promo terms
    "Flash Sale": "แฟลชเซล",
    "Flash sale": "แฟลชเซล",
    "flash sale": "แฟลชเซล",
    "COD":        "เก็บเงินปลายทาง",
    "Voucher":    "เวาเชอร์",
    "voucher":    "เวาเชอร์",
    "Coupon":     "คูปอง",
    "coupon":     "คูปอง",
    "Live":       "ไลฟ์",
    "live":       "ไลฟ์",
    "Unbox":      "อันบ็อกซ์",
    "Unboxing":   "อันบ็อกซิ่ง",
    "unbox":      "อันบ็อกซ์",
    "unboxing":   "อันบ็อกซิ่ง",
    "Affiliate":  "แอฟฟิลิเอต",
    "Pro":        "โปร",
    "Max":        "แม็กซ์",
    "Mini":       "มินิ",
    "Plus":       "พลัส",
    "Ultra":      "อัลตรา",
    "Lite":       "ไลต์",
    "1 แถม 1":    "หนึ่งแถมหนึ่ง",
    "1แถม1":      "หนึ่งแถมหนึ่ง",
    "1+1":        "หนึ่งแถมหนึ่ง",
    "AAA":        "ทริปเปิลเอ",
    "AA":         "ดับเบิลเอ",
    "Logi Bolt":  "โลจิ โบลต์",
    "Logi Options+": "โลจิ ออปชัน พลัส",
    "Wave Keys":  "เวฟ คีย์ส",
    "Logitech":   "โลจิเทค",
    "Windows":    "วินโดวส์",
    "Mac":        "แมค",
}

# ─────────────────────────────────────────────────────────────────────
# Rule 9: English Brand Names, Model Names & Tech Specs Mapping
# Replaces Thai phonetic transliterations with official English terms.
# Longer phrases placed first to avoid partial replacements.
# ─────────────────────────────────────────────────────────────────────
OFFICIAL_ENGLISH_MAP = [
    # Full Product & Brand combos (longest first)
    ("โลจิเทค เวฟ คีย์ส", "Logitech Wave Keys"),
    ("โลจิเทค เวฟ คีย์", "Logitech Wave Keys"),
    ("โลจิเทค เวฟคีย์ส", "Logitech Wave Keys"),
    ("โลจิเทค เวฟคีย์", "Logitech Wave Keys"),
    ("เวฟ คีย์ส", "Wave Keys"),
    ("เวฟ คีย์", "Wave Keys"),
    ("เวฟคีย์ส", "Wave Keys"),
    ("เวฟคีย์", "Wave Keys"),
    ("โลจิเทค เอ็มเอ็กซ์ มาสเตอร์", "Logitech MX Master"),
    ("โลจิเทค ลิฟต์", "Logitech Lift"),
    ("โลจิเทค ลิฟท์", "Logitech Lift"),
    ("โลจิเทค เพบเบิล", "Logitech Pebble"),
    ("โลจิ โบลต์", "Logi Bolt"),
    ("โลจิ โบลท์", "Logi Bolt"),
    ("โลจิโบลต์", "Logi Bolt"),
    ("โลจิโบลท์", "Logi Bolt"),
    ("โลจิ ออปชันส์ พลัส", "Logi Options+"),
    ("โลจิ ออปชัน พลัส", "Logi Options+"),
    ("โลจิ ออปชั่น พลัส", "Logi Options+"),
    ("โลจิเทค", "Logitech"),
    ("โลจิ", "Logi"),

    # Operating Systems & Ecosystems
    ("วินโดวส์", "Windows"),
    ("วินโดว์", "Windows"),
    ("แมคบุ๊ก", "MacBook"),
    ("แมคบุค", "MacBook"),
    ("แมคโอเอส", "macOS"),
    ("ไอโอเอส", "iOS"),
    ("แอนดรอยด์", "Android"),
    ("ไอแพด", "iPad"),
    ("ไอโฟน", "iPhone"),
    ("แอปเปิ้ล", "Apple"),
    ("แอปเปิล", "Apple"),

    # Standalone 'แมค' in computing / OS context
    (r'(?<=ระบบ\s)แมค', "Mac"),
    (r'(?<=และ\s)แมค', "Mac"),
    (r'(?<=กับ\s)แมค', "Mac"),
    (r'(?<=หรือ\s)แมค', "Mac"),
    (r'(?<=บน\s)แมค', "Mac"),
    (r'(?<=เครื่อง\s)แมค', "Mac"),
    (r'(?<=ฝั่ง\s)แมค', "Mac"),
    (r'แมค(?=\sและ)', "Mac"),
    (r'แมค(?=\sหรือ)', "Mac"),
    (r'\bแมค\b', "Mac"),

    # Connectivity, Wireless & Tech
    ("บลูทูธ", "Bluetooth"),
    ("บลูทูท", "Bluetooth"),
    ("ไวไฟ", "Wi-Fi"),
    ("วายฟาย", "Wi-Fi"),
    ("ยูเอสบี ซี", "USB-C"),
    ("ยูเอสบี-ซี", "USB-C"),
    ("ยูเอสบีซี", "USB-C"),
    ("ยูเอสบี เอ", "USB-A"),
    ("ยูเอสบี-เอ", "USB-A"),
    ("ยูเอสบีเอ", "USB-A"),
    ("ยูเอสบี", "USB"),
    ("ไทป์ ซี", "Type-C"),
    ("ไทป์-ซี", "Type-C"),
    ("ไทป์ซี", "Type-C"),
    ("เอชดีเอ็มไอ", "HDMI"),
    ("เอ็นเอฟซี", "NFC"),
    ("อีซี่ สวิตช์", "Easy-Switch"),
    ("อีซี่ สวิทช์", "Easy-Switch"),
    ("อีซี่สวิตช์", "Easy-Switch"),
    ("เอไอ", "AI"),
    ("แอลอีดี", "LED"),
    ("โอแอลอีดี", "OLED"),
    ("แอลซีดี", "LCD"),
    ("เอเอ็นซี", "ANC"),
    ("อีเอ็นซี", "ENC"),
    ("เอสเอสดี", "SSD"),

    # Battery & Hardware
    ("ทริปเปิลเอ", "AAA"),
    ("ทริปเปิ้ลเอ", "AAA"),
    ("สามเอ", "AAA"),
    ("ดับเบิลเอ", "AA"),
    ("ดับเบิ้ลเอ", "AA"),
    ("สองเอ", "AA"),
    ("เพาเวอร์แบงก์", "Power Bank"),
    ("เพาเวอร์แบงค์", "Power Bank"),
    ("พาวเวอร์แบงก์", "Power Bank"),
    ("พาวเวอร์แบงค์", "Power Bank"),
    ("ฟาสต์ชาร์จ", "Fast Charge"),
    ("ฟาสชาร์จ", "Fast Charge"),
    ("ควิกชาร์จ", "Quick Charge"),

    # Ergonomic / Design
    ("เออร์โกโนมิกส์", "Ergonomic"),
    ("เออร์โกโนมิก", "Ergonomic"),
    ("เออร์โกโนมิกข์", "Ergonomic"),
    ("เมมโมรี่โฟม", "Memory Foam"),
    ("เมมโมรีโฟม", "Memory Foam"),

    # Other Top Brands
    ("แองเคอร์", "Anker"),
    ("แอนเคอร์", "Anker"),
    ("ยูกรีน", "Ugreen"),
    ("เบสซัส", "Baseus"),
    ("เบซุส", "Baseus"),
    ("เอสเซเกอร์", "Essager"),
    ("เสียวหมี่", "Xiaomi"),
    ("เสี่ยวหมี่", "Xiaomi"),
    ("ซัมซุง", "Samsung"),
    ("โซนี่", "Sony"),
    ("เจบีแอล", "JBL"),
    ("หัวเว่ย", "Huawei"),
]

# ─────────────────────────────────────────────────────────────────────
# Natural Spoken Thai Corrections (Fixes AI hallucinations & unnatural phrasing)
# ─────────────────────────────────────────────────────────────────────
NATURAL_THAI_REPLACEMENTS = [
    (r"หนะคอม", "หน้าคอม"),
    (r"หนะจอ", "หน้าจอ"),
    (r"รักสุขภาพข้อมือตัวเองด่วนๆ", "รักข้อมือตัวเอง"),
    (r"รักสุขภาพข้อมือตัวเอง", "รักข้อมือตัวเอง"),
    (r"รักษาสุขภาพข้อมือตัวเอง", "รักข้อมือตัวเอง"),
    (r"รักสุขภาพข้อมือ", "รักข้อมือตัวเอง"),
    (r"รักษาสุขภาพข้อมือ", "รักข้อมือตัวเอง"),
    (r"เพื่อสุขภาพข้อมือ", "เพื่อสุขภาพ"),
    (r"เพื่อสุขภาพร่างกาย", "เพื่อสุขภาพ"),
    (r"ราคาลดกระหน่ำด่วนๆ", "ราคาพิเศษ"),
    (r"ลดกระหน่ำด่วนๆ", "ลดกระหน่ำ"),
]


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

    # Pattern to match numbers followed by unit abbreviations (e.g., "66W", "20,000mAh")
    _NUM_UNIT_PATTERN = re.compile(
        r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(' + '|'.join(
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

        # Currency & Price notation expansions (e.g., "199.-", "฿199", "199฿")
        result = re.sub(r'(\d+)\s*\.-', r'\1 บาท', result)
        result = re.sub(r'฿\s*(\d+)', r'\1 บาท', result)
        result = re.sub(r'(\d+)\s*฿', r'\1 บาท', result)

        # Percentage expansion (e.g., "50%" → "50 เปอร์เซ็นต์")
        result = re.sub(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*%', r'\1 เปอร์เซ็นต์', result)

        # Multiplier expansion (e.g., "2x", "3x" → "สองเท่า", "สามเท่า")
        result = re.sub(r'\b2x\b|\b2X\b', 'สองเท่า', result)
        result = re.sub(r'\b3x\b|\b3X\b', 'สามเท่า', result)

        # Day range expansion (e.g., "1-2 วัน" → "หนึ่งถึงสองวัน", "2-3 วัน" → "สองถึงสามวัน")
        result = re.sub(r'1-2\s*วัน', 'หนึ่งถึงสองวัน', result)
        result = re.sub(r'2-3\s*วัน', 'สองถึงสามวัน', result)
        result = re.sub(r'3-5\s*วัน', 'สามถึงห้าวัน', result)

        # Expand number+unit combos (e.g., "66W" → "66 วัตต์", "20,000mAh" → "20000 มิลลิแอมป์")
        def _replace_num_unit(m):
            num = m.group(1).replace(",", "")
            unit_raw = m.group(2)
            # Find the correct case-insensitive match
            for key, val in ABBREVIATION_MAP.items():
                if unit_raw.lower() == key.lower():
                    return f"{num} {val}"
            return m.group(0)

        result = cls._NUM_UNIT_PATTERN.sub(_replace_num_unit, result)

        # Expand standalone word abbreviations (longer first to avoid partial matches)
        # Uses alphanumeric lookaround boundaries for ASCII tokens to prevent corrupting words like:
        # "detail" -> "detเอไอl", "Product" -> "โปรduct", "Problem" -> "โปรblem", "From" -> "Fรอม"
        for abbr, thai in sorted(WORD_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if re.match(r'^[a-zA-Z0-9_\-]+$', abbr):
                pattern = re.compile(r'(?<![a-zA-Z0-9])' + re.escape(abbr) + r'(?![a-zA-Z0-9])', re.IGNORECASE)
            else:
                pattern = re.compile(re.escape(abbr), re.IGNORECASE)
            result = pattern.sub(thai, result)

        return result

    @classmethod
    def enforce_male_tone(cls, text: str) -> str:
        """
        Enforce strict male speaker persona (ผม / ครับ / นะครับ).
        Eliminates feminine sentence-final particles and slang:
        - นะคะ -> นะครับ
        - ค่ะ / คะ / บ้างคะ / ไหมคะ -> ครับ / บ้างครับ / ไหมครับ
        - จ้า -> ครับ
        - น้า -> นะ
        - แกรรร / แกรร -> ทุกคน
        - หนู -> ผม
        """
        if not text:
            return ""
        result = text
        result = re.sub(r'บ้างคะ', 'บ้างครับ', result)
        result = re.sub(r'ใช่ไหมคะ|ใช่มั้ยคะ', 'ใช่ไหมครับ', result)
        result = re.sub(r'ไหมคะ|มั้ยคะ', 'ไหมครับ', result)
        result = re.sub(r'นะคะ', 'นะครับ', result)
        result = re.sub(r'ค่ะ', 'ครับ', result)
        result = re.sub(r'คะ', 'ครับ', result)
        result = re.sub(r'จ้า', 'ครับ', result)
        result = re.sub(r'น้า', 'นะ', result)
        result = re.sub(r'แกรรร+|แกรร+', 'ทุกคน', result)
        result = re.sub(r'\bหนู\b', 'ผม', result)
        return result

    @classmethod
    def enforce_official_english(cls, text: str) -> str:
        """
        Enforce Rule 9: English brand names, model names, and tech specs.
        Replaces Thai phonetic transliterations with official English terms.
        """
        if not text:
            return ""
        result = text
        for item in OFFICIAL_ENGLISH_MAP:
            target, replacement = item
            if target.startswith('(?') or r'\b' in target:
                result = re.sub(target, replacement, result)
            else:
                result = result.replace(target, replacement)
        return result

    @classmethod
    def enforce_natural_thai(cls, text: str) -> str:
        """Fix awkward AI hallucinations and machine-translated phrasing into natural spoken Thai."""
        if not text:
            return ""
        result = text
        for pat, repl in NATURAL_THAI_REPLACEMENTS:
            result = re.sub(pat, repl, result)
        return result

    @classmethod
    def clean_display_text(cls, text: str) -> str:
        """
        Clean text for display (UI / Subtitles / Caption):
        - Enforces 100% strict male persona (ครับ / นะครับ, no ค่ะ / นะคะ)
        - Enforces Rule 9: English brand names, model names, and tech specs
        - Fixes unnatural AI phrasing into natural spoken Thai
        - Adds clean spacing between Thai and English tokens for legibility
        - Strips ellipses (..., …)
        - Cleans multi-spaces
        """
        if not text:
            return ""
        result = text
        result = cls.enforce_male_tone(result)
        result = cls.enforce_official_english(result)
        result = cls.enforce_natural_thai(result)
        # Clean typography: spacing between Thai characters and English words
        result = re.sub(r'([ก-๙])([A-Za-z])', r'\1 \2', result)
        result = re.sub(r'([A-Za-z])([ก-๙])', r'\1 \2', result)
        result = re.sub(r'[\.]{2,}|…', ' ', result)
        result = re.sub(r'\s{2,}', ' ', result)
        return result.strip()

    @classmethod
    def clean_symbols(cls, text: str) -> str:
        """Clean up symbols that TTS can't handle well."""
        # Remove hashtags entirely from spoken text
        text = re.sub(r'#\S+', '', text)

        # Strip ellipsis (..., …) and replace with clean space
        text = re.sub(r'[\.]{2,}|…', ' ', text)

        # Remove stray markdown/formatting
        text = re.sub(r'[*_~`]', '', text)

        # Clean stray slashes or bullet chars
        text = re.sub(r'[•|/]', ' ', text)

        # Normalize multiple spaces
        text = re.sub(r'\s{2,}', ' ', text)

        # Trim
        return text.strip()

    @classmethod
    def clean(cls, text: str) -> str:
        """
        Full sanitization pipeline for TTS audio synthesis.
        
        Returns text suitable for direct TTS voice generation:
        - No emoji
        - Enforced 100% male tone
        - Abbreviations expanded to Thai pronunciation
        - No hashtags or markdown
        - Clean spacing
        """
        if not text:
            return ""

        result = text
        result = cls.strip_emoji(result)
        result = cls.enforce_male_tone(result)
        result = cls.expand_abbreviations(result)
        result = cls.clean_symbols(result)
        return result

    @classmethod
    def clean_script_lines(cls, lines: List[str]) -> List[str]:
        """Clean a list of script lines for TTS synthesis."""
        return [cls.clean(line) for line in lines if line.strip()]

    @classmethod
    def process_angle(cls, angle: Dict) -> Dict:
        """
        Process a full angle dict, separating display script lines from TTS spoken audio lines:
        
        - script_lines: kept for UI & on-screen subtitles (Rule 9 official English, 100% male tone, no ellipses)
        - tts_lines: prepared for Edge-TTS synthesis (clean Thai phonetic pronunciation, male tone, no emojis)
        - hook_title, product_name, tiktok_caption: sanitized with official English and male tone
        """
        result = dict(angle)

        # Enforce on product_name
        pname = angle.get("product_name", "")
        if pname:
            result["product_name"] = cls.clean_display_text(pname)

        # Clean script_lines for on-screen display
        script_lines = angle.get("script_lines", [])
        if isinstance(script_lines, list):
            raw_lines = script_lines
        elif isinstance(script_lines, str):
            raw_lines = script_lines.split('\n')
        else:
            raw_lines = []

        cleaned_display_lines = [
            cls.clean_display_text(line) for line in raw_lines if line.strip()
        ]
        result["script_lines"] = cleaned_display_lines
        result["script_text"] = "\n".join(cleaned_display_lines)

        # TTS lines: optimized for TTS synthesis engine
        result["tts_lines"] = cls.clean_script_lines(cleaned_display_lines)

        # Clean hook_title
        hook = angle.get("hook_title", "")
        if hook:
            result["hook_title"] = cls.clean_display_text(hook)
            result["tts_hook_title"] = cls.clean(hook)

        # Clean other fields
        for field in ["pain_point", "key_features", "price_deal", "tiktok_caption"]:
            if field in result and isinstance(result[field], str):
                result[field] = cls.clean_display_text(result[field])

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
