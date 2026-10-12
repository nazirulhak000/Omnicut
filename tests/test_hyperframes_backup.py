"""HF approved artifacts survive backup relocation without copying caches."""
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import zipfile

import pytest

import scripts.backup_engine as backup
from scripts.db import DocumentTable
from scripts.hyperframes_authoring import CreativeJobStore


def test_hf7_approved_master_and_accepted_overlay_survive_relocated_backup(workspace):
    from copy import deepcopy
    import shutil
    from PIL import Image
    from scripts.api_hyperframes_workflow import Workflow
    from scripts.gadget_media_paths import GadgetMediaRoots
    from scripts.gadget_media_repository import GadgetMediaRepository
    from scripts.hyperframes_authoring import validate_inputs, verify_snapshot
    from scripts.hyperframes_overlay import HyperFramesOverlay, _sha
    from scripts.hyperframes_project import HyperFramesProjects
    from scripts.hyperframes_sources import HyperFramesSources

    root, _, _, _, target = workspace
    repo = GadgetMediaRepository(GadgetMediaRoots.under(root), channel_id="main")
    gadget = repo.create({"brand": "Exact", "model": "Preserved"}, project_id="backup-overlay-master", editorial_promise="Preserve approved master")
    master = repo.roots.project_dir(gadget.project_id) / "review/approved.mp4"
    master.write_bytes(b"approved-master-video-with-original-audio")
    original = master.read_bytes()
    gadget.status = "rendered"
    gadget.artifacts = [{"artifact_id": "original-approved-master", "kind": "render", "path": str(master), "approved": False, "sha256": _sha(master)}]
    repo.save(gadget)
    repo.approve_render(gadget.project_id, "original-approved-master")
    sources = HyperFramesSources(root)
    binding = {"type": "gadget_project", "project_id": gadget.project_id}
    projects = HyperFramesProjects(root, sources=sources)
    style = {"id": "locked-original-master", "version": 1, "tokens": {"background": "#000000"}}
    project = projects.create("main", binding, {"channel_id": "main"}, {"audio_mode": "silent", "duration_seconds": 1, "style_profile": style})
    overlay = HyperFramesOverlay(root, resolver=sources.approved_master, probe=lambda p: {"width": 1080, "height": 1920, "fps": 30, "duration": 1, "audio": True})
    info = overlay.inspect("main", binding)
    directory = projects.directory(project["project_id"], "main").relative_to(root).as_posix()
    frozen = overlay.freeze("main", directory, binding, approval={"approved": True, "master_digest": info["master_digest"]})
    image = root / "02_Assets/overlay.png"
    Image.new("RGB", (16, 16), "red").save(image)
    built = overlay.compose(frozen, f"{directory}/overlay_compositions/accepted", [{"path": image.relative_to(root).as_posix(), "sha256": _sha(image), "x": 48, "y": 48, "width": 100, "height": 100, "start": .2, "duration": .4}])
    project = projects.update(project["project_id"], "main", project["revision"], {"inputs": {**project["inputs"], **built["inputs"]}, "overlay_contract": built["asset_contract"]})
    packet = validate_inputs(root, project["inputs"])
    packet["source_snapshot"] = sources.packet("main", project)
    source_revision = sha256(json.dumps(packet["source_snapshot"], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    creative = CreativeJobStore(root)
    job = creative.create("main", project["project_id"], project["revision"], packet, expected_source_revision=source_revision)
    work = root / job["work_path"]
    work.mkdir(parents=True)
    claimed = creative.claim(job["id"], "main", "isolated-overlay-worker", job["generation"])
    fence = {key: claimed[key] for key in ("executor_id", "generation", "fence")}
    creative.checkpoint(job["id"], "main", **fence, checkpoint={"provider": "offline-fixture", "phase": "composition_staged", "next_action": "Submit the sealed approved overlay composition"})
    for entry in built["files"]:
        shutil.copyfile(root / built["source_dir"] / entry["path"], work / entry["path"])
    submitted = creative.submit(job["id"], "main", **fence, current_revision=project["revision"], current_source_revision=source_revision, source_dir=work)
    raw_submitted = creative.table.scoped_load("main")[0]["submitted_revision"]
    assert not {"revision_dir", "snapshot_path", "entry_path"}.intersection(raw_submitted)
    # Exercise a pre-upgrade archive with informational absolute pointers.
    with creative.table.scoped_mutate("main") as rows:
        row = next(item for item in rows if item["id"] == job["id"])
        row["submitted_revision"] = deepcopy(submitted["submitted_revision"])
        row["submitted_revision"]["snapshot_path"] = row["submitted_revision"]["revision_dir"]
    reference = deepcopy(submitted["submitted_revision"])
    for key in ("revision_dir", "snapshot_path", "entry_path"):
        reference.pop(key, None)
    reference.update(source_revision=source_revision, validated_input_hash=packet["input_hash"], asset_hashes=packet["asset_hashes"], asset_contract=built["asset_contract"])
    project = projects.update(project["project_id"], "main", project["revision"], {"accepted_revision": reference, "composition_revisions": [reference], "status": "preview_ready"})

    result = backup.BackupEngine.create_backup()
    assert backup.BackupEngine.restore_backup(result["backup_name"], target)["ok"]
    unavailable = root.with_name("source-unavailable")
    assert root.parent == target.parent and root.name == "source" and not unavailable.exists()
    # Release only this test's source database handles before moving it on Windows.
    from scripts import db
    connections = getattr(db._local, "conns", {})
    for key, connection in tuple(connections.items()):
        if Path(key).is_relative_to(root):
            connection.close()
            del connections[key]
    import gc
    gc.collect()
    root.rename(unavailable)
    assert not root.exists()
    relocated = Workflow(target)
    restored = relocated.projects.get(project["project_id"], "main")
    assert restored["accepted_revision"] == reference
    closed = relocated.snapshot(restored["accepted_revision"])
    assert verify_snapshot(closed) and Path(closed["revision_dir"]).is_relative_to(target)
    assert _sha(target / reference["revision_relative_path"] / "master.mp4") == sha256(original).hexdigest()
    assert (target / frozen["frozen_path"]).read_bytes() == original
    assert json.loads((target / frozen["frozen_path"]).with_name("master.json").read_text(encoding="utf-8")) == frozen
    relocated_sources = HyperFramesSources(target)
    assert relocated.source_revision("main", restored) == source_revision
    assert relocated_sources.gadget("main", binding).approved_master_id == "original-approved-master"
    restored_store = CreativeJobStore(target)
    mirror_bytes = (target / "_Docs/creative_jobs.json").read_bytes()
    restored_job = restored_store.get(job["id"], "main")
    assert restored_job["checkpoint"] == submitted["checkpoint"]
    assert restored_job["status"] == "submitted"
    assert Path(restored_job["submitted_revision"]["revision_dir"]).is_relative_to(target)
    assert verify_snapshot(restored_job["submitted_revision"])
    listed_job = next(row for row in restored_store.list("main") if row["id"] == job["id"])
    assert listed_job == restored_job
    # The external-session CLI's status request traverses the actual router.
    import io
    from urllib.parse import urlsplit
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from scripts import api_hyperframes_workflow as api
    from scripts.channel_scope import ChannelScope
    from tools.hyperframes_workflow import request_api
    app = FastAPI()
    app.include_router(api.router)
    scope = ChannelScope("main", source="header", strict=True, channel={"id": "main", "status": "active"})
    app.dependency_overrides[api.get_workflow] = lambda: relocated
    app.dependency_overrides[api.get_workflow_scope] = lambda: scope
    with TestClient(app) as client:
        cli_status = request_api("http://127.0.0.1:8000", "main", job["id"], "status",
            opener=lambda req, timeout: io.BytesIO(client.get(urlsplit(req.full_url).path).content))
    assert cli_status["job"] == restored_job
    assert (target / "_Docs/creative_jobs.json").read_bytes() == mirror_bytes
    assert (unavailable / master.relative_to(root)).read_bytes() == original


@pytest.mark.parametrize("problem", ["foreign_pointer", "revision_identity", "project", "channel", "entrypoint", "files_none", "file_path_list"])
def test_restored_creative_reads_reject_foreign_or_mismatched_snapshot_identity(workspace, problem):
    from copy import deepcopy
    from scripts.hyperframes_authoring import AuthoringError
    root, *_ = workspace
    store = CreativeJobStore(root)
    job = store.create("main", "rehydrate-project", 1, {})
    work = root / job["work_path"]
    work.mkdir(parents=True)
    (work / "index.html").write_text('<html><body><div data-composition-id="restore" data-width="1080" data-height="1920" data-duration="1"></div></body></html>', encoding="utf-8")
    claim = store.claim(job["id"], "main", "restore-test", 0)
    result = store.submit(job["id"], "main", **{key: claim[key] for key in ("executor_id", "generation", "fence")}, current_revision=1, source_dir=work)
    reference = deepcopy(result["submitted_revision"])
    if problem == "foreign_pointer":
        reference["entry_path"] = str(root.parent / "foreign/private.html")
    elif problem == "revision_identity":
        reference["revision_relative_path"] = "03_Projects/_HyperFrames_Studio/revisions/hf_revision_" + "0" * 32
    elif problem in {"project", "channel"}:
        reference[problem + "_id"] = "other-owner"
    elif problem == "files_none":
        reference["files"] = None
    elif problem == "file_path_list":
        reference["files"][0]["path"] = ["invalid"]
    else:
        reference["entrypoint"] = "../private.html"
    with store.table.scoped_mutate("main") as rows:
        next(row for row in rows if row["id"] == job["id"])["submitted_revision"] = reference
    mirror = (root / "_Docs/creative_jobs.json").read_bytes()
    for reader in (lambda: store.get(job["id"], "main"), lambda: store.list("main"), lambda: store.handoff_packet(job["id"], "main")):
        with pytest.raises(AuthoringError):
            reader()
    assert (root / "_Docs/creative_jobs.json").read_bytes() == mirror


def test_selected_export_cover_binding_survives_backup_relocation(workspace):
    from scripts.export_cover_bindings import ExportCoverBindingStore
    from scripts.channel_migration import RECOVERY_TABLES
    root, table, row, files, target = workspace
    assert "export_cover_bindings" in {spec.table for spec in RECOVERY_TABLES}
    video = root / "04_Exports/Ready_to_post/main/real.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"registered export")
    DocumentTable("export_registry", lambda: root / "_Docs/store.db", lambda: root / "_Docs/export_registry.json").save(
        [{"id": "exact-export", "channel_id": "main", "path": video.relative_to(root).as_posix()}])
    cover = root / "05_Covers_Thumbnails/main/selected/cover.jpg"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b"selected cover")
    store = ExportCoverBindingStore(root)
    store.save("main", "exact-export", video, selections={"3:4": cover.relative_to(root).as_posix()})
    expected = store.get("main", "exact-export", format="3:4")
    result = backup.BackupEngine.create_backup()
    assert backup.BackupEngine.restore_backup(result["backup_name"], target)["ok"]
    assert ExportCoverBindingStore(target).get("main", "exact-export", format="3:4") == expected
    assert (target / cover.relative_to(root)).read_bytes() == cover.read_bytes()


def _selected_binding(workspace):
    from scripts.export_cover_bindings import ExportCoverBindingStore
    root, *_ = workspace
    video = root / "04_Exports/Ready_to_post/main/selected.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(b"registered export")
    DocumentTable("export_registry", lambda: root / "_Docs/store.db", lambda: root / "_Docs/export_registry.json").save(
        [{"id": "selected-export", "channel_id": "main", "path": video.relative_to(root).as_posix()}])
    cover = root / "05_Covers_Thumbnails/main/selected/exact.jpg"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b"immutable chosen cover")
    store = ExportCoverBindingStore(root)
    store.save("main", "selected-export", video, {"9:16": cover})
    return store, cover


@pytest.mark.parametrize("problem", ["changed", "missing", "alias", "mirror_missing", "mirror_stale"])
def test_selected_export_cover_invalid_state_blocks_backup(workspace, monkeypatch, problem):
    root, *_ = workspace
    store, cover = _selected_binding(workspace)
    if problem == "changed":
        cover.write_bytes(b"changed after explicit selection")
    elif problem == "missing":
        cover.unlink()
    elif problem == "alias":
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda candidate: candidate == cover.parent or original(candidate))
    elif problem == "mirror_missing":
        (root / "_Docs/export_cover_bindings.json").unlink()
    else:
        (root / "_Docs/export_cover_bindings.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        backup.BackupEngine.create_backup()
    assert list(backup.BACKUP_DIR.glob("*.zip")) == []


def test_concurrent_explicit_cover_selection_aborts_backup_cleanly(workspace, monkeypatch):
    root, _, _, files, _ = workspace
    store, cover = _selected_binding(workspace)
    alternate = cover.with_name("new.jpg")
    alternate.write_bytes(b"new explicit selection")
    original_write = zipfile.ZipFile.write
    mutated = False
    def write_with_selection(archive, filename, *args, **kwargs):
        nonlocal mutated
        result = original_write(archive, filename, *args, **kwargs)
        if not mutated and str(filename) == str(files[0]):
            mutated = True
            row = store._rows("export_cover_bindings")[0]
            row["selections"]["9:16"] = {"path": alternate.relative_to(root).as_posix(), "sha256": sha256(alternate.read_bytes()).hexdigest(), "format": "9:16"}
            row["revision"] += 1
            with sqlite3.connect(root / "_Docs/store.db") as connection:
                connection.execute("UPDATE export_cover_bindings SET data=? WHERE id=?", (json.dumps(row), row["id"]))
            (root / "_Docs/export_cover_bindings.json").write_text(json.dumps([row]), encoding="utf-8")
        return result
    monkeypatch.setattr(zipfile.ZipFile, "write", write_with_selection)
    with pytest.raises(ValueError, match="changed during backup"):
        backup.BackupEngine.create_backup()
    assert mutated and list(backup.BACKUP_DIR.glob("*.zip")) == []


def test_selected_cover_aba_change_cannot_publish_wrong_archived_bytes(workspace, monkeypatch):
    store, cover = _selected_binding(workspace)
    original_bytes = cover.read_bytes()
    original_write = zipfile.ZipFile.write
    mutated = False
    def write_with_aba(archive, filename, *args, **kwargs):
        nonlocal mutated
        if str(filename) != str(cover):
            return original_write(archive, filename, *args, **kwargs)
        mutated = True
        cover.write_bytes(b"different while zip reads the file")
        try:
            return original_write(archive, filename, *args, **kwargs)
        finally:
            cover.write_bytes(original_bytes)
    monkeypatch.setattr(zipfile.ZipFile, "write", write_with_aba)
    with pytest.raises(ValueError, match="changed during backup"):
        backup.BackupEngine.create_backup()
    assert mutated and cover.read_bytes() == original_bytes
    assert list(backup.BACKUP_DIR.glob("*.zip")) == []


def test_selected_binding_aba_change_during_sqlite_copy_aborts(workspace, monkeypatch):
    root, *_ = workspace
    store, cover = _selected_binding(workspace)
    original_row = store._rows("export_cover_bindings")[0]
    changed_row = json.loads(json.dumps(original_row))
    changed_row["revision"] += 1
    original_copy = backup.BackupEngine._backup_sqlite_database
    def copy_with_aba(source, destination):
        with sqlite3.connect(source) as connection:
            connection.execute("UPDATE export_cover_bindings SET data=? WHERE id=?", (json.dumps(changed_row), changed_row["id"]))
        try:
            original_copy(source, destination)
        finally:
            with sqlite3.connect(source) as connection:
                connection.execute("UPDATE export_cover_bindings SET data=? WHERE id=?", (json.dumps(original_row), original_row["id"]))
    monkeypatch.setattr(backup.BackupEngine, "_backup_sqlite_database", copy_with_aba)
    with pytest.raises(ValueError, match="changed during backup"):
        backup.BackupEngine.create_backup()
    assert store._rows("export_cover_bindings")[0] == original_row
    assert list(backup.BACKUP_DIR.glob("*.zip")) == []


def test_binding_snapshot_does_not_treat_separate_batch_db_as_store(workspace):
    root, *_ = workspace
    _selected_binding(workspace)
    with sqlite3.connect(root / "03_Projects/batch_render_queue.db") as connection:
        connection.execute("CREATE TABLE batch_render_queue (id TEXT PRIMARY KEY, data TEXT)")
        connection.execute("INSERT INTO batch_render_queue VALUES (?,?)", ("batch", json.dumps({"id": "batch"})))
    result = backup.BackupEngine.create_backup()
    with zipfile.ZipFile(result["file_path"]) as archive:
        assert "03_Projects/batch_render_queue.db" in archive.namelist()


@pytest.fixture
def workspace(tmp_path, tmp_path_factory, monkeypatch):
    root = tmp_path / "source"
    docs = root / "_Docs"
    docs.mkdir(parents=True)
    projects = root / "03_Projects"
    projects.mkdir()
    directory = root / ".tmp/hyperframes/render/hfr_test/1"
    directory.mkdir(parents=True)
    video, thumbnail = directory / "video.mp4", directory / "thumbnail.webp"
    video.write_bytes(b"temporary reviewed video")
    thumbnail.write_bytes(b"temporary reviewed thumbnail")
    cover = root / "02_Assets/Covers/shared.webp"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b"approved source cover")
    ignored = directory / "unreferenced-cache.bin"
    ignored.write_bytes(b"not a durable reference")
    revision = projects / "_HyperFrames_Studio/revisions/rev_test"
    revision.mkdir(parents=True)
    (revision / "index.html").write_text('<link href=".theme.css">', encoding="utf-8")
    (revision / ".theme.css").write_text("body { color: white }", encoding="utf-8")
    table = DocumentTable("hyperframes_render_jobs", lambda: docs / "store.db", lambda: docs / "hyperframes_render_jobs.json")
    row = {"id": "hfr_test", "channel_id": "main", "status": "finalizing", "attempt": 1,
           "artifact": {"path": video.relative_to(root).as_posix(), "sha256": sha256(video.read_bytes()).hexdigest(),
                        "thumbnail_path": thumbnail.relative_to(root).as_posix(), "thumbnail_sha256": sha256(thumbnail.read_bytes()).hexdigest()},
           "finalize_intent": {"cover_source": cover.relative_to(root).as_posix(), "package": {"cover_sha256": sha256(cover.read_bytes()).hexdigest()}}}
    table.save([row])
    monkeypatch.setattr(backup, "BASE_DIR", root)
    monkeypatch.setattr(backup, "DOCS_DIR", docs)
    monkeypatch.setattr(backup, "PROJECTS_DIR", projects)
    monkeypatch.setattr(backup, "BACKUP_DIR", root / "06_Archive/Backups")
    yield root, table, row, [video, thumbnail, cover], tmp_path / "relocated"
    # Remove only this test's explicitly verified directory, including relocated
    # media and approved-master backups. Keep every other session's Temp intact.
    owned, base = tmp_path.resolve(), tmp_path_factory.getbasetemp().resolve()
    assert owned.parent == base and owned.name.startswith("test_")
    from scripts import db
    connections = getattr(db._local, "conns", {})
    for key, connection in tuple(connections.items()):
        if Path(key).is_relative_to(owned):
            connection.close()
            del connections[key]
    import gc
    import shutil
    gc.collect()
    if owned.exists():
        shutil.rmtree(owned)


@pytest.mark.parametrize("state", ["qc_ready", "finalizing", "recovery_required"])
def test_exact_hf_artifacts_and_accepted_dependencies_survive_relocation(workspace, state):
    root, table, row, files, target = workspace
    row["status"] = state
    table.save([row])
    result = backup.BackupEngine.create_backup()
    with zipfile.ZipFile(result["file_path"]) as archive:
        for source in files:
            assert archive.read(source.relative_to(root).as_posix()) == source.read_bytes()
        assert ".tmp/hyperframes/render/hfr_test/1/unreferenced-cache.bin" not in archive.namelist()
        assert "03_Projects/_HyperFrames_Studio/revisions/rev_test/.theme.css" in archive.namelist()
    restored = backup.BackupEngine.restore_backup(result["backup_name"], target)
    assert restored["ok"]
    for source in files:
        assert sha256((target / source.relative_to(root)).read_bytes()).hexdigest() == sha256(source.read_bytes()).hexdigest()
    records = DocumentTable("hyperframes_render_jobs", lambda: target / "_Docs/store.db", lambda: target / "_Docs/hyperframes_render_jobs.json").scoped_load("main")
    assert records == [row]


@pytest.mark.parametrize("problem", ["outside", "unmanaged", "missing", "changed", "traversal"])
def test_invalid_review_artifact_blocks_backup_without_partial_zip(workspace, problem):
    root, table, row, files, target = workspace
    if problem == "outside":
        row["artifact"]["path"] = str(target / "outside.mp4")
    elif problem == "unmanaged":
        row["artifact"]["path"] = "02_Assets/Covers/shared.webp"
    elif problem == "missing":
        row["artifact"]["path"] = ".tmp/hyperframes/render/hfr_test/1/missing.mp4"
    elif problem == "traversal":
        row["artifact"]["path"] = ".tmp/hyperframes/render/hfr_test/1/../1/video.mp4"
    else:
        files[0].write_bytes(b"changed after approval")
    table.save([row])
    with pytest.raises(ValueError):
        backup.BackupEngine.create_backup()
    assert list(backup.BACKUP_DIR.glob("*.zip")) == []


def test_sqlite_json_disagreement_cannot_create_inconsistent_backup(workspace):
    root, table, row, files, target = workspace
    changed = dict(row, status="qc_ready")
    (root / "_Docs/hyperframes_render_jobs.json").write_text(json.dumps([changed]), encoding="utf-8")
    with pytest.raises(ValueError, match="disagree"):
        backup.BackupEngine.create_backup()


def test_filesystem_alias_rejected_before_reading_unmanaged_media(workspace, monkeypatch):
    root, table, row, files, target = workspace
    from pathlib import Path
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == files[0].parent or original(path))
    with pytest.raises(ValueError, match="alias"):
        backup.BackupEngine.create_backup()


@pytest.mark.parametrize("kind", ["render", "creative"])
def test_background_job_change_during_archive_rejects_completed_backup(workspace, monkeypatch, kind):
    root, render_table, row, files, target = workspace
    table = render_table
    changed = dict(row, status="qc_ready")
    if kind == "creative":
        docs = root / "_Docs"
        store = CreativeJobStore(root)
        initial = store.create("main", "hf_project", 1, {})
        assert (docs / "creative_jobs.json").exists()
        with sqlite3.connect(docs / "store.db") as connection:
            assert connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='creative_jobs'").fetchone()
        changed = dict(initial, status="submitted")
    original_write = zipfile.ZipFile.write
    mutated = False

    def write_with_worker_transition(archive, filename, *args, **kwargs):
        nonlocal mutated
        result = original_write(archive, filename, *args, **kwargs)
        if not mutated and str(filename) == str(files[0]):
            mutated = True
            # Simulate an already-owned writer completing outside the gate.
            # New DocumentTable writes correctly respect maintenance.
            name = "creative_jobs" if kind == "creative" else "hyperframes_render_jobs"
            with sqlite3.connect(root / "_Docs/store.db") as connection:
                connection.execute(f"UPDATE {name} SET data=? WHERE id=?", (json.dumps(changed), changed["id"]))
            (root / f"_Docs/{name}.json").write_text(json.dumps([changed]), encoding="utf-8")
        return result

    monkeypatch.setattr(zipfile.ZipFile, "write", write_with_worker_transition)
    with pytest.raises(ValueError, match="changed during backup"):
        backup.BackupEngine.create_backup()
    assert mutated
    assert list(backup.BACKUP_DIR.glob("*.zip")) == []


def test_creative_sqlite_mirror_disagreement_blocks_snapshot(workspace):
    root, table, row, files, target = workspace
    docs = root / "_Docs"
    creative = CreativeJobStore(root)
    creative.create("main", "hf_project", 1, {})
    (docs / "creative_jobs.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="disagree"):
        backup.BackupEngine.create_backup()
    assert list(backup.BACKUP_DIR.glob("*.zip")) == []
