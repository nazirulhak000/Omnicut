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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, EXPORTS_DIR, ASSETS_DIR,
    FONTS_DIR, SFX_DIR, MUSIC_DIR, STICKERS_DIR, PROJECTS_DIR,
    CAPCUT_DRAFT_DIR, VOICES, DEFAULT_VOICE, DEFAULT_VOICE_RATE
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

# Enable CORS for React Frontend (Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
