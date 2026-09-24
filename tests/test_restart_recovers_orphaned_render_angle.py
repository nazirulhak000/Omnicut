"""
A server restart mid-render must not leave a ProductStore angle stuck on
"in_production" forever.

The angle is flipped to "in_production" at render *start*
(api_render.py's execute_render_job(), api_phase1.py's _execute_reroll())
and is only ever reverted back by each function's own `except` block on a
normal in-process failure. A killed/restarted process never runs that
except block -- TaskManager.initialize() already sweeps the orphaned
queued/processing task itself to "failed" on the next startup (that part
already worked), but nothing reverted the angle it was rendering, and
ProductStore.reconcile_existing_projects() deliberately never demotes
"in_production" on its own (an orphan is indistinguishable from a live
edit to that function). This exercises the fix: initialize()'s restart
sweep now also resolves the product/angle a swept render/reroll task was
working on and reverts it to "scripted".

Isolated per .agents/rules/testing_standard.md, following the pattern in
tests/test_reroll_status_sync.py (product_store + project_manifest via
tmp_path/monkeypatch) and tests/test_task_manager.py (task_manager's own
TASKS_FILE/_tasks/_initialized reset).
"""
import json
import multiprocessing
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.task_manager as tm_module
from scripts.task_manager import TaskManager, TaskStatus

from scripts import api_render, product_store, project_manifest, render_jobs
from scripts.api_schemas import RenderRequest
from scripts.product_store import ProductStore


def _run_interrupted_render(root_str, product_id, project_name, job_id, ready):
    """Child process: enter the real render worker, then wait to be killed."""
    root = Path(root_str)
    product_store.STORE_PATH = root / "_Docs" / "products.json"
    product_store.BASE_DIR = root
    project_manifest.PROJECTS_DIR = root / "03_Projects"
    tm_module.TASKS_FILE = root / "task_registry.json"
    TaskManager._tasks = {}
    TaskManager._initialized = False
    api_render.check_disk_space = lambda *_args: {"is_sufficient": True}

    def block_pipeline(**kwargs):
        kwargs["progress_callback"]("worker entered render pipeline", 0.3)
        ready.set()
        time.sleep(120)

    api_render.TikTokAutoCutterPipeline.run = staticmethod(block_pipeline)
    TaskManager.create_task(
        task_type="render_video", title="Interrupted render", task_id=job_id,
        payload={"product_id": product_id, "angle_id": "unboxing", "project_name": project_name},
    )
    render_jobs.create_job(job_id)
    api_render.execute_render_job(job_id, RenderRequest(
        product_name="Widget", raw_video_path=str(root / "source.mp4"),
        project_name=project_name, product_id=product_id, angle_id="unboxing",
        key_features="offline", pain_point="offline", price_deal="offline",
    ))


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Same isolation as tests/test_reroll_status_sync.py."""
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(product_store, "BASE_DIR", tmp_path)
    assert product_store.BASE_DIR == tmp_path, "the BASE_DIR patch did not take"
    return tmp_path


@pytest.fixture
def projects_dir(tmp_path, monkeypatch):
    target = tmp_path / "03_Projects"
    target.mkdir(exist_ok=True)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)
    return target


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Same isolation as tests/test_task_manager.py."""
    registry_file = tmp_path / "task_registry.json"
    monkeypatch.setattr(tm_module, "TASKS_FILE", registry_file)
    monkeypatch.setattr(TaskManager, "_tasks", {})
    monkeypatch.setattr(TaskManager, "_initialized", False)
    monkeypatch.setattr(TaskManager, "_last_disk_save", 0.0)
    yield registry_file


def test_restart_reverts_orphaned_render_task_angle_to_scripted(
    isolated_store, projects_dir, isolated_registry
):
    """The scenario from the bug report: a product/angle sitting in
    "in_production" because a render task was interrupted by a server
    kill, never reaching its own except-block. TaskManager.initialize()
    (the real restart entry point) must resolve product_id/angle_id from
    the stale task's payload and revert the angle to "scripted"."""
    product = ProductStore.add(name="Widget", url="https://x.test/w-restart")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "in_production",
        "script_lines": ["a"],
    }])

    # Simulate a previous process's task registry, written directly (as if
    # a prior server process crashed mid-render) -- a processing render
    # task whose payload names the project it was rendering, exactly the
    # shape api_render.py's /api/render and api_phase1.py's /reroll
    # actually create (payload only carries project_name, not
    # product_id/angle_id directly -- see those call sites).
    project_name = "widget_restart_test_1"
    # A killed renderer may leave a partial project directory behind.  The
    # normal ProductStore reconcile path must not hide a stale pointer here.
    partial_project = projects_dir / project_name
    partial_project.mkdir()
    (partial_project / "project.json").write_text(json.dumps({
        "product_id": product["id"], "angle_id": "unboxing", "artifacts": {},
    }), encoding="utf-8")
    stale_registry = {
        "stale_render_job": {
            "id": "stale_render_job",
            "type": "render_video",
            "title": "เรนเดอร์วิดีโอ: Widget",
            "status": TaskStatus.PROCESSING,
            "progress": 0.4,
            "payload": {"project_name": project_name, "product_name": "Widget", "export_mp4": True},
            "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    # find_by_project() resolves via angle.project_name -- link the angle
    # to this project the way a real render start (execute_render_job) does.
    ProductStore.update_angle_status(product["id"], "unboxing", "in_production", project_name=project_name)

    # Fresh process start: this is the real recovery entry point.
    TaskManager.initialize()

    # The stale task itself is still correctly swept to failed (must not break).
    task = TaskManager.get_task("stale_render_job")
    assert task["status"] == TaskStatus.FAILED
    assert "รีสตาร์ท" in task["error"]

    # The orphaned angle must no longer be stuck on "in_production".
    updated = ProductStore.get(product["id"])
    angle = next(a for a in updated["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] != "in_production"
    assert angle["status"] == "scripted"
    assert not angle.get("project_name"), "restart recovery must clear the abandoned render pointer"
    refreshed = ProductStore.get(product["id"])
    refreshed_angle = next(a for a in refreshed["angles"] if a["angle_id"] == "unboxing")
    assert refreshed_angle["status"] == "scripted"
    assert not refreshed_angle.get("project_name"), "reconcile must not relink the aborted project"


def test_killed_render_worker_recovers_task_and_project_state(
    isolated_store, projects_dir, isolated_registry, tmp_path, monkeypatch,
):
    product = ProductStore.add(name="Widget", url="https://x.test/w-killed-render")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing", "hook_title": "unboxing", "status": "scripted", "script_lines": ["a"],
    }])
    project_name = "widget_killed_render"
    partial_project = projects_dir / project_name
    partial_project.mkdir()
    (partial_project / "project.json").write_text(json.dumps({
        "product_id": product["id"], "angle_id": "unboxing", "artifacts": {},
    }), encoding="utf-8")
    job_id = "killed-render-job"
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    worker = context.Process(
        target=_run_interrupted_render,
        args=(str(tmp_path), product["id"], project_name, job_id, ready),
    )
    try:
        worker.start()
        assert ready.wait(20), f"render worker did not enter pipeline (exit={worker.exitcode})"
        active_angle = ProductStore._load()[0]["angles"][0]
        assert active_angle["status"] == "in_production"
        assert active_angle["project_name"] == project_name
        # Progress persistence is throttled, so a hard kill may leave the
        # on-disk snapshot queued even while the worker was processing.
        assert json.loads(isolated_registry.read_text(encoding="utf-8"))[job_id]["status"] in {"queued", "processing"}

        worker.terminate()
        worker.join(10)
        assert worker.exitcode is not None and worker.exitcode != 0

        monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
        TaskManager._tasks = {}
        TaskManager._initialized = False
        TaskManager.initialize()
        assert TaskManager.get_task(job_id)["status"] == TaskStatus.FAILED
        assert api_render.get_render_status(job_id)["status"] == "failed"
        recovered_angle = ProductStore.get(product["id"])["angles"][0]
        assert recovered_angle["status"] == "scripted"
        assert not recovered_angle.get("project_name")
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(10)


def test_restart_resolves_product_and_angle_id_directly_from_payload(
    isolated_store, projects_dir, isolated_registry
):
    """When the payload already carries product_id/angle_id directly (not
    just project_name), those must be used without needing
    find_by_project() at all."""
    product = ProductStore.add(name="Gadget", url="https://x.test/g-restart")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "demo",
        "hook_title": "โชว์ของ",
        "status": "in_production",
        "script_lines": ["a"],
    }])

    stale_registry = {
        "stale_reroll_job": {
            "id": "stale_reroll_job",
            "type": "render_video",
            "title": "สุ่มใหม่: hook",
            "status": TaskStatus.PROCESSING,
            "progress": 0.2,
            "payload": {"product_id": product["id"], "angle_id": "demo", "part": "hook"},
            "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    TaskManager.initialize()

    updated = ProductStore.get(product["id"])
    angle = next(a for a in updated["angles"] if a["angle_id"] == "demo")
    assert angle["status"] == "scripted"


def test_restart_leaves_already_advanced_angle_alone(isolated_store, projects_dir, isolated_registry):
    """If the angle already moved past "in_production" by the time
    recovery runs (e.g. it was already rendered by a separate process
    before this stale task record was swept), recovery must not clobber
    it back down to "scripted"."""
    # The file must actually exist on disk: ProductStore.get() runs
    # reconcile_existing_projects() on every read, and its own "strict
    # state validation" pass reverts a "rendered" angle whose video_url
    # does not resolve to a real file -- unrelated to the fix under test
    # here, so give it a real file to find.
    export_dir = isolated_store / "04_Exports" / "Ready_to_post"
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "already_done.mp4").write_bytes(b"\x00" * 64)

    product = ProductStore.add(name="Widget", url="https://x.test/w-advanced")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "rendered",
        "video_url": "04_Exports/Ready_to_post/already_done.mp4",
        "script_lines": ["a"],
    }])

    stale_registry = {
        "stale_render_job": {
            "id": "stale_render_job",
            "type": "render_video",
            "title": "เรนเดอร์วิดีโอ: Widget",
            "status": TaskStatus.PROCESSING,
            "progress": 0.9,
            "payload": {"product_id": product["id"], "angle_id": "unboxing"},
            "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    TaskManager.initialize()

    updated = ProductStore.get(product["id"])
    angle = next(a for a in updated["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "rendered"


def test_restart_skips_unresolvable_orphan_without_crashing(isolated_store, projects_dir, isolated_registry):
    """A stale render task whose payload cannot be resolved to any
    product/angle (missing fields, or the product was deleted since) must
    be skipped gracefully -- initialize() must not raise."""
    stale_registry = {
        "unresolvable_job": {
            "id": "unresolvable_job",
            "type": "render_video",
            "title": "เรนเดอร์วิดีโอ: ???",
            "status": TaskStatus.PROCESSING,
            "progress": 0.1,
            "payload": {},  # no project_name, no product_id/angle_id
            "logs": [],
        },
        "deleted_product_job": {
            "id": "deleted_product_job",
            "type": "render_video",
            "title": "เรนเดอร์วิดีโอ: Ghost",
            "status": TaskStatus.PROCESSING,
            "progress": 0.1,
            "payload": {"product_id": "does-not-exist", "angle_id": "ghost-angle"},
            "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    TaskManager.initialize()  # must not raise

    assert TaskManager.get_task("unresolvable_job")["status"] == TaskStatus.FAILED
    assert TaskManager.get_task("deleted_product_job")["status"] == TaskStatus.FAILED


def test_restart_does_not_touch_unrelated_task_types(isolated_store, projects_dir, isolated_registry):
    """A stale "scrape_and_plan" task (api_products.py) never touches
    angle status and must not trigger any ProductStore lookup/mutation."""
    # A real project folder on disk: ProductStore.get()'s reconcile pass
    # independently reverts "in_production" -> "scripted" when no project
    # folder backs it (unrelated pre-existing behavior) -- give it one so
    # this test isolates only the task-type filtering under test here.
    project_name = "widget_scrape_test_project"
    project_dir = projects_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    product = ProductStore.add(name="Widget", url="https://x.test/w-scrape")
    (project_dir / "project.json").write_text(
        json.dumps({"product_id": product["id"], "angle_id": "unboxing"}),
        encoding="utf-8",
    )
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "in_production",
        "project_name": project_name,
        "script_lines": ["a"],
    }])

    stale_registry = {
        "stale_scrape_job": {
            "id": "stale_scrape_job",
            "type": "scrape_and_plan",
            "title": "วิเคราะห์สินค้า",
            "status": TaskStatus.PROCESSING,
            "progress": 0.3,
            "payload": {"product_id": product["id"]},
            "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    TaskManager.initialize()

    assert TaskManager.get_task("stale_scrape_job")["status"] == TaskStatus.FAILED
    # Unrelated task type -- the angle it happens to name via product_id
    # must be left exactly as it was; recovery only ever looks at
    # RENDER_TASK_TYPES tasks.
    updated = ProductStore.get(product["id"])
    angle = next(a for a in updated["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "in_production"


def test_initialize_recovery_pass_only_runs_once_per_process(isolated_store, projects_dir, isolated_registry):
    """The _initialized guard must also gate the new angle-recovery pass:
    a second initialize() call in the same process must not re-run it and
    re-revert an angle a real render has since legitimately advanced."""
    product = ProductStore.add(name="Widget", url="https://x.test/w-once")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "in_production",
        "script_lines": ["a"],
    }])

    stale_registry = {
        "stale_render_job": {
            "id": "stale_render_job",
            "type": "render_video",
            "title": "เรนเดอร์วิดีโอ: Widget",
            "status": TaskStatus.PROCESSING,
            "progress": 0.4,
            "payload": {"product_id": product["id"], "angle_id": "unboxing"},
            "logs": [],
        },
    }
    isolated_registry.write_text(json.dumps(stale_registry), encoding="utf-8")

    TaskManager.initialize()
    assert TaskManager.get_task("stale_render_job")["status"] == TaskStatus.FAILED
    updated = ProductStore.get(product["id"])
    angle = next(a for a in updated["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "scripted"

    # Simulate the angle legitimately advancing afterwards (a fresh render
    # actually completed it), then call initialize() again -- it must be a
    # complete no-op given _initialized is already True.
    ProductStore.update_angle_status(product["id"], "unboxing", "rendered", video_url="x.mp4")
    TaskManager.initialize()

    updated_again = ProductStore.get(product["id"])
    angle_again = next(a for a in updated_again["angles"] if a["angle_id"] == "unboxing")
    assert angle_again["status"] == "rendered"
