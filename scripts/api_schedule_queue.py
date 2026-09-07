"""Persistent, multi-day publishing queue used by the Daily Agenda UI."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from scripts.api_tiktok_autopost import PrepareRequest, prepare
from scripts.config import BASE_DIR, EXPORTS_DIR
from scripts.schedule_store import ScheduleQueueStore, new_id, now_iso

POSTED_DIR = EXPORTS_DIR.parent / "Posted"
PROJECT_TZ = ZoneInfo("Asia/Bangkok")
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
    return {"items": sort_records(records), "timezone": "Asia/Bangkok", "status_labels": STATUS_LABELS}


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
