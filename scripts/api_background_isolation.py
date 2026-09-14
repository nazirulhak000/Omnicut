"""Read-only API for published background-isolation frame sequences.

The router deliberately owns no processing lifecycle.  A sequence worker
publishes a validated manifest and derived PNG frames first; this module only
serves a complete, ready sequence from the canonical project cache.  The
application mounts the router, so the normal application middleware (including
the API-key gate) remains the single authentication boundary.
"""

from __future__ import annotations

import re
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from scripts.background_isolation_sequence_artifacts import (
    SequenceArtifactStoreError,
    is_sequence_ready,
    read_sequence_manifest,
    sequence_frame_path,
    sequence_paths,
    sequence_status,
)
from scripts.config import PROJECTS_DIR
from scripts.task_manager import TaskManager
from scripts.background_isolation import normalize_background_isolation
from scripts.background_isolation_sequence import extract_background_isolation_sequence
from scripts.background_isolation_sequence_artifacts import build_sequence_artifact_id, build_sequence_manifest, write_sequence_manifest
from scripts.background_isolation_sequence_worker import process_background_isolation_sequence


router = APIRouter(prefix="/api/background-isolation", tags=["background-isolation"])

_FRAME_INDEX_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class BackgroundIsolationProcessRequest(BaseModel):
    """Request to build a ready RGBA sequence in the project cache."""

    source_path: str
    config: dict[str, Any] = Field(default_factory=dict)
    start: float = Field(default=0.0, ge=0.0)
    duration: float | None = Field(default=None, gt=0.0)
    fps: float = Field(default=30.0, gt=0.0, le=120.0)
    timebase: str | None = None
    width: int = Field(default=1080, gt=0, le=4096)
    height: int = Field(default=1920, gt=0, le=4096)
    rotation: int = Field(default=0)


def _source_for_processing(value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = Path(PROJECTS_DIR).parent / candidate
    candidate = candidate.resolve(strict=False)
    if candidate.is_symlink() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="background isolation source video not found")
    return candidate


def _source_fingerprint(source: Path) -> str:
    stat = source.stat()
    payload = f"{source.as_posix()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _run_background_isolation_task(task_id: str, req: BackgroundIsolationProcessRequest) -> None:
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
        source_id = build_sequence_artifact_id(
            f"{source_fingerprint}|start={req.start:.6f}|duration={req.duration if req.duration is not None else 'end'}",
            algorithm="background-isolation-source-v1",
            engine=normalized["engine"], model=normalized["model"], quality=normalized["quality"],
            worker_version="source-sequence-v1", fps=req.fps, timebase=timebase,
            width=req.width, height=req.height, rotation=req.rotation,
        )
        cache_root = Path(PROJECTS_DIR).resolve() / ".cache"

        def progress(event: dict[str, Any]) -> None:
            stage = event.get("stage", "processing")
            value = event.get("progress")
            if isinstance(value, (int, float)):
                TaskManager.update_progress(task_id, min(0.99, 0.45 * float(value) if stage == "processing" else 0.45 + 0.55 * float(value)), f"Background isolation: {stage}")

        TaskManager.update_progress(task_id, 0.05, "กำลังเตรียมเฟรมวิดีโอสำหรับตัดพื้นหลัง")
        extracted = extract_background_isolation_sequence(
            source, cache_root, source_id, start=req.start, duration=req.duration,
            fps=req.fps, timebase=timebase, width=req.width, height=req.height,
            progress_callback=progress,
        )
        if extracted.get("status") != "ready":
            raise RuntimeError(extracted.get("message") or "source frame extraction failed")
        source_manifest = build_sequence_manifest(
            source_id, source_fingerprint=source_fingerprint,
            algorithm="background-isolation-source-v1", engine=normalized["engine"],
            model=normalized["model"], quality=normalized["quality"],
            worker_version="source-sequence-v1", frame_count=extracted["frame_count"],
            fps=req.fps, timebase=timebase, width=req.width, height=req.height,
            rotation=req.rotation, status="ready",
        )
        write_sequence_manifest(cache_root, source_id, source_manifest)
        TaskManager.update_progress(task_id, 0.48, "กำลังแยกสินค้าออกจากพื้นหลังด้วย rembg")
        result = process_background_isolation_sequence(
            extracted["sequence_dir"], cache_root, {
                **normalized, "artifact": {"id": None, "status": "missing"},
            }, source_manifest, progress_callback=progress,
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
            },
            "sequence": sequence,
        }
        TaskManager.complete_task(task_id, completed, step_label="ตัดพื้นหลังสินค้าเสร็จแล้ว")
    except Exception as exc:
        TaskManager.fail_task(task_id, str(exc), step_label="ตัดพื้นหลังสินค้าไม่สำเร็จ")


@router.post("/process")
def process_background_isolation(req: BackgroundIsolationProcessRequest, background_tasks: BackgroundTasks):
    """Queue extraction + rembg segmentation and return a pollable task id."""

    _source_for_processing(req.source_path)
    if req.rotation not in (0, 90, 180, 270):
        raise HTTPException(status_code=422, detail="rotation must be 0, 90, 180, or 270")
    normalized = normalize_background_isolation(req.config)
    if not normalized["enabled"]:
        raise HTTPException(status_code=422, detail=f"background isolation config is disabled or invalid: {normalized.get('reason', 'invalid_config')}")
    task_id = str(uuid.uuid4())
    TaskManager.create_task(
        "background_isolation", "กำลังตัดพื้นหลังสินค้า", payload=req.model_dump(),
        target_tab="editor", task_id=task_id,
    )
    background_tasks.add_task(_run_background_isolation_task, task_id, req)
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
        sequence_paths(_canonical_cache_root(), artifact_id)
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
        status = sequence_status(cache_root, safe_id)
        ready = is_sequence_ready(cache_root, safe_id)
    except (SequenceArtifactStoreError, OSError, ValueError) as exc:
        # Missing, malformed, incomplete, and symlinked artifacts are all
        # intentionally indistinguishable to a reader.
        raise HTTPException(status_code=404, detail="background isolation sequence not found") from exc
    if status != "ready" or not ready:
        raise HTTPException(status_code=404, detail="background isolation sequence not found")

    manifest = read_sequence_manifest(cache_root, safe_id)
    if manifest is None or manifest.get("status") != "ready":
        raise HTTPException(status_code=404, detail="background isolation sequence not found")
    try:
        paths = sequence_paths(cache_root, safe_id)
    except (SequenceArtifactStoreError, OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="background isolation sequence not found") from exc
    return paths.directory, manifest


def _parse_frame_index(raw_frame_index: str) -> int:
    if not isinstance(raw_frame_index, str) or not _FRAME_INDEX_RE.fullmatch(raw_frame_index):
        raise HTTPException(status_code=400, detail="frame_index must be a zero-based integer")
    try:
        frame_index = int(raw_frame_index, 10)
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
        frame_path = sequence_frame_path(cache_root, artifact_id, frame_index)
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
    """Return a published ready manifest for one opaque sequence ID."""

    _sequence_dir, manifest = _ready_sequence(artifact_id)
    return manifest


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
    "router",
]
