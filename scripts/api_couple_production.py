"""
FastAPI router for Couple Paper Chat batch production jobs, checkpoints,
SSE event streaming, and preflight environment diagnostics.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from scripts import config
from scripts.couple_jobs import (
    CoupleJobError,
    CoupleJobStore,
)


router = APIRouter(prefix="/api/couple", tags=["CoupleProduction"])

_default_store: Optional[CoupleJobStore] = None
_default_store_dir: Optional[str] = None
_executor_hook: Optional[Callable[[Dict[str, Any], CoupleJobStore], Any]] = None


def get_couple_job_store() -> CoupleJobStore:
    """Returns the active CoupleJobStore, re-binding automatically if
    `config.BASE_DIR` changed (e.g. in isolated test fixtures).
    """
    global _default_store, _default_store_dir
    target_dir = str((config.BASE_DIR / "_Docs").resolve())
    if _default_store is None or (_default_store._explicit_storage is None and _default_store_dir != target_dir):
        _default_store = CoupleJobStore()
        _default_store_dir = target_dir
    return _default_store


def set_couple_job_store(store: Optional[CoupleJobStore]) -> None:
    """Allows tests or the application bootstrap to inject a custom store."""
    global _default_store, _default_store_dir
    _default_store = store
    _default_store_dir = str(store.storage_dir) if store is not None else None


def set_executor_hook(hook: Optional[Callable[[Dict[str, Any], CoupleJobStore], Any]]) -> None:
    """Configures an optional background executor callback invoked when a new
    job is created or resumed.
    """
    global _executor_hook
    _executor_hook = hook


def _raise_http_for_job_error(exc: CoupleJobError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={
            "message": exc.message,
            "code": exc.code,
        },
    ) from exc


# ── Pydantic Models ─────────────────────────────────────────────────────


class CreateCoupleJobRequest(BaseModel):
    product_code: str = Field(..., description="Product code, e.g. TTZ01, HAT01")
    total_clips: int = Field(20, ge=1, le=100, description="Number of clips in batch (default 20)")
    idempotency_key: Optional[str] = Field(None, description="Optional client idempotency key")


class CheckpointDecisionRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    expected_revision: Optional[int] = Field(None, description="Optimistic concurrency revision check")
    note: str = Field("", description="Optional reviewer note")


class PauseJobRequest(BaseModel):
    reason: str = Field("user", description="Pause reason: 'user' or 'quota'")


# ── Preflight Probes ────────────────────────────────────────────────────


def _probe_gpu_nvenc() -> Dict[str, Any]:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return {
            "available": False,
            "nvenc": False,
            "encoder": "libx264",
            "detail": "ไม่พบ ffmpeg ในระบบ",
        }
    try:
        proc = subprocess.run(
            [ffmpeg_bin, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        has_nvenc = "h264_nvenc" in (proc.stdout or "")
        return {
            "available": has_nvenc,
            "nvenc": has_nvenc,
            "encoder": "h264_nvenc" if has_nvenc else "libx264",
            "detail": "พร้อมใช้งาน h264_nvenc" if has_nvenc else "ใช้ CPU fallback (libx264)",
        }
    except Exception as exc:
        return {
            "available": False,
            "nvenc": False,
            "encoder": "libx264",
            "detail": f"ตรวจสอบ NVENC ไม่สำเร็จ: {exc}",
        }


def _probe_node_hyperframes() -> Dict[str, Any]:
    node_bin = shutil.which("node")
    hf_bin = shutil.which("hyperframes") or shutil.which("npx")
    studio_dir = config.BASE_DIR / "03_Projects" / "_HyperFrames_Studio"
    node_ready = bool(node_bin)
    hf_ready = bool(node_bin and (hf_bin or studio_dir.exists()))
    return {
        "ready": hf_ready,
        "node_available": node_ready,
        "hyperframes_available": hf_ready,
        "detail": "พร้อมใช้งาน Node และ HyperFrames" if hf_ready else "ไม่พบ Node หรือ HyperFrames CLI",
    }


def _probe_whisper() -> Dict[str, Any]:
    has_faster_whisper = importlib.util.find_spec("faster_whisper") is not None
    has_openai_whisper = importlib.util.find_spec("whisper") is not None
    ready = has_faster_whisper or has_openai_whisper
    backend = "faster_whisper" if has_faster_whisper else ("whisper" if has_openai_whisper else "none")
    return {
        "ready": ready,
        "backend": backend,
        "detail": f"พร้อมใช้งาน ({backend})" if ready else "ไม่พบไลบรารี Whisper",
    }


def _probe_gemini_keys() -> Dict[str, Any]:
    keys = config.get_gemini_api_keys()
    count = len(keys)
    return {
        "count": count,
        "ready": count > 0,
        "detail": f"ตั้งค่าคีย์แล้ว {count} คีย์" if count > 0 else "ยังไม่ได้ตั้งค่า GEMINI_API_KEY",
    }


# ── Routes ──────────────────────────────────────────────────────────────


@router.get("/preflight")
def get_couple_preflight() -> Dict[str, Any]:
    """Returns GPU/NVENC availability, Node/HyperFrames readiness, Whisper
    readiness, and configured Gemini API key count (never exposing raw keys).
    """
    gpu = _probe_gpu_nvenc()
    node_hf = _probe_node_hyperframes()
    whisper = _probe_whisper()
    gemini = _probe_gemini_keys()

    overall_ready = bool(node_hf["ready"] and gemini["ready"])
    return {
        "ready": overall_ready,
        "gpu": gpu,
        "nvenc_available": gpu["nvenc"],
        "node_ready": node_hf["node_available"],
        "hyperframes_ready": node_hf["hyperframes_available"],
        "whisper_ready": whisper["ready"],
        "gemini_key_count": gemini["count"],
        "checks": {
            "gpu_nvenc": gpu,
            "node_hyperframes": node_hf,
            "whisper": whisper,
            "gemini_api_keys": gemini,
        },
    }


@router.post("/jobs")
def create_couple_job(
    payload: CreateCoupleJobRequest,
    background_tasks: BackgroundTasks,
    idempotency_key_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> JSONResponse:
    effective_key = payload.idempotency_key if payload.idempotency_key is not None else idempotency_key_header
    try:
        job, created = store.create_job(
            product_code=payload.product_code,
            total_clips=payload.total_clips,
            idempotency_key=effective_key,
        )
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)

    if created and _executor_hook is not None:
        background_tasks.add_task(_executor_hook, job, store)

    status_code = 201 if created else 200
    return JSONResponse(status_code=status_code, content=job)


@router.get("/jobs")
def list_couple_jobs(
    product_code: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> Dict[str, Any]:
    try:
        jobs = store.list_jobs(product_code=product_code, status=status)
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
def get_couple_job(
    job_id: str,
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> Dict[str, Any]:
    try:
        return store.get_job(job_id)
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)


def _parse_last_event_id(header_val: Optional[str], query_val: Optional[str]) -> int:
    raw = header_val if header_val is not None and str(header_val).strip() != "" else query_val
    if raw is None:
        return 0
    try:
        return max(0, int(str(raw).strip()))
    except (ValueError, TypeError):
        return 0


def _format_sse_event(ev: Dict[str, Any]) -> str:
    seq = ev.get("seq", 0)
    ev_type = ev.get("type", "message")
    payload = json.dumps(ev, ensure_ascii=False)
    return f"id: {seq}\nevent: {ev_type}\ndata: {payload}\n\n"


@router.get("/jobs/{job_id}/events")
def stream_couple_job_events(
    job_id: str,
    request: Request,
    last_event_id: Optional[str] = Query(default=None),
    last_event_id_header: Optional[str] = Header(default=None, alias="Last-Event-ID"),
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> StreamingResponse:
    try:
        store.get_job(job_id)
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)

    after_seq = _parse_last_event_id(last_event_id_header, last_event_id)

    def _event_generator():
        yield "retry: 2000\n\n"
        events = store.get_events(job_id, after_seq=after_seq)
        for ev in events:
            yield _format_sse_event(ev)
        yield ": heartbeat\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/jobs/{job_id}/checkpoint")
def transition_couple_job_checkpoint(
    job_id: str,
    payload: CheckpointDecisionRequest,
    background_tasks: BackgroundTasks,
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> Dict[str, Any]:
    try:
        job = store.transition_checkpoint(
            job_id=job_id,
            decision=payload.decision,
            expected_revision=payload.expected_revision,
            note=payload.note,
        )
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)

    if payload.decision.strip().lower() == "approve" and _executor_hook is not None:
        background_tasks.add_task(_executor_hook, job, store)
    return job


@router.post("/jobs/{job_id}/pause")
def pause_couple_job(
    job_id: str,
    payload: Optional[PauseJobRequest] = None,
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> Dict[str, Any]:
    reason = payload.reason if payload is not None else "user"
    try:
        return store.pause_job(job_id, reason=reason)
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)


@router.post("/jobs/{job_id}/resume")
def resume_couple_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> Dict[str, Any]:
    try:
        job = store.resume_job(job_id)
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)

    if _executor_hook is not None:
        background_tasks.add_task(_executor_hook, job, store)
    return job


@router.post("/jobs/{job_id}/cancel")
def cancel_couple_job(
    job_id: str,
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> Dict[str, Any]:
    try:
        return store.cancel_job(job_id)
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)


@router.post("/jobs/{job_id}/clips/{clip_idx}/retry")
def retry_couple_job_clip(
    job_id: str,
    clip_idx: int,
    background_tasks: BackgroundTasks,
    store: CoupleJobStore = Depends(get_couple_job_store),
) -> Dict[str, Any]:
    try:
        job = store.retry_clip(job_id, clip_idx)
    except CoupleJobError as exc:
        _raise_http_for_job_error(exc)

    if _executor_hook is not None:
        background_tasks.add_task(_executor_hook, job, store)
    return job
