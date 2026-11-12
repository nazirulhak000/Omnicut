"""Round CLAUDE-AUTOPOST-E2E-FIXES-20261113: regressions for the end-to-end autopost audit.

Offline, temporary storage only (fixtures from test_channel_posting_protocol / test_publication_observations).
Finding ids refer to _Docs/Reports/AUTOPOST_END_TO_END_AUDIT_20261113.md.
"""
import datetime as dt
import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

import pytest

from scripts.channel_store import ChannelError
from scripts.posting_jobs import PostingJobStore, fingerprint
from scripts.publication_observations import PublicationObservationStore
from tests.test_channel_posting_protocol import D1, action_body, api_env, prepared_claimed_api  # noqa: F401

BKK = dt.timezone(dt.timedelta(hours=7))


def _queue(rows_to_add):
    from scripts.schedule_store import ScheduleQueueStore
    with ScheduleQueueStore.transaction(channel_id="main") as rows:
        rows.extend(rows_to_add)


def _queue_rows():
    from scripts.schedule_store import ScheduleQueueStore
    return ScheduleQueueStore.list_items(channel_id="main")


# ---- B11: TikTok's scheduling window ----

def test_schedule_window_refuses_past_too_soon_too_far_and_off_step():
    from scripts import api_tiktok_autopost as api
    now = dt.datetime(2026, 11, 13, 10, 0, tzinfo=BKK)
    api._check_schedule_window("2026-11-13", "10:15", now=now)            # exactly 15 minutes: ok
    api._check_schedule_window("2026-11-23", "10:00", now=now)            # exactly 10 days: ok
    for date, time, code in [("2026-11-13", "09:00", "posting_slot_too_soon"),
                             ("2026-11-13", "10:10", "posting_slot_too_soon"),
                             ("2026-11-23", "10:05", "posting_slot_too_far"),
                             ("2026-11-14", "10:03", "posting_schedule_invalid"),
                             ("2026-13-01", "10:00", "posting_schedule_invalid")]:
        with pytest.raises(ChannelError) as exc:
            api._check_schedule_window(date, time, now=now)
        assert exc.value.code == code


def test_prepare_refuses_a_slot_tiktok_would_reject_before_any_job_exists(api_env):
    client, api, registry, video, export, _ = api_env
    far = (dt.datetime.now(BKK) + dt.timedelta(days=12)).strftime("%Y-%m-%d")
    res = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"],
                                                             "schedule_date": far, "schedule_time": "09:00"})
    assert res.status_code == 422 and res.json()["code"] == "posting_slot_too_far"
    past = (dt.datetime.now(BKK) - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    res = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"],
                                                             "schedule_date": past, "schedule_time": "09:00"})
    assert res.status_code == 422 and res.json()["code"] == "posting_slot_too_soon"
    assert api._jobs().table.load() == []


# ---- A3 / B5: a newer prepare replaces a never-claimed job; a failed prepare leaves nothing blocking ----

def test_new_prepare_supersedes_unclaimed_job_and_frees_its_queue_row(api_env):
    client, api, registry, video, export, _ = api_env
    _queue([{"id": "q-a3", "channel_id": "main", "export_id": export["id"], "status": "planned"}])
    first = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": "q-a3"}).json()
    assert [r for r in _queue_rows() if r["id"] == "q-a3"][0]["posting_job_id"] == first["job_id"]
    # same clip prepared again (e.g. from the exports list): no 409, the old job is replaced, the row follows the new one
    second = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": "q-a3",
                                                                "idempotency_key": "second"})
    assert second.status_code == 200, second.text
    assert api._jobs().get("main", first["job_id"])["status"] == "cancelled"
    row = [r for r in _queue_rows() if r["id"] == "q-a3"][0]
    assert row["status"] == "ready_for_extension" and row["posting_job_id"] == second.json()["job_id"]


def test_claimed_job_is_never_superseded(api_env):
    client, api, registry, video, export, _ = api_env
    prepared_claimed_api(api_env)
    again = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "idempotency_key": "x2"})
    assert again.status_code == 409 and again.json()["code"] == "posting_export_already_prepared"


def test_expired_claim_reprepare_resets_row_then_binds_new_job(api_env):
    client, api, registry, video, export, _ = api_env
    _queue([{"id": "q-b5", "channel_id": "main", "export_id": export["id"], "status": "planned"}])
    first = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": "q-b5"}).json()
    client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": first["job_id"], "lease_owner": "ext-dead"})
    with api._jobs().table.scoped_mutate("main") as rows:
        rows[0]["lease_expires_at"] = 1.0                       # the extension died, its lease ran out
    again = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": "q-b5",
                                                               "idempotency_key": "again"})
    assert again.status_code == 200, again.text
    assert [r for r in _queue_rows() if r["id"] == "q-b5"][0]["posting_job_id"] == again.json()["job_id"]
    assert api._jobs().pending("main")["job_id"] == again.json()["job_id"]


# ---- B13: nothing pressed = nothing can be confirmed ----

def test_reconcile_of_never_attempted_claim_is_refused(api_env):
    client, api, registry, video, export, _ = api_env
    row = prepared_claimed_api(api_env)
    res = client.post("/api/tiktok-autopost/reconcile", json={**action_body(row), "outcome": "published",
                      "proof": {"kind": "manual_user_confirmation", "notice": "ผู้ใช้ยืนยันว่าโพสต์แล้ว"}})
    assert res.status_code == 409 and res.json()["code"] == "posting_not_attempted"
    assert registry.get(export["id"], channel_id="main")["status"] != "posted"
    assert video.exists()


# ---- B9 / A2 / B4: effects ----

def test_published_queue_row_gets_posted_at(api_env):
    client, api, registry, video, export, _ = api_env
    _queue([{"id": "q-b9", "channel_id": "main", "export_id": export["id"], "status": "planned"}])
    prepared = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"], "queue_id": "q-b9"}).json()
    row = client.post("/api/tiktok-autopost/claim", json={"protocol_version": 2, "job_id": prepared["job_id"], "lease_owner": "ext"}).json()
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    done = client.post("/api/tiktok-autopost/ack", json={**action_body(started), "outcome": "published",
                       "proof": {"kind": "platform_success_notice", "notice": "Video published", "confirmation_token": started.get("confirmation_token")}})
    assert done.status_code == 200, done.text
    queued = [r for r in _queue_rows() if r["id"] == "q-b9"][0]
    assert queued["status"] == "posted"
    assert dt.datetime.fromisoformat(queued["posted_at"]).utcoffset() is not None


def test_scheduled_without_queue_id_reuses_the_planned_row_and_writes_minute_slots(api_env):
    client, api, registry, video, export, _ = api_env
    _queue([{"id": "q-a2", "channel_id": "main", "export_id": export["id"], "status": "planned",
             "scheduled_at": f"{D1}T19:00+07:00", "created_at": "2026-11-01T00:00:00+00:00"}])
    row = prepared_claimed_api(api_env, schedule_date=D1, schedule_time="09:00")      # prepared from the exports list
    started = client.post("/api/tiktok-autopost/attempt", json=action_body(row)).json()
    done = client.post("/api/tiktok-autopost/ack", json={**action_body(started), "outcome": "scheduled_on_platform",
                       "proof": {"kind": "platform_success_notice", "notice": "Scheduled successfully", "confirmation_token": started.get("confirmation_token")}})
    assert done.status_code == 200, done.text
    rows = [r for r in _queue_rows() if r.get("export_id") == export["id"]]
    assert len(rows) == 1, rows                         # one clip = one row, never a second "planned" copy
    assert rows[0]["id"] == "q-a2" and rows[0]["status"] == "scheduled_on_platform"
    assert rows[0]["scheduled_at"] == f"{D1}T09:00+07:00"


def test_draft_row_without_slot_does_not_break_queue_sorting():
    from scripts.api_schedule_queue import sort_records
    rows = [{"id": "b", "scheduled_at": None}, {"id": "a", "scheduled_at": "2026-11-14T09:00+07:00"},
            {"id": "c", "scheduled_at": "2026-11-13T09:00+07:00", "created_at": None}]
    assert [r["id"] for r in sort_records(rows)] == ["c", "a", "b"]


# ---- B15: a job whose file changed must not block /pending ----

def test_pending_skips_a_job_whose_export_changed(api_env):
    client, api, registry, video, export, _ = api_env
    first = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(video), "export_id": export["id"]}).json()
    other_video = video.parent / "second.mp4"
    other_video.write_bytes(b"another clip")
    other = registry.ensure(other_video, channel_id="main")
    second = client.post("/api/tiktok-autopost/prepare", json={"video_path": str(other_video), "export_id": other["id"]}).json()
    assert client.get("/api/tiktok-autopost/pending").json()["job_id"] == first["job_id"]
    video.write_bytes(b"re-rendered in place")                    # e.g. auto-sharpen overwrote it after preparing
    assert client.get("/api/tiktok-autopost/pending").json()["job_id"] == second["job_id"]


# ---- C19: covers belong to their channel ----

def test_main_cannot_use_another_channels_cover_folder(api_env, monkeypatch):
    client, api, *_ = api_env
    import scripts.channel_store as cs

    class _Store:
        def list_channels(self, include_archived=True):
            return [{"id": "main"}, {"id": "second"}]
    monkeypatch.setattr(cs, "get_default_store", lambda: _Store())
    covers = api.COVERS_DIR
    for sub in ("second", "main", "product_cover_prototypes"):
        (covers / sub).mkdir(exist_ok=True)
    assert api._cover_in_channel(covers / "flat.jpg", "main")
    assert api._cover_in_channel(covers / "main" / "a.jpg", "main")
    assert api._cover_in_channel(covers / "product_cover_prototypes" / "a.jpg", "main")
    assert not api._cover_in_channel(covers / "second" / "a.jpg", "main")
    assert api._cover_in_channel(covers / "second" / "a.jpg", "second")
    assert not api._cover_in_channel(covers / "flat.jpg", "second")


# ---- C20: hash cache follows file changes ----

def test_digest_cache_rehashes_after_rewrite(tmp_path):
    import os
    from scripts import api_tiktok_autopost as api
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"one")
    first = api._file_digest(path)
    assert api._file_digest(path) == first
    path.write_bytes(b"two!")
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
    assert api._file_digest(path) != first


# ---- B2: a scheduled post is closed from its Content-page row ----

@pytest.fixture
def scheduled_domain(tmp_path):
    jobs = PostingJobStore(tmp_path, clock=lambda: 1000.0)
    job = jobs.prepare("main", {"export_id": "exp-1", "target_handle": "@mainuser", "strict_mode": True,
                                "caption": "ลมแรงเงียบ พัดลม Hatari ตัวนี้ดีจริง", "hashtags": "#พัดลม #EP12", "episode_no": 12,
                                "schedule_date": "2026-11-10", "schedule_time": "16:20"})
    job = jobs.claim("main", job["id"], "worker")
    job = jobs.validate_action("main", job["id"], "worker", job["lease_token"], job["revision"], "@mainuser", begin_publish=True)
    job = jobs.acknowledge("main", job["id"], "worker", job["lease_token"], job["revision"], "@mainuser",
                           "scheduled_on_platform", {"kind": "platform_success_notice", "notice": "Video published"})
    return PublicationObservationStore(tmp_path, jobs=jobs, clock=lambda: 1000.0), job


def _content_evidence(job, caption):
    return {"kind": "platform_publication", "source": "platform_detail", "published": True, "job_id": job["id"],
            "channel_id": "main", "source_account": "@mainuser", "platform_video_id": "7391234567890",
            "linkage": {"method": "content_row", "caption_text": caption}}


def test_content_row_with_same_caption_ep_and_time_links_the_scheduled_post(scheduled_domain):
    store, job = scheduled_domain
    assert not (job["receipt"]["proof"].get("platform_post_id"))      # a scheduled toast carries no video id
    row = store.observe("main", job["id"], "@mainuser", "7391234567890", "2026-11-10T16:20:00+07:00",
                        _content_evidence(job, "ลมแรงเงียบ พัดลม Hatari ตัวนี้ดีจริง #พัดลม #EP12"), idempotency_key="k1")
    assert row["status"] == "verified"


@pytest.mark.parametrize("caption,when", [
    ("ลมแรงเงียบ พัดลม Hatari ตัวอื่นเลย #EP12", "2026-11-10T16:20:00+07:00"),         # different caption
    ("ลมแรงเงียบ พัดลม Hatari ตัวนี้ดีจริง #EP13", "2026-11-10T16:20:00+07:00"),       # another clip's EP
    ("ลมแรงเงียบ พัดลม Hatari ตัวนี้ดีจริง #EP12", "2026-11-10T18:00:00+07:00"),       # another time
])
def test_content_row_mismatch_is_refused(scheduled_domain, caption, when):
    store, job = scheduled_domain
    with pytest.raises(ChannelError) as exc:
        store.observe("main", job["id"], "@mainuser", "7391234567890", when, _content_evidence(job, caption), idempotency_key="k2")
    assert exc.value.code == "publication_linkage_mismatch"


# ---- A1: posted exports stay posted, whatever a tool writes ----

def test_store_io_never_turns_a_posted_export_back_to_rendered(tmp_path):
    from scripts import store_io
    docs = tmp_path / "_Docs"
    docs.mkdir()
    with store_io.mutate_export_registry(docs) as rows:
        rows.append({"id": "exp-p", "path": "04_Exports/Ready_to_post/a.mp4", "status": "posted", "posted_at": "2026-11-10T20:15:24+07:00"})
        rows.append({"id": "exp-r", "path": "04_Exports/Ready_to_post/b.mp4", "status": "rendered", "posted_at": None})
    with store_io.mutate_export_registry(docs) as rows:
        for row in rows:
            row["status"] = "rendered"
            row["posted_at"] = None
    stored = {r["id"]: r for r in store_io.load_export_registry(docs)}
    assert stored["exp-p"]["status"] == "posted" and stored["exp-p"]["posted_at"] == "2026-11-10T20:15:24+07:00"
    assert stored["exp-r"]["status"] == "rendered"


def test_retired_queue_rewriting_tools_refuse_to_run():
    import importlib
    for name in ("tools.batch_schedule_non_couple_exports", "tools.reschedule_all_old_non_couple_clips", "tools.reschedule_47_unposted_clips"):
        module = importlib.import_module(name)
        with pytest.raises(SystemExit) as exc:
            module.main()
        assert exc.value.code == 2


# ---- C17: portable uploader server ----

def test_portable_server_contains_paths_and_needs_the_lease(tmp_path, monkeypatch):
    from tools import portable_uploader_server as server
    monkeypatch.setattr(server, "VAULT_ROOT", tmp_path)
    (tmp_path / "clip.mp4").write_bytes(b"v")
    (tmp_path / "queue.json").write_text(json.dumps([{"id": "q1"}, {"id": "q2"}]), encoding="utf-8")
    assert server._inside_vault("clip.mp4") == (tmp_path / "clip.mp4").resolve()
    assert server._inside_vault("../outside.txt") is None
    assert server._inside_vault("C:/Windows/win.ini") is None
    monkeypatch.setattr(server, "_CURRENT_JOB", None)
    httpd = HTTPServer(("127.0.0.1", 0), server.PortableRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def post(path, body):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")
    try:
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(base + "/api/media/..%2F..%2Fsecret.txt")
        assert exc.value.code == 404
        status, job = post("/api/tiktok-autopost/prepare", {"video_path": "clip.mp4", "queue_id": "q2"})
        assert status == 200
        status, _ = post("/api/tiktok-autopost/ack", {"job_id": job["job_id"], "outcome": "published"})
        assert status == 409                                        # no lease token
        status, claimed = post("/api/tiktok-autopost/claim", {"job_id": job["job_id"]})
        status, _ = post("/api/tiktok-autopost/ack", {"job_id": job["job_id"], "lease_token": claimed["lease_token"],
                                                       "outcome": "confirmation_unknown"})
        assert status == 200
        queue = json.loads((tmp_path / "queue.json").read_text(encoding="utf-8"))
        assert [q.get("status") for q in queue] == [None, "confirmation_unknown"]    # never the first row, never "posted"
    finally:
        httpd.shutdown()
        httpd.server_close()


# ---- C18: phone handoff never shares a clip with a working extension ----

def test_mobile_handoff_refuses_a_live_extension_claim(tmp_path, monkeypatch):
    from scripts import api_mobile_posting as mobile, config
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    jobs = PostingJobStore(tmp_path)
    job = jobs.prepare("main", {"export_id": "exp-m", "queue_id": "q-m", "target_handle": "@mainuser", "strict_mode": False})
    jobs.mark_prepare_effects("main", job["id"])
    jobs.claim("main", job["id"], "ext-live")
    with pytest.raises(Exception) as exc:
        mobile._sync_posting_job_on_handoff("main", "q-m", "exp-m", "phone:1")
    assert getattr(exc.value, "status_code", None) == 409
    assert jobs.get("main", job["id"])["status"] == "claimed"


def test_mobile_parked_job_returns_prepared_and_is_cancellable(tmp_path, monkeypatch):
    from scripts import api_mobile_posting as mobile, config
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    jobs = PostingJobStore(tmp_path)
    job = jobs.prepare("main", {"export_id": "exp-m2", "queue_id": "q-m2", "target_handle": "@mainuser", "strict_mode": False})
    mobile._sync_posting_job_on_handoff("main", "q-m2", "exp-m2", "phone:1")
    assert jobs.get("main", job["id"])["status"] == "awaiting_post"
    assert jobs.cancel("main", job["id"])["status"] == "cancelled"


def test_mobile_confirm_writes_a_verifiable_receipt(tmp_path, monkeypatch):
    from scripts import api_mobile_posting as mobile, config
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    jobs = PostingJobStore(tmp_path)
    job = jobs.prepare("main", {"export_id": "exp-m3", "queue_id": "q-m3", "target_handle": "@mainuser", "strict_mode": False})
    mobile._sync_posting_job_on_confirm("main", "q-m3", "exp-m3", "published", "2026-11-13T10:00:00+07:00", None)
    stored = jobs.get("main", job["id"])
    assert stored["status"] == "published"
    assert stored["receipt_hash"] == fingerprint(stored["receipt"])
