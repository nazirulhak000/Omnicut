from copy import deepcopy
import hashlib
import json
import sqlite3

from scripts.hyperframes_activity import hyperframes_activity_tasks
from scripts.hyperframes_recovery import read_hyperframes_jobs, recover_hyperframes_work


class Jobs:
    def __init__(self, rows):
        self.rows = deepcopy(rows)
        self.executed = []
    def recover_interrupted(self, owner, *, alive=None):
        changed = []
        for row in self.rows:
            if row.get("channel_id") == owner and row["status"] == "rendering" and not row.get("live", False):
                row["status"] = "interrupted"
                changed.append(row["id"])
        return changed
    def list(self, owner):
        return deepcopy([row for row in self.rows if row.get("channel_id") == owner])
    def execute(self, owner, job_id):
        self.executed.append((owner, job_id))


class Finalizer:
    def __init__(self):
        self.resumed = []
    def resume(self, owner, job_id):
        self.resumed.append((owner, job_id))


def mirror(root, rows, name="hyperframes_render_jobs.json"):
    path = root / "_Docs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_empty_workspace_recovery_and_activity_are_readonly(tmp_path):
    assert recover_hyperframes_work(tmp_path)["counts"] == {"interrupted": 0, "queued": 0, "finalizing": 0}
    assert hyperframes_activity_tasks(tmp_path, "main") == []
    assert list(tmp_path.iterdir()) == []


def test_recovery_only_queued_and_approved_intent_not_failed_or_conflict(tmp_path):
    rows = [{"id": "queued", "channel_id": "main", "status": "queued"},
            {"id": "dead", "channel_id": "main", "status": "rendering"},
            {"id": "live", "channel_id": "main", "status": "rendering", "live": True},
            {"id": "failed", "channel_id": "main", "status": "failed"},
            {"id": "finalize", "channel_id": "main", "status": "finalizing", "finalize_intent": {"id": "approved"}},
            {"id": "no-approval", "channel_id": "main", "status": "finalizing"},
            {"id": "conflict", "channel_id": "main", "status": "recovery_required", "finalize_intent": {"id": "approved"}}]
    mirror(tmp_path, rows)
    jobs, finalizer = Jobs(rows), Finalizer()
    report = recover_hyperframes_work(tmp_path, jobs=jobs, finalizer=finalizer,
                                     dispatch=lambda fn, *args: fn(*args), channel_allowed=lambda owner: True)
    assert report["counts"] == {"interrupted": 1, "queued": 1, "finalizing": 1}
    assert jobs.executed == [("main", "queued")]
    assert finalizer.resumed == [("main", "finalize")]
    assert report["errors"] == []


def test_archived_and_unknown_owners_not_dispatched_but_orphans_reconciled(tmp_path):
    rows = [{"id": "queued-main", "channel_id": "main", "status": "queued"},
            {"id": "queued-archived", "channel_id": "archived", "status": "queued"},
            {"id": "dead-archived", "channel_id": "archived", "status": "rendering"},
            {"id": "unknown", "channel_id": "missing", "status": "queued"}]
    mirror(tmp_path, rows)
    jobs = Jobs(rows)
    report = recover_hyperframes_work(tmp_path, jobs=jobs, dispatch=lambda fn, *args: fn(*args),
                                     channel_allowed=lambda owner: owner == "main")
    assert report["interrupted"] == ["dead-archived"]
    assert jobs.executed == [("main", "queued-main")]
    assert report["blocked_channels"] == ["archived", "missing"]


def test_service_adapter_and_dispatch_counts_do_not_claim_completion(tmp_path):
    rows = [{"id": "queued", "channel_id": "main", "status": "queued"}]
    mirror(tmp_path, rows)
    jobs = Jobs(rows)
    class Service:
        renders = jobs
        finalizer = Finalizer()
    dispatched = []
    report = recover_hyperframes_work(tmp_path, service=Service(), dispatch=lambda fn, *args: dispatched.append((fn, args)),
                                     channel_allowed=lambda owner: True)
    assert report["counts"]["queued"] == 1
    assert jobs.executed == []
    assert dispatched[0][1] == ("main", "queued")


def test_owner_failure_does_not_stop_other_channel_recovery(tmp_path):
    rows = [{"id": "one", "channel_id": "first", "status": "queued"},
            {"id": "two", "channel_id": "second", "status": "queued"}]
    mirror(tmp_path, rows)
    jobs = Jobs(rows)
    def allowed(owner):
        if owner == "first":
            raise ValueError("bad registry owner")
        return True
    result = recover_hyperframes_work(tmp_path, jobs=jobs, channel_allowed=allowed, dispatch=lambda fn, *args: fn(*args))
    assert result["errors"][0]["channel_id"] == "first"
    assert jobs.executed == [("second", "two")]


def test_existing_non_hf_database_does_not_create_hf_tables_or_mirrors(tmp_path):
    database = tmp_path / "_Docs/store.db"
    database.parent.mkdir()
    with sqlite3.connect(database) as conn:
        conn.execute("CREATE TABLE other(data TEXT)")
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    assert read_hyperframes_jobs(tmp_path) == []
    assert recover_hyperframes_work(tmp_path)["queued_dispatched"] == []
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    assert list(database.parent.iterdir()) == [database]


def test_activity_is_scoped_readonly_preserves_unknown_state_and_no_fake_progress(tmp_path):
    render = [{"id": "r1", "channel_id": "main", "project_id": "p", "status": "rendering", "phase": "capturing"},
              {"id": "r2", "channel_id": "other", "status": "queued"},
              {"id": "r3", "channel_id": "main", "status": "future_status"},
              {"id": "r4", "channel_id": "main", "status": "qc_ready"}]
    creative = [{"id": "c1", "channel_id": "main", "status": "submitted", "created_at": 1000,
                 "error": {"message": "note", "code": "known"}}]
    paths = [mirror(tmp_path, render), mirror(tmp_path, creative, "creative_jobs.json")]
    before = [path.read_bytes() for path in paths]
    tasks = hyperframes_activity_tasks(tmp_path, "main")
    by_id = {task["id"]: task for task in tasks}
    assert set(by_id) == {"r1", "r3", "r4", "c1"}
    assert by_id["r1"]["status"] == "processing" and by_id["r1"]["progress"] is None
    assert by_id["r1"]["step_label"] == "capturing"
    assert by_id["r3"]["status"] == "future_status" and by_id["r3"]["progress"] is None
    assert by_id["r4"]["status"] == "awaiting_review"
    assert by_id["c1"]["progress"] == 1
    assert by_id["c1"]["error"] == "note"
    assert by_id["c1"]["created_at"] == "1970-01-01T00:16:40+00:00"
    assert [path.read_bytes() for path in paths] == before
    assert not (tmp_path / "_Docs/store.db").exists()


def test_sqlite_canonical_jobs_take_precedence_over_stale_mirror(tmp_path):
    mirror(tmp_path, [{"id": "stale", "channel_id": "main", "status": "queued"}])
    with sqlite3.connect(tmp_path / "_Docs/store.db") as connection:
        connection.execute("CREATE TABLE hyperframes_render_jobs(data TEXT)")
        connection.execute("INSERT INTO hyperframes_render_jobs VALUES (?)", (json.dumps({"id": "fresh", "channel_id": "main", "status": "finalized"}),))
    assert read_hyperframes_jobs(tmp_path)[0]["id"] == "fresh"


def test_malformed_mirror_reports_error_without_new_store(tmp_path):
    path = mirror(tmp_path, [])
    path.write_text("{broken", encoding="utf-8")
    report = recover_hyperframes_work(tmp_path)
    assert report["errors"][0]["phase"] == "read"
    assert not (tmp_path / "_Docs/store.db").exists()
