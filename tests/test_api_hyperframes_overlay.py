"""Real HTTP/domain overlay integration; scoped storage and no provider calls."""
from copy import deepcopy
from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from scripts import api_hyperframes_overlay as overlay_api
from scripts import api_hyperframes_workflow as workflow_api
from scripts.channel_artifacts import register
from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.gadget_media_paths import GadgetMediaRoots
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.hyperframes_overlay import HyperFramesOverlay, _sha
from scripts.hyperframes_render import HyperFramesRenderJobs


@pytest.fixture
def context(isolated_storage, monkeypatch):
    root = isolated_storage
    specs = {"width": 1080, "height": 1920, "fps": 30, "duration": 1, "audio": True}
    captured = []
    def runner(job, directory, entry, target):
        captured.append(deepcopy(job))
        target.write_bytes(b"new-overlay-review-candidate")
    def thumbnail(video, output, duration):
        Image.new("RGB", (9, 16), "blue").save(output, "WEBP")
    renders = HyperFramesRenderJobs(root, runner=runner, probe=lambda p: specs.copy(), thumbnailer=thumbnail)
    service = workflow_api.Workflow(root, renders=renders)
    repo = GadgetMediaRepository(GadgetMediaRoots.under(root), channel_id="main")
    project = repo.create({"brand": "Exact", "model": "Target"}, project_id="overlay-approved-master", editorial_promise="Original approved script")
    master = repo.roots.export_dir(project.project_id) / "approved.mp4"
    master.parent.mkdir(parents=True, exist_ok=True)
    master.write_bytes(b"approved-original-video-and-audio")
    register(master.relative_to(root), "main")
    project.status = "rendered"
    project.artifacts = [{"artifact_id": "approved_original", "kind": "render", "path": str(master), "approved": False, "sha256": _sha(master)}]
    repo.save(project)
    repo.approve_render(project.project_id, "approved_original")
    scope = ChannelScope("main", source="header", strict=True, channel={"id": "main", "status": "active", "handle": "@rizanntry"})
    app = FastAPI()
    app.include_router(workflow_api.router)
    app.include_router(overlay_api.router)
    app.dependency_overrides[workflow_api.get_workflow] = lambda: service
    app.dependency_overrides[workflow_api.get_workflow_scope] = lambda: scope
    @app.exception_handler(ChannelError)
    async def channel_error(request, error):
        return JSONResponse(status_code=error.status_code, content=error.to_body())
    monkeypatch.setattr(overlay_api, "overlay_for", lambda service: HyperFramesOverlay(service.root, resolver=service.sources.approved_master, probe=lambda p: specs.copy()))
    monkeypatch.setattr(workflow_api, "require_final_ready", lambda scope: scope)
    return TestClient(app), service, repo, project, scope, master, captured


def request(context, *, shared=False):
    client, service, repo, source, scope, master, captured = context
    binding = {"type": "gadget_project", "project_id": source.project_id}
    response = client.post("/api/hyperframes/overlay/inspect", json={"source_binding": binding})
    assert response.status_code == 200, response.text
    inspected = response.json()["master"]
    relative = "02_Assets/overlay-image.png" if shared else "03_Projects/main/overlay-image.png"
    image = service.root / relative
    image.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), "red").save(image)
    return {"source_binding": binding, "approval": {"approved": True, "master_digest": inspected["master_digest"]},
            "inputs": {"title": "New overlay review", "brief": "Preserve approved master", "caption": "Same original content", "style_profile": {"id": "locked-master", "version": 1, "tokens": {"background": "#000000"}}},
            "layers": [{"path": relative, "sha256": _sha(image), "x": 48, "y": 48, "width": 100, "height": 100, "start": .2, "duration": .4}]}


def create(context, payload=None):
    response = context[0].post("/api/hyperframes/overlay/projects", json=payload or request(context))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("shared", [False, True])
def test_http_overlay_requires_human_accept_and_pins_master_until_review(context, shared):
    client, service, repo, source, scope, master, captured = context
    original = master.read_bytes()
    result = create(context, request(context, shared=shared))
    project, creative = result["project"], result["job"]
    assert creative["status"] == "submitted" and project["accepted_revision"] is None
    assert service.renders.list("main") == []
    assert project["inputs"]["audio_mode"] == "music_only"
    assert project["inputs"]["music_path"] == result["master"]["frozen_path"]
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/render-jobs', json={"expected_revision": project["revision"], "idempotency_key": "premature"})
    assert response.status_code == 409
    accepted = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": project["revision"], "authoring_job_id": creative["id"]})
    assert accepted.status_code == 200, accepted.text
    project = accepted.json()["project"]
    contract = project["accepted_revision"]["asset_contract"]
    assert contract == project["overlay_contract"]
    assert contract["approved_master_overlay"]["master_sha256"] == _sha(master)
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/render-jobs', json={"expected_revision": project["revision"], "idempotency_key": "approved-overlay"})
    assert response.status_code == 202, response.text
    job = client.get(f'/api/hyperframes/render-jobs/{response.json()["job"]["id"]}').json()["job"]
    assert job["status"] == "qc_ready" and captured[0]["asset_contract"] == contract
    finalized = client.post(f'/api/hyperframes/render-jobs/{job["id"]}/finalize', json={"expected_revision": job["revision"], "artifact_hash": job["artifact"]["sha256"], "publish_package": {}})
    assert finalized.status_code == 200, finalized.text
    saved = repo.get(source.project_id)
    assert saved.approved_master_id == "approved_original" and saved.status == "approved"
    assert len(saved.artifacts) == 2 and saved.artifacts[-1]["approved"] is False
    assert master.read_bytes() == original


@pytest.mark.parametrize("approval", [{}, {"approved": False}, {"approved": True, "master_digest": "stale"}])
def test_no_approval_creates_no_hf_project_or_creative_job(context, approval):
    client, service, *_ = context
    payload = request(context)
    payload["approval"] = approval
    response = client.post("/api/hyperframes/overlay/projects", json=payload)
    assert response.status_code == 409
    assert service.projects.list("main") == [] and service.creative.list("main") == []


def test_foreign_channel_cannot_inspect_or_create_master(context):
    client, service, repo, source, scope, *_ = context
    payload = request(context)
    foreign_scope = ChannelScope("second", source="header", strict=True, channel={"id": "second", "status": "active", "handle": "@rizannntry"})
    client.app.dependency_overrides[workflow_api.get_workflow_scope] = lambda: foreign_scope
    for endpoint, body in (("inspect", {"source_binding": payload["source_binding"]}), ("projects", payload)):
        response = client.post(f"/api/hyperframes/overlay/{endpoint}", json=body)
        assert response.status_code == 404, response.text
    assert service.projects.list("second") == []


def test_master_changed_after_inspection_never_reuses_old_approval(context):
    client, service, repo, source, scope, master, *_ = context
    payload = request(context)
    master.write_bytes(b"changed-master")
    response = client.post("/api/hyperframes/overlay/projects", json=payload)
    assert response.status_code == 409, response.text
    assert service.projects.list("main") == []


@pytest.mark.parametrize("change", ["unsafe_geometry", "wrong_hash", "script", "foreign_path", "traversal"])
def test_invalid_visual_layer_never_creates_authoring_or_render_job(context, change):
    client, service, *_ = context
    payload = request(context)
    layer = payload["layers"][0]
    if change == "unsafe_geometry":
        layer["x"] = 1000
    elif change == "wrong_hash":
        layer["sha256"] = "0" * 64
    elif change == "script":
        layer["script"] = "replace-master"
    elif change == "foreign_path":
        layer["path"] = "03_Projects/second/foreign.png"
    else:
        layer["path"] = "../outside.png"
    response = client.post("/api/hyperframes/overlay/projects", json=payload)
    assert response.status_code in {404, 409, 422}, response.text
    assert service.creative.list("main") == [] and service.renders.list("main") == []
    assert service.projects.list("main") == []


def test_overlay_inputs_cannot_be_edited_to_retime_or_mute_master(context):
    client, service, *_ = context
    result = create(context)
    project = result["project"]
    response = client.patch(f'/api/hyperframes/projects/{project["project_id"]}', json={"expected_revision": project["revision"], "inputs": {**project["inputs"], "audio_mode": "silent", "music_path": None, "duration_seconds": .5}})
    assert response.status_code == 409, response.text
    assert service.projects.get(project["project_id"], "main")["inputs"] == project["inputs"]


def test_overlay_image_symlink_cannot_escape_hash_scope(context):
    client, service, *_ = context
    payload = request(context)
    original = service.root / payload["layers"][0]["path"]
    linked = original.with_name("linked.png")
    try:
        linked.symlink_to(original)
    except OSError:
        pytest.skip("Host cannot create test symlinks")
    payload["layers"][0]["path"] = linked.relative_to(service.root).as_posix()
    response = client.post("/api/hyperframes/overlay/projects", json=payload)
    assert response.status_code == 422, response.text
    assert service.creative.list("main") == []


def test_missing_overlay_image_is_a_controlled_domain_error(context):
    client, service, *_ = context
    payload = request(context)
    (service.root / payload["layers"][0]["path"]).unlink()
    response = client.post("/api/hyperframes/overlay/projects", json=payload)
    assert response.status_code in {404, 422}, response.text
    assert service.creative.list("main") == []
    assert service.projects.list("main") == []


def test_submitted_overlay_cannot_replace_master_before_human_accept(context):
    client, service, *_ = context
    result = create(context)
    project, creative = result["project"], result["job"]
    reference = creative["submitted_revision"]
    directory = Path(reference["revision_dir"])
    (directory / "master.mp4").write_bytes(b"substituted-unapproved-master")
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": project["revision"], "authoring_job_id": creative["id"]})
    assert response.status_code in {409, 422}, response.text
    assert service.renders.list("main") == []


def test_late_master_revision_race_preserves_blocked_project_for_recovery(context, monkeypatch):
    client, service, repo, source, scope, master, _ = context
    payload = request(context)
    original = master.read_bytes()
    actual_create = service.projects.create
    def race_after_create(*args, **kwargs):
        project = actual_create(*args, **kwargs)
        changed = repo.get(source.project_id)
        changed.editorial_promise = "Concurrent editorial change after explicit approval"
        repo.save(changed)
        return project
    monkeypatch.setattr(service.projects, "create", race_after_create)
    response = client.post("/api/hyperframes/overlay/projects", json=payload)
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "overlay_approval_required" and body["recovery_status"] == "blocked"
    project = service.projects.get(body["project_id"], "main")
    assert project["status"] == "blocked" and project["readiness"]["errors"] == [body["code"]]
    assert service.creative.list("main") == []
    assert master.read_bytes() == original


def test_work_copy_never_overwrites_hardlinked_foreign_file_and_cancels_own_job(context, monkeypatch):
    client, service, repo, source, scope, master, _ = context
    payload = request(context)
    foreign = service.root / "03_Projects/second/foreign-master.mp4"
    foreign.parent.mkdir(parents=True)
    foreign.write_bytes(b"preserve-foreign-channel-file")
    actual_claim = service.creative.claim
    def inject_alias(*args, **kwargs):
        claimed = actual_claim(*args, **kwargs)
        os.link(foreign, service.root / claimed["work_path"] / "master.mp4")
        return claimed
    monkeypatch.setattr(service.creative, "claim", inject_alias)
    response = client.post("/api/hyperframes/overlay/projects", json=payload)
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "overlay_work_conflict" and body["recovery_status"] == "blocked"
    project = service.projects.get(body["project_id"], "main")
    assert project["status"] == "blocked"
    creative = service.creative.get(body["authoring_job_id"], "main")
    assert creative["status"] == "cancelled" and creative["fence"] is None and creative["lease_expires_at"] == 0
    assert foreign.read_bytes() == b"preserve-foreign-channel-file"
    assert master.read_bytes() == b"approved-original-video-and-audio"
    assert list(service.root.glob("03_Projects/main/HF_*/overlay_inputs/*/master.mp4"))
    assert list(service.root.glob("03_Projects/main/HF_*/overlay_compositions/*/index.html"))


def test_failed_overlay_cannot_cancel_a_reclaimed_executor_fence(context, monkeypatch):
    client, service, repo, source, scope, master, _ = context
    payload = request(context)
    actual_claim = service.creative.claim
    def superseded_claim(*args, **kwargs):
        claimed = actual_claim(*args, **kwargs)
        foreign = service.root / "03_Projects/second/reclaimed-file.mp4"
        foreign.parent.mkdir(parents=True)
        foreign.write_bytes(b"other-executor-output")
        os.link(foreign, service.root / claimed["work_path"] / "master.mp4")
        with service.creative.table.scoped_mutate("main") as rows:
            row = next(item for item in rows if item["id"] == claimed["id"])
            row.update(generation=claimed["generation"] + 1, executor_id="reclaimed_other_executor", fence="new-fence")
        return claimed
    monkeypatch.setattr(service.creative, "claim", superseded_claim)
    response = client.post("/api/hyperframes/overlay/projects", json=payload)
    assert response.status_code == 409, response.text
    body = response.json()
    assert service.projects.get(body["project_id"], "main")["status"] == "blocked"
    creative = service.creative.get(body["authoring_job_id"], "main")
    assert creative["status"] == "authoring" and creative["executor_id"] == "reclaimed_other_executor"
    assert creative["fence"] == "new-fence" and creative["lease_expires_at"] > 0
