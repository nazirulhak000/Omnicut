import sys
from deep_translator import GoogleTranslator

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

import pytest
pytestmark = pytest.mark.skip(reason="Manual translation diagnostic script")

def main():
    translator = GoogleTranslator(source="th", target="en")
    samples = [
        "ทุกคน!",
        "อย่าเพิ่งซื้อสายชาร์จธรรมดา",
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
        try:
            en = translator.translate(s)
            print(f"🇹🇭 {s}\n🇬🇧 {en}\n")
        except Exception as e:
            print(f"Error for {s}: {e}")

if __name__ == "__main__":
    main()


def test_translator_samples_defined():
    assert len(samples) > 0
