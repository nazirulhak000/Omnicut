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
from scripts.schedule_store import ScheduleQueueStore, ScheduleTemplateStore, new_id, now_iso

POSTED_DIR = EXPORTS_DIR.parent / "Posted"
PROJECT_TZ = ZoneInfo("Asia/Bangkok")
DEFAULT_PRIMARY_TIMES = ("07:00", "10:00", "12:00", "16:00", "20:00")
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
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    product_name: Optional[str] = None
    project_name: Optional[str] = None
    hook_title: Optional[str] = None
    cover_path: Optional[str] = None
    cover_url: Optional[str] = None
    caption: str = ""
    hashtags: str = ""
    tiktok_product_id: Optional[str] = None


class QueueCreateRequest(BaseModel):
    video_path: Optional[str] = None
    scheduled_at: Optional[str] = None
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    product_name: Optional[str] = None
    project_name: Optional[str] = None
    hook_title: Optional[str] = None
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
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    product_name: Optional[str] = None
    project_name: Optional[str] = None
    hook_title: Optional[str] = None
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


def _normalise_days(days: Dict[str, ScheduleDayPayload] | Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    for index in DAY_INDICES:
        raw = days.get(str(index), {}) if isinstance(days, dict) else {}
        if isinstance(raw, ScheduleDayPayload):
            enabled, times = raw.enabled, raw.times
        else:
            raw = raw if isinstance(raw, dict) else {}
            enabled, times = bool(raw.get("enabled", True)), raw.get("times", DEFAULT_PRIMARY_TIMES)
        values = [_valid_time(value) for value in times]
        if len(values) != 5 or len(set(values)) != 5:
            raise HTTPException(status_code=422, detail="แต่ละวันต้องมีเวลาไม่ซ้ำกัน 5 เวลา")
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
    key = video_key(path)
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
        "scheduled_at": iso,
        "status": "planned",
        "product_id": payload.product_id,
        "angle_id": payload.angle_id,
        "product_name": payload.product_name,
        "project_name": payload.project_name,
        "hook_title": payload.hook_title,
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
        product_id=req.product_id,
        angle_id=req.angle_id,
        product_name=req.product_name,
        project_name=req.project_name,
        hook_title=req.hook_title,
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
    """Yield future, enabled template slots, continuing beyond the range."""
    if count <= 0:
        return []
    slots: List[dt.datetime] = []
    occupied = {
        str(row.get("scheduled_at"))
        for row in ScheduleQueueStore._load()
        if row.get("status") != "posted"
    }
    day = start
    last_day = end
    # Auto-fill may spill after the requested range. A year is ample for the
    # maximum request and keeps malformed templates from creating an infinite loop.
    for _ in range(366):
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
        # Once the requested range has been exhausted, continue from the next
        # enabled day using the same per-week templates.
        day += dt.timedelta(days=1)
        if day > last_day:
            last_day = day
    return slots


def _eligible_clip_key(path: str) -> str:
    return video_key(resolve_video(path))


def _auto_fill_preview(req: AutoFillRequest) -> Dict[str, Any]:
    start = _date_value(req.start_date, field="start_date")
    end = _date_value(req.end_date, field="end_date")
    if end < start:
        raise HTTPException(status_code=422, detail="end_date ต้องไม่ก่อน start_date")
    if (end - start).days > 366:
        raise HTTPException(status_code=422, detail="ช่วง auto-fill ยาวได้ไม่เกิน 366 วัน")

    records = ScheduleQueueStore._load()
    queued_keys = {
        str(row.get("video_key") or _eligible_clip_key(row["video_path"]))
        for row in records
        if row.get("video_path")
    }
    requested_products = {str(value) for value in req.product_ids if str(value).strip()}
    candidates: List[tuple[str, AutoFillClipPayload]] = []
    skipped_invalid: List[Dict[str, str]] = []
    seen: set[str] = set()
    for clip in req.clips:
        try:
            key = _eligible_clip_key(clip.video_path)
        except HTTPException as exc:
            skipped_invalid.append({"video_path": clip.video_path, "reason": str(exc.detail)})
            continue
        if key in queued_keys or key in seen:
            continue
        product_key = str(clip.product_id or clip.product_name or "other")
        if requested_products and product_key not in requested_products:
            continue
        seen.add(key)
        candidates.append((product_key, clip))

    rng = random.Random(req.seed)
    buckets: Dict[str, List[AutoFillClipPayload]] = {}
    for product_key, clip in candidates:
        buckets.setdefault(product_key, []).append(clip)
    product_keys = list(buckets)
    rng.shuffle(product_keys)
    for clips in buckets.values():
        rng.shuffle(clips)

    selected_count = min(req.limit or len(candidates), len(candidates))
    selected: List[AutoFillClipPayload] = []
    latest_row = max(
        (row for row in records if row.get("status") != "posted" and _queue_timestamp(row.get("scheduled_at", ""))),
        key=lambda row: _queue_timestamp(row.get("scheduled_at", "")) or dt.datetime.min.replace(tzinfo=PROJECT_TZ),
        default=None,
    )
    last_product: Optional[str] = str(latest_row.get("product_id") or latest_row.get("product_name")) if latest_row else None
    while len(selected) < selected_count:
        available = [key for key in product_keys if buckets.get(key) and key != last_product]
        if not available:
            available = [key for key in product_keys if buckets.get(key)]
        if not available:
            break
        product_key = rng.choice(available)
        selected.append(buckets[product_key].pop())
        last_product = product_key

    now = dt.datetime.now(PROJECT_TZ).replace(second=0, microsecond=0)
    latest = max(
        (_queue_timestamp(row.get("scheduled_at", "")) for row in records if row.get("status") != "posted"),
        default=None,
    )
    cursor = max(now, latest) if latest else now
    allowed_days = None
    if req.enabled_days is not None:
        allowed_days = sorted({int(value) for value in req.enabled_days if 0 <= int(value) <= 6})
    if req.template_week_start:
        _week_key(req.template_week_start)
    slots = _slot_stream(
        start,
        end,
        cursor,
        len(selected),
        template_week_start=req.template_week_start,
        enabled_days=allowed_days,
    )
    items: List[Dict[str, Any]] = []
    for clip, when in zip(selected, slots):
        item = clip.model_dump()
        item["scheduled_at"] = scheduled_iso(when)
        items.append(item)
    skipped_slots = max(0, len(selected) - len(items))
    reason = None
    if not candidates:
        reason = "ไม่มีคลิปที่พร้อมจัดคิวและยังไม่เคยอยู่ในคิว"
    elif skipped_slots:
        reason = "ไม่มีช่วงเวลาหลักที่ว่างพอสำหรับคลิปที่เลือก"
    return {
        "items": items,
        "skipped_slots": skipped_slots,
        "skipped_invalid": skipped_invalid,
        "available_count": len(candidates),
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
        existing_keys = {str(item.get("video_key") or video_key(resolve_video(item["video_path"]))) for item in records}
        existing_times = {str(item.get("scheduled_at")) for item in records if item.get("status") != "posted"}
        created = [_payload_to_record(item, existing_keys, existing_times) for item in req.items]
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
    now = dt.datetime.now(PROJECT_TZ)
    enriched = []
    for row in sort_records(records):
        item = dict(row)
        scheduled = _queue_timestamp(item.get("scheduled_at", ""))
        item["is_overdue"] = bool(item.get("status") == "planned" and scheduled and scheduled < now)
        enriched.append(item)
    return {"items": enriched, "timezone": "Asia/Bangkok", "status_labels": STATUS_LABELS}


@router.post("")
def create_queue(req: QueueCreateRequest):
    items = _request_items(req)
    with ScheduleQueueStore._mutate() as records:
        existing_keys = {str(item.get("video_key") or video_key(resolve_video(item["video_path"]))) for item in records}
        existing_times = {str(item.get("scheduled_at")) for item in records if item.get("status") != "posted"}
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
    with ScheduleQueueStore._mutate() as records:
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
            tiktok_product_id=item.get("tiktok_product_id"),
            product_name=item.get("product_name"),
            schedule_date=when.strftime("%Y-%m-%d"),
            schedule_time=when.strftime("%H:%M"),
        ))
        item["status"] = "ready_for_extension"
        item["extension_prepared_at"] = now_iso()
        item["updated_at"] = now_iso()
        result = dict(item)
    return result
