"""Scoped HTTP provider paths using real creative/project storage and fake transport."""
import asyncio
from copy import deepcopy
import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest

from scripts import api_hyperframes_ai as ai
from scripts import api_hyperframes_workflow as workflow
from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.hyperframes_ai_provider import recover_provider_work


HTML = '<html><head></head><body><div data-composition-id="main" data-width="1080" data-height="1920" data-duration="3"><section class="clip" data-start="0" data-duration="3">Saved standalone draft</section></div></body></html>'


@pytest.fixture
def context(tmp_path):
    service = workflow.Workflow(tmp_path)
    scope = ChannelScope("main", source="header", strict=True,
        channel={"id": "main", "status": "active", "handle": "@rizanntry"})
    provider = ai.get_provider(service)
    provider.key_getter = lambda: ["offline-test-key"]
    provider.injected_transport = True
    calls = []
    async def transport(**kwargs):
        calls.append(kwargs)
        return {"text": json.dumps({"files": [{"path": "index.html", "content": HTML}]}),
            "usage": {"prompt_token_count": 12, "total_token_count": 45}}
    provider.transport = transport
    app = FastAPI()
    app.include_router(workflow.router)
    app.include_router(ai.router)
    app.dependency_overrides[workflow.get_workflow] = lambda: service
    app.dependency_overrides[workflow.get_workflow_scope] = lambda: scope
    app.dependency_overrides[ai.get_workflow_scope] = lambda: scope
    @app.exception_handler(ChannelError)
    async def failure(request, error):
        return JSONResponse(status_code=error.status_code, content={"code": error.code, "detail": str(error)})
    with TestClient(app) as client:
        yield client, service, provider, scope, calls
    ai._providers.pop(str(tmp_path.resolve()), None)


def create(context):
    client, service, provider, scope, calls = context
    response = client.post("/api/hyperframes/projects", json={"source_binding": {"type": "standalone"},
        "inputs": {"audio_mode": "silent", "duration_seconds": 3, "brief": "Standalone",
        "publication_metadata": {"title": "Standalone title", "caption": "Saved caption"},
        "style_profile": {"id": "test", "version": 1, "tokens": {"color": "#FFFFFF"}}}})
    assert response.status_code == 201, response.text
    project = response.json()["project"]
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/authoring-jobs', json={"expected_revision": project["revision"]})
    assert response.status_code == 201, response.text
    return project, response.json()["job"]


def test_provider_cache_survives_new_workflow_factory(tmp_path):
    first = ai.get_provider(workflow.Workflow(tmp_path))
    second = ai.get_provider(workflow.Workflow(tmp_path))
    try:
        assert first is second
        assert first.jobs.root == tmp_path.resolve()
        assert not (tmp_path / "_Docs/store.db").exists()
    finally:
        ai._providers.pop(str(tmp_path.resolve()), None)


def test_http_generate_submit_requires_separate_human_accept(context):
    client, service, provider, scope, calls = context
    project, job = create(context)
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0})
    assert response.status_code == 200, response.text
    poll = client.get(f'/api/hyperframes/authoring-jobs/{job["id"]}')
    submitted = poll.json()["job"]
    assert submitted["status"] == "submitted"
    assert submitted["checkpoint"]["usage"]["total_token_count"] == 45
    saved = service.projects.get(project["project_id"], "main")
    assert not saved.get("accepted_revision")
    assert service.renders.list("main") == []
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision',
        json={"expected_revision": project["revision"], "authoring_job_id": job["id"]})
    assert response.status_code == 200, response.text
    assert response.json()["project"]["accepted_revision"]["id"] == submitted["submitted_revision"]["id"]
    assert len(calls) == 1


@pytest.mark.parametrize("injection", [{"channel_id": "second"}, {"status": "submitted"}, {"source_dir": "01_Raw"}, {"executor_id": "external"}])
def test_http_generation_rejects_owner_status_and_path_injection(context, injection):
    client, service, provider, scope, calls = context
    project, job = create(context)
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0, **injection})
    assert response.status_code == 422
    assert calls == []
    assert service.creative.get(job["id"], "main")["status"] == "queued"


def test_foreign_channel_cannot_begin_or_cancel(context):
    client, service, provider, scope, calls = context
    project, job = create(context)
    foreign = ChannelScope("second", source="header", strict=True, channel={"id": "second", "status": "active"})
    client.app.dependency_overrides[ai.get_workflow_scope] = lambda: foreign
    for suffix, payload in (("generate", {"expected_generation": 0}), ("generate/cancel", None)):
        response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/{suffix}', **({"json": payload} if payload else {}))
        assert response.status_code in {404, 409}, response.text
        assert response.json()["code"] == "job_not_found"
    assert calls == []


@pytest.mark.parametrize("status", ["draft", "archived"])
def test_inactive_channel_never_sends_provider_request(context, status):
    client, service, provider, scope, calls = context
    project, job = create(context)
    blocked = ChannelScope("main", source="header", strict=True, channel={"id": "main", "status": status})
    client.app.dependency_overrides[ai.get_workflow_scope] = lambda: blocked
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0})
    assert response.status_code == 409
    assert response.json()["code"] == "channel_not_active"
    assert calls == []


def test_http_cancel_invalidates_fence_and_stops_pending_generation(context):
    client, service, provider, scope, calls = context
    project, job = create(context)
    async def pending(**kwargs):
        calls.append(kwargs)
        await asyncio.sleep(100)
    provider.transport = pending
    started = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0})
    assert started.status_code == 200
    cancelled = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate/cancel')
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["job"]["status"] == "interrupted"
    assert cancelled.json()["job"]["generation"] > started.json()["job"]["generation"]
    assert provider.tasks == {}
    assert not (service.root / job["work_path"] / "index.html").exists()


def test_http_source_edit_before_start_blocks_paid_call(context):
    client, service, provider, scope, calls = context
    project, job = create(context)
    service.projects.update(project["project_id"], "main", project["revision"],
        {"inputs": project["inputs"] | {"brief": "Changed after job"}})
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0})
    assert response.status_code == 409
    assert response.json()["code"] == "stale_base_revision"
    assert calls == []


def test_http_provider_failure_remains_durable_and_unaccepted(context):
    client, service, provider, scope, calls = context
    project, job = create(context)
    async def failed(**kwargs):
        raise RuntimeError("never expose offline-test-key")
    provider.transport = failed
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0})
    assert response.status_code == 200
    poll = client.get(f'/api/hyperframes/authoring-jobs/{job["id"]}')
    assert poll.json()["job"]["status"] == "failed"
    assert "offline-test-key" not in poll.text
    assert not service.projects.get(project["project_id"], "main").get("accepted_revision")


def test_http_source_change_during_generation_blocks_submission(context):
    client, service, provider, scope, calls = context
    project, job = create(context)
    async def edited(**kwargs):
        service.projects.update(project["project_id"], "main", project["revision"],
            {"inputs": project["inputs"] | {"brief": "Changed while AI was working"}})
        return {"text": json.dumps({"files": [{"path": "index.html", "content": HTML}]})}
    provider.transport = edited
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0})
    assert response.status_code == 200
    poll = client.get(f'/api/hyperframes/authoring-jobs/{job["id"]}')
    assert poll.json()["job"]["status"] == "failed"
    assert poll.json()["job"]["checkpoint"]["error_code"] == "stale_base_revision"
    assert not (service.root / job["work_path"] / "index.html").exists()


def test_http_locked_overlay_never_calls_paid_provider(context):
    client, service, provider, scope, calls = context
    project, job = create(context)
    service.projects.update(project["project_id"], "main", project["revision"],
        {"overlay_contract": {"master_sha256": "approved-master", "composition_sha256": "sealed-builder"}})
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0})
    assert response.status_code == 409
    assert response.json()["code"] == "overlay_composition_locked"
    assert calls == []
    assert service.creative.get(job["id"], "main")["status"] == "queued"


def test_http_archived_channel_cannot_cancel_existing_provider_work(context):
    client, service, provider, scope, calls = context
    project, job = create(context)
    async def pending(**kwargs):
        await asyncio.sleep(100)
    provider.transport = pending
    started = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate', json={"expected_generation": 0})
    assert started.status_code == 200
    blocked = ChannelScope("main", source="header", strict=True, channel={"id": "main", "status": "archived"})
    client.app.dependency_overrides[ai.get_workflow_scope] = lambda: blocked
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate/cancel')
    assert response.status_code == 409
    assert response.json()["code"] == "channel_archived"
    client.app.dependency_overrides[ai.get_workflow_scope] = lambda: scope
    assert client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/generate/cancel').status_code == 200


def test_startup_provider_recovery_no_import_time_or_empty_workspace_writes(tmp_path):
    assert recover_provider_work(tmp_path) == {"interrupted": [], "errors": []}
    assert not (tmp_path / "_Docs").exists()


def test_startup_provider_recovery_preserves_external_executor_and_never_dispatches(tmp_path):
    from scripts.hyperframes_authoring import CreativeJobStore
    jobs = CreativeJobStore(tmp_path)
    external = jobs.create("main", "p", 1, {})
    jobs.claim(external["id"], "main", "external-session", 0)
    internal = jobs.create("main", "p", 1, {})
    claim = jobs.claim(internal["id"], "main", "in_app_gemini_dead", 0)
    jobs.checkpoint(internal["id"], "main", **{key: claim[key] for key in ("executor_id", "generation", "fence")},
        checkpoint={"next_action": "Generating", "executor_pid": 123456, "executor_creation": "dead"})
    report = recover_provider_work(tmp_path, alive=lambda row: False)
    assert report == {"interrupted": [internal["id"]], "errors": []}
    assert jobs.get(external["id"], "main")["status"] == "authoring"
    assert jobs.get(internal["id"], "main")["status"] == "interrupted"
