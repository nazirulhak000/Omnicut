"""
Angle catalog for IT products (headphones, cables, power banks, keyboards, hubs).

One product yields many clips. These angles are what the AI picks from, and what
the app falls back to when running without any LLM at all. Angles that can be
shot from seller photos alone are marked, because phase 1 posts before the
product physically arrives.
"""

from typing import Any, Dict, List, Optional

IT_ANGLE_CATALOG: List[Dict[str, Any]] = [
    {
        "key": "spec_compare",
        "name": "เทียบรุ่น / เทียบราคา",
        "description": "เอาสองราคามาชนกัน แล้วเฉลยว่าเงินที่จ่ายเพิ่มไปได้อะไร",
        "needs_own_footage": False,
        "proof_needed": "ตารางสเปคสองฝั่ง ตัวเลขต้องขึ้นจอ",
        "hook_patterns": [
            "ตัวละ {ราคาถูก} กับ {ราคาแพง} ต่างกันตรงไหน เดี๋ยวเทียบให้ดู",
            "จ่ายเพิ่ม {ส่วนต่าง} บาท ได้อะไรเพิ่มบ้าง",
        ],
        "fallback_hook": "{สินค้า} ถูกกับแพง ต่างกันตรงไหน เดี๋ยวเทียบให้ดูชัดๆ",
    },
    {
        "key": "fake_vs_real",
        "name": "ของแท้ vs ของปลอม",
        "description": "สอนเช็คจุดสังเกตก่อนกดซื้อ — มุมที่คนแชร์เยอะสุดในสาย IT",
        "needs_own_footage": False,
        "proof_needed": "ภาพซูมจุดสังเกต 3 จุด",
        "hook_patterns": [
            "เช็ค 3 จุดนี้ก่อน ไม่งั้นได้ของปลอมแน่",
            "{สินค้า} ปลอมระบาดหนัก ดูตรงนี้ก่อนกด",
        ],
        "fallback_hook": "{สินค้า} ปลอมระบาดหนัก เช็ค 3 จุดนี้ก่อนกดซื้อ",
    },
    {
        "key": "real_test",
        "name": "ทดสอบจริง",
        "description": "จับเวลาชาร์จจริง วัดไฟจริง ฟังเสียงจริง — น่าเชื่อถือสุด แต่ต้องมีของ",
        "needs_own_footage": True,
        "proof_needed": "หน้าจอมิเตอร์/นาฬิกาจับเวลาในเฟรมเดียวกับสินค้า",
        "hook_patterns": [
            "เคลมว่า {สเปค} จริงไหม จับเวลาให้ดูเลย",
            "ลองใช้จริง {ระยะเวลา} แล้ว บอกตรงๆ",
        ],
        "fallback_hook": "{สินค้า} ที่เขาเคลมกัน จริงไหม จับเวลาให้ดูเลย",
    },
    {
        "key": "spec_explained",
        "name": "สเปคที่คนอ่านไม่เป็น",
        "description": "แปลศัพท์เทคนิคเป็นภาษาคน — ดึงคนที่กำลังหาข้อมูลก่อนซื้อ",
        "needs_own_footage": False,
        "proof_needed": "ตัวเลขสเปคใหญ่ๆ บนจอ พร้อมคำแปลสั้น",
        "hook_patterns": [
            "{ศัพท์เทคนิค} คืออะไร ทำไมต้องสน",
            "เห็นคำว่า {ศัพท์เทคนิค} แล้วงงใช่ไหม 30 วิเข้าใจเลย",
        ],
        "fallback_hook": "สเปค {สินค้า} อ่านไม่เป็นใช่ไหม 30 วิเข้าใจเลย",
    },
    {
        "key": "pain_point",
        "name": "ปัญหาที่คนใช้เจอจริง",
        "description": "เปิดด้วยความเจ็บที่คนดูเพิ่งเจอเมื่อวาน แล้วค่อยเฉลยทางออก",
        "needs_own_footage": True,
        "proof_needed": "ภาพของพัง/ปัญหาจริง แล้วตัดไปของใหม่",
        "hook_patterns": [
            "ใครสายชาร์จพังเดือนละเส้น ดูคลิปนี้",
            "{ปัญหา} มาตลอด จนเจอตัวนี้",
        ],
        "fallback_hook": "ใครมีปัญหากับของเดิมมาตลอด จนเจอ {สินค้า} ตัวนี้",
    },
    {
        "key": "dont_cheap_out",
        "name": "ของถูกที่ไม่ควรประหยัด",
        "description": "เตือนภัย + ชี้ว่าประหยัดตรงไหนแล้วเสียหายกว่า",
        "needs_own_footage": False,
        "proof_needed": "ภาพความเสียหายจากของถูก + ตัวเลขค่าเสียหาย",
        "hook_patterns": [
            "ประหยัด {จำนวนเงิน} แต่เสีย {ค่าเสียหาย} คุ้มไหม",
            "ของ {ราคาถูก} บาท พังยังไงบ้าง",
        ],
        "fallback_hook": "ประหยัดค่า {สินค้า} ไม่กี่บาท แต่เสี่ยงพังทั้งเครื่อง คุ้มไหม",
    },
    {
        "key": "how_to_setup",
        "name": "วิธีใช้ให้คุ้ม",
        "description": "สอนตั้งค่า/ใช้งานให้ได้เต็มสเปค — คนดูจบสูง เก็บไว้ดูซ้ำ",
        "needs_own_footage": True,
        "proof_needed": "ขั้นตอนเป็นสเต็ป 1-2-3 บนจอ",
        "hook_patterns": [
            "ซื้อ {สินค้า} มาแล้วใช้ผิดกันเยอะมาก",
            "3 สเต็ปให้ {สินค้า} แรงเต็มสเปค",
        ],
        "fallback_hook": "ซื้อ {สินค้า} มาแล้วใช้ผิดกันเยอะมาก ทำ 3 สเต็ปนี้",
    },
    {
        "key": "worth_upgrade",
        "name": "อัปเกรดคุ้มไหม",
        "description": "จับกลุ่มคนที่มีของเดิมอยู่แล้ว — ตลาดที่คู่แข่งมักลืม",
        "needs_own_footage": False,
        "proof_needed": "เทียบของเดิม vs ของใหม่เป็นตัวเลข",
        "hook_patterns": [
            "ใช้ {ของเดิม} อยู่ ควรเปลี่ยนไหม",
            "อัปเป็น {สินค้า} คุ้มกับ {ราคา} หรือเปล่า",
        ],
        "fallback_hook": "ใช้ของเดิมอยู่ อัปเป็น {สินค้า} คุ้มหรือเปล่า",
    },
]

ANGLES_BY_KEY: Dict[str, Dict[str, Any]] = {a["key"]: a for a in IT_ANGLE_CATALOG}

# Which of the 4 existing LUTs (02_Assets/LUTs_ColorPresets) suits each angle,
# used as the auto-pick when a render doesn't specify lut_name explicitly.
# None means no grade -- pain_point and dont_cheap_out lean on unfiltered
# realism (showing a real problem/damage reads as more honest ungraded).
ANGLE_LUT_HINTS: Dict[str, Optional[str]] = {
    "spec_compare": "lut_tech_cool_contrast.cube",
    "spec_explained": "lut_tech_cool_contrast.cube",
    "worth_upgrade": "lut_tech_cool_contrast.cube",
    "real_test": "lut_bright_clean_product.cube",
    "how_to_setup": "lut_bright_clean_product.cube",
    "fake_vs_real": "lut_bright_clean_product.cube",
    "pain_point": None,
    "dont_cheap_out": None,
}

# Punch-zoom scale sequence per angle, replacing one fixed 6-value pattern
# for every clip regardless of content. Unlike ANGLE_LUT_HINTS this is safe
# to auto-apply -- it's the same ffmpeg scale/crop work either way, just
# different numbers, not an extra filter pass like lut3d.
#
# A comparison/explainer angle stays calmer so on-screen numbers stay
# readable; a warning/fake-vs-real angle punches harder for urgency.
LOOK_PRESETS: Dict[str, List[float]] = {
    "spec_compare": [1.0, 1.05, 1.0, 1.1],
    "spec_explained": [1.0, 1.05, 1.0],
    "worth_upgrade": [1.1, 1.0, 1.2, 1.0],
    "real_test": [1.1, 1.0, 1.15, 1.0],
    "how_to_setup": [1.0, 1.05, 1.0, 1.05],
    "fake_vs_real": [1.3, 1.0, 1.35, 1.0],
    "pain_point": [1.25, 1.0, 1.35, 1.05, 1.3, 1.0],
    "dont_cheap_out": [1.3, 1.0, 1.4, 1.0],
}

# BGM auto-pick per angle, from the mood a filename already hints at (none of
# these tracks were tagged with real metadata -- this mapping is a first
# pass from names alone, not a verified listen; swap values here if a track
# doesn't actually fit once heard). Used as the auto-pick when a render
# doesn't specify bgm_name explicitly -- same fallback tier as ANGLE_LUT_HINTS.
BGM_MOOD_MAP: Dict[str, str] = {
    "pain_point": "bgm_flash_sale_urgent.wav",       # urgency matches "this problem, fix it now"
    "dont_cheap_out": "bgm_cyber_phonk.wav",          # dark/warning tone
    "fake_vs_real": "bgm_hypetrance_wav.mp3",         # tense, dramatic reveal
    "real_test": "bgm_over_loaded_hiphop_instrumental.mp3",  # original hardcoded default, confident/hype
    "how_to_setup": "bgm_lofi_daily.wav",             # calm tutorial pace, rewatchable
    "worth_upgrade": "bgm_aesthetic_pop.wav",         # bright, comparison/decision mood
    "spec_compare": "bgm_brass_funk.wav",             # upbeat but not overpowering, numbers stay legible
    "spec_explained": "bgm_whistle_cozy.wav",         # warm, approachable explainer tone
}
DEFAULT_BGM = "tiktok_upbeat_bgm.wav"  # no angle_key given / no match


def catalog_for_prompt(seller_assets_only: bool = False) -> List[Dict[str, Any]]:
    """
    Trim the catalog to what the AI is allowed to pick from.

    With `seller_assets_only`, angles that require holding the product are
    dropped — phase 1 posts before anything ships.
    """
    angles = IT_ANGLE_CATALOG
    if seller_assets_only:
        angles = [a for a in angles if not a["needs_own_footage"]]

    return [
        {
            "key": a["key"],
            "name": a["name"],
            "description": a["description"],
            "hook_patterns": a["hook_patterns"],
        }
        for a in angles
    ]


def fallback_angles(product_name: str, seller_assets_only: bool = False) -> List[Dict[str, Any]]:
    """
    Ready-to-use angles for running with no LLM at all.

    These come from `fallback_hook`, not `hook_patterns`: the patterns carry
    placeholders like {ราคาถูก} that only a model can fill, and a half-filled
    hook with literal braces in it would go straight onto the screen.
    """
    source = IT_ANGLE_CATALOG
    if seller_assets_only:
        source = [a for a in source if not a["needs_own_footage"]]

    return [
        {
            "angle_key": a["key"],
            "title": a["name"],
            "hook": a["fallback_hook"].replace("{สินค้า}", product_name),
            "why_it_works": a["description"],
            "needs_own_footage": a["needs_own_footage"],
            "priority": 5,
        }
        for a in source
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(fallback_angles("หูฟังบลูทูธ", seller_assets_only=True), ensure_ascii=False, indent=2))
