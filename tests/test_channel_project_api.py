"""HTTP project/product ownership tests with isolated durable stores."""
import json

import pytest
from fastapi import FastAPI, Header, Request
from fastapi.testclient import TestClient

from scripts import api_phase1, api_hooks, config
from scripts.channel_scope import ChannelScope, channel_error_handler
from scripts.channel_store import ChannelError
from scripts.product_store import ProductStore
from scripts.project_manifest import ProjectManifest


@pytest.fixture
def client():
    def request_scope(channel: str = Header(None, alias="X-OmniCut-Channel")):
        owner = channel or "main"
        return ChannelScope(owner, "header" if channel else "default", False,
                            channel={"id": owner, "status": "active", "revision": 1})
    app = FastAPI()
    @app.middleware("http")
    async def scoped_request(request: Request, call_next):
        request.state.channel_scope = request_scope(request.headers.get("X-OmniCut-Channel"))
        return await call_next(request)
    app.add_exception_handler(ChannelError, channel_error_handler)
    app.include_router(api_phase1.router)
    app.include_router(api_hooks.router)
    return TestClient(app)


def test_implicit_main_products_and_mutations_reject_foreign(client):
    main = ProductStore.add("Shared name", channel_id="main")
    second = ProductStore.add("Shared name", channel_id="second")
    result = client.get("/api/products").json()
    assert [row["id"] for row in result["products"]] == [main["id"]]
    result = client.get("/api/products", headers={"X-OmniCut-Channel": "second"}).json()
    assert [row["id"] for row in result["products"]] == [second["id"]]
    response = client.patch(f"/api/products/{second['id']}", json={"name": "Hijacked"})
    assert response.status_code == 404
    assert ProductStore.get(second["id"], channel_id="second")["name"] == "Shared name"


def test_json_extra_owner_is_checked_before_pydantic_discards_it(client):
    response = client.post("/api/products", headers={"X-OmniCut-Channel": "second"},
                           json={"name": "Rejected", "channel_id": "main"})
    assert response.status_code == 422
    assert ProductStore.list(channel_id="second") == []


def test_foreign_project_reads_and_writes_are_hidden(client):
    ProjectManifest.save("foreign", channel_id="second", hook_label="Original")
    original = ProjectManifest.path_for("foreign").read_bytes()
    for suffix in ("", "/origin", "/snapshots"):
        assert client.get("/api/projects/foreign" + suffix).status_code == 404
    assert client.patch("/api/projects/foreign/state", json={"hook_label": "Hijacked"}).status_code == 404
    assert client.post("/api/hooks/apply-project", json={
        "project_name": "foreign", "hook_variant": {"hook_label": "Hijacked"}}).status_code == 404
    assert ProjectManifest.path_for("foreign").read_bytes() == original
    assert client.get("/api/projects").json()["projects"] == []


def test_owner_cannot_be_changed_by_manifest_save():
    ProjectManifest.save("owned", channel_id="second")
    original = ProjectManifest.path_for("owned").read_bytes()
    with pytest.raises(ChannelError):
        ProjectManifest.save("owned", channel_id="main")
    assert ProjectManifest.path_for("owned").read_bytes() == original


def test_hook_update_preserves_other_project_fields(client):
    ProjectManifest.save("owned", channel_id="second", custom_script="Keep this",
                         overlays=[{"kind": "hook", "label": "Old"}])
    response = client.post("/api/hooks/apply-project", headers={"X-OmniCut-Channel": "second"},
                           json={"project_name": "owned", "hook_variant": {"hook_label": "New"}})
    assert response.status_code == 200
    manifest = ProjectManifest.load("owned")
    assert manifest["custom_script"] == "Keep this"
    assert manifest["overlays"][0]["label"] == "New"
