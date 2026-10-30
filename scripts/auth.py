"""
Shared-secret API key gate for the local API server.

This is the LOCAL-APP hardening step, not a multi-tenant auth system. One
secret, one owner. Proper per-user auth (JWT/session, tenant scoping) is a
separate, later migration step -- see _Docs/SAAS_READINESS_PLAN.md step 4.

Why this exists: with CORS wide open and zero auth, any web page the owner
happens to have open in a browser tab can call this API while the app runs
-- including endpoints that spend money on AI, post to TikTok, delete
files, and start renders. A single shared secret checked on every request
closes that hole without requiring a user model, login UI, or session
store.

Convention: follows the same manual .env loading pattern already used by
ai_bridge.py / gemini_tts_engine.py / gemini_vision_matcher.py (no central
loader in config.py, os.environ.setdefault so real env vars always win).
"""

import base64
import hashlib
import hmac
import ipaddress
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Mapping, Optional

logger = logging.getLogger("omnicut.auth")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Header the frontend (via Vite's dev proxy, which can inject it) and the
# Chrome extension (calling the API directly, cross-origin) both send.
API_KEY_HEADER = "X-API-Key"


def _load_env_file() -> None:
    """Read .env into the environment without overriding anything already set."""
    if not ENV_FILE.exists():
        return
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


def get_configured_api_key() -> str:
    """Return the configured shared secret, or '' if none is set.

    Re-reads os.environ each call (not cached at import time) so tests can
    monkeypatch os.environ / .env without reloading this module.
    """
    return os.environ.get("OMNICUT_API_KEY", "").strip()


def is_auth_enforced() -> bool:
    """True when a shared secret is configured and must be checked."""
    return bool(get_configured_api_key())


def key_matches(candidate: str) -> bool:
    """Constant-time comparison against the configured secret."""
    configured = get_configured_api_key()
    if not configured:
        return False
    if not candidate:
        return False
    # bytes, not str: compare_digest(str, str) raises TypeError on non-ASCII
    # input, which would turn a junk header into a 500 instead of a 401.
    return secrets.compare_digest(
        candidate.encode("utf-8", "replace"), configured.encode("utf-8", "replace")
    )


_warned_permissive = False


def warn_if_permissive() -> None:
    """Log a loud, impossible-to-miss warning once when no key is configured.

    Called at startup (app import time) and defensively from the middleware
    the first time it runs, so the warning appears whether the server was
    started via uvicorn, tests, or a script that imports the app directly.
    """
    global _warned_permissive
    if is_auth_enforced() or _warned_permissive:
        return
    _warned_permissive = True
    logger.warning(
        "=" * 70 + "\n"
        "OMNICUT_API_KEY is NOT set -- running with NO API authentication.\n"
        "Every endpoint (including AI generation, TikTok auto-post, file\n"
        "delete, and render) is reachable by ANY request that can reach this\n"
        "port, from ANY origin allowed by CORS_ORIGINS.\n"
        "This is fine for a single-user machine you fully control. Before\n"
        "exposing this port beyond localhost, set OMNICUT_API_KEY in .env.\n"
        + "=" * 70
    )
    print(
        "\n⚠️  [Auth] OMNICUT_API_KEY not set -- API is running with NO authentication. "
        "See .env.example.\n"
    )


# ======================================================================
# Remote access: app password + stateless signed session cookie
# ======================================================================
#
# The backend is reachable publicly through a Cloudflare tunnel when it runs
# on Google Colab. cloudflared connects to 127.0.0.1:8000, so tunnel traffic
# LOOKS like loopback -- the forward headers below are what give it away.
# Classification rule (see classify_request):
#   LOCAL  = client host is loopback/"testclient" AND none of the forward
#            headers are present.
#   REMOTE = everything else. Remote requests need a valid session cookie
#            (obtained by POST /api/auth/login with OMNICUT_APP_PASSWORD) or
#            a valid X-API-Key.
#
# Only stdlib crypto (hmac/hashlib/secrets) -- no new dependency.

SESSION_COOKIE_NAME = "omnicut_session"
SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60  # 30 days
_SESSION_TOKEN_VERSION = "v1"
_CLOCK_SKEW_SECONDS = 300

# Headers a reverse proxy / tunnel adds. Any one of them => REMOTE, even when
# the TCP peer is 127.0.0.1 (cloudflared, nginx, a dev proxy with xfwd...).
FORWARD_HEADERS = (
    "cf-connecting-ip",
    "cf-ray",
    "x-forwarded-for",
    "forwarded",
    "x-forwarded-host",
    "x-real-ip",
)

_LOOPBACK_NAMES = {"localhost", "127.0.0.1", "::1", "[::1]", "testclient"}


def _now() -> float:
    """Wall clock, indirected so tests can monkeypatch time deterministically."""
    return time.time()


def get_app_password() -> str:
    """Return OMNICUT_APP_PASSWORD ('' when unset). Re-read on every call."""
    return os.environ.get("OMNICUT_APP_PASSWORD", "").strip()


def is_password_configured() -> bool:
    return bool(get_app_password())


def password_matches(candidate: str) -> bool:
    """Constant-time comparison against OMNICUT_APP_PASSWORD."""
    configured = get_app_password()
    if not configured or not isinstance(candidate, str) or not candidate:
        return False
    return hmac.compare_digest(
        candidate.encode("utf-8"), configured.encode("utf-8")
    )


def _hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """RFC 5869 HKDF (extract + expand) with SHA-256, stdlib only."""
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm = b""
    block = b""
    counter = 1
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        okm += block
        counter += 1
    return okm[:length]


def _session_signing_key() -> Optional[bytes]:
    """Signing key: OMNICUT_SESSION_SECRET, else derived from the password.

    Deriving from the password means changing OMNICUT_APP_PASSWORD
    invalidates every outstanding session cookie. Returns None when neither
    is configured (no session can be issued or verified).
    """
    secret = os.environ.get("OMNICUT_SESSION_SECRET", "").strip()
    password = get_app_password()
    if secret:
        # The password digest is mixed into the HKDF info so that rotating the
        # password still invalidates sessions even with a persisted secret
        # (the Colab runner stores OMNICUT_SESSION_SECRET in Drive).
        pw_digest = hashlib.sha256(password.encode("utf-8")).digest() if password else b""
        return _hkdf_sha256(
            secret.encode("utf-8"), b"omnicut-session-salt-v1",
            b"omnicut-session-secret" + pw_digest,
        )
    if password:
        return _hkdf_sha256(
            password.encode("utf-8"), b"omnicut-session-salt-v1", b"omnicut-session-password"
        )
    return None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _sign(key: bytes, payload: str) -> str:
    # utf-8 (not ascii): the payload being verified is attacker-controlled.
    return _b64url(hmac.new(key, payload.encode("utf-8", "replace"), hashlib.sha256).digest())


def issue_session_token(max_age: int = SESSION_MAX_AGE_SECONDS) -> Optional[str]:
    """Create a stateless signed token ``v1.<iat>.<exp>.<nonce>.<sig>``."""
    key = _session_signing_key()
    if key is None:
        return None
    iat = int(_now())
    exp = iat + int(max_age)
    nonce = secrets.token_urlsafe(12)
    payload = f"{_SESSION_TOKEN_VERSION}.{iat}.{exp}.{nonce}"
    return f"{payload}.{_sign(key, payload)}"


def verify_session_token(token: Optional[str]) -> bool:
    """True only for an untampered, unexpired token signed with the current key."""
    if not token or not isinstance(token, str) or len(token) > 512:
        return False
    key = _session_signing_key()
    if key is None:
        return False
    parts = token.split(".")
    if len(parts) != 5 or parts[0] != _SESSION_TOKEN_VERSION:
        return False
    payload = ".".join(parts[:4])
    # Compare bytes: compare_digest(str, str) raises TypeError on non-ASCII.
    if not hmac.compare_digest(
        _sign(key, payload).encode("ascii"), parts[4].encode("utf-8", "replace")
    ):
        return False
    try:
        iat = int(parts[1])
        exp = int(parts[2])
    except ValueError:
        return False
    now = _now()
    if exp <= now:
        return False
    if iat > now + _CLOCK_SKEW_SECONDS:
        return False
    if exp - iat > SESSION_MAX_AGE_SECONDS + _CLOCK_SKEW_SECONDS:
        return False
    return True


def _is_loopback_client(host: Optional[str]) -> bool:
    normalized = (host or "").strip().lower()
    if normalized in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(normalized.strip("[]")).is_loopback
    except ValueError:
        return False


def has_forward_headers(headers: Mapping[str, str]) -> bool:
    """``headers`` must be a case-insensitive mapping (Starlette Headers)."""
    return any(headers.get(name) for name in FORWARD_HEADERS)


def classify_request(client_host: Optional[str], headers: Mapping[str, str]) -> str:
    """Return ``"local"`` or ``"remote"`` (see module notes above).

    A missing client (``None``) is treated as REMOTE -- fail closed.
    """
    if client_host is None:
        return "remote"
    if _is_loopback_client(client_host) and not has_forward_headers(headers):
        return "local"
    return "remote"


def client_ip_for_rate_limit(client_host: Optional[str], headers: Mapping[str, str]) -> str:
    """Prefer Cloudflare's real-client header; else the TCP peer."""
    cf_ip = (headers.get("cf-connecting-ip") or "").strip()
    if cf_ip:
        return cf_ip
    return client_host or "unknown"


def is_secure_request(scheme: str, headers: Mapping[str, str]) -> bool:
    """https directly, or https at the edge (x-forwarded-proto / cf-visitor)."""
    if (scheme or "").lower() in ("https", "wss"):
        return True
    xfp = (headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if xfp == "https":
        return True
    cf_visitor = (headers.get("cf-visitor") or "").replace(" ", "").lower()
    return '"scheme":"https"' in cf_visitor
