import pytest
from scripts.stages.shot_matching_stage import ShotMatchingStage
from scripts.pipeline_context import PipelineContext


def test_calculate_contiguous_beat_durations_absorbs_leadin_and_trailing_gaps():
    """Verify that calculate_contiguous_beat_durations:
    1. Starts beat 0 at 0.0s (absorbing lead-in silence before speech start 0.2s).
    2. Aligns each beat seamlessly with the next beat cut.
    3. Extends the last beat to match total_duration exactly.
    4. sum(durations) == total_duration down to the millisecond.
    """
    beat_cues = [
        {"id": 1, "start": 0.2, "end": 4.674},
        {"id": 2, "start": 4.674, "end": 9.104},
        {"id": 3, "start": 9.1, "end": 14.701},
        {"id": 4, "start": 14.701, "end": 20.667},
        {"id": 5, "start": 20.667, "end": 24.858},
    ]
    total_duration = 24.858333

    durations = ShotMatchingStage.calculate_contiguous_beat_durations(beat_cues, total_duration)
    assert len(durations) == 5
    # Beat 0 must absorb the 0.0-0.2s lead-in: duration = 4.674 - 0.0 = 4.674
    assert durations[0] == 4.674
    # Total sum must equal total_duration within 1ms
    assert abs(sum(durations) - total_duration) < 0.002


def test_calculate_contiguous_beat_durations_single_beat():
    beat_cues = [{"id": 1, "start": 0.5, "end": 4.0}]
    total_duration = 5.0
    durations = ShotMatchingStage.calculate_contiguous_beat_durations(beat_cues, total_duration)
    assert len(durations) == 1
    assert durations[0] == 5.0


def test_calculate_contiguous_beat_durations_empty():
    assert ShotMatchingStage.calculate_contiguous_beat_durations([], 10.0) == []


def test_storyboard_clip_list_contiguous_parity(tmp_path):
    """Test that _build_manual_storyboard_clip_list builds clips that sum to total_duration."""
    dummy_video = tmp_path / "dummy.mp4"
    dummy_video.write_bytes(b"dummy")

    beat_cues = [
        {"id": 1, "start": 0.2, "end": 4.674},
        {"id": 2, "start": 4.674, "end": 9.104},
        {"id": 3, "start": 9.1, "end": 14.701},
        {"id": 4, "start": 14.701, "end": 20.667},
        {"id": 5, "start": 20.667, "end": 24.858},
    ]
    total_duration = 24.858

    ctx = PipelineContext(
        project_name="test_proj",
        product_name="Test Product",
        raw_video_path=str(dummy_video),
        beat_cues=beat_cues,
        total_duration=total_duration,
        manual_shot_map=[
            {"beat_index": 0, "video_path": str(dummy_video), "trim_start": 0.0, "trim_end": 4.3},
            {"beat_index": 1, "video_path": str(dummy_video), "trim_start": 83.0, "trim_end": 87.7},
            {"beat_index": 2, "video_path": str(dummy_video), "trim_start": 36.0, "trim_end": 41.6},
            {"beat_index": 3, "video_path": str(dummy_video), "trim_start": 56.0, "trim_end": 63.1},
            {"beat_index": 4, "video_path": str(dummy_video), "trim_start": 93.0, "trim_end": 96.9},
        ],
    )

    clips = ShotMatchingStage._build_manual_storyboard_clip_list(ctx, dummy_video, 100.0)
    assert len(clips) == 5

    # Target durations sum to total_duration
    assert abs(sum(c["duration"] for c in clips) - total_duration) < 0.002
    assert clips[0]["duration"] == 4.674
