"""
OmniCut Mobile Quick Studio Engine (Backend).
Handles 3-step mobile production workflow:
1. Product & Angle Catalog optimized for fast mobile touch UI
2. Automatic Guided Take assembly & SOP styling (Fenrir voice, Mali-Bold Ghost Reveal, orange callouts)
3. One-touch Master Render with TikTok sharing metadata
"""

import re
import time
import uuid
from urllib.parse import quote
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import (
    BASE_DIR, EXPORTS_DIR, RAW_DIR, INBOX_DIR
)
from scripts.product_store import ProductStore
from scripts.shot_lists_store import ShotListsStore
from scripts import recording_sessions, render_jobs
from scripts.recording_sessions import RecordingSessionStore
from scripts.shot_list_builder import generate_shot_list_for_angle
from scripts.task_manager import TaskManager
from scripts.pipeline import TikTokAutoCutterPipeline
from scripts.it_angles import DEFAULT_BGM


def _angle_id(angle, index=0):
    return angle.get("angle_id") or angle.get("id") or f"angle_{index + 1}"


def _script_text(angle):
    lines = angle.get("tts_lines") or angle.get("script_lines")
    if lines:
        return "\n".join(str(line).strip() for line in lines if str(line).strip())
    return str(angle.get("script_text") or angle.get("script") or "").strip()


def _attached_raw(angle):
    videos = angle.get("selected_videos") or []
    return (videos[0] if videos else None) or angle.get("selected_video") or angle.get("video_file") or angle.get("raw_video")


def _find_or_create_angle(product: Dict[str, Any], angle_id: str, title: Optional[str] = None, script: Optional[str] = None) -> Dict[str, Any]:
    angles = product.get("angles") or []
    found = next((a for i, a in enumerate(angles) if _angle_id(a, i) == angle_id), None)
    if found:
        return found

    p_id = product.get("id") or product.get("product_id")
    p_name = product.get("name") or product.get("title") or "สินค้ายอดนิยม"
    actual_angle_id = angle_id if (angle_id and angle_id != "quick_take") else f"quick_take_{int(time.time())}"
    hook_title = (title or f"⚡ รีวิว {p_name} ใช้งานจริง ดีไหม คุ้มไหม?").strip()
    script_text = (script or (
        f"วันนี้มาแชร์ {p_name} ที่ทุกคนต้องมีติดตัวครับ\n"
        f"ตัวจริงคุณภาพดีมาก ฟังก์ชันครบครัน ใช้งานสะดวกสุดๆ ช่วยแก้ปัญหาได้ตรงจุด\n"
        f"ใครที่กำลังมองหาอยู่ แนะนำตัวนี้เลยครับ คุ้มค่าเงินแน่นอน\n"
        f"พิกัดราคาพิเศษ อยู่ในตะกร้าสีเหลือง ซ้ายล่างตอนนี้ กดสั่งได้เลยครับ"
    )).strip()

    script_lines = [l.strip() for l in script_text.splitlines() if l.strip()]
    new_angle = {
        "angle_id": actual_angle_id,
        "angle_name": "⚡ รีวิวเร่งด่วน / ถ่ายทำอิสระ",
        "hook_title": hook_title,
        "script_text": script_text,
        "script_lines": script_lines,
        "tts_lines": script_lines,
        "status": "draft",
        "selected_videos": [],
    }
    ProductStore.add_single_angle(p_id, new_angle, batch_index=1)
    updated = ProductStore.get(p_id)
    if updated and updated.get("angles"):
        product["angles"] = updated.get("angles") or []
        return updated["angles"][-1]
    return new_angle


def _find_angle(product, angle_id):
    angles = product.get("angles") or []
    angle = next((a for i, a in enumerate(angles) if _angle_id(a, i) == angle_id), None)
    if not angle:
        if angle_id == "quick_take" or not angles:
            return _find_or_create_angle(product, angle_id)
        raise ValueError(f"ไม่พบมุมนำเสนอ ID: {angle_id}")
    return angle


def _raw_path(value):
    """Resolve store-relative/legacy footage without allowing arbitrary file reads."""
    supplied = Path(str(value).replace("\\", "/"))
    roots = (RAW_DIR.resolve(), INBOX_DIR.resolve())
    candidates = [supplied] if supplied.is_absolute() else [BASE_DIR / supplied, RAW_DIR / supplied, INBOX_DIR / supplied]
    for candidate in candidates:
        resolved = candidate.resolve()
        if candidate.exists() or candidate.is_symlink():
            if not any(resolved.is_relative_to(root) for root in roots):
                raise ValueError("ไฟล์วัตถุดิบอยู่นอกโฟลเดอร์ที่อนุญาต")
            if not resolved.is_file():
                raise ValueError("วัตถุดิบต้องเป็นไฟล์วิดีโอ")
            return resolved
    raise ValueError("ไม่พบคลิปวัตถุดิบ กรุณาถ่ายทำหรือเลือกคลิปใหม่")


def _sessions():
    return sorted(recording_sessions._TABLE.load(), key=lambda r: r.get("updated_at") or r.get("created_at") or "", reverse=True)


class MobileQuickStudioService:
    """Service layer backing the Mobile Quick Studio API endpoints."""

    @classmethod
    def get_catalog(cls) -> List[Dict[str, Any]]:
        """Returns catalog of products formatted for mobile cards."""
        products = ProductStore.get_all()
        catalog = []
        sessions = _sessions()

        for p in products:
            p_id = p.get("id") or ""
            p_name = p.get("name") or "Unnamed Product"
            angles = p.get("angles") or []
            price = p.get("price_note") or p.get("price") or ""
            category = p.get("category") or "Gadget"
            specs = p.get("specs") or {}

            mobile_angles = []
            for a_idx, angle in enumerate(angles):
                a_id = _angle_id(angle, a_idx)
                a_name = angle.get("angle_name") or angle.get("name") or a_id
                script_text = _script_text(angle)
                hook = angle.get("hook") or {}
                hook_headline = (
                    angle.get("hook_title")
                    or hook.get("headline")
                    or angle.get("title")
                    or a_name
                )
                hook_sub = angle.get("hook_sub") or hook.get("sub") or ""

                # Check if shot list exists
                shot_list_record = ShotListsStore.get(p_id, a_id)
                shot_count = len(shot_list_record.get("shot_list", [])) if shot_list_record else 0

                # Check active or completed recording session
                matches = [rec for rec in sessions if rec.get("product_id") == p_id and rec.get("angle_id") == a_id]
                session = next((rec for rec in matches if rec.get("status") not in {"completed", "expired", "cancelled"}), None)
                if session is None:
                    session = next((rec for rec in matches if rec.get("status") == "completed"), None)
                attached_raw = _attached_raw(angle)
                is_rendered = bool(angle.get("video_url") or angle.get("status") == "rendered")
                has_footage = bool(attached_raw)
                attached_name = Path(str(attached_raw)).name if attached_raw else None

                mobile_angles.append({
                    "id": a_id,
                    "name": a_name,
                    "hook_headline": hook_headline,
                    "hook_sub": hook_sub,
                    "script_preview": (script_text[:120] + "...") if len(script_text) > 120 else script_text,
                    "script_full": script_text,

                    "shot_count": shot_count,
                    "status": "rendered" if is_rendered else (angle.get("status") or "draft"),
                    "is_rendered": is_rendered,
                    "has_footage": has_footage,
                    "attached_raw": attached_raw,
                    "attached_raw_name": attached_name,
                    "render_status": "rendered" if is_rendered else ("ready_to_cut" if has_footage else "draft"),
                    "has_session": session is not None,
                    "session_id": session.get("id") if session else None,
                    "session_status": session.get("status") if session else None,
                    "rendered_video_url": angle.get("video_url"),
                })

            # Check cover or image
            cover_url = p.get("cover_image") or p.get("thumbnail") or None
            if not cover_url and p.get("images"):
                first_image = p["images"][0]
                cover_url = (first_image.get("url") or first_image.get("path")) if isinstance(first_image, dict) else first_image

            rendered_count = sum(1 for a in mobile_angles if a.get("is_rendered"))
            footage_count = sum(1 for a in mobile_angles if a.get("has_footage"))
            total_count = len(mobile_angles)
            if total_count > 0 and rendered_count == total_count:
                prod_status = "completed"
            elif rendered_count > 0 or footage_count > 0:
                prod_status = "in_progress"
            else:
                prod_status = "not_started"

            catalog.append({
                "id": p_id,
                "name": p_name,
                "category": category,
                "price": price,
                "specs": specs,
                "cover_url": cover_url,
                "angles": mobile_angles,
                "total_angles": total_count,
                "rendered_count": rendered_count,
                "footage_count": footage_count,
                "product_status": prod_status,
            })

        return catalog

    @classmethod
    def create_quick_angle(
        cls,
        product_id: str,
        title: Optional[str] = None,
        script: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a custom angle or fast template angle directly from mobile touch UI."""
        product = ProductStore.get(product_id)
        if not product:
            raise ValueError(f"ไม่พบสินค้า ID: {product_id}")
        angle = _find_or_create_angle(product, "quick_take", title=title, script=script)
        resolved_id = _angle_id(angle)
        try:
            generate_shot_list_for_angle(product_id, resolved_id)
        except Exception as shot_err:
            print(f"⚠️ [create_quick_angle] shot list warning: {shot_err}")
        return angle

    @classmethod
    def upload_mobile_video(
        cls,
        product_id: str,
        angle_id: str,
        file_bytes: bytes,
        filename: str,
    ) -> Dict[str, Any]:
        """Uploads and attaches raw mobile video footage (MP4/MOV) directly to product and angle."""
        product = ProductStore.get(product_id)
        if not product:
            raise ValueError(f"ไม่พบสินค้า ID: {product_id}")
        if not file_bytes:
            raise ValueError("ไฟล์วิดีโอว่างเปล่า ไม่สามารถอัปโหลดได้")

        angle = _find_angle(product, angle_id)
        resolved_angle_id = _angle_id(angle)

        ext = Path(filename).suffix.lower()
        if ext not in {".mp4", ".mov", ".m4v"}:
            ext = ".mp4"
        safe_name = f"mobile_take_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"

        prod_raw_dir = RAW_DIR / product_id
        prod_raw_dir.mkdir(parents=True, exist_ok=True)
        dest_path = prod_raw_dir / safe_name
        dest_path.write_bytes(file_bytes)

        rel_path = f"01_Raw/{product_id}/{safe_name}"
        try:
            from scripts.media_service import get_file_info
            file_info = get_file_info(dest_path)
        except Exception:
            file_info = {
                "name": safe_name,
                "path": rel_path,
                "size": len(file_bytes),
                "type": "video",
                "duration": 0.0,
            }

        ProductStore.add_video_to_product(product_id, file_info)
        ProductStore.update_angle_videos(product_id, resolved_angle_id, [rel_path])

        return {
            "success": True,
            "filename": safe_name,
            "video_path": rel_path,
            "file_info": file_info
        }

    @classmethod
    def quick_add_product(cls, name_or_url: str) -> Dict[str, Any]:
        """Creates a new product directly from mobile by name or TikTok link."""
        name_or_url = (name_or_url or "").strip()
        if not name_or_url:
            raise ValueError("กรุณาระบุชื่อสินค้าหรือลิงก์สินค้า")

        is_url = name_or_url.startswith("http://") or name_or_url.startswith("https://")
        product_name = name_or_url
        cover_image = ""
        category = "IT / Gadget"

        if is_url:
            try:
                from scripts.api_products import resolve_tiktok_product_id
                resolved = resolve_tiktok_product_id(name_or_url)
                if resolved.get("success"):
                    from scripts.product_scraper import ProductScraper
                    scraped = ProductScraper.scrape(name_or_url)
                    if scraped.get("title"):
                        product_name = scraped["title"]
                    if scraped.get("images"):
                        first_img = scraped["images"][0]
                        cover_image = first_img.get("url") if isinstance(first_img, dict) else str(first_img)
            except Exception as scrape_err:
                print(f"⚠️ [quick_add_product] scrape fallback: {scrape_err}")
                product_name = "สินค้าใหม่ TikTok"

        created_product = ProductStore.add(
            name=product_name,
            category=category,
            thumbnail=cover_image,
            angles=[]
        )
        p_id = created_product["id"]

        cls.create_quick_angle(
            p_id,
            title=f"⚡ รีวิว {product_name} ดีไหม น่าใช้ไหม?",
            script=(
                f"วันนี้หยิบ {product_name} มารีวิวให้ดูกันชัดๆ ครับ\n"
                f"ของจริงสวยมาก ฟังก์ชันการใช้งานตอบโจทย์ คุ้มค่าเกินราคาจริงๆ\n"
                f"ใครที่กำลังมองหาของดีมีคุณภาพ แนะนำตัวนี้เลยครับ\n"
                f"พิกัดราคาโปรโมชั่น ในตะกร้าสีเหลือง ซ้ายล่างตอนนี้ กดสั่งได้เลยครับ"
            )
        )
        return ProductStore.get(p_id)

    @classmethod
    def get_or_create_session(cls, product_id: str, angle_id: str) -> Dict[str, Any]:
        """Gets existing recording session or creates a new one for guided filming."""
        product = ProductStore.get(product_id)
        if not product:
            raise ValueError(f"ไม่พบสินค้า ID: {product_id}")

        angle = _find_angle(product, angle_id)
        resolved_angle_id = _angle_id(angle)
        shot_list_record = ShotListsStore.get(product_id, resolved_angle_id)
        if not shot_list_record or not shot_list_record.get("shot_list"):
            try:
                generate_shot_list_for_angle(product_id, resolved_angle_id)
            except Exception as sl_err:
                print(f"⚠️ [get_or_create_session] shot list warning: {sl_err}")
                ShotListsStore.upsert({
                    "product_id": product_id,
                    "angle_id": resolved_angle_id,
                    "batch": 1,
                    "shot_list": [
                        {"beat_index": 0, "role": "hook", "start": 0, "end": 3, "planned_duration": 3, "text": "Hook เปิดคลิป"},
                        {"beat_index": 1, "role": "feature", "start": 3, "end": 15, "planned_duration": 12, "text": "รีวิวฟังก์ชัน"},
                        {"beat_index": 2, "role": "cta", "start": 15, "end": 20, "planned_duration": 5, "text": "สั่งซื้อในตะกร้า"},
                    ]
                }, batch=1)

        session = RecordingSessionStore.create(product_id, resolved_angle_id)
        return session

    @classmethod
    def assemble_and_render(
        cls,
        product_id: str,
        angle_id: str,
        session_id: Optional[str] = None,
        custom_raw_video: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes Step 3: Auto-Assemble & SOP Render.
        1. Finalizes session if needed
        2. Configures SOP Gadget Standard (Fenrir voice, Mali-Bold Ghost Subtitles, #FF6622 Spec Callouts, Upbeat BGM)
        3. Spawns background render job with TaskManager
        4. Saves project draft to 03_Projects/ (Dual-Mode Desktop Compatible)
        """
        product = ProductStore.get(product_id)
        if not product:
            raise ValueError(f"ไม่พบสินค้า ID: {product_id}")

        angle = _find_angle(product, angle_id)
        script_text = _script_text(angle)
        if not script_text:
            raise ValueError("มุมนี้ยังไม่มีสคริปต์ กรุณาเตรียมสคริปต์ก่อนประกอบคลิป")

        session = RecordingSessionStore.get(session_id) if session_id else None
        if session_id and not session:
            raise ValueError("ไม่พบเซสชันถ่ายทำ กรุณาเปิดหน้าถ่ายทำใหม่")
        if session and (session.get("product_id") != product_id or session.get("angle_id") != angle_id):
            raise ValueError("เซสชันถ่ายทำไม่ตรงกับสินค้าและมุมที่เลือก")

        raw_video_path = custom_raw_video
        needs_finalize = False
        if not raw_video_path and session:
            if session.get("status") == "completed":
                raw_video_path = session.get("raw_video_path")
                if not raw_video_path:
                    raise ValueError("เซสชันที่เสร็จแล้วไม่มีไฟล์วัตถุดิบ")
            else:
                segments = session.get("segments") or []
                needs_finalize = bool(segments) and all(s.get("status") == "uploaded" for s in segments)
                if not needs_finalize and any(s.get("status") == "uploaded" for s in segments):
                    raise ValueError("ถ่ายไม่ครบทุกช็อต กรุณากลับไปถ่ายทำให้ครบ")
        if not raw_video_path and not needs_finalize:
            raw_video_path = _attached_raw(angle)
        if not raw_video_path and not needs_finalize:
            prod_raw_dir = (RAW_DIR / product_id).resolve()
            if not prod_raw_dir.is_relative_to(RAW_DIR.resolve()):
                raise ValueError("รหัสสินค้าไม่ถูกต้อง")
            files = sorted(f for f in prod_raw_dir.glob("*") if f.suffix.lower() in {".mov", ".mp4", ".webm"})
            if len(files) == 1:
                raw_video_path = str(files[0])
        if not raw_video_path and not needs_finalize:
            raise ValueError("ยังไม่มีคลิปวิดีโอวัตถุดิบ กรุณาถ่ายทำหรือเลือกคลิปก่อนประกอบคลิป")
        if raw_video_path:
            raw_video_path = str(_raw_path(raw_video_path))

        product_name = product.get("name") or "Gadget"
        hook_headline = angle.get("hook_title") or (angle.get("hook") or {}).get("headline") or angle.get("angle_name") or angle.get("name") or "รีวิวเจาะลึก"

        # Extract specs for SOP Callouts (#FF6622 orange)
        specs = product.get("specs") or []
        if isinstance(specs, dict):
            features = [f"{k}: {v}" for k, v in list(specs.items())[:3]]
        else:
            features = [f"{spec.get('label', '')}: {spec.get('value', '')}" for spec in specs[:3] if isinstance(spec, dict)]
        key_features = angle.get("key_features") or ", ".join(features)

        # Unique Project Name
        safe_name = re.sub(r'[\\/*?:"<>| ]', '_', product_name)[:30]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        project_name = f"Mobile_{timestamp}_{safe_name}_{uuid.uuid4().hex[:8]}"

        # Create Task
        task = TaskManager.create_task(
            task_type="mobile_auto_assemble_render",
            title=f"⚡ Auto-Assemble & SOP Render: {product_name}",
            payload={
                "product_id": product_id,
                "angle_id": angle_id,
                "project_name": project_name,
                "raw_video_path": raw_video_path,
                "session_id": session_id,
            },
            target_tab="mobile_studio",
            target_id=product_id
        )
        task_id = task["id"]
        render_jobs.create_job(task_id, "รอคิวประกอบคลิปมือถือ")

        def _run_worker():
            try:
                with render_jobs.render_slot(task_id):
                    if render_jobs.is_cancel_requested(task_id):
                        raise render_jobs.RenderCancelled("งานถูกยกเลิก")
                    TaskManager.update_progress(task_id, 0.10, "กำลังวิเคราะห์ช็อตและสร้างเสียงพากย์ Fenrir (SOP)")

                    source_path = raw_video_path
                    if needs_finalize:
                        source_path = str(_raw_path(RecordingSessionStore.finalize(session_id).get("raw_video_path")))

                    def on_progress(p_msg, p_val):
                        scaled = 0.10 + (p_val * 0.85)
                        TaskManager.update_progress(task_id, round(scaled, 2), p_msg)
                        render_jobs.update_progress(task_id, round(scaled, 2), p_msg)

                    # Execute pipeline with strict SOP settings
                    result = TikTokAutoCutterPipeline.run(
                        product_name=product_name,
                        raw_video_path=str(source_path),
                        project_name=project_name,
                        key_features=key_features,
                        custom_script=script_text,
                        voice="Fenrir",
                        voice_engine_type="gemini_tts",
                        voice_preset="gemini_fenrir_male_strong",
                        font_name="Mali",
                        ghost_reveal=True,
                        bgm_name=DEFAULT_BGM,
                        bgm_volume=0.14,
                        export_mp4=True,
                        export_preset="post",
                        product_id=product_id,
                        angle_id=angle_id,
                        product_meta=product,
                        angle_meta=angle,
                        cancel_event=render_jobs.get_cancel_event(task_id),
                        progress_callback=on_progress
                    )

                    mp4_path = result.get("mp4_video") or result.get("mp4") or result.get("output_video") or result.get("video_path")
                    if not mp4_path:
                        raise ValueError("เรนเดอร์ไม่สำเร็จ: ไม่ได้รับไฟล์วิดีโอจาก pipeline")
                    output_path = Path(mp4_path)
                    if not output_path.is_absolute():
                        output_path = BASE_DIR / output_path
                    output_path = output_path.resolve()
                    if not output_path.is_relative_to(EXPORTS_DIR.resolve()):
                        raise ValueError("ไฟล์เรนเดอร์อยู่นอกโฟลเดอร์ผลงาน")
                    if not output_path.is_file() or output_path.stat().st_size == 0:
                        raise ValueError("เรนเดอร์ไม่สำเร็จ: ไม่พบไฟล์วิดีโอหรือไฟล์ว่างเปล่า")
                    mp4_path = str(output_path)
                    rel_url = "/api/media/" + quote(output_path.relative_to(BASE_DIR.resolve()).as_posix(), safe="/")

                    if render_jobs.is_cancel_requested(task_id):
                        raise render_jobs.RenderCancelled("งานถูกยกเลิก")
                    render_jobs.complete_job(task_id, {**result, "project_name": project_name, "mp4_video": mp4_path})

                    # Attach to product store
                    try:
                        ProductStore.attach_project(product_id, project_name)
                        ProductStore.update_angle_status(
                            product_id,
                            angle_id,
                            "rendered" if mp4_path else "in_production",
                            video_url=rel_url or None,
                            project_name=project_name,
                            export_id=result.get("export_id")
                        )
                    except Exception as store_err:
                        print(f"[MobileQuickStudio] Warning updating store: {store_err}")

                    TaskManager.complete_task(
                        task_id,
                        result={
                            "project_name": project_name,
                            "video_path": mp4_path,
                            "video_url": rel_url,
                            "product_name": product_name,
                            "hook_headline": hook_headline,
                            "hashtags": f"#{safe_name} #รีวิวไอที #tiktokshop #omnicut",
                            "mix_degraded": bool(result.get("mix_degraded")),
                            "mix_degraded_reason": result.get("mix_degraded_reason"),
                        },
                        step_label="🎉 ประกอบคลิปและเรนเดอร์สำเร็จ พร้อมโพสต์ TikTok!"
                    )
            except render_jobs.RenderCancelled:
                render_jobs.cancel_job(task_id)
                TaskManager.cancel_task(task_id)
            except Exception as exc:
                import traceback
                print(f"[MobileQuickStudio] Worker failed: {exc}")
                traceback.print_exc()
                render_jobs.fail_job(task_id, exc)
                TaskManager.fail_task(task_id, str(exc), step_label="ประกอบคลิปไม่สำเร็จ")

        TaskManager.run_in_background(_run_worker)

        return {
            "success": True,
            "task_id": task_id,
            "project_name": project_name,
            "message": "ระบบกำลังประกอบคลิปและเรนเดอร์ด้วย SOP อัตโนมัติ"
        }
