"""AC12/13/17 recovery regressions. Every fixture is temporary and offline."""
import json
import sqlite3
import subprocess
import os
import zipfile
import tempfile
from pathlib import Path

import pytest

from scripts import channel_migration as cm, db
from tests.test_channel_migration import build_root, apply
from tests.test_backup_engine import isolated_backup_env
from scripts.backup_engine import BackupEngine


@pytest.fixture
def relocation_root():
    with tempfile.TemporaryDirectory(prefix="omnicut-recovery-test-") as directory:
        yield Path(directory)


@pytest.mark.parametrize("table_name", ["posting_jobs", "posting_account_audit", "channel_artifacts", "future_store"])
def test_snapshot_restore_refuses_new_rows_in_non_migration_tables(tmp_path, table_name):
    root = build_root(tmp_path / "source")
    apply(root)
    table = db.DocumentTable(table_name, lambda: root / "_Docs/store.db", lambda: root / "_Docs" / f"{table_name}.json")
    table.save([{"id": "new-after-cutover", "channel_id": "main"}])
    with pytest.raises(cm.MigrationError, match="fingerprint"):
        cm.Migrator(root).restore_snapshot_in_place()
    assert table.load()[0]["id"] == "new-after-cutover"
    cm._close_cached_connections(root)


def test_nested_manifests_with_same_basename_are_discovered_and_protect_restore(tmp_path):
    root = build_root(tmp_path / "source")
    for channel in ("main", "second"):
        manifest = root / "03_Projects" / channel / "same" / "project.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"channel_id": channel}), encoding="utf-8")
    paths = cm.MigrationPaths.for_root(root)
    world = cm.load_world(paths)
    assert "main/same" in world.manifests and "second/same" in world.manifests
    before = cm.fingerprint(paths)
    target = root / "03_Projects/second/same/project.json"
    target.write_text('{"channel_id":"second","newer":true}', encoding="utf-8")
    assert cm.fingerprint(paths) != before
    snap = tmp_path / "snapshot"
    manifest = cm.create_snapshot(paths, snap, allowed_roots=[tmp_path])
    assert "03_Projects/second/same/project.json" in {entry["rel"] for entry in manifest["files"]}


@pytest.mark.parametrize("table_name", ["posting_jobs", "posting_account_audit", "channel_artifacts"])
@pytest.mark.parametrize("committed", [True, False])
def test_extra_store_intents_relocate_and_recover_without_losing_rows(tmp_path, table_name, committed):
    root = build_root(tmp_path / "source")
    mirror = root / "_Docs" / f"{table_name}.json"
    table = db.DocumentTable(table_name, lambda: root / "_Docs/store.db", lambda: mirror)
    rows = [{"id": "kept", "channel_id": "main"}]
    table.save(rows)
    if not committed:
        mirror.write_text('[{"id":"uncommitted"}]', encoding="utf-8")
    db._write_mirror_intent(mirror, table_name, cm._mirror_token(mirror))
    cm._close_cached_connections(root)
    snap = tmp_path / "snapshot"
    cm.create_snapshot(cm.MigrationPaths.for_root(root), snap, allowed_roots=[tmp_path])
    target = tmp_path / "restored"
    cm.restore_snapshot(snap / "manifest.json", target)
    verdict = cm.verify_restore(snap / "manifest.json", target)
    assert verdict["ok"], verdict["problems"]
    restored = db.DocumentTable(table_name, lambda: target / "_Docs/store.db", lambda: target / "_Docs" / f"{table_name}.json")
    assert restored.load() == rows
    assert not (target / "_Docs" / f"{table_name}.json.publish-pending").exists()
    cm._close_cached_connections(target)
    assert cm.verify_restore(snap / "manifest.json", target)["ok"]


def test_snapshot_tamper_is_detected_before_any_target_write(tmp_path):
    root = build_root(tmp_path / "source")
    snap = tmp_path / "snapshot"
    manifest = cm.create_snapshot(cm.MigrationPaths.for_root(root), snap, allowed_roots=[tmp_path])
    last_file = snap / manifest["files"][-1]["rel"]
    last_file.write_bytes(b"tampered")
    target = tmp_path / "restored"
    with pytest.raises(cm.MigrationError, match="เสีย"):
        cm.restore_snapshot(snap / "manifest.json", target)
    assert not target.exists()


def test_snapshot_rejects_foreign_intent_source_before_writing(tmp_path):
    root = build_root(tmp_path / "source")
    mirror = root / "_Docs/posting_jobs.json"
    table = db.DocumentTable("posting_jobs", lambda: root / "_Docs/store.db", lambda: mirror)
    table.save([{"id": "job"}])
    db._write_mirror_intent(mirror, "posting_jobs", cm._mirror_token(mirror))
    cm._close_cached_connections(root)
    snap = tmp_path / "snapshot"
    manifest = cm.create_snapshot(cm.MigrationPaths.for_root(root), snap, allowed_roots=[tmp_path])
    entry = next(item for item in manifest["files"] if item.get("mirror_intent"))
    entry["mirror_intent"]["source_path"] = str(tmp_path / "foreign.json")
    intent = snap / entry["rel"]
    intent.write_text(json.dumps(entry["mirror_intent"]), encoding="utf-8")
    entry["sha256"] = cm.sha256_file(intent)
    (snap / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    target = tmp_path / "restored"
    with pytest.raises(cm.MigrationError, match="root/table"):
        cm.restore_snapshot(snap / "manifest.json", target)
    assert not target.exists()


def test_verify_restore_detects_tamper_in_future_table(tmp_path):
    root = build_root(tmp_path / "source")
    table = db.DocumentTable("future_store", lambda: root / "_Docs/store.db", lambda: root / "_Docs/future_store.json")
    table.save([{"id": "kept"}])
    cm._close_cached_connections(root)
    snap = tmp_path / "snapshot"
    cm.create_snapshot(cm.MigrationPaths.for_root(root), snap, allowed_roots=[tmp_path])
    target = tmp_path / "restored"
    cm.restore_snapshot(snap / "manifest.json", target)
    connection = sqlite3.connect(target / "_Docs/store.db")
    try:
        connection.execute("DELETE FROM future_store")
        connection.commit()
    finally:
        connection.close()
    verdict = cm.verify_restore(snap / "manifest.json", target)
    assert not verdict["ok"]
    assert any("SQLite" in problem for problem in verdict["problems"])


def test_backup_batch_database_is_standalone_wal_consistent_and_restore_opens(isolated_backup_env, relocation_root):
    environment = isolated_backup_env
    database = environment["projects"] / "batch_render_queue.db"
    writer = sqlite3.connect(database)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE wal_probe(value TEXT)")
    writer.execute("INSERT INTO wal_probe VALUES ('committed-wal')")
    writer.commit()
    try:
        backup = BackupEngine.create_backup()
    finally:
        writer.close()
    with zipfile.ZipFile(backup["file_path"]) as archive:
        assert "03_Projects/batch_render_queue.db" in archive.namelist()
        assert not any(name.endswith(("-wal", "-shm")) for name in archive.namelist())
    target = relocation_root / "relocated"
    assert BackupEngine.restore_backup(backup["backup_name"], target)["ok"]
    connection = sqlite3.connect(target / "03_Projects/batch_render_queue.db")
    try:
        assert connection.execute("SELECT value FROM wal_probe").fetchone()[0] == "committed-wal"
    finally:
        connection.close()


def test_backup_preserves_identity_refs_and_registered_media_and_checks_tamper(isolated_backup_env, relocation_root):
    environment = isolated_backup_env
    root = environment["root"]
    files = ["02_Assets/Refs/playbook_notes.json", "02_Assets/Refs/ref.jpg",
             "_Docs/producer/second/Refs/ref.png", "04_Exports/Ready_to_post/second/clip.mp4",
             "05_Covers_Thumbnails/second/cover.jpg", "02_Assets/profile/avatar.png"]
    for relative in files:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"{}" if target.suffix == ".json" else b"fixture")
    (environment["docs"] / "export_registry.json").write_text(json.dumps([{"id": "e", "path": files[3], "cover_path": files[4]}]), encoding="utf-8")
    (environment["docs"] / "channels.json").write_text(json.dumps({"channels": [{"avatar_asset_path": files[5]}]}), encoding="utf-8")
    backup = BackupEngine.create_backup()
    target = relocation_root / "relocated"
    assert BackupEngine.restore_backup(backup["backup_name"], target)["ok"]
    assert all((target / relative).read_bytes() == (root / relative).read_bytes() for relative in files)
    with zipfile.ZipFile(backup["file_path"]) as archive:
        contents = {name: archive.read(name) for name in archive.namelist()}
    contents[files[-1]] = b"tampered"
    with zipfile.ZipFile(backup["file_path"], "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
    assert BackupEngine.verify_backup(backup["backup_name"])["is_valid"] is False
    untouched = relocation_root / "bad-restore"
    with pytest.raises(ValueError, match="checksum"):
        BackupEngine.restore_backup(backup["backup_name"], untouched)
    assert not untouched.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher")
def test_launcher_checks_exact_project_service_ownership_without_starting(tmp_path):
    helper = Path(__file__).resolve().parents[1] / "tools/launch_omnicut.ps1"
    script = f"""
. '{str(helper).replace("'", "''")}'
$root = '{str(tmp_path / "OmniCut").replace("'", "''")}'
$otherRoot = '{str(tmp_path / "other").replace("'", "''")}'
$when = Get-Date
$own = [pscustomobject]@{{ProcessId=10; ParentProcessId=0; CreationDate=$when; CommandLine=('python "' + $root + '\\scripts\\api_server.py"')}}
$other = [pscustomobject]@{{ProcessId=20; ParentProcessId=0; CreationDate=$when; CommandLine=('python "' + $otherRoot + '\\scripts\\api_server.py"')}}
$unknown = [pscustomobject]@{{ProcessId=30; ParentProcessId=0; CreationDate=$when; CommandLine=('python "' + $root + '\\other.py"')}}
$child = [pscustomobject]@{{ProcessId=40; ParentProcessId=10; CreationDate=$when; CommandLine='python child.py'}}
$map = @{{10=$own;20=$other;30=$unknown;40=$child}}
@((Test-OmnicutProcess $own $map $root 8000),(Test-OmnicutProcess $other $map $root 8000),(Test-OmnicutProcess $unknown $map $root 8000),(Test-OmnicutProcess $own $map $root 3002),(Test-OmnicutProcess $child $map $root 8000)) | ConvertTo-Json -Compress
"""
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == [True, False, False, False, True]


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher")
def test_launcher_validates_all_listeners_before_stopping_any(tmp_path):
    helper = Path(__file__).resolve().parents[1] / "tools/launch_omnicut.ps1"
    root = tmp_path / "launcher fixture"
    (root / ".venv/Scripts").mkdir(parents=True)
    (root / ".venv/Scripts/python.exe").write_bytes(b"fixture")
    (root / "frontend").mkdir()
    (root / "03_Projects/_HyperFrames_Studio").mkdir(parents=True)
    script = f"""
. '{str(helper).replace("'", "''")}'
$script:stopped = $false
$script:started = $false
$script:fixtureRoot = '{str(root).replace("'", "''")}'
function Get-CimInstance {{
    [pscustomobject]@{{ProcessId=10;ParentProcessId=0;CreationDate=(Get-Date);CommandLine=('python "' + $script:fixtureRoot + '\\scripts\\api_server.py"')}}
    [pscustomobject]@{{ProcessId=20;ParentProcessId=0;CreationDate=(Get-Date);CommandLine='unrelated-service'}}
}}
function Get-NetTCPConnection {{
    [pscustomobject]@{{OwningProcess=10;LocalPort=8000}}
    [pscustomobject]@{{OwningProcess=20;LocalPort=5173}}
}}
function Stop-Process {{ $script:stopped = $true }}
function Start-Process {{ $script:started = $true }}
$blocked = $false
try {{ Start-Omnicut -ProjectRoot $script:fixtureRoot }} catch {{ $blocked = $true }}
@($blocked,$script:stopped,$script:started) | ConvertTo-Json -Compress
"""
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == [True, False, False]


def test_project_lifecycle_preserves_channel_namespace_and_excludes_system_workspaces(tmp_path, monkeypatch):
    from scripts.project_manifest import ProjectManifest
    projects = tmp_path / "03_Projects"
    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", projects)
    monkeypatch.setattr("scripts.project_manifest.BASE_DIR", tmp_path)
    monkeypatch.setattr("scripts.project_manifest.ARCHIVE_DIR", tmp_path / "06_Archive")
    for name in ("first/same", "second/same", "GadgetMedia/dedicated", "_HyperFrames_Studio/system"):
        path = projects / name / "project.json"
        path.parent.mkdir(parents=True)
        path.write_text('{"channel_id":"main"}', encoding="utf-8")
    assert {row["project_name"] for row in ProjectManifest.list_projects()} == {"first/same", "second/same"}
    assert ProjectManifest.archive("first/same")["archived_to"] == "06_Archive/Projects/first/same"
    assert (projects / "second/same/project.json").exists()
    assert ProjectManifest.delete("second/same")["project_name"] == "second/same"
    with pytest.raises(ValueError, match="ระบบ"):
        ProjectManifest.delete("_HyperFrames_Studio/system")
    assert (projects / "_HyperFrames_Studio/system/project.json").exists()
