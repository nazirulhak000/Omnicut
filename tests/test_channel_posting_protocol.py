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


def prepared_claimed_api(env, **extra):
    client, api, registry, video, export, channel = env
    response = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], **extra})
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
    # a scheduled outcome needs a job that was really prepared with a publish time (intent=schedule)
    extra = {"schedule_date": "2026-11-12", "schedule_time": "09:00"} if outcome == "scheduled_on_platform" else {}
    row = prepared_claimed_api(api_env, **extra)
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


def test_manual_user_confirmation_ack_and_reconcile(api_env):
    client, api, registry, video, export, channel = api_env
    row = prepared_claimed_api(api_env)
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    body = {
        **action_body(started),
        "outcome": "published",
        "proof": {
            "kind": "manual_user_confirmation",
            "notice": "User confirmed posting on TikTok Studio",
        },
    }
    result = client.post("/api/tiktok-autopost/reconcile", json=body)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["status"] == "published"
    assert data["effects_applied"] is True
    assert registry.get(export["id"], channel_id="main")["status"] == "posted"


def test_content_page_reconciled_ack(api_env):
    client, api, registry, video, export, channel = api_env
    row = prepared_claimed_api(api_env)
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    body = {
        **action_body(started),
        "outcome": "published",
        "proof": {
            "kind": "content_page_reconciled",
            "notice": "Navigated to content management page",
        },
    }
    result = client.post("/api/tiktok-autopost/ack", json=body)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["status"] == "published"
    assert data["effects_applied"] is True
    assert registry.get(export["id"], channel_id="main")["status"] == "posted"



def _ack_args(row):
    return ("main", row["job_id"], row["lease_owner"], row["lease_token"], row["revision"], "@mainuser")


def test_real_tiktok_bare_video_published_toast_is_accepted_for_published(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    done = jobs.acknowledge(*_ack_args(row), "published", {"kind": "platform_success_notice", "notice": "Video published"})
    assert done["status"] == "published"


def test_bare_published_toast_is_rejected_as_scheduled_for_unscheduled_job(store):
    jobs, _ = store
    unscheduled = attempt(jobs, claimed(jobs))
    with pytest.raises(ChannelError) as exc:
        jobs.acknowledge(*_ack_args(unscheduled), "scheduled_on_platform",
                         {"kind": "platform_success_notice", "notice": "Video published"})
    assert exc.value.code == "posting_confirmation_required"
    assert jobs.get("main", unscheduled["job_id"])["status"] == "publishing"


def test_bare_published_toast_confirms_scheduled_job(store):
    jobs, _ = store
    data = payload()
    data.update(schedule_date="2026-11-10", schedule_time="07:00")
    row = jobs.prepare("main", data)
    row = attempt(jobs, jobs.claim("main", row["job_id"], "extension-a"))
    done = jobs.acknowledge(*_ack_args(row), "scheduled_on_platform",
                            {"kind": "platform_success_notice", "notice": "Video published"})
    assert done["status"] == "scheduled_on_platform"


def test_notice_must_still_be_a_platform_sentence(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    for notice in ["Video published by someone", "published", "Draft saved", ""]:
        with pytest.raises(ChannelError):
            jobs.acknowledge(*_ack_args(row), "published", {"kind": "platform_success_notice", "notice": notice})


# ---- draft_saved: the "Save draft" button (no toast; TikTok opens Content > Drafts) ----

def test_draft_saved_is_accepted_with_drafts_page_proof_and_is_not_a_post(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    done = jobs.acknowledge(*_ack_args(row), "draft_saved", {"kind": "drafts_page_confirmed"})
    assert done["status"] == "draft_saved"
    assert done["receipt"]["outcome"] == "draft_saved"
    # a saved draft still blocks preparing the same export again (no duplicate drafts)
    with pytest.raises(ChannelError) as exc:
        jobs.prepare("main", payload(), idempotency_key="again")
    assert exc.value.code == "posting_export_already_prepared"


def test_draft_saved_accepts_a_platform_sentence_or_manual_confirmation_only(store):
    jobs, _ = store
    def attempted(export_id):
        prepared = jobs.prepare("main", {**payload(), "export_id": export_id})
        return attempt(jobs, jobs.claim("main", prepared["job_id"], f"extension-{export_id}"))

    for index, notice in enumerate(["Draft saved", "บันทึกแบบร่างแล้ว", "Video draft saved."]):
        row = attempted(f"exp-notice-{index}")
        done = jobs.acknowledge(*_ack_args(row), "draft_saved", {"kind": "platform_success_notice", "notice": notice})
        assert done["status"] == "draft_saved"
    row = attempted("exp-manual")
    assert jobs.acknowledge(*_ack_args(row), "draft_saved", {"kind": "user_confirmed", "notice": "operator saw the draft in Drafts"})["status"] == "draft_saved"


def test_draft_saved_rejects_missing_or_wrong_evidence_and_scheduled_jobs(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    for proof in [{}, {"kind": "content_page_reconciled"}, {"kind": "platform_success_notice", "notice": "Video published"},
                  {"kind": "platform_success_notice", "notice": ""}]:
        with pytest.raises(ChannelError) as exc:
            jobs.acknowledge(*_ack_args(row), "draft_saved", proof)
        assert exc.value.code == "posting_confirmation_required"
    assert jobs.get("main", row["job_id"])["status"] == "publishing"
    # a job that carries a publish time is not a draft job
    data = {**payload(), "export_id": "exp-sched", "schedule_date": "2026-11-12", "schedule_time": "09:00"}
    sched = attempt(jobs, jobs.claim("main", jobs.prepare("main", data)["job_id"], "extension-z"))
    with pytest.raises(ChannelError) as exc:
        jobs.acknowledge(*_ack_args(sched), "draft_saved", {"kind": "drafts_page_confirmed"})
    assert exc.value.code == "posting_confirmation_required"


def test_drafts_page_proof_cannot_confirm_a_post(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    for outcome in ["published", "scheduled_on_platform"]:
        with pytest.raises(ChannelError) as exc:
            jobs.acknowledge(*_ack_args(row), outcome, {"kind": "drafts_page_confirmed"})
        assert exc.value.code == "posting_confirmation_required"


def test_draft_proof_must_carry_the_confirmation_token_of_this_click(store):
    jobs, _ = store
    row = claimed(jobs)
    row = jobs.validate_action(row["channel_id"], row["job_id"], row["lease_owner"], row["lease_token"],
                               row["revision"], "@mainuser", begin_publish=True, confirmation_token="tok-123")
    with pytest.raises(ChannelError):
        jobs.acknowledge(*_ack_args(row), "draft_saved", {"kind": "drafts_page_confirmed", "confirmation_token": "other"})
    done = jobs.acknowledge(*_ack_args(row), "draft_saved", {"kind": "drafts_page_confirmed", "confirmation_token": "tok-123"})
    assert done["status"] == "draft_saved"


def test_release_draft_frees_the_export_but_never_a_scheduled_or_published_job(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    jobs.acknowledge(*_ack_args(row), "draft_saved", {"kind": "drafts_page_confirmed"})
    released = jobs.release_draft("main", row["job_id"])
    assert released["status"] == "cancelled"
    assert jobs.release_draft("main", row["job_id"])["status"] == "cancelled"  # idempotent
    assert jobs.prepare("main", payload(), idempotency_key="after-release")["status"] == "prepared"
    data = {**payload(), "export_id": "exp-pub"}
    pub = attempt(jobs, jobs.claim("main", jobs.prepare("main", data)["job_id"], "extension-p"))
    jobs.acknowledge(*_ack_args(pub), "published", {"kind": "platform_success_notice", "notice": "Video published"})
    with pytest.raises(ChannelError) as exc:
        jobs.release_draft("main", pub["job_id"])
    assert exc.value.code == "posting_reconciliation_required"
    assert jobs.get("main", pub["job_id"])["status"] == "published"


# ---- R1: intent per job, force never releases an attempted job, evidence must say what was seen ----

def _intent_job(jobs, intent, export_id, **extra):
    data = {**payload(), "export_id": export_id, "intent": intent, **extra}
    prepared = jobs.prepare("main", data)
    return jobs.claim("main", prepared["job_id"], f"ext-{export_id}")


def _attempt_as(jobs, row, click_kind):
    return jobs.validate_action(row["channel_id"], row["job_id"], row["lease_owner"], row["lease_token"],
                                row["revision"], "@mainuser", begin_publish=True, click_kind=click_kind)


def test_force_release_never_cancels_an_attempted_or_final_job(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    for force in (False, True):
        with pytest.raises(ChannelError) as exc:
            jobs.release("main", row["job_id"], row["lease_owner"], row["lease_token"], row["revision"], force=force)
        assert exc.value.code == "posting_reconciliation_required"
    assert jobs.get("main", row["job_id"])["status"] == "publishing"
    with pytest.raises(ChannelError):
        jobs.prepare("main", payload(), idempotency_key="again-after-force")  # the export stays blocked
    # same for a job that already reached a final outcome
    for outcome, proof, export in [("scheduled_on_platform", {"kind": "platform_success_notice", "notice": "Video published"}, "exp-s"),
                                   ("draft_saved", {"kind": "drafts_page_confirmed"}, "exp-d")]:
        extra = {"schedule_date": "2026-11-12", "schedule_time": "09:00"} if outcome == "scheduled_on_platform" else {}
        done = _intent_job(jobs, "schedule" if extra else "draft", export, **extra)
        done = _attempt_as(jobs, done, "post" if extra else "draft")
        done = jobs.acknowledge(*_ack_args(done), outcome, proof)
        with pytest.raises(ChannelError) as exc:
            jobs.release("main", done["job_id"], done["lease_owner"], done["lease_token"], done["revision"], force=True)
        assert exc.value.code == "posting_reconciliation_required"
        assert jobs.get("main", done["job_id"])["status"] == outcome


def test_an_unattempted_claim_can_still_be_released(store):
    jobs, _ = store
    row = claimed(jobs)
    released = jobs.release("main", row["job_id"], row["lease_owner"], row["lease_token"], row["revision"])
    assert released["status"] == "cancelled"


def test_attempt_refuses_the_wrong_button_for_the_job_intent(store):
    jobs, _ = store
    # a draft job may only save a draft
    draft = _intent_job(jobs, "draft", "exp-i1")
    for kind in ("post", None):
        with pytest.raises(ChannelError) as exc:
            _attempt_as(jobs, draft, kind)
        assert exc.value.code == "posting_intent_mismatch"
    assert jobs.get("main", draft["job_id"])["status"] == "claimed"  # nothing was consumed
    assert _attempt_as(jobs, draft, "draft")["status"] == "publishing"
    # a post job may not save a draft
    post = _intent_job(jobs, "post_now", "exp-i2")
    with pytest.raises(ChannelError) as exc:
        _attempt_as(jobs, post, "draft")
    assert exc.value.code == "posting_intent_mismatch"
    assert _attempt_as(jobs, post, "post")["status"] == "publishing"
    # old workers that say nothing keep working for post jobs
    legacy = _intent_job(jobs, "schedule", "exp-i3", schedule_date="2026-11-12", schedule_time="09:00")
    assert _attempt_as(jobs, legacy, None)["status"] == "publishing"
    bad = _intent_job(jobs, "post_now", "exp-i4")
    with pytest.raises(ChannelError) as exc:
        _attempt_as(jobs, bad, "nonsense")
    assert exc.value.code == "posting_click_kind_invalid"


def test_outcome_must_match_the_intent(store):
    jobs, _ = store
    toast = {"kind": "platform_success_notice", "notice": "Video published"}
    draft = _attempt_as(jobs, _intent_job(jobs, "draft", "exp-o1"), "draft")
    with pytest.raises(ChannelError) as exc:
        jobs.acknowledge(*_ack_args(draft), "published", toast)
    assert exc.value.code == "posting_intent_mismatch"
    now = _attempt_as(jobs, _intent_job(jobs, "post_now", "exp-o2"), "post")
    with pytest.raises(ChannelError) as exc:
        jobs.acknowledge(*_ack_args(now), "scheduled_on_platform", toast)
    assert exc.value.code in {"posting_intent_mismatch", "posting_confirmation_required"}
    assert jobs.acknowledge(*_ack_args(now), "published", toast)["status"] == "published"


def test_a_scheduled_job_cannot_be_recorded_published_from_the_bare_toast(store):
    jobs, _ = store
    row = _attempt_as(jobs, _intent_job(jobs, "schedule", "exp-sc", schedule_date="2026-11-12", schedule_time="09:00"), "post")
    with pytest.raises(ChannelError) as exc:
        jobs.acknowledge(*_ack_args(row), "published", {"kind": "platform_success_notice", "notice": "Video published"})
    assert exc.value.code == "posting_confirmation_required"
    assert jobs.get("main", row["job_id"])["status"] == "publishing"
    done = jobs.acknowledge(*_ack_args(row), "scheduled_on_platform", {"kind": "platform_success_notice", "notice": "Video published"})
    assert done["status"] == "scheduled_on_platform"


def test_reconcile_and_manual_proofs_must_carry_a_notice(store):
    jobs, _ = store
    row = attempt(jobs, claimed(jobs))
    for kind in ("content_page_reconciled", "manual_user_confirmation", "user_confirmed"):
        for notice in (None, "", "ok", "   "):
            proof = {"kind": kind} if notice is None else {"kind": kind, "notice": notice}
            with pytest.raises(ChannelError) as exc:
                jobs.acknowledge(*_ack_args(row), "published", proof, reconcile=True)
            assert exc.value.code == "posting_confirmation_required"
    assert jobs.get("main", row["job_id"])["status"] == "publishing"
    done = jobs.acknowledge(*_ack_args(row), "published",
                            {"kind": "manual_user_confirmation", "notice": "operator saw the post on Studio > Content"}, reconcile=True)
    assert done["status"] == "published"


# ---- R4: job <-> queue consistency ----

def _queue_row(env, queue_id="queue-r4"):
    from scripts.schedule_store import ScheduleQueueStore
    client, api, registry, video, export, _ = env
    with ScheduleQueueStore.transaction(channel_id="main") as rows:
        rows.append({"id": queue_id, "channel_id": "main", "export_id": export["id"], "status": "planned"})
    return queue_id


def _queue_get(queue_id="queue-r4"):
    from scripts.schedule_store import ScheduleQueueStore
    return ScheduleQueueStore.get_item(queue_id, channel_id="main")


def test_unknown_outcome_is_mirrored_to_the_queue_and_the_final_proof_replaces_it(api_env):
    client, api, registry, video, export, _ = api_env
    queue_id = _queue_row(api_env)
    prepared = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": queue_id}).json()
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": prepared["job_id"], "lease_owner": "extension-a"}).json()
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    unknown = client.post("/api/tiktok-autopost/ack", json={**action_body(started), "outcome": "confirmation_unknown", "proof": {}})
    assert unknown.status_code == 200, unknown.text
    queued = _queue_get(queue_id)
    assert queued["status"] == "confirmation_unknown" and queued["posting_job_id"] == prepared["job_id"]
    assert registry.get(export["id"], channel_id="main")["status"] != "posted"          # nothing else was touched
    assert not api._jobs().get("main", prepared["job_id"])["effects_applied"]
    final = client.post("/api/tiktok-autopost/reconcile", json={**action_body(unknown.json()), "outcome": "published",
                        "proof": {"kind": "manual_user_confirmation", "notice": "ตรวจบน TikTok Studio แล้วโพสต์จริง"}})
    assert final.status_code == 200, final.text
    assert _queue_get(queue_id)["status"] == "posted"


def test_clear_of_a_prepared_job_resets_its_queue_row(api_env):
    client, api, registry, video, export, _ = api_env
    queue_id = _queue_row(api_env)
    prepared = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": queue_id}).json()
    assert _queue_get(queue_id)["status"] == "ready_for_extension"
    assert client.post("/api/tiktok-autopost/clear", json={"job_id": prepared["job_id"]}).status_code == 200
    row = _queue_get(queue_id)
    assert row["status"] == "planned" and "posting_job_id" not in row
    again = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": queue_id})
    assert again.status_code == 200, again.text                                       # not refused with 409 any more


def test_missing_queue_row_does_not_keep_a_confirmed_receipt_pending(api_env):
    from scripts.schedule_store import ScheduleQueueStore
    client, api, registry, video, export, _ = api_env
    queue_id = _queue_row(api_env)
    prepared = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": queue_id}).json()
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": prepared["job_id"], "lease_owner": "extension-a"}).json()
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    assert ScheduleQueueStore.remove_item(queue_id, channel_id="main") is not None
    done = client.post("/api/tiktok-autopost/ack", json={**action_body(started), "outcome": "published",
                       "proof": {"kind": "platform_success_notice", "notice": "Posted successfully"}})
    assert done.status_code == 200, done.text
    assert api._jobs().get("main", prepared["job_id"])["effects_applied"] is True


def test_queue_edit_is_refused_while_the_job_is_in_flight(api_env):
    from scripts import api_schedule_queue as queue_api
    from scripts.channel_store import ChannelError
    client, api, registry, video, export, _ = api_env
    queue_id = _queue_row(api_env)
    prepared = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": queue_id}).json()
    existing = lambda: _queue_get(queue_id)
    # prepared only: may be cancelled (reset) but not silently left alive by a delete
    with pytest.raises(ChannelError) as err:
        queue_api._settle_job_before_edit("main", existing(), cancel=False)
    assert err.value.code == "posting_job_in_flight"
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": prepared["job_id"], "lease_owner": "extension-a"}).json()
    with pytest.raises(ChannelError) as err:                      # claimed by the extension: park it from the panel first
        queue_api._settle_job_before_edit("main", existing(), cancel=True)
    assert err.value.code == "posting_job_in_flight"
    client.post("/api/tiktok-autopost/attempt", json=action_body(row))
    with pytest.raises(ChannelError) as err:                      # attempted: the post may exist on TikTok
        queue_api._settle_job_before_edit("main", existing(), cancel=True)
    assert err.value.code == "posting_job_in_flight"
    assert api._jobs().get("main", prepared["job_id"])["status"] != "cancelled"


def test_queue_reset_cancels_a_prepared_job_first(api_env):
    from scripts import api_schedule_queue as queue_api
    client, api, registry, video, export, _ = api_env
    queue_id = _queue_row(api_env)
    prepared = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": queue_id}).json()
    queue_api._settle_job_before_edit("main", _queue_get(queue_id), cancel=True)
    assert api._jobs().get("main", prepared["job_id"])["status"] == "cancelled"


# ---- publish_draft: open a draft that sits on TikTok and publish it ----

def _drafted_queue_row(env, queue_id="queue-pd"):
    """A queue row that went through the real draft flow: draft_on_platform + a draft_saved job."""
    client, api, registry, video, export, _ = env
    _queue_row(env, queue_id)
    prepared = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": queue_id,
                                                                  "intent": "draft", "caption": "แกะกล่องสายชาร์จ", "hashtags": "#t"}).json()
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": prepared["job_id"], "lease_owner": "extension-a"}).json()
    started = client.post("/api/tiktok-autopost/attempt", json={**action_body(row), "click_kind": "draft"}).json()
    done = client.post("/api/tiktok-autopost/ack", json={**action_body(started), "outcome": "draft_saved", "proof": {"kind": "drafts_page_confirmed"}})
    assert done.status_code == 200, done.text
    assert _queue_get(queue_id)["status"] == "draft_on_platform"
    return queue_id, prepared["job_id"]


def _publish_payload(env, queue_id, **extra):
    client, api, registry, video, export, _ = env
    return {"video_path": str(video), "export_id": export["id"], "queue_id": queue_id, "intent": "publish_draft",
            "caption": "แกะกล่องสายชาร์จ", "hashtags": "#t", **extra}


def test_publish_draft_schedules_from_the_draft_and_completes_the_queue(api_env):
    client, api, registry, video, export, _ = api_env
    queue_id, draft_job = _drafted_queue_row(api_env)
    prepared = client.post("/api/tiktok-autopost/prepare", json=_publish_payload(api_env, queue_id, schedule_date="2030-01-02", schedule_time="09:00"))
    assert prepared.status_code == 200, prepared.text
    job = api._jobs().get("main", prepared.json()["job_id"])
    assert job["intent"] == "publish_draft" and job["draft_source_job_id"] == draft_job
    assert api._jobs().get("main", draft_job)["status"] == "draft_saved"        # stays until the publication succeeds
    queued = _queue_get(queue_id)
    assert queued["status"] == "ready_for_extension" and queued["posting_job_id"] == job["job_id"] and queued["draft_job_id"] == draft_job
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": job["job_id"], "lease_owner": "extension-a"}).json()
    # a publication presses Post; it may never press Save draft
    assert client.post("/api/tiktok-autopost/attempt", json={**action_body(row), "click_kind": "draft"}).status_code == 409
    started = client.post("/api/tiktok-autopost/attempt", json={**action_body(row), "click_kind": "post"})
    assert started.status_code == 200, started.text
    # outcome rules follow the effective intent: a slot means "scheduled", never "published" from a bare toast, never a draft
    assert client.post("/api/tiktok-autopost/ack", json={**action_body(started.json()), "outcome": "draft_saved", "proof": {"kind": "drafts_page_confirmed"}}).status_code == 422
    bare = client.post("/api/tiktok-autopost/ack", json={**action_body(started.json()), "outcome": "published", "proof": {"kind": "platform_success_notice", "notice": "Video published"}})
    assert bare.status_code == 422
    done = client.post("/api/tiktok-autopost/ack", json={**action_body(started.json()), "outcome": "scheduled_on_platform",
                       "proof": {"kind": "platform_success_notice", "notice": "Scheduled successfully", "confirmation_token": started.json().get("confirmation_token")}})
    assert done.status_code == 200, done.text
    assert _queue_get(queue_id)["status"] == "scheduled_on_platform"
    assert api._jobs().get("main", draft_job)["status"] == "cancelled"          # consumed by the publication


def test_publish_draft_now_needs_explicit_live_confirmation_and_ends_posted(api_env):
    client, api, registry, video, export, _ = api_env
    queue_id, _draft = _drafted_queue_row(api_env)
    refused = client.post("/api/tiktok-autopost/prepare", json=_publish_payload(api_env, queue_id))
    assert refused.status_code == 422 and refused.json()["code"] == "posting_live_confirmation_required"
    half = client.post("/api/tiktok-autopost/prepare", json=_publish_payload(api_env, queue_id, schedule_date="2030-01-02"))
    assert half.status_code == 422
    assert _queue_get(queue_id)["status"] == "draft_on_platform"                  # nothing moved
    ok = client.post("/api/tiktok-autopost/prepare", json=_publish_payload(api_env, queue_id, confirm_live=True))
    assert ok.status_code == 200, ok.text
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": ok.json()["job_id"], "lease_owner": "extension-a"}).json()
    started = client.post("/api/tiktok-autopost/attempt", json={**action_body(row), "click_kind": "post"}).json()
    wrong = client.post("/api/tiktok-autopost/ack", json={**action_body(started), "outcome": "scheduled_on_platform",
                        "proof": {"kind": "platform_success_notice", "notice": "Scheduled successfully"}})
    assert wrong.status_code == 422                                              # an immediate publication is never "scheduled"
    done = client.post("/api/tiktok-autopost/ack", json={**action_body(started), "outcome": "published",
                       "proof": {"kind": "platform_success_notice", "notice": "Video published", "confirmation_token": started.get("confirmation_token")}})
    assert done.status_code == 200, done.text
    assert _queue_get(queue_id)["status"] == "posted"


def test_publish_draft_refuses_a_row_that_is_not_a_draft_on_tiktok(api_env):
    client, api, registry, video, export, _ = api_env
    planned = _queue_row(api_env, "queue-not-draft")
    res = client.post("/api/tiktok-autopost/prepare", json=_publish_payload(api_env, planned, schedule_date="2030-01-02", schedule_time="09:00"))
    assert res.status_code == 409 and res.json()["code"] == "posting_draft_not_on_platform"
    no_queue = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "intent": "publish_draft",
                                                                 "caption": "x ok", "schedule_date": "2030-01-02", "schedule_time": "09:00"})
    assert no_queue.status_code == 422 and no_queue.json()["code"] == "posting_draft_queue_required"


def test_cleared_draft_publication_returns_the_row_to_draft_on_platform_not_planned(api_env):
    client, api, registry, video, export, _ = api_env
    queue_id, draft_job = _drafted_queue_row(api_env)
    prepared = client.post("/api/tiktok-autopost/prepare", json=_publish_payload(api_env, queue_id, schedule_date="2030-01-02", schedule_time="09:00")).json()
    assert client.post("/api/tiktok-autopost/clear", json={"job_id": prepared["job_id"]}).status_code == 200
    row = _queue_get(queue_id)
    assert row["status"] == "draft_on_platform"                                    # the draft still exists on TikTok
    assert row["posting_job_id"] == draft_job
    # and it can be published again afterwards
    again = client.post("/api/tiktok-autopost/prepare", json=_publish_payload(api_env, queue_id, schedule_date="2030-01-03", schedule_time="10:00"))
    assert again.status_code == 200, again.text
