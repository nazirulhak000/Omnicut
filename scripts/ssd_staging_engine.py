"""SSD Staging Engine for OmniCut Pro Studio.

Agent 1: Staging & Drive Detection Engineer
Packages pending exports, cover thumbnails, schedule queues, the Chrome extension,
and a zero-dependency portable server into an isolated, self-describing vault on an External SSD.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import string
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR, EXPORTS_DIR

DOCS_DIR = BASE_DIR / "_Docs"
COVERS_DIR = BASE_DIR / "05_Covers_Thumbnails"
EXTENSION_DIR = BASE_DIR / "tiktok_autopost_extension"
TOOLS_DIR = BASE_DIR / "tools"

VAULT_DIR_NAME = "OmniCut_Portable_Vault"


def get_removable_drives() -> List[Dict[str, Any]]:
    """Scan and return available removable and external drives on the system."""
    drives: List[Dict[str, Any]] = []
    if platform.system() == "Windows":
        kernel32 = ctypes.windll.kernel32
        bitmask = kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_path = f"{letter}:\\"
                drive_type = kernel32.GetDriveTypeW(drive_path)
                # 2 = DRIVE_REMOVABLE, 3 = DRIVE_FIXED (external USB SSDs often report as FIXED)
                type_name = "removable" if drive_type == 2 else ("fixed" if drive_type == 3 else "other")
                is_candidate = drive_type in (2, 3) and letter != "C"  # Exclude primary OS drive
                free_bytes = ctypes.c_ulonglong(0)
                total_bytes = ctypes.c_ulonglong(0)
                kernel32.GetDiskFreeSpaceExW(
                    drive_path,
                    ctypes.byref(free_bytes),
                    ctypes.byref(total_bytes),
                    None
                )
                drives.append({
                    "drive": drive_path,
                    "letter": letter,
                    "drive_type": type_name,
                    "is_external_candidate": is_candidate,
                    "free_gb": round(free_bytes.value / (1024 ** 3), 2),
                    "total_gb": round(total_bytes.value / (1024 ** 3), 2),
                })
            bitmask >>= 1
    return drives


def flush_disk_buffers(path: Path) -> bool:
    """Commit all pending write buffers to physical NAND storage."""
    try:
        if platform.system() == "Windows":
            # Open directory or file handle and flush
            FILE_SHARE_READ = 1
            FILE_SHARE_WRITE = 2
            OPEN_EXISTING = 3
            FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
            GENERIC_READ = 0x80000000
            GENERIC_WRITE = 0x40000000

            handle = ctypes.windll.kernel32.CreateFileW(
                str(path),
                GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                FILE_FLAG_BACKUP_SEMANTICS,
                None,
            )
            if handle != -1 and handle != 0:
                ctypes.windll.kernel32.FlushFileBuffers(handle)
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
        elif hasattr(os, "sync"):
            os.sync()
            return True
    except Exception:
        pass
    return False


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file efficiently using streaming 1MB blocks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


class SSDStagingEngine:
    """Orchestrates staging of video exports and metadata to an External SSD."""

    @staticmethod
    def stage_to_vault(
        target_root: Path,
        base_dir: Optional[Path] = None,
        export_ids: Optional[List[str]] = None,
        include_all_pending: bool = True,
    ) -> Dict[str, Any]:
        """Stage pending video exports and metadata into OmniCut_Portable_Vault on target_root."""
        project_root = base_dir or BASE_DIR
        docs_dir = project_root / "_Docs"
        vault_root = target_root / VAULT_DIR_NAME

        media_videos_dir = vault_root / "media" / "videos"
        media_covers_dir = vault_root / "media" / "covers"
        vault_docs_dir = vault_root / "_Docs"
        vault_ext_dir = vault_root / "tiktok_autopost_extension"
        vault_tools_dir = vault_root / "tools"

        for directory in (media_videos_dir, media_covers_dir, vault_docs_dir, vault_ext_dir, vault_tools_dir):
            directory.mkdir(parents=True, exist_ok=True)

        # 1. Read canonical registries
        schedule_file = docs_dir / "schedule_queue.json"
        export_file = docs_dir / "export_registry.json"
        channels_file = docs_dir / "channels.json"

        schedule_items = []
        if schedule_file.exists():
            try:
                with open(schedule_file, "r", encoding="utf-8") as f:
                    schedule_items = json.load(f)
            except Exception:
                schedule_items = []

        export_items = []
        if export_file.exists():
            try:
                with open(export_file, "r", encoding="utf-8") as f:
                    export_items = json.load(f)
            except Exception:
                export_items = []

        # 2. Filter items to stage
        items_to_stage = []
        target_export_ids = set(export_ids) if export_ids else None

        for item in schedule_items:
            exp_id = item.get("export_id")
            status = item.get("status", "pending")
            is_unposted = status != "posted" and not bool(item.get("posted_at"))

            if target_export_ids is not None:
                if (exp_id and exp_id in target_export_ids) or item.get("id") in target_export_ids:
                    items_to_stage.append(item)
            elif include_all_pending and is_unposted:
                items_to_stage.append(item)

        # If no items found in schedule_queue, fallback to ready exports in export_registry
        if not items_to_stage and include_all_pending:
            for exp in export_items:
                is_unposted = exp.get("status") != "posted" and not bool(exp.get("posted_at"))
                is_ready = exp.get("status") in ("rendered", "ready") or "Ready_to_post" in exp.get("path", "")
                if is_unposted and is_ready:
                    if target_export_ids is None or exp.get("id") in target_export_ids:
                        items_to_stage.append({
                            "id": "queue_" + str(uuid.uuid4())[:12],
                            "export_id": exp.get("id"),
                            "video_path": exp.get("path"),
                            "status": "pending",
                            "product_id": exp.get("product_id"),
                            "angle_id": exp.get("angle_id"),
                            "project_name": exp.get("project_name", ""),
                            "hook_title": exp.get("project_name", ""),
                            "caption": exp.get("project_name", ""),
                            "hashtags": "#นายหน้าtiktok #รีวิวของดี",
                            "channel_id": "main",
                        })

        # Deduplicate items_to_stage by unique export identity
        seen_keys = set()
        unique_items = []
        for it in items_to_stage:
            key = it.get("export_id") or it.get("video_path") or it.get("id")
            if key and key not in seen_keys:
                seen_keys.add(key)
                unique_items.append(it)
        items_to_stage = unique_items

        # Load existing state from SSD to preserve any already-posted history
        existing_states = {}
        existing_state_file = vault_root / "state.json"
        if existing_state_file.exists():
            try:
                with open(existing_state_file, "r", encoding="utf-8") as f:
                    existing_states = json.load(f)
            except Exception:
                existing_states = {}

        staged_queue = []
        staged_state = {}
        checksum_records = []

        # 3. Copy media assets & compute hashes (Fast Delta Deduplication)
        for item in items_to_stage:
            item_id = item.get("id", str(uuid.uuid4())[:12])
            raw_video_path = item.get("video_path") or ""
            video_src = project_root / raw_video_path

            if not video_src.exists():
                continue

            video_filename = video_src.name
            video_dst = media_videos_dir / video_filename

            # Skip copying if identical file already exists on SSD (Delta Staging)
            if video_dst.exists() and video_dst.stat().st_size == video_src.stat().st_size:
                video_hash = compute_file_sha256(video_dst)
            else:
                shutil.copy2(video_src, video_dst)
                video_hash = compute_file_sha256(video_dst)

            rel_video_path = f"media/videos/{video_filename}"
            checksum_records.append(f"{video_hash}  {rel_video_path}")

            # Cover copy
            cover_filename = None
            rel_cover_path = None
            raw_cover_path = item.get("cover_path")
            if raw_cover_path:
                cover_src = project_root / raw_cover_path
                if cover_src.exists():
                    cover_filename = cover_src.name
                    cover_dst = media_covers_dir / cover_filename
                    if cover_dst.exists() and cover_dst.stat().st_size == cover_src.stat().st_size:
                        cover_hash = compute_file_sha256(cover_dst)
                    else:
                        shutil.copy2(cover_src, cover_dst)
                        cover_hash = compute_file_sha256(cover_dst)
                    rel_cover_path = f"media/covers/{cover_filename}"
                    checksum_records.append(f"{cover_hash}  {rel_cover_path}")

            # Build staged item
            staged_item = {
                "id": item_id,
                "export_id": item.get("export_id"),
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name") or item.get("project_name", ""),
                "hook_title": item.get("hook_title", ""),
                "caption": item.get("caption", ""),
                "hashtags": item.get("hashtags", ""),
                "tiktok_product_id": item.get("tiktok_product_id"),
                "scheduled_at": item.get("scheduled_at"),
                "channel_id": item.get("channel_id", "main"),
                "status": "pending",
                "video_rel_path": rel_video_path,
                "video_filename": video_filename,
                "cover_rel_path": rel_cover_path,
                "cover_filename": cover_filename,
                "video_sha256": video_hash,
            }
            staged_queue.append(staged_item)

            # Preserve previous posted outcome if present on SSD
            if item_id in existing_states and existing_states[item_id].get("status") == "posted":
                staged_state[item_id] = existing_states[item_id]
            else:
                staged_state[item_id] = {
                    "status": "pending",
                    "uploaded_at": None,
                    "post_url": None,
                    "post_id": None,
                    "error": None,
                }

        # 4. Write Vault Metadata
        batch_id = "batch_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        manifest = {
            "batch_id": batch_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_machine": platform.node(),
            "items_count": len(staged_queue),
            "vault_version": "1.0.0",
            "ready_for_upload": True,
        }

        with open(vault_root / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        with open(vault_root / "queue.json", "w", encoding="utf-8") as f:
            json.dump(staged_queue, f, indent=2, ensure_ascii=False)

        with open(vault_root / "state.json", "w", encoding="utf-8") as f:
            json.dump(staged_state, f, indent=2, ensure_ascii=False)

        with open(vault_root / "checksums.sha256", "w", encoding="utf-8") as f:
            f.write("\n".join(checksum_records) + "\n")

        # Copy channels.json if exists
        if channels_file.exists():
            shutil.copy2(channels_file, vault_docs_dir / "channels.json")
        else:
            default_channels = [{"id": "main", "name": "Main Channel", "handle": "@default", "status": "active"}]
            with open(vault_docs_dir / "channels.json", "w", encoding="utf-8") as f:
                json.dump(default_channels, f, indent=2)

        # 5. Copy Extension to Vault
        real_ext_src = EXTENSION_DIR if EXTENSION_DIR.exists() else project_root / "tiktok_autopost_extension"
        if real_ext_src.exists():
            shutil.copytree(real_ext_src, vault_ext_dir, dirs_exist_ok=True)

        # 6. Copy / generate portable mini-server
        portable_server_src = TOOLS_DIR / "portable_uploader_server.py"
        if portable_server_src.exists():
            shutil.copy2(portable_server_src, vault_tools_dir / "portable_uploader_server.py")

        # 7. Write START_CAFE_UPLOADER.bat launcher (with Embedded Python & System Fallback)
        bat_content = (
            "@echo off\r\n"
            "title OmniCut Cafe Uploader Server\r\n"
            "chcp 65001 > nul\r\n"
            "echo =====================================================\r\n"
            "echo   🚀 OmniCut Pro Studio - Cafe Uploader (Portable)   \r\n"
            "echo =====================================================\r\n"
            "cd /d \"%~dp0\"\r\n"
            "echo [1/3] ตรวจหา Python (Portable Embedded หรือ System Python)...\r\n"
            "if exist \"tools\\python\\python.exe\" (\r\n"
            "    echo [OK] พบ Portable Embedded Python บน SSD!\r\n"
            "    set PY_CMD=\"tools\\python\\python.exe\"\r\n"
            "    goto :RUN_SERVER\r\n"
            ")\r\n"
            "set PY_CMD=python\r\n"
            "where python >nul 2>nul\r\n"
            "if %ERRORLEVEL% equ 0 goto :RUN_SERVER\r\n"
            "set PY_CMD=py\r\n"
            "where py >nul 2>nul\r\n"
            "if %ERRORLEVEL% equ 0 goto :RUN_SERVER\r\n"
            "echo.\r\n"
            "echo [ERROR] ไม่พบ Python ในเครื่องโน้ตบุ๊ก และไม่พบ tools\\python\\ บน SSD\r\n"
            "echo 💡 คำแนะนำ: ติดตั้ง Python ในเครื่อง หรือดาวน์โหลด Python Embeddable ใส่ใน tools\\python\\\r\n"
            "echo.\r\n"
            "pause\r\n"
            "exit /b 1\r\n"
            "\r\n"
            ":RUN_SERVER\r\n"
            "echo [2/3] รันเซิร์ฟเวอร์จิ๋วพกพาบนพอร์ต 8000...\r\n"
            "start \"OmniCut_Mini_Server\" %PY_CMD% \"tools\\portable_uploader_server.py\" --port 8000\r\n"
            "timeout /t 2 > nul\r\n"
            "echo [3/3] เปิดหน้า TikTok Studio ใน Google Chrome...\r\n"
            "start \"\" \"https://www.tiktok.com/creator-center/upload\"\r\n"
            "echo.\r\n"
            "echo [READY] พร้อมอัปโหลดแล้ว! เปิดแถบข้าง Chrome Extension แล้วกดปุ่มโพสต์ได้เลย\r\n"
            "echo =====================================================\r\n"
            "pause\r\n"
        )
        with open(vault_root / "START_CAFE_UPLOADER.bat", "w", encoding="utf-8") as f:
            f.write(bat_content)

        # 8. Flush physical disk buffers
        flush_disk_buffers(vault_root)

        return {
            "status": "ok",
            "vault_path": str(vault_root),
            "batch_id": batch_id,
            "staged_count": len(staged_queue),
            "media_count": len(checksum_records),
            "safe_to_eject": True,
        }
