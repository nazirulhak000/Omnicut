"""A completed status must mean the last project write has already settled."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_phase1, api_render, project_manifest, render_jobs
from scripts.project_manifest import ProjectManifest


@pytest.fixture
def completion_client(tmp_path, monkeypatch):
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(api_phase1, "_project_origin", lambda name: (None, None, None))
    app = FastAPI()
    app.include_router(api_render.router)
    app.include_router(api_phase1.router)
    with TestClient(app) as client:
        yield client


def test_completed_status_waits_for_final_manifest_write(completion_client, monkeypatch):
    client = completion_client
    ProjectManifest.save("completion", clip_list=[])
    job = render_jobs.create_job("completion-job")
    job.update(status="rendering", progress=0.95)
    entered, release = Event(), Event()
    finalize = render_jobs.finalize_incremental_render

    def delayed_finalize(name):
        entered.set()
        if not release.wait(timeout=10):
            raise RuntimeError("test did not release finalizer")
        return finalize(name)

    monkeypatch.setattr(render_jobs, "finalize_incremental_render", delayed_finalize)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(render_jobs.complete_job, "completion-job", {"project_name": "completion"})
        try:
            assert entered.wait(timeout=10)
            status = client.get("/api/render/status/completion-job").json()
            assert status["status"] == "rendering"
            assert status["result"] is None
            assert status["progress"] < 1.0
        finally:
            release.set()
        future.result(timeout=10)

    status = client.get("/api/render/status/completion-job").json()
    assert status["status"] == "completed"
    assert status["result"]["project_name"] == "completion"
    assert status["incremental_render"]["schema_version"] == 1
    # A single read AFTER completed must contain the final revision and permit
    # the next editor save, with no timing assumption or repeated-read workaround.
    manifest = client.get("/api/projects/completion").json()
    revision = manifest["_editor_revision"]
    assert client.get("/api/projects/completion").json()["_editor_revision"] == revision
    response = client.patch("/api/projects/completion/state", json={
        "base_revision": revision, "hook_label": "saved after completed",
    })
    assert response.status_code == 200
    assert ProjectManifest.load("completion")["hook_label"] == "saved after completed"


def test_metadata_failure_still_publishes_successful_video(completion_client, monkeypatch):
    job = render_jobs.create_job("metadata-failure")
    job["status"] = "rendering"

    def fail_metadata(_):
        raise OSError("metadata unavailable")

    monkeypatch.setattr(render_jobs, "finalize_incremental_render", fail_metadata)
    render_jobs.complete_job("metadata-failure", {
        "project_name": "completion", "duration": 3.0,
        "mix_degraded": True, "mix_degraded_reason": "BGM unavailable",
    })
    status = completion_client.get("/api/render/status/metadata-failure").json()
    assert status["status"] == "completed"
    assert status["progress"] == 1.0
    assert status["result"]["duration"] == 3.0
    assert status["result"]["mix_degraded"] is True
    assert "metadata unavailable" in status["logs"][-1]["msg"]
