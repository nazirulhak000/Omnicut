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
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.config import BASE_DIR, EXPORTS_DIR
from scripts.product_store import ProductStore
from scripts.export_registry import ExportRegistry

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


def _cover_names_for_job(video_abs: Path, product_id: str = "", angle_id: str = "", product_name: str = "") -> list[str]:
    """Return deterministic project/product stems that may own this cover."""
    names: list[str] = [video_abs.stem, _TIMESTAMP_SUFFIX.sub("", video_abs.stem)]
    try:
        products = ProductStore.get_all()
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


def _resolve_cover_for_job(video_abs: Path, *, product_id: str = "", angle_id: str = "", product_name: str = "") -> Optional[Path]:
    for stem in _cover_names_for_job(video_abs, product_id, angle_id, product_name):
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


class CoverUpdateRequest(BaseModel):
    cover_path: str


@router.post("/prepare")
def prepare(req: PrepareRequest):
    """Called by the app's Post Studio panel. Validates + resolves both
    paths to absolute OS paths (chrome.debugger's DOM.setFileInputFiles
    needs a real filesystem path, not a URL) and stashes them for the
    extension to pick up next."""
    video_abs = _resolve_under(req.video_path, [EXPORTS_DIR, POSTED_DIR])
    export_record = ExportRegistry.get(req.export_id) if req.export_id else ExportRegistry.find_by_path(video_abs)
    if req.export_id and export_record is None:
        raise HTTPException(status_code=409, detail="ไม่พบ export_id ที่ระบุ จึงหยุดการเตรียมโพสต์เพื่อป้องกันการเลือกคลิปผิดตัว")
    if export_record is None:
        try:
            export_record = ExportRegistry.ensure(
                video_abs,
                product_id=req.product_id,
                angle_id=req.angle_id,
            )
        except ValueError:
            # Test/embedded callers may mount a temporary BASE_DIR in this
            # router while the registry still points at the production root.
            # Keep the legacy path-only handoff for that isolated case; the
            # real application uses one shared BASE_DIR and always gets an ID.
            export_record = {"id": None, "path": str(video_abs)}
    registered = Path(str(export_record.get("path") or ""))
    if not registered.is_absolute():
        registered = (BASE_DIR / registered).resolve()
    else:
        registered = registered.resolve()
    if registered != video_abs.resolve():
        raise HTTPException(status_code=409, detail="export_id ไม่ตรงกับไฟล์ที่เลือก")
    if export_record.get("status") == "posted":
        raise HTTPException(status_code=409, detail="คลิปนี้ถูกโพสต์ไปแล้ว ไม่ต้องส่งเข้า Extension ซ้ำ")
    latest_record = ExportRegistry.latest_for_angle(req.product_id, req.angle_id)
    if latest_record and latest_record.get("id") != export_record.get("id"):
        raise HTTPException(
            status_code=409,
            detail="ไฟล์นี้ไม่ใช่ export เวอร์ชันล่าสุดของมุมนี้ กรุณาเลือกคลิปล่าสุด",
        )
    cover_abs = _resolve_under(req.cover_path, [COVERS_DIR]) if req.cover_path else None
    cover_abs = _prefer_3x4_cover(cover_abs)
    if cover_abs is None:
        cover_abs = _resolve_cover_for_job(
            video_abs,
            product_id=req.product_id or "",
            angle_id=req.angle_id or "",
            product_name=req.product_name or "",
        )

    global _pending
    _pending = {
        "video_path": str(video_abs),
        "export_id": export_record.get("id"),
        "cover_path": str(cover_abs) if cover_abs else None,
        "caption": req.caption,
        "hashtags": req.hashtags,
        "product_id": req.product_id,
        "angle_id": req.angle_id,
        "tiktok_product_id": req.tiktok_product_id,
        "product_name": req.product_name,
        "schedule_date": req.schedule_date,
        "schedule_time": req.schedule_time,
        "prepared_at": datetime.now().isoformat(),
    }
    if req.queue_id:
        try:
            from scripts.schedule_store import ScheduleQueueStore
            with ScheduleQueueStore._mutate() as records:
                row = next((item for item in records if item.get("id") == req.queue_id), None)
                if row:
                    row["status"] = "ready_for_extension"
                    row["extension_prepared_at"] = datetime.now().isoformat()
                    row["updated_at"] = datetime.now().isoformat()
        except Exception:
            # The post handoff itself is already prepared; an optional queue
            # mirror must never prevent the extension from continuing.
            pass
    return {"success": True, "cover_path": _relative_cover(cover_abs)}


@router.post("/cover")
def update_cover(req: CoverUpdateRequest):
    """Refresh the cover on the already-prepared job.

    The editor can save a new cover after the extension job was prepared.
    Resolve and validate the path before mutating the in-memory job so a
    failed refresh never destroys the previous valid cover.
    """
    if _pending is None:
        raise HTTPException(status_code=404, detail="ยังไม่มีคลิปที่เตรียมไว้")
    cover_abs = _prefer_3x4_cover(_resolve_under(req.cover_path, [COVERS_DIR]))
    _pending["cover_path"] = str(cover_abs)
    return {"success": True, "cover_path": str(cover_abs)}


@router.get("/pending")
def get_pending():
    """Polled by the extension's popup/background worker. 404 means
    "nothing prepared yet" -- the extension should tell the user to click
    the app's button first rather than silently doing nothing."""
    if _pending is None:
        raise HTTPException(status_code=404, detail="ยังไม่มีคลิปที่เตรียมไว้ -- กด 'โพสต์ TikTok อัตโนมัติ' ในแอปก่อน")
    _repair_pending_cover()
    return _pending


@router.post("/clear")
def clear_pending():
    """Called by the extension once it has consumed the job (success or
    failure) so a stale job never gets replayed by mistake."""
    global _pending
    _pending = None
    return {"success": True}
