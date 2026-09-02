import sys
from deep_translator import GoogleTranslator

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

t = GoogleTranslator(source="auto", target="en")

samples = [
    "ทุกคน",
    "อย่าเพิ่งซื้อสายชาร์จธรรมดา",
    "ถ้ายังไม่เห็นตัวนี้",
    "สายชาร์จแม่เหล็ก 3 in 1",
    "ดูดแน่นมาก ชาร์จไว 66W",
    "ข้อต่อหมุนได้ 540 องศา",
    "นอนเล่นเกมไม่เกะกะมือ",
    "หมดปัญหาสายหักตรงคอ",
    "ราคาพิเศษวันนี้แค่ 149 บาท",
    "กดในตะกร้าซ้ายล่างได้เลย"
]

for s in samples:
    try:
        res = t.translate(s)
        print(f"{s} -> {res}")
    except Exception as e:
        print(f"Failed {s}: {e}")
