"""
Phase 1 API router — AI bridge, angle catalog, and the post log.

Kept in its own router so it can be mounted with a single include_router() call
and reviewed without touching the existing endpoints.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.ai_bridge import AIBridge, ManualModeRequired
from scripts.it_angles import ANGLES_BY_KEY, catalog_for_prompt, fallback_angles
from scripts.post_log import METRIC_FIELDS, PostLog

router = APIRouter(prefix="/api", tags=["phase1"])


# ----------------------------------------------------------------------
# Request models
# ----------------------------------------------------------------------
class AIPromptRequest(BaseModel):
    task: str
    context: Dict[str, Any]


class AIParseRequest(BaseModel):
    task: str
    raw_text: str


class PostCreateRequest(BaseModel):
    product_name: str
    clip_file: str
    platform: str = "tiktok"
    product_url: str = ""
    angle_key: str = ""
    angle_title: str = ""
    hook: str = ""
    caption: str = ""
    hashtags: List[str] = []


class MetricsRequest(BaseModel):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    cart_clicks: Optional[int] = None
    orders: Optional[int] = None
    commission_thb: Optional[float] = None


# ----------------------------------------------------------------------
# AI bridge
# ----------------------------------------------------------------------
@router.post("/ai/prompt")
def ai_prompt(req: AIPromptRequest):
    """
    Run an AI task. Returns finished data when a key is configured, otherwise
    the prompt for the user to paste into their own chat.
    """
    try:
        data = AIBridge.generate(req.task, req.context)
        return {"mode": "auto", "task": req.task, "data": data}
    except ManualModeRequired as manual:
        return {"mode": "manual", "task": req.task, "prompt": manual.prompt}
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:  # SDK/network failures must not kill the panel
        try:
            prompt = AIBridge.build_prompt(req.task, req.context)
        except ValueError as build_err:
            raise HTTPException(status_code=400, detail=str(build_err))
        return {
            "mode": "manual",
            "task": req.task,
            "prompt": prompt,
            "warning": f"เรียก AI อัตโนมัติไม่สำเร็จ ใช้โหมดวางเองแทน ({err})",
        }


@router.post("/ai/parse")
def ai_parse(req: AIParseRequest):
    """Turn a pasted answer into validated data."""
    try:
        return {"task": req.task, "data": AIBridge.parse_response(req.task, req.raw_text)}
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get("/ai/status")
def ai_status():
    return {
        "mode": "auto" if AIBridge.has_api_key() else "manual",
        "tasks": {key: spec["label"] for key, spec in AIBridge.TASKS.items()},
    }


# ----------------------------------------------------------------------
# Angle catalog
# ----------------------------------------------------------------------
@router.get("/angles")
def get_angles(seller_assets_only: bool = False, product_name: str = ""):
    """Angle catalog for IT products, plus no-LLM fallback angles."""
    return {
        "catalog": catalog_for_prompt(seller_assets_only=seller_assets_only),
        "fallback": fallback_angles(product_name or "สินค้านี้", seller_assets_only=seller_assets_only),
        "total": len(ANGLES_BY_KEY),
    }


# ----------------------------------------------------------------------
# Post log
# ----------------------------------------------------------------------
@router.get("/posts")
def get_posts():
    return {
        "posts": PostLog.list_posts(),
        "summary": PostLog.summary(),
        "pending_metrics": PostLog.pending_metrics(),
        "metric_fields": list(METRIC_FIELDS),
    }


@router.post("/posts")
def create_post(req: PostCreateRequest):
    """Record that a clip went live."""
    if not req.product_name.strip():
        raise HTTPException(status_code=400, detail="ต้องระบุชื่อสินค้า")
    if not req.clip_file.strip():
        raise HTTPException(status_code=400, detail="ต้องระบุไฟล์คลิปที่โพสต์")

    post = PostLog.add_post(
        product_name=req.product_name,
        clip_file=req.clip_file,
        platform=req.platform,
        product_url=req.product_url,
        angle_key=req.angle_key,
        angle_title=req.angle_title,
        hook=req.hook,
        caption=req.caption,
        hashtags=req.hashtags,
    )
    return {"success": True, "post": post, "summary": PostLog.summary()}


@router.post("/posts/{post_id}/metrics")
def set_metrics(post_id: str, req: MetricsRequest):
    """Fill in the 48-hour numbers."""
    try:
        post = PostLog.update_metrics(post_id, req.model_dump(exclude_none=True))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    return {"success": True, "post": post, "summary": PostLog.summary()}


@router.get("/posts/performance")
def get_performance():
    """Which angles actually earn — empty until metrics have been filled in."""
    return {"by_angle": PostLog.angle_performance(), "summary": PostLog.summary()}
