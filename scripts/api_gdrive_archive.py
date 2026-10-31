"""FastAPI Router for Google Drive Archiving & Local Breadcrumb Retention.

Provides endpoints to inspect reclaimable storage on posted clips, execute background
archiving to Google Drive Desktop with real-time progress polling, restore clips,
and reveal files in Explorer.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.gdrive_archive_engine import GDriveArchiveEngine

router = APIRouter(prefix="/api/archive", tags=["Google Drive Archive"])

# Background Task State
_TASK_LOCK = threading.Lock()
_CURRENT_ARCHIVE_TASK: Dict[str, Any] = {
    "status": "idle",  # "idle" | "running" | "completed" | "error"
    "stage": "idle",
    "current_index": 0,
    "total_items": 0,
    "current_file": "",
    "product_name": "",
    "reclaimed_bytes": 0,
    "reclaimed_formatted": "0 B",
    "total_bytes": 0,
    "percent": 0.0,
    "error": None,
    "result": None,
}


def _run_archive_worker(
    export_ids: Optional[List[str]],
    product_ids: Optional[List[str]],
    scope: str,
):
    global _CURRENT_ARCHIVE_TASK

    def on_progress(p: Dict[str, Any]):
        with _TASK_LOCK:
            _CURRENT_ARCHIVE_TASK.update({
                "stage": p.get("stage", "running"),
                "current_index": p.get("current_index", 0),
                "total_items": p.get("total_items", 0),
                "current_file": p.get("current_file", ""),
                "product_name": p.get("product_name", ""),
                "reclaimed_bytes": p.get("reclaimed_bytes", 0),
                "reclaimed_formatted": p.get("reclaimed_formatted", "0 B"),
                "total_bytes": p.get("total_bytes", 0),
                "percent": p.get("percent", 0.0),
            })

    try:
        res = GDriveArchiveEngine.archive_clips(
            export_ids=export_ids,
            product_ids=product_ids,
            scope=scope,
            progress_callback=on_progress,
        )
        with _TASK_LOCK:
            _CURRENT_ARCHIVE_TASK["status"] = "completed"
            _CURRENT_ARCHIVE_TASK["percent"] = 100.0
            _CURRENT_ARCHIVE_TASK["result"] = res
            _CURRENT_ARCHIVE_TASK["error"] = None
    except Exception as e:
        with _TASK_LOCK:
            _CURRENT_ARCHIVE_TASK["status"] = "error"
            _CURRENT_ARCHIVE_TASK["error"] = str(e)


class ArchiveExecuteRequest(BaseModel):
    export_ids: Optional[List[str]] = None
    product_ids: Optional[List[str]] = None
    scope: str = "video_only"  # "video_only" or "full"
    async_mode: bool = True


class RestoreRequest(BaseModel):
    export_id: str


class RevealRequest(BaseModel):
    target_path: str


@router.get("/status")
def get_archive_status() -> Dict[str, Any]:
    """Inspect all posted exports, eligible reclaimable storage, and Google Drive availability."""
    try:
        return GDriveArchiveEngine.get_archive_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect archive status: {str(e)}")


@router.get("/progress")
def get_archive_progress() -> Dict[str, Any]:
    """Poll live progress of background Google Drive archiving task."""
    with _TASK_LOCK:
        return dict(_CURRENT_ARCHIVE_TASK)


@router.post("/execute")
def execute_archive(req: ArchiveExecuteRequest) -> Dict[str, Any]:
    """Execute archiving of selected posted clips to Google Drive and reclaim local space."""
    global _CURRENT_ARCHIVE_TASK

    if req.async_mode:
        with _TASK_LOCK:
            if _CURRENT_ARCHIVE_TASK["status"] == "running":
                return {
                    "status": "already_running",
                    "message": "กำลังมีการสำรองข้อมูลขึ้น Google Drive อยู่แล้ว",
                    "progress": dict(_CURRENT_ARCHIVE_TASK),
                }

            # Initialize task state
            task_id = str(uuid.uuid4())
            _CURRENT_ARCHIVE_TASK.update({
                "task_id": task_id,
                "status": "running",
                "stage": "starting",
                "current_index": 0,
                "total_items": 0,
                "current_file": "",
                "product_name": "",
                "reclaimed_bytes": 0,
                "reclaimed_formatted": "0 B",
                "total_bytes": 0,
                "percent": 0.0,
                "error": None,
                "result": None,
            })

        worker = threading.Thread(
            target=_run_archive_worker,
            args=(req.export_ids, req.product_ids, req.scope),
            daemon=True,
        )
        worker.start()

        return {
            "status": "started",
            "task_id": task_id,
            "message": "เริ่มสำรองข้อมูลขึ้น Google Drive ในเบื้องหลังเรียบร้อย",
        }

    # Synchronous mode fallback
    try:
        result = GDriveArchiveEngine.archive_clips(
            export_ids=req.export_ids,
            product_ids=req.product_ids,
            scope=req.scope,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive execution failed: {str(e)}")


@router.post("/restore")
def restore_clip(req: RestoreRequest) -> Dict[str, Any]:
    """Restore an archived clip from Google Drive back to local storage."""
    try:
        result = GDriveArchiveEngine.restore_clip(export_id=req.export_id)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.post("/reveal")
def reveal_in_explorer(req: RevealRequest) -> Dict[str, Any]:
    """Open folder or select file in Windows Explorer."""
    success = GDriveArchiveEngine.open_in_explorer(req.target_path)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot reveal path in Explorer")
    return {"status": "ok", "revealed": True}
