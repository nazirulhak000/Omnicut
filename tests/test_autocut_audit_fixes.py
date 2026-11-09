"""Audit 20261109 section 3 contracts for the auto shot planner:
S3-01 topic hold without AI, S3-02 short raw, S3-05 manual pin speed floor,
S3-06 guided-take gaps, S3-07 auto plan tag, S3-09 landscape fit.

Offline: every analyser touching real media is patched."""

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.error_handler import AppError
from scripts.pipeline_context import PipelineContext
from scripts.stages.shot_matching_stage import ShotMatchingStage
from tests.legacy_shot_pacing import legacy_body_pacing  # noqa: F401  (fixture)

STAGE = "scripts.stages.shot_matching_stage"
FRAME = 1 / 30


def _context(cues, total_duration, **extra):
    ctx = PipelineContext(product_name="audit", raw_video_path="raw.mp4", clip_list=None,
                          total_duration=total_duration, export_mp4=False)
    ctx.raw_video = Path("raw.mp4")
    ctx.cues = cues
    ctx.micro_cues = cues
    ctx.editorial_pacing = None
    ctx.use_ai_vision = False
    ctx.effective_bgm_name = None
    ctx.mixed_audio_path = None
    ctx.transitions = None
    for key, value in extra.items():
        setattr(ctx, key, value)
    return ctx


def _run(ctx, info):
    with ExitStack() as stack:
        stack.enter_context(patch(f"{STAGE}.VideoEditor.get_media_info", return_value=info))
        stack.enter_context(patch(f"{STAGE}.SFXManager.resolve_bgm_path", return_value=None))
        stack.enter_context(patch(f"{STAGE}.MotionAnalyzer.get_motion_scores", return_value=([], [])))
        stack.enter_context(patch(f"{STAGE}.ScriptToneAnalyzer.classify_tone_shifts", return_value=[]))
        ShotMatchingStage.run(ctx)
    return ctx.actual_clip_list


def _played_end(clip):
    return float(clip["trim_end"])


@pytest.mark.usefixtures("legacy_body_pacing")
def test_split_sentence_continues_the_same_footage_without_ai():
    """S3-01: one 8 s line split by the shot cap plays one continuous span."""
    cues = [{"start": 0.0, "end": 8.0, "text": "ประโยคเดียวยาวมากที่ไม่มีจุดจบ"}]
    clips = _run(_context(cues, 8.0), {"duration": 60.0})
    assert len(clips) >= 2
    for prev, nxt in zip(clips, clips[1:]):
        assert nxt["trim_start"] == pytest.approx(_played_end(prev), abs=FRAME + 1e-3)


@pytest.mark.usefixtures("legacy_body_pacing")
@pytest.mark.parametrize("raw_duration", [1.5, 3.0])
def test_short_raw_plays_once_then_holds(raw_duration):
    """S3-02: no clip asks for footage past the raw, no replayed span."""
    cues = [{"start": 2.0 * i, "end": 2.0 * (i + 1), "text": f"ท่อน {i}."} for i in range(4)]
    clips = _run(_context(cues, 8.0), {"duration": raw_duration})
    assert all(float(c["trim_end"]) <= raw_duration + 1e-6 for c in clips)
    playing = [(round(c["trim_start"], 3), round(c["trim_end"], 3)) for c in clips if not c.get("held_source_time")]
    assert all(a != b for a, b in zip(playing, playing[1:]))
    assert any(c.get("hold_reason") == "raw_footage_too_short" for c in clips)
    # The planned timeline still covers the narration.
    assert sum(c["duration"] for c in clips) == pytest.approx(8.0, abs=0.05)


def test_fallback_offset_never_repeats_previous_span():
    offset = ShotMatchingStage._compute_smart_fallback_offset(
        g_idx=1, total_groups=4, raw_duration=4.0, c_dur=2.0, previous_offsets=[0.0],
    )
    assert abs(offset - 0.0) >= FRAME


def _manual_ctx(pins, beat_cues, total):
    return _context([], total, beat_cues=beat_cues, manual_shot_map=pins)


@pytest.mark.parametrize("pin,expected_speed,expected_freeze,expected_end", [
    ({"trim_start": 0.0, "trim_end": 0.5}, 0.25, 2.0, 0.5),   # 0.5 s pin in a 4 s beat
    ({"trim_start": 0.0, "trim_end": 40.0}, 4.0, None, 16.0),  # longer than 4x the beat
])
def test_manual_pin_fills_its_beat(pin, expected_speed, expected_freeze, expected_end):
    """S3-05: span / speed + freeze_tail == planned duration."""
    timing = ShotMatchingStage._manual_pin_timing(pin, "pin.mp4", 4.0, 0)
    assert timing["speed"] == expected_speed
    assert timing["trim_end"] == expected_end
    assert timing.get("freeze_tail") == expected_freeze
    played = (timing["trim_end"] - timing["trim_start"]) / timing["speed"] + timing.get("freeze_tail", 0.0)
    assert played == pytest.approx(4.0, abs=1e-3)


def test_manual_pin_without_end_uses_rest_of_file_or_fails():
    with patch(f"{STAGE}.VideoEditor.get_media_info", return_value={"duration": 6.0}):
        timing = ShotMatchingStage._manual_pin_timing({"trim_start": 1.0, "trim_end": 0.0}, "pin.mp4", 5.0, 2)
    assert timing["trim_end"] == 6.0 and timing["speed"] == 1.0
    with patch(f"{STAGE}.VideoEditor.get_media_info", return_value={"duration": 0.0}):
        with pytest.raises(AppError) as exc_info:
            ShotMatchingStage._manual_pin_timing({"trim_start": 1.0, "trim_end": 1.0}, "pin.mp4", 5.0, 2)
    assert exc_info.value.code == "MANUAL_PIN_EMPTY_SPAN"


def test_guided_take_slots_absorb_gaps_between_beats():
    """S3-06: each clip starts at its beat's voice onset; gaps are not dropped."""
    beats = [
        {"start": 0.3, "end": 2.0, "text": "a"},
        {"start": 2.5, "end": 4.0, "text": "b"},
        {"start": 4.6, "end": 6.0, "text": "c"},
    ]
    slots = ShotMatchingStage._beat_slot_durations(beats)
    starts = [0.0, slots[0], slots[0] + slots[1]]
    assert starts[1] == pytest.approx(2.5, abs=1e-3)
    assert starts[2] == pytest.approx(4.6, abs=1e-3)
    assert sum(slots) == pytest.approx(6.0, abs=1e-3)


@pytest.mark.usefixtures("legacy_body_pacing")
def test_auto_plan_is_tagged_and_landscape_raw_uses_blur_fit():
    """S3-07 tag + S3-09 blurred-canvas fit for landscape footage."""
    cues = [{"start": 2.0 * i, "end": 2.0 * (i + 1), "text": f"ท่อน {i}."} for i in range(3)]
    clips = _run(_context(cues, 6.0), {"duration": 30.0, "width": 1920, "height": 1080})
    assert clips and all(c.get("auto_generated") is True for c in clips)
    assert all(c.get("fit_mode") == "blur" for c in clips)

    portrait = _run(_context(cues, 6.0), {"duration": 30.0, "width": 1080, "height": 1920})
    assert all("fit_mode" not in c for c in portrait)


@pytest.mark.usefixtures("legacy_body_pacing")
def test_landscape_fit_skipped_when_cutout_enabled():
    cues = [{"start": 0.0, "end": 2.0, "text": "ท่อน."}]
    ctx = _context(cues, 2.0)
    with patch.object(PipelineContext, "resolve_background_isolation_contract", return_value={"enabled": True}):
        clips = _run(ctx, {"duration": 30.0, "width": 1920, "height": 1080})
    assert all("fit_mode" not in c for c in clips)


def test_user_clip_list_is_never_tagged():
    ctx = _context([{"start": 0.0, "end": 2.0, "text": "x"}], 2.0)
    ctx.clip_list = [{"id": "c0", "source_path": "a.mp4", "trim_start": 0.0, "trim_end": 2.0, "duration": 2.0}]
    clips = _run(ctx, {"duration": 30.0, "width": 1920, "height": 1080})
    assert "auto_generated" not in clips[0] and "fit_mode" not in clips[0]
