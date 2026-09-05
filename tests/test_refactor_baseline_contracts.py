"""Behavioral safety net captured before the structural editor refactor."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import project_manifest
from scripts.api_phase1 import UpdateProjectStateRequest
from scripts.overlay_model import migrate_to_overlays
from scripts.project_manifest import ProjectManifest


ROOT = Path(__file__).resolve().parent.parent
LEGACY_FIXTURE = ROOT / "tests" / "fixtures" / "legacy_project_v0.json"


@pytest.fixture
def isolated_projects(tmp_path, monkeypatch):
    projects = tmp_path / "03_Projects"
    projects.mkdir()
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", projects)
    return projects


@pytest.fixture
def client():
    from scripts.api_server import app

    return TestClient(app)


def test_fastapi_registers_editor_critical_routes():
    from scripts.api_server import app

    registered = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    required = {
        ("GET", "/api/status"),
        ("GET", "/api/projects"),
        ("GET", "/api/projects/{project_name}"),
        ("PATCH", "/api/projects/{project_name}/state"),
        ("POST", "/api/reroll"),
        ("POST", "/api/render"),
        ("GET", "/api/render/status/{job_id}"),
        ("GET", "/api/assets/all"),
    }
    assert required <= registered


def test_legacy_manifest_loads_without_rewriting_the_fixture(isolated_projects):
    project_dir = isolated_projects / "legacy-v0"
    project_dir.mkdir()
    target = project_dir / "project.json"
    original = LEGACY_FIXTURE.read_bytes()
    target.write_bytes(original)

    loaded = ProjectManifest.load("legacy-v0")

    assert loaded["style"]["fontName"] == "IBMPlex"
    assert "manifest_version" not in loaded, "the fixture intentionally predates versioned manifests"
    assert [item["kind"] for item in migrate_to_overlays(loaded)] == ["hook", "text"]
    assert target.read_bytes() == original, "loading an old project must never mutate it"


def test_editor_payload_matches_the_pydantic_save_contract():
    payload = {
        "cues": [{"start": 0.0, "end": 1.0, "text": "หนึ่ง"}],
        "micro_cues": [{"start": 0.0, "end": 0.5, "text": "หนึ่ง"}],
        "clip_list": [{
            "source_path": "01_Raw/demo/source.mp4",
            "trim_start": 0.0,
            "trim_end": 1.0,
            "duration": 1.0,
            "track_id": "video-1",
            "keyframes": [{"time": 0.0, "scale": 1.0}],
        }],
        "transitions": [],
        "style": {"font_name": "IBMPlex", "caption_scale": 1.0},
        "hook_brand": "Brand",
        "hook_model": "Model",
        "hook_label": "Label",
        "hook_duration": 1.0,
        "hook_motion": {"in": "bounce"},
        "hook_colors": {"brand": "#FFFFFF"},
        "hook_style": {"font_name": "IBMPlex"},
        "text_overlays": [],
        "overlays": [{"id": "hook", "kind": "hook", "tiers": []}],
        "track_mix": {"voice": 1.0, "bgm": 0.12, "sfx": 0.28, "mute": {"bgm": True}},
        "audio_mutes": {"voice": False, "bgm": True, "sfx": False},
    }

    validated = UpdateProjectStateRequest.model_validate(payload)

    assert validated.model_dump(exclude_unset=True) == payload
    assert set(payload) <= set(UpdateProjectStateRequest.model_fields)


def test_create_load_edit_save_reload_round_trip(client, isolated_projects):
    ProjectManifest.save(
        "round-trip",
        total_duration=2.0,
        clip_list=[{"source_path": "01_Raw/demo/a.mp4", "duration": 2.0}],
        cues=[{"start": 0.0, "end": 2.0, "text": "ก่อนแก้"}],
    )
    loaded = client.get("/api/projects/round-trip")
    assert loaded.status_code == 200

    payload = {
        "cues": [{"start": 0.0, "end": 2.0, "text": "หลังแก้"}],
        "micro_cues": [{"start": 0.0, "end": 1.0, "text": "หลัง"}],
        "clip_list": [{
            "source_path": "01_Raw/demo/a.mp4",
            "trim_start": 0.1,
            "trim_end": 1.9,
            "duration": 1.8,
            "track_id": "video-2",
            "keyframes": [{"time": 0.0, "scale": 1.0}, {"time": 1.8, "scale": 1.2}],
        }],
        "transitions": [],
        "style": {"font_name": "IBMPlex", "caption_scale": 1.0},
        "overlays": [{"id": "title", "kind": "text", "tiers": [{"text": "ใหม่"}]}],
        "track_mix": {"voice": 1.0, "bgm": 0.12, "sfx": 0.28, "mute": {"bgm": True}},
        "audio_mutes": {"voice": False, "bgm": True, "sfx": False},
    }
    saved = client.patch("/api/projects/round-trip/state", json=payload)
    assert saved.status_code == 200, saved.text

    reloaded = client.get("/api/projects/round-trip")
    assert reloaded.status_code == 200
    state = reloaded.json()
    for key, expected in payload.items():
        assert state[key] == expected, key
    assert state["total_duration"] == 2.0, "saving editor state must preserve unrelated fields"
    assert state["render_params"]["clip_list"] == payload["clip_list"]
    assert state["render_params"]["audio_mutes"] == payload["audio_mutes"]
