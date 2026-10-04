"""
FastAPI Router for OmniCut Mobile Quick Studio.
Provides mobile-first endpoints for product selection, guided filming session binding,
one-touch SOP auto-assembly & render, and TikTok sharing metadata.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from scripts.mobile_quick_studio import MobileQuickStudioService
from scripts.task_manager import TaskManager
from scripts.api_schemas import VoicePreviewRequest

router = APIRouter(prefix="/api/mobile-studio", tags=["Mobile Quick Studio"])


class CreateSessionPayload(BaseModel):
    product_id: str
    angle_id: str


class CreateQuickAnglePayload(BaseModel):
    product_id: str
    title: Optional[str] = None
    script: Optional[str] = None


class QuickAddProductPayload(BaseModel):
    name_or_url: str


class MobileVoicePreviewPayload(BaseModel):
    text: str
    voice: Optional[str] = "gemini_fenrir_male_strong"


class AssembleRenderPayload(BaseModel):
    product_id: str
    angle_id: str
    session_id: Optional[str] = None
    custom_raw_video: Optional[str] = None


@router.get("/catalog")
def get_mobile_catalog():
    """Returns products and angles formatted specifically for mobile touch cards."""
    try:
        catalog = MobileQuickStudioService.get_catalog()
        return {"success": True, "catalog": catalog, "total": len(catalog)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/session")
def get_or_create_session(payload: CreateSessionPayload):
    """Binds or creates a guided take filming session for mobile camera."""
    try:
        session = MobileQuickStudioService.get_or_create_session(
            payload.product_id, payload.angle_id
        )
        return {"success": True, "session": session}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/assemble")
def assemble_and_render(payload: AssembleRenderPayload):
    """
    Step 3: Triggers automated SOP assembly and render.
    Runs pipeline with Fenrir voice, Mali-Bold Ghost Subtitles, and #FF6622 Callouts.
    """
    try:
        result = MobileQuickStudioService.assemble_and_render(
            product_id=payload.product_id,
            angle_id=payload.angle_id,
            session_id=payload.session_id,
            custom_raw_video=payload.custom_raw_video
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/task/{task_id}")
def get_mobile_task(task_id: str):
    """Returns task status, render progress, and sharing metadata upon completion."""
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="ไม่พบงานเรนเดอร์")
    return {
        "success": True,
        "task": task,
        "is_completed": task.get("status") == "completed",
        "is_failed": task.get("status") == "failed",
        "is_cancelled": task.get("status") == "cancelled",
        "progress": task.get("progress", 0.0),
        "step_label": task.get("step_label", ""),
        "result": task.get("result") or {},
    }


@router.post("/quick-angle")
def create_quick_angle(payload: CreateQuickAnglePayload):
    """Creates a custom or instant template angle directly from mobile."""
    try:
        angle = MobileQuickStudioService.create_quick_angle(
            product_id=payload.product_id,
            title=payload.title,
            script=payload.script,
        )
        return {"success": True, "angle": angle}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload-video")
async def upload_mobile_video(
    product_id: str = Form(...),
    angle_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Directly uploads and binds camera roll footage to a product angle."""
    try:
        content = await file.read()
        res = MobileQuickStudioService.upload_mobile_video(
            product_id=product_id,
            angle_id=angle_id,
            file_bytes=content,
            filename=file.filename or "video.mp4"
        )
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/products/quick-add")
def quick_add_product(payload: QuickAddProductPayload):
    """Creates a product and initial angle from name or TikTok Shop link."""
    try:
        product = MobileQuickStudioService.quick_add_product(payload.name_or_url)
        return {"success": True, "product": product}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/preview-voice")
def preview_mobile_voice(payload: MobileVoicePreviewPayload):
    """Generates a quick 5-second voice audition sample for the script."""
    try:
        from scripts.api_voice import preview_voice
        req = VoicePreviewRequest(
            text=payload.text[:120],
            voice_gender=payload.voice or "gemini_fenrir_male_strong",
            speed=1.15,
            ad_tone="commercial_premium"
        )
        return preview_voice(req)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
