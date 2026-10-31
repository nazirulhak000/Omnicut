#!/usr/bin/env python3
"""Google Drive Archiving & Smart Breadcrumbs Engine for OmniCut Pro Studio.

Backs up heavy, completed/posted video assets, raw footage, and project drafts
to Google Drive (e.g. G:\\My Drive\\Omnicut_Exports\\02_Posted_Archive) to reclaim
local SSD storage, while strictly retaining lightweight 3:4 cover thumbnails,
metadata, and post proof locally in OmniCut so that UI galleries remain intact.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from scripts.config import BASE_DIR, EXPORTS_DIR, COVERS_DIR, RAW_DIR, PROJECTS_DIR

# Default Google Drive Desktop archive directory
DEFAULT_GDRIVE_ARCHIVE_PATH = Path("G:/My Drive/Omnicut_Exports/02_Posted_Archive")


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 digest of a file in streaming chunks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):  # 1MB chunks
            hasher.update(chunk)
    return hasher.hexdigest()


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


class GDriveArchiveEngine:
    """Engine for archiving posted clips to Google Drive and safely reclaiming local disk space."""

    @staticmethod
    def get_archive_root(custom_path: Optional[Path] = None) -> Optional[Path]:
        """Detect and return the active Google Drive archive directory."""
        if custom_path and custom_path.exists():
            return custom_path

        env_path = os.environ.get("OMNICUT_GDRIVE_ARCHIVE_DIR")
        if env_path:
            p = Path(env_path)
            if p.exists():
                return p

        # Check standard Google Drive Desktop location on G:
        if DEFAULT_GDRIVE_ARCHIVE_PATH.exists():
            return DEFAULT_GDRIVE_ARCHIVE_PATH

        parent = DEFAULT_GDRIVE_ARCHIVE_PATH.parent
        if parent.exists():
            DEFAULT_GDRIVE_ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
            return DEFAULT_GDRIVE_ARCHIVE_PATH

        return None

    @staticmethod
    def get_archive_status(
        base_dir: Optional[Path] = None,
        custom_gdrive_root: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Inspect all posted exports, calculate reclaimable space, and group by product."""
        root = base_dir or BASE_DIR
        docs_dir = root / "_Docs"
        export_file = docs_dir / "export_registry.json"
        post_log_file = docs_dir / "post_log.json"
        archive_root = GDriveArchiveEngine.get_archive_root(custom_gdrive_root)

        exports = []
        if export_file.exists():
            try:
                with open(export_file, "r", encoding="utf-8") as f:
                    exports = json.load(f)
            except Exception:
                exports = []

        post_logs = []
        if post_log_file.exists():
            try:
                with open(post_log_file, "r", encoding="utf-8") as f:
                    post_logs = json.load(f)
            except Exception:
                post_logs = []

        posted_export_ids = set()
        for p in post_logs:
            clip_file = p.get("clip_file") or ""
            if clip_file:
                posted_export_ids.add(Path(clip_file).stem)

        products_map: Dict[str, Dict[str, Any]] = {}
        total_reclaimable_bytes = 0
        total_archived_bytes = 0
        eligible_count = 0
        archived_count = 0

        for exp in exports:
            exp_id = exp.get("id")
            status = exp.get("status")
            posted_at = exp.get("posted_at")
            cloud_status = exp.get("cloud_status")
            rel_path = exp.get("path") or ""

            # Check if this export has been posted
            is_posted = status == "posted" or bool(posted_at) or exp_id in posted_export_ids
            if not is_posted:
                continue

            local_video_path = root / rel_path if rel_path else None
            local_exists = local_video_path.exists() and local_video_path.is_file() if local_video_path else False
            file_size = local_video_path.stat().st_size if local_exists else 0

            prod_id = exp.get("product_id") or "unassigned"
            prod_name = exp.get("project_name") or exp.get("product_name") or prod_id

            if prod_id not in products_map:
                # Find cover art
                cover_rel = exp.get("cover_path")
                if not cover_rel:
                    candidate_cover = root / "05_Covers_Thumbnails" / f"{prod_name}_cover_3x4.jpg"
                    if candidate_cover.exists():
                        cover_rel = f"05_Covers_Thumbnails/{candidate_cover.name}"

                products_map[prod_id] = {
                    "product_id": prod_id,
                    "product_name": prod_name,
                    "cover_path": cover_rel,
                    "cover_url": f"/api/media/{cover_rel}" if cover_rel else None,
                    "clips": [],
                    "total_bytes": 0,
                    "eligible_bytes": 0,
                    "archived_bytes": 0,
                    "all_archived": True,
                }

            is_already_archived = cloud_status == "archived_gdrive"
            if is_already_archived:
                archived_count += 1
                total_archived_bytes += file_size or exp.get("archived_size", 0)
                products_map[prod_id]["archived_bytes"] += file_size or exp.get("archived_size", 0)
            elif local_exists:
                eligible_count += 1
                total_reclaimable_bytes += file_size
                products_map[prod_id]["eligible_bytes"] += file_size
                products_map[prod_id]["all_archived"] = False

            products_map[prod_id]["total_bytes"] += file_size
            products_map[prod_id]["clips"].append({
                "export_id": exp_id,
                "project_name": exp.get("project_name"),
                "path": rel_path,
                "local_exists": local_exists,
                "size_bytes": file_size,
                "size_formatted": format_bytes(file_size),
                "posted_at": posted_at,
                "cloud_status": cloud_status,
                "cloud_path": exp.get("cloud_path"),
            })

        products_list = list(products_map.values())
        products_list.sort(key=lambda p: p["eligible_bytes"], reverse=True)

        return {
            "status": "ok",
            "gdrive_available": archive_root is not None,
            "gdrive_root": str(archive_root) if archive_root else None,
            "eligible_clips_count": eligible_count,
            "archived_clips_count": archived_count,
            "total_reclaimable_bytes": total_reclaimable_bytes,
            "total_reclaimable_formatted": format_bytes(total_reclaimable_bytes),
            "total_archived_bytes": total_archived_bytes,
            "total_archived_formatted": format_bytes(total_archived_bytes),
            "products": products_list,
        }

    @staticmethod
    def archive_clips(
        export_ids: Optional[List[str]] = None,
        product_ids: Optional[List[str]] = None,
        scope: str = "video_only",  # "video_only" or "full"
        base_dir: Optional[Path] = None,
        custom_gdrive_root: Optional[Path] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Archive target posted clips to Google Drive, verify SHA-256, and reclaim local space.
        
        Features Smart Delta Skip (skips recopying if verified copy exists on Drive)
        and real-time progress callbacks.
        """
        root = base_dir or BASE_DIR
        docs_dir = root / "_Docs"
        export_file = docs_dir / "export_registry.json"
        post_log_file = docs_dir / "post_log.json"

        archive_root = GDriveArchiveEngine.get_archive_root(custom_gdrive_root)
        if not archive_root:
            raise FileNotFoundError(
                "ไม่พบโฟลเดอร์ Google Drive (G:/My Drive/Omnicut_Exports/02_Posted_Archive) "
                "กรุณาตรวจสอบว่าเปิดโปรแกรม Google Drive for Desktop หรือยังครับ"
            )

        if not export_file.exists():
            return {"status": "error", "message": "ไม่พบ export_registry.json"}

        with open(export_file, "r", encoding="utf-8") as f:
            exports = json.load(f)

        target_exp_ids = set(export_ids) if export_ids else None
        target_prod_ids = set(product_ids) if product_ids else None

        # Pre-scan eligible candidates
        eligible_candidates = []
        total_target_bytes = 0
        for exp in exports:
            exp_id = exp.get("id")
            prod_id = exp.get("product_id") or "unassigned"
            status = exp.get("status")
            posted_at = exp.get("posted_at")
            rel_path = exp.get("path") or ""

            if target_exp_ids and exp_id not in target_exp_ids:
                continue
            if target_prod_ids and prod_id not in target_prod_ids:
                continue
            is_posted = status == "posted" or bool(posted_at)
            if not is_posted:
                continue

            local_video_path = root / rel_path
            if not local_video_path.exists() or not local_video_path.is_file():
                continue

            file_size = local_video_path.stat().st_size
            total_target_bytes += file_size
            eligible_candidates.append(exp)

        total_targets = len(eligible_candidates)
        archived_records = []
        reclaimed_bytes = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        if total_targets == 0:
            if progress_callback:
                progress_callback({
                    "stage": "completed",
                    "current_index": 0,
                    "total_items": 0,
                    "current_file": "",
                    "product_name": "",
                    "reclaimed_bytes": 0,
                    "reclaimed_formatted": "0 B",
                    "total_bytes": 0,
                    "percent": 100.0,
                })
            return {
                "status": "ok",
                "archived_count": 0,
                "reclaimed_bytes": 0,
                "reclaimed_formatted": "0 B",
                "records": [],
                "gdrive_vault": str(archive_root),
            }

        for i, exp in enumerate(eligible_candidates):
            exp_id = exp.get("id")
            prod_id = exp.get("product_id") or "unassigned"
            rel_path = exp.get("path") or ""
            local_video_path = root / rel_path
            if not local_video_path.exists() or not local_video_path.is_file():
                continue

            file_size = local_video_path.stat().st_size
            safe_prod_name = exp.get("project_name") or prod_id
            product_archive_dir = archive_root / safe_prod_name
            videos_archive_dir = product_archive_dir / "Videos"
            covers_archive_dir = product_archive_dir / "Covers"
            videos_archive_dir.mkdir(parents=True, exist_ok=True)
            covers_archive_dir.mkdir(parents=True, exist_ok=True)

            dest_video_path = videos_archive_dir / local_video_path.name

            # Notify start of file
            if progress_callback:
                progress_callback({
                    "stage": "copying",
                    "current_index": i + 1,
                    "total_items": total_targets,
                    "current_file": local_video_path.name,
                    "product_name": safe_prod_name,
                    "reclaimed_bytes": reclaimed_bytes,
                    "reclaimed_formatted": format_bytes(reclaimed_bytes),
                    "total_bytes": total_target_bytes,
                    "percent": round((i / total_targets) * 100, 1),
                })

            local_hash = compute_file_sha256(local_video_path)

            # SMART DELTA SKIP: Check if destination already exists with identical size and hash
            already_synced = False
            if dest_video_path.exists() and dest_video_path.stat().st_size == file_size:
                remote_hash = compute_file_sha256(dest_video_path)
                if remote_hash == local_hash:
                    already_synced = True

            if not already_synced:
                # Copy video to Google Drive
                shutil.copy2(local_video_path, dest_video_path)

                # Double verification: File size & SHA-256 Checksum must match bit-for-bit
                if not dest_video_path.exists() or dest_video_path.stat().st_size != file_size:
                    raise IOError(f"Google Drive verification failed: size mismatch for {dest_video_path.name}")

                remote_hash = compute_file_sha256(dest_video_path)
                if local_hash != remote_hash:
                    raise ValueError(f"Checksum mismatch between local and Google Drive for {dest_video_path.name}")

            # Also backup cover to Google Drive (BUT KEEP LOCAL COVER INTACT)
            cover_rel = exp.get("cover_path")
            if cover_rel:
                local_cover_path = root / cover_rel
                if local_cover_path.exists():
                    dest_cover_path = covers_archive_dir / local_cover_path.name
                    if not (dest_cover_path.exists() and dest_cover_path.stat().st_size == local_cover_path.stat().st_size):
                        shutil.copy2(local_cover_path, dest_cover_path)

            # Write individual manifest for this product archive
            manifest_file = product_archive_dir / "archive_manifest.json"
            manifest_data = {
                "product_id": prod_id,
                "project_name": safe_prod_name,
                "archived_at": now_iso,
                "source_machine": platform.node(),
                "scope": scope,
            }
            with open(manifest_file, "w", encoding="utf-8") as mf:
                json.dump(manifest_data, mf, indent=2, ensure_ascii=False)

            # If full scope requested, optionally archive raw & project folders
            if scope == "full":
                # Raw folder
                raw_prod_dir = root / "01_Raw" / safe_prod_name
                if raw_prod_dir.exists():
                    dest_raw_dir = product_archive_dir / "Sources" / "Raw"
                    shutil.copytree(raw_prod_dir, dest_raw_dir, dirs_exist_ok=True)
                    shutil.rmtree(raw_prod_dir)

                # Project folder
                proj_prod_dir = root / "03_Projects" / safe_prod_name
                if proj_prod_dir.exists():
                    dest_proj_dir = product_archive_dir / "Sources" / "Projects"
                    shutil.copytree(proj_prod_dir, dest_proj_dir, dirs_exist_ok=True)
                    shutil.rmtree(proj_prod_dir)

            # SAFE PRUNING: Only delete the local heavy video file now that Drive copy is verified
            local_video_path.unlink()
            reclaimed_bytes += file_size

            # Update export registry entry with cloud metadata (Smart Breadcrumbs)
            exp["cloud_status"] = "archived_gdrive"
            exp["cloud_path"] = str(dest_video_path).replace("\\", "/")
            exp["archived_at"] = now_iso
            exp["archived_size"] = file_size
            exp["archived_sha256"] = local_hash

            archived_records.append({
                "export_id": exp_id,
                "filename": local_video_path.name,
                "cloud_path": str(dest_video_path),
                "reclaimed_bytes": file_size,
                "delta_skipped": already_synced,
            })

            if progress_callback:
                progress_callback({
                    "stage": "item_completed",
                    "current_index": i + 1,
                    "total_items": total_targets,
                    "current_file": local_video_path.name,
                    "product_name": safe_prod_name,
                    "reclaimed_bytes": reclaimed_bytes,
                    "reclaimed_formatted": format_bytes(reclaimed_bytes),
                    "total_bytes": total_target_bytes,
                    "percent": round(((i + 1) / total_targets) * 100, 1),
                })

        # Atomic write back to export_registry.json
        tmp_export = export_file.with_suffix(".tmp")
        with open(tmp_export, "w", encoding="utf-8") as f:
            json.dump(exports, f, indent=2, ensure_ascii=False)
        tmp_export.replace(export_file)

        # Update post_log.json if exists
        if post_log_file.exists():
            try:
                with open(post_log_file, "r", encoding="utf-8") as f:
                    post_logs = json.load(f)
                archived_export_ids = {r["export_id"] for r in archived_records}
                for pl in post_logs:
                    clip_stem = Path(pl.get("clip_file") or "").stem
                    if clip_stem in archived_export_ids or pl.get("id") in archived_export_ids:
                        pl["cloud_archived"] = True
                        pl["archived_at"] = now_iso
                tmp_pl = post_log_file.with_suffix(".tmp")
                with open(tmp_pl, "w", encoding="utf-8") as f:
                    json.dump(post_logs, f, indent=2, ensure_ascii=False)
                tmp_pl.replace(post_log_file)
            except Exception:
                pass

        if progress_callback:
            progress_callback({
                "stage": "completed",
                "current_index": len(archived_records),
                "total_items": total_targets,
                "current_file": "",
                "product_name": "",
                "reclaimed_bytes": reclaimed_bytes,
                "reclaimed_formatted": format_bytes(reclaimed_bytes),
                "total_bytes": total_target_bytes,
                "percent": 100.0,
            })

        return {
            "status": "ok",
            "archived_count": len(archived_records),
            "reclaimed_bytes": reclaimed_bytes,
            "reclaimed_formatted": format_bytes(reclaimed_bytes),
            "records": archived_records,
            "gdrive_vault": str(archive_root),
        }

    @staticmethod
    def restore_clip(export_id: str, base_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Restore an archived video clip from Google Drive back to local storage."""
        root = base_dir or BASE_DIR
        docs_dir = root / "_Docs"
        export_file = docs_dir / "export_registry.json"

        if not export_file.exists():
            raise FileNotFoundError("ไม่พบ export_registry.json")

        with open(export_file, "r", encoding="utf-8") as f:
            exports = json.load(f)

        target_exp = None
        for exp in exports:
            if exp.get("id") == export_id:
                target_exp = exp
                break

        if not target_exp:
            raise KeyError(f"ไม่พบคลิป export_id '{export_id}'")

        cloud_path_str = target_exp.get("cloud_path")
        if not cloud_path_str:
            raise ValueError(f"คลิป '{export_id}' ไม่มีข้อมูล cloud_path")

        cloud_path = Path(cloud_path_str)
        if not cloud_path.exists():
            raise FileNotFoundError(f"ไม่พบไฟล์บน Google Drive: {cloud_path}")

        orig_rel_path = target_exp.get("path")
        dest_local_path = root / orig_rel_path
        dest_local_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(cloud_path, dest_local_path)

        # Update export entry
        target_exp["cloud_status"] = "restored_local"
        tmp_export = export_file.with_suffix(".tmp")
        with open(tmp_export, "w", encoding="utf-8") as f:
            json.dump(exports, f, indent=2, ensure_ascii=False)
        tmp_export.replace(export_file)

        return {
            "status": "ok",
            "export_id": export_id,
            "local_path": str(dest_local_path),
            "size_formatted": format_bytes(dest_local_path.stat().st_size),
        }

    @staticmethod
    def open_in_explorer(target_path: str) -> bool:
        """Reveal file or open directory in Windows File Explorer."""
        p = Path(target_path)
        if not p.exists():
            return False
        try:
            if p.is_file():
                subprocess.Popen(f'explorer /select,"{p}"')
            else:
                subprocess.Popen(f'explorer "{p}"')
            return True
        except Exception:
            return False
