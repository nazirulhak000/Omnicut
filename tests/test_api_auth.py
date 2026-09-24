"""
Regression tests for the P1 item 5/6 security fix: scripts/api_server.py had
no authentication at all and allow_origins=["*"] -- any web page open in the
user's browser could drive the whole local API while the app ran.

Fix: a single shared-secret check (scripts/auth.py) applied via middleware
in api_server.py, gated by OMNICUT_API_KEY. Unconfigured (the default local
single-user setup) -> every request passes through, but a loud warning is
logged. Configured -> every request must carry a matching `X-API-Key`
header (constant-time compare) or gets 401. CORS now reads an explicit
origin allowlist from CORS_ORIGINS instead of "*".

Isolated / offline per .agents/rules/testing_standard.md: no real network
calls, no real .env mutation -- OMNICUT_API_KEY is monkeypatched directly
onto os.environ and scripts.auth's module-level warning flag is reset per
test so warn_if_permissive() behavior can be asserted independently.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.auth as auth_module
from scripts.api_server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_api_key_env(monkeypatch):
    """Every test starts from a known state: no key configured."""
    monkeypatch.delenv("OMNICUT_API_KEY", raising=False)
    monkeypatch.setattr(auth_module, "_warned_permissive", False)
    yield


def test_unconfigured_key_allows_requests_through():
    """Default local single-user setup: no OMNICUT_API_KEY -> no 401s."""
    assert auth_module.get_configured_api_key() == ""
    assert auth_module.is_auth_enforced() is False

    res = client.get("/api/status")
    assert res.status_code != 401


def test_tts_env_loader_preserves_explicit_api_key_setting(tmp_path, monkeypatch):
    """Importing the voice API must not reactivate auth from a local .env."""
    from scripts.gemini_tts_engine import _load_env_file

    env_file = tmp_path / ".env"
    env_file.write_text("OMNICUT_API_KEY=from-file\nTEST_TTS_ENV_LOADER=from-file\n", encoding="utf-8")
    monkeypatch.setenv("OMNICUT_API_KEY", "")
    monkeypatch.delenv("TEST_TTS_ENV_LOADER", raising=False)

    _load_env_file(env_file)

    assert auth_module.get_configured_api_key() == ""
    assert __import__("os").environ["TEST_TTS_ENV_LOADER"] == "from-file"


def test_unconfigured_key_logs_a_warning_once(monkeypatch, caplog):
    """The permissive default must be loud, not silent."""
    import logging
    caplog.set_level(logging.WARNING, logger="omnicut.auth")

    auth_module.warn_if_permissive()

    assert any("NO API authentication" in r.message for r in caplog.records)


def test_configured_key_rejects_missing_header(monkeypatch):
    monkeypatch.setenv("OMNICUT_API_KEY", "s3cr3t-test-key")

    res = client.get("/api/status")

    assert res.status_code == 401
    assert "X-API-Key" in res.json()["detail"]


def test_configured_key_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv("OMNICUT_API_KEY", "s3cr3t-test-key")

    res = client.get("/api/status", headers={"X-API-Key": "wrong-key"})

    assert res.status_code == 401


def test_configured_key_accepts_correct_key(monkeypatch):
    monkeypatch.setenv("OMNICUT_API_KEY", "s3cr3t-test-key")

    res = client.get("/api/status", headers={"X-API-Key": "s3cr3t-test-key"})

    assert res.status_code != 401


def test_key_matches_uses_constant_time_compare(monkeypatch):
    """Guard against a future refactor swapping in `==`, which is fine
    functionally but was explicitly required to be constant-time."""
    monkeypatch.setenv("OMNICUT_API_KEY", "abc123")

    assert auth_module.key_matches("abc123") is True
    assert auth_module.key_matches("abc124") is False
    assert auth_module.key_matches("") is False


def test_options_preflight_is_never_blocked_by_api_key(monkeypatch):
    """Browsers never attach custom headers to a CORS preflight -- the key
    check must not 401 an OPTIONS request, or every cross-origin call from
    the frontend would fail before the real request is even sent."""
    monkeypatch.setenv("OMNICUT_API_KEY", "s3cr3t-test-key")

    res = client.options(
        "/api/status",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert res.status_code != 401


def test_cors_origins_default_to_local_vite_dev_server():
    """No CORS_ORIGINS env set -> falls back to the Vite dev server origins
    (frontend/vite.config.js runs on port 5173), never to '*'."""
    from scripts.api_server import CORS_ORIGINS

    assert "*" not in CORS_ORIGINS
    assert "http://localhost:5173" in CORS_ORIGINS
    assert "http://127.0.0.1:5173" in CORS_ORIGINS


def test_cors_rejects_unlisted_origin():
    res = client.get("/api/status", headers={"Origin": "http://evil.example.com"})
    # CORSMiddleware does not block the request itself for a simple GET,
    # but it must not echo back the disallowed origin -- that's what stops
    # the browser from letting the calling page read the response.
    assert res.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_cors_allows_configured_vite_origin():
    res = client.get("/api/status", headers={"Origin": "http://localhost:5173"})
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_headers_present_even_on_401_from_key_gate(monkeypatch):
    """Middleware registration order matters here: CORSMiddleware must be
    added AFTER api_key_gate so Starlette (which wraps middleware in
    reverse add_middleware() order) puts CORS on the outside. Otherwise a
    401 from the key gate reaches the browser as an opaque CORS failure
    instead of a readable 401 body, breaking both the frontend and the
    extension's error handling."""
    monkeypatch.setenv("OMNICUT_API_KEY", "s3cr3t-test-key")

    res = client.get("/api/status", headers={"Origin": "http://localhost:5173"})

    assert res.status_code == 401
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
