"""
Angle catalog for IT products (headphones, cables, power banks, keyboards, hubs).

One product yields many clips. These angles are what the AI picks from, and what
the app falls back to when running without any LLM at all. Angles that can be
shot from seller photos alone are marked, because phase 1 posts before the
product physically arrives.
"""

from typing import Any, Dict, List

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
    },
]

ANGLES_BY_KEY: Dict[str, Dict[str, Any]] = {a["key"]: a for a in IT_ANGLE_CATALOG}


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
    """Angles with hooks filled in by string substitution, for running with no LLM."""
    source = IT_ANGLE_CATALOG
    if seller_assets_only:
        source = [a for a in source if not a["needs_own_footage"]]

    return [
        {
            "angle_key": a["key"],
            "title": a["name"],
            "hook": a["hook_patterns"][0].replace("{สินค้า}", product_name),
            "why_it_works": a["description"],
            "needs_own_footage": a["needs_own_footage"],
            "priority": 5,
        }
        for a in source
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(fallback_angles("หูฟังบลูทูธ", seller_assets_only=True), ensure_ascii=False, indent=2))
