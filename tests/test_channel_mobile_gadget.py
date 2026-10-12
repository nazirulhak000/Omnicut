"""P3-D offline owner boundaries and pinned worker handoff."""
import json
import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient
from scripts import api_recording, api_shot_lists, api_mobile_studio, api_gadget_media, api_gadget_media_projects
from scripts import product_store, recording_sessions, shot_lists_store, config
from scripts.channel_scope import ChannelScope
from scripts.channel_scope import channel_error_handler
from scripts.channel_workflows import get_workflow_scope
from scripts.channel_store import ChannelError
from scripts.gadget_media_campaign import CampaignStore, create_starter_campaign
from scripts.gadget_media_repository import GadgetMediaRepository
from scripts.gadget_media_paths import GadgetMediaRoots
from scripts.product_store import ProductStore
from scripts.shot_lists_store import ShotListsStore
from scripts.recording_sessions import RecordingSessionStore

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.delenv(config.MULTI_CHANNEL_STRICT_ENV, raising=False)
    for module, name in [(product_store, "products"), (recording_sessions, "recording_sessions"), (shot_lists_store, "shot_lists")]:
        monkeypatch.setattr(module, "STORE_PATH", tmp_path / "_Docs" / (name + ".json"))
    monkeypatch.setattr(api_recording, "_SEGMENTS_DIR", tmp_path / "segments")
    campaigns = tmp_path / "_Docs/campaigns.json"
    for module in [api_gadget_media, api_gadget_media_projects]:
        monkeypatch.setattr(module, "CAMPAIGNS_FILE", campaigns)
    from scripts import project_manifest
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "03_Projects")
    repo = GadgetMediaRepository(GadgetMediaRoots.under(tmp_path))
    monkeypatch.setattr(api_gadget_media_projects, "PROJECT_REPOSITORY", repo)
    monkeypatch.setattr(api_gadget_media_projects, "BASE_DIR", tmp_path)
    def scope(channel: str = Header(None, alias="X-OmniCut-Channel")):
        owner = channel or "main"
        return ChannelScope(owner, "header" if channel else "default", False, channel={"id": owner, "status": "active", "identity_snapshot": {}, "revision": 1})
    app = FastAPI()
    app.add_exception_handler(ChannelError, channel_error_handler)
    app.dependency_overrides[get_workflow_scope] = scope
    for module in [api_recording, api_shot_lists, api_mobile_studio, api_gadget_media, api_gadget_media_projects]:
        app.include_router(module.router)
    rows = [{"id": owner, "channel_id": owner, "name": owner, "angles": [{"angle_id": "angle", "script_lines": ["Official line"]}]} for owner in ["main", "second"]]
    product_store._TABLE.save(rows)
    return tmp_path, TestClient(app), repo, campaigns


@pytest.mark.parametrize("status", ["draft", "archived"])
@pytest.mark.parametrize("endpoint,payload", [
    ("/api/recording-sessions", {"product_id": "main", "angle_id": "angle"}),
    ("/api/products/main/angles/angle/shot-list", {}),
    ("/api/mobile-studio/assemble", {"product_id": "main", "angle_id": "angle"}),
    ("/api/gadget-media/campaigns", {"name": "Blocked"}),
    ("/api/gadget-media/projects", {"brand": "Fixture", "model": "Exact"}),
])
def test_implicit_main_lifecycle_blocks_new_work_before_writes(env, status, endpoint, payload):
    root, client, repo, campaigns = env
    before_products = product_store._TABLE.load()
    before_sessions = recording_sessions._TABLE.load()
    before_shots = shot_lists_store._TABLE.load()
    client.app.dependency_overrides[get_workflow_scope] = lambda: ChannelScope(
        "main", "default", False, channel={"id": "main", "status": status})
    response = client.post(endpoint, json=payload)
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "channel_not_active"
    assert product_store._TABLE.load() == before_products
    assert recording_sessions._TABLE.load() == before_sessions
    assert shot_lists_store._TABLE.load() == before_shots
    assert not campaigns.exists()
    assert repo.list() == []


def plan(owner):
    return ShotListsStore.upsert({"product_id": owner, "angle_id": "angle", "shot_list": [{"beat_index": 0, "role": "hook", "start": 0, "end": 1, "planned_duration": 1}]}, channel_id=owner)


def test_gadget_draft_identity_survives_profile_change_and_presentation_updates(env):
    from scripts.channel_identity import project_channel_identity
    from tests.test_channel_identity import profile
    root, client, repo, _campaigns = env
    row = profile(root)
    expected = project_channel_identity(row)
    client.app.dependency_overrides[get_workflow_scope] = lambda: ChannelScope("second", "header", False, channel=row)
    created = client.post("/api/gadget-media/projects", json={"project_id": "frozen-draft", "brand": "Fixture", "model": "Exact"})
    assert created.status_code == 201, created.text
    assert created.json()["presentation"]["channel_identity_snapshot"] == expected
    row["watermark_text"] = "New live profile"
    patched = client.patch("/api/gadget-media/projects/frozen-draft", json={"presentation": {"mode": "product_only"}})
    assert patched.status_code == 200, patched.text
    assert patched.json()["presentation"]["channel_identity_snapshot"] == expected
    forged = {**expected, "watermark_text": "Forged"}
    rejected = client.patch("/api/gadget-media/projects/frozen-draft", json={"presentation": {"channel_identity_snapshot": forged}})
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "channel_identity_immutable"
    stored = repo.for_channel("second").get("frozen-draft")
    assert stored.presentation["channel_identity_snapshot"] == expected
    repo.for_channel("second").save_timeline("frozen-draft", {"workspace_scope": "gadget_media", "project_id": "frozen-draft", "clips": [], "cues": [], "overlays": []})
    preview = client.get("/api/gadget-media/projects/frozen-draft/timeline")
    assert preview.status_code == 200
    assert preview.json()["channel_id"] == "second"
    assert preview.json()["channel_identity_snapshot"] == expected


def test_shot_and_recording_parent_owner_before_mutation(env):
    root, client, repo, campaigns = env
    plan("second")
    before = shot_lists_store._TABLE.load()
    with pytest.raises(ChannelError) as err:
        ShotListsStore.upsert({"product_id": "second", "angle_id": "angle", "shot_list": []}, channel_id="main")
    assert err.value.status_code == 404
    assert shot_lists_store._TABLE.load() == before
    assert ShotListsStore.get("second", "angle", channel_id="main") is None
    session = RecordingSessionStore.create("second", "angle", channel_id="second")
    assert session["channel_id"] == "second"
    assert client.get("/api/recording-sessions/" + session["id"]).status_code == 404
    response = client.post("/api/recording-sessions/" + session["id"] + "/segments", data={"beat_index": 0}, files={"file": ("clip.webm", b"offline bytes", "video/webm")})
    assert response.status_code == 404, response.text
    assert not (root / "segments").exists()
    assert client.delete("/api/recording-sessions/" + session["id"] + "/segments/0").status_code == 404
    assert RecordingSessionStore.get(session["id"], channel_id="second")["segments"][0]["status"] == "pending"


def test_mobile_catalog_and_token_cannot_rescope(env):
    root, client, _, _ = env
    plan("second")
    session = RecordingSessionStore.create("second", "angle", channel_id="second")
    response = client.get("/api/mobile-studio/catalog")
    assert response.status_code == 200
    assert "second" not in json.dumps(response.json())
    response = client.post("/api/mobile-studio/assemble", json={"product_id": "main", "angle_id": "angle", "session_id": session["id"]})
    assert response.status_code == 404, response.text
    assert client.post("/api/recording-sessions", json={"product_id": "second", "angle_id": "angle", "channel_id": "second"}).status_code == 422


def test_gadget_campaign_nested_write_preserves_foreign_and_link_guard(env):
    _, client, repo, path = env
    for owner in ["main", "second"]:
        CampaignStore(path, channel_id=owner).create(create_starter_campaign(owner, campaign_id=owner))
    before = CampaignStore(path, channel_id="second").get("second").to_dict()
    assert client.patch("/api/gadget-media/campaigns/main/slots/gadget-01", json={"script": "Updated"}).status_code == 200
    assert CampaignStore(path, channel_id="second").get("second").to_dict() == before
    assert len(client.get("/api/gadget-media/campaigns").json()["campaigns"]) == 1
    project = repo.for_channel("second").create({"brand": "Brand", "model": "Model"}, project_id="foreign-project")
    response = client.patch("/api/gadget-media/campaigns/main/slots/gadget-01", json={"product_project_id": project.project_id})
    assert response.status_code == 404, response.text
    assert CampaignStore(path, channel_id="main").get("main").slots[0].product_project_id is None


def test_gadget_facade_private_reads_and_writes_fail_closed(env):
    root, client, repo, _ = env
    project = repo.for_channel("second").create({"brand": "Brand", "model": "Model"}, project_id="second-project")
    timeline_path = repo.roots.project_dir(project.project_id) / "timeline.json"
    timeline_path.write_text(json.dumps({"secret": "second"}), encoding="utf-8")
    with pytest.raises(ChannelError):
        repo.for_channel("main").load_timeline(project.project_id)
    assert client.get("/api/gadget-media/projects/second-project").status_code == 404
    assert client.patch("/api/gadget-media/projects/second-project", json={"audience": "Bad"}).status_code == 404
    assert client.get("/api/gadget-media/projects").json()["projects"] == []
    assert repo.for_channel("second").get(project.project_id).audience == ""
    assert project.channel_id == "second"


def test_project_patch_rejects_foreign_generated_reference_before_save(env):
    root, client, repo, _ = env
    own = repo.for_channel("main").create({"brand": "B", "model": "M"}, project_id="main-project")
    foreign = repo.for_channel("second").create({"brand": "B", "model": "M"}, project_id="other-project")
    audio = repo.roots.project_dir(foreign.project_id) / "audio/voice.wav"
    audio.parent.mkdir(exist_ok=True); audio.write_bytes(b"offline")
    response = client.patch("/api/gadget-media/projects/main-project", json={"presentation": {"audio_path": str(audio)}})
    assert response.status_code == 404, response.text
    assert "audio_path" not in repo.get(own.project_id).presentation
    own_audio = repo.roots.project_dir(own.project_id) / "audio/voice.wav"
    own_audio.parent.mkdir(exist_ok=True); own_audio.write_bytes(b"offline own")
    response = client.patch("/api/gadget-media/projects/main-project", json={"presentation": {"audio_path": str(own_audio)}})
    assert response.status_code == 200, response.text


def test_shot_background_pins_owner_and_snapshot(env, monkeypatch):
    from fastapi import BackgroundTasks
    _, _, _, _ = env
    captured = {}
    def create(**kwargs):
        captured.update(kwargs)
        return {"id": "offline-job"}
    monkeypatch.setattr(api_shot_lists.TaskManager, "create_task", create)
    profile = {"id": "second", "status": "active", "revision": 7, "identity_hash": "before", "presentation": {"voice": "original"}}
    scope = ChannelScope("second", "header", False, channel=profile)
    tasks = BackgroundTasks()
    result = api_shot_lists.create_shot_list("second", "angle", {}, tasks, scope)
    profile["presentation"]["voice"] = "changed"
    scope.channel_id = "main"
    assert result["task_id"] == "offline-job"
    assert captured["channel_id"] == "second"
    assert captured["job_scope"]["channel_revision"] == 7
    assert captured["job_scope"]["channel_identity_snapshot"]["presentation"]["voice"] == "original"
    assert tasks.tasks[0].args[-2] == "second"
    assert tasks.tasks[0].args[-1]["channel_identity_snapshot"]["presentation"]["voice"] == "original"


def test_scoped_worker_forwards_pinned_channel(env, monkeypatch):
    captured = []
    monkeypatch.setattr(api_shot_lists, "generate_shot_list_for_angle", lambda *args, **kwargs: captured.append(kwargs) or {})
    for name in ["update_progress", "complete_task", "fail_task"]:
        monkeypatch.setattr(api_shot_lists.TaskManager, name, lambda *args, **kwargs: captured.append(kwargs))
    snapshot = {"channel_id": "second", "channel_revision": 5}
    api_shot_lists._execute_generate_shot_list_worker("job", "second", "angle", {}, None, "second", snapshot)
    assert captured and all(row["channel_id"] == "second" for row in captured)
    assert captured[1]["job_scope"] == snapshot


def test_recording_cleanup_never_deletes_shared_raw(env, monkeypatch):
    root, client, _, _ = env
    monkeypatch.setattr(recording_sessions, "PROJECTS_DIR", root / "03_Projects")
    shared = root / "01_Raw/product/original.mp4"
    shared.parent.mkdir(parents=True); shared.write_bytes(b"keep")
    recording_sessions._cleanup_consumed_segments([{"raw_file_path": str(shared)}], "session")
    assert shared.read_bytes() == b"keep"
    scratch = root / "03_Projects/_RecordingSegments/session/segment.mp4"
    scratch.parent.mkdir(parents=True); scratch.write_bytes(b"consumed")
    recording_sessions._cleanup_consumed_segments([{"raw_file_path": str(scratch)}], "session")
    assert not scratch.parent.exists()
    plan("main")
    session = RecordingSessionStore.create("main", "angle", channel_id="main")
    RecordingSessionStore.upload_segment(session["id"], 0, str(shared), 1, channel_id="main")
    assert client.delete("/api/recording-sessions/" + session["id"] + "/segments/0").status_code == 200
    assert shared.read_bytes() == b"keep"
