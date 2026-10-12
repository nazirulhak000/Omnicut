"""Stage seams keep source selection and opt-in corrections independent of audio mute."""

from copy import deepcopy

import pytest

from scripts import color_match, pipeline
from scripts.pipeline_context import PipelineContext
from scripts.stages import source_resolution, video_assembly_stage


@pytest.mark.parametrize("mute_clip", [False, True])
def test_color_matching_survives_clip_bus_mute(tmp_path, monkeypatch, mute_clip):
    clips = [
        {"id": "a", "source_path": str(tmp_path / "a.mp4"), "duration": 1.0, "volume": 0.7},
        {"id": "b", "source_path": str(tmp_path / "b.mp4"), "duration": 1.0, "volume": 0.4},
    ]
    original = deepcopy(clips)
    monkeypatch.setattr(color_match, "plan_color_match", lambda items: {"corrections": [{"id": "b"}]})
    monkeypatch.setattr(color_match, "apply_corrections", lambda items, corrections: [{**deepcopy(clip), "color_brightness": 0.1} for clip in items])
    monkeypatch.setattr(video_assembly_stage, "EXPORTS_DIR", tmp_path / "exports")
    saved = {}
    rendered = {}
    monkeypatch.setattr(video_assembly_stage.ProjectManifest, "save", lambda name, **kwargs: saved.update(kwargs))
    monkeypatch.setattr(video_assembly_stage.ExportRegistry, "ensure", lambda *args, **kwargs: {"id": "test-export"})
    monkeypatch.setattr(pipeline.VideoEditor, "assemble_tiktok_video", lambda **kwargs: rendered.update(kwargs))
    ctx = PipelineContext(
        product_name="Synthetic integration", raw_video_path=str(tmp_path / "a.mp4"),
        project_name="test", export_mp4=True,
        manifest={"render_params": {"enable_color_match": True}},
        audio_mutes={"clip": mute_clip}, total_duration=2.0,
    )
    ctx.actual_clip_list = clips
    ctx.transitions = [{"type": "fade", "duration": 0.2}]
    video_assembly_stage.VideoAssemblyStage.run(ctx)
    assert [clip["color_brightness"] for clip in rendered["clip_list"]] == [0.1, 0.1]
    assert [clip["volume"] for clip in rendered["clip_list"]] == ([0.0, 0.0] if mute_clip else [0.7, 0.4])
    assert clips == original
    expected = deepcopy(original)
    expected[1].update(transition_in="fade", transition_duration=0.2)
    assert saved["clip_list"] == expected
    assert rendered["clip_list"][1]["transition_in"] == saved["clip_list"][1]["transition_in"]
    assert saved["transitions"] == ctx.transitions
    assert not any(path.is_file() for path in (tmp_path / "exports").rglob('*')), "renderer and registry are mocked; no actual export"


@pytest.mark.parametrize("raw_path", [None, "missing.mp4"])
def test_missing_requested_source_does_not_take_unrelated_inbox_image(tmp_path, monkeypatch, raw_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "other-product.png").write_bytes(b"unrelated product")
    raw = tmp_path / "raw"
    raw.mkdir()
    projects = tmp_path / "projects"
    monkeypatch.setattr(source_resolution, "BASE_DIR", tmp_path)
    monkeypatch.setattr(source_resolution, "RAW_DIR", raw)
    monkeypatch.setattr(source_resolution, "INBOX_DIR", inbox)
    monkeypatch.setattr(source_resolution, "PROJECTS_DIR", projects)
    ctx = PipelineContext(product_name="Requested product", raw_video_path=raw_path)
    with pytest.raises(FileNotFoundError):
        source_resolution.SourceResolutionStage.run(ctx)
    assert not projects.exists()
    assert ctx.image_files == []
