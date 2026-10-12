"""Clip hat01-meme-45s: captions + SFX on the real whisper timestamps.
Run: python clips/hat01-meme-45s/build.py
Cue names here are the ones compositions/hat01-meme-45s.html reads (T.<cue>).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "kit"))
from hf_timing import build  # noqa: E402

# (show_caption, [(display, whisper_spelling, cue_name_or_None), ...])
CLAUSES = [
    (False, [("อากาศไทยตอนนี้", "อากาศไทยตอนนี้", "heat"), ("ร้อน", "ร้อน", "hot"), ("กองไฟ", "กองไฟ", "fire"),
             ("ใครยังไหว", "ใครยังไหว", "alive")]),
    (True, [("เปิดแอร์", "เปิดแอร์", "air"), ("ทั้งวันทั้งคืน", "ทั้งวันทั้งคืน", "allday")]),
    (True, [("บิลค่าไฟมา", "บินค่าไฟมา", "bill")]),
    (True, [("เหงื่อแตก", "เหนื่อแตก", "sweat"), ("ยิ่งกว่าเดิม", "ยิ่งกว่าเดิม", None)]),
    (False, [("ใจเย็นครับ", "ใจเย็นครับ", "calm")]),
    (True, [("ทางรอด", "ทางรอด", "escape"), ("ของคนขี้ร้อนแล้ว", "ของคนที่ร้อนแล้ว", "escape2")]),
    (True, [("Hatari", "หาตาริ", "hatari"), ("T16M1", "T16M1", "model")]),
    (True, [("พัดลมตั้งโต๊ะ", "พัดลมตั้งโต๊ะ", "desk"), ("16 นิ้ว", "16นิ้ว", "inch")]),
    (True, [("ลองเอามือไปรับลม", "ลองเอามือไปรับลม", "hand"), ("แรงกำลังดี", "แรงกำลังดี", "strong")]),
    (True, [("ส่ายซ้ายขวา", "สายสายขวา", "swing"), ("กระจายลมทั่วห้อง", "กระจายลมทั่วห้อง", "spread")]),
    (True, [("ทั้งบ้าน", "ทางบ้าน", "family"), ("ไม่ต้องแย่งกัน", "ไม่ต้องแย่งกัน", "nofight")]),
    (True, [("มอเตอร์ Ball Bearing", "โมอเตอร์บอลแบริง", "motor")]),
    (True, [("หมุนลื่น", "หมุนลื่น", None), ("เสียงเงียบ", "เสียงเนียบ", "quiet")]),
    (True, [("เปิดนอนได้ทั้งคืน", "เปิดนอนได้ทั้งคืน", "sleep")]),
    (True, [("ประหยัดไฟเบอร์ 5", "ประยัติไฟเบอร์5", "no5"), ("กินไฟน้อย", "กินไฟน้อย", "low")]),
    (True, [("ค่าไฟไม่บานปลาย", "ค่าไฟไม่บานปลาย", "nobill")]),
    (True, [("Thermal Fuse", "ThermalFuse", "fuse"), ("ตัดไฟอัตโนมัติ", "ตัดไฟอัตโนมัติ", "cut")]),
    (True, [("รับประกันมอเตอร์", "รับรับการโมอเตอร์", "warranty"), ("3 ปีเต็ม", "3ปีเต็ม", "y3")]),
    (True, [("สเปกจัดเต็ม", "สเปคจัดเต็ม", "full"), ("ใครร้อนอยู่", "ใครร้อนอยู่", "whohot")]),
    (True, [("กดตะกร้าสีเหลือง", "กดตะกล้าสีเหลือง", "order"), ("ซ้ายล่าง", "สายล่าง", "leftdown")]),
]

# meme pauses: let the punchline land before the voice moves on
GAPS = [("bill", 0.9), ("escape2", 0.8), ("y3", 0.6)]


def sfx(c):
    return [  # (file in assets/shared/sfx, time, duration, volume) — meme hits on whisper cues
        ("pop.wav", c["heat"] + 0.05, 0.15, 0.5), ("vine_boom.mp3", c["hot"], 1.2, 0.45),
        ("fire.mp3", c["fire"] - 0.1, 2.0, 0.3), ("glass_break.mp3", c["fire"] - 0.12, 1.3, 0.55), ("pop.wav", c["alive"], 0.15, 0.55),
        ("whoosh2.mp3", c["air"] - 0.05, 0.45, 0.35), ("boom.wav", c["allday"], 0.8, 0.4),
        ("whoosh.mp3", c["bill"], 0.5, 0.4), ("emotional_damage.mp3", c["bill_end"] + 0.05, 1.5, 0.55),
        ("drip.mp3", c["sweat"] + 0.1, 0.5, 0.5), ("drip.mp3", c["sweat"] + 0.55, 0.5, 0.45),
        ("record_scratch.mp3", c["calm"] - 0.05, 0.78, 0.5), ("ding.wav", c["escape"], 0.8, 0.4),
        ("drumroll.mp3", c["escape2_end"] - 0.1, 1.05, 0.45), ("airhorn.mp3", c["hatari"] - 0.2, 1.3, 0.3),
        ("boom.wav", c["inch"], 0.8, 0.4),
        ("whoosh.mp3", c["hand"] - 0.1, 0.5, 0.45), ("whoosh2.mp3", c["strong"] - 0.05, 0.45, 0.5),
        ("whoosh.mp3", c["swing"] - 0.1, 0.5, 0.4), ("pop.wav", c["family"], 0.15, 0.55),
        ("whoosh2.mp3", c["motor"] - 0.1, 0.45, 0.35), ("ding.wav", c["quiet"] + 0.45, 0.8, 0.3),
        ("sleep.mp3", c["sleep"] + 0.1, 2.0, 0.3),
        ("boom.wav", c["no5"] + 0.2, 0.8, 0.5), ("cha_ching.mp3", c["nobill"], 1.6, 0.45),
        ("cinematic_boom.mp3", c["fuse"] + 0.3, 1.2, 0.45), ("electric.mp3", c["fuse"] + 0.35, 0.8, 0.35), ("boom.wav", c["y3"] + 0.15, 0.8, 0.5),
        ("wow.mp3", c["y3_end"] + 0.05, 1.3, 0.5),
        ("cash.wav", c["full"] + 0.1, 0.7, 0.45), ("boom.wav", c["order"], 0.8, 0.5),
        ("cash_register.mp3", c["order"] + 0.5, 1.0, 0.5),
    ]


if __name__ == "__main__":
    build(HERE, CLAUSES, sfx, caption_stop="order", gaps=GAPS)
