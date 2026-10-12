"""Exact export cover choices persist without production rendering/storage."""
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import json

import pytest

from scripts.channel_scope import ChannelError
from scripts.db import DocumentTable
from scripts.export_cover_bindings import ExportCoverBindingStore


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    docs = root / "_Docs"
    docs.mkdir(parents=True)
    registry = DocumentTable("export_registry", lambda: docs / "store.db", lambda: docs / "export_registry.json")
    rows = []
    for owner, identity in (("main", "export_old"), ("main", "export_new"), ("second", "export_foreign")):
        video = root / f"04_Exports/{owner}/{identity}.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(identity.encode())
        rows.append({"id": identity, "channel_id": owner, "path": video.relative_to(root).as_posix()})
    registry.save(rows)
    cover = root / "05_Covers_Thumbnails/main/explicit/selected.jpg"
    cover.parent.mkdir(parents=True)
    cover.write_bytes(b"real rendered cover fixture")
    return root, rows, cover


def test_empty_read_does_not_create_storage(tmp_path):
    store = ExportCoverBindingStore(tmp_path)
    assert store.get("main", "unknown") is None
    assert store.revision("main", "unknown") == 0
    assert list(tmp_path.iterdir()) == []


def test_read_with_existing_database_does_not_create_empty_binding_table(workspace):
    root, exports, cover = workspace
    assert ExportCoverBindingStore(root).get("main", "export_old") is None
    with sqlite3.connect(root / "_Docs/store.db") as connection:
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='export_cover_bindings'").fetchone() is None
    assert not (root / "_Docs/export_cover_bindings.json").exists()


def test_explicit_export_choice_survives_reload_without_latest_filename_guess(workspace):
    root, exports, cover = workspace
    store = ExportCoverBindingStore(root)
    saved = store.save("main", "export_old", exports[0]["path"], {"9:16": cover}, expected_revision=0)
    reloaded = ExportCoverBindingStore(root)
    choice = reloaded.get("main", "export_old")
    assert choice["path"] == cover.relative_to(root).as_posix()
    assert choice["revision"] == saved["revision"] == 1
    assert reloaded.get("main", "export_new") is None
    assert reloaded.get("second", "export_old") is None
    assert store.save("main", "export_old", exports[0]["path"], {"9:16": cover}, expected_revision=0) == saved
    with sqlite3.connect(root / "_Docs/store.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM export_cover_bindings").fetchone()[0] == 1


def test_changed_cover_is_not_returned(workspace):
    root, exports, cover = workspace
    store = ExportCoverBindingStore(root)
    store.save("main", "export_old", exports[0]["path"], {"9:16": cover})
    cover.write_bytes(b"unreviewed replacement")
    with pytest.raises(ChannelError) as failure:
        store.get("main", "export_old")
    assert failure.value.code == "export_cover_selection_changed"


@pytest.mark.parametrize("problem", ["missing", "alias", "malformed", "null_selection", "null_container"])
def test_existing_invalid_choice_is_distinct_from_absent_selection(workspace, monkeypatch, problem):
    root, exports, cover = workspace
    store = ExportCoverBindingStore(root)
    store.save("main", "export_old", exports[0]["path"], {"9:16": cover})
    assert store.get("main", "export_old", format="3:4") is None
    if problem == "missing":
        cover.unlink()
    elif problem == "alias":
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == cover.parent or original(path))
    else:
        with store.table.scoped_mutate("main") as rows:
            if problem == "null_container":
                rows[0]["selections"] = None
            else:
                rows[0]["selections"]["9:16"] = None if problem == "null_selection" else {}
    with pytest.raises(ChannelError) as failure:
        store.get("main", "export_old")
    assert failure.value.code == "export_cover_selection_invalid"


def test_saving_profile_cover_preserves_explicit_vertical_selection(workspace):
    root, exports, cover = workspace
    store = ExportCoverBindingStore(root)
    store.save("main", "export_old", exports[0]["path"], {"9:16": cover}, expected_revision=0)
    profile = cover.with_name("profile.jpg")
    profile.write_bytes(b"profile selection")
    store.save("main", "export_old", exports[0]["path"], {"3:4": profile}, expected_revision=1)
    assert store.get("main", "export_old")["path"] == cover.relative_to(root).as_posix()
    assert store.get("main", "export_old", format="3:4")["path"] == profile.relative_to(root).as_posix()


@pytest.mark.parametrize("problem", ["wrong_video", "foreign_export", "foreign_cover", "outside_cover", "missing_cover", "alias"])
def test_invalid_exact_identity_or_cover_fails_without_binding_write(workspace, monkeypatch, problem):
    root, exports, cover = workspace
    store = ExportCoverBindingStore(root)
    export_id, video = "export_old", exports[0]["path"]
    if problem == "wrong_video":
        video = exports[1]["path"]
    elif problem == "foreign_export":
        export_id, video = "export_foreign", exports[2]["path"]
    elif problem == "foreign_cover":
        cover = root / "05_Covers_Thumbnails/second/chosen.jpg"
        cover.parent.mkdir(parents=True)
        cover.write_bytes(b"foreign")
    elif problem == "outside_cover":
        cover = root / "04_Exports/main/cover.jpg"
        cover.write_bytes(b"wrong managed directory")
    elif problem == "missing_cover":
        cover = cover.with_name("missing.jpg")
    elif problem == "alias":
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == cover.parent or original(path))
    with pytest.raises(ChannelError):
        store.save("main", export_id, video, {"9:16": cover})
    assert not (root / "_Docs/export_cover_bindings.json").exists()


def test_concurrent_old_render_cannot_replace_new_explicit_selection(workspace):
    root, exports, cover = workspace
    store = ExportCoverBindingStore(root)
    old_revision = store.revision("main", "export_old")
    second = cover.with_name("new-selection.jpg")
    second.write_bytes(b"new explicit choice")
    store.save("main", "export_old", exports[0]["path"], {"9:16": second}, expected_revision=old_revision)
    with pytest.raises(ChannelError) as failure:
        store.save("main", "export_old", exports[0]["path"], {"9:16": cover}, expected_revision=old_revision)
    assert failure.value.code == "export_cover_revision_conflict"
    assert store.get("main", "export_old")["path"] == second.relative_to(root).as_posix()


def _endpoint_fixture(workspace, monkeypatch):
    from scripts import api_covers
    root, exports, cover = workspace
    monkeypatch.setattr(api_covers, "BASE_DIR", root)
    monkeypatch.setattr(api_covers, "COVERS_DIR", root / "05_Covers_Thumbnails")
    monkeypatch.setattr(api_covers, "require_media_owner", lambda *args, **kwargs: None)
    monkeypatch.setattr(api_covers, "register_companion", lambda *args: None)
    monkeypatch.setattr(api_covers, "_normalise_requested_cover_scene", lambda **kwargs: None)
    return api_covers, root, exports


@pytest.mark.parametrize("target", ["export_foreign", "export_old"])
def test_endpoint_rejects_foreign_or_mismatched_export_before_render(workspace, monkeypatch, target):
    api, root, exports = _endpoint_fixture(workspace, monkeypatch)
    called = []
    monkeypatch.setattr(api, "render_pro_cover", lambda **kwargs: called.append(kwargs))
    video = exports[2]["path"] if target == "export_foreign" else exports[1]["path"]
    with pytest.raises(ChannelError):
        api.render_pro_cover_endpoint(api.RenderProCoverRequest(export_id=target, video_path=video), SimpleNamespace(channel_id="main"))
    assert called == []
    assert not (root / "_Docs/export_cover_bindings.json").exists()


def test_endpoint_persists_actual_generated_files_for_exact_export(workspace, monkeypatch):
    api, root, exports = _endpoint_fixture(workspace, monkeypatch)
    def offline_render(**kwargs):
        directory = kwargs["output_dir"]
        directory.mkdir(parents=True)
        main, profile = directory / "rendered.jpg", directory / "profile.jpg"
        main.write_bytes(b"offline rendered 9:16")
        profile.write_bytes(b"offline rendered 3:4")
        return main, profile
    monkeypatch.setattr(api, "render_pro_cover", offline_render)
    response = api.render_pro_cover_endpoint(api.RenderProCoverRequest(export_id="export_old", video_path=exports[0]["path"], aspect_ratio="both"), SimpleNamespace(channel_id="main"))
    store = ExportCoverBindingStore(root)
    assert store.get("main", "export_old")["path"] == response["cover_path"]
    assert store.get("main", "export_old", format="3:4")["path"] == response["cover_3x4_path"]
    assert response["cover_binding_revision"] == 1
    assert store.get("main", "export_new") is None


@pytest.mark.parametrize("source", ["raw", "timeline"])
def test_endpoint_binds_export_identity_without_replacing_cover_source(workspace, monkeypatch, source):
    api, root, exports = _endpoint_fixture(workspace, monkeypatch)
    raw = root / "01_Raw/source.mp4"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(b"owned offline source")
    source_data = "data:image/png;base64,offline-timeline-fixture"
    captured = []

    def offline_render(**kwargs):
        captured.append(kwargs)
        directory = kwargs["output_dir"]
        directory.mkdir(parents=True)
        selected = directory / "source-cover.jpg"
        selected.write_bytes(b"offline source cover")
        return selected, None

    monkeypatch.setattr(api, "render_pro_cover", offline_render)
    request = api.RenderProCoverRequest(
        export_id="export_old", video_path=exports[0]["path"],
        raw_video_path=str(raw) if source == "raw" else None,
        custom_image_data=source_data if source == "timeline" else None,
    )
    response = api.render_pro_cover_endpoint(request, SimpleNamespace(channel_id="main"))
    assert captured[0]["video_path_str"] == exports[0]["path"]
    assert captured[0]["raw_video_path_str"] == (str(raw) if source == "raw" else None)
    assert captured[0]["custom_image_data_str"] == (source_data if source == "timeline" else None)
    assert ExportCoverBindingStore(root).get("main", "export_old")["path"] == response["cover_path"]
    assert ExportCoverBindingStore(root).get("main", "export_new") is None


def _prepare_fixture(workspace, monkeypatch):
    from scripts import api_tiktok_autopost as api
    from scripts.channel_scope import ChannelScope
    from scripts.posting_jobs import PostingJobStore
    root, exports, cover = workspace
    monkeypatch.setattr(api, "BASE_DIR", root)
    monkeypatch.setattr(api, "EXPORTS_DIR", root / "04_Exports")
    monkeypatch.setattr(api, "POSTED_DIR", root / "04_Exports/Posted")
    monkeypatch.setattr(api, "COVERS_DIR", root / "05_Covers_Thumbnails")
    monkeypatch.setattr(api, "_posting_ready", lambda scope: None)
    monkeypatch.setattr(api, "_pending", None)
    registry = SimpleNamespace(lookup=lambda **kwargs: next((r for r in exports if r["id"] == kwargs.get("export_id") and r["channel_id"] == kwargs["channel_id"]), None),
                               latest_for_angle=lambda *args, **kwargs: None)
    monkeypatch.setattr(api, "ExportRegistry", registry)
    jobs = PostingJobStore(root)
    monkeypatch.setattr(api, "_jobs", lambda: jobs)
    scope = ChannelScope("main", "header", False, channel={"id": "main", "handle": "@rizanntry", "revision": 1})
    return api, root, exports, cover, jobs, scope


@pytest.mark.parametrize("problem", ["missing", "changed"])
def test_prepare_invalid_explicit_cover_creates_no_posting_job(workspace, monkeypatch, problem):
    api, root, exports, cover, jobs, scope = _prepare_fixture(workspace, monkeypatch)
    ExportCoverBindingStore(root).save("main", "export_old", exports[0]["path"], {"9:16": cover})
    if problem == "missing":
        cover.unlink()
    else:
        cover.write_bytes(b"changed after selection")
    with pytest.raises(ChannelError) as failure:
        api.prepare(api.PrepareRequest(export_id="export_old", video_path=exports[0]["path"]), scope)
    assert failure.value.code.startswith("export_cover_selection_")
    assert not (root / "_Docs/posting_jobs.json").exists()


def test_prepare_pins_exact_saved_cover_without_sibling_inference(workspace, monkeypatch):
    api, root, exports, cover, jobs, scope = _prepare_fixture(workspace, monkeypatch)
    vertical = cover.with_name("selected_cover.jpg")
    vertical.write_bytes(b"explicit vertical")
    guessed = cover.with_name("selected_cover_3x4.jpg")
    guessed.write_bytes(b"unselected filename sibling")
    chosen = ExportCoverBindingStore(root)
    chosen.save("main", "export_old", exports[0]["path"], {"9:16": vertical})
    response = api.prepare(api.PrepareRequest(export_id="export_old", video_path=exports[0]["path"]), scope)
    job = jobs.get("main", response["job_id"])
    assert Path(job["cover_path"]) == vertical
    assert job["cover_sha256"] == chosen.get("main", "export_old")["sha256"]
    assert job["status"] == "prepared" and job.get("attempt", 0) == 0


def test_prepare_conflicting_cover_rejected_instead_of_silent_override(workspace, monkeypatch):
    api, root, exports, cover, jobs, scope = _prepare_fixture(workspace, monkeypatch)
    ExportCoverBindingStore(root).save("main", "export_old", exports[0]["path"], {"9:16": cover})
    other = cover.with_name("unselected.jpg")
    other.write_bytes(b"other")
    with pytest.raises(ChannelError) as failure:
        api.prepare(api.PrepareRequest(export_id="export_old", video_path=exports[0]["path"], cover_path=str(other)), scope)
    assert failure.value.code == "export_cover_selection_conflict"
    assert not (root / "_Docs/posting_jobs.json").exists()


def test_existing_queue_keeps_original_cover_despite_later_invalid_binding(workspace, monkeypatch):
    from scripts.schedule_store import ScheduleQueueStore
    api, root, exports, cover, jobs, scope = _prepare_fixture(workspace, monkeypatch)
    later = cover.with_name("later.jpg")
    later.write_bytes(b"later explicit cover")
    ExportCoverBindingStore(root).save("main", "export_old", exports[0]["path"], {"9:16": later})
    later.unlink()
    queue = {"id": "queue_old", "channel_id": "main", "export_id": "export_old", "cover_path": str(cover.relative_to(root)), "status": "planned"}
    monkeypatch.setattr(ScheduleQueueStore, "get_item", lambda *args, **kwargs: dict(queue))
    def update(*args, **kwargs):
        args[1](queue, [queue])
        return dict(queue)
    monkeypatch.setattr(ScheduleQueueStore, "update_item", update)
    response = api.prepare(api.PrepareRequest(export_id="export_old", video_path=exports[0]["path"], queue_id="queue_old", cover_path=queue["cover_path"]), scope)
    job = jobs.get("main", response["job_id"])
    assert Path(job["cover_path"]) == cover
    assert queue["cover_path"] == str(cover.relative_to(root))
    assert queue["posting_job_id"] == job["job_id"]


def test_absent_binding_preserves_legacy_cover_resolution(workspace, monkeypatch):
    api, root, exports, cover, jobs, scope = _prepare_fixture(workspace, monkeypatch)
    monkeypatch.setattr(api, "_resolve_cover_for_job", lambda *args, **kwargs: cover)
    response = api.prepare(api.PrepareRequest(export_id="export_old", video_path=exports[0]["path"]), scope)
    assert Path(jobs.get("main", response["job_id"])["cover_path"]) == cover


@pytest.mark.parametrize("frozen_cover", [False, True])
def test_hyperframes_without_binding_uses_exact_package_or_none_never_angle_guess(workspace, monkeypatch, frozen_cover):
    api, root, exports, cover, jobs, scope = _prepare_fixture(workspace, monkeypatch)
    exports[0]["project_name"] = "main/HF_project"
    package = {"export_id": "export_old", "channel_id": "main", "cover_path": None, "source_binding": {"type": "standalone"}, "video_path": exports[0]["path"], "video_sha256": ExportCoverBindingStore._digest(root / exports[0]["path"])}
    if frozen_cover:
        package.update(cover_path=cover.relative_to(root).as_posix(), cover_sha256=ExportCoverBindingStore._digest(cover))
    directory = root / "03_Projects/main/HF_project"
    directory.mkdir(parents=True)
    (directory / "project.json").write_text(json.dumps({"channel_id": "main", "engine": "hyperframes", "publish_package_refs": [package]}), encoding="utf-8")
    wrong = cover.with_name("latest-angle-cover.jpg")
    wrong.write_bytes(b"belongs to a later Angle")
    def forbidden_guess(*args, **kwargs):
        pytest.fail("HyperFrames must never infer a cover from the current Angle")
    monkeypatch.setattr(api, "_resolve_cover_for_job", forbidden_guess)
    monkeypatch.setattr(api, "_prefer_3x4_cover", forbidden_guess)
    response = api.prepare(api.PrepareRequest(export_id="export_old", video_path=exports[0]["path"]), scope)
    job = jobs.get("main", response["job_id"])
    assert job["cover_path"] == (str(cover) if frozen_cover else None)
    assert job["cover_sha256"] == (package["cover_sha256"] if frozen_cover else None)


def test_pending_poll_keeps_explicit_absent_cover_and_job_bytes(workspace, monkeypatch):
    api, root, exports, cover, jobs, scope = _prepare_fixture(workspace, monkeypatch)
    exports[0]["project_name"] = "main/HF_project"
    directory = root / "03_Projects/main/HF_project"
    directory.mkdir(parents=True)
    (directory / "project.json").write_text(json.dumps({"channel_id": "main", "engine": "hyperframes",
        "publish_package_refs": [{"export_id": "export_old", "channel_id": "main", "cover_path": None, "source_binding": {"type": "standalone"}, "video_path": exports[0]["path"], "video_sha256": ExportCoverBindingStore._digest(root / exports[0]["path"])}]}), encoding="utf-8")
    monkeypatch.setattr(api, "_resolve_cover_for_job", lambda *args, **kwargs: pytest.fail("Polling cannot infer a new cover"))
    monkeypatch.setattr(api, "_prefer_3x4_cover", lambda *args, **kwargs: pytest.fail("Polling cannot infer a sibling cover"))
    response = api.prepare(api.PrepareRequest(export_id="export_old", video_path=exports[0]["path"]), scope)
    before = (root / "_Docs/posting_jobs.json").read_bytes()
    pending = api.get_pending(scope)
    assert pending["job_id"] == response["job_id"]
    assert pending["cover_path"] is None and pending["cover_sha256"] is None
    assert (root / "_Docs/posting_jobs.json").read_bytes() == before
    assert jobs.get("main", response["job_id"])["cover_path"] is None


def test_new_queue_records_exact_validated_cover_hash(workspace, monkeypatch):
    from scripts import api_schedule_queue as queue_api
    root, exports, cover = workspace
    monkeypatch.setattr(queue_api, "BASE_DIR", root)
    payload = queue_api.QueueItemPayload(video_path=exports[0]["path"], scheduled_at="2026-10-20T09:00:00+07:00", cover_path=str(cover))
    row = queue_api._build_record(payload, root / exports[0]["path"], "export_old", set(), set(), "main")
    assert row["cover_path"] == cover.relative_to(root).as_posix()
    assert row["cover_sha256"] == ExportCoverBindingStore._digest(cover)


def test_new_queue_hash_drift_rejected_before_posting_job(workspace, monkeypatch):
    from scripts import api_schedule_queue as queue_api
    from scripts.schedule_store import ScheduleQueueStore
    api, root, exports, cover, jobs, scope = _prepare_fixture(workspace, monkeypatch)
    monkeypatch.setattr(queue_api, "BASE_DIR", root)
    payload = queue_api.QueueItemPayload(video_path=exports[0]["path"], scheduled_at="2026-10-20T09:00:00+07:00", cover_path=str(cover))
    row = queue_api._build_record(payload, root / exports[0]["path"], "export_old", set(), set(), "main")
    cover.write_bytes(b"changed after the queue was reviewed")
    monkeypatch.setattr(ScheduleQueueStore, "get_item", lambda *args, **kwargs: dict(row))
    with pytest.raises(ChannelError) as failure:
        api.prepare(api.PrepareRequest(export_id="export_old", video_path=exports[0]["path"], queue_id=row["id"], cover_path=row["cover_path"]), scope)
    assert failure.value.code == "posting_queue_cover_changed"
    assert not (root / "_Docs/posting_jobs.json").exists()


def test_new_queue_rejects_other_channel_cover(workspace, monkeypatch):
    from scripts import api_schedule_queue as queue_api
    root, exports, cover = workspace
    monkeypatch.setattr(queue_api, "BASE_DIR", root)
    payload = queue_api.QueueItemPayload(video_path=exports[0]["path"], scheduled_at="2026-10-20T09:00:00+07:00", cover_path=str(cover))
    with pytest.raises(ChannelError) as failure:
        queue_api._build_record(payload, root / exports[0]["path"], "export_old", set(), set(), "second")
    assert failure.value.code == "resource_not_found"


def test_queue_cannot_capture_changed_selected_cover_as_new_approved_hash(workspace, monkeypatch):
    from scripts import api_schedule_queue as queue_api
    root, exports, cover = workspace
    monkeypatch.setattr(queue_api, "BASE_DIR", root)
    store = ExportCoverBindingStore(root)
    store.save("main", "export_old", exports[0]["path"], selections={"9:16": cover.relative_to(root).as_posix()})
    cover.write_bytes(b"changed after Gallery loaded the selection")
    payload = queue_api.QueueItemPayload(video_path=exports[0]["path"], scheduled_at="2026-10-20T09:00:00+07:00", cover_path=str(cover))
    with pytest.raises(ChannelError) as failure:
        queue_api._build_record(payload, root / exports[0]["path"], "export_old", set(), set(), "main")
    assert failure.value.code == "export_cover_selection_changed"
