import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

from pythainlp.tokenize import word_tokenize

def smart_thai_split(text: str, max_chars: int = 16) -> list:
    """Split Thai sentence into natural 2-3 word micro-bursts for TikTok subtitles."""
    # 1. Split by spaces or obvious punctuation
    clean = text.strip()
    raw_parts = [p.strip() for p in clean.replace("!", "! ").replace("?", "? ").split() if p.strip()]
    
    bursts = []
    for part in raw_parts:
        if len(part) <= max_chars:
            bursts.append(part)
        else:
            # Use PyThaiNLP to break long segments cleanly
            tokens = word_tokenize(part, engine="newmm", keep_whitespace=False)
            curr = []
            for tok in tokens:
                curr.append(tok)
                curr_len = sum(len(x) for x in curr)
                if len(curr) >= 3 or curr_len >= 12:
                    bursts.append("".join(curr))
                    curr = []
            if curr:
                bursts.append("".join(curr))
    return bursts

samples = [
    "ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา ถ้ายังไม่เห็นตัวนี้",
    "บอกเลยว่า Esseger สายชาร์จแม่เหล็ก 3-in-1 คือดูดแน่นมากกก ชาร์จไว 66W",
    "แถมข้อต่อยังหมุนได้ 540 องศา จะนอนเล่นเกมหรือดูซีรีส์ก็ไม่เกะกะมือ",
    "หมดปัญหาสายหักตรงคอ เสียบในที่มืดได้สบายๆ เลยครับ",
    "พิกัดราคาพิเศษวันนี้แค่ 149 บาท กดในตะกร้าซ้ายล่างได้เลยครับ!"
]

for s in samples:
    b = smart_thai_split(s)
    print(f"\nOriginal: {s}")
    print(f"Bursts ({len(b)}): {b}")
