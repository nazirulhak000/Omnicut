"""
Tests for scripts/task_manager.py -- the background-task state machine.

TaskManager holds background-task state (_tasks, a class-level dict)
persisted to 03_Projects/task_registry.json and is consulted by
scripts/api_tasks.py. An untested state machine here is a classic source
of stuck/zombie tasks (a task stuck "processing" forever) or of tasks
silently vanishing on restart. This file has never had direct coverage.

Isolated / offline per .agents/rules/testing_standard.md: every test
monkeypatches scripts.task_manager.TASKS_FILE to a tmp_path file AND
resets the class-level TaskManager._tasks / _initialized state, since
`import scripts.config` alone would not stop this module reading its own
module-level TASKS_FILE binding. The real 03_Projects/task_registry.json
is never read or written by these tests.
"""
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.task_manager as tm_module
from scripts.task_manager import TaskManager, TaskStatus


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Point TaskManager at a scratch registry file and reset all
    class-level state so no task leaks in from another test or from the
    real project registry (which was already loaded once at process
    import time before this fixture ever runs)."""
    registry_file = tmp_path / "task_registry.json"
    monkeypatch.setattr(tm_module, "TASKS_FILE", registry_file)
    monkeypatch.setattr(TaskManager, "_tasks", {})
    monkeypatch.setattr(TaskManager, "_initialized", False)
    monkeypatch.setattr(TaskManager, "_last_disk_save", 0.0)
    yield registry_file


# ---------------------------------------------------------------------------
# Full lifecycle: create -> update_progress -> complete/fail/cancel
# ---------------------------------------------------------------------------

def test_create_task_registers_with_queued_status_and_zero_progress():
    task = TaskManager.create_task(task_type="render", title="Render video")
    assert task["status"] == TaskStatus.QUEUED
    assert task["progress"] == 0.0
    assert task["result"] is None
    assert task["error"] is None
    assert task["completed_at"] is None
    assert len(task["logs"]) == 1

    fetched = TaskManager.get_task(task["id"])
    assert fetched is not None
    assert fetched["id"] == task["id"]


def test_create_task_uses_caller_supplied_task_id_when_given():
    task = TaskManager.create_task(task_type="render", title="X", task_id="my_custom_id")
    assert task["id"] == "my_custom_id"
    assert TaskManager.get_task("my_custom_id") is not None


def test_update_progress_transitions_queued_to_processing_and_clamps_range():
    task = TaskManager.create_task(task_type="render", title="X")
    updated = TaskManager.update_progress(task["id"], progress=0.5, step_label="halfway")
    assert updated["status"] == TaskStatus.PROCESSING
    assert updated["progress"] == 0.5
    assert updated["step_label"] == "halfway"

    # Out-of-range values are clamped into [0.0, 1.0].
    over = TaskManager.update_progress(task["id"], progress=5.0)
    assert over["progress"] == 1.0
    under = TaskManager.update_progress(task["id"], progress=-3.0)
    assert under["progress"] == 0.0


def test_update_progress_appends_log_entries_and_caps_at_50():
    task = TaskManager.create_task(task_type="render", title="X")
    for i in range(60):
        TaskManager.update_progress(task["id"], progress=i / 60, msg=f"step {i}")
    fetched = TaskManager.get_task(task["id"])
    assert len(fetched["logs"]) == 50
    # Newest kept, oldest dropped (the very first "step 0" log plus the
    # create_task log should have rolled off).
    assert fetched["logs"][-1]["msg"] == "step 59"


def test_complete_task_sets_terminal_state_and_result():
    task = TaskManager.create_task(task_type="render", title="X")
    TaskManager.update_progress(task["id"], progress=0.9)
    completed = TaskManager.complete_task(task["id"], result={"path": "out.mp4"})

    assert completed["status"] == TaskStatus.COMPLETED
    assert completed["progress"] == 1.0
    assert completed["result"] == {"path": "out.mp4"}
    assert completed["completed_at"] is not None


def test_fail_task_sets_error_and_terminal_state():
    task = TaskManager.create_task(task_type="render", title="X")
    failed = TaskManager.fail_task(task["id"], error="ffmpeg exploded")

    assert failed["status"] == TaskStatus.FAILED
    assert failed["error"] == "ffmpeg exploded"
    assert "ffmpeg exploded" in failed["step_label"]
    assert failed["completed_at"] is not None


def test_cancel_task_sets_cancelled_state():
    task = TaskManager.create_task(task_type="render", title="X")
    cancelled = TaskManager.cancel_task(task["id"])
    assert cancelled["status"] == TaskStatus.CANCELLED
    assert cancelled["completed_at"] is not None


# ---------------------------------------------------------------------------
# get_task / get_active_tasks / delete_task / clear_completed
# ---------------------------------------------------------------------------

def test_get_task_returns_none_for_unknown_id():
    assert TaskManager.get_task("does_not_exist") is None


def test_get_active_tasks_sorted_newest_first_and_respects_limit():
    """_now_iso() has only whole-second resolution, so tasks created in a
    tight loop can share an identical updated_at string -- real recency
    ordering only becomes observable once updated_at actually differs.
    Set updated_at directly (bypassing the clock) to test the sort itself
    rather than racing real wall-clock seconds."""
    ids = []
    for i in range(5):
        t = TaskManager.create_task(task_type="render", title=f"T{i}")
        ids.append(t["id"])

    for i, tid in enumerate(ids):
        TaskManager._tasks[tid]["updated_at"] = f"2026-01-01 00:00:0{i}"

    active = TaskManager.get_active_tasks(limit=3)
    assert len(active) == 3
    # Newest updated_at (T4) should be first.
    assert active[0]["title"] == "T4"
    assert active[1]["title"] == "T3"
    assert active[2]["title"] == "T2"


def test_delete_task_removes_it_and_reports_false_for_missing():
    task = TaskManager.create_task(task_type="render", title="X")
    assert TaskManager.delete_task(task["id"]) is True
    assert TaskManager.get_task(task["id"]) is None
    assert TaskManager.delete_task(task["id"]) is False  # already gone


def test_clear_completed_removes_only_terminal_tasks():
    queued = TaskManager.create_task(task_type="render", title="queued")
    to_complete = TaskManager.create_task(task_type="render", title="done")
    to_fail = TaskManager.create_task(task_type="render", title="failed")
    to_cancel = TaskManager.create_task(task_type="render", title="cancelled")

    TaskManager.complete_task(to_complete["id"])
    TaskManager.fail_task(to_fail["id"], error="oops")
    TaskManager.cancel_task(to_cancel["id"])

    cleared_count = TaskManager.clear_completed()
    assert cleared_count == 3
    assert TaskManager.get_task(queued["id"]) is not None
    assert TaskManager.get_task(to_complete["id"]) is None
    assert TaskManager.get_task(to_fail["id"]) is None
    assert TaskManager.get_task(to_cancel["id"]) is None


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------

def test_update_progress_on_unknown_task_id_returns_none():
    assert TaskManager.update_progress("nope", progress=0.5) is None


def test_update_progress_does_not_reopen_a_completed_task():
    task = TaskManager.create_task(task_type="render", title="X")
    TaskManager.complete_task(task["id"], result="done")
    result = TaskManager.update_progress(task["id"], progress=0.3, step_label="should not apply")

    # Returns the task unchanged rather than reopening it.
    assert result["status"] == TaskStatus.COMPLETED
    assert result["progress"] == 1.0
    assert result["step_label"] != "should not apply"


def test_update_progress_does_not_reopen_a_cancelled_task():
    task = TaskManager.create_task(task_type="render", title="X")
    TaskManager.cancel_task(task["id"])
    result = TaskManager.update_progress(task["id"], progress=0.7)
    assert result["status"] == TaskStatus.CANCELLED
    assert result["progress"] == 0.0  # untouched from create_task default


def test_a_terminal_task_stays_terminal():
    """complete_task() and fail_task() leave an already-terminal task alone,
    the way update_progress() and cancel_task() already did.

    Before this guard existed, completing an already-failed task flipped its
    status to COMPLETED while leaving `error` populated -- a record claiming
    both that it failed and that it succeeded.
    """
    task = TaskManager.create_task(task_type="render", title="X")
    TaskManager.fail_task(task["id"], error="first failure")
    result = TaskManager.complete_task(task["id"], result="actually fine now")

    assert result["status"] == TaskStatus.FAILED
    assert result["error"] == "first failure"
    assert result.get("result") != "actually fine now"


def test_failing_an_already_completed_task_leaves_it_completed():
    """The same guard in the other direction."""
    task = TaskManager.create_task(task_type="render", title="X")
    TaskManager.complete_task(task["id"], result="done")
    result = TaskManager.fail_task(task["id"], error="late failure")

    assert result["status"] == TaskStatus.COMPLETED
    assert result["result"] == "done"
    assert "error" not in result or result["error"] != "late failure"


def test_restart_recovery_still_marks_interrupted_tasks_failed():
    """The terminal guard must not block restart recovery.

    initialize() sets the status directly rather than calling fail_task(),
    so an interrupted task is still marked failed on the next start.
    """
    task = TaskManager.create_task(task_type="render", title="interrupted")
    TaskManager.update_progress(task["id"], progress=0.5)

    # Simulate a restart: drop the in-memory state and re-read from disk.
    TaskManager._initialized = False
    TaskManager._tasks = {}
    TaskManager.initialize()

    recovered = TaskManager.get_task(task["id"])
    assert recovered["status"] == TaskStatus.FAILED
    assert "รีสตาร์ท" in recovered["error"]


def test_cancel_task_is_a_noop_on_already_completed_or_failed_task():
    """cancel_task() DOES guard terminal states explicitly (unlike
    complete_task/fail_task above) -- verify that guard actually holds."""
    completed = TaskManager.create_task(task_type="render", title="A")
    TaskManager.complete_task(completed["id"])
    result = TaskManager.cancel_task(completed["id"])
    assert result["status"] == TaskStatus.COMPLETED  # unchanged

    failed = TaskManager.create_task(task_type="render", title="B")
    TaskManager.fail_task(failed["id"], error="boom")
    result2 = TaskManager.cancel_task(failed["id"])
    assert result2["status"] == TaskStatus.FAILED  # unchanged


def test_fail_task_on_unknown_id_returns_none():
    assert TaskManager.fail_task("nope", error="x") is None


def test_cancel_task_on_unknown_id_returns_none():
    assert TaskManager.cancel_task("nope") is None


def test_complete_task_on_unknown_id_returns_none():
    assert TaskManager.complete_task("nope") is None


# ---------------------------------------------------------------------------
# Restart / initialize() recovery behavior
# ---------------------------------------------------------------------------

def test_initialize_marks_queued_and_processing_tasks_as_failed_on_restart(isolated_registry):
    """Simulate a server crash: write a registry file directly (bypassing
    TaskManager, as if a previous process wrote it) containing a queued
    task and a processing task, then call initialize() fresh and confirm
    both are marked failed with the restart message."""
    stale_registry = {
        "queued_task": {
            "id": "queued_task", "type": "render", "title": "Q", "status": TaskStatus.QUEUED,
            "progress": 0.0, "logs": [],
        },
        "processing_task": {
            "id": "processing_task", "type": "render", "title": "P", "status": TaskStatus.PROCESSING,
            "progress": 0.4, "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    TaskManager.initialize()

    q = TaskManager.get_task("queued_task")
    p = TaskManager.get_task("processing_task")
    assert q["status"] == TaskStatus.FAILED
    assert p["status"] == TaskStatus.FAILED
    assert "รีสตาร์ท" in q["error"]
    assert "รีสตาร์ท" in p["error"]


def test_initialize_leaves_completed_tasks_untouched(isolated_registry):
    stale_registry = {
        "done_task": {
            "id": "done_task", "type": "render", "title": "Done", "status": TaskStatus.COMPLETED,
            "progress": 1.0, "result": {"ok": True}, "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    TaskManager.initialize()

    d = TaskManager.get_task("done_task")
    assert d["status"] == TaskStatus.COMPLETED
    assert d["result"] == {"ok": True}
    assert "error" not in d or d.get("error") is None


def test_initialize_is_idempotent_and_only_recovers_once(isolated_registry):
    """A second initialize() call within the same process must be a
    no-op (guarded by cls._initialized) -- otherwise a task legitimately
    created after the first recovery could get clobbered by recovery
    logic running again. Note: update_progress() itself also calls
    cls.initialize() internally, so if the guard were broken, creating
    and progressing a brand-new task after the first initialize() could
    trigger a second recovery pass that (harmlessly here, since the new
    task isn't queued/processing at the wrong moment, but in general)
    re-scans all tasks -- the guard existing at all is what we pin down."""
    stale_registry = {
        "queued_task": {
            "id": "queued_task", "type": "render", "title": "Q", "status": TaskStatus.QUEUED,
            "progress": 0.0, "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    TaskManager.initialize()
    assert TaskManager._initialized is True
    # The recovered task is now FAILED, as the restart-recovery test above
    # already covers. Create a brand-new task and progress it -- this new
    # task was never queued/processing at initialize() time, so a second,
    # buggy initialize() re-running its recovery loop would leave it alone
    # too (recovery only touches tasks that are queued/processing AT SCAN
    # TIME). What this test actually pins down is the guard itself: a
    # second initialize() call must return immediately without re-reading
    # TASKS_FILE from disk and clobbering in-memory state with the stale
    # file contents.
    new_task = TaskManager.create_task(task_type="render", title="fresh")
    TaskManager.update_progress(new_task["id"], progress=0.1, step_label="working")

    TaskManager.initialize()  # must be a no-op: _initialized is already True

    fresh = TaskManager.get_task(new_task["id"])
    assert fresh["status"] == TaskStatus.PROCESSING
    assert fresh["step_label"] == "working"
    # And the recovered task's FAILED state (set by the first, real
    # initialize()) must not have been touched by the second call.
    q = TaskManager.get_task("queued_task")
    assert q["status"] == TaskStatus.FAILED


# ---------------------------------------------------------------------------
# Persistence round-tripping through the registry file
# ---------------------------------------------------------------------------

def test_create_task_persists_to_disk_immediately(isolated_registry):
    task = TaskManager.create_task(task_type="render", title="Persisted")
    on_disk = json.loads(isolated_registry.read_text(encoding="utf-8"))
    assert task["id"] in on_disk
    assert on_disk[task["id"]]["title"] == "Persisted"


def test_state_round_trips_through_a_fresh_initialize(isolated_registry, monkeypatch):
    """Write via one 'process' (TaskManager as currently initialized),
    then simulate a fresh process by resetting class state and
    re-initializing -- the completed task must reload with its result
    intact, exercising the real JSON (de)serialization path."""
    task = TaskManager.create_task(task_type="render", title="Round trip")
    TaskManager.complete_task(task["id"], result={"video": "final.mp4", "duration": 12.5})

    # Simulate process restart: fresh class state, same disk file.
    monkeypatch.setattr(TaskManager, "_tasks", {})
    monkeypatch.setattr(TaskManager, "_initialized", False)
    TaskManager.initialize()

    reloaded = TaskManager.get_task(task["id"])
    assert reloaded["status"] == TaskStatus.COMPLETED
    assert reloaded["result"] == {"video": "final.mp4", "duration": 12.5}


def test_initialize_tolerates_corrupt_registry_file(isolated_registry):
    isolated_registry.write_text("{not valid json", encoding="utf-8")
    TaskManager.initialize()  # must not raise
    assert TaskManager.get_active_tasks() == []


def test_initialize_accepts_legacy_list_shaped_registry(isolated_registry):
    """initialize() explicitly supports a list-of-tasks legacy format in
    addition to the current dict-keyed-by-id format."""
    legacy = [
        {"id": "a", "type": "render", "title": "A", "status": TaskStatus.COMPLETED, "logs": []},
        {"id": "b", "type": "render", "title": "B", "status": TaskStatus.QUEUED, "logs": []},
    ]
    isolated_registry.write_text(json.dumps(legacy), encoding="utf-8")
    TaskManager.initialize()

    assert TaskManager.get_task("a")["status"] == TaskStatus.COMPLETED
    assert TaskManager.get_task("b")["status"] == TaskStatus.FAILED  # recovered on load


# ---------------------------------------------------------------------------
# Concurrency: update_progress() from several threads
# ---------------------------------------------------------------------------

def test_concurrent_update_progress_from_many_threads_stays_consistent():
    """Fire update_progress() for the SAME task from many threads at once.
    The task must end up in a single well-defined state (no partial/torn
    write), every update must be reflected in the log (bounded to 50), and
    no exception should escape any thread -- this is the thread-safety
    claim in the module docstring."""
    task = TaskManager.create_task(task_type="render", title="Concurrent")
    task_id = task["id"]
    errors = []

    def worker(n):
        try:
            for i in range(20):
                TaskManager.update_progress(task_id, progress=(n * 20 + i) / 160, msg=f"w{n}-{i}")
        except Exception as e:  # pragma: no cover - failure path
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    final = TaskManager.get_task(task_id)
    assert final["status"] == TaskStatus.PROCESSING
    assert 0.0 <= final["progress"] <= 1.0
    assert len(final["logs"]) <= 50


def test_concurrent_creates_do_not_lose_any_task():
    """Many threads creating distinct tasks concurrently must all show up
    -- exercises the _TASK_LOCK guard around cls._tasks mutation."""
    created_ids = []
    lock = threading.Lock()

    def worker(n):
        t = TaskManager.create_task(task_type="render", title=f"Task {n}")
        with lock:
            created_ids.append(t["id"])

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(created_ids) == 30
    assert len(set(created_ids)) == 30  # all unique ids
    for tid in created_ids:
        assert TaskManager.get_task(tid) is not None


# ---------------------------------------------------------------------------
# run_in_background()
# ---------------------------------------------------------------------------

def test_run_in_background_executes_submitted_function():
    done = threading.Event()
    result = {}

    def job(x, y):
        result["value"] = x + y
        done.set()

    TaskManager.run_in_background(job, 2, y=3)
    assert done.wait(timeout=5), "background job did not run in time"
    assert result["value"] == 5


def test_run_in_background_isolates_exceptions_per_task():
    """A background job that raises must not affect the shared worker
    pool's ability to run subsequent jobs (ThreadPoolExecutor swallows the
    exception into the Future, which nothing here retrieves -- confirms
    the pool keeps working rather than a thread dying and starving it)."""
    def bad_job():
        raise RuntimeError("boom")

    done = threading.Event()

    def good_job():
        done.set()

    TaskManager.run_in_background(bad_job)
    TaskManager.run_in_background(good_job)
    assert done.wait(timeout=5), "worker pool stopped processing after a job raised"
