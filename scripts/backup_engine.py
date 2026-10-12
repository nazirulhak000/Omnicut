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
import tempfile
import zipfile
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR
from scripts import maintenance_lock

BACKUP_DIR = BASE_DIR / "06_Archive" / "Backups"
DOCS_DIR = BASE_DIR / "_Docs"
PROJECTS_DIR = BASE_DIR / "03_Projects"

_BACKUP_LOCK = threading.Lock()


@contextmanager
def _snapshot_guard():
    """Block new durable writes and drain transactions before taking copies."""
    from scripts.project_manifest import ProjectManifest
    info = maintenance_lock.acquire(BASE_DIR, owner="BackupEngine", reason="consistent backup")
    try:
        for database in (DOCS_DIR / "store.db", PROJECTS_DIR / "batch_render_queue.db"):
            if database.exists():
                with sqlite3.connect(str(database), timeout=30) as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.rollback()
        with ProjectManifest._SAVE_LOCK:
            yield
    finally:
        maintenance_lock.release(BASE_DIR, info["token"])


class BackupEngine:
    """Engine for creating, listing, and verifying OmniCut system backups."""

    @classmethod
    def _hyperframes_snapshot_state(cls):
        """Fence background workers that are not stopped by HTTP maintenance."""
        state = {}
        database = DOCS_DIR / "store.db"
        encode = lambda values: json.dumps(sorted(values, key=lambda row: row["id"]), sort_keys=True, ensure_ascii=False)
        for table in ("creative_jobs", "hyperframes_render_jobs", "export_cover_bindings"):
            mirror = DOCS_DIR / f"{table}.json"
            raw = mirror.read_bytes() if mirror.exists() else None
            rows = json.loads(raw.decode("utf-8-sig")) if raw is not None else []
            if not isinstance(rows, list):
                raise ValueError("HyperFrames job mirror must be a list")
            state[table] = hashlib.sha256(raw).hexdigest() if raw is not None else None
            state[table + ":rows"] = hashlib.sha256(encode(rows).encode("utf-8")).hexdigest()
            if database.exists():
                from scripts.channel_migration import ro_connect
                with ro_connect(database) as connection:
                    exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                    if exists:
                        canonical = [json.loads(row[0]) for row in connection.execute(f"SELECT data FROM {table}")]
                        if encode(canonical) != encode(rows):
                            raise ValueError("HyperFrames SQLite and JSON job records disagree")
        from scripts.export_cover_bindings import ExportCoverBindingStore
        bindings = ExportCoverBindingStore(BASE_DIR)
        covers = {}
        for row in bindings._rows("export_cover_bindings"):
            if not isinstance(row, dict) or not isinstance(row.get("selections"), dict):
                raise ValueError("Explicit export cover binding is malformed")
            for format in row["selections"]:
                try:
                    selection = bindings.get(row.get("channel_id"), row.get("export_id"), format=format)
                except Exception as error:
                    raise ValueError("Explicit selected export cover is missing, changed or unmanaged") from error
                if selection is None:
                    raise ValueError("Explicit selected export cover cannot be resolved")
                covers[selection["path"]] = selection["sha256"]
        state["selected_export_covers"] = covers
        return state

    @classmethod
    def _hyperframes_review_files(cls):
        """Capture exact managed review inputs, never arbitrary temporary caches."""
        metadata = DOCS_DIR / "hyperframes_render_jobs.json"
        jobs = json.loads(metadata.read_text(encoding="utf-8-sig")) if metadata.exists() else []
        if not isinstance(jobs, list):
            raise ValueError("HyperFrames render job mirror must be a list")
        database = DOCS_DIR / "store.db"
        if database.exists():
            from scripts.channel_migration import ro_connect
            with ro_connect(database) as connection:
                exists = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='hyperframes_render_jobs'").fetchone()
                if exists:
                    canonical = [json.loads(row[0]) for row in connection.execute("SELECT data FROM hyperframes_render_jobs")]
                    encode = lambda rows: json.dumps(sorted(rows, key=lambda row: row["id"]), sort_keys=True, ensure_ascii=False)
                    if encode(canonical) != encode(jobs):
                        raise ValueError("HyperFrames SQLite and JSON render job records disagree")
        root = BASE_DIR.resolve()
        found = {}

        def verified(raw, digest, allowed):
            if not isinstance(raw, str) or not raw or not isinstance(digest, str) or len(digest) != 64:
                raise ValueError("HyperFrames review artifact needs an exact path and hash")
            candidate = Path(raw)
            candidate = candidate if candidate.is_absolute() else root / candidate
            if ".." in candidate.parts or not candidate.is_relative_to(root):
                raise ValueError("HyperFrames backup artifact escapes root")
            for component in (candidate, *candidate.parents):
                if component == root:
                    break
                if component.is_symlink() or getattr(component, "is_junction", lambda: False)():
                    raise ValueError("HyperFrames backup artifact has a filesystem alias")
            source = candidate.resolve()
            relative = source.relative_to(root)
            if not allowed(relative) or not source.is_file() or cls._compute_sha256(source) != digest:
                raise ValueError("HyperFrames referenced review artifact is missing, changed or unmanaged")
            found[relative.as_posix()] = source

        for job in jobs:
            if job.get("status") not in {"qc_ready", "finalizing", "recovery_required"}:
                continue
            artifact = job.get("artifact") or {}
            intent = job.get("finalize_intent") or {}
            job_id, attempt = job.get("id"), job.get("attempt")
            if not isinstance(job_id, str) or Path(job_id).name != job_id or not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
                raise ValueError("HyperFrames reviewed job has no managed attempt identity")
            prefix = (".tmp", "hyperframes", "render", job_id, str(attempt))
            managed = lambda relative: relative.parts[:5] == prefix and len(relative.parts) == 6
            verified(artifact.get("path"), artifact.get("sha256"), managed)
            verified(artifact.get("thumbnail_path"), artifact.get("thumbnail_sha256"), managed)
            if intent.get("cover_source"):
                verified(intent["cover_source"], (intent.get("package") or {}).get("cover_sha256"),
                         lambda relative: relative.parts[0] in {"02_Assets", "05_Covers_Thumbnails"})
        return found

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
        with _BACKUP_LOCK, _snapshot_guard():
            target_dir = cls.get_backup_dir(backup_dir)
            now = datetime.datetime.now()
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            zip_filename = f"{custom_name_prefix}_{timestamp_str}.zip"
            zip_path = target_dir / zip_filename
            temp_zip_path = target_dir / f".tmp_{zip_filename}"

            included_files: List[str] = []
            snapshot_files: List[Dict[str, Any]] = []
            total_uncompressed_bytes = 0
            hf_snapshot_state = cls._hyperframes_snapshot_state() if include_docs else None

            def include_file(archive, source, arcname, *, kind="file"):
                if arcname in included_files:
                    return
                archive.write(source, arcname=arcname)
                included_files.append(arcname)
                entry = {"rel": arcname, "kind": kind, "sha256": cls._compute_sha256(source), "size": source.stat().st_size}
                if source.name.endswith(".json.publish-pending"):
                    entry["mirror_intent"] = json.loads(source.read_text(encoding="utf-8"))
                if kind == "sqlite":
                    from scripts import channel_migration as cm
                    with cm.ro_connect(source) as connection:
                        entry["all_tables"] = cm.sqlite_contents_digest(connection)
                        entry["tables"] = {spec.table: cm._table_digest(rows) for spec in cm.RECOVERY_TABLES
                                           if (rows := cm._read_rows(connection, spec.table)) is not None}
                        if hf_snapshot_state is not None and arcname == "_Docs/store.db":
                            for table in ("creative_jobs", "hyperframes_render_jobs", "export_cover_bindings"):
                                rows = cm._read_rows(connection, table) or []
                                encoded = json.dumps(sorted(rows, key=lambda row: row["id"]), sort_keys=True, ensure_ascii=False).encode("utf-8")
                                if hashlib.sha256(encoded).hexdigest() != hf_snapshot_state[table + ":rows"]:
                                    raise ValueError("HyperFrames or explicit cover records changed during backup")
                snapshot_files.append(entry)

            try:
                with zipfile.ZipFile(
                    temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
                ) as zf:
                    # 1. Backup _Docs files
                    if include_docs and DOCS_DIR.exists():
                        for item in DOCS_DIR.rglob("*"):
                            if item.is_file():
                                if item.suffix.lower() == ".json" or item.name.endswith(".json.publish-pending"):
                                    arcname = f"_Docs/{item.relative_to(DOCS_DIR).as_posix()}"
                                    include_file(zf, item, arcname)
                                    total_uncompressed_bytes += item.stat().st_size
                                elif item.name == "store.db":
                                    # Use safe SQLite backup API to avoid locked database issues
                                    temp_sqlite_copy = target_dir / f".tmp_store_{timestamp_str}.db"
                                    try:
                                        cls._backup_sqlite_database(item, temp_sqlite_copy)
                                        arcname = "_Docs/store.db"
                                        include_file(zf, temp_sqlite_copy, arcname, kind="sqlite")
                                        total_uncompressed_bytes += temp_sqlite_copy.stat().st_size
                                    finally:
                                        try:
                                            temp_sqlite_copy.unlink()
                                        except OSError:
                                            pass
                                elif "producer" in item.relative_to(DOCS_DIR).parts:
                                    # Uploaded reference media are inputs to saved notes.
                                    include_file(zf, item, f"_Docs/{item.relative_to(DOCS_DIR).as_posix()}")
                                    total_uncompressed_bytes += item.stat().st_size

                    # 2. Backup 03_Projects files
                    if include_projects and PROJECTS_DIR.exists():
                        for root, _, files in os.walk(PROJECTS_DIR):
                            rel_root = Path(root).relative_to(BASE_DIR)
                            for file in files:
                                file_path = Path(root) / file
                                # Skip lock files and temporary cache files
                                sealed_hf_revision = rel_root.parts[:3] == ("03_Projects", "_HyperFrames_Studio", "revisions")
                                if file.startswith(".") and not file.startswith(".token_analytics") and not sealed_hf_revision:
                                    continue
                                if file.endswith(".tmp") or file.endswith(".lock"):
                                    continue
                                if file.endswith((".db-wal", ".db-shm", ".db-journal")):
                                    continue

                                arcname = f"{rel_root.as_posix()}/{file}"
                                if file.endswith(".db"):
                                    with tempfile.TemporaryDirectory(prefix="omnicut-backup-db-") as staging:
                                        db_copy = Path(staging) / file
                                        cls._backup_sqlite_database(file_path, db_copy)
                                        include_file(zf, db_copy, arcname, kind="sqlite")
                                        total_uncompressed_bytes += db_copy.stat().st_size
                                else:
                                    include_file(zf, file_path, arcname)
                                    total_uncompressed_bytes += file_path.stat().st_size

                    if include_docs:
                        for relative in hf_snapshot_state["selected_export_covers"]:
                            source = BASE_DIR / relative
                            newly_included = relative not in included_files
                            include_file(zf, source, relative)
                            if newly_included:
                                total_uncompressed_bytes += source.stat().st_size
                        for arcname, source in cls._hyperframes_review_files().items():
                            if arcname not in included_files:
                                include_file(zf, source, arcname)
                                total_uncompressed_bytes += source.stat().st_size
                        refs = BASE_DIR / "02_Assets" / "Refs"
                        if refs.is_dir():
                            for source in refs.rglob("*"):
                                if source.is_file():
                                    include_file(zf, source, source.relative_to(BASE_DIR).as_posix())
                                    total_uncompressed_bytes += source.stat().st_size
                        # Keep registered exports and covers available after
                        # relocation, without copying the complete Raw vault.
                        def referenced_paths(value):
                            if isinstance(value, dict):
                                for key, child in value.items():
                                    if isinstance(child, str) and child.strip() and (key == "path" or key.endswith("_path")):
                                        yield child
                                    yield from referenced_paths(child)
                            elif isinstance(value, list):
                                for child in value:
                                    yield from referenced_paths(child)

                        for metadata in DOCS_DIR.rglob("*.json"):
                            for raw_path in referenced_paths(json.loads(metadata.read_text(encoding="utf-8-sig"))):
                                source = (BASE_DIR / raw_path).resolve()
                                if not source.is_relative_to(BASE_DIR.resolve()):
                                    continue
                                relative = source.relative_to(BASE_DIR.resolve())
                                if relative.parts and relative.parts[0] in {"04_Exports", "05_Covers_Thumbnails"} and source.is_file():
                                    arcname = relative.as_posix()
                                    if arcname not in included_files:
                                        include_file(zf, source, arcname)
                                        total_uncompressed_bytes += source.stat().st_size

                    # 3. Write internal backup manifest
                    # Registry avatars are identity inputs; include only the
                    # referenced local files, never copy the entire Raw vault.
                    registry = DOCS_DIR / "channels.json"
                    if include_docs and registry.is_file():
                        channels = json.loads(registry.read_text(encoding="utf-8")).get("channels", [])
                        for channel in channels:
                            avatar = channel.get("avatar") or {}
                            raw_path = avatar.get("path") or channel.get("avatar_asset_path")
                            if not raw_path:
                                continue
                            avatar_path = (BASE_DIR / raw_path).resolve()
                            if not avatar_path.is_relative_to(BASE_DIR.resolve()):
                                raise ValueError("Channel avatar outside backup root")
                            if avatar_path.is_file():
                                arcname = avatar_path.relative_to(BASE_DIR).as_posix()
                                if arcname not in included_files:
                                    include_file(zf, avatar_path, arcname)
                                    total_uncompressed_bytes += avatar_path.stat().st_size
                    manifest_data = {
                        "backup_name": zip_filename,
                        "created_at": now.isoformat(timespec="seconds"),
                        "file_count": len(included_files),
                        "total_uncompressed_bytes": total_uncompressed_bytes,
                        "version": "1.0",
                        "files": included_files,
                        "mirror_intents_require_rebind_on_relocation": True,
                        "snapshot": {"schema": 1, "migration": "multi_channel_v1", "source_root": str(BASE_DIR), "files": snapshot_files},
                    }
                    manifest_json = json.dumps(manifest_data, ensure_ascii=False, indent=2)
                    zf.writestr("backup_manifest.json", manifest_json)

                if include_docs:
                    # Reopen after closing the writer: Windows ZipInfo keeps
                    # its original backslash spelling until the directory is read.
                    with zipfile.ZipFile(temp_zip_path, "r") as verified_zip:
                        for table in ("creative_jobs", "hyperframes_render_jobs", "export_cover_bindings"):
                            expected_hash = hf_snapshot_state[table]
                            if expected_hash and hashlib.sha256(verified_zip.read(f"_Docs/{table}.json")).hexdigest() != expected_hash:
                                raise ValueError("HyperFrames or explicit cover mirror changed during backup")
                        for relative, expected_hash in hf_snapshot_state["selected_export_covers"].items():
                            if hashlib.sha256(verified_zip.read(relative)).hexdigest() != expected_hash:
                                raise ValueError("Explicit selected export cover changed during backup")
                if include_docs and cls._hyperframes_snapshot_state() != hf_snapshot_state:
                    raise ValueError("HyperFrames background jobs changed during backup; retry after workers settle")

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
                if manifest and manifest.get("snapshot"):
                    entries = manifest["snapshot"]["files"]
                    declared = [entry["rel"] for entry in entries]
                    if len(set(declared)) != len(declared) or sorted(zf.namelist()) != sorted([*declared, "backup_manifest.json"]):
                        return {"is_valid": False, "backup_name": filename, "error": "Duplicate or undeclared backup files"}
                    for entry in entries:
                        if hashlib.sha256(zf.read(entry["rel"])).hexdigest() != entry["sha256"]:
                            return {"is_valid": False, "backup_name": filename, "error": f"Checksum mismatch: {entry['rel']}"}

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

    @classmethod
    def restore_backup(cls, filename: str, target_root: Path, backup_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Restore and verify an archive into a new, empty data root.

        This is a relocation/rehearsal API. It never overwrites an existing
        workspace, and validates every checksum and intent before writing it.
        """
        from scripts import channel_migration as cm
        target_root = Path(target_root).resolve()
        if target_root == BASE_DIR.resolve() or target_root.is_relative_to(BASE_DIR.resolve()):
            raise ValueError("Restore target must be outside the active data root")
        if target_root.exists() and any(target_root.iterdir()):
            raise ValueError("Restore target must be empty")
        archive_path = cls.resolve_safe_path(filename, backup_dir)
        with _BACKUP_LOCK, tempfile.TemporaryDirectory(prefix="omnicut-restore-") as workdir:
            staging = Path(workdir)
            with zipfile.ZipFile(archive_path, "r") as archive:
                metadata = json.loads(archive.read("backup_manifest.json"))
                snapshot = metadata.get("snapshot")
                if not snapshot:
                    raise ValueError("Legacy backup has no verified restore manifest")
                manifest_path = staging / "manifest.json"
                manifest_path.write_text(json.dumps(snapshot), encoding="utf-8")
                manifest = cm._load_manifest(manifest_path)
                declared = [entry["rel"] for entry in manifest["files"]]
                if len(set(declared)) != len(declared) or sorted(archive.namelist()) != sorted([*declared, "backup_manifest.json"]):
                    raise ValueError("Backup contains duplicate or undeclared files")
                for entry in manifest["files"]:
                    data = archive.read(entry["rel"])
                    if cm.sha256_bytes(data) != entry["sha256"]:
                        raise ValueError(f"Backup checksum mismatch: {entry['rel']}")
                    cm.atomic_write_bytes(staging / entry["rel"], data, allowed_roots=[staging])
            result = cm.restore_snapshot(manifest_path, target_root)
            verdict = cm.verify_restore(manifest_path, target_root)
            if not verdict["ok"]:
                raise cm.ValidationFailed(verdict["problems"])
            return {**result, **verdict, "backup_name": filename}

    @staticmethod
    def _compute_sha256(path: Path) -> str:
        """Computes SHA-256 checksum of a file efficiently in chunks."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
