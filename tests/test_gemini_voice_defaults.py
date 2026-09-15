"""Regression coverage for the Gemini TTS default contract."""

import ast
import inspect
from pathlib import Path

from scripts.api_batch_render import BatchRenderRequest
from scripts.api_schemas import RenderRequest
from scripts.pipeline import TikTokAutoCutterPipeline
from scripts.pipeline_context import PipelineContext
from scripts.stages.voice_stage import VoiceStage


ROOT = Path(__file__).resolve().parents[1]


def test_voice_defaults_are_gemini_at_public_entry_points():
    assert PipelineContext(product_name="test", raw_video_path="input.mp4").voice_engine_type == "gemini_tts"
    assert inspect.signature(TikTokAutoCutterPipeline.run).parameters[
        "voice_engine_type"
    ].default == "gemini_tts"
    assert RenderRequest.model_fields["voice_mode"].default == "gemini_tts"
    assert BatchRenderRequest.model_fields["voice_mode"].default == "gemini_tts"


def test_legacy_edge_request_remains_explicit_in_batch_mapping():
    source = (ROOT / "scripts" / "batch_render.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    # The batch worker must preserve an explicit Edge-TTS request while
    # treating omitted/unknown modes as Gemini TTS.
    assert '"edge_tts" if options.get("voice_mode") == "edge_tts" else "gemini_tts"' in source
    assert tree is not None


def test_voice_stage_normalizes_blank_engine_to_gemini(tmp_path, capsys):
    ctx = PipelineContext(
        product_name="test",
        raw_video_path="input.mp4",
        project_name="test_project",
        voice_engine_type="",
    )
    ctx.manifest = {"cues": [], "total_duration": 0.0, "render_params": {}}
    reused_audio = tmp_path / "voice.wav"
    reused_audio.write_bytes(b"RIFF")
    ctx.should_run = lambda _stage: False
    ctx.reuse = lambda _key, _label: reused_audio

    VoiceStage.run(ctx)

    assert ctx.voice_engine_type == "gemini_tts"
    assert ctx.voice_engine_used == "gemini_tts"
    assert "ใช้ Gemini TTS" in capsys.readouterr().out


def test_voice_stage_warns_for_explicit_edge_without_reclassifying_it(tmp_path, capsys):
    ctx = PipelineContext(
        product_name="test",
        raw_video_path="input.mp4",
        project_name="test_project",
        voice_engine_type="edge_tts",
    )
    ctx.manifest = {"cues": [], "total_duration": 0.0, "render_params": {}}
    reused_audio = tmp_path / "voice.wav"
    reused_audio.write_bytes(b"RIFF")
    ctx.should_run = lambda _stage: False
    ctx.reuse = lambda _key, _label: reused_audio

    VoiceStage.run(ctx)

    assert ctx.voice_engine_type == "edge_tts"
    assert "จะไม่ใช้เป็น fallback" in capsys.readouterr().out
