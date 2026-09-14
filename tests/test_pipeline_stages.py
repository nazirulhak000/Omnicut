"""
Unit tests for PipelineContext and Modular Pipeline Stages (Phase 7).
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from scripts.pipeline_context import PipelineContext
from scripts.stages import (
    SourceResolutionStage,
    ScriptStage,
    VoiceStage,
    SubtitleStage,
    AudioMixStage,
    ShotMatchingStage,
    VideoAssemblyStage,
)
from scripts.pipeline import TikTokAutoCutterPipeline, choose_transition, _every_boundary_is_a_cut


def test_pipeline_context_initialization():
    """Context stores inputs and helper methods behave correctly."""
    ctx = PipelineContext(
        product_name="PowerBank 20000mAh",
        raw_video_path="test_video.mp4",
        project_name="test_proj"
    )
    assert ctx.product_name == "PowerBank 20000mAh"
    assert ctx.raw_video_path == "test_video.mp4"
    assert ctx.project_name == "test_proj"
    assert ctx.should_run("script") is True
    assert ctx.should_run("voice") is True
    assert ctx.stage_timings == {}


def test_pipeline_records_monotonic_stage_timings(monkeypatch):
    """Every stage is timed without changing the orchestration contract."""
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

    ticks = iter(range(16))
    monkeypatch.setattr("scripts.pipeline.time.perf_counter", lambda: next(ticks))

    TikTokAutoCutterPipeline.run(
        product_name="Timed Product",
        raw_video_path="dummy.mp4",
        export_mp4=False,
    )

    assert observed["ctx"].stage_timings == {
        "source": 1.0,
        "script": 1.0,
        "voice": 1.0,
        "subtitles": 1.0,
        "mix": 1.0,
        "shot_matching": 1.0,
        "video_assembly": 1.0,
    }


def test_video_assembly_persists_render_performance_snapshot(monkeypatch):
    """Completed manifests retain timings for a real render bottleneck audit."""
    ctx = PipelineContext(
        product_name="Timed Product",
        raw_video_path="dummy.mp4",
        project_name="timed-project",
        export_mp4=False,
    )
    ctx.stage_timings = {"source": 0.125, "ffmpeg_assembly": 1.5}
    ctx.pipeline_started_at = 10.0

    monkeypatch.setattr("scripts.stages.video_assembly_stage.time.perf_counter", lambda: 12.345)
    with patch("scripts.stages.video_assembly_stage.ProjectManifest.save") as save:
        VideoAssemblyStage.run(ctx)

    performance = save.call_args.kwargs["render_performance"]
    assert performance == {
        "schema_version": 1,
        "stage_seconds": {"source": 0.125, "ffmpeg_assembly": 1.5},
        "pipeline_elapsed_s": 2.345,
    }


def test_pipeline_context_reroll_stages():
    """resume_from controls should_run for earlier vs later stages."""
    ctx = PipelineContext(
        product_name="Product",
        raw_video_path="video.mp4",
        project_name="proj",
        resume_from="subtitles"
    )
    assert ctx.should_run("script") is False
    assert ctx.should_run("voice") is False
    assert ctx.should_run("mix") is False
    assert ctx.should_run("subtitles") is True
    assert ctx.should_run("video") is True


def test_choose_transition_variants():
    """choose_transition returns valid types and durations."""
    t1 = choose_transition(1.0, 1.3, 0)
    assert t1["type"] == "circleopen"
    assert t1["duration"] == 0.35

    t2 = choose_transition(1.3, 1.0, 1)
    assert t2["type"] == "circleclose"

    t3 = choose_transition(1.0, 1.0, 2)
    assert t3["type"].startswith(("slide", "fade"))


def test_every_boundary_is_a_cut():
    """_every_boundary_is_a_cut detects cut-only arrays."""
    assert _every_boundary_is_a_cut([]) is True
    assert _every_boundary_is_a_cut(["cut", "cut"]) is True
    assert _every_boundary_is_a_cut([{"type": "cut"}, {"type": "cut"}]) is True
    assert _every_boundary_is_a_cut(["cut", "fade"]) is False
    assert _every_boundary_is_a_cut([{"type": "cut"}, {"type": "dissolve"}]) is False


def test_script_stage_with_custom_script():
    """Custom script is parsed and formatted into lines with cues and sfx."""
    ctx = PipelineContext(
        product_name="Gadget",
        raw_video_path="dummy.mp4",
        custom_script="บรรทัดหนึ่ง\nบรรทัดสอง\nสั่งเลยตอนนี้",
        script_overlays=["หัวข้อ", "จุดเด่น", "ราคา"]
    )
    ScriptStage.run(ctx)
    assert ctx.script_data is not None
    assert len(ctx.script_data["lines"]) == 3
    assert ctx.script_data["lines"][0]["sfx"] == "whoosh"
    assert ctx.script_data["lines"][0]["on_screen"] == "หัวข้อ"
    assert ctx.script_data["lines"][1]["sfx"] == "pop"
    assert ctx.script_data["lines"][2]["sfx"] == "cash"
