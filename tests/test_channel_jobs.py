"""Pinned job scope and worker ownership using isolated stores; no media engines."""
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient

from scripts import api_render, api_tasks, api_batch_render, render_jobs
from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.channel_workflows import capture_job_scope, get_workflow_scope
from scripts.task_manager import TaskManager, TaskStatus
from scripts.batch_render import BatchRenderManager
from scripts.pipeline_context import PipelineContext, channel_project_name
from scripts.api_schemas import RenderRequest


def scope(channel_id="second", source="header", status="active"):
    return ChannelScope(channel_id, source, False, channel={
        "id": channel_id, "status": status, "revision": 4,
        "identity_hash": "old", "display_name": "Pinned",
        "avatar": {"path": "fixture.png"},
    })


def request(**kwargs):
    return RenderRequest(product_name="Fixture", raw_video_path="01_Raw/raw.mp4",
                         key_features="fixture", pain_point="fixture", price_deal="fixture",
                         export_mp4=False, **kwargs)


def test_task_scope_snapshot_and_filtered_mutations():
    current = scope()
    pinned = capture_job_scope(current)
    created = TaskManager.create_task("render_video", "second", task_id="second-job", job_scope=pinned)
    TaskManager.create_task("render_video", "main", task_id="main-job", channel_id="main")
    pinned["channel_identity_snapshot"]["display_name"] = "mutated"
    created["channel_identity_snapshot"]["display_name"] = "mutated"
    assert TaskManager.get_task("second-job", channel_id="second")["channel_identity_snapshot"]["display_name"] == "Pinned"
    assert TaskManager.get_task("second-job", channel_id="main") is None
    assert TaskManager.cancel_task("second-job", channel_id="main") is None
    assert TaskManager.delete_task("second-job", channel_id="main") is False
    assert [t["id"] for t in TaskManager.get_active_tasks(channel_id="main")] == ["main-job"]
    TaskManager.complete_task("second-job", channel_id="second")
    assert TaskManager.clear_completed(channel_id="main") == 0
    assert TaskManager.get_task("second-job", channel_id="second")["status"] == TaskStatus.COMPLETED


def test_render_scope_callbacks_and_cancel_do_not_cross_channels():
    pinned = capture_job_scope(scope())
    render_jobs.create_job("second", job_scope=pinned)
    pinned["channel_identity_snapshot"]["display_name"] = "changed"
    assert render_jobs.get_job("second", channel_id="main") is None
    render_jobs.progress_reporter("second", channel_id="main")("wrong", 0.5)
    assert render_jobs.get_job("second", channel_id="second")["progress"] == 0
    assert render_jobs.request_cancel("second", channel_id="main") is False
    assert not render_jobs.get_cancel_event("second", channel_id="second").is_set()
    assert render_jobs.get_job("second")["channel_identity_snapshot"]["display_name"] == "Pinned"
    assert render_jobs.request_cancel("second", channel_id="second") is True


def test_explicit_job_id_collision_never_replaces_foreign_owner():
    render_jobs.create_job("collision", channel_id="second")
    TaskManager.create_task("render_video", "foreign", task_id="collision", channel_id="second")
    with pytest.raises(ChannelError):
        render_jobs.create_job("collision", channel_id="main")
    with pytest.raises(ChannelError):
        TaskManager.create_task("render_video", "replacement", task_id="collision", channel_id="main")
    assert render_jobs.get_job("collision")["channel_id"] == "second"
    assert TaskManager.get_task("collision")["title"] == "foreign"


@pytest.mark.parametrize("kwargs", [
    {"channel_id": "Main"},
    {"channel_id": "main", "job_scope": {"channel_id": "second"}},
    {"channel_id": "main", "job_scope": {"channel_identity_snapshot": {"id": "second"}}},
    {"channel_id": "main", "job_scope": {"status": "completed"}},
    {"channel_id": "main", "job_scope": {"channel_identity_snapshot": "malformed"}},
])
def test_job_capture_rejects_invalid_or_conflicting_owner(kwargs):
    with pytest.raises(ChannelError):
        render_jobs.create_job("bad", **kwargs)
    assert "bad" not in render_jobs.ACTIVE_JOBS


def test_http_implicit_main_task_and_render_visibility():
    TaskManager.create_task("render_video", "foreign", task_id="foreign", channel_id="second")
    render_jobs.create_job("foreign", channel_id="second")
    app = FastAPI()
    app.include_router(api_tasks.router)
    app.include_router(api_render.router)
    app.dependency_overrides[get_workflow_scope] = lambda: scope("main", "default")
    with TestClient(app) as client:
        assert client.get("/api/tasks/active").json()["tasks"] == []
        assert client.get("/api/tasks/foreign").status_code == 404
        assert client.get("/api/render/status/foreign").status_code == 404
        assert client.post("/api/tasks/foreign/cancel").status_code == 404
    assert not render_jobs.get_cancel_event("foreign", channel_id="second").is_set()


def test_batch_api_missing_product_is_404(monkeypatch):
    from scripts.api_server import app
    from scripts.product_store import ProductStore
    monkeypatch.setattr(ProductStore, "get", lambda *args, **kw: None)
    with TestClient(app) as client:
        response = client.post("/api/render/batch", json={"product_id": "missing", "export_mp4": False})
    assert response.status_code == 404, response.text


def test_render_enqueue_captures_identity_and_worker_options(monkeypatch):
    current = scope()
    monkeypatch.setattr(api_render, "check_disk_space", lambda *_: {"is_sufficient": True})
    tasks = BackgroundTasks()
    result = api_render.trigger_render(request(project_name="film"), tasks, current)
    current.channel["identity_hash"] = "new"
    current.channel["display_name"] = "New"
    job = render_jobs.get_job(result["job_id"], channel_id="second")
    assert job["channel_identity_hash"] == "old"
    callback = tasks.tasks[0]
    assert callback.args[1].project_name == "second/film"
    assert callback.args[2]["channel_identity_snapshot"]["display_name"] == "Pinned"
    observed = {}
    monkeypatch.setattr(api_render.TikTokAutoCutterPipeline, "run", lambda **kw: observed.update(kw) or {})
    api_render.execute_render_job(*callback.args)
    assert observed["channel_id"] == "second"
    assert observed["job_scope"]["channel_identity_hash"] == "old"
    assert TaskManager.get_task(result["job_id"], channel_id="main") is None


def test_batch_persisted_scope_survives_memory_reset_and_filtered_cancel(monkeypatch):
    from scripts.product_store import ProductStore
    current = scope()
    product = {"id": "owned", "channel_id": "second", "name": "Fixture",
               "angles": [{"angle_id": "a", "script_lines": ["fixture"]}]}
    monkeypatch.setattr(ProductStore, "get", lambda pid, **kw: deepcopy(product) if kw.get("channel_id") == "second" else None)
    monkeypatch.setattr(BatchRenderManager, "_ensure_dispatcher", lambda: None)
    import scripts.batch_render as batch_module
    monkeypatch.setattr(batch_module, "check_disk_space", lambda *_: {"is_sufficient": True})
    created = BatchRenderManager.create_batch("owned", job_scope=capture_job_scope(current))
    batch_module.BATCH_REGISTRY.clear()
    current.channel["display_name"] = "changed"
    assert BatchRenderManager.get_batch(created["batch_id"], channel_id="main") is None
    restored = BatchRenderManager.get_batch(created["batch_id"], channel_id="second")
    assert restored["job_scope"]["channel_identity_snapshot"]["display_name"] == "Pinned"
    restored["job_scope"]["channel_identity_snapshot"]["display_name"] = "caller mutation"
    assert BatchRenderManager.get_batch(created["batch_id"], channel_id="second")["job_scope"]["channel_identity_snapshot"]["display_name"] == "Pinned"
    assert not BatchRenderManager.cancel_batch(created["batch_id"], channel_id="main")
    assert BatchRenderManager.cancel_batch(created["batch_id"], channel_id="second")


@pytest.mark.parametrize("name", ["../film", "second/../film", "/film", "third/film", "film\\..\\escape"])
def test_secondary_project_namespace_rejects_escape(name):
    with pytest.raises(ChannelError):
        channel_project_name(name, "second")


def test_pipeline_context_keeps_pinned_identity_and_namespace():
    pinned = capture_job_scope(scope())
    ctx = PipelineContext(product_name="fixture", raw_video_path=None, job_scope=pinned)
    pinned["channel_identity_snapshot"]["display_name"] = "changed"
    assert ctx.channel_identity_snapshot["display_name"] == "Pinned"
    assert ctx.store_kwargs() == {"channel_id": "second"}
    assert channel_project_name("film", ctx.channel_id) == "second/film"
    assert channel_project_name("film", "main") == "film"
    with pytest.raises(ChannelError):
        PipelineContext(product_name="fixture", raw_video_path=None, job_scope=ctx.job_scope,
                        channel_identity_snapshot={"id": "second", "identity_hash": "new"})


def test_source_guard_rejects_foreign_clip_before_project_writes(isolated_storage):
    import scripts.stages.source_resolution as source
    from scripts.project_manifest import ProjectManifest
    root = isolated_storage
    raw = root / "01_Raw" / "raw.mp4"
    raw.write_bytes(b"x" * 2048)
    private = ProjectManifest.dir_for("other-film")
    private.mkdir(parents=True)
    (private / "project.json").write_text('{"channel_id":"main"}', encoding="utf-8")
    clip = private / "voice.wav"
    clip.write_bytes(b"x" * 2048)
    ctx = PipelineContext(product_name="fixture", raw_video_path=str(raw),
                          project_name="film", job_scope=capture_job_scope(scope()),
                          clip_list=[{"source_path": str(clip)}])
    with pytest.raises(ChannelError):
        source.SourceResolutionStage.run(ctx)
    assert not ProjectManifest.dir_for("second/film").exists()


def test_guided_take_metadata_owner_is_separate_from_shared_raw(isolated_storage):
    import json
    from scripts.stages.source_resolution import SourceResolutionStage
    root = isolated_storage
    raw = root / "01_Raw" / "shared.mp4"
    raw.write_bytes(b"x" * 2048)
    raw.with_name(raw.name + ".guided_take.json").write_text(json.dumps({
        "channel_id": "main", "session_id": "foreign", "clip_map": [],
    }), encoding="utf-8")
    ctx = PipelineContext(product_name="fixture", raw_video_path=str(raw), project_name="film",
                          job_scope=capture_job_scope(scope()))
    with pytest.raises(ChannelError):
        SourceResolutionStage.run(ctx)
    from scripts.project_manifest import ProjectManifest
    assert not ProjectManifest.dir_for("second/film").exists()


def test_batch_worker_uses_persisted_channel_for_every_store_operation(monkeypatch, isolated_storage):
    import scripts.batch_render as batch
    from scripts.product_store import ProductStore
    raw = isolated_storage / "01_Raw" / "raw.mp4"
    raw.write_bytes(b"x" * 2048)
    product = {"id": "owned", "channel_id": "second", "name": "Fixture",
               "angles": [{"angle_id": "a", "selected_videos": [str(raw)], "script_lines": ["fixture"]}]}
    calls = []
    def get(pid, **kw):
        calls.append(("get", kw))
        assert kw == {"channel_id": "second"}
        return deepcopy(product)
    def update(*args, **kw):
        calls.append(("write", kw))
        assert kw["channel_id"] == "second"
    monkeypatch.setattr(ProductStore, "get", get)
    monkeypatch.setattr(ProductStore, "update_angle_status", update)
    monkeypatch.setattr(ProductStore, "attach_project", update)
    monkeypatch.setattr(batch, "check_disk_space", lambda *_: {"is_sufficient": True})
    monkeypatch.setattr(BatchRenderManager, "_ensure_dispatcher", lambda: None)
    observed = []
    monkeypatch.setattr(batch.TikTokAutoCutterPipeline, "run", lambda **kw: observed.append(kw) or {"project_name": kw["project_name"]})
    created = BatchRenderManager.create_batch("owned", options={"export_mp4": False}, job_scope=capture_job_scope(scope()))
    batch.BATCH_REGISTRY.clear()
    BatchRenderManager._run_batch_worker(created["batch_id"])
    assert observed[0]["channel_id"] == "second"
    assert observed[0]["project_name"].startswith("second/")
    assert observed[0]["job_scope"]["channel_identity_hash"] == "old"
    assert TaskManager.get_task(created["batch_id"], channel_id="second")["status"] == TaskStatus.COMPLETED
    assert calls and all(kw.get("channel_id") == "second" for _, kw in calls)


def test_export_collision_preserves_bytes_and_persists_pinned_provenance(monkeypatch, isolated_storage):
    import datetime
    from types import SimpleNamespace
    from scripts.stages import video_assembly_stage as assembly
    from scripts import pipeline
    from scripts.export_registry import ExportRegistry
    from scripts.project_manifest import ProjectManifest
    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            return cls(2026, 10, 10, 12, 0, 0)
    monkeypatch.setattr(assembly, "datetime", SimpleNamespace(datetime=Frozen))
    prior = assembly.EXPORTS_DIR / "second" / "film_20261010_120000.mp4"
    prior.parent.mkdir(parents=True, exist_ok=True)
    prior.write_bytes(b"old identity export")
    observed = []
    def assemble(**kwargs):
        target = Path(kwargs["output_mp4_path"])
        observed.append(target)
        assert target != prior
        target.write_bytes(b"offline fixture export")
    monkeypatch.setattr(pipeline.VideoEditor, "assemble_tiktok_video", assemble)
    ctx = PipelineContext(product_name="fixture", raw_video_path=None,
                          project_name="second/film", job_scope=capture_job_scope(scope()))
    assembly.VideoAssemblyStage.run(ctx)
    assert prior.read_bytes() == b"old identity export"
    assert observed[0].name == "film_20261010_120000_v2.mp4"
    record = ExportRegistry.get(ctx.result_paths["export_id"], channel_id="second")
    assert record["channel_identity_hash"] == "old"
    manifest = ProjectManifest.load("second/film")
    assert manifest["channel_identity_snapshot"]["display_name"] == "Pinned"
    assert manifest["render_interrupted"] is False
