"""Actual Gadget approval -> HF Gallery/prepare/schedule publication readiness."""
from copy import deepcopy
import json

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from tests.test_channel_exports_posts import env
from tests.test_hyperframes_sources import create, render, finish
from scripts import api_hyperframes_workflow as hf
from scripts import api_gadget_media_projects as gadget_api
from scripts import api_tiktok_autopost as posting_api
from scripts import api_schedule_queue as queue_api
from scripts import api_exports as gallery_api
from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.export_registry import ExportRegistry
from scripts.gadget_media_campaign import CampaignStore, SourceRef, create_starter_campaign
from scripts.gadget_media_paths import GadgetMediaRoots
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.hyperframes_finalize import HyperFramesFinalizer
from scripts.hyperframes_publish_readiness import export_readiness
from scripts.hyperframes_render import HyperFramesRenderJobs
from scripts.posting_jobs import PostingJobStore
from scripts.schedule_store import ScheduleQueueStore


@pytest.fixture
def context(env, monkeypatch):
    root = env
    def runner(job, directory, entry, target):
        target.write_bytes(b"actual-review-registry-export")
    def thumbnail(video, output, duration):
        Image.new("RGB", (9, 16), "blue").save(output)
    jobs = HyperFramesRenderJobs(root, runner=runner,
        probe=lambda video: {"width": 1080, "height": 1920, "fps": 30, "duration": 1, "audio": False}, thumbnailer=thumbnail)
    service = hf.Workflow(root, renders=jobs)
    service.finalizer = HyperFramesFinalizer(root, jobs=jobs, projects=service.projects, sources=service.sources, registry=ExportRegistry)
    repository = GadgetMediaRepository(GadgetMediaRoots.under(root))
    monkeypatch.setattr(gadget_api, "PROJECT_REPOSITORY", repository)
    monkeypatch.setattr(gadget_api, "BASE_DIR", root)
    for key, value in {"BASE_DIR": root, "EXPORTS_DIR": root / "04_Exports/Ready_to_post",
                       "POSTED_DIR": root / "04_Exports/Posted", "COVERS_DIR": root / "05_Covers_Thumbnails"}.items():
        monkeypatch.setattr(posting_api, key, value)
    monkeypatch.setattr(posting_api, "_pending", None)
    scope = ChannelScope("main", source="header", strict=False, channel={"id": "main", "status": "active", "handle": "@rizanntry"})
    app = FastAPI()
    for router in (hf.router, gadget_api.router, posting_api.router, queue_api.router, gallery_api.router):
        app.include_router(router)
    app.dependency_overrides[hf.get_workflow] = lambda: service
    for dependency in {hf.get_workflow_scope, gadget_api.get_workflow_scope, posting_api.get_workflow_scope, queue_api.get_channel_scope}:
        app.dependency_overrides[dependency] = lambda: scope
    @app.exception_handler(ChannelError)
    async def channel_error(request, error):
        return JSONResponse(status_code=error.status_code, content={"code": error.code, "detail": str(error)})
    # Profile/account readiness has independent live-posting gate tests. This
    # suite specifically checks source-domain gating before any queue/job writes.
    monkeypatch.setattr(hf, "require_final_ready", lambda scope: scope)
    monkeypatch.setattr(posting_api, "_posting_ready", lambda scope: scope)
    return TestClient(app), service, ExportRegistry, scope


def candidate(context, *, slot=False, slot_ready=False):
    client, service, _, _ = context
    repo = service.sources.gadgets.for_channel("main")
    source = repo.create({"brand": "Exact", "model": "Real review"}, project_id="actual-reviewed-gadget")
    binding = {"type": "gadget_project", "project_id": source.project_id}
    if slot:
        campaign = create_starter_campaign(campaign_id="real-linked-campaign")
        campaign.channel_id = "main"
        campaign.slots[0].product_project_id = source.project_id
        if slot_ready:
            campaign.slots[0].status = "edited"
            campaign.slots[0].script = "Actual reviewed campaign script"
            campaign.slots[0].source_refs = [SourceRef(source_url="https://example.invalid/official-clean-source", rights_basis="self_recorded")]
        source.campaign_links = [{"campaign_id": campaign.campaign_id, "slot_id": campaign.slots[0].slot_id}]
        repo.save(source)
        CampaignStore(service.root / "_Docs/gadget_media_campaigns.json", channel_id="main").save(campaign)
        binding.update(source.campaign_links[0])
    project = create(client, binding)
    job = render(context, project)
    response = finish(context, job)
    assert response.status_code == 200, response.text
    project = service.projects.get(project["project_id"], "main")
    record = ExportRegistry.get(project["publish_package"]["export_id"], channel_id="main")
    assert record is not None
    artifact = repo.get(source.project_id).artifacts[0]
    return repo, source, project, record, artifact


def approve(context, source, artifact):
    response = context[0].post(f'/api/gadget-media/projects/{source.project_id}/renders/{artifact["artifact_id"]}/approve')
    assert response.status_code == 200, response.text
    assert response.json()["approved_master_id"] == artifact["artifact_id"]
    return response


def preparation(record):
    return {"export_id": record["id"], "video_path": record["path"], "caption": "Reviewed export"}


def schedule(record):
    return {**preparation(record), "scheduled_at": "2035-01-01T09:00:00+07:00"}


def test_unapproved_actual_gadget_candidate_cannot_prepare_or_schedule(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context)
    assert export_readiness(service.root, "main", record)["ready"] is False
    for route, body in (("/api/tiktok-autopost/prepare", preparation(record)), ("/api/schedule-queue", schedule(record))):
        response = client.post(route, json=body)
        assert response.status_code == 409 and response.json()["code"] == "hyperframes_source_review_required", response.text
    assert PostingJobStore(service.root).pending("main") is None
    assert ScheduleQueueStore.list_items(channel_id="main") == []
    assert repo.get(source.project_id).approved_master_id is None


def test_actual_existing_review_approval_enables_exact_export_prepare_and_schedule(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context)
    approve(context, source, artifact)
    assert export_readiness(service.root, "main", record)["ready"] is True
    prepared = client.post("/api/tiktok-autopost/prepare", json=preparation(record))
    assert prepared.status_code == 200, prepared.text
    pending = PostingJobStore(service.root).pending("main")
    assert pending["export_id"] == record["id"] and pending["product_id"] is None
    queued = client.post("/api/schedule-queue", json=schedule(record))
    assert queued.status_code == 200, queued.text
    records = ScheduleQueueStore.list_items(channel_id="main")
    assert len(records) == 1 and records[0]["export_id"] == record["id"]
    assert records[0]["project_name"] == record["project_name"]


def test_approval_of_other_master_does_not_authorize_hf_candidate(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context)
    other = repo.roots.export_dir(source.project_id) / "older.mp4"
    other.write_bytes(b"other-master")
    repo.add_render_artifact(source.project_id, {"artifact_id": "older-master", "kind": "render", "path": str(other), "approved": False})
    approve(context, source, {"artifact_id": "older-master"})
    assert export_readiness(service.root, "main", record)["ready"] is False
    response = client.post("/api/tiktok-autopost/prepare", json=preparation(record))
    assert response.status_code == 409 and PostingJobStore(service.root).pending("main") is None


def test_retargeted_real_campaign_slot_blocks_previously_approved_export(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context, slot=True)
    approve(context, source, artifact)
    campaigns = CampaignStore(service.root / "_Docs/gadget_media_campaigns.json", channel_id="main")
    campaign = campaigns.get(project["source_binding"]["campaign_id"])
    campaign.slots[0].product_project_id = "different-project"
    campaigns.save(campaign)
    for route, body in (("/api/tiktok-autopost/prepare", preparation(record)), ("/api/schedule-queue", schedule(record))):
        response = client.post(route, json=body)
        assert response.status_code == 409 and response.json()["code"] == "hyperframes_slot_changed", response.text
    assert PostingJobStore(service.root).pending("main") is None
    assert ScheduleQueueStore.list_items(channel_id="main") == []


def test_changed_approved_master_bytes_cannot_create_jobs(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context)
    approve(context, source, artifact)
    (service.root / artifact["path"]).write_bytes(b"changed-after-review")
    response = client.post("/api/tiktok-autopost/prepare", json=preparation(record))
    assert response.status_code == 409 and response.json()["code"] == "hyperframes_export_changed"
    assert PostingJobStore(service.root).pending("main") is None


def test_registered_export_cannot_retarget_approved_candidate_to_other_bytes(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context)
    approve(context, source, artifact)
    replacement = service.root / "04_Exports/Ready_to_post/main/different-unreviewed.mp4"
    replacement.write_bytes(b"other-unreviewed-video")
    ExportRegistry.update_path(record["id"], replacement, channel_id="main")
    record = ExportRegistry.get(record["id"], channel_id="main")
    for route, body in (("/api/tiktok-autopost/prepare", preparation(record)), ("/api/schedule-queue", schedule(record))):
        response = client.post(route, json=body)
        assert response.status_code == 409, response.text
    assert PostingJobStore(service.root).pending("main") is None
    assert ScheduleQueueStore.list_items(channel_id="main") == []


def test_actual_master_approval_does_not_bypass_campaign_slot_readiness(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context, slot=True)
    approve(context, source, artifact)
    readiness = export_readiness(service.root, "main", record)
    assert readiness["master_ready"] is True and readiness["slot_ready"] is False
    assert readiness["ready"] is False and "script is required before publish readiness" in readiness["slot_errors"]
    for route, body in (("/api/tiktok-autopost/prepare", preparation(record)), ("/api/schedule-queue", schedule(record))):
        response = client.post(route, json=body)
        assert response.status_code == 409 and response.json()["code"] == "hyperframes_source_review_required", response.text
    assert PostingJobStore(service.root).pending("main") is None
    assert ScheduleQueueStore.list_items(channel_id="main") == []


def test_actual_reviewed_campaign_slot_and_exact_master_allow_scheduling(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context, slot=True, slot_ready=True)
    approve(context, source, artifact)
    readiness = export_readiness(service.root, "main", record)
    assert readiness["master_ready"] is True and readiness["slot_ready"] is True and readiness["ready"] is True
    response = client.post("/api/schedule-queue", json=schedule(record))
    assert response.status_code == 200, response.text
    assert ScheduleQueueStore.list_items(channel_id="main")[0]["export_id"] == record["id"]


def test_gadget_gallery_has_real_review_status_without_product_link_prompt(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context)
    response = client.get("/api/exports")
    assert response.status_code == 200, response.text
    row = next(item for item in response.json()["exports"] if item["export_id"] == record["id"])
    assert row["source_review_required"] is True and row["source_review_ready"] is False
    assert row["is_unlinked"] is False and row["is_latest"] is True
    assert row["product_name"] == "Exact Real review"
    approve(context, source, artifact)
    row = next(item for item in client.get("/api/exports").json()["exports"] if item["export_id"] == record["id"])
    assert row["source_review_ready"] is True


def test_standalone_gallery_retains_frozen_title_after_next_brief_edit(context):
    client, service, _, _ = context
    project = create(client, {"type": "standalone"}, title="Original standalone release")
    assert finish(context, render(context, project)).status_code == 200
    project = service.projects.get(project["project_id"], "main")
    export_id = project["publish_package"]["export_id"]
    frozen = deepcopy(project["publish_package_refs"][0])
    response = client.patch(f'/api/hyperframes/projects/{project["project_id"]}', json={"expected_revision": project["revision"], "inputs": {**project["inputs"], "title": "Next unrelated brief title"}})
    assert response.status_code == 200
    assert response.json()["project"]["publish_package_refs"][0] == frozen
    row = next(item for item in client.get("/api/exports").json()["exports"] if item["export_id"] == export_id)
    assert row["product_name"] == "Original standalone release" and row["is_unlinked"] is False


def test_existing_queue_never_retargets_after_approved_master_changes(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context)
    approve(context, source, artifact)
    response = client.post("/api/schedule-queue", json=schedule(record))
    assert response.status_code == 200, response.text
    before = deepcopy(ScheduleQueueStore.list_items(channel_id="main")[0])
    different = repo.roots.export_dir(source.project_id) / "newer-master.mp4"
    different.write_bytes(b"new-reviewed-master")
    repo.add_render_artifact(source.project_id, {"artifact_id": "newer-master", "kind": "render", "path": str(different), "approved": False})
    approve(context, source, {"artifact_id": "newer-master"})
    response = client.post(f'/api/schedule-queue/{before["id"]}/prepare')
    assert response.status_code == 409 and response.json()["code"] == "hyperframes_source_review_required", response.text
    assert ScheduleQueueStore.list_items(channel_id="main")[0] == before
    assert PostingJobStore(service.root).pending("main") is None


def test_ready_campaign_slot_content_change_after_master_approval_blocks_prepare(context):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context, slot=True, slot_ready=True)
    approve(context, source, artifact)
    binding = project["source_binding"]
    store = CampaignStore(service.root / "_Docs/gadget_media_campaigns.json", channel_id="main")
    store.update_slot(binding["campaign_id"], binding["slot_id"], {"script": "A different ready script"})
    readiness = export_readiness(service.root, "main", record)
    assert readiness["master_ready"] is True and readiness["slot_ready"] is False
    assert any("content changed after the render snapshot" in error for error in readiness["slot_errors"])
    response = client.post("/api/tiktok-autopost/prepare", json=preparation(record))
    assert response.status_code == 409 and response.json()["code"] == "hyperframes_source_review_required"
    assert PostingJobStore(service.root).pending("main") is None
