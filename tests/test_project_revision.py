from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_phase1, project_manifest
from scripts.project_manifest import ProjectManifest


def test_two_editors_cannot_overwrite_each_other_and_reload_recovers(tmp_path, monkeypatch):
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(api_phase1, "_project_origin", lambda name: (None, None, None))
    ProjectManifest.save("revision", clip_list=[{"id": "clip", "source_path": "video.mp4"}])
    app = FastAPI()
    app.include_router(api_phase1.router)
    client = TestClient(app)
    original = client.get("/api/projects/revision").json()
    revision = original["_editor_revision"]
    def save(label):
        return client.patch("/api/projects/revision/state", json={"base_revision": revision, "hook_label": label})
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(save, ["A", "B"]))
    assert sorted(response.status_code for response in responses) == [200, 409]
    latest = client.get("/api/projects/revision").json()
    assert latest["_editor_revision"] != revision
    accepted = client.patch("/api/projects/revision/state", json={
        "base_revision": latest["_editor_revision"], "hook_label": "after reload"})
    assert accepted.status_code == 200
    assert ProjectManifest.load("revision")["hook_label"] == "after reload"


def test_external_cutout_migration_invalidates_editor_revision(tmp_path, monkeypatch):
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(api_phase1, "_project_origin", lambda name: (None, None, None))
    ProjectManifest.save("revision", clip_list=[])
    app = FastAPI()
    app.include_router(api_phase1.router)
    client = TestClient(app)
    revision = client.get("/api/projects/revision").json()["_editor_revision"]
    ProjectManifest.save("revision", background_isolation={"enabled": True, "artifact": {"id": "video"}})
    response = client.patch("/api/projects/revision/state", json={
        "base_revision": revision, "background_isolation": {"enabled": False}})
    assert response.status_code == 409
    assert ProjectManifest.load("revision")["background_isolation"]["enabled"] is True
