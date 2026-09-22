from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

import scripts.api_background_isolation as api
from scripts.background_isolation_sequence_artifacts import (
    build_sequence_artifact_id,
    build_sequence_manifest,
    sequence_paths,
    write_sequence_frame,
    write_sequence_manifest,
)
from scripts.background_isolation_sequence_worker import DERIVED_CACHE_NAMESPACE


PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0dIDAT\x08\xd7"
    b"c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[TestClient, Path]:
    project_root = tmp_path / "project"
    cache_root = project_root / ".cache"
    monkeypatch.setattr(api, "PROJECTS_DIR", project_root)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app), cache_root


def test_background_isolation_cancel_bridge_signals_and_cleans_event_registry():
    api._BACKGROUND_TASK_CANCEL_EVENTS.clear()
    event = threading.Event()
    api._BACKGROUND_TASK_CANCEL_EVENTS["task-1"] = event

    assert api.request_background_isolation_cancel("task-1") is True
    assert event.is_set()
    assert api.request_background_isolation_cancel("missing") is False

    api._BACKGROUND_TASK_CANCEL_EVENTS.pop("task-1", None)


def _ready_sequence(cache_root: Path, frame_count: int = 2) -> tuple[str, dict]:
    artifact_id = build_sequence_artifact_id("source-fingerprint")
    for index in range(frame_count):
        write_sequence_frame(cache_root, artifact_id, index, PNG_1X1, namespace=DERIVED_CACHE_NAMESPACE)
    manifest = build_sequence_manifest(
        artifact_id,
        source_fingerprint="source-fingerprint",
        frame_count=frame_count,
        fps=30.0,
        timebase="1/30",
        width=1,
        height=1,
        status="ready",
    )
    write_sequence_manifest(cache_root, artifact_id, manifest, namespace=DERIVED_CACHE_NAMESPACE)
    return artifact_id, manifest


def test_manifest_and_frame_return_only_ready_derived_artifacts(monkeypatch, tmp_path):
    client, cache_root = _client(monkeypatch, tmp_path)
    artifact_id, manifest = _ready_sequence(cache_root)

    manifest_response = client.get(f"/api/background-isolation/sequences/{artifact_id}/manifest")
    assert manifest_response.status_code == 200
    assert manifest_response.json() == manifest
    assert "source_fingerprint" in manifest_response.json()

    frame_response = client.get(f"/api/background-isolation/sequences/{artifact_id}/frames/0")
    assert frame_response.status_code == 200
    assert frame_response.headers["content-type"].startswith("image/png")
    assert frame_response.content == PNG_1X1

    canonical_frame_response = client.get(
        f"/api/background-isolation/sequences/{artifact_id}/frames/frame_000000.png"
    )
    assert canonical_frame_response.status_code == 200
    assert canonical_frame_response.headers["content-type"].startswith("image/png")
    assert canonical_frame_response.content == PNG_1X1


@pytest.mark.parametrize("status", ["missing", "stale", "processing", "error", "cancelled"])
def test_manifest_and_frame_hide_non_ready_sequences(monkeypatch, tmp_path, status):
    client, cache_root = _client(monkeypatch, tmp_path)
    artifact_id = build_sequence_artifact_id("non-ready")
    if status != "missing":
        paths = sequence_paths(cache_root, artifact_id, namespace=DERIVED_CACHE_NAMESPACE)
        paths.frames.mkdir(parents=True)
        write_sequence_frame(cache_root, artifact_id, 0, PNG_1X1, namespace=DERIVED_CACHE_NAMESPACE)
        manifest = build_sequence_manifest(
            artifact_id,
            source_fingerprint="non-ready",
            frame_count=1,
            fps=30.0,
            timebase="1/30",
            width=1,
            height=1,
            status=status,
        )
        (paths.manifest.parent).mkdir(parents=True, exist_ok=True)
        paths.manifest.write_text(json.dumps(manifest), encoding="utf-8")

    assert client.get(f"/api/background-isolation/sequences/{artifact_id}/manifest").status_code == 404
    assert client.get(f"/api/background-isolation/sequences/{artifact_id}/frames/0").status_code == 404


@pytest.mark.parametrize("artifact_id", ["", "../bgseq1-0000000000000000", "bgseq1-INVALID", "bgiso1-0000000000000000"])
def test_invalid_artifact_id_is_bad_request(monkeypatch, tmp_path, artifact_id):
    client, _cache_root = _client(monkeypatch, tmp_path)
    assert client.get(f"/api/background-isolation/sequences/{artifact_id}/manifest").status_code in {400, 404}


@pytest.mark.parametrize("frame_index", ["-1", "abc", "1.5", "1000000", "frame_000001.jpg", "frame_00001.png"])
def test_invalid_frame_index_is_bad_request(monkeypatch, tmp_path, frame_index):
    client, cache_root = _client(monkeypatch, tmp_path)
    artifact_id, _manifest = _ready_sequence(cache_root)
    response = client.get(f"/api/background-isolation/sequences/{artifact_id}/frames/{frame_index}")
    assert response.status_code == 400


def test_valid_but_missing_frame_is_not_found(monkeypatch, tmp_path):
    client, cache_root = _client(monkeypatch, tmp_path)
    artifact_id, _manifest = _ready_sequence(cache_root, frame_count=1)
    assert client.get(f"/api/background-isolation/sequences/{artifact_id}/frames/1").status_code == 404


def test_non_png_or_symlink_frame_is_not_served(monkeypatch, tmp_path):
    client, cache_root = _client(monkeypatch, tmp_path)
    artifact_id, _manifest = _ready_sequence(cache_root, frame_count=1)
    frame_path = sequence_paths(cache_root, artifact_id, namespace=DERIVED_CACHE_NAMESPACE).frames / "frame_000000.png"
    frame_path.write_bytes(b"not png")
    assert client.get(f"/api/background-isolation/sequences/{artifact_id}/frames/0").status_code == 404

    outside = tmp_path / "outside.png"
    outside.write_bytes(PNG_1X1)
    frame_path.unlink()
    try:
        frame_path.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    assert client.get(f"/api/background-isolation/sequences/{artifact_id}/frames/0").status_code == 404


def test_cache_root_symlink_is_rejected(monkeypatch, tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside-cache"
    outside.mkdir()
    try:
        (project_root / ".cache").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    monkeypatch.setattr(api, "PROJECTS_DIR", project_root)
    app = FastAPI()
    app.include_router(api.router)
    response = TestClient(app).get(
        "/api/background-isolation/sequences/bgseq1-0000000000000000/manifest"
    )
    assert response.status_code == 500


def test_raw_or_assets_like_paths_are_never_accepted(monkeypatch, tmp_path):
    client, cache_root = _client(monkeypatch, tmp_path)
    raw = tmp_path / "01_Raw"
    assets = tmp_path / "02_Assets"
    raw.mkdir()
    assets.mkdir()
    (raw / "secret.png").write_bytes(PNG_1X1)
    (assets / "secret.png").write_bytes(PNG_1X1)
    artifact_id = build_sequence_artifact_id("protected-path")
    assert client.get(f"/api/background-isolation/sequences/{artifact_id}/manifest").status_code == 404
    assert not (cache_root / "background-isolation-sequences").exists()


def test_process_rejects_missing_source_and_disabled_config(monkeypatch, tmp_path):
    client, _cache_root = _client(monkeypatch, tmp_path)
    missing = client.post(
        "/api/background-isolation/process",
        json={"source_path": str(tmp_path / "missing.mp4"), "config": {"enabled": True}},
    )
    assert missing.status_code == 404

    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    disabled = client.post(
        "/api/background-isolation/process",
        json={"source_path": str(source), "config": {"enabled": False}},
    )
    assert disabled.status_code == 422


def test_process_rejects_non_media_and_symlink_escape_sources(monkeypatch, tmp_path):
    client, _cache_root = _client(monkeypatch, tmp_path)
    secret = tmp_path.parent / "outside-background-source.mp4"
    secret.write_bytes(b"fixture")
    link = tmp_path / "project" / "escape.mp4"
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(secret)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    escaped = client.post(
        "/api/background-isolation/process",
        json={"source_path": str(link), "config": {"enabled": True}},
    )
    assert escaped.status_code == 404

    non_media = tmp_path / "notes.txt"
    non_media.write_text("not a video", encoding="utf-8")
    rejected = client.post(
        "/api/background-isolation/process",
        json={"source_path": str(non_media), "config": {"enabled": True}},
    )
    assert rejected.status_code == 404


def test_process_rejects_invalid_rotation(monkeypatch, tmp_path):
    client, _cache_root = _client(monkeypatch, tmp_path)
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    response = client.post(
        "/api/background-isolation/process",
        json={
            "source_path": str(source),
            "config": {"enabled": True},
            "rotation": 45,
        },
    )
    assert response.status_code == 422


def test_preflight_validates_source_and_returns_actionable_capacity_result(monkeypatch, tmp_path):
    client, _cache_root = _client(monkeypatch, tmp_path)
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    captured = {}

    def fake_preflight(req, resolved_source):
        captured["request"] = req
        captured["source"] = resolved_source
        return {
            "ok": True,
            "frame_count": 60,
            "estimated_cache_bytes": 123,
            "issues": [],
        }

    monkeypatch.setattr(api, "_background_isolation_preflight", fake_preflight)
    response = client.post(
        "/api/background-isolation/preflight",
        json={
            "source_path": str(source),
            "config": {"enabled": True, "model": "u2net"},
            "start": 8.0,
            "duration": 2.0,
            "fps": 30,
        },
    )

    assert response.status_code == 200
    assert response.json()["frame_count"] == 60
    assert captured["source"] == source.resolve()
    assert captured["request"].config["enabled"] is True
    assert captured["request"].config["model"] == "u2net"


def test_source_sequence_identity_changes_across_trim_windows():
    normalized = api.normalize_background_isolation({"enabled": True})
    first = api._source_sequence_id(
        "sha256:source",
        normalized,
        start=1.0,
        duration=2.0,
        fps=30.0,
        timebase="1/30",
        width=1080,
        height=1920,
        rotation=0,
    )
    second = api._source_sequence_id(
        "sha256:source",
        normalized,
        start=8.0,
        duration=2.0,
        fps=30.0,
        timebase="1/30",
        width=1080,
        height=1920,
        rotation=0,
    )

    assert first != second
    assert first.startswith("bgseq1-")


def test_request_identity_includes_trim_window(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    normalized = api.normalize_background_isolation({"enabled": True})

    first = api._request_identity(
        source,
        normalized,
        api.BackgroundIsolationProcessRequest(source_path=str(source), start=1.0, duration=2.0),
    )
    second = api._request_identity(
        source,
        normalized,
        api.BackgroundIsolationProcessRequest(source_path=str(source), start=8.0, duration=2.0),
    )

    assert first != second


def test_worker_threads_requested_window_into_extraction_and_published_manifest(monkeypatch, tmp_path):
    project_root = tmp_path / "03_Projects"
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    output = tmp_path / "derived"
    output.mkdir()
    captured = {}

    monkeypatch.setattr(api, "PROJECTS_DIR", project_root)
    monkeypatch.setattr(api.TaskManager, "update_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(api.TaskManager, "fail_task", lambda *args, **kwargs: pytest.fail(str(args)))
    monkeypatch.setattr(api.TaskManager, "complete_task", lambda task_id, result, **kwargs: captured.update(result=result))
    monkeypatch.setattr(api, "write_sequence_manifest", lambda *args, **kwargs: None)

    def fake_extract(*args, **kwargs):
        captured["extract"] = kwargs
        return {
            "status": "ready",
            "sequence_dir": str(tmp_path / "source-sequence"),
            "frame_count": 60,
            "start": kwargs["start"],
            "duration": kwargs["duration"],
        }

    def fake_process(_source, _cache, _config, source_manifest, **_kwargs):
        captured["source_manifest"] = source_manifest
        artifact_id = "bgseq1-0123456789abcdef"
        manifest = build_sequence_manifest(
            artifact_id,
            source_fingerprint=source_manifest["source_fingerprint"],
            frame_count=60,
            fps=30,
            timebase="1/30",
            width=1080,
            height=1920,
            source_start=source_manifest["source_start"],
            source_duration=source_manifest["source_duration"],
            status="ready",
        )
        (output / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return {"status": "ready", "artifact_id": artifact_id, "output_directory": str(output)}

    monkeypatch.setattr(api, "extract_background_isolation_sequence", fake_extract)
    monkeypatch.setattr(api, "process_background_isolation_sequence", fake_process)

    api._run_background_isolation_task(
        "task-window",
        api.BackgroundIsolationProcessRequest(
            source_path=str(source),
            config={"enabled": True},
            start=8.0,
            duration=2.0,
        ),
        threading.Event(),
    )

    assert captured["extract"]["start"] == 8.0
    assert captured["extract"]["duration"] == 2.0
    assert captured["source_manifest"]["source_start"] == 8.0
    assert captured["source_manifest"]["source_duration"] == 2.0
    assert captured["result"]["artifact"]["source_start"] == 8.0
    assert captured["result"]["sequence"]["source_duration"] == 2.0


def test_background_task_scheduler_deduplicates_recovery_launches(monkeypatch):
    submitted = []
    ran = []
    task = {"id": "task-1", "status": "queued"}
    req = api.BackgroundIsolationProcessRequest(source_path="clip.mov")

    monkeypatch.setattr(api.TaskManager, "get_task", lambda task_id: task if task_id == "task-1" else None)
    monkeypatch.setattr(api.TaskManager, "run_in_background", lambda fn: submitted.append(fn))
    monkeypatch.setattr(api, "_run_background_isolation_task", lambda task_id, value: ran.append((task_id, value.source_path)))

    assert api._schedule_background_isolation_task("task-1", req) is True
    assert api._schedule_background_isolation_task("task-1", req) is False
    assert len(submitted) == 1

    submitted[0]()
    assert ran == [("task-1", "clip.mov")]


def test_process_coalesces_identical_active_requests(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJECTS_DIR", tmp_path / "project")
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    active = []
    created = []

    def create_task(*args, **kwargs):
        created.append(kwargs)
        active.append({"id": kwargs["task_id"], "type": args[0], "status": "queued", "payload": kwargs["payload"]})

    monkeypatch.setattr(api.TaskManager, "get_active_tasks", lambda limit=1000: list(active))
    monkeypatch.setattr(api.TaskManager, "create_task", create_task)
    monkeypatch.setattr(api, "_schedule_background_isolation_task", lambda *args: True)
    req = api.BackgroundIsolationProcessRequest(source_path=str(source), config={"enabled": True})

    first = api.process_background_isolation(req, BackgroundTasks())
    second = api.process_background_isolation(req, BackgroundTasks())
    assert first["task_id"] == second["task_id"]
    assert len(created) == 1
