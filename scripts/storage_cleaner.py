"""
Safe Storage Optimizer & Cache Cleaner.
Provides automated scanning and cleanup for safe, reclaimable transient files:
1. Producer Hub vision proxies (.vision_proxies/)
2. Temporary audio/video render previews (preview_*.wav, temp_*.mp4)
3. CapCut draft cloud cache (.cloud_cache*, cache_*)
4. Test / scratch directories that are non-critical

STRICT RULE 1 GUARANTEE:
Never deletes or alters files in 01_Raw or 02_Assets under any condition.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List

from scripts.config import (
    BASE_DIR,
    PROJECTS_DIR,
    CAPCUT_DRAFT_DIR,
    RAW_DIR,
    ASSETS_DIR,
)

SAFE_CACHE_TARGETS = [
    # Transient producer vision thumbnails
    BASE_DIR / ".vision_proxies",
    # Temporary test scratch directory
    BASE_DIR / "temp_scratch",
]


def _dir_size(p: Path) -> int:
    """Safely calculate total size in bytes of a folder."""
    if not p or not p.exists():
        return 0
    total = 0
    try:
        for entry in os.scandir(str(p)):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
            except Exception:
                pass
    except Exception:
        pass
    return total


def is_strictly_protected_path(target_path: Path) -> bool:
    """Returns True if the target path is inside 01_Raw or 02_Assets."""
    try:
        resolved = target_path.resolve()
        raw_resolved = RAW_DIR.resolve()
        assets_resolved = ASSETS_DIR.resolve()
        if resolved == raw_resolved or raw_resolved in resolved.parents:
            return True
        if resolved == assets_resolved or assets_resolved in resolved.parents:
            return True
    except Exception:
        pass
    return False


def scan_safe_reclaimable_cache() -> Dict[str, Any]:
    """
    Scans all transient, non-critical cache areas that can be purged safely without losing work.
    """
    items: List[Dict[str, Any]] = []
    total_bytes = 0

    # 1. Producer Vision Proxies (.vision_proxies)
    vision_proxy_dir = BASE_DIR / ".vision_proxies"
    if vision_proxy_dir.exists():
        v_size = _dir_size(vision_proxy_dir)
        v_count = sum(1 for _ in vision_proxy_dir.rglob("*") if _.is_file())
        if v_size > 0:
            items.append({
                "id": "vision_proxies",
                "label": "AI Vision Proxy Previews",
                "description": "ภาพแคชย่อส่วนขนาดเล็กสำหรับ AI Gemini Vision",
                "path": str(vision_proxy_dir),
                "bytes": v_size,
                "mb": round(v_size / (1024 * 1024), 2),
                "count": v_count,
            })
            total_bytes += v_size

    # 2. Temporary audio/render previews in 03_Projects
    temp_preview_bytes = 0
    temp_preview_count = 0
    if PROJECTS_DIR.exists():
        try:
            for f in PROJECTS_DIR.rglob("*"):
                if f.is_file() and not is_strictly_protected_path(f):
                    name_lower = f.name.lower()
                    if ("preview" in name_lower or "temp" in name_lower) and f.suffix in (".wav", ".mp3", ".tmp", ".jpg", ".png"):
                        temp_preview_bytes += f.stat().st_size
                        temp_preview_count += 1
        except Exception:
            pass

    if temp_preview_bytes > 0:
        items.append({
            "id": "project_previews",
            "label": "ไฟล์พรีวิวเสียงและภาพชั่วคราวใน 03_Projects",
            "description": "ไฟล์เสียงทดสอบ TTS และแคชพรีวิวที่ไม่ได้ใช้งานแล้ว",
            "path": str(PROJECTS_DIR),
            "bytes": temp_preview_bytes,
            "mb": round(temp_preview_bytes / (1024 * 1024), 2),
            "count": temp_preview_count,
        })
        total_bytes += temp_preview_bytes

    # 3. CapCut draft cloud / transient cache
    capcut_cache_bytes = 0
    capcut_cache_count = 0
    if CAPCUT_DRAFT_DIR.exists():
        try:
            for entry in CAPCUT_DRAFT_DIR.iterdir():
                if entry.is_dir() and (entry.name.startswith(".cloud_cache") or entry.name.startswith("cache_")):
                    c_size = _dir_size(entry)
                    capcut_cache_bytes += c_size
                    capcut_cache_count += 1
        except Exception:
            pass

    if capcut_cache_bytes > 0:
        items.append({
            "id": "capcut_cache",
            "label": "CapCut Cloud & Transient Cache",
            "description": "โฟลเดอร์แคชคลาวด์และไฟล์ชั่วคราวของ CapCut PC",
            "path": str(CAPCUT_DRAFT_DIR),
            "bytes": capcut_cache_bytes,
            "mb": round(capcut_cache_bytes / (1024 * 1024), 2),
            "count": capcut_cache_count,
        })
        total_bytes += capcut_cache_bytes

    # 4. Background Isolation Cutout Cache (03_Projects/.cache)
    cutout_cache_dir = PROJECTS_DIR / ".cache"
    cutout_cache_bytes = 0
    cutout_cache_count = 0
    if cutout_cache_dir.exists() and not is_strictly_protected_path(cutout_cache_dir):
        try:
            for f in cutout_cache_dir.rglob("*"):
                if f.is_file():
                    cutout_cache_bytes += f.stat().st_size
                    cutout_cache_count += 1
        except Exception:
            pass

    if cutout_cache_bytes > 0:
        items.append({
            "id": "cutout_cache",
            "label": "แคชการตัดพื้นหลังสินค้า (Cutout Frame Cache)",
            "description": "ไฟล์เฟรมภาพแยกสำหรับตัดพื้นหลังสินค้าใน 03_Projects/.cache",
            "path": str(cutout_cache_dir),
            "bytes": cutout_cache_bytes,
            "mb": round(cutout_cache_bytes / (1024 * 1024), 2),
            "count": cutout_cache_count,
        })
        total_bytes += cutout_cache_bytes

    return {
        "items": items,
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "total_gb": round(total_bytes / (1024 * 1024 * 1024), 3),
        "items_count": len(items),
    }


def execute_safe_purge() -> Dict[str, Any]:
    """
    Executes safe cleanup of transient caches.
    Strictly verifies each path to avoid touching 01_Raw and 02_Assets.
    """
    purged_bytes = 0
    purged_files = 0
    errors: List[str] = []

    # 1. Clean vision proxies
    vision_proxy_dir = BASE_DIR / ".vision_proxies"
    if vision_proxy_dir.exists() and not is_strictly_protected_path(vision_proxy_dir):
        try:
            for p in list(vision_proxy_dir.iterdir()):
                if p.is_file():
                    purged_bytes += p.stat().st_size
                    p.unlink(missing_ok=True)
                    purged_files += 1
        except Exception as e:
            errors.append(f"Vision proxies: {e}")

    # 2. Clean temporary preview files in 03_Projects
    if PROJECTS_DIR.exists():
        try:
            for f in list(PROJECTS_DIR.rglob("*")):
                if f.is_file() and not is_strictly_protected_path(f):
                    name_lower = f.name.lower()
                    if ("preview" in name_lower or "temp" in name_lower) and f.suffix in (".wav", ".mp3", ".tmp", ".jpg", ".png"):
                        try:
                            sz = f.stat().st_size
                            f.unlink(missing_ok=True)
                            purged_bytes += sz
                            purged_files += 1
                        except Exception:
                            pass
        except Exception as e:
            errors.append(f"Projects temp: {e}")

    # 3. Clean CapCut cloud cache
    if CAPCUT_DRAFT_DIR.exists():
        try:
            for entry in list(CAPCUT_DRAFT_DIR.iterdir()):
                if entry.is_dir() and (entry.name.startswith(".cloud_cache") or entry.name.startswith("cache_")):
                    if not is_strictly_protected_path(entry):
                        sz = _dir_size(entry)
                        shutil.rmtree(str(entry), ignore_errors=True)
                        purged_bytes += sz
                        purged_files += 1
        except Exception as e:
            errors.append(f"CapCut cache: {e}")

    # 4. Clean Background Isolation Cutout Cache (03_Projects/.cache)
    cutout_cache_dir = PROJECTS_DIR / ".cache"
    if cutout_cache_dir.exists() and not is_strictly_protected_path(cutout_cache_dir):
        try:
            for item in list(cutout_cache_dir.iterdir()):
                if not is_strictly_protected_path(item):
                    sz = _dir_size(item) if item.is_dir() else item.stat().st_size
                    cnt = sum(1 for _ in item.rglob("*") if _.is_file()) if item.is_dir() else 1
                    if item.is_dir():
                        shutil.rmtree(str(item), ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    purged_bytes += sz
                    purged_files += cnt
        except Exception as e:
            errors.append(f"Cutout cache: {e}")

    return {
        "success": True,
        "purged_files": purged_files,
        "purged_bytes": purged_bytes,
        "purged_mb": round(purged_bytes / (1024 * 1024), 2),
        "message": f"ล้างไฟล์แคชและขยะชั่วคราวสำเร็จ {purged_files} ไฟล์ ({round(purged_bytes / (1024 * 1024), 2)} MB)",
        "errors": errors,
    }


def scan_cutout_cache() -> Dict[str, Any]:
    """
    Scans only the Background Isolation Cutout Cache in 03_Projects/.cache.
    Returns bytes, mb, and file count.
    """
    cutout_cache_dir = PROJECTS_DIR / ".cache"
    cutout_cache_bytes = 0
    cutout_cache_count = 0
    if cutout_cache_dir.exists() and not is_strictly_protected_path(cutout_cache_dir):
        try:
            for f in cutout_cache_dir.rglob("*"):
                if f.is_file():
                    cutout_cache_bytes += f.stat().st_size
                    cutout_cache_count += 1
        except Exception:
            pass
    return {
        "bytes": cutout_cache_bytes,
        "mb": round(cutout_cache_bytes / (1024 * 1024), 2),
        "count": cutout_cache_count,
    }


def purge_cutout_cache_only() -> Dict[str, Any]:
    """
    Safely clears only the Background Isolation Cutout Cache in 03_Projects/.cache.
    STRICT DON'T: Never touches 01_Raw, 02_Assets, or project state files.
    """
    cutout_cache_dir = PROJECTS_DIR / ".cache"
    purged_bytes = 0
    purged_files = 0
    errors = []

    if cutout_cache_dir.exists() and not is_strictly_protected_path(cutout_cache_dir):
        try:
            for item in list(cutout_cache_dir.iterdir()):
                if not is_strictly_protected_path(item):
                    sz = _dir_size(item) if item.is_dir() else item.stat().st_size
                    cnt = sum(1 for _ in item.rglob("*") if _.is_file()) if item.is_dir() else 1
                    if item.is_dir():
                        shutil.rmtree(str(item), ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    purged_bytes += sz
                    purged_files += cnt
        except Exception as e:
            errors.append(f"Cutout cache: {e}")

    return {
        "success": len(errors) == 0,
        "purged_files": purged_files,
        "purged_bytes": purged_bytes,
        "purged_mb": round(purged_bytes / (1024 * 1024), 2),
        "message": f"ล้างแคชตัดพื้นหลังสินค้าสำเร็จ {purged_files} ไฟล์ ({round(purged_bytes / (1024 * 1024), 2)} MB)",
        "errors": errors,
    }

