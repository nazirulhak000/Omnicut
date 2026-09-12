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

from scripts.config import BASE_DIR, RAW_DIR, INBOX_DIR, EXPORTS_DIR, STICKERS_DIR
from scripts.product_store import ProductStore
from scripts.task_manager import TaskManager
from scripts import render_jobs
from scripts.render_jobs import RenderCancelled
from scripts.pipeline import TikTokAutoCutterPipeline
from scripts.api_render import check_disk_space

logger = logging.getLogger("batch_render")

_BATCH_LOCK = threading.RLock()
BATCH_REGISTRY: Dict[str, Dict[str, Any]] = {}


class BatchRenderManager:
    """Manages batch video rendering jobs and background execution queues."""

    @classmethod
    def create_batch(
        cls,
        product_id: str,
        angle_ids: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validates product angles and enqueues a batch render job."""
        product = ProductStore.get(product_id)
        if not product:
            raise ValueError(f"ไม่พบข้อมูลสินค้า id '{product_id}'")

        options = options or {}
        all_angles = product.get("angles", [])
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

        # Verify disk space
        disk = check_disk_space(EXPORTS_DIR)
        if not disk.get("is_sufficient", True):
            free_gb = disk.get("free_gb", 0)
            min_gb = disk.get("min_required_gb", 3.0)
            raise RuntimeError(
                f"พื้นที่ว่างบนดิสก์เหลือน้อยเกินไป ({free_gb} GB เหลืออยู่, ต้องการขั้นต่ำ {min_gb} GB)"
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
                "status": "queued",  # queued, in_production, rendered, failed, skipped
                "job_id": None,
                "project_name": a.get("project_name") or "",
                "video_url": a.get("video_url") or "",
                "error": None,
            })

        batch_data = {
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

        # Register in TaskManager for global activity center tracking
        TaskManager.create_task(
            task_type="batch_render",
            title=f"เรนเดอร์วิดีโอ {len(items)} มุมมอง: {product_title}",
            payload={
                "batch_id": batch_id,
                "product_id": product_id,
                "product_title": product_title,
                "total_items": len(items),
            },
            target_tab="product",
            target_id=product_id,
            task_id=batch_id,
        )

        # Launch worker in background thread
        worker_thread = threading.Thread(
            target=cls._run_batch_worker,
            args=(batch_id,),
            daemon=True,
            name=f"batch_render_{batch_id[:8]}"
        )
        worker_thread.start()

        return {
            "batch_id": batch_id,
            "product_id": product_id,
            "product_title": product_title,
            "total_items": len(items),
            "status": "queued",
            "items": items,
        }

    @classmethod
    def get_batch(cls, batch_id: str) -> Optional[Dict[str, Any]]:
        """Returns the current state and progress of a batch job."""
        with _BATCH_LOCK:
            return BATCH_REGISTRY.get(batch_id)

    @classmethod
    def cancel_batch(cls, batch_id: str) -> bool:
        """Flags a batch job for cancellation."""
        with _BATCH_LOCK:
            batch = BATCH_REGISTRY.get(batch_id)
            if not batch:
                return False
            batch["cancelled"] = True
            if batch["status"] in ("queued", "processing"):
                batch["status"] = "cancelled"
            TaskManager.cancel_task(batch_id)
            return True

    @classmethod
    def _run_batch_worker(cls, batch_id: str) -> None:
        """Sequential FIFO worker that renders each angle one by one."""
        with _BATCH_LOCK:
            batch = BATCH_REGISTRY.get(batch_id)
            if not batch:
                return
            batch["status"] = "processing"

        product_id = batch["product_id"]
        product_title = batch["product_title"]
        items = batch["items"]
        total_items = len(items)
        options = batch.get("options", {})

        TaskManager.update_progress(
            batch_id,
            0.0,
            step_label=f"เริ่มเรนเดอร์คิว 0/{total_items} มุมมอง..."
        )

        completed_count = 0
        failed_count = 0

        for idx, item in enumerate(items):
            # Check for cancellation before starting next angle
            if batch.get("cancelled"):
                logger.info("Batch %s cancelled by user before item %d", batch_id, idx)
                item["status"] = "cancelled"
                continue

            angle_id = item["angle_id"]
            angle_name = item["angle_name"]

            with _BATCH_LOCK:
                batch["current_index"] = idx
                batch["current_angle_name"] = angle_name
                item["status"] = "in_production"

            # Re-fetch latest product state from DB to get up-to-date angle data
            try:
                latest_prod = ProductStore.get(product_id)
                angle_data = None
                if latest_prod:
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
                continue

            # Check if posted
            if angle_data.get("status") == "posted" or angle_data.get("posted_at"):
                item["status"] = "skipped"
                item["error"] = "คลิปนี้ถูกโพสต์แล้ว ข้ามการเรนเดอร์ซ้ำ"
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
                continue

            primary_video = chosen_videos[0]
            raw_video_path = Path(primary_video)
            if not raw_video_path.is_absolute():
                raw_video_path = BASE_DIR / primary_video

            if not raw_video_path.exists():
                item["status"] = "failed"
                item["error"] = f"ไม่พบไฟล์วิดีโอที่ระบุ: {primary_video}"
                failed_count += 1
                continue

            # Update angle to in_production in ProductStore
            try:
                ProductStore.update_angle_status(
                    product_id,
                    angle_id,
                    "in_production",
                    project_name=angle_data.get("project_name")
                )
            except Exception:
                pass

            sub_job_id = str(uuid.uuid4())
            item["job_id"] = sub_job_id
            render_jobs.create_job(sub_job_id)

            def make_sub_progress(item_idx: int, a_name: str):
                def sub_on_progress(msg: str, progress: float):
                    overall = ((item_idx + (progress / 100.0)) / total_items) * 100.0
                    with _BATCH_LOCK:
                        batch["progress"] = round(overall, 1)
                    TaskManager.update_progress(
                        batch_id,
                        overall,
                        step_label=f"[{item_idx + 1}/{total_items}] {a_name}: {msg}"
                    )
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
                    with render_jobs.render_slot(sub_job_id):
                        result = TikTokAutoCutterPipeline.run(
                            cancel_event=render_jobs.get_cancel_event(sub_job_id),
                            product_name=angle_data.get("product_name") or product_title,
                            raw_video_path=str(raw_video_path),
                            project_name=angle_data.get("project_name") or None,
                            key_features=angle_data.get("key_features") or latest_prod.get("description", ""),
                            pain_point=angle_data.get("pain_point", ""),
                            price_deal=angle_data.get("price_deal") or latest_prod.get("price_note", ""),
                            custom_script=custom_script,
                            hook_brand=angle_data.get("hook_brand"),
                            hook_model=angle_data.get("hook_model"),
                            hook_label=angle_data.get("hook_label"),
                            voice=options.get("voice_gender", "female"),
                            voice_rate=options.get("voice_rate", "+15%"),
                            voice_engine_type="gemini_tts" if options.get("voice_mode") == "gemini_tts" else "edge_tts",
                            voice_preset=options.get("voice_preset", "gemini_puck_male_hype"),
                            ad_tone=angle_data.get("ad_tone") or "commercial_premium",
                            style_preset=options.get("style_preset", "clean_tech_review"),
                            font_name=options.get("font_name", "IBMPlex"),
                            bilingual_subtitles=options.get("bilingual_subtitles", True),
                            use_ai_vision=options.get("use_ai_vision", True),
                            export_mp4=True,
                            product_id=product_id,
                            angle_id=angle_id,
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
                            ProductStore.attach_project(product_id, proj_name)
                        except Exception:
                            pass

                    # Mark rendered in store
                    ProductStore.update_angle_status(
                        product_id,
                        angle_id,
                        "rendered" if mp4_val else "in_production",
                        video_url=str(mp4_val) if mp4_val else None,
                        project_name=proj_name,
                        export_id=result.get("export_id")
                    )

                    render_jobs.complete_job(sub_job_id, result)
                    item["status"] = "rendered"
                    item["project_name"] = proj_name
                    item["video_url"] = str(mp4_val)
                    completed_count += 1
                    success = True
                    break

                except RenderCancelled:
                    logger.info("Sub-job %s cancelled for angle %s", sub_job_id, angle_id)
                    render_jobs.cancel_job(sub_job_id)
                    item["status"] = "cancelled"
                    try:
                        ProductStore.update_angle_status(product_id, angle_id, "scripted", project_name="")
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
                render_jobs.fail_job(sub_job_id, str(last_err) if last_err else "Error")
                try:
                    ProductStore.update_angle_status(product_id, angle_id, "scripted")
                except Exception:
                    pass

            with _BATCH_LOCK:
                batch["completed_items"] = completed_count
                batch["failed_items"] = failed_count

        # Final batch state
        with _BATCH_LOCK:
            batch["progress"] = 100.0
            if batch.get("cancelled"):
                batch["status"] = "cancelled"
                TaskManager.complete_task(
                    batch_id,
                    result={"completed": completed_count, "failed": failed_count, "total": total_items, "items": items},
                    step_label=f"ยกเลิกคิวเรนเดอร์ (สำเร็จ {completed_count}/{total_items} คลิป)"
                )
            elif completed_count > 0:
                batch["status"] = "completed"
                TaskManager.complete_task(
                    batch_id,
                    result={"completed": completed_count, "failed": failed_count, "total": total_items, "items": items},
                    step_label=f"🎉 เรนเดอร์ชุดสำเร็จ {completed_count}/{total_items} คลิป!"
                )
            else:
                batch["status"] = "failed"
                TaskManager.fail_task(
                    batch_id,
                    error=f"เรนเดอร์ไม่สำเร็จทั้ง {total_items} มุมมอง กรุณาตรวจเช็กไฟล์วิดีโอต้นฉบับ"
                )
