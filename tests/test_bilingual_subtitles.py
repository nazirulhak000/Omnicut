import sys
import urllib.request
import urllib.parse
import json

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

def translate_th_to_en(text: str) -> str:
    clean = text.strip()
    if not clean:
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=th&tl=en&dt=t&q=" + urllib.parse.quote(clean)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return "".join([part[0] for part in data[0] if part[0]]).strip()
    except Exception as e:
        return ""

samples = [
    "ทุกคน! อย่าเพิ่งซื้อสายชาร์จธรรมดา",
    "ถ้ายังไม่เห็นตัวนี้",
    "Esseger สายชาร์จแม่เหล็ก 3-in-1",
    "ดูดแน่นมากกก ชาร์จไว 66W",
    "ข้อต่อหมุนได้ 540 องศา",
    "เล่นเกมไม่เกะกะมือ",
    "หมดปัญหาสายหักตรงคอ",
    "ราคาพิเศษวันนี้แค่ 149 บาท",
    "กดในตะกร้าซ้ายล่างได้เลยครับ!"
]

for s in samples:
    en = translate_th_to_en(s)
    print(f"🇹🇭 {s}\n🇬🇧 {en}\n")
