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

from fastapi import HTTPException

from scripts.config import BASE_DIR

class RenderCancelled(Exception):
    """
    Raised when a job's cancel_event is observed set -- inside the pipeline's
    stage loop (scripts/pipeline.py) or inside the ffmpeg polling loop
    (scripts/video_editor.py). Deliberately a distinct type from every other
    failure so api_render.py / api_phase1.py can tell "the user asked to stop
    this" apart from "this actually broke" and route each to the right
    terminal state (cancelled vs failed) instead of collapsing both into the
    generic except Exception path.

    Lives here (not in pipeline.py) so video_editor.py can raise/import it
    too without a pipeline.py <-> video_editor.py import cycle -- pipeline.py
    already imports VideoEditor from video_editor.py.
    """


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

# How many callers may be blocked waiting for _RENDER_SLOT before a new one
# is refused outright instead of joining the wait. Most endpoints in this
# app are synchronous `def`s that FastAPI runs on its threadpool -- render_
# slot()'s wait used to be a bare, uncapped acquire(), so a burst of queued
# render/reroll requests could alone exhaust that threadpool and take down
# every OTHER endpoint (status polling included), not just rendering.
MAX_QUEUED_RENDERS = 3

# Guards _QUEUED_COUNT -- a separate, tiny lock rather than piggybacking on
# _RENDER_SLOT itself, since the whole point is to check/reserve a queue
# slot *before* touching _RENDER_SLOT.
_QUEUE_COUNT_LOCK = threading.Lock()
_QUEUED_COUNT = 0


def is_busy() -> bool:
    """True while a render holds the slot -- callers use it to refuse work
    that would pull files out from under the running job."""
    return _RENDER_SLOT.locked()


def queued_count() -> int:
    """How many callers are currently blocked waiting for _RENDER_SLOT (not
    counting whichever one holds it)."""
    with _QUEUE_COUNT_LOCK:
        return _QUEUED_COUNT


def _prune_old_jobs(max_keep: int = 50) -> None:
    """Prunes finished/failed jobs to keep memory footprint strictly bounded (max 50 jobs)."""
    if len(ACTIVE_JOBS) <= max_keep:
        return
    finished_keys = [
        k for k, v in ACTIVE_JOBS.items()
        if v.get("status") in ("completed", "failed", "cancelled")
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
        # Cooperative-cancellation signal: the pipeline and the ffmpeg polling
        # loop both check this between units of work and unwind with
        # RenderCancelled when it is set. request_cancel() is the only writer.
        "cancel_event": threading.Event(),
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

    Refuses outright (HTTP 429) instead of joining the wait once
    MAX_QUEUED_RENDERS callers are already queued -- see that constant's
    comment for why an uncapped wait here is dangerous for the whole API, not
    just for rendering.

    Usage:
        with render_slot(job_id):
            TikTokAutoCutterPipeline.run(...)
    """
    global _QUEUED_COUNT

    must_wait = _RENDER_SLOT.locked()
    if must_wait:
        with _QUEUE_COUNT_LOCK:
            if _QUEUED_COUNT >= MAX_QUEUED_RENDERS:
                raise HTTPException(
                    status_code=429,
                    detail="คิวเรนเดอร์เต็ม — มีงานรออยู่หลายรายการแล้ว กรุณารอสักครู่แล้วลองใหม่",
                )
            _QUEUED_COUNT += 1

        job = get_job(job_id, owner_id=owner_id)
        if job:
            job["status"] = "queued"
            job["message"] = "รอคิว — เครื่องนี้ตัดต่อได้ทีละคลิป มีงานอื่นกำลังทำอยู่"

    try:
        _RENDER_SLOT.acquire()
    finally:
        if must_wait:
            with _QUEUE_COUNT_LOCK:
                _QUEUED_COUNT -= 1

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
        # A "cancelling" job is already unwinding -- don't bounce it back to
        # "processing" just because one more progress tick arrives before the
        # cancel is actually observed by the pipeline/ffmpeg loop.
        if job.get("status") not in ("cancelling", "cancelled"):
            job["status"] = "processing"
        job["progress"] = min(1.0, max(0.0, progress))
        job["message"] = msg
        job["logs"].append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "msg": msg,
            "progress": int(progress * 100),
        })
        # ffmpeg progress ticks land here at ~2.5/sec -- a 5-minute render
        # would otherwise grow this list to ~750 entries, and the status-
        # polling endpoint returns the whole job dict (logs included) on
        # every poll, so an uncapped list makes polling traffic grow with
        # render duration. Keep only the most recent entries, same cap
        # TaskManager.update_progress() already uses for the same reason.
        if len(job["logs"]) > 50:
            job["logs"] = job["logs"][-50:]

    return on_progress


def update_progress(job_id: str, progress: float, message: str = "", owner_id: Optional[str] = None) -> None:
    """Direct helper to update a job's progress and message."""
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return
    if job.get("status") not in ("cancelling", "cancelled"):
        job["status"] = "processing"
    job["progress"] = min(1.0, max(0.0, float(progress)))
    if message:
        job["message"] = str(message)
    job["logs"].append({
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "msg": message or job.get("message", ""),
        "progress": int(job["progress"] * 100),
    })
    # Same unbounded-growth concern as progress_reporter()'s on_progress()
    # above -- this is the other call site the pipeline uses per-tick.
    if len(job["logs"]) > 50:
        job["logs"] = job["logs"][-50:]


def request_cancel(job_id: str, owner_id: Optional[str] = None) -> bool:
    """
    Ask a running/queued job to stop. Sets its cancel_event (so the pipeline
    and the ffmpeg polling loop notice cooperatively) and moves its status to
    the transient "cancelling" state -- not yet terminal, since the worker
    thread may take a moment to actually unwind. Returns False when the job
    is unknown or already in a terminal state (nothing left to cancel).
    """
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return False
    if job.get("status") in ("completed", "failed", "cancelled"):
        return False

    event = job.get("cancel_event")
    if event is None:
        # Job created before this field existed (e.g. across a hot-reload) --
        # give it one now so is_cancel_requested() still works going forward.
        event = threading.Event()
        job["cancel_event"] = event
    event.set()

    job["status"] = "cancelling"
    job["message"] = "กำลังยกเลิกงาน..."
    job["logs"].append({
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "msg": "ผู้ใช้ขอยกเลิกงาน — กำลังรอให้หยุดอย่างปลอดภัย",
        "progress": int(job.get("progress", 0.0) * 100),
    })
    return True


def is_cancel_requested(job_id: str, owner_id: Optional[str] = None) -> bool:
    """True if request_cancel() has been called for this job."""
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return False
    event = job.get("cancel_event")
    return bool(event and event.is_set())


def get_cancel_event(job_id: str, owner_id: Optional[str] = None) -> Optional[threading.Event]:
    """The job's cancel_event itself, for threading into the pipeline/ffmpeg
    call as `cancel_event=` rather than polling by job_id from deep inside."""
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return None
    return job.get("cancel_event")


def cancel_job(job_id: str, message: str = "งานถูกยกเลิกโดยผู้ใช้", owner_id: Optional[str] = None) -> None:
    """Mark a job's final, terminal "cancelled" state once its worker thread
    has actually unwound (called from the RenderCancelled except branch) --
    distinct from "cancelling", which only means a stop was requested."""
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return
    job["status"] = "cancelled"
    job["message"] = message
    job["logs"].append({
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "msg": message,
        "progress": int(job.get("progress", 0.0) * 100),
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
    """Publish completion only after the final project write has settled."""
    job = get_job(job_id, owner_id=owner_id)
    if not job:
        return
    shaped_result = {
        "project_name": result.get("project_name"),
        "mp4_video": result.get("mp4_video"),
        "mp4_url": media_url(result.get("mp4_video")),
        "duration": result.get("duration", 0),
        "script": result.get("script"),
        "manifest": result.get("manifest"),
        # The editor shows a warning bar when the full audio mix fell back to
        # voice-only (no music / SFX in the clip).
        "mix_degraded": bool(result.get("mix_degraded")),
        "mix_degraded_reason": result.get("mix_degraded_reason"),
    }
    project_name = result.get("project_name")
    if project_name:
        try:
            metadata = finalize_incremental_render(project_name)
            if metadata:
                job["incremental_render"] = {
                    "schema_version": metadata.get("schema_version"),
                    "stages": sorted((metadata.get("stage_fingerprints") or {}).keys()),
                    "artifacts": sorted((metadata.get("artifact_fingerprints") or {}).keys()),
                }
        except Exception as fingerprint_err:
            # Fingerprints harden future reuse but are not part of the render
            # output itself. Do not report a successful video as failed because
            # a best-effort metadata stamp could not be written.
            job.setdefault("logs", []).append({
                "time": datetime.datetime.now().strftime("%H:%M:%S"),
                "msg": f"Incremental reuse metadata unavailable: {fingerprint_err}",
                "progress": 100,
            })

    # Status polling stops at completed and the editor immediately reads the
    # project revision. Publish the terminal status last, after metadata has
    # finished writing and the complete response payload is available.
    job["result"] = shaped_result
    job["progress"] = 1.0
    job["message"] = message
    job["status"] = "completed"


def finalize_incremental_render(project_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """Stamp fingerprints after the pipeline has atomically saved its manifest.

    The pipeline's stage implementation owns the initial manifest write, while
    this job seam owns the successful-render transition. Keeping the metadata
    write here covers both `/api/render` and the shared reroll worker without
    changing stage ordering or the render slot. Failure to stamp metadata never
    turns a completed render into a failed job; legacy path validation remains
    available until the next successful completion.
    """
    if not project_name:
        return None

    from scripts.pipeline_context import build_incremental_render_metadata
    from scripts.project_manifest import ProjectManifest

    manifest = ProjectManifest.load(project_name)
    if not manifest:
        return None
    metadata = build_incremental_render_metadata(manifest)
    updated = ProjectManifest.save(project_name, incremental_render=metadata)
    return updated.get("incremental_render")


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
