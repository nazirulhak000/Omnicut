"""API Router for External SSD Staging & Reconciliation in OmniCut Pro Studio.

Provides 1-click endpoints for detecting external drives, staging ready-to-post
clips to External SSD (Sneakernet), and reconciling posted results upon return.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.ssd_staging_engine import SSDStagingEngine, get_removable_drives
from scripts.ssd_reconcile_engine import SSDReconcileEngine
from scripts.config import BASE_DIR

router = APIRouter(prefix="/api/ssd", tags=["SSD Sneakernet Sync"])


class StageRequest(BaseModel):
    target_drive: str
    export_ids: Optional[List[str]] = None
    include_all_pending: bool = True


class ReconcileRequest(BaseModel):
    target_drive: str
    clean_ssd_after: bool = False
    retention_mode: Optional[str] = "archive"


@router.get("/drives")
def list_drives() -> Dict[str, Any]:
    """Scan and list all detected removable and external drives."""
    drives = get_removable_drives()
    return {"status": "ok", "drives": drives}


@router.post("/stage")
def stage_to_ssd(req: StageRequest) -> Dict[str, Any]:
    """Stage pending clips, covers, queue, and extension to External SSD."""
    target_path = Path(req.target_drive)
    if not target_path.exists():
        raise HTTPException(status_code=400, detail=f"Target path '{req.target_drive}' does not exist.")

    try:
        result = SSDStagingEngine.stage_to_vault(
            target_root=target_path,
            base_dir=BASE_DIR,
            export_ids=req.export_ids,
            include_all_pending=req.include_all_pending,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSD Staging failed: {str(e)}")


@router.get("/inspect")
def inspect_drive(target_drive: str) -> Dict[str, Any]:
    """Inspect an external drive to see if it holds a vault and check upload status."""
    import json
    target_path = Path(target_drive)
    if not target_path.exists():
        raise HTTPException(status_code=400, detail=f"Target path '{target_drive}' not found.")

    vault_path = target_path / "OmniCut_Portable_Vault" if target_path.name != "OmniCut_Portable_Vault" else target_path
    if not vault_path.exists():
        return {
            "status": "ok",
            "has_vault": False,
            "message": "ไม่พบข้อมูล Vault บนไดรฟ์นี้ (พร้อมสำหรับการส่งออกรอบใหม่)"
        }

    manifest_file = vault_path / "manifest.json"
    queue_file = vault_path / "queue.json"
    state_file = vault_path / "state.json"

    manifest = {}
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            pass

    queue = []
    if queue_file.exists():
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue = json.load(f)
        except Exception:
            pass

    state = {}
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass

    posted_count = sum(1 for s in state.values() if s.get("status") == "posted")
    pending_count = len(queue) - posted_count

    return {
        "status": "ok",
        "has_vault": True,
        "batch_id": manifest.get("batch_id"),
        "created_at": manifest.get("created_at"),
        "total_items": len(queue),
        "posted_count": posted_count,
        "pending_count": max(0, pending_count),
        "items": queue,
        "states": state,
    }


@router.post("/reconcile")
def reconcile_from_ssd(req: ReconcileRequest) -> Dict[str, Any]:
    """Reconcile upload receipts from External SSD back to Home PC databases."""
    target_path = Path(req.target_drive)
    if not target_path.exists():
        raise HTTPException(status_code=400, detail=f"Target path '{req.target_drive}' does not exist.")

    try:
        result = SSDReconcileEngine.reconcile_from_vault(
            vault_root=target_path,
            base_dir=BASE_DIR,
            clean_ssd_after=req.clean_ssd_after,
            retention_mode=req.retention_mode,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSD Reconciliation failed: {str(e)}")
