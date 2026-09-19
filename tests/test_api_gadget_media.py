from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_gadget_media


def test_gadget_media_campaign_api_creates_and_updates_21_slots(tmp_path, monkeypatch):
    campaign_path = tmp_path / "campaigns.json"
    monkeypatch.setattr(api_gadget_media, "CAMPAIGNS_FILE", campaign_path)
    app = FastAPI()
    app.include_router(api_gadget_media.router)
    client = TestClient(app)

    created = client.post(
        "/api/gadget-media/campaigns",
        json={"campaign_id": "api-campaign", "name": "Gadget Media Test"},
    )

    assert created.status_code == 201
    body = created.json()
    assert len(body["slots"]) == 21
    assert body["account_role"] == "gadget_media"

    updated = client.patch(
        "/api/gadget-media/campaigns/api-campaign/slots/gadget-01",
        json={"status": "scripted", "script": "สคริปต์ทดสอบ"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "scripted"

    readiness = client.get("/api/gadget-media/campaigns/api-campaign/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["total_slots"] == 21
    assert readiness.json()["blocked_slots"] == 21
