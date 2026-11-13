"""
Tests for scripts/api_flow.py (FastAPI Endpoints)
"""

from unittest.mock import patch, MagicMock
import pytest
from starlette.testclient import TestClient

from scripts.api_server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_flow_status_offline(client, monkeypatch):
    monkeypatch.setattr("scripts.flow_client.FlowClient.is_healthy", lambda self, timeout=2.0: False)
    resp = client.get("/api/flow/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_online"] is False
    assert data["credits_remaining"] == 0


def test_api_flow_presets(client):
    resp = client.get("/api/flow/presets")
    assert resp.status_code == 200
    data = resp.json()
    assert "camera_techniques" in data
    assert "lighting_presets" in data
    assert len(data["camera_techniques"]) > 0


def test_api_flow_prompt_expand(client):
    payload = {
        "thai_description": "หมุนรอบสินค้า ชัดๆ",
        "product_name": "Power Bank",
        "technique": "orbit",
        "lighting": "studio_clean",
    }
    resp = client.post("/api/flow/prompt/expand", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "Power Bank" in data["prompt"]
    assert "9:16" in data["prompt"]


def test_api_flow_generate_job(client, tmp_path, monkeypatch):
    test_jobs_file = tmp_path / "flow_jobs.json"
    monkeypatch.setattr("scripts.flow_service.FLOW_JOBS_FILE", test_jobs_file)

    mock_service = MagicMock()
    mock_service.submit_generation.return_value = {
        "job": {
            "id": "flow_job_123",
            "product_id": "prod_test",
            "status": "queued",
        },
        "flow_response": {"job_ids": ["job_123"]},
    }
    monkeypatch.setattr("scripts.api_flow.get_flow_service", lambda: mock_service)

    payload = {
        "product_id": "prod_test",
        "scenes": [
            {
                "prompt": "Cinematic shot of tech gadget",
                "type": "video",
                "aspect_ratio": "9:16",
            }
        ],
    }
    resp = client.post("/api/flow/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["job"]["product_id"] == "prod_test"
    assert data["job"]["status"] == "queued"
