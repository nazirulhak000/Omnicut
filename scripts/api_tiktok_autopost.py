"""
Round POST-2: hand-off point between the app's Post Studio panel and the
TikTok Auto-Post Chrome extension (tiktok_autopost_extension/).

The app can't message the extension directly (no externally_connectable
pairing, since an unpacked extension's id is unstable across machines) --
instead this module holds ONE "pending" job in memory. The app POSTs here
when the user clicks "โพสต์ TikTok อัตโนมัติ"; the extension's popup GETs it
when the user clicks the extension icon on a real, already-logged-in TikTok
Studio upload tab and does the actual chrome.debugger work from there. See
TIKTOK_AUTOPOST_PLAN.md for why it has to be debugger-based at all, and why
the browser step (attach/DOM.setFileInputFiles/detach) cannot happen here.

In-memory, single job at a time, by design: this is a local single-user tool
run by one person clicking one button at a time, not a queue.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.config import BASE_DIR, EXPORTS_DIR

POSTED_DIR = BASE_DIR / "04_Exports" / "Posted"
COVERS_DIR = BASE_DIR / "05_Covers_Thumbnails"

router = APIRouter(prefix="/api/tiktok-autopost", tags=["tiktok-autopost"])

_pending: Optional[dict] = None


def _resolve_under(raw_path: str, allowed_roots) -> Path:
    p = Path(raw_path)
    if not p.is_absolute():
        p = BASE_DIR / raw_path
    p = p.resolve()
    if not any(str(p).startswith(str(root.resolve())) for root in allowed_roots):
        raise HTTPException(status_code=403, detail=f"ไฟล์นี้ไม่ได้อยู่ในโฟลเดอร์ที่อนุญาต: {raw_path}")
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {raw_path}")
    return p


class PrepareRequest(BaseModel):
    video_path: str
    cover_path: Optional[str] = None
    caption: str = ""
    hashtags: str = ""
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    tiktok_product_id: Optional[str] = None
    schedule_time: Optional[str] = None


@router.post("/prepare")
def prepare(req: PrepareRequest):
    """Called by the app's Post Studio panel. Validates + resolves both
    paths to absolute OS paths (chrome.debugger's DOM.setFileInputFiles
    needs a real filesystem path, not a URL) and stashes them for the
    extension to pick up next."""
    video_abs = _resolve_under(req.video_path, [EXPORTS_DIR, POSTED_DIR])
    cover_abs = _resolve_under(req.cover_path, [COVERS_DIR]) if req.cover_path else None

    global _pending
    _pending = {
        "video_path": str(video_abs),
        "cover_path": str(cover_abs) if cover_abs else None,
        "caption": req.caption,
        "hashtags": req.hashtags,
        "product_id": req.product_id,
        "angle_id": req.angle_id,
        "tiktok_product_id": req.tiktok_product_id,
        "schedule_time": req.schedule_time,
        "prepared_at": datetime.now().isoformat(),
    }
    return {"success": True}


@router.get("/pending")
def get_pending():
    """Polled by the extension's popup/background worker. 404 means
    "nothing prepared yet" -- the extension should tell the user to click
    the app's button first rather than silently doing nothing."""
    if _pending is None:
        raise HTTPException(status_code=404, detail="ยังไม่มีคลิปที่เตรียมไว้ -- กด 'โพสต์ TikTok อัตโนมัติ' ในแอปก่อน")
    return _pending


@router.post("/clear")
def clear_pending():
    """Called by the extension once it has consumed the job (success or
    failure) so a stale job never gets replayed by mistake."""
    global _pending
    _pending = None
    return {"success": True}
