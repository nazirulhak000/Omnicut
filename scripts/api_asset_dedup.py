"""API Router for Asset Deduplication in OmniCut Pro Studio."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.channel_workflows import get_workflow_scope
from scripts.api_videos import _guard_write, _guard_raw_mutation, _resolve_allowed_video_path
from scripts import asset_dedup
from pathlib import Path
from scripts.asset_dedup import AssetDedupEngine, ReferenceLoadError

router = APIRouter(prefix="/api/assets/duplicates", tags=["asset-dedup"])


class CleanDuplicatesRequest(BaseModel):
    duplicate_paths: List[str] = Field(..., description="List of full or relative paths to delete")
    move_to_trash: bool = Field(default=True, description="Move to .trash instead of permanent delete")


@router.get("/scan")
def scan_duplicates(min_size_kb: int = 10, scope: ChannelScope = Depends(get_workflow_scope)) -> Dict[str, Any]:
    """Scans inbox and raw directories for duplicate media assets."""
    try:
        # S1-12: a channel only sees its own (or shared, unreferenced) media.
        path_filter = AssetDedupEngine.channel_path_filter(
            scope.channel_id, allow_legacy_main=not scope.strict,
        )
        results = AssetDedupEngine.scan_duplicates(
            min_file_size_bytes=min_size_kb * 1024, path_filter=path_filter,
        )
        return {"status": "ok", **results}
    except (HTTPException, ChannelError):
        raise
    except ReferenceLoadError as e:
        raise HTTPException(status_code=503, detail=f"สแกนไฟล์ซ้ำไม่ได้ เพราะตรวจรายการอ้างอิงไม่ครบ: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deduplication scan failed: {str(e)}")


@router.post("/clean")
def clean_duplicates(req: CleanDuplicatesRequest, scope: ChannelScope = Depends(get_workflow_scope)) -> Dict[str, Any]:
    """Safely cleans specified duplicate files."""
    if not req.duplicate_paths:
        raise HTTPException(status_code=400, detail="No duplicate paths provided")

    _guard_write(scope)
    for value in req.duplicate_paths:
        candidate = Path(value)
        candidate = candidate if candidate.is_absolute() else asset_dedup.BASE_DIR / candidate
        _guard_raw_mutation(candidate.resolve(), scope)
    try:
        result = AssetDedupEngine.clean_duplicates(
            duplicate_paths=req.duplicate_paths,
            move_to_trash=req.move_to_trash
        )
        return result
    except (HTTPException, ChannelError):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleaning duplicates failed: {str(e)}")
