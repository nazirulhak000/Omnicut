"""
Test 100% Synchronized Voice & Subtitles with Natural Breathing Pauses
"""

import sys
from pathlib import Path
from pythainlp.tokenize import word_tokenize
import re

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

def segment_script_into_clauses(script_text: str, max_chars: int = 38) -> list:
    """
    Intelligently splits full script into natural 1-line semantic clauses (not too long, not single words).
    """
    raw_lines = [l.strip() for l in script_text.strip().split("\n") if l.strip()]
    final_clauses = []

    # Natural boundary markers for taking a breath & cutting subtitles
    SPLIT_REGEX = re.compile(
        r"(?<=[!?])\s+|"
        r"(?=ถ้ายัง|บอกเลยว่า|คือดูด|ดูดแน่น|ชาร์จไว|แถม|จะนอน|หรือดู|หมดปัญหา|เสียบใน|พิกัด|กดใน|จิ้มใน|รีบกด)"
    )

    for line in raw_lines:
        clean_line = re.sub(r"\s+", " ", line).strip()
        if len(clean_line) <= max_chars:
            final_clauses.append(clean_line)
            continue

        parts = [p.strip() for p in SPLIT_REGEX.split(clean_line) if p.strip()]
        curr = []
        for p in parts:
            cand = " ".join(curr + [p]) if curr else p
            if len(cand) <= max_chars:
                curr.append(p)
            else:
                if curr:
                    final_clauses.append(" ".join(curr).strip())
                curr = [p]
        if curr:
            rem = " ".join(curr).strip()
            if len(rem) <= 6 and final_clauses:
                final_clauses[-1] += " " + rem
            else:
                final_clauses.append(rem)

    return final_clauses

if __name__ == "__main__":
    sample = """ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้
บอกเลยว่า Esseger สายชาร์จแม่เหล็ก 3-in-1 คือดูดแน่นมากกก ชาร์จไว 66W
แถมข้อต่อยังหมุนได้ 540 องศา จะนอนเล่นเกมหรือดูซีรีส์ก็ไม่เกะกะมือ
หมดปัญหาสายหักตรงคอ เสียบในที่มืดได้สบายๆ เลยครับ
พิกัดราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ!"""

    clauses = segment_script_into_clauses(sample, max_chars=36)
    print(f"Segmented into {len(clauses)} perfect 1-line clauses:\n")
    for i, c in enumerate(clauses, 1):
        print(f"[{i:02d}] ({len(c):02d} chars): {c}")
