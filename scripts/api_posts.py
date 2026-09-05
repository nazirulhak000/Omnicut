"""
API Router for Post Log and Performance Tracking.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from scripts.post_log import PostLog

router = APIRouter(tags=["PostLog"])


@router.get("/api/post-log")
def get_post_log(newest_first: bool = True):
    """Returns all posted clips with their recorded metrics."""
    posts = PostLog.list_posts(newest_first=newest_first)
    return {"posts": posts, "count": len(posts), "summary": PostLog.summary()}


@router.post("/api/post-log")
def add_post_log(payload: Dict[str, Any]):
    """Records that a clip went live on TikTok (or other platform)."""
    try:
        post = PostLog.add_post(
            product_name=payload.get("product_name", ""),
            clip_file=payload.get("clip_file", ""),
            platform=payload.get("platform", "tiktok"),
            product_url=payload.get("product_url", ""),
            angle_key=payload.get("angle_key", ""),
            angle_title=payload.get("angle_title", ""),
            hook=payload.get("hook", ""),
            caption=payload.get("caption", ""),
            hashtags=payload.get("hashtags"),
            posted_at=payload.get("posted_at"),
        )
        return {"success": True, "post": post, "summary": PostLog.summary()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/api/post-log/{post_id}/metrics")
@router.post("/api/post-log/{post_id}/metrics")
@router.patch("/api/posts/{post_id}/metrics")
def update_post_log_metrics(post_id: str, payload: Dict[str, Any]):
    """Fills in the 48-hour performance numbers for a post."""
    try:
        post = PostLog.update_metrics(post_id, payload)
        return {"success": True, "post": post, "summary": PostLog.summary()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/post-log/pending")
def get_pending_metrics():
    """Returns posts that are past 48 h but still have no performance numbers filled in."""
    pending = PostLog.pending_metrics()
    return {"pending": pending, "count": len(pending)}


@router.get("/api/post-log/performance")
def get_angle_performance():
    """Returns average views, cart-click-rate, and commission grouped by angle key."""
    return {"by_angle": PostLog.angle_performance(), "summary": PostLog.summary()}


@router.get("/api/posts/summary")
@router.get("/api/post-log/summary")
def get_post_log_summary():
    """Returns overall totals: clips posted, measured, total views, orders, commission."""
    return PostLog.summary()
