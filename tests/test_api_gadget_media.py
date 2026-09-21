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

    blocked_publish = client.patch(
        "/api/gadget-media/campaigns/api-campaign/slots/gadget-01",
        json={"status": "published"},
    )
    assert blocked_publish.status_code == 400
    assert "cannot be published" in blocked_publish.json()["detail"]

    # Test analytics endpoint
    analytics_resp = client.get("/api/gadget-media/campaigns/api-campaign/analytics")
    assert analytics_resp.status_code == 200
    analytics_data = analytics_resp.json()
    assert "total_views" in analytics_data
    assert "series" in analytics_data
    assert "watch_before_buy" in analytics_data["series"]

    # Test preset sources endpoint
    preset_resp = client.get("/api/gadget-media/preset-sources")
    assert preset_resp.status_code == 200
    assert "sources" in preset_resp.json()
