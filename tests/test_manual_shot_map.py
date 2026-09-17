from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

import scripts.auth as auth_module
from scripts.product_store import ProductStore
from scripts.pipeline_context import PipelineContext
from scripts.stages.shot_matching_stage import ShotMatchingStage
from scripts.api_server import app

client = TestClient(app)


from contextlib import contextmanager

def test_product_store_update_manual_shot_map(tmp_path):
    product = {
        "id": "prod_test_msm",
        "name": "Test Product",
        "angles": [
            {
                "angle_id": "ang_1",
                "angle_name": "Angle 1",
                "manual_shot_map": [],
            }
        ]
    }
    products_list = [product]
    @contextmanager
    def mock_mutate():
        yield products_list

    with patch.object(ProductStore, "_mutate", mock_mutate):
        sample_map = [
            {"beat_index": 0, "video_path": "01_Raw/test/vid1.mp4", "trim_start": 1.0, "trim_end": 4.0},
            {"beat_index": 2, "video_path": "01_Raw/test/vid2.mp4", "trim_start": 5.0, "trim_end": 8.5},
        ]
        res = ProductStore.update_angle_manual_shot_map("prod_test_msm", "ang_1", sample_map)
        ang = res["angles"][0]
        assert len(ang["manual_shot_map"]) == 2
        assert ang["manual_shot_map"][0]["beat_index"] == 0
        assert ang["manual_shot_map"][0]["trim_start"] == 1.0


def test_api_manual_shot_map_endpoints():
    product = {
        "id": "prod_test_api",
        "name": "Test Product",
        "angles": [
            {
                "angle_id": "ang_1",
                "angle_name": "Angle 1",
                "manual_shot_map": [
                    {"beat_index": 1, "video_path": "01_Raw/sample.mp4", "trim_start": 2.0, "trim_end": 5.0}
                ],
            }
        ]
    }
    with patch.object(ProductStore, "get", return_value=product), \
         patch.object(ProductStore, "update_angle_manual_shot_map") as mock_update, \
         patch("scripts.shot_lists_store.ShotListsStore.get", return_value={"beat_cues": [{"start": 0, "end": 3}], "total_duration": 3.0}):
        # Test GET
        res_get = client.get("/api/products/prod_test_api/angles/ang_1/manual-shot-map")
        assert res_get.status_code == 200
        data = res_get.json()
        assert data["has_shot_list"] is True
        assert len(data["manual_shot_map"]) == 1
        assert data["manual_shot_map"][0]["beat_index"] == 1

        # Test PATCH
        payload = {
            "shot_map": [
                {"beat_index": 0, "video_path": "01_Raw/sample.mp4", "trim_start": 0.5, "trim_end": 3.0}
            ]
        }
        res_patch = client.patch("/api/products/prod_test_api/angles/ang_1/manual-shot-map", json=payload)
        assert res_patch.status_code == 200
        assert res_patch.json()["success"] is True
        assert mock_update.called


def test_shot_matching_stage_manual_override():
    stage = ShotMatchingStage()
    ctx = PipelineContext(
        project_name="test_proj",
        product_name="Test Product",
        raw_video_path="01_Raw/test.mp4",
        manual_shot_map=[
            {"beat_index": 1, "video_path": "01_Raw/custom_clip.mp4", "trim_start": 10.0, "trim_end": 14.5}
        ]
    )
    # Pre-populate clip_list with 3 clips
    ctx.clip_list = [
        {"shot_index": 0, "source_path": "01_Raw/orig0.mp4", "trim_start": 0.0, "trim_end": 3.0},
        {"shot_index": 1, "source_path": "01_Raw/orig1.mp4", "trim_start": 3.0, "trim_end": 7.0},
        {"shot_index": 2, "source_path": "01_Raw/orig2.mp4", "trim_start": 7.0, "trim_end": 10.0},
    ]

    stage.run(ctx)
        
    assert ctx.actual_clip_list[1]["source_path"] == "01_Raw/custom_clip.mp4"
    assert ctx.actual_clip_list[1]["trim_start"] == 10.0
    assert ctx.actual_clip_list[1]["trim_end"] == 14.5
    assert ctx.actual_clip_list[1].get("manual_pinned") is True
    # shot_index 0 and 2 should remain unchanged
    assert ctx.actual_clip_list[0]["source_path"] == "01_Raw/orig0.mp4"
    assert ctx.actual_clip_list[2]["source_path"] == "01_Raw/orig2.mp4"


def test_manual_storyboard_clip_list_generation_strictly_matches_beats():
    """Test that _build_manual_storyboard_clip_list produces exactly len(beat_cues) clips
    and computes playback speeds accurately without any trailing overflow clips.
    """
    ctx = PipelineContext(
        project_name="test_storyboard",
        product_name="Test Product",
        raw_video_path="01_Raw/test.mp4",
        total_duration=20.0,
        beat_cues=[
            {"start": 0.0, "end": 4.0, "text": "Beat 0"},
            {"start": 4.0, "end": 9.0, "text": "Beat 1"},
            {"start": 9.0, "end": 15.0, "text": "Beat 2"},
            {"start": 15.0, "end": 20.0, "text": "Beat 3"},
        ],
        manual_shot_map=[
            {"beat_index": 0, "video_path": "01_Raw/clip_a.mp4", "trim_start": 0.0, "trim_end": 4.0},
            {"beat_index": 2, "video_path": "01_Raw/clip_b.mp4", "trim_start": 10.0, "trim_end": 16.0},
        ],
    )
    clips = ShotMatchingStage._build_manual_storyboard_clip_list(ctx, "01_Raw/test.mp4", 60.0)
    assert len(clips) == 4, f"Expected exactly 4 clips matching 4 beats, got {len(clips)}"

    # Beat 0: target_dur=4.0, trim_span=4.0 -> speed=1.0
    assert clips[0]["manual_pinned"] is True
    assert clips[0]["duration"] == 4.0
    assert clips[0]["speed"] == 1.0
    assert clips[0]["source_path"] == "01_Raw/clip_a.mp4"

    # Beat 1: unpinned fallback -> target_dur=5.0
    assert clips[1]["manual_pinned"] is False
    assert clips[1]["duration"] == 5.0
    assert clips[1]["source_path"] == "01_Raw/test.mp4"

    # Beat 2: target_dur=6.0, trim_span=6.0 -> speed=1.0
    assert clips[2]["manual_pinned"] is True
    assert clips[2]["duration"] == 6.0
    assert clips[2]["speed"] == 1.0

    # Total duration must equal sum of beat durations exactly
    total_clip_dur = sum(c["duration"] for c in clips)
    assert total_clip_dur == 20.0


def test_manual_storyboard_truncates_overflow_clips():
    """Simulates the exact user bug:
    A 5-beat script generated 9 clips from micro-cues, but user pinned 5 storyboard shots.
    The final clip list must be truncated to 5 clips, eliminating the 4 trailing overflow clips.
    """
    stage = ShotMatchingStage()
    ctx = PipelineContext(
        project_name="test_overflow_bug",
        product_name="Test Product",
        raw_video_path="01_Raw/test.mp4",
        total_duration=25.0,
        beat_cues=[
            {"start": 0.0, "end": 5.0, "text": "Beat 0"},
            {"start": 5.0, "end": 10.0, "text": "Beat 1"},
            {"start": 10.0, "end": 15.0, "text": "Beat 2"},
            {"start": 15.0, "end": 20.0, "text": "Beat 3"},
            {"start": 20.0, "end": 25.0, "text": "Beat 4"},
        ],
        manual_shot_map=[
            {"beat_index": 0, "video_path": "01_Raw/v1.mp4", "trim_start": 0.0, "trim_end": 5.0},
            {"beat_index": 1, "video_path": "01_Raw/v2.mp4", "trim_start": 0.0, "trim_end": 5.0},
            {"beat_index": 2, "video_path": "01_Raw/v3.mp4", "trim_start": 0.0, "trim_end": 5.0},
            {"beat_index": 3, "video_path": "01_Raw/v4.mp4", "trim_start": 0.0, "trim_end": 5.0},
            {"beat_index": 4, "video_path": "01_Raw/v5.mp4", "trim_start": 0.0, "trim_end": 5.0},
        ],
    )
    # Simulate 9 clips previously generated by micro_cues cutter (5 voiceover clips + 4 trailing overflow clips)
    ctx.clip_list = [
        {"shot_index": 0, "source_path": "01_Raw/v.mp4", "trim_start": 0.0, "trim_end": 3.0, "duration": 3.0},
        {"shot_index": 1, "source_path": "01_Raw/v.mp4", "trim_start": 3.0, "trim_end": 6.0, "duration": 3.0},
        {"shot_index": 2, "source_path": "01_Raw/v.mp4", "trim_start": 6.0, "trim_end": 9.0, "duration": 3.0},
        {"shot_index": 3, "source_path": "01_Raw/v.mp4", "trim_start": 9.0, "trim_end": 12.0, "duration": 3.0},
        {"shot_index": 4, "source_path": "01_Raw/v.mp4", "trim_start": 12.0, "trim_end": 15.0, "duration": 3.0},
        # Trailing 4 overflow clips that caused the 11s bug:
        {"shot_index": 5, "source_path": "01_Raw/v.mp4", "trim_start": 15.0, "trim_end": 18.0, "duration": 3.0},
        {"shot_index": 6, "source_path": "01_Raw/v.mp4", "trim_start": 18.0, "trim_end": 21.0, "duration": 3.0},
        {"shot_index": 7, "source_path": "01_Raw/v.mp4", "trim_start": 21.0, "trim_end": 24.0, "duration": 3.0},
        {"shot_index": 8, "source_path": "01_Raw/v.mp4", "trim_start": 24.0, "trim_end": 27.0, "duration": 3.0},
    ]

    stage.run(ctx)

    # Must be truncated to strictly 5 clips!
    assert len(ctx.actual_clip_list) == 5, f"Expected 5 clips, got {len(ctx.actual_clip_list)}"
    total_dur = sum(c["duration"] for c in ctx.actual_clip_list)
    assert total_dur == 25.0, f"Expected total duration 25.0s, got {total_dur}"

