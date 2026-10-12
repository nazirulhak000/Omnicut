"""
Batch Render Engine & Queue Worker for OmniCut Pro Studio.

Processes multiple product angles sequentially in a background queue,
preventing CPU/Memory thrashing via concurrency locking and keeping
track of overall batch progress across all angles.
"""

import sys
import uuid
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

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

logger = logging.getLogger("batch_render")


def _maintenance_root() -> Path:
    """Data root of the batch queue (maintenance lock lives at <root>/_Docs)."""
    return Path(_batch_queue_store.BATCH_QUEUE_PATH).parent.parent

# 1-to-1 default mapping between 10 script angles and 10 editorial style presets
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
}

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

    @classmethod
    def _run_batch_worker(cls, batch_id: str) -> None:
        """Sequential FIFO worker that renders each angle one by one."""
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
        product_title = batch["product_title"]
        items = batch["items"]
        total_items = len(items)
        options = batch.get("options", {})

        TaskManager.update_progress(
            batch_id,
            0.0,
            step_label=f"เริ่มเรนเดอร์คิว 0/{total_items} มุมมอง..."
        , **channel_kwargs)

        completed_count = sum(1 for item in items if item.get("status") == "rendered")
        failed_count = sum(1 for item in items if item.get("status") == "failed")

        for idx, item in enumerate(items):
            if item.get("status") in ("rendered", "failed", "skipped", "cancelled"):
                continue
            # Check for cancellation before starting next angle
            if batch.get("cancelled"):
                logger.info("Batch %s cancelled by user before item %d", batch_id, idx)
                item["status"] = "cancelled"
                cls._persist_batch(batch)
                continue

            angle_id = item["angle_id"]
            angle_name = item["angle_name"]

            with _BATCH_LOCK:
                batch["current_index"] = idx
                batch["current_angle_name"] = angle_name
                item["status"] = "in_production"
                cls._persist_batch(batch)

            # Re-fetch latest product state from DB to get up-to-date angle data
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
                item["status"] = "failed"
                item["error"] = "ไม่พบข้อมูลมุมมองในฐานข้อมูล"
                failed_count += 1
                cls._persist_batch(batch)
                continue

            # Check if posted
            if angle_data.get("status") == "posted" or angle_data.get("posted_at"):
                item["status"] = "skipped"
                item["error"] = "คลิปนี้ถูกโพสต์แล้ว ข้ามการเรนเดอร์ซ้ำ"
                cls._persist_batch(batch)
                continue

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
                item["status"] = "failed"
                item["error"] = "ไม่มีไฟล์คลิปวิดีโอสำหรับมุมมองนี้ กรุณาแนบคลิปก่อนเรนเดอร์"
                failed_count += 1
                cls._persist_batch(batch)
                continue

            primary_video = chosen_videos[0]
            raw_video_path = Path(primary_video)
            if not raw_video_path.is_absolute():
                raw_video_path = BASE_DIR / primary_video

            if not raw_video_path.exists():
                item["status"] = "failed"
                item["error"] = f"ไม่พบไฟล์วิดีโอที่ระบุ: {primary_video}"
                failed_count += 1
                cls._persist_batch(batch)
                continue

            # Resolve project_name for this angle following standard convention
            current_batch = angle_data.get("batch") or item.get("batch") or options.get("batch_index") or 1
            proj_name = angle_data.get("project_name")
            if not proj_name:
                angle_pnames = options.get("angle_project_names") or {}
                if angle_id in angle_pnames:
                    proj_name = angle_pnames[angle_id]
                elif len(items) == 1 and options.get("project_name"):
                    proj_name = options.get("project_name")

            # Collision & Batch Isolation Guard:
            # Verify proj_name does not belong to another angle/batch or collide with existing project folders
            is_colliding = False
            if proj_name:
                from scripts.product_store import _extract_batch_from_name
                proj_batch = _extract_batch_from_name(proj_name)
                if proj_batch is not None and current_batch is not None and proj_batch != current_batch:
                    is_colliding = True
                else:
                    for o in latest_prod.get("angles", []):
                        if o is not angle_data and o.get("project_name") == proj_name:
                            is_colliding = True
                            break

            if not proj_name or is_colliding:
                existing_product_projs = set(latest_prod.get("projects", []))
                for o in latest_prod.get("angles", []):
                    if o.get("project_name") and o is not angle_data:
                        existing_product_projs.add(o["project_name"])
                if PROJECTS_DIR.exists():
                    for d in PROJECTS_DIR.iterdir():
                        if d.is_dir():
                            existing_product_projs.add(d.name)

                proj_name = synthesize_project_name(
                    product_code=latest_prod.get("product_code", ""),
                    product_title=angle_data.get("product_name") or product_title,
                    angle_id=angle_id,
                    angle_name=angle_data.get("angle_name", ""),
                    batch=current_batch,
                    existing_dirs=list(existing_product_projs),
                )

            from scripts.pipeline_context import channel_project_name
            proj_name = channel_project_name(proj_name, pinned.get("channel_id"))
            angle_data["project_name"] = proj_name
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
            item["job_id"] = sub_job_id
            render_jobs.create_job(sub_job_id, job_scope=pinned, **channel_kwargs)

            def make_sub_progress(item_idx: int, a_name: str):
                def sub_on_progress(msg: str, progress: float):
                    overall = ((item_idx + (progress / 100.0)) / total_items) * 100.0
                    with _BATCH_LOCK:
                        batch["progress"] = round(overall, 1)
                    TaskManager.update_progress(
                        batch_id,
                        overall,
                        step_label=f"[{item_idx + 1}/{total_items}] {a_name}: {msg}"
                    , **channel_kwargs)
                return sub_on_progress

            # Prepare script lines
            script_lines = angle_data.get("script_lines") or []
            if not script_lines and angle_data.get("script_text"):
                script_lines = angle_data["script_text"].split("\n")
            custom_script = "\n".join(script_lines)

            # Auto retry up to 1 time if transient error
            success = False
            last_err = None

            for attempt in range(2):
                if batch.get("cancelled"):
                    break
                try:
                    with render_jobs.render_slot(sub_job_id, **channel_kwargs):
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
                            price_deal=angle_data.get("price_deal") or latest_prod.get("price_note", ""),
                            custom_script=custom_script,
                            hook_brand=hook_brand,
                            hook_model=hook_model,
                            hook_label=hook_label,
                            voice=options.get("voice_gender", "male"),
                            voice_rate=options.get("voice_rate", "+15%"),
                            voice_engine_type="edge_tts" if options.get("voice_mode") == "edge_tts" else "gemini_tts",
                            voice_preset=options.get("voice_preset", "gemini_fenrir_male_strong"),
                            ad_tone=angle_data.get("ad_tone") or options.get("ad_tone") or "commercial_hype",
                            style_preset=(
                                angle_data.get("style_preset")
                                or ANGLE_TO_DEFAULT_STYLE.get(str(angle_data.get("angle_id") or "").strip().lower())
                                or options.get("style_preset")
                                or "clean_tech_review"
                            ),
                            hook_style={
                                "template": (
                                    (angle_data.get("hook_style") or {}).get("template")
                                    or template_for_style_preset(
                                        angle_data.get("style_preset")
                                        or ANGLE_TO_DEFAULT_STYLE.get(str(angle_data.get("angle_id") or "").strip().lower())
                                        or options.get("style_preset")
                                        or "clean_tech_review"
                                    )
                                    or template_for_ad_tone(angle_data.get("ad_tone") or options.get("ad_tone") or "commercial_hype")
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
                            progress_callback=make_sub_progress(idx, angle_name)
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
                    item["status"] = "rendered" if is_rendered else "draft_ready"
                    item["project_name"] = proj_name
                    item["video_url"] = str(mp4_val) if is_rendered else ""
                    completed_count += 1
                    success = True
                    break

                except RenderCancelled:
                    logger.info("Sub-job %s cancelled for angle %s", sub_job_id, angle_id)
                    render_jobs.cancel_job(sub_job_id, **channel_kwargs)
                    item["status"] = "cancelled"
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

            if not success and item["status"] != "cancelled":
                failed_count += 1
                item["status"] = "failed"
                item["error"] = str(last_err) if last_err else "เรนเดอร์ไม่สำเร็จ"
                render_jobs.fail_job(sub_job_id, str(last_err) if last_err else "Error", **channel_kwargs)
                try:
                    ProductStore.update_angle_status(product_id, angle_id, "scripted", **channel_kwargs)
                except Exception:
                    pass

            with _BATCH_LOCK:
                batch["completed_items"] = completed_count
                batch["failed_items"] = failed_count
                cls._persist_batch(batch)

        # Final batch state
        with _BATCH_LOCK:
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
                "product_id": product_id,
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
