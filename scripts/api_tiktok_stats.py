"""TikTok Studio stats import — local-only receiver for the extension.

The Chrome extension (tiktok_autopost_extension/) reads the Studio Posts
table in the user's own logged-in browser and POSTs the parsed rows here.
No TikTok API, no cloud, no OAuth — the numbers were already on screen.

Request rows come from stats_parser.js: title, posted_text, privacy,
views, likes, comments, shares, duration_sec, thumbnail, video_url,
video_id -- plus optional retention columns avg_watch_time_sec and
completion_rate (TikTok Studio header variants such as "Average watch time"
/ "Watched full video" are accepted; "45%" -> 0.45). Matching/merging lives
in PostLog.upsert_tiktok_stats.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from scripts.channel_scope import ChannelScope, get_channel_scope, require_writable
from scripts.channel_store import ChannelError
from scripts.channel_workflows import api_store_kwargs
from pydantic import BaseModel, Field, model_validator

from scripts.post_log import PostLog, STYLE_GROUP_FIELDS, parse_completion_rate, parse_watch_time_sec
from scripts.product_store import ProductStore
from scripts.tiktok_pending import TikTokPending, TikTokIgnored
from scripts.posting_jobs import PostingJobStore, account_check

router = APIRouter(prefix="/api/tiktok-stats", tags=["tiktok-stats"])

MAX_ROWS = 200


def _scope_kwargs(scope):
    # Direct legacy Python callers have no request dependency. HTTP always resolves main explicitly.
    return api_store_kwargs(scope) if isinstance(scope, ChannelScope) else {}


def _guard_write(scope):
    if isinstance(scope, ChannelScope) and not scope.is_implicit_default:
        require_writable(scope)



# Header variants (TikTok Studio exports, CSV tools, Thai UI) -> canonical
# keys.  Matched after lower-casing and dropping everything but letters,
# digits and Thai characters.
_RETENTION_ALIASES = {
    "avg_watch_time_sec": (
        "avgwatchtimesec", "avgwatchtime", "averagewatchtime", "averagewatchtimesec",
        "averagewatchtimeseconds", "avgwatchtimeseconds", "averagewatchtimes", "avgwatchtimes",
        "averageviewduration", "avgviewduration", "เวลารับชมเฉลี่ย", "เวลาการรับชมเฉลี่ย",
        "ระยะเวลารับชมเฉลี่ย",
    ),
    "completion_rate": (
        "completionrate", "watchedfullvideo", "watchedfullvideorate", "watchedfullvideo%",
        "fullvideowatchedrate", "finishrate", "completion", "percentagewatchedfullvideo",
        "ดูวิดีโอจนจบ", "รับชมวิดีโอจนจบ", "ดูจนจบ", "อัตราการดูจนจบ",
    ),
}


def _header_key(key: Any) -> str:
    return re.sub(r"[^0-9a-z\u0E00-\u0E7F%]+", "", str(key).lower())


_ALIAS_LOOKUP = {alias: canonical for canonical, aliases in _RETENTION_ALIASES.items() for alias in aliases}


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
    # Optional retention columns (raw: number or Studio text such as "8.5s"
    # / "45.3%"); normalized in _clean_row. Absent -> import unchanged.
    avg_watch_time_sec: Optional[Any] = None
    completion_rate: Optional[Any] = None

    @model_validator(mode="before")
    @classmethod
    def _map_retention_headers(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        mapped = dict(data)
        for key, value in data.items():
            canonical = _ALIAS_LOOKUP.get(_header_key(key))
            if canonical and mapped.get(canonical) in (None, ""):
                mapped[canonical] = value
        return mapped


class StatsImportRequest(BaseModel):
    rows: List[StatsRow] = Field(default_factory=list)
    synced_at: Optional[str] = None
    source_account: Optional[str] = None


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
    watch = parse_watch_time_sec(data.get("avg_watch_time_sec"))
    rate = parse_completion_rate(data.get("completion_rate"))
    # Keep the row shape unchanged when the columns were not sent.
    for key, value in (("avg_watch_time_sec", watch), ("completion_rate", rate)):
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return data


def _export_clip_candidates(scope=None) -> List[Dict[str, Any]]:
    """Exported clip candidates for auto-registering posts.

    Users who post directly in TikTok Studio or via OmniCut's Schedule Queue
    have real numbers that need to match against known project clips.
    We gather candidates from:
    1. ScheduleQueueStore: durable queue records which hold exact captions,
       hashtags, and clip files as scheduled/posted to TikTok.
    2. ProductStore: all rendered/configured angles with their generated captions,
       hook titles, product names, and video exports.
    """
    candidates: List[Dict[str, Any]] = []
    seen: Dict[tuple, Dict[str, Any]] = {}

    # 1. Gather from ScheduleQueueStore (exact captions and hashtags sent to TikTok)
    try:
        from scripts.schedule_store import ScheduleQueueStore
        # Candidate matching must use the importing account's request channel.
        for q in ScheduleQueueStore.list_items(**_scope_kwargs(scope)):
            caption = str(q.get("caption") or "").strip()
            hook = str(q.get("hook_title") or "").strip()
            product_name = str(q.get("product_name") or "").strip()
            video_path = str(q.get("video_path") or "").strip()
            clip_file = Path(video_path).name if video_path else ""
            hashtags = str(q.get("hashtags") or "").strip()
            project_name = str(q.get("project_name") or "").strip()
            angle_id = str(q.get("angle_id") or "").strip()

            if not caption and not hook and not clip_file:
                continue

            key = (clip_file.lower() if clip_file else "", hook.lower() if hook else caption[:40].lower())
            item = {
                "hook_title": hook or caption[:80],
                "product_name": product_name,
                "angle_title": hook or caption[:50] or project_name,
                "angle_key": angle_id,
                "clip_file": clip_file or "clip.mp4",
                "caption": caption,
                "hashtags": hashtags,
                "project_name": project_name,
                "duration_sec": None,
                "source": "schedule_queue",
            }
            seen[key] = item
            candidates.append(item)
    except ChannelError:
        raise
    except Exception as q_err:
        print(f"[api_tiktok_stats] WARNING: could not load schedule queue for candidates: {q_err}")

    # 2. Gather from ProductStore
    try:
        products = ProductStore.get_all(**_scope_kwargs(scope))
    except ChannelError:
        raise
    except Exception as store_err:  # store missing/corrupt must not break sync
        print(f"[api_tiktok_stats] WARNING: could not load products for candidates: {store_err}")
        return candidates

    for p in products:
        product_name = str(p.get("name") or p.get("product_name") or "").strip()
        for a in (p.get("angles") or []):
            hook = str(a.get("hook_title") or "").strip()
            caption = str(a.get("tiktok_caption") or a.get("caption") or "").strip()
            hashtags = str(a.get("tiktok_hashtags") or a.get("hashtags") or "").strip()
            video_url = str(a.get("video_url") or "").strip()
            clip_file = Path(video_url).name if video_url else str(a.get("clip_file") or "").strip()
            angle_title = str(a.get("angle_name") or a.get("angle_title") or hook).strip()
            angle_key = str(a.get("angle_id") or a.get("id") or "").strip()
            project_name = str(a.get("project_name") or "").strip()
            hook_brand = str(a.get("hook_brand") or "").strip()
            hook_model = str(a.get("hook_model") or "").strip()
            duration_sec = a.get("duration_sec")

            if not hook and not clip_file and not caption:
                continue

            key = (clip_file.lower() if clip_file else "", hook.lower() if hook else caption[:40].lower())
            existing = seen.get(key)
            if existing:
                if not existing.get("caption") and caption:
                    existing["caption"] = caption
                if not existing.get("hashtags") and hashtags:
                    existing["hashtags"] = hashtags
                if not existing.get("hook_brand") and hook_brand:
                    existing["hook_brand"] = hook_brand
                if not existing.get("hook_model") and hook_model:
                    existing["hook_model"] = hook_model
                if existing.get("duration_sec") is None and duration_sec is not None:
                    existing["duration_sec"] = duration_sec
                continue

            item = {
                "hook_title": hook or caption[:80],
                "product_name": product_name,
                "angle_title": angle_title,
                "angle_key": angle_key,
                "clip_file": clip_file or "clip.mp4",
                "caption": caption,
                "hashtags": hashtags,
                "project_name": project_name,
                "hook_brand": hook_brand,
                "hook_model": hook_model,
                "duration_sec": duration_sec,
                "source": "product_store",
            }
            seen[key] = item
            candidates.append(item)

    return candidates


@router.post("/import")
def import_stats(payload: StatsImportRequest, scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Merge extension-scraped Studio rows into the post log."""
    _guard_write(scope)
    check = None
    if isinstance(scope, ChannelScope):
        check = account_check(scope.channel_id, scope.channel.get("handle") or "", payload.source_account, strict=scope.strict, allow_unknown=True)
        binding = scope.channel.get("account_binding") or {}
        if scope.channel_id != "main" or scope.strict:
            if binding.get("status") != "verified" or binding.get("verified_handle") != check["source_account"]:
                raise ChannelError(409, "account_binding_unverified", "บัญชีที่ซิงก์ยังไม่ตรงกับ account binding ของช่อง")
        PostingJobStore().account_audit(scope.channel_id, "stats_source_account", check)
    if len(payload.rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"ส่งได้ครั้งละไม่เกิน {MAX_ROWS} แถว (ได้ {len(payload.rows)})")
    rows = [_clean_row(r) for r in payload.rows]
    if check is not None and check["account_verified"]:
        rows = [{**row, "source_account": check["source_account"], "account_unverified": False} for row in rows]
    rows = [r for r in rows if r.get("title") or r.get("video_id")]
    if not rows:
        raise HTTPException(status_code=400, detail="ไม่มีแถวที่ใช้ได้ — เปิดหน้า TikTok Studio แท็บ โพสต์ ก่อนกดซิงก์")
    if check is not None and not check["account_verified"]:
        synced_at = payload.synced_at or datetime.now().isoformat(timespec="seconds")
        quarantined = [{**row, "account_unverified": True, "source_account": None} for row in rows]
        TikTokPending.replace_from_sync(quarantined, synced_at, **_scope_kwargs(scope))
        return {"total": len(rows), "matched": 0, "updated": 0, "registered": 0, "unmatched": quarantined,
                "synced_at": synced_at, "pending_count": len(TikTokPending.list_rows(**_scope_kwargs(scope))),
                "summary": PostLog.summary(**_scope_kwargs(scope)), "account_check": check}
    result = PostLog.upsert_tiktok_stats(rows, register_missing=True, clip_candidates=_export_clip_candidates(scope), **_scope_kwargs(scope))
    result["synced_at"] = payload.synced_at or datetime.now().isoformat(timespec="seconds")
    # Persist unmatched rows so the Performance tab can hand-match them
    # later -- the side panel's response is gone once the browser closes.
    unmatched_vids = {u.get("video_id") for u in (result.get("unmatched") or []) if u.get("video_id")}
    matched_vids = [r.get("video_id") for r in rows if r.get("video_id") and r.get("video_id") not in unmatched_vids]
    TikTokPending.replace_from_sync(result.get("unmatched") or [], result["synced_at"], **_scope_kwargs(scope))
    TikTokPending.remove_video_ids(matched_vids, **_scope_kwargs(scope))
    result["pending_count"] = len(TikTokPending.list_rows(**_scope_kwargs(scope)))
    result["summary"] = PostLog.summary(**_scope_kwargs(scope))
    if check is not None:
        result["account_check"] = check
    return result


@router.get("/latest")
def latest_stats(scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Posts that already carry TikTok numbers, newest sync first."""
    posts = PostLog.list_posts(newest_first=True, **_scope_kwargs(scope))
    synced = [p for p in posts if p.get("tiktok_synced_at") or p.get("tiktok_video_id") or (p.get("metrics") and p.get("metrics_filled_at"))]
    synced.sort(key=lambda p: p.get("tiktok_synced_at") or p.get("metrics_filled_at") or "", reverse=True)
    return {"posts": synced, "count": len(synced), "summary": PostLog.summary(**_scope_kwargs(scope))}


class AttachRequest(BaseModel):
    pending_id: str
    post_id: Optional[str] = None
    candidate: Optional[Dict[str, Any]] = None


class IgnoreRequest(BaseModel):
    pending_id: str


class RestoreRequest(BaseModel):
    ignored_id: str


@router.get("/pending")
def list_pending(scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Studio rows auto-matching could not place -- for manual matching."""
    rows = TikTokPending.list_rows(**_scope_kwargs(scope))
    return {
        "rows": rows,
        "count": len(rows),
        "ignored_count": len(TikTokIgnored.list_rows(**_scope_kwargs(scope))),
    }


@router.get("/clip-candidates")
def list_clip_candidates(scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Library clips (from the product store) the user can attach a row to."""
    return {"candidates": _export_clip_candidates(scope)}


@router.post("/attach")
def attach_pending(payload: AttachRequest, scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Hand-match one pending row: to an existing post (post_id) or to a
    library clip (candidate -> attach-or-register)."""
    _guard_write(scope)
    try:
        row = TikTokPending.get(payload.pending_id, **_scope_kwargs(scope))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if row.get("account_unverified"):
        raise ChannelError(409, "source_account_required", "รายการนี้ยังไม่ทราบบัญชี ต้องซิงก์จากบัญชีที่ยืนยันได้ก่อนจับคู่")
    if payload.post_id is None and payload.candidate is None:
        raise HTTPException(status_code=400, detail="ต้องเลือกโพสต์หรือคลิปในคลังก่อนจับคู่")
    candidate = payload.candidate
    if candidate is not None and isinstance(scope, ChannelScope):
        # Resolve the client's selection back to a server-owned candidate. Never trust metadata from another channel.
        matches = [item for item in _export_clip_candidates(scope)
                   if item.get("clip_file") == candidate.get("clip_file")
                   and item.get("angle_key") == candidate.get("angle_key")
                   and item.get("project_name") == candidate.get("project_name")]
        if len(matches) != 1:
            raise ChannelError(404, "resource_not_found", "ไม่พบคลิปที่ร้องขอ")
        candidate = matches[0]
    try:
        PostLog.attach_manual(row, post_id=payload.post_id, candidate=candidate, **_scope_kwargs(scope))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    TikTokPending.remove(payload.pending_id, **_scope_kwargs(scope))
    return {
        "attached": True,
        "remaining": len(TikTokPending.list_rows(**_scope_kwargs(scope))),
        "summary": PostLog.summary(**_scope_kwargs(scope)),
    }


@router.post("/pending/ignore")
def ignore_pending(payload: IgnoreRequest, scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Row is not one of ours (someone else's clip / irrelevant) -- drop it and permanently record as ignored."""
    _guard_write(scope)
    try:
        ignored_entry = TikTokPending.ignore(payload.pending_id, **_scope_kwargs(scope))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "ignored": True,
        "item": ignored_entry,
        "remaining": len(TikTokPending.list_rows(**_scope_kwargs(scope))),
        "ignored_count": len(TikTokIgnored.list_rows(**_scope_kwargs(scope))),
    }


@router.post("/pending/ignore-all")
def ignore_all_pending(scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Batch-ignore all remaining pending rows."""
    _guard_write(scope)
    count = TikTokPending.ignore_all(**_scope_kwargs(scope))
    return {
        "ignored_count": count,
        "remaining": 0,
        "total_ignored": len(TikTokIgnored.list_rows(**_scope_kwargs(scope))),
    }


@router.get("/ignored")
def list_ignored(scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """List rows that the user skipped/ignored from pending."""
    rows = TikTokIgnored.list_rows(**_scope_kwargs(scope))
    return {"rows": rows, "count": len(rows)}


@router.post("/ignored/restore")
def restore_ignored(payload: RestoreRequest, scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Move a previously ignored row back into pending."""
    _guard_write(scope)
    try:
        restored = TikTokPending.restore(payload.ignored_id, **_scope_kwargs(scope))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "restored": True,
        "item": restored,
        "remaining": len(TikTokPending.list_rows(**_scope_kwargs(scope))),
        "ignored_count": len(TikTokIgnored.list_rows(**_scope_kwargs(scope))),
    }


@router.get("/style-performance")
def style_performance(group_by: Optional[str] = None, scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """Read-only: which style_preset / hook_style / story_format performs.

    Only mature (>= 48h) metrics count. Per group: count, median_views,
    avg_watch_time_sec, completion_rate (None when no post has the metric).
    ``group_by`` limits the answer to one dimension; omitted -> all three.
    """
    if group_by is not None and group_by not in STYLE_GROUP_FIELDS:
        raise HTTPException(status_code=400, detail=f"group_by ต้องเป็นหนึ่งใน {', '.join(STYLE_GROUP_FIELDS)}")
    report = PostLog.style_performance_report(**_scope_kwargs(scope))
    if group_by is not None:
        return {"group_by": group_by, "measured": report["measured"], "groups": report[f"by_{group_by}"]}
    return report


@router.get("/milestones")
def get_viral_milestones(threshold: int = 1000, scope: ChannelScope = Depends(get_channel_scope)) -> Dict[str, Any]:
    """
    Returns clips that achieved viral milestones (e.g. >= 1k, 5k, 10k views).
    Includes product details, hook title, and action link to create follow-up clips.
    """
    posts = PostLog.list_posts(newest_first=True, **_scope_kwargs(scope))
    milestone_posts = []

    for p in posts:
        metrics = p.get("metrics") or {}
        views = int(metrics.get("views") or 0)
        if views >= threshold:
            # Determine highest milestone tier reached
            if views >= 50000:
                tier = "50k"
                tier_label = "ระดับเมกะไวรัล (50K+)"
            elif views >= 10000:
                tier = "10k"
                tier_label = "ระดับไวรัลปัง (10K+)"
            elif views >= 5000:
                tier = "5k"
                tier_label = "ระดับดาวเด่น (5K+)"
            else:
                tier = "1k"
                tier_label = "ระดับเติบโตน่าจับตา (1K+)"

            milestone_posts.append({
                "post_id": p.get("id"),
                "product_name": p.get("product_name") or "สินค้า",
                "angle_title": p.get("angle_title") or p.get("hook") or "ไม่มีมุมมอง",
                "hook": p.get("hook") or "",
                "views": views,
                "likes": int(metrics.get("likes") or 0),
                "comments": int(metrics.get("comments") or 0),
                "shares": int(metrics.get("shares") or 0),
                "posted_at": p.get("posted_at") or "",
                "tiktok_url": p.get("tiktok_url") or "",
                "tier": tier,
                "tier_label": tier_label,
            })

    # Sort descending by views
    milestone_posts.sort(key=lambda x: x["views"], reverse=True)

    return {
        "milestones": milestone_posts,
        "count": len(milestone_posts),
        "threshold": threshold,
        "has_viral": any(m["views"] >= 10000 for m in milestone_posts),
    }

