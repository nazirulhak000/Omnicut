"""Exported clip bus mute must match the Preview mix without changing saved sliders."""

from pathlib import Path
from unittest.mock import patch

from scripts.pipeline_context import PipelineContext
from scripts.stages.video_assembly_stage import VideoAssemblyStage


def test_clip_track_mute_reaches_render_but_preserves_saved_clip_volume(tmp_path):
    clip = {"source_path": str(tmp_path / "source.mp4"), "trim_start": 0.0,
            "trim_end": 1.0, "duration": 1.0, "volume": 0.65}
    ctx = PipelineContext(
        product_name="Track Mix Test",
        raw_video_path=str(tmp_path / "source.mp4"),
        project_name="track-mix-test",
        export_mp4=True,
        total_duration=1.0,
        raw_video=Path(tmp_path / "source.mp4"),
        mixed_audio_path=Path(tmp_path / "mix.wav"),
        ass_sub_path=Path(tmp_path / "subtitles.ass"),
        audio_mutes={"clip": True},
    )
    ctx.actual_clip_list = [clip]

    with patch("scripts.pipeline.VideoEditor.assemble_tiktok_video") as assemble, patch(
        "scripts.stages.video_assembly_stage.EXPORTS_DIR", tmp_path
    ), patch("scripts.stages.video_assembly_stage.ExportRegistry.ensure", return_value={"id": "test"}), patch(
        "scripts.stages.video_assembly_stage.ProjectManifest.save"
    ) as save:
        VideoAssemblyStage.run(ctx)

    assert assemble.call_args.kwargs["clip_list"][0]["volume"] == 0.0
    assert ctx.actual_clip_list[0]["volume"] == 0.65
    assert save.call_args.kwargs["clip_list"][0]["volume"] == 0.65
