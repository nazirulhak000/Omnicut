"""
Shared render-job registry.

Full renders and partial re-rolls both run in the background and both are
watched by the same frontend polling loop, so they have to land in one
registry — otherwise /api/render/status/{job_id} would not find a re-roll.

Jobs live in memory only: a server restart forgets them, which is fine because
the artifacts themselves are on disk and recorded in the project manifest.
"""

import collections
import datetime
import os
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


def pin_job_scope(channel_id=None, job_scope=None) -> Dict[str, Any]:
    """Copy JSON provenance once, rejecting an owner conflict without normalization."""
    import json
    from scripts.channel_store import ChannelError, is_valid_channel_id
    try:
        pinned = json.loads(json.dumps(job_scope or {}, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise ChannelError(422, "channel_scope_invalid", "ข้อมูลขอบเขตงานต้องเป็น JSON") from exc
    fields = {"channel_id", "channel_scope_source", "channel_scope_strict", "channel_status", "channel_revision", "channel_identity_hash", "channel_identity_snapshot"}
    if not isinstance(pinned, dict) or set(pinned) - fields:
        raise ChannelError(422, "channel_scope_invalid", "ข้อมูลขอบเขตงานไม่ถูกต้อง")
    captured_id = pinned.get("channel_id")
    if channel_id is not None and captured_id is not None and channel_id != captured_id:
        raise ChannelError(422, "channel_scope_conflict", "ช่องของงานไม่ตรงกับ request")
    effective = channel_id if channel_id is not None else captured_id
    if effective is not None:
        if not is_valid_channel_id(effective):
            raise ChannelError(422, "channel_scope_invalid", "channel_id ของงานไม่ถูกต้อง")
        snapshot = pinned.get("channel_identity_snapshot")
        if snapshot is not None and (not isinstance(snapshot, dict) or snapshot.get("id") != effective):
            raise ChannelError(422, "channel_scope_conflict", "identity ของงานไม่ตรงกับช่อง")
        pinned["channel_id"] = effective
    return pinned


def _owned_by(job: Dict[str, Any], owner_id: Optional[str], channel_id: Optional[str] = None) -> bool:
    """True if `owner_id` is unset (unscoped call) or matches the job's owner.

    Jobs created before this field existed have no "owner_id" key -- treat
    those as DEFAULT_OWNER so in-flight jobs from just before a hot-reload
    keep working under scoping.
    """
    owner_matches = owner_id is None or job.get("owner_id", DEFAULT_OWNER) == owner_id
    channel_matches = channel_id is None or (job.get("channel_id") or "main") == channel_id
    return owner_matches and channel_matches

# Render slot pool (AGENTS rules 21 + 24). This machine is a 20-core / 32GB
# RAM workstation with an RTX 4060 (8GB VRAM): four pipelines at once fit
# comfortably (~4.5GB RAM, ~2GB VRAM), so up to RENDER_MAX_CONCURRENT clips
# render in parallel. Every render, re-roll and batch item acquires one slot
# before touching the pipeline; anything beyond the pool waits as "queued".
# Override with OMNICUT_RENDER_CONCURRENCY (clamped to 1..4) -- 1 restores
# the old one-clip-at-a-time behaviour.
RENDER_CONCURRENCY_ENV = "OMNICUT_RENDER_CONCURRENCY"
RENDER_CONCURRENCY_DEFAULT = 4
RENDER_CONCURRENCY_MIN = 1
RENDER_CONCURRENCY_MAX = 4


def resolve_render_concurrency(raw: Optional[str] = None) -> int:
    """Parse a concurrency override (env var when `raw` is None), clamped.

    Missing/blank/garbage values fall back to RENDER_CONCURRENCY_DEFAULT;
    numbers outside 1..4 are clamped rather than rejected so a typo in the
    env never stops the server from starting.
    """
    if raw is None:
        raw = os.environ.get(RENDER_CONCURRENCY_ENV)
    if raw is None or not str(raw).strip():
        return RENDER_CONCURRENCY_DEFAULT
    try:
        value = int(str(raw).strip())
    except ValueError:
        return RENDER_CONCURRENCY_DEFAULT
    return max(RENDER_CONCURRENCY_MIN, min(RENDER_CONCURRENCY_MAX, value))


class RenderQueueFull(Exception):
    """Raised by _SlotPool.enqueue when the wait queue is at capacity."""


class _SlotPool:
    """Bounded, strictly FIFO pool of render slots.

    A plain Semaphore lets a thread that just released a slot barge back in
    ahead of threads already waiting -- a 4-worker batch would then starve a
    single render/re-roll indefinitely. Here waiters are served in arrival
    order, and a newcomer never jumps a non-empty queue.
    """

    def __init__(self, capacity: int):
        self.capacity = max(1, int(capacity))
        self._cond = threading.Condition(threading.Lock())
        self._active = 0
        self._waiters: "collections.deque[object]" = collections.deque()

    def active(self) -> int:
        with self._cond:
            return self._active

    def waiting(self) -> int:
        with self._cond:
            return len(self._waiters)

    def try_acquire(self) -> bool:
        with self._cond:
            if not self._waiters and self._active < self.capacity:
                self._active += 1
                return True
            return False

    def enqueue(self, max_waiting: int) -> object:
        """Reserve a place in line, or raise RenderQueueFull."""
        with self._cond:
            if len(self._waiters) >= max_waiting:
                raise RenderQueueFull()
            ticket = object()
            self._waiters.append(ticket)
            return ticket

    def acquire_ticket(self, ticket: object) -> None:
        """Block until `ticket` is first in line and a slot is free."""
        with self._cond:
            try:
                while self._waiters[0] is not ticket or self._active >= self.capacity:
                    self._cond.wait()
            except BaseException:
                try:
                    self._waiters.remove(ticket)
                except ValueError:
                    pass
                self._cond.notify_all()
                raise
            self._waiters.popleft()
            self._active += 1
            # The next in line may also fit (several slots freed at once).
            self._cond.notify_all()

    def release(self) -> None:
        with self._cond:
            if self._active <= 0:
                raise RuntimeError("render slot released more times than acquired")
            self._active -= 1
            self._cond.notify_all()


RENDER_MAX_CONCURRENT = resolve_render_concurrency()
_RENDER_SLOTS = _SlotPool(RENDER_MAX_CONCURRENT)

# How many callers may be blocked waiting for a render slot before a new one
# is refused outright instead of joining the wait. Most endpoints in this
# app are synchronous `def`s that FastAPI runs on its threadpool -- render_
# slot()'s wait used to be a bare, uncapped acquire(), so a burst of queued
# render/reroll requests could alone exhaust that threadpool and take down
# every OTHER endpoint (status polling included), not just rendering.
MAX_QUEUED_RENDERS = 3

# Guards ACTIVE_JOBS insert/prune: concurrent create_job calls (batch items
# render four at a time) must not mutate the dict while _prune_old_jobs
# iterates it.
_JOBS_LOCK = threading.RLock()


def render_concurrency() -> int:
    """How many clips may render at once (size of the slot pool)."""
    return _RENDER_SLOTS.capacity


def set_render_concurrency(value: Any) -> int:
    """Resize the slot pool (clamped 1..4). Only allowed while idle --
    swapping the pool under a running render would orphan its slot."""
    global RENDER_MAX_CONCURRENT, _RENDER_SLOTS
    size = resolve_render_concurrency(str(value))
    if _RENDER_SLOTS.active() or _RENDER_SLOTS.waiting():
        raise RuntimeError("cannot resize the render slot pool while renders are running or queued")
    RENDER_MAX_CONCURRENT = size
    _RENDER_SLOTS = _SlotPool(size)
    return size


def is_busy() -> bool:
    """True while at least one render holds a slot -- callers use it to refuse
    work that would pull files out from under a running job (delete/archive
    project), so it stays true as long as ANY clip is rendering, not only
    when the pool is full."""
    return _RENDER_SLOTS.active() > 0


def active_count() -> int:
    """How many renders currently hold a slot."""
    return _RENDER_SLOTS.active()


def queued_count() -> int:
    """How many callers are currently blocked waiting for a render slot (not
    counting the ones holding one)."""
    return _RENDER_SLOTS.waiting()


# Per-project render mutex. With one global slot two renders of the SAME
# project could never overlap; with a pool they can (double-clicked render,
# a re-roll while a batch re-renders that angle), and both would write the
# same 03_Projects/<name>/ folder and manifest. TikTokAutoCutterPipeline.run
# takes this for its project, so same-project renders queue behind each other
# while different projects still render in parallel.
_PROJECT_LOCKS_GUARD = threading.Lock()
_PROJECT_LOCKS: Dict[str, list] = {}  # key -> [RLock, refcount]
PROJECT_LOCK_POLL_SECONDS = 0.5


def _project_lock_key(project_name: str, channel_id: Optional[str]) -> str:
    name = str(project_name).replace("\\", "/").strip("/")
    if channel_id and channel_id != "main" and "/" not in name:
        name = f"{channel_id}/{name}"
    return os.path.normcase(name)


class _ProjectLockHandle:
    def __init__(self, key: Optional[str] = None, entry: Optional[list] = None):
        self._key = key
        self._entry = entry

    def release(self) -> None:
        if self._entry is None:
            return
        entry, self._entry = self._entry, None
        entry[0].release()
        _drop_project_lock_ref(self._key, entry)


def _drop_project_lock_ref(key: Optional[str], entry: list) -> None:
    with _PROJECT_LOCKS_GUARD:
        entry[1] -= 1
        if entry[1] <= 0 and _PROJECT_LOCKS.get(key) is entry:
            del _PROJECT_LOCKS[key]


def acquire_project_render_lock(
    project_name: Optional[str],
    *,
    channel_id: Optional[str] = None,
    cancel_event: Optional[threading.Event] = None,
) -> _ProjectLockHandle:
    """Block until no other render is producing `project_name`; returns a
    handle whose release() must be called. A falsy name (the pipeline will
    invent a fresh one) needs no lock. Waiting honours `cancel_event` by
    raising RenderCancelled."""
    if not project_name:
        return _ProjectLockHandle()
    key = _project_lock_key(project_name, channel_id)
    with _PROJECT_LOCKS_GUARD:
        entry = _PROJECT_LOCKS.get(key)
        if entry is None:
            entry = _PROJECT_LOCKS[key] = [threading.RLock(), 0]
        entry[1] += 1
    try:
        while not entry[0].acquire(timeout=PROJECT_LOCK_POLL_SECONDS):
            if cancel_event is not None and cancel_event.is_set():
                raise RenderCancelled(f"Render cancelled while waiting for project '{project_name}'")
    except BaseException:
        _drop_project_lock_ref(key, entry)
        raise
    return _ProjectLockHandle(key, entry)


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


def create_job(job_id: str, message: str = "กำลังเริ่มต้นกระบวนการ...", owner_id: Optional[str] = None, *, channel_id: Optional[str] = None, job_scope: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Register a queued job and return it."""
    pinned = pin_job_scope(channel_id, job_scope)
    prior = ACTIVE_JOBS.get(job_id)
    if prior and pinned.get("channel_id") and not _owned_by(prior, owner_id, pinned["channel_id"]):
        from scripts.channel_store import ChannelError
        raise ChannelError(409, "channel_job_collision", "id งานมีอยู่แล้ว")
    with _JOBS_LOCK:
        return _register_job(job_id, owner_id, message, pinned)


def _register_job(job_id: str, owner_id: Optional[str], message: str, pinned: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a fresh queued job (caller holds _JOBS_LOCK)."""
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
        **pinned,
    }
    return ACTIVE_JOBS[job_id]


def get_job(job_id: str, owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single job by ID, scoped to `owner_id` when given.

    A job_id that exists but belongs to a different owner behaves exactly
    like a missing job_id (returns None) -- never a permission error that
    would confirm the id exists.
    """
    job = ACTIVE_JOBS.get(job_id)
    if not job or not _owned_by(job, owner_id, channel_id):
        return None
    return job


@contextmanager
def render_slot(job_id: str, owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> Iterator[None]:
    """
    Block until one of the RENDER_MAX_CONCURRENT slots is free and it is this
    job's turn (strict FIFO), updating its status to "queued" with an
    explanatory message for as long as it has to wait.

    Refuses outright (HTTP 429) instead of joining the wait once
    MAX_QUEUED_RENDERS callers are already queued -- see that constant's
    comment for why an uncapped wait here is dangerous for the whole API, not
    just for rendering.

    Usage:
        with render_slot(job_id):
            TikTokAutoCutterPipeline.run(...)
    """
    pool = _RENDER_SLOTS
    if not pool.try_acquire():
        try:
            ticket = pool.enqueue(MAX_QUEUED_RENDERS)
        except RenderQueueFull:
            raise HTTPException(
                status_code=429,
                detail="คิวเรนเดอร์เต็ม — มีงานรออยู่หลายรายการแล้ว กรุณารอสักครู่แล้วลองใหม่",
            )
        try:
            job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
            if job:
                job["status"] = "queued"
                job["message"] = f"รอคิว — เครื่องนี้ตัดต่อพร้อมกันได้ {pool.capacity} คลิป ตอนนี้ช่องเต็มอยู่"
        finally:
            # acquire_ticket always consumes or discards the ticket, so a
            # failure above can never leave a dead ticket blocking the line.
            pool.acquire_ticket(ticket)

    try:
        yield
    finally:
        pool.release()


def progress_reporter(job_id: str, owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> Callable[[str, float], None]:
    """A `progress_callback` for the pipeline that writes into the job."""
    def on_progress(msg: str, progress: float) -> None:
        job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
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


def update_progress(job_id: str, progress: float, message: str = "", owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> None:
    """Direct helper to update a job's progress and message."""
    job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
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


def request_cancel(job_id: str, owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> bool:
    """
    Ask a running/queued job to stop. Sets its cancel_event (so the pipeline
    and the ffmpeg polling loop notice cooperatively) and moves its status to
    the transient "cancelling" state -- not yet terminal, since the worker
    thread may take a moment to actually unwind. Returns False when the job
    is unknown or already in a terminal state (nothing left to cancel).
    """
    job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
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


def is_cancel_requested(job_id: str, owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> bool:
    """True if request_cancel() has been called for this job."""
    job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
    if not job:
        return False
    event = job.get("cancel_event")
    return bool(event and event.is_set())


def get_cancel_event(job_id: str, owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> Optional[threading.Event]:
    """The job's cancel_event itself, for threading into the pipeline/ffmpeg
    call as `cancel_event=` rather than polling by job_id from deep inside."""
    job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
    if not job:
        return None
    return job.get("cancel_event")


def cancel_job(job_id: str, message: str = "งานถูกยกเลิกโดยผู้ใช้", owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> None:
    """Mark a job's final, terminal "cancelled" state once its worker thread
    has actually unwound (called from the RenderCancelled except branch) --
    distinct from "cancelling", which only means a stop was requested."""
    job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
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


def complete_job(job_id: str, result: Dict[str, Any], message: str = "🎉 การตัดต่อเสร็จสมบูรณ์ 100%!", owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> None:
    """Publish completion only after the final project write has settled."""
    job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
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
            metadata = finalize_incremental_render(project_name, **({"channel_id": job["channel_id"]} if job.get("channel_id") else {}))
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


def finalize_incremental_render(project_name: Optional[str], *, channel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
    if channel_id is not None:
        from scripts.channel_scope import ChannelScope, ensure_same_channel
        ensure_same_channel(ChannelScope(channel_id, "header", False), manifest.get("channel_id"), resource_label="โปรเจกต์", allow_legacy_main=True)
    metadata = build_incremental_render_metadata(manifest)
    updated = ProjectManifest.save(project_name, incremental_render=metadata)
    return updated.get("incremental_render")


def fail_job(job_id: str, error: Any, owner_id: Optional[str] = None, *, channel_id: Optional[str] = None) -> None:
    job = get_job(job_id, owner_id=owner_id, channel_id=channel_id)
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
