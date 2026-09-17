import pytest
from scripts import gemini_vision_matcher as gvm


def test_visual_contrast_avoids_back_to_back_macro():
    """Verify that after a macro_closeup shot, the matcher prefers broader action/front angles over another macro."""
    catalog = {
        "is_spin_footage": False,
        "scenes": [
            {
                "id": 1,
                "start": 0.0,
                "end": 6.0,
                "action_type": "closeup",
                "angle_phase": "macro_closeup",
                "description": "ช็อตเด็ดมาโคร โชว์โลโก้ สกรีนคมชัดกลางเฟรม",
                "keywords": ["โลโก้", "สกรีนชัดเจน", "hero"],
                "punch_zoom": 1.25,
            },
            {
                "id": 2,
                "start": 6.0,
                "end": 12.0,
                "action_type": "closeup",
                "angle_phase": "macro_closeup",
                "description": "มาโครส่องหัวน็อตและช่องลำโพงระยะประชิด",
                "keywords": ["หัวน็อต", "ลำโพง"],
                "punch_zoom": 1.25,
            },
            {
                "id": 3,
                "start": 12.0,
                "end": 18.0,
                "action_type": "hands_on",
                "angle_phase": "front",
                "description": "มือจับตัวเครื่องทดสอบการใช้งานจริง",
                "keywords": ["ใช้งาน", "มือจับ"],
                "punch_zoom": 1.10,
            },
        ],
    }

    cues = [
        {"start": 0.0, "end": 2.5, "text": "ทุกคนครับ นี่คือหูฟังตัวท็อป โลโก้ชัดเจนครับ"},
        {"start": 2.5, "end": 5.0, "text": "ใช้งานจริงจับถนัดมือมาก พกพาสะดวกครับ"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(catalog, cues, raw_duration=30.0)
    assert len(matched) == 2

    # Shot 1: Hero Macro Logo (Scene 1)
    assert matched[0]["scene_start"] == 0.0
    assert "macro_closeup" in matched[0]["visual_reason"]

    # Shot 2: Must NOT be another macro_closeup (Scene 2), should contrast to hands_on / front (Scene 3)
    assert matched[1]["scene_start"] == 12.0
    assert "hands_on" in matched[1]["visual_reason"]
    assert "macro_closeup" not in matched[1]["visual_reason"]


def test_jbl_sequence_angle_progression():
    """Verify that a multi-shot video achieves diverse angle rotation and avoids Jump Cuts."""
    catalog = {
        "is_spin_footage": False,
        "scenes": [
            {"id": 1, "start": 0.0, "end": 7.0, "action_type": "hands_on", "angle_phase": "front", "description": "มือหยิบหูฟังสาย JBL โชว์ความยาวสาย", "keywords": ["หูฟัง", "สายหูฟัง"], "punch_zoom": 1.1},
            {"id": 2, "start": 7.0, "end": 15.0, "action_type": "closeup", "angle_phase": "side", "description": "โชว์หูฟังด้านข้าง", "keywords": ["ด้านข้าง"], "punch_zoom": 1.15},
            {"id": 6, "start": 37.0, "end": 45.0, "action_type": "port_connection", "angle_phase": "macro_closeup", "description": "โชว์หัวเชื่อมต่อแบบ USB Type-C สกรีนโลโก้ JBL", "keywords": ["Type-C", "USB-C", "หัวเสียบ"], "punch_zoom": 1.2},
            {"id": 8, "start": 56.0, "end": 67.0, "action_type": "feature_demo", "angle_phase": "front", "description": "สาธิตระบบแม่เหล็กที่หลังหูฟัง ประกบติดกัน", "keywords": ["แม่เหล็ก", "ประกบติด", "กันสายพัน"], "punch_zoom": 1.15},
            {"id": 9, "start": 78.5, "end": 82.0, "action_type": "closeup", "angle_phase": "macro_closeup", "description": "ช็อตเด็ดมาโคร โชว์โลโก้ JBL สกรีนคมชัดกลางเฟรม", "keywords": ["โลโก้ JBL", "โลโก้", "สกรีนชัดเจน", "hero"], "punch_zoom": 1.25},
            {"id": 10, "start": 82.0, "end": 93.3, "action_type": "cta_showcase", "angle_phase": "front", "description": "แสดงภาพรวมหูฟัง JBL ในมือส่งท้าย ปิดการรีวิว", "keywords": ["ภาพรวม", "สั่งซื้อ", "ตะกร้า"], "punch_zoom": 1.25},
        ],
    }

    cues = [
        {"start": 0.0, "end": 5.4, "text": "ทุกคนครับ ใครเจอปัญหาหูฟังไร้สายแบตหมดขัดจังหวะ ฟังทางนี้ครับ"},
        {"start": 5.4, "end": 10.6, "text": "พอหันมาใช้หูฟังแบบมีสายทั่วไป เสียงก็แบนราบ ไร้มิติ ไม่สะใจใช่ไหมครับ"},
        {"start": 10.6, "end": 16.0, "text": "ผมบอกเลยว่าชีวิตดีขึ้นแน่นอน ด้วยหูฟังยูเอสบีซี รุ่นใหม่ JBL Tune 310C ครับ"},
        {"start": 16.0, "end": 21.8, "text": "เบสแน่นทรงพลัง คมชัดระดับ Hi-Res แถมสายแบนทนทาน ไม่พันกันครับ"},
        {"start": 21.8, "end": 27.8, "text": "ไม่ต้องกังวลเรื่องชาร์จแบต กดสั่งราคาพิเศษในตะกร้าซ้ายล่าง ตอนนี้เลยครับ"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(catalog, cues, raw_duration=93.3)
    assert len(matched) == 5

    # Shot 1 is Hero Macro Logo (78.5s)
    assert matched[0]["scene_start"] == 78.5

    # Shot 2 contrasts to front/hands_on (0.0s)
    assert matched[1]["scene_start"] == 0.0

    # Verify no consecutive identical angles
    for i in range(len(matched) - 1):
        r1 = matched[i]["visual_reason"]
        r2 = matched[i + 1]["visual_reason"]
        assert not ("(macro_closeup)" in r1 and "(macro_closeup)" in r2), f"Jump cut detected at shots {i} and {i+1}"
