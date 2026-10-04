"""
OmniCut Mobile Quick Studio Engine (Backend).
Handles 3-step mobile production workflow:
1. Product & Angle Catalog optimized for fast mobile touch UI
2. Automatic Guided Take assembly & SOP styling (Fenrir voice, Mali-Bold Ghost Reveal, orange callouts)
3. One-touch Master Render with TikTok sharing metadata
"""

import hashlib
import re
import time
import uuid
from urllib.parse import quote
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import (
    BASE_DIR, EXPORTS_DIR, RAW_DIR, INBOX_DIR, COVERS_DIR
)
from scripts.product_store import ProductStore
from scripts.shot_lists_store import ShotListsStore
from scripts import recording_sessions, render_jobs
from scripts.recording_sessions import RecordingSessionStore
from scripts.shot_list_builder import generate_shot_list_for_angle
from scripts.task_manager import TaskManager, TaskStatus
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
        "status": "scripted",
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


def _find_duplicate_raw(prod_raw_dir: Path, size: int, digest: str) -> Optional[Path]:
    """Zero-duplicate guard: return an existing take with the same size + SHA-256.

    เทียบ size ก่อนเพื่อไม่ต้องเปิดอ่านไฟล์ทุกไฟล์ (วิดีโออาจใหญ่หลายร้อย MB)
    แล้วค่อยยืนยันด้วย SHA-256 ตาม `.agents/rules/asset_sourcing_and_deduplication.md`
    """
    if not prod_raw_dir.is_dir() or size <= 0:
        return None
    for candidate in sorted(prod_raw_dir.iterdir()):
        if not candidate.is_file() or candidate.suffix.lower() not in {".mp4", ".mov", ".m4v"}:
            continue
        try:
            if candidate.stat().st_size != size:
                continue
            if hashlib.sha256(candidate.read_bytes()).hexdigest() == digest:
                return candidate
        except OSError:
            continue
    return None


def _sessions():
    return sorted(recording_sessions._TABLE.load(), key=lambda r: r.get("updated_at") or r.get("created_at") or "", reverse=True)


def _media_url(path_str: Optional[str]) -> Optional[str]:
    """Helper to safely format store relative path into browser /api/media/ URL."""
    if not path_str:
        return None
    s = str(path_str).replace("\\", "/").strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/api/media/"):
        s = s[len("/api/media/"):]
    elif s.startswith("api/media/"):
        s = s[len("api/media/"):]
    s = s.lstrip("/")
    return "/api/media/" + quote(s, safe="/")


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
                raw_status = angle.get("status") or "draft"
                is_rendered = bool(angle.get("video_url") or raw_status in ("rendered", "posted"))
                has_footage = bool(attached_raw)
                attached_name = Path(str(attached_raw)).name if attached_raw else None

                if raw_status == "posted":
                    effective_status = "posted"
                elif raw_status == "in_production":
                    effective_status = "in_production"
                elif is_rendered or raw_status == "rendered":
                    effective_status = "rendered"
                else:
                    effective_status = raw_status

                cov_3x4 = angle.get("cover_3x4_path")
                cov_9x16 = angle.get("cover_9x16_path")
                cov_primary = cov_9x16 or angle.get("cover_path") or cov_3x4

                mobile_angles.append({
                    "id": a_id,
                    "angle_id": a_id,
                    "name": a_name,
                    "hook_headline": hook_headline,
                    "hook_sub": hook_sub,
                    "script_preview": (script_text[:120] + "...") if len(script_text) > 120 else script_text,
                    "script_full": script_text,

                    "shot_count": shot_count,
                    "status": effective_status,
                    "is_rendered": is_rendered,
                    "has_footage": has_footage,
                    "attached_raw": attached_raw,
                    "attached_raw_name": attached_name,
                    "render_status": "rendered" if is_rendered else ("ready_to_cut" if has_footage else "draft"),
                    "has_session": session is not None,
                    "session_id": session.get("id") if session else None,
                    "session_status": session.get("status") if session else None,
                    "rendered_video_url": _media_url(angle.get("video_url")),
                    "export_id": angle.get("export_id"),
                    "project_name": angle.get("project_name"),
                    "posted_at": angle.get("posted_at"),
                    "cover_path": angle.get("cover_path"),
                    "cover_url": _media_url(cov_primary),
                    "cover_3x4_path": cov_3x4,
                    "cover_3x4_url": _media_url(cov_3x4),
                    "cover_9x16_path": cov_9x16,
                    "cover_9x16_url": _media_url(cov_9x16),
                    "qc_reviewed": angle.get("qc_reviewed"),
                    "qc_note": angle.get("qc_note"),
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

        prod_raw_dir = RAW_DIR / product_id
        prod_raw_dir.mkdir(parents=True, exist_ok=True)

        # P2-2 / กฎ 13: ตรวจ checksum ก่อนเขียนเสมอ — ไฟล์ซ้ำใช้ไฟล์เดิม ไม่เขียนทับ/เพิ่มซ้ำ
        digest = hashlib.sha256(file_bytes).hexdigest()
        duplicate = _find_duplicate_raw(prod_raw_dir, len(file_bytes), digest)
        if duplicate is not None:
            dest_path = duplicate
            deduplicated = True
        else:
            safe_name = f"mobile_take_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
            dest_path = prod_raw_dir / safe_name
            dest_path.write_bytes(file_bytes)
            deduplicated = False
        safe_name = dest_path.name

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

        if isinstance(file_info, dict):
            file_info["sha256"] = digest

        # add_video_to_product dedupes by path/rel_path internally, so a
        # deduplicated take re-attaches without creating a second entry.
        ProductStore.add_video_to_product(product_id, file_info)
        ProductStore.update_angle_videos(product_id, resolved_angle_id, [rel_path])

        return {
            "success": True,
            "filename": safe_name,
            "video_path": rel_path,
            "file_info": file_info,
            "sha256": digest,
            "deduplicated": deduplicated,
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
        tiktok_pid = None

        if is_url:
            all_prods = ProductStore.list()
            existing = next((p for p in all_prods if p.get("url") == name_or_url), None)
            if existing:
                return existing

            try:
                from scripts.api_products import resolve_tiktok_product_id
                resolved = resolve_tiktok_product_id(name_or_url)
                if resolved.get("success"):
                    tiktok_pid = resolved.get("product_id")
                    from scripts.product_scraper import ProductScraper
                    scraper_fn = getattr(ProductScraper, "scrape_url", None) or getattr(ProductScraper, "scrape", None)
                    if scraper_fn:
                        scraped = scraper_fn(name_or_url)
                        if scraped and scraped.get("title"):
                            product_name = scraped["title"]
                        if scraped and scraped.get("images"):
                            first_img = scraped["images"][0]
                            cover_image = first_img.get("url") if isinstance(first_img, dict) else str(first_img)
            except Exception as scrape_err:
                print(f"⚠️ [quick_add_product] scrape fallback: {scrape_err}")
                product_name = "สินค้าใหม่ TikTok"

        created_product = ProductStore.add(
            name=product_name,
            category=category,
            thumbnail=cover_image,
            angles=[],
            url=name_or_url if is_url else "",
            tiktok_product_id=tiktok_pid or "",
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
        custom_raw_video: Optional[str] = None,
        bgm_enabled: bool = True
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
        if angle.get("status") == "posted" or angle.get("posted_at"):
            raise ValueError(f"มุมนำเสนอ '{angle_id}' ได้รับการเผยแพร่ (Posted) แล้ว ไม่อนุญาตให้เรนเดอร์ทับ")

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

        # Preflight: Disk space check (>500MB)
        import shutil
        disk_target = EXPORTS_DIR if EXPORTS_DIR.exists() else BASE_DIR
        try:
            free_bytes = shutil.disk_usage(disk_target).free
            if free_bytes < 500 * 1024 * 1024:
                raise ValueError("พื้นที่ดิสก์ไม่เพียงพอสำหรับการเรนเดอร์ (เหลือน้อยกว่า 500MB)")
        except OSError as disk_err:
            print(f"⚠️ [MobileQuickStudio] Disk space probe warning: {disk_err}")

        # Idempotency guard: resume existing running task if duplicate request
        active_tasks = TaskManager.get_active_tasks(limit=100)
        for t in active_tasks:
            if t.get("status") in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
                payload = t.get("payload") or {}
                if (
                    t.get("type") == "mobile_auto_assemble_render"
                    and payload.get("product_id") == product_id
                    and payload.get("angle_id") == angle_id
                ):
                    return {
                        "success": True,
                        "task_id": t["id"],
                        "project_name": payload.get("project_name", ""),
                        "message": "ระบบกำลังประมวลผลงานเดิมอยู่แล้ว กำลังเชื่อมต่อเข้าสู่งานเดิม",
                        "resumed": True
                    }

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

                    # Set status to in_production in store
                    try:
                        ProductStore.update_angle_status(product_id, angle_id, "in_production", project_name=project_name)
                    except Exception as pre_err:
                        print(f"[MobileQuickStudio] Warning setting in_production: {pre_err}")

                    source_path = raw_video_path
                    if needs_finalize:
                        source_path = str(_raw_path(RecordingSessionStore.finalize(session_id).get("raw_video_path")))

                    def on_progress(p_msg, p_val):
                        scaled = 0.10 + (p_val * 0.85)
                        TaskManager.update_progress(task_id, round(scaled, 2), p_msg)
                        render_jobs.update_progress(task_id, round(scaled, 2), p_msg)

                    # Multi-source support
                    selected_videos = angle.get("selected_videos") or []
                    multi_paths = []
                    for sv in selected_videos:
                        try:
                            p = _raw_path(sv)
                            if p and p.is_file():
                                multi_paths.append(str(p))
                        except Exception:
                            pass

                    pipeline_kwargs = {
                        "product_name": product_name,
                        "raw_video_path": str(source_path),
                        "project_name": project_name,
                        "key_features": key_features,
                        "custom_script": script_text,
                        "voice": "Fenrir",
                        "voice_engine_type": "gemini_tts",
                        "voice_preset": "gemini_fenrir_male_strong",
                        "font_name": "Mali",
                        "ghost_reveal": True,
                        "bgm_name": DEFAULT_BGM if bgm_enabled else None,
                        "bgm_volume": 0.14 if bgm_enabled else 0.0,
                        "export_mp4": True,
                        "export_preset": "post",
                        "product_id": product_id,
                        "angle_id": angle_id,
                        "product_meta": product,
                        "angle_meta": angle,
                        "cancel_event": render_jobs.get_cancel_event(task_id),
                        "progress_callback": on_progress
                    }
                    if len(multi_paths) > 1:
                        pipeline_kwargs["multi_video_paths"] = multi_paths

                    # Execute pipeline with strict SOP settings
                    result = TikTokAutoCutterPipeline.run(**pipeline_kwargs)

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
                    rel_store_path = output_path.relative_to(BASE_DIR.resolve()).as_posix()
                    rel_url = "/api/media/" + quote(rel_store_path, safe="/")

                    if render_jobs.is_cancel_requested(task_id):
                        raise render_jobs.RenderCancelled("งานถูกยกเลิก")

                    # Resolve cover variants
                    cover_3x4_path = result.get("cover_3x4_path") or result.get("cover_3x4")
                    cover_9x16_path = result.get("cover_9x16_path") or result.get("cover_9x16") or result.get("cover_path")
                    if not cover_9x16_path and output_path:
                        stem = output_path.stem
                        for cand in (
                            COVERS_DIR / f"{stem}_cover.jpg",
                            COVERS_DIR / f"{stem}_cover_9x16.jpg",
                        ):
                            if cand.is_file():
                                cover_9x16_path = str(cand.relative_to(BASE_DIR.resolve())).replace("\\", "/")
                                break
                    if not cover_3x4_path and output_path:
                        stem = output_path.stem
                        cand_3x4 = COVERS_DIR / f"{stem}_cover_3x4.jpg"
                        if cand_3x4.is_file():
                            cover_3x4_path = str(cand_3x4.relative_to(BASE_DIR.resolve())).replace("\\", "/")

                    # Attach to product store with relative path (MUST succeed before completing job)
                    ProductStore.attach_project(product_id, project_name)
                    ProductStore.update_angle_status(
                        product_id,
                        angle_id,
                        "rendered" if mp4_path else "in_production",
                        video_url=rel_store_path or None,
                        project_name=project_name,
                        export_id=result.get("export_id"),
                        cover_path=cover_9x16_path or cover_3x4_path,
                        cover_3x4_path=cover_3x4_path,
                        cover_9x16_path=cover_9x16_path
                    )

                    render_jobs.complete_job(task_id, {
                        **result,
                        "project_name": project_name,
                        "mp4_video": mp4_path,
                        "cover_3x4_path": cover_3x4_path,
                        "cover_9x16_path": cover_9x16_path
                    })

                    cover_9x16_url = _media_url(cover_9x16_path)
                    cover_3x4_url = _media_url(cover_3x4_path)
                    cover_url = cover_9x16_url or cover_3x4_url

                    TaskManager.complete_task(
                        task_id,
                        result={
                            "project_name": project_name,
                            "video_path": mp4_path,
                            "video_url": rel_url,
                            "cover_path": cover_9x16_path or cover_3x4_path,
                            "cover_url": cover_url,
                            "cover_9x16_url": cover_9x16_url,
                            "cover_3x4_url": cover_3x4_url,
                            "export_id": result.get("export_id"),
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
                try:
                    ProductStore.update_angle_status(product_id, angle_id, "draft", project_name=project_name)
                except Exception:
                    pass
            except Exception as exc:
                import traceback
                print(f"[MobileQuickStudio] Worker failed: {exc}")
                traceback.print_exc()
                render_jobs.fail_job(task_id, exc)
                TaskManager.fail_task(task_id, str(exc), step_label="ประกอบคลิปไม่สำเร็จ")
                try:
                    ProductStore.update_angle_status(product_id, angle_id, "draft", project_name=project_name)
                except Exception:
                    pass

        TaskManager.run_in_background(_run_worker)

        return {
            "success": True,
            "task_id": task_id,
            "project_name": project_name,
            "message": "ระบบกำลังประกอบคลิปและเรนเดอร์ด้วย SOP อัตโนมัติ"
        }
