"""Publication projections and review routes use only explicit temporary roots."""
from copy import deepcopy

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
import pytest

from scripts.channel_scope import ChannelScope, get_channel_scope
from scripts.channel_store import ChannelError
from scripts.channel_workflows import get_workflow_scope
from scripts.posting_jobs import PostingJobStore
from scripts.publication_effects import PublicationEffects
from scripts.publication_observations import PublicationObservationStore
import scripts.api_publication_observations as api


@pytest.fixture
def workspace(tmp_path):
    jobs = PostingJobStore(tmp_path)
    payload = {"export_id": "export-old", "target_handle": "@mainuser", "strict_mode": True,
               "product_id": "product-1", "angle_id": "angle-1", "queue_id": "queue-1",
               "caption": "Original caption", "hashtags": "#one #two", "video_path": "04_Exports/original.mp4"}
    job = jobs.prepare("main", payload)
    job = jobs.mark_prepare_effects("main", job["id"])
    job = jobs.claim("main", job["id"], "extension")
    job = jobs.validate_action("main", job["id"], "extension", job["lease_token"], job["revision"], "@mainuser", begin_publish=True)
    job = jobs.acknowledge("main", job["id"], "extension", job["lease_token"], job["revision"], "@mainuser", "scheduled_on_platform",
                           {"kind": "platform_success_notice", "notice": "Scheduled successfully", "platform_post_id": "123456789"})
    job = jobs.mark_effects_applied("main", job["id"])
    observations = PublicationObservationStore(tmp_path, jobs=jobs)
    effects = PublicationEffects(tmp_path, observations=observations, jobs=jobs)
    effects.tables["export_registry"].save([
        {"id": "export-old", "channel_id": "main", "path": "04_Exports/original.mp4", "status": "ready",
         "product_id": "product-1", "angle_id": "angle-1", "created_at": "2026-10-10T09:00:00+07:00"},
        {"id": "export-foreign", "channel_id": "second", "path": "foreign.mp4", "status": "ready"}])
    effects.tables["schedule_queue"].save([
        {"id": "queue-1", "channel_id": "main", "status": "scheduled_on_platform", "export_id": "export-old", "posting_job_id": job["id"]},
        {"id": "queue-foreign", "channel_id": "second", "status": "planned", "export_id": "export-foreign"}])
    effects.tables["products"].save([
        {"id": "product-1", "channel_id": "main", "angles": [{"angle_id": "angle-1", "export_id": "export-old", "status": "rendered", "batch": 1}]},
        {"id": "product-foreign", "channel_id": "second", "angles": []}])
    evidence = {"kind": "platform_publication", "source": "reviewed_platform_record", "published": True,
                "job_id": job["id"], "channel_id": "main", "source_account": "@mainuser", "platform_video_id": "123456789"}
    event = observations.observe("main", job["id"], "@mainuser", "123456789", "2026-10-11T09:00:00+07:00", evidence, idempotency_key="review-1")
    return jobs, job, observations, effects, event


def test_all_projections_publish_once_preserve_receipt_attempt_and_other_channels(workspace):
    jobs, original, observations, effects, event = workspace
    foreign = {name: table.scoped_load("second") for name, table in effects.tables.items()}
    result = effects.apply("main", event["id"])
    assert result["effects_applied"] is True
    assert effects.apply("main", event["id"]) == result
    posts = effects.tables["posts"].scoped_load("main")
    assert len(posts) == 1
    assert posts[0]["tiktok_url"] == "https://www.tiktok.com/@mainuser/video/123456789"
    assert posts[0]["hashtags"] == ["#one", "#two"]
    export = effects.tables["export_registry"].scoped_load("main")[0]
    assert export["status"] == "posted"
    assert export["path"] == "04_Exports/original.mp4"
    assert effects.tables["schedule_queue"].scoped_load("main")[0]["status"] == "posted"
    assert effects.tables["products"].scoped_load("main")[0]["angles"][0]["status"] == "posted"
    job = jobs.get("main", original["id"])
    assert job["publication_status"] == "published"
    for field in ("status", "receipt", "receipt_hash", "effects_applied", "attempt", "lease_token", "lease_owner", "lease_expires_at", "publish_attempted_at"):
        assert job[field] == original[field]
    assert {name: table.scoped_load("second") for name, table in effects.tables.items()} == foreign


def test_recovery_after_post_log_commit_creates_no_duplicate(workspace, monkeypatch):
    jobs, job, observations, effects, event = workspace
    original_handler = effects._export_registry
    monkeypatch.setattr(effects, "_export_registry", lambda _: (_ for _ in ()).throw(RuntimeError("failure")))
    with pytest.raises(RuntimeError):
        effects.apply("main", event["id"])
    saved = observations.get("main", event["id"])
    assert saved["effects"]["post_log"]["status"] == "applied"
    assert saved["effects"]["export_registry"]["status"] == "error"
    repaired = PublicationEffects(effects.root).apply("main", event["id"])
    assert repaired["effects_applied"]
    assert len(effects.tables["posts"].scoped_load("main")) == 1


@pytest.mark.parametrize("mutation", ["retarget", "newer_export", "same_timestamp", "missing_timestamp"])
def test_old_export_publication_does_not_retarget_current_angle(workspace, mutation):
    _, _, _, effects, event = workspace
    if mutation == "retarget":
        with effects.tables["products"].scoped_mutate("main") as rows:
            rows[0]["angles"][0]["export_id"] = "export-new"
    else:
        with effects.tables["export_registry"].scoped_mutate("main") as rows:
            other = deepcopy(rows[0])
            other.update(id="export-new", path="04_Exports/new.mp4", status="ready")
            if mutation == "newer_export":
                other["created_at"] = "2026-10-11T09:00:00+07:00"
            if mutation == "missing_timestamp":
                other.pop("created_at")
            rows.append(other)
    original_angle = deepcopy(effects.tables["products"].scoped_load("main")[0]["angles"][0])
    assert effects.apply("main", event["id"])["effects_applied"]
    assert effects.tables["products"].scoped_load("main")[0]["angles"][0] == original_angle
    assert effects.tables["posts"].scoped_load("main")[0]["export_id"] == "export-old"


def test_changed_queue_blocks_only_its_effect_and_repairs_original_exact_job(workspace):
    _, job, observations, effects, event = workspace
    with effects.tables["schedule_queue"].scoped_mutate("main") as rows:
        rows[0]["posting_job_id"] = "different-job"
    with pytest.raises(ChannelError) as exc:
        effects.apply("main", event["id"])
    assert exc.value.code == "publication_queue_changed"
    assert observations.get("main", event["id"])["effects"]["schedule_queue"]["status"] == "error"
    with effects.tables["schedule_queue"].scoped_mutate("main") as rows:
        rows[0]["posting_job_id"] = job["id"]
    assert effects.apply("main", event["id"])["effects_applied"]
    assert len(effects.tables["posts"].scoped_load("main")) == 1


def test_existing_exact_stats_post_is_enriched_and_metrics_preserved(workspace):
    _, _, _, effects, event = workspace
    effects.tables["posts"].save([{"id": "existing-post", "channel_id": "main", "platform_post_id": "123456789", "metrics": {"views": 42}}])
    effects.apply("main", event["id"])
    rows = effects.tables["posts"].scoped_load("main")
    assert len(rows) == 1
    assert rows[0]["id"] == "existing-post" and rows[0]["metrics"] == {"views": 42}


def test_ambiguous_exact_post_matches_do_not_merge(workspace):
    _, _, _, effects, event = workspace
    effects.tables["posts"].save([
        {"id": "by-export", "channel_id": "main", "export_id": "export-old"},
        {"id": "by-platform", "channel_id": "main", "platform_post_id": "123456789"}])
    with pytest.raises(ChannelError) as exc:
        effects.apply("main", event["id"])
    assert exc.value.code == "publication_post_ambiguous"
    assert len(effects.tables["posts"].scoped_load("main")) == 2


def make_client(workspace, monkeypatch, channel="main", status="active"):
    _, _, observations, effects, _ = workspace
    monkeypatch.setattr(api, "_services", lambda: (observations, effects))
    app = FastAPI()
    app.include_router(api.router)
    scope = ChannelScope(channel, "default", False, channel={"id": channel, "status": status})
    app.dependency_overrides[get_channel_scope] = lambda: scope
    import scripts.channel_workflows as workflow
    monkeypatch.setattr(workflow, "get_channel_scope", lambda request: scope)
    @app.exception_handler(ChannelError)
    async def errors(request, exc):
        return JSONResponse(status_code=exc.status_code, content=exc.to_body())
    return TestClient(app)


def review_payload(job):
    return {"source_account": "@mainuser", "platform_video_id": "123456789", "observed_published_at": "2026-10-11T09:00:00+07:00",
            "evidence_url": "https://www.tiktok.com/@mainuser/video/123456789", "review_confirmation": "reviewed_published_video",
            "idempotency_key": "api-review", "expected_job_revision": job["revision"]}


def test_review_endpoint_is_explicit_exact_manual_attestation_and_duplicate_retries_work(workspace, monkeypatch):
    jobs, job, observations, effects, event = workspace
    # Start with no event: exercise the full mounted POST handoff.
    observations.table.save([])
    client = make_client(workspace, monkeypatch)
    path = f"/api/tiktok-autopost/jobs/{job['id']}/publication-observations"
    payload = review_payload(job)
    first = client.post(path, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["review_mode"] == "manual_platform_review"
    assert first.json()["observation"]["effects_applied"]
    second = client.post(path, json=payload)
    assert second.status_code == 200, second.text
    assert second.json()["observation"]["id"] == first.json()["observation"]["id"]
    assert len(client.get(path).json()["items"]) == 1
    assert jobs.get("main", job["id"])["receipt"] == job["receipt"]


@pytest.mark.parametrize("change", [
    {"review_confirmation": True}, {"review_confirmation": ""},
    {"evidence_url": "https://www.tiktok.com/@seconduser/video/123456789"},
    {"evidence_url": "https://evil.example/@mainuser/video/123456789"},
    {"evidence_url": "https://www.tiktok.com/@mainuser/video/987654321"},
    {"evidence_url": "https://www.tiktok.com/@mainuser/video/123456789?redirect=1"},
    {"published": True},
])
def test_review_endpoint_rejects_boolean_proof_wrong_url_and_extra_payload(workspace, monkeypatch, change):
    jobs, job, observations, effects, event = workspace
    observations.table.save([])
    payload = review_payload(job)
    payload.update(change)
    client = make_client(workspace, monkeypatch)
    response = client.post(f"/api/tiktok-autopost/jobs/{job['id']}/publication-observations", json=payload)
    assert response.status_code == 422
    assert observations.table.scoped_load("main") == []
    assert jobs.get("main", job["id"]) == job


def test_review_foreign_job_cannot_leak_or_publish(workspace, monkeypatch):
    jobs, job, observations, effects, event = workspace
    client = make_client(workspace, monkeypatch, channel="second")
    path = f"/api/tiktok-autopost/jobs/{job['id']}/publication-observations"
    assert client.get(path).status_code == 404
    assert client.post(path, json=review_payload(job)).status_code == 404
    assert jobs.get("main", job["id"]) == job


def test_review_archived_channel_cannot_write_but_can_list(workspace, monkeypatch):
    jobs, job, observations, effects, event = workspace
    client = make_client(workspace, monkeypatch, status="archived")
    path = f"/api/tiktok-autopost/jobs/{job['id']}/publication-observations"
    before = observations.table.load()
    response = client.post(path, json=review_payload(job))
    assert response.status_code == 409 and response.json()["code"] == "channel_archived"
    assert client.get(path).status_code == 200
    assert observations.table.load() == before


def test_raw_foreign_body_owner_is_rejected_before_effects(workspace, monkeypatch):
    jobs, job, observations, effects, event = workspace
    client = make_client(workspace, monkeypatch)
    before = observations.table.load()
    payload = review_payload(job)
    payload["channel_id"] = "second"
    response = client.post(f"/api/tiktok-autopost/jobs/{job['id']}/publication-observations", json=payload)
    assert response.status_code == 422 and response.json()["code"] == "channel_scope_conflict"
    assert observations.table.load() == before
