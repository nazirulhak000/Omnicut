"""
Global Persistent Task Manager & Background Job Queue
Persists background operations (Product Scraping, AI Script Generation, Video Rendering, Voice Synthesis)
to disk so jobs survive page refreshes, tab switching, and server restarts.
"""

import os
import sys
import json
import uuid
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


class TaskStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskManager:
    """Thread-safe persistent task queue and activity tracker."""
    _tasks: Dict[str, Dict[str, Any]] = {}
    _initialized = False

    @classmethod
    def _now_iso(cls) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def initialize(cls) -> None:
        """Loads tasks from disk and recovers unfinished tasks from previous server sessions."""
        with _TASK_LOCK:
            if cls._initialized:
                return

            if TASKS_FILE.exists():
                try:
                    raw = TASKS_FILE.read_text(encoding="utf-8")
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        cls._tasks = data
                    elif isinstance(data, list):
                        cls._tasks = {t["id"]: t for t in data if "id" in t}
                except Exception as e:
                    print(f"⚠️ [TaskManager] Failed to load tasks from disk: {e}")
                    cls._tasks = {}

            # Mark any tasks that were left in processing/queued as failed (server crashed/restarted)
            changed = False
            for task_id, task in cls._tasks.items():
                if task.get("status") in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
                    task["status"] = TaskStatus.FAILED
                    task["error"] = "เซิร์ฟเวอร์รีสตาร์ท — งานถูกยกเลิกอัตโนมัติ"
                    task["step_label"] = "งานถูกขัดจังหวะจากการรีสตาร์ทระบบ"
                    task["updated_at"] = cls._now_iso()
                    changed = True

            cls._initialized = True
            if changed:
                cls._save_to_disk_locked()

    _last_disk_save = 0.0

    @classmethod
    def _save_to_disk_locked(cls, force: bool = True) -> None:
        """Writes current tasks to disk atomically with throttling and Windows retry."""
        now = time.time()
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
            # Fallback direct write if atomic rename is blocked by momentary file locks
            TASKS_FILE.write_text(json.dumps(cls._tasks, ensure_ascii=False, indent=2), encoding="utf-8")
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
    ) -> Dict[str, Any]:
        """Creates and registers a new task."""
        cls.initialize()
        t_id = task_id or f"task_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
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
            "logs": [{"time": datetime.datetime.now().strftime("%H:%M:%S"), "msg": "งานถูกสร้างขึ้นในระบบ", "progress": 0}],
        }

        with _TASK_LOCK:
            cls._tasks[t_id] = task_obj
            cls._save_to_disk_locked()

        return task_obj

    @classmethod
    def update_progress(
        cls,
        task_id: str,
        progress: float,
        step_label: Optional[str] = None,
        msg: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates progress and step label for a task."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task:
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
    ) -> Optional[Dict[str, Any]]:
        """Marks a task as completed."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task:
                return None

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
    ) -> Optional[Dict[str, Any]]:
        """Marks a task as failed."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task:
                return None

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
    def cancel_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """Cancels a pending or running task."""
        cls.initialize()
        with _TASK_LOCK:
            task = cls._tasks.get(task_id)
            if not task:
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
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single task by ID."""
        cls.initialize()
        with _TASK_LOCK:
            return cls._tasks.get(task_id)

    @classmethod
    def get_active_tasks(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns all running/queued tasks plus recent completed/failed tasks (sorted by updated_at desc)."""
        cls.initialize()
        with _TASK_LOCK:
            all_list = list(cls._tasks.values())
            # Sort newest first
            all_list.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
            return all_list[:limit]

    @classmethod
    def delete_task(cls, task_id: str) -> bool:
        """Deletes a task from registry."""
        cls.initialize()
        with _TASK_LOCK:
            if task_id in cls._tasks:
                del cls._tasks[task_id]
                cls._save_to_disk_locked()
                return True
            return False

    @classmethod
    def clear_completed(cls) -> int:
        """Clears all completed, failed, or cancelled tasks."""
        cls.initialize()
        with _TASK_LOCK:
            to_del = [
                tid for tid, t in cls._tasks.items()
                if t.get("status") in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
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
