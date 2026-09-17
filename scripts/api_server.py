"""
FastAPI Backend Server for OmniCut Pro Studio AI & CapCut Pipeline.
Provides REST APIs, video/audio streaming with byte-range support, and SSE progress updates.
This root module configures the FastAPI application, mounts modular routers, and runs the server.
"""

import os
import sys
import ipaddress
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, EXPORTS_DIR, ASSETS_DIR,
    FONTS_DIR, SFX_DIR, MUSIC_DIR, STICKERS_DIR, PROJECTS_DIR,
    CAPCUT_DRAFT_DIR, VOICES, DEFAULT_VOICE, DEFAULT_VOICE_RATE
)
from scripts.auth import (
    API_KEY_HEADER, is_auth_enforced, key_matches, warn_if_permissive,
)

# Re-exports for backwards compatibility with tests and scripts
from scripts.it_angles import DEFAULT_BGM
from scripts.media_service import get_local_ip
from scripts.api_exports import list_exports, link_export_to_angle
from scripts.api_schemas import (
    ScriptGenerateRequest, VoicePreviewRequest, RenderRequest,
    DeleteFileRequest, AddPostRequest, UpdatePostMetricsRequest,
    OpenFolderRequest, TranscribeRequest, RenameVideoPayload,
    ReassignVideoPayload, BatchDeleteVideosPayload, LinkAngleRequest
)

# Parity and routing contracts (mounted via api_videos and api_render):
# "default_bgm": DEFAULT_BGM,
# overlays

# Modular Routers
from scripts.api_phase1 import router as phase1_router
from scripts.api_editor import router as editor_router
from scripts.api_tokens import router as tokens_router
from scripts.api_voice import router as voice_router
from scripts.api_videos import router as videos_router
from scripts.api_covers import router as covers_router
from scripts.api_tiktok_autopost import router as tiktok_autopost_router
from scripts.api_schedule_queue import router as schedule_queue_router
from scripts.api_products import router as products_router
from scripts.api_exports import router as exports_router
from scripts.api_tasks import router as tasks_router
from scripts.api_render import router as render_router
from scripts.api_posts import router as posts_router
from scripts.api_shot_lists import router as shot_lists_router
from scripts.api_recording import router as recording_router
from scripts.api_analytics import router as analytics_router
from scripts.api_tiktok_stats import router as tiktok_stats_router
from scripts.api_backup import router as backup_router
from scripts.api_asset_dedup import router as asset_dedup_router
from scripts.api_hooks import router as hooks_router
from scripts.api_batch_render import router as batch_render_router
from scripts.batch_render import BatchRenderManager
from scripts.api_producer import router as producer_router
from scripts.api_background_isolation import (
    recover_background_isolation_tasks,
    router as background_isolation_router,
)


def recover_startup_work() -> dict[str, int]:
    """Recover durable workers once the FastAPI server is actually starting.

    Keeping this behind an explicit helper makes importing ``api_server`` safe
    for tests, CLI tooling, and app inspection.  Each recovery subsystem is
    isolated so a corrupt checkpoint cannot prevent the other worker from
    starting.
    """

    recovered = {
        "background_isolation": 0,
        "batch_render": 0,
    }
    try:
        recovered["background_isolation"] = recover_background_isolation_tasks()
        if recovered["background_isolation"]:
            print(
                "[BackgroundIsolation] resumed "
                f"{recovered['background_isolation']} checkpointed task(s)"
            )
    except Exception as exc:
        # A stale/corrupt task record must never prevent the API from starting.
        print(f"[BackgroundIsolation] startup recovery skipped: {exc}")

    try:
        recovered["batch_render"] = BatchRenderManager.recover_pending_batches()
        if recovered["batch_render"]:
            print(
                "[BatchRender] resumed "
                f"{recovered['batch_render']} checkpointed batch(es)"
            )
    except Exception as exc:
        print(f"[BatchRender] startup recovery skipped: {exc}")

    return recovered


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run durable worker recovery at server startup, never at module import."""

    _app.state.startup_recovery = recover_startup_work()
    yield


app = FastAPI(
    title="OmniCut Pro Studio API",
    description="Backend API for OmniCut Pro Studio AI & CapCut Desktop Generator",
    version="2.0.0",
    lifespan=lifespan,
)

# Warn loudly at import time if no shared secret is configured -- this is
# the single most important place for the owner to see it (uvicorn console,
# or the first pytest collection).
warn_if_permissive()

# ----------------------------------------------------------------------
# CORS -- explicit allowlist, read from env. Vite's dev server proxies
# /api/* requests from the frontend (see frontend/vite.config.js: target
# http://127.0.0.1:8000, port 5173), so the browser's Origin header on
# those requests is the Vite dev origin, not the backend -- hence the
# defaults below. The Chrome extension (tiktok_autopost_extension/) calls
# the API directly, cross-origin, from a chrome-extension://<id> origin;
# Chrome exempts fetches to hosts declared in the extension's
# host_permissions (manifest.json already lists http://127.0.0.1:8000/*)
# from the usual CORS response-blocking, so it does not need to appear in
# this list to keep working. The API key check below is what actually
# gates the extension's requests.
#
# allow_origins cannot be ["*"] together with allow_credentials=True --
# browsers reject that combination outright -- so this must stay an
# explicit list now that allow_credentials=True is kept for cookie-based
# auth headroom.
_default_cors_origins = "http://localhost:5173,http://127.0.0.1:5173,https://localhost:5173,https://127.0.0.1:5173"
CORS_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", _default_cors_origins).split(",")
    if o.strip()
]


_LOCAL_BIND_NAMES = {"localhost", "127.0.0.1", "::1", "[::1]"}


def _is_loopback_host(host: str | None) -> bool:
    """Return whether a bind/client host is unambiguously local-only."""
    normalized = (host or "").strip().lower()
    if normalized in _LOCAL_BIND_NAMES:
        return True
    try:
        return ipaddress.ip_address(normalized.strip("[]")).is_loopback
    except ValueError:
        return False


def get_bind_host() -> str:
    """Resolve and validate the server bind host.

    The default is loopback so the normal single-user setup is not exposed
    to the LAN.  An explicit non-loopback bind requires the shared API key;
    this check protects the ``python scripts/api_server.py`` launch path.
    The middleware below is still the defense-in-depth check for callers that
    start Uvicorn with its own ``--host`` flag.
    """
    host = os.environ.get("OMNICUT_HOST", "127.0.0.1").strip() or "127.0.0.1"
    if not _is_loopback_host(host) and not is_auth_enforced():
        raise RuntimeError(
            "OMNICUT_API_KEY is required when OMNICUT_HOST binds beyond localhost"
        )
    return host


def _is_local_request(request: Request) -> bool:
    """Allow the intentionally unauthenticated mode only to local clients.

    ``testclient`` is Starlette's synthetic peer name and is safe to permit
    here because it cannot be produced by a real TCP client.
    """
    if request.client is None:
        return True
    return _is_loopback_host(request.client.host) or request.client.host == "testclient"

async def api_key_gate(request: Request, call_next):
    """Single shared-secret check applied to every request.

    Behavior:
    - OMNICUT_API_KEY unset (default local single-user setup): requests from
      loopback pass through, but non-loopback clients are rejected. This
      keeps localhost development working while making an accidental LAN
      bind fail closed.
    - OMNICUT_API_KEY set: every request must carry a matching
      `X-API-Key` header (constant-time compare), or it gets 401.
      CORS preflight (OPTIONS) is let through unauthenticated -- browsers
      never attach custom headers to the preflight itself, and the
      CORSMiddleware below (registered after this one, so it wraps
      OUTSIDE it -- Starlette builds its stack in reverse registration
      order) still enforces the origin allowlist on it, and still
      attaches Access-Control-Allow-Origin to a 401 from this gate so the
      frontend/extension see a readable error instead of an opaque CORS
      failure.
    - GET/HEAD media requests only: also accepts the key as an
      `?api_key=` query param, falling back to it when the header is absent
      or wrong. Native
      <video>/<audio>/<img> tags (used for /api/media/... streaming and
      thumbnails) cannot attach a custom header at all -- the frontend's
      Vite proxy normally injects the header; direct-to-backend deployments
      can explicitly opt into the legacy query-param path.
      Query params can end up in server access logs and browser history,
      so this fallback is deliberately withheld from every mutating verb.
    """
    if request.method == "OPTIONS":
        return await call_next(request)

    if not is_auth_enforced():
        warn_if_permissive()
        if _is_local_request(request):
            return await call_next(request)
        return JSONResponse(
            status_code=401,
            content={
                "detail": (
                    "OMNICUT_API_KEY is required for non-local access. "
                    "Bind the API to localhost or configure the shared key."
                )
            },
        )

    candidate = request.headers.get(API_KEY_HEADER, "")
    if (
        not key_matches(candidate)
        and request.method in ("GET", "HEAD")
        and request.url.path.startswith("/api/media/")
    ):
        candidate = request.query_params.get("api_key", "")
    if not key_matches(candidate):
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing or invalid API key. Set the X-API-Key header."},
        )

    return await call_next(request)


# Registration order matters: Starlette wraps middleware in REVERSE of
# add_middleware() call order, so the first one added ends up outermost.
# The key gate is added first so it becomes the inner layer; CORS is added
# second so it wraps every response (including a 401 from the gate) with
# the right Access-Control-* headers.
app.middleware("http")(api_key_gate)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount all domain-specific routers
app.include_router(phase1_router)
app.include_router(editor_router)
app.include_router(tokens_router)
app.include_router(voice_router)
app.include_router(videos_router)
app.include_router(covers_router)
app.include_router(tiktok_autopost_router)
app.include_router(schedule_queue_router)
app.include_router(products_router)
app.include_router(exports_router)
app.include_router(tasks_router)
app.include_router(render_router)
app.include_router(posts_router)
app.include_router(shot_lists_router)
app.include_router(recording_router)
app.include_router(analytics_router)
app.include_router(tiktok_stats_router)
app.include_router(backup_router)
app.include_router(asset_dedup_router)
app.include_router(hooks_router)
app.include_router(batch_render_router)
app.include_router(producer_router)
app.include_router(background_isolation_router)

# ----------------------------------------------------------------------
# Run Server directly if executed
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    should_reload = os.environ.get("FASTAPI_RELOAD", "true").lower() in ("1", "true")
    uvicorn.run(
        "scripts.api_server:app",
        host=get_bind_host(),
        port=8000,
        reload=should_reload
    )
