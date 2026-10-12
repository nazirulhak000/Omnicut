"""Offline publication identity, durable recovery and competing effect workers."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from scripts.channel_store import ChannelError
from scripts.posting_jobs import PostingJobStore, fingerprint
from scripts.publication_observations import PublicationObservationStore, EFFECT_PHASES


@pytest.fixture
def domain(tmp_path):
    now = [1000.0]
    jobs = PostingJobStore(tmp_path, clock=lambda: now[0])
    job = jobs.prepare("main", {"export_id": "exp-1", "target_handle": "@mainuser", "strict_mode": True})
    job = jobs.claim("main", job["id"], "worker")
    job = jobs.validate_action("main", job["id"], "worker", job["lease_token"], job["revision"], "@mainuser", begin_publish=True)
    job = jobs.acknowledge("main", job["id"], "worker", job["lease_token"], job["revision"], "@mainuser",
                           "scheduled_on_platform", {"kind": "platform_success_notice", "notice": "Scheduled successfully", "platform_post_id": "123456789"})
    job = jobs.mark_effects_applied("main", job["id"])
    store = PublicationObservationStore(tmp_path, jobs=jobs, clock=lambda: now[0], effect_timeout=10)
    return store, jobs, job, now


def observe(domain, **changes):
    store, _, job, _ = domain
    data = {"channel_id": "main", "job_id": job["id"], "source_account": "@mainuser",
            "platform_video_id": "123456789", "observed_published_at": "2026-10-11T09:00:00+07:00",
            "evidence": {"kind": "platform_publication", "source": "platform_detail", "published": True,
                         "job_id": job["id"], "channel_id": "main", "source_account": "@mainuser", "platform_video_id": "123456789"},
            "idempotency_key": "event-1"}
    data.update(changes)
    return store.observe(**data)


def test_durable_observation_leaves_original_attempt_and_receipt_immutable(domain, tmp_path):
    store, jobs, original, _ = domain
    row = observe(domain)
    assert row["status"] == "verified"
    assert jobs.get("main", original["id"]) == original
    assert PublicationObservationStore(tmp_path).get("main", row["id"]) == row
    assert len(store.for_job("main", original["id"])) == 1


def test_duplicate_events_dedupe_and_conflicting_event_key_rejected(domain):
    first = observe(domain)
    assert observe(domain) == first
    assert observe(domain, idempotency_key="duplicate-import") == first
    with pytest.raises(ChannelError) as exc:
        observe(domain, observed_published_at="2026-10-11T10:00:00+07:00")
    assert exc.value.code == "publication_idempotency_conflict"


@pytest.mark.parametrize("changes,code", [
    ({"channel_id": "second"}, "resource_not_found"),
    ({"job_id": "wrong-job"}, "resource_not_found"),
    ({"source_account": "@seconduser"}, "account_handle_mismatch"),
    ({"platform_video_id": "invalid"}, "publication_video_id_invalid"),
    ({"observed_published_at": "2026-10-11T09:00:00"}, "publication_timestamp_invalid"),
    ({"evidence": {"kind": "metrics", "views": 100}}, "publication_evidence_required"),
])
def test_identity_and_proof_guards(domain, changes, code):
    with pytest.raises(ChannelError) as exc:
        observe(domain, **changes)
    assert exc.value.code == code
    assert domain[0].table.scoped_load("main") == []


@pytest.mark.parametrize("field,value", [("job_id", "other"), ("channel_id", "second"), ("source_account", "@seconduser"), ("published", False)])
def test_evidence_identity_cannot_be_substituted(domain, field, value):
    job = domain[2]
    proof = {"kind": "platform_publication", "source": "platform_api", "published": True,
             "job_id": job["id"], "channel_id": "main", "source_account": "@mainuser", "platform_video_id": "123456789"}
    proof[field] = value
    with pytest.raises(ChannelError):
        observe(domain, evidence=proof)
    assert domain[0].table.scoped_load("main") == []


def test_platform_video_mismatch_rejected_even_when_proof_agrees(domain):
    job = domain[2]
    proof = {"kind": "platform_publication", "source": "platform_api", "published": True,
             "job_id": job["id"], "channel_id": "main", "source_account": "@mainuser", "platform_video_id": "987654321"}
    with pytest.raises(ChannelError) as exc:
        observe(domain, platform_video_id="987654321", evidence=proof)
    assert exc.value.code == "publication_linkage_mismatch"


@pytest.mark.parametrize("missing", ["receipt", "observation"])
def test_missing_exact_id_waits_without_any_effect(domain, missing):
    store, jobs, job, _ = domain
    changes = {}
    if missing == "receipt":
        with jobs.table.scoped_mutate("main") as rows:
            rows[0]["receipt"]["proof"].pop("platform_post_id")
            rows[0]["receipt_hash"] = fingerprint(rows[0]["receipt"])
    else:
        changes["platform_video_id"] = None
        proof = {"kind": "platform_publication", "source": "platform_detail", "published": True,
                 "job_id": job["id"], "channel_id": "main", "source_account": "@mainuser", "platform_video_id": None}
        changes["evidence"] = proof
    row = observe(domain, **changes)
    assert row["status"] == "waiting_linkage"
    with pytest.raises(ChannelError) as exc:
        store.apply_effect("main", row["id"], "post_log", expected_revision=row["revision"], handler=lambda _: pytest.fail("must not run"))
    assert exc.value.code == "publication_waiting_linkage"


def test_effect_repair_is_durable_and_handlers_upsert_by_stable_identity(domain, tmp_path):
    store, jobs, job, _ = domain
    row = observe(domain)
    committed = {}
    def interrupted(event):
        committed[event["id"]] = "post"
        raise RuntimeError("crash after external commit")
    with pytest.raises(RuntimeError):
        store.apply_effect("main", row["id"], "post_log", expected_revision=1, handler=interrupted)
    store = PublicationObservationStore(tmp_path, jobs=jobs)
    row = store.get("main", row["id"])
    assert row["effects"]["post_log"]["status"] == "error"
    for phase in EFFECT_PHASES:
        row = store.apply_effect("main", row["id"], phase, expected_revision=row["revision"], handler=lambda event: committed.update({event["id"]: "post"}))
    assert row["effects_applied"] is True
    assert len(committed) == 1
    assert jobs.get("main", job["id"]) == job
    assert store.apply_effect("main", row["id"], "post_log", expected_revision=1, handler=lambda _: pytest.fail("duplicate handler")) == row


def test_stale_revision_and_foreign_channel_cannot_apply_effect(domain):
    store = domain[0]
    row = observe(domain)
    for channel, revision, code in [("second", 1, "resource_not_found"), ("main", 0, "publication_revision_conflict")]:
        with pytest.raises(ChannelError) as exc:
            store.apply_effect(channel, row["id"], "angle", expected_revision=revision, handler=lambda _: pytest.fail("must not run"))
        assert exc.value.code == code


def test_concurrent_effect_and_expired_worker_are_fenced(domain):
    store, _, _, now = domain
    row = observe(domain)
    entered, release = threading.Event(), threading.Event()
    def old_worker(event):
        entered.set()
        assert release.wait(10)
    with ThreadPoolExecutor(max_workers=1) as pool:
        old = pool.submit(store.apply_effect, "main", row["id"], "angle", expected_revision=1, handler=old_worker)
        assert entered.wait(10)
        current = store.get("main", row["id"])
        with pytest.raises(ChannelError) as exc:
            store.apply_effect("main", row["id"], "angle", expected_revision=current["revision"], handler=lambda _: pytest.fail("busy"))
        assert exc.value.code == "publication_effect_busy"
        now[0] += 11
        replacement = store.apply_effect("main", row["id"], "angle", expected_revision=current["revision"], handler=lambda _: None)
        release.set()
        with pytest.raises(ChannelError) as exc:
            old.result()
        assert exc.value.code == "publication_effect_fenced"
        assert store.get("main", row["id"]) == replacement


def test_explicit_roots_required_and_same_storage_enforced(tmp_path):
    with pytest.raises(ValueError):
        PublicationObservationStore(None)
    with pytest.raises(ValueError):
        PublicationObservationStore(tmp_path, jobs=PostingJobStore(tmp_path / "other"))


def test_wrong_phase_and_job_revision_rejected(domain):
    with pytest.raises(ChannelError) as exc:
        observe(domain, expected_job_revision=0)
    assert exc.value.code == "publication_job_revision_conflict"
    row = observe(domain)
    with pytest.raises(ChannelError) as exc:
        domain[0].apply_effect("main", row["id"], "publish", expected_revision=1, handler=lambda _: None)
    assert exc.value.code == "publication_effect_invalid"


@pytest.mark.parametrize("source", [None, "invalid@@account", 123])
def test_malformed_source_account_returns_domain_error(domain, source):
    with pytest.raises(ChannelError) as exc:
        observe(domain, source_account=source)
    assert exc.value.code == "publication_account_invalid"


def test_receipt_corruption_and_unscheduled_job_cannot_be_observed(domain):
    store, jobs, job, _ = domain
    with jobs.table.scoped_mutate("main") as rows:
        rows[0]["receipt"]["source_account"] = "@seconduser"
    with pytest.raises(ChannelError) as exc:
        observe(domain)
    assert exc.value.code == "publication_receipt_invalid"
    with jobs.table.scoped_mutate("main") as rows:
        rows[0]["status"] = "published"
    with pytest.raises(ChannelError) as exc:
        observe(domain)
    assert exc.value.code == "publication_job_not_scheduled"


def test_platform_id_cannot_be_attached_to_another_job(domain):
    store, jobs, job, _ = domain
    observe(domain)
    with jobs.table.scoped_mutate("main") as rows:
        another = deepcopy(job)
        another.update(id="other-job", job_id="other-job", export_id="exp-2", idempotency_key="other-key")
        rows.append(another)
    proof = {"kind": "platform_publication", "source": "platform_api", "published": True,
             "job_id": "other-job", "channel_id": "main", "source_account": "@mainuser", "platform_video_id": "123456789"}
    with pytest.raises(ChannelError) as exc:
        observe(domain, job_id="other-job", evidence=proof, idempotency_key="other-event")
    assert exc.value.code == "publication_video_already_linked"
