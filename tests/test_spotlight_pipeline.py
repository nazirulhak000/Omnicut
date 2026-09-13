"""Pipeline/API seam tests for the optional SpotlightV1 contract."""

from pathlib import Path
from unittest.mock import patch

from scripts.api_schemas import RenderRequest
from scripts.pipeline import TikTokAutoCutterPipeline
from scripts.pipeline_context import PipelineContext, _payload_fingerprint, _stage_payload_from_manifest
from scripts.stages import (
    AudioMixStage,
    ScriptStage,
    ShotMatchingStage,
    SourceResolutionStage,
    SubtitleStage,
    VideoAssemblyStage,
    VoiceStage,
)


ENABLED = {
    "schema_version": 1,
    "enabled": True,
    "shape": "rect",
    "focus": {"x": 0.52, "y": 0.48, "width": 0.4, "height": 0.3},
    "dim_opacity": 0.5,
    "feather": 0.02,
}


def _context(**overrides):
    values = {
        "product_name": "Demo Product",
        "raw_video_path": "01_Raw/demo.mp4",
        "project_name": "spotlight-test",
    }
    values.update(overrides)
    return PipelineContext(**values)


def test_render_request_accepts_optional_spotlight_without_changing_legacy_defaults():
    request = RenderRequest(
        product_name="Demo Product",
        raw_video_path="01_Raw/demo.mp4",
        key_features="feature",
        pain_point="pain",
        price_deal="deal",
    )
    assert request.spotlight is None

    with_spotlight = request.model_copy(update={"spotlight": ENABLED})
    assert with_spotlight.spotlight == ENABLED


def test_context_normalizes_enabled_input_and_rejects_raw_filter_payload():
    ctx = _context(
        spotlight={
            **ENABLED,
            "filter": "movie=bad; drawtext=text='should never reach renderer'",
            "focus": {**ENABLED["focus"], "x": 9},
        }
    )

    resolved = ctx.resolve_spotlight_contract()

    assert resolved["enabled"] is True
    assert resolved["shape"] == "rectangle"
    assert resolved["focus"]["x"] == 0.8
    assert "filter" not in resolved
    assert ctx.resolve_spotlight_contract() == resolved


def test_context_reuses_normalized_spotlight_from_legacy_manifest():
    manifest = {
        "render_params": {
            "spotlight": ENABLED,
        }
    }
    ctx = _context(manifest=manifest, spotlight=None)

    resolved = ctx.resolve_spotlight_contract()

    assert resolved["enabled"] is True
    assert resolved["shape"] == "rectangle"
    assert resolved["focus"] == ENABLED["focus"]


def test_context_accepts_spotlight_embedded_in_legacy_effects_array():
    ctx = _context(
        spotlight=None,
        effects=[
            {"kind": "sparkle", "effectId": "fx_sparkle"},
            {"kind": "spotlight", "config": ENABLED},
        ],
    )

    resolved = ctx.resolve_spotlight_contract()

    assert resolved["enabled"] is True
    assert resolved["shape"] == "rectangle"


def test_manifest_snapshot_persists_canonical_spotlight_in_both_locations():
    ctx = _context(spotlight=ENABLED)
    resolved = ctx.resolve_spotlight_contract()

    snapshot = ctx._manifest_snapshot_from_context()

    assert snapshot["spotlight"] == resolved
    assert snapshot["render_params"]["spotlight"] == resolved
    assert "filter" not in snapshot["spotlight"]


def test_spotlight_changes_video_fingerprint_deterministically():
    base = {
        "render_params": {
            "raw_video_path": "01_Raw/demo.mp4",
            "spotlight": None,
        },
        "total_duration": 2.0,
        "clip_list": [],
        "transitions": [],
    }
    enabled = {
        **base,
        "render_params": {**base["render_params"], "spotlight": ENABLED},
    }

    base_payload = _stage_payload_from_manifest(base, "video")
    enabled_payload = _stage_payload_from_manifest(enabled, "video")

    assert _payload_fingerprint(base_payload) == _payload_fingerprint(
        _stage_payload_from_manifest(base, "video")
    )
    assert _payload_fingerprint(base_payload) != _payload_fingerprint(enabled_payload)


def test_pipeline_threads_spotlight_into_context(monkeypatch):
    observed = {}

    def capture(ctx):
        observed["ctx"] = ctx

    for stage in (
        SourceResolutionStage,
        ScriptStage,
        VoiceStage,
        SubtitleStage,
        AudioMixStage,
        ShotMatchingStage,
        VideoAssemblyStage,
    ):
        monkeypatch.setattr(stage, "run", capture)

    result = TikTokAutoCutterPipeline.run(
        product_name="Demo Product",
        raw_video_path="01_Raw/demo.mp4",
        project_name="spotlight-test",
        key_features="feature",
        pain_point="pain",
        price_deal="deal",
        spotlight=ENABLED,
        export_mp4=False,
    )

    assert result == {}
    assert observed["ctx"].resolve_spotlight_contract()["enabled"] is True


def test_video_assembly_sends_only_normalized_spotlight_when_renderer_supports_it(tmp_path):
    ctx = _context(
        raw_video_path=str(tmp_path / "source.mp4"),
        export_mp4=True,
        total_duration=1.0,
        raw_video=Path(tmp_path / "source.mp4"),
        mixed_audio_path=Path(tmp_path / "mix.wav"),
        ass_sub_path=Path(tmp_path / "subtitles.ass"),
        spotlight={**ENABLED, "filter": "invalid"},
    )
    ctx.actual_clip_list = []

    with patch("scripts.pipeline.VideoEditor.assemble_tiktok_video") as assemble, patch(
        "scripts.stages.video_assembly_stage.EXPORTS_DIR", tmp_path
    ), patch("scripts.stages.video_assembly_stage.ExportRegistry.ensure", return_value={"id": "x"}):
        VideoAssemblyStage.run(ctx)

    passed = assemble.call_args.kwargs["spotlight"]
    assert passed["enabled"] is True
    assert passed["shape"] == "rectangle"
    assert "filter" not in passed


def test_video_assembly_legacy_renderer_keeps_default_call_shape(tmp_path):
    ctx = _context(
        export_mp4=True,
        total_duration=1.0,
        raw_video=Path(tmp_path / "source.mp4"),
        mixed_audio_path=Path(tmp_path / "mix.wav"),
        ass_sub_path=Path(tmp_path / "subtitles.ass"),
        spotlight=None,
    )
    ctx.actual_clip_list = []

    with patch("scripts.pipeline.VideoEditor.assemble_tiktok_video") as assemble, patch(
        "scripts.stages.video_assembly_stage.EXPORTS_DIR", tmp_path
    ), patch("scripts.stages.video_assembly_stage.ExportRegistry.ensure", return_value={"id": "x"}):
        VideoAssemblyStage.run(ctx)

    assert "spotlight" not in assemble.call_args.kwargs
