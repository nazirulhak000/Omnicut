"""Offline tests for Mobile HTTPS Bridge API, auth exemptions, and media MIME/cache headers."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import scripts.api_auth as api_auth
import scripts.auth as auth_module
import scripts.mobile_bridge as mobile_bridge
from scripts.api_server import app
from scripts.media_service import stream_media_file

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_bridge_env(tmp_path, monkeypatch):
    monkeypatch.delenv("OMNICUT_API_KEY", raising=False)
    monkeypatch.delenv("OMNICUT_APP_PASSWORD", raising=False)
    monkeypatch.delenv("OMNICUT_PUBLIC_URL", raising=False)
    monkeypatch.delenv("OMNICUT_AUTH_DISABLED", raising=False)
    monkeypatch.delenv("OMNICUT_REQUIRE_AUTH", raising=False)
    monkeypatch.setenv("OMNICUT_CERT_DIR", str(tmp_path / "certs"))
    monkeypatch.setattr(auth_module, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(mobile_bridge, "detect_tailscale_url", lambda: None)
    monkeypatch.setattr(mobile_bridge, "get_local_ip", lambda force=False: "192.168.1.55")
    monkeypatch.setattr(mobile_bridge, "count_active_uploads", lambda: 0)
    monkeypatch.setattr(mobile_bridge, "count_active_filming_sessions", lambda: 0)
    api_auth.login_rate_limiter.reset()

    class _DummyServer:
        def __init__(self):
            self.should_exit = False

        async def serve(self):
            while not self.should_exit:
                await asyncio.sleep(0.01)

    monkeypatch.setattr(
        mobile_bridge.mobile_bridge_manager,
        "_create_uvicorn_server",
        lambda **kwargs: _DummyServer(),
    )
    yield
    asyncio.run(mobile_bridge.mobile_bridge_manager.stop())
    mobile_bridge.mobile_bridge_manager._cert_dir = None
    mobile_bridge.mobile_bridge_manager.mode = "lan_https"


def test_status_local_only_and_rejects_forwarded():
    res = client.get("/api/mobile-bridge/status")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is False
    assert body["mode"] == "lan_https"
    assert body["tls_port"] == 8443
    assert body["urls"]["lan_https"] == "https://192.168.1.55:8443"
    assert body["active_uploads"] == 0
    assert body["active_filming_sessions"] == 0

    remote_res = client.get("/api/mobile-bridge/status", headers={"X-Forwarded-For": "203.0.113.9"})
    assert remote_res.status_code == 403


def test_toggle_starts_generates_password_and_stops(tmp_path):
    res_on = client.post("/api/mobile-bridge/toggle", json={"enabled": True, "mode": "lan_https"})
    assert res_on.status_code == 200
    body_on = res_on.json()
    assert body_on["enabled"] is True
    assert body_on["password_configured"] is True

    pw = auth_module.get_app_password()
    assert len(pw) == 8
    assert pw != "12345678"
    assert f"OMNICUT_APP_PASSWORD={pw}" in (tmp_path / ".env").read_text(encoding="utf-8")

    res_off = client.post("/api/mobile-bridge/toggle", json={"enabled": False})
    assert res_off.status_code == 200
    assert res_off.json()["enabled"] is False


def test_password_and_rotate_strictly_local_only(monkeypatch):
    assert client.get("/api/mobile-bridge/password", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 403
    assert client.post("/api/mobile-bridge/password/rotate", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 403

    # Even with a valid API key, forwarded/remote requests must still get 403.
    monkeypatch.setenv("OMNICUT_API_KEY", "valid-api-key")
    assert client.get(
        "/api/mobile-bridge/password",
        headers={"X-Forwarded-For": "1.2.3.4", "X-API-Key": "valid-api-key"},
    ).status_code == 403
    assert client.post(
        "/api/mobile-bridge/password/rotate",
        headers={"X-Forwarded-For": "1.2.3.4", "X-API-Key": "valid-api-key"},
    ).status_code == 403
    monkeypatch.delenv("OMNICUT_API_KEY", raising=False)

    rot1 = client.post("/api/mobile-bridge/password/rotate")
    assert rot1.status_code == 200
    pw1 = rot1.json()["password"]
    assert len(pw1) == 8
    assert pw1 != "12345678"

    got = client.get("/api/mobile-bridge/password")
    assert got.status_code == 200
    assert got.json()["password"] == pw1

    rot2 = client.post("/api/mobile-bridge/password/rotate")
    assert rot2.status_code == 200
    pw2 = rot2.json()["password"]
    assert len(pw2) == 8
    assert pw2 != pw1


def test_ca_crt_download_allowed_before_login_and_blocked_for_forwarded(monkeypatch):
    monkeypatch.setenv("OMNICUT_APP_PASSWORD", "TESTPW99")

    res = client.get("/api/mobile-bridge/ca.crt")
    assert res.status_code == 200
    assert b"BEGIN CERTIFICATE" in res.content

    res_fwd = client.get("/api/mobile-bridge/ca.crt", headers={"X-Forwarded-For": "203.0.113.5"})
    assert res_fwd.status_code == 403


def test_tailscale_detection(monkeypatch):
    monkeypatch.setattr(mobile_bridge.shutil, "which", lambda cmd: "C:/Program Files/Tailscale/tailscale.exe")
    monkeypatch.setattr(
        mobile_bridge.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"BackendState": "Running", "Self": {"DNSName": "omnicut-pc.tail1234.ts.net."}}),
        ),
    )
    # Call the unpatched function directly via module reload-safe reference or test helper
    from importlib import reload
    import scripts.mobile_bridge as mb_mod
    # Restore real detect_tailscale_url for this test
    real_fn = mb_mod.MobileBridgeManager.get_status
    assert real_fn is not None
    # Verify parsing logic directly
    monkeypatch.undo()
    monkeypatch.setattr(mb_mod.shutil, "which", lambda cmd: "tailscale")
    monkeypatch.setattr(
        mb_mod.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"BackendState": "Running", "Self": {"DNSName": "omnicut-pc.tail1234.ts.net."}}),
        ),
    )
    assert mb_mod.detect_tailscale_url() == "https://omnicut-pc.tail1234.ts.net"


def test_font_asset_auth_exemption_readonly_only(monkeypatch):
    monkeypatch.setenv("OMNICUT_APP_PASSWORD", "TESTPW99")
    headers = {"x-forwarded-for": "203.0.113.10"}

    assert api_auth.is_exempt_path("/api/media/02_Assets/Fonts/IBMPlexSansThai-SemiBold.woff2", "GET") is True
    assert api_auth.is_exempt_path("/api/media/02_Assets/Fonts/IBMPlexSansThai-SemiBold.woff2", "HEAD") is True
    assert api_auth.is_exempt_path("/api/media/02_Assets/Fonts/IBMPlexSansThai-SemiBold.woff2", "POST") is False
    assert api_auth.is_exempt_path("/api/media/02_Assets/Fonts/../secret.txt", "GET") is False

    from starlette.datastructures import Headers, QueryParams
    d_get = api_auth.evaluate_access(
        scope_type="http",
        method="GET",
        path="/api/media/02_Assets/Fonts/IBMPlexSansThai-SemiBold.woff2",
        client_host="127.0.0.1",
        headers=Headers(headers),
        cookies={},
        query=QueryParams(""),
    )
    assert d_get.allow is True
    assert d_get.method == "exempt"

    d_post = api_auth.evaluate_access(
        scope_type="http",
        method="POST",
        path="/api/media/02_Assets/Fonts/IBMPlexSansThai-SemiBold.woff2",
        client_host="127.0.0.1",
        headers=Headers(headers),
        cookies={},
        query=QueryParams(""),
    )
    assert d_post.allow is False
    assert d_post.status == 401


@pytest.mark.parametrize(
    "filename,expected_mime",
    [
        ("font.woff", "font/woff"),
        ("font.woff2", "font/woff2"),
        ("clip.webm", "video/webm"),
        ("clip.mkv", "video/x-matroska"),
        ("audio.aac", "audio/aac"),
        ("audio.m4a", "audio/mp4"),
        ("audio.ogg", "audio/ogg"),
        ("anim.gif", "image/gif"),
    ],
)
def test_media_service_mime_types_and_font_cache_header(tmp_path, filename, expected_mime):
    fonts_dir = tmp_path / "02_Assets" / "Fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    target = fonts_dir / filename
    target.write_bytes(b"1234567890")

    req = Request({"type": "http", "method": "GET", "path": "/media", "headers": []})
    resp = stream_media_file(target, req)
    assert resp.headers["content-type"] == expected_mime
    assert resp.headers["cache-control"] == "public, max-age=3600"
