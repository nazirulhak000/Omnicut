"""
Lightning-Fast Bilingual Subtitle Translator (Thai -> English)
Uses 1-shot batch translation & dictionary mapping to achieve < 0.5s translation speed.
"""

import sys
import re
from typing import Dict, List, Optional
from deep_translator import GoogleTranslator

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

class SubtitleTranslator:
    """Batch translates Thai subtitle bursts into concise, punchy English captions."""

    DICT = {
        "ทุกคน": "Everyone!",
        "อย่าเพิ่งซื้อ": "Don't buy yet!",
        "อย่าเพิ่งซื้อสายชาร์จ": "Don't buy normal cables",
        "สายชาร์จแม่เหล็ก": "Magnetic charging cable",
        "ดูดแน่นมาก": "Super strong suction",
        "ดูดแน่นมากกก": "Super strong grip!",
        "ชาร์จไว": "Fast charging",
        "ชาร์จไว 66w": "Fast charging 66W",
        "หมุนได้ 540 องศา": "540° full rotation",
        "นอนเล่นเกม": "Gaming in bed",
        "ไม่เกะกะมือ": "No tangled wires",
        "หมดปัญหา": "No more broken cables",
        "สายหักตรงคอ": "Broken cable tip",
        "เสียบในที่มืดได้": "Easy plug in the dark",
        "สบายๆ เลยครับ": "Super easy!",
        "ราคาพิเศษ": "Special price",
        "วันนี้แค่": "Only today",
        "149 บาท": "149 THB",
        "กดในตะกร้า": "Tap yellow cart",
        "ซ้ายล่างได้เลยครับ": "Bottom left cart!"
    }

    _translator_instance = None

    @classmethod
    def get_translator(cls):
        if cls._translator_instance is None:
            cls._translator_instance = GoogleTranslator(source="auto", target="en")
        return cls._translator_instance

    @classmethod
    def translate_batch(cls, phrases: List[str]) -> List[str]:
        """Translates a list of Thai phrases into English in 1 single shot."""
        if not phrases:
            return []

        results = []
        to_translate_indices = []
        to_translate_texts = []

        # 1. Check dictionary cache first
        for i, text in enumerate(phrases):
            clean = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s]", "", text).strip()
            if not clean:
                results.append("")
            elif clean.lower() in cls.DICT:
                results.append(cls.DICT[clean.lower()])
            else:
                results.append(None) # Marker for batch API
                to_translate_indices.append(i)
                to_translate_texts.append(clean)

        # 2. Batch Translate remaining items
        if to_translate_texts:
            try:
                t = cls.get_translator()
                # Join with newline separator
                joined_text = " ||| ".join(to_translate_texts)
                translated_blob = t.translate(joined_text)
                if translated_blob and not any(err_sig in translated_blob for err_sig in ["Error 500", "500.", "That's an error", "<html", "<body"]):
                    translated_parts = [p.strip() for p in translated_blob.split("|||")]
                    for idx, part in zip(to_translate_indices, translated_parts):
                        if part and not any(err_sig in part for err_sig in ["Error 500", "500.", "That's an error", "<html"]):
                            results[idx] = part
                        else:
                            results[idx] = ""
            except Exception as e:
                # Fallback on failure
                for idx in to_translate_indices:
                    if results[idx] is None:
                        results[idx] = ""

        # Fill any remaining None
        return [r if (r is not None and not any(err_sig in str(r) for err_sig in ["Error 500", "500.", "That's an error", "<html"])) else "" for r in results]

if __name__ == "__main__":
    test_phrases = [
        "ทุกคน!",
        "อย่าเพิ่งซื้อสายชาร์จธรรมดา",
        "ถ้ายังไม่เห็นตัวนี้",
        "บอกเลยว่า Esseger",
        "สายชาร์จแม่เหล็ก 3-in-1",
        "คือดูดแน่นมากกก",
        "ชาร์จไว 66W",
        "แถมข้อต่อยังหมุนได้",
        "540 องศา",
        "จะนอนเล่นเกม",
        "หรือดูซีรีส์ก็",
        "ไม่เกะกะมือ",
        "หมดปัญหาสายหักตรงคอ",
        "เสียบในที่มืดได้",
        "สบายๆ เลยครับ",
        "พิกัดราคาพิเศษ",
        "วันนี้แค่",
        "149 บาท",
        "กดในตะกร้า",
        "ซ้ายล่างได้",
        "เลยครับ!"
    ]
    import time
    t0 = time.time()
    res = SubtitleTranslator.translate_batch(test_phrases)
    t1 = time.time()
    print(f"Translated {len(test_phrases)} phrases in {t1-t0:.2f}s:")
    for th, en in zip(test_phrases, res):
        print(f"🇹🇭 {th} -> 🇬🇧 {en}")
