"""
FastAPI Router for Google Flow (Veo) Video Generation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scripts.flow_accounts import get_flow_account_manager
from scripts.flow_client import get_flow_client, FlowClientError
from scripts.flow_prompt_engine import (
    expand_prompt_with_gemini,
    bundle_flow_context,
    bundle_flow_batch_contexts,
    CAMERA_TECHNIQUES,
    LIGHTING_PRESETS,
)
from scripts.flow_service import get_flow_service, FlowJobStore

logger = logging.getLogger("omnicut.api_flow")

router = APIRouter(prefix="/api/flow", tags=["Google Flow"])


class AccountSwitchRequest(BaseModel):
    account_id: Optional[str] = None
    accountId: Optional[str] = None
    user_index: Optional[int] = None
    userIndex: Optional[int] = None


class AccountUpdateRequest(BaseModel):
    account_id: Optional[str] = None
    accountId: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    credits: Optional[int] = None
    plan: Optional[str] = None
    status: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class AutoFailoverRequest(BaseModel):
    enabled: Optional[bool] = None
    auto_failover: Optional[bool] = None
    min_credits: Optional[int] = None
    min_failover_credits: Optional[int] = None


class PromptExpandRequest(BaseModel):
    thai_description: str
    product_name: str = ""
    product_specs: Optional[Dict[str, Any]] = None
    technique: str = "orbit"
    lighting: str = "studio_clean"


class ContextBundleRequest(BaseModel):
    product_id: str
    beat_text: str
    camera_direction: str = "orbit"
    lighting: str = "studio_clean"
    product_name: Optional[str] = None
    product_specs: Optional[Dict[str, Any]] = None
    aspect_ratio: str = "9:16"
    duration: int = 8
    download_quality: str = "original"
    max_credits: int = 25


class ShotItem(BaseModel):
    beat_text: Optional[str] = None
    prompt: Optional[str] = None
    camera_direction: Optional[str] = "orbit"
    lighting: Optional[str] = "studio_clean"
    aspect_ratio: Optional[str] = "9:16"
    duration: Optional[int] = 8
    reference_images: Optional[List[str]] = None
    first_frame: Optional[str] = None
    max_credits: Optional[int] = 25
    download_quality: Optional[str] = "original"


class BatchGenerateRequest(BaseModel):
    product_id: str
    shots: List[ShotItem]
    project_name: Optional[str] = None
    auto_bundle: bool = True


class SceneItem(BaseModel):
    prompt: str
    type: str = "video"
    aspect_ratio: str = "9:16"
    duration: Optional[int] = 8
    model: Optional[str] = None
    reference_images: Optional[List[str]] = None
    first_frame: Optional[str] = None
    max_credits: int = 100
    download_quality: str = "original"
    technique: Optional[str] = None
    shot_index: Optional[int] = None
    shot_label: Optional[str] = None


class GenerateRequest(BaseModel):
    product_id: str
    scenes: List[SceneItem]
    project_name: Optional[str] = None


class IngestRequest(BaseModel):
    product_id: str
    source_path: str
    shot_label: str = ""
    custom_name: Optional[str] = None


@router.get("/status")
def get_status(detailed: bool = False, auto_start: bool = False):
    """Checks flow-mcp service and Google Flow web session without auto-starting."""
    service = get_flow_service()
    return service.get_status(detailed=detailed, auto_start=auto_start)


@router.get("/accounts")
def get_accounts():
    """Returns list of Google Flow accounts, active account, and total pool credits."""
    manager = get_flow_account_manager()
    return {"ok": True, **manager.get_pool_summary()}


@router.post("/accounts/switch")
def switch_account(req: AccountSwitchRequest):
    """Switches active account in Google Flow account pool and synchronizes with Chrome."""
    manager = get_flow_account_manager()
    acc_id = req.account_id or req.accountId
    user_idx = req.user_index if req.user_index is not None else req.userIndex
    if not acc_id and user_idx is None:
        raise HTTPException(status_code=400, detail="account_id or user_index is required")
    try:
        res = manager.switch_account_with_chrome(account_id=acc_id, user_index=user_idx)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to switch account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/open-login")
def open_login():
    """Clicks 'Account details' -> 'Switch account' in Chrome so the user can easily click 'Use another account' and sign in."""
    from scripts.flow_accounts import open_chrome_login
    res = open_chrome_login()
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error", "Failed to open login in Chrome"))
    return res


@router.post("/accounts/sync")
def sync_account():
    """Syncs active account's real email and credits from Chrome CDP."""
    manager = get_flow_account_manager()
    synced = manager.sync_active_account_with_chrome()
    if not synced:
        return {"ok": False, "message": "Chrome CDP not reachable or account details unavailable"}
    return {"ok": True, "active_account": synced, **manager.get_pool_summary()}


@router.post("/accounts/update")
def update_account(req: AccountUpdateRequest):
    """Updates account metadata/label and credits."""
    manager = get_flow_account_manager()
    acc_id = req.account_id or req.accountId
    if not acc_id:
        raise HTTPException(status_code=400, detail="account_id is required")

    updates: Dict[str, Any] = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.email is not None:
        updates["email"] = req.email
    if req.credits is not None:
        updates["credits"] = req.credits
    if req.plan is not None:
        updates["plan"] = req.plan
    if req.status is not None:
        updates["status"] = req.status
    if req.data and isinstance(req.data, dict):
        updates.update(req.data)

    try:
        updated = manager.update_account(acc_id, updates)
        return {"ok": True, "account": updated}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/auto-failover")
def toggle_auto_failover(req: AutoFailoverRequest):
    """Toggles auto-failover on/off."""
    manager = get_flow_account_manager()
    enabled = req.enabled if req.enabled is not None else (req.auto_failover if req.auto_failover is not None else True)
    min_cred = req.min_credits if req.min_credits is not None else req.min_failover_credits
    res = manager.set_auto_failover(enabled=enabled, min_credits=min_cred)
    return {
        "ok": True,
        "auto_failover": res,
        "min_failover_credits": manager.get_min_failover_credits(),
    }


@router.post("/service/start")
def start_service():
    """Starts the local flow-mcp service daemon."""
    client = get_flow_client()
    if client.is_healthy():
        return {"ok": True, "message": "flow-mcp service is already running."}
    try:
        client.start_service_daemon()
        return {"ok": True, "message": "flow-mcp service started successfully."}
    except Exception as e:
        logger.error(f"Failed to start flow-mcp daemon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/service/stop")
def stop_service():
    """Stops the flow-mcp service and closes the Google Flow Chrome browser."""
    service = get_flow_service()
    return service.stop_service()


@router.get("/presets")
def get_presets():
    """Returns available camera techniques and lighting presets."""
    return {
        "camera_techniques": [
            {"id": k, "label": k.replace("_", " ").title(), "description": v}
            for k, v in CAMERA_TECHNIQUES.items()
        ],
        "lighting_presets": [
            {"id": k, "label": k.replace("_", " ").title(), "description": v}
            for k, v in LIGHTING_PRESETS.items()
        ],
    }


@router.post("/context/bundle")
def bundle_context(req: ContextBundleRequest):
    """Bundles product info, auto-picks reference image, and expands cinematic prompt with Gemini Flash."""
    try:
        bundled = bundle_flow_context(
            product_id=req.product_id,
            beat_text=req.beat_text,
            camera_direction=req.camera_direction,
            lighting=req.lighting,
            product_name=req.product_name,
            product_specs=req.product_specs,
            aspect_ratio=req.aspect_ratio,
            duration=req.duration,
            download_quality=req.download_quality,
            max_credits=req.max_credits,
        )
        return {"ok": True, "scene": bundled}
    except Exception as e:
        logger.error(f"Context bundle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product/{product_id}/angles/{angle_id}/shots-flow")
def get_angle_shots_flow(
    product_id: str,
    angle_id: str,
    duration: int = 8,
    aspect_ratio: str = "9:16",
    max_credits: int = 25,
):
    """
    Automatically bundles the 5 script beats of the given angle with synthesized prompts
    and auto-picked reference images, ready for 1-click execution.
    """
    service = get_flow_service()
    try:
        res = service.bundle_angle_shots_flow(
            product_id=product_id,
            angle_id=angle_id,
            duration=duration,
            aspect_ratio=aspect_ratio,
            max_credits=max_credits,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to bundle angle shots for flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-generate")
def batch_generate(req: BatchGenerateRequest):
    """Dispatches batch generation for multiple shots with background polling and auto-ingest."""
    service = get_flow_service()
    try:
        shots_data = [s.model_dump(exclude_none=True) for s in req.shots]
        res = service.dispatch_batch_generation(
            product_id=req.product_id,
            shots=shots_data,
            project_name=req.project_name,
            auto_bundle=req.auto_bundle,
        )
        return {"ok": True, **res}
    except FlowClientError as e:
        raise HTTPException(status_code=502, detail=f"Flow engine error: {e}")
    except Exception as e:
        logger.error(f"Batch generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prompt/expand")
def expand_prompt(req: PromptExpandRequest):
    """Enriches and translates Thai shot notes into Google Flow cinematic English prompts."""
    try:
        expanded = expand_prompt_with_gemini(
            thai_description=req.thai_description,
            product_name=req.product_name,
            product_specs=req.product_specs,
            technique=req.technique,
            lighting=req.lighting,
        )
        return {"ok": True, "prompt": expanded}
    except Exception as e:
        logger.error(f"Prompt expansion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
def create_generation_job(req: GenerateRequest):
    """Submits scene generation batch to Google Flow."""
    service = get_flow_service()
    try:
        scenes_data = [s.model_dump(exclude_none=True) for s in req.scenes]
        res = service.submit_generation(
            product_id=req.product_id,
            scenes=scenes_data,
            project_name=req.project_name,
        )
        return {"ok": True, **res}
    except FlowClientError as e:
        raise HTTPException(status_code=502, detail=f"Flow engine error: {e}")
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
def list_jobs(product_id: Optional[str] = None):
    """Lists recent generation jobs."""
    jobs = FlowJobStore.list_jobs(product_id=product_id)
    return {"jobs": jobs}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Retrieves and polls status for a specific job."""
    service = get_flow_service()
    try:
        job = service.check_and_sync_job(job_id)
        return {"ok": True, "job": job}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
def ingest_clip(req: IngestRequest):
    """Ingests a completed video clip into 01_Raw/<product_id>/AI_Flow/."""
    service = get_flow_service()
    try:
        metadata = service.ingest_clip(
            product_id=req.product_id,
            source_path=req.source_path,
            shot_label=req.shot_label,
            custom_name=req.custom_name,
        )
        return {"ok": True, "metadata": metadata}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
