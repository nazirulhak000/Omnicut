"""Unit tests for BackupEngine — isolated with temporary directories."""
from pathlib import Path
import json
import sqlite3
import zipfile
import pytest

from scripts.backup_engine import BackupEngine


@pytest.fixture
def isolated_backup_env(tmp_path: Path, monkeypatch):
    """Sets up an isolated environment with dummy _Docs and 03_Projects."""
    docs_dir = tmp_path / "_Docs"
    projects_dir = tmp_path / "03_Projects"
    backup_dir = tmp_path / "06_Archive" / "Backups"

    docs_dir.mkdir(parents=True)
    projects_dir.mkdir(parents=True)
    backup_dir.mkdir(parents=True)

    # Create dummy json in docs
    (docs_dir / "products.json").write_text(json.dumps({"products": [{"id": "p1"}]}), encoding="utf-8")
    (docs_dir / "post_log.json").write_text(json.dumps([{"id": "post1"}]), encoding="utf-8")
    (docs_dir / "schedule_queue.json").write_text(json.dumps([]), encoding="utf-8")
    # Non-json file in docs should be ignored unless store.db
    (docs_dir / "ignore_me.txt").write_text("ignore", encoding="utf-8")

    # Create dummy project in 03_Projects
    proj1 = projects_dir / "PROJ_01"
    proj1.mkdir()
    (proj1 / "project.json").write_text(json.dumps({"title": "Review 1"}), encoding="utf-8")
    (proj1 / "script_brief.md").write_text("# Script Brief", encoding="utf-8")
    (proj1 / ".temp_cache.lock").write_text("lock", encoding="utf-8")  # should be ignored

    monkeypatch.setattr("scripts.backup_engine.BASE_DIR", tmp_path)
    monkeypatch.setattr("scripts.backup_engine.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("scripts.backup_engine.DOCS_DIR", docs_dir)
    monkeypatch.setattr("scripts.backup_engine.PROJECTS_DIR", projects_dir)

    return {
        "root": tmp_path,
        "docs": docs_dir,
        "projects": projects_dir,
        "backup": backup_dir,
    }


def test_create_backup_creates_valid_zip_with_manifest(isolated_backup_env):
    backup_dir = isolated_backup_env["backup"]
    result = BackupEngine.create_backup(backup_dir=backup_dir)

    assert result["file_count"] >= 4  # 3 json + 2 proj files (excluding lock)
    assert result["size_bytes"] > 0
    assert result["sha256"] is not None

    zip_file = Path(result["file_path"])
    assert zip_file.exists()

    # Verify content inside zip
    with zipfile.ZipFile(zip_file, "r") as zf:
        names = zf.namelist()
        assert "backup_manifest.json" in names
        assert "_Docs/products.json" in names
        assert "_Docs/post_log.json" in names
        assert "_Docs/ignore_me.txt" not in names
        assert "03_Projects/PROJ_01/project.json" in names
        assert "03_Projects/PROJ_01/.temp_cache.lock" not in names

        # Read manifest
        manifest = json.loads(zf.read("backup_manifest.json").decode("utf-8"))
        assert manifest["file_count"] == result["file_count"]
        assert manifest["version"] == "1.0"


def test_create_backup_captures_committed_wal_pages(isolated_backup_env):
    """The archive must contain committed rows that have not been checkpointed."""
    docs_dir = isolated_backup_env["docs"]
    backup_dir = isolated_backup_env["backup"]
    db_path = docs_dir / "store.db"

    writer = sqlite3.connect(db_path)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE wal_probe (value TEXT NOT NULL)")
    writer.execute("INSERT INTO wal_probe(value) VALUES ('committed-in-wal')")
    writer.commit()
    try:
        assert db_path.with_name("store.db-wal").exists()
        result = BackupEngine.create_backup(backup_dir=backup_dir)
    finally:
        writer.close()

    with zipfile.ZipFile(result["file_path"], "r") as archive:
        archive.extract("_Docs/store.db", isolated_backup_env["root"] / "restored")
    restored_db = isolated_backup_env["root"] / "restored" / "_Docs" / "store.db"
    restored = sqlite3.connect(restored_db)
    try:
        assert restored.execute("SELECT value FROM wal_probe").fetchone() == ("committed-in-wal",)
    finally:
        restored.close()


def test_sqlite_backup_failure_does_not_fall_back_to_raw_copy(isolated_backup_env, monkeypatch):
    """A failed SQLite snapshot must abort instead of silently omitting WAL data."""
    docs_dir = isolated_backup_env["docs"]
    backup_dir = isolated_backup_env["backup"]
    db_path = docs_dir / "store.db"
    sqlite3.connect(db_path).close()

    def fail_snapshot(source_path, destination_path):
        raise sqlite3.OperationalError("simulated backup failure")

    monkeypatch.setattr(BackupEngine, "_backup_sqlite_database", staticmethod(fail_snapshot))
    with pytest.raises(sqlite3.OperationalError, match="simulated backup failure"):
        BackupEngine.create_backup(backup_dir=backup_dir)

    assert not list(backup_dir.glob("*.zip"))
    assert not list(backup_dir.glob(".tmp_store_*.db"))


def test_list_and_verify_backups(isolated_backup_env):
    backup_dir = isolated_backup_env["backup"]

    # Initially empty
    assert len(BackupEngine.list_backups(backup_dir=backup_dir)) == 0

    # Create one backup
    b1 = BackupEngine.create_backup(backup_dir=backup_dir)
    backups = BackupEngine.list_backups(backup_dir=backup_dir)
    assert len(backups) == 1
    assert backups[0]["backup_name"] == b1["backup_name"]
    assert backups[0]["is_valid"] is True

    # Verify backup
    verification = BackupEngine.verify_backup(b1["backup_name"], backup_dir=backup_dir)
    assert verification["is_valid"] is True
    assert verification["manifest"]["backup_name"] == b1["backup_name"]


def test_resolve_safe_path_prevents_traversal(isolated_backup_env):
    backup_dir = isolated_backup_env["backup"]

    # Safe name passes
    safe = BackupEngine.resolve_safe_path("omnicut_backup_2026.zip", backup_dir=backup_dir)
    assert safe == backup_dir / "omnicut_backup_2026.zip"

    # Traversal attempts fail
    with pytest.raises(ValueError, match="Path traversal|Invalid backup filename"):
        BackupEngine.resolve_safe_path("../etc/passwd", backup_dir=backup_dir)

    with pytest.raises(ValueError, match="Path traversal|Invalid backup filename"):
        BackupEngine.resolve_safe_path("..\\windows\\system32", backup_dir=backup_dir)


def test_delete_backup(isolated_backup_env):
    backup_dir = isolated_backup_env["backup"]
    b1 = BackupEngine.create_backup(backup_dir=backup_dir)
    fname = b1["backup_name"]

    assert (backup_dir / fname).exists()
    assert BackupEngine.delete_backup(fname, backup_dir=backup_dir) is True
    assert not (backup_dir / fname).exists()
    assert BackupEngine.delete_backup(fname, backup_dir=backup_dir) is False
