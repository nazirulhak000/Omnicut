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
