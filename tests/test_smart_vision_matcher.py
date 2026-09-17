"""
Unit tests for the Scene Catalog indexing, semantic matching, and smart fallback offset
architecture in scripts/gemini_vision_matcher.py and scripts/stages/shot_matching_stage.py.
"""
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts import gemini_vision_matcher as gvm
from scripts.stages.shot_matching_stage import ShotMatchingStage


@pytest.fixture(autouse=True)
def _isolate_cache_file(monkeypatch, tmp_path):
    monkeypatch.setattr(gvm, "VISION_CACHE_FILE", tmp_path / ".vision_cache.json")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")


# ---------------------------------------------------------------------------
# 1. Catalog Cache Save and Load
# ---------------------------------------------------------------------------

def test_save_and_get_cached_catalog(tmp_path):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"sample video bytes for testing catalog")
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw)

    sample_catalog = {
        "raw_file": str(raw),
        "duration": 45.0,
        "is_spin_footage": True,
        "summary": "คลิปหมุนโชว์สายชาร์จ 360 องศา",
        "scenes": [
            {
                "id": 1,
                "start": 0.0,
                "end": 8.0,
                "action_type": "overview",
                "angle_phase": "front",
                "description": "สินค้าวางมุมตรง",
                "keywords": ["ตัวเครื่อง", "ภาพรวม"],
                "punch_zoom": 1.10,
            }
        ]
    }

    # Before saving
    assert gvm.GeminiVisionMatcher.get_cached_catalog(str(raw)) is None

    # Save
    gvm.GeminiVisionMatcher.save_cached_catalog(file_hash, sample_catalog)

    # After saving
    loaded = gvm.GeminiVisionMatcher.get_cached_catalog(str(raw))
    assert loaded is not None
    assert loaded["is_spin_footage"] is True
    assert len(loaded["scenes"]) == 1
    assert loaded["scenes"][0]["action_type"] == "overview"


# ---------------------------------------------------------------------------
# 2. Semantic and Keyword Matching with Scene Catalog
# ---------------------------------------------------------------------------

def test_match_script_with_catalog_keyword_relevance():
    sample_catalog = {
        "is_spin_footage": False,
        "summary": "คลิปรีวิวสายชาร์จและแกะกล่อง",
        "scenes": [
            {
                "id": 1,
                "start": 0.0,
                "end": 10.0,
                "action_type": "unboxing",
                "angle_phase": "top",
                "description": "แกะกล่องแพ็กเกจ มีสายและของแถมในกล่อง",
                "keywords": ["กล่อง", "แพ็กเกจ", "แกะ", "ของแถม"],
                "punch_zoom": 1.10,
            },
            {
                "id": 2,
                "start": 10.0,
                "end": 20.0,
                "action_type": "port_connection",
                "angle_phase": "closeup",
                "description": "เสียบชาร์จเข้าพอร์ต Type-C ไฟติด",
                "keywords": ["ชาร์จ", "เสียบ", "พอร์ต", "ไฟ"],
                "punch_zoom": 1.25,
            },
            {
                "id": 3,
                "start": 20.0,
                "end": 30.0,
                "action_type": "turntable_spin",
                "angle_phase": "45deg",
                "description": "หมุนข้อต่อโชว์ 540 องศา เล่นเกมไม่เกะกะ",
                "keywords": ["หมุน", "ข้อต่อ", "540", "องศา"],
                "punch_zoom": 1.15,
            },
            {
                "id": 4,
                "start": 30.0,
                "end": 40.0,
                "action_type": "cta_showcase",
                "angle_phase": "front",
                "description": "โชว์สินค้าราคาพิเศษ กดในตะกร้า",
                "keywords": ["ราคา", "โปร", "ตะกร้า", "ลด"],
                "punch_zoom": 1.20,
            },
        ]
    }

    cues = [
        {"start": 0.0, "end": 3.0, "text": "เปิดกล่องมามีของแถมครบชุดครับ!"},
        {"start": 3.0, "end": 6.5, "text": "พอร์ตชาร์จ Type-C เสียบแล้วไฟติดทันทีครับ"},
        {"start": 6.5, "end": 10.0, "text": "ข้อต่อหมุนได้ 540 องศา เล่นเกมสบายมากครับ"},
        {"start": 10.0, "end": 13.5, "text": "ราคาพิเศษวันนี้ รีบกดในตะกร้าเลยครับ!"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(sample_catalog, cues, raw_duration=40.0)

    assert len(matched) == 4
    # Cue 1 (กล่อง) matches Scene 1 (unboxing)
    assert matched[0]["scene_start"] == 0.0
    assert "unboxing" in matched[0]["visual_reason"]

    # Cue 2 (พอร์ต/เสียบ/ชาร์จ) matches Scene 2 (port_connection)
    assert matched[1]["scene_start"] == 10.0
    assert "port_connection" in matched[1]["visual_reason"]

    # Cue 3 (หมุน/540) matches Scene 3 (turntable_spin)
    assert matched[2]["scene_start"] == 20.0
    assert "turntable_spin" in matched[2]["visual_reason"]

    # Cue 4 (ราคา/ตะกร้า) matches Scene 4 (cta_showcase)
    assert matched[3]["scene_start"] == 30.0
    assert "cta_showcase" in matched[3]["visual_reason"]


def test_match_script_with_catalog_turntable_variety_and_anti_duplicate():
    # Footage is 100% turntable spin, 5 scenes
    spin_catalog = {
        "is_spin_footage": True,
        "summary": "คลิปหมุนโชว์สินค้าแบบ 360 Turntable ตลอดคลิป",
        "scenes": [
            {"id": 1, "start": 0.0, "end": 8.0, "action_type": "turntable_spin", "angle_phase": "front", "description": "มุมตรง", "keywords": [], "punch_zoom": 1.10},
            {"id": 2, "start": 8.0, "end": 16.0, "action_type": "turntable_spin", "angle_phase": "45deg", "description": "มุมเฉียง 45 องศา", "keywords": [], "punch_zoom": 1.15},
            {"id": 3, "start": 16.0, "end": 24.0, "action_type": "turntable_spin", "angle_phase": "side", "description": "มุมข้าง", "keywords": [], "punch_zoom": 1.12},
            {"id": 4, "start": 24.0, "end": 32.0, "action_type": "turntable_spin", "angle_phase": "macro_closeup", "description": "มุมซูมรายละเอียด", "keywords": [], "punch_zoom": 1.25},
            {"id": 5, "start": 32.0, "end": 40.0, "action_type": "turntable_spin", "angle_phase": "back", "description": "มุมหลัง", "keywords": [], "punch_zoom": 1.10},
        ]
    }

    cues = [
        {"start": 0.0, "end": 2.5, "text": "ทุกคนต้องดูสิ่งนี้เลยครับ"},
        {"start": 2.5, "end": 5.0, "text": "ดีไซน์สวยเรียบหรูดูแพงครับ"},
        {"start": 5.0, "end": 7.5, "text": "วัสดุพรีเมียมจับถนัดมือครับ"},
        {"start": 7.5, "end": 10.0, "text": "งานประกอบละเอียดมากครับ"},
        {"start": 10.0, "end": 12.5, "text": "จัดด่วนในตะกร้าได้เลยครับ"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(spin_catalog, cues, raw_duration=40.0)

    assert len(matched) == 5

    # Check that consecutive shots do not have identical start timestamps
    starts = [m["start_time"] for m in matched]
    for i in range(len(starts) - 1):
        assert starts[i] != starts[i + 1], f"Consecutive shots {i} and {i+1} must not have identical start time"

    # Check punch zoom levels vary
    zooms = [m["punch_zoom"] for m in matched]
    assert len(set(zooms)) >= 3, "Turntable variety must rotate punch zoom levels"


def test_match_script_to_video_uses_catalog_instantaneously_without_gemini_api(tmp_path, monkeypatch):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video bytes")
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw)

    catalog = {
        "raw_file": str(raw),
        "duration": 30.0,
        "is_spin_footage": False,
        "summary": "พรีวิวสินค้า",
        "scenes": [
            {"id": 1, "start": 0.0, "end": 10.0, "action_type": "overview", "angle_phase": "front", "description": "ด้านหน้า", "keywords": ["สินค้า"], "punch_zoom": 1.1}
        ]
    }
    gvm.GeminiVisionMatcher.save_cached_catalog(file_hash, catalog)

    cues = [{"start": 0.0, "end": 2.5, "text": "ดูสินค้านี้กันครับ"}]

    # Ensure if Gemini client is called, it fails the test
    monkeypatch.setattr("google.genai.Client", lambda *a, **k: pytest.fail("Must not call Gemini API when catalog is cached!"))

    matched = gvm.GeminiVisionMatcher.match_script_to_video(str(raw), cues, raw_duration=30.0)
    assert len(matched) == 1
    assert matched[0]["scene_start"] == 0.0


# ---------------------------------------------------------------------------
# 3. Smart Fallback Offset Distribution
# ---------------------------------------------------------------------------

def test_smart_fallback_offset_distribution():
    raw_duration = 60.0
    c_dur = 3.0
    total_groups = 6

    offsets = []
    for g_idx in range(total_groups):
        offset = ShotMatchingStage._compute_smart_fallback_offset(
            g_idx=g_idx,
            total_groups=total_groups,
            raw_duration=raw_duration,
            c_dur=c_dur,
            previous_offsets=offsets,
        )
        offsets.append(offset)

    assert len(offsets) == 6
    # Must span across the video, reaching past 30s instead of being stuck at early seconds
    assert max(offsets) > 35.0, f"Max offset should cover later footage, got {max(offsets)}"
    # All offsets must fit within raw duration
    for off in offsets:
        assert 0.0 <= off <= raw_duration - c_dur

    # No two consecutive offsets should be within 1.5s
    for i in range(len(offsets) - 1):
        assert abs(offsets[i] - offsets[i + 1]) >= 1.5, f"Offsets too close: {offsets[i]} and {offsets[i+1]}"


def test_anti_ping_pong_and_domain_diversity():
    catalog = {
        "is_spin_footage": False,
        "summary": "หูฟัง JBL",
        "scenes": [
            {"id": 1, "start": 0.0, "end": 7.0, "action_type": "hands_on", "angle_phase": "front", "description": "มือหยิบหูฟังสาย JBL โชว์ความยาวสาย", "keywords": ["หูฟัง", "สายหูฟัง"], "punch_zoom": 1.1},
            {"id": 2, "start": 7.0, "end": 15.0, "action_type": "closeup", "angle_phase": "macro_closeup", "description": "โชว์หูฟังทั้งสองข้างในฝ่ามือ โลโก้ JBL L R", "keywords": ["โลโก้ JBL", "หูฟังซ้ายขวา"], "punch_zoom": 1.15},
            {"id": 3, "start": 15.0, "end": 22.0, "action_type": "feature_demo", "angle_phase": "45deg", "description": "จุกยางซิลิโคนอินเอียร์สีส้ม", "keywords": ["จุกหูฟัง", "อินเอียร์"], "punch_zoom": 1.1},
            {"id": 6, "start": 37.0, "end": 45.0, "action_type": "port_connection", "angle_phase": "macro_closeup", "description": "โชว์หัวเชื่อมต่อแบบ USB Type-C สกรีนโลโก้ JBL", "keywords": ["Type-C", "USB-C", "หัวเสียบ"], "punch_zoom": 1.2},
            {"id": 8, "start": 56.0, "end": 67.0, "action_type": "feature_demo", "angle_phase": "front", "description": "สาธิตระบบแม่เหล็กที่หลังหูฟัง ประกบติดกันเพื่อป้องกันสายพันกัน", "keywords": ["แม่เหล็ก", "ประกบติด", "กันสายพัน"], "punch_zoom": 1.15},
            {"id": 10, "start": 82.0, "end": 93.3, "action_type": "cta_showcase", "angle_phase": "front", "description": "แสดงภาพรวมหูฟัง JBL ในมือส่งท้าย ปิดการรีวิว", "keywords": ["ภาพรวม", "สั่งซื้อ", "ตะกร้า"], "punch_zoom": 1.25},
        ]
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

    # Distinct scenes must be chosen (at least 4 distinct scenes across 5 shots, no ping-pong 1-6-1-6)
    chosen_starts = [m["start_time"] for m in matched]
    unique_starts = set(chosen_starts)
    assert len(unique_starts) >= 4, f"Expected high diversity, got only {len(unique_starts)} unique scenes: {chosen_starts}"

    # Cue 3 (ยูเอสบีซี) must pick Type-C port connection (start=37.0)
    assert matched[2]["scene_start"] == 37.0

    # Cue 4 (ไม่พันกัน / สายแบน) must pick magnet anti-tangle demo (start=56.0)
    assert matched[3]["scene_start"] == 56.0

    # Cue 5 (CTA / ตะกร้า) must pick CTA showcase (start=82.0)
    assert matched[4]["scene_start"] == 82.0


def test_hero_cover_shot_macro_priority():
    """Shot 1 / Beat 1 (hook & thumbnail cover) must prioritize crisp macro logo over loose palm shot."""
    catalog = {
        "is_spin_footage": False,
        "scenes": [
            {
                "id": 1,
                "start": 7.0,
                "end": 15.0,
                "action_type": "closeup",
                "angle_phase": "macro_closeup",
                "description": "โชว์หูฟังทั้งสองข้างในฝ่ามือ พลิกแสดงโลโก้",
                "keywords": ["หูฟัง", "ฝ่ามือ"],
                "punch_zoom": 1.15,
            },
            {
                "id": 2,
                "start": 78.5,
                "end": 82.0,
                "action_type": "closeup",
                "angle_phase": "macro_closeup",
                "description": "ช็อตเด็ดมาโคร โชว์โลโก้ JBL สกรีนคมชัดกลางเฟรม เหมาะทำหน้าปกและเปิดคลิป",
                "keywords": ["โลโก้ JBL", "โลโก้", "สกรีนชัดเจน", "hero"],
                "punch_zoom": 1.25,
            },
        ],
    }

    cues = [
        {"start": 0.0, "end": 2.5, "text": "ทุกคนครับ ใครเจอปัญหาหูฟังแบตหมด ฟังทางนี้ด่วนครับ"},
        {"start": 2.5, "end": 5.0, "text": "นี่คือหูฟังตัวเทพที่ทุกคนต้องมีครับ"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(catalog, cues, raw_duration=85.0)
    assert len(matched) >= 1
    # Shot 1 must pick Scene 2 (78.5s hero macro logo) instead of Scene 1 (palm shot)
    assert matched[0]["scene_start"] == 78.5
    assert "โลโก้" in matched[0]["visual_reason"]

