"""Clip ess02-vs-25s: captions + SFX on the real whisper timestamps.
Run: python clips/ess02-vs-25s/build.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "kit"))
from hf_timing import build  # noqa: E402

# (show_caption, [(display, whisper_spelling, cue_name_or_None), ...])
# whisper spelling: สึกหัวชาร์จ ฝั่งซ้าย ฝั่งซ้าย หัวชาแถมรุ่นเก่า 5 วัตต์ ฝั่งขวา Essager PD 30 วัตต์ยกแรกความแรง ฝั่งซ้ายจ่ายไฟแค่ 5 วัตต์ ฝั่งขวาจัดเต็ม 30 วัตต์ยกสอง ความไว ชาร์ 30 นาที ฝั่งขวาแบบตขึ้นถึง 50%ยกสาม ความปลอดภัย มีระบบป้องกันไฟเกินใช้ยาวๆ ไม่ร้อนจัดผู้ชนะคือ Essager ใครอยากได้ กดตะกร้าเหลือง ซ้ายล่างเลย
CLAUSES = [
    (False, [("ศึกหัวชาร์จ", "สึกหัวชาร์จ", "title")]),
    (True, [("ฝั่งซ้าย", "ฝั่งซ้าย", "left"), ("หัวชาร์จแถมรุ่นเก่า 5W", "หัวชาแถมรุ่นเก่า5วัตต์", "oldname")]),
    (True, [("ฝั่งขวา", "ฝั่งขวา", "right"), ("Essager PD 30W", "EssagerPD30วัตต์", "essname")]),
    (False, [("ยกแรก", "ยกแรก", "r1"), ("ความแรง", "ความแรง", "r1t")]),
    (True, [("ฝั่งซ้ายจ่ายไฟแค่ 5 วัตต์", "ฝั่งซ้ายจ่ายไฟแค่5วัตต์", "r1l"), ("ฝั่งขวาจัดเต็ม 30 วัตต์", "ฝั่งขวาจัดเต็ม30วัตต์", "r1r")]),
    (False, [("ยกสอง", "ยกสอง", "r2"), ("ความไว", "ความไว", "r2t")]),
    (True, [("ชาร์จ 30 นาที", "ชาร์30นาที", "r2a"), ("ฝั่งขวาแบตขึ้นถึง 50%", "ฝั่งขวาแบบตขึ้นถึง50%", "r2r")]),
    (False, [("ยกสาม", "ยกสาม", "r3"), ("ความปลอดภัย", "ความปลอดภัย", "r3t")]),
    (True, [("มีระบบป้องกันไฟเกิน", "มีระบบป้องกันไฟเกิน", "r3a"), ("ใช้ยาวๆ ไม่ร้อนจัด", "ใช้ยาวๆไม่ร้อนจัด", "r3b")]),
    (False, [("ผู้ชนะคือ", "ผู้ชนะคือ", "win"), ("Essager", "Essager", "winner")]),
    (True, [("ใครอยากได้", "ใครอยากได้", "want"), ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "order"), ("ซ้ายล่างเลย", "ซ้ายล่างเลย", "leftdown")]),
]

# fight-game beats: VS clash, K.O., YOU WIN land in the pauses
GAPS = [("essname", 0.6), ("r3b", 0.7), ("winner", 0.8)]


def sfx(c):
    return [  # fighting-game sound design
        ("fight_bell.mp3", c["title"], 1.6, 0.4), ("whoosh.mp3", c["left"], 0.5, 0.45),
        ("whoosh.mp3", c["right"], 0.5, 0.45), ("critical_hit.mp3", c["essname_end"] - 0.1, 1.3, 0.55),
        ("fight_fx.mp3", c["r1"] - 0.1, 1.4, 0.4), ("punch.mp3", c["r1l"] + 0.1, 0.8, 0.35),
        ("boom.wav", c["r1r"] + 0.2, 0.8, 0.5), ("punch.mp3", c["r1r"] + 0.6, 0.8, 0.6),
        ("whoosh2.mp3", c["r2"] - 0.05, 0.45, 0.4), ("levelup.mp3", c["r2r"], 1.4, 0.3), ("punch.mp3", c["r2r"] + 1.1, 0.8, 0.6),
        ("whoosh2.mp3", c["r3"] - 0.05, 0.45, 0.4), ("cinematic_boom.mp3", c["r3a"] + 0.2, 1.2, 0.45),
        ("critical_hit.mp3", c["r3b_end"], 1.3, 0.6), ("boom.wav", c["r3b_end"] + 0.05, 0.8, 0.6),
        ("airhorn.mp3", c["winner"] - 0.1, 1.3, 0.3), ("cash_register.mp3", c["order"] + 0.3, 1.0, 0.5),
    ]


if __name__ == "__main__":
    build(HERE, CLAUSES, sfx, caption_stop="order", gaps=GAPS)
