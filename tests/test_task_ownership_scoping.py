"""
Ownership scoping for scripts.task_manager.TaskManager and scripts.render_jobs.

These structures are process-wide in-memory (plus a JSON-backed persistence
layer for tasks) with no owner key at all before this change -- the first
step toward multi-tenancy is making them *capable* of ownership scoping
without yet wiring real per-request tenants through auth (that is a later
step; see _Docs/SAAS_READINESS_PLAN.md item 13).

Covers:
- an owner cannot see or mutate another owner's task/job (lookup behaves as
  not-found, never as a permission error that would confirm the id exists)
- an unscoped call (owner_id=None) still works exactly as before scoping
- ids are not sequential/guessable (secrets.token_urlsafe / uuid4)

Plain single-owner lifecycle behavior (create/progress/complete/fail/cancel,
restart recovery) is covered by tests/test_error_handling_recovery.py and
tests/test_phase1_smoke.py -- not duplicated here.
"""

import json
import re

import pytest

from scripts.task_manager import TaskManager, TaskStatus, DEFAULT_OWNER
from scripts import render_jobs


# ----------------------------------------------------------------------
# TaskManager ownership scoping
# ----------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolated_task_registry(tmp_path, monkeypatch):
    """Never touch the real 03_Projects/task_registry.json.

    The module binds TASKS_FILE/STORAGE_DIR at import time, so patch the
    binding on scripts.task_manager itself (not scripts.config) and reset
    the in-memory state each test.
    """
    fake_tasks_file = tmp_path / "task_registry.json"
    monkeypatch.setattr("scripts.task_manager.TASKS_FILE", fake_tasks_file)
    monkeypatch.setattr("scripts.task_manager.STORAGE_DIR", tmp_path)
    TaskManager._initialized = False
    TaskManager._tasks = {}
    TaskManager.initialize()
    yield
    TaskManager._initialized = False
    TaskManager._tasks = {}


def test_create_task_defaults_owner_when_unspecified():
    task = TaskManager.create_task(task_type="render_video", title="t1")
    assert task["owner_id"] == DEFAULT_OWNER


def test_create_task_honors_explicit_owner():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    assert task["owner_id"] == "tenant_a"


def test_get_task_hides_other_owners_task():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    assert TaskManager.get_task(task["id"], owner_id="tenant_b") is None
    # Not-found for a wrong owner must look identical to a genuinely missing id.
    assert TaskManager.get_task(task["id"], owner_id="tenant_b") == TaskManager.get_task("does-not-exist", owner_id="tenant_b")


def test_get_task_returns_task_for_correct_owner():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    fetched = TaskManager.get_task(task["id"], owner_id="tenant_a")
    assert fetched is not None
    assert fetched["id"] == task["id"]


def test_get_task_unscoped_call_still_works_like_before():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    # No owner_id passed at all -- exactly today's single-user call shape.
    fetched = TaskManager.get_task(task["id"])
    assert fetched is not None and fetched["id"] == task["id"]


def test_get_active_tasks_filters_by_owner():
    TaskManager.create_task(task_type="render_video", title="a1", owner_id="tenant_a")
    TaskManager.create_task(task_type="render_video", title="a2", owner_id="tenant_a")
    TaskManager.create_task(task_type="render_video", title="b1", owner_id="tenant_b")

    a_tasks = TaskManager.get_active_tasks(owner_id="tenant_a")
    assert {t["title"] for t in a_tasks} == {"a1", "a2"}

    b_tasks = TaskManager.get_active_tasks(owner_id="tenant_b")
    assert {t["title"] for t in b_tasks} == {"b1"}

    # Unscoped listing (today's behavior) still returns everyone.
    everyone = TaskManager.get_active_tasks()
    assert {t["title"] for t in everyone} == {"a1", "a2", "b1"}


def test_update_progress_rejects_wrong_owner():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    result = TaskManager.update_progress(task["id"], 0.5, owner_id="tenant_b")
    assert result is None
    # The task itself must be untouched by the rejected cross-owner call.
    assert TaskManager.get_task(task["id"], owner_id="tenant_a")["progress"] == 0.0


def test_update_progress_allows_correct_owner():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    result = TaskManager.update_progress(task["id"], 0.5, owner_id="tenant_a")
    assert result is not None
    assert result["progress"] == 0.5


def test_complete_task_rejects_wrong_owner():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    assert TaskManager.complete_task(task["id"], owner_id="tenant_b") is None
    assert TaskManager.get_task(task["id"], owner_id="tenant_a")["status"] == TaskStatus.QUEUED


def test_fail_task_rejects_wrong_owner():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    assert TaskManager.fail_task(task["id"], "boom", owner_id="tenant_b") is None
    assert TaskManager.get_task(task["id"], owner_id="tenant_a")["status"] == TaskStatus.QUEUED


def test_cancel_task_rejects_wrong_owner():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    assert TaskManager.cancel_task(task["id"], owner_id="tenant_b") is None
    assert TaskManager.get_task(task["id"], owner_id="tenant_a")["status"] == TaskStatus.QUEUED


def test_delete_task_rejects_wrong_owner_then_allows_real_owner():
    task = TaskManager.create_task(task_type="render_video", title="t1", owner_id="tenant_a")
    assert TaskManager.delete_task(task["id"], owner_id="tenant_b") is False
    assert TaskManager.get_task(task["id"], owner_id="tenant_a") is not None
    assert TaskManager.delete_task(task["id"], owner_id="tenant_a") is True
    assert TaskManager.get_task(task["id"], owner_id="tenant_a") is None


def test_clear_completed_only_clears_the_scoped_owners_tasks():
    a = TaskManager.create_task(task_type="render_video", title="a1", owner_id="tenant_a")
    b = TaskManager.create_task(task_type="render_video", title="b1", owner_id="tenant_b")
    TaskManager.complete_task(a["id"], owner_id="tenant_a")
    TaskManager.complete_task(b["id"], owner_id="tenant_b")

    cleared = TaskManager.clear_completed(owner_id="tenant_a")
    assert cleared == 1
    assert TaskManager.get_task(a["id"], owner_id="tenant_a") is None
    # tenant_b's completed task must survive tenant_a's cleanup.
    assert TaskManager.get_task(b["id"], owner_id="tenant_b") is not None


def test_tasks_without_owner_field_are_treated_as_default_owner():
    """Data persisted before this change has no "owner_id" key at all."""
    task = TaskManager.create_task(task_type="render_video", title="legacy")
    del TaskManager._tasks[task["id"]]["owner_id"]

    # An unscoped lookup still finds it.
    assert TaskManager.get_task(task["id"]) is not None
    # Scoped to the well-known default owner, it is also visible.
    assert TaskManager.get_task(task["id"], owner_id=DEFAULT_OWNER) is not None
    # But not visible to an unrelated tenant.
    assert TaskManager.get_task(task["id"], owner_id="tenant_x") is None


# ----------------------------------------------------------------------
# TaskManager id generation
# ----------------------------------------------------------------------

def test_task_ids_are_not_sequential_or_timestamp_based():
    ids = [TaskManager.create_task(task_type="render_video", title=f"t{i}")["id"] for i in range(5)]
    # The old scheme was f"task_{ms_timestamp}_{6 hex chars}" -- sortable and
    # walkable. The new scheme must not share that shape.
    assert all(not re.match(r"^task_\d+_[0-9a-f]{6}$", i) for i in ids)
    # No id should be a prefix of another (rules out simple incrementing counters).
    for i, id_a in enumerate(ids):
        for id_b in ids[i + 1:]:
            assert not id_b.startswith(id_a) and not id_a.startswith(id_b)


def test_task_ids_have_meaningful_entropy():
    ids = {TaskManager.create_task(task_type="render_video", title="t")["id"] for _ in range(20)}
    assert len(ids) == 20  # no collisions
    for i in ids:
        assert len(i) >= 16  # secrets.token_urlsafe(16) yields a long, high-entropy string


def test_explicit_task_id_still_honored():
    """render_jobs passes its own uuid4 job_id in as task_id -- must not be overridden."""
    task = TaskManager.create_task(task_type="render_video", title="t", task_id="explicit-id-123")
    assert task["id"] == "explicit-id-123"


# ----------------------------------------------------------------------
# render_jobs ownership scoping
# ----------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_active_jobs():
    render_jobs.ACTIVE_JOBS.clear()
    yield
    render_jobs.ACTIVE_JOBS.clear()


def test_render_job_defaults_owner_when_unspecified():
    job = render_jobs.create_job("job-1")
    assert job["owner_id"] == render_jobs.DEFAULT_OWNER


def test_render_job_honors_explicit_owner():
    job = render_jobs.create_job("job-1", owner_id="tenant_a")
    assert job["owner_id"] == "tenant_a"


def test_get_job_hides_other_owners_job():
    render_jobs.create_job("job-1", owner_id="tenant_a")
    assert render_jobs.get_job("job-1", owner_id="tenant_b") is None
    # Not-found for a wrong owner looks identical to a genuinely missing id.
    assert render_jobs.get_job("job-1", owner_id="tenant_b") == render_jobs.get_job("does-not-exist", owner_id="tenant_b")


def test_get_job_returns_job_for_correct_owner():
    render_jobs.create_job("job-1", owner_id="tenant_a")
    job = render_jobs.get_job("job-1", owner_id="tenant_a")
    assert job is not None and job["id"] == "job-1"


def test_get_job_unscoped_call_still_works_like_before():
    render_jobs.create_job("job-1", owner_id="tenant_a")
    assert render_jobs.get_job("job-1") is not None


def test_render_jobs_update_progress_rejects_wrong_owner():
    render_jobs.create_job("job-1", owner_id="tenant_a")
    render_jobs.update_progress("job-1", 0.5, "working", owner_id="tenant_b")
    job = render_jobs.get_job("job-1", owner_id="tenant_a")
    assert job["progress"] == 0.0
    assert job["status"] == "queued"


def test_render_jobs_update_progress_allows_correct_owner():
    render_jobs.create_job("job-1", owner_id="tenant_a")
    render_jobs.update_progress("job-1", 0.5, "working", owner_id="tenant_a")
    job = render_jobs.get_job("job-1", owner_id="tenant_a")
    assert job["progress"] == 0.5


def test_render_jobs_complete_job_rejects_wrong_owner():
    render_jobs.create_job("job-1", owner_id="tenant_a")
    render_jobs.complete_job("job-1", {"project_name": "p"}, owner_id="tenant_b")
    job = render_jobs.get_job("job-1", owner_id="tenant_a")
    assert job["status"] == "queued"


def test_render_jobs_fail_job_rejects_wrong_owner():
    render_jobs.create_job("job-1", owner_id="tenant_a")
    render_jobs.fail_job("job-1", RuntimeError("boom"), owner_id="tenant_b")
    job = render_jobs.get_job("job-1", owner_id="tenant_a")
    assert job["status"] == "queued"


def test_render_jobs_without_owner_field_are_treated_as_default_owner():
    job = render_jobs.create_job("legacy-job")
    del render_jobs.ACTIVE_JOBS["legacy-job"]["owner_id"]

    assert render_jobs.get_job("legacy-job") is not None
    assert render_jobs.get_job("legacy-job", owner_id=render_jobs.DEFAULT_OWNER) is not None
    assert render_jobs.get_job("legacy-job", owner_id="tenant_x") is None
