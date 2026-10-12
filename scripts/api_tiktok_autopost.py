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
from datetime import datetime
from pathlib import Path
import json
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field
from hashlib import sha256
from scripts import config
from scripts.channel_scope import ChannelScope, ensure_same_channel, require_active_for_new_work, require_final_ready, resolve_scope
from scripts.channel_route_policy import UNLISTED_ROUTE_POLICY
from scripts.channel_workflows import get_workflow_scope, require_record_owner, require_project_owner
from scripts.channel_store import ChannelError, normalize_handle
from scripts.posting_jobs import PostingJobStore, PROTOCOL_VERSION, account_check

from scripts.config import BASE_DIR, EXPORTS_DIR
from scripts.product_store import ProductStore
from scripts.export_registry import ExportRegistry
from scripts.export_cover_bindings import ExportCoverBindingStore

POSTED_DIR = BASE_DIR / "04_Exports" / "Posted"
COVERS_DIR = BASE_DIR / "05_Covers_Thumbnails"

router = APIRouter(prefix="/api/tiktok-autopost", tags=["tiktok-autopost"])

_pending: Optional[dict] = None


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


class OutcomeRequest(ActionRequest):
    outcome: str
    proof: dict = Field(default_factory=dict)


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
    if req.queue_id:
        from scripts.schedule_store import ScheduleQueueStore
        queue = ScheduleQueueStore.get_item(req.queue_id, channel_id=channel_id)
        require_record_owner(scope, queue, resource_label="คิวโพสต์")
        if queue.get("export_id") != export_record["id"]:
            raise ChannelError(409, "posting_parent_conflict", "คิวไม่ตรงกับ export ที่เลือก")
    latest_record = ExportRegistry.latest_for_angle(product_id, angle_id, channel_id=channel_id)
    if latest_record and latest_record.get("id") != export_record.get("id"):
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
    if cover_abs and channel_id != "main" and not _is_contained(cover_abs, (COVERS_DIR / channel_id).resolve()):
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
    payload = {
        "video_path": str(video_abs),
        "export_id": export_record.get("id"),
        "cover_path": str(cover_abs) if cover_abs else None,
        "caption": req.caption,
        "hashtags": req.hashtags,
        "product_id": product_id,
        "angle_id": angle_id,
        "tiktok_product_id": req.tiktok_product_id,
        "product_name": req.product_name,
        "schedule_date": req.schedule_date,
        "schedule_time": req.schedule_time,
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
    _pending = job  # Legacy read cache only; never used to authorize an effect.
    if req.queue_id:
        try:
            from scripts.schedule_store import ScheduleQueueStore

            def _mark_ready(row, _records):
                if row.get("export_id") != job["export_id"]:
                    raise ChannelError(409, "posting_parent_conflict", "คิวเปลี่ยน export ระหว่างเตรียมงานแล้ว จึงไม่ผูกงานผิดคลิป")
                if row.get("status") not in {"planned", "failed"} and not (
                        row.get("status") == "ready_for_extension" and row.get("posting_job_id") == job["job_id"]):
                    raise ChannelError(409, "posting_queue_changed", "คิวเปลี่ยนสถานะแล้ว จึงไม่ทับงานอื่น")
                row["status"] = "ready_for_extension"
                row["posting_job_id"] = job["job_id"]
                row["extension_prepared_at"] = datetime.now().isoformat()
                row["updated_at"] = datetime.now().isoformat()

            result = ScheduleQueueStore.update_item(req.queue_id, _mark_ready, channel_id=channel_id)
            if result is None:
                raise ChannelError(404, "resource_not_found", "คิวถูกลบก่อนผูกงานโพสต์")
            job = _jobs().mark_prepare_effects(channel_id, job["job_id"])
            _pending = job
        except Exception as exc:
            _jobs().mark_prepare_effects(channel_id, job["job_id"], error=type(exc).__name__)
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
    cover_abs = _prefer_3x4_cover(_resolve_under(req.cover_path, [COVERS_DIR]))
    if scope.channel_id != "main" and not _is_contained(cover_abs, (COVERS_DIR / scope.channel_id).resolve()):
        raise ChannelError(404, "resource_not_found", "ไฟล์ปกนี้ไม่อยู่ในช่องของงาน")
    _jobs().update_cover(scope.channel_id, job["job_id"], str(cover_abs), cover_sha256=_file_digest(cover_abs))
    return {"success": True, "cover_path": str(cover_abs)}


@router.get("/pending")
def get_pending(scope: ChannelScope = Depends(get_workflow_scope)):
    """Polled by the extension's popup/background worker. 404 means
    "nothing prepared yet" -- the extension should tell the user to click
    the app's button first rather than silently doing nothing."""
    scope = _actual_scope(scope)
    job = _jobs().pending(scope.channel_id)
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
    _jobs().cancel(scope.channel_id, req.job_id)
    if _pending and _pending.get("job_id") == req.job_id:
        _pending = None
    return {"success": True}


def _actual_scope(scope):
    return scope if isinstance(scope, ChannelScope) else resolve_scope(
        header_values=[], query_values=[], policy=UNLISTED_ROUTE_POLICY)


def _jobs():
    return PostingJobStore(BASE_DIR)


def _file_digest(path):
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
                                   confirmation_token=req.confirmation_token)


@router.post("/release")
def release_job(req: ActionRequest, scope: ChannelScope = Depends(get_workflow_scope)):
    scope = _actual_scope(scope)
    job = _jobs().get(scope.channel_id, req.job_id)
    _validate_request_payload(req, job)
    released = _jobs().release(scope.channel_id, req.job_id, req.lease_owner, req.lease_token, req.expected_revision)
    if job.get("queue_id"):
        from scripts.schedule_store import ScheduleQueueStore
        def reset(row, _rows):
            if row.get("posting_job_id") == job["job_id"] and row.get("status") == "ready_for_extension":
                row["status"] = "planned"
                row.pop("posting_job_id", None)
                row["updated_at"] = datetime.now().isoformat()
        ScheduleQueueStore.update_item(job["queue_id"], reset, channel_id=scope.channel_id)
    return released


def _apply_outcome_effects(scope, job):
    if job.get("effects_applied") or job["status"] == "confirmation_unknown":
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
            if row.get("posting_job_id") != job["job_id"] or row.get("status") == "cancelled":
                raise ChannelError(409, "posting_queue_changed", "คิวเปลี่ยนงานหรือยกเลิกแล้ว ต้องตรวจผลก่อน")
            row["status"] = "posted" if job["status"] == "published" else "scheduled_on_platform"
            row["posting_job_id"] = job["job_id"]
        if ScheduleQueueStore.update_item(job["queue_id"], apply, channel_id=scope.channel_id) is None:
            raise ChannelError(404, "posting_queue_missing", "ไม่พบคิวเดิม จึงยังบันทึกผลคิวไม่สำเร็จ")
    return _jobs().mark_effects_applied(scope.channel_id, job["job_id"])


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
