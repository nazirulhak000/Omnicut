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


def test_render_rewrite_rejects_stale_editor_save_until_revision_is_refetched(tmp_path, monkeypatch):
    """L7-04 replay: save -> R1, render pipeline writes the manifest twice -> R2.

    The editor still holding R1 must get 409 (guard intact, pipeline output kept);
    after re-reading the project (what the editor now does when a render
    completes) the same save with the fetched revision is accepted.
    """
    from scripts import render_jobs

    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(api_phase1, "_project_origin", lambda name: (None, None, None))
    ProjectManifest.save("render_rev", clip_list=[{"source_path": "a.mp4", "trim_start": 0, "trim_end": 2}])
    app = FastAPI()
    app.include_router(api_phase1.router)
    client = TestClient(app)

    r0 = client.get("/api/projects/render_rev").json()["_editor_revision"]
    saved = client.patch("/api/projects/render_rev/state", json={"base_revision": r0, "track_mix": {"mute": {}, "solo": {}}})
    assert saved.status_code == 200
    r1 = saved.json()["_editor_revision"]
    assert r1 != r0

    # Pipeline stage write (clip list as actually rendered), then the job seam's
    # fingerprint stamp -- the real function, against the tmp manifest.
    pipeline_clips = [{"source_path": "a.mp4", "trim_start": 0, "trim_end": 1.5}]
    ProjectManifest.save("render_rev", clip_list=pipeline_clips, render_params={"clip_list": pipeline_clips})
    mid = client.get("/api/projects/render_rev").json()["_editor_revision"]
    render_jobs.finalize_incremental_render("render_rev")
    r2 = client.get("/api/projects/render_rev").json()["_editor_revision"]
    # The job's last write moves the revision again: a single read taken before
    # it would be stale, which is why the editor re-reads until two reads agree.
    assert len({r1, mid, r2}) == 3
    # Reads never move the revision.
    assert client.get("/api/projects/render_rev").json()["_editor_revision"] == r2

    stale = client.patch("/api/projects/render_rev/state", json={"base_revision": r1, "clip_list": []})
    assert stale.status_code == 409
    assert ProjectManifest.load("render_rev")["clip_list"] == pipeline_clips

    rerender_stale = client.patch("/api/projects/render_rev/state", json={"base_revision": r1, "track_mix": {"mute": {"bgm": True}, "solo": {}}})
    assert rerender_stale.status_code == 409

    fresh = client.patch("/api/projects/render_rev/state", json={"base_revision": r2, "track_mix": {"mute": {"bgm": True}, "solo": {}}})
    assert fresh.status_code == 200
    after = ProjectManifest.load("render_rev")
    assert after["track_mix"]["mute"]["bgm"] is True
    # Fields the editor did not send stay as the pipeline left them.
    assert after["clip_list"] == pipeline_clips
