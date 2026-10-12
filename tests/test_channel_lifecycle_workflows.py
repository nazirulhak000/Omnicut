"""Legacy main still obeys channel lifecycle before creating jobs or bytes."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_background_isolation, api_voice, api_producer
from scripts.channel_scope import ChannelScope, channel_error_handler, get_channel_scope
from scripts.channel_store import ChannelError
from scripts.channel_workflows import get_workflow_scope


@pytest.mark.parametrize("status", ["draft", "archived"])
@pytest.mark.parametrize("route,payload", [
    ("/api/background-isolation/process", {"source_path": "missing.mp4"}),
    ("/api/sub-srt/transcribe", {"media_path": "missing.mp4"}),
    ("/api/voice/preview", {"text": "Official sample"}),
])
def test_implicit_main_new_media_work_rejects_before_engines(monkeypatch, status, route, payload):
    scope = ChannelScope("main", "default", False, channel={"id": "main", "status": status})
    app = FastAPI()
    app.add_exception_handler(ChannelError, channel_error_handler)
    app.dependency_overrides[get_workflow_scope] = lambda: scope
    app.include_router(api_background_isolation.router)
    app.include_router(api_voice.router)
    monkeypatch.setattr(api_voice, "get_optional_channel_scope", lambda request: None)
    monkeypatch.setattr(api_voice, "get_channel_scope", lambda request: scope)
    def forbidden(*args, **kwargs):
        pytest.fail("Media engine ran before lifecycle rejection")
    monkeypatch.setattr(api_voice.subprocess, "run", forbidden)
    monkeypatch.setattr(api_voice.GeminiFlashTTSEngine, "generate_speech", forbidden)
    monkeypatch.setattr(api_voice.VoiceEngine, "generate_voiceover", forbidden)
    response = TestClient(app).post(route, json=payload)
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "channel_not_active"


def test_implicit_archived_main_producer_rejects_before_loading_or_replacing_notes(monkeypatch):
    scope = ChannelScope("main", "default", False, channel={"id": "main", "status": "archived"})
    app = FastAPI()
    app.add_exception_handler(ChannelError, channel_error_handler)
    app.dependency_overrides[get_channel_scope] = lambda: scope
    app.include_router(api_producer.router)
    def forbidden(*args, **kwargs):
        pytest.fail("Notes store touched before lifecycle rejection")
    monkeypatch.setattr(api_producer, "load_notes_from_disk", forbidden)
    monkeypatch.setattr(api_producer, "save_notes_to_disk", forbidden)
    response = TestClient(app).post("/api/producer/notes", json={"notes": []})
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "channel_archived"
