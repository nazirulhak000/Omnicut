"""
FastAPI Backend Server for OmniCut Pro Studio AI & CapCut Pipeline
Provides REST APIs, video/audio streaming with byte-range support, and SSE progress updates.
"""

import os
import sys
import glob
import time
import uuid
import json
import shutil
import asyncio
import datetime
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scripts.config import (
    BASE_DIR, INBOX_DIR, RAW_DIR, EXPORTS_DIR, ASSETS_DIR,
    FONTS_DIR, SFX_DIR, MUSIC_DIR, STICKERS_DIR, PROJECTS_DIR,
    CAPCUT_DRAFT_DIR, VOICES, DEFAULT_VOICE, DEFAULT_VOICE_RATE
)
from scripts.script_generator import ScriptGenerator
from scripts.pipeline import TikTokAutoCutterPipeline
from scripts.voice_engine import VoiceEngine
from scripts.gemini_tts_engine import GeminiFlashTTSEngine
from scripts.tts_sanitizer import TTSSanitizer
from scripts.product_scraper import ProductScraper
from scripts.product_store import ProductStore
from scripts.post_log import PostLog

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

# Shared with the phase-1 router so full renders and partial re-rolls are
# tracked in one place and answered by the same status endpoint.
from scripts import render_jobs
from scripts.render_jobs import ACTIVE_JOBS
from scripts.asset_registry import AssetRegistry
from scripts.it_angles import DEFAULT_BGM
from scripts.task_manager import TaskManager
from scripts.post_log import PostLog
from scripts.api_phase1 import router as phase1_router
from scripts.api_editor import router as editor_router
from scripts.api_tokens import router as tokens_router

app.include_router(phase1_router)
app.include_router(editor_router)
app.include_router(tokens_router)

# ----------------------------------------------------------------------
# Data Models
# ----------------------------------------------------------------------
class ScriptGenerateRequest(BaseModel):
    product_name: str
    key_features: str = "แม่เหล็กแรงดูดสูง เสียบง่าย ชาร์จเร็ว ไม่ทำร้ายแบต"
    pain_point: str = "สายชาร์จพังง่าย เสียบยากในที่มืด"
    price_deal: str = "ลดพิเศษวันนี้"
    template_key: str = "problem_solution"

class VoicePreviewRequest(BaseModel):
    text: str
    voice_gender: str = "female"
    speed: float = 1.20
    ad_tone: Optional[str] = "commercial_premium"

class RenderRequest(BaseModel):
    product_name: str
    raw_video_path: str
    project_name: Optional[str] = None
    key_features: str
    pain_point: str
    price_deal: str
    # 3-tier hook banner: brand (largest) / model (mid) / label (smallest,
    # e.g. "หูฟังไร้สาย") -- replaces the old single hook_title free-text
    # sentence, which was really the voiceover's opening line getting
    # mis-used as a banner caption.
    hook_brand: Optional[str] = None
    hook_model: Optional[str] = None
    hook_label: Optional[str] = None
    # 4 independently toggleable hook-banner motion effects (bounce, stagger,
    # pulse, underline). Missing keys / None default to True inside
    # subtitle_engine's _resolve_hook_motion -- omitting this field entirely
    # keeps the full default preset, it does not turn motion off.
    hook_motion: Optional[Dict[str, Any]] = None
    # per-tier text colours: {brand, model, label} as #RRGGBB
    hook_colors: Optional[Dict[str, str]] = None
    hook_style: Optional[Dict[str, Any]] = None
    custom_script: Optional[str] = None
    script_overlays: Optional[List[str]] = None  # per-line spec-bar text, index-aligned with custom_script
    voice_mode: str = "gemini_tts" # gemini_tts, edge_tts, human, video
    voice_gender: str = "female"
    voice_rate: str = "+15%"
    voice_preset: Optional[str] = "gemini_puck_male_hype"  # Gemini prebuilt voice, e.g. gemini_puck_male_hype
    ad_tone: Optional[str] = "commercial_premium"
    human_voice_audio: Optional[str] = None
    # Where this clip came from in the product flow. Recorded so deleting the
    # project can offer to take its script with it without guessing.
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    font_name: str = "IBMPlex"
    bilingual_subtitles: bool = True
    use_ai_vision: bool = True
    sticker_badge: Optional[str] = "badge_flash_sale_3d.png"
    bgm_name: Optional[str] = None  # BGM filename from AssetRegistry.bgm(); None keeps SFXManager's own default
    bgm_volume: Optional[float] = None
    bgm_ducking: bool = False
    lut_name: Optional[str] = None  # LUT filename from AssetRegistry.luts(); None auto-picks by IT angle, or no grade
    clip_list: Optional[List[Dict[str, Any]]] = None  # Manual Editor: [{source_path, trim_start, trim_end}]; None keeps single-source auto-cut
    # Per boundary between clip_list entries. Two accepted shapes: the legacy
    # bare string ("cut" | "fade" | ...) and the Editor's {type, duration}
    # dict, which is what EditorShell actually sends now. Typed List[str]
    # before, which rejected the dict form outright -- /api/reroll has always
    # declared List[Any], so the two endpoints disagreed on the same field.
    transitions: Optional[List[Any]] = None
    export_mp4: bool = True
    caption_position: Optional[str] = "bottom"
    caption_color: Optional[str] = None
    caption_scale: Optional[float] = 1.0
    sticker_position: Optional[str] = "top_right"
    sticker_scale: Optional[float] = 1.0
    text_overlays: Optional[List[Dict[str, Any]]] = None

class DeleteFileRequest(BaseModel):
    file_path: str

class AddPostRequest(BaseModel):
    product_name: str
    clip_file: str
    platform: str = "tiktok"
    product_url: Optional[str] = ""
    angle_key: Optional[str] = ""
    angle_title: Optional[str] = ""
    hook: Optional[str] = ""
    caption: Optional[str] = ""
    hashtags: Optional[List[str]] = None
    posted_at: Optional[str] = None

class UpdatePostMetricsRequest(BaseModel):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    cart_clicks: Optional[int] = None
    orders: Optional[int] = None
    commission_thb: Optional[float] = None

class OpenFolderRequest(BaseModel):
    target: str # "exports", "inbox", "raw", "assets", "capcut", "root", or custom path

class TranscribeRequest(BaseModel):
    media_path: str
    lang: Optional[str] = "th" # "th", "en", "zh", None for auto
    mode: str = "bilingual" # "bilingual", "mono", "dual"
    words_per_line: int = 5
    fast: bool = True

# ----------------------------------------------------------------------
# Helper Utilities
# ----------------------------------------------------------------------
def measure_wav_duration(wav_path: Path) -> float:
    """Seconds of audio in a WAV file, 0.0 if it cannot be read."""
    try:
        import wave
        with wave.open(str(wav_path), "rb") as wf:
            return round(wf.getnframes() / float(wf.getframerate()), 2)
    except Exception:
        return 0.0


def get_file_info(file_path: Path) -> Dict[str, Any]:
    stat = file_path.stat()
    rel_path = str(file_path.relative_to(BASE_DIR)).replace("\\", "/")
    webp_path = file_path.with_suffix(".webp")
    thumbnail_url = None
    if webp_path.exists():
        try:
            thumbnail_url = f"/api/media/{str(webp_path.relative_to(BASE_DIR)).replace('\\', '/')}"
        except Exception:
            thumbnail_url = None

    return {
        "name": file_path.name,
        "path": str(file_path),
        "rel_path": rel_path,
        "thumbnail_url": thumbnail_url,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": stat.st_mtime
    }

# (DeleteFileRequest defined above near line 124 — no duplicate needed)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".hevc", ".mkv"}

def scan_video_files(*dirs: Path) -> List[Path]:
    """Fast single-pass filesystem scanner for video files across given directories."""
    found = []
    seen = set()
    for d in dirs:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
                resolved = p.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    found.append(p)
    return found

# Range-supporting file streamer for smooth HTML5 video/audio playback
def stream_media_file(file_path: Path, request: Request):
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    content_type = "video/mp4"
    ext = file_path.suffix.lower()
    if ext in [".mov"]:
        content_type = "video/quicktime"
    elif ext in [".mp3"]:
        content_type = "audio/mpeg"
    elif ext in [".wav"]:
        content_type = "audio/wav"
    elif ext in [".jpg", ".jpeg"]:
        content_type = "image/jpeg"
    elif ext in [".png"]:
        content_type = "image/png"
    elif ext in [".webp"]:
        content_type = "image/webp"
    elif ext in [".ttf"]:
        content_type = "font/ttf"
    elif ext in [".otf"]:
        content_type = "font/otf"

    STREAM_CHUNK_SIZE = 256 * 1024  # 256KB high-throughput buffer

    # A StreamingResponse holds its file handle open for as long as the client
    # keeps the connection, and an <audio> element parked on a project keeps
    # one open for as long as the Editor tab is. On Windows that handle blocks
    # deleting the project -- the server ends up refusing its own delete with
    # WinError 32 on mixed_audio.wav. Project audio is only a few MB, so it is
    # read into memory and the handle is closed before the response is even
    # returned. Big exports stay streamed; nothing deletes those from here.
    INLINE_MAX_BYTES = 32 * 1024 * 1024

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        end = min(end, file_size - 1)
        chunk_size = (end - start) + 1

        if file_size <= INLINE_MAX_BYTES:
            with open(file_path, "rb") as f:
                f.seek(start)
                payload = f.read(chunk_size)
            return Response(
                content=payload,
                status_code=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(payload)),
                    "Content-Type": content_type,
                },
            )

        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = chunk_size
                while bytes_left > 0:
                    read_len = min(STREAM_CHUNK_SIZE, bytes_left)
                    data = f.read(read_len)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(iterfile(), status_code=206, headers=headers)
    else:
        if file_size <= INLINE_MAX_BYTES:
            return Response(
                content=file_path.read_bytes(),
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(file_size),
                    "Content-Type": content_type,
                },
            )

        def iterfile():
            with open(file_path, "rb") as f:
                while chunk := f.read(STREAM_CHUNK_SIZE):
                    yield chunk

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(iterfile(), headers=headers)

import socket as _socket

_ip_cache: Dict[str, Any] = {"ip": None, "ts": 0.0}
_IP_TTL = 5.0  # re-check every 5 s so Wi-Fi switches are reflected almost immediately

def get_local_ip(force: bool = False) -> str:
    """Returns the primary local IPv4 address. Re-checked every 5 s (or forced) so
    switching Wi-Fi networks is reflected dynamically without restarting the server."""
    now = time.monotonic()
    if force or _ip_cache["ip"] is None or (now - _ip_cache["ts"]) > _IP_TTL:
        ip = "127.0.0.1"
        try:
            s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            s.settimeout(0.3)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                ip = _socket.gethostbyname(_socket.gethostname())
            except Exception:
                pass
        _ip_cache["ip"] = ip
        _ip_cache["ts"] = now
    return _ip_cache["ip"]

# ----------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------

@app.get("/api/status")
def get_system_status(refresh_ip: bool = False):
    """Returns general health and system stats with fast single-pass scanning."""
    raw_files = scan_video_files(RAW_DIR, INBOX_DIR)
    export_files = list(EXPORTS_DIR.glob("*.mp4"))
    local_ip = get_local_ip(force=refresh_ip)

    return {
        "status": "online",
        "ffmpeg_ready": True,
        "capcut_draft_path": str(CAPCUT_DRAFT_DIR),
        "capcut_synced": CAPCUT_DRAFT_DIR.exists(),
        "total_raw_videos": len(raw_files),
        "total_exports": len(export_files),
        "local_ip": local_ip,
        "mobile_url": f"http://{local_ip}:5173",
        "directories": {
            "base": str(BASE_DIR),
            "inbox": str(INBOX_DIR),
            "raw": str(RAW_DIR),
            "exports": str(EXPORTS_DIR),
            "assets": str(ASSETS_DIR),
            "capcut": str(CAPCUT_DRAFT_DIR)
        }
    }

@app.get("/api/videos")
def list_raw_videos(product_id: Optional[str] = None):
    """Lists all available raw video candidates with fast single-pass scanning."""
    candidates = scan_video_files(RAW_DIR, INBOX_DIR)
    unique_paths = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    all_videos = [get_file_info(p) for p in unique_paths]

    product_videos = []
    if product_id:
        try:
            prod_assigned = ProductStore.get_product_videos(product_id)
            assigned_paths = {v.get("path") or v.get("rel_path") for v in prod_assigned}

            prod_dir = RAW_DIR / product_id
            prod_dir_paths = {p.resolve() for p in scan_video_files(prod_dir)} if prod_dir.exists() else set()

            for v in all_videos:
                v_path = Path(v["path"]).resolve()
                if v["path"] in assigned_paths or v["rel_path"] in assigned_paths or v_path in prod_dir_paths:
                    product_videos.append(v)
        except Exception as e:
            print(f"Error fetching product videos: {e}")
            product_videos = []

    return {
        "videos": all_videos,
        "product_videos": product_videos if product_id else all_videos,
        "product_id": product_id,
        "total_count": len(all_videos),
        "product_count": len(product_videos) if product_id else len(all_videos)
    }


class RenameVideoPayload(BaseModel):
    video_path: str
    new_name: str
    product_id: Optional[str] = None

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    target_dir: str = Form("inbox"),
    product_id: Optional[str] = Form(None),
    custom_name: Optional[str] = Form(None)
):
    """Uploads a video or audio file to 00_Inbox or 01_Raw, and links to product if product_id is provided."""
    dest_dir = INBOX_DIR if target_dir == "inbox" else RAW_DIR
    if product_id:
        dest_dir = RAW_DIR / product_id
        dest_dir.mkdir(parents=True, exist_ok=True)

    orig_filename = Path(file.filename or f"iphone_video_{int(time.time())}.mp4").name
    orig_suffix = Path(orig_filename).suffix or ".mp4"

    if custom_name and custom_name.strip():
        # Clean custom name (allow Thai, English, digits, dashes, underscores, spaces)
        clean_custom = "".join(c for c in custom_name.strip() if c.isalnum() or c in "._- \u0E00-\u0E7F").strip()
        if clean_custom:
            safe_filename = f"{clean_custom}{orig_suffix}"
        else:
            safe_filename = f"video_{int(time.time())}{orig_suffix}"
    else:
        # Keep Thai letters, English letters, digits, dots, dashes, underscores
        safe_filename = "".join(c for c in orig_filename if c.isalnum() or c in "._- \u0E00-\u0E7F")
        if not safe_filename:
            safe_filename = f"video_{int(time.time())}{orig_suffix}"

    save_path = dest_dir / safe_filename
    if save_path.exists():
        stem = Path(safe_filename).stem
        save_path = dest_dir / f"{stem}_{int(time.time())}{orig_suffix}"

    with open(save_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    # Auto-convert iPhone HEIC/HEIF images to standard JPEG for universal browser compatibility
    if orig_suffix.lower() in [".heic", ".heif"]:
        jpg_save_path = save_path.with_suffix(".jpg")
        try:
            conv_cmd = ["ffmpeg", "-y", "-i", str(save_path), "-q:v", "2", str(jpg_save_path)]
            subprocess.run(conv_cmd, check=True, capture_output=True)
            if jpg_save_path.exists():
                try:
                    save_path.unlink()
                except Exception:
                    pass
                save_path = jpg_save_path
        except Exception as conv_err:
            print(f"Warning: HEIC conversion failed: {conv_err}")

    file_info = get_file_info(save_path)

    # Automatically attach to product if product_id given
    if product_id:
        try:
            ProductStore.add_video_to_product(product_id, file_info)
        except Exception as e:
            print(f"Warning: Failed to attach video to product {product_id}: {e}")

    return {
        "message": "Upload successful",
        "file": file_info
    }

@app.post("/api/videos/rename")
def rename_video_file(payload: RenameVideoPayload):
    """Safely renames a video file on disk and updates any ProductStore references."""
    video_path = payload.video_path
    new_name = payload.new_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="กรุณาระบุชื่อคลิปใหม่")

    cleaned_path = video_path.replace("\\", "/").lstrip("/")
    v_path = Path(cleaned_path)
    if not v_path.is_absolute():
        v_path = (BASE_DIR / cleaned_path).resolve()

    if not v_path.exists() or not v_path.is_file():
        # Try in RAW_DIR directly
        raw_check = (RAW_DIR / cleaned_path).resolve()
        if raw_check.exists() and raw_check.is_file():
            v_path = raw_check
        else:
            raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์คลิปต้นฉบับ: {Path(video_path).name}")

    # Security check: must be inside BASE_DIR
    try:
        v_path.relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เปลี่ยนชื่อไฟล์ภายนอกโปรเจกต์")

    orig_suffix = v_path.suffix
    clean_new_name = "".join(c for c in new_name if c.isalnum() or c in "._- \u0E00-\u0E7F").strip()
    if not clean_new_name:
        raise HTTPException(status_code=400, detail="ชื่อใหม่มีตัวอักษรที่ไม่ถูกต้อง")

    # Ensure extension is preserved
    if not clean_new_name.lower().endswith(orig_suffix.lower()):
        clean_new_name = f"{clean_new_name}{orig_suffix}"

    target_path = v_path.parent / clean_new_name
    if target_path.exists() and target_path.resolve() != v_path.resolve():
        target_path = v_path.parent / f"{target_path.stem}_{int(time.time())}{orig_suffix}"

    try:
        v_path.rename(target_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เปลี่ยนชื่อไฟล์บนดิสก์ไม่สำเร็จ: {e}")

    new_file_info = get_file_info(target_path)

    # Update ProductStore if referenced
    try:
        products = ProductStore._load()
        updated_any = False
        old_rel = str(v_path.relative_to(BASE_DIR)).replace("\\", "/")
        old_abs = str(v_path)
        for p in products:
            if payload.product_id and p.get("id") != payload.product_id:
                continue
            v_list = p.get("videos", [])
            for v in v_list:
                if v.get("path") == old_abs or v.get("rel_path") == old_rel or v.get("name") == v_path.name:
                    v["path"] = new_file_info["path"]
                    v["rel_path"] = new_file_info["rel_path"]
                    v["name"] = new_file_info["name"]
                    updated_any = True
        if updated_any:
            ProductStore._save(products)
    except Exception as e:
        print(f"Notice: Failed to update ProductStore on rename: {e}")

    return {
        "success": True,
        "message": f"เปลี่ยนชื่อเป็น {target_path.name} เรียบร้อยแล้ว",
        "file": new_file_info
    }

@app.post("/api/products/{product_id}/videos")
def attach_video_to_product(product_id: str, payload: Dict[str, Any]):
    """Links an existing video file to a product."""
    video_path = payload.get("video_path")
    if not video_path:
        raise HTTPException(status_code=400, detail="Missing video_path")

    v_path = Path(video_path)
    if not v_path.is_absolute():
        v_path = BASE_DIR / video_path

    if not v_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    file_info = get_file_info(v_path)
    updated = ProductStore.add_video_to_product(product_id, file_info)
    return {"success": True, "product": updated}

@app.delete("/api/products/{product_id}/videos")
def remove_video_from_product(product_id: str, video_path: str):
    """Unlinks a video file from a product. If the file was inside RAW_DIR/product_id, moves it to RAW_DIR root so it becomes general."""
    v_path = Path(video_path)
    if not v_path.is_absolute():
        v_path = BASE_DIR / video_path

    prod_dir = (RAW_DIR / product_id).resolve()
    if v_path.exists():
        try:
            if v_path.resolve().is_relative_to(prod_dir):
                target_path = RAW_DIR / v_path.name
                if target_path.exists():
                    target_path = RAW_DIR / f"{v_path.stem}_{int(time.time())}{v_path.suffix}"
                shutil.move(str(v_path), str(target_path))
        except Exception as e:
            print(f"Notice: Failed to move unlinked video: {e}")

    updated = ProductStore.remove_video_from_product(product_id, video_path)
    return {"success": True, "product": updated}

# ----------------------------------------------------------------------
# Raw Footage Vault API (Comprehensive Raw Video Hub)
# ----------------------------------------------------------------------

class ReassignVideoPayload(BaseModel):
    video_path: str
    target_product_id: Optional[str] = None
    source_product_id: Optional[str] = None

class BatchDeleteVideosPayload(BaseModel):
    video_paths: List[str]

@app.get("/api/raw-vault")
def get_raw_vault():
    """Returns rich metadata of all raw footage grouped by products and unassigned clips."""
    products = ProductStore._load()

    # 1. Collect all video files in RAW_DIR and INBOX_DIR (Fast single-pass)
    raw_file_paths = scan_video_files(RAW_DIR, INBOX_DIR)
    all_raw_files = [get_file_info(p) for p in raw_file_paths]

    # 2. Build product groups
    product_groups = []
    assigned_file_paths = set()

    for p in products:
        pid = p["id"]
        p_title = p.get("title", pid)
        p_cover = p.get("image_url") or p.get("cover_image") or None
        prod_dir = (RAW_DIR / pid).resolve()

        prod_videos = []
        assigned_in_store = {v.get("path") for v in p.get("videos", []) if v.get("path")}
        assigned_rel_in_store = {v.get("rel_path") for v in p.get("videos", []) if v.get("rel_path")}

        for v in all_raw_files:
            v_abs = Path(v["path"]).resolve()
            is_in_dir = False
            try:
                is_in_dir = v_abs.is_relative_to(prod_dir)
            except Exception:
                pass

            if is_in_dir or v["path"] in assigned_in_store or v["rel_path"] in assigned_rel_in_store or v["rel_path"] in assigned_in_store:
                v_copy = dict(v)
                v_copy["product_id"] = pid
                v_copy["product_title"] = p_title
                prod_videos.append(v_copy)
                assigned_file_paths.add(v_abs)

        total_mb = sum(v.get("size_mb", 0) for v in prod_videos)
        product_groups.append({
            "product_id": pid,
            "product_title": p_title,
            "product_cover": p_cover,
            "category": p.get("category", "ทั่วไป"),
            "video_count": len(prod_videos),
            "total_size_mb": round(total_mb, 2),
            "videos": prod_videos
        })

    # 3. Collect unassigned / B-roll videos
    unassigned_videos = []
    for v in all_raw_files:
        v_abs = Path(v["path"]).resolve()
        if v_abs not in assigned_file_paths:
            v_copy = dict(v)
            v_copy["product_id"] = None
            v_copy["product_title"] = None
            unassigned_videos.append(v_copy)

    total_all_clips = len(all_raw_files)
    total_all_size_mb = round(sum(v.get("size_mb", 0) for v in all_raw_files), 2)

    return {
        "products": product_groups,
        "unassigned": unassigned_videos,
        "total_clips": total_all_clips,
        "total_size_mb": total_all_size_mb
    }

@app.post("/api/raw-vault/reassign")
def reassign_raw_video(payload: ReassignVideoPayload):
    """Reassigns or moves a raw video file to a new product, or unbinds it to general pool."""
    video_path = payload.video_path
    target_pid = payload.target_product_id
    source_pid = payload.source_product_id

    cleaned_path = video_path.replace("\\", "/").lstrip("/")
    v_path = Path(cleaned_path)
    if not v_path.is_absolute():
        v_path = (BASE_DIR / cleaned_path).resolve()

    if not v_path.exists():
        raw_check = (RAW_DIR / cleaned_path).resolve()
        if raw_check.exists():
            v_path = raw_check
        else:
            raise HTTPException(status_code=404, detail="ไม่พบไฟล์วิดีโอนี้")

    # Security check
    try:
        v_path.relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 1. If source_pid given, remove from source product
    if source_pid:
        try:
            ProductStore.remove_video_from_product(source_pid, str(v_path))
        except Exception as e:
            print(f"Notice on remove from source product: {e}")

    # 2. If target_pid given, move file into target product directory and attach
    if target_pid:
        target_dir = RAW_DIR / target_pid
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = target_dir / v_path.name
        if dest_path.resolve() != v_path.resolve():
            if dest_path.exists():
                dest_path = target_dir / f"{v_path.stem}_{int(time.time())}{v_path.suffix}"
            shutil.move(str(v_path), str(dest_path))
            v_path = dest_path

        file_info = get_file_info(v_path)
        ProductStore.add_video_to_product(target_pid, file_info)
        return {
            "success": True,
            "message": "ผูกคลิปเข้ากับสินค้าเรียบร้อยแล้ว",
            "file": file_info
        }
    else:
        # Move to general RAW_DIR root if it was inside a product folder
        if v_path.parent != RAW_DIR.resolve():
            dest_path = RAW_DIR / v_path.name
            if dest_path.exists():
                dest_path = RAW_DIR / f"{v_path.stem}_{int(time.time())}{v_path.suffix}"
            shutil.move(str(v_path), str(dest_path))
            v_path = dest_path

        file_info = get_file_info(v_path)
        return {
            "success": True,
            "message": "ปลดคลิปออกเป็นคลิปอิสระ (Unassigned) เรียบร้อยแล้ว",
            "file": file_info
        }

@app.post("/api/raw-vault/batch-delete")
def batch_delete_raw_videos(payload: BatchDeleteVideosPayload):
    """Deletes multiple video files safely from disk and removes references."""
    deleted_count = 0
    errors = []

    for v_str in payload.video_paths:
        try:
            cleaned_path = v_str.replace("\\", "/").lstrip("/")
            v_path = Path(cleaned_path)
            if not v_path.is_absolute():
                v_path = (BASE_DIR / cleaned_path).resolve()

            if not v_path.exists():
                raw_check = (RAW_DIR / cleaned_path).resolve()
                if raw_check.exists():
                    v_path = raw_check

            if v_path.exists() and v_path.is_file():
                v_path.resolve().relative_to(BASE_DIR.resolve()) # security check
                for attempt in range(3):
                    try:
                        v_path.unlink()
                        deleted_count += 1
                        break
                    except PermissionError:
                        if attempt < 2:
                            import gc
                            gc.collect()
                            time.sleep(0.2)
                        else:
                            raise

                # Clean from ProductStore
                products = ProductStore._load()
                updated_any = False
                for p in products:
                    v_list = p.get("videos", [])
                    new_v_list = [v for v in v_list if v.get("path") != str(v_path) and v.get("name") != v_path.name]
                    if len(new_v_list) != len(v_list):
                        p["videos"] = new_v_list
                        updated_any = True
                if updated_any:
                    ProductStore._save(products)
        except PermissionError:
            errors.append(f"{v_str}: ไฟล์กำลังถูกเปิดใช้งานหรือเล่นอยู่ กรุณาปิดโปรแกรมที่เปิดไฟล์ก่อน")
        except Exception as e:
            errors.append(f"{v_str}: {str(e)}")

    return {
        "success": True,
        "deleted_count": deleted_count,
        "errors": errors
    }

@app.post("/api/voice/preview")
def preview_voice(payload: Dict[str, Any]):
    """Generates a short voice preview for testing voice tone, speed, and TTS quality."""
    text = payload.get("text", "สวัสดีครับ นี่คือเสียงตัวอย่างสำหรับคลิปรีวิวสินค้าของคุณ")
    voice_gender = payload.get("voice_gender", "gemini_puck_male_hype")
    speed = float(payload.get("speed", 1.15))
    ad_tone = payload.get("ad_tone", "commercial_premium")

    clean_text = TTSSanitizer.clean(text)
    if not clean_text.strip():
        clean_text = "สวัสดีครับ ทดสอบเสียงพากย์รีวิวสินค้าครับ"

    voiceover_dir = ASSETS_DIR / "Voiceover" / "previews"
    voiceover_dir.mkdir(parents=True, exist_ok=True)
    out_file = voiceover_dir / f"preview_{int(time.time() * 1000)}.wav"

    try:
        audio_path = None
        if GeminiFlashTTSEngine.is_available():
            try:
                audio_path = GeminiFlashTTSEngine.generate_speech(
                    text=clean_text,
                    output_path=str(out_file),
                    voice_preset=voice_gender if "gemini_" in voice_gender else "gemini_puck_male_hype",
                    ad_tone=ad_tone,
                    speed=speed
                )
            except Exception as g_err:
                print(f"⚠️ [preview_voice] Gemini TTS failed ({g_err}) — fallback to Edge-TTS...")

        if not audio_path:
            gender = "female" if "female" in str(voice_gender).lower() or "Premwadee" in str(voice_gender) or "kore" in str(voice_gender).lower() or "aoede" in str(voice_gender).lower() else "male"
            res = VoiceEngine.generate_crystal_voice(
                text_or_lines=clean_text,
                output_audio_path=str(out_file),
                speed=speed,
                voice_gender=gender
            )
            audio_path = res["audio_path"]

        rel_path = str(Path(audio_path).relative_to(BASE_DIR)).replace("\\", "/")
        return {
            "success": True,
            "audio_url": f"/api/media/{rel_path}",
            "text": clean_text
        }
    except Exception as e:
        print(f"Error in preview_voice: {e}")
        raise HTTPException(status_code=500, detail=f"Voice preview failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Voice Cache Endpoints
# ─────────────────────────────────────────────────────────────────────────────
VOICE_CACHE_DIR = PROJECT_ROOT / "frontend" / "public" / "voice_cache"
VOICE_CACHE_MANIFEST = VOICE_CACHE_DIR / "manifest.json"

_VOICE_PRESETS_META = {
    "gemini_puck_male_hype":     {"voice": "Puck",   "label": "Puck — ชายพลังสูง TikTok",       "gender": "male"},
    "gemini_charon_male_pro":    {"voice": "Charon", "label": "Charon — ชายทุ้มลึก น่าเชื่อถือ","gender": "male"},
    "gemini_kore_female_bright": {"voice": "Kore",   "label": "Kore — หญิงสดใส ป้ายยาเก่ง",     "gender": "female"},
    "gemini_aoede_female_pro":   {"voice": "Aoede",  "label": "Aoede — หญิงพรีเมียม นุ่มนวล",   "gender": "female"},
    "gemini_fenrir_male_strong": {"voice": "Fenrir", "label": "Fenrir — ชายสตรอง คมเข้ม",        "gender": "male"},
}
_AD_TONES_META = {
    "commercial_premium":   "โฆษณาพรีเมียม",
    "commercial_hype":      "ป้ายยาไวรัล",
    "commercial_aesthetic": "มินิมอล ดูแพง",
    "commercial_expert":    "ผู้เชี่ยวชาญ",
}


@app.get("/api/voice/presets")
def get_voice_presets():
    """
    Returns the voice cache manifest (generated by scripts/generate_voice_cache.py).
    If the manifest is missing, returns an inline combo list with ready=False so the
    frontend can still render the picker and fall back to live TTS preview.
    """
    if VOICE_CACHE_MANIFEST.exists():
        try:
            return json.loads(VOICE_CACHE_MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            pass  # fall through to inline generation below

    # Manifest not yet created — return skeleton so UI can still render
    combos = []
    for voice_id, voice_cfg in _VOICE_PRESETS_META.items():
        for tone_id, tone_label in _AD_TONES_META.items():
            fname = f"{voice_id}__{tone_id}.wav"
            combos.append({
                "voice_id": voice_id,
                "tone_id": tone_id,
                "voice_label": voice_cfg["label"],
                "tone_label": tone_label,
                "voice_gender": voice_cfg["gender"],
                "filename": fname,
                "url": f"/voice_cache/{fname}",
                "ready": (VOICE_CACHE_DIR / fname).exists(),
            })
    return {
        "generated_at": None,
        "total": len(combos),
        "ready": sum(1 for c in combos if c["ready"]),
        "combos": combos,
    }


@app.get("/api/voice/cache-status")
def get_voice_cache_status():
    """Quick per-file readiness check (no manifest needed)."""
    result = {}
    for voice_id in _VOICE_PRESETS_META:
        for tone_id in _AD_TONES_META:
            fname = f"{voice_id}__{tone_id}.wav"
            result[fname] = (VOICE_CACHE_DIR / fname).exists()
    ready = sum(1 for v in result.values() if v)
    return {"ready": ready, "total": len(result), "files": result}


@app.post("/api/voice/generate-cache")
async def trigger_voice_cache_generation(background_tasks: BackgroundTasks, force: bool = False):
    """
    Kicks off cache generation in the background.
    Requires GEMINI_API_KEY to be set.
    """
    if not GeminiFlashTTSEngine.is_available():
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not set — cannot generate voice cache.")

    def _generate():
        import subprocess as sp
        cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_voice_cache.py")]
        if force:
            cmd.append("--force")
        sp.run(cmd, capture_output=False)

    background_tasks.add_task(_generate)
    return {"status": "started", "message": "Voice cache generation started in background."}


@app.get("/api/media/{file_path:path}")
def stream_media(file_path: str, request: Request):
    """Streams video or audio file by absolute or relative path."""
    import urllib.parse
    decoded_path = urllib.parse.unquote(file_path)
    target = Path(decoded_path)
    if not target.is_absolute():
        target = BASE_DIR / decoded_path

    target = target.resolve()
    # Security check: ensure target is within BASE_DIR or CAPCUT_DRAFT_DIR
    if not (str(target).startswith(str(BASE_DIR)) or str(target).startswith(str(CAPCUT_DRAFT_DIR))):
        raise HTTPException(status_code=403, detail="Access denied")

    return stream_media_file(target, request)

@app.get("/api/exports")
def list_exports():
    """Lists all rendered videos in 04_Exports/Ready_to_post enriched with product & script metadata.
    Distinguishes latest active export vs previous superseded versions vs external unlinked files.
    """
    files = sorted(list(EXPORTS_DIR.glob("*.mp4")), key=os.path.getmtime, reverse=True)
    all_products = ProductStore.get_all()

    # 1. Build lookup tables
    project_angle_map: Dict[str, tuple] = {}
    for p in all_products:
        for proj_name in p.get("projects", []):
            if proj_name:
                project_angle_map[proj_name.lower()] = (p, None)
        for a in p.get("angles", []):
            proj = a.get("project_name", "")
            if proj:
                project_angle_map[proj.lower()] = (p, a)
            vid_url = a.get("video_url", "")
            if vid_url:
                project_angle_map[Path(vid_url).stem.lower()] = (p, a)
                project_angle_map[Path(vid_url).name.lower()] = (p, a)

    # Check 03_Projects/ folders to get script_data if available
    project_disk_info: Dict[str, dict] = {}
    projects_dir = BASE_DIR / "03_Projects"
    if projects_dir.exists():
        for pdir in projects_dir.iterdir():
            if pdir.is_dir():
                pjson = pdir / "project.json"
                if pjson.exists():
                    try:
                        with open(pjson, "r", encoding="utf-8") as pf:
                            project_disk_info[pdir.name.lower()] = json.load(pf)
                    except Exception:
                        pass

    # Pass 1: Identify match for each file
    raw_matches = []
    for f in files:
        fname_low = f.name.lower()
        fstem_low = f.stem.lower()

        matched_prod = None
        matched_angle = None
        matched_proj_name = None

        # 1. Exact angle video_url match
        for p in all_products:
            for a in p.get("angles", []):
                vid_url = a.get("video_url", "")
                if vid_url:
                    vid_p = Path(vid_url)
                    if fname_low == vid_p.name.lower() or fstem_low == vid_p.stem.lower():
                        matched_prod, matched_angle = p, a
                        matched_proj_name = a.get("project_name")
                        break
            if matched_prod:
                break

        # 2. Exact project name match (stripping timestamp suffix like _YYYYMMDD_HHMMSS)
        if not matched_prod:
            import re
            base_proj_name = re.sub(r'_\d{8}_\d{6}(_draft)?$', '', fstem_low)
            if base_proj_name in project_angle_map:
                p, a = project_angle_map[base_proj_name]
                matched_prod = p
                matched_angle = a
                matched_proj_name = a.get("project_name") if a else base_proj_name
            elif fstem_low in project_angle_map:
                p, a = project_angle_map[fstem_low]
                matched_prod = p
                matched_angle = a
                matched_proj_name = a.get("project_name") if a else fstem_low

        # 2.5 Check project_disk_info if still not matched
        if not matched_proj_name:
            import re
            base_proj_name = re.sub(r'_\d{8}_\d{6}(_draft)?$', '', fstem_low)
            if base_proj_name in project_disk_info:
                matched_proj_name = base_proj_name
            elif fstem_low in project_disk_info:
                matched_proj_name = fstem_low

        # 3. Product ID match (exact token match)
        if not matched_prod:
            for p in all_products:
                pid = p.get("id", "").lower()
                if pid and (fstem_low == pid or fstem_low.startswith(f"{pid}_") or f"_{pid}_" in fstem_low):
                    matched_prod = p
                    break

        disk_proj = project_disk_info.get(matched_proj_name.lower()) if matched_proj_name else None

        raw_matches.append({
            "file": f,
            "product": matched_prod,
            "angle": matched_angle,
            "proj_name": matched_proj_name,
            "disk_proj": disk_proj
        })

    # Pass 2: Determine versioning per group
    latest_file_per_group: Dict[str, Any] = {}
    for item in raw_matches:
        p = item["product"]
        a = item["angle"]
        proj = item["proj_name"]
        group_key = None
        if p and a:
            group_key = f"{p.get('id')}:{a.get('angle_id')}"
        elif proj:
            group_key = f"proj:{proj}"
        elif p:
            group_key = f"prod:{p.get('id')}"

        if group_key and group_key not in latest_file_per_group:
            latest_file_per_group[group_key] = item["file"]

    results = []
    for item in raw_matches:
        f = item["file"]
        matched_prod = item["product"]
        matched_angle = item["angle"]
        matched_proj_name = item["proj_name"]
        disk_proj = item["disk_proj"]

        info = get_file_info(f)

        group_key = None
        if matched_prod and matched_angle:
            group_key = f"{matched_prod.get('id')}:{matched_angle.get('angle_id')}"
        elif matched_proj_name:
            group_key = f"proj:{matched_proj_name}"
        elif matched_prod:
            group_key = f"prod:{matched_prod.get('id')}"

        latest_f = latest_file_per_group.get(group_key) if group_key else None

        # Product metadata
        if matched_prod:
            info["product_id"] = matched_prod.get("id")
            info["product_name"] = matched_prod.get("name")
            info["price_deal"] = matched_prod.get("price_note")
            info["key_features"] = ", ".join(matched_prod.get("selling_points", []))

        # Script/Angle metadata
        if matched_angle:
            info["angle_id"] = matched_angle.get("angle_id")
            info["angle_name"] = matched_angle.get("angle_name")
            info["hook_title"] = matched_angle.get("hook_title")
            info["script_lines"] = matched_angle.get("script_lines")
            info["tiktok_caption"] = matched_angle.get("tiktok_caption")
            info["tiktok_hashtags"] = matched_angle.get("tiktok_hashtags")
            info["ad_tone"] = matched_angle.get("ad_tone")
            info["angle_status"] = matched_angle.get("status")
            info["qc_note"] = matched_angle.get("qc_note")
            info["project_name"] = matched_angle.get("project_name") or matched_proj_name
        elif disk_proj:
            s_data = disk_proj.get("script_data", {})
            info["hook_title"] = s_data.get("hook")
            info["script_lines"] = [l.get("text", "") if isinstance(l, dict) else str(l) for l in s_data.get("lines", [])]
            info["project_name"] = disk_proj.get("project_name") or matched_proj_name

        # Determine version status
        # An export is linked to a script only if it has an angle or a project.json script
        has_script = bool(matched_angle or (disk_proj and disk_proj.get("script_data", {}).get("hook")))

        if has_script:
            info["is_unlinked"] = False
            # Only the single newest file in the group is 'latest'; earlier ones are 'previous_version'
            if latest_f and latest_f == f:
                info["is_latest"] = True
                info["is_previous_version"] = False
            else:
                info["is_latest"] = False
                info["is_previous_version"] = True
                if latest_f:
                    info["latest_video_name"] = latest_f.name
                    info["latest_video_path"] = str(latest_f)
                    info["latest_video_rel"] = f"04_Exports/Ready_to_post/{latest_f.name}"

            # Only mark as QC rejected if THIS SPECIFIC file is the one associated with the QC rejection,
            # NOT all historic/other versions of the same angle!
            angle_vid = (matched_angle.get("video_url") or "").lower() if matched_angle else ""
            angle_qc_note = matched_angle.get("qc_note") if matched_angle else None
            is_this_file_rejected = False
            if angle_qc_note and angle_vid:
                is_this_file_rejected = (fname_low in angle_vid or str(f).lower() in angle_vid or Path(angle_vid).name.lower() == fname_low)
            elif angle_qc_note and matched_angle:
                # If no video_url recorded on angle, only latest_f could possibly be the rejected one
                is_this_file_rejected = (latest_f and latest_f == f)

            info["is_qc_rejected"] = is_this_file_rejected
            if not is_this_file_rejected:
                info["qc_note"] = None
        else:
            info["is_unlinked"] = True
            info["is_latest"] = False
            info["is_previous_version"] = False
            info["is_qc_rejected"] = False

        results.append(info)

    return {"exports": results}

class LinkAngleRequest(BaseModel):
    video_path: str
    product_id: str
    angle_id: str

@app.post("/api/exports/link-angle")
def link_export_to_angle(req: LinkAngleRequest):
    """Links an exported video to a product angle."""
    try:
        updated = ProductStore.update_angle_status(
            product_id=req.product_id,
            angle_id=req.angle_id,
            status="rendered",
            video_url=req.video_path
        )
        return {"status": "success", "product": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/script/generate")
def generate_script(req: ScriptGenerateRequest):
    """Generates structured high-converting TikTok product review script."""
    data = ScriptGenerator.generate(
        product_name=req.product_name,
        key_features=req.key_features,
        pain_point=req.pain_point,
        price_deal=req.price_deal,
        template_key=req.template_key
    )
    return data

@app.post("/api/products/scrape-and-plan")
def scrape_and_plan(payload: Dict[str, Any]):
    """Scrapes product info or accepts raw text/keywords/images and generates Content Matrix."""
    url = payload.get("url", "").strip()
    raw_text = payload.get("raw_text", "").strip()
    custom_keyword = payload.get("custom_keyword", "").strip()
    image_path = payload.get("image_path", "").strip()

    if not url and not raw_text and not custom_keyword and not image_path:
        raise HTTPException(status_code=400, detail="กรุณาระบุลิงก์ ข้อความรายละเอียด หรือรูปภาพสินค้า")

    try:
        if url:
            product_info = ProductScraper.scrape_url(url)
        else:
            product_info = {
                "platform": "manual",
                "url": "",
                "title": custom_keyword or "สินค้า",
                "description": raw_text or custom_keyword,
                "price_note": "ราคาพิเศษในตะกร้า",
                "raw_text": raw_text or custom_keyword,
                "images": [],
                "image_count": 0
            }

        if image_path:
            img_p = Path(image_path)
            img_name = img_p.name
            img_rel = str(img_p.relative_to(BASE_DIR)).replace("\\", "/") if BASE_DIR in img_p.parents else img_name
            product_info["images"] = [{"name": img_name, "rel_path": img_rel, "local_path": str(img_p)}]
            product_info["image_count"] = 1
            product_info["thumbnail"] = img_rel
            if not custom_keyword and not raw_text:
                clean_title = img_p.stem.replace("_", " ").replace("-", " ")
                product_info["title"] = clean_title or "สินค้า"
                product_info["description"] = f"สินค้าจากภาพ {img_name}"

        if custom_keyword:
            product_info["title"] = custom_keyword
        if raw_text and len(raw_text) > 10:
            product_info["description"] = raw_text
            product_info["raw_text"] = f"{product_info.get('title', '')}\n{raw_text}"

        angle_count = int(payload.get("angle_count", 10))
        angles = ProductScraper.generate_content_matrix(product_info, count=angle_count)

        # Save to permanent ProductStore History
        thumbnail_img = ""
        if product_info.get("images") and len(product_info["images"]) > 0:
            thumbnail_img = product_info["images"][0].get("rel_path", "")

        saved_prod = ProductStore.add(
            name=product_info.get("title", "สินค้า"),
            url=product_info.get("url", ""),
            platform=product_info.get("platform", ""),
            category="IT / Gadget",
            price_note=product_info.get("price_note", ""),
            thumbnail=thumbnail_img,
            angles=angles,
            images=product_info.get("images", [])
        )
        product_info["id"] = saved_prod["id"]

        return {
            "success": True,
            "product": product_info,
            "saved_product": saved_prod,
            "angles": angles
        }
    except Exception as e:
        print(f"[API] Scrape and plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _execute_scrape_and_plan_worker(task_id: str, payload: Dict[str, Any]):
    """Background worker that executes product scrape & 10-angle script generation with step-by-step progress."""
    try:
        TaskManager.update_progress(task_id, 0.15, "กำลังดึงข้อมูลและสเปกสินค้า")
        url = payload.get("url", "").strip()
        raw_text = payload.get("raw_text", "").strip()
        custom_keyword = payload.get("custom_keyword", "").strip()
        image_path = payload.get("image_path", "").strip()
        angle_count = int(payload.get("angle_count", 7))

        if url:
            TaskManager.update_progress(task_id, 0.30, f"กำลังดึงข้อมูลจากร้านค้า: {url[:35]}")
            product_info = ProductScraper.scrape_url(url)
        else:
            product_info = {
                "platform": "manual",
                "url": "",
                "title": custom_keyword or "สินค้า",
                "description": raw_text or custom_keyword,
                "price_note": "ราคาพิเศษในตะกร้า",
                "raw_text": raw_text or custom_keyword,
                "images": [],
                "image_count": 0
            }

        if image_path:
            img_p = Path(image_path)
            img_name = img_p.name
            img_rel = str(img_p.relative_to(BASE_DIR)).replace("\\", "/") if BASE_DIR in img_p.parents else img_name
            product_info["images"] = [{"name": img_name, "rel_path": img_rel, "local_path": str(img_p)}]
            product_info["image_count"] = 1
            product_info["thumbnail"] = img_rel
            if not custom_keyword and not raw_text:
                clean_title = img_p.stem.replace("_", " ").replace("-", " ")
                product_info["title"] = clean_title or "สินค้า"
                product_info["description"] = f"สินค้าจากภาพ {img_name}"

        if custom_keyword:
            product_info["title"] = custom_keyword
        if raw_text and len(raw_text) > 10:
            product_info["description"] = raw_text
            product_info["raw_text"] = f"{product_info.get('title', '')}\n{raw_text}"

        title_display = product_info.get("title", custom_keyword or "สินค้า")
        if len(title_display) > 35:
            title_display = title_display[:35]

        TaskManager.update_progress(task_id, 0.55, f"AI กำลังแต่ง {angle_count} สคริปต์ ({title_display})")

        angles = ProductScraper.generate_content_matrix(product_info, count=angle_count)

        TaskManager.update_progress(task_id, 0.85, "กำลังปรับแต่งบทพูดสำหรับเสียงพากย์ AI (TTS Sanitizer)")
        from scripts.tts_sanitizer import TTSSanitizer
        angles = TTSSanitizer.process_angles(angles)

        TaskManager.update_progress(task_id, 0.95, "กำลังบันทึกลงแคตตาล็อกสินค้า")

        thumbnail_img = ""
        if product_info.get("images") and len(product_info["images"]) > 0:
            thumbnail_img = product_info["images"][0].get("rel_path", "")

        saved_prod = ProductStore.add(
            name=product_info.get("title", "สินค้า"),
            url=product_info.get("url", ""),
            platform=product_info.get("platform", ""),
            category="IT / Gadget",
            price_note=product_info.get("price_note", ""),
            thumbnail=thumbnail_img,
            angles=angles,
            images=product_info.get("images", [])
        )
        product_info["id"] = saved_prod["id"]

        result_data = {
            "product": product_info,
            "saved_product": saved_prod,
            "angles": angles
        }

        TaskManager.complete_task(
            task_id,
            result=result_data,
            step_label=f"🎉 สำเร็จ! สร้าง {len(angles)} สคริปต์เรียบร้อย",
            target_id=saved_prod["id"]
        )
        print(f"✅ [TaskManager] Scrape task completed: {task_id} ({saved_prod['id']})")

    except Exception as e:
        print(f"❌ [TaskManager] Scrape task failed ({task_id}): {e}")
        TaskManager.fail_task(task_id, str(e), step_label="วิเคราะห์สินค้าไม่สำเร็จ")

@app.post("/api/products/scrape-and-plan-async")
def scrape_and_plan_async(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """Launches Scrape & Plan as a persistent background task, returning job ID immediately."""
    url = payload.get("url", "").strip()
    raw_text = payload.get("raw_text", "").strip()
    custom_keyword = payload.get("custom_keyword", "").strip()
    angle_count = int(payload.get("angle_count", 7))

    if not url and not raw_text and not custom_keyword:
        raise HTTPException(status_code=400, detail="กรุณาระบุลิงก์ ข้อความรายละเอียด หรือชื่อสินค้า")

    name_label = custom_keyword or (f"ลิงก์: {url[:30]}" if url else "สินค้าใหม่")
    task_title = f"วิเคราะห์สินค้า: {name_label} ({angle_count} สคริปต์)"

    task = TaskManager.create_task(
        task_type="scrape_and_plan",
        title=task_title,
        payload=payload,
        target_tab="flow"
    )

    background_tasks.add_task(_execute_scrape_and_plan_worker, task["id"], payload)

    return {
        "success": True,
        "task_id": task["id"],
        "task": task
    }

# ═══════════════════════════════════════════════════════════════════════
# 📋 GLOBAL TASK & ACTIVITY MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════
@app.get("/api/tasks/active")
def get_active_tasks():
    """Returns all running/queued tasks and recent history for global tracking."""
    tasks = TaskManager.get_active_tasks()
    return {"tasks": tasks, "count": len(tasks)}

@app.get("/api/tasks/{task_id}")
def get_task_by_id(task_id: str):
    """Returns a specific task status."""
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancels a pending/running task."""
    task = TaskManager.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task": task}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """Removes a task from registry."""
    ok = TaskManager.delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}

@app.post("/api/tasks/clear-completed")
def clear_completed_tasks():
    """Clears all completed, failed, or cancelled tasks."""
    cleared = TaskManager.clear_completed()
    return {"success": True, "cleared_count": cleared}

# ═══════════════════════════════════════════════════════════════════════
# 📋 POST LOG — Feedback Loop (track which angles sell best)
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/post-log")
def get_post_log(newest_first: bool = True):
    """Returns all posted clips with their recorded metrics."""
    posts = PostLog.list_posts(newest_first=newest_first)
    return {"posts": posts, "count": len(posts), "summary": PostLog.summary()}

@app.post("/api/post-log")
def add_post_log(payload: Dict[str, Any]):
    """Records that a clip went live on TikTok (or other platform)."""
    try:
        post = PostLog.add_post(
            product_name=payload.get("product_name", ""),
            clip_file=payload.get("clip_file", ""),
            platform=payload.get("platform", "tiktok"),
            product_url=payload.get("product_url", ""),
            angle_key=payload.get("angle_key", ""),
            angle_title=payload.get("angle_title", ""),
            hook=payload.get("hook", ""),
            caption=payload.get("caption", ""),
            hashtags=payload.get("hashtags"),
            posted_at=payload.get("posted_at"),
        )
        return {"success": True, "post": post, "summary": PostLog.summary()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.patch("/api/post-log/{post_id}/metrics")
@app.post("/api/post-log/{post_id}/metrics")
@app.patch("/api/posts/{post_id}/metrics")
def update_post_log_metrics(post_id: str, payload: Dict[str, Any]):
    """Fills in the 48-hour performance numbers for a post."""
    try:
        post = PostLog.update_metrics(post_id, payload)
        return {"success": True, "post": post, "summary": PostLog.summary()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/post-log/pending")
def get_pending_metrics():
    """Returns posts that are past 48 h but still have no performance numbers filled in."""
    pending = PostLog.pending_metrics()
    return {"pending": pending, "count": len(pending)}

@app.get("/api/post-log/performance")
def get_angle_performance():
    """Returns average views, cart-click-rate, and commission grouped by angle key."""
    return {"by_angle": PostLog.angle_performance(), "summary": PostLog.summary()}

@app.get("/api/posts/summary")
@app.get("/api/post-log/summary")
def get_post_log_summary():
    """Returns overall totals: clips posted, measured, total views, orders, commission."""
    return PostLog.summary()

@app.patch("/api/products/{product_id}/angles/{angle_id}")
def update_product_angle_status(product_id: str, angle_id: str, payload: Dict[str, Any]):
    """Updates status (draft, scripted, in_production, rendered, posted) of a specific angle script.

    Optional payload fields:
      qc_note       – free-text QC failure reason (stored on the angle for Studio reference)
      clear_qc_note – boolean; set True to wipe a previous qc_note when the clip passes QC
    """
    status = payload.get("status")
    video_url = payload.get("video_url")
    project_name = payload.get("project_name")
    qc_note = payload.get("qc_note")          # str | None
    clear_qc_note = bool(payload.get("clear_qc_note", False))
    if not status:
        raise HTTPException(status_code=400, detail="Missing status")
    try:
        updated = ProductStore.update_angle_status(
            product_id,
            angle_id,
            status,
            video_url=video_url,
            project_name=project_name,
            qc_note=qc_note,
            clear_qc_note=clear_qc_note,
        )
        return {"success": True, "product": updated}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))


@app.post("/api/products/{product_id}/angles/{angle_id}/videos")
def update_angle_videos_endpoint(product_id: str, angle_id: str, payload: Dict[str, Any]):
    """Persists selected raw footage attachments for a specific script angle."""
    try:
        selected_videos = payload.get("selected_videos", [])
        updated = ProductStore.update_angle_videos(product_id, angle_id, selected_videos)
        return {"success": True, "product": updated}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/products/{product_id}/default-videos")
def set_default_videos_endpoint(product_id: str, payload: Dict[str, Any]):
    """Sets default raw footage attachments for all script angles in a product."""
    try:
        selected_videos = payload.get("selected_videos", [])
        updated = ProductStore.set_default_videos_for_all_angles(product_id, selected_videos)
        return {"success": True, "product": updated}
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/script/ai-generate")
def generate_ai_scripts(req: ScriptGenerateRequest):
    """Generates 4 viral multi-angle TikTok review scripts using Google Gemini 2.5 Flash."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        # Fallback to local templates if no key
        base = ScriptGenerator.generate(req.product_name, req.key_features, req.pain_point, req.price_deal)
        return {
            "angles": [
                {
                    "angle_id": "problem_solution",
                    "angle_name": "🚫 เปิดด้วยปัญหา / จี้จุดเจ็บ",
                    "badge_color": "red",
                    "hook_title": f"อย่าเพิ่งซื้อ {req.product_name} ถ้ายังไม่เห็นสิ่งนี้!",
                    "estimated_sec": 26,
                    "script_text": base["full_text"],
                    "caption": f"ใครเจอปัญหา {req.pain_point} ดูด่วน! {req.product_name}",
                    "hashtags": ["#ของดีบอกต่อ", "#รีวิวของใช้", "#tiktokshop", f"#{req.product_name.replace(' ', '')}"]
                }
            ]
        }

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""คุณเป็นสุดยอด Copywriter และผู้เชี่ยวชาญการทำคลิป TikTok Shop / Affiliate มือโปร
กรุณาแต่งสคริปต์วิดีโอรีวิวป้ายยา 4 มุมมอง (4 Angles) สำหรับสินค้า:
- ชื่อสินค้า: {req.product_name}
- จุดเด่น: {req.key_features}
- ปัญหาที่แก้: {req.pain_point}
- ราคา/โปร: {req.price_deal}

กฎเหล็กการเขียนบทพูด:
- ชื่อแบรนด์, ชื่อรุ่นสินค้า, และคำศัพท์เฉพาะทางที่เป็นภาษาอังกฤษ (เช่น Logitech, Wave Keys, Logi Bolt, Bluetooth, USB-C, Type-C, iPad ฯลฯ) ให้คงไว้เป็นภาษาอังกฤษตามชื่อทางการเสมอ ห้ามทับศัพท์เป็นคำไทยเพี้ยนๆ (เช่น ห้ามเขียน "โลจิเทค", "โลจิ โบลต์")
- ห้ามใช้จุดไข่ปลา "..." หรือ "…" ในทุกฟิลด์โดยเด็ดขาด (ทั้งใน script_text, hook_title, caption) ให้เว้นวรรคธรรมดาแทน
- ห้ามใช้ภาษาโฆษณาทีวีทางการ ให้ใช้ภาษาพูดเพื่อนสนิทป้ายยา
- ห้ามใส่ emoji ในบทพูด (script_text) ใส่ได้เฉพาะ angle_name และ hook_title

กรุณาแต่งสคริปต์ภาษาพูดคนรีวิวจริง (ไม่เอาภาษาโฆษณาแข็งๆ) 4 รูปแบบ:
1. เตือนภัย / จี้จุดเจ็บ (Stop Scroll / Pain Point)
2. โชว์ฟังก์ชันสุดล้ำ / ว้าว (Tech Feature Hype)
3. โปรเดือด / ความคุ้มค่า (FOMO / Price Value)
4. ชีวิตดีขึ้น / เปรียบเทียบ (Transformation / Social Proof)

ตอบกลับเป็น JSON Format เท่านั้น:
```json
{{
  "angles": [
    {{
      "angle_id": "pain_point",
      "angle_name": "🚫 เตือนห้ามซื้อ / จี้จุดเจ็บ",
      "badge_color": "red",
      "hook_title": "พาดหัวแบนเนอร์บนจอ 3 วิแรก สั้นมาก",
      "estimated_sec": 26,
      "script_text": "ประโยคที่ 1\\nประโยคที่ 2\\nประโยคที่ 3\\nประโยคที่ 4\\nประโยคที่ 5 ปิดการขายจิ้มตะกร้า",
      "caption": "แคปชั่นสั้นๆ สำหรับโพสต์",
      "hashtags": ["#แฮชแท็ก1", "#แฮชแท็ก2", "#แฮชแท็ก3"]
    }}
  ]
}}
```
"""
        models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
        response = None
        for m_name in models:
            try:
                response = client.models.generate_content(model=m_name, contents=prompt)
                if response and response.text:
                    break
            except Exception:
                time.sleep(1)

        if not response or not response.text:
            raise RuntimeError("No response from Gemini API.")

        import re
        m = re.search(r"```json\s*([\s\S]*?)\s*```", response.text)
        clean_json = m.group(1).strip() if m else response.text.strip()
        data = json.loads(clean_json)
        # Sanitize any stray ellipses across all fields
        import re as _re
        for angle in data.get("angles", []):
            for k in ["script_text", "hook_title", "caption", "angle_name"]:
                v = angle.get(k)
                if isinstance(v, str):
                    angle[k] = _re.sub(r'[.]{2,}|\u2026', ' ', v).strip()
        return data

    except Exception as e:
        print(f"Error in generate_ai_scripts: {e}")
        # Graceful fallback
        base = ScriptGenerator.generate(req.product_name, req.key_features, req.pain_point, req.price_deal)
        return {
            "angles": [
                {
                    "angle_id": "problem_solution",
                    "angle_name": "🚫 เปิดด้วยปัญหา / จี้จุดเจ็บ (Offline Template)",
                    "badge_color": "red",
                    "hook_title": f"อย่าเพิ่งซื้อ {req.product_name} ถ้ายังไม่เห็นสิ่งนี้!",
                    "estimated_sec": 26,
                    "script_text": base["full_text"],
                    "caption": f"ใครเจอปัญหา {req.pain_point} ดูด่วน! {req.product_name}",
                    "hashtags": ["#ของดีบอกต่อ", "#รีวิวของใช้", "#tiktokshop"]
                }
            ]
        }

@app.post("/api/voice/preview")
def preview_voice(req: VoicePreviewRequest):
    """Generates a quick voice sample for auditioning (Edge-TTS or Gemini 3.1 Flash Commercial)."""
    sample_file = BASE_DIR / "test_voice.wav"
    
    if req.voice_gender and "gemini" in req.voice_gender:
        from scripts.gemini_tts_engine import GeminiFlashTTSEngine

        # Same resolver the pipeline uses, so the audition matches the render.
        gemini_voice = GeminiFlashTTSEngine.resolve_voice(preset=req.voice_gender)

        try:
            GeminiFlashTTSEngine.generate_speech(
                text=req.text or "สวัสดีครับ สายชาร์จแม่เหล็กตัวนี้คือที่สุด ดูดแน่น ชาร์จเร็ว 66 วัตต์ รีบกดในตะกร้าซ้ายล่างได้เลยครับ",
                output_path=str(sample_file),
                voice_name=gemini_voice,
                ad_tone=req.ad_tone or "commercial_premium",
                speed=req.speed or 1.15
            )
            return {
                "audio_url": f"/api/media/{sample_file.name}",
                "duration": measure_wav_duration(sample_file),
                "voice_name": gemini_voice
            }
        except Exception as g_err:
            print(f"⚠️ [preview_voice] Gemini TTS failed ({g_err}) — fallback to Edge-TTS...")

    res = VoiceEngine.generate_crystal_voice(
        text_or_lines=req.text or "สวัสดีค่ะ นี่คือเสียงตัวอย่างสำหรับคลิปรีวิวสินค้า",
        output_audio_path=str(sample_file),
        speed=req.speed,
        voice_gender=req.voice_gender
    )
    return {
        "audio_url": f"/api/media/{sample_file.name}",
        "duration": res["duration"]
    }

@app.post("/api/delete-file")
def delete_file(req: DeleteFileRequest):
    """Safely deletes a file from 00_Inbox, 01_Raw, 04_Exports, or 02_Assets with Windows file-lock handling."""
    import gc
    import shutil
    target = Path(req.file_path)
    if not target.is_absolute():
        target = BASE_DIR / req.file_path
    
    target = target.resolve()

    # Safety check: only allow deletion inside specific allowed project directories
    allowed_roots = [
        (BASE_DIR / "00_Inbox").resolve(),
        (BASE_DIR / "01_Raw").resolve(),
        (BASE_DIR / "04_Exports").resolve(),
        (BASE_DIR / "02_Assets").resolve(),
        (BASE_DIR / "03_Projects").resolve(),
        (BASE_DIR / "06_Archive").resolve()
    ]
    
    is_safe = any(str(target).startswith(str(root)) for root in allowed_roots)
    if not is_safe:
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้ลบไฟล์นอกพื้นที่โปรเจกต์")

    if not target.exists():
        return {"success": True, "message": "ไฟล์ถูกลบไปแล้ว", "filename": target.name}

    # Clean up associated subtitle files and companion .webp thumbnail
    stem = target.stem
    parent = target.parent
    companions = [
        parent / f"{stem}-sub.srt",
        parent / f"{stem}-sub.vtt",
        parent / f"{stem}.srt",
        parent / f"{stem}.vtt",
        target.with_suffix(".webp")
    ]
    for sub_file in companions:
        if sub_file.exists():
            try:
                sub_file.unlink()
            except Exception:
                pass

    gc.collect()

    def _on_deleted_success():
        try:
            ProductStore.rollback_by_video_or_project(target.name)
        except Exception:
            pass
        return {"success": True, "message": f"ลบไฟล์ {target.name} เรียบร้อยแล้ว", "filename": target.name}

    # Attempt 1: Direct deletion with retry loop
    for attempt in range(3):
        try:
            target.unlink()
            return _on_deleted_success()
        except PermissionError:
            gc.collect()
            time.sleep(0.2)
        except Exception as e:
            break

    # Attempt 2: If locked on Windows by an open video playback stream handle,
    # rename/move the file to hidden .trash directory in 06_Archive so it instantly vanishes from Exports
    try:
        trash_dir = BASE_DIR / "06_Archive" / ".trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        trash_target = trash_dir / f"{uuid.uuid4().hex}_{target.name}"
        shutil.move(str(target), str(trash_target))
        
        # Try unlinking from trash
        try:
            trash_target.unlink()
        except Exception:
            pass
        return _on_deleted_success()
    except Exception:
        pass

    # Attempt 3: Windows CMD force delete
    try:
        subprocess.run(["cmd", "/c", "del", "/f", "/q", str(target)], capture_output=True)
        if not target.exists():
            return _on_deleted_success()
    except Exception:
        pass

    raise HTTPException(status_code=500, detail="ไฟล์กำลังถูกเปิดใช้งานโดยเครื่องเล่นวิดีโอหรือ CapCut กรุณาหยุดเล่นวิดีโอหรือกดรีเฟรชหน้าเว็บ 1 ครั้งแล้วลองลบใหม่อีกครั้งครับ")

@app.get("/api/sfx")
def list_sfx():
    """Lists available sound effects from 02_Assets/SFX."""
    sfx_files = sorted(list(SFX_DIR.glob("*.wav")) + list(SFX_DIR.glob("*.mp3")))
    results = []
    for sf in sfx_files:
        info = get_file_info(sf)
        info["audio_url"] = f"/api/media/{info['rel_path']}"
        results.append(info)
    return {"sfx": results}

@app.get("/api/assets/all")
def list_all_assets():
    """
    Lists all categorized assets (SFX, Music, Fonts, Stickers, LUTs).

    Backed by AssetRegistry (scripts/asset_registry.py) instead of a second,
    separate glob -- this used to re-scan 02_Assets/* independently of the
    registry, so the two could disagree (e.g. this endpoint guessed a font's
    family from its filename while nothing else did). Response shape/keys
    (`music`, `font_family`, per-file fields) kept exactly as before so
    SystemAssets.jsx needs no change.
    """
    registry = AssetRegistry.load()

    font_list = [{**f, "font_family": f["family"]} for f in registry["fonts"]]

    return {
        "sfx": registry["sfx"],
        "music": registry["bgm"],
        # Which track plays when a project names none. The editor used to keep
        # its own copy of this and they drifted apart.
        "default_bgm": DEFAULT_BGM,
        "fonts": font_list,
        "stickers": registry["stickers"],
        "luts": registry["luts"],
        "counts": {
            "sfx": len(registry["sfx"]),
            "music": len(registry["bgm"]),
            "fonts": len(font_list),
            "stickers": len(registry["stickers"]),
            "luts": len(registry["luts"])
        }
    }

@app.post("/api/assets/rescan")
def rescan_assets():
    """Force a fresh scan of 02_Assets/* -- for a file dropped in by hand, outside the upload UI."""
    registry = AssetRegistry.rebuild()
    return {"success": True, "counts": registry["counts"]}

@app.post("/api/assets/upload")
async def upload_asset(file: UploadFile = File(...), asset_type: str = Form("sfx")):
    """Uploads an asset to the appropriate 02_Assets subfolder."""
    type_map = {
        "sfx": SFX_DIR,
        "music": MUSIC_DIR,
        "fonts": ASSETS_DIR / "Fonts",
        "stickers": ASSETS_DIR / "Stickers_Memes",
        "luts": ASSETS_DIR / "LUTs_ColorPresets",
        "branding": ASSETS_DIR / "Branding"  # reserved for a future logo/watermark feature; no consuming UI yet
    }
    dest_dir = type_map.get(asset_type.lower(), SFX_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    save_path = dest_dir / file.filename
    with open(save_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # So the new file is immediately selectable without a separate rescan step.
    AssetRegistry.rebuild()

    return {
        "message": f"เพิ่มทรัพยากร {file.filename} เข้าสู่ {asset_type.upper()} เรียบร้อยแล้ว",
        "file": get_file_info(save_path)
    }

@app.post("/api/open-folder")
def open_folder(req: OpenFolderRequest):
    """Opens a target directory in Windows Explorer."""
    folder_map = {
        "exports": EXPORTS_DIR,
        "inbox": INBOX_DIR,
        "raw": RAW_DIR,
        "assets": ASSETS_DIR,
        "sfx": SFX_DIR,
        "music": MUSIC_DIR,
        "fonts": ASSETS_DIR / "Fonts",
        "stickers": ASSETS_DIR / "Stickers_Memes",
        "luts": ASSETS_DIR / "LUTs_ColorPresets",
        "capcut": CAPCUT_DRAFT_DIR,
        "root": BASE_DIR
    }
    target_path = folder_map.get(req.target, Path(req.target))
    
    if os.name == 'nt':
        try:
            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(target_path))
            return {"success": True, "path": str(target_path)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"success": False, "message": "Not on Windows"}

@app.post("/api/sub-srt/transcribe")
def run_sub_srt_transcription(req: TranscribeRequest):
    """
    Runs sub-srt Speech Recognition (faster-whisper) on a video or audio file.
    Outputs accurate .srt / .vtt subtitles with PyThaiNLP word boundaries and optional English translation.
    """
    media_path = Path(req.media_path)
    if not media_path.is_absolute():
        media_path = BASE_DIR / req.media_path

    if not media_path.exists():
        raise HTTPException(status_code=404, detail=f"Media file not found: {media_path}")

    skill_script = PROJECT_ROOT / ".agents" / "skills" / "sub-srt" / "generate_srt.py"
    if not skill_script.exists():
        skill_script = Path(os.environ.get("USERPROFILE", "")) / ".gemini" / "config" / "skills" / "sub-srt" / "generate_srt.py"

    out_dir = media_path.parent
    cmd = [
        sys.executable, str(skill_script),
        str(media_path),
        "--mode", req.mode,
        "--words-per-line", str(req.words_per_line),
        "--vtt",
        "--outdir", str(out_dir)
    ]
    if req.lang:
        cmd.extend(["--lang", req.lang])
    if req.fast:
        cmd.append("--fast")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {proc.stderr}")

        base_stem = media_path.stem
        srt_file = out_dir / f"{base_stem}-sub.srt"
        vtt_file = out_dir / f"{base_stem}-sub.vtt"

        # Read generated srt content
        srt_content = srt_file.read_text(encoding="utf-8", errors="ignore") if srt_file.exists() else ""
        
        return {
            "success": True,
            "srt_path": str(srt_file) if srt_file.exists() else None,
            "srt_url": f"/api/media/{srt_file.relative_to(BASE_DIR)}" if srt_file.exists() else None,
            "vtt_url": f"/api/media/{vtt_file.relative_to(BASE_DIR)}" if vtt_file.exists() else None,
            "content": srt_content,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------
# Asynchronous Video Rendering & SSE Job Tracking
# ----------------------------------------------------------------------

def execute_render_job(job_id: str, req_data: RenderRequest):
    """Background worker function executing the full video pipeline."""
    base_progress = render_jobs.progress_reporter(job_id)

    def on_progress(msg: str, progress: float):
        base_progress(msg, progress)
        TaskManager.update_progress(job_id, progress, step_label=msg)

    try:
        raw_video = Path(req_data.raw_video_path)
        if not raw_video.is_absolute():
            raw_video = BASE_DIR / req_data.raw_video_path

        # Resolve Human voice if extracted from video or uploaded
        human_voice_path = req_data.human_voice_audio
        if req_data.voice_mode == "video":
            human_voice_path = str(raw_video)
        elif req_data.voice_mode == "human" and human_voice_path:
            h_path = Path(human_voice_path)
            if not h_path.is_absolute():
                human_voice_path = str(BASE_DIR / human_voice_path)

        # F5-TTS was dropped: this machine has no CUDA, so it was minutes per
        # clip on CPU. Anything asking for it falls back to Edge-TTS.
        voice_engine_type = "gemini_tts" if req_data.voice_mode == "gemini_tts" else "edge_tts"

        # Resolve sticker badge path
        sticker_file_path = None
        if req_data.sticker_badge:
            candidate = STICKERS_DIR / req_data.sticker_badge
            if candidate.exists():
                sticker_file_path = str(candidate)
            elif (BASE_DIR / req_data.sticker_badge).exists():
                sticker_file_path = str(BASE_DIR / req_data.sticker_badge)

        # Update angle to in_production with project_name when render starts
        if req_data.product_id and req_data.angle_id:
            try:
                ProductStore.update_angle_status(
                    req_data.product_id,
                    req_data.angle_id,
                    "in_production",
                    project_name=req_data.project_name
                )
            except Exception:
                pass

        # See render_jobs._RENDER_SLOT: this machine has no CUDA and 13.7GB RAM,
        # so renders are serialized -- a second request waits as "queued"
        # rather than fighting the first one for CPU/RAM.
        with render_jobs.render_slot(job_id):
            result = TikTokAutoCutterPipeline.run(
                product_name=req_data.product_name,
                raw_video_path=str(raw_video),
                project_name=req_data.project_name,
                key_features=req_data.key_features,
                pain_point=req_data.pain_point,
                price_deal=req_data.price_deal,
                custom_script=req_data.custom_script,
                script_overlays=req_data.script_overlays,
                voice=req_data.voice_gender,
                voice_rate=req_data.voice_rate,
                voice_engine_type=voice_engine_type,
                voice_preset=req_data.voice_preset,
                ad_tone=req_data.ad_tone or "commercial_premium",
                human_voice_audio_path=human_voice_path,
                hook_brand=req_data.hook_brand,
                hook_model=req_data.hook_model,
                hook_label=req_data.hook_label,
                hook_motion=req_data.hook_motion,
                hook_colors=req_data.hook_colors,
                hook_style=req_data.hook_style,
                font_name=req_data.font_name,
                bilingual_subtitles=req_data.bilingual_subtitles,
                use_ai_vision=req_data.use_ai_vision,
                sticker_path=sticker_file_path,
                bgm_name=req_data.bgm_name,
                bgm_volume=req_data.bgm_volume,
                bgm_ducking=req_data.bgm_ducking,
                lut_name=req_data.lut_name,
                clip_list=req_data.clip_list,
                transitions=req_data.transitions,
                export_mp4=req_data.export_mp4,
                caption_position=req_data.caption_position or "bottom",
                caption_color=req_data.caption_color,
                caption_scale=req_data.caption_scale or 1.0,
                sticker_position=req_data.sticker_position or "top_right",
                sticker_scale=req_data.sticker_scale or 1.0,
                text_overlays=req_data.text_overlays,
                product_id=req_data.product_id,
                angle_id=req_data.angle_id,
                progress_callback=on_progress
            )

        # Record the link the other way too: the product now knows which
        # projects came out of it, which is what makes a later delete exact
        # rather than a name match.
        if req_data.product_id and result.get("project_name"):
            try:
                ProductStore.attach_project(req_data.product_id, result["project_name"])
            except Exception as link_err:
                print(f"Warning: could not link project to product: {link_err}")

        # Update angle status strictly reflecting reality:
        # If exported MP4 exists -> 'rendered'
        # If timeline project was generated (export_mp4 is False) -> 'in_production' with project_name attached
        if req_data.product_id and req_data.angle_id:
            try:
                mp4_val = result.get("mp4") or result.get("output_video") or result.get("video_path") or ""
                is_rendered = bool(req_data.export_mp4 and mp4_val)
                ProductStore.update_angle_status(
                    req_data.product_id,
                    req_data.angle_id,
                    "rendered" if is_rendered else "in_production",
                    video_url=str(mp4_val) if is_rendered else None,
                    project_name=result.get("project_name")
                )
            except Exception as angle_err:
                print(f"Warning: could not update angle status: {angle_err}")

        render_jobs.complete_job(job_id, result)
        is_exported = bool(req_data.export_mp4 and (result.get("mp4") or result.get("output_video") or result.get("video_path")))
        TaskManager.complete_task(
            job_id,
            result=result,
            step_label="🎉 เรนเดอร์วิดีโอเสร็จสมบูรณ์ 100%!" if is_exported else "🎉 การตัดต่อเสร็จสมบูรณ์ 100%!",
            target_id=result.get("project_name")
        )

    except Exception as e:
        if req_data.product_id and req_data.angle_id:
            try:
                ProductStore.update_angle_status(req_data.product_id, req_data.angle_id, "scripted")
            except Exception:
                pass
        render_jobs.fail_job(job_id, e)
        fail_msg = "การเรนเดอร์วิดีโอล้มเหลว" if req_data.export_mp4 else "การตัดต่อวิดีโอล้มเหลว"
        TaskManager.fail_task(job_id, str(e), step_label=fail_msg)

@app.post("/api/render")
def trigger_render(req: RenderRequest, background_tasks: BackgroundTasks):
    """Triggers the video creation pipeline in the background."""
    job_id = str(uuid.uuid4())
    render_jobs.create_job(job_id)

    # Register in global TaskManager
    p_name = req.product_name or req.project_name or "วิดีโอใหม่"
    is_render_task = bool(req.export_mp4)
    TaskManager.create_task(
        task_type="render_video" if is_render_task else "edit_project",
        title=f"{'เรนเดอร์วิดีโอ' if is_render_task else 'ตัดต่อวิดีโอ'}: {p_name}",
        payload={"project_name": req.project_name, "product_name": req.product_name, "export_mp4": is_render_task},
        target_tab="gallery" if is_render_task else "editor",
        target_id=req.project_name,
        task_id=job_id
    )

    background_tasks.add_task(execute_render_job, job_id, req)
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/render/status/{job_id}")
def get_render_status(job_id: str):
    """Returns current status and progress of a render job."""
    if job_id in ACTIVE_JOBS:
        return ACTIVE_JOBS[job_id]

    # Fallback to persistent TaskManager registry on disk so reloads don't lose job state
    task = TaskManager.get_task(job_id)
    if task:
        return {
            "id": job_id,
            "status": task.get("status", "completed"),
            "progress": task.get("progress", 1.0),
            "message": task.get("step_label", "เสร็จสิ้น"),
            "result": task.get("result") or {},
            "error": task.get("error"),
        }
    raise HTTPException(status_code=404, detail="Job not found")

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
        reload=should_reload,
        reload_dirs=[str(PROJECT_ROOT / "scripts")] if should_reload else None
    )
