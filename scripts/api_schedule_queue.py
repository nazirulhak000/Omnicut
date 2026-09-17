"""Persistent, multi-day publishing queue used by the Daily Agenda UI."""

from __future__ import annotations

import datetime as dt
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from scripts.api_tiktok_autopost import PrepareRequest, prepare
from scripts.config import BASE_DIR, EXPORTS_DIR
from scripts.export_registry import ExportRegistry, _normalise_path as _export_normalise_path
from scripts.post_log import PostLog
from scripts.schedule_store import ScheduleQueueStore, ScheduleTemplateStore, new_id, now_iso
from scripts.style_motion_policy import resolve_style_motion_policy

POSTED_DIR = EXPORTS_DIR.parent / "Posted"
PROJECT_TZ = ZoneInfo("Asia/Bangkok")
DEFAULT_PRIMARY_TIMES = ("09:00", "12:30", "16:00", "19:00", "21:30")
OLD_DEFAULT_PRIMARY_TIMES = ("12:30", "19:00", "21:30")
LEGACY_PRIMARY_TIMES = ("07:00", "10:00", "12:00", "16:00", "20:00")
MAX_TEMPLATE_TIMES = 24
DAY_INDICES = tuple(range(7))
ACTIVE_STATUSES = {"planned", "ready_for_extension", "awaiting_post", "failed"}
ALL_STATUSES = ACTIVE_STATUSES | {"posted"}
STATUS_LABELS = {
    "planned": "รอจัดส่ง",
    "ready_for_extension": "พร้อมทำใน Extension",
    "awaiting_post": "รอกดโพสต์",
    "posted": "โพสต์แล้ว",
    "failed": "ผิดพลาด",
}

router = APIRouter(prefix="/api/schedule-queue", tags=["schedule-queue"])


class QueueItemPayload(BaseModel):
    video_path: str
    scheduled_at: str
    export_id: Optional[str] = None
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    product_name: Optional[str] = None
    project_name: Optional[str] = None
    hook_title: Optional[str] = None
    style_preset: Optional[str] = None
    hook_color: Optional[str] = None
    cover_path: Optional[str] = None
    cover_url: Optional[str] = None
    caption: str = ""
    hashtags: str = ""
    tiktok_product_id: Optional[str] = None


class QueueCreateRequest(BaseModel):
    video_path: Optional[str] = None
    scheduled_at: Optional[str] = None
    export_id: Optional[str] = None
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    product_name: Optional[str] = None
    project_name: Optional[str] = None
    hook_title: Optional[str] = None
    style_preset: Optional[str] = None
    hook_color: Optional[str] = None
    cover_path: Optional[str] = None
    cover_url: Optional[str] = None
    caption: str = ""
    hashtags: str = ""
    tiktok_product_id: Optional[str] = None
    items: List[QueueItemPayload] = Field(default_factory=list)


class QueuePatchRequest(BaseModel):
    scheduled_at: Optional[str] = None
    status: Optional[str] = None

    @field_validator("status")
    def valid_status(cls, value):
        if value not in ALL_STATUSES:
            raise ValueError(f"สถานะไม่ถูกต้อง: {value}")
        return value


class ScheduleDayPayload(BaseModel):
    enabled: bool = True
    times: List[str] = Field(default_factory=lambda: list(DEFAULT_PRIMARY_TIMES))


class ScheduleTemplatePayload(BaseModel):
    week_start: Optional[str] = None
    days: Dict[str, ScheduleDayPayload] = Field(default_factory=dict)


class TemplateCopyRequest(BaseModel):
    source_week_start: Optional[str] = None
    target_week_start: str


class AutoFillClipPayload(BaseModel):
    video_path: str
    export_id: Optional[str] = None
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    product_name: Optional[str] = None
    project_name: Optional[str] = None
    hook_title: Optional[str] = None
    style_preset: Optional[str] = None
    hook_color: Optional[str] = None
    cover_path: Optional[str] = None
    cover_url: Optional[str] = None
    caption: str = ""
    hashtags: str = ""
    tiktok_product_id: Optional[str] = None


class AutoFillRequest(BaseModel):
    start_date: str
    end_date: str
    clips: List[AutoFillClipPayload] = Field(default_factory=list)
    template_week_start: Optional[str] = None
    enabled_days: Optional[List[int]] = None
    product_ids: List[str] = Field(default_factory=list)
    limit: Optional[int] = Field(default=None, ge=1, le=10000)
    seed: Optional[int] = None
    optimize_by_stats: bool = False


class AutoFillCommitRequest(BaseModel):
    items: List[QueueItemPayload] = Field(default_factory=list)


def _date_value(raw: str, *, field: str = "วันที่") -> dt.date:
    try:
        return dt.date.fromisoformat(str(raw or ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field}ต้องเป็นรูปแบบ YYYY-MM-DD") from exc


def _monday(value: dt.date) -> dt.date:
    return value - dt.timedelta(days=value.weekday())


def _week_key(raw: Optional[str]) -> Optional[str]:
    if raw in (None, "", "default"):
        return None
    value = _date_value(raw, field="week_start")
    if value.weekday() != 0:
        raise HTTPException(status_code=422, detail="week_start ต้องเป็นวันจันทร์")
    return value.isoformat()


def _valid_time(value: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
        raise HTTPException(status_code=422, detail=f"เวลาไม่ถูกต้อง: {value}")
    if int(text[3:]) % 5:
        raise HTTPException(status_code=422, detail="เวลาหลักต้องเป็นรอบละ 5 นาที")
    return text


def _normalise_hex_color(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text.upper() if re.fullmatch(r"#[0-9A-Fa-f]{6}", text) else None


def _resolve_hook_color(style_preset: Optional[str] = None, explicit_color: Any = None) -> Optional[str]:
    """Resolve the renderer's accent token used by the Hook badge.

    The explicit color wins for custom/legacy renders. Otherwise use the same
    style policy as the video renderer so queue diversity is based on the
    color the viewer actually sees, not on a frontend-only guess.
    """
    if not str(style_preset or "").strip():
        # A color without its style preset is legacy/ambiguous metadata.
        return None
    explicit = _normalise_hex_color(explicit_color)
    if explicit:
        return explicit
    return resolve_style_motion_policy(style_preset).accent_color.upper()


def _product_key(value: Any, fallback: Any = None) -> str:
    return str(value or fallback or "other").strip().casefold() or "other"


def _row_visual_key(row: Dict[str, Any]) -> Optional[str]:
    return _resolve_hook_color(row.get("style_preset"), row.get("hook_color"))


def _product_aliases(product_id: Any = None, product_name: Any = None) -> set[str]:
    aliases = {
        _product_key(value)
        for value in (product_id, product_name)
        if str(value or "").strip()
    }
    return aliases


def _clip_product_aliases(clip: AutoFillClipPayload) -> set[str]:
    return _product_aliases(clip.product_id, clip.product_name)


def _row_product_aliases(row: Dict[str, Any]) -> set[str]:
    return _product_aliases(row.get("product_id"), row.get("product_name"))


def _normalise_days(days: Dict[str, ScheduleDayPayload] | Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    for index in DAY_INDICES:
        raw = days.get(str(index), {}) if isinstance(days, dict) else {}
        if isinstance(raw, ScheduleDayPayload):
            enabled, times = raw.enabled, raw.times
        else:
            raw = raw if isinstance(raw, dict) else {}
            enabled, times = bool(raw.get("enabled", True)), raw.get("times", DEFAULT_PRIMARY_TIMES)
        if not isinstance(times, (list, tuple)):
            raise HTTPException(status_code=422, detail="ช่วงเวลาต้องเป็นรายการเวลา")
        values = [_valid_time(value) for value in times]
        if set(values) == set(LEGACY_PRIMARY_TIMES) and len(values) == len(LEGACY_PRIMARY_TIMES):
            # Keep templates saved before the three-slot schedule readable while
            # moving them to the new five-slot defaults on the next template read/save.
            values = list(DEFAULT_PRIMARY_TIMES)
        elif set(values) == set(OLD_DEFAULT_PRIMARY_TIMES) and len(values) == len(OLD_DEFAULT_PRIMARY_TIMES):
            # The old built-in three-slot default was never a meaningful custom
            # override, so promote it to the new default when it is encountered.
            values = list(DEFAULT_PRIMARY_TIMES)
        if not values or len(values) > MAX_TEMPLATE_TIMES or len(values) != len(set(values)):
            raise HTTPException(status_code=422, detail=f"แต่ละวันต้องมีเวลาไม่ซ้ำกัน 1–{MAX_TEMPLATE_TIMES} ช่วง")
        output[str(index)] = {"enabled": enabled, "times": sorted(values)}
    return output


def _default_template() -> Dict[str, Any]:
    return {
        "id": "default",
        "week_start": None,
        "timezone": "Asia/Bangkok",
        "days": {str(index): {"enabled": True, "times": list(DEFAULT_PRIMARY_TIMES)} for index in DAY_INDICES},
        "updated_at": None,
    }


def _effective_template(week_start: Optional[str]) -> Dict[str, Any]:
    key = _week_key(week_start)
    records = ScheduleTemplateStore._load()
    default = next((row for row in records if row.get("id") == "default"), None) or _default_template()
    base = dict(default)
    base["days"] = _normalise_days(default.get("days", {}))
    base["id"] = "default"
    base["week_start"] = key
    if key:
        override = next((row for row in records if row.get("id") == f"week:{key}"), None)
        if override:
            base["days"] = _normalise_days(override.get("days", {}))
            base["id"] = override.get("id", f"week:{key}")
            base["updated_at"] = override.get("updated_at")
    return base


def _template_record(week_start: Optional[str], days: Dict[str, Any]) -> Dict[str, Any]:
    key = _week_key(week_start)
    now = now_iso()
    return {
        "id": f"week:{key}" if key else "default",
        "week_start": key,
        "timezone": "Asia/Bangkok",
        "days": _normalise_days(days),
        "updated_at": now,
    }


def _contained(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_video(raw: str) -> Path:
    value = str(raw or "").strip().replace("\\", "/")
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    path = path.resolve()
    if not any(_contained(path, root) for root in (EXPORTS_DIR, POSTED_DIR)):
        raise HTTPException(status_code=403, detail="ไฟล์คิวต้องอยู่ใน 04_Exports/Ready_to_post หรือ Posted")
    if path.suffix.lower() != ".mp4":
        raise HTTPException(status_code=422, detail="คิวรองรับเฉพาะไฟล์ MP4 ที่ตัดต่อเสร็จแล้ว")
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์วิดีโอ: {raw}")
    return path


def video_key(path: Path) -> str:
    # Ready_to_post -> Posted moves must keep the same queue identity. The
    # export filename under 04_Exports is the stable identity; the directory
    # is only a lifecycle location.
    return f"{EXPORTS_DIR.parent.name}/{path.name}".replace("\\", "/").casefold()


def relative_path(path: Path) -> str:
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def parse_scheduled_at(raw: str) -> dt.datetime:
    value = str(raw or "").strip()
    if not value:
        raise HTTPException(status_code=422, detail="กรุณาระบุวันที่และเวลาโพสต์")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="รูปแบบวันที่และเวลาไม่ถูกต้อง") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=PROJECT_TZ)
    parsed = parsed.astimezone(PROJECT_TZ).replace(second=0, microsecond=0)
    if parsed.minute % 5:
        raise HTTPException(status_code=422, detail="เวลาโพสต์ต้องเป็นรอบละ 5 นาทีตาม TikTok")
    return parsed


def scheduled_iso(value: dt.datetime) -> str:
    return value.astimezone(PROJECT_TZ).isoformat(timespec="minutes")


def sort_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(records, key=lambda item: (item.get("scheduled_at", ""), item.get("created_at", ""), item.get("id", "")))


def _payload_to_record(payload: QueueItemPayload, existing_keys: set, existing_times: set) -> Dict[str, Any]:
    path = resolve_video(payload.video_path)
    export_record = ExportRegistry.get(payload.export_id) if payload.export_id else ExportRegistry.find_by_path(path)
    if payload.export_id and export_record is None:
        raise HTTPException(status_code=409, detail="ไม่พบ export_id ที่ระบุ จึงหยุดการจัดคิวเพื่อป้องกันการเลือกคลิปผิดตัว")
    export_id = export_record.get("id") if export_record else payload.export_id
    if export_record:
        registered = resolve_video(export_record.get("path"))
        if registered != path:
            raise HTTPException(status_code=409, detail="export_id ไม่ตรงกับไฟล์ที่เลือก")
        if export_record.get("status") == "posted":
            raise HTTPException(status_code=409, detail="คลิปนี้ถูกโพสต์แล้ว ไม่สามารถจัดคิวซ้ำได้")
        latest = ExportRegistry.latest_for_angle(payload.product_id, payload.angle_id)
        if latest and latest.get("id") != export_record.get("id"):
            raise HTTPException(status_code=409, detail="ไฟล์นี้ไม่ใช่ export เวอร์ชันล่าสุดของมุมนี้ กรุณาเลือกคลิปล่าสุด")
    key = f"export:{export_id}" if export_id else video_key(path)
    if key in existing_keys:
        raise HTTPException(status_code=409, detail=f"คลิปนี้อยู่ในคิวแล้ว: {path.name}")
    when = parse_scheduled_at(payload.scheduled_at)
    iso = scheduled_iso(when)
    if iso in existing_times:
        raise HTTPException(status_code=409, detail=f"มีคลิปอื่นจองเวลา {when:%d/%m/%Y %H:%M} แล้ว")
    created = now_iso()
    record = {
        "id": new_id(),
        "video_path": relative_path(path),
        "video_key": key,
        "export_id": export_id,
        "scheduled_at": iso,
        "status": "planned",
        "product_id": payload.product_id,
        "angle_id": payload.angle_id,
        "product_name": payload.product_name,
        "project_name": payload.project_name,
        "hook_title": payload.hook_title,
        "style_preset": payload.style_preset,
        "hook_color": _resolve_hook_color(payload.style_preset, payload.hook_color),
        "cover_path": payload.cover_path,
        "cover_url": payload.cover_url,
        "caption": payload.caption,
        "hashtags": payload.hashtags,
        "tiktok_product_id": payload.tiktok_product_id,
        "created_at": created,
        "updated_at": created,
        "extension_prepared_at": None,
        "posted_at": None,
    }
    existing_keys.add(key)
    existing_times.add(iso)
    return record


def _request_items(req: QueueCreateRequest) -> List[QueueItemPayload]:
    if req.items:
        return req.items
    if not req.video_path or not req.scheduled_at:
        raise HTTPException(status_code=422, detail="กรุณาระบุ video_path และ scheduled_at หรือส่ง items แบบชุด")
    return [QueueItemPayload(
        video_path=req.video_path,
        scheduled_at=req.scheduled_at,
        export_id=req.export_id,
        product_id=req.product_id,
        angle_id=req.angle_id,
        product_name=req.product_name,
        project_name=req.project_name,
        hook_title=req.hook_title,
        style_preset=req.style_preset,
        hook_color=req.hook_color,
        cover_path=req.cover_path,
        cover_url=req.cover_url,
        caption=req.caption,
        hashtags=req.hashtags,
        tiktok_product_id=req.tiktok_product_id,
    )]


def _template_for_date(day: dt.date, template_week_start: Optional[str] = None) -> Dict[str, Any]:
    return _effective_template(template_week_start or _monday(day).isoformat())


def _queue_timestamp(value: str) -> Optional[dt.datetime]:
    try:
        return parse_scheduled_at(value)
    except HTTPException:
        return None


def _slot_stream(
    start: dt.date,
    end: dt.date,
    cursor: dt.datetime,
    count: int,
    *,
    template_week_start: Optional[str] = None,
    enabled_days: Optional[List[int]] = None,
) -> List[dt.datetime]:
    """Yield future, enabled template slots inside the requested date range."""
    if count <= 0:
        return []
    slots: List[dt.datetime] = []
    # Posted rows stay in this set on purpose: once a slot has been used --
    # posted or not -- auto-fill must never offer it again. Excluding posted
    # rows here used to free up today's already-posted times for reuse, so a
    # fresh auto-fill run silently overwrote them with new clips at the same
    # times instead of moving on to slots that were never used.
    occupied = {str(row.get("scheduled_at")) for row in ScheduleQueueStore._load()}
    day = start
    # The selected date range is a hard boundary. Auto-fill is a previewable
    # planning action, so silently placing the remainder on later dates makes
    # the user's explicit "today"/custom-range choice unsafe. The 366-day
    # guard still protects against malformed input/template combinations.
    for _ in range(366):
        if day > end:
            break
        template = _template_for_date(day, template_week_start)
        day_config = template["days"].get(str(day.weekday()), {})
        if (enabled_days is None or day.weekday() in enabled_days) and day_config.get("enabled", True):
            for time in day_config.get("times", DEFAULT_PRIMARY_TIMES):
                when = parse_scheduled_at(f"{day.isoformat()}T{time}:00+07:00")
                iso = scheduled_iso(when)
                if when <= cursor or iso in occupied:
                    continue
                slots.append(when)
                if len(slots) >= count:
                    return slots
        day += dt.timedelta(days=1)
    return slots


def _eligible_clip_key(path: str) -> str:
    return video_key(resolve_video(path))


def _existing_queue_keys(records: List[Dict[str, Any]]) -> set[str]:
    """Keep new ID keys compatible with pre-ID queue rows during migration."""
    keys: set[str] = set()
    for row in records:
        if row.get("export_id"):
            keys.add(f"export:{row['export_id']}")
        if row.get("video_key"):
            keys.add(str(row["video_key"]))
        if row.get("video_path"):
            try:
                keys.add(video_key(resolve_video(row["video_path"])))
            except HTTPException:
                pass
    return keys


def _post_datetime(value: Any) -> Optional[dt.datetime]:
    try:
        parsed = dt.datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=PROJECT_TZ)
    return parsed.astimezone(PROJECT_TZ)


def _stats_bucket_summary(bucket: Dict[str, Any], label_key: str, label: Any) -> Dict[str, Any]:
    samples = bucket["samples"]
    views = bucket["views"]
    avg_views = views / samples if samples else 0.0
    engagement = bucket["engagement"] / samples if samples else 0.0
    avg_orders = bucket["orders"] / samples if samples else 0.0
    avg_commission = bucket["commission"] / samples if samples else 0.0
    cart_click_rate = bucket["cart_clicks"] / views * 100.0 if views else 0.0
    orders_per_1000_views = bucket["orders"] / views * 1000.0 if views else 0.0
    commission_per_1000_views = bucket["commission"] / views * 1000.0 if views else 0.0
    # Normalise conversion and commission by reach so a high-view clip does
    # not automatically outrank a clip that actually drives more revenue.
    score = (
        (avg_views / 1000.0)
        + (engagement * 10.0)
        + (cart_click_rate * 5.0)
        + (orders_per_1000_views * 100.0)
        + (commission_per_1000_views * 10.0)
    )
    return {
        label_key: label,
        "samples": samples,
        "avg_views": round(avg_views),
        "avg_engagement_rate": round(engagement, 2),
        "cart_click_rate": round(cart_click_rate, 2),
        "avg_orders": round(avg_orders, 2),
        "orders_per_1000_views": round(orders_per_1000_views, 2),
        "avg_commission_thb": round(avg_commission, 2),
        "commission_per_1000_views_thb": round(commission_per_1000_views, 2),
        "score": round(score, 2),
    }


def _build_performance_analytics(clips: List[AutoFillClipPayload]) -> tuple[Dict[str, Any], Dict[str, float], Dict[int, float]]:
    """Build explainable product/hour scores from measured local post data."""
    try:
        posts = PostLog.list_posts(newest_first=False)
    except Exception:
        posts = []
    product_buckets: Dict[str, Dict[str, Any]] = {}
    hour_buckets: Dict[int, Dict[str, Any]] = {}
    measured = 0
    for post in posts:
        metrics = post.get("metrics") or {}
        if not metrics or not _post_datetime(post.get("posted_at")):
            continue
        views = max(0, int(metrics.get("views") or 0))
        likes = max(0, int(metrics.get("likes") or 0))
        comments = max(0, int(metrics.get("comments") or 0))
        shares = max(0, int(metrics.get("shares") or 0))
        orders = max(0, int(metrics.get("orders") or 0))
        commission = max(0.0, float(metrics.get("commission_thb") or 0.0))
        engagement = ((likes + comments + shares) / views * 100.0) if views else 0.0
        cart_clicks = max(0, int(metrics.get("cart_clicks") or 0))
        contribution = {"samples": 1, "views": views, "engagement": engagement, "cart_clicks": cart_clicks, "orders": orders, "commission": commission}
        product_name = str(post.get("product_name") or "ไม่ระบุสินค้า").strip()
        product_buckets.setdefault(_product_key(product_name), {"samples": 0, "views": 0, "engagement": 0.0, "cart_clicks": 0, "orders": 0, "commission": 0.0})
        for key, value in contribution.items():
            product_buckets[_product_key(product_name)][key] += value
        hour = _post_datetime(post.get("posted_at")).hour
        hour_buckets.setdefault(hour, {"samples": 0, "views": 0, "engagement": 0.0, "cart_clicks": 0, "orders": 0, "commission": 0.0})
        for key, value in contribution.items():
            hour_buckets[hour][key] += value
        measured += 1

    products = [_stats_bucket_summary(bucket, "product_name", next((str(post.get("product_name") or "ไม่ระบุสินค้า").strip() for post in posts if _product_key(post.get("product_name")) == key), "ไม่ระบุสินค้า")) for key, bucket in product_buckets.items()]
    products.sort(key=lambda row: (-row["score"], -row["samples"], row["product_name"]))
    hours = [_stats_bucket_summary(bucket, "hour", hour) for hour, bucket in hour_buckets.items()]
    hours.sort(key=lambda row: (-row["score"], -row["samples"], row["hour"]))
    product_scores: Dict[str, float] = {}
    for row in products:
        product_scores[_product_key(row["product_name"])] = row["score"]
    for clip in clips:
        name_score = product_scores.get(_product_key(clip.product_name))
        if name_score is not None and clip.product_id:
            product_scores[_product_key(clip.product_id)] = name_score
    hour_scores = {row["hour"]: row["score"] for row in hours}
    confidence = "high" if measured >= 10 else "medium" if measured >= 5 else "low" if measured else "none"
    analytics = {
        "available": bool(measured),
        "sample_size": measured,
        "confidence": confidence,
        "top_products": products[:5],
        "top_hours": hours[:5],
        "method": "reach + engagement + cart click rate + orders/1,000 views + commission/1,000 views; ใช้เป็นคะแนนช่วยเลือก ไม่ใช่การการันตียอดขาย",
    }
    return analytics, product_scores, hour_scores


def _previous_queue_row(records: List[Dict[str, Any]], cursor: dt.datetime) -> Optional[Dict[str, Any]]:
    candidates = []
    for row in records:
        scheduled = _queue_timestamp(row.get("scheduled_at", ""))
        if scheduled and scheduled <= cursor:
            candidates.append((scheduled, row))
    return max(candidates, key=lambda item: (item[0], str(item[1].get("id") or "")))[1] if candidates else None


def _previous_post_row(posts: List[Dict[str, Any]], cursor: dt.datetime) -> Optional[Dict[str, Any]]:
    candidates = []
    for post in posts:
        posted_at = _post_datetime(post.get("posted_at"))
        if posted_at and posted_at <= cursor:
            candidates.append((posted_at, post))
    if not candidates:
        return None
    posted_at, post = max(candidates, key=lambda item: (item[0], str(item[1].get("id") or "")))
    return {
        "scheduled_at": scheduled_iso(posted_at),
        "product_id": post.get("product_id"),
        "product_name": post.get("product_name"),
        "angle_id": post.get("angle_key"),
        "style_preset": post.get("style_preset"),
        "hook_color": post.get("hook_color"),
        "id": post.get("id"),
    }


def _daily_constraint_sets(records: List[Dict[str, Any]], posts: List[Dict[str, Any]]) -> tuple[Dict[dt.date, set[str]], Dict[dt.date, set[str]]]:
    products_by_day: Dict[dt.date, set[str]] = {}
    colors_by_day: Dict[dt.date, set[str]] = {}

    for row in records:
        when = _queue_timestamp(row.get("scheduled_at", ""))
        if not when:
            continue
        products_by_day.setdefault(when.date(), set()).update(_row_product_aliases(row))
        color = _row_visual_key(row)
        if color:
            colors_by_day.setdefault(when.date(), set()).add(color)

    for post in posts:
        when = _post_datetime(post.get("posted_at"))
        if not when:
            continue
        products_by_day.setdefault(when.date(), set()).update(_product_aliases(post.get("product_id"), post.get("product_name")))
        color = _resolve_hook_color(post.get("style_preset"), post.get("hook_color"))
        if color:
            colors_by_day.setdefault(when.date(), set()).add(color)

    return products_by_day, colors_by_day


def _validate_autofill_daily_constraints(records: List[Dict[str, Any]], posts: List[Dict[str, Any]], pending: List[Dict[str, Any]]) -> None:
    products_by_day, colors_by_day = _daily_constraint_sets(records, posts)
    for item in sorted(pending, key=lambda row: row.get("scheduled_at", "")):
        when = _queue_timestamp(item.get("scheduled_at", ""))
        if not when:
            continue
        day = when.date()
        aliases = _row_product_aliases(item)
        if aliases.intersection(products_by_day.get(day, set())):
            raise HTTPException(status_code=409, detail="auto-fill บันทึกไม่ได้: สินค้านี้ถูกจัดคิวหรือโพสต์แล้วในวันเดียวกัน")
        color = _row_visual_key(item)
        if color and color in colors_by_day.get(day, set()):
            raise HTTPException(status_code=409, detail="auto-fill บันทึกไม่ได้: สี Hook นี้ถูกใช้แล้วในวันเดียวกัน")
        products_by_day.setdefault(day, set()).update(aliases)
        if color:
            colors_by_day.setdefault(day, set()).add(color)


def _auto_fill_preview(req: AutoFillRequest) -> Dict[str, Any]:
    start = _date_value(req.start_date, field="start_date")
    end = _date_value(req.end_date, field="end_date")
    if end < start:
        raise HTTPException(status_code=422, detail="end_date ต้องไม่ก่อน start_date")
    if (end - start).days > 366:
        raise HTTPException(status_code=422, detail="ช่วง auto-fill ยาวได้ไม่เกิน 366 วัน")

    records = ScheduleQueueStore._load()
    try:
        history_posts = PostLog.list_posts(newest_first=False)
    except Exception:
        history_posts = []
    posted_clip_names = {
        Path(str(post.get("clip_file") or "").replace("\\", "/")).name.casefold()
        for post in history_posts
        if Path(str(post.get("clip_file") or "").replace("\\", "/")).name.casefold()
        and Path(str(post.get("clip_file") or "").replace("\\", "/")).name.casefold() not in {"clip.mp4", "video.mp4"}
    }
    queued_keys = _existing_queue_keys(records)
    requested_products = {_product_key(value) for value in req.product_ids if str(value).strip()}
    candidates: List[tuple[str, AutoFillClipPayload]] = []
    skipped_invalid: List[Dict[str, str]] = []
    skipped_existing = 0
    skipped_product_filter = 0
    seen: set[str] = set()
    for clip in req.clips:
        try:
            resolved_clip = resolve_video(clip.video_path)
            if resolved_clip.name.casefold() in posted_clip_names:
                raise HTTPException(status_code=409, detail="คลิปนี้มีประวัติถูกโพสต์แล้ว จึงไม่เสนอซ้ำ")
            key = f"export:{clip.export_id}" if clip.export_id else _eligible_clip_key(clip.video_path)
            export_record = ExportRegistry.get(clip.export_id) if clip.export_id else ExportRegistry.find_by_path(resolved_clip)
            if clip.export_id and export_record is None:
                raise HTTPException(status_code=409, detail="ไม่พบ export_id ของคลิปที่ส่งมา")
            if export_record:
                if export_record.get("status") == "posted":
                    raise HTTPException(status_code=409, detail="คลิปที่โพสต์แล้วไม่สามารถนำมาจัดคิวซ้ำได้")
                latest = ExportRegistry.latest_for_angle(clip.product_id, clip.angle_id)
                if latest and latest.get("id") != export_record.get("id"):
                    raise HTTPException(status_code=409, detail="คลิปนี้ไม่ใช่ export เวอร์ชันล่าสุดของมุมนี้")
        except HTTPException as exc:
            skipped_invalid.append({"video_path": clip.video_path, "reason": str(exc.detail)})
            continue
        if key in queued_keys or key in seen:
            skipped_existing += 1
            continue
        product_key = _product_key(clip.product_id, clip.product_name)
        if requested_products and product_key not in requested_products:
            skipped_product_filter += 1
            continue
        seen.add(key)
        candidates.append((product_key, clip))

    now = dt.datetime.now(PROJECT_TZ).replace(second=0, microsecond=0)
    latest = max(
        (
            scheduled
            for row in records
            if row.get("status") != "posted"
            for scheduled in [_queue_timestamp(row.get("scheduled_at", ""))]
            if scheduled and start <= scheduled.date() <= end
        ),
        default=None,
    )
    cursor = max(now, latest) if latest else now
    analytics, product_scores, hour_scores = _build_performance_analytics([clip for _, clip in candidates]) if req.optimize_by_stats else ({
        "available": False,
        "sample_size": 0,
        "confidence": "none",
        "top_products": [],
        "top_hours": [],
        "method": "ปิดการใช้สถิติ",
    }, {}, {})

    allowed_days = None
    if req.enabled_days is not None:
        allowed_days = sorted({int(value) for value in req.enabled_days if 0 <= int(value) <= 6})
    if req.template_week_start:
        _week_key(req.template_week_start)
    selected_count = min(req.limit or len(candidates), len(candidates))
    slot_count = selected_count
    if req.optimize_by_stats and hour_scores:
        # Ask for the full template horizon first, then keep the best measured
        # hours. Requesting only len(selected) slots would always return the
        # earliest times and leave the stats ranking nothing to choose from.
        slot_count = max(selected_count, ((end - start).days + 1) * 24)
    slots = _slot_stream(
        start,
        end,
        cursor,
        slot_count,
        template_week_start=req.template_week_start,
        enabled_days=allowed_days,
    )
    available_slots = list(slots)
    if req.optimize_by_stats and hour_scores and len(slots) > selected_count:
        slots = sorted(
            sorted(slots, key=lambda value: value),
            key=lambda value: (-hour_scores.get(value.hour, 0.0), value),
        )[:selected_count]
        slots.sort()

    used_products_by_day, used_colors_by_day = _daily_constraint_sets(records, history_posts)
    used_products_by_day = {day: values for day, values in used_products_by_day.items() if start <= day <= end}
    used_colors_by_day = {day: values for day, values in used_colors_by_day.items() if start <= day <= end}

    # The previous clip is the row immediately before the first genuinely
    # available slot. This includes posted rows, so a clip posted at 19:00
    # still blocks the same product/color from being put at 21:00.
    previous_cursor = available_slots[0] if available_slots else cursor
    previous_row = _previous_queue_row(records, previous_cursor)
    history_row = _previous_post_row(history_posts, previous_cursor)
    if history_row:
        queue_time = _queue_timestamp(previous_row.get("scheduled_at", "")) if previous_row else None
        history_time = _queue_timestamp(history_row.get("scheduled_at", ""))
        if previous_row is None or (history_time and (queue_time is None or history_time > queue_time)):
            previous_row = history_row
    rng = random.Random(req.seed)
    buckets: Dict[str, List[AutoFillClipPayload]] = {}
    for product_key, clip in candidates:
        buckets.setdefault(product_key, []).append(clip)
    product_keys = list(buckets)
    if req.optimize_by_stats and product_scores:
        product_keys.sort(key=lambda key: (-product_scores.get(_product_key(key), 0.0), rng.random()))
    else:
        rng.shuffle(product_keys)
    for clips in buckets.values():
        rng.shuffle(clips)

    selection_target = min(selected_count, len(slots))
    selected: List[AutoFillClipPayload] = []
    while len(selected) < selection_target:
        target_day = slots[len(selected)].date() if len(selected) < len(slots) else None

        def usable(key: str) -> bool:
            if not buckets.get(key):
                return False
            return any(
                target_day is not None
                and not used_products_by_day.get(target_day, set()).intersection(_clip_product_aliases(clip))
                and (
                    not _resolve_hook_color(clip.style_preset, clip.hook_color)
                    or _resolve_hook_color(clip.style_preset, clip.hook_color)
                    not in used_colors_by_day.get(target_day, set())
                )
                for clip in buckets[key]
            )

        available = [key for key in product_keys if usable(key)]
        if not available:
            break
        product_key = available[0] if req.optimize_by_stats and product_scores else rng.choice(available)
        clip_options = [
            clip for clip in buckets[product_key]
            if target_day is not None
            and not used_products_by_day.get(target_day, set()).intersection(_clip_product_aliases(clip))
            and (
                not _resolve_hook_color(clip.style_preset, clip.hook_color)
                or _resolve_hook_color(clip.style_preset, clip.hook_color)
                not in used_colors_by_day.get(target_day, set())
            )
        ]
        if not clip_options:
            buckets[product_key] = []
            continue
        clip = rng.choice(clip_options)
        buckets[product_key].remove(clip)
        selected.append(clip)
        used_products_by_day.setdefault(target_day, set()).update(_clip_product_aliases(clip))
        color = _resolve_hook_color(clip.style_preset, clip.hook_color)
        if color:
            used_colors_by_day.setdefault(target_day, set()).add(color)
    items: List[Dict[str, Any]] = []
    for clip, when in zip(selected, slots):
        item = clip.model_dump()
        item["scheduled_at"] = scheduled_iso(when)
        item["hook_color"] = _resolve_hook_color(item.get("style_preset"), item.get("hook_color"))
        items.append(item)
    skipped_repetition = max(0, selection_target - len(selected))
    skipped_slots = max(0, selected_count - len(slots)) + max(0, len(selected) - len(items))
    skipped_items = max(0, selected_count - len(items))
    reason = None
    if not candidates:
        reason = "ไม่มีคลิปที่พร้อมจัดคิวและยังไม่เคยอยู่ในคิว"
    elif skipped_repetition:
        reason = "เหลือคลิปที่ติดเงื่อนไขกันสินค้าซ้ำหรือสี Hook ซ้ำ จึงไม่ฝืนจัดคิวให้ซ้ำกัน"
    elif skipped_slots:
        reason = "ไม่มีช่วงเวลาหลักที่ว่างพอสำหรับคลิปที่เลือก"
    return {
        "items": items,
        "skipped_slots": skipped_slots,
        "skipped_repetition": skipped_repetition,
        "skipped_items": skipped_items,
        "skipped_invalid": skipped_invalid,
        "skip_summary": {
            "invalid_or_posted": len(skipped_invalid),
            "already_queued": skipped_existing,
            "outside_product_filter": skipped_product_filter,
            "duplicate_product_or_hook_color": skipped_repetition,
            "no_available_slot": skipped_slots,
        },
        "available_count": len(candidates),
        "requested_count": selected_count,
        "range_start": start.isoformat(),
        "range_end": end.isoformat(),
        "selection_rules": ["ไม่ซ้ำสินค้าในวันเดียวกัน", "ไม่ซ้ำสี Hook ในวันเดียวกัน"],
        "analytics": analytics,
        "timezone": "Asia/Bangkok",
        "seed": req.seed,
        "reason": reason,
    }


@router.get("/template")
def get_schedule_template(week_start: Optional[str] = Query(default=None)):
    template = _effective_template(week_start)
    template["has_override"] = bool(template.get("id") != "default" and template.get("week_start"))
    return template


@router.put("/template")
def save_schedule_template(req: ScheduleTemplatePayload):
    week_key = _week_key(req.week_start)
    with ScheduleTemplateStore._mutate() as records:
        record = _template_record(week_key, req.days)
        records[:] = [row for row in records if row.get("id") != record["id"]]
        records.append(record)
    return _effective_template(week_key)


@router.post("/template/copy")
def copy_schedule_template(req: TemplateCopyRequest):
    target = _week_key(req.target_week_start)
    if target is None:
        raise HTTPException(status_code=422, detail="target_week_start ต้องเป็นวันจันทร์")
    source = _effective_template(req.source_week_start or target)
    with ScheduleTemplateStore._mutate() as records:
        record = _template_record(target, source["days"])
        records[:] = [row for row in records if row.get("id") != record["id"]]
        records.append(record)
    return _effective_template(target)


@router.delete("/template/{week_start}")
def reset_schedule_template(week_start: str):
    key = _week_key(week_start)
    if key is None:
        raise HTTPException(status_code=422, detail="week_start ต้องเป็นวันจันทร์")
    with ScheduleTemplateStore._mutate() as records:
        records[:] = [row for row in records if row.get("id") != f"week:{key}"]
    return _effective_template(key)


@router.post("/auto-fill/preview")
def preview_auto_fill(req: AutoFillRequest):
    return _auto_fill_preview(req)


@router.post("/auto-fill")
def commit_auto_fill(req: AutoFillCommitRequest):
    if not req.items:
        raise HTTPException(status_code=422, detail="ไม่มีรายการ preview ให้บันทึก")
    # Reuse the queue's atomic identity/time validation so a preview can never
    # silently overwrite a manual row added while the modal was open.
    with ScheduleQueueStore._mutate() as records:
        existing_keys = _existing_queue_keys(records)
        # Include posted rows -- see _slot_stream's comment: a used slot stays
        # used even after the clip in it posts, so a race against a manual
        # add (or a second preview) can't double-book that time either.
        existing_times = {str(item.get("scheduled_at")) for item in records}
        created = [_payload_to_record(item, existing_keys, existing_times) for item in req.items]
        try:
            history_posts = PostLog.list_posts(newest_first=False)
        except Exception:
            history_posts = []
        # Preview is advisory; the queue may have changed while the modal was
        # open. Re-check product and Hook-color uniqueness while holding the
        # same queue mutation lock, so the commit remains all-or-nothing.
        _validate_autofill_daily_constraints(records, history_posts, created)
        records.extend(created)
    return {"items": sort_records(created), "count": len(created)}


@router.get("")
def list_queue(status: Optional[str] = Query(default=None), date_from: Optional[str] = None, date_to: Optional[str] = None):
    if status and status not in ALL_STATUSES:
        raise HTTPException(status_code=422, detail="สถานะไม่ถูกต้อง")
    records = ScheduleQueueStore._load()
    if status:
        records = [item for item in records if item.get("status") == status]
    if date_from:
        records = [item for item in records if item.get("scheduled_at", "")[:10] >= date_from]
    if date_to:
        records = [item for item in records if item.get("scheduled_at", "")[:10] <= date_to]
    # Load the export registry ONCE and index it by normalized path, instead
    # of calling ExportRegistry.find_by_path() (an O(registry size) scan
    # that itself calls Path.resolve() per row it checks) once per queue
    # row below -- ~30 queue rows x ~40 registry rows was ~1,200 resolve()
    # syscalls on every GET /schedule-queue.
    export_id_by_path = ExportRegistry.path_index()
    now = dt.datetime.now(PROJECT_TZ)
    enriched = []
    for row in sort_records(records):
        item = dict(row)
        if not item.get("export_id") and item.get("video_path"):
            try:
                path_key = _export_normalise_path(resolve_video(item["video_path"]))
                export_id = export_id_by_path.get(path_key) if path_key else None
                if export_id:
                    item["export_id"] = export_id
            except Exception:
                pass
        scheduled = _queue_timestamp(item.get("scheduled_at", ""))
        item["is_overdue"] = bool(item.get("status") == "planned" and scheduled and scheduled < now)
        enriched.append(item)
    return {"items": enriched, "timezone": "Asia/Bangkok", "status_labels": STATUS_LABELS}


@router.post("")
def create_queue(req: QueueCreateRequest):
    items = _request_items(req)
    with ScheduleQueueStore._mutate() as records:
        existing_keys = _existing_queue_keys(records)
        # See _slot_stream's comment: a posted row still counts as occupying
        # its time slot, otherwise manually re-adding a clip at a time that
        # already posted something silently overwrites that slot's history.
        existing_times = {str(item.get("scheduled_at")) for item in records}
        created = [_payload_to_record(item, existing_keys, existing_times) for item in items]
        records.extend(created)
    return {"items": sort_records(created), "count": len(created)}


@router.patch("/{item_id}")
def patch_queue(item_id: str, req: QueuePatchRequest):
    with ScheduleQueueStore._mutate() as records:
        item = next((row for row in records if row.get("id") == item_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")
        current = item.get("status", "planned")
        if item.get("status") == "posted" and req.status != "posted":
            raise HTTPException(status_code=409, detail="รายการที่โพสต์แล้วแก้ไขไม่ได้")
        if req.scheduled_at is not None:
            if current != "planned":
                raise HTTPException(status_code=409, detail="ต้องรีเซ็ตกลับเป็นรอจัดส่งก่อนจึงจะย้ายเวลาได้")
            new_when = scheduled_iso(parse_scheduled_at(req.scheduled_at))
            if any(row.get("id") != item_id and row.get("scheduled_at") == new_when and row.get("status") != "posted" for row in records):
                raise HTTPException(status_code=409, detail="มีคลิปอื่นจองเวลานี้แล้ว")
            item["scheduled_at"] = new_when
        if req.status is not None:
            item["status"] = req.status
            if req.status == "posted":
                item["posted_at"] = now_iso()
        item["updated_at"] = now_iso()
        result = dict(item)
    return result


@router.delete("/{item_id}")
def remove_queue(item_id: str):
    with ScheduleQueueStore._mutate() as records:
        item = next((row for row in records if row.get("id") == item_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")
        if item.get("status") in {"ready_for_extension", "awaiting_post"}:
            raise HTTPException(status_code=409, detail="กรุณารีเซ็ตคลิปกลับเป็นรอจัดส่งก่อนนำออกจากคิว")
        if item.get("status") == "posted":
            raise HTTPException(status_code=409, detail="รายการที่โพสต์แล้วนำออกจากคิวไม่ได้")
        records.remove(item)
    return {"success": True, "id": item_id}


@router.post("/{item_id}/prepare")
def prepare_queue_item(item_id: str):
    # `prepare()` (scripts/api_tiktok_autopost.py) reads/writes ExportRegistry
    # live -- ExportRegistry shares this process's one store.db connection
    # (scripts/db.py) with ScheduleQueueStore, so calling it from inside an
    # already-open `ScheduleQueueStore._mutate()` transaction raised
    # `sqlite3.OperationalError: cannot start a transaction within a
    # transaction` on every call, leaving the item stuck in "planned"
    # forever. Fix: resolve/ensure the export (via `prepare()`) BEFORE
    # opening the queue transaction, matching the snapshot-then-mutate
    # pattern already used in product_store.py's `_reconcile_into`. The read
    # of `item` here and the write of its new status below are two separate
    # `ScheduleQueueStore` transactions rather than one atomic one -- a
    # concurrent delete/edit of this exact item in that narrow window is a
    # pre-existing, not newly introduced, race (the old code had the same
    # exposure between its `autopost._pending` check and the `prepare()`
    # call); a full cross-store saga is out of scope for this fix.
    records = ScheduleQueueStore._load()
    item = next((row for row in records if row.get("id") == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")
    if item.get("status") not in {"planned", "failed"}:
        raise HTTPException(status_code=409, detail="รายการนี้ถูกส่งให้ Extension แล้วหรือโพสต์ไปแล้ว")
    from scripts import api_tiktok_autopost as autopost
    if autopost._pending is not None:
        raise HTTPException(status_code=409, detail="มีคลิปอื่นรอทำใน Extension อยู่ กรุณาทำให้เสร็จก่อน")
    when = parse_scheduled_at(item["scheduled_at"])
    prepare(PrepareRequest(
        video_path=item["video_path"],
        cover_path=item.get("cover_path"),
        caption=item.get("caption") or "",
        hashtags=item.get("hashtags") or "",
        product_id=item.get("product_id"),
        angle_id=item.get("angle_id"),
        export_id=item.get("export_id"),
        tiktok_product_id=item.get("tiktok_product_id"),
        product_name=item.get("product_name"),
        schedule_date=when.strftime("%Y-%m-%d"),
        schedule_time=when.strftime("%H:%M"),
    ))
    with ScheduleQueueStore._mutate() as records:
        item = next((row for row in records if row.get("id") == item_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")
        if item.get("status") not in {"planned", "failed"}:
            raise HTTPException(status_code=409, detail="รายการนี้ถูกส่งให้ Extension แล้วหรือโพสต์ไปแล้ว")
        item["status"] = "ready_for_extension"
        item["extension_prepared_at"] = now_iso()
        item["updated_at"] = now_iso()
        result = dict(item)
    return result
