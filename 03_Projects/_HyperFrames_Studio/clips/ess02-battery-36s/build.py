"""Clip ess02-battery-36s: captions + SFX on the real whisper timestamps.
Run: python clips/ess02-battery-36s/build.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "kit"))
from hf_timing import build  # noqa: E402

# (show_caption, [(display, whisper_spelling, cue_name_or_None), ...])
# whisper spelling: แบตเหลือน 1%แต่อีก 10 นาทีต้องออกจากบ้าน ใครเคยเป็นบ้างครับ เสียบหัวชาร์จแถมเก่าๆไว้ ผ่านไปครึ่งชั่วโมงแบตขึ้นมาแค่นี้เดียวพอกันทีครับ วันนี้ผมเปลี่ยนมาใช้ตัวนี้Exager PD 30W หัวชาร์จตัวจิ๋ว เล็กแค่ฝ่ามือจ่ายไฟแรงสุด 30 วัต์ รองรับ PD ชาร์จไว iPhone 15 และ 16 ได้เต็มสปีดช้าแค่ 30 นาทีแบตขึ้นถึง 50% มีระบบป้องกันไฟเกิน ใช้ยาวๆ ไม่ร้อนจัดออกจากบ้านทันเวลาแบบชิ้วๆ ใครแบตหมดบ่อย กดตักร่าสีเหลืองสายล่างได้เลยครับ
CLAUSES = [
    (False, [("แบตเหลือ", "แบตเหลือน", "bat"), ("1%", "1%", "one"), ("อีก 10 นาที", "อีก10นาที", "ten"),
             ("ต้องออกจากบ้าน", "ต้องออกจากบ้าน", "leave"), ("ใครเคยเป็นบ้าง", "ใครเคยเป็นบ้าง", "who")]),
    (True, [("หัวชาร์จแถมเก่าๆ", "หัวชาร์จแถมเก่าๆ", "old")]),
    (True, [("ผ่านไปครึ่งชั่วโมง", "ผ่านไปครึ่งชั่วโมง", "halfhour")]),
    (True, [("แบตขึ้นมาแค่นิดเดียว", "แบตขึ้นมาแค่นี้เดียว", "tinybat")]),
    (False, [("พอกันที", "พอกันที", "enough"), ("เปลี่ยนมาใช้ตัวนี้", "เปลี่ยนมาใช้ตัวนี้", "switch")]),
    (True, [("Essager", "Exager", "essager"), ("PD", "PD", "pd1"), ("30W", "30W", "w30a")]),
    (True, [("หัวชาร์จตัวจิ๋ว", "หัวชาร์จตัวจิ๋ว", "small"), ("เล็กแค่ฝ่ามือ", "เล็กแค่ฝ่ามือ", "palm")]),
    (True, [("จ่ายไฟแรงสุด", "จ่ายไฟแรงสุด", "jaifai"), ("30 วัตต์", "30วัต์", "w30b")]),
    (True, [("รองรับ PD", "รองรับPD", "pd2"), ("ชาร์จไว", "ชาร์จไว", "fast")]),
    (True, [("iPhone 15 และ 16", "iPhone15และ16", "iphone"), ("ได้เต็มสปีด", "ได้เต็มสปีด", "speed")]),
    (True, [("ชาร์จแค่ 30 นาที", "ช้าแค่30นาที", "min30"), ("แบตขึ้นถึง 50%", "แบตขึ้นถึง50%", "p50")]),
    (True, [("มีระบบป้องกันไฟเกิน", "มีระบบป้องกันไฟเกิน", "safe")]),
    (True, [("ใช้ยาวๆ", "ใช้ยาวๆ", None), ("ไม่ร้อนจัด", "ไม่ร้อนจัด", "cool")]),
    (True, [("ออกจากบ้านทันเวลา", "ออกจากบ้านทันเวลา", "ontime"), ("แบบชิลๆ", "แบบชิ้วๆ", "chill")]),
    (True, [("ใครแบตหมดบ่อย", "ใครแบตหมดบ่อย", "who2")]),
    (True, [("กดตะกร้าสีเหลือง", "กดตักร่าสีเหลือง", "order"), ("ซ้ายล่าง", "สายล่าง", "leftdown")]),
]

# meme pauses (STYLE.md: after the pain punchline, before the reveal, after the closing benefit)
GAPS = [("tinybat", 0.9), ("switch", 0.8), ("p50", 0.6)]


def sfx(c):
    return [  # (file in assets/shared/sfx, time, duration, volume) — meme hits on whisper cues
        ("pop.wav", c["bat"], 0.15, 0.5), ("vine_boom.mp3", c["one"], 1.2, 0.5),
        ("clock_tick.mp3", c["ten"], 2.0, 0.35), ("pop.wav", c["leave"], 0.15, 0.5),
        ("whoosh.mp3", c["old"] - 0.1, 0.5, 0.4), ("few_moments_later.mp3", c["halfhour"] - 0.05, 2.2, 0.45),
        ("sad_trombone.mp3", c["tinybat_end"] + 0.02, 1.6, 0.45),
        ("record_scratch.mp3", c["enough"] - 0.05, 0.78, 0.5), ("ding.wav", c["switch"], 0.8, 0.4),
        ("drumroll.mp3", c["switch_end"] - 0.1, 0.9, 0.45), ("airhorn.mp3", c["essager"] - 0.3, 1.3, 0.3),
        ("whoosh2.mp3", c["w30a"] - 0.05, 0.45, 0.4), ("boom.wav", c["w30a"], 0.8, 0.45),
        ("whoosh.mp3", c["small"] - 0.1, 0.5, 0.4), ("pop.wav", c["palm"], 0.15, 0.55),
        ("electric.mp3", c["jaifai"], 1.0, 0.35), ("boom.wav", c["w30b"], 0.8, 0.55),
        ("whoosh2.mp3", c["pd2"] - 0.05, 0.45, 0.35), ("ding.wav", c["pd2"] + 0.15, 0.8, 0.35),
        ("iphone.mp3", c["iphone"], 1.2, 0.45), ("whoosh.mp3", c["speed"] - 0.1, 0.5, 0.5),
        ("whoosh2.mp3", c["min30"] - 0.05, 0.45, 0.35), ("levelup.mp3", c["p50"], 1.4, 0.35),
        ("wow.mp3", c["safe"] - 0.55, 1.3, 0.5), ("cinematic_boom.mp3", c["safe"] + 0.3, 1.2, 0.45),
        ("pop.wav", c["cool"], 0.15, 0.55), ("chill_guy.mp3", c["chill"] - 0.1, 1.3, 0.35),
        ("cash.wav", c["who2"] + 0.1, 0.7, 0.45), ("boom.wav", c["order"], 0.8, 0.5),
        ("cash_register.mp3", c["order"] + 0.5, 1.0, 0.5),
    ]


if __name__ == "__main__":
    build(HERE, CLAUSES, sfx, caption_stop="order", gaps=GAPS)
