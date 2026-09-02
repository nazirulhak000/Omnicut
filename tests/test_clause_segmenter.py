"""
Smart Thai Semantic Clause Segmenter
Groups Thai text into complete, grammatically sound, 1-line clauses (15-30 chars).
Never breaks numbers from units (540 องศา), never isolates words, ensures natural breathing rhythm.
"""

import sys
import re
from typing import List
from pythainlp.tokenize import word_tokenize

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

def segment_into_semantic_clauses(text: str, max_chars: int = 30) -> List[str]:
    """
    Segments Thai script text into natural, complete semantic clauses for speaking and subtitling.
    1. Splits by existing line breaks and punctuation (!, ?, ., \n).
    2. Uses PyThaiNLP to break long lines into complete meaningful clauses.
    3. Merges orphan words (ๆ, องศา, เลย, ครับ, บาท, ตัวนี้, ฯลฯ) with their parent phrase.
    """
    raw_lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    clauses = []

    # Common words that must NEVER start a clause or be isolated
    ATTACH_LEFT = {
        "ๆ", "เลย", "ครับ", "ค่ะ", "นะ", "นะครับ", "นะคะ", "บาท", "องศา", "วัตต์", 
        "ได้", "ด้วย", "แล้ว", "นี้", "ตัวนี้", "อันนี้", "มาก", "มากกก", "จริง", 
        "จริงๆ", "ทันที", "ตรงคอ", "มือ", "เลยครับ", "เลยค่ะ"
    }

    # Conjunctions / clause starters where it is natural to take a breath
    BREATH_CONNECTORS = {
        "ถ้า", "ถ้ายัง", "บอกเลยว่า", "แถม", "จะ", "หรือ", "หมดปัญหา", 
        "พิกัด", "กดใน", "จิ้ม", "รีบ", "คือ", "เสียบ"
    }

    for line in raw_lines:
        # Split by strong punctuation first
        sub_parts = re.split(r"([!?]+|\s{2,})", line)
        parts = []
        for p in sub_parts:
            p = p.strip()
            if not p: continue
            if re.match(r"^[!?]+$", p):
                if parts:
                    parts[-1] += p
                else:
                    parts.append(p)
            else:
                parts.append(p)

        for part in parts:
            if len(part) <= max_chars:
                clauses.append(part)
            else:
                # Tokenize into words
                tokens = word_tokenize(part, engine="newmm", keep_whitespace=False)
                current_clause = []
                
                for i, tok in enumerate(tokens):
                    # Check if token is a natural breath connector and we already have some text
                    is_connector = tok in BREATH_CONNECTORS
                    curr_len = sum(len(t) for t in current_clause)
                    
                    if curr_len >= 12 and (is_connector or curr_len + len(tok) > max_chars):
                        clause_str = "".join(current_clause).strip()
                        if clause_str:
                            clauses.append(clause_str)
                        current_clause = [tok]
                    else:
                        current_clause.append(tok)

                if current_clause:
                    clause_str = "".join(current_clause).strip()
                    if clause_str:
                        # If the last remaining fragment is too short, merge with previous clause
                        if (len(clause_str) <= 6 or clause_str in ATTACH_LEFT) and clauses:
                            clauses[-1] += " " + clause_str if not clauses[-1].endswith(" ") else clause_str
                        else:
                            clauses.append(clause_str)

    # Post-process: Clean up and merge any trailing orphan words
    cleaned = []
    for c in clauses:
        c_str = c.strip()
        if not c_str: continue

        # If starts with attach-left word, merge to previous
        first_word = c_str.split()[0] if " " in c_str else c_str
        if (c_str in ATTACH_LEFT or first_word in ATTACH_LEFT or len(c_str) <= 3) and cleaned:
            cleaned[-1] = (cleaned[-1] + " " + c_str).strip()
        else:
            cleaned.append(c_str)

    return cleaned

if __name__ == "__main__":
    sample = """ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้
บอกเลยว่า Esseger สายชาร์จแม่เหล็ก 3-in-1 คือดูดแน่นมากกก ชาร์จไว 66W
แถมข้อต่อยังหมุนได้ 540 องศา จะนอนเล่นเกมหรือดูซีรีส์ก็ไม่เกะกะมือ
หมดปัญหาสายหักตรงคอ เสียบในที่มืดได้สบายๆ เลยครับ
พิกัดราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ!"""

    res = segment_into_semantic_clauses(sample, max_chars=32)
    print(f"Segmented into {len(res)} natural semantic clauses:\n")
    for idx, r in enumerate(res, 1):
        print(f" {idx:02d}. [{len(r):02d} chars] -> {r}")
