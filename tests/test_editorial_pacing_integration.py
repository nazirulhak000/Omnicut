"""Integration contracts for the optional editorial pacing manifest field."""

from scripts.editorial_pacing import build_pacing_plan_from_cues
from scripts.pipeline_context import (
    PipelineContext,
    _stage_payload_from_manifest,
    build_incremental_render_metadata,
)


def _sample_plan():
    return build_pacing_plan_from_cues(
        [
            {
                "start": 0.0,
                "end": 2.0,
                "word_timings": [
                    {"text": "one", "start": 0.0, "end": 0.4},
                    {"text": "two", "start": 1.0, "end": 1.4},
                ],
            }
        ],
        duration=2.0,
    )


def test_subtitle_payload_includes_editorial_pacing_contract():
    plan = _sample_plan()
    manifest = {
        "cues": [],
        "total_duration": 2.0,
        "editorial_pacing": plan,
    }

    payload = _stage_payload_from_manifest(manifest, "subtitles")

    assert payload["inputs"]["editorial_pacing"] == plan


def test_context_snapshot_preserves_pacing_for_incremental_rerender():
    plan = _sample_plan()
    context = PipelineContext(
        product_name="demo",
        raw_video_path="demo.mp4",
        editorial_pacing=plan,
    )

    snapshot = context._manifest_snapshot_from_context()

    assert snapshot["editorial_pacing"] == plan
    assert snapshot["render_params"]["editorial_pacing"] == plan


def test_pacing_changes_subtitle_fingerprint_but_legacy_manifest_stays_supported():
    plan = _sample_plan()
    legacy = {"cues": [], "total_duration": 2.0}
    current = {**legacy, "editorial_pacing": plan}

    legacy_metadata = build_incremental_render_metadata(legacy)
    current_metadata = build_incremental_render_metadata(current)

    assert legacy_metadata["stage_fingerprints"]["subtitles"] != current_metadata["stage_fingerprints"]["subtitles"]
    assert _stage_payload_from_manifest(legacy, "subtitles")["inputs"]["editorial_pacing"] is None
