"""
API Router for Product Scraping, Content Planning, and Video Attachments.
"""

import re
import time
import shutil
import urllib.request
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks

from scripts.config import BASE_DIR, RAW_DIR
from scripts.product_scraper import ProductScraper
from scripts.product_store import ProductStore
from scripts.task_manager import TaskManager
from scripts.media_service import get_file_info
from scripts.tts_sanitizer import TTSSanitizer

router = APIRouter(tags=["Products"])


def resolve_tiktok_product_id(url_or_id: str) -> Dict[str, Any]:
    """Extracts or resolves a TikTok numeric Product ID from ID, full URL, or shortlink."""
    cleaned = (url_or_id or "").strip()
    if not cleaned:
        return {"success": False, "product_id": None, "resolved_url": None}

    # 1. Direct 10+ digit number
    if re.fullmatch(r"\d{10,}", cleaned):
        return {"success": True, "product_id": cleaned, "resolved_url": None}

    # 2. Extract from string if it matches standard product URL patterns
    m = re.search(r"/(?:product|item)/(\d{10,})", cleaned) or re.search(r"[?&](?:item_id|itemId|product_id)=(\d{10,})", cleaned)
    if m:
        return {"success": True, "product_id": m.group(1), "resolved_url": cleaned}

    # 3. If it looks like a URL (e.g. vt.tiktok.com shortlink or web link), resolve redirect
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        try:
            req = urllib.request.Request(
                cleaned,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                final_url = resp.geturl()
                m2 = re.search(r"/(?:product|item)/(\d{10,})", final_url) or re.search(r"[?&](?:item_id|itemId|product_id)=(\d{10,})", final_url)
                if m2:
                    return {"success": True, "product_id": m2.group(1), "resolved_url": final_url}
                m3 = re.search(r"(\d{15,})", final_url)
                if m3:
                    return {"success": True, "product_id": m3.group(1), "resolved_url": final_url}
                return {"success": False, "product_id": None, "resolved_url": final_url}
        except Exception as e:
            print(f"Notice: Failed to resolve redirect for {cleaned}: {e}")

    # 4. Fallback: check any 15+ consecutive digits anywhere in input
    m4 = re.search(r"(\d{15,})", cleaned)
    if m4:
        return {"success": True, "product_id": m4.group(1), "resolved_url": None}

    return {"success": False, "product_id": None, "resolved_url": None}


@router.post("/api/products/resolve-tiktok-id")
def resolve_tiktok_id_endpoint(payload: Dict[str, Any]):
    """Resolves a raw string, direct ID, full URL, or shortlink to a numeric TikTok Product ID."""
    url_or_id = payload.get("url_or_id", "")
    return resolve_tiktok_product_id(url_or_id)


@router.post("/api/products/{product_id}/videos")
def attach_video_to_product(product_id: str, payload: Dict[str, Any]):
    """Links an existing video file to a product."""
    video_path = payload.get("video_path")
    if not video_path:
        raise HTTPException(status_code=400, detail="Missing video_path")

    v_path = Path(video_path)
    if not v_path.is_absolute():
        v_path = BASE_DIR / video_path

    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    file_info = get_file_info(v_path)
    updated = ProductStore.add_video_to_product(product_id, file_info)
    return {"success": True, "product": updated}


@router.delete("/api/products/{product_id}/videos")
def remove_video_from_product(product_id: str, video_path: str):
    """Unlinks a video file from a product."""
    v_path = Path(video_path)
    if not v_path.is_absolute():
        v_path = BASE_DIR / video_path

    prod_dir = (RAW_DIR / product_id).resolve()
    if v_path.exists():
        try:
            if v_path.resolve().is_relative_to(prod_dir):
                target_path = RAW_DIR / v_path.name
                if target_path.exists():
                    target_path = RAW_DIR / f"{v_path.stem}_{int(time.time())}{v_path.suffix}"
                shutil.move(str(v_path), str(target_path))
        except Exception as e:
            print(f"Notice: Failed to move unlinked video: {e}")

    updated = ProductStore.remove_video_from_product(product_id, video_path)
    return {"success": True, "product": updated}


@router.patch("/api/products/{product_id}/angles/{angle_id}")
def update_product_angle_status(product_id: str, angle_id: str, payload: Dict[str, Any]):
    """Updates status (draft, scripted, in_production, rendered, posted) of a specific angle script.

    Optional payload fields:
      qc_note       – free-text QC failure reason (stored on the angle for Studio reference)
      clear_qc_note – boolean; set True to wipe a previous qc_note when the clip passes QC
    """
    status = payload.get("status")
    video_url = payload.get("video_url")
    project_name = payload.get("project_name")
    qc_note = payload.get("qc_note")          # str | None
    clear_qc_note = bool(payload.get("clear_qc_note", False))
    clear_conflict_note = bool(payload.get("clear_conflict_note", False))
    if not status:
        raise HTTPException(status_code=400, detail="Missing status")
    try:
        updated = ProductStore.update_angle_status(
            product_id,
            angle_id,
            status,
            video_url=video_url,
            project_name=project_name,
            qc_note=qc_note,
            clear_qc_note=clear_qc_note,
            clear_conflict_note=clear_conflict_note,
        )
        return {"success": True, "product": updated}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.post("/api/products/{product_id}/angles/{angle_id}/videos")
def update_angle_videos_endpoint(product_id: str, angle_id: str, payload: Dict[str, Any]):
    """Persists selected raw footage attachments for a specific script angle."""
    try:
        selected_videos = payload.get("selected_videos", [])
        updated = ProductStore.update_angle_videos(product_id, angle_id, selected_videos)
        return {"success": True, "product": updated}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/products/{product_id}/default-videos")
def set_default_videos_endpoint(product_id: str, payload: Dict[str, Any]):
    """Sets default raw footage attachments for all script angles in a product."""
    try:
        selected_videos = payload.get("selected_videos", [])
        updated = ProductStore.set_default_videos_for_all_angles(product_id, selected_videos)
        return {"success": True, "product": updated}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/products/scrape-and-plan")
def scrape_and_plan(payload: Dict[str, Any]):
    """Scrapes product info or accepts raw text/keywords/images and generates Content Matrix."""
    url = payload.get("url", "").strip()
    raw_text = payload.get("raw_text", "").strip()
    custom_keyword = payload.get("custom_keyword", "").strip()
    image_path = payload.get("image_path", "").strip()

    if not url and not raw_text and not custom_keyword and not image_path:
        raise HTTPException(status_code=400, detail="กรุณาระบุลิงก์ ข้อความรายละเอียด หรือรูปภาพสินค้า")

    try:
        if url:
            product_info = ProductScraper.scrape_url(url)
        else:
            product_info = {
                "platform": "manual",
                "url": "",
                "title": custom_keyword or "สินค้า",
                "description": raw_text or custom_keyword,
                "price_note": "ราคาพิเศษในตะกร้า",
                "raw_text": raw_text or custom_keyword,
                "images": [],
                "image_count": 0
            }

        if image_path:
            img_p = Path(image_path)
            img_name = img_p.name
            img_rel = str(img_p.relative_to(BASE_DIR)).replace("\\", "/") if BASE_DIR in img_p.parents else img_name
            product_info["images"] = [{"name": img_name, "rel_path": img_rel, "local_path": str(img_p)}]
            product_info["image_count"] = 1
            product_info["thumbnail"] = img_rel
            if not custom_keyword and not raw_text:
                clean_title = img_p.stem.replace("_", " ").replace("-", " ")
                product_info["title"] = clean_title or "สินค้า"
                product_info["description"] = f"สินค้าจากภาพ {img_name}"

        if custom_keyword:
            product_info["title"] = custom_keyword
        if raw_text and len(raw_text) > 10:
            product_info["description"] = raw_text
            product_info["raw_text"] = f"{product_info.get('title', '')}\n{raw_text}"

        angle_count = int(payload.get("angle_count", 10))
        tiktok_product_id = str(payload.get("tiktok_product_id") or "").strip()
        if tiktok_product_id:
            resolved = resolve_tiktok_product_id(tiktok_product_id)
            if resolved.get("success") and resolved.get("product_id"):
                tiktok_product_id = resolved["product_id"]
        elif url:
            resolved = resolve_tiktok_product_id(url)
            if resolved.get("success") and resolved.get("product_id"):
                tiktok_product_id = resolved["product_id"]

        angles = ProductScraper.generate_content_matrix(product_info, count=angle_count)

        thumbnail_img = ""
        if product_info.get("images") and len(product_info["images"]) > 0:
            thumbnail_img = product_info["images"][0].get("rel_path", "")

        saved_prod = ProductStore.add(
            name=product_info.get("title", "สินค้า"),
            url=product_info.get("url", ""),
            platform=product_info.get("platform", ""),
            category="IT / Gadget",
            price_note=product_info.get("price_note", ""),
            thumbnail=thumbnail_img,
            angles=angles,
            images=product_info.get("images", []),
            tiktok_product_id=tiktok_product_id or None,
        )
        product_info["id"] = saved_prod["id"]
        product_info["tiktok_product_id"] = saved_prod.get("tiktok_product_id")

        return {
            "success": True,
            "product": product_info,
            "saved_product": saved_prod,
            "angles": angles
        }
    except Exception as e:
        print(f"[API] Scrape and plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _execute_scrape_and_plan_worker(task_id: str, payload: Dict[str, Any]):
    """Background worker that executes product scrape & script generation."""
    try:
        TaskManager.update_progress(task_id, 0.15, "กำลังดึงข้อมูลและสเปกสินค้า")
        url = payload.get("url", "").strip()
        raw_text = payload.get("raw_text", "").strip()
        custom_keyword = payload.get("custom_keyword", "").strip()
        image_path = payload.get("image_path", "").strip()
        angle_count = int(payload.get("angle_count", 7))

        if url:
            TaskManager.update_progress(task_id, 0.30, f"กำลังดึงข้อมูลจากร้านค้า: {url[:35]}")
            product_info = ProductScraper.scrape_url(url)
        else:
            product_info = {
                "platform": "manual",
                "url": "",
                "title": custom_keyword or "สินค้า",
                "description": raw_text or custom_keyword,
                "price_note": "ราคาพิเศษในตะกร้า",
                "raw_text": raw_text or custom_keyword,
                "images": [],
                "image_count": 0
            }

        if image_path:
            img_p = Path(image_path)
            img_name = img_p.name
            img_rel = str(img_p.relative_to(BASE_DIR)).replace("\\", "/") if BASE_DIR in img_p.parents else img_name
            product_info["images"] = [{"name": img_name, "rel_path": img_rel, "local_path": str(img_p)}]
            product_info["image_count"] = 1
            product_info["thumbnail"] = img_rel
            if not custom_keyword and not raw_text:
                clean_title = img_p.stem.replace("_", " ").replace("-", " ")
                product_info["title"] = clean_title or "สินค้า"
                product_info["description"] = f"สินค้าจากภาพ {img_name}"

        if custom_keyword:
            product_info["title"] = custom_keyword
        if raw_text and len(raw_text) > 10:
            product_info["description"] = raw_text
            product_info["raw_text"] = f"{product_info.get('title', '')}\n{raw_text}"

        title_display = product_info.get("title", custom_keyword or "สินค้า")
        if len(title_display) > 35:
            title_display = title_display[:35]

        TaskManager.update_progress(task_id, 0.55, f"AI กำลังแต่ง {angle_count} สคริปต์ ({title_display})")
        angles = ProductScraper.generate_content_matrix(product_info, count=angle_count)

        TaskManager.update_progress(task_id, 0.85, "กำลังปรับแต่งบทพูดสำหรับเสียงพากย์ AI (TTS Sanitizer)")
        angles = TTSSanitizer.process_angles(angles)

        TaskManager.update_progress(task_id, 0.95, "กำลังบันทึกลงแคตตาล็อกสินค้า")
        thumbnail_img = ""
        if product_info.get("images") and len(product_info["images"]) > 0:
            thumbnail_img = product_info["images"][0].get("rel_path", "")

        tiktok_product_id = str(payload.get("tiktok_product_id") or "").strip()
        if tiktok_product_id:
            resolved = resolve_tiktok_product_id(tiktok_product_id)
            if resolved.get("success") and resolved.get("product_id"):
                tiktok_product_id = resolved["product_id"]
        elif url:
            resolved = resolve_tiktok_product_id(url)
            if resolved.get("success") and resolved.get("product_id"):
                tiktok_product_id = resolved["product_id"]

        saved_prod = ProductStore.add(
            name=product_info.get("title", "สินค้า"),
            url=product_info.get("url", ""),
            platform=product_info.get("platform", ""),
            category="IT / Gadget",
            price_note=product_info.get("price_note", ""),
            thumbnail=thumbnail_img,
            angles=angles,
            images=product_info.get("images", []),
            tiktok_product_id=tiktok_product_id or None,
        )
        product_info["id"] = saved_prod["id"]
        product_info["tiktok_product_id"] = saved_prod.get("tiktok_product_id")

        result_data = {
            "product": product_info,
            "saved_product": saved_prod,
            "angles": angles
        }

        TaskManager.complete_task(
            task_id,
            result=result_data,
            step_label=f"🎉 สำเร็จ! สร้าง {len(angles)} สคริปต์เรียบร้อย",
            target_id=saved_prod["id"]
        )
    except Exception as e:
        print(f"❌ [TaskManager] Scrape task failed ({task_id}): {e}")
        TaskManager.fail_task(task_id, str(e), step_label="วิเคราะห์สินค้าไม่สำเร็จ")


@router.post("/api/products/scrape-and-plan-async")
def scrape_and_plan_async(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Launches Scrape & Plan as a persistent background task, returning job ID immediately."""
    url = payload.get("url", "").strip()
    raw_text = payload.get("raw_text", "").strip()
    custom_keyword = payload.get("custom_keyword", "").strip()
    angle_count = int(payload.get("angle_count", 7))

    if not url and not raw_text and not custom_keyword:
        raise HTTPException(status_code=400, detail="กรุณาระบุลิงก์ ข้อความรายละเอียด หรือชื่อสินค้า")

    name_label = custom_keyword or (f"ลิงก์: {url[:30]}" if url else "สินค้าใหม่")
    task_title = f"วิเคราะห์สินค้า: {name_label} ({angle_count} สคริปต์)"

    task = TaskManager.create_task(
        task_type="scrape_and_plan",
        title=task_title,
        payload=payload,
        target_tab="flow"
    )

    background_tasks.add_task(_execute_scrape_and_plan_worker, task["id"], payload)

    return {
        "success": True,
        "task_id": task["id"],
        "task": task
    }
