"""
Tests for ShotListsStore, invalidation on script change, and category-aware shot list directions.
"""

import pytest
from unittest.mock import patch
from scripts.shot_lists_store import ShotListsStore
from scripts.shot_list_builder import (
    assign_beat_role,
    camera_direction_for_beat,
    build_shot_list,
)
from scripts.product_store import ProductStore


def test_assign_beat_role():
    assert assign_beat_role(0, 1) == "hook"
    assert assign_beat_role(0, 3) == "hook"
    assert assign_beat_role(1, 3) == "feature"
    assert assign_beat_role(2, 3) == "cta"


def test_camera_direction_category_aware():
    # Desk Tech Hook
    tech_hook = camera_direction_for_beat("hook", 0, "เมาส์ไร้สาย", "", "Logitech Lift", category="IT Desk Accessories")
    assert "45°" in tech_hook or "Top-Down" in tech_hook or "โต๊ะทำงาน" in tech_hook

    # Cable Hook
    cable_hook = camera_direction_for_beat("hook", 0, "สายชาร์จ", "", "Essager Cable", category="Charger and Cables")
    assert "Close-up" in cable_hook or "สาย" in cable_hook

    # Beauty Hook
    beauty_hook = camera_direction_for_beat("hook", 0, "ลิปบาล์ม", "", "Glasting Lip", category="Beauty Skincare")
    assert "Medium Close-up" in beauty_hook or "ใบหน้า" in beauty_hook

    # Generic Hook
    generic_hook = camera_direction_for_beat("hook", 0, "สินค้า", "", "Generic Product", category="Other")
    assert "Medium shot" in generic_hook


def test_build_shot_list():
    cues = [
        {"start": 0.0, "end": 2.5, "text": "เบื่อไหมกับเมาส์เดิมๆ", "on_screen": ""},
        {"start": 2.5, "end": 6.0, "text": "ตัวนี้มุม 57 องศา สบายมือสุดๆ", "on_screen": "57°"},
        {"start": 6.0, "end": 8.0, "text": "กดสั่งได้ในตะกร้าเลย", "on_screen": ""},
    ]
    shots = build_shot_list(cues, "Logitech Lift", category="IT mouse")
    assert len(shots) == 3
    assert shots[0]["role"] == "hook"
    assert shots[1]["role"] == "feature"
    assert shots[2]["role"] == "cta"
    assert shots[2]["is_separate_clip"] is True
    assert shots[0]["is_separate_clip"] is False


def test_shot_lists_store_crud_and_stale():
    test_record = {
        "id": "prod_123:angle_abc",
        "product_id": "prod_123",
        "angle_id": "angle_abc",
        "product_name": "Test Product",
        "shot_list": [],
        "custom_script": "Line 1\nLine 2",
        "total_duration": 5.0,
    }

    with patch.object(ShotListsStore, "get") as mock_get:
        mock_get.return_value = test_record

        # Not stale when script matches
        assert ShotListsStore.is_stale("prod_123", "angle_abc", "Line 1\nLine 2") is False

        # Stale when script differs
        assert ShotListsStore.is_stale("prod_123", "angle_abc", "Line 1\nLine 2 changed") is True
        assert ShotListsStore.is_stale("prod_123", "angle_abc", "Line 1") is True

        # When no record exists, is_stale returns False
        mock_get.return_value = None
        assert ShotListsStore.is_stale("prod_123", "angle_abc", "Line 1") is False

    # Test delete via mutate mock
    with patch("scripts.shot_lists_store._TABLE.mutate") as mock_mutate:
        fake_records = [
            {"id": "prod_123:angle_abc", "product_id": "prod_123", "angle_id": "angle_abc"},
            {"id": "prod_456:angle_def", "product_id": "prod_456", "angle_id": "angle_def"},
        ]
        class MockMutateContext:
            def __enter__(self):
                return fake_records
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_mutate.return_value = MockMutateContext()
        deleted = ShotListsStore.delete("prod_123", "angle_abc")
        assert deleted is True
        assert len(fake_records) == 1
        assert fake_records[0]["id"] == "prod_456:angle_def"


def test_semantic_camera_direction_for_lift():
    prod = "Logitech Lift"
    # Beat 1: Hook
    d1 = camera_direction_for_beat("hook", 0, "จ่ายแค่วันละไม่ถึง 3 บาท แต่ได้สุขภาพข้อมือ", "", prod)
    assert "45°" in d1 or "โต๊ะทำงาน" in d1

    # Beat 2: Ergonomic posture / angle
    d2 = camera_direction_for_beat("feature", 1, "ลงทุนครั้งเดียวกับ โลจิเทค Lift เมาส์สุขภาพมาตรฐานโลก", "", prod)
    assert "57°" in d2 or "ฝ่ามือ" in d2 or "ข้อมือ" in d2 or "ดีไซน์" in d2

    # Beat 3: Value / Cost
    d3 = camera_direction_for_beat("feature", 2, "เฉลี่ยแล้วตกวันละ สตางค์เท่านั้น ถูกกว่าซื้อ ยาแก้ปวดแก้เมื่อย", "", prod)
    assert "คุ้มค่า" in d3 or "360°" in d3 or "ยก" in d3 or "ข้อมือ" in d3

    # Beat 4: Clicking / SmartWheel / Silence
    d4 = camera_direction_for_beat("feature", 3, "แถมทำงานลื่นไหล ปุ่มกดนุ่มเงียบกริบ ถนอมมือของคุณ", "", prod)
    assert "คลิก" in d4 or "SmartWheel" in d4 or "เงียบกริบ" in d4

    # Beat 5: CTA
    d5 = camera_direction_for_beat("cta", 4, "กดสั่งซื้อในตะกร้าด้านล่างได้เลย", "", prod)
    assert "ตะกร้า" in d5
