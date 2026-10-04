"""Contract tests for applying editorial pacing at the shared clip-list seam."""

from pathlib import Path
from unittest.mock import patch

from scripts.pipeline_context import PipelineContext
from scripts.stages.shot_matching_stage import ShotMatchingStage


def _context(*, pacing=None, clip_list=None, cue_count=3, total_duration=6.0):
    cues = [
        {"start": float(index * 2), "end": float((index + 1) * 2), "text": f"Cue {index}"}
        for index in range(cue_count)
    ]
    ctx = PipelineContext(
        product_name="Pacing test",
        raw_video_path="raw.mp4",
        clip_list=clip_list,
        total_duration=total_duration,
        export_mp4=False,
    )
    ctx.raw_video = Path("raw.mp4")
    ctx.cues = cues
    ctx.micro_cues = cues
    ctx.editorial_pacing = pacing
    ctx.use_ai_vision = False
    ctx.effective_bgm_name = None
    ctx.mixed_audio_path = None
    ctx.transitions = None
    return ctx


def test_editorial_beats_drive_generated_clip_boundaries():
    ctx = _context(pacing={"beats": [{"timestamp": 2.0}, {"timestamp": 4.0}]})

    with patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 10.0}), \
         patch("scripts.stages.shot_matching_stage.SFXManager.resolve_bgm_path", return_value=None), \
         patch("scripts.stages.shot_matching_stage.MotionAnalyzer.get_motion_scores", return_value=([], [])), \
         patch("scripts.stages.shot_matching_stage.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]):
        ShotMatchingStage.run(ctx)

    assert ctx.is_newly_generated_clips is True
    # Beats drive the boundaries; each one then gets the J-lead after the
    # voice onset it precedes (cue starts 2.0/4.0 + 0.18 on the 1/30 grid,
    # round EDITOR-CUT-QUALITY-R2 audit A7a), like the legacy path.
    assert [clip["duration"] for clip in ctx.actual_clip_list] == [2.167, 2.0, 1.833]
    assert sum(clip["duration"] for clip in ctx.actual_clip_list) == 6.0


def test_manual_clip_list_bypasses_editorial_pacing():
    manual_clips = [
        {
            "id": "manual-clip",
            "source_path": "manual.mp4",
            "trim_start": 3.0,
            "trim_end": 5.5,
            "duration": 2.5,
        }
    ]
    ctx = _context(
        pacing={"beats": [{"timestamp": 2.0}, {"timestamp": 4.0}]},
        clip_list=manual_clips,
    )

    with patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 10.0}), \
         patch("scripts.stages.shot_matching_stage.SFXManager.resolve_bgm_path", return_value=None), \
         patch("scripts.stages.shot_matching_stage.MotionAnalyzer.get_motion_scores", return_value=([], [])):
        ShotMatchingStage.run(ctx)

    assert ctx.is_newly_generated_clips is False
    assert ctx.actual_clip_list is manual_clips
    assert ctx.actual_clip_list[0]["trim_start"] == 3.0
    assert ctx.actual_clip_list[0]["trim_end"] == 5.5


def test_style_budget_is_applied_to_auto_generated_transitions():
    ctx = _context(cue_count=6, total_duration=12.0)

    with patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 10.0}), \
         patch("scripts.stages.shot_matching_stage.SFXManager.resolve_bgm_path", return_value=None), \
         patch("scripts.stages.shot_matching_stage.MotionAnalyzer.get_motion_scores", return_value=([], [])), \
         patch("scripts.stages.shot_matching_stage.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]):
        ShotMatchingStage.run(ctx)

    assert len(ctx.transitions) == 5
    assert [transition["type"] for transition in ctx.transitions[:4]] == ["cut"] * 4
    assert ctx.transitions[4]["type"] != "cut"


def test_style_motion_adds_keyframes_to_auto_generated_restraint_slots():
    ctx = _context(cue_count=4, total_duration=8.0)

    with patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 10.0}), \
         patch("scripts.stages.shot_matching_stage.SFXManager.resolve_bgm_path", return_value=None), \
         patch("scripts.stages.shot_matching_stage.MotionAnalyzer.get_motion_scores", return_value=([], [])), \
         patch("scripts.stages.shot_matching_stage.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]):
        ShotMatchingStage.run(ctx)

    assert ctx.actual_clip_list[0]["keyframes"]
    assert "keyframes" not in ctx.actual_clip_list[1]
    assert ctx.actual_clip_list[2]["keyframes"]


def test_selected_viral_style_reaches_generated_transitions_and_camera_motion():
    ctx = _context(cue_count=6, total_duration=12.0)
    ctx.style_preset = "viral_punch"

    with patch("scripts.stages.shot_matching_stage.VideoEditor.get_media_info", return_value={"duration": 10.0}), \
         patch("scripts.stages.shot_matching_stage.SFXManager.resolve_bgm_path", return_value=None), \
         patch("scripts.stages.shot_matching_stage.MotionAnalyzer.get_motion_scores", return_value=([], [])), \
         patch("scripts.stages.shot_matching_stage.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]):
        ShotMatchingStage.run(ctx)

    # Slides follow the outgoing shot's pan (R2): viral_punch pans every clip,
    # alternating right/left, so clips 1 and 3 (the outgoing shots at the two
    # slide boundaries) both pan left -> content moves right -> slideright.
    assert [transition["type"] for transition in ctx.transitions] == [
        "cut", "slideright", "cut", "slideright", "cut",
    ]
    assert all(clip.get("keyframes") for clip in ctx.actual_clip_list)
