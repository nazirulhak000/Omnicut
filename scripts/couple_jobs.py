"""
Durable job store and state machine for Couple Paper Chat batch production.

Backed by SQLite WAL + JSON mirror (`_Docs/couple_jobs_store.json`) via
`scripts.db.DocumentTable("couple_jobs")`.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from scripts import config
from scripts.db import DocumentTable
from scripts.maintenance_lock import _pid_alive


JOB_STATUSES = (
    "queued",
    "running",
    "awaiting_approval",
    "paused_quota",
    "paused",
    "completed",
    "failed",
    "cancelled",
)

ACTIVE_JOB_STATUSES = frozenset({
    "queued",
    "running",
    "awaiting_approval",
    "paused_quota",
    "paused",
})

TERMINAL_JOB_STATUSES = frozenset({
    "completed",
    "failed",
    "cancelled",
})

JOB_STAGES = (
    "tts",
    "whisper",
    "compose",
    "checkpoint",
    "render",
    "finalize",
)

CLIP_STATUSES = (
    "pending",
    "running",
    "awaiting_review",
    "rendered",
    "failed",
)


class CoupleJobError(Exception):
    """Base error for CoupleJobStore operations."""

    status_code: int = 400
    code: str = "couple_job_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class JobNotFoundError(CoupleJobError):
    status_code = 404
    code = "job_not_found"


class JobConflictError(CoupleJobError):
    status_code = 409
    code = "job_conflict"


class RevisionConflictError(CoupleJobError):
    status_code = 409
    code = "revision_conflict"


class InvalidJobStateError(CoupleJobError):
    status_code = 409
    code = "invalid_job_state"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_product_code(product_code: str) -> str:
    cleaned = str(product_code or "").strip().upper()
    if not cleaned:
        raise CoupleJobError("ต้องระบุรหัสสินค้า (product_code)", status_code=422, code="invalid_product_code")
    return cleaned


def _build_initial_clips(product_code: str, total_clips: int) -> List[Dict[str, Any]]:
    prefix = product_code.lower()
    return [
        {
            "idx": idx,
            "clip_id": f"{prefix}_{idx:02d}",
            "status": "pending",
            "error": None,
        }
        for idx in range(1, total_clips + 1)
    ]


def _count_rendered_clips(clips: List[Dict[str, Any]]) -> int:
    return sum(1 for clip in clips if isinstance(clip, dict) and clip.get("status") == "rendered")


def _append_job_event(
    job: Dict[str, Any],
    event_type: str,
    data: Optional[Dict[str, Any]] = None,
    ts: Optional[str] = None,
) -> Dict[str, Any]:
    events = job.setdefault("events", [])
    next_seq = (events[-1]["seq"] + 1) if events else 1
    event = {
        "seq": next_seq,
        "type": str(event_type),
        "data": deepcopy(data) if isinstance(data, dict) else {},
        "ts": ts or _now_iso(),
    }
    events.append(event)
    return event


class CoupleJobStore:
    """Durable store and state machine for Couple Paper Chat batch jobs."""

    def __init__(self, storage_dir: Optional[Path | str] = None) -> None:
        self._explicit_storage = Path(storage_dir).resolve() if storage_dir is not None else None
        self.table = DocumentTable(
            "couple_jobs",
            self._resolve_db_path,
            self._resolve_json_path,
        )
        self._active_executors: set[str] = set()
        self._executor_lock = threading.Lock()

    def _resolve_storage_dir(self) -> Path:
        if self._explicit_storage is not None:
            if self._explicit_storage.suffix.lower() == ".json":
                return self._explicit_storage.parent
            return self._explicit_storage
        return (config.BASE_DIR / "_Docs").resolve()

    def _resolve_db_path(self) -> Path:
        return self._resolve_storage_dir() / "store.db"

    def _resolve_json_path(self) -> Path:
        if self._explicit_storage is not None and self._explicit_storage.suffix.lower() == ".json":
            return self._explicit_storage
        return self._resolve_storage_dir() / "couple_jobs_store.json"

    @property
    def storage_dir(self) -> Path:
        return self._resolve_storage_dir()

    @property
    def json_path(self) -> Path:
        return self._resolve_json_path()

    @property
    def db_path(self) -> Path:
        return self._resolve_db_path()

    # -- executor tracking for safe startup recovery ----------------------

    def register_active_executor(self, job_id: str) -> None:
        with self._executor_lock:
            self._active_executors.add(job_id)

    def unregister_active_executor(self, job_id: str) -> None:
        with self._executor_lock:
            self._active_executors.discard(job_id)

    def has_active_executor(self, job_id: str) -> bool:
        with self._executor_lock:
            return job_id in self._active_executors

    # -- queries ----------------------------------------------------------

    def list_jobs(
        self,
        *,
        product_code: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        norm_product = _normalize_product_code(product_code) if product_code else None
        rows = self.table.load()
        filtered = []
        for row in rows:
            if norm_product and row.get("product_code") != norm_product:
                continue
            if status and row.get("status") != status:
                continue
            filtered.append(deepcopy(row))
        filtered.sort(
            key=lambda r: (str(r.get("created_at") or ""), str(r.get("updated_at") or ""), int(r.get("revision") or 0)),
            reverse=True,
        )
        return filtered

    def get_job(self, job_id: str) -> Dict[str, Any]:
        for row in self.table.load():
            if row.get("job_id") == job_id or row.get("id") == job_id:
                return deepcopy(row)
        raise JobNotFoundError(f"ไม่พบงานผลิต {job_id}")

    def get_events(self, job_id: str, after_seq: int = 0) -> List[Dict[str, Any]]:
        job = self.get_job(job_id)
        min_seq = max(0, int(after_seq or 0))
        return [
            deepcopy(ev)
            for ev in job.get("events", [])
            if isinstance(ev, dict) and int(ev.get("seq", 0)) > min_seq
        ]

    # -- mutations --------------------------------------------------------

    def _mutate_job(
        self,
        job_id: str,
        fn: Callable[[Dict[str, Any]], None],
        *,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        with self.table.mutate() as rows:
            target = next(
                (r for r in rows if r.get("job_id") == job_id or r.get("id") == job_id),
                None,
            )
            if target is None:
                raise JobNotFoundError(f"ไม่พบงานผลิต {job_id}")
            if expected_revision is not None and int(target.get("revision", 1)) != int(expected_revision):
                raise RevisionConflictError(
                    f"ข้อมูลงานถูกอัปเดตไปแล้ว (คาดหวัง revision {expected_revision} แต่ปัจจุบันคือ {target.get('revision')})"
                )
            fn(target)
            target["completed_clips"] = _count_rendered_clips(target.get("clips", []))
            target["revision"] = int(target.get("revision", 1)) + 1
            target["updated_at"] = _now_iso()
            return deepcopy(target)

    def create_job(
        self,
        product_code: str,
        total_clips: int = 20,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        norm_code = _normalize_product_code(product_code)
        total = int(total_clips or 20)
        if total < 1 or total > 100:
            raise CoupleJobError("จำนวนคลิปต้องอยู่ระหว่าง 1 ถึง 100", status_code=422, code="invalid_total_clips")
        idem_key = str(idempotency_key).strip() if idempotency_key is not None and str(idempotency_key).strip() else None

        with self.table.mutate() as rows:
            if idem_key is not None:
                by_key = next((r for r in rows if r.get("idempotency_key") == idem_key), None)
                if by_key is not None:
                    if by_key.get("product_code") != norm_code:
                        raise JobConflictError(
                            f"idempotency_key '{idem_key}' ถูกใช้กับสินค้า {by_key.get('product_code')} แล้ว"
                        )
                    return deepcopy(by_key), False

            active_for_product = next(
                (
                    r
                    for r in rows
                    if r.get("product_code") == norm_code and r.get("status") in ACTIVE_JOB_STATUSES
                ),
                None,
            )
            if active_for_product is not None:
                existing_key = active_for_product.get("idempotency_key")
                if idem_key is not None and existing_key != idem_key:
                    raise JobConflictError(
                        f"มีงานที่กำลังดำเนินการสำหรับสินค้า {norm_code} อยู่แล้ว ({active_for_product.get('job_id')})"
                    )
                return deepcopy(active_for_product), False

            now = _now_iso()
            job_id = f"cjob_{uuid.uuid4().hex[:12]}"
            clips = _build_initial_clips(norm_code, total)
            first_clip_id = clips[0]["clip_id"] if clips else f"{norm_code.lower()}_01"
            job: Dict[str, Any] = {
                "id": job_id,
                "job_id": job_id,
                "product_code": norm_code,
                "idempotency_key": idem_key,
                "status": "queued",
                "revision": 1,
                "created_at": now,
                "updated_at": now,
                "total_clips": total,
                "completed_clips": 0,
                "current_stage": "tts",
                "checkpoint": {
                    "clip_id": first_clip_id,
                    "chat_snapshot_url": None,
                    "cta_snapshot_url": None,
                    "approved": None,
                    "note": "",
                },
                "clips": clips,
                "error": None,
                "pause_reason": None,
                "executor_pid": None,
                "events": [],
            }
            _append_job_event(
                job,
                "job_created",
                {
                    "job_id": job_id,
                    "product_code": norm_code,
                    "total_clips": total,
                    "status": "queued",
                    "stage": "tts",
                },
                ts=now,
            )
            rows.append(job)
            return deepcopy(job), True

    def start_job(
        self,
        job_id: str,
        *,
        stage: str = "tts",
        executor_pid: Optional[int] = None,
    ) -> Dict[str, Any]:
        if stage not in JOB_STAGES:
            raise CoupleJobError(f"ไม่รู้จัก stage '{stage}'", status_code=422, code="invalid_stage")

        def _apply(job: Dict[str, Any]) -> None:
            if job["status"] in TERMINAL_JOB_STATUSES:
                raise InvalidJobStateError(f"ไม่สามารถเริ่มงานที่อยู่ในสถานะ {job['status']} ได้")
            job["status"] = "running"
            job["current_stage"] = stage
            job["pause_reason"] = None
            job["error"] = None
            job["executor_pid"] = executor_pid if executor_pid is not None else os.getpid()
            _append_job_event(
                job,
                "job_started",
                {"stage": stage, "executor_pid": job["executor_pid"]},
            )

        return self._mutate_job(job_id, _apply)

    def update_stage(
        self,
        job_id: str,
        stage: str,
        *,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        if stage not in JOB_STAGES:
            raise CoupleJobError(f"ไม่รู้จัก stage '{stage}'", status_code=422, code="invalid_stage")
        if status is not None and status not in JOB_STATUSES:
            raise CoupleJobError(f"ไม่รู้จัก status '{status}'", status_code=422, code="invalid_status")

        def _apply(job: Dict[str, Any]) -> None:
            job["current_stage"] = stage
            if status is not None:
                job["status"] = status
            _append_job_event(
                job,
                "stage_changed",
                {"stage": stage, "status": job["status"]},
            )

        return self._mutate_job(job_id, _apply)

    def open_checkpoint(
        self,
        job_id: str,
        *,
        clip_id: Optional[str] = None,
        chat_snapshot_url: Optional[str] = None,
        cta_snapshot_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        def _apply(job: Dict[str, Any]) -> None:
            if job["status"] in TERMINAL_JOB_STATUSES:
                raise InvalidJobStateError(f"ไม่สามารถเปิดจุดตรวจในสถานะ {job['status']} ได้")
            clips = job.get("clips", [])
            first_clip_id = clip_id or (clips[0]["clip_id"] if clips else f"{job['product_code'].lower()}_01")
            if clips:
                clips[0]["status"] = "awaiting_review"
            job["status"] = "awaiting_approval"
            job["current_stage"] = "checkpoint"
            job["checkpoint"] = {
                "clip_id": first_clip_id,
                "chat_snapshot_url": chat_snapshot_url,
                "cta_snapshot_url": cta_snapshot_url,
                "approved": None,
                "note": "",
            }
            _append_job_event(
                job,
                "checkpoint_opened",
                {
                    "clip_id": first_clip_id,
                    "chat_snapshot_url": chat_snapshot_url,
                    "cta_snapshot_url": cta_snapshot_url,
                },
            )

        return self._mutate_job(job_id, _apply)

    def transition_checkpoint(
        self,
        job_id: str,
        decision: str,
        expected_revision: Optional[int] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        clean_decision = str(decision or "").strip().lower()
        if clean_decision not in ("approve", "reject"):
            raise CoupleJobError(
                "decision ต้องเป็น 'approve' หรือ 'reject'",
                status_code=422,
                code="invalid_checkpoint_decision",
            )
        clean_note = str(note or "").strip()

        def _apply(job: Dict[str, Any]) -> None:
            if job.get("status") != "awaiting_approval":
                raise InvalidJobStateError(
                    f"งานไม่ได้อยู่ในสถานะรออนุมัติจุดตรวจ (ปัจจุบัน: {job.get('status')})"
                )
            checkpoint = job.setdefault("checkpoint", {})
            clips = job.get("clips", [])
            if clean_decision == "approve":
                checkpoint["approved"] = True
                checkpoint["note"] = clean_note
                job["status"] = "running"
                job["current_stage"] = "render"
                job["pause_reason"] = None
                if clips and clips[0].get("status") == "awaiting_review":
                    clips[0]["status"] = "running"
                    clips[0]["error"] = None
                _append_job_event(
                    job,
                    "checkpoint_approved",
                    {"clip_id": checkpoint.get("clip_id"), "note": clean_note},
                )
            else:
                checkpoint["approved"] = False
                checkpoint["note"] = clean_note
                job["status"] = "paused"
                job["pause_reason"] = "checkpoint_rejected"
                if clips:
                    clips[0]["status"] = "pending"
                    clips[0]["error"] = clean_note or "ตีกลับแก้ไขจากจุดตรวจคลิปแรก"
                _append_job_event(
                    job,
                    "checkpoint_rejected",
                    {"clip_id": checkpoint.get("clip_id"), "note": clean_note},
                )

        return self._mutate_job(job_id, _apply, expected_revision=expected_revision)

    def pause_job(self, job_id: str, reason: str = "user") -> Dict[str, Any]:
        clean_reason = str(reason or "user").strip()

        def _apply(job: Dict[str, Any]) -> None:
            if job.get("status") in TERMINAL_JOB_STATUSES:
                raise InvalidJobStateError(f"ไม่สามารถหยุดชั่วคราวงานที่อยู่ในสถานะ {job.get('status')} ได้")
            is_quota = clean_reason in ("quota", "paused_quota", "tts_quota", "429")
            job["status"] = "paused_quota" if is_quota else "paused"
            job["pause_reason"] = clean_reason
            if is_quota and not job.get("error"):
                job["error"] = "โควตา TTS เต็มชั่วคราว (429)"
            _append_job_event(
                job,
                "job_paused_quota" if is_quota else "job_paused",
                {"reason": clean_reason, "status": job["status"]},
            )

        return self._mutate_job(job_id, _apply)

    def resume_job(self, job_id: str) -> Dict[str, Any]:
        def _apply(job: Dict[str, Any]) -> None:
            if job.get("status") in ("completed", "cancelled"):
                raise InvalidJobStateError(f"ไม่สามารถทำต่องานที่อยู่ในสถานะ {job.get('status')} ได้")
            prev_status = job.get("status")
            job["status"] = "running"
            job["pause_reason"] = None
            job["error"] = None
            if job.get("current_stage") == "checkpoint" and job.get("checkpoint", {}).get("approved") is False:
                job["current_stage"] = "compose"
            _append_job_event(
                job,
                "job_resumed",
                {"previous_status": prev_status, "stage": job.get("current_stage")},
            )

        return self._mutate_job(job_id, _apply)

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        def _apply(job: Dict[str, Any]) -> None:
            if job.get("status") == "completed":
                raise InvalidJobStateError("ไม่สามารถยกเลิกงานที่เสร็จสมบูรณ์แล้วได้")
            prev_status = job.get("status")
            job["status"] = "cancelled"
            job["executor_pid"] = None
            for clip in job.get("clips", []):
                if clip.get("status") in ("running", "awaiting_review"):
                    clip["status"] = "pending"
            _append_job_event(
                job,
                "job_cancelled",
                {"previous_status": prev_status},
            )

        self.unregister_active_executor(job_id)
        return self._mutate_job(job_id, _apply)

    def fail_job(self, job_id: str, error: str) -> Dict[str, Any]:
        def _apply(job: Dict[str, Any]) -> None:
            job["status"] = "failed"
            job["error"] = str(error or "เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ")
            job["executor_pid"] = None
            _append_job_event(
                job,
                "job_failed",
                {"error": job["error"], "stage": job.get("current_stage")},
            )

        self.unregister_active_executor(job_id)
        return self._mutate_job(job_id, _apply)

    def update_clip(
        self,
        job_id: str,
        clip_idx: int,
        status: str,
        *,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        if status not in CLIP_STATUSES:
            raise CoupleJobError(f"ไม่รู้จักสถานะคลิป '{status}'", status_code=422, code="invalid_clip_status")
        idx_int = int(clip_idx)

        def _apply(job: Dict[str, Any]) -> None:
            clips = job.get("clips", [])
            clip = next((c for c in clips if int(c.get("idx", 0)) == idx_int), None)
            if clip is None:
                raise CoupleJobError(
                    f"ไม่พบคลิปที่ {idx_int} ในงาน {job_id}",
                    status_code=404,
                    code="clip_not_found",
                )
            clip["status"] = status
            clip["error"] = error
            _append_job_event(
                job,
                "clip_updated",
                {"clip_idx": idx_int, "clip_id": clip.get("clip_id"), "status": status, "error": error},
            )
            rendered_count = _count_rendered_clips(clips)
            if rendered_count == int(job.get("total_clips", len(clips))) and len(clips) > 0:
                job["status"] = "completed"
                job["current_stage"] = "finalize"
                job["error"] = None
                job["executor_pid"] = None
                _append_job_event(
                    job,
                    "job_completed",
                    {"completed_clips": rendered_count, "total_clips": job.get("total_clips")},
                )

        return self._mutate_job(job_id, _apply)

    def retry_clip(self, job_id: str, clip_idx: int) -> Dict[str, Any]:
        idx_int = int(clip_idx)

        def _apply(job: Dict[str, Any]) -> None:
            if job.get("status") == "cancelled":
                raise InvalidJobStateError("ไม่สามารถลองใหม่ในงานที่ถูกยกเลิกแล้วได้")
            clips = job.get("clips", [])
            clip = next((c for c in clips if int(c.get("idx", 0)) == idx_int), None)
            if clip is None:
                raise CoupleJobError(
                    f"ไม่พบคลิปที่ {idx_int} ในงาน {job_id}",
                    status_code=404,
                    code="clip_not_found",
                )
            previous_clip_status = clip.get("status")
            clip["status"] = "pending"
            clip["error"] = None
            if job.get("status") in ("failed", "paused", "paused_quota", "completed"):
                job["status"] = "running"
                job["pause_reason"] = None
                job["error"] = None
            _append_job_event(
                job,
                "clip_retried",
                {
                    "clip_idx": idx_int,
                    "clip_id": clip.get("clip_id"),
                    "previous_status": previous_clip_status,
                },
            )

        return self._mutate_job(job_id, _apply)

    def append_event(
        self,
        job_id: str,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        def _apply(job: Dict[str, Any]) -> None:
            _append_job_event(job, event_type, data or {})

        return self._mutate_job(job_id, _apply)

    def recover_interrupted_jobs(self) -> List[Dict[str, Any]]:
        """On server boot, transitions any job stuck in `running` from a dead
        or inactive executor back to `queued` while preserving clips that
        already have `status == "rendered"`.
        """
        recovered: List[Dict[str, Any]] = []
        with self.table.mutate() as rows:
            now = _now_iso()
            for job in rows:
                if job.get("status") != "running":
                    continue
                job_id = str(job.get("job_id") or job.get("id") or "")
                pid = job.get("executor_pid")
                if self.has_active_executor(job_id) and isinstance(pid, int) and pid > 0 and _pid_alive(pid):
                    continue

                clips = job.get("clips", [])
                for clip in clips:
                    if clip.get("status") == "running":
                        clip["status"] = "pending"

                rendered_count = _count_rendered_clips(clips)
                job["completed_clips"] = rendered_count
                job["status"] = "queued"
                job["executor_pid"] = None
                job["revision"] = int(job.get("revision", 1)) + 1
                job["updated_at"] = now
                _append_job_event(
                    job,
                    "job_recovered",
                    {
                        "status": "queued",
                        "completed_clips": rendered_count,
                        "total_clips": job.get("total_clips", len(clips)),
                    },
                    ts=now,
                )
                recovered.append(deepcopy(job))
        return recovered
