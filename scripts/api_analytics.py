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
from typing import Dict, Any, List, Optional, Set
from fastapi import APIRouter, HTTPException, Query

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, ASSETS_DIR,
    PROJECTS_DIR, EXPORTS_DIR, COVERS_DIR, ARCHIVE_DIR,
    CAPCUT_DRAFT_DIR
)
from scripts.product_store import ProductStore
from scripts.token_tracker import TokenTracker
from scripts.storage_cleaner import (
    scan_safe_reclaimable_cache,
    execute_safe_purge,
    scan_cutout_cache,
    purge_cutout_cache_only,
)

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
    if not path or not path.exists() or path.is_symlink() or not path.is_dir():
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


def _safe_direct_child(root: Path, value: object) -> Optional[Path]:
    """Resolve a trusted direct child without allowing traversal or symlinks."""
    if value is None:
        return None
    raw_value = str(value).strip()
    if not raw_value or raw_value in {".", ".."}:
        return None

    candidate = Path(raw_value)
    if candidate.is_absolute() or len(candidate.parts) != 1:
        return None

    try:
        root_resolved = root.resolve()
        resolved = (root_resolved / candidate).resolve()
        if resolved.parent != root_resolved or resolved.is_symlink():
            return None
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def _parse_iso(value: object) -> Optional[datetime.datetime]:
    """Parse the ISO timestamps used by ProductStore/PostLog."""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _age_days_from_iso(iso_str: Optional[str]) -> Optional[int]:
    """Days elapsed since an ISO timestamp; None if missing/unparseable."""
    if not iso_str:
        return None
    try:
        then = _parse_iso(iso_str)
        if then is None:
            return None
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
        known_created_at_count = 0
        posted_with_created_at_count = 0
        created_to_posted_count = 0
        created_to_posted_times_sec = []
        recent_productions = []

        now = datetime.datetime.now()

        for p in products:
            angles = p.get("angles") or []
            for a in angles:
                total_angles += 1
                status = a.get("status") or "scripted"
                # A posted_at timestamp is durable evidence of publication for
                # legacy records whose status field was not migrated yet.
                if a.get("posted_at"):
                    status = "posted"
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
                c_dt = _parse_iso(created_at_str)
                p_dt = _parse_iso(posted_at_str)
                if c_dt:
                    known_created_at_count += 1
                    if status == "posted":
                        posted_with_created_at_count += 1
                if c_dt and p_dt:
                    try:
                        if c_dt.tzinfo and not p_dt.tzinfo:
                            p_dt = p_dt.replace(tzinfo=c_dt.tzinfo)
                        elif p_dt.tzinfo and not c_dt.tzinfo:
                            c_dt = c_dt.replace(tzinfo=p_dt.tzinfo)
                        diff = (p_dt - c_dt).total_seconds()
                        if diff > 0:
                            created_to_posted_count += 1
                            created_to_posted_times_sec.append(diff)
                            if diff < 86400 * 30:  # reasonable cycle-time window
                                cycle_times_sec.append(diff)
                    except (TypeError, ValueError):
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

        bottleneck_stage = None
        if status_counts["scripted"] > 15 and status_counts["in_production"] < 3:
            bottleneck_stage = "scripted"
        elif status_counts["in_production"] > 10:
            bottleneck_stage = "in_production"
        elif status_counts["rendered"] > 10 and status_counts["posted"] < status_counts["rendered"] / 2:
            bottleneck_stage = "rendered"

        current_state_percentages = {
            key: round((count / total_angles * 100), 1) if total_angles else 0.0
            for key, count in status_counts.items()
        }
        observed_created_to_posted_rate = (
            round((created_to_posted_count / known_created_at_count * 100), 1)
            if known_created_at_count else None
        )

        return {
            "summary": {
                "total_products": len(products),
                "total_angles": total_angles,
                "scripted": status_counts["scripted"],
                "in_production": status_counts["in_production"],
                "rendered": status_counts["rendered"],
                "posted": status_counts["posted"],
                # Existing dashboard field kept as a current-state snapshot
                # ratio, not a cohort conversion rate.
                "published_percentage": current_state_percentages["posted"],
                "current_state_percentages": current_state_percentages,
                "avg_cycle_time_minutes": avg_cycle_time_minutes,
                "bottleneck_note": bottleneck,
                "bottleneck_stage": bottleneck_stage,
                "lifecycle": {
                    "cohort_conversion_available": False,
                    "known_created_at_count": known_created_at_count,
                    "posted_with_created_at_count": posted_with_created_at_count,
                    "created_to_posted_observations": created_to_posted_count,
                    "created_to_posted_observed_rate": observed_created_to_posted_rate,
                    "created_to_posted_cycle_time_sample_count": len(created_to_posted_times_sec),
                    "note": "Status transition history is not stored; rates are current-state observations, not cohort conversion.",
                }
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
        capcut_draft_size = _dir_size(CAPCUT_DRAFT_DIR) if CAPCUT_DRAFT_DIR.exists() else 0

        # Scan safe reclaimable caches via storage_cleaner
        reclaimable_scan = scan_safe_reclaimable_cache()
        safe_purge_bytes = reclaimable_scan["total_bytes"]

        # Top heaviest product folders in 01_Raw
        heavy_products = []
        try:
            if RAW_DIR.exists():
                for item in RAW_DIR.iterdir():
                    if item.is_dir() and not item.is_symlink():
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

        # Scan posted exports & potential archive candidates. The Posted folder
        # is resolved below the configured export root; untrusted project names
        # never participate in filesystem joins.
        exports_root = EXPORTS_DIR.parent if EXPORTS_DIR.name == "Ready_to_post" else EXPORTS_DIR
        posted_dir = _safe_direct_child(exports_root, "Posted")
        posted_mp4s = []
        if posted_dir and posted_dir.exists() and posted_dir.is_dir() and not posted_dir.is_symlink():
            try:
                posted_mp4s = [
                    item for item in posted_dir.iterdir()
                    if item.is_file() and not item.is_symlink() and item.suffix.lower() == ".mp4"
                ]
            except (OSError, PermissionError):
                posted_mp4s = []
        posted_exports_bytes = 0
        for media_file in posted_mp4s:
            try:
                posted_exports_bytes += media_file.stat().st_size
            except (OSError, PermissionError):
                continue

        products = ProductStore.get_all()
        posted_angles_count = 0
        posted_projects_bytes = 0
        posted_projects_set: Set[str] = set()
        completed_raw_paths: Set[str] = set()
        completed_products_raw_bytes = 0
        posted_items_list = []

        for p in products:
            angles = p.get("angles", [])
            p_posted = [a for a in angles if a.get("status") == "posted" or a.get("posted_at")]
            posted_angles_count += len(p_posted)

            # If all angles are posted, raw footage becomes an archive
            # candidate; external backup is still required before reclaiming.
            if angles and len(p_posted) == len(angles):
                code = p.get("product_code") or p.get("id")
                if code and RAW_DIR.exists() and RAW_DIR.is_dir() and not RAW_DIR.is_symlink():
                    try:
                        for rdir in RAW_DIR.iterdir():
                            if not rdir.is_dir() or rdir.is_symlink() or str(code).casefold() not in rdir.name.casefold():
                                continue
                            raw_key = str(rdir.resolve()).casefold()
                            if raw_key in completed_raw_paths:
                                continue
                            raw_size = _dir_size(rdir)
                            if raw_size <= 0:
                                continue
                            completed_raw_paths.add(raw_key)
                            completed_products_raw_bytes += raw_size
                            posted_dates = [a.get("posted_at") for a in p_posted if a.get("posted_at")]
                            raw_posted_at = max(posted_dates) if posted_dates else None
                            posted_items_list.append({
                                "type": "raw_source",
                                "name": rdir.name,
                                "product_name": p.get("name") or "สินค้า",
                                "size_bytes": raw_size,
                                "size_mb": round(raw_size / (1024 * 1024), 1),
                                "posted_at": raw_posted_at,
                                "age_days": _age_days_from_iso(raw_posted_at),
                                "archive_reason": "all_angles_posted",
                            })
                    except (OSError, PermissionError):
                        pass

            for a in p_posted:
                proj_name = a.get("project_name")
                pdir = _safe_direct_child(PROJECTS_DIR, proj_name)
                if pdir and pdir.exists() and pdir.is_dir() and not pdir.is_symlink():
                    project_key = str(pdir.resolve()).casefold()
                    if project_key in posted_projects_set:
                        continue
                    psize = _dir_size(pdir)
                    if psize <= 0:
                        continue
                    posted_projects_set.add(project_key)
                    posted_projects_bytes += psize
                    posted_at_str = a.get("posted_at")
                    posted_items_list.append({
                        "type": "project",
                        "name": pdir.name,
                        "product_name": p.get("name") or "สินค้า",
                        "size_bytes": psize,
                        "size_mb": round(psize / (1024 * 1024), 1),
                        "posted_at": posted_at_str,
                        "age_days": _age_days_from_iso(posted_at_str)
                    })

        for f in posted_mp4s:
            try:
                fstat = f.stat()
                fsize = fstat.st_size
                # Files carry no posted_at of their own -- mtime is set when
                # the export lands in Posted/, so it is a reasonable proxy.
                mtime_iso = datetime.datetime.fromtimestamp(fstat.st_mtime).isoformat()
            except (OSError, PermissionError):
                continue
            posted_items_list.append({
                "type": "export_mp4",
                "name": f.name,
                "size_bytes": fsize,
                "size_mb": round(fsize / (1024 * 1024), 1),
                "posted_at": mtime_iso,
                "age_days": _age_days_from_iso(mtime_iso)
            })

        archive_candidate_bytes = posted_exports_bytes + posted_projects_bytes + completed_products_raw_bytes

        posted_archive_potential = {
            "posted_clips_count": len(posted_mp4s),
            "posted_angles_count": posted_angles_count,
            "posted_exports_bytes": posted_exports_bytes,
            "posted_exports_mb": round(posted_exports_bytes / (1024 * 1024), 1),
            "posted_projects_bytes": posted_projects_bytes,
            "posted_projects_mb": round(posted_projects_bytes / (1024 * 1024), 1),
            "posted_projects_count": len(posted_projects_set),
            "completed_products_raw_bytes": completed_products_raw_bytes,
            "completed_products_raw_mb": round(completed_products_raw_bytes / (1024 * 1024), 1),
            "completed_products_raw_count": len(completed_raw_paths),
            "archive_candidate_bytes": archive_candidate_bytes,
            "archive_candidate_mb": round(archive_candidate_bytes / (1024 * 1024), 1),
            "archive_candidate_gb": round(archive_candidate_bytes / (1024 ** 3), 2),
            # Legacy reclaim fields now mean only files covered by the safe
            # purge policy. Archive candidates stay separate because they need
            # verified external backup before any local deletion.
            "total_reclaimable_bytes": safe_purge_bytes,
            "total_reclaimable_mb": round(safe_purge_bytes / (1024 * 1024), 1),
            "total_reclaimable_gb": round(safe_purge_bytes / (1024 ** 3), 2),
            "reclaim_estimate_is_safe_delete": True,
            "reclaim_estimate_note": "Safe purge amount only; archive candidates require external backup first.",
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
            "safe_purge_items": reclaimable_scan.get("items", []),
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
    Safely clears only temporary audio preview files, vision proxies, and CapCut transient cache.
    STRICT DON'T: Never touches 01_Raw or 02_Assets.
    """
    try:
        res = execute_safe_purge()

        # Invalidate cache to force rescan next time
        _STORAGE_CACHE["data"] = None
        _STORAGE_CACHE["timestamp"] = 0.0

        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to purge safe cache: {e}")


@router.get("/storage/cutout-cache")
def get_cutout_cache_stats() -> Dict[str, Any]:
    """
    Returns current status and size of the Background Isolation Cutout Cache.
    """
    try:
        return scan_cutout_cache()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan cutout cache: {e}")


@router.post("/storage/purge-cutout-cache")
def purge_cutout_cache() -> Dict[str, Any]:
    """
    Safely clears only the Background Isolation Cutout Cache in 03_Projects/.cache.
    STRICT DON'T: Never touches 01_Raw or 02_Assets.
    """
    try:
        res = purge_cutout_cache_only()
        _STORAGE_CACHE["data"] = None
        _STORAGE_CACHE["timestamp"] = 0.0
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to purge cutout cache: {e}")


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
