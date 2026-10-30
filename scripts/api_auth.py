"""
Remote-access auth for OmniCut Pro Studio: login router + ASGI gate.

Why: on Google Colab the API is exposed publicly through a Cloudflare tunnel
(cloudflared -> 127.0.0.1:8000). Tunnel traffic looks like loopback, so the
old "loopback == trusted" rule (plus a blanket Colab bypass) left every route
-- including the ttyd root web shell at /terminal, /ws, /agy -- open to anyone
holding the URL.

Pieces:
- ``router``: ``GET /api/auth/me``, ``POST /api/auth/login``,
  ``POST /api/auth/logout`` (cookie ``omnicut_session``).
- ``AuthGateMiddleware``: pure ASGI, covers BOTH ``http`` and ``websocket``
  scopes (the old ``@app.middleware("http")`` gate never saw WebSockets).

Decision table (see ``evaluate_access``):
- OPTIONS, /api/auth/*, /api/health, SPA shell + static assets -> allow.
- LOCAL (loopback/testclient peer, no forward headers):
    * OMNICUT_API_KEY unset -> allow (single-user dev machine).
    * OMNICUT_API_KEY set   -> /api/* needs X-API-Key (or a valid session
      cookie); non-/api paths stay open as before.
- REMOTE (anything else): valid session cookie or valid X-API-Key, otherwise
    * no OMNICUT_APP_PASSWORD -> 503 (fail closed),
    * HTML navigation         -> 302 /?login=1&next=<path>,
    * otherwise               -> 401 {"detail", "login_required": true}.
- WebSocket: same auth rule, rejected with close 4401 (auth) / 4403 (origin)
  BEFORE accept. Remote WS also needs ``Origin`` host == ``Host``.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional
from urllib.parse import quote, urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.datastructures import Headers, QueryParams
from starlette.requests import cookie_parser
from starlette.responses import RedirectResponse

from scripts import auth

logger = logging.getLogger("omnicut.auth")

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ----------------------------------------------------------------------------
# Messages (contract -- frontend matches on status + login_required)
# ----------------------------------------------------------------------------
MSG_LOGIN_REQUIRED = "ต้องเข้าสู่ระบบก่อน"
MSG_WRONG_PASSWORD = "รหัสผ่านไม่ถูกต้อง"
MSG_RATE_LIMITED = "ลองบ่อยเกินไป รอ 1 นาที"
MSG_NOT_CONFIGURED = "ยังไม่ได้ตั้งรหัสผ่านแอป (OMNICUT_APP_PASSWORD)"
MSG_LOCAL_API_KEY = "Missing or invalid API key. Set the X-API-Key header."

WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_FORBIDDEN_ORIGIN = 4403

# ----------------------------------------------------------------------------
# Exempt paths (always reachable so a login screen can render)
# ----------------------------------------------------------------------------
_EXEMPT_EXACT = frozenset({
    "/",
    "/index.html",
    "/manifest.webmanifest",
    "/favicon.ico",
    "/favicon.svg",
    "/icons.svg",
    "/apple-touch-icon.png",
    "/api/health",
    "/api/auth",
})
_EXEMPT_PREFIXES = ("/api/auth/", "/assets/", "/icons/")
_PWA_ICON_RE = re.compile(r"^/pwa-[A-Za-z0-9_-]+\.png$")


def is_exempt_path(path: str) -> bool:
    if not path:
        return False
    # Never exempt anything that could be normalised into another route.
    if "\\" in path or "//" in path or any(seg in ("..", ".") for seg in path.split("/")):
        return False
    if path in _EXEMPT_EXACT:
        return True
    if any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES):
        return True
    return bool(_PWA_ICON_RE.match(path))


# ----------------------------------------------------------------------------
# Credential checks
# ----------------------------------------------------------------------------

def _api_key_ok(headers: Headers, method: str, path: str, query: QueryParams) -> bool:
    candidate = headers.get(auth.API_KEY_HEADER, "")
    if auth.key_matches(candidate):
        return True
    # Legacy: native <video>/<img> tags cannot set headers -> GET/HEAD media
    # only may carry ?api_key= (never for mutating verbs; it leaks into logs).
    if method in ("GET", "HEAD") and path.startswith("/api/media/"):
        return auth.key_matches(query.get("api_key", ""))
    return False


def credential_method(headers: Headers, cookies: dict, method: str, path: str,
                      query: QueryParams) -> Optional[str]:
    """Return ``"cookie"`` / ``"api_key"`` / None for presented credentials."""
    if auth.verify_session_token(cookies.get(auth.SESSION_COOKIE_NAME)):
        return "cookie"
    if _api_key_ok(headers, method, path, query):
        return "api_key"
    return None


def _host_port(netloc: str) -> tuple[Optional[str], Optional[int]]:
    try:
        parts = urlsplit(f"//{netloc}")
        return (parts.hostname or None), parts.port
    except ValueError:
        return None, None


def origin_matches_host(origin: str, host: str) -> bool:
    """True when the Origin's host[:port] equals the request Host header."""
    if not origin or not host:
        return False
    try:
        o = urlsplit(origin)
        o_host, o_port = o.hostname, o.port
    except ValueError:
        return False
    if not o_host:
        return False
    default_port = {"http": 80, "https": 443, "ws": 80, "wss": 443}.get((o.scheme or "").lower())
    o_port = o_port or default_port
    h_host, h_port = _host_port(host)
    if not h_host or h_host.lower() != o_host.lower():
        return False
    if h_port is None:
        return o_port in (80, 443)
    return h_port == o_port


# ----------------------------------------------------------------------------
# Decision
# ----------------------------------------------------------------------------

@dataclass
class Decision:
    allow: bool
    method: Optional[str] = None          # local | cookie | api_key | exempt
    status: int = 200
    body: dict = field(default_factory=dict)
    redirect_to: Optional[str] = None
    ws_close_code: Optional[int] = None


def _deny(status: int, detail: str, ws_code: int = WS_CLOSE_UNAUTHORIZED, **extra) -> Decision:
    return Decision(allow=False, status=status, body={"detail": detail, **extra}, ws_close_code=ws_code)


def evaluate_access(
    *,
    scope_type: str,
    method: str,
    path: str,
    client_host: Optional[str],
    headers: Headers,
    cookies: dict,
    query: QueryParams,
    allowed_origins: Iterable[str] = (),
) -> Decision:
    """Pure decision function shared by the ASGI gate (and unit tests)."""
    is_ws = scope_type == "websocket"
    method = (method or ("GET" if is_ws else "")).upper()

    if not is_ws and method == "OPTIONS":
        return Decision(allow=True, method="exempt")
    if not is_ws and is_exempt_path(path):
        return Decision(allow=True, method="exempt")

    kind = auth.classify_request(client_host, headers)
    origin = headers.get("origin", "")
    host = headers.get("host", "")

    if kind == "local":
        if is_ws and origin and not (
            origin_matches_host(origin, host) or origin in set(allowed_origins)
        ):
            # Cross-site WebSocket hijacking guard: a random web page open in
            # the owner's browser must not reach the local ttyd shell.
            return _deny(403, "origin not allowed", WS_CLOSE_FORBIDDEN_ORIGIN)
        if not auth.is_auth_enforced():
            auth.warn_if_permissive()
            return Decision(allow=True, method="local")
        if not path.startswith("/api"):
            return Decision(allow=True, method="local")
        cred = credential_method(headers, cookies, method, path, query)
        if cred:
            return Decision(allow=True, method=cred)
        return _deny(401, MSG_LOCAL_API_KEY)

    # ---- REMOTE ----
    cred = credential_method(headers, cookies, method, path, query)
    if cred:
        if is_ws and not origin_matches_host(origin, host):
            return _deny(403, "origin not allowed", WS_CLOSE_FORBIDDEN_ORIGIN)
        return Decision(allow=True, method=cred)

    if not auth.is_password_configured():
        return _deny(503, MSG_NOT_CONFIGURED)
    if is_ws:
        return _deny(401, MSG_LOGIN_REQUIRED, login_required=True)
    accept = headers.get("accept", "").lower()
    if method in ("GET", "HEAD") and "text/html" in accept and not path.startswith("/api/"):
        return Decision(
            allow=False,
            status=302,
            redirect_to=f"/?login=1&next={quote(path, safe='/')}",
        )
    return _deny(401, MSG_LOGIN_REQUIRED, login_required=True)


# ----------------------------------------------------------------------------
# ASGI middleware
# ----------------------------------------------------------------------------

class AuthGateMiddleware:
    """Pure ASGI auth gate for ``http`` and ``websocket`` scopes."""

    def __init__(self, app, allowed_origins: Iterable[str] = ()):
        self.app = app
        self.allowed_origins = tuple(allowed_origins)

    async def __call__(self, scope, receive, send):
        scope_type = scope.get("type")
        if scope_type not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        client = scope.get("client")
        client_host = client[0] if client else None
        cookies = cookie_parser(headers.get("cookie", "")) if headers.get("cookie") else {}
        query = QueryParams(scope.get("query_string", b""))

        decision = evaluate_access(
            scope_type=scope_type,
            method=scope.get("method", ""),
            path=scope.get("path", ""),
            client_host=client_host,
            headers=headers,
            cookies=cookies,
            query=query,
            allowed_origins=self.allowed_origins,
        )
        if decision.allow:
            await self.app(scope, receive, send)
            return

        if scope_type == "websocket":
            # Reject before accept: consume the connect event, then close.
            # Uvicorn turns a pre-accept close into an HTTP 403 handshake.
            message = await receive()
            if message.get("type") == "websocket.connect":
                await send({
                    "type": "websocket.close",
                    "code": decision.ws_close_code or WS_CLOSE_UNAUTHORIZED,
                    "reason": "",
                })
            return

        if decision.redirect_to:
            response = RedirectResponse(decision.redirect_to, status_code=302)
        else:
            response = JSONResponse(status_code=decision.status, content=decision.body)
        await response(scope, receive, send)


# ----------------------------------------------------------------------------
# Login rate limiter (in-memory, per client IP, sliding 60s window)
# ----------------------------------------------------------------------------

LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60.0
_MAX_TRACKED_IPS = 10_000


class LoginRateLimiter:
    def __init__(self, max_attempts: int = LOGIN_MAX_ATTEMPTS,
                 window: float = LOGIN_WINDOW_SECONDS):
        self.max_attempts = max_attempts
        self.window = window
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def hit(self, ip: str) -> bool:
        """Record one attempt; return False when the IP is over the limit."""
        now = auth._now()
        with self._lock:
            if len(self._hits) > _MAX_TRACKED_IPS:
                self._hits.clear()
            bucket = self._hits.setdefault(ip, deque())
            while bucket and now - bucket[0] >= self.window:
                bucket.popleft()
            if len(bucket) >= self.max_attempts:
                return False
            bucket.append(now)
            return True

    def reset(self, ip: Optional[str] = None) -> None:
        with self._lock:
            if ip is None:
                self._hits.clear()
            else:
                self._hits.pop(ip, None)


login_rate_limiter = LoginRateLimiter()


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------

class LoginRequest(BaseModel):
    password: str = Field(..., max_length=1024)


def _client_host(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def _cookie_kwargs(request: Request) -> dict:
    return {
        "path": "/",
        "httponly": True,
        "samesite": "lax",
        "secure": auth.is_secure_request(request.url.scheme, request.headers),
    }


@router.get("/me")
def auth_me(request: Request):
    kind = auth.classify_request(_client_host(request), request.headers)
    local = kind == "local"
    method = credential_method(
        request.headers, request.cookies, request.method, request.url.path, request.query_params
    )
    if method is None and local and not auth.is_auth_enforced():
        method = "local"
    return {
        "authenticated": method is not None,
        "auth_required": (not local) or auth.is_auth_enforced(),
        "method": method,
        "password_configured": auth.is_password_configured(),
    }


@router.post("/login")
def auth_login(payload: LoginRequest, request: Request):
    if not auth.is_password_configured():
        return JSONResponse(status_code=503, content={"detail": MSG_NOT_CONFIGURED})
    ip = auth.client_ip_for_rate_limit(_client_host(request), request.headers)
    if not login_rate_limiter.hit(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": MSG_RATE_LIMITED},
            headers={"Retry-After": str(int(LOGIN_WINDOW_SECONDS))},
        )
    if not auth.password_matches(payload.password):
        logger.warning("[Auth] เข้าสู่ระบบไม่สำเร็จ (รหัสผ่านผิด) จาก %s", ip)
        return JSONResponse(status_code=401, content={"detail": MSG_WRONG_PASSWORD})
    token = auth.issue_session_token()
    if token is None:  # pragma: no cover - password configured => key exists
        return JSONResponse(status_code=503, content={"detail": MSG_NOT_CONFIGURED})
    login_rate_limiter.reset(ip)
    response = JSONResponse(content={"ok": True})
    response.set_cookie(
        auth.SESSION_COOKIE_NAME,
        token,
        max_age=auth.SESSION_MAX_AGE_SECONDS,
        **_cookie_kwargs(request),
    )
    return response


@router.post("/logout")
def auth_logout(request: Request):
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(auth.SESSION_COOKIE_NAME, **_cookie_kwargs(request))
    return response


# ----------------------------------------------------------------------------
# Health (exempt from the gate; cheap -- no disk scan, no secrets)
# ----------------------------------------------------------------------------

health_router = APIRouter(tags=["Health"])

_STARTED_AT = datetime.now(timezone.utc).isoformat(timespec="seconds")


def detect_runtime() -> str:
    """``"colab"`` on Google Colab, else ``"local"`` (informational only --
    never used for access decisions)."""
    if "google.colab" in sys.modules or os.path.isdir("/content"):
        return "colab"
    return "local"


@health_router.get("/api/health")
def health(request: Request):
    kind = auth.classify_request(_client_host(request), request.headers)
    return {
        "ok": True,
        "version": getattr(request.app, "version", None),
        "runtime": detect_runtime(),
        "started_at": _STARTED_AT,
        "auth_required": kind != "local" or auth.is_auth_enforced(),
    }
