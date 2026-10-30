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

Remote-access hardening (2026-10-30): the app is exposed through a
Cloudflare tunnel on Colab. cloudflared connects from 127.0.0.1, and the old
gate (a) treated ANY request as local when /content existed, google.colab was
imported or OMNICUT_ALLOW_REMOTE was set, (b) skipped every non-/api path
(/terminal, /ws, /agy = ttyd root shell) and (c) never saw WebSockets. The
bypass is deleted; scripts/api_auth.py adds a pure-ASGI gate (http +
websocket) plus /api/auth/{me,login,logout} with a signed `omnicut_session`
cookie. Tunnel traffic is recognised by its forward headers (cf-connecting-ip,
cf-ray, x-forwarded-for, forwarded). The original local/API-key tests below
are unchanged: no test here asserted the Colab bypass, and local semantics
(no key -> open, key -> X-API-Key required on /api/*) are preserved.

Isolated / offline per .agents/rules/testing_standard.md: no real network
calls, no real .env mutation -- every auth env var is monkeypatched directly
onto os.environ, the login rate limiter is reset per test, and the WebSocket
"accepted" path uses a dummy route (the real /ws needs a running ttyd).
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.api_auth as api_auth
import scripts.auth as auth_module
from scripts.api_server import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_api_key_env(monkeypatch):
    """Every test starts from a known state: no key/password/secret configured."""
    monkeypatch.delenv("OMNICUT_API_KEY", raising=False)
    monkeypatch.delenv("OMNICUT_APP_PASSWORD", raising=False)
    monkeypatch.delenv("OMNICUT_SESSION_SECRET", raising=False)
    monkeypatch.delenv("OMNICUT_ALLOW_REMOTE", raising=False)
    monkeypatch.setattr(auth_module, "_warned_permissive", False)
    api_auth.login_rate_limiter.reset()
    yield
    api_auth.login_rate_limiter.reset()


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
    assert auth_module.key_matches("abé") is False  # non-ASCII must not raise


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


# ======================================================================
# Remote access: tunnel detection, login, session cookie, WS gate
# ======================================================================
import sys as _sys
import types

from fastapi import FastAPI, WebSocket
from starlette.datastructures import Headers
from starlette.websockets import WebSocketDisconnect

PASSWORD = "correct horse battery staple"
TUNNEL = {"cf-connecting-ip": "198.51.100.7", "cf-ray": "8a1b2c3d4e5f-SIN"}


def _fresh_client(**kwargs):
    return TestClient(app, **kwargs)


def _cookie_header(token):
    return {"Cookie": f"{auth_module.SESSION_COOKIE_NAME}={token}"}


@pytest.fixture()
def password(monkeypatch):
    monkeypatch.setenv("OMNICUT_APP_PASSWORD", PASSWORD)
    return PASSWORD


# --- classification -----------------------------------------------------

@pytest.mark.parametrize(
    "host,headers,expected",
    [
        ("127.0.0.1", {}, "local"),
        ("::1", {}, "local"),
        ("testclient", {}, "local"),
        ("127.0.0.1", {"cf-connecting-ip": "1.2.3.4"}, "remote"),
        ("127.0.0.1", {"cf-ray": "x"}, "remote"),
        ("127.0.0.1", {"x-forwarded-for": "1.2.3.4"}, "remote"),
        ("127.0.0.1", {"forwarded": "for=1.2.3.4"}, "remote"),
        ("192.168.1.25", {}, "remote"),
        (None, {}, "remote"),
    ],
)
def test_classify_request(host, headers, expected):
    assert auth_module.classify_request(host, Headers(headers)) == expected


def test_local_request_still_allowed_without_any_config():
    res = _fresh_client().get("/api/status")
    assert res.status_code not in (401, 503)


def test_tunnel_request_without_cookie_gets_401(password):
    res = _fresh_client().get("/api/status", headers=TUNNEL)
    assert res.status_code == 401
    assert res.json() == {"detail": "ต้องเข้าสู่ระบบก่อน", "login_required": True}


def test_colab_and_allow_remote_bypass_is_gone(password, monkeypatch):
    """Old gate: /content, google.colab or OMNICUT_ALLOW_REMOTE => 'local'."""
    monkeypatch.setenv("OMNICUT_ALLOW_REMOTE", "1")
    monkeypatch.setitem(_sys.modules, "google.colab", types.ModuleType("google.colab"))
    res = _fresh_client().get("/api/status", headers=TUNNEL)
    assert res.status_code == 401


def test_remote_without_password_configured_fails_closed():
    res = _fresh_client().get("/api/status", headers=TUNNEL)
    assert res.status_code == 503
    assert res.json()["detail"] == "ยังไม่ได้ตั้งรหัสผ่านแอป (OMNICUT_APP_PASSWORD)"
    lan = TestClient(app, client=("192.168.1.25", 5555))
    assert lan.get("/api/status").status_code == 503


# --- login / logout / me --------------------------------------------------

def test_login_ok_sets_hardened_cookie(password):
    res = _fresh_client().post(
        "/api/auth/login", json={"password": PASSWORD},
        headers={**TUNNEL, "x-forwarded-proto": "https"},
    )
    assert res.status_code == 200
    assert res.json() == {"ok": True}
    cookie = res.headers["set-cookie"]
    lowered = cookie.lower()
    assert cookie.startswith(f"{auth_module.SESSION_COOKIE_NAME}=")
    assert "httponly" in lowered
    assert "samesite=lax" in lowered
    assert "secure" in lowered
    assert "max-age=2592000" in lowered
    assert "path=/" in lowered


def test_login_cookie_not_secure_over_plain_http(password):
    res = _fresh_client().post("/api/auth/login", json={"password": PASSWORD})
    assert res.status_code == 200
    assert "secure" not in res.headers["set-cookie"].lower()


def test_login_wrong_password(password):
    res = _fresh_client().post("/api/auth/login", json={"password": "nope"}, headers=TUNNEL)
    assert res.status_code == 401
    assert res.json() == {"detail": "รหัสผ่านไม่ถูกต้อง"}
    assert "set-cookie" not in res.headers


def test_login_without_password_configured_returns_503():
    res = _fresh_client().post("/api/auth/login", json={"password": "x"}, headers=TUNNEL)
    assert res.status_code == 503


def test_login_rate_limited_per_client_ip(password):
    c = _fresh_client()
    for _ in range(5):
        assert c.post("/api/auth/login", json={"password": "bad"}, headers=TUNNEL).status_code == 401
    blocked = c.post("/api/auth/login", json={"password": PASSWORD}, headers=TUNNEL)
    assert blocked.status_code == 429
    assert blocked.json() == {"detail": "ลองบ่อยเกินไป รอ 1 นาที"}
    other_ip = {**TUNNEL, "cf-connecting-ip": "203.0.113.9"}
    assert c.post("/api/auth/login", json={"password": PASSWORD}, headers=other_ip).status_code == 200


def test_login_rate_limit_window_expires(password, monkeypatch):
    clock = {"t": 1_800_000_000.0}
    monkeypatch.setattr(auth_module, "_now", lambda: clock["t"])
    c = _fresh_client()
    for _ in range(5):
        c.post("/api/auth/login", json={"password": "bad"}, headers=TUNNEL)
    assert c.post("/api/auth/login", json={"password": "bad"}, headers=TUNNEL).status_code == 429
    clock["t"] += 61
    assert c.post("/api/auth/login", json={"password": PASSWORD}, headers=TUNNEL).status_code == 200


def test_login_cookie_grants_remote_access(password):
    c = _fresh_client()
    assert c.post("/api/auth/login", json={"password": PASSWORD}, headers=TUNNEL).status_code == 200
    res = c.get("/api/status", headers=TUNNEL)
    assert res.status_code not in (401, 503)
    me = c.get("/api/auth/me", headers=TUNNEL).json()
    assert me == {
        "authenticated": True, "auth_required": True,
        "method": "cookie", "password_configured": True,
    }


def test_me_reports_local_and_remote_states(password):
    local = _fresh_client().get("/api/auth/me").json()
    assert local == {
        "authenticated": True, "auth_required": False,
        "method": "local", "password_configured": True,
    }
    remote = _fresh_client().get("/api/auth/me", headers=TUNNEL)
    assert remote.status_code == 200
    assert remote.json() == {
        "authenticated": False, "auth_required": True,
        "method": None, "password_configured": True,
    }


def test_me_reachable_remotely_even_without_password():
    res = _fresh_client().get("/api/auth/me", headers=TUNNEL)
    assert res.status_code == 200
    assert res.json()["password_configured"] is False


def test_logout_clears_cookie(password):
    res = _fresh_client().post("/api/auth/logout", headers=TUNNEL)
    assert res.status_code == 200
    cookie = res.headers["set-cookie"].lower()
    assert cookie.startswith(f"{auth_module.SESSION_COOKIE_NAME}=")
    assert "max-age=0" in cookie


# --- token validation -------------------------------------------------------

def test_expired_cookie_rejected(password, monkeypatch):
    token = auth_module.issue_session_token()
    real_now = auth_module._now()
    monkeypatch.setattr(
        auth_module, "_now", lambda: real_now + auth_module.SESSION_MAX_AGE_SECONDS + 1
    )
    assert auth_module.verify_session_token(token) is False
    res = _fresh_client().get("/api/status", headers={**TUNNEL, **_cookie_header(token)})
    assert res.status_code == 401


def test_tampered_cookie_rejected(password):
    token = auth_module.issue_session_token()
    v, iat, exp, nonce, sig = token.split(".")
    longer = f"{v}.{iat}.{int(exp) + 10**9}.{nonce}.{sig}"
    flipped = ("A" if sig[0] != "A" else "B") + sig[1:]
    flipped_sig = f"{v}.{iat}.{exp}.{nonce}.{flipped}"
    assert auth_module.verify_session_token(f"v1.{iat}.{exp}.ไทย.{sig}") is False
    assert auth_module.verify_session_token(f"v1.{iat}.{exp}.{nonce}.ไทย") is False
    for bad in (longer, flipped_sig, "garbage", token + "x"):
        assert auth_module.verify_session_token(bad) is False
        res = _fresh_client().get("/api/status", headers={**TUNNEL, **_cookie_header(bad)})
        assert res.status_code == 401


def test_changing_password_invalidates_sessions(password, monkeypatch):
    token = auth_module.issue_session_token()
    assert auth_module.verify_session_token(token) is True
    monkeypatch.setenv("OMNICUT_APP_PASSWORD", "a brand new password")
    assert auth_module.verify_session_token(token) is False


def test_session_secret_env_used_as_signing_key(password, monkeypatch):
    monkeypatch.setenv("OMNICUT_SESSION_SECRET", "s" * 40)
    token = auth_module.issue_session_token()
    assert auth_module.verify_session_token(token) is True
    monkeypatch.setenv("OMNICUT_SESSION_SECRET", "t" * 40)
    assert auth_module.verify_session_token(token) is False


def test_password_change_invalidates_even_with_persisted_secret(password, monkeypatch):
    monkeypatch.setenv("OMNICUT_SESSION_SECRET", "s" * 40)
    token = auth_module.issue_session_token()
    monkeypatch.setenv("OMNICUT_APP_PASSWORD", "rotated password")
    assert auth_module.verify_session_token(token) is False


def test_password_matches_helper(password):
    assert auth_module.password_matches(PASSWORD) is True
    assert auth_module.password_matches(PASSWORD + " ") is False
    assert auth_module.password_matches("") is False


# --- API key + exempt paths + HTML redirect ----------------------------------

def test_remote_x_api_key_still_works(monkeypatch):
    monkeypatch.setenv("OMNICUT_API_KEY", "ext-key")
    c = _fresh_client()
    ok = c.get("/api/status", headers={**TUNNEL, "X-API-Key": "ext-key"})
    assert ok.status_code not in (401, 503)
    # API key configured but no password: a remote miss fails closed (503).
    assert c.get("/api/status", headers={**TUNNEL, "X-API-Key": "wrong"}).status_code == 503


@pytest.mark.parametrize("path", ["/terminal", "/agy", "/terminal/index.html"])
def test_remote_html_navigation_to_shell_redirects_to_login(password, path):
    res = _fresh_client().get(
        path, headers={**TUNNEL, "Accept": "text/html,application/xhtml+xml"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"] == f"/?login=1&next={path}"


@pytest.mark.parametrize("path", ["/terminal", "/token", "/agy", "/docs", "/openapi.json",
                                  "/api/media/04_Exports/x.mp4", "/api/agy/status"])
def test_remote_non_html_requests_to_protected_paths_get_401(password, path):
    res = _fresh_client().get(path, headers=TUNNEL, follow_redirects=False)
    assert res.status_code == 401
    assert res.json()["login_required"] is True


@pytest.mark.parametrize("path", ["/", "/index.html", "/manifest.webmanifest",
                                  "/favicon.svg", "/apple-touch-icon.png", "/pwa-192.png",
                                  "/assets/does-not-exist.js"])
def test_remote_spa_shell_and_static_assets_exempt(password, path):
    res = _fresh_client().get(
        path, headers={**TUNNEL, "Accept": "text/html"}, follow_redirects=False
    )
    assert res.status_code not in (302, 401, 503)


def test_exempt_path_rejects_traversal_tricks():
    assert api_auth.is_exempt_path("/assets/app.js") is True
    assert api_auth.is_exempt_path("/assets/../api/products") is False
    assert api_auth.is_exempt_path("//api/status") is False
    assert api_auth.is_exempt_path("/pwa-../x.png") is False


def test_remote_options_preflight_not_blocked(password):
    res = _fresh_client().options(
        "/api/status",
        headers={**TUNNEL, "Origin": "http://localhost:5173",
                 "Access-Control-Request-Method": "GET"},
    )
    assert res.status_code not in (401, 503)


# --- WebSocket gate -----------------------------------------------------------

def test_remote_websocket_rejected_without_cookie(password):
    with pytest.raises(WebSocketDisconnect) as exc:
        with _fresh_client().websocket_connect(
            "/ws", headers={**TUNNEL, "Origin": "http://testserver"}
        ):
            pass
    assert exc.value.code == 4401


def test_remote_terminal_ws_rejected_without_password_configured():
    with pytest.raises(WebSocketDisconnect) as exc:
        with _fresh_client().websocket_connect("/terminal/ws", headers=TUNNEL):
            pass
    assert exc.value.code == 4401


def test_local_websocket_cross_site_origin_rejected():
    """CSWSH guard: a random site open in the owner browser must not reach ttyd."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with _fresh_client().websocket_connect(
            "/ws", headers={"Origin": "https://evil.example"}
        ):
            pass
    assert exc.value.code == 4403


def _dummy_ws_app():
    dummy = FastAPI()
    dummy.add_middleware(api_auth.AuthGateMiddleware, allowed_origins=["http://localhost:5173"])

    @dummy.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("hello")
        await websocket.close()

    return dummy


def test_remote_websocket_accepted_with_cookie_and_same_origin(password):
    token = auth_module.issue_session_token()
    c = TestClient(_dummy_ws_app())
    with c.websocket_connect(
        "/ws", headers={**TUNNEL, **_cookie_header(token), "Origin": "http://testserver"}
    ) as ws:
        assert ws.receive_text() == "hello"


def test_remote_websocket_with_cookie_but_foreign_or_missing_origin_rejected(password):
    token = auth_module.issue_session_token()
    c = TestClient(_dummy_ws_app())
    for headers in (
        {**TUNNEL, **_cookie_header(token), "Origin": "https://evil.example"},
        {**TUNNEL, **_cookie_header(token)},  # Origin absent is only OK for local
    ):
        with pytest.raises(WebSocketDisconnect) as exc:
            with c.websocket_connect("/ws", headers=headers):
                pass
        assert exc.value.code == 4403


def test_local_websocket_without_origin_or_from_vite_allowed():
    c = TestClient(_dummy_ws_app())
    with c.websocket_connect("/ws") as ws:
        assert ws.receive_text() == "hello"
    with c.websocket_connect("/ws", headers={"Origin": "http://localhost:5173"}) as ws:
        assert ws.receive_text() == "hello"


@pytest.mark.parametrize(
    "origin,host,expected",
    [
        ("https://studio.nazirulhak.com", "studio.nazirulhak.com", True),
        ("https://studio.nazirulhak.com", "studio.nazirulhak.com:443", True),
        ("http://127.0.0.1:8000", "127.0.0.1:8000", True),
        ("http://127.0.0.1:5173", "127.0.0.1:8000", False),
        ("https://evil.example", "studio.nazirulhak.com", False),
        ("null", "studio.nazirulhak.com", False),
        ("", "studio.nazirulhak.com", False),
    ],
)
def test_origin_matches_host(origin, host, expected):
    assert api_auth.origin_matches_host(origin, host) is expected


# ======================================================================
# /api/health, SPA catch-all containment, cache headers
# ======================================================================
import scripts.api_server as api_server_module


def test_health_reachable_remotely_without_login():
    res = _fresh_client().get("/api/health", headers=TUNNEL)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["runtime"] in ("colab", "local")
    assert body["auth_required"] is True
    assert body["started_at"]
    assert body["version"] == app.version


def test_health_local_reports_no_auth_required():
    body = _fresh_client().get("/api/health").json()
    assert body["auth_required"] is False


def test_health_runtime_detects_colab(monkeypatch):
    monkeypatch.setitem(_sys.modules, "google.colab", types.ModuleType("google.colab"))
    assert api_auth.detect_runtime() == "colab"


@pytest.fixture()
def tmp_dist(tmp_path, monkeypatch):
    project = tmp_path / "project"
    dist = project / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>SPA</html>", encoding="utf-8")
    (dist / "manifest.webmanifest").write_text("{}", encoding="utf-8")
    (dist / "pwa-192.png").write_bytes(b"png")
    (project / ".env").write_text("SECRET=leak", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("outside", encoding="utf-8")
    monkeypatch.setattr(api_server_module, "DIST_DIR", dist)
    return dist


def test_resolve_spa_file_contains_paths(tmp_dist, tmp_path):
    resolve = api_server_module.resolve_spa_file
    assert resolve(tmp_dist, "pwa-192.png") == (tmp_dist / "pwa-192.png").resolve()
    for evil in ("../../.env", r"..\..\.env", "../../../outside.txt",
                 str(tmp_path / "outside.txt"), str(tmp_dist.parent.parent / ".env"),
                 "/etc/passwd", "C:/Windows/win.ini", "", "assets", "a\x00b"):
        assert resolve(tmp_dist, evil) is None, evil


def _spa_route_or_skip():
    if not any(getattr(r, "path", "") == "/{full_path:path}" for r in app.routes):
        pytest.skip("frontend/dist not built: SPA catch-all route not registered")


@pytest.mark.parametrize("path", [
    "/..%2f..%2f.env",
    "/..%2F..%2F..%2Foutside.txt",
    "/%2e%2e/%2e%2e/.env",
    "/..%5c..%5c.env",
])
def test_spa_catch_all_never_serves_outside_dist(tmp_dist, path):
    _spa_route_or_skip()
    res = _fresh_client().get(path)
    assert "leak" not in res.text and "outside" not in res.text
    if res.status_code == 200:
        assert res.text == "<html>SPA</html>"


def test_spa_catch_all_absolute_path_variant(tmp_dist, tmp_path):
    _spa_route_or_skip()
    absolute = str(tmp_path / "outside.txt").replace("\\", "/")
    res = _fresh_client().get("/" + absolute)
    assert "outside" not in res.text


def test_spa_cache_headers(tmp_dist):
    _spa_route_or_skip()
    c = _fresh_client()
    assert c.get("/").headers.get("cache-control") == "no-cache"
    assert c.get("/some/client/route").headers.get("cache-control") == "no-cache"
    assert c.get("/manifest.webmanifest").headers.get("cache-control") == "no-cache"
    assert c.get("/pwa-192.png").headers.get("cache-control") is None


def test_hashed_assets_get_immutable_cache(tmp_path):
    from starlette.applications import Starlette
    from starlette.routing import Mount

    (tmp_path / "index-abc123.js").write_text("x", encoding="utf-8")
    static_app = Starlette(routes=[Mount(
        "/assets", app=api_server_module._ImmutableStaticFiles(directory=str(tmp_path)))])
    c = TestClient(static_app)
    res = c.get("/assets/index-abc123.js")
    assert res.status_code == 200
    assert res.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert "cache-control" not in c.get("/assets/missing.js").headers
