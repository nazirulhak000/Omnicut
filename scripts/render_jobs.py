"""
Shared render-job registry.

Full renders and partial re-rolls both run in the background and both are
watched by the same frontend polling loop, so they have to land in one
registry — otherwise /api/render/status/{job_id} would not find a re-roll.

Jobs live in memory only: a server restart forgets them, which is fine because
the artifacts themselves are on disk and recorded in the project manifest.
"""

import datetime
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional

from scripts.config import BASE_DIR

ACTIVE_JOBS: Dict[str, Dict[str, Any]] = {}

# Single well-known owner for the current single-user deployment -- mirrors
# scripts.task_manager.DEFAULT_OWNER. Jobs created without an explicit
# owner_id are attributed to this constant so behavior for today's one user
# is unchanged. Real per-tenant owners arrive with auth (later step).
DEFAULT_OWNER = "local"


def _owned_by(job: Dict[str, Any], owner_id: Optional[str]) -> bool:
    """True if `owner_id` is unset (unscoped call) or matches the job's owner.

    Jobs created before this field existed have no "owner_id" key -- treat
    those as DEFAULT_OWNER so in-flight jobs from just before a hot-reload
    keep working under scoping.
    """
    if owner_id is None:
        return True
    return job.get("owner_id", DEFAULT_OWNER) == owner_id

# This machine renders on CPU with no CUDA and 13.7GB RAM (see
# _Docs/PRD_phase1.md section 3) -- two ffmpeg encodes or two TTS calls at
# once is a real OOM/thrash risk, not a theoretical one. Every render and
# re-roll acquires this before touching the pipeline, so only one clip is
# ever being produced at a time; everything else waits its turn as "queued".
_RENDER_SLOT = threading.Lock()


def is_busy() -> bool:
    """True while a render holds the slot -- callers use it to refuse work
    that would pull files out from under the running job."""
    return _RENDER_SLOT.locked()


def _prune_old_jobs(max_keep: int = 50) -> None:
    """Prunes finished/failed jobs to keep memory footprint strictly bounded (max 50 jobs)."""
    if len(ACTIVE_JOBS) <= max_keep:
        return
    finished_keys = [
        k for k, v in ACTIVE_JOBS.items()
        if v.get("status") in ("completed", "failed")
    ]
    excess = len(ACTIVE_JOBS) - max_keep
    for k in finished_keys[:excess]:
        ACTIVE_JOBS.pop(k, None)


def create_job(job_id: str, message: str = "กำลังเริ่มต้นกระบวนการ...", owner_id: Optional[str] = None) -> Dict[str, Any]:
    """Register a queued job and return it."""
    _prune_old_jobs(max_keep=50)
    ACTIVE_JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0.0,
        "message": message,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "logs": [],
        "result": None,
        "error": None,
        "owner_id": owner_id or DEFAULT_OWNER,
    }
    return ACTIVE_JOBS[job_id]


def get_job(job_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single job by ID, scoped to `owner_id` when given.

    A job_id that exists but belongs to a different owner behaves exactly
    like a missing job_id (returns None) -- never a permission error that
    would confirm the id exists.
    """
    job = ACTIVE_JOBS.get(job_id)
    if not job or not _owned_by(job, owner_id):
        return None
    return job


@contextmanager
def render_slot(job_id: str, owner_id: Optional[str] = None) -> Iterator[None]:
    """
    Block until it is this job's turn to actually render, updating its status
    to "queued" with an explanatory message for as long as it has to wait.

    Usage:
        with render_slot(job_id):
            TikTokAutoCutterPipeline.run(...)
    """
    if _RENDER_SLOT.locked():
        job = get_job(job_id, owner_id=owner_id)
        if job:
            job["status"] = "queued"
            job["message"] = "รอคิว — เครื่องนี้ตัดต่อได้ทีละคลิป มีงานอื่นกำลังทำอยู่"

    _RENDER_SLOT.acquire()
    try:
        yield
    finally:
        _RENDER_SLOT.release()


def progress_reporter(job_id: str, owner_id: Optional[str] = None) -> Callable[[str, float], None]:
    """A `progress_callback` for the pipeline that writes into the job."""
    def on_progress(msg: str, progress: float) -> None:
        job = get_job(job_id, owner_id=owner_id)
        if not job:
            return
        job["status"] = "processing"
        job["progress"] = min(1.0, max(0.0, progress))
        job["message"] = msg
        job["logs"].append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "msg": msg,
            "progress": int(progress * 100),
        })

    return on_progress


def update_progress(job_id: str, progress: float, message: str = "", owner_id: Optional[str] = None) -> None:
    """Direct helper to update a job's progress and message."""
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return
    job["status"] = "processing"
    job["progress"] = min(1.0, max(0.0, float(progress)))
    if message:
        job["message"] = str(message)
    job["logs"].append({
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "msg": message or job.get("message", ""),
        "progress": int(job["progress"] * 100),
    })


def media_url(file_path: Optional[str]) -> Optional[str]:
    """Turn an absolute artifact path into a /api/media URL the browser can load."""
    if not file_path:
        return None
    path = Path(file_path)
    if not path.exists():
        return None
    try:
        relative = path.relative_to(BASE_DIR)
    except ValueError:
        return None
    return f"/api/media/{relative}".replace("\\", "/")


def complete_job(job_id: str, result: Dict[str, Any], message: str = "🎉 การตัดต่อเสร็จสมบูรณ์ 100%!", owner_id: Optional[str] = None) -> None:
    """Mark a job finished, shaping the pipeline result for the frontend."""
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return
    job["status"] = "completed"
    job["progress"] = 1.0
    job["message"] = message
    job["result"] = {
        "project_name": result.get("project_name"),
        "mp4_video": result.get("mp4_video"),
        "mp4_url": media_url(result.get("mp4_video")),
        "duration": result.get("duration", 0),
        "script": result.get("script"),
        "manifest": result.get("manifest"),
    }


def fail_job(job_id: str, error: Any, owner_id: Optional[str] = None) -> None:
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return
    job["status"] = "failed"

    from scripts.error_handler import classify_exception, AppError, log_structured_error

    if isinstance(error, AppError):
        app_err = error
    else:
        # job["result"] is only populated by complete_job(), so on this path
        # it is always absent -- the name has to come from the exception the
        # pipeline stamped it onto, or from the job's own record.
        proj = (
            getattr(error, "pipeline_project_name", None)
            or job.get("project_name")
            or (job.get("result") or {}).get("project_name")
        )
        app_err = classify_exception(error if isinstance(error, Exception) else Exception(str(error)), project_name=proj, job_id=job_id)

    log_structured_error(app_err)

    job["error"] = app_err.message_th
    job["error_category"] = app_err.category.value
    job["error_code"] = app_err.code
    job["suggestion_th"] = app_err.suggestion_th
    job["message"] = f"❌ {app_err.message_th}"
    job["logs"].append({
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "msg": f"[{app_err.code}] {app_err.message_th}",
        "progress": 0,
    })
