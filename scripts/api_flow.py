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
def get_status(detailed: bool = False):
    """Checks flow-mcp service and Google Flow web session."""
    service = get_flow_service()
    return service.get_status(detailed=detailed)


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
