"""TikTok Studio stats import — local-only receiver for the extension.

The Chrome extension (tiktok_autopost_extension/) reads the Studio Posts
table in the user's own logged-in browser and POSTs the parsed rows here.
No TikTok API, no cloud, no OAuth — the numbers were already on screen.

Request rows come from stats_parser.js: title, posted_text, privacy,
views, likes, comments, shares, duration_sec, thumbnail, video_url,
video_id. Matching/merging lives in PostLog.upsert_tiktok_stats.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from scripts.post_log import PostLog

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


@router.post("/import")
def import_stats(payload: StatsImportRequest) -> Dict[str, Any]:
    """Merge extension-scraped Studio rows into the post log."""
    if len(payload.rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"ส่งได้ครั้งละไม่เกิน {MAX_ROWS} แถว (ได้ {len(payload.rows)})")
    rows = [_clean_row(r) for r in payload.rows]
    rows = [r for r in rows if r.get("title") or r.get("video_id")]
    if not rows:
        raise HTTPException(status_code=400, detail="ไม่มีแถวที่ใช้ได้ — เปิดหน้า TikTok Studio แท็บ โพสต์ ก่อนกดซิงก์")
    result = PostLog.upsert_tiktok_stats(rows)
    result["synced_at"] = payload.synced_at or datetime.now().isoformat(timespec="seconds")
    result["summary"] = PostLog.summary()
    return result


@router.get("/latest")
def latest_stats() -> Dict[str, Any]:
    """Posts that already carry TikTok numbers, newest sync first."""
    posts = PostLog.list_posts(newest_first=True)
    synced = [p for p in posts if p.get("tiktok_synced_at") or p.get("tiktok_video_id") or (p.get("metrics") and p.get("metrics_filled_at"))]
    synced.sort(key=lambda p: p.get("tiktok_synced_at") or p.get("metrics_filled_at") or "", reverse=True)
    return {"posts": synced, "count": len(synced), "summary": PostLog.summary()}
