"""Clip goc01-spec-42s: captions + SFX on the real whisper timestamps.
Run: python clips/goc01-spec-42s/build.py
Cue names here are the ones compositions/goc01-spec-42s.html reads (T.<cue>).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "kit"))
from hf_timing import build  # noqa: E402

# (show_caption, [(display, whisper_spelling, cue_name_or_None), ...])
CLAUSES = [
    # 1. Hook (Kinetic title handles the hook words, so show_caption=False)
    (False, [
        ("คนทำคลิป", "คนทำคลิป", "creator"),
        ("สายไลฟ์สด", "สายหลายสด", "live"),
        ("เจอปัญหา", "เจอปัญหา", "prob"),
        ("เสียงพัดลม", "เสียงพัดลม", "fan"),
        ("ดังรบกวน", "ดังรบกวน", "noise"),
        ("หยุดฟังทางนี้", "หยุดฟังทางนี้", "stop"),
        ("ก่อนครับ", "ก่อนครับ", "calm"),
    ]),
    # 2. Pain
    (True, [
        ("อัดคลิปทีไร", "อัดคลิปที่ไร", "rec"),
        ("เสียงรอบข้าง", "เสียงรอบข้าง", "env"),
        ("ดังแทรกเข้ามา", "ดังแซ่เข้ามา", "intrude"),
        ("ตลอด", "ตลอด", "always"),
    ]),
    (True, [
        ("ทำให้วิดีโอของเรา", "ทำให้วีดีโอของเรา", "video"),
        ("ดูไม่เป็นมืออาชีพ", "ดูไม่เป็นมืออาชีพ", "unprof"),
        ("เลยใช่ไหมครับ", "เลยใช่ไหมครับ", "ask"),
    ]),
    # 3. Hero Reveal & Compatibility
    (True, [
        ("หมดกังวล", "หมดกังวน", "noworries"),
        ("ได้เลยครับ", "ได้เลยครับ", "fine"),
    ]),
    (True, [
        ("แค่ใช้ไมค์ไร้สาย", "แค่ใช้มัยร้ายสาย", "mic"),
        ("GoChek", "GoCheck", "brand"),
        ("Ultra S24", "UltraS24", "model"),
    ]),
    (True, [
        ("เสียบใช้งานง่าย", "เสียบใช้งานง่าย", "easy"),
        ("ทั้งมือถือ", "ทั้งมือถือ", "phone"),
        ("iPad", "iPad", "ipad"),
        ("และคอมพิวเตอร์", "และComputer", "pc"),
    ]),
    # 4. Spec 1: Smart CSC 2.0 & INFER 1.0
    (True, [
        ("ตัวนี้มีระบบ", "ตัวนี้มีระบบ", "csc_sys"),
        ("Smart CSC 2.0", "สมาร์ทCSC2.0", "csc_name"),
        ("กรองเสียงรบกวน", "กรองเสียงรบกวน", "csc_filter"),
        ("สูงถึง 90%", "สูงถึง90%", "csc_90"),
    ]),
    (True, [
        ("พร้อมชิป INFER 1.0", "พร้อมชิปInferr1.0", "chip"),
        ("ให้คุณภาพเสียงดี", "ให้คุณภาพเสียงดี", "sound"),
        ("คมชัดสมจริงครับ", "คมชัดสมจริงครับ", "real"),
    ]),
    # 5. Spec 2: Case & 35h Battery
    (True, [
        ("แถมยังมีกล่องชาร์จ", "แถมยังมีกล่องชัด", "case"),
        ("อัตโนมัติ", "อัตโนมัติ", "auto"),
    ]),
    (True, [
        ("พกพาไปใช้งาน", "พกพาไปใช้งาน", "carry"),
        ("นอกสถานที่", "นอกสถานที่", "outdoor"),
        ("สูงสุดถึง 35 ชั่วโมง", "ได้นามรวมสูงสุดถึง35ชั่วโมง", "h35"),
    ]),
    (True, [
        ("น้ำหนักเบา", "น้ำหนักเบา", "light"),
        ("แถมแข็งแกร่งมากครับ", "แถมแข็งแกร่งมากครับ", "tough"),
    ]),
    # 6. CTA (stops at cart so kinetic CTA box takes over)
    (True, [
        ("ไมค์ไร้สาย", "ไม่ร้ายสาย", "cta_mic"),
        ("สเปกจัดเต็มขนาดนี้", "สเปคจัดเต็มขนาดนี้", "cta_full"),
        ("ราคาพิเศษสุดคุ้ม", "ราคาพิเศษสุดคุม", "cta_price"),
    ]),
    (True, [
        ("กดสั่งในตะกร้าสีเหลือง", "กดสั่งในตักร่าสีเหลือง", "cart"),
        ("ซ้ายล่าง", "สายล่าง", "leftdown"),
        ("ตอนนี้ได้เลยครับ", "ตอนนี้ได้เลยครับ", "now"),
    ]),
]

# Meme pauses: let punchline & sound land before voice continues
GAPS = [
    ("ask", 0.75),       # After "เลยใช่ไหมครับ" -> emotional damage / sigh
    ("fine", 0.70),      # After "ได้เลยครับ" -> record scratch / whoosh into hero
    ("real", 0.65),      # After "คมชัดสมจริงครับ" -> mind blown / wow
]


def sfx(c):
    return [  # (file in assets/shared/sfx, time, duration, volume)
        # Hook (0 - 5.5s)
        ("pop.wav", c["creator"] + 0.05, 0.15, 0.5),
        ("whoosh.mp3", c["live"] - 0.05, 0.45, 0.4),
        ("vine_boom.mp3", c["prob"], 1.2, 0.5),
        ("fire.mp3", c["fan"] - 0.1, 1.8, 0.25),
        ("glass_break.mp3", c["noise"] - 0.05, 1.2, 0.5),
        ("record_scratch.mp3", c["stop"] - 0.05, 0.75, 0.55),
        ("pop.wav", c["calm"], 0.15, 0.5),

        # Pain (5.5 - 11.5s)
        ("whoosh2.mp3", c["rec"] - 0.05, 0.45, 0.4),
        ("drip.mp3", c["env"] + 0.1, 0.5, 0.5),
        ("boom.wav", c["intrude"], 0.8, 0.45),
        ("sad_trombone.mp3", c["unprof"] + 0.1, 1.5, 0.45),
        ("emotional_damage.mp3", c["ask_end"] + 0.05, 1.5, 0.55),

        # Solution / Reveal (11.5 - 18.5s)
        ("record_scratch.mp3", c["noworries"] - 0.05, 0.7, 0.5),
        ("drumroll.mp3", c["fine_end"] - 0.1, 0.9, 0.45),
        ("airhorn.mp3", c["brand"] - 0.15, 1.3, 0.35),
        ("cinematic_boom.mp3", c["model"] - 0.1, 1.2, 0.5),
        ("whoosh.mp3", c["easy"] - 0.05, 0.5, 0.4),
        ("pop.wav", c["phone"], 0.15, 0.5),
        ("pop.wav", c["ipad"], 0.15, 0.5),
        ("levelup.mp3", c["pc"] + 0.1, 0.8, 0.45),

        # Spec 1 - Smart CSC & INFER chip (19 - 28s)
        ("whoosh2.mp3", c["csc_sys"] - 0.05, 0.45, 0.35),
        ("boom.wav", c["csc_name"], 0.8, 0.45),
        ("ding.wav", c["csc_filter"], 0.8, 0.4),
        ("cinematic_boom.mp3", c["csc_90"], 1.2, 0.5),
        ("electric.mp3", c["chip"] + 0.1, 0.8, 0.4),
        ("levelup.mp3", c["sound"], 0.8, 0.45),
        ("wow.mp3", c["real_end"] + 0.05, 1.3, 0.5),

        # Spec 2 - Case & 35h Battery (28 - 36s)
        ("whoosh.mp3", c["case"] - 0.05, 0.5, 0.4),
        ("ding.wav", c["auto"], 0.8, 0.4),
        ("boom.wav", c["h35"], 0.8, 0.5),
        ("chill_guy.mp3", c["h35"] + 0.5, 1.8, 0.45),
        ("whoosh2.mp3", c["light"] - 0.05, 0.45, 0.4),
        ("boom.wav", c["tough"], 0.8, 0.45),

        # CTA (36 - 44s)
        ("cash.wav", c["cta_mic"] + 0.1, 0.7, 0.45),
        ("cha_ching.mp3", c["cta_price"] + 0.1, 1.5, 0.5),
        ("boom.wav", c["cart"], 0.8, 0.55),
        ("cash_register.mp3", c["cart"] + 0.4, 1.2, 0.55),
    ]


if __name__ == "__main__":
    build(HERE, CLAUSES, sfx, caption_stop="cart", gaps=GAPS)
