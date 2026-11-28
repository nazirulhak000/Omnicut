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
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import re
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field
from hashlib import sha256
from scripts import config
from scripts.channel_scope import ChannelScope, ensure_same_channel, require_active_for_new_work, require_final_ready, resolve_scope
from scripts.channel_route_policy import UNLISTED_ROUTE_POLICY
from scripts.channel_workflows import get_workflow_scope, require_record_owner, require_project_owner
from scripts.channel_store import ChannelError, normalize_handle
from scripts.content_guard import content_reason
from scripts.episode_registry import EpisodeRegistry, compose_hashtags
from scripts.posting_jobs import INTENTS, PostingJobStore, PROTOCOL_VERSION, account_check

from scripts.config import BASE_DIR, EXPORTS_DIR
from scripts.product_store import ProductStore
from scripts.export_registry import ExportRegistry
from scripts.export_cover_bindings import ExportCoverBindingStore

POSTED_DIR = BASE_DIR / "04_Exports" / "Posted"
COVERS_DIR = BASE_DIR / "05_Covers_Thumbnails"

router = APIRouter(prefix="/api/tiktok-autopost", tags=["tiktok-autopost"])

_pending: Optional[dict] = None

PROJECT_TZ = timezone(timedelta(hours=7))
# TikTok Studio only accepts a scheduled time at least 15 minutes and at most 10 days ahead, on a 5-minute step.
SCHEDULE_MIN_LEAD = timedelta(minutes=15)
SCHEDULE_MAX_LEAD = timedelta(days=10)


def _now_iso() -> str:
    from scripts.schedule_store import now_iso
    return now_iso()


def _check_schedule_window(schedule_date: Optional[str], schedule_time: Optional[str], *, now: Optional[datetime] = None) -> None:
    """Refuse a slot TikTok will reject, before anything is uploaded."""
    if not schedule_date or not schedule_time:
        return
    try:
        slot = datetime.strptime(f"{schedule_date} {schedule_time}", "%Y-%m-%d %H:%M").replace(tzinfo=PROJECT_TZ)
    except ValueError:
        raise ChannelError(422, "posting_schedule_invalid", "วันที่/เวลานัดโพสต์ต้องเป็นรูปแบบ YYYY-MM-DD และ HH:MM")
    if slot.minute % 5:
        raise ChannelError(422, "posting_schedule_invalid", "TikTok ตั้งเวลาได้ทีละ 5 นาที (เช่น 10:00, 10:05)")
    current = now or datetime.now(PROJECT_TZ)
    if slot < current + SCHEDULE_MIN_LEAD:
        raise ChannelError(422, "posting_slot_too_soon", "เวลานัดผ่านไปแล้วหรือเหลือไม่ถึง 15 นาที ให้จัดเวลาใหม่ก่อนเตรียมคลิป")
    if slot > current + SCHEDULE_MAX_LEAD:
        raise ChannelError(422, "posting_slot_too_far", "TikTok ตั้งเวลาล่วงหน้าได้ไม่เกิน 10 วัน ให้เตรียมคลิปนี้เมื่อใกล้ถึงวัน")


def _cover_in_channel(cover_abs: Path, channel_id: str) -> bool:
    """A cover belongs to a channel when it sits in that channel's folder (main: also the legacy flat folder)."""
    try:
        parts = cover_abs.resolve().relative_to(COVERS_DIR.resolve()).parts
    except ValueError:
        return False
    if channel_id != "main":
        return len(parts) > 1 and parts[0] == channel_id
    if len(parts) == 1 or parts[0] == "main":
        return True
    # main keeps its legacy sub-folders (prototypes...), but never another channel's own folder
    try:
        from scripts.channel_store import get_default_store
        others = {c.get("id") for c in get_default_store().list_channels(include_archived=True)} - {"main"}
    except Exception:
        return False
    return parts[0] not in others


def _is_contained(path: Path, root: Path) -> bool:
    """True when `path` sits inside `root`.

    `str.startswith` would also accept a sibling whose name merely extends
    the root's (``Capcut_evil`` against ``Capcut``), so compare path
    components instead.
    """
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_under(raw_path: str, allowed_roots) -> Path:
    p = Path(raw_path)
    if not p.is_absolute():
        p = BASE_DIR / raw_path
    p = p.resolve()
    if not any(_is_contained(p, root.resolve()) for root in allowed_roots):
        raise HTTPException(status_code=403, detail=f"ไฟล์นี้ไม่ได้อยู่ในโฟลเดอร์ที่อนุญาต: {raw_path}")
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {raw_path}")
    return p


_TIMESTAMP_SUFFIX = re.compile(r"_\d{8}_\d{6}(?:_draft)?$", re.IGNORECASE)
_COVER_SUFFIXES = ("_cover_3x4.jpg", "_cover.jpg")
_COVER_9X16_SUFFIX = "_cover.jpg"
_COVER_3X4_SUFFIX = "_cover_3x4.jpg"


def _prefer_3x4_cover(path: Optional[Path]) -> Optional[Path]:
    """Use TikTok's profile crop when an explicit legacy 9:16 path is given.

    Queue rows created before cover variants were split can still contain the
    9:16 ``*_cover.jpg`` path.  Keep custom covers untouched, but transparently
    switch to the sibling 3:4 variant whenever it exists so the extension and
    the app preview use the same image.
    """
    if path is None:
        return None
    name = path.name
    if not name.casefold().endswith(_COVER_9X16_SUFFIX):
        return path
    stem = name[: -len(_COVER_9X16_SUFFIX)]
    expected_name = f"{stem}{_COVER_3X4_SUFFIX}"
    candidate = path.with_name(expected_name)
    if candidate.is_file():
        return candidate
    # Windows filesystems are case-insensitive, while tests and mounted
    # workspaces may be case-sensitive.  Match the sibling name explicitly.
    try:
        expected_folded = expected_name.casefold()
        for sibling in path.parent.iterdir():
            if sibling.is_file() and sibling.name.casefold() == expected_folded:
                return sibling
    except OSError:
        pass
    return path


def _find_named_cover(stem: str) -> Optional[Path]:
    """Find a generated cover by stem, preferring TikTok's 3:4 crop."""
    name = str(stem or "").strip()
    if not name or not COVERS_DIR.exists():
        return None
    candidates = {candidate.name.casefold(): candidate for candidate in COVERS_DIR.iterdir() if candidate.is_file()}
    for suffix in _COVER_SUFFIXES:
        match = candidates.get(f"{name}{suffix}".casefold())
        if match:
            return match
    return None


def _cover_names_for_job(video_abs: Path, product_id: str = "", angle_id: str = "", product_name: str = "", channel_id: str = "main") -> list[str]:
    """Return deterministic project/product stems that may own this cover."""
    names: list[str] = [video_abs.stem, _TIMESTAMP_SUFFIX.sub("", video_abs.stem)]
    try:
        products = ProductStore.get_all(channel_id=channel_id)
    except Exception:
        products = []
    for product in products:
        if product_id and str(product.get("id", "")) != str(product_id):
            continue
        if product_name and str(product.get("name", "")).casefold() != str(product_name).casefold():
            continue
        if not product_id and not product_name:
            continue
        names.append(str(product.get("name", "")))
        for angle in product.get("angles", []) or []:
            if angle_id and str(angle.get("angle_id", "")) != str(angle_id):
                continue
            names.append(str(angle.get("project_name", "")))
            video_url = str(angle.get("video_url", ""))
            if video_url:
                names.append(Path(video_url).stem)
    return list(dict.fromkeys(name for name in names if name.strip()))


def _resolve_cover_for_job(video_abs: Path, *, product_id: str = "", angle_id: str = "", product_name: str = "", channel_id: str = "main") -> Optional[Path]:
    if channel_id != "main":
        # Basename fallback in the legacy flat cover folder cannot prove a
        # second channel's ownership. Its explicit namespaced cover is required.
        return None
    for stem in _cover_names_for_job(video_abs, product_id, angle_id, product_name, channel_id):
        cover = _find_named_cover(stem)
        if cover:
            return cover
    return None


def _relative_cover(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    return str(path.relative_to(BASE_DIR)).replace("\\", "/")


def _relative_cover_safe(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        return str(raw).replace("\\", "/")
    try:
        return str(path.resolve().relative_to(BASE_DIR.resolve())).replace("\\", "/")
    except ValueError:
        return None


def _cover_media_url(rel: Optional[str]) -> Optional[str]:
    """The one URL form for a cover: always derived from its path, never taken from a client."""
    if not rel:
        return None
    from urllib.parse import quote
    return "/api/media/" + quote(rel.replace("\\", "/"), safe="/")


def _repair_pending_cover() -> None:
    """Backfill a missing cover for a pending job before the extension reads it."""
    if not _pending or _pending.get("cover_path"):
        return
    video_raw = _pending.get("video_path")
    if not video_raw:
        return
    cover = _resolve_cover_for_job(
        Path(video_raw),
        product_id=str(_pending.get("product_id") or ""),
        angle_id=str(_pending.get("angle_id") or ""),
        product_name=str(_pending.get("product_name") or ""),
    )
    if cover:
        _pending["cover_path"] = str(cover.resolve())


class PrepareRequest(BaseModel):
    video_path: str
    export_id: Optional[str] = None
    cover_path: Optional[str] = None
    caption: str = ""
    hashtags: str = ""
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    tiktok_product_id: Optional[str] = None
    product_name: Optional[str] = None
    queue_id: Optional[str] = None
    schedule_date: Optional[str] = None
    schedule_time: Optional[str] = None
    # schedule | draft | post_now | publish_draft. Missing = inferred (schedule when a time is given, else post_now).
    intent: Optional[str] = None
    # publish_draft without a schedule posts LIVE: the operator must say so explicitly.
    confirm_live: bool = False
    idempotency_key: Optional[str] = None


class CoverUpdateRequest(BaseModel):
    cover_path: str
    job_id: Optional[str] = None


class CancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str


class ClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol_version: int = Field(ge=2, le=2)
    job_id: str
    lease_owner: str


class ActionRequest(ClaimRequest):
    lease_token: str
    expected_revision: int
    payload_hash: str
    source_account: Optional[str] = None
    confirmation_token: Optional[str] = Field(default=None, min_length=1, max_length=128)
    force: bool = False
    # post | draft: which button the worker is about to press (checked against the job's intent on /attempt)
    click_kind: Optional[str] = None


class OutcomeRequest(ActionRequest):
    outcome: str
    proof: dict = Field(default_factory=dict)


def _resolve_intent(req) -> str:
    """What the operator meant to do. A schedule intent needs BOTH date and time, any other intent needs NEITHER:
    this is what stops an unscheduled clip from being posted live by a "schedule" run."""
    has_date, has_time = bool(req.schedule_date), bool(req.schedule_time)
    intent = req.intent or ("schedule" if (has_date and has_time) else "post_now")
    if intent not in INTENTS:
        raise ChannelError(422, "posting_intent_invalid", "intent ต้องเป็น schedule | draft | post_now | publish_draft")
    if intent == "schedule" and not (has_date and has_time):
        raise ChannelError(422, "posting_schedule_required", "งานตั้งเวลาต้องมีทั้งวันที่และเวลา (ไม่มีเวลา = จะกลายเป็นโพสต์สด จึงปฏิเสธ)")
    if intent == "publish_draft":
        if has_date != has_time:
            raise ChannelError(422, "posting_schedule_required", "เผยแพร่จากแบบร่างต้องมีทั้งวันที่และเวลา หรือไม่มีทั้งคู่ (โพสต์ทันที)")
        if not has_date and not getattr(req, "confirm_live", False):
            raise ChannelError(422, "posting_live_confirmation_required", "เผยแพร่แบบร่างโดยไม่ตั้งเวลา = โพสต์สดทันที ต้องยืนยันชัดเจน (confirm_live)")
        return intent
    if intent != "schedule" and (has_date or has_time):
        raise ChannelError(422, "posting_schedule_not_allowed", "งานแบบร่าง/โพสต์ทันทีต้องไม่มีวันที่หรือเวลานัด")
    return intent


@router.post("/prepare")
def prepare(req: PrepareRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    """Called by the app's Post Studio panel. Validates + resolves both
    paths to absolute OS paths (chrome.debugger's DOM.setFileInputFiles
    needs a real filesystem path, not a URL) and stashes them for the
    extension to pick up next."""
    scope = _actual_scope(scope)
    _posting_ready(scope)
    channel_id = scope.channel_id
    # Canonical ownership is checked before any filesystem access. Body fields
    # never choose an owner or an export other than this scoped registry row.
    video_candidate = Path(req.video_path)
    video_candidate = (video_candidate if video_candidate.is_absolute() else BASE_DIR / video_candidate).resolve()
    export_record = ExportRegistry.lookup(export_id=req.export_id, path=video_candidate, channel_id=channel_id)
    if req.export_id and export_record is None:
        raise HTTPException(status_code=409, detail="ไม่พบ export_id ที่ระบุ จึงหยุดการเตรียมโพสต์เพื่อป้องกันการเลือกคลิปผิดตัว")
    if export_record is None:
        if scope.strict or channel_id != "main":
            raise ChannelError(404, "resource_not_found", "ไฟล์นี้ยังไม่มีเจ้าของ export ของช่องนี้")
        video_abs = _resolve_under(req.video_path, [EXPORTS_DIR, POSTED_DIR])
        export_record = ExportRegistry.ensure(
            video_abs, product_id=req.product_id, angle_id=req.angle_id, channel_id=channel_id,
        )
    ensure_same_channel(scope, export_record.get("channel_id"), allow_legacy_main=not scope.strict)
    video_abs = _resolve_under(str(video_candidate), [EXPORTS_DIR, POSTED_DIR])
    registered = Path(str(export_record.get("path") or ""))
    if not registered.is_absolute():
        registered = (BASE_DIR / registered).resolve()
    else:
        registered = registered.resolve()
    if registered != video_abs.resolve():
        raise HTTPException(status_code=409, detail="export_id ไม่ตรงกับไฟล์ที่เลือก")
    if export_record.get("status") == "posted":
        raise HTTPException(status_code=409, detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่ต้องส่งเข้า Extension ซ้ำ")
    from scripts.hyperframes_publish_readiness import require_export_ready
    source_readiness = require_export_ready(BASE_DIR, channel_id, export_record)
    product_id = export_record.get("product_id") or req.product_id
    angle_id = export_record.get("angle_id") or req.angle_id
    if req.product_id and export_record.get("product_id") and req.product_id != export_record["product_id"]:
        raise ChannelError(409, "posting_parent_conflict", "สินค้าไม่ตรงกับ export ที่เลือก")
    if req.angle_id and export_record.get("angle_id") and req.angle_id != export_record["angle_id"]:
        raise ChannelError(409, "posting_parent_conflict", "มุมไม่ตรงกับ export ที่เลือก")
    if product_id:
        product = ProductStore.get(product_id, channel_id=channel_id)
        if product is None and (scope.strict or channel_id != "main" or ProductStore.owner_of(product_id)[0]):
            raise ChannelError(404, "resource_not_found", "ไม่พบสินค้าเจ้าของ export ในช่องนี้")
    if export_record.get("project_name") and (scope.strict or channel_id != "main"):
        require_project_owner(scope, export_record["project_name"])
    draft_source_job_id = None
    if req.queue_id:
        from scripts.schedule_store import ScheduleQueueStore
        queue = ScheduleQueueStore.get_item(req.queue_id, channel_id=channel_id)
        require_record_owner(scope, queue, resource_label="คิวโพสต์")
        if queue.get("export_id") != export_record["id"]:
            raise ChannelError(409, "posting_parent_conflict", "คิวไม่ตรงกับ export ที่เลือก")
        if req.intent == "publish_draft":
            draft_source_job_id = queue.get("posting_job_id")
            if queue.get("status") != "draft_on_platform" or not draft_source_job_id:
                raise ChannelError(409, "posting_draft_not_on_platform", "เผยแพร่จากแบบร่างได้เฉพาะคิวที่อยู่ในสถานะ 'บันทึกเป็นแบบร่างบน TikTok แล้ว'")
            queued_at = str(queue.get("scheduled_at") or "")
            if req.schedule_date and req.schedule_time and queued_at:
                # one source of truth for the time: the queue row (the scheduler edits it). A stale panel must not publish a
                # slot the scheduler no longer has.
                if f"{req.schedule_date}T{req.schedule_time}" != queued_at[:16]:
                    raise ChannelError(409, "posting_slot_mismatch", f"เวลาที่ส่งมา ({req.schedule_date} {req.schedule_time}) ไม่ตรงกับเวลาในคิว ({queued_at[:16].replace('T', ' ')}) กรุณาโหลดรายการใหม่")
            source_job = _jobs().get(channel_id, draft_source_job_id)
            if source_job["status"] != "draft_saved" or source_job.get("export_id") != export_record["id"]:
                raise ChannelError(409, "posting_draft_not_on_platform", "งานแบบร่างเดิมไม่อยู่ในสถานะที่เผยแพร่ต่อได้")
    elif req.intent == "publish_draft":
        raise ChannelError(422, "posting_draft_queue_required", "เผยแพร่จากแบบร่างต้องระบุคิว (queue_id) ของแบบร่างนั้น")
    if not req.queue_id:
        latest_record = ExportRegistry.latest_for_angle(product_id, angle_id, channel_id=channel_id,
                                                        project_name=export_record.get("project_name"),
                                                        batch=export_record.get("batch"))
        if latest_record and latest_record.get("status") != "posted" and latest_record.get("id") != export_record.get("id"):
            raise ChannelError(409, "stale_export", "คลิปนี้มี export รุ่นใหม่แล้ว กรุณาเลือกคลิปใหม่ก่อนเตรียมโพสต์",
                               action="reselect_export", export_id=export_record.get("id"),
                               latest_export_id=latest_record.get("id"))
    hyperframes_package = None
    project_name = export_record.get("project_name")
    if not req.queue_id and project_name:
        manifest_path = ExportCoverBindingStore(BASE_DIR)._path(Path("03_Projects") / project_name / "project.json")
        if not manifest_path.is_relative_to((BASE_DIR / "03_Projects").resolve()):
            raise ChannelError(404, "resource_not_found", "Export project is outside the project store")
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            require_record_owner(scope, manifest, resource_label="export project")
            if manifest.get("engine") == "hyperframes":
                if manifest.get("channel_id") != channel_id:
                    raise ChannelError(404, "resource_not_found", "HyperFrames project has no exact channel owner")
                packages = [p for p in manifest.get("publish_package_refs", []) if p.get("export_id") == export_record["id"]]
                if len(packages) != 1:
                    raise ChannelError(409, "hyperframes_publish_package_missing", "Exact HyperFrames export package is missing or ambiguous")
                hyperframes_package = packages[0]
                require_record_owner(scope, hyperframes_package, resource_label="HyperFrames export package")
                if hyperframes_package.get("channel_id") != channel_id:
                    raise ChannelError(404, "resource_not_found", "HyperFrames export package has no exact channel owner")
        elif Path(project_name).name.startswith("HF_"):
            raise ChannelError(409, "hyperframes_publish_package_missing", "HyperFrames export project manifest is missing")
    selected_cover = None
    if not req.queue_id:
        bindings = ExportCoverBindingStore(BASE_DIR)
        selected_cover = bindings.get(channel_id, export_record["id"], format="3:4") or bindings.get(channel_id, export_record["id"], format="9:16")
    if selected_cover:
        cover_abs = _resolve_under(selected_cover["path"], [COVERS_DIR])
        if req.cover_path and _resolve_under(req.cover_path, [COVERS_DIR]) != cover_abs:
            raise ChannelError(409, "export_cover_selection_conflict", "Requested cover differs from the exact saved export selection; reload before preparing")
        if _file_digest(cover_abs) != selected_cover["sha256"]:
            raise ChannelError(409, "export_cover_selection_changed", "Explicit selected cover changed before preparing")
    elif req.queue_id:
        frozen_cover = queue.get("cover_path")
        cover_abs = _resolve_under(frozen_cover, [COVERS_DIR]) if frozen_cover else None
        if req.cover_path and (cover_abs is None or _resolve_under(req.cover_path, [COVERS_DIR]) != cover_abs):
            raise ChannelError(409, "posting_queue_cover_conflict", "Requested cover differs from the existing queue's frozen cover")
        if queue.get("cover_sha256") and (cover_abs is None or _file_digest(cover_abs) != queue["cover_sha256"]):
            raise ChannelError(409, "posting_queue_cover_changed", "Frozen queued cover changed; review and reselect before preparing")
    else:
        requested = req.cover_path or (hyperframes_package or {}).get("cover_path")
        cover_abs = _resolve_under(requested, [COVERS_DIR]) if requested else None
        if hyperframes_package and not req.cover_path and cover_abs and hyperframes_package.get("cover_sha256") != _file_digest(cover_abs):
            raise ChannelError(409, "export_cover_selection_changed", "Frozen HyperFrames package cover changed")
    if cover_abs and not _cover_in_channel(cover_abs, channel_id):
        raise ChannelError(404, "resource_not_found", "ไฟล์ปกนี้ไม่อยู่ในช่องของงาน")
    if hyperframes_package is not None and cover_abs:
        raw_cover = selected_cover["path"] if selected_cover else req.cover_path or hyperframes_package.get("cover_path")
        managed_cover = ExportCoverBindingStore(BASE_DIR)._path(raw_cover)
        if managed_cover.relative_to(BASE_DIR.resolve()).parts[:2] != ("05_Covers_Thumbnails", channel_id):
            raise ChannelError(404, "resource_not_found", "HyperFrames cover belongs to another channel")
    if not selected_cover and not req.queue_id and hyperframes_package is None:
        cover_abs = _prefer_3x4_cover(cover_abs)
    if cover_abs is None and not req.queue_id and hyperframes_package is None:
        cover_abs = _resolve_cover_for_job(
            video_abs,
            product_id=req.product_id or "",
            angle_id=req.angle_id or "",
            product_name=req.product_name or "",
            channel_id=channel_id,
        )

    global _pending
    cover_digest = _file_digest(cover_abs) if cover_abs else None
    if selected_cover and cover_digest != selected_cover["sha256"]:
        raise ChannelError(409, "export_cover_selection_changed", "Explicit selected cover changed before its posting snapshot")
    if hyperframes_package and not selected_cover and not req.cover_path and cover_abs and cover_digest != hyperframes_package.get("cover_sha256"):
        raise ChannelError(409, "export_cover_selection_changed", "Frozen HyperFrames cover changed before its posting snapshot")
    if req.queue_id and queue.get("cover_sha256") and cover_digest != queue["cover_sha256"]:
        raise ChannelError(409, "posting_queue_cover_changed", "Frozen queued cover changed before its posting snapshot")
    intent = _resolve_intent(req)
    if intent in {"schedule", "publish_draft"}:
        _check_schedule_window(req.schedule_date, req.schedule_time)
    # the clip's permanent EP number (issued the first time; the same lineage always gets the same one) and its hashtag form
    episode = EpisodeRegistry(BASE_DIR).ensure(channel_id, product_id=product_id, angle_id=angle_id, export_id=export_record["id"])
    final_hashtags = compose_hashtags(req.hashtags, episode["episode_no"])
    blocked = content_reason(req.caption, final_hashtags)
    # an empty caption is allowed here (cover/media-only preparation); the worker refuses to type nothing
    if blocked and blocked != "empty_caption":
        raise ChannelError(422, "posting_content_blocked", f"เนื้อหาโพสต์ไม่ผ่านตัวกัน ({blocked}): ห้ามมีราคา/ส่วนลด, placeholder ที่ยังไม่แทนค่า, ข้อความว่าง หรือยาวเกิน")
    payload = {
        "video_path": str(video_abs),
        "export_id": export_record.get("id"),
        "cover_path": str(cover_abs) if cover_abs else None,
        "caption": req.caption,
        "hashtags": final_hashtags,
        "episode_no": episode["episode_no"],
        "product_id": product_id,
        "angle_id": angle_id,
        "tiktok_product_id": req.tiktok_product_id,
        "product_name": req.product_name,
        "schedule_date": req.schedule_date,
        "schedule_time": req.schedule_time,
        "intent": intent,
        **({"draft_source_job_id": draft_source_job_id} if draft_source_job_id else {}),
        "queue_id": req.queue_id,
        "target_handle": scope.channel.get("handle") or "",
        "channel_revision": int(scope.channel.get("revision", 0)),
        "account_binding": scope.channel.get("account_binding") or {},
        "strict_mode": scope.strict,
        "video_sha256": _file_digest(video_abs),
        "cover_sha256": cover_digest,
    }
    if source_readiness.get("engine") == "hyperframes":
        if source_readiness.get("video_sha256") and payload["video_sha256"] != source_readiness["video_sha256"]:
            raise ChannelError(409, "hyperframes_export_changed", "Reviewed export changed before its posting snapshot")
        payload.update(project_name=export_record.get("project_name"),
                       source_binding=source_readiness["source_binding"],
                       source_artifact_id=source_readiness.get("source_artifact_id"))
        if source_readiness.get("slot_fingerprint"):
            payload["source_slot_fingerprint"] = source_readiness["slot_fingerprint"]
    job = _jobs().prepare(channel_id, payload, idempotency_key=req.idempotency_key)
    for replaced in job.pop("superseded_jobs", None) or []:
        # the replaced (never-claimed / abandoned) job must not keep its queue row waiting on it
        _reset_queue_row(scope, replaced)
    _pending = job  # Legacy read cache only; never used to authorize an effect.
    if req.queue_id:
        try:
            from scripts.schedule_store import ScheduleQueueStore

            def _mark_ready(row, _records):
                if row.get("export_id") != job["export_id"]:
                    raise ChannelError(409, "posting_parent_conflict", "คิวเปลี่ยน export ระหว่างเตรียมงานแล้ว จึงไม่ผูกงานผิดคลิป")
                from_draft = job.get("intent") == "publish_draft"
                if from_draft:
                    if not (row.get("status") == "draft_on_platform" and row.get("posting_job_id") == job.get("draft_source_job_id")) and not (
                            row.get("status") == "ready_for_extension" and row.get("posting_job_id") == job["job_id"]):
                        raise ChannelError(409, "posting_queue_changed", "คิวเปลี่ยนสถานะแล้ว จึงไม่ทับงานอื่น")
                    row["draft_job_id"] = job.get("draft_source_job_id") or row.get("draft_job_id")
                elif row.get("status") not in {"planned", "failed"} and not (
                        row.get("status") == "ready_for_extension" and (
                            row.get("posting_job_id") == job["job_id"] or _job_is_cancelled(channel_id, row.get("posting_job_id")))):
                    raise ChannelError(409, "posting_queue_changed", "คิวเปลี่ยนสถานะแล้ว จึงไม่ทับงานอื่น")
                row["status"] = "ready_for_extension"
                row["posting_job_id"] = job["job_id"]
                row["extension_prepared_at"] = _now_iso()
                row["updated_at"] = _now_iso()

            result = ScheduleQueueStore.update_item(req.queue_id, _mark_ready, channel_id=channel_id)
            if result is None:
                raise ChannelError(404, "resource_not_found", "คิวถูกลบก่อนผูกงานโพสต์")
            job = _jobs().mark_prepare_effects(channel_id, job["job_id"])
            _pending = job
        except Exception as exc:
            _jobs().mark_prepare_effects(channel_id, job["job_id"], error=type(exc).__name__)
            # An invisible half-prepared job would block every later prepare of this export: retire it.
            try:
                _jobs().cancel(channel_id, job["job_id"])
            except ChannelError:
                pass
            raise
    return {"success": True, "cover_path": _relative_cover(cover_abs), "job_id": job["job_id"],
            "channel_id": channel_id, "protocol_version": PROTOCOL_VERSION, "revision": job["revision"]}


@router.post("/cover")
def update_cover(req: CoverUpdateRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    """Refresh the cover on the already-prepared job.

    The editor can save a new cover after the extension job was prepared.
    Resolve and validate the path before mutating the in-memory job so a
    failed refresh never destroys the previous valid cover.
    """
    scope = _actual_scope(scope)
    job = _jobs().get(scope.channel_id, req.job_id) if req.job_id else _jobs().pending(scope.channel_id)
    if job is None:
        raise HTTPException(status_code=404, detail="ยังไม่มีคลิปที่เตรียมไว้")
    if job.get("queue_id"):
        # a queued clip posts the cover frozen on its queue row; swapping it here would bypass that snapshot
        raise ChannelError(409, "posting_queue_cover_frozen", "คลิปจากคิวใช้ปกที่ล็อกไว้ในคิว เปลี่ยนปกในคิวแล้วเตรียมคลิปใหม่")
    cover_abs = _prefer_3x4_cover(_resolve_under(req.cover_path, [COVERS_DIR]))
    if not _cover_in_channel(cover_abs, scope.channel_id):
        raise ChannelError(404, "resource_not_found", "ไฟล์ปกนี้ไม่อยู่ในช่องของงาน")
    _jobs().update_cover(scope.channel_id, job["job_id"], str(cover_abs), cover_sha256=_file_digest(cover_abs))
    return {"success": True, "cover_path": str(cover_abs)}


@router.get("/pending")
def get_pending(scope: ChannelScope = Depends(get_workflow_scope)):
    """Polled by the extension's popup/background worker. 404 means
    "nothing prepared yet" -- the extension should tell the user to click
    the app's button first rather than silently doing nothing."""
    scope = _actual_scope(scope)
    job = None
    for candidate in _jobs().pending_candidates(scope.channel_id):
        try:
            _canonical_job(scope, candidate["job_id"], before_action=True)
        except ChannelError as exc:
            if exc.code in {"posting_export_changed", "posting_cover_changed"}:
                # its file changed after preparing: it can never be claimed, so it must not block the jobs behind it
                continue
            raise
        except HTTPException as exc:
            if exc.status_code in {403, 404}:
                continue
            raise
        job = candidate
        break
    if job is None and scope.channel_id == "main" and not scope.strict and _pending and not _pending.get("job_id"):
        # Legacy read-only compatibility, never claimable by protocol v2.
        _repair_pending_cover()
        return _pending
    if job is None:
        raise HTTPException(status_code=404, detail="ยังไม่มีคลิปที่เตรียมไว้ -- กด 'โพสต์ TikTok อัตโนมัติ' ในแอปก่อน")
    # Protocol jobs are immutable posting snapshots, including an explicit
    # absence of a cover. Polling must never infer and mutate their metadata.
    return {key: value for key, value in job.items() if key != "lease_token"}


@router.post("/clear")
def clear_pending(req: "CancelRequest", scope: ChannelScope = Depends(get_workflow_scope)):
    """Called by the extension once it has consumed the job (success or
    failure) so a stale job never gets replayed by mistake."""
    global _pending
    scope = _actual_scope(scope)
    job = _jobs().get(scope.channel_id, req.job_id)
    _jobs().cancel(scope.channel_id, req.job_id)
    # a cancelled job must not leave its queue row pointing at it (the next prepare would be refused with 409)
    _reset_queue_row(scope, job)
    if _pending and _pending.get("job_id") == req.job_id:
        _pending = None
    return {"success": True}


def _reset_queue_row(scope, job):
    """Put the queue row of a job that never reached TikTok back to `planned`. Only a row that still points at this
    very job and is waiting for the extension is touched."""
    if not job.get("queue_id"):
        return
    from scripts.schedule_store import ScheduleQueueStore

    def reset(row, _rows):
        if row.get("posting_job_id") == job["job_id"] and row.get("status") in {"ready_for_extension", "awaiting_post"}:
            if job.get("intent") == "publish_draft" and row.get("draft_job_id"):
                # the draft is still on TikTok: back to that state, not to "planned" (which would allow a duplicate upload)
                row["status"] = "draft_on_platform"
                row["posting_job_id"] = row["draft_job_id"]
            else:
                row["status"] = "planned"
                row.pop("posting_job_id", None)
            row.pop("extension_prepared_at", None)
            row["updated_at"] = _now_iso()
    ScheduleQueueStore.update_item(job["queue_id"], reset, channel_id=scope.channel_id)


def _job_is_cancelled(channel_id, job_id) -> bool:
    if not job_id:
        return False
    try:
        return _jobs().get(channel_id, job_id).get("status") == "cancelled"
    except ChannelError:
        return True  # the row points at a job that no longer exists


def _actual_scope(scope):
    return scope if isinstance(scope, ChannelScope) else resolve_scope(
        header_values=[], query_values=[], policy=UNLISTED_ROUTE_POLICY)


def _jobs():
    return PostingJobStore(BASE_DIR)


_DIGEST_CACHE: dict = {}


def _file_digest(path):
    """SHA-256 of a file, cached by (path, size, mtime): claim/validate/attempt each re-check a 50-100 MB clip.
    Any rewrite (re-render, sharpen via os.replace) changes mtime, so a changed file is always re-hashed."""
    path = Path(path)
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    cached = _DIGEST_CACHE.get(key)
    if cached:
        return cached
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    if len(_DIGEST_CACHE) > 512:
        _DIGEST_CACHE.clear()
    _DIGEST_CACHE[key] = digest.hexdigest()
    return _DIGEST_CACHE[key]


def _posting_ready(scope):
    require_active_for_new_work(scope)
    if scope.channel_id == "main" and not scope.strict and scope.is_implicit_default:
        return
    require_final_ready(scope)
    channel = scope.channel
    binding = channel.get("account_binding") or {}
    if binding.get("status") != "verified" or binding.get("verified_handle") != channel.get("handle"):
        raise ChannelError(409, "account_binding_unverified", "บัญชี TikTok ยังไม่ได้รับการยืนยันหรือ handle ไม่ตรงกับช่อง")
    if not channel.get("posting_enabled"):
        raise ChannelError(409, "posting_not_allowed", "ช่องนี้ยังไม่เปิดโพสต์")


def _canonical_job(scope, job_id, *, before_action=False):
    job = _jobs().get(scope.channel_id, job_id)
    export = ExportRegistry.lookup(export_id=job["export_id"], channel_id=scope.channel_id)
    require_record_owner(scope, export, resource_label="export ของงานโพสต์")
    if before_action:
        _posting_ready(scope)
        channel = scope.channel
        if int(channel.get("revision", 0)) != job["channel_revision"] or channel.get("handle") != job["target_handle"] or channel.get("account_binding", {}) != job["account_binding"]:
            raise ChannelError(409, "posting_binding_changed", "ตัวตนหรือบัญชีของช่องเปลี่ยนแล้ว ห้ามใช้ snapshot งานเก่าโพสต์")
        path = _resolve_under(str(export["path"]), [EXPORTS_DIR, POSTED_DIR])
        if path != Path(job["video_path"]).resolve() or _file_digest(path) != job["video_sha256"] or export.get("status") == "posted":
            raise ChannelError(409, "posting_export_changed", "ไฟล์ export เปลี่ยนหรือถูกโพสต์แล้ว ห้ามใช้ snapshot เก่า")
        if job.get("cover_path"):
            cover = _resolve_under(job["cover_path"], [COVERS_DIR])
            if _file_digest(cover) != job.get("cover_sha256"):
                raise ChannelError(409, "posting_cover_changed", "ไฟล์ปกเปลี่ยนแล้ว ห้ามใช้ snapshot งานเดิม")
    return job, export


def _validate_request_payload(req, job):
    if req.payload_hash != job["payload_hash"]:
        raise ChannelError(409, "posting_payload_changed", "ข้อมูล snapshot ของงานโพสต์ไม่ตรงกัน")


@router.get("/capabilities")
def capabilities():
    return {"protocol_version": PROTOCOL_VERSION, "durable_jobs": True,
            "job_scoped_ack": True, "account_guard": True}


LINKAGE_GRACE = timedelta(minutes=10)


@router.get("/linkage-due")
def linkage_due(scope: ChannelScope = Depends(get_workflow_scope)):
    """Scheduled posts whose slot passed (+10 min) and that are not yet linked to their TikTok video: the extension
    looks them up on the Content page (read-only) and closes them via /jobs/{id}/content-linkage."""
    scope = _actual_scope(scope)
    from scripts.publication_observations import PublicationObservationStore
    observations = PublicationObservationStore(BASE_DIR, jobs=_jobs())
    linked = {row["job_id"] for row in observations.table.scoped_load(scope.channel_id) if row.get("status") == "verified"}
    now = datetime.now(PROJECT_TZ)
    items = []
    for job in _jobs().table.scoped_load(scope.channel_id):
        if job.get("status") != "scheduled_on_platform" or job["id"] in linked or job.get("publication_observation_id"):
            continue
        if not (job.get("schedule_date") and job.get("schedule_time")):
            continue
        try:
            slot = datetime.strptime(f"{job['schedule_date']} {job['schedule_time']}", "%Y-%m-%d %H:%M").replace(tzinfo=PROJECT_TZ)
        except ValueError:
            continue
        if slot + LINKAGE_GRACE > now:
            continue
        items.append({"job_id": job["id"], "revision": job["revision"], "export_id": job.get("export_id"),
                      "caption": job.get("caption") or "", "hashtags": job.get("hashtags") or "",
                      "episode_no": job.get("episode_no"),
                      "schedule_date": job["schedule_date"], "schedule_time": job["schedule_time"],
                      "scheduled_at": slot.isoformat(timespec="minutes"),
                      "target_handle": job.get("target_handle") or ""})
    items.sort(key=lambda item: item["scheduled_at"])
    return {"items": items}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, scope: ChannelScope = Depends(get_workflow_scope)):
    job = _jobs().get(_actual_scope(scope).channel_id, job_id)
    return {key: value for key, value in job.items() if key != "lease_token"}


@router.post("/claim")
def claim_job(req: ClaimRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    scope = _actual_scope(scope)
    _canonical_job(scope, req.job_id, before_action=True)
    return _jobs().claim(scope.channel_id, req.job_id, req.lease_owner)


@router.post("/validate")
def validate_job(req: ActionRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    scope = _actual_scope(scope)
    job, _ = _canonical_job(scope, req.job_id, before_action=True)
    _validate_request_payload(req, job)
    return _jobs().validate_action(scope.channel_id, req.job_id, req.lease_owner, req.lease_token,
                                   req.expected_revision, req.source_account)


@router.post("/attempt")
def attempt_publish(req: ActionRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    scope = _actual_scope(scope)
    job, _ = _canonical_job(scope, req.job_id, before_action=True)
    _validate_request_payload(req, job)
    return _jobs().validate_action(scope.channel_id, req.job_id, req.lease_owner, req.lease_token,
                                   req.expected_revision, req.source_account, begin_publish=True,
                                   confirmation_token=req.confirmation_token, click_kind=req.click_kind)


@router.post("/release")
def release_job(req: ActionRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    scope = _actual_scope(scope)
    job = _jobs().get(scope.channel_id, req.job_id)
    _validate_request_payload(req, job)
    released = _jobs().release(scope.channel_id, req.job_id, req.lease_owner, req.lease_token, req.expected_revision, force=req.force)
    _reset_queue_row(scope, job)
    return released


def _apply_outcome_effects(scope, job):
    if job.get("effects_applied"):
        return job
    if job["status"] == "confirmation_unknown":
        # The post may or may not be live: show that on the queue row (so the next run does not pick the clip again and
        # the operator sees it) but touch nothing else and do not mark effects applied -- the final proof will.
        _mirror_unknown_to_queue(scope, job)
        return job
    # Re-read the canonical record on every retry; request data never selects
    # a path, caption, parent, or export here. Local effects are idempotent.
    _, export = _canonical_job(scope, job["job_id"])
    if job["status"] == "published":
        from scripts.api_exports import apply_posted_outcome, MarkPostedRequest
        current_path = Path(str(export["path"]))
        if not current_path.is_absolute():
            current_path = BASE_DIR / current_path
        # A crash after moving but before the registry update is recoverable
        # only at the canonical same-basename Posted destination, with digest.
        if not current_path.exists():
            candidate = POSTED_DIR / Path(job["video_path"]).name
            if candidate.is_file() and _file_digest(candidate) == job["video_sha256"]:
                ExportRegistry.update_path(job["export_id"], candidate, channel_id=scope.channel_id)
                current_path = candidate
        if not current_path.is_file() or _file_digest(current_path) != job["video_sha256"]:
            raise ChannelError(409, "posting_export_changed", "ไฟล์ยืนยันผลไม่ตรงกับ snapshot งานโพสต์")
        effect = apply_posted_outcome(MarkPostedRequest(file_path=str(current_path), export_id=job["export_id"],
                                      product_id=job.get("product_id"), angle_id=job.get("angle_id")), scope, job)
        if effect.get("status_warning") or effect.get("post_log_warning"):
            raise ChannelError(409, "posting_effects_pending", "TikTok ยืนยันแล้ว แต่ประวัติหรือสถานะยังบันทึกไม่ครบ ให้ส่งผลเดิมซ้ำเพื่อซ่อมบันทึก")
    if job.get("queue_id"):
        from scripts.schedule_store import ScheduleQueueStore
        def apply(row, _rows):
            if row.get("export_id") != job["export_id"]:
                raise ChannelError(409, "posting_parent_conflict", "คิวเปลี่ยน export ไปแล้ว จึงไม่แก้ผลของคลิปอื่น")
            if row.get("status") == "cancelled":
                raise ChannelError(409, "posting_queue_changed", "คิวเปลี่ยนงานหรือยกเลิกแล้ว ต้องตรวจผลก่อน")
            if row.get("posting_job_id") and row["posting_job_id"] != job["job_id"]:
                raise ChannelError(409, "posting_queue_changed", "คิวผูกกับงานอื่นแล้ว ต้องตรวจผลก่อน")
            row["status"] = {"published": "posted", "draft_saved": "draft_on_platform"}.get(job["status"], "scheduled_on_platform")
            if job["status"] == "draft_saved":
                # when the draft was saved: the "check against TikTok" never needs to look further back than this
                row["draft_saved_at"] = _now_iso()
            if job["status"] == "published":
                row["posted_at"] = row.get("posted_at") or _now_iso()
            row["posting_job_id"] = job["job_id"]
            row["updated_at"] = _now_iso()
        # A queue row that no longer exists is not a reason to keep the receipt pending forever: the post itself is
        # recorded on the job and the export; there is simply no row left to update.
        ScheduleQueueStore.update_item(job["queue_id"], apply, channel_id=scope.channel_id)
    elif job["status"] in {"scheduled_on_platform", "draft_saved"}:
        from scripts.schedule_store import ScheduleQueueStore, new_id, now_iso
        owner = ScheduleQueueStore.new_owner(channel_id=scope.channel_id)
        queue_id = new_id()
        sched_iso = None
        if job.get("schedule_date") and job.get("schedule_time"):
            # same minute-precision form as the queue's scheduled_iso(): slot checks compare these strings
            sched_iso = f"{job['schedule_date']}T{job['schedule_time']}+07:00"
        norm_video_path = str(job["video_path"]).replace("\\", "/")
        if "04_Exports/" in norm_video_path:
            norm_video_path = norm_video_path[norm_video_path.index("04_Exports/"):]
        queue_item = {
            "id": queue_id,
            "owner": owner,
            "channel_id": scope.channel_id,
            "export_id": job["export_id"],
            "video_path": norm_video_path,
            "video_key": f"export:{job['export_id']}",
            "product_id": job.get("product_id"),
            "product_name": job.get("product_name"),
            "angle_id": job.get("angle_id"),
            "project_name": (export or {}).get("project_name") or job.get("project_name"),
            "hook_title": (export or {}).get("hook_title") or job.get("hook_title"),
            "cover_path": _relative_cover_safe(job.get("cover_path")),
            "cover_url": _cover_media_url(_relative_cover_safe(job.get("cover_path"))),
            "cover_sha256": job.get("cover_sha256"),
            "caption": job.get("caption") or "",
            "hashtags": job.get("hashtags") or "",
            "tiktok_product_id": job.get("tiktok_product_id"),
            "status": "scheduled_on_platform" if job["status"] == "scheduled_on_platform" else "draft_on_platform",
            "scheduled_at": sched_iso,
            "posting_job_id": job["job_id"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        if job["status"] == "draft_saved":
            queue_item["draft_saved_at"] = now_iso()
        with ScheduleQueueStore.transaction(channel_id=scope.channel_id) as records:
            # Any still-open row of this export is THE row of this clip (a second row = a second post later).
            open_states = {"scheduled_on_platform", "draft_on_platform", "planned", "failed",
                           "ready_for_extension", "confirmation_unknown"}
            existing = next((r for r in records if r.get("posting_job_id") == job["job_id"]), None) or next(
                (r for r in records if r.get("export_id") == job["export_id"] and r.get("status") in open_states),
                None,
            )
            if existing:
                existing["status"] = queue_item["status"]
                existing["posting_job_id"] = job["job_id"]
                if sched_iso:
                    existing["scheduled_at"] = sched_iso
                if job["status"] == "draft_saved":
                    existing["draft_saved_at"] = queue_item["draft_saved_at"]
                existing["updated_at"] = now_iso()
                queue_id = existing["id"]
            else:
                records.append(queue_item)
        with _jobs().table.scoped_mutate(scope.channel_id) as job_rows:
            target_job = next((r for r in job_rows if r["id"] == job["job_id"]), None)
            if target_job:
                target_job["queue_id"] = queue_id
        job["queue_id"] = queue_id
    if job.get("intent") == "publish_draft" and job.get("draft_source_job_id") and job["status"] in {"published", "scheduled_on_platform"}:
        # the draft was consumed by this publication: retire its job record (idempotent, never touches a non-draft job)
        try:
            _jobs().release_draft(scope.channel_id, job["draft_source_job_id"], reason="published_from_draft")
        except ChannelError:
            pass
    return _jobs().mark_effects_applied(scope.channel_id, job["job_id"])


def _mirror_unknown_to_queue(scope, job):
    if not job.get("queue_id"):
        return
    from scripts.schedule_store import ScheduleQueueStore

    def mark(row, _rows):
        if row.get("export_id") != job["export_id"] or row.get("status") in {"cancelled", "posted"}:
            return
        if row.get("posting_job_id") and row["posting_job_id"] != job["job_id"]:
            return
        row["status"] = "confirmation_unknown"
        row["posting_job_id"] = job["job_id"]
        row["updated_at"] = _now_iso()
    ScheduleQueueStore.update_item(job["queue_id"], mark, channel_id=scope.channel_id)


def _ack(req, scope, *, reconcile=False):
    scope = _actual_scope(scope)
    job, _ = _canonical_job(scope, req.job_id)
    _validate_request_payload(req, job)
    # Accepted proof contains no caller-selected link/path/caption identities.
    if set(req.proof) - {"kind", "notice", "platform_post_id", "confirmation_token"}:
        raise ChannelError(422, "posting_proof_invalid", "หลักฐานผลโพสต์มีข้อมูลที่ไม่อนุญาต")
    if req.proof.get("platform_post_id") and not re.fullmatch(r"[0-9]{8,32}", str(req.proof["platform_post_id"])):
        raise ChannelError(422, "posting_proof_invalid", "รหัสโพสต์จาก TikTok ไม่ถูกต้อง")
    job = _jobs().acknowledge(scope.channel_id, req.job_id, req.lease_owner, req.lease_token,
                              req.expected_revision, req.source_account, req.outcome, req.proof, reconcile=reconcile)
    return _apply_outcome_effects(scope, job)


@router.post("/ack")
def acknowledge_job(req: OutcomeRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    return _ack(req, scope)


@router.post("/reconcile")
def reconcile_job(req: OutcomeRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    # Reconciliation only records an already-attempted result. It cannot
    # grant a new publish lease or return the job to the prepared queue.
    return _ack(req, scope, reconcile=True)


class AutomationSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel_id: Optional[str] = None
    enabled: Optional[bool] = None
    mode: Optional[Literal["hybrid", "schedule", "due_now"]] = None
    poll_interval_sec: Optional[int] = Field(default=None, ge=10, le=3600)
    due_window_before_min: Optional[int] = Field(default=None, ge=0, le=120)
    due_window_after_min: Optional[int] = Field(default=None, ge=1, le=240)


class TriggerRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel_id: Optional[str] = None
    mode: Literal["hybrid", "schedule", "due_now"] = "hybrid"
    limit: int = Field(default=5, ge=1, le=30)
    all_channels: bool = False


def _sanitize_job(job: dict) -> dict:
    return {key: value for key, value in job.items() if key != "lease_token"}


def _target_channel_id(channel_id: Optional[str], scope: ChannelScope) -> str:
    if channel_id:
        from scripts.channel_store import get_default_store, is_valid_channel_id
        if not is_valid_channel_id(channel_id):
            raise ChannelError(422, "invalid_channel_id", "รหัสช่องไม่ถูกต้อง")
        if channel_id != "main" and get_default_store().find(channel_id) is None:
            raise ChannelError(404, "channel_not_found", f"ไม่พบช่อง {channel_id}")
        return channel_id
    return _actual_scope(scope).channel_id


@router.get("/automation-status")
def get_automation_status(
    channel_id: Optional[str] = None,
    scope: ChannelScope = Depends(get_workflow_scope),
):
    from scripts.autopost_scheduler import (
        get_automation_settings_store,
        is_conductor_running,
        is_due_now,
        read_conductor_state,
    )
    from scripts.schedule_store import ScheduleQueueStore

    target_channel = _target_channel_id(channel_id, scope)
    settings = get_automation_settings_store().get(target_channel)
    items = ScheduleQueueStore.list_items(channel_id=target_channel)
    now = datetime.now(PROJECT_TZ)
    before_min = int(settings.get("due_window_before_min", 5))
    after_min = int(settings.get("due_window_after_min", 30))

    queue_counts = {
        "planned": sum(1 for r in items if r.get("status") == "planned"),
        "ready_for_extension": sum(1 for r in items if r.get("status") == "ready_for_extension"),
        "scheduled_on_platform": sum(1 for r in items if r.get("status") == "scheduled_on_platform"),
        "posted": sum(1 for r in items if r.get("status") == "posted"),
        "failed": sum(1 for r in items if r.get("status") == "failed"),
        "due_now_count": sum(
            1 for r in items if is_due_now(r, now=now, before_min=before_min, after_min=after_min)
        ),
    }

    job_rows = _jobs().table.scoped_load(target_channel)
    active_jobs = [
        _sanitize_job(r) for r in job_rows if r.get("status") in {"prepared", "claimed", "publishing"}
    ]
    recent_jobs = [
        _sanitize_job(r)
        for r in sorted(
            job_rows,
            key=lambda r: (str(r.get("updated_at") or ""), str(r.get("created_at") or "")),
            reverse=True,
        )[:10]
    ]

    conductor_state = read_conductor_state(BASE_DIR)
    running, running_pid = is_conductor_running(BASE_DIR)
    if conductor_state is not None:
        conductor_state = {**conductor_state, "running": running, "pid": running_pid or conductor_state.get("pid")}

    return {
        "channel_id": target_channel,
        "queue_counts": queue_counts,
        "active_jobs": active_jobs,
        "recent_jobs": recent_jobs,
        "conductor_state": conductor_state,
        "automation_settings": settings,
    }


@router.get("/automation-settings")
def get_automation_settings(
    channel_id: Optional[str] = None,
    scope: ChannelScope = Depends(get_workflow_scope),
):
    from scripts.autopost_scheduler import get_automation_settings_store

    target_channel = _target_channel_id(channel_id, scope)
    return get_automation_settings_store().get(target_channel)


@router.put("/automation-settings")
def update_automation_settings(
    req: AutomationSettingsUpdate,
    channel_id: Optional[str] = None,
    scope: ChannelScope = Depends(get_workflow_scope),
):
    from scripts.autopost_scheduler import get_automation_settings_store

    target_channel = _target_channel_id(req.channel_id or channel_id, scope)
    patch = req.model_dump(exclude_none=True, exclude={"channel_id"})
    return get_automation_settings_store().put(target_channel, patch)


@router.post("/trigger-run")
def trigger_conductor_run(
    req: TriggerRunRequest,
    scope: ChannelScope = Depends(get_workflow_scope),
):
    from scripts.autopost_scheduler import spawn_conductor

    target_channel = _target_channel_id(req.channel_id, scope)
    return spawn_conductor(
        mode=req.mode,
        channel_id=target_channel,
        limit=req.limit,
        all_channels=req.all_channels,
        root=BASE_DIR,
    )
