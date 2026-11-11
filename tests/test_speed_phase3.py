"""Speed round phase 3: analysis that only feeds the automatic shot plan is skipped when the
clip list is already fixed. Offline and deterministic."""
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.pipeline_context import PipelineContext
from scripts.stages.shot_matching_stage import ShotMatchingStage

STAGE = "scripts.stages.shot_matching_stage"


def _ctx(tmp_path):
    mixed = tmp_path / "mixed.wav"
    mixed.write_bytes(b"RIFF")
    ctx = PipelineContext(product_name="speed phase 3", raw_video_path="raw.mp4", total_duration=6.0, export_mp4=False)
    ctx.raw_video = Path("raw.mp4")
    ctx.cues = [
        {"id": 1, "start": 0.0, "end": 3.0, "text": "ท่อนแรก"},
        {"id": 2, "start": 3.0, "end": 6.0, "text": "ท่อนสอง"},
    ]
    ctx.micro_cues = list(ctx.cues)
    ctx.use_ai_vision = False
    ctx.mixed_audio_path = mixed
    return ctx


@pytest.fixture()
def analyzers():
    """Record which analyzers the stage calls; none of them touch a real file."""
    calls = []

    def record(name, value):
        def fake(*_a, **_kw):
            calls.append(name)
            return value
        return fake

    with patch(f"{STAGE}.VideoEditor.get_media_info", return_value={"duration": 30.0, "width": 1080, "height": 1920}), \
            patch(f"{STAGE}.SFXManager.resolve_bgm_path", side_effect=record("bgm", Path("bgm.wav"))), \
            patch(f"{STAGE}.BeatSync.get_beat_times", side_effect=record("beats", [])), \
            patch(f"{STAGE}.BeatSync.get_rms_energy", side_effect=record("energy", ([], []))), \
            patch(f"{STAGE}.MotionAnalyzer.get_motion_scores", side_effect=record("motion", ([], []))), \
            patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]):
        yield calls


def test_fixed_clip_list_skips_shot_plan_analysis(tmp_path, analyzers):
    ctx = _ctx(tmp_path)
    clip = {"id": "c0", "source_path": "a.mp4", "trim_start": 0.0, "trim_end": 6.0, "duration": 6.0}
    ctx.clip_list = [dict(clip)]

    ShotMatchingStage.run(ctx)

    assert analyzers == []
    assert ctx.actual_clip_list == [clip]
    assert ctx.is_newly_generated_clips is False


def test_automatic_shot_plan_still_runs_every_analyzer(tmp_path, analyzers):
    ctx = _ctx(tmp_path)

    ShotMatchingStage.run(ctx)

    assert sorted(analyzers) == ["beats", "bgm", "energy", "motion"]
    assert ctx.is_newly_generated_clips is True
    assert ctx.actual_clip_list
