"""Default cover after render: offline and in temp storage. Only the last test runs ffmpeg and Pillow."""
import os
import shutil
import subprocess
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from scripts import api_covers
from scripts import api_phase1
from scripts import api_render
from scripts import auto_cover
from scripts import batch_render
from scripts import product_store as ps
from scripts import render_jobs
from scripts.channel_scope import ChannelError
from scripts.db import DocumentTable
from scripts.export_cover_bindings import ExportCoverBindingStore
from scripts.export_registry import ExportRegistry

CHANNEL = "main"
EXPORT_ID = "export_clip"


@pytest.fixture
def studio(isolated_storage, monkeypatch):
    """One registered export, one product angle, and a renderer that only writes bytes."""
    root = isolated_storage
    monkeypatch.delenv(auto_cover.ENV_SWITCH, raising=False)
    video = root / "04_Exports" / CHANNEL / "20261112_clip_hook_v1.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"rendered clip")
    docs = root / "_Docs"
    DocumentTable("export_registry", lambda: docs / "store.db", lambda: docs / "export_registry.json").save(
        [{"id": EXPORT_ID, "channel_id": CHANNEL, "path": video.relative_to(root).as_posix()}])
    product = ps.ProductStore.add(
        name="Auto Cover Product",
        angles=[{"angle_id": "a1", "project_name": "clip_project", "status": "rendered"}],
    )

    calls = []

    def fake_render(**kwargs):
        out = kwargs["output_dir"]
        out.mkdir(parents=True, exist_ok=True)
        primary, profile = out / "clip_cover.jpg", out / "clip_cover_3x4.jpg"
        primary.write_bytes(b"9x16 " + out.name.encode())
        profile.write_bytes(b"3x4 " + out.name.encode())
        calls.append(kwargs)
        return primary, profile

    monkeypatch.setattr(api_covers, "render_pro_cover", fake_render)
    monkeypatch.setattr(api_covers, "recommended_cover_timestamp", lambda path: 2.5)

    class Studio:
        pass

    s = Studio()
    s.root, s.video, s.product_id, s.calls = root, video, product["id"], calls
    s.bindings = ExportCoverBindingStore(root)
    s.angle = lambda: ps.ProductStore.get(product["id"], channel_id=CHANNEL)["angles"][0]
    s.run = lambda **kw: auto_cover.ensure_default_cover(
        EXPORT_ID, channel_id=CHANNEL, product_id=product["id"], angle_id="a1", **kw)
    return s


def _manual_cover(studio, name="manual.jpg"):
    cover = studio.root / "05_Covers_Thumbnails" / CHANNEL / "picked" / name
    cover.parent.mkdir(parents=True, exist_ok=True)
    cover.write_bytes(b"a person chose this")
    return cover


def test_render_without_cover_gets_clean_cover_in_both_sizes(studio):
    outcome = studio.run()

    assert outcome["status"] == "created" and outcome["bound"] and outcome["angle_updated"]
    assert outcome["at_seconds"] == 2.5
    (call,) = studio.calls
    assert call["aspect_ratio"] == "both"
    assert call["enable_hook_text"] is False and call["enable_badge"] is False
    assert call["at_seconds"] == 2.5
    assert "scene" not in call and "hook_text" not in call

    angle = studio.angle()
    assert angle["cover_source"] == "auto"
    assert angle["cover_path"] == angle["cover_9x16_path"] == outcome["cover_path"]
    assert angle["cover_3x4_path"] == outcome["cover_3x4_path"]
    assert outcome["cover_path"].startswith(f"05_Covers_Thumbnails/{CHANNEL}/")
    assert studio.bindings.source_of(CHANNEL, EXPORT_ID) == "auto"
    assert studio.bindings.get(CHANNEL, EXPORT_ID)["path"] == outcome["cover_path"]
    assert studio.bindings.get(CHANNEL, EXPORT_ID, format="3:4")["path"] == outcome["cover_3x4_path"]


def test_frame_falls_back_when_no_recommendation(studio, monkeypatch):
    monkeypatch.setattr(api_covers, "recommended_cover_timestamp", lambda path: None)
    assert studio.run()["at_seconds"] == auto_cover.FALLBACK_SECONDS
    assert studio.calls[0]["at_seconds"] == auto_cover.FALLBACK_SECONDS


def test_cover_a_person_bound_to_the_export_is_kept(studio):
    cover = _manual_cover(studio)
    studio.bindings.save(CHANNEL, EXPORT_ID, str(studio.video), {"9:16": cover})

    assert studio.run() == {"status": "kept", "reason": "manual_cover"}
    assert studio.calls == []
    assert studio.bindings.get(CHANNEL, EXPORT_ID)["path"] == cover.relative_to(studio.root).as_posix()


def test_cover_a_person_saved_on_the_angle_is_kept(studio):
    cover = _manual_cover(studio)
    ps.ProductStore.update_angle_cover(studio.product_id, "a1", cover_path=str(cover), channel_id=CHANNEL)

    assert studio.run() == {"status": "kept", "reason": "manual_cover"}
    assert studio.calls == []
    assert "cover_source" not in studio.angle()
    assert studio.bindings.source_of(CHANNEL, EXPORT_ID) is None


def test_automatic_cover_is_reused_until_the_video_is_newer(studio):
    first = studio.run()
    again = studio.run()
    assert again == {"status": "kept", "reason": "auto_cover_current", "cover_path": first["cover_path"]}
    assert len(studio.calls) == 1

    newer = (studio.root / first["cover_path"]).stat().st_mtime + 60
    os.utime(studio.video, (newer, newer))
    second = studio.run()

    assert second["status"] == "created" and second["cover_path"] != first["cover_path"]
    assert len(studio.calls) == 2
    assert studio.angle()["cover_path"] == second["cover_path"]
    assert studio.angle()["cover_source"] == "auto"
    assert studio.bindings.get(CHANNEL, EXPORT_ID)["path"] == second["cover_path"]
    # Superseded automatic covers are left for the owner to clear.
    assert (studio.root / first["cover_path"]).is_file()


def test_person_saving_a_cover_after_an_automatic_one_takes_over(studio):
    studio.run()
    cover = _manual_cover(studio)
    studio.bindings.save(CHANNEL, EXPORT_ID, str(studio.video), {"9:16": cover})
    ps.ProductStore.update_angle_cover(studio.product_id, "a1", cover_path=str(cover),
                                       cover_9x16_path=str(cover), channel_id=CHANNEL)

    assert studio.bindings.source_of(CHANNEL, EXPORT_ID) == "manual"
    assert "cover_source" not in studio.angle()
    newer = cover.stat().st_mtime + 60
    os.utime(studio.video, (newer, newer))
    assert studio.run() == {"status": "kept", "reason": "manual_cover"}
    assert len(studio.calls) == 1


def test_switch_off_and_unknown_export_do_nothing(studio, monkeypatch):
    assert auto_cover.ensure_default_cover("export_unknown", channel_id=CHANNEL) == {
        "status": "skipped", "reason": "export_not_found"}
    assert auto_cover.ensure_default_cover(None) == {"status": "skipped", "reason": "no_export_id"}
    studio.video.unlink()
    assert studio.run() == {"status": "skipped", "reason": "video_missing"}
    monkeypatch.setenv(auto_cover.ENV_SWITCH, "0")
    assert studio.run() == {"status": "skipped", "reason": "disabled"}
    assert studio.calls == []


def test_renderer_failure_is_reported_not_raised(studio, monkeypatch):
    def broken(**kwargs):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(api_covers, "render_pro_cover", broken)
    outcome = studio.run()

    assert outcome["status"] == "failed" and "ffmpeg exploded" in outcome["reason"]
    assert not any(studio.angle().get(key) for key in ("cover_path", "cover_9x16_path", "cover_3x4_path"))
    assert studio.bindings.source_of(CHANNEL, EXPORT_ID) is None


def test_export_without_a_product_angle_still_gets_a_bound_cover(studio):
    outcome = auto_cover.ensure_default_cover(EXPORT_ID, channel_id=CHANNEL)
    assert outcome["status"] == "created" and outcome["bound"] and not outcome["angle_updated"]
    assert not studio.angle().get("cover_path")


def test_binding_store_never_lets_auto_replace_a_person(studio):
    cover = _manual_cover(studio)
    other = _manual_cover(studio, "other.jpg")
    store = studio.bindings
    assert store.source_of(CHANNEL, EXPORT_ID) is None
    store.save(CHANNEL, EXPORT_ID, str(studio.video), {"9:16": cover})
    with pytest.raises(ChannelError) as refused:
        store.save(CHANNEL, EXPORT_ID, str(studio.video), {"9:16": other}, source="auto")
    assert refused.value.code == "export_cover_manual_selection"
    assert store.get(CHANNEL, EXPORT_ID)["path"] == cover.relative_to(studio.root).as_posix()
    with pytest.raises(ChannelError):
        store.save(CHANNEL, EXPORT_ID, str(studio.video), {"9:16": other}, source="robot")


def test_binding_store_person_save_of_same_file_clears_auto_mark(studio):
    cover = _manual_cover(studio)
    store = studio.bindings
    auto = store.save(CHANNEL, EXPORT_ID, str(studio.video), {"9:16": cover}, source="auto")
    assert auto["source"] == "auto"
    assert store.save(CHANNEL, EXPORT_ID, str(studio.video), {"9:16": cover}, source="auto") == auto
    kept = store.save(CHANNEL, EXPORT_ID, str(studio.video), {"9:16": cover})
    assert "source" not in kept and kept["revision"] == auto["revision"] + 1
    assert store.source_of(CHANNEL, EXPORT_ID) == "manual"


def test_angle_cover_source_rules(studio):
    manual = _manual_cover(studio)
    generated = _manual_cover(studio, "generated.jpg")
    update = ps.ProductStore.update_angle_cover

    update(studio.product_id, "a1", cover_path=str(generated), channel_id=CHANNEL, cover_source="auto")
    assert studio.angle()["cover_source"] == "auto"

    # status updates that carry a cover come from a person
    ps.ProductStore.update_angle_status(studio.product_id, "a1", "rendered",
                                        cover_path=str(manual), channel_id=CHANNEL)
    assert "cover_source" not in studio.angle()

    update(studio.product_id, "a1", cover_path=str(generated), cover_9x16_path=str(generated),
           channel_id=CHANNEL, cover_source="auto")
    angle = studio.angle()
    assert "cover_source" not in angle
    assert angle["cover_path"].endswith("manual.jpg")

    with pytest.raises(ValueError):
        update(studio.product_id, "a1", cover_path=str(manual), channel_id=CHANNEL, cover_source="robot")


# --- the three places a render completes -----------------------------------

@pytest.fixture
def cover_requests(monkeypatch):
    """Record what each render completion site asks ``ensure_default_cover`` for."""
    seen = []

    def record(export_id, **kwargs):
        seen.append((export_id, kwargs))
        return {"status": "created"}

    for module in (api_render, api_phase1, batch_render):
        monkeypatch.setattr(module, "ensure_default_cover", record)
        # The sharpness step that runs first has its own tests (test_auto_sharpen).
        monkeypatch.setattr(module, "ensure_tiktok_sharp", lambda *args, **kwargs: {"status": "skipped"})
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    return seen


def _first_render(monkeypatch, product_id, *, result, export_mp4=True):
    monkeypatch.setattr(api_render.TaskManager, "fail_task", Mock())
    monkeypatch.setattr(api_render.TaskManager, "complete_task", Mock())
    monkeypatch.setattr(api_render, "check_disk_space", lambda *_args: {"is_sufficient": True})
    monkeypatch.setattr(api_render.TikTokAutoCutterPipeline, "run", Mock(return_value=result))
    job_id = "auto-cover-first-render"
    render_jobs.create_job(job_id)
    api_render.execute_render_job(job_id, api_render.RenderRequest(
        product_name="Auto Cover Product", raw_video_path="source.mp4", project_name="clip_project",
        product_id=product_id, angle_id="a1", export_mp4=export_mp4,
        key_features="offline", pain_point="offline", price_deal="offline",
    ))
    return render_jobs.get_job(job_id)


def test_first_render_asks_for_a_default_cover(studio, cover_requests, monkeypatch):
    job = _first_render(monkeypatch, studio.product_id, result={
        "mp4": studio.video.relative_to(studio.root).as_posix(),
        "project_name": "clip_project", "export_id": EXPORT_ID})

    assert job["status"] == "completed"
    ((export_id, kwargs),) = cover_requests
    assert export_id == EXPORT_ID
    assert kwargs["product_id"] == studio.product_id and kwargs["angle_id"] == "a1"


def test_draft_only_first_render_asks_for_no_cover(studio, cover_requests, monkeypatch):
    job = _first_render(monkeypatch, studio.product_id, export_mp4=False,
                        result={"mp4": "", "project_name": "clip_project", "export_id": ""})

    assert job["status"] == "completed"
    assert cover_requests == []


def _editor_render(monkeypatch, studio, *, mp4):
    from scripts import pipeline as pipeline_mod
    from scripts.project_manifest import ProjectManifest

    ProjectManifest.save(
        "clip_project", script_data={"lines": [{"text": "a"}]}, cues=[], micro_cues=[], total_duration=5.0,
        render_params={"raw_video_path": "source.mp4", "product_id": studio.product_id, "angle_id": "a1"},
        artifacts={"mp4_video": {"path": mp4}} if mp4 else {},
    )
    result = {"mp4_video": mp4, "project_name": "clip_project", "clip_list": [],
              "export_id": EXPORT_ID if mp4 else ""}
    monkeypatch.setattr(pipeline_mod.TikTokAutoCutterPipeline, "run", classmethod(lambda cls, **kw: result))
    job_id = "auto-cover-editor-render"
    render_jobs.create_job(job_id)
    api_phase1._execute_reroll(job_id, "clip_project", "video", {})
    return render_jobs.get_job(job_id)


def test_editor_render_asks_for_a_default_cover(studio, cover_requests, monkeypatch):
    job = _editor_render(monkeypatch, studio, mp4=studio.video.relative_to(studio.root).as_posix())

    assert job["status"] == "completed"
    ((export_id, kwargs),) = cover_requests
    assert export_id == EXPORT_ID
    assert kwargs["product_id"] == studio.product_id and kwargs["angle_id"] == "a1"
    assert kwargs["channel_id"] == CHANNEL


def test_editor_render_without_output_asks_for_no_cover(studio, cover_requests, monkeypatch):
    _editor_render(monkeypatch, studio, mp4="")
    assert cover_requests == []


def _batch_render(monkeypatch, studio, tmp_path, *, export_mp4):
    from scripts import batch_queue_store
    from scripts.task_manager import TaskManager

    monkeypatch.setattr(batch_queue_store, "BATCH_QUEUE_PATH", tmp_path / "batch_render_queue.json")
    for name in ("update_progress", "complete_task", "fail_task", "cancel_task"):
        monkeypatch.setattr(TaskManager, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(TaskManager, "create_task", lambda **kwargs: kwargs)
    monkeypatch.setattr(batch_render.BatchRenderManager, "_ensure_dispatcher", lambda: None)
    batch_render.BATCH_REGISTRY.clear()
    clip = tmp_path / "raw.mp4"
    clip.write_text("clip")
    product = {"id": "prod_auto_cover", "title": "Auto Cover Product", "angles": [{
        "angle_id": "a1", "angle_name": "รีวิวสเปก", "status": "scripted",
        "selected_video": str(clip), "script_lines": ["a"]}]}
    result = {"mp4": studio.video.relative_to(studio.root).as_posix() if export_mp4 else "",
              "project_name": "clip_project", "export_id": EXPORT_ID if export_mp4 else ""}

    try:
        with patch.object(ps.ProductStore, "get", return_value=product), \
             patch.object(ps.ProductStore, "update_angle_status"), \
             patch("scripts.pipeline.TikTokAutoCutterPipeline.run", return_value=result):
            batch = batch_render.BatchRenderManager.create_batch(
                product_id="prod_auto_cover", angle_ids=["a1"], options={"export_mp4": export_mp4})
            batch_render.BatchRenderManager._run_batch_worker(batch["batch_id"])
    finally:
        batch_render.BATCH_REGISTRY.clear()


@pytest.mark.parametrize("export_mp4, expected", [(True, [EXPORT_ID]), (False, [])])
def test_batch_render_asks_for_a_default_cover_only_for_rendered_clips(
        studio, cover_requests, monkeypatch, tmp_path, export_mp4, expected):
    _batch_render(monkeypatch, studio, tmp_path, export_mp4=export_mp4)

    assert [export_id for export_id, _ in cover_requests] == expected
    for _, kwargs in cover_requests:
        assert kwargs["product_id"] == "prod_auto_cover" and kwargs["angle_id"] == "a1"


# --- the real renderer, end to end -----------------------------------------

def test_real_frame_becomes_a_bound_cover_in_both_sizes(isolated_storage):
    """No mocks: a real clip, the real frame picker and the real cover renderer."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg is not installed")
    root = isolated_storage
    video = root / "04_Exports" / CHANNEL / "20261112_real_hook_v1.mp4"
    video.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:d=3:r=30",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(video),
    ], check=True, capture_output=True)
    product = ps.ProductStore.add(
        name="Real Cover Product",
        angles=[{"angle_id": "a1", "project_name": "real_project", "status": "rendered"}],
    )
    # The same registration call the assembly stage makes once the clip exists.
    export_id = ExportRegistry.ensure(
        str(video), product_id=product["id"], angle_id="a1", project_name="real_project",
        status="rendered", channel_id=CHANNEL)["id"]

    outcome = auto_cover.ensure_default_cover(
        export_id, channel_id=CHANNEL, product_id=product["id"], angle_id="a1")

    assert outcome["status"] == "created" and outcome["bound"] and outcome["angle_updated"], outcome
    assert 0.0 <= outcome["at_seconds"] <= 3.0
    covers = root / "05_Covers_Thumbnails" / CHANNEL
    primary, profile = root / outcome["cover_path"], root / outcome["cover_3x4_path"]
    assert covers in primary.parents and covers in profile.parents
    with Image.open(primary) as image:
        assert image.size == (api_covers.COVER_W, api_covers.COVER_H)
        assert len(set(image.resize((16, 16)).get_flattened_data())) > 4  # a picture, not a flat fill
    with Image.open(profile) as image:
        assert image.size == (api_covers.PROFILE_W, api_covers.PROFILE_H)
    angle = ps.ProductStore.get(product["id"], channel_id=CHANNEL)["angles"][0]
    assert angle["cover_source"] == "auto" and angle["cover_path"] == outcome["cover_path"]
    store = ExportCoverBindingStore(root)
    assert store.source_of(CHANNEL, export_id) == "auto"
    assert store.get(CHANNEL, export_id, format="3:4")["path"] == outcome["cover_3x4_path"]
    # The cover step wrote nothing next to the clip.
    assert [path.name for path in video.parent.iterdir()] == [video.name]
