"""
Safe Storage Optimizer & Cache Cleaner.
Provides automated scanning and cleanup for safe, reclaimable transient files:
1. Producer Hub vision proxies (.vision_proxies/)
2. Temporary audio/video render previews (preview_*.wav, temp_*.mp4)
3. CapCut draft cloud cache (.cloud_cache* only; any folder holding
   draft_content.json is a real draft and is never touched)
4. Test / scratch directories that are non-critical
5. Editing proxies (03_Projects/.cache/editing-proxies) -- 540p stand-ins
   rebuilt on demand from masters that are never touched here

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
from scripts.proxy_manager import purge_proxy_cache, scan_proxy_cache

SAFE_CACHE_TARGETS = [
    # Transient producer vision thumbnails
    BASE_DIR / ".vision_proxies",
    # Temporary test scratch directory
    BASE_DIR / "temp_scratch",
]

TEMP_PROJECT_PREFIXES = ("preview_", "temp_")
TEMP_PROJECT_SUFFIXES = (".wav", ".mp3", ".tmp", ".jpg", ".png")
CAPCUT_CACHE_PREFIX = ".cloud_cache"
CAPCUT_DRAFT_MARKER = "draft_content.json"

CUTOUT_NAMESPACES = ("background-isolation", "background-isolation-sequences",
                     "background-isolation-foreground-sequences", "background-isolation-videos")


def _cutout_cache_roots() -> list[Path]:
    root = PROJECTS_DIR / ".cache"
    if root.is_symlink() or root.is_junction() or not root.is_dir():
        return []
    resolved = root.resolve()
    return [path for name in CUTOUT_NAMESPACES if (path := root / name).is_dir()
            and not path.is_symlink() and not path.is_junction()
            and path.resolve().parent == resolved and not is_strictly_protected_path(path)]


def _is_transient_project_file(f: Path) -> bool:
    """True for scratch audio/image files named preview_* or temp_* (prefix only,
    so template.png / cover_preview.jpg are never matched)."""
    return f.name.lower().startswith(TEMP_PROJECT_PREFIXES) and f.suffix in TEMP_PROJECT_SUFFIXES


def _is_capcut_cache_dir(entry: Path) -> bool:
    """True only for CapCut .cloud_cache* folders that do not hold a real draft."""
    try:
        return (
            entry.is_dir()
            and not entry.is_symlink()
            and entry.name.startswith(CAPCUT_CACHE_PREFIX)
            and not any(entry.rglob(CAPCUT_DRAFT_MARKER))
        )
    except Exception:
        return False


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
                    if _is_transient_project_file(f):
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
                if _is_capcut_cache_dir(entry):
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
    cutout_summary = scan_cutout_cache()
    cutout_cache_bytes = cutout_summary["bytes"]
    cutout_cache_count = cutout_summary["count"]

    if cutout_cache_bytes > 0:
        items.append({
            "id": "cutout_cache",
            "label": "แคชการตัดพื้นหลังสินค้า (Cutout)",
            "description": "วิดีโอ Cutout, Preview และเฟรมรุ่นเก่า เฉพาะโฟลเดอร์ Cutout",
            "path": str(cutout_cache_dir),
            "bytes": cutout_cache_bytes,
            "mb": round(cutout_cache_bytes / (1024 * 1024), 2),
            "count": cutout_cache_count,
        })
        total_bytes += cutout_cache_bytes

    # 5. Editing Proxy Cache (03_Projects/.cache/editing-proxies)
    proxy_summary = scan_proxy_cache()
    if proxy_summary["bytes"] > 0:
        items.append({
            "id": "editing_proxies",
            "label": "แคชไฟล์พรีวิวย่อ (Editing Proxy)",
            "description": "ไฟล์วิดีโอย่อ 540p สำหรับเล่นบนไทม์ไลน์ สร้างใหม่ได้เสมอจากไฟล์ต้นฉบับ",
            "path": proxy_summary["path"],
            "bytes": proxy_summary["bytes"],
            "mb": round(proxy_summary["bytes"] / (1024 * 1024), 2),
            "count": proxy_summary["count"],
        })
        total_bytes += proxy_summary["bytes"]

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
                    if _is_transient_project_file(f):
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
                if _is_capcut_cache_dir(entry):
                    if not is_strictly_protected_path(entry):
                        sz = _dir_size(entry)
                        shutil.rmtree(str(entry), ignore_errors=True)
                        purged_bytes += sz
                        purged_files += 1
        except Exception as e:
            errors.append(f"CapCut cache: {e}")

    # 4. Clean Background Isolation Cutout Cache (03_Projects/.cache)
    cutout_result = purge_cutout_cache_only()
    purged_bytes += cutout_result["purged_bytes"]
    purged_files += cutout_result["purged_files"]
    errors.extend(cutout_result["errors"])

    # 5. Clean editing proxies. Only this namespace is removed -- the shared
    # 03_Projects/.cache parent holds the cutout caches too.
    try:
        proxy_result = purge_proxy_cache()
        purged_bytes += proxy_result["freed_bytes"]
        purged_files += proxy_result["removed_count"]
    except Exception as e:
        errors.append(f"Editing proxies: {e}")

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
    cutout_cache_bytes = 0
    cutout_cache_count = 0
    for cutout_cache_dir in _cutout_cache_roots():
        try:
            for f in cutout_cache_dir.rglob("*"):
                if f.is_file() and not f.is_symlink():
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
    purged_bytes = 0
    purged_files = 0
    errors = []

    for item in _cutout_cache_roots():
        try:
            # Reject links inside the namespace as well: Windows junctions can
            # point at another project even when the top-level path is safe.
            members = list(item.rglob("*"))
            if any(path.is_symlink() or path.is_junction() for path in members):
                raise ValueError(f"unsafe link in {item.name}")
            sz = _dir_size(item)
            cnt = sum(path.is_file() for path in members)
            shutil.rmtree(item)
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
