"""Gadget rendering consumes the queued identity without adding captions or CTA."""
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi import BackgroundTasks

from scripts import api_gadget_media_projects as api, gadget_media_renderer as renderer, render_jobs
from scripts.channel_identity import project_channel_identity
from scripts.channel_store import MAIN_SEED
from scripts.channel_scope import ChannelScope
from scripts.export_registry import ExportRegistry
from scripts.gadget_media_paths import GadgetMediaRoots
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.gadget_media_timeline_adapter import GadgetMediaTimelineAdapter
from tests.test_channel_identity import profile
from tests.test_gadget_media_product_studio import _complete_project


def test_existing_unregistered_gadget_output_is_not_overwritten(monkeypatch, isolated_storage):
    repository = GadgetMediaRepository(GadgetMediaRoots.under(isolated_storage), channel_id="second")
    project = _complete_project("collision-project")
    project.channel_id = "second"
    repository.save(project)
    first, first_version = renderer._next_output(repository, project.project_id)
    first.write_bytes(b"prior render before registry failure")
    second, second_version = renderer._next_output(repository, project.project_id)
    assert second != first and second_version == first_version + 1
    second.write_bytes(b"next fixture result")
    assert first.read_bytes() == b"prior render before registry failure"


@pytest.mark.parametrize("owner", ["main", "second"])
def test_queued_gadget_renderer_uses_pinned_watermark_and_registry(owner, monkeypatch, isolated_storage):
    root = isolated_storage
    repository = GadgetMediaRepository(GadgetMediaRoots.under(root), channel_id=owner)
    project = _complete_project("identity-project-" + owner)
    project.channel_id = owner
    source = repository.roots.raw_dir(project.project_id) / "original/source.mp4"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake-video")
    project.source_assets[0]["local_path"] = str(source)
    project.status = "ready_to_render"
    project.quality_report = {"passed": True}
    repository.save(project)
    repository.save_timeline(project.project_id, GadgetMediaTimelineAdapter.build(project))
    monkeypatch.setattr(api, "PROJECT_REPOSITORY", repository)
    monkeypatch.setattr(api, "BASE_DIR", root)
    monkeypatch.setattr(api, "require_final_ready", lambda scope: scope)
    row = {**profile(root, owner), "status": "active"}
    if owner == "main":
        row = {**MAIN_SEED, "avatar_asset_path": row["avatar_asset_path"], "status": "active"}
    expected = project_channel_identity(row)
    scope = ChannelScope(owner, "header", False, channel=row)
    tasks = BackgroundTasks()
    result = api.start_project_render(project.project_id, api.RenderRequest(), tasks, scope)
    # A profile edit after queuing must not alter the ASS or export identity.
    row["watermark_text"] = "Changed live profile"
    row["display_name"] = "Changed live name"
    audio = repository.roots.project_layout(project.project_id)["mix"] / "fixture.wav"
    audio.write_bytes(b"offline audio")
    monkeypatch.setattr(renderer, "_prepare_audio", lambda *args: audio)
    observed = {}
    def assemble(**kwargs):
        observed.update(kwargs)
        Path(kwargs["output_mp4_path"]).write_bytes(b"offline video")
    monkeypatch.setattr(renderer.VideoEditor, "assemble_tiktok_video", assemble)
    callback = tasks.tasks[0]
    callback.func(*callback.args, **callback.kwargs)
    job = render_jobs.get_job(result["job_id"], channel_id=owner)
    assert job["status"] == "completed", job
    ass = Path(observed["ass_subtitle_path"]).read_text(encoding="utf-8")
    dialogues = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogues) == 1 and ",Watermark," in dialogues[0]
    assert expected["watermark_text"] in dialogues[0]
    assert "Changed live profile" not in ass
    assert observed["style_preset"] == "clean_tech_review"
    assert len(observed["clip_list"]) == 5
    exports = ExportRegistry.path_owners(observed["output_mp4_path"])
    assert exports and exports[0][1] == owner
    row = ExportRegistry.all(channel_id=owner)[0]
    assert row["channel_identity_snapshot"] == expected
    persisted = repository.get(project.project_id)
    assert persisted.artifacts[-1]["channel_identity_snapshot"] == expected
    preview = api.get_project_timeline(project.project_id, scope)
    assert preview["channel_id"] == owner
    assert preview["channel_identity_snapshot"] == expected

    # Probe the exact ASS handed to the real assembly seam through libass.
    # No caption/callout/CTA events are introduced; only the existing fixed
    # watermark region may change from Gadget's prior EMPTY_ASS output.
    frame = root / (owner + "-gadget-watermark.png")
    ass_path = Path(observed["ass_subtitle_path"])
    relative_ass = ass_path.relative_to(root).as_posix()
    from scripts import config
    font_directory = config.FONTS_DIR.as_posix().replace(":", "\\:")
    command = [shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=1",
               "-vf", f"subtitles='{relative_ass}':fontsdir='{font_directory}'",
               "-frames:v", "1", "-threads", "1", frame.name]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    from PIL import Image, ImageChops
    with Image.open(frame) as rendered:
        assert rendered.size == (1080, 1920)
        diff = ImageChops.difference(rendered.convert("RGB"), Image.new("RGB", rendered.size, "black"))
        assert diff.getbbox() is not None
        assert diff.crop((0, 0, 830, 1920)).getbbox() is None
