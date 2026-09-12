"""TikTok Studio stats import — local-only receiver for the extension.

The Chrome extension (tiktok_autopost_extension/) reads the Studio Posts
table in the user's own logged-in browser and POSTs the parsed rows here.
No TikTok API, no cloud, no OAuth — the numbers were already on screen.

Request rows come from stats_parser.js: title, posted_text, privacy,
views, likes, comments, shares, duration_sec, thumbnail, video_url,
video_id. Matching/merging lives in PostLog.upsert_tiktok_stats.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scripts.post_log import PostLog
from scripts.product_store import ProductStore
from scripts.tiktok_pending import TikTokPending

router = APIRouter(prefix="/api/tiktok-stats", tags=["tiktok-stats"])

MAX_ROWS = 200


class StatsRow(BaseModel):
    title: str = ""
    posted_text: str = ""
    privacy: str = ""
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    duration_sec: Optional[int] = None
    thumbnail: Optional[str] = None
    video_url: Optional[str] = None
    video_id: Optional[str] = None


class StatsImportRequest(BaseModel):
    rows: List[StatsRow] = Field(default_factory=list)
    synced_at: Optional[str] = None


def _clean_row(row: StatsRow) -> Dict[str, Any]:
    data = row.model_dump()
    data["title"] = str(data.get("title") or "")[:200]
    for key in ("views", "likes", "comments", "shares", "duration_sec"):
        value = data.get(key)
        if value is None:
            continue
        try:
            value = int(value)
        except (TypeError, ValueError):
            data[key] = None
            continue
        data[key] = value if value >= 0 else None
    return data


def _export_clip_candidates() -> List[Dict[str, Any]]:
    """Exported clip candidates for auto-registering posts.

    Users who post directly in TikTok Studio (without OmniCut's mark-posted
    button) have no post_log entry at all, so a stats sync has nothing to
    match against. The product store already knows every rendered angle's
    hook_title/product, which is enough to register the post on the fly.
    """
    candidates: List[Dict[str, Any]] = []
    seen = set()
    try:
        products = ProductStore.get_all()
    except Exception as store_err:  # store missing/corrupt must not break sync
        print(f"[api_tiktok_stats] WARNING: could not load products for candidates: {store_err}")
        return candidates
    for p in products:
        product_name = str(p.get("name") or p.get("product_name") or "")
        for a in (p.get("angles") or []):
            hook = str(a.get("hook_title") or "")
            video_url = str(a.get("video_url") or "")
            clip_file = Path(video_url).name if video_url else str(a.get("clip_file") or "")
            key = (hook.lower(), clip_file.lower())
            if key in seen or (not hook and not clip_file):
                continue
            seen.add(key)
            candidates.append({
                "hook_title": hook,
                "product_name": product_name,
                "angle_title": str(a.get("angle_title") or hook),
                "angle_key": str(a.get("angle_id") or a.get("id") or ""),
                "clip_file": clip_file or "clip.mp4",
                "duration_sec": a.get("duration_sec"),
            })
    return candidates


@router.post("/import")
def import_stats(payload: StatsImportRequest) -> Dict[str, Any]:
    """Merge extension-scraped Studio rows into the post log."""
    if len(payload.rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"ส่งได้ครั้งละไม่เกิน {MAX_ROWS} แถว (ได้ {len(payload.rows)})")
    rows = [_clean_row(r) for r in payload.rows]
    rows = [r for r in rows if r.get("title") or r.get("video_id")]
    if not rows:
        raise HTTPException(status_code=400, detail="ไม่มีแถวที่ใช้ได้ — เปิดหน้า TikTok Studio แท็บ โพสต์ ก่อนกดซิงก์")
    result = PostLog.upsert_tiktok_stats(rows, register_missing=True, clip_candidates=_export_clip_candidates())
    result["synced_at"] = payload.synced_at or datetime.now().isoformat(timespec="seconds")
    # Persist unmatched rows so the Performance tab can hand-match them
    # later -- the side panel's response is gone once the browser closes.
    unmatched_vids = {u.get("video_id") for u in (result.get("unmatched") or []) if u.get("video_id")}
    matched_vids = [r.get("video_id") for r in rows if r.get("video_id") and r.get("video_id") not in unmatched_vids]
    TikTokPending.replace_from_sync(result.get("unmatched") or [], result["synced_at"])
    TikTokPending.remove_video_ids(matched_vids)
    result["pending_count"] = len(TikTokPending.list_rows())
    result["summary"] = PostLog.summary()
    return result


@router.get("/latest")
def latest_stats() -> Dict[str, Any]:
    """Posts that already carry TikTok numbers, newest sync first."""
    posts = PostLog.list_posts(newest_first=True)
    synced = [p for p in posts if p.get("tiktok_synced_at") or p.get("tiktok_video_id") or (p.get("metrics") and p.get("metrics_filled_at"))]
    synced.sort(key=lambda p: p.get("tiktok_synced_at") or p.get("metrics_filled_at") or "", reverse=True)
    return {"posts": synced, "count": len(synced), "summary": PostLog.summary()}


class AttachRequest(BaseModel):
    pending_id: str
    post_id: Optional[str] = None
    candidate: Optional[Dict[str, Any]] = None


class IgnoreRequest(BaseModel):
    pending_id: str


@router.get("/pending")
def list_pending() -> Dict[str, Any]:
    """Studio rows auto-matching could not place -- for manual matching."""
    rows = TikTokPending.list_rows()
    return {"rows": rows, "count": len(rows)}


@router.get("/clip-candidates")
def list_clip_candidates() -> Dict[str, Any]:
    """Library clips (from the product store) the user can attach a row to."""
    return {"candidates": _export_clip_candidates()}


@router.post("/attach")
def attach_pending(payload: AttachRequest) -> Dict[str, Any]:
    """Hand-match one pending row: to an existing post (post_id) or to a
    library clip (candidate -> attach-or-register)."""
    try:
        row = TikTokPending.get(payload.pending_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if payload.post_id is None and payload.candidate is None:
        raise HTTPException(status_code=400, detail="ต้องเลือกโพสต์หรือคลิปในคลังก่อนจับคู่")
    try:
        PostLog.attach_manual(row, post_id=payload.post_id, candidate=payload.candidate)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    TikTokPending.remove(payload.pending_id)
    return {
        "attached": True,
        "remaining": len(TikTokPending.list_rows()),
        "summary": PostLog.summary(),
    }


@router.post("/pending/ignore")
def ignore_pending(payload: IgnoreRequest) -> Dict[str, Any]:
    """Row is not one of ours (someone else's clip / irrelevant) -- drop it."""
    try:
        TikTokPending.get(payload.pending_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    TikTokPending.remove(payload.pending_id)
    return {"ignored": True, "remaining": len(TikTokPending.list_rows())}
