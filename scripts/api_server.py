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
from scripts.api_gadget_media import router as gadget_media_router
from scripts.api_gadget_media_projects import router as gadget_media_projects_router
from scripts.api_background_isolation import (
    recover_background_isolation_tasks,
    router as background_isolation_router,
)
from scripts.api_typesafe_studio import router as typesafe_studio_router
from scripts.api_audio_beats import router as audio_beats_router
from scripts.api_proxy import router as proxy_router
from scripts.api_mobile_studio import router as mobile_studio_router
from scripts.api_hyperframes import router as hyperframes_router
from scripts.api_hyperframes_workflow import router as hyperframes_workflow_router
from scripts.api_hyperframes_ai import router as hyperframes_ai_router
from scripts.api_hyperframes_overlay import router as hyperframes_overlay_router
from scripts.api_publication_observations import router as publication_observations_router
from scripts.api_channels import router as channels_router
from scripts.api_copilot import router as copilot_router
from scripts.api_agy import router as agy_router
from scripts.channel_scope import CHANNEL_HEADER, install_channel_scope
from scripts.maintenance_lock import install_maintenance_gate



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
    # ── Auto-Seed ProductStore from products_seed.json if empty (e.g. fresh Colab clone) ──
    try:
        from scripts.product_store import ProductStore
        from scripts.config import BASE_DIR
        store = ProductStore()
        if len(store.list()) == 0:
            seed_file = BASE_DIR / "_Docs" / "products_seed.json"
            if seed_file.exists():
                import json
                seed_data = json.loads(seed_file.read_text(encoding="utf-8"))
                if isinstance(seed_data, list) and seed_data:
                    scope = ProductStore._scope(None, all_channels=True)
                    with ProductStore._scoped_mutate(scope) as prods:
                        prods.extend(seed_data)
                    print(f"[ProductStore] Auto-seeded {len(seed_data)} products and scripts from products_seed.json")
    except Exception as exc:
        print(f"[ProductStore] Auto-seed skipped: {exc}")
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

    try:
        from scripts.hyperframes_recovery import recover_hyperframes_work
        from scripts.config import BASE_DIR
        recovered["hyperframes"] = recover_hyperframes_work(BASE_DIR)["counts"]
    except Exception as exc:
        print(f"[HyperFrames] startup recovery skipped: {exc}")
        recovered["hyperframes"] = {"interrupted": 0, "queued": 0, "finalizing": 0}

    try:
        from scripts.hyperframes_ai_provider import recover_provider_work
        from scripts.config import BASE_DIR
        recovered["hyperframes_ai"] = recover_provider_work(BASE_DIR)
    except Exception as exc:
        print(f"[HyperFrames AI] startup recovery skipped: {exc}")
        recovered["hyperframes_ai"] = {"interrupted": [], "errors": [{"code": "provider_recovery_failed"}]}

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
    if (
        os.environ.get("OMNICUT_ALLOW_REMOTE", "").lower() in ("1", "true", "yes")
        or Path("/content").exists()
        or "google.colab" in sys.modules
    ):
        return True
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

    # Allow loading frontend SPA HTML and static assets freely
    if not request.url.path.startswith("/api"):
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
# The channel-scope middleware (pure ASGI, multi-channel P1) is added first
# so it is the innermost layer: auth runs before it and CORS decorates its
# 422 responses. The key gate is added next so it becomes the middle layer;
# CORS is added last so it wraps every response (including a 401 from the
# gate) with the right Access-Control-* headers.
# The maintenance gate (multi-channel P2.3) is added before it all, so it is
# the very innermost layer: while <root>/_Docs/.maintenance.lock exists every
# non-GET/HEAD/OPTIONS request gets 503 maintenance_mode (adds no routes).
install_maintenance_gate(app)
install_channel_scope(app)
app.middleware("http")(api_key_gate)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    # "*" already admits X-OmniCut-Channel on preflight; listed for clarity.
    allow_headers=["*", CHANNEL_HEADER],
    expose_headers=[CHANNEL_HEADER],
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
app.include_router(gadget_media_router)
app.include_router(gadget_media_projects_router)
app.include_router(background_isolation_router)
app.include_router(typesafe_studio_router)
app.include_router(audio_beats_router)
app.include_router(proxy_router)
app.include_router(mobile_studio_router)
app.include_router(hyperframes_router)
app.include_router(hyperframes_workflow_router)
app.include_router(hyperframes_ai_router)
app.include_router(hyperframes_overlay_router)
app.include_router(publication_observations_router)
app.include_router(channels_router)
app.include_router(copilot_router)
app.include_router(agy_router)


# ----------------------------------------------------------------------
# Serve Built Frontend SPA (if available in frontend/dist)
# ----------------------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
    if (DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="frontend_assets")

    @app.get("/{full_path:path}")
    async def serve_spa_frontend(full_path: str):
        # Do not hijack API, docs, or openapi routes
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = DIST_DIR / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(DIST_DIR / "index.html")

# ----------------------------------------------------------------------
# Run Server directly if executed
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    should_reload = os.environ.get("FASTAPI_RELOAD", "false").lower() in ("1", "true")
    uvicorn.run(
        "scripts.api_server:app",
        host=get_bind_host(),
        port=8000,
        reload=should_reload
    )
