"""
Batch Render Engine & Queue Worker for OmniCut Pro Studio.

Batches are admitted one at a time by a single durable FIFO dispatcher.
Inside a batch, angles render concurrently on a ThreadPoolExecutor
(``BATCH_MAX_WORKERS``, AGENTS rule 24) in waves: each wave holds the global
render slot (``render_jobs.render_slot``) once, so single renders and
re-rolls still queue behind it and ``render_jobs.is_busy()`` stays truthful.
Items whose MP4 was already produced for this batch (``is_valid_mp4``) are
skipped on resume. All shared batch state is mutated under ``_BATCH_LOCK``;
the lock is never held while a clip renders.
"""

import glob
import json
import re
import shutil
import subprocess
import sys
import uuid
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, Iterator, List, Optional

from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import BASE_DIR, RAW_DIR, INBOX_DIR, EXPORTS_DIR, STICKERS_DIR, PROJECTS_DIR
from scripts.product_store import ProductStore
from scripts.task_manager import TaskManager
from scripts.batch_queue_store import BatchQueueStore
from scripts import batch_queue_store as _batch_queue_store
from scripts import maintenance_lock
from scripts import render_jobs
from scripts.render_jobs import RenderCancelled
from scripts.pipeline import TikTokAutoCutterPipeline
from scripts.overlay_model import template_for_style_preset, template_for_ad_tone, guess_brand_model
from scripts.api_render import check_disk_space
from scripts.style_motion_policy import STYLE_MOTION_POLICIES

logger = logging.getLogger("batch_render")

# AGENTS rule 24: batch work runs on 4 concurrent workers by default.
BATCH_MAX_WORKERS = 4
# An output smaller than this is treated as truncated/broken.
MIN_VALID_MP4_BYTES = 1024 * 1024
DEFAULT_BATCH_STYLE = "clean_tech_review"
# Batch picker values that mean "no explicit choice, use each angle's default".
AUTO_STYLE_VALUES = frozenset({"", "auto"})
# How long a wave waits before retrying when the render queue is full (429).
_SLOT_RETRY_SECONDS = 2.0


def _maintenance_root() -> Path:
    """Data root of the batch queue (maintenance lock lives at <root>/_Docs)."""
    return Path(_batch_queue_store.BATCH_QUEUE_PATH).parent.parent

# Default style preset per script angle: the 10 classic angles plus every IT
# angle key in scripts/it_angles.py. Must stay identical to
# ANGLE_TO_DEFAULT_STYLE in frontend/src/lib/stylePresetCatalog.js
# (enforced by tests/test_style_preset_consistency.py).
ANGLE_TO_DEFAULT_STYLE: Dict[str, str] = {
    "stop_scroll": "viral_punch",
    "fomo_deal": "flash_deal",
    "pain_point": "pain_punch",
    "spec_review": "clean_tech_review",
    "comparison": "tech_compare",
    "unboxing": "tech_product_showcase",
    "life_hack": "smart_hack",
    "niche_target": "niche_focus",
    "longterm_review": "smooth_showcase",
    "math_value": "premium_minimal",
    "spec_compare": "tech_compare",
    "fake_vs_real": "viral_punch",
    "real_test": "tech_product_showcase",
    "spec_explained": "niche_focus",
    "dont_cheap_out": "pain_punch",
    "how_to_setup": "smart_hack",
    "worth_upgrade": "premium_minimal",
}


def _known_style(value: Any) -> Optional[str]:
    """Return a renderer-supported preset id, or None for auto/unknown values."""
    key = str(value or "").strip().lower()
    if key in AUTO_STYLE_VALUES:
        return None
    return key if key in STYLE_MOTION_POLICIES else None


def default_style_for_angle(angle_data: Dict[str, Any]) -> Optional[str]:
    """Recommended preset for an angle (accepts angle_key/angle_id, ``_bN`` suffix)."""
    for raw in (angle_data.get("angle_key"), angle_data.get("angle_id"), angle_data.get("id")):
        key = str(raw or "").strip().lower()
        if not key:
            continue
        style = ANGLE_TO_DEFAULT_STYLE.get(key) or ANGLE_TO_DEFAULT_STYLE.get(re.sub(r"_b\d+$", "", key))
        if style:
            return style
    return None


def resolve_batch_style_preset(angle_data: Dict[str, Any], options: Dict[str, Any]) -> str:
    """Style for one batch item.

    An explicit preset chosen in the batch modal wins; ``auto``/empty/unknown
    values (including the legacy ``commercial_premium``) mean "no choice" and
    fall through to the angle's own preset, then the angle default.
    """
    return (
        _known_style(options.get("style_preset"))
        or _known_style(angle_data.get("style_preset"))
        or default_style_for_angle(angle_data)
        or DEFAULT_BATCH_STYLE
    )


def _ffprobe_binary() -> Optional[str]:
    return shutil.which("ffprobe")


def _run_ffprobe(command: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, timeout=30)


def _has_mp4_atoms(path: Path) -> bool:
    """Fallback when ffprobe is unavailable: ISO BMFF header plus a moov atom."""
    try:
        size = path.stat().st_size
        window = 4 * 1024 * 1024
        with open(path, "rb") as handle:
            head = handle.read(window)
            if b"ftyp" not in head[:64]:
                return False
            if b"moov" in head:
                return True
            handle.seek(max(0, size - window))
            return b"moov" in handle.read(window)
    except OSError:
        return False


def is_valid_mp4(path: Any) -> bool:
    """True when ``path`` is a finished MP4: > 1MB, has a video stream, duration > 0.

    Uses ffprobe; if ffprobe is not installed it falls back to an MP4 atom
    check instead of failing, so a missing tool never blocks a batch.
    """
    try:
        p = Path(path)
        if not p.is_file() or p.stat().st_size <= MIN_VALID_MP4_BYTES:
            return False
    except (OSError, TypeError, ValueError):
        return False

    ffprobe = _ffprobe_binary()
    if not ffprobe:
        logger.warning("[BatchRender] ไม่พบ ffprobe ตรวจไฟล์ %s ด้วยโครงสร้าง MP4 แทน", p.name)
        return _has_mp4_atoms(p)
    command = [
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_type:format=duration",
        "-of", "json", str(p),
    ]
    try:
        proc = _run_ffprobe(command)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("[BatchRender] ffprobe ตรวจไฟล์ %s ไม่สำเร็จ: %s", p.name, exc)
        return False
    if proc.returncode != 0:
        return False
    try:
        data = json.loads(proc.stdout or "{}")
        duration = float((data.get("format") or {}).get("duration") or 0)
    except (ValueError, TypeError, AttributeError):
        return False
    has_video = any((s or {}).get("codec_type") == "video" for s in (data.get("streams") or []))
    return has_video and duration > 0

ANGLE_SLUG_MAP: Dict[str, str] = {
    "spec_review": "รีวิวสเปก",
    "unboxing": "แกะกล่องว้าว",
    "pain_point": "ปัญหาก่อนใช้",
    "fomo_deal": "โปรไฟลุก",
    "comparison": "เทียบของเดิม",
    "life_hack": "ทริกลึก",
    "stop_scroll": "เตือนภัย",
    "niche_target": "เจาะกลุ่ม",
    "longterm_review": "รีวิวใช้จริง",
    "math_value": "คำนวณคุ้มค่า",
}


def synthesize_project_name(
    product_code: str = "",
    product_title: str = "",
    angle_id: str = "",
    angle_name: str = "",
    existing_dirs: Optional[List[str]] = None,
    batch: Optional[int] = None,
) -> str:
    """
    Builds a collision-free project name matching the system standard:
    [product_code]-[angle_slug]_[index] (e.g. "BCD01-รีวิวสเปก_1")
    or falls back to [short_prod]_[angle_slug]_[index] if product_code is missing.
    """
    import re
    code_part = (product_code or "").strip().upper()
    clean_aid = (angle_id or "").strip().lower()
    base_aid = re.sub(r'_b\d+$', '', clean_aid)

    angle_slug = ANGLE_SLUG_MAP.get(clean_aid) or ANGLE_SLUG_MAP.get(base_aid)
    if not angle_slug:
        raw = angle_name or angle_id or "มุม1"
        cleaned = re.sub(r'[\uFE00-\uFE0F]', '', raw)
        cleaned = re.sub(r'\.{2,}|…', ' ', cleaned)
        cleaned = re.sub(r'[^\wก-๙\s_-]', ' ', cleaned).strip()
        words = [w for w in cleaned.split() if w]
        angle_slug = "_".join(words[:2]) if words else "มุม1"

    if code_part:
        base = f"{code_part}-{angle_slug}"
    else:
        cleaned_p = re.sub(r'\[[^\]]*\]', ' ', product_title or '')
        cleaned_p = re.sub(r'\([^)]*\)', ' ', cleaned_p)
        words_p = [w for w in re.sub(r'[^\wก-๙\s_-]', ' ', cleaned_p).strip().split() if w]
        short_prod = "_".join(words_p[:3]).lower() if words_p else "video"
        base = f"{short_prod}_{angle_slug}"

    if batch is None:
        m = re.search(r'_b(\d+)$', clean_aid)
        if m:
            batch = int(m.group(1))

    version = max(1, int(batch) if batch is not None else 1)
    while True:
        candidate = f"{base}_{version}"
        if existing_dirs is not None:
            if candidate not in existing_dirs:
                return candidate
        else:
            if not (PROJECTS_DIR / candidate).exists():
                return candidate
        version += 1


_BATCH_LOCK = threading.RLock()
BATCH_REGISTRY: Dict[str, Dict[str, Any]] = {}
_DISPATCHER_LOCK = threading.Lock()
_DISPATCHER_THREAD: Optional[threading.Thread] = None


class BatchRenderManager:
    """Manages batch video rendering jobs and background execution queues."""

    @classmethod
    def _persist_batch(cls, batch: Dict[str, Any]) -> None:
        """Checkpoint state transitions; live progress stays in memory."""
        snapshot = dict(batch)
        # DocumentTable's durable identity is named ``id``. Keep the public
        # batch_id contract unchanged while mirroring that same value here.
        snapshot["id"] = str(snapshot["batch_id"])
        snapshot["items"] = [dict(item) for item in batch.get("items", [])]
        with BatchQueueStore.mutate() as records:
            for index, row in enumerate(records):
                if row.get("batch_id") == snapshot.get("batch_id"):
                    records[index] = snapshot
                    break
            else:
                records.append(snapshot)

    @classmethod
    def _load_persisted_batch(cls, batch_id: str) -> Optional[Dict[str, Any]]:
        for row in BatchQueueStore.load():
            if row.get("batch_id") == batch_id:
                return row
        return None

    @classmethod
    def _next_queued_batch_id(cls) -> Optional[str]:
        candidates = [
            row for row in BatchQueueStore.load()
            if row.get("status") == "queued" and not row.get("cancelled")
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda row: (row.get("created_at", 0), row.get("batch_id", "")))
        return str(candidates[0]["batch_id"])

    @classmethod
    def _ensure_dispatcher(cls) -> None:
        """Start at most one FIFO dispatcher, regardless of batch count."""
        global _DISPATCHER_THREAD
        with _DISPATCHER_LOCK:
            if _DISPATCHER_THREAD and _DISPATCHER_THREAD.is_alive():
                return
            _DISPATCHER_THREAD = threading.Thread(
                target=cls._dispatch_pending_batches,
                daemon=True,
                name="batch_render_dispatcher",
            )
            _DISPATCHER_THREAD.start()

    @classmethod
    def _dispatch_pending_batches(cls) -> None:
        global _DISPATCHER_THREAD
        while True:
            if maintenance_lock.is_blocked(_maintenance_root()):
                # Maintenance mode: start no new batch; queued ones stay
                # queued and are picked up again by recovery after it ends.
                with _DISPATCHER_LOCK:
                    if _DISPATCHER_THREAD is threading.current_thread():
                        _DISPATCHER_THREAD = None
                logger.warning("[BatchRender] maintenance mode: หยุดเริ่ม batch ใหม่ชั่วคราว")
                return
            batch_id = cls._next_queued_batch_id()
            if not batch_id:
                # `_ensure_dispatcher()` can see this thread alive between
                # the empty lookup above and `return`, then leave a newly
                # enqueued batch with no worker. Recheck while holding the
                # same lock used by the starter before declaring idle.
                with _DISPATCHER_LOCK:
                    batch_id = cls._next_queued_batch_id()
                    if not batch_id:
                        if _DISPATCHER_THREAD is threading.current_thread():
                            _DISPATCHER_THREAD = None
                        return
            cls._run_batch_worker(batch_id)

    @classmethod
    def recover_pending_batches(cls) -> int:
        """Requeue interrupted work after a restart without redoing completed items."""
        if maintenance_lock.is_blocked(_maintenance_root()):
            logger.warning("[BatchRender] maintenance mode: ข้ามการกู้คิว batch จนกว่าจะย้ายข้อมูลเสร็จ")
            return 0
        recovered = 0
        for batch in BatchQueueStore.load():
            if batch.get("status") not in ("queued", "processing") or batch.get("cancelled"):
                continue
            batch["status"] = "queued"
            for item in batch.get("items", []):
                if item.get("status") == "in_production":
                    item["status"] = "queued"
                    item["error"] = "เซิร์ฟเวอร์รีสตาร์ท — นำกลับเข้าคิวเพื่อทำใหม่"
            with _BATCH_LOCK:
                BATCH_REGISTRY[batch["batch_id"]] = batch
            cls._persist_batch(batch)
            recovered += 1
        if recovered:
            cls._ensure_dispatcher()
        return recovered

    @classmethod
    def create_batch(
        cls,
        product_id: str,
        angle_ids: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
        *, channel_id: Optional[str] = None, job_scope: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validates product angles and enqueues a batch render job."""
        maintenance_lock.refuse_new_job(_maintenance_root(), job_label="batch render ใหม่")
        pinned = render_jobs.pin_job_scope(channel_id, job_scope)
        channel_kwargs = {"channel_id": pinned["channel_id"]} if pinned.get("channel_id") else {}
        product = ProductStore.get(product_id, **channel_kwargs)
        if not product:
            raise ValueError(f"ไม่พบข้อมูลสินค้า id '{product_id}'")

        from copy import deepcopy
        options = deepcopy(options or {})
        from scripts.pipeline_context import channel_project_name
        if pinned.get("channel_id"):
            if options.get("project_name"):
                options["project_name"] = channel_project_name(options["project_name"], pinned["channel_id"])
            options["angle_project_names"] = {
                aid: channel_project_name(name, pinned["channel_id"])
                for aid, name in (options.get("angle_project_names") or {}).items()
            }
        batch_index = options.get("batch_index")
        all_angles = product.get("angles", [])
        if batch_index is not None:
            all_angles = [a for a in all_angles if (a.get("batch") or 1) == batch_index]
        if not all_angles:
            raise ValueError("สินค้านี้ยังไม่มีมุมมอง (Angles) สำหรับเรนเดอร์")

        # Filter target angles
        target_angles: List[Dict[str, Any]] = []
        if angle_ids:
            angle_id_set = set(str(aid) for aid in angle_ids)
            for a in all_angles:
                aid = str(a.get("angle_id") or a.get("id") or "")
                if aid in angle_id_set:
                    target_angles.append(a)
        else:
            # Default: all angles that are not already posted
            for a in all_angles:
                if a.get("status") != "posted" and not a.get("posted_at"):
                    target_angles.append(a)

        if not target_angles:
            raise ValueError("ไม่มีมุมมองที่สามารถเรนเดอร์ได้ (อาจถูกโพสต์แล้วทั้งหมด)")
        if pinned.get("channel_id"):
            for angle in target_angles:
                if angle.get("project_name"):
                    channel_project_name(angle["project_name"], pinned["channel_id"])

        # Verify disk space (lower threshold if draft-only since no MP4 is produced)
        is_draft = not options.get("export_mp4", True)
        disk = check_disk_space(EXPORTS_DIR)
        min_required = 0.5 if is_draft else 3.0
        if disk.get("error") or disk.get("free_gb") is None and not disk.get("is_sufficient", True):
            raise RuntimeError("ตรวจสอบพื้นที่ว่างก่อนเริ่มคิวไม่ได้ จึงหยุดการเรนเดอร์")
        if not disk.get("is_sufficient", True) and disk.get("free_gb", 0) < min_required:
            free_gb = disk.get("free_gb", 0)
            raise RuntimeError(
                f"พื้นที่ว่างบนดิสก์เหลือน้อยเกินไป ({free_gb} GB เหลืออยู่, ต้องการขั้นต่ำ {min_required} GB)"
            )

        batch_id = str(uuid.uuid4())
        product_title = product.get("title") or product.get("name") or "สินค้า"

        items = []
        for a in target_angles:
            aid = str(a.get("angle_id") or a.get("id") or "")
            aname = a.get("angle_name") or f"มุมมอง {aid}"
            items.append({
                "angle_id": aid,
                "angle_name": aname,
                "batch": a.get("batch") or batch_index or 1,
                "status": "queued",  # queued, in_production, rendered, failed, skipped
                "job_id": None,
                "project_name": a.get("project_name") or "",
                "video_url": a.get("video_url") or "",
                "error": None,
            })

        batch_data = {
            **pinned,
            "job_scope": pinned,
            "batch_id": batch_id,
            "product_id": product_id,
            "product_title": product_title,
            "total_items": len(items),
            "completed_items": 0,
            "failed_items": 0,
            "status": "queued",  # queued, processing, completed, failed, cancelled
            "progress": 0.0,
            "current_index": 0,
            "current_angle_name": "",
            "items": items,
            "options": options,
            "created_at": time.time(),
            "cancelled": False,
        }

        with _BATCH_LOCK:
            BATCH_REGISTRY[batch_id] = batch_data
        cls._persist_batch(batch_data)

        # Register in TaskManager for global activity center tracking
        task_action = "สร้างดราฟต์ไทม์ไลน์" if is_draft else "เรนเดอร์วิดีโอ"
        TaskManager.create_task(
            task_type="batch_draft" if is_draft else "batch_render",
            title=f"{task_action} {len(items)} มุมมอง: {product_title}",
            payload={
                "batch_id": batch_id,
                "product_id": product_id,
                "product_title": product_title,
                "total_items": len(items),
                "is_draft": is_draft,
            },
            target_tab="product",
            target_id=product_id,
            task_id=batch_id,
            job_scope=pinned, **channel_kwargs,
        )

        # A single dispatcher owns admission. Do not create one blocked
        # thread per batch: 220 queued clips must remain a durable FIFO list.
        cls._ensure_dispatcher()

        return {
            "batch_id": batch_id,
            "product_id": product_id,
            "product_title": product_title,
            "total_items": len(items),
            "status": "queued",
            "items": items,
        }

    @classmethod
    def get_batch(cls, batch_id: str, *, channel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Returns the current state and progress of a batch job."""
        with _BATCH_LOCK:
            batch = BATCH_REGISTRY.get(batch_id)
        if batch is None:
            batch = cls._load_persisted_batch(batch_id)
        if batch is not None and channel_id is not None and (batch.get("channel_id") or "main") != channel_id:
            return None
        if batch is not None:
            with _BATCH_LOCK:
                BATCH_REGISTRY[batch_id] = batch
        if batch is not None and channel_id is not None:
            from copy import deepcopy
            return deepcopy(batch)
        return batch

    @classmethod
    def cancel_batch(cls, batch_id: str, *, channel_id: Optional[str] = None) -> bool:
        """Flags a batch job for cancellation."""
        if cls.get_batch(batch_id, channel_id=channel_id) is None:
            return False
        batch = cls.get_batch(batch_id)
        if not batch:
            return False
        with _BATCH_LOCK:
            batch["cancelled"] = True
            if batch["status"] in ("queued", "processing"):
                batch["status"] = "cancelled"
            cls._persist_batch(batch)
            channel_kwargs = {"channel_id": channel_id} if channel_id is not None else {}
            TaskManager.cancel_task(batch_id, **channel_kwargs)
            for item in batch.get("items", []):
                if item.get("job_id"):
                    render_jobs.request_cancel(item["job_id"], **channel_kwargs)
            return True

    # ------------------------------------------------------------------
    # Worker: concurrent waves inside one batch
    # ------------------------------------------------------------------

    @staticmethod
    def _refresh_counts(batch: Dict[str, Any]) -> None:
        """Recount from item state (caller holds _BATCH_LOCK)."""
        items = batch.get("items", [])
        batch["completed_items"] = sum(1 for it in items if it.get("status") in ("rendered", "draft_ready"))
        batch["failed_items"] = sum(1 for it in items if it.get("status") == "failed")

    @classmethod
    def _update_item(cls, batch: Dict[str, Any], item: Dict[str, Any], **fields: Any) -> None:
        """Mutate one item and checkpoint the batch under the shared lock."""
        with _BATCH_LOCK:
            item.update(fields)
            cls._refresh_counts(batch)
            cls._persist_batch(batch)

    @classmethod
    @contextmanager
    def _wave_slot(cls, batch: Dict[str, Any], channel_kwargs: Dict[str, Any]) -> Iterator[None]:
        """Hold the global render slot for one wave.

        A wave is a single waiter on the slot, so a batch never fills the
        render queue by itself. If other callers already filled it (HTTP 429)
        the wave waits and retries instead of failing its items.
        """
        while True:
            slot = render_jobs.render_slot(f"batch:{batch['batch_id']}", **channel_kwargs)
            try:
                slot.__enter__()
            except HTTPException as exc:
                if exc.status_code != 429 or batch.get("cancelled"):
                    raise
                time.sleep(_SLOT_RETRY_SECONDS)
                continue
            break
        try:
            yield
        finally:
            slot.__exit__(None, None, None)

    @classmethod
    def _find_resumable_output(
        cls, batch: Dict[str, Any], item: Dict[str, Any], angle_data: Dict[str, Any]
    ) -> Optional[str]:
        """A valid MP4 already produced for this batch (resume gate), or None.

        Only files written after the batch was created count, so choosing to
        re-render an angle that has an older export still renders it again.
        """
        created_at = float(batch.get("created_at") or 0)
        candidates: List[str] = []
        for value in (item.get("video_url"), angle_data.get("video_url")):
            if value:
                candidates.append(str(value))
        names = {n for n in (item.get("project_name"), angle_data.get("project_name")) if n}
        for name in sorted(names):
            try:
                matches = sorted(
                    EXPORTS_DIR.glob(f"{glob.escape(str(name))}_*.mp4"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
            except OSError:
                matches = []
            candidates.extend(str(m) for m in matches)
        for candidate in candidates:
            path = Path(candidate)
            if not path.is_absolute():
                path = BASE_DIR / path
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime + 1.0 < created_at:
                continue
            if is_valid_mp4(path):
                return candidate
        return None

    @classmethod
    def _run_batch_worker(cls, batch_id: str) -> None:
        """Render a batch's pending angles on BATCH_MAX_WORKERS threads, in waves."""
        batch = cls.get_batch(batch_id)
        if not batch:
            return
        with _BATCH_LOCK:
            # Cancellation can land between dispatcher selection and worker
            # start; never resurrect a cancelled checkpoint as processing.
            if batch.get("cancelled") or batch.get("status") == "cancelled":
                return
            batch["status"] = "processing"
            cls._persist_batch(batch)

        product_id = batch["product_id"]
        pinned = render_jobs.pin_job_scope(batch.get("channel_id"), batch.get("job_scope"))
        channel_kwargs = {"channel_id": pinned["channel_id"]} if pinned.get("channel_id") else {}
        items = batch["items"]
        total_items = len(items)
        options = batch.get("options", {})

        TaskManager.update_progress(
            batch_id,
            0.0,
            step_label=f"เริ่มเรนเดอร์คิว 0/{total_items} มุมมอง..."
        , **channel_kwargs)

        ctx: Dict[str, Any] = {
            "batch": batch,
            "batch_id": batch_id,
            "product_id": product_id,
            "product_title": batch["product_title"],
            "items": items,
            "total_items": total_items,
            "options": options,
            "pinned": pinned,
            "channel_kwargs": channel_kwargs,
            # Per-item fraction done (0..1) for the overall progress bar.
            "progress": {
                idx: 1.0 for idx, it in enumerate(items)
                if it.get("status") in ("rendered", "draft_ready", "failed", "skipped", "cancelled")
            },
        }

        pending = [
            (idx, item) for idx, item in enumerate(items)
            if item.get("status") not in ("rendered", "draft_ready", "failed", "skipped", "cancelled")
        ]
        workers = max(1, int(BATCH_MAX_WORKERS))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"batch_{batch_id[:8]}") as pool:
            for start in range(0, len(pending), workers):
                wave = pending[start:start + workers]
                if batch.get("cancelled"):
                    logger.info("Batch %s cancelled by user before item %d", batch_id, wave[0][0])
                    for _idx, item in pending[start:]:
                        cls._update_item(batch, item, status="cancelled")
                    break
                try:
                    with cls._wave_slot(batch, channel_kwargs):
                        futures = [pool.submit(cls._process_item_safely, ctx, idx, item) for idx, item in wave]
                        for future in futures:
                            future.result()
                except HTTPException as exc:
                    # Slot refused for a reason other than a full queue (or the
                    # batch was cancelled while waiting): fail just this wave.
                    for _idx, item in wave:
                        if item.get("status") in ("queued", "in_production"):
                            cls._update_item(batch, item, status="cancelled" if batch.get("cancelled") else "failed",
                                             error=None if batch.get("cancelled") else str(exc.detail))

        cls._finalize_batch(ctx)

    @classmethod
    def _process_item_safely(cls, ctx: Dict[str, Any], idx: int, item: Dict[str, Any]) -> None:
        try:
            cls._process_item(ctx, idx, item)
        except Exception as exc:  # never let one angle take down the wave
            logger.exception("[BatchRender] มุมมอง %s ล้มเหลวโดยไม่คาดคิด: %s", item.get("angle_id"), exc)
            cls._update_item(ctx["batch"], item, status="failed", error=str(exc) or "เรนเดอร์ไม่สำเร็จ")
        finally:
            with _BATCH_LOCK:
                ctx["progress"][idx] = 1.0

    @classmethod
    def _process_item(cls, ctx: Dict[str, Any], idx: int, item: Dict[str, Any]) -> None:
        """Render one angle. Runs on a pool thread; never holds _BATCH_LOCK while rendering."""
        batch = ctx["batch"]
        batch_id = ctx["batch_id"]
        product_id = ctx["product_id"]
        product_title = ctx["product_title"]
        items = ctx["items"]
        total_items = ctx["total_items"]
        options = ctx["options"]
        pinned = ctx["pinned"]
        channel_kwargs = ctx["channel_kwargs"]

        def mark(**fields: Any) -> None:
            cls._update_item(batch, item, **fields)

        if batch.get("cancelled"):
            mark(status="cancelled")
            return

        angle_id = item["angle_id"]
        angle_name = item["angle_name"]

        with _BATCH_LOCK:
            batch["current_index"] = idx
            batch["current_angle_name"] = angle_name
            item["status"] = "in_production"
            cls._persist_batch(batch)

        # Re-fetch latest product state from DB to get up-to-date angle data
        latest_prod = None
        try:
            latest_prod = ProductStore.get(product_id, **channel_kwargs)
            angle_data = None
            if latest_prod:
                item_batch = item.get("batch") or options.get("batch_index")
                if item_batch is not None:
                    for a in latest_prod.get("angles", []):
                        if (a.get("batch") or 1) == item_batch and str(a.get("angle_id") or a.get("id")) == angle_id:
                            angle_data = a
                            break
                if not angle_data:
                    for a in latest_prod.get("angles", []):
                        if str(a.get("angle_id") or a.get("id")) == angle_id:
                            angle_data = a
                            break
        except Exception as e:
            logger.error("Failed to read product %s angle %s: %s", product_id, angle_id, e)
            angle_data = None

        if not angle_data:
            mark(status="failed", error="ไม่พบข้อมูลมุมมองในฐานข้อมูล")
            return

        # Check if posted
        if angle_data.get("status") == "posted" or angle_data.get("posted_at"):
            mark(status="skipped", error="คลิปนี้ถูกโพสต์แล้ว ข้ามการเรนเดอร์ซ้ำ")
            return

        # Resume gate: an MP4 already produced for this batch is not rendered again.
        if options.get("export_mp4", True):
            resumed = cls._find_resumable_output(batch, item, angle_data)
            if resumed:
                resumed_project = item.get("project_name") or angle_data.get("project_name") or ""
                try:
                    ProductStore.update_angle_status(
                        product_id,
                        angle_id,
                        "rendered",
                        video_url=resumed,
                        project_name=resumed_project or None,
                        batch=angle_data.get("batch") or item.get("batch"),
                        **channel_kwargs,
                    )
                except Exception as exc:
                    logger.warning("[BatchRender] อัปเดตสถานะมุม %s หลังข้ามไม่สำเร็จ: %s", angle_id, exc)
                logger.info("[BatchRender] ข้ามมุม %s: มีไฟล์ MP4 สมบูรณ์จากรอบนี้แล้ว (%s)", angle_id, resumed)
                mark(status="rendered", video_url=resumed, project_name=resumed_project, error=None)
                return

        # Resolve footage
        chosen_videos = angle_data.get("selected_videos") or []
        if not chosen_videos and angle_data.get("selected_video"):
            chosen_videos = [angle_data["selected_video"]]
        if not chosen_videos and latest_prod:
            chosen_videos = latest_prod.get("default_videos") or []

        # Check files in RAW/INBOX if still empty
        if not chosen_videos:
            raw_clips = list(RAW_DIR.glob("*.mp4")) + list(INBOX_DIR.glob("*.mp4"))
            if raw_clips:
                chosen_videos = [str(raw_clips[0])]

        if not chosen_videos:
            mark(status="failed", error="ไม่มีไฟล์คลิปวิดีโอสำหรับมุมมองนี้ กรุณาแนบคลิปก่อนเรนเดอร์")
            return

        primary_video = chosen_videos[0]
        raw_video_path = Path(primary_video)
        if not raw_video_path.is_absolute():
            raw_video_path = BASE_DIR / primary_video

        if not raw_video_path.exists():
            mark(status="failed", error=f"ไม่พบไฟล์วิดีโอที่ระบุ: {primary_video}")
            return

        # Resolve project_name for this angle following standard convention
        current_batch = angle_data.get("batch") or item.get("batch") or options.get("batch_index") or 1
        proj_name = angle_data.get("project_name")
        if not proj_name:
            angle_pnames = options.get("angle_project_names") or {}
            if angle_id in angle_pnames:
                proj_name = angle_pnames[angle_id]
            elif len(items) == 1 and options.get("project_name"):
                proj_name = options.get("project_name")

        existing_product_projs = set(latest_prod.get("projects", []))
        for o in latest_prod.get("angles", []):
            if o.get("project_name") and o is not angle_data:
                existing_product_projs.add(o["project_name"])
        if PROJECTS_DIR.exists():
            for d in PROJECTS_DIR.iterdir():
                if d.is_dir():
                    existing_product_projs.add(d.name)

        from scripts.pipeline_context import channel_project_name
        from scripts.product_store import _extract_batch_from_name

        # Collision & Batch Isolation Guard. Sibling items render at the same
        # time now, so names they reserved count as taken; reserve under the
        # lock so two workers can never pick the same project folder.
        with _BATCH_LOCK:
            sibling_names = {
                it.get("project_name") for it in items
                if it is not item and it.get("project_name")
            }
            is_colliding = False
            if proj_name:
                proj_batch = _extract_batch_from_name(proj_name)
                if proj_batch is not None and current_batch is not None and proj_batch != current_batch:
                    is_colliding = True
                elif proj_name in sibling_names or channel_project_name(proj_name, pinned.get("channel_id")) in sibling_names:
                    is_colliding = True
                else:
                    for o in latest_prod.get("angles", []):
                        if o is not angle_data and o.get("project_name") == proj_name:
                            is_colliding = True
                            break

            if not proj_name or is_colliding:
                proj_name = synthesize_project_name(
                    product_code=latest_prod.get("product_code", ""),
                    product_title=angle_data.get("product_name") or product_title,
                    angle_id=angle_id,
                    angle_name=angle_data.get("angle_name", ""),
                    batch=current_batch,
                    existing_dirs=list(existing_product_projs | sibling_names),
                )

            proj_name = channel_project_name(proj_name, pinned.get("channel_id"))
            angle_data["project_name"] = proj_name
            # In-memory reservation is what siblings read; it is checkpointed
            # together with job_id just below.
            item["project_name"] = proj_name

        # Update angle to in_production in ProductStore
        try:
            ProductStore.update_angle_status(
                product_id,
                angle_id,
                "in_production",
                project_name=proj_name,
                batch=angle_data.get("batch") if angle_data else item.get("batch"),
             **channel_kwargs)
        except Exception:
            pass

        sub_job_id = str(uuid.uuid4())
        render_jobs.create_job(sub_job_id, job_scope=pinned, **channel_kwargs)
        mark(job_id=sub_job_id)
        if batch.get("cancelled"):
            # cancel_batch may have scanned items before this job_id existed.
            render_jobs.request_cancel(sub_job_id, **channel_kwargs)

        def sub_on_progress(msg: str, progress: float) -> None:
            with _BATCH_LOCK:
                ctx["progress"][idx] = max(0.0, min(1.0, float(progress) / 100.0))
                overall = (sum(ctx["progress"].values()) / max(1, total_items)) * 100.0
                batch["progress"] = round(overall, 1)
            TaskManager.update_progress(
                batch_id,
                overall,
                step_label=f"[{idx + 1}/{total_items}] {angle_name}: {msg}"
            , **channel_kwargs)

        # Prepare script lines
        script_lines = angle_data.get("script_lines") or []
        if not script_lines and angle_data.get("script_text"):
            script_lines = angle_data["script_text"].split("\n")
        custom_script = "\n".join(script_lines)

        style_preset = resolve_batch_style_preset(angle_data, options)
        ad_tone = angle_data.get("ad_tone") or options.get("ad_tone") or "commercial_hype"

        # Auto retry up to 1 time if transient error
        success = False
        cancelled = False
        last_err = None

        for attempt in range(2):
            if batch.get("cancelled"):
                break
            try:
                # The wave holding render_jobs.render_slot owns admission; a
                # per-item slot here would serialise the wave again.
                effective_product_name = angle_data.get("product_name") or product_title
                brand_guess, model_guess = guess_brand_model(effective_product_name)
                hook_brand = angle_data.get("hook_brand") or latest_prod.get("hook_brand") or brand_guess or None
                hook_model = angle_data.get("hook_model") or latest_prod.get("hook_model") or model_guess or None
                hook_label = angle_data.get("hook_label") or latest_prod.get("hook_label") or ""

                result = TikTokAutoCutterPipeline.run(
                    cancel_event=render_jobs.get_cancel_event(sub_job_id, **channel_kwargs),
                    job_scope=pinned or None, **channel_kwargs,
                    product_name=effective_product_name,
                    raw_video_path=str(raw_video_path),
                    project_name=proj_name,
                    key_features=angle_data.get("key_features") or latest_prod.get("description", ""),
                    pain_point=angle_data.get("pain_point", ""),
                    # price_note stays product data; it is never copied into
                    # the clip (no price/discount in TikTok clips).
                    price_deal=angle_data.get("price_deal", ""),
                    custom_script=custom_script,
                    hook_brand=hook_brand,
                    hook_model=hook_model,
                    hook_label=hook_label,
                    voice=options.get("voice_gender", "male"),
                    voice_rate=options.get("voice_rate", "+15%"),
                    voice_engine_type="edge_tts" if options.get("voice_mode") == "edge_tts" else "gemini_tts",
                    voice_preset=options.get("voice_preset", "gemini_fenrir_male_strong"),
                    ad_tone=ad_tone,
                    style_preset=style_preset,
                    hook_style={
                        "template": (
                            (angle_data.get("hook_style") or {}).get("template")
                            or template_for_style_preset(style_preset)
                            or template_for_ad_tone(ad_tone)
                        )
                    },
                    font_name=options.get("font_name", "IBMPlex"),
                    bilingual_subtitles=options.get("bilingual_subtitles", True),
                    ghost_reveal=bool(options.get("ghost_reveal", True)),
                    use_ai_vision=options.get("use_ai_vision", True),
                    export_mp4=options.get("export_mp4", True),
                    product_id=product_id,
                    angle_id=angle_id,
                    manual_shot_map=angle_data.get("manual_shot_map") or [],
                    progress_callback=sub_on_progress,
                )

                mp4_val = (
                    result.get("mp4")
                    or result.get("mp4_video")
                    or result.get("output_video")
                    or result.get("video_path")
                    or ""
                )
                proj_name = result.get("project_name", "")

                if product_id and proj_name:
                    try:
                        ProductStore.attach_project(product_id, proj_name, **channel_kwargs)
                    except Exception:
                        pass

                # Mark rendered or in_production in store
                is_draft = not options.get("export_mp4", True)
                is_rendered = bool(not is_draft and mp4_val)
                item_b = angle_data.get("batch") if angle_data else item.get("batch")
                ProductStore.update_angle_status(
                    product_id,
                    angle_id,
                    "rendered" if is_rendered else "in_production",
                    video_url=str(mp4_val) if is_rendered else None,
                    project_name=proj_name,
                    export_id=result.get("export_id") if is_rendered else None,
                    batch=item_b,
                 **channel_kwargs)

                render_jobs.complete_job(sub_job_id, result, **channel_kwargs)
                mark(
                    status="rendered" if is_rendered else "draft_ready",
                    project_name=proj_name,
                    video_url=str(mp4_val) if is_rendered else "",
                )
                success = True
                break

            except RenderCancelled:
                logger.info("Sub-job %s cancelled for angle %s", sub_job_id, angle_id)
                render_jobs.cancel_job(sub_job_id, **channel_kwargs)
                cancelled = True
                mark(status="cancelled")
                try:
                    item_b = angle_data.get("batch") if angle_data else item.get("batch")
                    ProductStore.update_angle_status(
                        product_id, angle_id, "scripted", project_name="", batch=item_b
                    , **channel_kwargs)
                except Exception:
                    pass
                break

            except Exception as e:
                last_err = e
                logger.warning("Attempt %d failed for angle %s: %s", attempt + 1, angle_id, e)
                if attempt == 0:
                    time.sleep(2)  # Pause before retry

        if success or cancelled:
            return
        if batch.get("cancelled") and last_err is None:
            mark(status="cancelled")
            return
        mark(status="failed", error=str(last_err) if last_err else "เรนเดอร์ไม่สำเร็จ")
        render_jobs.fail_job(sub_job_id, str(last_err) if last_err else "Error", **channel_kwargs)
        try:
            ProductStore.update_angle_status(product_id, angle_id, "scripted", **channel_kwargs)
        except Exception:
            pass

    @classmethod
    def _finalize_batch(cls, ctx: Dict[str, Any]) -> None:
        batch = ctx["batch"]
        batch_id = ctx["batch_id"]
        items = ctx["items"]
        total_items = ctx["total_items"]
        options = ctx["options"]
        channel_kwargs = ctx["channel_kwargs"]
        with _BATCH_LOCK:
            cls._refresh_counts(batch)
            completed_count = batch["completed_items"]
            failed_count = batch["failed_items"]
            batch["progress"] = 100.0
            is_draft = not options.get("export_mp4", True)
            action_name = "สร้างดราฟต์" if is_draft else "เรนเดอร์"
            unit_name = "มุมมอง" if is_draft else "คลิป"

            first_project_name = None
            for it in items:
                if it.get("project_name"):
                    first_project_name = it["project_name"]
                    break

            completed_result = {
                "completed": completed_count,
                "failed": failed_count,
                "total": total_items,
                "items": items,
                "project_name": first_project_name or "",
                "product_id": ctx["product_id"],
            }

            if batch.get("cancelled"):
                batch["status"] = "cancelled"
                TaskManager.complete_task(
                    batch_id,
                    result=completed_result,
                    step_label=f"ยกเลิกคิว{action_name} (สำเร็จ {completed_count}/{total_items} {unit_name})"
                , **channel_kwargs)
            elif completed_count > 0:
                batch["status"] = "completed"
                TaskManager.complete_task(
                    batch_id,
                    result=completed_result,
                    step_label=f"🎉 {action_name}ชุดสำเร็จ {completed_count}/{total_items} {unit_name}!"
                , **channel_kwargs)
            else:
                batch["status"] = "failed"
                TaskManager.fail_task(
                    batch_id,
                    error=f"{action_name}ไม่สำเร็จทั้ง {total_items} {unit_name} กรุณาตรวจเช็กไฟล์วิดีโอต้นฉบับ"
                , **channel_kwargs)
            cls._persist_batch(batch)
