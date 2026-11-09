"""SSD Reconcile Engine for OmniCut Pro Studio.

Agent 4: Two-Way Reconciliation & State Auditor
Synchronizes upload receipts and posted statuses from the External SSD
back into the Home Desktop PC's canonical databases, moves posted videos to 04_Exports/Posted/,
and handles SSD retention (Archive to Posted_Archive, Delete, or Keep).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from scripts import store_io
from scripts.config import BASE_DIR, EXPORTS_DIR

VAULT_DIR_NAME = "OmniCut_Portable_Vault"
POSTED_DIR = BASE_DIR / "04_Exports" / "Posted"
READY_DIR = BASE_DIR / "04_Exports" / "Ready_to_post"


class SSDReconcileEngine:
    """Reconciles upload state from External SSD into Home PC canonical stores."""

    @staticmethod
    def reconcile_from_vault(
        vault_root: Path,
        base_dir: Optional[Path] = None,
        clean_ssd_after: bool = False,
        retention_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read state from vault and reconcile into project canonical registries.

        Retention Modes:
        - 'archive': Move posted video files on SSD into OmniCut_Portable_Vault/Posted_Archive/ (Default)
        - 'delete': Delete posted video files from SSD to free up space (when clean_ssd_after=True)
        - 'keep': Leave posted video files in media/videos/
        """
        # Backwards compatibility with clean_ssd_after flag
        if retention_mode is None:
            retention_mode = "delete" if clean_ssd_after else "archive"

        project_root = base_dir or BASE_DIR
        docs_dir = project_root / "_Docs"
        exports_posted_dir = project_root / "04_Exports" / "Posted"
        exports_ready_dir = project_root / "04_Exports" / "Ready_to_post"

        exports_posted_dir.mkdir(parents=True, exist_ok=True)

        if vault_root.name != VAULT_DIR_NAME:
            vault_root = vault_root / VAULT_DIR_NAME

        if not vault_root.exists():
            return {
                "status": "error",
                "message": f"Vault not found at {vault_root}",
                "reconciled_count": 0,
            }

        state_file = vault_root / "state.json"
        queue_file = vault_root / "queue.json"

        if not state_file.exists():
            return {
                "status": "ok",
                "message": "No state.json found on SSD vault",
                "reconciled_count": 0,
            }

        with open(state_file, "r", encoding="utf-8") as f:
            vault_states = json.load(f)

        vault_queue = []
        if queue_file.exists():
            with open(queue_file, "r", encoding="utf-8") as f:
                vault_queue = json.load(f)

        queue_lookup = {q["id"]: q for q in vault_queue}

        # 1. Load Home PC registries
        # อ่านผ่าน store (อ่านพังต้อง raise ไม่กลายเป็น []) แล้วแก้บนสำเนา
        # จากนั้นเขียนกลับเฉพาะ field ที่เปลี่ยนผ่านทรานแซกชันของ store
        home_schedule = store_io.load_schedule_queue(docs_dir)
        home_exports = store_io.load_export_registry(docs_dir)
        home_post_log = store_io.load_posts(docs_dir)
        baseline_schedule = copy.deepcopy(home_schedule)
        baseline_exports = copy.deepcopy(home_exports)
        baseline_post_ids = {id(e) for e in home_post_log}

        existing_log_export_ids = {entry.get("export_id") for entry in home_post_log if entry.get("export_id")}

        reconciled_items = []
        already_posted_count = 0
        pending_items = []

        # 2. Reconcile posted items
        for item_id, state in vault_states.items():
            if state.get("status") != "posted":
                pending_items.append(item_id)
                continue

            q_info = queue_lookup.get(item_id, {})
            export_id = q_info.get("export_id")
            uploaded_at = state.get("uploaded_at") or datetime.now(timezone.utc).isoformat()
            post_url = state.get("post_url")
            platform_id = state.get("post_id")

            # Update schedule_queue.json
            matched_queue = False
            for sq in home_schedule:
                if sq.get("id") == item_id or (export_id and sq.get("export_id") == export_id):
                    if sq.get("status") == "posted":
                        already_posted_count += 1
                    else:
                        sq["status"] = "posted"
                        sq["posted_at"] = uploaded_at
                        if post_url:
                            sq["post_url"] = post_url
                        if platform_id:
                            sq["platform_id"] = platform_id
                    matched_queue = True

            # Update export_registry.json and move local file to Posted/
            for exp in home_exports:
                if exp.get("id") == export_id:
                    exp["status"] = "posted"
                    exp["posted_at"] = uploaded_at
                    if post_url:
                        exp["post_url"] = post_url

                    curr_path_str = exp.get("path", "")
                    if curr_path_str:
                        curr_file = project_root / curr_path_str
                        if curr_file.exists() and "Ready_to_post" in curr_path_str:
                            new_file = exports_posted_dir / curr_file.name
                            shutil.move(curr_file, new_file)
                            new_rel_path = f"04_Exports/Posted/{curr_file.name}"
                            exp["path"] = new_rel_path
                            exp["path_key"] = new_rel_path

                            # Also update schedule_queue video_path
                            for sq in home_schedule:
                                if sq.get("export_id") == export_id:
                                    sq["video_path"] = new_rel_path

            # Update post_log.json if not logged
            if export_id and export_id not in existing_log_export_ids:
                log_entry = {
                    "id": uuid.uuid4().hex,  # store rows ต้องมี id (PostLog ใช้ uuid4 hex)
                    "export_id": export_id,
                    "queue_id": item_id,
                    "product_id": q_info.get("product_id"),
                    "project_name": q_info.get("product_name"),
                    "posted_at": uploaded_at,
                    "post_url": post_url,
                    "platform_id": platform_id,
                    "platform": "tiktok",
                    "channel_id": q_info.get("channel_id", "main"),
                }
                home_post_log.append(log_entry)
                existing_log_export_ids.add(export_id)

            reconciled_items.append(item_id)

        # 3. Save Home PC registries through the stores (merge changed fields by id)
        store_io.apply_row_changes(store_io.SCHEDULE_QUEUE, baseline_schedule, home_schedule, docs_dir)
        store_io.apply_row_changes(store_io.EXPORT_REGISTRY, baseline_exports, home_exports, docs_dir)
        new_log_entries = [e for e in home_post_log if id(e) not in baseline_post_ids]
        if new_log_entries:
            with store_io.mutate_posts(docs_dir) as live_log:
                live_ids = {e.get("export_id") for e in live_log if e.get("export_id")}
                for entry in new_log_entries:
                    if entry.get("export_id") not in live_ids:
                        live_log.append(entry)

        # 4. Handle SSD Media Retention (Archive to Posted_Archive, Delete, or Keep)
        cleaned_media_count = 0
        archived_media_count = 0
        ssd_archive_dir = vault_root / "Posted_Archive"

        if retention_mode == "delete":
            for item_id in reconciled_items:
                q = queue_lookup.get(item_id)
                if q and q.get("video_rel_path"):
                    target_file = vault_root / q["video_rel_path"]
                    if target_file.exists():
                        target_file.unlink()
                        cleaned_media_count += 1
        elif retention_mode == "archive":
            ssd_archive_dir.mkdir(parents=True, exist_ok=True)
            for item_id in reconciled_items:
                q = queue_lookup.get(item_id)
                if q and q.get("video_rel_path"):
                    source_file = vault_root / q["video_rel_path"]
                    if source_file.exists() and source_file.parent != ssd_archive_dir:
                        dest_file = ssd_archive_dir / source_file.name
                        shutil.move(source_file, dest_file)
                        q["video_rel_path"] = f"Posted_Archive/{source_file.name}"
                        archived_media_count += 1

            # Update queue.json on SSD to reflect new paths
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(vault_queue, f, indent=2, ensure_ascii=False)

        return {
            "status": "ok",
            "reconciled_count": len(reconciled_items),
            "already_posted_count": already_posted_count,
            "cleaned_media_count": cleaned_media_count,
            "archived_media_count": archived_media_count,
            "pending_unposted_count": len(pending_items),
            "reconciled_item_ids": reconciled_items,
            "retention_mode": retention_mode,
        }
