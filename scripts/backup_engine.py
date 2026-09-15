"""BackupEngine — One-Click System Backup for OmniCut Pro Studio.

Creates and manages standalone zip archives containing:
1. All database & metadata JSONs in `_Docs/` (products, post_log, schedule_queue, etc.)
2. SQLite database `_Docs/store.db` (if exists, backed up safely)
3. Full project configurations & scripts in `03_Projects/` (project.json, briefs, subtitles, manifests)

Archives are saved under `06_Archive/Backups/` with automated integrity checks.
Safe path containment prevents directory traversal.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import threading
import zipfile
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR

BACKUP_DIR = BASE_DIR / "06_Archive" / "Backups"
DOCS_DIR = BASE_DIR / "_Docs"
PROJECTS_DIR = BASE_DIR / "03_Projects"

_BACKUP_LOCK = threading.Lock()


class BackupEngine:
    """Engine for creating, listing, and verifying OmniCut system backups."""

    @staticmethod
    def _backup_sqlite_database(source_path: Path, destination_path: Path) -> None:
        """Create a consistent SQLite copy, including pages held in WAL.

        A raw ``copy2(store.db)`` is not a valid fallback for a WAL database:
        committed pages may still live in ``store.db-wal``.  If SQLite's
        backup API cannot produce a copy, fail the backup instead of emitting
        an archive that silently loses data.
        """
        source_conn: Optional[sqlite3.Connection] = None
        destination_conn: Optional[sqlite3.Connection] = None
        try:
            source_conn = sqlite3.connect(
                f"file:{source_path.resolve()}?mode=ro", uri=True, timeout=5
            )
            destination_conn = sqlite3.connect(str(destination_path), timeout=5)
            with destination_conn:
                source_conn.backup(destination_conn)
                integrity = destination_conn.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise sqlite3.DatabaseError(
                    f"SQLite integrity check failed: {integrity[0] if integrity else 'no result'}"
                )
        except Exception:
            if destination_path.exists():
                try:
                    destination_path.unlink()
                except OSError:
                    pass
            raise
        finally:
            if source_conn is not None:
                source_conn.close()
            if destination_conn is not None:
                destination_conn.close()

    @classmethod
    def get_backup_dir(cls, custom_dir: Optional[Path] = None) -> Path:
        """Returns the resolved backup directory, creating it if needed."""
        target = custom_dir or BACKUP_DIR
        target.mkdir(parents=True, exist_ok=True)
        return target

    @classmethod
    def resolve_safe_path(cls, filename: str, backup_dir: Optional[Path] = None) -> Path:
        """Resolves filename within backup_dir, strictly preventing path traversal."""
        b_dir = cls.get_backup_dir(backup_dir).resolve()
        clean_name = Path(filename).name
        if not clean_name or clean_name != filename or ".." in filename:
            raise ValueError(f"Invalid backup filename: '{filename}'")
        resolved = (b_dir / clean_name).resolve()
        if not resolved.is_relative_to(b_dir):
            raise ValueError(f"Path traversal detected: '{filename}'")
        return resolved

    @classmethod
    def create_backup(
        cls,
        backup_dir: Optional[Path] = None,
        include_projects: bool = True,
        include_docs: bool = True,
        custom_name_prefix: str = "omnicut_backup",
    ) -> Dict[str, Any]:
        """Creates a timestamped zip archive of system state."""
        with _BACKUP_LOCK:
            target_dir = cls.get_backup_dir(backup_dir)
            now = datetime.datetime.now()
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            zip_filename = f"{custom_name_prefix}_{timestamp_str}.zip"
            zip_path = target_dir / zip_filename
            temp_zip_path = target_dir / f".tmp_{zip_filename}"

            included_files: List[str] = []
            total_uncompressed_bytes = 0

            try:
                with zipfile.ZipFile(
                    temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
                ) as zf:
                    # 1. Backup _Docs files
                    if include_docs and DOCS_DIR.exists():
                        for item in DOCS_DIR.iterdir():
                            if item.is_file():
                                if item.suffix.lower() == ".json":
                                    arcname = f"_Docs/{item.name}"
                                    zf.write(item, arcname=arcname)
                                    included_files.append(arcname)
                                    total_uncompressed_bytes += item.stat().st_size
                                elif item.name == "store.db":
                                    # Use safe SQLite backup API to avoid locked database issues
                                    temp_sqlite_copy = target_dir / f".tmp_store_{timestamp_str}.db"
                                    try:
                                        cls._backup_sqlite_database(item, temp_sqlite_copy)
                                        arcname = "_Docs/store.db"
                                        zf.write(temp_sqlite_copy, arcname=arcname)
                                        included_files.append(arcname)
                                        total_uncompressed_bytes += temp_sqlite_copy.stat().st_size
                                    finally:
                                        try:
                                            temp_sqlite_copy.unlink()
                                        except OSError:
                                            pass

                    # 2. Backup 03_Projects files
                    if include_projects and PROJECTS_DIR.exists():
                        for root, _, files in os.walk(PROJECTS_DIR):
                            rel_root = Path(root).relative_to(BASE_DIR)
                            for file in files:
                                file_path = Path(root) / file
                                # Skip lock files and temporary cache files
                                if file.startswith(".") and not file.startswith(".token_analytics"):
                                    continue
                                if file.endswith(".tmp") or file.endswith(".lock"):
                                    continue

                                arcname = f"{rel_root.as_posix()}/{file}"
                                zf.write(file_path, arcname=arcname)
                                included_files.append(arcname)
                                total_uncompressed_bytes += file_path.stat().st_size

                    # 3. Write internal backup manifest
                    manifest_data = {
                        "backup_name": zip_filename,
                        "created_at": now.isoformat(timespec="seconds"),
                        "file_count": len(included_files),
                        "total_uncompressed_bytes": total_uncompressed_bytes,
                        "version": "1.0",
                        "files": included_files,
                    }
                    manifest_json = json.dumps(manifest_data, ensure_ascii=False, indent=2)
                    zf.writestr("backup_manifest.json", manifest_json)

                # Atomically move temp zip to destination
                if zip_path.exists():
                    zip_path.unlink()
                temp_zip_path.replace(zip_path)

            except Exception:
                if temp_zip_path.exists():
                    try:
                        temp_zip_path.unlink()
                    except OSError:
                        pass
                raise

            # Compute SHA-256 checksum and final stats
            file_size_bytes = zip_path.stat().st_size
            sha256 = cls._compute_sha256(zip_path)

            return {
                "backup_name": zip_filename,
                "file_path": str(zip_path),
                "size_bytes": file_size_bytes,
                "size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "uncompressed_bytes": total_uncompressed_bytes,
                "uncompressed_mb": round(total_uncompressed_bytes / (1024 * 1024), 2),
                "file_count": len(included_files),
                "created_at": now.isoformat(timespec="seconds"),
                "sha256": sha256,
            }

    @classmethod
    def list_backups(cls, backup_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Lists all existing backup archives sorted newest to oldest."""
        target_dir = cls.get_backup_dir(backup_dir)
        backups = []

        for p in target_dir.glob("*.zip"):
            if p.name.startswith(".tmp"):
                continue
            stat = p.stat()
            created_at = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
            backup_info: Dict[str, Any] = {
                "backup_name": p.name,
                "file_path": str(p),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": created_at,
                "is_valid": True,
            }

            # Best-effort reading manifest inside zip without full decompression
            try:
                with zipfile.ZipFile(p, "r") as zf:
                    if "backup_manifest.json" in zf.namelist():
                        raw = zf.read("backup_manifest.json")
                        meta = json.loads(raw.decode("utf-8"))
                        backup_info["file_count"] = meta.get("file_count", len(zf.namelist()))
                        backup_info["uncompressed_mb"] = meta.get("uncompressed_mb")
                        if meta.get("created_at"):
                            backup_info["created_at"] = meta["created_at"]
                    else:
                        backup_info["file_count"] = len(zf.namelist())
            except Exception:
                backup_info["is_valid"] = False
                backup_info["file_count"] = 0

            backups.append(backup_info)

        # Sort newest first
        backups.sort(key=lambda b: b.get("created_at", ""), reverse=True)
        return backups

    @classmethod
    def verify_backup(cls, filename: str, backup_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Tests the zip file integrity and reads its manifest."""
        zip_path = cls.resolve_safe_path(filename, backup_dir)
        if not zip_path.exists():
            raise FileNotFoundError(f"Backup file not found: '{filename}'")

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                bad_file = zf.testzip()
                if bad_file:
                    return {
                        "is_valid": False,
                        "error": f"Corrupted file in archive: {bad_file}",
                        "backup_name": filename,
                    }

                manifest = None
                if "backup_manifest.json" in zf.namelist():
                    raw = zf.read("backup_manifest.json")
                    manifest = json.loads(raw.decode("utf-8"))

                return {
                    "is_valid": True,
                    "backup_name": filename,
                    "file_count": len(zf.namelist()) - (1 if manifest else 0),
                    "manifest": manifest,
                }
        except zipfile.BadZipFile as e:
            return {
                "is_valid": False,
                "error": f"Bad zip archive: {e}",
                "backup_name": filename,
            }

    @classmethod
    def delete_backup(cls, filename: str, backup_dir: Optional[Path] = None) -> bool:
        """Safely deletes an existing backup archive."""
        with _BACKUP_LOCK:
            zip_path = cls.resolve_safe_path(filename, backup_dir)
            if zip_path.exists() and zip_path.is_file():
                zip_path.unlink()
                return True
            return False

    @staticmethod
    def _compute_sha256(path: Path) -> str:
        """Computes SHA-256 checksum of a file efficiently in chunks."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
