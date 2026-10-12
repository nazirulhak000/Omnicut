"""Standalone/Gadget HTTP source contracts against real isolated repositories."""
from copy import deepcopy
import hashlib
import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from scripts import api_hyperframes_workflow as api
from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.gadget_media_campaign import CampaignStore, create_starter_campaign
from scripts.gadget_media_paths import GadgetMediaRoots
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.hyperframes_finalize import HyperFramesFinalizer
from scripts.hyperframes_render import HyperFramesRenderJobs
from scripts.hyperframes_sources import HyperFramesSources


class Registry:
    def __init__(self):
        self.rows = []

    def find_by_path(self, path, *, channel_id):
        return deepcopy(next((r for r in self.rows if r["path"] == path and r["channel_id"] == channel_id), None))

    def ensure_many(self, entries, *, channel_id, job_scope):
        result = []
        for entry in entries:
            row = self.find_by_path(entry["path"], channel_id=channel_id)
            if row is None:
                row = {**deepcopy(entry), "id": f"hf_export_{len(self.rows)}", "channel_id": channel_id}
                self.rows.append(row)
            result.append(row)
        return result


@pytest.fixture
def context(tmp_path, monkeypatch):
    def runner(job, directory, entry, target):
        target.write_bytes(b"source-adapter-qc-video")
    def thumbnail(video, output, duration):
        Image.new("RGB", (9, 16), "blue").save(output)
    jobs = HyperFramesRenderJobs(tmp_path, runner=runner,
        probe=lambda video: {"width": 1080, "height": 1920, "fps": 30, "duration": 1, "audio": False}, thumbnailer=thumbnail)
    registry = Registry()
    service = api.Workflow(tmp_path, renders=jobs)
    service.finalizer = HyperFramesFinalizer(tmp_path, jobs=jobs, projects=service.projects, sources=service.sources, registry=registry)
    scope = ChannelScope("main", source="header", strict=True, channel={"id": "main", "status": "active", "handle": "@rizanntry"})
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_workflow] = lambda: service
    app.dependency_overrides[api.get_workflow_scope] = lambda: scope
    @app.exception_handler(ChannelError)
    async def channel_error(request, error):
        return JSONResponse(status_code=error.status_code, content={"code": error.code, "detail": str(error)})
    monkeypatch.setattr(api, "require_final_ready", lambda scope: scope)
    return TestClient(app), service, registry, scope


def create(client, binding, **inputs):
    response = client.post("/api/hyperframes/projects", json={"source_binding": binding, "inputs": {
        "audio_mode": "silent", "duration_seconds": 1, "brief": "Clean offline source",
        "title": "Campaign title", "caption": "Original caption", "hashtags": ["#clean"],
        "style_profile": {"id": "tech", "version": 1, "tokens": {"background": "#111111"}}, **inputs}})
    assert response.status_code == 201, response.text
    return response.json()["project"]


def submit(context, project, *, document=None, media=None, expected_status=200):
    client, service, _, _ = context
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/authoring-jobs', json={"expected_revision": project["revision"]})
    assert response.status_code == 201, response.text
    job = response.json()["job"]
    claimed = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/claim', json={"executor_id": "hf-source-test", "expected_generation": 0}).json()["job"]
    fence = {"executor_id": "hf-source-test", "generation": claimed["generation"], "fence": claimed["fence"]}
    (service.root / job["work_path"] / "index.html").write_text(document or '<html><head></head><body><div data-composition-id="source" data-width="1080" data-height="1920" data-duration="1">Clean</div></body></html>', encoding="utf-8")
    for name, raw in (media or {}).items():
        (service.root / job["work_path"] / name).write_bytes(raw)
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/submit', json=fence)
    assert response.status_code == expected_status, response.text
    return response.json()["job"] if expected_status == 200 else response


def render(context, project):
    client = context[0]
    creative = submit(context, project)
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": project["revision"], "authoring_job_id": creative["id"]})
    assert response.status_code == 200, response.text
    project = response.json()["project"]
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/render-jobs', json={"expected_revision": project["revision"], "idempotency_key": "source-one"})
    assert response.status_code == 202, response.text
    response = client.get(f'/api/hyperframes/render-jobs/{response.json()["job"]["id"]}')
    assert response.json()["job"]["status"] == "qc_ready", response.text
    return response.json()["job"]


def finish(context, job):
    return context[0].post(f'/api/hyperframes/render-jobs/{job["id"]}/finalize', json={"expected_revision": job["revision"], "artifact_hash": job["artifact"]["sha256"], "publish_package": {}})


def gadget(context):
    service = context[1]
    repo = GadgetMediaRepository(GadgetMediaRoots.under(service.root), channel_id="main")
    project = repo.create({"brand": "Exact", "model": "Target"}, project_id="actual-gadget-project", editorial_promise="Actual saved hook")
    return repo, project, {"type": "gadget_project", "project_id": project.project_id}


def test_standalone_full_http_finalize_without_product_store(context):
    client, service, registry, _ = context
    project = create(client, {"type": "standalone"}, description="Independent source metadata")
    packet = service.source_packet("main", project)
    assert packet["product"]["metadata"]["description"] == "Independent source metadata"
    job = render(context, project)
    response = finish(context, job)
    assert response.status_code == 200, response.text
    package = service.projects.get(project["project_id"], "main")["publish_package"]
    assert package["caption"] == "Original caption" and package["hashtags"] == ["#clean"]
    assert package["source_title"] == "Campaign title" and package["source_hook"] == "Campaign title"
    assert package["source_binding"] == {"type": "standalone"}
    assert registry.rows[0]["product_id"] is None and registry.rows[0]["angle_id"] is None
    assert not (service.root / "_Docs/products.json").exists()
    assert service.products is None
    assert client.get(f'/api/hyperframes/render-jobs/{job["id"]}/artifact/video').content == b"source-adapter-qc-video"
    # Retrying the recorded human approval must reuse the same exact export.
    assert finish(context, job).status_code == 200
    assert len(registry.rows) == 1


def test_standalone_saved_metadata_revision_invalidates_submission(context):
    client, service, _, _ = context
    project = create(client, {"type": "standalone"})
    before = service.source_revision("main", project)
    creative = submit(context, project)
    response = client.patch(f'/api/hyperframes/projects/{project["project_id"]}', json={"expected_revision": 1, "inputs": {**project["inputs"], "title": "Changed saved title"}})
    assert response.status_code == 200
    assert before != service.source_revision("main", response.json()["project"])
    assert client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": 1, "authoring_job_id": creative["id"]}).status_code == 409


@pytest.mark.parametrize("inputs", [{"title": "x" * 201}, {"description": ["bad"]}, {"hashtags": [1]}, {"caption": "x" * 4001}])
def test_source_metadata_is_bounded_before_write(context, inputs):
    response = context[0].post("/api/hyperframes/projects", json={"source_binding": {"type": "standalone"}, "inputs": {"audio_mode": "silent", **inputs}})
    assert response.status_code == 422
    assert context[1].projects.list("main") == []


def test_gadget_finalize_materializes_review_candidate_then_real_domain_approval(context):
    client, service, registry, _ = context
    repo, source, binding = gadget(context)
    project = create(client, binding)
    packet = service.source_packet("main", project)
    assert packet["product"]["gadget"]["project_id"] == source.project_id
    job = render(context, project)
    response = finish(context, job)
    assert response.status_code == 200, response.text
    package = service.projects.get(project["project_id"], "main")["publish_package"]
    candidate = repo.get(source.project_id)
    assert candidate.status == "rendered" and candidate.approved_master_id is None
    assert len(candidate.artifacts) == 1 and candidate.artifacts[0]["approved"] is False
    assert candidate.artifacts[0]["export_id"] == registry.rows[0]["id"]
    assert package["source_review_required"] is True
    assert package["source_title"] == "Exact Target" and package["source_hook"] == "Actual saved hook"
    assert service.sources.review_status("main", binding, package["export_id"])["ready"] is False
    repo.approve_render(source.project_id, candidate.artifacts[0]["artifact_id"])
    assert service.sources.review_status("main", binding, package["export_id"])["ready"] is True
    assert registry.rows[0]["product_id"] is None and registry.rows[0]["angle_id"] is None
    assert finish(context, job).status_code == 200
    assert len(repo.get(source.project_id).artifacts) == 1
    assert json.loads((repo.roots.project_dir(source.project_id) / "project.json").read_text(encoding="utf-8"))["artifacts"][0]["export_id"] == package["export_id"]


def test_gadget_source_changed_after_render_blocks_finalize(context):
    _, service, registry, _ = context
    repo, source, binding = gadget(context)
    job = render(context, create(context[0], binding))
    repo.patch(source.project_id, {"editorial_promise": "Other saved facts"})
    response = finish(context, job)
    assert response.status_code == 409 and response.json()["code"] == "hyperframes_parent_changed"
    assert registry.rows == [] and repo.get(source.project_id).artifacts == []


def test_gadget_late_cas_failure_retains_export_and_does_not_attach(context):
    _, service, registry, _ = context
    repo, source, binding = gadget(context)
    job = render(context, create(context[0], binding))
    def late_change(phase):
        if phase == "manifest":
            repo.patch(source.project_id, {"audience": "New audience"})
    service.finalizer.fault_hook = late_change
    response = finish(context, job)
    assert response.status_code == 409
    assert len(registry.rows) == 1 and repo.get(source.project_id).artifacts == []
    assert service.renders.get("main", job["id"])["status"] == "recovery_required"


def test_gadget_foreign_channel_source_rejected_without_hf_write(context):
    _, service, _, _ = context
    repo = GadgetMediaRepository(GadgetMediaRoots.under(service.root), channel_id="second")
    source = repo.create({"brand": "Exact", "model": "Other"}, project_id="other-channel-gadget")
    response = context[0].post("/api/hyperframes/projects", json={"source_binding": {"type": "gadget_project", "project_id": source.project_id}, "inputs": {"audio_mode": "silent", "duration_seconds": 1, "style_profile": {"id": "tech", "version": 1, "tokens": {"background": "#111111"}}}})
    assert response.status_code == 404 and service.projects.list("main") == []


def test_gadget_slot_reads_actual_campaign_and_rejects_retarget(context):
    _, service, _, _ = context
    repo, source, binding = gadget(context)
    campaign = create_starter_campaign(campaign_id="actual-campaign")
    campaign.channel_id = "main"
    campaign.slots[0].product_project_id = source.project_id
    campaigns = CampaignStore(service.root / "_Docs/gadget_media_campaigns.json", channel_id="main")
    campaigns.save(campaign)
    source.campaign_links = [{"campaign_id": campaign.campaign_id, "slot_id": campaign.slots[0].slot_id}]
    repo.save(source)
    binding.update(campaign_id=campaign.campaign_id, slot_id=campaign.slots[0].slot_id)
    project = create(context[0], binding)
    assert service.source_packet("main", project)["product"]["gadget"]["slot"]["product_project_id"] == source.project_id
    campaign.slots[0].product_project_id = "other-project"
    campaigns.save(campaign)
    with pytest.raises(ChannelError, match="another project"):
        service.source_packet("main", project)


def test_gadget_review_validates_exact_master_bytes(context):
    _, service, _, _ = context
    repo, source, binding = gadget(context)
    job = render(context, create(context[0], binding))
    assert finish(context, job).status_code == 200
    candidate = repo.get(source.project_id).artifacts[0]
    repo.approve_render(source.project_id, candidate["artifact_id"])
    master = service.sources.approved_master("main", binding)
    assert master["artifact_id"] == candidate["artifact_id"] and master["approved"]
    (service.root / master["path"]).write_bytes(b"replaced unapproved media")
    with pytest.raises(ChannelError, match="bytes changed"):
        service.sources.review_status("main", binding, candidate["export_id"])


def test_gadget_new_candidate_preserves_existing_approved_master(context):
    _, service, _, _ = context
    repo, source, binding = gadget(context)
    master = repo.roots.export_dir(source.project_id) / "approved.mp4"
    master.parent.mkdir(parents=True, exist_ok=True)
    master.write_bytes(b"preserved-master")
    source.status = "rendered"
    source.artifacts = [{"artifact_id": "old-master", "kind": "render", "path": str(master), "approved": False}]
    repo.save(source)
    repo.approve_render(source.project_id, "old-master")
    job = render(context, create(context[0], binding))
    assert finish(context, job).status_code == 200
    saved = repo.get(source.project_id)
    assert saved.approved_master_id == "old-master" and saved.status == "approved"
    assert saved.artifacts[0]["approved"] is True and saved.artifacts[1]["approved"] is False
    assert service.sources.review_status("main", binding, saved.artifacts[1]["export_id"])["ready"] is False
    assert master.read_bytes() == b"preserved-master"


def test_gadget_partial_parent_commit_repair_is_idempotent(context):
    _, service, registry, _ = context
    repo, source, binding = gadget(context)
    job = render(context, create(context[0], binding))
    def interrupt(phase):
        if phase == "parent":
            raise OSError("Simulated post-attachment process interruption")
    service.finalizer.fault_hook = interrupt
    with pytest.raises(OSError, match="post-attachment"):
        finish(context, job)
    assert len(repo.get(source.project_id).artifacts) == 1
    service.finalizer.fault_hook = lambda phase: None
    assert service.finalizer.repair("main", job["id"])["status"] == "finalized"
    assert len(repo.get(source.project_id).artifacts) == 1 and len(registry.rows) == 1


def test_approved_master_rejects_foreign_channel_media(context):
    _, service, _, _ = context
    repo, source, binding = gadget(context)
    foreign = service.root / "04_Exports/Ready_to_post/second/master.mp4"
    foreign.parent.mkdir(parents=True)
    foreign.write_bytes(b"other-owner")
    source.status = "rendered"
    source.artifacts = [{"artifact_id": "foreign", "kind": "render", "path": str(foreign), "approved": False}]
    repo.save(source)
    repo.approve_render(source.project_id, "foreign")
    with pytest.raises(ChannelError, match="outside this Gadget"):
        service.sources.approved_master("main", binding)


def test_source_adapter_rejects_external_repository_root(context, tmp_path):
    from dataclasses import replace
    service = context[1]
    roots = replace(GadgetMediaRoots.under(service.root), docs=tmp_path.parent / "external-docs")
    with pytest.raises(ChannelError, match="share the workspace"):
        HyperFramesSources(service.root, gadget_repository=GadgetMediaRepository(roots))


def test_generic_client_input_cannot_supply_trusted_overlay_contract(context):
    client, service, _, _ = context
    project = create(client, {"type": "standalone"}, asset_contract={"approved_master_overlay": {"forged": True}})
    creative = submit(context, project)
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": 1, "authoring_job_id": creative["id"]})
    assert response.status_code == 200
    assert "asset_contract" not in response.json()["project"]["accepted_revision"]


@pytest.mark.parametrize("tamper", [False, True])
def test_server_overlay_contract_pins_exact_accepted_and_rendered_files(context, tamper):
    client, service, _, _ = context
    project = create(client, {"type": "standalone"})
    document = '<html><head></head><body><div data-composition-id="source" data-width="1080" data-height="1920" data-duration="1"><video src="master.mp4" muted data-start="0" data-duration="1"></video></div></body></html>'
    contract = {"approved_master_overlay": {"master_path": "master.mp4", "master_sha256": hashlib.sha256(b"frozen-master").hexdigest(), "composition_sha256": hashlib.sha256(document.encode()).hexdigest()}, "required_audio": []}
    project = service.projects.update(project["project_id"], "main", 1, {"overlay_contract": contract})
    with pytest.raises(api.HyperFramesProjectError, match="new overlay project"):
        service.projects.update(project["project_id"], "main", project["revision"], {"inputs": project["inputs"]})
    creative = submit(context, project, document=document, media={"master.mp4": b"frozen-master"})
    if tamper:
        changed = deepcopy(contract)
        changed["approved_master_overlay"]["composition_sha256"] = "0" * 64
        project = service.projects.update(project["project_id"], "main", project["revision"], {"overlay_contract": changed})
        # Exercise the hash guard directly while keeping the accepted base current.
        with service.creative.table.scoped_mutate("main") as rows:
            row = next(row for row in rows if row["id"] == creative["id"])
            row["base_revision"] = project["revision"]
            row["submitted_revision"]["base_revision"] = project["revision"]
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": project["revision"], "authoring_job_id": creative["id"]})
    if tamper:
        assert response.status_code == 409 and response.json()["code"] == "hyperframes_overlay_revision_changed"
        return
    assert response.status_code == 200, response.text
    project = response.json()["project"]
    assert project["accepted_revision"]["asset_contract"] == contract
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/render-jobs', json={"expected_revision": project["revision"], "idempotency_key": "overlay-contract"})
    assert response.status_code == 202, response.text
    assert service.renders.get("main", response.json()["job"]["id"])["asset_contract"] == contract


def test_external_authoring_cannot_replace_server_sealed_overlay(context):
    client, service, _, _ = context
    project = create(client, {"type": "standalone"})
    document = '<html><head></head><body><div data-composition-id="source" data-width="1080" data-height="1920" data-duration="1"><video src="master.mp4" muted></video></div></body></html>'
    contract = {"approved_master_overlay": {"master_path": "master.mp4", "master_sha256": hashlib.sha256(b"frozen-master").hexdigest(), "composition_sha256": hashlib.sha256(document.encode()).hexdigest()}, "required_audio": []}
    project = service.projects.update(project["project_id"], "main", 1, {"overlay_contract": contract})
    response = submit(context, project, document=document + "<!-- external replacement -->", media={"master.mp4": b"frozen-master"}, expected_status=409)
    assert response.json()["code"] == "hyperframes_overlay_revision_changed"
    assert service.projects.get(project["project_id"], "main")["accepted_revision"] is None


def test_custom_source_adapter_cannot_cross_workflow_or_project_root(context):
    service = context[1]
    foreign = HyperFramesSources(service.root / "another-workspace")
    with pytest.raises(ChannelError, match="share the workflow root"):
        api.Workflow(service.root, sources=foreign)
    with pytest.raises(api.HyperFramesProjectError, match="share the project root"):
        api.HyperFramesProjects(service.root, sources=foreign)
    with pytest.raises(ChannelError, match="share the finalize root"):
        HyperFramesFinalizer(service.root, sources=foreign)
    assert not (foreign.root / "03_Projects").exists()
