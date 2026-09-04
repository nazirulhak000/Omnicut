"""
Lightning-Fast Bilingual Subtitle Translator (Thai -> English)
Uses 1-shot batch translation & dictionary mapping to achieve < 0.5s translation speed.
"""

import sys
import re
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

class SubtitleTranslator:
    """Batch translates Thai subtitle bursts into concise, punchy English captions."""

    # Generic Thai spoken-review phrases -> concise English equivalents
    # Universal & product-agnostic: works for any category (beauty, gadgets, home, fashion, food)
    DICT = {
        "ทุกคน":              "Everyone!",
        "อย่าเพิ่งซื้อ":      "Don't buy yet!",
        "หมดปัญหา":           "Problem solved",
        "ราคาพิเศษ":          "Special price",
        "วันนี้แค่":          "Only today",
        "กดในตะกร้า":         "Tap the cart",
        "ซ้ายล่างได้เลยครับ": "Bottom-left cart!",
        "คุ้มมาก":            "Super worth it!",
        "รีบกด":              "Order now",
        "ของมันต้องมี":       "Must-have item",
        "บอกเลยว่า":          "Honestly",
        "คือมันดีมาก":        "It's really great",
        "รู้งี้ซื้อตั้งนานแล้ว": "Wish I bought it sooner",
        "สบายๆ เลยครับ":      "Super easy!",
        "เนี่ยดูดิ":          "Check this out",
        "โคตรคุ้ม":           "Insanely good value",
        "พิกัดในตะกร้า":      "Find it in the cart",
        "ส่งฟรี":             "Free shipping",
        "ของแท้":             "100% Authentic",
        "ของแท้แน่นอน":       "Guaranteed authentic",
        "ห้ามพลาด":           "Don't miss out",
        "ใช้ง่ายมาก":         "Super easy to use",
        "สวยมาก":             "Looks gorgeous",
        "คุณภาพดีมาก":        "Top quality",
        "ลดราคาพิเศษ":        "Huge discount",
        "จิ้มที่ตะกร้า":      "Tap the cart",
        "โปรโมชั่นวันนี้":    "Today's promo",
        "พิกัดที่ลิงก์":      "Link in bio",
        "มีเก็บเงินปลายทาง":  "Cash on delivery available",
        "ลองแล้วจะติดใจ":     "You will love it",
    }

    _translator_instance = None

    @classmethod
    def get_translator(cls):
        if cls._translator_instance is None:
            cls._translator_instance = GoogleTranslator(source="auto", target="en")
        return cls._translator_instance


    _CACHE: Dict[str, str] = {}

    @classmethod
    def _translate_single(cls, text: str, custom_dict: Optional[Dict[str, str]] = None) -> str:
        if not text:
            return ""
        norm_text = text.lower().strip()
        if custom_dict and norm_text in custom_dict:
            return custom_dict[norm_text]
        if norm_text in cls.DICT:
            return cls.DICT[norm_text]
        if text in cls._CACHE:
            return cls._CACHE[text]
        # One attempt used to be the whole story: a single hiccup (and the
        # free endpoint rate-limits readily when several phrases go out at
        # once) returned "" and that cue simply never got an English line.
        # Failures scattered through a clip rather than clustering, which is
        # what a per-request limit looks like -- so retry with a short backoff
        # before giving up.
        for attempt in range(3):
            try:
                t = GoogleTranslator(source="auto", target="en")
                res = t.translate(text)
                if res and not any(sig in res for sig in ["Error 500", "500.", "That's an error", "<html", "<body"]):
                    cleaned = res.strip().replace("\n", " ").replace("\\", "")
                    cls._CACHE[text] = cleaned
                    return cleaned
            except Exception:
                pass
            if attempt < 2:
                time.sleep(0.4 * (attempt + 1))

        # Some phrases make the free Google endpoint answer with its own
        # "Error 500" page every single time, however many retries -- two of
        # this project's lines did exactly that. A second provider clears
        # them, and it is the difference between a bilingual caption and a
        # Thai-only one.
        try:
            from deep_translator import MyMemoryTranslator

            res = MyMemoryTranslator(source="th-TH", target="en-US").translate(text)
            if res and not any(sig in res for sig in ["Error 500", "500.", "That's an error", "<html", "<body"]):
                cleaned = res.strip().replace("\n", " ").replace("\\", "")
                cls._CACHE[text] = cleaned
                return cleaned
        except Exception:
            pass
        return ""

    @classmethod
    def translate_batch(cls, phrases: List[str], custom_dict: Optional[Dict[str, str]] = None) -> List[str]:
        """Translates a list of Thai phrases into English with guaranteed 1-to-1 exact alignment."""
        if not phrases:
            return []

        cleaned_phrases = []
        for text in phrases:
            clean = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s.,!?-]", "", text).strip()
            cleaned_phrases.append(clean)

        norm_custom = {k.lower().strip(): v for k, v in custom_dict.items()} if custom_dict else None

        # 6 parallel requests is what provoked the rate-limiting in the first
        # place; 3 with retries finishes about as fast and comes back whole.
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(lambda p: cls._translate_single(p, norm_custom), cleaned_phrases))

        # Never fail silently: a missing English line is invisible in the ASS
        # (the cue just renders Thai-only), so say it out loud instead.
        failed = [p for p, r in zip(cleaned_phrases, results) if p and not r]
        if failed:
            print(f"   ⚠️  แปลอังกฤษไม่สำเร็จ {len(failed)}/{len(cleaned_phrases)} บรรทัด: {failed[:3]}")

        return results

if __name__ == "__main__":
    test_phrases = [
        "ทุกคน!",
        "อย่าเพิ่งซื้อ",
        "ถ้ายังไม่เห็นคลิปนี้",
        "บอกเลยว่า",
        "ของมันต้องมี",
        "คือมันดีมาก",
        "ใช้ง่ายมาก",
        "หมดปัญหาเดิมๆ",
        "สบายๆ เลยครับ",
        "พิกัดราคาพิเศษ",
        "วันนี้แค่",
        "199 บาท",
        "กดในตะกร้า",
        "ซ้ายล่างได้เลยครับ!"
    ]
    import time
    t0 = time.time()
    res = SubtitleTranslator.translate_batch(test_phrases)
    t1 = time.time()
    print(f"Translated {len(test_phrases)} phrases in {t1-t0:.2f}s:")
    for th, en in zip(test_phrases, res):
        print(f"🇹🇭 {th} -> 🇬🇧 {en}")
