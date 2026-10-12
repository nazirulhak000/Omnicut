"""HTTP-to-domain workflow tests; every write stays inside pytest storage."""
from copy import deepcopy
import hashlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from PIL import Image
import pytest

from scripts import api_hyperframes_workflow as api
from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.hyperframes_finalize import HyperFramesFinalizer, _fingerprint
from scripts.hyperframes_render import HyperFramesRenderJobs


class Products:
    def __init__(self):
        self.product = {"id": "p", "channel_id": "main", "angles": [{"id": "a", "status": "scripted"}]}

    def get(self, product_id, *, channel_id):
        return deepcopy(self.product) if product_id == "p" and channel_id == "main" else None

    def compare_and_set_angle(self, channel, product_id, angle_id, fingerprint, fields):
        angle = self.product["angles"][0]
        if angle.get("export_id") == fields["export_id"]:
            return True
        if _fingerprint(angle) != fingerprint:
            return False
        angle.update(deepcopy(fields))
        return True


class Registry:
    def __init__(self):
        self.rows = []

    def find_by_path(self, path, *, channel_id):
        return next((deepcopy(r) for r in self.rows if r["path"] == path and r["channel_id"] == channel_id), None)

    def ensure_many(self, entries, *, channel_id, job_scope):
        result = []
        for entry in entries:
            row = self.find_by_path(entry["path"], channel_id=channel_id)
            if row is None:
                row = {**deepcopy(entry), "id": "export_test", "channel_id": channel_id}
                self.rows.append(row)
            result.append(row)
        return result


@pytest.fixture
def context(tmp_path, monkeypatch):
    products, registry = Products(), Registry()
    def runner(job, directory, entry, target):
        target.write_bytes(b"isolated-qc-video")
    def thumbnail(video, output, duration):
        Image.new("RGB", (9, 16), "blue").save(output)
    jobs = HyperFramesRenderJobs(tmp_path, runner=runner, probe=lambda video: {"width": 1080, "height": 1920, "fps": 30, "duration": 1, "audio": False}, thumbnailer=thumbnail)
    service = api.Workflow(tmp_path, products=products, renders=jobs)
    service.finalizer = HyperFramesFinalizer(tmp_path, jobs=jobs, projects=service.projects, product_store=products, registry=registry)
    scope = ChannelScope("main", source="header", strict=True, channel={"id": "main", "status": "active", "handle": "@rizanntry"})
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.get_workflow] = lambda: service
    app.dependency_overrides[api.get_workflow_scope] = lambda: scope
    @app.exception_handler(ChannelError)
    async def channel_error(request, error):
        return JSONResponse(status_code=error.status_code, content={"code": error.code, "detail": str(error)})
    # Channel readiness itself has a separate production gate suite.
    monkeypatch.setattr(api, "require_final_ready", lambda scope: scope)
    return TestClient(app), service, products, registry, scope


def create(client):
    response = client.post("/api/hyperframes/projects", json={"source_binding": {"type": "product_angle", "product_id": "p", "angle_id": "a"}, "inputs": {"audio_mode": "silent", "duration_seconds": 1, "brief": "Clean product demonstration", "style_profile": {"id": "tech", "version": 1, "tokens": {"background": "#111111"}}}})
    assert response.status_code == 201, response.text
    return response.json()["project"]


def submitted(context):
    client, service, products, registry, scope = context
    project = create(client)
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/authoring-jobs', json={"expected_revision": 1})
    assert response.status_code == 201, response.text
    job = response.json()["job"]
    claimed = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/claim', json={"executor_id": "test-session", "expected_generation": 0})
    assert claimed.status_code == 200, claimed.text
    claimed = claimed.json()["job"]
    fence = {"executor_id": "test-session", "generation": claimed["generation"], "fence": claimed["fence"]}
    directory = service.root / job["work_path"]
    (directory / "index.html").write_text('<html><head></head><body><div data-composition-id="test" data-width="1080" data-height="1920" data-duration="1">Product</div></body></html>', encoding="utf-8")
    response = client.post(f'/api/hyperframes/authoring-jobs/{job["id"]}/submit', json=fence)
    assert response.status_code == 200, response.text
    return project, response.json()["job"], fence


def test_http_authoring_accept_render_finalize_gallery_parent_contract(context):
    client, service, products, registry, scope = context
    project, creative, fence = submitted(context)
    packet = client.get(f'/api/hyperframes/authoring-jobs/{creative["id"]}/handoff').json()["handoff"]
    assert packet["channel_id"] == "main"
    assert packet["inputs"]["source_binding"]["angle_id"] == "a"
    accepted = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": 1, "authoring_job_id": creative["id"]})
    assert accepted.status_code == 200, accepted.text
    project = accepted.json()["project"]
    assert "revision_dir" not in project["accepted_revision"]
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/render-jobs', json={"expected_revision": 2, "idempotency_key": "render-one"})
    assert response.status_code == 202, response.text
    job_id = response.json()["job"]["id"]
    job = client.get(f'/api/hyperframes/render-jobs/{job_id}').json()["job"]
    assert job["status"] == "qc_ready"
    assert client.get(f'/api/hyperframes/render-jobs/{job_id}/artifact/video').content == b"isolated-qc-video"
    temporary_video = service.root / job["artifact"]["path"]
    temporary_video.write_bytes(b"unreviewed replacement")
    assert client.get(f'/api/hyperframes/render-jobs/{job_id}/artifact/video').status_code == 404
    temporary_video.write_bytes(b"isolated-qc-video")
    assert registry.rows == []
    finalized = client.post(f'/api/hyperframes/render-jobs/{job_id}/finalize', json={"expected_revision": job["revision"], "artifact_hash": job["artifact"]["sha256"], "publish_package": {"caption": "Review", "hashtags": ["#product"]}})
    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["job"]["status"] == "finalized"
    temporary_video.unlink()
    (service.root / job["artifact"]["thumbnail_path"]).unlink()
    assert client.get(f'/api/hyperframes/render-jobs/{job_id}/artifact/video').content == b"isolated-qc-video"
    assert client.get(f'/api/hyperframes/render-jobs/{job_id}/artifact/thumbnail').status_code == 200
    angle = products.product["angles"][0]
    assert angle["status"] == "rendered" and angle["export_id"] == "export_test"
    assert angle["project_name"] == project["project_name"]
    assert len(registry.rows) == 1


def test_submit_reads_current_source_server_side_and_rejects_late_change(context):
    project, job, fence = submitted(context)
    client, service, products, registry, scope = context
    products.product["angles"][0]["script"] = "Changed saved script"
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": 1, "authoring_job_id": job["id"]})
    assert response.status_code == 409
    assert registry.rows == []


def test_new_brief_invalidates_submitted_revision(context):
    project, job, fence = submitted(context)
    client = context[0]
    inputs = {**project["inputs"], "brief": "Revised brief"}
    assert client.patch(f'/api/hyperframes/projects/{project["project_id"]}', json={"expected_revision": 1, "inputs": inputs}).status_code == 200
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": 1, "authoring_job_id": job["id"]})
    assert response.status_code == 409


def test_cross_channel_lists_and_ids_are_isolated(context):
    client, service, products, registry, scope = context
    project, job, fence = submitted(context)
    scope.channel_id = "second"
    scope._channel = {"id": "second", "status": "active"}
    assert client.get("/api/hyperframes/projects").json() == {"projects": []}
    assert client.get(f'/api/hyperframes/projects/{project["project_id"]}').status_code == 404
    assert client.get(f'/api/hyperframes/authoring-jobs/{job["id"]}').status_code == 404


@pytest.mark.parametrize("extra", [{"status": "rendered"}, {"channel_identity": {"channel_id": "second"}}, {"channel_id": "second"}])
def test_executor_cannot_set_owner_status_identity(context, extra):
    project = create(context[0])
    response = context[0].patch(f'/api/hyperframes/projects/{project["project_id"]}', json={"expected_revision": 1, "inputs": project["inputs"], **extra})
    assert response.status_code == 422


def test_not_accepted_cannot_render_and_readonly_channel_cannot_create(context):
    client, service, products, registry, scope = context
    project = create(client)
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/render-jobs', json={"expected_revision": 1, "idempotency_key": "unsafe"})
    assert response.status_code == 409
    scope._channel["status"] = "archived"
    assert client.post("/api/hyperframes/projects", json={"source_binding": project["source_binding"], "inputs": project["inputs"]}).status_code == 409


def test_source_change_after_acceptance_blocks_render(context):
    project, creative, fence = submitted(context)
    client, service, products, registry, scope = context
    accepted = client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": 1, "authoring_job_id": creative["id"]})
    assert accepted.status_code == 200
    products.product["angles"][0]["script"] = "Changed after review"
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/render-jobs', json={"expected_revision": 2, "idempotency_key": "stale-source"})
    assert response.status_code == 409
    assert response.json()["code"] == "hyperframes_source_changed"
    assert service.renders.list("main") == []


def test_render_pins_one_checked_source_packet_during_concurrent_change(context, monkeypatch):
    project, creative, _ = submitted(context)
    client, service, products, _, _ = context
    assert client.post(f'/api/hyperframes/projects/{project["project_id"]}/accept-revision', json={"expected_revision": 1, "authoring_job_id": creative["id"]}).status_code == 200
    original = service.source_packet
    calls = []
    def change_after_read(channel, project):
        packet = original(channel, project)
        calls.append(packet)
        products.product["price_note"] = "Changed concurrently"
        return packet
    monkeypatch.setattr(service, "source_packet", change_after_read)
    response = client.post(f'/api/hyperframes/projects/{project["project_id"]}/render-jobs', json={"expected_revision": 2, "idempotency_key": "source-race"})
    assert response.status_code == 202
    job = service.renders.get("main", response.json()["job"]["id"])
    assert len(calls) == 1 and "price_note" not in job["source_product_snapshot"]
    response = client.post(f'/api/hyperframes/render-jobs/{job["id"]}/finalize', json={"expected_revision": job["revision"], "artifact_hash": job["artifact"]["sha256"], "publish_package": {}})
    assert response.status_code == 409 and response.json()["code"] == "hyperframes_product_changed"


def test_custom_root_cannot_fall_back_to_production_products(tmp_path):
    service = api.Workflow(tmp_path)
    assert service.products is None
    with pytest.raises(api.HyperFramesProjectError, match="scoped source store"):
        service.projects.create("main", {"type": "product_angle", "product_id": "p", "angle_id": "a"},
                                {"channel_id": "main", "handle": "@rizanntry"})
    assert not list((tmp_path / "03_Projects").rglob("project.json"))
