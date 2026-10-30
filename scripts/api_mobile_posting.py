"""Mobile posting handoff, 7-day slot agenda, .ics calendar alerts, and Google Drive bridge."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from scripts import config
from scripts.channel_scope import (
    ChannelScope,
    get_channel_scope,
    require_writable,
)
from scripts.channel_store import ChannelError
from scripts.export_registry import ExportRegistry
from scripts.posting_jobs import PostingJobStore
from scripts.schedule_store import ScheduleQueueStore, now_iso

PROJECT_TZ = ZoneInfo("Asia/Bangkok")
STANDARD_SLOTS: tuple[str, ...] = (
    "07:00",
    "09:20",
    "11:40",
    "14:00",
    "16:20",
    "18:40",
    "21:00",
)
MOBILE_CLAIM_LEASE_SECONDS = 1800  # 30 minutes
COVER_EXTENSIONS = (".webp", ".jpg", ".jpeg", ".png")

router = APIRouter(prefix="/api/mobile-post", tags=["MobilePosting"])


# ---------------------------------------------------------------------------
# Helpers & Scope
# ---------------------------------------------------------------------------

def _channel_of(scope: Any) -> Optional[str]:
    return scope.channel_id if isinstance(scope, ChannelScope) else None


def _kw(channel_id: Optional[str]) -> Dict[str, Any]:
    return {} if channel_id is None else {"channel_id": channel_id}


def _guard_writable(scope: Any) -> None:
    if isinstance(scope, ChannelScope) and not scope.is_implicit_default:
        require_writable(scope)


def _parse_iso_dt(value: Any) -> Optional[dt.datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=PROJECT_TZ)
    return parsed.astimezone(PROJECT_TZ)


def _format_scheduled_iso(value: dt.datetime) -> str:
    return value.astimezone(PROJECT_TZ).replace(second=0, microsecond=0).isoformat(timespec="minutes")


def _claim_is_expired(row: Dict[str, Any], now: Optional[dt.datetime] = None) -> bool:
    expires_raw = row.get("claim_expires_at")
    if not expires_raw:
        return False
    expires_dt = _parse_iso_dt(expires_raw)
    if expires_dt is None:
        return False
    ref = now or dt.datetime.now(PROJECT_TZ)
    return expires_dt <= ref


def _media_url_from_path(raw_path: Any) -> str:
    if not raw_path:
        return ""
    text = str(raw_path).strip().replace("\\", "/")
    if text.startswith(("http://", "https://", "/api/media/")):
        return text
    if text.startswith("api/media/"):
        return f"/{text}"
    try:
        p = Path(str(raw_path))
        if p.is_absolute():
            rel = p.resolve().relative_to(config.BASE_DIR.resolve())
            return f"/api/media/{rel.as_posix()}"
    except Exception:
        pass
    cleaned = text.lstrip("/")
    return f"/api/media/{cleaned}" if cleaned else ""


def _derive_cover_3x4(cover_9x16: str) -> str:
    if not cover_9x16:
        return ""
    for ext in COVER_EXTENSIONS:
        suffix = f"_cover{ext}"
        if cover_9x16.lower().endswith(suffix):
            stem = cover_9x16[: -len(suffix)]
            return f"{stem}_cover_3x4{ext}"
    return cover_9x16


def _extract_caption_and_hashtags(raw_text: str) -> tuple[str, str]:
    text = (raw_text or "").strip()
    if not text:
        return "", ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2 and all(tok.startswith("#") for tok in lines[-1].split()):
        hashtags = lines[-1]
        caption = "\n".join(lines[:-1]).strip()
        return caption, hashtags
    tags = re.findall(r"#[^\s#]+", text)
    if tags:
        hashtags = " ".join(tags)
        caption_only = re.sub(r"#[^\s#]+", "", text).strip()
        return caption_only or text, hashtags
    return text, ""


def _serialize_queue_item(row: Dict[str, Any], now: Optional[dt.datetime] = None) -> Dict[str, Any]:
    ref_now = now or dt.datetime.now(PROJECT_TZ)
    queue_id = str(row.get("id") or row.get("queue_id") or "")
    video_path = str(row.get("video_path") or "")
    stem = Path(video_path).stem if video_path else str(row.get("clip_id") or queue_id)
    clip_id = str(row.get("clip_id") or row.get("export_id") or stem or queue_id)
    product_code = str(row.get("product_code") or row.get("product_id") or "")
    product_name = str(row.get("product_name") or row.get("hook_title") or stem or "สินค้า TikTok Shop")
    tiktok_product_id = str(row.get("tiktok_product_id") or "")
    scheduled_at = str(row.get("scheduled_at") or "")
    caption = str(row.get("caption") or "")
    hashtags = str(row.get("hashtags") or "")
    if isinstance(row.get("hashtags"), list):
        hashtags = " ".join(str(t) for t in row["hashtags"] if t)

    cover_raw = row.get("cover_url") or row.get("cover_path") or ""
    cover_9x16_url = _media_url_from_path(row.get("cover_9x16_url") or cover_raw)
    cover_3x4_url = _media_url_from_path(row.get("cover_3x4_url") or _derive_cover_3x4(str(cover_raw)))
    video_url = _media_url_from_path(row.get("video_url") or video_path)

    sched_dt = _parse_iso_dt(scheduled_at)
    minutes_until_due: Optional[int] = None
    is_due_soon = False
    if sched_dt is not None:
        diff_min = int(round((sched_dt - ref_now).total_seconds() / 60.0))
        minutes_until_due = diff_min
        is_due_soon = diff_min <= 10

    return {
        "queue_id": queue_id,
        "clip_id": clip_id,
        "stem": stem,
        "product_code": product_code,
        "product_name": product_name,
        "tiktok_product_id": tiktok_product_id,
        "scheduled_at": scheduled_at,
        "caption": caption,
        "hashtags": hashtags,
        "video_url": video_url,
        "video_path": video_path,
        "cover_9x16_url": cover_9x16_url,
        "cover_3x4_url": cover_3x4_url,
        "status": str(row.get("status") or "planned"),
        "claimed_by": row.get("claimed_by"),
        "claimed_at": row.get("claimed_at"),
        "claim_expires_at": row.get("claim_expires_at"),
        "posted_at": row.get("posted_at"),
        "evidence_type": row.get("evidence_type"),
        "evidence_url": row.get("evidence_url"),
        "minutes_until_due": minutes_until_due,
        "is_due_soon": is_due_soon,
    }


# ---------------------------------------------------------------------------
# Google Drive Bridge & Auto-Archive (6.6 & 6.7)
# ---------------------------------------------------------------------------

def get_gdrive_roots() -> List[Path]:
    """Return configured or standard Google Drive export root directories."""
    candidates: List[Path] = []
    env_root = os.environ.get("OMNICUT_GDRIVE_EXPORT_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root))
    candidates.append(Path("/content/drive/MyDrive/Omnicut_Exports"))
    candidates.append(Path(r"G:\My Drive\Omnicut_Exports"))

    roots: List[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).replace("\\", "/").casefold()
        if key in seen:
            continue
        seen.add(key)
        if path.exists() or (env_root and path == Path(env_root)):
            roots.append(path)
    return roots


def _find_companion_covers(ready_dir: Path, stem: str) -> List[Path]:
    covers: List[Path] = []
    if not ready_dir.is_dir():
        return covers
    prefix_1 = f"{stem}_cover".casefold()
    for entry in sorted(ready_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_file():
            continue
        name_lower = entry.name.casefold()
        if name_lower.startswith(prefix_1) and entry.suffix.lower() in COVER_EXTENSIONS:
            covers.append(entry)
    return covers


def scan_gdrive_ready_items(roots: Optional[List[Path]] = None) -> List[Dict[str, Any]]:
    """Scan 01_Ready_to_post/ across Google Drive roots for ready MP4 + companion files."""
    active_roots = roots if roots is not None else get_gdrive_roots()
    items: List[Dict[str, Any]] = []
    seen_stems: set[str] = set()

    for root in active_roots:
        ready_dir = root / "01_Ready_to_post"
        if not ready_dir.is_dir():
            continue
        for mp4_path in sorted(ready_dir.glob("*.mp4"), key=lambda p: p.name):
            if not mp4_path.is_file():
                continue
            stem = mp4_path.stem
            if stem.casefold() in seen_stems:
                continue
            seen_stems.add(stem.casefold())

            txt_path = ready_dir / f"{stem}.txt"
            json_path = ready_dir / f"{stem}.json"
            covers = _find_companion_covers(ready_dir, stem)

            raw_txt = ""
            if txt_path.is_file():
                try:
                    raw_txt = txt_path.read_text(encoding="utf-8-sig")
                except Exception:
                    raw_txt = ""

            meta: Dict[str, Any] = {}
            if json_path.is_file():
                try:
                    loaded = json.loads(json_path.read_text(encoding="utf-8-sig"))
                    if isinstance(loaded, dict):
                        meta = loaded
                except Exception:
                    meta = {}

            txt_caption, txt_hashtags = _extract_caption_and_hashtags(raw_txt)
            caption = str(meta.get("caption") or txt_caption or "")
            hashtags_val = meta.get("hashtags") or txt_hashtags or ""
            if isinstance(hashtags_val, list):
                hashtags = " ".join(str(t) for t in hashtags_val if t)
            else:
                hashtags = str(hashtags_val)

            cover_9x16 = ""
            cover_3x4 = ""
            for c in covers:
                if "3x4" in c.stem.lower():
                    cover_3x4 = str(c)
                elif not cover_9x16:
                    cover_9x16 = str(c)
            if not cover_3x4 and cover_9x16:
                cover_3x4 = cover_9x16
            if not cover_9x16 and cover_3x4:
                cover_9x16 = cover_3x4

            scheduled_at = str(meta.get("scheduled_at") or meta.get("schedule_time") or "")
            product_code = str(meta.get("product_code") or meta.get("product_id") or "")
            product_name = str(meta.get("product_name") or stem)
            tiktok_product_id = str(meta.get("tiktok_product_id") or "")

            items.append({
                "queue_id": str(meta.get("queue_id") or f"gdrive:{stem}"),
                "clip_id": str(meta.get("clip_id") or stem),
                "stem": stem,
                "product_code": product_code,
                "product_name": product_name,
                "tiktok_product_id": tiktok_product_id,
                "scheduled_at": scheduled_at,
                "caption": caption,
                "hashtags": hashtags,
                "video_path": str(mp4_path),
                "video_url": _media_url_from_path(mp4_path),
                "cover_9x16_url": _media_url_from_path(cover_9x16),
                "cover_3x4_url": _media_url_from_path(cover_3x4),
                "cover_files": [str(c) for c in covers],
                "has_txt": txt_path.is_file(),
                "has_json": json_path.is_file(),
                "status": str(meta.get("status") or "planned"),
                "claimed_by": meta.get("claimed_by"),
                "gdrive_root": str(root),
            })
    return items


def archive_gdrive_export(
    clip_id_or_stem: str,
    *,
    roots: Optional[List[Path]] = None,
    posted_at: Optional[str] = None,
    evidence_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Move {stem}.mp4, {stem}.txt, {stem}.json, and {stem}_cover.* from
    01_Ready_to_post/ to 02_Posted_Archive/ across Google Drive roots."""
    raw = str(clip_id_or_stem or "").strip()
    if raw.startswith("gdrive:"):
        raw = raw[len("gdrive:"):]
    stem = Path(raw).stem if raw.lower().endswith(".mp4") else raw
    if not stem:
        return {"archived": False, "stem": "", "moved_files": []}

    active_roots = roots if roots is not None else get_gdrive_roots()
    moved_files: List[str] = []
    archive_dir_used: Optional[str] = None
    timestamp = posted_at or now_iso()

    for root in active_roots:
        ready_dir = root / "01_Ready_to_post"
        if not ready_dir.is_dir():
            continue
        archive_dir = root / "02_Posted_Archive"
        candidates: List[Path] = []
        for suffix in (".mp4", ".txt", ".json"):
            candidate = ready_dir / f"{stem}{suffix}"
            if candidate.is_file():
                candidates.append(candidate)
        for cover_file in _find_companion_covers(ready_dir, stem):
            if cover_file not in candidates:
                candidates.append(cover_file)

        if not candidates:
            continue

        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_dir_used = str(archive_dir)

        json_candidate = ready_dir / f"{stem}.json"
        if json_candidate.is_file():
            try:
                meta = json.loads(json_candidate.read_text(encoding="utf-8-sig"))
                if isinstance(meta, dict):
                    meta["status"] = "posted"
                    meta["posted_at"] = timestamp
                    meta["evidence_type"] = "manual_user_confirmation"
                    if evidence_url:
                        meta["evidence_url"] = evidence_url
                    json_candidate.write_text(
                        json.dumps(meta, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
            except Exception:
                pass

        for src in candidates:
            dest = archive_dir / src.name
            if dest.exists():
                dest.unlink()
            shutil.move(str(src), str(dest))
            moved_files.append(str(dest))

    return {
        "archived": bool(moved_files),
        "stem": stem,
        "archive_dir": archive_dir_used,
        "moved_files": moved_files,
        "status": "posted" if moved_files else "not_found",
        "posted_at": timestamp if moved_files else None,
    }


# ---------------------------------------------------------------------------
# PostingJobStore synchronization (desktop extension fence)
# ---------------------------------------------------------------------------

def _sync_posting_job_on_handoff(
    channel_id: Optional[str],
    queue_id: str,
    export_id: Optional[str],
    claim_owner: str,
) -> None:
    """Mark any prepared desktop extension job as awaiting_post so /pending skips it."""
    eff_channel = channel_id or config.DEFAULT_CHANNEL_ID
    try:
        store = PostingJobStore(config.BASE_DIR)
        with store.table.scoped_mutate(eff_channel) as rows:
            for row in rows:
                matches_queue = bool(queue_id and row.get("queue_id") == queue_id)
                matches_export = bool(export_id and row.get("export_id") == export_id)
                if (matches_queue or matches_export) and row.get("status") in {"prepared", "claimed"}:
                    if not row.get("publish_attempted_at"):
                        row["previous_status"] = row.get("status", "prepared")
                        row["status"] = "awaiting_post"
                        row["lease_owner"] = claim_owner
                        row["updated_at"] = store.clock()
    except Exception:
        pass
    try:
        from scripts import api_tiktok_autopost as autopost
        pending = getattr(autopost, "_pending", None)
        if isinstance(pending, dict):
            if (queue_id and pending.get("queue_id") == queue_id) or (
                export_id and pending.get("export_id") == export_id
            ):
                autopost._pending = None
    except Exception:
        pass


def _sync_posting_job_on_abandon(
    channel_id: Optional[str],
    queue_id: str,
    export_id: Optional[str],
) -> None:
    """Release any awaiting_post job in PostingJobStore when abandoned on mobile."""
    eff_channel = channel_id or config.DEFAULT_CHANNEL_ID
    try:
        store = PostingJobStore(config.BASE_DIR)
        with store.table.scoped_mutate(eff_channel) as rows:
            for row in rows:
                matches_queue = bool(queue_id and row.get("queue_id") == queue_id)
                matches_export = bool(export_id and row.get("export_id") == export_id)
                if (matches_queue or matches_export) and row.get("status") == "awaiting_post":
                    row["status"] = row.pop("previous_status", "cancelled")
                    row["lease_owner"] = None
                    row["lease_token"] = None
                    row["lease_expires_at"] = None
                    row["updated_at"] = store.clock()
    except Exception:
        pass


def _sync_posting_job_on_confirm(
    channel_id: Optional[str],
    queue_id: str,
    export_id: Optional[str],
    outcome: str,
    posted_at: str,
    evidence_url: Optional[str],
) -> None:
    """Finalize any PostingJobStore job when mobile confirms publication."""
    eff_channel = channel_id or config.DEFAULT_CHANNEL_ID
    try:
        store = PostingJobStore(config.BASE_DIR)
        with store.table.scoped_mutate(eff_channel) as rows:
            for row in rows:
                matches_queue = bool(queue_id and row.get("queue_id") == queue_id)
                matches_export = bool(export_id and row.get("export_id") == export_id)
                if (matches_queue or matches_export) and row.get("status") not in {"cancelled", "published"}:
                    row["status"] = outcome
                    row["effects_applied"] = True
                    row["posted_at"] = posted_at
                    row["receipt"] = {
                        "outcome": outcome,
                        "evidence_type": "manual_user_confirmation",
                        "evidence_url": evidence_url,
                        "confirmed_at": now_iso(),
                    }
                    row["updated_at"] = store.clock()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class MobileHandoffRequest(BaseModel):
    queue_id: str = Field(..., min_length=1)
    device_id: str = Field(..., min_length=1, max_length=128)


class MobileConfirmRequest(BaseModel):
    queue_id: str = Field(..., min_length=1)
    device_id: str = Field(..., min_length=1, max_length=128)
    mode: Literal["posted", "scheduled_in_app"] = "posted"
    evidence_url: Optional[str] = None


class MobileAbandonRequest(BaseModel):
    queue_id: str = Field(..., min_length=1)
    device_id: str = Field(..., min_length=1, max_length=128)


class MobileRescheduleRequest(BaseModel):
    queue_id: str = Field(..., min_length=1)
    scheduled_at: str = Field(..., min_length=1)


class GDriveArchiveRequest(BaseModel):
    stem: Optional[str] = None
    clip_id: Optional[str] = None
    queue_id: Optional[str] = None
    evidence_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/next-due")
def get_next_due(
    device_id: Optional[str] = Query(default=None),
    queue_id: Optional[str] = Query(default=None),
    scope: ChannelScope = Depends(get_channel_scope),
):
    """Return the next due clip for mobile posting (or currently claimed by the same device)."""
    channel_id = _channel_of(scope)
    now = dt.datetime.now(PROJECT_TZ)
    records = ScheduleQueueStore.list_items(**_kw(channel_id))
    phone_owner = f"phone:{device_id.strip()}" if device_id and device_id.strip() else None

    chosen: Optional[Dict[str, Any]] = None

    # 1. Explicit queue_id if requested
    if queue_id:
        chosen = next((r for r in records if r.get("id") == queue_id and r.get("status") != "posted"), None)

    # 2. Resume active claim by the same device
    if chosen is None and phone_owner:
        same_device_claims = [
            r for r in records
            if r.get("status") == "awaiting_post"
            and r.get("claimed_by") == phone_owner
            and not _claim_is_expired(r, now)
        ]
        if same_device_claims:
            same_device_claims.sort(key=lambda r: (str(r.get("scheduled_at") or ""), str(r.get("id") or "")))
            chosen = same_device_claims[0]

    # 3. Earliest planned item (or expired awaiting_post item)
    if chosen is None:
        eligible = [
            r for r in records
            if r.get("status") == "planned"
            or (r.get("status") == "awaiting_post" and _claim_is_expired(r, now))
        ]
        if eligible:
            eligible.sort(key=lambda r: (str(r.get("scheduled_at") or "9999"), str(r.get("created_at") or ""), str(r.get("id") or "")))
            chosen = eligible[0]

    if chosen is not None:
        serialized = _serialize_queue_item(chosen, now)
        return {**serialized, "item": serialized}

    # 4. Fallback to Google Drive 01_Ready_to_post if queue is empty
    gdrive_items = scan_gdrive_ready_items()
    if gdrive_items:
        first_gdrive = gdrive_items[0]
        return {**first_gdrive, "item": first_gdrive}

    return {
        "item": None,
        "queue_id": None,
        "clip_id": None,
        "product_code": None,
        "product_name": None,
        "tiktok_product_id": None,
        "scheduled_at": None,
        "caption": "",
        "hashtags": "",
        "video_url": "",
        "cover_9x16_url": "",
        "cover_3x4_url": "",
        "status": "empty",
        "claimed_by": None,
    }


@router.post("/handoff")
def handoff_to_mobile(
    req: MobileHandoffRequest,
    scope: ChannelScope = Depends(get_channel_scope),
):
    """Claim a scheduled item for mobile posting (`phone:{device_id}`) and set status to `awaiting_post`."""
    channel_id = _channel_of(scope)
    _guard_writable(scope)
    phone_owner = f"phone:{req.device_id.strip()}"
    now = dt.datetime.now(PROJECT_TZ)
    expires = now + dt.timedelta(seconds=MOBILE_CLAIM_LEASE_SECONDS)

    def apply(row: Dict[str, Any], _records: List[Dict[str, Any]]) -> None:
        status = row.get("status", "planned")
        if status == "posted":
            raise HTTPException(status_code=409, detail="รายการนี้ถูกโพสต์ไปแล้ว")
        current_claim = row.get("claimed_by")
        if (
            status == "awaiting_post"
            and current_claim
            and current_claim != phone_owner
            and not _claim_is_expired(row, now)
        ):
            raise HTTPException(
                status_code=409,
                detail=f"รายการนี้ถูกเครื่องอื่นรับไปโพสต์แล้ว ({current_claim})",
            )
        row["status"] = "awaiting_post"
        row["claimed_by"] = phone_owner
        row["claimed_at"] = now.isoformat(timespec="seconds")
        row["claim_expires_at"] = expires.isoformat(timespec="seconds")
        row["updated_at"] = now_iso()

    updated = ScheduleQueueStore.update_item(req.queue_id, apply, **_kw(channel_id))
    if updated is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")

    _sync_posting_job_on_handoff(
        channel_id,
        req.queue_id,
        updated.get("export_id"),
        phone_owner,
    )
    serialized = _serialize_queue_item(updated, now)
    return {**serialized, "item": serialized}


@router.post("/confirm")
def confirm_mobile_post(
    req: MobileConfirmRequest,
    scope: ChannelScope = Depends(get_channel_scope),
):
    """Idempotently confirm mobile post, preserving scheduled_at as posted_at and archiving Google Drive files."""
    channel_id = _channel_of(scope)
    _guard_writable(scope)
    phone_owner = f"phone:{req.device_id.strip()}"
    now = dt.datetime.now(PROJECT_TZ)

    existing = ScheduleQueueStore.get_item(req.queue_id, **_kw(channel_id))
    if existing is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")

    # Idempotent return if already posted/confirmed
    if existing.get("status") == "posted" and existing.get("confirmation_receipt"):
        serialized = _serialize_queue_item(existing, now)
        return {
            **serialized,
            "item": serialized,
            "receipt": existing["confirmation_receipt"],
            "idempotent": True,
        }

    def apply(row: Dict[str, Any], _records: List[Dict[str, Any]]) -> None:
        if row.get("status") == "posted" and row.get("confirmation_receipt"):
            return
        current_claim = row.get("claimed_by")
        if (
            row.get("status") == "awaiting_post"
            and current_claim
            and current_claim != phone_owner
            and not _claim_is_expired(row, now)
        ):
            raise HTTPException(
                status_code=409,
                detail=f"รายการนี้ถูกถือสิทธิ์โดยเครื่องอื่น ({current_claim})",
            )

        # Preserve scheduled_at as posted_at when available (per user rule)
        preserved_posted_at = str(row.get("scheduled_at") or "").strip() or now.isoformat(timespec="seconds")
        receipt = {
            "queue_id": req.queue_id,
            "device_id": req.device_id,
            "claimed_by": phone_owner,
            "mode": req.mode,
            "evidence_type": "manual_user_confirmation",
            "evidence_url": req.evidence_url,
            "posted_at": preserved_posted_at,
            "confirmed_at": now.isoformat(timespec="seconds"),
        }
        row["status"] = "posted"
        row["post_mode"] = req.mode
        row["posted_at"] = preserved_posted_at
        row["evidence_type"] = "manual_user_confirmation"
        row["evidence_url"] = req.evidence_url
        row["claimed_by"] = phone_owner
        row["confirmation_receipt"] = receipt
        row["updated_at"] = now_iso()

    updated = ScheduleQueueStore.update_item(req.queue_id, apply, **_kw(channel_id))
    if updated is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")

    export_id = updated.get("export_id")
    if export_id:
        try:
            ExportRegistry.mark_posted(export_id, **_kw(channel_id))
        except Exception:
            pass

    outcome = "published" if req.mode == "posted" else "scheduled_on_platform"
    _sync_posting_job_on_confirm(
        channel_id,
        req.queue_id,
        export_id,
        outcome,
        str(updated.get("posted_at") or ""),
        req.evidence_url,
    )

    video_path = str(updated.get("video_path") or "")
    stem = Path(video_path).stem if video_path else str(updated.get("clip_id") or req.queue_id)
    archive_result = archive_gdrive_export(
        stem,
        posted_at=str(updated.get("posted_at") or ""),
        evidence_url=req.evidence_url,
    )

    serialized = _serialize_queue_item(updated, now)
    return {
        **serialized,
        "item": serialized,
        "receipt": updated.get("confirmation_receipt"),
        "gdrive_archive": archive_result,
        "idempotent": False,
    }


@router.post("/abandon")
def abandon_mobile_post(
    req: MobileAbandonRequest,
    scope: ChannelScope = Depends(get_channel_scope),
):
    """Release an `awaiting_post` claim back to `planned` and clear `claimed_by`."""
    channel_id = _channel_of(scope)
    _guard_writable(scope)
    phone_owner = f"phone:{req.device_id.strip()}"
    now = dt.datetime.now(PROJECT_TZ)

    def apply(row: Dict[str, Any], _records: List[Dict[str, Any]]) -> None:
        if row.get("status") == "posted":
            raise HTTPException(status_code=409, detail="รายการที่โพสต์แล้วไม่สามารถคืนคิวได้")
        current_claim = row.get("claimed_by")
        if (
            row.get("status") == "awaiting_post"
            and current_claim
            and current_claim != phone_owner
            and not _claim_is_expired(row, now)
        ):
            raise HTTPException(
                status_code=409,
                detail=f"ไม่สามารถยกเลิกสิทธิ์ของเครื่องอื่นได้ ({current_claim})",
            )
        row["status"] = "planned"
        row["claimed_by"] = None
        row.pop("claimed_at", None)
        row.pop("claim_expires_at", None)
        row["updated_at"] = now_iso()

    updated = ScheduleQueueStore.update_item(req.queue_id, apply, **_kw(channel_id))
    if updated is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")

    _sync_posting_job_on_abandon(channel_id, req.queue_id, updated.get("export_id"))
    serialized = _serialize_queue_item(updated, now)
    return {**serialized, "item": serialized}


@router.get("/agenda")
def get_mobile_agenda(
    start_date: Optional[str] = Query(default=None),
    days_count: int = Query(default=7, ge=1, le=14),
    scope: ChannelScope = Depends(get_channel_scope),
):
    """Return a lightweight 7-day mobile agenda grouped by day with the 7 standard slots."""
    channel_id = _channel_of(scope)
    now = dt.datetime.now(PROJECT_TZ)
    if start_date:
        try:
            start_day = dt.date.fromisoformat(start_date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="start_date ต้องเป็นรูปแบบ YYYY-MM-DD") from exc
    else:
        start_day = now.date()

    records = ScheduleQueueStore.list_items(**_kw(channel_id))
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for row in records:
        sched = str(row.get("scheduled_at") or "")
        day_key = sched[:10]
        if day_key:
            by_date.setdefault(day_key, []).append(_serialize_queue_item(row, now))

    days: List[Dict[str, Any]] = []
    for offset in range(days_count):
        day = start_day + dt.timedelta(days=offset)
        day_iso = day.isoformat()
        day_items = sorted(by_date.get(day_iso, []), key=lambda item: item.get("scheduled_at") or "")
        occupied_map: Dict[str, Dict[str, Any]] = {}
        for item in day_items:
            parsed = _parse_iso_dt(item.get("scheduled_at"))
            if parsed:
                occupied_map[parsed.strftime("%H:%M")] = item

        slots: List[Dict[str, Any]] = []
        for slot_time in STANDARD_SLOTS:
            slot_iso = f"{day_iso}T{slot_time}+07:00"
            occupant = occupied_map.get(slot_time)
            slots.append({
                "time": slot_time,
                "scheduled_at": slot_iso,
                "occupied": occupant is not None,
                "item": occupant,
            })
        days.append({
            "date": day_iso,
            "items": day_items,
            "slots": slots,
        })

    return {
        "days": days,
        "standard_slots": list(STANDARD_SLOTS),
        "timezone": "Asia/Bangkok",
    }


@router.post("/reschedule")
def reschedule_mobile_item(
    req: MobileRescheduleRequest,
    scope: ChannelScope = Depends(get_channel_scope),
):
    """Move an item to one of the 7 standard daily slots without drag-and-drop."""
    channel_id = _channel_of(scope)
    _guard_writable(scope)

    target_dt = _parse_iso_dt(req.scheduled_at)
    if target_dt is None:
        raise HTTPException(status_code=422, detail="รูปแบบวันที่และเวลาไม่ถูกต้อง")
    slot_hm = target_dt.strftime("%H:%M")
    if slot_hm not in STANDARD_SLOTS:
        raise HTTPException(
            status_code=422,
            detail=f"เวลาต้องอยู่ใน 7 รอบมาตรฐาน ({', '.join(STANDARD_SLOTS)})",
        )
    new_iso = _format_scheduled_iso(target_dt)

    def apply(row: Dict[str, Any], records: List[Dict[str, Any]]) -> None:
        if row.get("status") == "posted":
            raise HTTPException(status_code=409, detail="รายการที่โพสต์แล้วไม่สามารถย้ายเวลาได้")
        for other in records:
            if other.get("id") == req.queue_id or other.get("status") == "posted":
                continue
            if str(other.get("scheduled_at") or "") == new_iso:
                raise HTTPException(status_code=409, detail=f"มีคลิปอื่นจองเวลา {slot_hm} แล้ว")
        row["scheduled_at"] = new_iso
        row["updated_at"] = now_iso()

    updated = ScheduleQueueStore.update_item(req.queue_id, apply, **_kw(channel_id))
    if updated is None:
        raise HTTPException(status_code=404, detail="ไม่พบรายการในคิว")

    serialized = _serialize_queue_item(updated)
    return {**serialized, "item": serialized}


def _ics_escape(value: str) -> str:
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\r\n", r"\n")
        .replace("\n", r"\n")
    )


@router.get("/calendar.ics")
def get_calendar_ics(
    base_url: str = Query(default="https://studio.omniflow.local"),
    scope: ChannelScope = Depends(get_channel_scope),
):
    """Generate an RFC 5545 iCalendar feed with VALARM (-PT10M) and mobile deep links."""
    channel_id = _channel_of(scope)
    records = ScheduleQueueStore.list_items(**_kw(channel_id))
    planned = [
        r for r in records
        if r.get("status") in {"planned", "awaiting_post"} and r.get("scheduled_at")
    ]
    planned.sort(key=lambda r: str(r.get("scheduled_at") or ""))

    dtstamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//OmniCut Pro Studio//Mobile Posting Schedule//TH",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:OmniCut คิวโพสต์ TikTok",
        "X-WR-TIMEZONE:Asia/Bangkok",
    ]

    clean_base = base_url.rstrip("/")
    for row in planned:
        sched_dt = _parse_iso_dt(row.get("scheduled_at"))
        if sched_dt is None:
            continue
        end_dt = sched_dt + dt.timedelta(minutes=15)
        start_utc = sched_dt.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        end_utc = end_dt.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        queue_id = str(row.get("id") or "")
        product_name = str(row.get("product_name") or row.get("hook_title") or "คลิป TikTok")
        tiktok_pid = str(row.get("tiktok_product_id") or "")
        deep_link = f"{clean_base}/?mode=mobile&tab=post&queue={queue_id}"
        description = f"โพสต์คลิป: {product_name}"
        if tiktok_pid:
            description += f"\nรหัสสินค้า: {tiktok_pid}"
        description += f"\nลิงก์เปิดโพสต์: {deep_link}"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:omnicut-queue-{queue_id}@omnicut.local",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{start_utc}",
            f"DTEND:{end_utc}",
            f"SUMMARY:{_ics_escape(f'โพสต์ TikTok: {product_name}')}",
            f"DESCRIPTION:{_ics_escape(description)}",
            f"URL:{deep_link}",
            "BEGIN:VALARM",
            "TRIGGER:-PT10M",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_ics_escape(f'อีก 10 นาทีถึงรอบโพสต์: {product_name}')}",
            "END:VALARM",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    ics_text = "\r\n".join(lines) + "\r\n"
    return Response(
        content=ics_text,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="omnicut-schedule.ics"'},
    )


@router.get("/gdrive-ready")
def list_gdrive_ready():
    """Scan 01_Ready_to_post/ in Google Drive roots and return ready-to-post items."""
    roots = get_gdrive_roots()
    items = scan_gdrive_ready_items(roots)
    return {
        "items": items,
        "count": len(items),
        "roots": [str(r) for r in roots],
    }


@router.post("/gdrive-archive")
def archive_gdrive_item(req: GDriveArchiveRequest):
    """Move all companion files ({stem}.mp4, .txt, .json, _cover.*) from 01_Ready_to_post/ to 02_Posted_Archive/."""
    target = req.stem or req.clip_id or req.queue_id or ""
    if not target.strip():
        raise HTTPException(status_code=422, detail="กรุณาระบุ stem, clip_id หรือ queue_id")

    result = archive_gdrive_export(target, evidence_url=req.evidence_url)
    if not result["archived"]:
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์สำหรับ '{target}' ใน 01_Ready_to_post")
    return result
