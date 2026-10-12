"""Processing and read API for video cutouts and legacy frame sequences.

The task worker publishes a validated transparent video before this router
serves its manifest and media. Published PNG sequences remain readable for
existing projects. Application middleware retains the authentication boundary.
"""

from __future__ import annotations

import re
import hashlib
import importlib.util
import json
import math
import os
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from scripts.background_isolation_sequence_artifacts import (
    SequenceArtifactStoreError,
    read_sequence_manifest,
    sequence_frame_path,
    sequence_paths,
    sequence_status,
)
from scripts import config
from scripts.config import PROJECTS_DIR
from scripts.channel_scope import ChannelScope, get_optional_channel_scope, get_channel_scope, require_active_for_new_work
from scripts.channel_store import ChannelError
from scripts.channel_workflows import get_workflow_scope, require_media_owner, require_project_owner, capture_job_scope
from scripts.channel_artifacts import register as register_artifact
from scripts.storage_cleaner import is_strictly_protected_path
from scripts.task_manager import TaskManager
from scripts.background_isolation import normalize_background_isolation
from scripts.cutout_runtime import probe_sam2_runtime, resolve_checkpoint, sam2_input_memory_bytes
from scripts.background_isolation_sequence_artifacts import build_sequence_artifact_id
from scripts.background_isolation_sequence_worker import DERIVED_CACHE_NAMESPACE
from scripts.background_isolation_video_worker import (
    VIDEO_NAMESPACE, VIDEO_NAME, VIDEO_SCHEMA_VERSION,
    process_background_isolation_video, video_artifact_id,
)


router = APIRouter(prefix="/api/background-isolation", tags=["background-isolation"])

_FRAME_INDEX_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")
_FRAME_NAME_RE = re.compile(r"^frame_([0-9]{6})\.png$")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_BACKGROUND_SOURCE_EXTENSIONS = frozenset({
    ".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm",
})
_BACKGROUND_SOURCE_ROOT_NAMES = ("", "00_Inbox", "01_Raw", "02_Assets", "03_Projects", "04_Exports", "05_Covers_Thumbnails", "06_Archive")


class BackgroundIsolationProcessRequest(BaseModel):
    """Request to build a ready transparent video in the project cache."""

    source_path: str
    config: dict[str, Any] = Field(default_factory=dict)
    start: float = Field(default=0.0, ge=0.0)
    duration: float | None = Field(default=None, gt=0.0)
    active_intervals: list[tuple[float, float]] | None = None
    fps: float = Field(default=30.0, gt=0.0, le=120.0)
    timebase: str | None = None
    width: int = Field(default=1080, gt=0, le=4096)
    height: int = Field(default=1920, gt=0, le=4096)
    rotation: int = Field(default=0)
    project_name: str | None = None


def _validate_active_intervals(req: BackgroundIsolationProcessRequest) -> None:
    if req.active_intervals is None:
        return
    if not req.active_intervals or req.duration is None:
        raise HTTPException(status_code=422, detail="scoped Cutout needs intervals and duration")
    previous = req.start
    for begin, end in req.active_intervals:
        if not (req.start <= begin < end <= req.start + req.duration + 1e-6) or begin < previous - 1e-6:
            raise HTTPException(status_code=422, detail="invalid Cutout interval")
        previous = end


_BACKGROUND_TASK_LOCK = threading.Lock()
_BACKGROUND_TASKS_RUNNING: set[str] = set()
_BACKGROUND_TASK_CANCEL_EVENTS: dict[str, threading.Event] = {}


def _background_isolation_preflight(
    req: BackgroundIsolationProcessRequest,
    source: Path,
) -> dict[str, Any]:
    """Return actionable runtime/capacity checks without starting a worker."""

    effective_duration = req.duration
    if effective_duration is None and req.config.get("engine") == "sam2":
        from scripts.silence_detect import _probe_duration
        source_duration = _probe_duration(source)
        if math.isfinite(source_duration) and source_duration > req.start:
            effective_duration = source_duration - req.start
    frame_count = math.ceil((effective_duration or 0) * req.fps - 1e-9) if effective_duration else None
    isolated_frame_count = (sum(math.ceil((end - begin) * req.fps - 1e-9)
                                for begin, end in req.active_intervals)
                            if req.active_intervals is not None else frame_count)
    estimated_cache_bytes = (
        ((isolated_frame_count or 0) * req.width * req.height // 4
         + (frame_count - (isolated_frame_count or 0)) * req.width * req.height // 128)
        if frame_count is not None else None
    )
    disk_target = Path(PROJECTS_DIR).resolve(strict=False)
    while not disk_target.exists() and disk_target != disk_target.parent:
        disk_target = disk_target.parent
    free_disk_bytes = shutil.disk_usage(disk_target).free
    required_disk_bytes = max(128 * 1024 * 1024, int((estimated_cache_bytes or 0) * 2))
    available_memory_bytes = None
    if importlib.util.find_spec("psutil") is not None:
        try:
            psutil = importlib.import_module("psutil")
            available_memory_bytes = int(psutil.virtual_memory().available)
        except Exception:
            available_memory_bytes = None

    engine = req.config.get("engine", "rembg")
    issues: list[dict[str, str]] = []

    if engine == "sam2":
        model_name = req.config.get("model", "sam2.1_hiera_tiny")
        try:
            resolve_checkpoint(model_name, cache_root=Path(PROJECTS_DIR) / ".cache")
            model_cached = True
        except (FileNotFoundError, ValueError):
            model_cached = False
        modules = probe_sam2_runtime()
        if not modules["sam2_runtime"]:
            issues.append({
                "severity": "error",
                "code": "sam2_runtime_missing",
                "message": "ไม่พบ GPU Cutout Runtime ตั้งค่า OMNICUT_SAM2_PYTHON หรือ tools/cutout_runtime/.venv",
            })
        elif not modules.get("cuda"):
            issues.append({
                "severity": "error",
                "code": "sam2_cuda_unavailable",
                "message": "SAM2 ต้องใช้ runtime ที่มี CUDA และ NVIDIA GPU: " + str(modules.get("error") or "CUDA unavailable"),
            })
        if not model_cached:
            issues.append({
                "severity": "error",
                "code": "model_not_cached",
                "message": f"ไม่พบโมเดล {model_name}.pt ตั้งค่า OMNICUT_SAM2_CHECKPOINT_DIR ให้ตรงกับโมเดลที่เลือก",
            })
        # SAM2's eager input tensor uses 1024² RGB float32 on host RAM.
        # Tracking still covers the full window, including sparse intervals.
        required_memory_bytes = sam2_input_memory_bytes(frame_count or 0)
    else:
        model_name = req.config.get("model", "u2net")
        modules = {
            name: importlib.util.find_spec(name) is not None
            for name in ("rembg", "onnxruntime", "PIL")
        }
        model_home = Path(os.environ.get("U2NET_HOME") or (Path.home() / ".u2net"))
        model_path = model_home / f"{model_name}.onnx"
        model_cached = model_path.is_file()
        for module, available in modules.items():
            if not available:
                issues.append({
                    "severity": "error",
                    "code": f"{module.lower()}_missing",
                    "message": f"ไม่พบ runtime {module} ใน environment ของ backend",
                })
        if not model_cached:
            issues.append({
                "severity": "warning",
                "code": "model_not_cached",
                "message": f"ยังไม่พบโมเดล {model_path.name} ในเครื่อง งานแรกอาจต้องดาวน์โหลดโมเดล",
            })
        required_memory_bytes = (
            384 * 1024 * 1024 if req.config.get("model") == "u2netp" else 768 * 1024 * 1024
        )

    if effective_duration is None:
        issues.append({
            "severity": "error" if engine == "sam2" else "warning",
            "code": "duration_unknown",
            "message": "อ่านความยาว source ไม่สำเร็จ กรุณาระบุ duration ก่อนเริ่ม SAM2 เพื่อประเมิน RAM และพื้นที่"
                if engine == "sam2" else "ไม่ทราบความยาวช่วงวิดีโอ จึงยังประเมินจำนวนเฟรมและพื้นที่ไม่ได้",
        })
    elif free_disk_bytes < required_disk_bytes:
        issues.append({
            "severity": "error",
            "code": "disk_space_low",
            "message": "พื้นที่ cache ไม่พอสำหรับวิดีโอ Cutout ช่วงนี้",
        })
    if available_memory_bytes is not None and available_memory_bytes < required_memory_bytes:
        issues.append({
            "severity": "error",
            "code": "memory_low",
            "message": ("RAM ว่างไม่พอสำหรับช่วง SAM2 ที่เลือก กรุณาตัดช่วง source ให้สั้นลงหรือปิดโปรแกรมอื่น"
                        if engine == "sam2" else
                        "RAM ว่างไม่พอสำหรับโมเดล Cutout ที่เลือก กรุณาปิดโปรแกรมอื่นหรือใช้โมเดล u2netp"),
        })

    return {
        "ok": not any(issue["severity"] == "error" for issue in issues),
        "source_path": str(source),
        "start": req.start,
        "duration": effective_duration,
        "duration_inferred": req.duration is None and effective_duration is not None,
        "fps": req.fps,
        "frame_count": frame_count,
        "isolated_frame_count": isolated_frame_count,
        "estimated_cache_bytes": estimated_cache_bytes,
        "free_disk_bytes": free_disk_bytes,
        "required_disk_bytes": required_disk_bytes,
        "available_memory_bytes": available_memory_bytes,
        "required_memory_bytes": required_memory_bytes,
        "model": model_name,
        "model_cached": model_cached,
        "runtime": modules,
        "issues": issues,
    }


def request_background_isolation_cancel(task_id: str) -> bool:
    """Signal a running isolation worker to stop at its next safe checkpoint."""

    with _BACKGROUND_TASK_LOCK:
        event = _BACKGROUND_TASK_CANCEL_EVENTS.get(task_id)
        if event is None:
            return False
        event.set()
        return True


def _source_for_processing(value: str) -> Path:
    raw_candidate = Path(value).expanduser()
    workspace_root = Path(PROJECTS_DIR).resolve(strict=False).parent
    candidate = raw_candidate if raw_candidate.is_absolute() else workspace_root / raw_candidate
    if raw_candidate.is_symlink():
        raise HTTPException(status_code=404, detail="background isolation source video not found")
    candidate = candidate.resolve(strict=False)
    if candidate.suffix.casefold() not in _BACKGROUND_SOURCE_EXTENSIONS or not candidate.is_file():
        raise HTTPException(status_code=404, detail="background isolation source video not found")
    allowed = _contained(candidate, (config.SOURCE_ROOT / "02_Assets").resolve())
    for root_name in _BACKGROUND_SOURCE_ROOT_NAMES:
        root = workspace_root / root_name if root_name else workspace_root
        if root.is_symlink():
            continue
        root = root.resolve(strict=False)
        if _contained(candidate, root):
            allowed = True
            break
    if not allowed:
        raise HTTPException(status_code=404, detail="background isolation source video not found")
    return candidate


def _source_fingerprint(source: Path) -> str:
    stat = source.stat()
    payload = f"{source.as_posix()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _request_identity(source: Path, normalized: dict[str, Any], req: BackgroundIsolationProcessRequest) -> str:
    """Stable identity for coalescing equivalent queued cutout requests."""
    payload = {
        "source": str(source), "config": normalized, "fps": req.fps,
        "timebase": req.timebase, "width": req.width, "height": req.height,
        "rotation": req.rotation, "project_name": req.project_name,
        "start": req.start, "duration": req.duration,
        "active_intervals": req.active_intervals,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _source_sequence_id(
    source_fingerprint: str,
    normalized: dict[str, Any],
    *,
    start: float = 0.0,
    duration: float | None = None,
    fps: float,
    timebase: str,
    width: int,
    height: int,
    rotation: int,
) -> str:
    """Build one cache identity for one source/settings/window tuple."""

    return build_sequence_artifact_id(
        source_fingerprint,
        algorithm="background-isolation-source-v1",
        engine=normalized["engine"],
        model=normalized["model"],
        quality=normalized["quality"],
        worker_version="source-sequence-v2",
        fps=fps,
        timebase=timebase,
        width=width,
        height=height,
        rotation=rotation,
        source_start=start,
        source_duration=duration,
    )


def _pinned_scope(channel_id, job_scope):
    if channel_id is None:
        return None
    pinned = job_scope or {}
    return ChannelScope(channel_id, pinned.get("channel_scope_source", "job"), bool(pinned.get("channel_scope_strict", False)), channel=pinned.get("channel_identity_snapshot"))


def _guard_source(scope, path):
    if isinstance(scope, ChannelScope):
        require_media_owner(scope, path, base_dir=Path(PROJECTS_DIR).parent)


def _guard_artifact(request, path):
    if request is not None:
        scope = get_optional_channel_scope(request) or get_channel_scope(request)
        _guard_source(scope, path)


def _run_background_isolation_task(
    task_id: str,
    req: BackgroundIsolationProcessRequest,
    cancel_event: threading.Event | None = None,
    channel_id=None,
    job_scope=None,
) -> None:
    if cancel_event is None:
        with _BACKGROUND_TASK_LOCK:
            cancel_event = _BACKGROUND_TASK_CANCEL_EVENTS.get(task_id)
    scope = _pinned_scope(channel_id, job_scope)
    kwargs = {"channel_id": channel_id} if channel_id is not None else {}
    try:
        source = _source_for_processing(req.source_path)
        _guard_source(scope, source)
        if req.project_name and scope is not None:
            require_project_owner(scope, req.project_name)
        normalized = normalize_background_isolation(req.config)
        if not normalized["enabled"]:
            raise ValueError(f"background isolation config is disabled or invalid: {normalized.get('reason', 'invalid_config')}")
        if req.project_name:
            project_file = Path(PROJECTS_DIR).resolve() / req.project_name / "project.json"
            if project_file.is_file():
                try:
                    pdata = json.loads(project_file.read_text(encoding="utf-8"))
                    params = pdata.get("render_params") or {}
                    clips = (pdata.get("clip_list") or params.get("clip_list") or pdata.get("clips") or [])
                    if normalized.get("subject_points") and "prompt_reference_source" not in normalized:
                        # Old projects have no picker reference metadata. Keep
                        # points on the first timeline source/window; basenames
                        # and per-source inference conflate different takes.
                        first = next((c for c in clips if isinstance(c, dict) and c.get("source_path")), None)
                        if first:
                            normalized["prompt_reference_source"] = first["source_path"]
                            normalized.setdefault("prompt_reference_start", first.get("trim_start") or 0.0)
                except Exception:
                    pass
        normalized = normalize_background_isolation(normalized)
        if not normalized["enabled"]:
            raise ValueError("invalid Cutout prompt reference")
        source_fingerprint = _source_fingerprint(source)
        if channel_id is not None:
            source_fingerprint = hashlib.sha256((channel_id + "|" + source_fingerprint).encode()).hexdigest()
        if req.timebase:
            timebase = req.timebase
        elif float(req.fps).is_integer():
            timebase = f"1/{int(req.fps)}"
        else:
            timebase = "1001/30000"
        cache_root = Path(PROJECTS_DIR).resolve() / ".cache"

        def progress(event: dict[str, Any]) -> None:
            stage = event.get("stage", "processing")
            value = event.get("progress")
            if isinstance(value, (int, float)):
                TaskManager.update_progress(task_id, min(0.99, 0.45 * float(value) if stage == "processing" else 0.45 + 0.55 * float(value)), f"Background isolation: {stage}", **kwargs)

        TaskManager.update_progress(task_id, 0.05, "กำลังตัดพื้นหลังวิดีโอ", **kwargs)
        if channel_id is not None:
            expected_id = video_artifact_id(source_fingerprint, normalized, start=req.start, duration=req.duration, fps=req.fps, timebase=timebase, width=req.width, height=req.height, rotation=req.rotation, active_intervals=req.active_intervals)
            expected_directory = cache_root / VIDEO_NAMESPACE / expected_id
            for name in ["manifest.json", VIDEO_NAME, "preview.webm"]:
                register_artifact(expected_directory / name, channel_id)
        result = process_background_isolation_video(
            source, cache_root, normalized,
            source_fingerprint=source_fingerprint, start=req.start,
            duration=req.duration, fps=req.fps, timebase=timebase,
            width=req.width, height=req.height, rotation=req.rotation,
            cancel_event=cancel_event, progress_callback=progress,
            active_intervals=req.active_intervals,
        )
        if result.get("status") != "ready" or not result.get("artifact_id"):
            raise RuntimeError(result.get("message") or "background isolation failed")
        output_manifest = Path(result["output_directory"]) / "manifest.json"
        sequence = json.loads(output_manifest.read_text(encoding="utf-8"))
        if channel_id is not None:
            sequence["channel_id"] = channel_id
            output_manifest.write_text(json.dumps(sequence, ensure_ascii=False), encoding="utf-8")
            for artifact in output_manifest.parent.rglob("*"):
                if artifact.is_file():
                    register_artifact(artifact, channel_id)
        completed = {
            **normalized,
            "artifact": {
                "schema_version": 1, "id": result["artifact_id"], "status": "ready",
                "source_fingerprint": sequence["source_fingerprint"],
                "source_start": sequence["source_start"],
                "source_duration": sequence["source_duration"],
            },
            "sequence": sequence,
        }
        if cancel_event is not None and cancel_event.is_set():
            TaskManager.cancel_task(task_id, **kwargs)
            return
        TaskManager.complete_task(task_id, completed, step_label="ตัดพื้นหลังสินค้าเสร็จแล้ว", **kwargs)
    except Exception as exc:
        if cancel_event is not None and cancel_event.is_set():
            TaskManager.cancel_task(task_id, **kwargs)
        else:
            TaskManager.fail_task(task_id, str(exc), step_label="ตัดพื้นหลังสินค้าไม่สำเร็จ", **kwargs)


def _schedule_background_isolation_task(task_id: str, req: BackgroundIsolationProcessRequest, channel_id=None, job_scope=None) -> bool:
    """Start one task at most once per server process.

    The task registry is durable, while this set protects the in-process
    recovery path from scheduling the same task twice during a reload or a
    fast reconnect. The worker itself remains retry-safe because its frame
    checkpoint is deterministic.
    """

    with _BACKGROUND_TASK_LOCK:
        if task_id in _BACKGROUND_TASKS_RUNNING:
            return False
        task = TaskManager.get_task(task_id, **({"channel_id": channel_id} if channel_id is not None else {}))
        if not task or task.get("status") in {"completed", "failed", "cancelled"}:
            return False
        cancel_event = threading.Event()
        _BACKGROUND_TASK_CANCEL_EVENTS[task_id] = cancel_event
        _BACKGROUND_TASKS_RUNNING.add(task_id)

    def run_and_release() -> None:
        try:
            _run_background_isolation_task(task_id, req, **({"channel_id": channel_id, "job_scope": job_scope} if channel_id is not None else {}))
        finally:
            with _BACKGROUND_TASK_LOCK:
                _BACKGROUND_TASKS_RUNNING.discard(task_id)
                _BACKGROUND_TASK_CANCEL_EVENTS.pop(task_id, None)

    TaskManager.run_in_background(run_and_release)
    return True


def recover_background_isolation_tasks() -> int:
    """Resume queued/processing background-isolation tasks after startup."""

    resumed = 0
    for task in TaskManager.get_active_tasks(limit=1000):
        if task.get("type") != "background_isolation":
            continue
        if task.get("status") not in {"queued", "processing"}:
            continue
        payload = task.get("payload") or {}
        try:
            req = BackgroundIsolationProcessRequest(**payload)
        except Exception as exc:
            TaskManager.fail_task(task.get("id", ""), f"invalid recovery payload: {exc}", step_label="กู้คืนงานตัดพื้นหลังไม่สำเร็จ")
            continue
        if _schedule_background_isolation_task(task["id"], req, task.get("channel_id"), {key: value for key, value in task.items() if key.startswith("channel_")}):
            resumed += 1
    return resumed


@router.post("/preflight")
def preflight_background_isolation(req: BackgroundIsolationProcessRequest, request: Request = None) -> dict[str, Any]:
    """Validate local runtime/model/capacity before queueing expensive work."""

    source = _source_for_processing(req.source_path)
    if request is not None:
        optional = get_optional_channel_scope(request)
        if optional is not None:
            _guard_source(optional, source)
        elif not any(_contained(source, root.resolve()) for root in [Path(PROJECTS_DIR).parent / name for name in ["00_Inbox", "01_Raw", "02_Assets"]] + [config.SOURCE_ROOT / "02_Assets"]):
            _guard_source(get_channel_scope(request), source)
    _validate_active_intervals(req)
    if req.rotation not in (0, 90, 180, 270):
        raise HTTPException(status_code=422, detail="rotation must be 0, 90, 180, or 270")
    normalized = normalize_background_isolation(req.config)
    if not normalized["enabled"]:
        raise HTTPException(
            status_code=422,
            detail=f"background isolation config is disabled or invalid: {normalized.get('reason', 'invalid_config')}",
        )
    canonical = req.model_copy(update={"config": normalized})
    return _background_isolation_preflight(canonical, source)


@router.post("/process")
def process_background_isolation(req: BackgroundIsolationProcessRequest, background_tasks: BackgroundTasks, scope: ChannelScope = Depends(get_workflow_scope)):
    """Queue extraction + rembg segmentation and return a pollable task id."""

    if isinstance(scope, ChannelScope):
        require_active_for_new_work(scope)
    source = _source_for_processing(req.source_path)
    _validate_active_intervals(req)
    if req.rotation not in (0, 90, 180, 270):
        raise HTTPException(status_code=422, detail="rotation must be 0, 90, 180, or 270")
    normalized = normalize_background_isolation(req.config)
    if not normalized["enabled"]:
        raise HTTPException(status_code=422, detail=f"background isolation config is disabled or invalid: {normalized.get('reason', 'invalid_config')}")
    if isinstance(scope, ChannelScope):
        _guard_source(scope, source)
        if req.project_name:
            require_project_owner(scope, req.project_name)
    channel_id = scope.channel_id if isinstance(scope, ChannelScope) else None
    job_scope = capture_job_scope(scope) if isinstance(scope, ChannelScope) else None
    identity = _request_identity(source, normalized, req)
    if channel_id is not None:
        identity = hashlib.sha256((channel_id + "|" + identity).encode()).hexdigest()
    with _BACKGROUND_TASK_LOCK:
        for active in TaskManager.get_active_tasks(limit=1000, **({"channel_id": channel_id} if channel_id is not None else {})):
            payload = active.get("payload") or {}
            if (active.get("type") == "background_isolation"
                    and active.get("status") in {"queued", "processing"}
                    and payload.get("request_identity") == identity):
                return {"task_id": active["id"], "status": active["status"], "config": normalized}
        task_id = str(uuid.uuid4())
        payload = req.model_dump()
        payload["request_identity"] = identity
        TaskManager.create_task(
            "background_isolation", "กำลังตัดพื้นหลังสินค้า", payload=payload,
            target_tab="editor", task_id=task_id, channel_id=channel_id, job_scope=job_scope,
        )
    background_tasks.add_task(_schedule_background_isolation_task, task_id, req, channel_id, job_scope)
    return {"task_id": task_id, "status": "queued", "config": normalized}


def _contained(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _canonical_cache_root() -> Path:
    """Return PROJECTS_DIR/.cache only when it remains inside PROJECTS_DIR."""

    project_root = Path(PROJECTS_DIR).resolve(strict=False)
    cache_candidate = project_root / ".cache"
    # A symlinked cache root is not an acceptable derived root.  Resolving it
    # and checking containment also catches a junction/reparse-point escape.
    if cache_candidate.is_symlink():
        raise HTTPException(status_code=500, detail="derived cache configuration is unsafe")
    cache_root = cache_candidate.resolve(strict=False)
    if not _contained(cache_root, project_root):
        raise HTTPException(status_code=500, detail="derived cache configuration is unsafe")
    return cache_root


def _invalid_artifact_id() -> HTTPException:
    return HTTPException(status_code=400, detail="invalid background isolation artifact id")


def _validated_artifact_id(artifact_id: str) -> str:
    """Validate the opaque ID through the canonical path guard."""

    try:
        # sequence_paths validates the exact bgseq1 format and rejects cache
        # namespace, artifact directory, and frames-directory symlinks.
        sequence_paths(_canonical_cache_root(), artifact_id, namespace=DERIVED_CACHE_NAMESPACE)
    except HTTPException:
        raise
    except (SequenceArtifactStoreError, TypeError, ValueError) as exc:
        raise _invalid_artifact_id() from exc
    return artifact_id


def _ready_sequence(artifact_id: str) -> tuple[Path, dict[str, Any]]:
    """Resolve a ready sequence without disclosing unsafe cache details."""

    safe_id = _validated_artifact_id(artifact_id)
    cache_root = _canonical_cache_root()
    try:
        status = sequence_status(cache_root, safe_id, namespace=DERIVED_CACHE_NAMESPACE)
    except (SequenceArtifactStoreError, OSError, ValueError) as exc:
        # Missing, malformed, incomplete, and symlinked artifacts are all
        # intentionally indistinguishable to a reader.
        raise HTTPException(status_code=404, detail="background isolation sequence not found") from exc
    if status != "ready":
        raise HTTPException(status_code=404, detail="background isolation sequence not found")

    manifest = read_sequence_manifest(cache_root, safe_id, namespace=DERIVED_CACHE_NAMESPACE)
    if manifest is None or manifest.get("status") != "ready":
        raise HTTPException(status_code=404, detail="background isolation sequence not found")
    try:
        paths = sequence_paths(cache_root, safe_id, namespace=DERIVED_CACHE_NAMESPACE)
    except (SequenceArtifactStoreError, OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="background isolation sequence not found") from exc
    return paths.directory, manifest


def _parse_frame_index(raw_frame_index: str) -> int:
    if not isinstance(raw_frame_index, str):
        raise HTTPException(status_code=400, detail="frame_index must be a zero-based integer")
    if _FRAME_INDEX_RE.fullmatch(raw_frame_index):
        candidate = raw_frame_index
    else:
        frame_name = _FRAME_NAME_RE.fullmatch(raw_frame_index)
        if not frame_name:
            raise HTTPException(status_code=400, detail="frame_index must be a zero-based integer")
        candidate = frame_name.group(1)
    try:
        frame_index = int(candidate, 10)
    except (TypeError, ValueError, OverflowError) as exc:
        raise HTTPException(status_code=400, detail="frame_index must be a zero-based integer") from exc
    if frame_index > 999999:
        raise HTTPException(status_code=400, detail="frame_index is out of range")
    return frame_index


def _validated_png_frame(artifact_id: str, frame_index: int, frame_count: int) -> Path:
    if frame_index >= frame_count:
        raise HTTPException(status_code=404, detail="background isolation frame not found")
    cache_root = _canonical_cache_root()
    try:
        frame_path = sequence_frame_path(
            cache_root,
            artifact_id,
            frame_index,
            namespace=DERIVED_CACHE_NAMESPACE,
        )
    except (SequenceArtifactStoreError, OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="background isolation frame not found") from exc

    if (
        frame_path.suffix.casefold() != ".png"
        or frame_path.is_symlink()
        or not frame_path.is_file()
        or not _contained(frame_path.resolve(strict=False), cache_root)
    ):
        raise HTTPException(status_code=404, detail="background isolation frame not found")
    try:
        with frame_path.open("rb") as handle:
            if handle.read(len(_PNG_SIGNATURE)) != _PNG_SIGNATURE:
                raise HTTPException(status_code=404, detail="background isolation frame not found")
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(status_code=404, detail="background isolation frame not found") from exc
    return frame_path


@router.get("/sequences/{artifact_id}/manifest")
def get_background_isolation_manifest(artifact_id: str, request: Request = None) -> dict[str, Any]:
    """Return a published video or legacy sequence manifest by artifact ID."""
    video = _ready_video(artifact_id)
    if video is not None:
        _guard_artifact(request, video[0])
        manifest = dict(video[1])
        proxy_path = video[0].with_name("preview.webm")
        preview = manifest.get("preview") or {}
        if (proxy_path.is_symlink() or not proxy_path.is_file()
                or proxy_path.stat().st_size != preview.get("size_bytes")):
            manifest.pop("preview", None)
        return manifest
    _sequence_dir, manifest = _ready_sequence(artifact_id)
    _guard_artifact(request, _sequence_dir / "manifest.json")
    return manifest


def _ready_video(artifact_id: str) -> tuple[Path, dict[str, Any]] | None:
    if not isinstance(artifact_id, str) or not re.fullmatch(r"bgseq1-[0-9a-f]{16}", artifact_id):
        raise _invalid_artifact_id()
    root = _canonical_cache_root()
    namespace = root / VIDEO_NAMESPACE
    directory = namespace / artifact_id
    video = directory / VIDEO_NAME
    manifest_path = directory / "manifest.json"
    if any(path.is_symlink() for path in (namespace, directory, video, manifest_path)):
        raise HTTPException(status_code=404, detail="background isolation video not found")
    if not manifest_path.is_file() or not video.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="background isolation video not found")
    if (manifest.get("schema_version") != VIDEO_SCHEMA_VERSION
            or manifest.get("artifact_id") != artifact_id
            or manifest.get("status") != "ready"
            or manifest.get("video_file") != VIDEO_NAME):
        raise HTTPException(status_code=404, detail="background isolation video not found")
    return video, manifest


@router.get("/videos/{artifact_id}/cutout.webm")
def get_background_isolation_video(artifact_id: str, request: Request = None) -> FileResponse:
    ready = _ready_video(artifact_id)
    if ready is None:
        raise HTTPException(status_code=404, detail="background isolation video not found")
    _guard_artifact(request, ready[0])
    return FileResponse(ready[0], media_type="video/webm", headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.get("/videos/{artifact_id}/preview.webm")
def get_background_isolation_video_preview(artifact_id: str, request: Request = None) -> FileResponse:
    ready = _ready_video(artifact_id)
    if ready is None:
        raise HTTPException(status_code=404, detail="background isolation preview not found")
    preview = ready[1].get("preview") or {}
    path = ready[0].with_name("preview.webm")
    if (preview.get("video_file") != "preview.webm" or preview.get("derived_from") != VIDEO_NAME
            or preview.get("master_sha256") != ready[1].get("sha256")
            or path.is_symlink() or not path.is_file()
            or path.stat().st_size != preview.get("size_bytes")):
        raise HTTPException(status_code=404, detail="background isolation preview not found")
    _guard_artifact(request, path)
    return FileResponse(path, media_type="video/webm", headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.get("/sequences/{artifact_id}/frames/{frame_index}")
def get_background_isolation_frame(artifact_id: str, frame_index: str, request: Request = None) -> FileResponse:
    """Serve one zero-based derived PNG frame from a ready sequence."""

    parsed_index = _parse_frame_index(frame_index)
    _sequence_dir, manifest = _ready_sequence(artifact_id)
    frame_path = _validated_png_frame(artifact_id, parsed_index, manifest["frame_count"])
    _guard_artifact(request, frame_path)
    return FileResponse(frame_path, media_type="image/png")


class InteractiveSegmentRequest(BaseModel):
    source_path: str
    timestamp: float = 0.0
    points: list[dict[str, Any]] = []
    width: int = 540
    height: int = 960


@router.post("/interactive-segment")
def interactive_segment_endpoint(req: InteractiveSegmentRequest, request: Request = None) -> dict[str, Any]:
    """Single-frame real-time SAM 2 interactive segmentation for subject lift preview."""
    source = _source_for_processing(req.source_path)
    if request is not None:
        optional = get_optional_channel_scope(request)
        shared = any(_contained(source, root.resolve()) for root in [Path(PROJECTS_DIR).parent / name for name in ["00_Inbox", "01_Raw", "02_Assets"]] + [config.SOURCE_ROOT / "02_Assets"])
        if optional is not None or not shared:
            _guard_source(optional or get_channel_scope(request), source)
    try:
        from scripts.interactive_sam2_client import segment_frame_interactive
        return segment_frame_interactive(
            str(source),
            req.timestamp,
            req.points,
            width=req.width,
            height=req.height,
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "contours": [], "bbox": None}


__all__ = [
    "get_background_isolation_frame",
    "get_background_isolation_manifest",
    "preflight_background_isolation",
    "interactive_segment_endpoint",
    "router",
]
