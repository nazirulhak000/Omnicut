"""
Text Wrapping and Bilingual Kinetic Highlighting Service for Subtitle Engine.
Handles line wrapping for Thai and English, 3-tier keyword highlighting,
and 100% color synchronization between stacked Thai and English subtitles.
"""

import re
from typing import Dict, List, Optional, Tuple

# Dynamic Kinetic Highlighting keywords (ASS color mapped)
# 🟡 &H0000E6FF& = Neon Yellow (Pain points, prices, deals, primary punch)
# 🔵 &H00FFE600& = Electric Cyan (Features, tech, ergonomics, certifications)
# 🔴 &H00303BFF& = Alert Red (Urgency, warnings)
KINETIC_KEYWORDS: Dict[str, List[str]] = {
    "&H0000E6FF&": [  # 🟡 Neon Yellow (Pain points, prices, deals, primary punch, positive reactions)
        "ออฟฟิศซินโดรม", "ปวดข้อมือ", "ปวดหลัง", "ปวดคอ", "ปวดหัว", "ปวดไหล่", "ปวดขา", "ปวดเมื่อย",
        "ปวดมือ", "ปวดตัว", "ปวด", "เมื่อยล้า", "เมื่อย", "ทรมาน", "เหนื่อยล้า", "เหนื่อย",
        "เจ็บมือ", "บาดมือ", "แสบตา", "รกโต๊ะ", "เสียงดังหนวกหู", "เสียงกวนใจ",
        "สายพันกัน", "สายขาด", "แบตหมดไว", "แบตเสื่อม", "กระตุก", "เครื่องค้าง", "ค้าง", "ช้ามาก", "ช้า",
        "พังง่าย", "พัง", "หักง่าย", "หัก", "เสียเงินฟรี", "เสียดายเงิน", "เสีย", "หลุดบ่อย", "หลุด",
        "สิวบุก", "สิวเห่อ", "สิวขึ้น", "เป็นสิว", "รอยสิว", "รอยดำ", "รอยแดง", "หน้ามัน", "หน้าหมอง", "หมองคล้ำ",
        "ผิวแห้ง", "ผิวลอก", "เหนียวเหนอะหนะ", "เหนอะหนะ", "คราบฝังลึก", "สกปรก", "กลิ่นอับ", "เหม็นอับ", "เหม็น",
        "อึดอัด", "แน่นพุง", "พุงยื่น", "ขาใหญ่", "ดูอ้วน", "เชยๆ", "เชย", "ล้าสมัย", "ไม่มั่นใจ", "ไม่สวย",
        "ปัญหา", "ยุ่งยาก", "เสียเวลา", "เปลืองแรง", "เปลืองเงิน", "หงุดหงิด",
        "ราคาพิเศษ", "ลดราคา", "ลดกระหน่ำ", "ลดแรง", "ดีลพิเศษ", "ดีลลับ", "โปรเด็ด", "โปรแรง", "โปรโมชั่น",
        "แฟลชเซล", "flash sale", "โค้ดลด", "โค้ดลับ", "คูปอง", "ส่งฟรี", "1 แถม 1", "หนึ่งแถมหนึ่ง",
        "ของแถม", "แจกฟรี", "ฟรี", "บาท", "หลักสิบ", "หลักร้อย", "ราคาดี", "ราคาโดน", "ถูกและดี",
        "ถูกสุดๆ", "ถูกมาก", "คุ้มสุดๆ", "คุ้มค่า", "คุ้มราคา", "เกินคุ้ม", "คุ้ม", "ประหยัด", "ตกใจราคา",
        "ตะกร้าส้ม", "ตะกร้าซ้ายล่าง", "ตะกร้า", "ใส่ตะกร้า", "จิ้มตะกร้า", "จิ้มเลย", "จิ้มตรงนี้", "กดตรงนี้",
        "พิกัดในคอมเมนต์", "พิกัดในโปรไฟล์", "พิกัด", "ปักหมุด", "อย่ารอ", "อย่าช้า", "ช้าหมด",
        "รีบตำ", "รีบจัด", "ด่วนเลย", "ด่วน", "ต้องมี", "ของมันต้องมี", "ขาดไม่ได้", "สอยด่วน", "รีบสอย",
        "เคาะราคา", "สั่งซื้อเลย", "กดลงตะกร้า", "ลิงก์หน้าโปรไฟล์", "กดที่ลิงก์", "จัดโปร", "ลดเยอะมาก",
        "ป้ายยา", "ตัวท็อป", "ตัวแม่", "ยืนหนึ่ง", "ตัวตึง", "ของดีบอกต่อ", "ใช้ดีบอกต่อ", "ของดี",
        "ดีจริง", "ดูดีมาก", "ดีมาก", "ดีเกินคาด", "ดีเกินราคา", "ว้าวมาก", "ว้าว", "ตาแตก", "ตะลึง",
        "สุดปัง", "ปังมาก", "จึ้งมาก", "จึ้ง", "เลิศมาก", "เลิศ", "เอาเรื่อง", "ของแทร่", "เปลี่ยนชีวิต",
        "ยกระดับ", "หลงรักเลย", "หลงรัก", "ชอบมาก", "ติดใจ", "ไม่ผิดหวัง", "ไม่จกตา", "รีวิวจริง",
        "ใช้จริง", "หมดปัญหา", "ลืมแบบเก่าไปเลย", "โคตรดี", "โคตรคุ้ม", "ฟินมาก", "ช็อค", "น่ารักกว่าในรูป", "ของที่รอคอย",
        "สมคำร่ำลือ", "ตอบโจทย์", "ตัวจริง", "ปังไม่ไหว", "สิบเต็มสิบ", "10/10", "คุ้มสุดในรุ่น", "ยืนยันอีกเสียง",
        "ขาดตัวนี้ไม่ได้", "ต้องมีติดบ้าน", "ไอเทมลับ", "ไอเทมเด็ด", "รอดไม่รอด", "ของมันต้องลอง", "ประทับใจ",
        "เกินต้าน", "ยอมใจ", "เด็ดจริง", "ไม่คิดว่าจะดี", "ดีกว่าที่คิด", "คุ้มเกินเบอร์", "ปังสุด", "สุดจัด",
        "ลองแล้วรัก", "ถูกใจมาก", "ใช้เองรีวิวเอง", "โนสปอน", "ซื้อเองใช้เอง", "ใช้จนหมด", "ซื้อซ้ำ", "ตุนด่วน", "ต้องตุน", "ตำด่วน", "ใช้ทุกวัน"
    ],
    "&H00FFE600&": [  # 🔵 Electric Cyan (Features, tech, ergonomics, certifications, comfort)
        "Logitech Wave Keys", "Logitech", "Wave Keys", "คีย์บอร์ดในฝัน", "คีย์บอร์ด", "ไร้สาย", "บลูทูธ",
        "แม่เหล็ก", "แรงดูดสูง", "ดูดแน่น", "540 องศา", "360 องศา", "ชาร์จไว", "ฟาสชาร์จ", "66W", "100W",
        "แบตอึด", "แบตทน", "ทนทาน", "แข็งแรง", "ประกันศูนย์", "ของแท้", "แท้ 100%", "จอสวย", "จอลื่น",
        "120Hz", "คมชัด", "กล้องชัด", "เสียงดี", "เบสแน่น", "ตัดเสียงรบกวน", "กันน้ำ", "ชิปเร็ว",
        "ลื่นไหล", "ไม่สะดุด", "เชื่อมต่อง่าย", "เสียบปุ๊บติดปั๊บ", "พกพาสะดวก", "น้ำหนักเบา", "กะทัดรัด",
        "ปรับระดับได้", "พับเก็บได้", "ประหยัดพื้นที่", "ประกอบง่าย", "ใช้งานง่าย",
        "ปุ่มเงียบ", "สวิตช์เงียบ", "ไร้สาย 2.4G", "ต่อได้ 3 อุปกรณ์", "สลับเครื่องไว", "รองรับ Mac และ Windows",
        "ปรับความสูงได้", "วัสดุพรีเมียม", "งานประกอบเนี๊ยบ", "แบตเตอรี่ใช้ได้นาน", "ชาร์จครั้งเดียวอยู่ได้ยาว", "จับถนัดมือ",
        "สรีรศาสตร์", "เมมโมรี่โฟม", "ที่รองข้อมือ", "พิมพ์สบาย", "นั่งสบาย", "นอนสบาย", "ใส่สบาย",
        "สบายมาก", "นุ่มสบาย", "สบายมือ", "สบายหลัง", "สบายตา", "สบายตัว", "สบาย", "นุ่มนิ่ม", "นุ่มฟู",
        "นุ่มมาก", "นุ่มๆ", "นุ่ม", "ยืดหยุ่น", "สัมผัสนุ่ม", "ไม่ระคายเคือง", "ไม่บาดผิว", "ทรงสวย",
        "ทรงเป๊ะ", "พอดีตัว", "เข้ารูป", "ทิ้งตัวสวย", "พรางหุ่น", "เก็บพุง", "ระบายอากาศ", "ไม่อับชื้น",
        "ไม่ร้อน", "เย็นสบาย", "มินิมอล", "ดีไซน์แบบคลื่นๆ", "แบบคลื่นๆ", "คลื่น", "ดีไซน์สวย",
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
        "ห้ามพลาด", "ห้ามเลื่อนผ่าน", "ของปลอมระบาด", "ซื้อผิดรุ่น", "ดูให้จบ", "ข้อเสีย", "สิ่งที่ควรรู้",
        "เช็กด่วน", "ระวังโดนหลอก", "ข้อควรระวัง", "อย่าเพิ่งเลื่อน", "เตือนไว้ก่อน", "ก่อนจะสาย", "จุดสังเกต", "ระวังผิดหวัง", "ดูตรงนี้ก่อน"
    ]
}

# Dynamic Kinetic Highlighting keywords for English (ASS color mapped)
KINETIC_KEYWORDS_EN: Dict[str, List[str]] = {
    "&H0000E6FF&": [  # 🟡 Neon Yellow (Pain points, prices, deals, primary punch, positive reactions)
        "office syndrome", "wrist pain", "back pain", "neck pain", "shoulder pain", "headache", "leg pain",
        "body pain", "hand hurts", "hurts", "painful", "pain", "tight", "sore", "exhausted",
        "tiring", "tired", "suffering", "messy desk", "noisy",
        "tangled", "broken cord", "dead battery", "low battery", "laggy", "lagging", "freezing", "too slow", "slow",
        "breaks easily", "broken", "waste of money", "waste of time", "wasted", "annoying",
        "acne breakout", "breakouts", "pimples", "dark spots", "redness", "oily skin", "dull skin",
        "dry skin", "peeling skin", "sticky", "greasy", "deep stains", "dirty", "bad odor", "smelly",
        "uncomfortable", "stuffy", "bloated", "tight fit", "outdated", "unconfident", "insecure",
        "problems", "problem", "frustrating", "troublesome", "not sure",
        "special price", "huge discount", "discount", "special deal", "secret deal", "best promo", "promotion",
        "flash sale", "promo code", "voucher", "coupon", "free shipping", "buy 1 get 1", "bogo",
        "free gift", "giveaway", "free", "baht", "super cheap", "cheap", "affordable", "best price",
        "best value", "great value", "worth every penny", "worth it", "save money", "shocking price",
        "yellow basket", "orange basket", "cart", "add to cart", "click cart", "click now", "click here",
        "pinned link", "link in bio", "coordinates", "don't wait", "don't delay", "almost gone",
        "buy now", "grab it now", "hurry up", "must have", "essential", "check profile link", "grab yours",
        "holy grail", "game changer", "life-changing", "top tier", "the best", "highly recommend",
        "really good", "looks really good", "looks good", "so good", "very good", "good", "exceeded expectations",
        "unbelievable", "very wow", "wow", "mind blowing", "stunning", "gorgeous", "slay",
        "aesthetic", "next level", "fell in love", "obsessed", "love it", "no regret", "won't be disappointed",
        "real review", "tried and tested", "problem solved", "insanely good", "super worth it", "so satisfying",
        "much cuter", "long-awaited", "recommend", "10 out of 10", "10/10", "worth the hype", "honest review",
        "holy grail item", "no sponsor", "bought it myself", "repurchase", "stock up", "daily staple"
    ],
    "&H00FFE600&": [  # 🔵 Electric Cyan (Features, tech, ergonomics, certifications, comfort)
        "logitech wave keys", "wave keys", "logitech", "dream keyboard", "keyboard", "wireless", "bluetooth",
        "magnetic", "strong magnet", "540 degrees", "360 degrees", "fast charging", "quick charge", "66w", "100w",
        "long battery", "battery life", "durable", "sturdy", "warranty", "genuine", "authentic", "smooth screen",
        "120hz", "crystal clear", "sharp camera", "great sound", "deep bass", "noise cancelling", "anc", "waterproof",
        "fast chip", "ultra smooth", "easy connect", "plug and play", "portable", "lightweight", "compact",
        "adjustable", "foldable", "space saving", "easy to assemble", "easy to use",
        "silent keys", "quiet typing", "multi-device", "easy switch", "mac and windows compatible",
        "ergonomic", "ergonomics", "memory foam", "wrist rest", "typing comfortable", "sit comfortably",
        "comfortable fit", "comfortable", "comfy", "super comfy", "soft and comfy", "extra soft", "pillow soft",
        "very soft", "soft", "flexible", "gentle touch", "non-irritating", "flattering fit",
        "perfect fit", "slim fit", "tummy control", "breathable", "airy", "cool and fresh",
        "minimalist", "minimal", "wavy design", "wavy", "sleek design", "beautiful design",
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
        "look at this", "watch this", "warn", "stop", "before you buy", "watch out", "critical warning", "check this before buying"
    ]
}

_EN_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "am", "of", "to", "in",
    "on", "at", "for", "with", "and", "or", "but", "if", "it", "its", "this", "that",
    "these", "those", "as", "by", "from", "up", "out", "so", "than", "then", "too",
    "very", "can", "will", "just", "not", "no", "do", "does", "did", "you", "your",
    "i", "my", "we", "our", "they", "their", "he", "she", "his", "her", "how", "what",
    "who", "why", "when", "where", "all", "any", "more", "most", "some", "such", "own",
    "about", "into", "over", "also", "have", "has", "had", "would", "could", "should",
}

_TH_PARTICLES = {
    "ครับ", "ค่ะ", "คะ", "นะ", "น่ะ", "จ้า", "เลย", "ก็", "ที่", "ซึ่ง", "และ", "หรือ",
    "แต่", "กับ", "ของ", "ใน", "จะ", "ได้", "ให้", "มา", "ไป", "อยู่", "คือ", "ว่า",
    "เป็น", "มี", "ไม่", "แล้ว", "ด้วย", "อีก", "มัน", "เรา", "เขา", "ทั้ง", "ทุก",
}


def wrap_text_for_ass(text: str, max_chars_per_line: int = 40) -> str:
    """
    Wraps long Thai text into multiple balanced lines using ASS \\N.
    Mirrors wrapCanvasText() in SequencePlayer.jsx.
    """
    if not text:
        return ""
    raw_paras = str(text).replace("\\N", "\n").split("\n")
    result_lines = []

    prefixes = {"ผู้", "การ", "ความ", "นัก", "ชาว", "จาก"}

    for para in raw_paras:
        clean = re.sub(r'\s+', ' ', re.sub(r'[\.]{2,}|…', ' ', para)).strip().replace("\r", "")
        if not clean:
            continue
        if len(clean) <= max_chars_per_line:
            result_lines.append(clean)
            continue

        try:
            from pythainlp.tokenize import word_tokenize
            raw_words = word_tokenize(clean, engine="newmm")
        except Exception:
            raw_words = clean.split(" ")

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
            result_lines.extend([l1, l2])
            continue

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
        result_lines.extend(lines if lines else [clean])

    return "\\N".join(result_lines) if result_lines else str(text).strip()


def wrap_en_for_ass(text: str, max_chars_per_line: int = 58) -> str:
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


def apply_kinetic_highlighting(
    text: str,
    primary_color_ass: str = "&H00FFFFFF&",
    color_hint: Optional[str] = None,
    custom_keywords: Optional[List[str]] = None
) -> str:
    """
    Scans Thai text for power keywords with 3-tier intelligence.
    """
    if not text:
        return text

    clean_primary = primary_color_ass if primary_color_ass.endswith("&") else f"{primary_color_ass}&"
    result = text
    chosen_color = color_hint or "&H0000E6FF&"

    marker_pattern = re.compile(r"(\*([^*]+)\*|\[([^\]]+)\])")
    if marker_pattern.search(result):
        def _replace_marker(m):
            kw = m.group(2) or m.group(3)
            return f"{{\\c{chosen_color}}}{kw}{{\\c{clean_primary}}}"
        return marker_pattern.sub(_replace_marker, result)

    if "{\\c" in text:
        return text

    def _safe_replace_kw(target_str: str, kw: str, color_tag: str) -> str:
        idx = target_str.find(kw)
        if idx == -1:
            return target_str
        prefix = ""
        if idx > 0 and '\u0e00' <= target_str[idx - 1] <= '\u0e7f' and not target_str[idx - 1].isspace():
            prefix = " "
        replacement = f"{prefix}{{\\c{color_tag}}}{kw}{{\\c{clean_primary}}}"
        return target_str[:idx] + replacement + target_str[idx + len(kw):]

    if custom_keywords:
        for ckw in sorted(custom_keywords, key=len, reverse=True):
            if len(ckw) >= 2 and ckw in result:
                cyan_color = color_hint or "&H00FFE600&"
                return _safe_replace_kw(result, ckw, cyan_color)

    color_order = [color_hint] if color_hint else list(KINETIC_KEYWORDS.keys())
    for color_tag in color_order:
        kw_list = KINETIC_KEYWORDS.get(color_tag, [])
        for kw in sorted(kw_list, key=len, reverse=True):
            if kw in result and f"{{\\c{color_tag}}}" not in result:
                return _safe_replace_kw(result, kw, color_tag)

    return result


def apply_kinetic_highlighting_en(
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

    marker_pattern = re.compile(r"(\*([^*]+)\*|\[([^\]]+)\])")
    if marker_pattern.search(result):
        def _replace_marker(m):
            kw = m.group(2) or m.group(3)
            return f"{{\\c{chosen_color}}}{kw}{{\\c{clean_primary}}}"
        return marker_pattern.sub(_replace_marker, result)

    if "{\\c" in text:
        return text

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

    color_order = [color_hint] if color_hint else list(KINETIC_KEYWORDS_EN.keys())
    for color_tag in color_order:
        kw_list = KINETIC_KEYWORDS_EN.get(color_tag, [])
        for kw in sorted(kw_list, key=len, reverse=True):
            pattern = re.compile(rf"(?i)\b{re.escape(kw)}\b")
            match = pattern.search(result)
            if match and f"{{\\c{color_tag}}}" not in result:
                matched_str = match.group(0)
                start, end = match.span()
                result = result[:start] + f"{{\\c{color_tag}}}{matched_str}{{\\c{clean_primary}}}" + result[end:]
                return result

    return result


def _salient_word_en(text: str) -> Optional[str]:
    """Longest non-stopword token, as the thing worth colouring."""
    best = None
    for raw in re.findall(r"[A-Za-z][A-Za-z'-]*", text):
        if raw.lower() in _EN_STOPWORDS or len(raw) < 3:
            continue
        if best is None or len(raw) > len(best):
            best = raw
    return best


def _salient_word_th(text: str) -> Optional[str]:
    """Longest non-particle Thai token; falls back to the longest run of Thai letters."""
    candidates: List[str] = []
    try:
        from pythainlp.tokenize import word_tokenize
        candidates = [w.strip() for w in word_tokenize(text, engine="newmm") if w.strip()]
    except Exception:
        candidates = re.findall(r"[฀-๿]+", text)
    best = None
    for w in candidates:
        if w in _TH_PARTICLES or len(w) < 3:
            continue
        if not re.search(r"[฀-๿]", w):
            continue
        if best is None or len(w) > len(best):
            best = w
    return best


def _force_highlight(text: str, word: Optional[str], colour: str, primary: str) -> str:
    """Colour `word` inside `text` using the same wrapper the matchers use."""
    if not word or word not in text:
        return text
    clean_primary = primary if primary.endswith("&") else f"{primary}&"
    idx = text.find(word)
    if idx == -1:
        return text
    prefix = ""
    if idx > 0 and '\u0e00' <= text[idx - 1] <= '\u0e7f' and not text[idx - 1].isspace():
        prefix = " "
    replacement = f"{prefix}{{\\c{colour}}}{word}{{\\c{clean_primary}}}"
    return text[:idx] + replacement + text[idx + len(word):]


def apply_bilingual_kinetic_highlighting(
    th_text: str,
    en_text: str,
    primary_th: str = "&H00FFFFFF&",
    primary_en: str = "&H00EAEAEA&",
    custom_keywords: Optional[List[str]] = None
) -> Tuple[str, str]:
    """
    Guarantees 100% color synchronization between stacked Thai and English subtitles.
    """
    th_res = apply_kinetic_highlighting(th_text, primary_color_ass=primary_th, custom_keywords=custom_keywords)
    th_color = None
    if "{\\c" in th_res:
        m = re.search(r"\{\\c(&H[0-9A-Fa-f]+&)\}", th_res)
        if m:
            th_color = m.group(1)

    en_res = apply_kinetic_highlighting_en(en_text, primary_color_ass=primary_en, color_hint=th_color, custom_keywords=custom_keywords)
    en_color = None
    if "{\\c" in en_res:
        m = re.search(r"\{\\c(&H[0-9A-Fa-f]+&)\}", en_res)
        if m:
            en_color = m.group(1)

    if not th_color and en_color:
        th_res = apply_kinetic_highlighting(th_text, primary_color_ass=primary_th, color_hint=en_color, custom_keywords=custom_keywords)
        th_color = en_color if "{\\c" in th_res else None

    if th_color and not en_color:
        en_res = _force_highlight(en_res, _salient_word_en(en_text), th_color, primary_en)
    elif en_color and not th_color:
        th_res = _force_highlight(th_res, _salient_word_th(th_text), en_color, primary_th)
    elif th_color and en_color and th_color != en_color:
        en_res = re.sub(r"\{\\c&H[0-9A-Fa-f]+&\}", f"{{\\c{th_color}}}", en_res)

    return th_res, en_res
