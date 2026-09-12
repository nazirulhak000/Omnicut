"""
API Router for Product Scraping, Content Planning, and Video Attachments.
"""

import re
import time
import shutil
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from scripts.config import BASE_DIR, RAW_DIR
from scripts.product_scraper import (
    ProductScraper, DURATION_SPECS, DEFAULT_DURATION, EXTRA_BEAT_BLOCKS,
    apply_angle_content_metadata,
)
from scripts.product_store import ProductStore
from scripts.task_manager import TaskManager
from scripts.media_service import get_file_info
from scripts.quota import is_quota_error
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


def _normalize_scraped_images(product_info: Dict[str, Any]) -> None:
    """ProductScraper.scrape_url() puts plain image URL strings in "images"
    (scraped straight off <meta og:image>/<img> tags -- there is no local
    file, so there's nothing to compute a rel_path/local_path from). Every
    downstream reader here expects dict entries with those keys, which is
    what _apply_images_to_product_info below produces for user-uploaded
    images -- so a URL-string entry left as-is crashes the first time
    anything calls .get(...) on it, or tries to read it as a local path.
    Normalize to the same dict shape (with local_path omitted, since one
    doesn't exist) before any of that code ever sees it.
    """
    images = product_info.get("images") or []
    if images and isinstance(images[0], str):
        product_info["images"] = [
            {"name": url.rsplit("/", 1)[-1].split("?", 1)[0] or "image", "url": url}
            for url in images
        ]


def _merge_product_source_images(existing_images, scraped_images):
    """Keep existing references and append newly discovered source images."""
    merged = []
    seen = set()

    def canonical_reference(reference: str) -> str:
        parsed = urllib.parse.urlsplit(reference)
        if parsed.scheme and parsed.netloc:
            # CDN query strings commonly contain only size/signature variants
            # of the same image. Keep the first URL, but compare by origin and
            # path so repeated refreshes do not create visual duplicates.
            return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}".rstrip("/").lower()
        return re.sub(r"[\\/]+", "/", reference).rstrip("/").lower()

    for image in [*(existing_images or []), *(scraped_images or [])]:
        if isinstance(image, str):
            image = {
                "name": image.rsplit("/", 1)[-1].split("?", 1)[0] or "image",
                "url": image,
            }
        if not isinstance(image, dict):
            continue
        reference = (
            image.get("rel_path") or image.get("path") or image.get("local_path")
            or image.get("url") or image.get("src") or ""
        )
        canonical = canonical_reference(reference)
        if not reference or not canonical or canonical in seen:
            continue
        seen.add(canonical)
        merged.append(image)
        if len(merged) >= 20:
            break
    return merged


SOURCE_PREVIEW_FIELDS = (
    "name", "url", "description", "raw_text", "price_note",
    "specs", "selling_points", "pain_points", "images",
)


def _source_preview_candidate(scraped: Dict[str, Any]) -> Dict[str, Any]:
    """Map scraper output to the stable field names used by preview UI."""
    return {
        "name": scraped.get("title", ""),
        "url": scraped.get("url", ""),
        "description": scraped.get("description", ""),
        "raw_text": scraped.get("raw_text", ""),
        "price_note": scraped.get("price_note", ""),
        "specs": scraped.get("specs") or [],
        "selling_points": scraped.get("selling_points") or [],
        "pain_points": scraped.get("pain_points") or [],
        "images": scraped.get("images") or [],
    }


def _source_preview_current(product: Dict[str, Any]) -> Dict[str, Any]:
    return {
        field: product.get(field, "" if field not in {"specs", "selling_points", "pain_points", "images"} else [])
        for field in SOURCE_PREVIEW_FIELDS
    }


def _source_values_differ(left: Any, right: Any) -> bool:
    if isinstance(left, list) or isinstance(right, list):
        return (left or []) != (right or [])
    return str(left or "").strip() != str(right or "").strip()


def _with_product_source_fallback(product: Dict[str, Any]) -> Dict[str, Any]:
    """Expose source context for legacy products without inventing a scrape.

    Older products may have been created from a title-only/manual flow. Their
    generated angles still contain useful, already-approved context such as
    key features and pain points, but the product-level description/raw_text
    fields are empty. Return a copy enriched from those angle fields so the
    UI and reroll prompt have the same fallback, while leaving the persisted
    product untouched and clearly labelling the provenance.
    """
    source = product or {}
    enriched = dict(source)
    product_name = str(source.get("name") or "").strip()
    angles = source.get("angles") or []

    # Some legacy records contain angles copied from another product. When an
    # angle carries product_name, only use it if it belongs to this product;
    # nameless legacy angles remain eligible because there is no identity to
    # compare.
    relevant_angles = [
        angle for angle in angles
        if not angle.get("product_name")
        or not product_name
        or str(angle.get("product_name")).strip() == product_name
    ]

    def unique_text(field: str) -> list:
        values = []
        for angle in relevant_angles:
            value = str(angle.get(field) or "").strip()
            if value and value not in values:
                values.append(value)
        return values

    features = unique_text("key_features")
    pains = unique_text("pain_point")
    has_fallback = False

    if not enriched.get("description") and features:
        enriched["description"] = " · ".join(features)
        has_fallback = True
    if not enriched.get("selling_points") and features:
        enriched["selling_points"] = features
        has_fallback = True
    if not enriched.get("pain_points") and pains:
        enriched["pain_points"] = pains
        has_fallback = True
    if not enriched.get("raw_text") and (features or pains):
        source_lines = [enriched.get("name", "สินค้า")]
        if features:
            source_lines.append("จุดเด่นจากสคริปต์เดิม: " + " · ".join(features))
        if pains:
            source_lines.append("ปัญหาที่สคริปต์เดิมอ้างถึง: " + " · ".join(pains))
        enriched["raw_text"] = "\n".join(source_lines)
        has_fallback = True

    if has_fallback:
        enriched["metadata_source"] = "derived_from_angles"
    return enriched


def _apply_images_to_product_info(product_info: Dict[str, Any], image_paths: list, custom_keyword: str, raw_text: str) -> None:
    """Attach up to MAX user-uploaded reference images to product_info in place.

    Shared by the sync and async scrape-and-plan paths so both stay in sync
    on how a rel_path is computed and how the first image seeds a title when
    nothing else was typed -- previously duplicated logic that only handled
    a single image_path.

    User-uploaded images always take priority: if the user attached photos,
    those replace whatever scrape_url() may have already put in "images"
    (product page thumbnails), since the user's own screenshots are the
    reference they explicitly meant to give the AI.
    """
    _normalize_scraped_images(product_info)
    if not image_paths:
        return
    entries = []
    for raw_path in image_paths:
        img_p = Path(raw_path)
        img_name = img_p.name
        img_rel = str(img_p.relative_to(BASE_DIR)).replace("\\", "/") if BASE_DIR in img_p.parents else img_name
        entries.append({"name": img_name, "rel_path": img_rel, "local_path": str(img_p)})
    product_info["images"] = entries
    product_info["image_count"] = len(entries)
    product_info["thumbnail"] = entries[0]["rel_path"]
    if not custom_keyword and not raw_text:
        first_name = entries[0]["name"]
        clean_title = Path(first_name).stem.replace("_", " ").replace("-", " ")
        product_info["title"] = clean_title or "สินค้า"
        product_info["description"] = (
            f"สินค้าจากภาพ {len(entries)} รูป" if len(entries) > 1 else f"สินค้าจากภาพ {first_name}"
        )


@router.post("/api/products/resolve-tiktok-id")
def resolve_tiktok_id_endpoint(payload: Dict[str, Any]):
    """Resolves a raw string, direct ID, full URL, or shortlink to a numeric TikTok Product ID."""
    url_or_id = payload.get("url_or_id", "")
    return resolve_tiktok_product_id(url_or_id)


@router.post("/api/products/{product_id}/preview-source")
def preview_product_source(product_id: str, payload: Optional[Dict[str, Any]] = None):
    """Read a URL and return a diff without changing the saved product."""
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{product_id}'")
    url = str((payload or {}).get("url") or product.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="ต้องระบุ URL สินค้าก่อนดูตัวอย่างข้อมูลใหม่")

    try:
        scraped = ProductScraper.scrape_url(url)
    except (ValueError, OSError) as err:
        raise HTTPException(status_code=400, detail=f"อ่านข้อมูลจาก URL ไม่สำเร็จ: {err}")

    source_method = scraped.get("metadata_source") or "slug_fallback"
    if source_method == "slug_fallback":
        warning = scraped.get("source_warning") or "หน้าเว็บไม่ส่งรายละเอียดสินค้าออกมา"
        raise HTTPException(status_code=422, detail=f"ยังไม่มีรายละเอียดจากหน้าเว็บ: {warning}")

    current = _source_preview_current(product)
    incoming = _source_preview_candidate(scraped)
    changed_fields = [
        field for field in SOURCE_PREVIEW_FIELDS
        if _source_values_differ(current.get(field), incoming.get(field))
    ]
    merged_images = _merge_product_source_images(current.get("images"), incoming.get("images"))
    return {
        "success": True,
        "source_type": "url",
        "url": incoming["url"] or url,
        "metadata_source": source_method,
        "source_warning": scraped.get("source_warning", ""),
        "current": current,
        "incoming": incoming,
        "merged_images": merged_images,
        "changed_fields": changed_fields,
        "image_summary": {
            "existing": len(current.get("images") or []),
            "incoming": len(incoming.get("images") or []),
            "merged": len(merged_images),
        },
    }


def _get_product_image_paths(product_id: str):
    """Return a product and its usable reference image paths for Vision."""
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{product_id}'")

    image_paths = []
    for image in product.get("images") or []:
        if isinstance(image, str):
            reference = image
        elif isinstance(image, dict):
            reference = image.get("local_path") or image.get("rel_path") or image.get("path") or image.get("url") or image.get("src")
        else:
            reference = ""
        if reference:
            image_paths.append(reference)
    if not image_paths:
        raise HTTPException(status_code=400, detail="สินค้านี้ยังไม่มีรูปอ้างอิงให้อ่าน")
    return product, image_paths


def _build_image_metadata_preview(product_id: str):
    """Read product reference images with Vision and return an editable diff."""
    product, image_paths = _get_product_image_paths(product_id)

    try:
        extracted = ProductScraper.extract_metadata_from_images(
            image_paths=image_paths,
            product_name=product.get("name") or product.get("title") or "",
        )
    except Exception as err:
        if is_quota_error(err):
            raise HTTPException(status_code=429, detail=getattr(err, "suggestion_th", str(err)))
        if isinstance(err, (ValueError, RuntimeError, OSError)):
            raise HTTPException(status_code=422, detail=f"อ่าน metadata จากรูปไม่สำเร็จ: {err}")
        raise

    current = _source_preview_current(product)
    incoming = {
        "name": extracted.get("name") or product.get("name") or "",
        "url": product.get("url") or "",
        "description": extracted.get("description") or "",
        "raw_text": extracted.get("raw_text") or "",
        "price_note": product.get("price_note") or "",
        "specs": extracted.get("specs") or [],
        "selling_points": extracted.get("selling_points") or [],
        "pain_points": extracted.get("pain_points") or [],
        "images": [],
    }
    changed_fields = [
        field for field in SOURCE_PREVIEW_FIELDS
        if field not in {"url", "price_note", "images"}
        and _source_values_differ(current.get(field), incoming.get(field))
    ]
    return {
        "success": True,
        "source_type": "vision_image",
        "url": product.get("url") or "",
        "metadata_source": "vision_image",
        "source_warning": extracted.get("source_warning", ""),
        "source_images": image_paths[:8],
        "current": current,
        "incoming": incoming,
        "merged_images": current.get("images") or [],
        "changed_fields": changed_fields,
        "image_summary": {
            "existing": len(current.get("images") or []),
            "incoming": len(image_paths[:8]),
            "merged": len(current.get("images") or []),
        },
    }


@router.post("/api/products/{product_id}/preview-image-metadata")
def preview_product_image_metadata(product_id: str):
    """Synchronous compatibility endpoint for callers that still need the result inline."""
    return _build_image_metadata_preview(product_id)


def _execute_preview_image_metadata_worker(task_id: str, product_id: str):
    """Background worker for Vision image metadata preview."""
    try:
        TaskManager.update_progress(task_id, 0.1, "กำลังเตรียมรูปอ้างอิงสินค้า")
        TaskManager.update_progress(task_id, 0.35, "กำลังอ่านรายละเอียดจากรูปด้วย Vision")
        preview = _build_image_metadata_preview(product_id)
        TaskManager.complete_task(
            task_id,
            result={"product_id": product_id, "preview": preview},
            step_label="อ่านข้อมูลจากรูปเรียบร้อยแล้ว — ตรวจผลก่อนบันทึก",
            target_id=product_id,
        )
    except Exception as err:
        import traceback
        print(f"[TaskManager] Image metadata task failed ({task_id}): {type(err).__name__}: {err}")
        traceback.print_exc()
        if is_quota_error(err):
            TaskManager.fail_task(task_id, err.suggestion_th, step_label="โควต้า AI ไม่พอสำหรับการอ่านรูป")
        else:
            TaskManager.fail_task(
                task_id,
                str(err),
                step_label="อ่าน metadata จากรูปไม่สำเร็จ",
            )


@router.post("/api/products/{product_id}/preview-image-metadata-async")
def preview_product_image_metadata_async(product_id: str, background_tasks: BackgroundTasks):
    """Start Vision image metadata preview as a persistent background task."""
    product, image_paths = _get_product_image_paths(product_id)
    product_name = product.get("name") or product.get("title") or product_id
    task = TaskManager.create_task(
        task_type="image_metadata",
        title=f"อ่านข้อมูลจากรูป: {product_name}",
        payload={"product_id": product_id, "image_count": len(image_paths)},
        target_tab="flow",
        target_id=product_id,
    )
    background_tasks.add_task(_execute_preview_image_metadata_worker, task["id"], product_id)
    return {"success": True, "task_id": task["id"], "task": task}


@router.post("/api/products/{product_id}/refresh-source")
def refresh_product_source(product_id: str, payload: Optional[Dict[str, Any]] = None):
    """Apply explicitly selected fields from a previously previewed source."""
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{product_id}'")
    payload = payload or {}
    url = str(payload.get("url") or product.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="สินค้านี้ยังไม่มี URL ต้นทางให้ดึงข้อมูลใหม่")

    try:
        scraped = ProductScraper.scrape_url(url)
    except (ValueError, OSError) as err:
        raise HTTPException(status_code=400, detail=f"ดึงข้อมูลจาก URL ไม่สำเร็จ: {err}")

    source_method = scraped.get("metadata_source") or "slug_fallback"
    if source_method == "slug_fallback":
        warning = scraped.get("source_warning") or "หน้าเว็บไม่ส่งรายละเอียดสินค้าออกมา"
        raise HTTPException(status_code=422, detail=f"ยังไม่ได้รายละเอียดจากหน้าเว็บ: {warning}")

    selected_fields = set(payload.get("fields") or SOURCE_PREVIEW_FIELDS)
    selected_fields &= set(SOURCE_PREVIEW_FIELDS)
    overrides = payload.get("overrides") or {}
    if not isinstance(overrides, dict):
        raise HTTPException(status_code=400, detail="ข้อมูลที่แก้จาก preview ต้องเป็น object")
    scraped_images = scraped.get("images") or []
    fields = {
        "platform": scraped.get("platform") or product.get("platform", ""),
        "metadata_source": source_method,
    }
    incoming = _source_preview_candidate(scraped)
    for field in selected_fields - {"images"}:
        if field in overrides:
            value = overrides[field]
            if field in {"specs", "selling_points", "pain_points"}:
                if not isinstance(value, list):
                    raise HTTPException(status_code=400, detail=f"ฟิลด์ {field} ต้องเป็นรายการ")
                fields[field] = value
            elif not isinstance(value, str):
                raise HTTPException(status_code=400, detail=f"ฟิลด์ {field} ต้องเป็นข้อความ")
            else:
                fields[field] = value.strip()
        elif incoming.get(field):
            fields[field] = incoming[field]
    if "images" in selected_fields:
        fields["images"] = _merge_product_source_images(product.get("images"), scraped_images)
    if "price_note" in selected_fields and scraped.get("price_note") and scraped["price_note"] != "ราคาพิเศษในตะกร้า":
        fields["price_note"] = scraped["price_note"]
    if not product.get("thumbnail") and scraped_images:
        first_image = scraped_images[0]
        fields["thumbnail"] = first_image if isinstance(first_image, str) else (
            first_image.get("rel_path") or first_image.get("url") or ""
        )

    updated = ProductStore.update(product_id, **fields)
    return {
        "success": True,
        "product": updated,
        "metadata_source": source_method,
        "source_warning": scraped.get("source_warning", ""),
    }


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
      qc_note         – free-text QC failure reason (stored on the angle for Studio reference)
      clear_qc_note   – boolean; set True to wipe a previous qc_note when the clip passes QC
      mark_qc_passed  – boolean; set True only when a human actually clicked "QC ผ่าน".
                        A rendered clip with no qc_note is NOT the same thing as a
                        reviewed-and-approved clip -- see ProductStore.update_angle_status.
    """
    status = payload.get("status")
    video_url = payload.get("video_url")
    export_id = payload.get("export_id")
    project_name = payload.get("project_name")
    qc_note = payload.get("qc_note")          # str | None
    clear_qc_note = bool(payload.get("clear_qc_note", False))
    clear_conflict_note = bool(payload.get("clear_conflict_note", False))
    mark_qc_passed = bool(payload.get("mark_qc_passed", False))
    if not status:
        raise HTTPException(status_code=400, detail="Missing status")
    if status == "posted" and not export_id:
        raise HTTPException(
            status_code=409,
            detail="การมาร์กโพสต์ต้องระบุ export_id และต้องผ่าน /api/exports/mark-posted เท่านั้น",
        )
    try:
        updated = ProductStore.update_angle_status(
            product_id,
            angle_id,
            status,
            video_url=video_url,
            project_name=project_name,
            export_id=export_id,
            qc_note=qc_note,
            clear_qc_note=clear_qc_note,
            clear_conflict_note=clear_conflict_note,
            mark_qc_passed=mark_qc_passed,
        )
        return {"success": True, "product": updated}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.patch("/api/products/{product_id}/angles/{angle_id}/cover")
def update_product_angle_cover(product_id: str, angle_id: str, payload: Dict[str, Any]):
    """Persists generated 9:16/3:4 cover paths for one product angle."""
    if not any(payload.get(key) for key in ("cover_path", "cover_3x4_path", "cover_9x16_path")):
        raise HTTPException(status_code=400, detail="ต้องระบุไฟล์ปกอย่างน้อยหนึ่งไฟล์")
    try:
        updated = ProductStore.update_angle_cover(
            product_id,
            angle_id,
            cover_path=payload.get("cover_path"),
            cover_3x4_path=payload.get("cover_3x4_path"),
            cover_9x16_path=payload.get("cover_9x16_path"),
        )
        return {"success": True, "product": updated}
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


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
    image_paths = payload.get("image_paths") or []

    if not url and not raw_text and not custom_keyword and not image_paths:
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

        _apply_images_to_product_info(product_info, image_paths, custom_keyword, raw_text)

        if custom_keyword:
            product_info["title"] = custom_keyword
        if raw_text and len(raw_text) > 10:
            product_info["description"] = raw_text
            product_info["raw_text"] = f"{product_info.get('title', '')}\n{raw_text}"

        angle_count = int(payload.get("angle_count", 10))
        duration = str(payload.get("duration") or DEFAULT_DURATION)
        if duration not in DURATION_SPECS:
            raise HTTPException(status_code=400, detail=f"duration ต้องเป็นหนึ่งใน {', '.join(DURATION_SPECS)}")
        extra_beats = payload.get("extra_beats")
        if extra_beats is not None:
            invalid = [b for b in extra_beats if b not in EXTRA_BEAT_BLOCKS]
            if invalid:
                raise HTTPException(status_code=400, detail=f"extra_beats ไม่รู้จัก: {', '.join(invalid)}")

        tiktok_product_id = str(payload.get("tiktok_product_id") or "").strip()
        if tiktok_product_id:
            resolved = resolve_tiktok_product_id(tiktok_product_id)
            if resolved.get("success") and resolved.get("product_id"):
                tiktok_product_id = resolved["product_id"]
        elif url:
            resolved = resolve_tiktok_product_id(url)
            if resolved.get("success") and resolved.get("product_id"):
                tiktok_product_id = resolved["product_id"]

        angles = ProductScraper.generate_content_matrix(
            product_info, count=angle_count,
            # Vision reads local files directly and downloads http(s) URLs
            # on the fly (see generate_content_matrix's image-reading loop),
            # so both user-uploaded (local_path) and scraped (url) images
            # reach the model here.
            image_paths=[img.get("local_path") or img.get("url") for img in product_info.get("images", []) if img.get("local_path") or img.get("url")],
            duration=duration,
            extra_beats=extra_beats,
        )

        thumbnail_img = ""
        if product_info.get("images") and len(product_info["images"]) > 0:
            thumbnail_img = product_info["images"][0].get("rel_path") or product_info["images"][0].get("url", "")

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
            description=product_info.get("description", ""),
            raw_text=product_info.get("raw_text", ""),
            metadata_source=product_info.get("metadata_source", ""),
            source_warning=product_info.get("source_warning", ""),
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
        # A quota hit is the user's own daily cap, not a scrape failure; 500
        # would send them looking for a broken URL instead.
        if is_quota_error(e):
            raise HTTPException(status_code=429, detail=e.suggestion_th)
        import traceback
        print(f"[API] Scrape and plan error: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _execute_scrape_and_plan_worker(task_id: str, payload: Dict[str, Any]):
    """Background worker that executes product scrape & script generation."""
    try:
        TaskManager.update_progress(task_id, 0.15, "กำลังดึงข้อมูลและสเปกสินค้า")
        url = payload.get("url", "").strip()
        raw_text = payload.get("raw_text", "").strip()
        custom_keyword = payload.get("custom_keyword", "").strip()
        image_paths = payload.get("image_paths") or []
        angle_count = int(payload.get("angle_count", 7))
        duration = str(payload.get("duration") or DEFAULT_DURATION)
        extra_beats = payload.get("extra_beats")

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

        _apply_images_to_product_info(product_info, image_paths, custom_keyword, raw_text)

        if custom_keyword:
            product_info["title"] = custom_keyword
        if raw_text and len(raw_text) > 10:
            product_info["description"] = raw_text
            product_info["raw_text"] = f"{product_info.get('title', '')}\n{raw_text}"

        title_display = product_info.get("title", custom_keyword or "สินค้า")
        if len(title_display) > 35:
            title_display = title_display[:35]

        img_count = len(product_info.get("images", []))
        vision_note = f" (อ่านสรรพคุณจากภาพ {img_count} รูปด้วย)" if img_count else ""
        TaskManager.update_progress(task_id, 0.55, f"AI กำลังแต่ง {angle_count} สคริปต์ ({title_display}){vision_note}")
        angles = ProductScraper.generate_content_matrix(
            product_info, count=angle_count,
            # Vision reads local files directly and downloads http(s) URLs
            # on the fly (see generate_content_matrix's image-reading loop),
            # so both user-uploaded (local_path) and scraped (url) images
            # reach the model here.
            image_paths=[img.get("local_path") or img.get("url") for img in product_info.get("images", []) if img.get("local_path") or img.get("url")],
            duration=duration,
            extra_beats=extra_beats,
        )

        TaskManager.update_progress(task_id, 0.85, "กำลังปรับแต่งบทพูดสำหรับเสียงพากย์ AI (TTS Sanitizer)")
        angles = TTSSanitizer.process_angles(angles)

        TaskManager.update_progress(task_id, 0.95, "กำลังบันทึกลงแคตตาล็อกสินค้า")
        thumbnail_img = ""
        if product_info.get("images") and len(product_info["images"]) > 0:
            thumbnail_img = product_info["images"][0].get("rel_path") or product_info["images"][0].get("url", "")

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
            description=product_info.get("description", ""),
            raw_text=product_info.get("raw_text", ""),
            metadata_source=product_info.get("metadata_source", ""),
            source_warning=product_info.get("source_warning", ""),
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
        # str(e) alone drops the exception type and traceback, which is what
        # made a prior "'str' object has no attribute 'get'" failure here
        # nearly impossible to trace back to its actual origin (turned out to
        # be a google-genai SDK error path, several layers below this code).
        # Logging the type + full traceback costs nothing and is the only way
        # the next occurrence gets diagnosed directly instead of by inference.
        import traceback
        print(f"❌ [TaskManager] Scrape task failed ({task_id}): {type(e).__name__}: {e}")
        traceback.print_exc()
        if is_quota_error(e):
            # Say which cap stopped it. "วิเคราะห์สินค้าไม่สำเร็จ" would send the
            # user looking for a bad URL instead of their own daily budget.
            TaskManager.fail_task(
                task_id,
                e.suggestion_th,
                step_label="เกินโควต้า AI ต่อวันแล้ว",
            )
        else:
            TaskManager.fail_task(task_id, str(e), step_label="วิเคราะห์สินค้าไม่สำเร็จ")


@router.post("/api/products/scrape-and-plan-async")
def scrape_and_plan_async(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Launches Scrape & Plan as a persistent background task, returning job ID immediately."""
    url = payload.get("url", "").strip()
    raw_text = payload.get("raw_text", "").strip()
    custom_keyword = payload.get("custom_keyword", "").strip()
    image_paths = payload.get("image_paths") or []
    angle_count = int(payload.get("angle_count", 7))

    if not url and not raw_text and not custom_keyword and not image_paths:
        raise HTTPException(status_code=400, detail="กรุณาระบุลิงก์ ข้อความรายละเอียด รูปภาพ หรือชื่อสินค้า")

    duration = str(payload.get("duration") or DEFAULT_DURATION)
    if duration not in DURATION_SPECS:
        raise HTTPException(status_code=400, detail=f"duration ต้องเป็นหนึ่งใน {', '.join(DURATION_SPECS)}")
    extra_beats = payload.get("extra_beats")
    if extra_beats is not None:
        invalid = [b for b in extra_beats if b not in EXTRA_BEAT_BLOCKS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"extra_beats ไม่รู้จัก: {', '.join(invalid)}")

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


def _execute_reroll_script_worker(
    task_id: str, product_id: str, angle_id: str, angle_count: int,
    duration: str, extra_beats, angle_snapshot: Dict[str, Any],
) -> None:
    """Background worker: regenerate ONE angle's script content in place.

    Reuses the product's own persisted description/raw_text/images as the
    source material (the same ones the original scrape-and-plan used) rather
    than re-scraping -- a reroll changes length/content emphasis, not what
    the product actually is. angle_count is always 1: this call only ever
    asks the AI for a single angle back, distinguished from the normal
    content-matrix call by passing count=1 and the SAME angle_id already on
    this angle, so the model reworks that one angle instead of inventing a
    fresh matrix.
    """
    try:
        TaskManager.update_progress(task_id, 0.10, "กำลังเตรียมข้อมูลสินค้า")
        product = _with_product_source_fallback(ProductStore.get(product_id) or {})
        if not product:
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

        product_info = {
            "title": product.get("name", ""),
            "description": product.get("description", ""),
            "price_note": product.get("price_note", ""),
            "raw_text": product.get("raw_text", ""),
            "images": product.get("images", []),
        }

        img_count = len(product_info.get("images", []))
        vision_note = f" (อ่านสรรพคุณจากภาพ {img_count} รูปด้วย)" if img_count else ""
        TaskManager.update_progress(
            task_id, 0.40,
            f"AI กำลังเขียนสคริปต์ใหม่ ({DURATION_SPECS.get(duration, {}).get('label', duration)}){vision_note}",
        )
        angles = ProductScraper.generate_content_matrix(
            product_info, count=1,
            # Vision reads local files directly and downloads http(s) URLs
            # on the fly, so both user-uploaded (local_path) and scraped
            # (url) images reach the model on a reroll too.
            image_paths=[img.get("local_path") or img.get("url") for img in product_info.get("images", []) if img.get("local_path") or img.get("url")],
            duration=duration,
            extra_beats=extra_beats,
            # A reroll targets the specific angle already on this product
            # (e.g. "pain_point") rather than letting the matrix generator
            # pick from its full 10-angle list -- see generate_content_matrix's
            # angle_id_override.
            angle_id_override=angle_snapshot.get("angle_id"),
        )
        if not angles:
            raise ValueError("AI ไม่ได้สร้างสคริปต์ใหม่กลับมา")

        TaskManager.update_progress(task_id, 0.80, "กำลังปรับแต่งบทพูดสำหรับเสียงพากย์ AI (TTS Sanitizer)")
        new_angle = TTSSanitizer.process_angles(angles)[0]
        # generate_content_matrix always answers with its own angle_id
        # (from its fixed 10-angle catalog); force it back to the angle_id
        # this angle already has so replace_angle_content's identity match
        # still finds it, and the timeline/render side (which keys off
        # angle_id) doesn't see a different angle appear.
        apply_angle_content_metadata(
            new_angle,
            angle_id=angle_snapshot.get("angle_id"),
            extra_beats=extra_beats,
            preserve_name=angle_snapshot.get("angle_name"),
        )
        new_angle["duration"] = duration
        new_angle["extra_beats"] = extra_beats or []

        TaskManager.update_progress(task_id, 0.95, "กำลังบันทึกสคริปต์ใหม่")
        updated_product = ProductStore.replace_angle_content(product_id, angle_id, new_angle)
        # new_angle is the AI's raw output -- it has no idea about this
        # angle's status/project_name/video_url (replace_angle_content
        # deliberately never sends those to the AI, and preserves whatever
        # was already on the angle). Read the angle back OUT of the just-
        # persisted product instead of returning new_angle directly, so the
        # frontend's completion handler sees the real, full, saved state
        # (lifecycle fields included) rather than a partial AI-only object
        # that looks like the reroll wiped them.
        saved_angle = next(
            (a for a in updated_product.get("angles", []) if (a.get("angle_id") or a.get("id")) == angle_id),
            new_angle,
        )

        TaskManager.complete_task(
            task_id,
            result={"product": updated_product, "angle": saved_angle},
            step_label="🎉 รีสคริปต์สำเร็จ!",
            target_id=product_id,
        )
    except Exception as e:
        import traceback
        print(f"[API] Reroll script error: {type(e).__name__}: {e}")
        traceback.print_exc()
        if is_quota_error(e):
            TaskManager.fail_task(task_id, e.suggestion_th, step_label="เกินโควต้า AI ต่อวันแล้ว")
        else:
            TaskManager.fail_task(task_id, str(e), step_label="รีสคริปต์ไม่สำเร็จ")


@router.post("/api/products/{product_id}/angles/{angle_id}/reroll-script")
def reroll_angle_script(product_id: str, angle_id: str, payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Regenerates ONE angle's script with a new duration/content mix via AI,
    as a background task (same pattern as scrape-and-plan-async). Overwrites
    the angle's script content immediately on completion -- no version
    history is kept, matching how a hand-edit to the script already works.
    """
    duration = str(payload.get("duration") or DEFAULT_DURATION)
    if duration not in DURATION_SPECS:
        raise HTTPException(status_code=400, detail=f"duration ต้องเป็นหนึ่งใน {', '.join(DURATION_SPECS)}")
    extra_beats = payload.get("extra_beats")
    if extra_beats is not None:
        invalid = [b for b in extra_beats if b not in EXTRA_BEAT_BLOCKS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"extra_beats ไม่รู้จัก: {', '.join(invalid)}")
    else:
        # Keep the API default identical to the generator/UI default, and pass
        # the resolved list to the worker so persisted content_types matches
        # the actual extra beats in the generated script.
        extra_beats = list(EXTRA_BEAT_BLOCKS.keys())[:DURATION_SPECS[duration]["default_extra_beats"]]

    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{product_id}'")
    angle_snapshot = next(
        (a for a in product.get("angles", []) if (a.get("angle_id") or a.get("id")) == angle_id),
        None,
    )
    if not angle_snapshot:
        raise HTTPException(status_code=404, detail=f"ไม่พบมุม '{angle_id}' ในสินค้านี้")
    if angle_snapshot.get("status") == "posted" or angle_snapshot.get("posted_at"):
        raise HTTPException(
            status_code=400,
            detail="ไม่อนุญาตให้รีสคริปต์มุมที่โพสต์แล้ว เนื่องจากต้องเก็บไว้เป็นหลักฐาน",
        )

    task_title = f"รีสคริปต์: {angle_snapshot.get('angle_name', angle_id)} ({DURATION_SPECS[duration]['label']})"
    task = TaskManager.create_task(
        task_type="reroll_script",
        title=task_title,
        payload={"product_id": product_id, "angle_id": angle_id, "duration": duration, "extra_beats": extra_beats},
        target_tab="flow",
        target_id=product_id,
    )

    background_tasks.add_task(
        _execute_reroll_script_worker,
        task["id"], product_id, angle_id, 1, duration, extra_beats, angle_snapshot,
    )

    return {
        "success": True,
        "task_id": task["id"],
        "task": task,
    }


def _execute_generate_batch_worker(
    task_id: str, product_id: str, angle_count: int,
    duration: str, extra_beats,
) -> None:
    try:
        TaskManager.update_progress(task_id, 0.10, "กำลังเตรียมข้อมูลสินค้า")
        product = _with_product_source_fallback(ProductStore.get(product_id) or {})
        if not product:
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

        existing_angles = product.get("angles", [])
        avoid_angles = [a.get("angle_name") for a in existing_angles if a.get("angle_name")]

        max_batch = 1
        for a in existing_angles:
            b = a.get("batch")
            if isinstance(b, int) and b > max_batch:
                max_batch = b
        next_batch = max_batch + 1 if existing_angles else 1
        batch_label = f"ล็อตที่ {next_batch}"

        product_info = {
            "title": product.get("name", ""),
            "description": product.get("description", ""),
            "price_note": product.get("price_note", ""),
            "raw_text": product.get("raw_text", ""),
            "images": product.get("images", []),
            "specs": product.get("specs", []),
            "selling_points": product.get("selling_points", []),
            "pain_points": product.get("pain_points", []),
        }

        TaskManager.update_progress(task_id, 0.40, f"AI กำลังแต่ง {angle_count} สคริปต์ใหม่ ({batch_label})")
        image_paths = [
            img.get("local_path") or img.get("url")
            for img in product_info.get("images", [])
            if img.get("local_path") or img.get("url")
        ]

        new_angles = ProductScraper.generate_content_matrix(
            product_info,
            count=angle_count,
            image_paths=image_paths,
            duration=duration,
            extra_beats=extra_beats,
            avoid_angles=avoid_angles,
            batch_label=batch_label,
        )

        TaskManager.update_progress(task_id, 0.80, "กำลังปรับแต่งบทพูดสำหรับเสียงพากย์ AI (TTS Sanitizer)")
        new_angles = TTSSanitizer.process_angles(new_angles)

        TaskManager.update_progress(task_id, 0.95, f"กำลังบันทึกสคริปต์ {batch_label} ลงสินค้า")
        updated_product = ProductStore.append_angles(product_id, new_angles, batch_index=next_batch)

        result_data = {
            "product": updated_product,
            "new_angles": new_angles,
            "batch_index": next_batch,
        }

        TaskManager.complete_task(
            task_id,
            result=result_data,
            step_label=f"🎉 สำเร็จ! สร้างสคริปต์ {batch_label} ({len(new_angles)} มุม) เรียบร้อย",
            target_id=product_id,
        )
    except Exception as e:
        import traceback
        print(f"[API] Generate batch error: {type(e).__name__}: {e}")
        traceback.print_exc()
        if is_quota_error(e):
            TaskManager.fail_task(task_id, e.suggestion_th, step_label="เกินโควต้า AI ต่อวันแล้ว")
        else:
            TaskManager.fail_task(task_id, str(e), step_label="เจนสคริปต์ล็อตใหม่ไม่สำเร็จ")


@router.post("/api/products/{product_id}/generate-batch")
def generate_product_batch(product_id: str, payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Generates a new batch (e.g. 10 angles) for an existing product without duplicating previous angles."""
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{product_id}'")

    angle_count = int(payload.get("angle_count", 10))
    duration = str(payload.get("duration") or DEFAULT_DURATION)
    if duration not in DURATION_SPECS:
        raise HTTPException(status_code=400, detail=f"duration ต้องเป็นหนึ่งใน {', '.join(DURATION_SPECS)}")
    extra_beats = payload.get("extra_beats")
    if extra_beats is not None:
        invalid = [b for b in extra_beats if b not in EXTRA_BEAT_BLOCKS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"extra_beats ไม่รู้จัก: {', '.join(invalid)}")
    else:
        extra_beats = list(EXTRA_BEAT_BLOCKS.keys())[:DURATION_SPECS[duration]["default_extra_beats"]]

    task_title = f"เจนสคริปต์ล็อตใหม่: {product.get('name', product_id)} ({angle_count} สคริปต์)"
    task = TaskManager.create_task(
        task_type="generate_batch",
        title=task_title,
        payload={"product_id": product_id, "angle_count": angle_count, "duration": duration, "extra_beats": extra_beats},
        target_tab="flow",
        target_id=product_id,
    )

    background_tasks.add_task(
        _execute_generate_batch_worker,
        task["id"], product_id, angle_count, duration, extra_beats,
    )

    return {
        "success": True,
        "task_id": task["id"],
        "task": task,
    }


@router.post("/api/products/{product_id}/angles")
def add_product_angle(product_id: str, payload: Dict[str, Any]):
    """Adds a single angle (custom or cloned) to an existing product."""
    product = ProductStore.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"ไม่พบสินค้า id '{product_id}'")

    angle_data = payload.get("angle") if "angle" in payload else payload
    if not angle_data or not isinstance(angle_data, dict):
        raise HTTPException(status_code=400, detail="ต้องระบุข้อมูล angle ใน payload")

    batch_index = payload.get("batch_index") if "batch_index" in payload else None
    try:
        updated = ProductStore.add_single_angle(product_id, angle_data, batch_index=batch_index)
        return {"success": True, "product": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

