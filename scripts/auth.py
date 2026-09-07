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

import logging
import os
import secrets
from pathlib import Path

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
    return secrets.compare_digest(candidate, configured)


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
