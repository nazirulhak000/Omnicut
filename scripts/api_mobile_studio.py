"""
FastAPI Router for OmniCut Mobile Quick Studio.
Provides mobile-first endpoints for product selection, guided filming session binding,
one-touch SOP auto-assembly & render, and TikTok sharing metadata.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Request
from pydantic import BaseModel

from scripts.mobile_quick_studio import MobileQuickStudioService
from scripts.task_manager import TaskManager
from scripts.api_schemas import VoicePreviewRequest

from fastapi import Depends
from scripts.channel_store import ChannelError
from scripts.channel_scope import ChannelScope, require_writable, require_active_for_new_work, require_final_ready
from scripts.channel_workflows import api_store_kwargs, capture_job_scope, get_workflow_scope

router = APIRouter(prefix="/api/mobile-studio", tags=["Mobile Quick Studio"])

def _scope_kwargs(scope):
    return api_store_kwargs(scope) if isinstance(scope, ChannelScope) else {}


def _job_snapshot(scope):
    return capture_job_scope(scope) if isinstance(scope, ChannelScope) else {}


def _guard_write(scope, new_work=False):
    if isinstance(scope, ChannelScope):
        (require_active_for_new_work if new_work else require_writable)(scope)



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
    bgm_enabled: Optional[bool] = True


@router.get("/catalog")
def get_mobile_catalog(
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100), scope: ChannelScope = Depends(get_workflow_scope)):
    """Returns products and angles formatted specifically for mobile touch cards.

    P2-4: ส่ง ``page``/``page_size`` เพื่อดึงทีละหน้า (page_size สูงสุด 100) คืน
    ``page``/``page_size``/``total_pages``/``has_more`` ให้ client รู้ว่ามีหน้าถัดไป
    ไม่ส่งพารามเลย = ของเดิมทั้งหมด (client เก่าและเทสเดิมยังได้ ``catalog``/``total`` เหมือนเดิม)
    """
    try:
        catalog = MobileQuickStudioService.get_catalog(**_scope_kwargs(scope))
        total = len(catalog)
        if page is None and page_size is None:
            return {
                "success": True,
                "catalog": catalog,
                "total": total,
                "page": 1,
                "page_size": total,
                "total_pages": 1,
                "has_more": False,
            }
        size = page_size or 20
        current = page or 1
        start = (current - 1) * size
        total_pages = (total + size - 1) // size or 1
        return {
            "success": True,
            "catalog": catalog[start:start + size],
            "total": total,
            "page": current,
            "page_size": size,
            "total_pages": total_pages,
            "has_more": start + size < total,
        }
    except (HTTPException, ChannelError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/session")
def get_or_create_session(payload: CreateSessionPayload, scope: ChannelScope = Depends(get_workflow_scope)):
    """Binds or creates a guided take filming session for mobile camera."""
    _guard_write(scope, new_work=True)
    try:
        session = MobileQuickStudioService.get_or_create_session(
            payload.product_id, payload.angle_id
        , **_scope_kwargs(scope))
        return {"success": True, "session": session}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except (HTTPException, ChannelError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/assemble")
def assemble_and_render(payload: AssembleRenderPayload, scope: ChannelScope = Depends(get_workflow_scope)):
    """
    Step 3: Triggers automated SOP assembly and render.
    Runs pipeline with Fenrir voice, Mali-Bold Ghost Subtitles, and #FF6622 Callouts.
    """
    _guard_write(scope, new_work=True)
    if isinstance(scope, ChannelScope) and (not scope.is_implicit_default or scope.strict):
        require_final_ready(scope)
    try:
        result = MobileQuickStudioService.assemble_and_render(
            product_id=payload.product_id,
            angle_id=payload.angle_id,
            session_id=payload.session_id,
            custom_raw_video=payload.custom_raw_video,
            bgm_enabled=payload.bgm_enabled if payload.bgm_enabled is not None else True,
         **_scope_kwargs(scope), job_scope=_job_snapshot(scope))
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except (HTTPException, ChannelError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/task/{task_id}")
def get_mobile_task(task_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    """Returns task status, render progress, and sharing metadata upon completion."""
    task = TaskManager.get_task(task_id, **_scope_kwargs(scope))
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


@router.post("/cancel/{task_id}")
def cancel_mobile_task(task_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    """Cancels an in-flight mobile auto-assemble render.

    task_id is the same uuid4 mobile_quick_studio.py passes as render_jobs'
    job_id, so asking the render-job side to stop also unwinds the actual
    background work -- this never starts a new render. Mirrors the shared
    scripts/api_tasks.py cancel route (TaskManager + render_jobs).
    """
    _guard_write(scope, new_work=False)
    task = TaskManager.get_task(task_id, **_scope_kwargs(scope))
    if not task:
        raise HTTPException(status_code=404, detail="ไม่พบงานเรนเดอร์")
    if task.get("status") in ("completed", "failed", "cancelled"):
        return {"success": True, "already_terminal": True, "task": task}
    TaskManager.cancel_task(task_id, **_scope_kwargs(scope))
    from scripts import render_jobs
    render_jobs.request_cancel(task_id, **_scope_kwargs(scope))
    return {"success": True, "task": TaskManager.get_task(task_id, **_scope_kwargs(scope))}


@router.post("/quick-angle")
def create_quick_angle(payload: CreateQuickAnglePayload, scope: ChannelScope = Depends(get_workflow_scope)):
    """Creates a custom or instant template angle directly from mobile."""
    _guard_write(scope, new_work=True)
    try:
        angle = MobileQuickStudioService.create_quick_angle(
            product_id=payload.product_id,
            title=payload.title,
            script=payload.script,
         **_scope_kwargs(scope))
        return {"success": True, "angle": angle}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except (HTTPException, ChannelError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upload-video")
async def upload_mobile_video(
    product_id: str = Form(...),
    angle_id: str = Form(...),
    file: UploadFile = File(...), scope: ChannelScope = Depends(get_workflow_scope)):
    """Directly uploads and binds camera roll footage to a product angle."""
    _guard_write(scope, new_work=False)
    try:
        content = await file.read()
        res = MobileQuickStudioService.upload_mobile_video(
            product_id=product_id,
            angle_id=angle_id,
            file_bytes=content,
            filename=file.filename or "video.mp4"
        , **_scope_kwargs(scope))
        return res
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except (HTTPException, ChannelError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/products/quick-add")
def quick_add_product(payload: QuickAddProductPayload, scope: ChannelScope = Depends(get_workflow_scope)):
    """Creates a product and initial angle from name or TikTok Shop link."""
    _guard_write(scope, new_work=True)
    try:
        product = MobileQuickStudioService.quick_add_product(payload.name_or_url, **_scope_kwargs(scope))
        return {"success": True, "product": product}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except (HTTPException, ChannelError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/preview-voice")
def preview_mobile_voice(payload: MobileVoicePreviewPayload, request: Request = None):
    """Generates a quick 5-second voice audition sample for the script."""
    try:
        from scripts.api_voice import preview_voice
        req = VoicePreviewRequest(
            text=payload.text[:120],
            voice_gender=payload.voice or "gemini_fenrir_male_strong",
            speed=1.15,
            ad_tone="commercial_premium"
        )
        return preview_voice(req, **({"request": request} if request is not None else {}))
    except (HTTPException, ChannelError):
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
