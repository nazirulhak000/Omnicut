"""Startup recovery regressions; every persistent path is a temporary fixture."""

import json
import threading

import pytest

import scripts.task_manager as task_module
from scripts.project_manifest import ProjectManifest
from scripts.task_manager import TaskManager, TaskStatus
import scripts.batch_render as batch_module
from scripts.batch_render import BatchRenderManager


@pytest.fixture(autouse=True)
def isolated_task_registry(tmp_path, monkeypatch):
    registry = tmp_path / "task_registry.json"
    monkeypatch.setattr(task_module, "TASKS_FILE", registry)
    monkeypatch.setattr(TaskManager, "_tasks", {})
    monkeypatch.setattr(TaskManager, "_initialized", False)
    monkeypatch.setattr(TaskManager, "_last_disk_save", 0.0)
    yield registry


def test_malformed_task_rows_cannot_crash_startup_and_are_quarantined(isolated_task_registry):
    snapshot = {
        "valid": {
            "id": "valid", "type": "other", "status": TaskStatus.PROCESSING,
            "title": "valid task", "created_at": "2026-09-15 00:00:00",
        },
        "null-row": None,
        "not-a-task": ["invalid"],
        "mismatched-key": {"id": "different", "status": TaskStatus.QUEUED},
    }
    isolated_task_registry.write_text(json.dumps(snapshot), encoding="utf-8")

    TaskManager.initialize()

    assert TaskManager.get_task("valid")["status"] == TaskStatus.FAILED
    assert TaskManager.get_task("null-row") is None
    quarantines = list(isolated_task_registry.parent.glob("task_registry.invalid-*.json"))
    assert len(quarantines) == 1
    assert json.loads(quarantines[0].read_text(encoding="utf-8")) == snapshot


@pytest.mark.parametrize("suffix", [".json.bak1", ".json.bak2", ".json.bak3"])
def test_manifest_loads_when_only_rolling_backup_remains(tmp_path, monkeypatch, suffix):
    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", tmp_path)
    project_dir = tmp_path / "backup_only"
    project_dir.mkdir()
    (project_dir / f"project{suffix}").write_text(
        json.dumps({"title": suffix, "version": 1}), encoding="utf-8"
    )

    assert ProjectManifest.load("backup_only") == {"title": suffix, "version": 1}


def test_dispatcher_handles_batch_enqueued_at_idle_exit_boundary(monkeypatch):
    """A live dispatcher must recheck before exiting so enqueue cannot strand work."""
    first_empty_check = threading.Event()
    permit_idle_exit = threading.Event()
    calls = 0
    handled = []

    def next_batch():
        nonlocal calls
        calls += 1
        if calls == 1:
            first_empty_check.set()
            assert permit_idle_exit.wait(timeout=2)
            return None
        return "queued-at-boundary" if calls == 2 else None

    monkeypatch.setattr(BatchRenderManager, "_next_queued_batch_id", next_batch)
    monkeypatch.setattr(BatchRenderManager, "_run_batch_worker", handled.append)
    worker = threading.Thread(target=BatchRenderManager._dispatch_pending_batches)
    monkeypatch.setattr(batch_module, "_DISPATCHER_THREAD", worker)
    worker.start()
    assert first_empty_check.wait(timeout=2)
    BatchRenderManager._ensure_dispatcher()
    permit_idle_exit.set()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert handled == ["queued-at-boundary"]


def test_next_queued_batch_is_fifo_and_skips_cancelled_rows(monkeypatch):
    rows = [
        {"batch_id": "later", "status": "queued", "cancelled": False, "created_at": 20},
        {"batch_id": "cancelled", "status": "queued", "cancelled": True, "created_at": 1},
        {"batch_id": "first", "status": "queued", "cancelled": False, "created_at": 10},
        {"batch_id": "done", "status": "completed", "cancelled": False, "created_at": 0},
    ]
    monkeypatch.setattr(batch_module.BatchQueueStore, "load", lambda: rows)

    assert BatchRenderManager._next_queued_batch_id() == "first"


def test_ensure_dispatcher_does_not_start_one_thread_per_batch(monkeypatch):
    started = []

    class FakeThread:
        def __init__(self, **kwargs):
            self.target = kwargs["target"]
            self.daemon = kwargs["daemon"]
            self.name = kwargs["name"]

        def is_alive(self):
            return True

        def start(self):
            started.append(self)

    monkeypatch.setattr(batch_module.threading, "Thread", FakeThread)
    monkeypatch.setattr(batch_module, "_DISPATCHER_THREAD", None)

    BatchRenderManager._ensure_dispatcher()
    BatchRenderManager._ensure_dispatcher()

    assert len(started) == 1
    assert started[0].daemon is True
    assert started[0].name == "batch_render_dispatcher"
