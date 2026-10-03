"""Validate an OmniCut ZIP backup by safe extraction into temporary storage.

The tool does not modify the archive or restore into the live project. It
checks ZIP CRCs, manifest membership, JSON payloads, and an included SQLite DB.
"""
from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


DEFAULT_TEMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"


def _safe_member_name(name: str) -> PurePosixPath:
    if "\\" in name or "\x00" in name:
        raise ValueError(f"Unsafe archive path: {name!r}")
    relative = PurePosixPath(name)
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"Unsafe archive path: {name!r}")
    if ":" in relative.parts[0]:
        raise ValueError(f"Drive-qualified archive path: {name!r}")
    return relative


def _validate_json_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path in root.rglob("*.json"):
        if path.name == "backup_manifest.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(root).as_posix()}: {exc}")
    return errors


def _sqlite_integrity(path: Path) -> str:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0]) if row else "no result"
    finally:
        connection.close()


def dry_run_backup(archive: Path, *, temp_root: Path | None = None,
                   max_uncompressed_bytes: int = 8 * 1024**3,
                   max_files: int = 50_000) -> dict[str, Any]:
    """Check and unpack one archive into disposable temp storage, then inspect it."""
    archive = archive.expanduser().resolve(strict=False)
    report: dict[str, Any] = {"schema_version": "backup-restore-dry-run.v1", "archive": str(archive),
                              "live_project_modified": False, "status": "invalid", "checks": []}
    if not archive.is_file():
        report["checks"].append({"code": "archive_missing", "status": "fail", "message": "ไม่พบไฟล์ backup"})
        return report
    try:
        total_bytes = 0
        with zipfile.ZipFile(archive, "r") as source:
            infos = source.infolist()
            if len(infos) > max_files:
                raise ValueError(f"Archive has too many entries ({len(infos)} > {max_files})")
            safe_names: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
            seen: set[str] = set()
            for info in infos:
                relative = _safe_member_name(info.filename.rstrip("/")) if not info.is_dir() else _safe_member_name(info.filename.rstrip("/"))
                key = relative.as_posix().casefold()
                if key in seen:
                    raise ValueError(f"Duplicate archive entry: {info.filename}")
                seen.add(key)
                unix_mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(unix_mode):
                    raise ValueError(f"Symbolic link entry is not allowed: {info.filename}")
                total_bytes += info.file_size
                if total_bytes > max_uncompressed_bytes:
                    raise ValueError(f"Archive expansion limit exceeded ({max_uncompressed_bytes} bytes)")
                safe_names.append((info, relative))
            bad_member = source.testzip()
            if bad_member:
                raise ValueError(f"ZIP CRC failed for {bad_member}")
            manifest_info = next((info for info, rel in safe_names if rel.as_posix() == "backup_manifest.json"), None)
            if manifest_info is None:
                raise ValueError("backup_manifest.json is missing")
            manifest = json.loads(source.read(manifest_info).decode("utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("Backup manifest must be a JSON object")
            listed = manifest.get("files")
            if not isinstance(listed, list) or not all(isinstance(item, str) for item in listed):
                raise ValueError("Backup manifest has no valid files list")
            for item in listed:
                _safe_member_name(item)
            actual_files = {relative.as_posix() for info, relative in safe_names
                            if not info.is_dir() and relative.as_posix() != "backup_manifest.json"}
            listed_files = set(listed)
            if actual_files != listed_files:
                missing = sorted(listed_files - actual_files)[:30]
                extra = sorted(actual_files - listed_files)[:30]
                raise ValueError(f"Manifest/archive mismatch; missing={missing}; extra={extra}")
            file_count = manifest.get("file_count")
            if isinstance(file_count, bool) or not isinstance(file_count, int) or file_count != len(listed_files):
                raise ValueError("Manifest file_count must be an integer matching listed files")

            temp_parent = (temp_root or DEFAULT_TEMP_ROOT).expanduser().resolve(strict=False)
            temp_parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="backup_restore_dry_run_", dir=temp_parent) as temp_name:
                extraction_root = Path(temp_name).resolve()
                extracted_bytes = 0
                for info, relative in safe_names:
                    target = (extraction_root / Path(*relative.parts)).resolve(strict=False)
                    if target != extraction_root and extraction_root not in target.parents:
                        raise ValueError(f"Extraction escaped temp directory: {info.filename}")
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(info, "r") as src, target.open("xb") as dst:
                        while True:
                            chunk = src.read(1024 * 1024)
                            if not chunk:
                                break
                            extracted_bytes += len(chunk)
                            if extracted_bytes > max_uncompressed_bytes:
                                raise ValueError("Actual extracted bytes exceeded the configured limit")
                            dst.write(chunk)
                json_errors = _validate_json_files(extraction_root)
                if json_errors:
                    raise ValueError("Invalid JSON payloads: " + "; ".join(json_errors[:20]))
                db_path = extraction_root / "_Docs" / "store.db"
                sqlite_result = _sqlite_integrity(db_path) if db_path.is_file() else None
                if sqlite_result not in (None, "ok"):
                    raise ValueError(f"SQLite integrity check failed: {sqlite_result}")
                report["checks"].extend([
                    {"code": "zip_crc", "status": "pass", "message": "ZIP members ผ่าน CRC"},
                    {"code": "manifest_membership", "status": "pass", "file_count": len(listed_files)},
                    {"code": "json_payloads", "status": "pass", "message": "JSON ที่รวมมา parse ได้"},
                    {"code": "sqlite_integrity", "status": "pass" if sqlite_result else "not_included", "result": sqlite_result},
                    {"code": "temporary_unpack", "status": "pass", "extracted_bytes": extracted_bytes,
                     "cleaned_after_check": True},
                ])
                report["manifest"] = {"created_at": manifest.get("created_at"), "version": manifest.get("version"),
                                       "file_count": len(listed_files), "total_uncompressed_bytes": total_bytes}
                report["status"] = "validated_archive_contents"
                report["limitations"] = [
                    "ไม่ได้ restore ทับโปรเจกต์จริง",
                    "backup ปัจจุบันรวม _Docs JSON/SQLite และ 03_Projects; ไม่รวมสื่อใน 01_Raw/02_Assets หรือ model cache",
                    "ผลนี้ยืนยันความสมบูรณ์ของเนื้อหาใน archive ไม่ได้รับประกันว่า media ภายนอกทั้งหมดพร้อมบนเครื่องใหม่",
                ]
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile,
            zipfile.LargeZipFile, sqlite3.DatabaseError, RuntimeError) as exc:
        report["checks"].append({"code": "dry_run_failed", "status": "fail", "message": str(exc)[:2000]})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--temp-root", type=Path, default=DEFAULT_TEMP_ROOT)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    default_output = Path(__file__).resolve().parents[1] / ".tmp" / f"backup_restore_dry_run_{stamp}.json"
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--max-uncompressed-mb", type=int, default=8192)
    parser.add_argument("--max-files", type=int, default=50_000)
    args = parser.parse_args(argv)
    output_path = args.output.expanduser().resolve(strict=False)
    if output_path == args.archive.expanduser().resolve(strict=False):
        parser.error("report output must not overwrite the backup archive")
    if output_path.exists():
        parser.error("report output already exists; choose a new path to avoid overwriting it")
    report = dry_run_backup(args.archive, temp_root=args.temp_root,
                             max_uncompressed_bytes=max(1, args.max_uncompressed_mb) * 1024**2,
                             max_files=max(1, args.max_files))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(args.output),
                      "live_project_modified": report["live_project_modified"]}, ensure_ascii=True))
    return 0 if report["status"] == "validated_archive_contents" else 2


if __name__ == "__main__":
    raise SystemExit(main())
