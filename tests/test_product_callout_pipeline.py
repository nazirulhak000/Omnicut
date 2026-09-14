"""Backend overlay pipeline tests ensuring no unwanted auto callouts are injected."""

from copy import deepcopy
from unittest.mock import patch

from scripts.pipeline_context import PipelineContext
from scripts.stages.subtitle_stage import (
    SubtitleStage,
    _materialize_product_callouts,
)
from scripts.subtitle_engine import SubtitleEngine


def _context(**kwargs):
    values = {
        "product_name": "Soundcore Q45",
        "raw_video_path": "unused.mp4",
    }
    values.update(kwargs)
    return PipelineContext(**values)


def _callouts(overlays):
    return [item for item in overlays if item.get("role") == "product_callout"]


def test_does_not_auto_materialize_unwanted_product_callouts():
    """Verify that auto-materialization of brand/model/feature callouts is disabled."""
    ctx = _context(
        product_meta={
            "brand": "Anker",
            "model": "Soundcore Q45",
            "features": ["Adaptive ANC"],
        },
        beat_cues=[
            {"id": "intro", "start": 0.0, "end": 1.2, "on_screen": ""},
            {"id": "feature", "start": 1.2, "end": 2.4, "on_screen": "Adaptive ANC"},
        ],
        cues=[
            {"start": 0.0, "end": 0.4, "on_screen": "fallback text"},
        ],
    )

    result = _materialize_product_callouts(ctx, [])
    # Must NOT inject any auto callouts
    assert result == []


def test_preserves_manual_overlays_without_mutation():
    manual = {
        "id": "manual-anc",
        "kind": "text",
        "role": "product_callout",
        "callout_type": "feature",
        "origin": "manual",
        "start": 0.7,
        "end": 1.7,
        "tiers": [{"text": "ANC", "look": {"color": "#00FFAA"}}],
    }
    hook = {"id": "ovl_hook", "kind": "hook", "role": "hook"}
    existing = [hook, manual]
    original = deepcopy(existing)
    ctx = _context(
        product_meta={"features": ["ANC", "Fast charge"]},
        beat_cues=[{"start": 0.0, "end": 2.0, "on_screen": "ANC"}],
        overlays=existing,
    )

    result = _materialize_product_callouts(ctx, existing)
    # Manual overlays must be preserved exactly
    assert len(result) == 2
    assert result[0]["id"] == "ovl_hook"
    assert result[1]["id"] == "manual-anc"
    assert existing == original
    assert result is not existing


def test_subtitle_stage_does_not_inject_callouts_to_renderer(tmp_path):
    hook_overlay = {"id": "ovl_hook", "kind": "hook", "role": "hook"}
    ctx = _context(
        project_dir=tmp_path,
        total_duration=2.0,
        beat_cues=[{"start": 0.0, "end": 2.0, "on_screen": "20000mAh"}],
        cues=[{"start": 0.0, "end": 2.0, "text": "พาวเวอร์แบงก์"}],
        overlays=[hook_overlay],
    )

    with patch.object(SubtitleEngine, "generate_ass", return_value=(None, [])) as generate_ass:
        SubtitleStage.run(ctx)

    passed_overlays = generate_ass.call_args.kwargs["overlays"]
    # Overlays must remain ONLY what the user provided
    assert passed_overlays == [hook_overlay]
    assert ctx.effective_overlays == [hook_overlay]
