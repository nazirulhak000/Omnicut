"""Exact publication observation projects into real Gadget/slot history."""
from copy import deepcopy
import threading

import pytest

from tests.test_hyperframes_publish_readiness import context, candidate, approve, preparation
from tests.test_channel_exports_posts import env
from scripts.channel_store import ChannelError
from scripts.gadget_media_campaign import CampaignStore
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.hyperframes_publication import apply_gadget_publication
from scripts.posting_jobs import PostingJobStore
from scripts.publication_effects import PublicationEffects
from scripts.publication_observations import PublicationObservationStore


def observed(context, *, slot=False, accepted_id=True):
    client, service, _, _ = context
    repo, source, project, record, artifact = candidate(context, slot=slot, slot_ready=slot)
    approve(context, source, artifact)
    response = client.post("/api/tiktok-autopost/prepare", json=preparation(record))
    assert response.status_code == 200, response.text
    jobs = PostingJobStore(service.root)
    job = jobs.get("main", response.json()["job_id"])
    assert job["source_binding"] == project["source_binding"]
    assert job["source_artifact_id"] == artifact["artifact_id"]
    job = jobs.claim("main", job["id"], "offline-extension")
    job = jobs.validate_action("main", job["id"], "offline-extension", job["lease_token"], job["revision"], "@rizanntry", begin_publish=True)
    proof = {"kind": "platform_success_notice", "notice": "Scheduled successfully"}
    if accepted_id:
        proof["platform_post_id"] = "123456789"
    job = jobs.acknowledge("main", job["id"], "offline-extension", job["lease_token"], job["revision"], "@rizanntry", "scheduled_on_platform", proof)
    job = jobs.mark_effects_applied("main", job["id"])
    observations = PublicationObservationStore(service.root, jobs=jobs)
    evidence = {"kind": "platform_publication", "source": "reviewed_platform_record", "published": True,
                "job_id": job["id"], "channel_id": "main", "source_account": "@rizanntry", "platform_video_id": "123456789"}
    event = observations.observe("main", job["id"], "@rizanntry", "123456789", "2026-10-12T09:00:00+07:00", evidence, idempotency_key="actual-gadget-publication")
    effects = PublicationEffects(service.root, observations=observations, jobs=jobs)
    return repo, source, record, artifact, jobs, job, observations, effects, event


def test_actual_approved_gadget_publication_updates_project_artifact_and_history_once(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    result = effects.apply("main", event["id"])
    assert result["effects_applied"] is True
    saved = repo.get(source.project_id)
    assert saved.status == "published"
    assert saved.metrics["published_at"] == event["observed_published_at"]
    assert saved.metrics["published_export_id"] == record["id"]
    published = saved.artifacts[0]
    assert published["published"] is True and published["publication_observation_id"] == event["id"]
    assert published["tiktok_url"] == "https://www.tiktok.com/@rizanntry/video/123456789"
    assert len(saved.artifacts) == 1
    assert effects.apply("main", event["id"]) == result
    assert repo.get(source.project_id).to_dict() == saved.to_dict()
    current = jobs.get("main", job["id"])
    for field in ("status", "receipt", "receipt_hash", "attempt", "lease_owner", "lease_token", "publish_attempted_at"):
        assert current[field] == job[field]


def test_old_published_artifact_never_retargets_current_newer_master(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    newer = repo.roots.export_dir(source.project_id) / "newer.mp4"
    newer.write_bytes(b"different-new-master")
    repo.add_render_artifact(source.project_id, {"artifact_id": "later-master", "kind": "render", "path": str(newer), "approved": False})
    approve(context, source, {"artifact_id": "later-master"})
    before = repo.get(source.project_id)
    assert effects.apply("main", event["id"])["effects_applied"]
    saved = repo.get(source.project_id)
    assert saved.status == "approved" and saved.approved_master_id == "later-master"
    assert saved.metrics == before.metrics and saved.artifacts[1] == before.artifacts[1]
    assert saved.artifacts[0]["published"] is True and saved.artifacts[0]["approved"] is False
    assert saved.artifacts[0]["publication"]["current_master_at_projection"] is False


def test_actual_reviewed_campaign_slot_publication_uses_existing_domain(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context, slot=True)
    assert job["source_slot_fingerprint"]
    assert effects.apply("main", event["id"])["effects_applied"]
    store = CampaignStore(effects.root / "_Docs/gadget_media_campaigns.json", channel_id="main")
    campaign = store.get(job["source_binding"]["campaign_id"])
    slot = next(slot for slot in campaign.slots if slot.slot_id == job["source_binding"]["slot_id"])
    assert slot.status == "published" and slot.ready_to_publish is True
    assert slot.product_project_id == source.project_id
    artifact = repo.get(source.project_id).artifacts[0]
    assert artifact["publication"]["slot_projection"]["status"] == "applied"


@pytest.mark.parametrize("change", ["retarget", "content"])
def test_publication_retains_artifact_truth_without_overwriting_changed_slot(context, change):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context, slot=True)
    store = CampaignStore(effects.root / "_Docs/gadget_media_campaigns.json", channel_id="main")
    binding = job["source_binding"]
    store.update_slot(binding["campaign_id"], binding["slot_id"],
                      {"product_project_id": "another-project"} if change == "retarget" else {"script": "Newer script for same slot"})
    before = store.path.read_bytes()
    assert effects.apply("main", event["id"])["effects_applied"]
    assert store.path.read_bytes() == before
    saved = repo.get(source.project_id)
    assert saved.status == "published" and saved.artifacts[0]["published"]
    projection = saved.artifacts[0]["publication"]["slot_projection"]
    assert projection == {"status": "skipped", "reason": "slot_retargeted" if change == "retarget" else "slot_content_changed"}


def test_recovery_after_gadget_commit_preserves_first_projection_and_new_master(context, monkeypatch):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    original = effects._angle
    def fail_after_commit(event):
        original(event)
        raise RuntimeError("Interruption after Gadget source commit")
    monkeypatch.setattr(effects, "_angle", fail_after_commit)
    with pytest.raises(RuntimeError, match="Gadget source commit"):
        effects.apply("main", event["id"])
    first = deepcopy(repo.get(source.project_id).artifacts[0]["publication"])
    newer = repo.roots.export_dir(source.project_id) / "later.mp4"
    newer.write_bytes(b"new-master-during-repair")
    repo.add_render_artifact(source.project_id, {"artifact_id": "repair-master", "kind": "render", "path": str(newer), "approved": False})
    approve(context, source, {"artifact_id": "repair-master"})
    repaired = PublicationEffects(effects.root).apply("main", event["id"])
    assert repaired["effects_applied"]
    saved = repo.get(source.project_id)
    assert saved.approved_master_id == "repair-master" and saved.status == "approved"
    assert saved.artifacts[0]["publication"] == first and len(saved.artifacts) == 2
    assert len(effects.tables["posts"].scoped_load("main")) == 1


def test_missing_exact_scheduled_platform_linkage_cannot_publish_gadget(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context, accepted_id=False)
    before = repo.get(source.project_id).to_dict()
    assert event["status"] == "waiting_linkage"
    with pytest.raises(ChannelError, match="not yet established"):
        effects.apply("main", event["id"])
    assert repo.get(source.project_id).to_dict() == before


def test_frozen_artifact_hash_mismatch_leaves_recoverable_parent_phase(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    current = repo.get(source.project_id)
    current.artifacts[0]["sha256"] = "0" * 64
    repo.save(current)
    with pytest.raises(ChannelError) as error:
        effects.apply("main", event["id"])
    assert error.value.code == "hyperframes_publication_artifact_changed"
    assert observations.get("main", event["id"])["effects"]["angle"]["status"] == "error"
    assert repo.get(source.project_id).status == "approved"


def test_source_helper_rejects_other_channel_before_gadget_mutation(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    changed = deepcopy(event)
    changed["channel_id"] = "second"
    before = repo.get(source.project_id).to_dict()
    with pytest.raises(ChannelError) as error:
        apply_gadget_publication(effects.root, job, changed)
    assert error.value.code == "hyperframes_publication_conflict"
    assert repo.get(source.project_id).to_dict() == before


def test_recovery_after_campaign_commit_before_gadget_save_finishes_once(context, monkeypatch):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context, slot=True)
    original = GadgetMediaRepository.save
    def fail_before_gadget_commit(repository, project):
        if project.status == "published":
            raise OSError("Interrupted after Campaign slot projection")
        return original(repository, project)
    monkeypatch.setattr(GadgetMediaRepository, "save", fail_before_gadget_commit)
    with pytest.raises(OSError, match="Campaign slot projection"):
        effects.apply("main", event["id"])
    binding = job["source_binding"]
    store = CampaignStore(effects.root / "_Docs/gadget_media_campaigns.json", channel_id="main")
    slot = next(slot for slot in store.get(binding["campaign_id"]).slots if slot.slot_id == binding["slot_id"])
    assert slot.status == "published"
    assert repo.get(source.project_id).status == "approved"
    before = store.path.read_bytes()
    monkeypatch.setattr(GadgetMediaRepository, "save", original)
    assert PublicationEffects(effects.root).apply("main", event["id"])["effects_applied"]
    assert store.path.read_bytes() == before
    assert repo.get(source.project_id).status == "published"
    assert len(repo.get(source.project_id).artifacts) == 1
    assert len(effects.tables["posts"].scoped_load("main")) == 1


def test_reviewing_same_published_master_again_preserves_status_and_manifest_bytes(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    assert effects.apply("main", event["id"])["effects_applied"]
    before = repo.get(source.project_id).to_dict()
    manifest = repo.roots.project_dir(source.project_id) / "project.json"
    raw = manifest.read_bytes()
    response = approve(context, source, artifact)
    assert response.json()["status"] == "published"
    assert repo.get(source.project_id).to_dict() == before and manifest.read_bytes() == raw


def test_gadget_publication_keeps_other_channel_project_bytes_unchanged(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    foreign_repo = repo.for_channel("second")
    foreign = foreign_repo.create({"brand": "Other", "model": "Channel"}, project_id="other-channel-gadget")
    directory = foreign_repo.roots.project_dir(foreign.project_id)
    before = {path.name: path.read_bytes() for path in directory.glob("*.json")}
    assert effects.apply("main", event["id"])["effects_applied"]
    assert {path.name: path.read_bytes() for path in directory.glob("*.json")} == before
    assert foreign_repo.get(foreign.project_id).status == "brief"


def test_source_helper_cannot_substitute_other_platform_video_for_frozen_receipt(context):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    changed = deepcopy(event)
    changed["platform_video_id"] = "987654321"
    before = repo.get(source.project_id).to_dict()
    with pytest.raises(ChannelError) as error:
        apply_gadget_publication(effects.root, job, changed)
    assert error.value.code == "hyperframes_publication_conflict"
    assert repo.get(source.project_id).to_dict() == before


@pytest.mark.parametrize("writer_kind", ["timeline", "quality", "artifact"])
def test_concurrent_gadget_writer_cannot_erase_publication_projection(context, monkeypatch, writer_kind):
    repo, source, record, artifact, jobs, job, observations, effects, event = observed(context)
    original_lock = GadgetMediaRepository._lock
    attempted = threading.Event()
    errors = []
    class SharedLock:
        def __enter__(self):
            if threading.current_thread().name == "gadget-source-writer":
                attempted.set()
            original_lock.acquire()
            return self
        def __exit__(self, *args):
            original_lock.release()
    lock = SharedLock()
    monkeypatch.setattr(GadgetMediaRepository, "_lock", lock)
    monkeypatch.setattr(repo, "_lock", lock)
    writer = repo.for_channel("main")
    def write():
        try:
            if writer_kind == "timeline":
                writer.save_timeline(source.project_id, {"workspace_scope": "gadget_media", "project_id": source.project_id, "duration": 2, "tracks": []})
            elif writer_kind == "quality":
                writer.save_quality_report(source.project_id, {"passed": True, "editorial_score": 91})
            else:
                writer.add_render_artifact(source.project_id, {"artifact_id": "concurrent-candidate", "kind": "render", "path": "04_Exports/Ready_to_post/main/concurrent.mp4", "approved": False})
        except Exception as error:
            errors.append(error)
    thread = threading.Thread(target=write, name="gadget-source-writer")
    try:
        # The competing writer is paused at its first lock acquisition. With
        # the old implementation it has already read an obsolete project;
        # the corrected operation acquires the lock before reading anything.
        with lock:
            thread.start()
            assert attempted.wait(5), "Concurrent writer did not reach the shared lock"
            assert effects.apply("main", event["id"])["effects_applied"]
    finally:
        thread.join(5)
    assert not thread.is_alive() and errors == []
    saved = repo.get(source.project_id)
    assert saved.status == "published" and saved.metrics["publication_observation_id"] == event["id"]
    assert saved.artifacts[0]["published"] is True and saved.artifacts[0]["publication_observation_id"] == event["id"]
    if writer_kind == "timeline":
        assert saved.edit["duration"] == 2 and writer.load_timeline(source.project_id)["duration"] == 2
    elif writer_kind == "quality":
        assert saved.quality_report["editorial_score"] == 91
    else:
        assert len(saved.artifacts) == 2 and saved.artifacts[1]["artifact_id"] == "concurrent-candidate"
