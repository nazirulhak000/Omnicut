"""M5 real-render smoke: one sample per new motion recipe goes through FFmpeg.

The deterministic plan-level contracts live in test_style_distinctness.py;
this file proves the plans the new presets generate (slide-only smart_hack, the
new wipe/slide "compare" family, pain_punch's ease_out heavy push, niche_focus'
iris reveals) actually render with the production FFmpeg path: same frame
count and duration as the voice, no filter-graph failure. Four renders, tiny
synthetic media under tmp_path (deleted by pytest), analysers patched, no
network.
"""

import shutil
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.test_real_render_cut_alignment import (
    CUE_LEN,
    FPS,
    SR,
    STAGE,
    _decoded_audio,
    _frame_pts,
    _write_empty_ass,
    _write_index_coded_source,
    _write_voice,
)

pytestmark = [
    pytest.mark.render_regression,
    pytest.mark.skipif(
        not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
        reason="FFmpeg and FFprobe are required for real-render measurements",
    ),
]

N_CUES = 7  # 14 s: enough boundaries for every preset's first movement slots
EXPECTED_KINDS = {
    "smart_hack": {"slideleft", "slideright"},
    "tech_compare": {"wipeleft", "slideleft", "wiperight"},
    "pain_punch": {"slideleft", "slideright", "circleopen"},
    "niche_focus": {"circleopen"},
}


def _plan(raw, cues, total, style):
    from scripts.pipeline_context import PipelineContext
    from scripts.stages.shot_matching_stage import ShotMatchingStage

    ctx = PipelineContext(product_name="M5 real render", raw_video_path=str(raw), clip_list=None,
                          total_duration=total, export_mp4=False)
    ctx.raw_video = Path(raw)
    ctx.cues = cues
    ctx.micro_cues = cues
    ctx.editorial_pacing = None
    ctx.use_ai_vision = False
    ctx.effective_bgm_name = None
    ctx.mixed_audio_path = None
    ctx.transitions = None
    ctx.style_preset = style
    with ExitStack() as stack:
        stack.enter_context(patch(f"{STAGE}.SFXManager.resolve_bgm_path", return_value=None))
        stack.enter_context(patch(f"{STAGE}.BeatSync.get_beat_times", return_value=[]))
        stack.enter_context(patch(f"{STAGE}.MotionAnalyzer.get_motion_scores", return_value=([], [])))
        stack.enter_context(patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]))
        ShotMatchingStage.run(ctx)
    return ctx


@pytest.mark.parametrize("style", sorted(EXPECTED_KINDS))
def test_new_preset_plan_renders_through_the_real_ffmpeg_path(tmp_path, monkeypatch, style):
    from scripts.stages.video_assembly_stage import _centre_transition_overlaps
    from scripts.style_motion_policy import resolve_style_motion_policy
    from scripts.video_editor import VideoEditor

    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    raw = tmp_path / "raw.mp4"
    _write_index_coded_source(raw)
    ass = tmp_path / "empty.ass"
    _write_empty_ass(ass)
    cue_starts = [round(CUE_LEN * i, 3) for i in range(N_CUES)]
    cues = [{"start": s, "end": round(s + CUE_LEN, 3), "text": f"cue {i}"} for i, s in enumerate(cue_starts)]
    total = round(CUE_LEN * N_CUES, 3)
    voice = tmp_path / "voice.wav"
    _write_voice(voice, cue_starts, total)

    ctx = _plan(raw, cues, total, style)
    clips = [dict(c) for c in ctx.actual_clip_list]
    transitions = [dict(t) if isinstance(t, dict) else {"type": str(t), "duration": 0.0} for t in ctx.transitions]
    assert len(transitions) == len(clips) - 1

    # the plan the planner produced is the style's own recipe
    kinds = {t["type"] for t in transitions} - {"cut"}
    assert kinds and kinds <= EXPECTED_KINDS[style], (style, kinds)
    policy = resolve_style_motion_policy(style)
    moved = [c for c in clips if c.get("keyframes")]
    assert moved, style
    assert all(c["keyframes"][-1]["easing"] == policy.camera_easing for c in moved)

    _centre_transition_overlaps(clips, transitions)
    out = tmp_path / f"{style}.mp4"
    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(raw)], total_duration=total, mixed_audio_path=str(voice),
        ass_subtitle_path=str(ass), output_mp4_path=str(out), clip_list=clips,
        transitions=transitions, export_preset="draft",
    )
    assert out.exists() and out.stat().st_size > 10_000
    pts = _frame_pts(out)
    assert abs(len(pts) - round(total * FPS)) <= 1, (style, len(pts))
    audio = _decoded_audio(out)
    assert abs(len(audio) / SR - total) <= 0.1
