from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_gadget_media_projects
from scripts.gadget_media_paths import GadgetMediaRoots
from scripts.gadget_media_repository import GadgetMediaRepository


def _client(tmp_path, monkeypatch):
    repository = GadgetMediaRepository(GadgetMediaRoots.under(tmp_path))
    monkeypatch.setattr(api_gadget_media_projects, "PROJECT_REPOSITORY", repository)
    app = FastAPI()
    app.include_router(api_gadget_media_projects.router)
    return TestClient(app), repository


def test_product_project_api_crud_and_isolated_timeline(tmp_path, monkeypatch):
    client, repository = _client(tmp_path, monkeypatch)
    created = client.post("/api/gadget-media/projects", json={
        "project_id": "api-product-project",
        "brand": "Xiaomi",
        "model": "14T",
        "category": "Smartphone",
        "audience": "คนที่กำลังเลือกมือถือ",
    })
    assert created.status_code == 201
    assert created.json()["module"] == "gadget_media"

    listed = client.get("/api/gadget-media/projects")
    assert listed.status_code == 200
    assert listed.json()["projects"][0]["project_id"] == "api-product-project"

    source = {
        "source_id": "source-001",
        "local_path": "01_Raw/GadgetMedia/test.mp4",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "duration": 60,
        "rights_reviewed": True,
        "upscaled": False,
        "product_key": "xiaomi 14t",
    }
    patched = client.patch("/api/gadget-media/projects/api-product-project", json={
        "source_assets": [source],
        "story": {"blocks": [{
            "block_id": "block-hook",
            "role": "hook",
            "text": "Hook",
            "claim_ids": [],
            "evidence_ids": ["source-001"],
        }]},
        "edit": {"edl": {"shots": [{
            "shot_id": "shot-001",
            "source_id": "source-001",
            "story_block_id": "block-hook",
            "source_start": 0,
            "source_end": 50,
        }]}},
        "status": "sourcing",
    })
    assert patched.status_code == 200

    # Advance through the explicit state machine before opening the timeline.
    for status in ("source_ready", "research_ready", "script_ready"):
        response = client.patch("/api/gadget-media/projects/api-product-project", json={"status": status})
        assert response.status_code == 200

    built = client.post("/api/gadget-media/projects/api-product-project/timeline/build")
    assert built.status_code == 200
    assert built.json()["timeline"]["duration"] == 50
    assert built.json()["project"]["status"] == "in_production"
    assert (repository.roots.projects / "api-product-project" / "timeline.json").is_file()
    assert not (tmp_path / "03_Projects" / "api-product-project").exists()


def test_api_rejects_status_skip(tmp_path, monkeypatch):
    client, _repository = _client(tmp_path, monkeypatch)
    client.post("/api/gadget-media/projects", json={
        "project_id": "api-state-project",
        "brand": "Xiaomi",
        "model": "14T",
    })
    response = client.patch("/api/gadget-media/projects/api-state-project", json={"status": "approved"})
    assert response.status_code == 400
    assert "invalid status transition" in response.json()["detail"]


def test_api_queues_gemini_narration_for_project_story(tmp_path, monkeypatch):
    client, _repository = _client(tmp_path, monkeypatch)
    client.post("/api/gadget-media/projects", json={
        "project_id": "api-narration-project",
        "brand": "Xiaomi",
        "model": "14T",
    })
    client.patch("/api/gadget-media/projects/api-narration-project", json={
        "story": {"blocks": [{"block_id": "hook", "role": "hook", "text": "เปิดเรื่องให้น่าสนใจ"}]},
    })
    calls = []
    monkeypatch.setattr(api_gadget_media_projects.GeminiFlashTTSEngine, "is_available", lambda: True)
    monkeypatch.setattr(
        api_gadget_media_projects,
        "execute_gadget_media_narration",
        lambda job_id, project_id, repository, **options: calls.append((job_id, project_id, repository, options)),
    )

    response = client.post("/api/gadget-media/projects/api-narration-project/audio/generate", json={
        "voice_preset": "gemini_charon_male_pro",
        "ad_tone": "commercial_expert",
        "speed": 1.1,
    })
    assert response.status_code == 202
    assert calls[0][1] == "api-narration-project"
    assert calls[0][3]["voice_preset"] == "gemini_charon_male_pro"
