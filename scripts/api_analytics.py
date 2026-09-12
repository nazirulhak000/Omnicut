"""
Analytics & Operations Hub API Router
Provides comprehensive statistics across 4 key dimensions:
1. Production & Pipeline Funnel
2. Tokens & AI Performance
3. Storage & Safe Disk Quota Management
4. Content & Inventory Health
"""

import os
import shutil
import time
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, ASSETS_DIR,
    PROJECTS_DIR, EXPORTS_DIR, COVERS_DIR, ARCHIVE_DIR,
    CAPCUT_DRAFT_DIR
)
from scripts.product_store import ProductStore
from scripts.token_tracker import TokenTracker
from scripts.export_registry import ExportRegistry

router = APIRouter(prefix="/api/analytics", tags=["Analytics Hub"])

# In-memory cache for storage scan to avoid frequent heavy disk I/O
_STORAGE_CACHE: Dict[str, Any] = {
    "data": None,
    "timestamp": 0.0
}
STORAGE_CACHE_TTL_SECONDS = 300.0  # 5 minutes

EXPORT_ARCHIVE_AGE_DAYS = 30  # Flag posted exports/projects older than this
DISK_ALERT_PERCENTAGE = 80.0  # Flag when drive usage crosses this


def _dir_size(path: Path) -> int:
    """Calculate total byte size of a directory safely."""
    total = 0
    if not path or not path.exists():
        return 0
    try:
        for entry in os.scandir(str(path)):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    return total


def _age_days_from_iso(iso_str: Optional[str]) -> Optional[int]:
    """Days elapsed since an ISO timestamp; None if missing/unparseable."""
    if not iso_str:
        return None
    try:
        then = datetime.datetime.fromisoformat(iso_str)
        now = datetime.datetime.now(then.tzinfo) if then.tzinfo else datetime.datetime.now()
        return max(0, (now - then).days)
    except (ValueError, TypeError):
        return None


@router.get("/production")
def get_production_analytics() -> Dict[str, Any]:
    """
    Analyzes video production pipeline:
    - 4-phase funnel (scripted -> in_production -> rendered -> posted)
    - Bottlenecks
    - Angle types distribution
    - Average cycle time estimation
    """
    try:
        products = ProductStore.get_all()
        
        status_counts = {
            "scripted": 0,
            "in_production": 0,
            "rendered": 0,
            "posted": 0
        }
        angle_type_counts: Dict[str, int] = {}
        total_angles = 0
        cycle_times_sec = []
        recent_productions = []

        now = datetime.datetime.now()

        for p in products:
            angles = p.get("angles") or []
            for a in angles:
                total_angles += 1
                status = a.get("status") or "scripted"
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts["scripted"] += 1

                # Angle / content type
                types = a.get("content_types") or []
                if not types and a.get("badge"):
                    types = [a.get("badge")]
                if not types:
                    types = ["ทั่วไป"]
                for t in types:
                    angle_type_counts[t] = angle_type_counts.get(t, 0) + 1

                # Cycle time estimation (from created_at / updated_at to posted_at)
                created_at_str = a.get("created_at") or p.get("created_at")
                posted_at_str = a.get("posted_at")
                if created_at_str and posted_at_str:
                    try:
                        c_dt = datetime.datetime.fromisoformat(created_at_str)
                        p_dt = datetime.datetime.fromisoformat(posted_at_str)
                        diff = (p_dt - c_dt).total_seconds()
                        if 0 < diff < 86400 * 30:  # reasonable window (< 30 days)
                            cycle_times_sec.append(diff)
                    except Exception:
                        pass

                # Collect recent items
                recent_productions.append({
                    "product_id": p.get("id"),
                    "product_name": p.get("name") or p.get("title") or "สินค้า",
                    "product_code": p.get("product_code") or "",
                    "angle_id": a.get("angle_id") or a.get("id"),
                    "hook_title": a.get("hook_title") or a.get("angle_name") or "ไม่มีพาดหัว",
                    "status": status,
                    "project_name": a.get("project_name"),
                    "video_url": a.get("video_url"),
                    "updated_at": a.get("updated_at") or p.get("updated_at") or ""
                })

        # Sort recent items by updated_at descending
        recent_productions.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        recent_productions = recent_productions[:15]

        avg_cycle_time_minutes = (
            round(sum(cycle_times_sec) / (len(cycle_times_sec) * 60), 1)
            if cycle_times_sec else 0.0
        )

        # Identify bottleneck
        bottleneck = None
        if status_counts["scripted"] > 15 and status_counts["in_production"] < 3:
            bottleneck = "คอขวดอยู่ที่ขั้นตอนถ่ายทำ (มีสคริปต์รอถ่ายจำนวนมาก)"
        elif status_counts["in_production"] > 10:
            bottleneck = "คอขวดอยู่ที่ขั้นตอนตัดต่อ (มีโปรเจกต์ค้างในไทม์ไลน์)"
        elif status_counts["rendered"] > 10 and status_counts["posted"] < status_counts["rendered"] / 2:
            bottleneck = "มีคลิปตัดเสร็จรอลงโพสต์จำนวนมาก"

        return {
            "summary": {
                "total_products": len(products),
                "total_angles": total_angles,
                "scripted": status_counts["scripted"],
                "in_production": status_counts["in_production"],
                "rendered": status_counts["rendered"],
                "posted": status_counts["posted"],
                "published_percentage": round((status_counts["posted"] / total_angles * 100), 1) if total_angles else 0.0,
                "avg_cycle_time_minutes": avg_cycle_time_minutes,
                "bottleneck_note": bottleneck
            },
            "angle_types": [
                {"name": k, "count": v}
                for k, v in sorted(angle_type_counts.items(), key=lambda x: x[1], reverse=True)
            ],
            "recent_productions": recent_productions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate production analytics: {e}")


@router.get("/storage")
def get_storage_analytics(force_scan: bool = False) -> Dict[str, Any]:
    """
    Scans disk usage for project folders:
    - 01_Raw
    - 02_Assets
    - 03_Projects
    - 04_Exports
    - 05_Covers
    - 06_Archive
    - CapCut Draft cache
    Includes safe purgable size calculation.
    """
    global _STORAGE_CACHE
    now = time.time()

    if not force_scan and _STORAGE_CACHE["data"] and (now - _STORAGE_CACHE["timestamp"] < STORAGE_CACHE_TTL_SECONDS):
        return _STORAGE_CACHE["data"]

    try:
        # Check overall drive space
        disk_usage = shutil.disk_usage(str(BASE_DIR))
        total_disk_bytes = disk_usage.total
        used_disk_bytes = disk_usage.used
        free_disk_bytes = disk_usage.free

        # Scan each directory
        raw_size = _dir_size(RAW_DIR)
        assets_size = _dir_size(ASSETS_DIR)
        projects_size = _dir_size(PROJECTS_DIR)
        exports_size = _dir_size(EXPORTS_DIR.parent if EXPORTS_DIR.name == "Ready_to_post" else EXPORTS_DIR)
        covers_size = _dir_size(COVERS_DIR)
        archive_size = _dir_size(ARCHIVE_DIR)

        # Scan CapCut drafts cache if exists
        capcut_draft_size = 0
        capcut_cache_size = 0
        if CAPCUT_DRAFT_DIR.exists():
            capcut_draft_size = _dir_size(CAPCUT_DRAFT_DIR)
            # Find cloud_cache dirs
            try:
                for entry in CAPCUT_DRAFT_DIR.iterdir():
                    if entry.is_dir() and (entry.name.startswith(".cloud_cache") or entry.name.startswith("cache_")):
                        capcut_cache_size += _dir_size(entry)
            except Exception:
                pass

        # Scan temporary audio preview caches in PROJECTS_DIR
        temp_cache_size = 0
        try:
            for item in PROJECTS_DIR.rglob("*.wav"):
                if "preview" in item.name.lower() or "temp" in item.name.lower():
                    temp_cache_size += item.stat().st_size
        except Exception:
            pass

        safe_purge_bytes = capcut_cache_size + temp_cache_size

        # Top heaviest product folders in 01_Raw
        heavy_products = []
        try:
            if RAW_DIR.exists():
                for item in RAW_DIR.iterdir():
                    if item.is_dir():
                        size = _dir_size(item)
                        heavy_products.append({
                            "name": item.name,
                            "path": str(item),
                            "size_bytes": size,
                            "size_mb": round(size / (1024 * 1024), 1)
                        })
                heavy_products.sort(key=lambda x: x["size_bytes"], reverse=True)
                heavy_products = heavy_products[:10]
        except Exception:
            pass

        # Scan posted exports & potential archive reclaimable space
        posted_dir = EXPORTS_DIR.parent / "Posted"
        posted_mp4s = list(posted_dir.glob("*.mp4")) if posted_dir.exists() else []
        posted_exports_bytes = sum(f.stat().st_size for f in posted_mp4s if f.is_file())

        products = ProductStore.get_all()
        posted_angles_count = 0
        posted_projects_bytes = 0
        posted_projects_set = set()
        completed_products_raw_bytes = 0
        posted_items_list = []

        for p in products:
            angles = p.get("angles", [])
            p_posted = [a for a in angles if a.get("status") == "posted"]
            posted_angles_count += len(p_posted)

            # If all angles are posted, raw footage could be safely archived
            if angles and len(p_posted) == len(angles):
                code = p.get("product_code") or p.get("id")
                if code and RAW_DIR.exists():
                    for rdir in RAW_DIR.glob(f"*{code}*"):
                        if rdir.is_dir():
                            completed_products_raw_bytes += _dir_size(rdir)

            for a in p_posted:
                proj_name = a.get("project_name")
                if proj_name and proj_name not in posted_projects_set:
                    posted_projects_set.add(proj_name)
                    pdir = PROJECTS_DIR / proj_name
                    if pdir.exists():
                        psize = _dir_size(pdir)
                        posted_projects_bytes += psize
                        posted_at_str = a.get("posted_at")
                        posted_items_list.append({
                            "type": "project",
                            "name": proj_name,
                            "product_name": p.get("name") or "สินค้า",
                            "size_bytes": psize,
                            "size_mb": round(psize / (1024 * 1024), 1),
                            "posted_at": posted_at_str,
                            "age_days": _age_days_from_iso(posted_at_str)
                        })

        for f in posted_mp4s:
            fsize = f.stat().st_size
            # Files carry no posted_at of their own -- mtime is set when the
            # export lands in Posted/, so it's a reasonable proxy for "how
            # long has this been sitting here since it was posted".
            mtime_iso = datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            posted_items_list.append({
                "type": "export_mp4",
                "name": f.name,
                "size_bytes": fsize,
                "size_mb": round(fsize / (1024 * 1024), 1),
                "posted_at": mtime_iso,
                "age_days": _age_days_from_iso(mtime_iso)
            })

        total_reclaimable_bytes = posted_exports_bytes + posted_projects_bytes + completed_products_raw_bytes

        posted_archive_potential = {
            "posted_clips_count": len(posted_mp4s),
            "posted_angles_count": posted_angles_count,
            "posted_exports_bytes": posted_exports_bytes,
            "posted_exports_mb": round(posted_exports_bytes / (1024 * 1024), 1),
            "posted_projects_bytes": posted_projects_bytes,
            "posted_projects_mb": round(posted_projects_bytes / (1024 * 1024), 1),
            "completed_products_raw_bytes": completed_products_raw_bytes,
            "completed_products_raw_mb": round(completed_products_raw_bytes / (1024 * 1024), 1),
            "total_reclaimable_bytes": total_reclaimable_bytes,
            "total_reclaimable_mb": round(total_reclaimable_bytes / (1024 * 1024), 1),
            "total_reclaimable_gb": round(total_reclaimable_bytes / (1024 ** 3), 2),
            "items_count": len(posted_items_list),
            "items": sorted(posted_items_list, key=lambda x: x["size_bytes"], reverse=True)
        }

        used_percentage = round(used_disk_bytes / total_disk_bytes * 100, 1) if total_disk_bytes else 0.0

        ready_items = [
            item for item in posted_items_list
            if (item.get("age_days") or 0) >= EXPORT_ARCHIVE_AGE_DAYS
        ]
        ready_bytes = sum(item["size_bytes"] for item in ready_items)
        disk_alert = used_percentage >= DISK_ALERT_PERCENTAGE
        should_notify = bool(ready_items) or disk_alert

        message_parts = []
        if ready_items:
            message_parts.append(
                f"มีไฟล์ที่โพสต์แล้วค้างเกิน {EXPORT_ARCHIVE_AGE_DAYS} วัน {len(ready_items)} รายการ "
                f"({round(ready_bytes / (1024 * 1024), 1)} MB) แนะนำย้ายไป External Drive/Cloud"
            )
        if disk_alert:
            message_parts.append(f"ดิสก์ใช้งานไปแล้ว {used_percentage}% (เกิน {DISK_ALERT_PERCENTAGE}%)")

        archive_recommendation = {
            "ready_count": len(ready_items),
            "ready_mb": round(ready_bytes / (1024 * 1024), 1),
            "ready_items": sorted(ready_items, key=lambda x: x.get("age_days") or 0, reverse=True)[:20],
            "disk_alert": disk_alert,
            "should_notify": should_notify,
            "message": " · ".join(message_parts) if message_parts else None
        }

        data = {
            "drive": {
                "total_bytes": total_disk_bytes,
                "used_bytes": used_disk_bytes,
                "free_bytes": free_disk_bytes,
                "used_percentage": used_percentage
            },
            "directories": [
                {"name": "01_Raw (ฟุตเทจดิบ)", "folder": "01_Raw", "size_bytes": raw_size, "size_mb": round(raw_size / (1024 * 1024), 1), "size_gb": round(raw_size / (1024**3), 2)},
                {"name": "02_Assets (เพลง/SFX/ฟอนต์)", "folder": "02_Assets", "size_bytes": assets_size, "size_mb": round(assets_size / (1024 * 1024), 1), "size_gb": round(assets_size / (1024**3), 2)},
                {"name": "03_Projects (ดราฟต์ตัดต่อ)", "folder": "03_Projects", "size_bytes": projects_size, "size_mb": round(projects_size / (1024 * 1024), 1), "size_gb": round(projects_size / (1024**3), 2)},
                {"name": "04_Exports (วิดีโอส่งออก)", "folder": "04_Exports", "size_bytes": exports_size, "size_mb": round(exports_size / (1024 * 1024), 1), "size_gb": round(exports_size / (1024**3), 2)},
                {"name": "05_Covers_Thumbnails (ปกคลิป)", "folder": "05_Covers_Thumbnails", "size_bytes": covers_size, "size_mb": round(covers_size / (1024 * 1024), 1), "size_gb": round(covers_size / (1024**3), 2)},
                {"name": "06_Archive (ไฟล์เก่าสำรอง)", "folder": "06_Archive", "size_bytes": archive_size, "size_mb": round(archive_size / (1024 * 1024), 1), "size_gb": round(archive_size / (1024**3), 2)},
            ],
            "capcut_draft_bytes": capcut_draft_size,
            "capcut_draft_gb": round(capcut_draft_size / (1024**3), 2),
            "safe_purge_bytes": safe_purge_bytes,
            "safe_purge_mb": round(safe_purge_bytes / (1024 * 1024), 1),
            "heavy_products": heavy_products,
            "posted_archive_potential": posted_archive_potential,
            "archive_recommendation": archive_recommendation,
            "last_scanned_at": datetime.datetime.now().isoformat()
        }

        _STORAGE_CACHE["data"] = data
        _STORAGE_CACHE["timestamp"] = now
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate storage analytics: {e}")


@router.post("/storage/purge-safe-cache")
def purge_safe_cache() -> Dict[str, Any]:
    """
    Safely clears only temporary audio preview files and CapCut transient cache.
    STRICT DON'T: Never touches 01_Raw or 02_Assets.
    """
    purged_bytes = 0
    purged_files = 0

    try:
        # 1. Clean temporary audio previews in 03_Projects
        for item in PROJECTS_DIR.rglob("*.wav"):
            if "preview" in item.name.lower() or "temp" in item.name.lower():
                try:
                    size = item.stat().st_size
                    item.unlink(missing_ok=True)
                    purged_bytes += size
                    purged_files += 1
                except Exception:
                    pass

        # 2. Clean CapCut cloud_cache if accessible
        if CAPCUT_DRAFT_DIR.exists():
            for entry in CAPCUT_DRAFT_DIR.iterdir():
                if entry.is_dir() and (entry.name.startswith(".cloud_cache") or entry.name.startswith("cache_")):
                    try:
                        size = _dir_size(entry)
                        shutil.rmtree(str(entry), ignore_errors=True)
                        purged_bytes += size
                        purged_files += 1
                    except Exception:
                        pass

        # Invalidate cache to force rescan next time
        _STORAGE_CACHE["data"] = None
        _STORAGE_CACHE["timestamp"] = 0.0

        return {
            "success": True,
            "purged_files": purged_files,
            "purged_bytes": purged_bytes,
            "purged_mb": round(purged_bytes / (1024 * 1024), 2),
            "message": f"ล้างไฟล์แคชชั่วคราวสำเร็จ {purged_files} ไฟล์ ({round(purged_bytes / (1024 * 1024), 2)} MB)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to purge safe cache: {e}")


@router.get("/inventory")
def get_inventory_health() -> Dict[str, Any]:
    """
    Evaluates product readiness and content health:
    - Products with clips vs without
    - Image and video completeness
    - Ready-to-cut catalog scoring
    """
    try:
        products = ProductStore.get_all()
        total_products = len(products)
        
        covered_products = 0
        uncovered_products = 0
        products_with_images = 0
        products_with_videos = 0
        products_with_scripts = 0
        products_with_shots = 0

        product_health_list = []

        for p in products:
            angles = p.get("angles") or []
            images = p.get("images") or []
            videos = p.get("videos") or []
            
            has_rendered_clip = any(a.get("status") in ("rendered", "posted") or a.get("video_url") for a in angles)
            if has_rendered_clip:
                covered_products += 1
            else:
                uncovered_products += 1

            has_images = len(images) > 0
            has_videos = len(videos) > 0
            has_scripts = len(angles) > 0

            if has_images:
                products_with_images += 1
            if has_videos:
                products_with_videos += 1
            if has_scripts:
                products_with_scripts += 1

            # Check shot list presence
            shot_lists_count = 0
            for a in angles:
                aid = a.get("angle_id") or a.get("id")
                # check if shot list exists
                shot_file = PROJECTS_DIR / f".shot_list_{p.get('id')}_{aid}.json"
                if shot_file.exists():
                    shot_lists_count += 1
            if shot_lists_count > 0:
                products_with_shots += 1

            # Completeness score (0 - 100)
            score = 0
            if has_images:
                score += 25
            if len(images) >= 3:
                score += 15
            if has_videos:
                score += 30
            if has_scripts:
                score += 20
            if shot_lists_count > 0:
                score += 10

            product_health_list.append({
                "id": p.get("id"),
                "name": p.get("name") or p.get("title") or "สินค้า",
                "product_code": p.get("product_code") or "",
                "images_count": len(images),
                "videos_count": len(videos),
                "angles_count": len(angles),
                "shot_lists_count": shot_lists_count,
                "rendered_clips": sum(1 for a in angles if a.get("status") in ("rendered", "posted") or a.get("video_url")),
                "completeness_score": min(score, 100),
                "readiness": "ready" if has_videos and has_scripts else ("need_footage" if not has_videos else "need_script"),
                "updated_at": p.get("updated_at") or ""
            })

        # Sort product health by completeness descending
        product_health_list.sort(key=lambda x: x["completeness_score"], reverse=True)

        avg_completeness = (
            round(sum(p["completeness_score"] for p in product_health_list) / total_products, 1)
            if total_products else 0.0
        )

        return {
            "summary": {
                "total_products": total_products,
                "covered_products": covered_products,
                "uncovered_products": uncovered_products,
                "coverage_percentage": round(covered_products / total_products * 100, 1) if total_products else 0.0,
                "with_images_percentage": round(products_with_images / total_products * 100, 1) if total_products else 0.0,
                "with_videos_percentage": round(products_with_videos / total_products * 100, 1) if total_products else 0.0,
                "with_scripts_percentage": round(products_with_scripts / total_products * 100, 1) if total_products else 0.0,
                "avg_completeness_score": avg_completeness
            },
            "products": product_health_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate inventory health: {e}")
