"""Contract tests for the guided-take / proportional mapping branches in
ShotMatchingStage (scripts/stages/shot_matching_stage.py) -- see
C:\\Users\\Winon\\.claude\\plans\\cheeky-cooking-quokka.md (Phase D).
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from scripts.pipeline_context import PipelineContext
from scripts.stages.shot_matching_stage import ShotMatchingStage
from scripts.error_handler import AppError


def _beat_cues(durations):
    cues = []
    t = 0.0
    for i, dur in enumerate(durations):
        cues.append({"id": i + 1, "start": round(t, 3), "end": round(t + dur, 3), "text": f"Beat {i}"})
        t += dur
    return cues


def _context(**overrides):
    ctx = PipelineContext(
        product_name="Guided take test",
        raw_video_path="raw.mp4",
        total_duration=overrides.pop("total_duration", 20.0),
        export_mp4=False,
        use_ai_vision=True,
    )
    ctx.raw_video = Path("raw.mp4")
    ctx.cues = []
    ctx.micro_cues = []
    ctx.effective_bgm_name = None
    ctx.mixed_audio_path = None
    ctx.transitions = None
    for key, value in overrides.items():
        setattr(ctx, key, value)
    return ctx


@patch("scripts.stages.shot_matching_stage.GeminiVisionMatcher.match_script_to_video")
@patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 42.0})
@patch("scripts.stages.shot_matching_stage.SFXManager.resolve_bgm_path", return_value=None)
@patch("scripts.stages.shot_matching_stage.MotionAnalyzer.get_motion_scores", return_value=([], []))
@patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key-to-prove-vision-is-skipped"})
def test_guided_take_exact_mapping_skips_ai_vision(_motion, _bgm, _media_info, mock_gemini_match):
    beat_cues = _beat_cues([4.0, 5.0, 3.0])
    clip_map = [
        {"beat_index": 0, "role": "hook", "trim_start": 0.0, "trim_end": 5.0, "actual_duration": 5.0, "planned_duration": 4.0},
        {"beat_index": 1, "role": "feature", "trim_start": 5.0, "trim_end": 9.0, "actual_duration": 4.0, "planned_duration": 5.0},
        {"beat_index": 2, "role": "cta", "trim_start": 9.0, "trim_end": 12.0, "actual_duration": 3.0, "planned_duration": 3.0},
    ]
    ctx = _context(beat_cues=beat_cues, guided_take_meta={"clip_map": clip_map})

    ShotMatchingStage.run(ctx)

    # AI Vision must never be invoked, even though a GEMINI_API_KEY is set --
    # guided-take mapping takes priority and skips it entirely.
    mock_gemini_match.assert_not_called()
    assert ctx.ai_matched_shots is None
    assert ctx.is_newly_generated_clips is True

    assert len(ctx.actual_clip_list) == 3
    for i, (clip, cue, seg) in enumerate(zip(ctx.actual_clip_list, beat_cues, clip_map)):
        target = cue["end"] - cue["start"]
        expected_speed = seg["actual_duration"] / target
        assert clip["duration"] == pytest.approx(target, abs=1e-3)
        assert clip["speed"] == pytest.approx(expected_speed, abs=1e-3)
        assert clip["trim_start"] == pytest.approx(seg["trim_start"], abs=1e-3)
        assert clip["trim_end"] == pytest.approx(seg["trim_end"], abs=1e-3)
        assert clip["shot_index"] == i


@patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 42.0})
def test_guided_take_beat_mismatch_raises(_media_info):
    beat_cues = _beat_cues([4.0, 5.0])  # 2 beats
    clip_map = [
        {"beat_index": 0, "role": "hook", "trim_start": 0.0, "trim_end": 4.0, "actual_duration": 4.0, "planned_duration": 4.0},
    ]  # only 1 segment -- stale sidecar / script edited after filming
    ctx = _context(beat_cues=beat_cues, guided_take_meta={"clip_map": clip_map})

    with pytest.raises(AppError) as exc_info:
        ShotMatchingStage.run(ctx)
    assert exc_info.value.code == "GUIDED_TAKE_BEAT_MISMATCH"


@patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 30.0})
@patch("scripts.stages.shot_matching_stage.SFXManager.resolve_bgm_path", return_value=None)
@patch("scripts.stages.shot_matching_stage.MotionAnalyzer.get_motion_scores", return_value=([], []))
def test_proportional_mapping_uses_constant_speed(_motion, _bgm, _media_info):
    beat_cues = _beat_cues([2.0, 4.0, 6.0])  # total planned = 12.0, raw_duration = 30.0
    ctx = _context(beat_cues=beat_cues, shot_list_id="prod:angle", use_ai_vision=False)

    ShotMatchingStage.run(ctx)

    assert ctx.is_newly_generated_clips is True
    assert len(ctx.actual_clip_list) == 3

    expected_speed = 30.0 / 12.0
    speeds = [clip["speed"] for clip in ctx.actual_clip_list]
    assert all(s == pytest.approx(expected_speed, abs=1e-3) for s in speeds)

    # Each beat's raw-footage slice is proportional to its planned share.
    durations_planned = [2.0, 4.0, 6.0]
    for clip, planned in zip(ctx.actual_clip_list, durations_planned):
        raw_span = clip["trim_end"] - clip["trim_start"]
        assert raw_span == pytest.approx((planned / 12.0) * 30.0, abs=1e-2)

    # Trims tile the raw video contiguously with no gap/overlap, ending at
    # (approximately) the full raw duration.
    assert ctx.actual_clip_list[0]["trim_start"] == pytest.approx(0.0, abs=1e-3)
    assert ctx.actual_clip_list[-1]["trim_end"] == pytest.approx(30.0, abs=1e-2)
