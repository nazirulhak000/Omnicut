"""
FastAPI Router for Google Flow (Veo) Video Generation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
    max_credits: int = 25
    download_quality: str = "original"
    technique: Optional[str] = None


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
def get_status(detailed: bool = False, auto_start: bool = True):
    """Checks flow-mcp service and Google Flow web session with auto-start daemon."""
    service = get_flow_service()
    return service.get_status(detailed=detailed, auto_start=auto_start)


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
