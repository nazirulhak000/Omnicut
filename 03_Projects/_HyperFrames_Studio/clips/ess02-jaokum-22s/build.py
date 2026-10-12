"""Clip ess02-jaokum-22s: captions + SFX on the real whisper timestamps.
Run: python clips/ess02-jaokum-22s/build.py   (from the studio root or anywhere)
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "kit"))
from hf_timing import build  # noqa: E402

# (show_caption, [(display, whisper_spelling, cue_name_or_None), ...])
CLAUSES = [
    (False, [("สายเดินทาง", "สายเดินทาง", "hA"), ("คนทำงานออฟฟิศ", "คนทำงานออฟฟิส", "hB"),
             ("พกของเยอะๆ", "พกของเยอะๆ", "hC"), ("ฟังทางนี้", "ฟังทั้งนี้", "hD")]),
    (True, [("เบื่อไหม", "เบื่อไหม", "bue"), ("ต้องแบกหัวชาร์จ", "ต้องแบกหัวชาร์จ", "baek"), ("หนักๆ", "หนักๆ", "nak")]),
    (True, [("พะรุงพะรัง", "พลุงพลัง", "prung"), ("เต็มกระเป๋า", "เต็มกระเป๋า", "tem")]),
    (False, [("ลองเปลี่ยนมาพก", "ลองเปลี่ยนมาพก", "switch")]),
    (True, [("Essager", "Essager", "essager"), ("PD", "PD", "pd1"), ("30W", "30W", "w30a")]),
    (True, [("แค่ชิ้นเดียว", "แค่ชิ้นเดียว", "one"), ("จบ", "จบ", "jop")]),
    (True, [("รองรับ", "รองรับ", "rongrap"), ("iPad", "iPad", "ipad"), ("แท็บเล็ต", "Tablet", "tablet")]),
    (True, [("โทรศัพท์มือถือ", "โทรศัพท์มือถือ", "phone")]),
    (True, [("อุปกรณ์ขนาดเล็ก", "อุปกรณ์ขนาดเล็ก", "small")]),
    (True, [("ลดน้ำหนักกระเป๋า", "รถหนักระเป๋า", "lighter"), ("ได้เยอะ", "ได้เยอะ", "lot")]),
    (True, [("รีบกดซื้อ", "รีบกดซื้อ", "order"), ("ในตะกร้า", "ในตก้า", "basket")]),
    (True, [("ซ้ายล่าง", "สายร่าง", "leftdown"), ("ได้เลย", "ได้เลย", "last")]),
]


def sfx(c):
    return [  # (file, time, duration, volume) — every hit sits on a whisper cue or a cut
    ("pop.wav", c["hA"], 0.15, 0.55), ("pop.wav", c["hB"], 0.15, 0.55), ("pop.wav", c["hC"], 0.15, 0.55),
    ("boom.wav", c["hD"], 0.8, 0.4), ("whoosh2.mp3", c["bue"] - 0.1, 0.45, 0.35),
    ("boom.wav", c["nak"], 0.8, 0.6), ("whoosh.mp3", c["prung"], 0.5, 0.4),
    ("electric.mp3", c["switch"] - 0.2, 0.7, 0.4), ("boom.wav", c["switch"], 0.8, 0.55),
    ("whoosh.mp3", c["essager"] - 0.1, 0.5, 0.4), ("boom.wav", c["w30a"], 0.8, 0.45), ("ding.wav", c["jop"], 0.8, 0.4),
    ("whoosh.mp3", c["rongrap"] - 0.1, 0.5, 0.4), ("ding.wav", c["ipad"] + 0.18, 0.8, 0.35),
    ("ding.wav", c["tablet"] + 0.18, 0.8, 0.35), ("ding.wav", c["phone"] + 0.18, 0.8, 0.35),
    ("ding.wav", c["small"] + 0.18, 0.8, 0.35), ("whoosh2.mp3", c["lighter"] - 0.1, 0.45, 0.4),
    ("levelup.mp3", c["lighter"] + 0.2, 1.4, 0.3), ("boom.wav", c["order"], 0.8, 0.55), ("cash.wav", c["basket"], 0.7, 0.55),
]


if __name__ == "__main__":
    build(HERE, CLAUSES, sfx, caption_stop="order")
