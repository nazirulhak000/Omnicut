"""
API Router for Post Log and Performance Tracking.

Channel-scoped (multi-channel P2.2, ADR §7.1 + §12/§13): every route reads
or writes the request channel's posts only; a post id of another channel is
404 ``resource_not_found``; new posts are stamped with the request channel
(a conflicting body ``channel_id`` is rejected with 422).
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException

from scripts.channel_ownership import reject_foreign_body_channel
from scripts.channel_scope import ChannelScope, get_channel_scope, require_active_for_new_work
from scripts.channel_store import ChannelError
from scripts.post_log import PostLog

router = APIRouter(tags=["PostLog"])


def _channel_of(scope: Any) -> Optional[str]:
    """Request channel; ``None`` when called directly (compat unscoped)."""
    return scope.channel_id if isinstance(scope, ChannelScope) else None


def _kw(channel_id: Optional[str]) -> Dict[str, Any]:
    return {} if channel_id is None else {"channel_id": channel_id}


@router.get("/api/post-log")
def get_post_log(newest_first: bool = True, scope: ChannelScope = Depends(get_channel_scope)):
    """Returns all posted clips with their recorded metrics."""
    kw = _kw(_channel_of(scope))
    posts = PostLog.list_posts(newest_first=newest_first, **kw)
    return {"posts": posts, "count": len(posts), "summary": PostLog.summary(**kw)}


@router.post("/api/post-log")
def add_post_log(payload: Dict[str, Any], scope: ChannelScope = Depends(get_channel_scope)):
    """Records that a clip went live on TikTok (or other platform)."""
    channel_id = _channel_of(scope)
    if channel_id is not None:
        reject_foreign_body_channel(payload, channel_id)
        if not scope.is_implicit_default:
            # Recording a new post = new work for the channel (draft/archived -> 409).
            require_active_for_new_work(scope)
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
            **_kw(channel_id),
        )
        return {"success": True, "post": post, "summary": PostLog.summary(**_kw(channel_id))}
    except ChannelError:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/api/post-log/{post_id}/metrics")
@router.post("/api/post-log/{post_id}/metrics")
@router.patch("/api/posts/{post_id}/metrics")
def update_post_log_metrics(post_id: str, payload: Dict[str, Any], scope: ChannelScope = Depends(get_channel_scope)):
    """Fills in the 48-hour performance numbers for a post.

    Allowed for an archived channel too (recording results of posts that
    already happened, ADR §10.4)."""
    channel_id = _channel_of(scope)
    try:
        post = PostLog.update_metrics(post_id, payload, **_kw(channel_id))
        return {"success": True, "post": post, "summary": PostLog.summary(**_kw(channel_id))}
    except ValueError as e:
        # The scoped write never touched another channel's post; if the id
        # exists only outside this channel, answer like it does not exist.
        if channel_id is not None and PostLog.owner_of(post_id)[0] and not any(
            p.get("id") == post_id for p in PostLog.list_posts(channel_id=channel_id)
        ):
            raise ChannelError(404, "resource_not_found", "ไม่พบโพสต์ที่ร้องขอ")
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/post-log/pending")
def get_pending_metrics(scope: ChannelScope = Depends(get_channel_scope)):
    """Returns posts that are past 48 h but still have no performance numbers filled in."""
    pending = PostLog.pending_metrics(**_kw(_channel_of(scope)))
    return {"pending": pending, "count": len(pending)}


@router.get("/api/post-log/performance")
def get_angle_performance(scope: ChannelScope = Depends(get_channel_scope)):
    """Returns average views, cart-click-rate, and commission grouped by angle key."""
    kw = _kw(_channel_of(scope))
    return {"by_angle": PostLog.angle_performance(**kw), "summary": PostLog.summary(**kw)}


@router.get("/api/posts/summary")
@router.get("/api/post-log/summary")
def get_post_log_summary(scope: ChannelScope = Depends(get_channel_scope)):
    """Returns overall totals: clips posted, measured, total views, orders, commission."""
    return PostLog.summary(**_kw(_channel_of(scope)))
