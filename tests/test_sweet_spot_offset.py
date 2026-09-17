# -*- coding: utf-8 -*-
"""
Unit tests for Scene Sweet-Spot Offset and Continuous Progression (Phase 2).
Verifies:
1. Scenes with excess duration skip initial dead air / camera-shake / setup frames (0.5s - 1.2s).
2. Tightly cut scenes (excess < 1.0s) are not clipped.
3. Reusing a long scene advances the in-point progressively to display fresh visual slices.
4. Timestamp bounds strictly respect scene end and total raw video duration.
5. Smart fallback offset for opening shot (g_idx == 0) starts at a clean sweet spot (>= 0.8s).
6. Parameter `apply_sweet_spot=False` maintains exact scene_start compatibility when requested.
"""
import pytest
from scripts import gemini_vision_matcher as gvm
from scripts.stages.shot_matching_stage import ShotMatchingStage


def test_sweet_spot_offset_skips_start_dead_air():
    catalog = {
        "is_spin_footage": False,
        "summary": "รีวิวหูฟัง",
        "scenes": [
            {
                "id": 1,
                "start": 10.0,
                "end": 20.0,
                "action_type": "closeup",
                "angle_phase": "macro_closeup",
                "description": "โชว์โลโก้หูฟังคมชัดระยะประชิด",
                "keywords": ["โลโก้", "หูฟัง", "คมชัด"],
                "punch_zoom": 1.20,
            },
            {
                "id": 2,
                "start": 25.0,
                "end": 35.0,
                "action_type": "hands_on",
                "angle_phase": "45deg",
                "description": "มือหยิบหูฟังเสียบเข้าหู",
                "keywords": ["หยิบ", "ใส่", "เสียบ"],
                "punch_zoom": 1.15,
            },
        ]
    }

    cues = [
        {"start": 0.0, "end": 2.5, "text": "หูฟังตัวนี้โลโก้คมชัดมากครับ"},
        {"start": 2.5, "end": 5.5, "text": "หยิบใส่หูสบาย ไม่เจ็บหูเลย"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(
        catalog, cues, raw_duration=50.0, apply_sweet_spot=True
    )

    assert len(matched) == 2

    # Shot 1: Scene 1 (closeup, 10.0s - 20.0s, excess 7.5s)
    # Must skip the first ~1.0s setup frame and start in the sweet spot
    assert matched[0]["scene_id"] == 1
    assert matched[0]["scene_start"] == 10.0
    assert 10.6 <= matched[0]["start_time"] <= 11.5
    assert matched[0]["start_time"] > matched[0]["scene_start"]

    # Shot 2: Scene 2 (hands_on, 25.0s - 35.0s, excess 7.0s)
    assert matched[1]["scene_id"] == 2
    assert matched[1]["scene_start"] == 25.0
    assert 25.6 <= matched[1]["start_time"] <= 26.5
    assert matched[1]["start_time"] > matched[1]["scene_start"]


def test_tight_scenes_are_not_clipped():
    catalog = {
        "is_spin_footage": False,
        "summary": "ช็อตสั้นพอดีคำ",
        "scenes": [
            {
                "id": 1,
                "start": 5.0,
                "end": 7.5,
                "action_type": "closeup",
                "angle_phase": "front",
                "description": "ช็อตสั้น 2.5s พอดีกับบท",
                "keywords": ["สั้น", "ช็อต"],
                "punch_zoom": 1.10,
            }
        ]
    }

    cues = [
        {"start": 0.0, "end": 2.2, "text": "ช็อตสั้นพอดีบท"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(
        catalog, cues, raw_duration=20.0, apply_sweet_spot=True
    )

    # Excess is only 0.3s (< 1.0s), so sweet_offset must be 0.0
    assert matched[0]["scene_id"] == 1
    assert matched[0]["start_time"] == 5.0
    assert matched[0]["start_time"] == matched[0]["scene_start"]


def test_progressive_offset_on_scene_reuse():
    # Long turntable spin scene (15 seconds long)
    catalog = {
        "is_spin_footage": True,
        "summary": "แท่นหมุน 360 องศาขนาดยาว",
        "scenes": [
            {
                "id": 1,
                "start": 10.0,
                "end": 25.0,
                "action_type": "turntable_spin",
                "angle_phase": "front",
                "description": "หมุนรอบตัวยาวต่อเนื่อง 15 วินาที",
                "keywords": ["หมุน", "รอบตัว"],
                "punch_zoom": 1.15,
            }
        ]
    }

    cues = [
        {"start": 0.0, "end": 2.5, "text": "หมุนโชว์รอบแรกครับ"},
        {"start": 2.5, "end": 5.0, "text": "หมุนโชว์รอบสองครับ"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(
        catalog, cues, raw_duration=40.0, apply_sweet_spot=True
    )

    assert len(matched) == 2
    # First use: starts at sweet spot
    first_start = matched[0]["start_time"]
    assert first_start > 10.0

    # Second use: must advance forward into the scene (progressive offset)
    second_start = matched[1]["start_time"]
    assert second_start >= first_start + 1.8
    assert second_start + 2.5 <= 25.0


def test_apply_sweet_spot_false_flag():
    catalog = {
        "is_spin_footage": False,
        "summary": "ทดสอบ flag ปิด sweet spot",
        "scenes": [
            {
                "id": 1,
                "start": 15.0,
                "end": 25.0,
                "action_type": "closeup",
                "angle_phase": "macro_closeup",
                "description": "โชว์สินค้า",
                "keywords": ["สินค้า"],
                "punch_zoom": 1.15,
            }
        ]
    }

    cues = [
        {"start": 0.0, "end": 2.5, "text": "สินค้าตัวนี้ดีมาก"},
    ]

    matched = gvm.GeminiVisionMatcher.match_script_with_catalog(
        catalog, cues, raw_duration=40.0, apply_sweet_spot=False
    )

    assert matched[0]["start_time"] == 15.0
    assert matched[0]["start_time"] == matched[0]["scene_start"]


def test_smart_fallback_offset_sweet_spot():
    # Opening shot (g_idx == 0) on long footage should start around 0.8s - 1.5s
    offset = ShotMatchingStage._compute_smart_fallback_offset(
        g_idx=0,
        total_groups=5,
        raw_duration=60.0,
        c_dur=3.0,
    )
    assert 0.8 <= offset <= 1.5
