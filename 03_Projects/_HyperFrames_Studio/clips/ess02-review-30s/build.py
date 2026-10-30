"""Clip ess02-review-30s: captions + SFX on the real whisper timestamps.
Run: python clips/ess02-review-30s/build.py   (from the studio root or anywhere)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "kit"))
from hf_timing import build  # noqa: E402

# (show_caption, [(display, whisper_spelling, cue_name_or_None), ...])
CLAUSES = [
    (False, [("หัวชาร์จแถม", "หัวชาร์จแถม", "hookA"), ("เก่าๆ", "เก่าเก่า", "hookB"),
             ("ชาร์จช้า", "ชาร์จชา", "hookC"), ("เป็นเต่า", "เป็นเต่า", "hookD")]),
    (False, [("เปลี่ยนมาดู", "เปลี่ยนมาดู", "switch"), ("ตัวนี้", "ตัวนี้", "tuani")]),
    (True, [("Essager", "เอสเจอ", "essager"), ("PD", "PD", "pd1"), ("30W", "30วัตต์", "w30a")]),
    (True, [("หัวชาร์จไว", "หัวชาร์จไว", "small"), ("ตัวจิ๋ว", "ตัวจิว", "jiw")]),
    (True, [("เล็กแค่ฝ่ามือ", "เล็กแค่ฝ่ามือ", "palm")]),
    (True, [("พกไปไหน", "พกไปไหน", "pok"), ("ก็ง่าย", "ก็ง่าย", None)]),
    (True, [("จ่ายไฟ", "จ่ายไฟ", "jaifai"), ("แรงสุด", "แรงสุด", None), ("30 วัตต์", "30วัตต์", "w30b")]),
    (True, [("รองรับ", "รองรับ", "rongrap"), ("PD", "PD", "pd2"), ("ชาร์จไว", "ชาร์จไว", None)]),
    (True, [("iPhone", "iPhone", "iphone"), ("15", "15", "n15"), ("และ", "และ", None), ("16", "16", "n16")]),
    (True, [("ได้", "ได้", None), ("เต็มสปีด", "เต็มสปีด", "speed")]),
    (True, [("ชาร์จแค่", "ชาร์จแค่", "chaek"), ("30 นาที", "30นาที", "min30")]),
    (True, [("แบตขึ้นถึง", "แบตขึ้นถึง", "bat"), ("50%", "50%", "p50")]),
    (True, [("ประหยัดเวลา", "ประหยัดเวลา", "prayat"), ("ไปเยอะมาก", "ไปเยอะมาก", None)]),
    (True, [("มีระบบ", "มีระบบ", "mira"), ("ป้องกันไฟเกิน", "ป้องกันไฟเกิน", "safe1")]),
    (True, [("ใช้ยาวๆ", "ใช้ยาวๆ", "chaiyao"), ("ไม่ร้อนจัด", "ไม่ร้อนจัด", "safe2")]),
    (True, [("ถนอม", "ถนอม", "safe3"), ("แบตเตอรี่", "แบตเตอรี่", None)]),
    (True, [("หัวชาร์จไว", "หัวชาร์จไว", "cta1"), ("คุ้มๆ", "คุมๆ", "kum"), ("แบบนี้", "แบบนี้", None)]),
    (True, [("กดสั่ง", "กดสั่ง", "order"), ("ในตะกร้าสีเหลือง", "ในตะกล้าสีเหลือง", "basket")]),
    (True, [("ซ้ายล่าง", "สายล่าง", "leftdown"), ("ได้เลย", "ได้เลย", "last")]),
]


def sfx(c):
    return [  # (file, time, duration, volume) — every hit sits on a whisper cue or a cut
    ("pop.wav", c["hookA"], 0.15, 0.55), ("pop.wav", c["hookB"], 0.15, 0.55), ("pop.wav", c["hookC"], 0.15, 0.55),
    ("electric.mp3", 2.86, 0.7, 0.4), ("boom.wav", 3.04, 0.8, 0.55),
    ("pop.wav", c["tuani"], 0.15, 0.6),
    ("whoosh.mp3", 4.72, 0.5, 0.4), ("whoosh2.mp3", c["w30a"] - 0.05, 0.45, 0.4), ("boom.wav", c["w30a"], 0.8, 0.45),
    ("whoosh.mp3", 7.04, 0.5, 0.4), ("pop.wav", c["jiw"] + 0.5, 0.15, 0.6),
    ("whoosh2.mp3", 8.7, 0.45, 0.35), ("ding.wav", c["palm"], 0.8, 0.3),
    ("electric.mp3", c["jaifai"], 1.0, 0.35), ("boom.wav", c["w30b"], 0.8, 0.6),
    ("whoosh2.mp3", 13.35, 0.45, 0.35), ("ding.wav", c["pd2"], 0.8, 0.35),
    ("whoosh.mp3", 14.58, 0.5, 0.4), ("iphone.mp3", c["iphone"] + 0.1, 1.2, 0.45), ("whoosh.mp3", c["speed"] - 0.1, 0.5, 0.5),
    ("whoosh2.mp3", 17.2, 0.45, 0.35), ("levelup.mp3", c["p50"], 1.4, 0.35), ("boom.wav", c["p50"], 0.8, 0.5),
    ("whoosh2.mp3", 22.2, 0.45, 0.35), ("ding.wav", c["safe1"] + 0.18, 0.8, 0.35),
    ("ding.wav", c["safe2"] + 0.18, 0.8, 0.35), ("ding.wav", c["safe3"] + 0.18, 0.8, 0.35),
    ("whoosh.mp3", 27.04, 0.5, 0.4), ("boom.wav", c["order"], 0.8, 0.55), ("cash.wav", c["basket"], 0.7, 0.55),
]


if __name__ == "__main__":
    build(HERE, CLAUSES, sfx, caption_stop="order")
