from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from tools.backup_restore_dry_run import dry_run_backup


def _make_backup(path: Path, *, include_db: bool = True, manifest_files: list[str] | None = None):
    files: dict[str, bytes] = {"_Docs/products.json": b"[]", "03_Projects/demo/project.json": b"{\"name\":\"demo\"}"}
    if include_db:
        db = path.parent / "store.db"
        connection = sqlite3.connect(db)
        connection.execute("CREATE TABLE sample (value TEXT)")
        connection.execute("INSERT INTO sample VALUES ('ok')")
        connection.commit()
        connection.close()
        files["_Docs/store.db"] = db.read_bytes()
    listed = manifest_files if manifest_files is not None else sorted(files)
    manifest = {"version": "1.0", "created_at": "2026-09-29T00:00:00",
                "file_count": len(listed), "total_uncompressed_bytes": sum(map(len, files.values())), "files": listed}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr("backup_manifest.json", json.dumps(manifest))
    return files


def test_valid_backup_contents_are_checked_in_temp_and_cleaned(tmp_path):
    archive = tmp_path / "backup.zip"
    _make_backup(archive)
    temp_root = tmp_path / "scratch"

    report = dry_run_backup(archive, temp_root=temp_root)

    assert report["status"] == "validated_archive_contents"
    assert report["live_project_modified"] is False
    assert any(check["code"] == "sqlite_integrity" and check["result"] == "ok" for check in report["checks"])
    assert list(temp_root.iterdir()) == []


def test_manifest_mismatch_is_rejected(tmp_path):
    archive = tmp_path / "mismatch.zip"
    _make_backup(archive, include_db=False, manifest_files=["_Docs/missing.json"])

    report = dry_run_backup(archive, temp_root=tmp_path / "scratch")

    assert report["status"] == "invalid"
    assert report["checks"][0]["code"] == "dry_run_failed"
    assert "Manifest/archive mismatch" in report["checks"][0]["message"]


def test_path_traversal_member_is_rejected_before_extraction(tmp_path):
    archive = tmp_path / "unsafe.zip"
    manifest = {"version": "1.0", "file_count": 1, "files": ["../escape.json"]}
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../escape.json", b"{}")
        output.writestr("backup_manifest.json", json.dumps(manifest))
    scratch = tmp_path / "scratch"

    report = dry_run_backup(archive, temp_root=scratch)

    assert report["status"] == "invalid"
    assert "Unsafe archive path" in report["checks"][0]["message"]
    assert not (tmp_path / "escape.json").exists()


def test_corrupt_zip_is_reported_without_project_changes(tmp_path):
    archive = tmp_path / "not-a-zip.zip"
    archive.write_bytes(b"not a zip")

    report = dry_run_backup(archive, temp_root=tmp_path / "scratch")

    assert report["status"] == "invalid"
    assert report["live_project_modified"] is False


def test_cli_cannot_overwrite_backup_archive(tmp_path):
    archive = tmp_path / "backup.zip"
    original = b"keep-this-backup"
    archive.write_bytes(original)

    try:
        from tools import backup_restore_dry_run as tool
        tool.main([str(archive), "--output", str(archive)])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("CLI should reject report path that collides with archive")
    assert archive.read_bytes() == original


@pytest.mark.parametrize("manifest", [
    pytest.param([], id="array"),
    pytest.param(None, id="null"),
    pytest.param("not-an-object", id="string"),
    pytest.param({"files": [], "file_count": None}, id="null-count"),
    pytest.param({"files": [], "file_count": False}, id="boolean-count"),
])
def test_malformed_manifest_is_reported_invalid_without_extraction(tmp_path, manifest):
    archive = tmp_path / "invalid-manifest.zip"
    scratch = tmp_path / "scratch"
    try:
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("backup_manifest.json", json.dumps(manifest))

        report = dry_run_backup(archive, temp_root=scratch)

        assert report["status"] == "invalid"
        assert report["live_project_modified"] is False
        assert report["checks"][0]["code"] == "dry_run_failed"
        assert not scratch.exists(), "invalid manifest must be rejected before extraction"
    finally:
        archive.unlink(missing_ok=True)
