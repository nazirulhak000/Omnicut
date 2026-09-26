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

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from scripts.background_isolation_sequence_artifacts import (
    SequenceArtifactStoreError,
    read_sequence_manifest,
    sequence_frame_path,
    sequence_paths,
    sequence_status,
)
from scripts.config import PROJECTS_DIR
from scripts.storage_cleaner import is_strictly_protected_path
from scripts.task_manager import TaskManager
from scripts.background_isolation import normalize_background_isolation
from scripts.background_isolation_sequence_artifacts import build_sequence_artifact_id
from scripts.background_isolation_sequence_worker import DERIVED_CACHE_NAMESPACE
from scripts.background_isolation_video_worker import (
    VIDEO_NAMESPACE, VIDEO_NAME, VIDEO_SCHEMA_VERSION,
    process_background_isolation_video,
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
    fps: float = Field(default=30.0, gt=0.0, le=120.0)
    timebase: str | None = None
    width: int = Field(default=1080, gt=0, le=4096)
    height: int = Field(default=1920, gt=0, le=4096)
    rotation: int = Field(default=0)
    project_name: str | None = None


_BACKGROUND_TASK_LOCK = threading.Lock()
_BACKGROUND_TASKS_RUNNING: set[str] = set()
_BACKGROUND_TASK_CANCEL_EVENTS: dict[str, threading.Event] = {}


def _background_isolation_preflight(
    req: BackgroundIsolationProcessRequest,
    source: Path,
) -> dict[str, Any]:
    """Return actionable runtime/capacity checks without starting a worker."""

    modules = {
        name: importlib.util.find_spec(name) is not None
        for name in ("rembg", "onnxruntime", "PIL")
    }
    model_home = Path(os.environ.get("U2NET_HOME") or (Path.home() / ".u2net"))
    model_path = model_home / f"{req.config.get('model', 'u2net')}.onnx"
    frame_count = math.ceil((req.duration or 0) * req.fps - 1e-9) if req.duration else None
    # The new worker streams pixels through RAM and stages one alpha video.
    # Keep a conservative compressed-video allowance without reserving disk
    # for two full-resolution PNG sequences.
    estimated_cache_bytes = (
        frame_count * req.width * req.height // 4 if frame_count is not None else None
    )
    disk_target = Path(PROJECTS_DIR).resolve(strict=False)
    while not disk_target.exists() and disk_target != disk_target.parent:
        disk_target = disk_target.parent
    free_disk_bytes = shutil.disk_usage(disk_target).free
    required_disk_bytes = max(128 * 1024 * 1024, int((estimated_cache_bytes or 0) * 2))
    required_memory_bytes = (
        384 * 1024 * 1024 if req.config.get("model") == "u2netp" else 768 * 1024 * 1024
    )
    available_memory_bytes = None
    if importlib.util.find_spec("psutil") is not None:
        try:
            psutil = importlib.import_module("psutil")
            available_memory_bytes = int(psutil.virtual_memory().available)
        except Exception:
            available_memory_bytes = None
    issues: list[dict[str, str]] = []
    for module, available in modules.items():
        if not available:
            issues.append({
                "severity": "error",
                "code": f"{module.lower()}_missing",
                "message": f"ไม่พบ runtime {module} ใน environment ของ backend",
            })
    if not model_path.is_file():
        issues.append({
            "severity": "warning",
            "code": "model_not_cached",
            "message": f"ยังไม่พบโมเดล {model_path.name} ในเครื่อง งานแรกอาจต้องดาวน์โหลดโมเดล",
        })
    if req.duration is None:
        issues.append({
            "severity": "warning",
            "code": "duration_unknown",
            "message": "ไม่ทราบความยาวช่วงวิดีโอ จึงยังประเมินจำนวนเฟรมและพื้นที่ไม่ได้",
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
            "message": "RAM ว่างไม่พอสำหรับโมเดล Cutout ที่เลือก กรุณาปิดโปรแกรมอื่นหรือใช้โมเดล u2netp",
        })

    return {
        "ok": not any(issue["severity"] == "error" for issue in issues),
        "source_path": str(source),
        "start": req.start,
        "duration": req.duration,
        "fps": req.fps,
        "frame_count": frame_count,
        "estimated_cache_bytes": estimated_cache_bytes,
        "free_disk_bytes": free_disk_bytes,
        "required_disk_bytes": required_disk_bytes,
        "available_memory_bytes": available_memory_bytes,
        "required_memory_bytes": required_memory_bytes,
        "model": req.config.get("model", "u2net"),
        "model_cached": model_path.is_file(),
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
    allowed = False
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


def _run_background_isolation_task(
    task_id: str,
    req: BackgroundIsolationProcessRequest,
    cancel_event: threading.Event | None = None,
) -> None:
    if cancel_event is None:
        with _BACKGROUND_TASK_LOCK:
            cancel_event = _BACKGROUND_TASK_CANCEL_EVENTS.get(task_id)
    try:
        source = _source_for_processing(req.source_path)
        normalized = normalize_background_isolation(req.config)
        if not normalized["enabled"]:
            raise ValueError(f"background isolation config is disabled or invalid: {normalized.get('reason', 'invalid_config')}")
        source_fingerprint = _source_fingerprint(source)
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
                TaskManager.update_progress(task_id, min(0.99, 0.45 * float(value) if stage == "processing" else 0.45 + 0.55 * float(value)), f"Background isolation: {stage}")

        TaskManager.update_progress(task_id, 0.05, "กำลังตัดพื้นหลังวิดีโอ")
        result = process_background_isolation_video(
            source, cache_root, normalized,
            source_fingerprint=source_fingerprint, start=req.start,
            duration=req.duration, fps=req.fps, timebase=timebase,
            width=req.width, height=req.height, rotation=req.rotation,
            cancel_event=cancel_event, progress_callback=progress,
        )
        if result.get("status") != "ready" or not result.get("artifact_id"):
            raise RuntimeError(result.get("message") or "background isolation failed")
        output_manifest = Path(result["output_directory"]) / "manifest.json"
        sequence = json.loads(output_manifest.read_text(encoding="utf-8"))
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
            TaskManager.cancel_task(task_id)
            return
        TaskManager.complete_task(task_id, completed, step_label="ตัดพื้นหลังสินค้าเสร็จแล้ว")
    except Exception as exc:
        if cancel_event is not None and cancel_event.is_set():
            TaskManager.cancel_task(task_id)
        else:
            TaskManager.fail_task(task_id, str(exc), step_label="ตัดพื้นหลังสินค้าไม่สำเร็จ")


def _schedule_background_isolation_task(task_id: str, req: BackgroundIsolationProcessRequest) -> bool:
    """Start one task at most once per server process.

    The task registry is durable, while this set protects the in-process
    recovery path from scheduling the same task twice during a reload or a
    fast reconnect. The worker itself remains retry-safe because its frame
    checkpoint is deterministic.
    """

    with _BACKGROUND_TASK_LOCK:
        if task_id in _BACKGROUND_TASKS_RUNNING:
            return False
        task = TaskManager.get_task(task_id)
        if not task or task.get("status") in {"completed", "failed", "cancelled"}:
            return False
        cancel_event = threading.Event()
        _BACKGROUND_TASK_CANCEL_EVENTS[task_id] = cancel_event
        _BACKGROUND_TASKS_RUNNING.add(task_id)

    def run_and_release() -> None:
        try:
            _run_background_isolation_task(task_id, req)
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
        if _schedule_background_isolation_task(task["id"], req):
            resumed += 1
    return resumed


@router.post("/preflight")
def preflight_background_isolation(req: BackgroundIsolationProcessRequest) -> dict[str, Any]:
    """Validate local runtime/model/capacity before queueing expensive work."""

    source = _source_for_processing(req.source_path)
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
def process_background_isolation(req: BackgroundIsolationProcessRequest, background_tasks: BackgroundTasks):
    """Queue extraction + rembg segmentation and return a pollable task id."""

    source = _source_for_processing(req.source_path)
    if req.rotation not in (0, 90, 180, 270):
        raise HTTPException(status_code=422, detail="rotation must be 0, 90, 180, or 270")
    normalized = normalize_background_isolation(req.config)
    if not normalized["enabled"]:
        raise HTTPException(status_code=422, detail=f"background isolation config is disabled or invalid: {normalized.get('reason', 'invalid_config')}")
    identity = _request_identity(source, normalized, req)
    with _BACKGROUND_TASK_LOCK:
        for active in TaskManager.get_active_tasks(limit=1000):
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
            target_tab="editor", task_id=task_id,
        )
    background_tasks.add_task(_schedule_background_isolation_task, task_id, req)
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
def get_background_isolation_manifest(artifact_id: str) -> dict[str, Any]:
    """Return a published video or legacy sequence manifest by artifact ID."""
    video = _ready_video(artifact_id)
    if video is not None:
        manifest = dict(video[1])
        proxy_path = video[0].with_name("preview.webm")
        preview = manifest.get("preview") or {}
        if (proxy_path.is_symlink() or not proxy_path.is_file()
                or proxy_path.stat().st_size != preview.get("size_bytes")):
            manifest.pop("preview", None)
        return manifest
    _sequence_dir, manifest = _ready_sequence(artifact_id)
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
def get_background_isolation_video(artifact_id: str) -> FileResponse:
    ready = _ready_video(artifact_id)
    if ready is None:
        raise HTTPException(status_code=404, detail="background isolation video not found")
    return FileResponse(ready[0], media_type="video/webm", headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.get("/videos/{artifact_id}/preview.webm")
def get_background_isolation_video_preview(artifact_id: str) -> FileResponse:
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
    return FileResponse(path, media_type="video/webm", headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.get("/sequences/{artifact_id}/frames/{frame_index}")
def get_background_isolation_frame(artifact_id: str, frame_index: str) -> FileResponse:
    """Serve one zero-based derived PNG frame from a ready sequence."""

    parsed_index = _parse_frame_index(frame_index)
    _sequence_dir, manifest = _ready_sequence(artifact_id)
    frame_path = _validated_png_frame(artifact_id, parsed_index, manifest["frame_count"])
    return FileResponse(frame_path, media_type="image/png")


__all__ = [
    "get_background_isolation_frame",
    "get_background_isolation_manifest",
    "preflight_background_isolation",
    "router",
]
