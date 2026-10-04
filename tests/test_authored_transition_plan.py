"""An editor's cuts are decisions, including an entirely hard-cut timeline."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from scripts.pipeline_context import PipelineContext
from scripts.stages.video_assembly_stage import VideoAssemblyStage


def _context(transitions, *, newly_generated=False, editor=True):
    clips = [
        {"id": f"c{i}", "source_path": "dummy.mp4", "trim_start": 1 + 3 * i,
         "trim_end": 3 + 3 * i, "duration": 2, "speed": 1, "zoom": 1.2,
         "transition_in": "cut"}
        for i in range(4)
    ]
    ctx = PipelineContext(product_name="Test", raw_video_path="dummy.mp4",
                          project_name="authored-plan", export_mp4=False)
    ctx.actual_clip_list = clips
    ctx.clip_list = clips if editor else None
    ctx.transitions = transitions
    ctx.style_preset = "viral_punch"
    ctx.is_newly_generated_clips = newly_generated
    ctx.total_duration = 8
    return ctx


def _saved(ctx):
    with patch("scripts.stages.video_assembly_stage.ProjectManifest.save") as save:
        VideoAssemblyStage.run(ctx)
    return save.call_args.kwargs


@pytest.mark.parametrize("transitions", [None, [], ["cut"] * 3, [{"type": "cut"}] * 3])
def test_editor_all_cut_plan_is_preserved(transitions):
    ctx = _context(transitions)
    original = deepcopy(ctx.actual_clip_list)
    saved = _saved(ctx)
    assert saved["clip_list"] == original
    assert [b["type"] for b in saved["transitions"]] == ["cut"] * 3
    assert ctx.transitions == saved["transitions"]


def test_planner_all_cut_decision_is_not_filled_a_second_time():
    ctx = _context(["cut"] * 3, newly_generated=True, editor=False)
    original = deepcopy(ctx.actual_clip_list)
    with patch("scripts.stages.video_assembly_stage._fill_undecided_transitions",
               side_effect=AssertionError("A complete plan must not be replaced")):
        saved = _saved(ctx)
    assert saved["clip_list"] == original
    assert [b["type"] for b in saved["transitions"]] == ["cut"] * 3


def test_existing_clip_metadata_is_used_when_transition_array_is_absent():
    ctx = _context(None, editor=False)
    ctx.actual_clip_list[2].update(transition_in="slideleft", transition_duration=.6, transition_easing="ease_out")
    saved = _saved(ctx)
    assert saved["transitions"][1] == {"type": "slideleft", "duration": .6, "easing": "ease_out"}
    assert [b["type"] for b in saved["transitions"]] == ["cut", "slideleft", "cut"]


def test_explicit_array_updates_preview_metadata_and_pads_missing_boundaries_with_cuts():
    ctx = _context([{"type": "fade", "duration": .3, "easing": "ease_in_out"}])
    saved = _saved(ctx)
    assert saved["clip_list"][1]["transition_in"] == "fade"
    assert saved["clip_list"][1]["transition_duration"] == .3
    assert saved["clip_list"][1]["transition_easing"] == "ease_in_out"
    assert [b["type"] for b in saved["transitions"]] == ["fade", "cut", "cut"]


def test_empty_explicit_array_disables_effects_on_existing_clip_metadata():
    ctx = _context([])
    ctx.actual_clip_list[2].update(transition_in="slideleft", transition_duration=.6, transition_easing="ease_out")
    saved = _saved(ctx)
    assert [b["type"] for b in saved["transitions"]] == ["cut"] * 3
    assert saved["clip_list"][2]["transition_in"] == "cut"
    assert "transition_duration" not in saved["clip_list"][2]
    assert "transition_easing" not in saved["clip_list"][2]


def test_unspecified_new_plan_still_receives_budgeted_automatic_effects():
    ctx = _context(None, newly_generated=True, editor=False)
    saved = _saved(ctx)
    assert [b["type"] for b in saved["transitions"]] == ["cut", "slideleft", "cut"]
    assert saved["clip_list"][2]["transition_easing"] == "ease_out"
