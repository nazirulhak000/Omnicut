"""
FastAPI Router for Batch Video Render Queue.
Enables 1-click batch rendering of multiple script angles for a product.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scripts.batch_render import BatchRenderManager

router = APIRouter(prefix="/api/render/batch", tags=["batch-render"])


class BatchRenderRequest(BaseModel):
    product_id: str = Field(..., description="ID of the product whose angles will be rendered")
    angle_ids: Optional[List[str]] = Field(None, description="Specific angle IDs to render. If omitted, all eligible angles are rendered.")
    batch_index: Optional[int] = Field(None, description="Specific batch index (e.g. 1, 2) to render")
    voice_gender: str = "female"
    voice_rate: str = "+15%"
    voice_mode: str = "gemini_tts"
    voice_preset: str = "gemini_fenrir_male_strong"
    style_preset: str = "clean_tech_review"
    font_name: str = "IBMPlex"
    bilingual_subtitles: bool = True
    use_ai_vision: bool = True
    export_mp4: bool = True
    project_name: Optional[str] = None
    angle_project_names: Optional[Dict[str, str]] = None


@router.post("")
def start_batch_render(req: BatchRenderRequest) -> Dict[str, Any]:
    """Starts a background batch rendering job for multiple angles of a product."""
    try:
        options = {
            "voice_gender": req.voice_gender,
            "voice_rate": req.voice_rate,
            "voice_mode": req.voice_mode,
            "voice_preset": req.voice_preset,
            "style_preset": req.style_preset,
            "font_name": req.font_name,
            "bilingual_subtitles": req.bilingual_subtitles,
            "use_ai_vision": req.use_ai_vision,
            "export_mp4": req.export_mp4,
            "project_name": req.project_name,
            "angle_project_names": req.angle_project_names or {},
            "batch_index": req.batch_index,
        }
        res = BatchRenderManager.create_batch(
            product_id=req.product_id,
            angle_ids=req.angle_ids,
            options=options,
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=507, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการเริ่มคิวเรนเดอร์: {e}")


@router.get("/{batch_id}")
def get_batch_render_status(batch_id: str) -> Dict[str, Any]:
    """Returns the current progress, status, and item details of a batch render."""
    batch = BatchRenderManager.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="ไม่พบคิวเรนเดอร์ชุดนี้")
    return batch


@router.post("/{batch_id}/cancel")
def cancel_batch_render(batch_id: str) -> Dict[str, Any]:
    """Cancels an in-progress or queued batch render job."""
    success = BatchRenderManager.cancel_batch(batch_id)
    if not success:
        raise HTTPException(status_code=404, detail="ไม่พบคิวเรนเดอร์ชุดนี้")
    return {"batch_id": batch_id, "status": "cancelled"}
