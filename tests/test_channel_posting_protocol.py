"""Durable posting and account fencing; offline mocks and temporary storage only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from scripts.posting_jobs import PostingJobStore, account_check
from scripts.channel_store import ChannelError


def payload(channel="main"):
    return {"export_id": "exp-1", "video_path": "canonical.mp4", "target_handle": "@mainuser" if channel == "main" else "@seconduser",
            "channel_revision": 1, "account_binding": {"status": "verified"}, "strict_mode": channel != "main",
            "video_sha256": "frozen", "caption": "frozen caption", "cover_path": None, "queue_id": None}


@pytest.fixture
def store(tmp_path):
    now = [1000.0]
    return PostingJobStore(tmp_path, clock=lambda: now[0], lease_seconds=10), now


def claimed(store, channel="main", owner="extension-a"):
    row = store.prepare(channel, payload(channel))
    return store.claim(channel, row["job_id"], owner)


def attempt(store, row, source="@mainuser"):
    return store.validate_action(row["channel_id"], row["job_id"], row["lease_owner"], row["lease_token"],
                                 row["revision"], source, begin_publish=True)


def test_prepare_is_durable_immutable_idempotent_and_channel_scoped(store, tmp_path):
    jobs, _ = store
    data = payload()
    row = jobs.prepare("main", data, idempotency_key="request-1")
    data["caption"] = "mutated"
    assert PostingJobStore(tmp_path).get("main", row["job_id"])["caption"] == "frozen caption"
    assert jobs.prepare("main", payload(), idempotency_key="request-1")["job_id"] == row["job_id"]
    with pytest.raises(ChannelError) as exc:
        jobs.prepare("main", data, idempotency_key="request-1")
    assert exc.value.code == "posting_idempotency_conflict"
    with pytest.raises(ChannelError) as exc:
        jobs.get("second", row["job_id"])
    assert exc.value.status_code == 404
    assert jobs.prepare("second", payload("second"))["channel_id"] == "second"


def test_concurrent_claim_has_one_winner_and_instance_cannot_claim_other_channel(store):
    jobs, _ = store
    row = jobs.prepare("main", payload())
    def claim(owner):
        try:
            return jobs.claim("main", row["job_id"], owner)
        except ChannelError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ["extension-a", "extension-b"]))
    winners = [r for r in results if isinstance(r, dict)]
    assert len(winners) == 1
    second = jobs.prepare("second", payload("second"))
    with pytest.raises(ChannelError) as exc:
        jobs.claim("second", second["job_id"], winners[0]["lease_owner"])
    assert exc.value.code == "posting_instance_busy"


def test_expired_claim_is_fenced_but_attempted_job_can_never_be_reclaimed(store, tmp_path):
    jobs, now = store
    old = claimed(jobs)
    now[0] += 11
    new = jobs.claim("main", old["job_id"], "extension-b")
    assert new["lease_token"] != old["lease_token"]
    with pytest.raises(ChannelError) as exc:
        attempt(jobs, old)
    assert exc.value.code == "posting_lease_invalid"
    publishing = attempt(jobs, new)
    now[0] += 100
    restarted = PostingJobStore(tmp_path, clock=lambda: now[0])
    with pytest.raises(ChannelError) as exc:
        restarted.claim("main", publishing["job_id"], "extension-c")
    assert exc.value.code == "posting_reconciliation_required"
    assert restarted.pending("main") is None


@pytest.mark.parametrize("strict,channel", [(True, "main"), (False, "second")])
def test_unknown_or_wrong_account_blocks_before_attempt(store, strict, channel):
    jobs, _ = store
    data = payload(channel)
    data["strict_mode"] = strict
    row = jobs.claim(channel, jobs.prepare(channel, data)["job_id"], "extension-a")
    for source in [None, "@wronguser"]:
        with pytest.raises(ChannelError):
            attempt(jobs, row, source)
    assert jobs.get(channel, row["job_id"])["attempt"] == 0


def test_compat_main_unknown_account_blocks_posting(store):
    jobs, _ = store
    row = claimed(jobs)
    with pytest.raises(ChannelError) as exc:
        attempt(jobs, row, None)
    assert exc.value.code == "source_account_required"
    assert jobs.get("main",row["job_id"])["status"] == "claimed"
    with pytest.raises(ChannelError) as exc:
        account_check("main", "@mainuser", "@wronguser", strict=False)
    assert exc.value.code == "account_handle_mismatch"


def test_receipt_retry_is_idempotent_unknown_requires_reconcile_not_publish(store):
    jobs, now = store
    row = attempt(jobs, claimed(jobs))
    args = ("main", row["job_id"], row["lease_owner"], row["lease_token"], row["revision"], "@mainuser")
    unknown = jobs.acknowledge(*args, "confirmation_unknown", {})
    assert jobs.acknowledge(*args, "confirmation_unknown", {})["revision"] == unknown["revision"]
    with pytest.raises(ChannelError):
        jobs.claim("main", row["job_id"], "extension-a")
    now[0] += 100
    result = jobs.acknowledge("main", row["job_id"], row["lease_owner"], row["lease_token"], unknown["revision"],
                              "@mainuser", "published", {"kind": "platform_success_notice", "notice": "Posted successfully"}, reconcile=True)
    assert result["status"] == "published"
    assert result["attempt"] == 1


def test_receipt_rejects_navigation_only_wrong_account_owner_revision(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    args = ["main", row["job_id"], row["lease_owner"], row["lease_token"], row["revision"], "@mainuser"]
    with pytest.raises(ChannelError) as exc:
        jobs.acknowledge(*args, "published", {"kind": "navigation"})
    assert exc.value.code == "posting_confirmation_required"
    for index, bad in [(2, "another-extension"), (3, "wrong-token"), (4, 999), (5, "@otheruser")]:
        forged = list(args)
        forged[index] = bad
        with pytest.raises(ChannelError):
            jobs.acknowledge(*forged, "published", {"kind": "platform_success_notice", "notice": "Posted successfully"})
    assert jobs.get("main", row["job_id"])["status"] == "publishing"


def test_prepared_cover_revision_locks_on_claim_and_changes_payload_hash(store):
    jobs, _ = store
    old = jobs.prepare("main", payload())
    edited = jobs.update_cover("main", old["job_id"], "new.jpg")
    assert edited["payload_hash"] != old["payload_hash"]
    row = jobs.claim("main", old["job_id"], "extension-a")
    with pytest.raises(ChannelError) as exc:
        jobs.update_cover("main", row["job_id"], "different.jpg")
    assert exc.value.code == "posting_payload_locked"


@pytest.fixture
def api_env(tmp_path, monkeypatch):
    from scripts import api_tiktok_autopost as api, api_exports, export_registry, product_store, post_log, schedule_store, config
    from scripts.channel_scope import ChannelScope, SOURCE_HEADER, SOURCE_DEFAULT, install_channel_scope
    from scripts.channel_workflows import get_workflow_scope
    root = tmp_path
    ready = root / "04_Exports" / "Ready_to_post"
    ready.mkdir(parents=True)
    covers = root / "05_Covers_Thumbnails"
    covers.mkdir()
    for module in [api, api_exports, export_registry, product_store]:
        if hasattr(module, "BASE_DIR"):
            monkeypatch.setattr(module, "BASE_DIR", root)
    for module in [api, api_exports]:
        monkeypatch.setattr(module, "EXPORTS_DIR", ready)
        monkeypatch.setattr(module, "POSTED_DIR", root / "04_Exports" / "Posted")
        monkeypatch.setattr(module, "COVERS_DIR", covers)
    monkeypatch.setattr(config, "BASE_DIR", root)
    monkeypatch.setattr(export_registry, "REGISTRY_PATH", root / "_Docs" / "export_registry.json")
    monkeypatch.setattr(product_store, "STORE_PATH", root / "_Docs" / "products.json")
    monkeypatch.setattr(post_log, "LOG_PATH", root / "_Docs" / "post_log.json")
    monkeypatch.setattr(schedule_store, "SCHEDULE_QUEUE_PATH", root / "_Docs" / "schedule_queue.json")
    channel = {"id": "main", "handle": "@mainuser", "revision": 1, "status": "active", "account_binding": {"status": "unverified"}}
    def scope(request: Request):
        channel_id = request.headers.get("X-OmniCut-Channel", "main")
        source = SOURCE_HEADER if request.headers.get("X-OmniCut-Channel") else SOURCE_DEFAULT
        return ChannelScope(channel_id, source, False, {**channel, "id": channel_id})
    app = FastAPI()
    app.include_router(api.router)
    # Install typed-error handling; dependencies use isolated explicit fixtures.
    install_channel_scope(app, strict=False)
    app.dependency_overrides[get_workflow_scope] = scope
    client = TestClient(app)
    video = ready / "owned.mp4"
    video.write_bytes(b"private fixture video")
    export = export_registry.ExportRegistry.ensure(video, channel_id="main")
    return client, api, export_registry.ExportRegistry, video, export, channel


def prepared_claimed_api(env):
    client, api, registry, video, export, channel = env
    response = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"]})
    assert response.status_code == 200, response.text
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": response.json()["job_id"], "lease_owner": "extension-a"})
    assert row.status_code == 200, row.text
    return row.json()


def action_body(row, source="@mainuser"):
    return {"protocol_version": 2, "job_id": row["job_id"], "lease_owner": row["lease_owner"],
            "lease_token": row["lease_token"], "expected_revision": row["revision"],
            "payload_hash": row["payload_hash"], "source_account": source}


def test_api_channel_guard_before_files_and_legacy_clear_cannot_drop_claim(api_env):
    client, api, registry, video, export, channel = api_env
    foreign = registry.ensure(video.parent / "foreign.mp4", channel_id="second")
    response = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": foreign["id"]})
    assert response.status_code == 404
    row = prepared_claimed_api(api_env)
    assert client.post("/api/tiktok-autopost/clear", json={}).status_code == 422
    assert client.post("/api/tiktok-autopost/clear", json={"job_id": row["job_id"]}).status_code == 409
    assert "lease_token" not in client.get("/api/tiktok-autopost/pending").json()


def test_api_binding_and_file_change_block_before_attempt(api_env):
    client, api, registry, video, export, channel = api_env
    row = prepared_claimed_api(api_env)
    channel["revision"] = 2
    result = client.post("/api/tiktok-autopost/attempt", json=action_body(row))
    assert result.status_code == 409 and result.json()["code"] == "posting_binding_changed"
    channel["revision"] = 1
    video.write_bytes(b"different export")
    result = client.post("/api/tiktok-autopost/attempt", json=action_body(row))
    assert result.status_code == 409 and result.json()["code"] == "posting_export_changed"


def test_cover_file_change_blocks_before_claimed_side_effect(api_env):
    client, api, registry, video, export, channel = api_env
    cover = api.COVERS_DIR / "owned_cover_3x4.jpg"
    cover.write_bytes(b"original cover")
    response = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "cover_path": str(cover)})
    assert response.status_code == 200, response.text
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": response.json()["job_id"], "lease_owner": "extension-a"}).json()
    cover.write_bytes(b"different cover")
    result = client.post("/api/tiktok-autopost/validate", json=action_body(row))
    assert result.status_code == 409 and result.json()["code"] == "posting_cover_changed"


def test_only_implicit_main_bypasses_readiness_and_explicit_main_enforces_binding(api_env, monkeypatch):
    client, api, registry, video, export, channel = api_env
    checks = []
    monkeypatch.setattr(api, "require_final_ready", lambda scope: checks.append(scope.channel_id))
    body = {"video_path": str(video), "export_id": export["id"]}
    assert client.post("/api/tiktok-autopost/prepare", json=body).status_code == 200
    assert checks == []
    blocked = client.post("/api/tiktok-autopost/prepare", json=body, headers={"X-OmniCut-Channel": "main"})
    assert blocked.status_code == 409 and blocked.json()["code"] == "account_binding_unverified"
    assert checks == ["main"]
    channel.update(posting_enabled=True, account_binding={"status": "verified", "verified_handle": "@mainuser"})
    body["idempotency_key"] = "explicit-ready"
    # A changed binding cannot overwrite/reuse the old prepared export job.
    assert client.post("/api/tiktok-autopost/prepare", json=body, headers={"X-OmniCut-Channel": "main"}).status_code == 409
    assert checks == ["main", "main"]


@pytest.mark.parametrize("outcome", ["scheduled_on_platform", "confirmation_unknown"])
def test_scheduled_unknown_do_not_mark_export_or_postlog(api_env, monkeypatch, outcome):
    client, api, registry, video, export, channel = api_env
    row = prepared_claimed_api(api_env)
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    from scripts import api_exports
    monkeypatch.setattr(api_exports, "apply_posted_outcome", lambda *a, **kw: pytest.fail("must not mark scheduled/unknown"))
    proof = {} if outcome == "confirmation_unknown" else {"kind": "platform_success_notice", "notice": "Scheduled successfully"}
    result = client.post("/api/tiktok-autopost/ack", json={**action_body(started), "outcome": outcome, "proof": proof})
    assert result.status_code == 200, result.text
    assert registry.get(export["id"], channel_id="main")["status"] != "posted"
    assert video.exists()


def test_published_effect_retry_uses_server_snapshot_and_never_republishes(api_env, monkeypatch):
    client, api, registry, video, export, channel = api_env
    row = prepared_claimed_api(api_env)
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    from scripts import api_exports
    calls = []
    def mark(req, scope, posting_job):
        calls.append((req, scope))
        if len(calls) == 1:
            raise RuntimeError("local archive temporarily unavailable")
        return {"success": True}
    monkeypatch.setattr(api_exports, "apply_posted_outcome", mark)
    body = {**action_body(started), "outcome": "published", "proof": {"kind": "platform_success_notice", "notice": "Posted successfully"}}
    with pytest.raises(RuntimeError, match="temporarily"):
        client.post("/api/tiktok-autopost/ack", json=body)
    stored = api._jobs().get("main", row["job_id"])
    assert stored["status"] == "published" and not stored["effects_applied"]
    assert client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": row["job_id"], "lease_owner": "extension-a"}).status_code == 409
    result = client.post("/api/tiktok-autopost/ack", json=body)
    assert result.status_code == 200 and result.json()["effects_applied"] is True
    assert calls[-1][0].file_path == str(video)
    assert calls[-1][0].export_id == export["id"]
    assert calls[-1][1].channel_id == "main"
    assert client.post("/api/tiktok-autopost/ack", json={**body, "caption": "forged"}).status_code == 422
    assert client.post("/api/tiktok-autopost/ack", json={**body, "proof": {"kind": "platform_success_notice", "video_url": "untrusted"}}).status_code == 422


def test_real_published_archive_and_postlog_retry_is_idempotent(api_env):
    client, api, registry, video, export, channel = api_env
    from scripts.post_log import PostLog
    row = prepared_claimed_api(api_env)
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    body = {**action_body(started), "outcome": "published", "proof": {"kind": "platform_success_notice", "notice": "Posted successfully"}}
    for _ in range(2):
        response = client.post("/api/tiktok-autopost/ack", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["effects_applied"]
    assert not video.exists()
    assert (api.POSTED_DIR / video.name).read_bytes() == b"private fixture video"
    assert registry.get(export["id"], channel_id="main")["status"] == "posted"
    assert len([r for r in PostLog.get_all(channel_id="main") if r.get("export_id") == export["id"]]) == 1


def test_queue_prepare_failure_is_durable_ineligible_and_retry_completes(api_env, monkeypatch):
    client, api, registry, video, export, channel = api_env
    from scripts.schedule_store import ScheduleQueueStore as Queue
    with Queue.transaction(channel_id="main") as rows:
        rows.append({"id": "queue-1", "channel_id": "main", "export_id": export["id"], "status": "planned"})
    original = Queue.update_item
    monkeypatch.setattr(Queue, "update_item", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("queue unavailable")))
    body = {"video_path": str(video), "export_id": export["id"], "queue_id": "queue-1", "idempotency_key": "queue-retry"}
    with pytest.raises(RuntimeError, match="queue unavailable"):
        client.post("/api/tiktok-autopost/prepare", json=body)
    stored = api._jobs().table.load()[0]
    assert not stored["prepare_effects_applied"]
    assert api._jobs().pending("main") is None
    with pytest.raises(ChannelError) as exc:
        api._jobs().claim("main", stored["job_id"], "extension-a")
    assert exc.value.code == "posting_prepare_incomplete"
    monkeypatch.setattr(Queue, "update_item", original)
    result = client.post("/api/tiktok-autopost/prepare", json=body)
    assert result.status_code == 200, result.text
    assert result.json()["job_id"] == stored["job_id"]
    assert Queue.get_item("queue-1", channel_id="main")["posting_job_id"] == stored["job_id"]
    assert api._jobs().pending("main")["prepare_effects_applied"]
    Queue.update_item("queue-1", lambda row, _: row.update(status="cancelled"), channel_id="main")
    assert client.post("/api/tiktok-autopost/prepare", json=body).status_code == 409
    assert Queue.get_item("queue-1", channel_id="main")["status"] == "cancelled"


def test_success_requires_outcome_specific_notice(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    for proof in [{"kind": "platform_success_notice"}, {"kind": "platform_success_notice", "notice": "Scheduled successfully"}]:
        with pytest.raises(ChannelError) as exc:
            jobs.acknowledge("main", row["job_id"], row["lease_owner"], row["lease_token"], row["revision"], "@mainuser", "published", proof)
        assert exc.value.code == "posting_confirmation_required"
    assert jobs.get("main", row["job_id"])["status"] == "publishing"


def test_crash_after_file_move_before_registry_update_recovers_from_snapshot(api_env, monkeypatch):
    client, api, registry, video, export, channel = api_env
    from scripts import api_exports
    row = prepared_claimed_api(api_env)
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    body = {**action_body(started), "outcome": "published", "proof": {"kind": "platform_success_notice", "notice": "Posted successfully"}}
    original = api_exports.apply_posted_outcome
    def interrupted(req, scope, posting_job):
        api.POSTED_DIR.mkdir(parents=True)
        video.rename(api.POSTED_DIR / video.name)
        raise RuntimeError("interrupted after move")
    monkeypatch.setattr(api_exports, "apply_posted_outcome", interrupted)
    with pytest.raises(RuntimeError, match="interrupted"):
        client.post("/api/tiktok-autopost/ack", json=body)
    assert not api._jobs().get("main", row["job_id"])["effects_applied"]
    monkeypatch.setattr(api_exports, "apply_posted_outcome", original)
    result = client.post("/api/tiktok-autopost/ack", json=body)
    assert result.status_code == 200, result.text
    assert result.json()["effects_applied"]
    assert registry.get(export["id"], channel_id="main")["status"] == "posted"


def test_stats_source_account_wrong_and_secondary_unknown_fail_before_merge(api_env, monkeypatch):
    from scripts import api_tiktok_stats as stats
    from scripts.channel_scope import ChannelScope, SOURCE_HEADER
    monkeypatch.setattr(stats, "_guard_write", lambda scope: None)
    monkeypatch.setattr(stats.PostLog, "upsert_tiktok_stats", lambda *a, **kw: pytest.fail("foreign account must not merge"))
    for channel, source in [("main", "@wronguser"), ("second", None), ("second", "@wronguser")]:
        scope = ChannelScope(channel, SOURCE_HEADER, False, {"handle": "@mainuser", "account_binding": {"status": "verified", "verified_handle": "@mainuser"}})
        with pytest.raises(ChannelError) as exc:
            stats.import_stats(stats.StatsImportRequest(rows=[stats.StatsRow(title="fixture")], source_account=source), scope=scope)
        assert exc.value.code in {"account_handle_mismatch", "source_account_required"}


def test_stats_compat_unknown_is_returned_as_warning_and_durably_audited(api_env, monkeypatch):
    from scripts import api_tiktok_stats as stats
    from scripts.channel_scope import ChannelScope, SOURCE_HEADER
    from scripts.db import DocumentTable
    monkeypatch.setattr(stats, "_guard_write", lambda scope: None)
    monkeypatch.setattr(stats, "_export_clip_candidates", lambda scope: [])
    monkeypatch.setattr(stats.PostLog, "upsert_tiktok_stats", lambda *a, **kw: {"unmatched": [], "matched": 1})
    monkeypatch.setattr(stats.PostLog, "summary", lambda **kw: {})
    monkeypatch.setattr(stats.TikTokPending, "replace_from_sync", lambda *a, **kw: None)
    monkeypatch.setattr(stats.TikTokPending, "remove_video_ids", lambda *a, **kw: None)
    monkeypatch.setattr(stats.TikTokPending, "list_rows", lambda **kw: [])
    scope = ChannelScope("main", SOURCE_HEADER, False, {"handle": "@mainuser"})
    result = stats.import_stats(stats.StatsImportRequest(rows=[stats.StatsRow(title="fixture")]), scope=scope)
    assert result["account_check"]["source_account"] is None
    assert result["account_check"]["warning"]
    root = PostingJobStore().path.parent
    audit = DocumentTable("posting_account_audit", lambda: root / "store.db", lambda: root / "posting_account_audit.json").load()
    assert audit[-1]["event"] == "stats_source_account"
    assert audit[-1]["channel_id"] == "main" and audit[-1]["warning"]


def test_release_expired_claim_and_lost_reply_are_fenced_and_never_release_attempt(store):
    jobs, now = store
    row = claimed(jobs)
    now[0] += 100
    args = ("main",row["job_id"],row["lease_owner"],row["lease_token"],row["revision"])
    assert jobs.release(*args)["status"] == "cancelled"
    assert jobs.release(*args)["status"] == "cancelled"
    replacement = jobs.prepare("main",payload())
    assert replacement["job_id"] != row["job_id"] and replacement["status"] == "prepared"
    with pytest.raises(ChannelError):
        jobs.release("main",row["job_id"],"another",row["lease_token"],row["revision"])
    data=payload(); data["export_id"]="exp-2"
    other=jobs.claim("main",jobs.prepare("main",data)["job_id"],"extension-a")
    publishing=attempt(jobs,other)
    with pytest.raises(ChannelError) as exc:
        jobs.release("main",publishing["job_id"],publishing["lease_owner"],publishing["lease_token"],publishing["revision"])
    assert exc.value.code == "posting_reconciliation_required"


def test_confirmation_token_cannot_confirm_a_different_attempt(store):
    jobs,_=store
    row=claimed(jobs)
    started=jobs.validate_action("main",row["job_id"],row["lease_owner"],row["lease_token"],row["revision"],"@mainuser",
                                begin_publish=True,confirmation_token="attempt-1")
    args=("main",started["job_id"],started["lease_owner"],started["lease_token"],started["revision"],"@mainuser","published")
    proof={"kind":"platform_success_notice","notice":"Posted successfully","confirmation_token":"another-attempt"}
    with pytest.raises(ChannelError):
        jobs.acknowledge(*args,proof)
    proof["confirmation_token"]="attempt-1"
    assert jobs.acknowledge(*args,proof)["status"] == "published"


def test_real_postlog_failure_keeps_receipt_retryable_after_file_move(api_env,monkeypatch):
    from scripts.post_log import PostLog
    client,api,registry,video,export,_=api_env
    row=prepared_claimed_api(api_env)
    started=client.post("/api/tiktok-autopost/attempt",json=action_body(row)).json()
    body={**action_body(started),"outcome":"published","proof":{"kind":"platform_success_notice","notice":"Posted successfully"}}
    original=PostLog.record_posted_export
    monkeypatch.setattr(PostLog,"record_posted_export",lambda **kwargs: (_ for _ in ()).throw(OSError("disk temporarily unavailable")))
    failed=client.post("/api/tiktok-autopost/ack",json=body)
    assert failed.status_code == 409 and failed.json()["code"] == "posting_effects_pending"
    assert api._jobs().get("main",row["job_id"])["effects_applied"] is False
    assert not video.exists() and registry.get(export["id"],channel_id="main")["status"] == "posted"
    monkeypatch.setattr(PostLog,"record_posted_export",original)
    assert client.post("/api/tiktok-autopost/ack",json=body).json()["effects_applied"] is True
    assert len([post for post in PostLog.get_all(channel_id="main") if post.get("export_id")==export["id"]]) == 1


def test_api_release_is_job_owned_and_does_not_touch_foreign_job(api_env):
    client,api,*_=api_env
    row=prepared_claimed_api(api_env)
    foreign=client.post("/api/tiktok-autopost/release",headers={"X-OmniCut-Channel":"second"},json=action_body(row))
    assert foreign.status_code == 422 and foreign.json()["code"] == "channel_scope_unknown"
    assert client.post("/api/tiktok-autopost/release",json=action_body(row)).json()["status"] == "cancelled"
    assert client.post("/api/tiktok-autopost/release",json=action_body(row)).json()["status"] == "cancelled"


def test_confirmed_receipt_repairs_superseded_export_without_newest_guard(api_env):
    import os
    from fastapi import HTTPException
    from scripts.api_exports import _require_latest_export
    from scripts.product_store import ProductStore
    client,api,registry,video,export,_=api_env
    product=ProductStore.add("Fixture product",angles=[{"angle_id":"angle-1","angle_name":"Fixture angle","status":"rendered"}],channel_id="main")
    export=registry.ensure(video,product_id=product["id"],angle_id="angle-1",channel_id="main")
    row=prepared_claimed_api(api_env)
    started=client.post("/api/tiktok-autopost/attempt",json=action_body(row)).json()
    # Rendering a newer version cannot invalidate publication that already
    # happened. The manual mark-posted path still retains its newest guard.
    newer=video.with_name("newer.mp4");newer.write_bytes(b"new version remains untouched")
    os.utime(video,(100,100));os.utime(newer,(200,200))
    newer_export=registry.ensure(newer,product_id=product["id"],angle_id="angle-1",channel_id="main")
    ProductStore.update_angle_status(product["id"],"angle-1","rendered",export_id=newer_export["id"],video_url=str(newer),channel_id="main")
    assert registry.latest_for_angle(product["id"],"angle-1",channel_id="main")["id"] == newer_export["id"]
    with pytest.raises(HTTPException) as manual:
        _require_latest_export(export,product["id"],"angle-1","main")
    assert manual.value.status_code == 409
    body={**action_body(started),"outcome":"published","proof":{"kind":"platform_success_notice","notice":"Posted successfully"}}
    result=client.post("/api/tiktok-autopost/ack",json=body)
    assert result.status_code == 200 and result.json()["effects_applied"]
    assert registry.get(export["id"],channel_id="main")["status"] == "posted"
    assert newer.read_bytes() == b"new version remains untouched"
    angle=ProductStore.get(product["id"],channel_id="main")["angles"][0]
    assert angle["export_id"] == newer_export["id"] and angle["status"] == "rendered"


def test_confirmed_job_never_repairs_a_queue_rebound_to_another_job(api_env):
    from scripts.schedule_store import ScheduleQueueStore
    client,api,registry,video,export,_=api_env
    with ScheduleQueueStore.transaction(channel_id="main") as rows:
        rows.append({"id":"queue-1","channel_id":"main","export_id":export["id"],"status":"planned"})
    prepared=client.post("/api/tiktok-autopost/prepare",json={"video_path":str(video),"export_id":export["id"],"queue_id":"queue-1"}).json()
    row=client.post("/api/tiktok-autopost/claim",json={"protocol_version":2,"job_id":prepared["job_id"],"lease_owner":"extension-a"}).json()
    started=client.post("/api/tiktok-autopost/attempt",json=action_body(row)).json()
    def rebind(queue,_rows): queue["posting_job_id"]="another-job"
    ScheduleQueueStore.update_item("queue-1",rebind,channel_id="main")
    body={**action_body(started),"outcome":"published","proof":{"kind":"platform_success_notice","notice":"Posted successfully"}}
    result=client.post("/api/tiktok-autopost/ack",json=body)
    assert result.status_code == 409 and result.json()["code"] == "posting_queue_changed"
    queue=ScheduleQueueStore.get_item("queue-1",channel_id="main")
    assert queue["posting_job_id"] == "another-job" and queue["status"] == "ready_for_extension"
    assert video.exists() and registry.get(export["id"],channel_id="main")["status"] != "posted"
    assert api._jobs().get("main",row["job_id"])["status"] == "published"
    assert not api._jobs().get("main",row["job_id"])["effects_applied"]


@pytest.mark.parametrize("link_new_angle", [False,True])
@pytest.mark.parametrize("initially_bound", [False,True])
@pytest.mark.parametrize("new_mtime,newer_registration", [(200,False),(100,False),(50,False),(50,True),(50,None)])
def test_new_export_between_file_move_and_angle_mutation_is_preserved(api_env,monkeypatch,link_new_angle,initially_bound,new_mtime,newer_registration):
    import os
    import datetime
    from scripts import export_registry
    from scripts.product_store import ProductStore
    client,api,registry,video,export,_=api_env
    product=ProductStore.add("Race fixture",angles=[{"angle_id":"angle-1","status":"rendered"}],channel_id="main")
    registry.ensure(video,product_id=product["id"],angle_id="angle-1",channel_id="main")
    if initially_bound:
        ProductStore.update_angle_status(product["id"],"angle-1","rendered",export_id=export["id"],video_url=str(video),channel_id="main")
    # Real copied files can retain old mtimes; registration timestamps have
    # second precision, so ties are deliberately frozen in this regression.
    monkeypatch.setattr(export_registry,"_now",lambda:export["created_at"])
    os.utime(video,(100,100))
    row=prepared_claimed_api(api_env)
    started=client.post("/api/tiktok-autopost/attempt",json=action_body(row)).json()
    original=ProductStore.update_angle_status
    injected=[]
    def concurrent_render(*args,**kwargs):
        if kwargs.get("status")=="posted" and not injected:
            newer=video.with_name("concurrent-new.mp4");newer.write_bytes(b"new render during old publication repair")
            os.utime(newer,(new_mtime,new_mtime))
            if newer_registration is None:
                monkeypatch.setattr(export_registry,"_now",lambda:"")
            elif newer_registration:
                created=(datetime.datetime.fromisoformat(export["created_at"])+datetime.timedelta(seconds=1)).isoformat()
                monkeypatch.setattr(export_registry,"_now",lambda:created)
            new_export=registry.ensure(newer,product_id=product["id"],angle_id="angle-1",channel_id="main")
            injected.append(new_export)
            if link_new_angle:
                original(product["id"],"angle-1","rendered",export_id=new_export["id"],video_url=str(newer),channel_id="main")
        return original(*args,**kwargs)
    monkeypatch.setattr(ProductStore,"update_angle_status",concurrent_render)
    body={**action_body(started),"outcome":"published","proof":{"kind":"platform_success_notice","notice":"Posted successfully"}}
    result=client.post("/api/tiktok-autopost/ack",json=body)
    assert result.status_code==200 and result.json()["effects_applied"],result.text
    from scripts.post_log import PostLog
    assert registry.get(export["id"],channel_id="main")["status"]=="posted"
    assert len([post for post in PostLog.get_all(channel_id="main") if post.get("export_id")==export["id"]])==1
    angle=ProductStore.get(product["id"],channel_id="main")["angles"][0]
    previous_id=export["id"] if initially_bound else None
    assert angle.get("export_id")== (injected[0]["id"] if link_new_angle else previous_id) and angle["status"]=="rendered"
    assert registry.get(injected[0]["id"],channel_id="main")["status"]=="rendered"
