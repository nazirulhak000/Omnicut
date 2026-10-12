"""Offline P3-C HTTP media/bytes ownership and dispatch boundaries."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from scripts import config, api_videos, api_voice, api_proxy, api_asset_dedup, api_background_isolation, proxy_manager, product_store, project_manifest, task_manager
from scripts.channel_scope import ChannelScope
from scripts.channel_workflows import get_workflow_scope
from scripts.channel_artifacts import register

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.delenv(config.MULTI_CHANNEL_STRICT_ENV, raising=False)
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    for module in [api_videos, api_voice, api_proxy, product_store]:
        monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    for name in ["RAW_DIR", "INBOX_DIR", "ASSETS_DIR", "EXPORTS_DIR", "ARCHIVE_DIR"]:
        family = {"RAW_DIR": "01_Raw", "INBOX_DIR": "00_Inbox", "ASSETS_DIR": "02_Assets", "EXPORTS_DIR": "04_Exports", "ARCHIVE_DIR": "06_Archive"}[name]
        folder = tmp_path / family; folder.mkdir()
        monkeypatch.setattr(api_videos, name, folder)
        monkeypatch.setattr(config, name, folder)
    monkeypatch.setattr(api_proxy, "CAPCUT_DRAFT_DIR", tmp_path / "drafts")
    monkeypatch.setattr(api_videos, "CAPCUT_DRAFT_DIR", tmp_path / "drafts")
    projects = tmp_path / "03_Projects"; projects.mkdir()
    for module in [proxy_manager, api_background_isolation, project_manifest]:
        monkeypatch.setattr(module, "PROJECTS_DIR", projects)
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs/products.json")
    monkeypatch.setattr(task_manager, "TASKS_FILE", tmp_path / "_Docs/tasks.json")
    monkeypatch.setattr(task_manager.TaskManager, "_initialized", False)
    monkeypatch.setattr(task_manager.TaskManager, "_tasks", {})
    api_proxy._IN_FLIGHT.clear()
    app = FastAPI()
    @app.middleware("http")
    async def pin_scope(request, call_next):
        owner = request.headers.get("X-OmniCut-Channel") or request.query_params.get("channel") or "main"
        request.state.channel_scope = ChannelScope(owner, "header" if request.headers.get("X-OmniCut-Channel") else "default", False, channel={"id": owner, "status": "active", "revision": 4, "identity_hash": "captured"})
        return await call_next(request)
    def scope(request: Request):
        return request.state.channel_scope
    app.dependency_overrides[get_workflow_scope] = scope
    for module in [api_videos, api_voice, api_proxy, api_asset_dedup, api_background_isolation]:
        app.include_router(module.router)
    product_store._TABLE.save([{"id": "foreign", "channel_id": "second", "name": "Foreign", "videos": [{"path": "01_Raw/shared.mp4"}]}])
    raw = tmp_path / "01_Raw/shared.mp4"; raw.write_bytes(b"shared bytes")
    foreign = tmp_path / "04_Exports/private.mp4"; foreign.write_bytes(b"private bytes")
    register(foreign, "second")
    yield tmp_path, TestClient(app), raw, foreign
    api_proxy._IN_FLIGHT.clear()


def test_media_shared_bytes_and_private_owner(env):
    root, client, raw, foreign = env
    assert client.get("/api/media/01_Raw/shared.mp4").content == b"shared bytes"
    assert client.get("/api/media/04_Exports/private.mp4").status_code == 404
    response = client.get("/api/media/04_Exports/private.mp4?channel=second")
    assert response.status_code == 200 and response.content == b"private bytes"
    assert client.post("/api/reveal-file", json={"file_path": str(foreign)}).status_code == 404
    assert client.post("/api/delete-file", json={"file_path": str(foreign)}).status_code == 404
    assert foreign.read_bytes() == b"private bytes"


def test_upload_and_shared_mutation_refuse_foreign_metadata_before_write(env):
    root, client, raw, _ = env
    response = client.post("/api/upload", data={"target_dir": "raw", "product_id": "foreign"}, files={"file": ("video.mp4", b"offline", "video/mp4")})
    assert response.status_code == 404
    assert not (root / "01_Raw/foreign").exists()
    assert client.post("/api/videos/rename", json={"video_path": str(raw), "new_name": "renamed"}).status_code == 404
    assert client.post("/api/raw-vault/batch-delete", json={"video_paths": [str(raw)]}).status_code == 404
    assert client.post("/api/assets/duplicates/clean", json={"duplicate_paths": [str(raw)]}).status_code == 404
    assert raw.read_bytes() == b"shared bytes"
    assert not (root / "06_Archive/.trash").exists()


def test_proxy_foreign_source_refused_and_cache_namespace_disjoint(env):
    root, client, raw, foreign = env
    assert client.get("/api/proxy/for-clip", params={"source_path": str(foreign)}).status_code == 404
    assert not api_proxy._IN_FLIGHT
    assert proxy_manager.proxy_path_for(raw, channel_id="main") != proxy_manager.proxy_path_for(raw, channel_id="second")
    response = client.get("/api/proxy/for-clip", params={"source_path": str(raw), "build": False}, headers={"X-OmniCut-Channel": "second"})
    assert response.status_code == 200
    assert response.json()["master_url"].endswith("?channel=second")
    assert not (root / "03_Projects/.cache").exists()


def test_transcription_guards_source_and_writes_only_owned_companions(env, monkeypatch):
    root, client, raw, foreign = env
    called = []
    def run(cmd, **kwargs):
        called.append(cmd)
        output = Path(cmd[cmd.index("--outdir") + 1])
        (output / (Path(cmd[2]).stem + "-sub.srt")).write_text("owned subtitles", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="offline", stderr="")
    monkeypatch.setattr(api_voice.subprocess, "run", run)
    assert client.post("/api/sub-srt/transcribe", json={"media_path": str(foreign)}).status_code == 404
    assert called == []
    response = client.post("/api/sub-srt/transcribe", json={"media_path": str(raw)})
    assert response.status_code == 200, response.text
    assert response.json()["srt_url"].endswith("?channel=main")
    assert client.get(response.json()["srt_url"]).status_code == 200
    srt = Path(response.json()["srt_path"])
    assert srt.is_relative_to(root / "03_Projects/main/_Transcripts")
    assert raw.read_bytes() == b"shared bytes"
    assert not raw.with_name("shared-sub.srt").exists()
    assert client.get("/api/media/" + srt.relative_to(root).as_posix(), headers={"X-OmniCut-Channel": "second"}).status_code == 404


def test_cutout_dispatch_foreign_source_and_channel_coalescing(env, monkeypatch):
    root, client, raw, foreign = env
    submitted = []
    monkeypatch.setattr(task_manager.TaskManager, "run_in_background", lambda fn: submitted.append(fn))
    payload = {"source_path": str(foreign), "config": {"enabled": True}, "duration": 1}
    assert client.post("/api/background-isolation/process", json=payload).status_code == 404
    assert submitted == []
    payload["source_path"] = str(raw)
    main = client.post("/api/background-isolation/process", json=payload)
    second = client.post("/api/background-isolation/process", json=payload, headers={"X-OmniCut-Channel": "second"})
    assert main.status_code == second.status_code == 200
    assert main.json()["task_id"] != second.json()["task_id"]
    task = task_manager.TaskManager.get_task(second.json()["task_id"], channel_id="second")
    assert task["channel_identity_snapshot"]["id"] == "second"
    assert task["channel_revision"] == 4
    assert len(submitted) == 2


def test_cutout_artifact_routes_enforce_persisted_owner(env):
    from scripts.background_isolation_sequence_artifacts import build_sequence_artifact_id, build_sequence_manifest, write_sequence_frame, write_sequence_manifest, sequence_paths
    from scripts.background_isolation_sequence_worker import DERIVED_CACHE_NAMESPACE
    root, client, _, _ = env
    cache = root / "03_Projects/.cache"
    artifact_id = build_sequence_artifact_id("offline-source")
    write_sequence_frame(cache, artifact_id, 0, bytes.fromhex("89504e470d0a1a0a") + b"offline", namespace=DERIVED_CACHE_NAMESPACE)
    manifest = build_sequence_manifest(artifact_id, source_fingerprint="offline-source", frame_count=1, fps=30, timebase="1/30", width=1, height=1, status="ready")
    write_sequence_manifest(cache, artifact_id, manifest, namespace=DERIVED_CACHE_NAMESPACE)
    directory = sequence_paths(cache, artifact_id, namespace=DERIVED_CACHE_NAMESPACE).directory
    for path in directory.rglob("*"):
        if path.is_file(): register(path, "second")
    base = "/api/background-isolation/sequences/" + artifact_id
    assert client.get(base + "/manifest").status_code == 404
    assert client.get(base + "/frames/0").status_code == 404
    headers = {"X-OmniCut-Channel": "second"}
    assert client.get(base + "/manifest", headers=headers).status_code == 200
    assert client.get(base + "/frames/0", headers=headers).status_code == 200


def test_cutout_recovery_hands_worker_persisted_owner_without_registry_relookup(env, monkeypatch):
    root, client, raw, _ = env
    task_manager.TaskManager.create_task("background_isolation", "offline", task_id="recover", payload={"source_path": str(raw), "config": {"enabled": True}}, channel_id="second", job_scope={"channel_id": "second", "channel_revision": 8, "channel_identity_snapshot": {"id": "second", "status": "active", "identity_hash": "original"}})
    work = []
    monkeypatch.setattr(task_manager.TaskManager, "run_in_background", lambda fn: work.append(fn))
    received = []
    monkeypatch.setattr(api_background_isolation, "_run_background_isolation_task", lambda *args, **kwargs: received.append(kwargs))
    api_background_isolation._BACKGROUND_TASKS_RUNNING.clear()
    assert api_background_isolation.recover_background_isolation_tasks() == 1
    work[0]()
    assert received[0]["channel_id"] == "second"
    assert received[0]["job_scope"]["channel_revision"] == 8
    assert received[0]["job_scope"]["channel_identity_snapshot"]["identity_hash"] == "original"


def test_voice_previews_are_channel_owned_unique_artifacts(env, monkeypatch):
    root, client, _, _ = env
    def generate(**kwargs):
        Path(kwargs["output_audio_path"]).write_bytes(b"offline voice")
        return True
    monkeypatch.setattr(api_voice.VoiceEngine, "generate_crystal_voice", generate)
    monkeypatch.setattr(api_voice, "measure_wav_duration", lambda path: 1)
    payload = {"text": "Official preview", "voice_gender": "male"}
    first = client.post("/api/voice/preview", json=payload, headers={"X-OmniCut-Channel": "second"})
    second = client.post("/api/voice/preview", json=payload, headers={"X-OmniCut-Channel": "second"})
    assert first.status_code == second.status_code == 200
    assert first.json()["audio_url"] != second.json()["audio_url"]
    url = first.json()["audio_url"]
    assert url.endswith("?channel=second")
    assert client.get(url.split("?")[0]).status_code == 404
    assert client.get(url).content == b"offline voice"
    assert not (root / "test_voice.wav").exists()
