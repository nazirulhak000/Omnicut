import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from scripts.api_server import app
from scripts.product_store import ProductStore
from scripts.api_shot_lists import (
    smart_map_storyboard_to_beats,
    sync_manual_shot_map,
    get_universal_filming_recipe,
)

client = TestClient(app)


def test_smart_map_storyboard_equal_beats():
    source_map = [
        {"beat_index": 0, "video_path": "01_Raw/hook.mp4", "trim_start": 0.0, "trim_end": 4.0},
        {"beat_index": 1, "video_path": "01_Raw/feature1.mp4", "trim_start": 5.0, "trim_end": 9.0},
        {"beat_index": 2, "video_path": "01_Raw/feature2.mp4", "trim_start": 10.0, "trim_end": 14.0},
        {"beat_index": 3, "video_path": "01_Raw/cta.mp4", "trim_start": 15.0, "trim_end": 19.0},
    ]
    adapted = smart_map_storyboard_to_beats(source_map, 4)
    assert len(adapted) == 4
    for i in range(4):
        assert adapted[i]["beat_index"] == i
    assert adapted[0]["video_path"] == "01_Raw/hook.mp4"
    assert adapted[3]["video_path"] == "01_Raw/cta.mp4"


def test_smart_map_storyboard_extended_beats_auto_loop():
    # 5 source shots mapped into 8 target beats (30s -> 60s scenario)
    source_map = [
        {"beat_index": 0, "video_path": "01_Raw/hook.mp4", "trim_start": 0.0, "trim_end": 4.0},
        {"beat_index": 1, "video_path": "01_Raw/showcase.mp4", "trim_start": 10.0, "trim_end": 15.0},
        {"beat_index": 2, "video_path": "01_Raw/detail.mp4", "trim_start": 20.0, "trim_end": 25.0},
        {"beat_index": 3, "video_path": "01_Raw/action.mp4", "trim_start": 30.0, "trim_end": 35.0},
        {"beat_index": 4, "video_path": "01_Raw/cta.mp4", "trim_start": 40.0, "trim_end": 44.0},
    ]

    adapted = smart_map_storyboard_to_beats(source_map, 8)
    assert len(adapted) == 8

    # Beat 0 must be Hook
    assert adapted[0]["beat_index"] == 0
    assert adapted[0]["video_path"] == "01_Raw/hook.mp4"

    # Beat 7 must be CTA
    assert adapted[7]["beat_index"] == 7
    assert adapted[7]["video_path"] == "01_Raw/cta.mp4"

    # Middle beats 1 to 6 should loop through showcase, detail, action
    # Cycle 1: beats 1, 2, 3
    assert adapted[1]["video_path"] == "01_Raw/showcase.mp4"
    assert adapted[2]["video_path"] == "01_Raw/detail.mp4"
    assert adapted[3]["video_path"] == "01_Raw/action.mp4"

    # Cycle 2: beats 4, 5, 6 (shifted offset to avoid repeating the exact frame)
    assert adapted[4]["video_path"] == "01_Raw/showcase.mp4"
    assert adapted[4].get("is_auto_extended") is True
    assert adapted[4]["trim_start"] > source_map[1]["trim_start"]  # offset applied!


def test_sync_manual_shot_map_api():
    product = {
        "id": "prod_sync_test",
        "name": "IWACHI i6 Wireless Mouse",
        "category": "เมาส์ไร้สาย",
        "angles": [
            {
                "angle_id": "ang_source",
                "angle_name": "แกะกล่องว้าว",
                "script_lines": ["Line 1", "Line 2", "Line 3"],
                "manual_shot_map": [
                    {"beat_index": 0, "video_path": "01_Raw/clip1.mp4", "trim_start": 0.0, "trim_end": 3.0},
                    {"beat_index": 1, "video_path": "01_Raw/clip2.mp4", "trim_start": 3.0, "trim_end": 6.0},
                    {"beat_index": 2, "video_path": "01_Raw/clip3.mp4", "trim_start": 6.0, "trim_end": 9.0},
                ],
            },
            {
                "angle_id": "ang_target_empty",
                "angle_name": "รีวิวสเปก",
                "script_lines": ["Line A", "Line B", "Line C"],
                "manual_shot_map": [],
            },
            {
                "angle_id": "ang_target_existing",
                "angle_name": "ปัญหาเดิม",
                "script_lines": ["Line X", "Line Y", "Line Z"],
                "manual_shot_map": [
                    {"beat_index": 0, "video_path": "01_Raw/custom.mp4", "trim_start": 1.0, "trim_end": 4.0}
                ],
            },
        ],
    }

    with patch.object(ProductStore, "get", return_value=product), \
         patch.object(ProductStore, "batch_update_manual_shot_maps") as mock_batch_update:

        # Test sync with overwrite_policy="skip_existing"
        payload = {
            "target_angle_ids": ["ang_target_empty", "ang_target_existing"],
            "overwrite_policy": "skip_existing",
        }
        res = client.post("/api/products/prod_sync_test/angles/ang_source/sync-manual-shot-map", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        # Only ang_target_empty should be synced (ang_target_existing skipped)
        assert data["synced_count"] == 1
        assert data["synced_angles"][0]["angle_id"] == "ang_target_empty"
        assert mock_batch_update.called

        # Test sync with overwrite_policy="overwrite_all"
        payload_overwrite = {
            "target_angle_ids": ["ang_target_empty", "ang_target_existing"],
            "overwrite_policy": "overwrite_all",
        }
        res_ov = client.post("/api/products/prod_sync_test/angles/ang_source/sync-manual-shot-map", json=payload_overwrite)
        assert res_ov.status_code == 200
        data_ov = res_ov.json()
        assert data_ov["synced_count"] == 2


def test_get_universal_filming_recipe():
    product = {
        "id": "prod_recipe_test",
        "name": "IWACHI i6 Wireless Ergonomic Mouse",
        "category": "เมาส์ไร้สาย สรีรศาสตร์",
    }
    with patch.object(ProductStore, "get", return_value=product):
        res = client.get("/api/products/prod_recipe_test/filming-recipe")
        assert res.status_code == 200
        data = res.json()
        assert data["total_shots"] == 5
        assert "เมาส์" in data["category_badge"]
        shots = data["shots"]
        assert shots[0]["role"] == "hook"
        assert shots[1]["role"] == "showcase"
        assert shots[2]["role"] == "macro"
        assert shots[3]["role"] == "action"
        assert shots[4]["role"] == "cta"
