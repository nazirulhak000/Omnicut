"""
FastAPI Backend Server for OmniCut Pro Studio AI & CapCut Pipeline.
Provides REST APIs, video/audio streaming with byte-range support, and SSE progress updates.
This root module configures the FastAPI application, mounts modular routers, and runs the server.
"""

import os
import sys
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

app = FastAPI(
    title="OmniCut Pro Studio API",
    description="Backend API for OmniCut Pro Studio AI & CapCut Desktop Generator",
    version="2.0.0"
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
_default_cors_origins = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", _default_cors_origins).split(",")
    if o.strip()
]

async def api_key_gate(request: Request, call_next):
    """Single shared-secret check applied to every request.

    Behavior:
    - OMNICUT_API_KEY unset (default local single-user setup): every
      request passes through untouched. warn_if_permissive() already
      logged this loudly at startup so it's never a silent hole.
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
    """
    if not is_auth_enforced() or request.method == "OPTIONS":
        return await call_next(request)

    candidate = request.headers.get(API_KEY_HEADER, "")
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

# ----------------------------------------------------------------------
# Run Server directly if executed
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    should_reload = os.environ.get("FASTAPI_RELOAD", "true").lower() in ("1", "true")
    uvicorn.run(
        "scripts.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=should_reload
    )
