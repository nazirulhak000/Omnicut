"""
Global Persistent Task Manager & Background Job Queue
Persists background operations (Product Scraping, AI Script Generation, Video Rendering, Voice Synthesis)
to disk so jobs survive page refreshes, tab switching, and server restarts.
"""

import os
import sys
import json
import secrets
import time
import datetime
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure persistent registry directory exists
STORAGE_DIR = PROJECT_ROOT / "03_Projects"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
TASKS_FILE = STORAGE_DIR / "task_registry.json"

_TASK_LOCK = threading.RLock()
_WORKER_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="capcut_worker")

# Single well-known owner for the current single-user deployment. Every task
# created without an explicit owner_id is attributed to this constant, so
# behavior for today's one user is identical to before ownership scoping
# existed. Multi-tenancy (real per-request owner resolution, auth, etc.) is a
# later step -- this just makes the data shape ready for it.
DEFAULT_OWNER = "local"


class TaskStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Task types that correspond to a render/reroll job which flips a
# ProductStore angle to "in_production" at start (see api_render.py's
# execute_render_job() and api_phase1.py's _execute_reroll()). Read off the
# actual task_type= values passed to create_task() at every call site
# (api_render.py's /api/render, api_phase1.py's /reroll) -- "scrape_and_plan"
# (api_products.py) never touches angle status and is deliberately excluded.
RENDER_TASK_TYPES = ("render_video", "edit_project")

# Terminal (completed/failed/cancelled) tasks whose completed_at/updated_at
# is older than this are pruned from cls._tasks automatically -- before
# this, only the manual /api/tasks endpoints (delete_task, clear_completed)
# ever evicted anything, so every task ever run stayed resident forever:
# _save_to_disk_locked's full-dict JSON serialize and get_active_tasks'
# full-dict sort both cost O(total task history) on every call, growing
# without bound for the life of the process. Active/queued/processing tasks
# are never pruned here regardless of age -- see _prune_old_tasks_locked().
TASK_RETENTION_DAYS = 7

# How often _save_to_disk_locked() re-checks for prunable tasks. Pruning is
# one pass over cls._tasks -- no more expensive than the serialize/sort this
# module already does on every save/list call -- so this throttle exists
# only to avoid doing that extra pass on every single save when nothing is
# likely to have aged out since the last check.
_TASK_PRUNE_INTERVAL_SECONDS = 3600


class TaskManager:
    """Thread-safe persistent task queue and activity tracker."""
    _tasks: Dict[str, Dict[str, Any]] = {}
    _initialized = False

    @classmethod
    def _now_iso(cls) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _quarantine_invalid_snapshot(cls, raw: str) -> bool:
        """Preserve a malformed registry before a later recovery save replaces it."""
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        quarantine = TASKS_FILE.with_name(
            f"{TASKS_FILE.stem}.invalid-{stamp}{TASKS_FILE.suffix}"
        )
        try:
            quarantine.write_text(raw, encoding="utf-8")
            print(f"⚠️ [TaskManager] Quarantined malformed registry at {quarantine.name}")
            return True
        except OSError as exc:
            print(f"⚠️ [TaskManager] Could not quarantine malformed registry: {exc}")
            return False

    @classmethod
    def initialize(cls) -> None:
        """Loads tasks from disk and recovers unfinished tasks from previous server sessions."""
        with _TASK_LOCK:
            if cls._initialized:
                return

            can_persist_recovery = True
            if TASKS_FILE.exists():
                try:
                    raw = TASKS_FILE.read_text(encoding="utf-8")
                    data = json.loads(raw)
                    invalid_rows = False
                    if isinstance(data, dict):
                        tasks = {}
                        for task_id, task in data.items():
                            if isinstance(task_id, str) and task_id and isinstance(task, dict) and task.get("id") == task_id:
                                tasks[task_id] = task
                            else:
                                invalid_rows = True
                        cls._tasks = tasks
                    elif isinstance(data, list):
                        tasks = {}
                        for task in data:
                            task_id = task.get("id") if isinstance(task, dict) else None
                            if isinstance(task_id, str) and task_id and task_id not in tasks:
                                tasks[task_id] = task
                            else:
                                invalid_rows = True
                        cls._tasks = tasks
                    else:
                        invalid_rows = True
                        cls._tasks = {}
                    if invalid_rows:
                        can_persist_recovery = cls._quarantine_invalid_snapshot(raw)
                except Exception as e:
                    print(f"⚠️ [TaskManager] Failed to load tasks from disk: {e}")
                    cls._tasks = {}
                    can_persist_recovery = False

            # Render jobs are intentionally failed on restart because their
            # subprocess lifecycle is not resumable. Background-isolation
            # jobs are different: their per-frame checkpoint is durable, so
            # keep them queued and let the API recovery hook resume them.
            changed = False
            orphaned_render_tasks = []
            for task_id, task in cls._tasks.items():
                if task.get("status") in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
                    if task.get("type") in ("background_isolation", "batch_render"):
                        task["status"] = TaskStatus.QUEUED
                        task["error"] = None
                        task["step_label"] = (
                            "กำลังกู้คืนงานตัดพื้นหลังจาก checkpoint เดิม"
                            if task.get("type") == "background_isolation"
                            else "กำลังกู้คืนคิวเรนเดอร์จาก checkpoint เดิม"
                        )
                        task["updated_at"] = cls._now_iso()
                        changed = True
                        continue
                    if task.get("type") in RENDER_TASK_TYPES:
                        orphaned_render_tasks.append(task)
                    task["status"] = TaskStatus.FAILED
                    task["error"] = "เซิร์ฟเวอร์รีสตาร์ท — งานถูกยกเลิกอัตโนมัติ"
                    task["step_label"] = "งานถูกขัดจังหวะจากการรีสตาร์ทระบบ"
                    task["updated_at"] = cls._now_iso()
                    changed = True

            # Prune stale terminal tasks left over from previous sessions
            # before marking initialized -- see TASK_RETENTION_DAYS above.
            if cls._prune_old_tasks_locked():
                changed = True

            cls._initialized = True
            if changed and can_persist_recovery:
                cls._save_to_disk_locked()

        # A render/reroll task swept to "failed" above (by this same
        # restart) left its ProductStore angle set to "in_production" --
        # that flip happens at render *start* (api_render.py's
        # execute_render_job(), api_phase1.py's _execute_reroll()) and is
        # only ever reverted from each function's own `except` block on a
        # normal in-process failure. A killed/restarted process never runs
        # that except block, so without this the angle sits on
        # "in_production" forever -- reconcile_existing_projects()
        # deliberately never demotes that status on its own (it can't tell
        # an orphan from a genuinely live edit). Done outside _TASK_LOCK:
        # it calls into ProductStore, which takes its own separate lock,
        # and nothing here needs _TASK_LOCK held while it runs.
        if orphaned_render_tasks:
            cls._revert_orphaned_render_angles(orphaned_render_tasks)

    @classmethod
    def _revert_orphaned_render_angles(cls, tasks: List[Dict[str, Any]]) -> None:
        """For each render/reroll task just swept to "failed" by a restart,
        resolve the product/angle it was working on and revert that angle's
        status away from "in_production" -- the same status a normal
        failed-render's own except-block already sets (see
        api_render.py's execute_render_job() and api_phase1.py's
        _execute_reroll()), just reached by a different path: this process
        never got to run that except-block because it was killed/restarted
        mid-render instead of failing in-process.

        Resolution mirrors _execute_reroll()'s own logic exactly (payload
        first, then ProductStore.find_by_project() using the payload's
        project_name) rather than inventing a new approach -- see
        api_phase1.py's _execute_reroll() for the source of this pattern.

        Deliberately conservative: the only status this ever writes is
        "scripted" (the safe default a normal failed render already uses),
        never anything that could look like a successful render. A task
        whose product/angle cannot be resolved, or whose product/angle no
        longer exists, is skipped with a log line -- never raised, since a
        stale/incomplete task record must not be able to crash startup.
        """
        # Local import: avoids a module-level import cycle risk (this file
        # is imported very early, at process/module-import time) and keeps
        # product_store's own import graph exactly as it already is.
        from scripts.product_store import ProductStore

        for task in tasks:
            task_id = task.get("id", "<unknown>")
            payload = task.get("payload") or {}

            product_id = payload.get("product_id")
            angle_id = payload.get("angle_id")

            project_name = payload.get("project_name")
            if not (product_id and angle_id) and project_name:
                try:
                    prod, ang = ProductStore.find_by_project(
                        project_name,
                        product_id=product_id or "",
                        angle_id=angle_id or "",
                    )
                except Exception as lookup_err:
                    print(
                        f"⚠️ [TaskManager] restart recovery: could not look up product/angle "
                        f"for orphaned task {task_id!r} (project_name={project_name!r}): {lookup_err}"
                    )
                    prod, ang = None, None
                if prod and not product_id:
                    product_id = prod.get("id")
                if ang and not angle_id:
                    angle_id = ang.get("angle_id") or ang.get("id")

            if not (product_id and angle_id):
                print(
                    f"⚠️ [TaskManager] restart recovery: task {task_id!r} (type={task.get('type')!r}) "
                    f"looked like an orphaned render but no product_id/angle_id could be resolved "
                    f"(payload={payload!r}) -- skipping, angle status left untouched."
                )
                continue

            try:
                product = ProductStore.get(product_id)
                angle = None
                if product:
                    for a in product.get("angles", []) or []:
                        if (a.get("angle_id") or a.get("id")) == angle_id:
                            angle = a
                            break

                if angle is None:
                    print(
                        f"⚠️ [TaskManager] restart recovery: product={product_id!r} "
                        f"angle={angle_id!r} resolved from orphaned task {task_id!r} no longer "
                        "exists -- skipping, nothing to revert."
                    )
                    continue

                if angle.get("status") != "in_production":
                    # Something else (a later real render, a manual edit)
                    # already moved this angle on since the crash -- do not
                    # clobber whatever it's doing now just because an old
                    # task record still points at it.
                    print(
                        f"[TaskManager] restart recovery: skipping product={product_id!r} "
                        f"angle={angle_id!r} for orphaned task {task_id!r} -- current status "
                        f"is {angle.get('status')!r}, not 'in_production', so nothing to revert."
                    )
                    continue

                ProductStore.update_angle_status(product_id, angle_id, "scripted", project_name="")
                print(
                    f"[TaskManager] restart recovery: reverted product={product_id!r} "
                    f"angle={angle_id!r} from 'in_production' to 'scripted' -- its render "
                    f"task {task_id!r} (type={task.get('type')!r}) was orphaned by a server "
                    f"restart and never reached its own failure handler."
                )
            except Exception as revert_err:
                print(
                    f"⚠️ [TaskManager] restart recovery: could not revert product={product_id!r} "
                    f"angle={angle_id!r} for orphaned task {task_id!r}: {revert_err} -- "
                    "skipping, angle status left untouched."
                )

    _last_disk_save = 0.0
    _last_prune_at = 0.0

    @classmethod
    def _prune_old_tasks_locked(cls) -> bool:
        """Evicts terminal (completed/failed/cancelled) tasks older than
        TASK_RETENTION_DAYS. Caller must already hold _TASK_LOCK.

        Active/queued/processing tasks are never touched here, regardless
        of age. A task with no usable completed_at/updated_at (e.g. a
        hand-written or otherwise legacy record missing both) is left
        alone rather than guessed at -- pruning is a cleanup, not something
        that should risk dropping a record it can't actually date.

        Returns True if anything was removed, so callers can decide
        whether the removal itself warrants a disk save.
        """
        cutoff = datetime.datetime.now() - datetime.timedelta(days=TASK_RETENTION_DAYS)
        terminal = (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        to_delete = []
        for task_id, task in cls._tasks.items():
            if task.get("status") not in terminal:
                continue
            ts = task.get("completed_at") or task.get("updated_at")
            if not ts:
                continue
            try:
                when = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                continue
            if when < cutoff:
                to_delete.append(task_id)

        for task_id in to_delete:
            del cls._tasks[task_id]
        return bool(to_delete)

    @classmethod
    def _save_to_disk_locked(cls, force: bool = True) -> None:
        """Writes current tasks to disk atomically with throttling and Windows retry."""
        now = time.time()
        if now - cls._last_prune_at > _TASK_PRUNE_INTERVAL_SECONDS:
            cls._last_prune_at = now
            cls._prune_old_tasks_locked()

        if not force and (now - cls._last_disk_save < 2.0):
            return
        cls._last_disk_save = now
        try:
            temp_file = TASKS_FILE.with_suffix(f".tmp_{os.getpid()}")
            temp_file.write_text(json.dumps(cls._tasks, ensure_ascii=False, indent=2), encoding="utf-8")
            for _ in range(3):
                try:
                    temp_file.replace(TASKS_FILE)
                    return
                except Exception:
                    time.sleep(0.05)
            # cls._tasks in memory is the authoritative source: initialize()
            # only ever wholesale-replaces it from disk (see the file-load
            # block above), it never merges disk into memory, so the file on
            # disk is just a convenience snapshot for restart recovery. A
            # truncating write_text() fallback used to run here -- but this
            # branch is reached only after 3 atomic-rename attempts already
            # failed (the contended case), which is also the case most
            # likely to get interrupted mid-write, and unlike every other
            # writer in this codebase, a half-written task_registry.json IS
            # read straight back in as authoritative on the next startup.
            # Skip the save instead: memory stays correct, and the next
            # successful tick (2s later, or the next state-changing call)
            # catches up.
            #
            # Cleanup before logging, deliberately: some consoles (cp874/
            # cp1252 etc, seen on Windows) raise UnicodeEncodeError on the
            # warning glyph below, which the outer bare `except` swallows --
            # if that happened before the unlink, the tmp file would leak
            # every time this branch is hit on such a console.
            temp_file.unlink(missing_ok=True)
            print("⚠️ [TaskManager] Failed to persist task registry after 3 atomic-rename "
                  "attempts -- skipping this save, in-memory tasks remain authoritative.")
        except Exception:
            pass # Non-critical: tasks are safely held in memory in cls._tasks

    @classmethod
    def create_task(
        cls,
        task_type: str,
        title: str,
        payload: Optional[Dict[str, Any]] = None,
        target_tab: str = "flow",
        target_id: Optional[str] = None,
        task_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates and registers a new task."""
        cls.initialize()
        # secrets.token_urlsafe rather than the old timestamp-ms + 6 hex chars
        # scheme: that scheme was guessable/walkable (sequential-ish prefix,
        # low-entropy suffix). Callers that pass an explicit task_id (e.g. a
        # render job's uuid4) are unaffected.
        t_id = task_id or secrets.token_urlsafe(16)
        now = cls._now_iso()

        task_obj = {
            "id": t_id,
            "type": task_type,
            "title": title,
            "status": TaskStatus.QUEUED,
            "progress": 0.0,
            "step_label": "อยู่ในคิวรอเริ่มทำงาน...",
            "target_tab": target_tab,
            "target_id": target_id,
            "payload": payload or {},
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "owner_id": owner_id or DEFAULT_OWNER,
            "logs": [{"time": datetime.datetime.now().strftime("%H:%M:%S"), "msg": "งานถูกสร้างขึ้นในระบบ", "progress": 0}],
        }

        with _TASK_LOCK:
            cls._tasks[t_id] = task_obj
            cls._save_to_disk_locked()

        return task_obj

    @staticmethod
    def _owned_by(task: Dict[str, Any], owner_id: Optional[str]) -> bool:
        """True if `owner_id` is unset (unscoped call) or matches the task's owner.

        Tasks persisted before this field existed have no "owner_id" key --
        treat those as DEFAULT_OWNER so old data keeps working under scoping.
        """
        if owner_id is None:
            return True
        return task.get("owner_id", DEFAULT_OWNER) == owner_id

    @classmethod
    def update_progress(
        cls,
        task_id: str,
        progress: float,
        step_label: Optional[str] = None,
        msg: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates progress and step label for a task."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task or not cls._owned_by(task, owner_id):
                return None

            # Don't overwrite finished states
            if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return task

            task["status"] = TaskStatus.PROCESSING
            task["progress"] = min(1.0, max(0.0, float(progress)))
            if step_label:
                task["step_label"] = step_label
            task["updated_at"] = cls._now_iso()

            log_msg = msg or step_label
            if log_msg:
                task.setdefault("logs", []).append({
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "msg": log_msg,
                    "progress": int(task["progress"] * 100),
                })
                # Keep logs manageable
                if len(task["logs"]) > 50:
                    task["logs"] = task["logs"][-50:]

            cls._save_to_disk_locked(force=False)
            return task

    @classmethod
    def complete_task(
        cls,
        task_id: str,
        result: Any = None,
        step_label: str = "ดำเนินการเสร็จสิ้น 100%",
        target_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Marks a task as completed."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task or not cls._owned_by(task, owner_id):
                return None
            # A task that already reached a terminal state stays there, the way
            # update_progress() and cancel_task() already treat one. Without
            # this, completing an already-failed task flipped it to COMPLETED
            # while leaving its `error` populated -- a record claiming both.
            if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return task

            task["status"] = TaskStatus.COMPLETED
            task["progress"] = 1.0
            task["step_label"] = step_label
            task["result"] = result
            if target_id:
                task["target_id"] = target_id
            task["updated_at"] = cls._now_iso()
            task["completed_at"] = cls._now_iso()
            task.setdefault("logs", []).append({
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "msg": step_label,
                "progress": 100,
            })

            cls._save_to_disk_locked()
            return task

    @classmethod
    def fail_task(
        cls,
        task_id: str,
        error: str,
        step_label: str = "เกิดข้อผิดพลาดในการประมวลผล",
        owner_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Marks a task as failed."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task or not cls._owned_by(task, owner_id):
                return None
            # Terminal is terminal, as in complete_task(). Restart recovery in
            # initialize() sets the status directly rather than coming through
            # here, so it is unaffected by this guard.
            if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return task

            task["status"] = TaskStatus.FAILED
            task["error"] = str(error)
            task["step_label"] = f"❌ {step_label}: {error}"
            task["updated_at"] = cls._now_iso()
            task["completed_at"] = cls._now_iso()
            task.setdefault("logs", []).append({
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "msg": f"Error: {error}",
                "progress": int(task.get("progress", 0) * 100),
            })

            cls._save_to_disk_locked()
            return task

    @classmethod
    def cancel_task(cls, task_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Cancels a pending or running task."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task or not cls._owned_by(task, owner_id):
                return None

            if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return task

            task["status"] = TaskStatus.CANCELLED
            task["step_label"] = "งานถูกยกเลิกโดยผู้ใช้"
            task["updated_at"] = cls._now_iso()
            task["completed_at"] = cls._now_iso()

            cls._save_to_disk_locked()
            return task

    @classmethod
    def get_task(cls, task_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves a single task by ID.

        A task_id that exists but belongs to a different owner behaves
        exactly like a missing task_id (returns None) -- it must never
        distinguish "not found" from "not yours", or the lookup itself
        becomes an oracle confirming the id exists.
        """
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task or not cls._owned_by(task, owner_id):
                return None
            return task

    @classmethod
    def get_active_tasks(cls, limit: int = 50, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all running/queued tasks plus recent completed/failed tasks (sorted by updated_at desc).

        With owner_id given, only that owner's tasks are considered -- an
        unscoped call (owner_id=None) still returns everything, unchanged
        from before scoping existed.
        """
        cls.initialize()
        with _TASK_LOCK:
            all_list = [t for t in cls._tasks.values() if cls._owned_by(t, owner_id)]
            # Sort newest first
            all_list.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
            return all_list[:limit]

    @classmethod
    def delete_task(cls, task_id: str, owner_id: Optional[str] = None) -> bool:
        """Deletes a task from registry."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task or not cls._owned_by(task, owner_id):
                return False
            del cls._tasks[task_id]
            cls._save_to_disk_locked()
            return True

    @classmethod
    def clear_completed(cls, owner_id: Optional[str] = None) -> int:
        """Clears all completed, failed, or cancelled tasks."""
        cls.initialize()
        with _TASK_LOCK:
            to_del = [
                tid for tid, t in cls._tasks.items()
                if t.get("status") in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                and cls._owned_by(t, owner_id)
            ]
            for tid in to_del:
                del cls._tasks[tid]
            if to_del:
                cls._save_to_disk_locked()
            return len(to_del)

    @classmethod
    def run_in_background(cls, fn: Callable, *args, **kwargs) -> None:
        """Submits a function to the background thread pool."""
        _WORKER_POOL.submit(fn, *args, **kwargs)


# Initialize immediately on module import
TaskManager.initialize()
