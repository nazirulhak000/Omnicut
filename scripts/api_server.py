"""
FastAPI Backend Server for TikTok Auto-Cutter AI & CapCut Pipeline
Provides REST APIs, video/audio streaming with byte-range support, and SSE progress updates.
"""

import os
import sys
import glob
import time
import uuid
import json
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
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
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

app = FastAPI(
    title="TikTok Auto-Cutter Pro API",
    description="Backend API for TikTok Auto-Cutter AI & CapCut Desktop Generator",
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
from scripts.api_phase1 import router as phase1_router

app.include_router(phase1_router)

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
    hook_title: Optional[str] = None
    custom_script: Optional[str] = None
    script_overlays: Optional[List[str]] = None  # per-line spec-bar text, index-aligned with custom_script
    voice_mode: str = "gemini_tts" # gemini_tts, edge_tts, human, video
    voice_gender: str = "female"
    voice_rate: str = "+15%"
    voice_preset: Optional[str] = "gemini_puck_male_hype"  # Gemini prebuilt voice, e.g. gemini_puck_male_hype
    ad_tone: Optional[str] = "commercial_premium"
    human_voice_audio: Optional[str] = None
    font_name: str = "IBMPlex"
    bilingual_subtitles: bool = True
    use_ai_vision: bool = True
    sticker_badge: Optional[str] = "badge_flash_sale_3d.png"
    bgm_name: Optional[str] = None  # BGM filename from AssetRegistry.bgm(); None keeps SFXManager's own default
    lut_name: Optional[str] = None  # LUT filename from AssetRegistry.luts(); None auto-picks by IT angle, or no grade
    export_mp4: bool = True

class DeleteFileRequest(BaseModel):
    file_path: str

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
    return {
        "name": file_path.name,
        "path": str(file_path),
        "rel_path": str(file_path.relative_to(BASE_DIR)).replace("\\", "/"),
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": stat.st_mtime
    }

# Range-supporting file streamer for smooth HTML5 video/audio playback
def stream_media_file(file_path: Path, request: Request):
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    content_type = "video/mp4"
    if file_path.suffix.lower() in [".mov"]:
        content_type = "video/quicktime"
    elif file_path.suffix.lower() in [".mp3"]:
        content_type = "audio/mpeg"
    elif file_path.suffix.lower() in [".wav"]:
        content_type = "audio/wav"

    if range_header:
        # Example: "bytes=100-200" or "bytes=100-"
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        end = min(end, file_size - 1)
        chunk_size = (end - start) + 1

        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = chunk_size
                while bytes_left > 0:
                    read_len = min(64 * 1024, bytes_left)
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
        def iterfile():
            with open(file_path, "rb") as f:
                while chunk := f.read(64 * 1024):
                    yield chunk

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(iterfile(), headers=headers)

def get_local_ip() -> str:
    """Returns the primary local IPv4 address of this machine on the LAN/Wi-Fi."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            import socket
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

# ----------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------

@app.get("/api/status")
def get_system_status():
    """Returns general health and system stats."""
    raw_files = []
    for ext in ("*.mov", "*.mp4", "*.m4v", "*.MOV", "*.MP4"):
        raw_files.extend(glob.glob(str(RAW_DIR / "**" / ext), recursive=True))
        raw_files.extend(glob.glob(str(INBOX_DIR / "**" / ext), recursive=True))
    
    export_files = list(EXPORTS_DIR.glob("*.mp4"))
    local_ip = get_local_ip()

    return {
        "status": "online",
        "ffmpeg_ready": True,
        "capcut_draft_path": str(CAPCUT_DRAFT_DIR),
        "capcut_synced": CAPCUT_DRAFT_DIR.exists(),
        "total_raw_videos": len(set(raw_files)),
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
def list_raw_videos():
    """Lists all available raw video candidates from Inbox and Raw directories."""
    candidates = []
    for ext in ("*.mov", "*.mp4", "*.m4v", "*.MOV", "*.MP4"):
        candidates.extend(glob.glob(str(RAW_DIR / "**" / ext), recursive=True))
        candidates.extend(glob.glob(str(INBOX_DIR / "**" / ext), recursive=True))

    unique_paths = sorted(list(set(candidates)), key=os.path.getmtime, reverse=True)
    results = [get_file_info(Path(p)) for p in unique_paths]
    return {"videos": results}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), target_dir: str = Form("inbox")):
    """Uploads a video or audio file to 00_Inbox."""
    dest_dir = INBOX_DIR if target_dir == "inbox" else RAW_DIR
    save_path = dest_dir / file.filename

    with open(save_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    return {
        "message": "Upload successful",
        "file": get_file_info(save_path)
    }

@app.post("/api/upload-multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...), target_dir: str = Form("inbox")):
    """Uploads multiple video or audio files to 00_Inbox."""
    dest_dir = INBOX_DIR if target_dir == "inbox" else RAW_DIR
    uploaded_files = []
    for f in files:
        save_path = dest_dir / f.filename
        with open(save_path, "wb") as buffer:
            content = await f.read()
            buffer.write(content)
        uploaded_files.append(get_file_info(save_path))

    return {
        "message": f"Successfully uploaded {len(uploaded_files)} files",
        "files": uploaded_files
    }

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
    """Lists all rendered videos in 04_Exports/Ready_to_post."""
    files = sorted(list(EXPORTS_DIR.glob("*.mp4")), key=os.path.getmtime, reverse=True)
    return {"exports": [get_file_info(f) for f in files]}

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
    return {"script": data}

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
        models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
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

    # Clean up associated subtitle files
    stem = target.stem
    parent = target.parent
    for sub_file in [parent / f"{stem}-sub.srt", parent / f"{stem}-sub.vtt", parent / f"{stem}.srt", parent / f"{stem}.vtt"]:
        if sub_file.exists():
            try:
                sub_file.unlink()
            except Exception:
                pass

    gc.collect()

    # Attempt 1: Direct deletion with retry loop
    for attempt in range(3):
        try:
            target.unlink()
            return {"success": True, "message": f"ลบไฟล์ {target.name} เรียบร้อยแล้ว", "filename": target.name}
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
        return {"success": True, "message": f"ลบไฟล์ {target.name} เรียบร้อยแล้ว", "filename": target.name}
    except Exception:
        pass

    # Attempt 3: Windows CMD force delete
    try:
        subprocess.run(["cmd", "/c", "del", "/f", "/q", str(target)], capture_output=True)
        if not target.exists():
            return {"success": True, "message": f"ลบไฟล์ {target.name} เรียบร้อยแล้ว", "filename": target.name}
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
    on_progress = render_jobs.progress_reporter(job_id)

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
                hook_title=req_data.hook_title,
                font_name=req_data.font_name,
                bilingual_subtitles=req_data.bilingual_subtitles,
                use_ai_vision=req_data.use_ai_vision,
                sticker_path=sticker_file_path,
                bgm_name=req_data.bgm_name,
                lut_name=req_data.lut_name,
                export_mp4=req_data.export_mp4,
                progress_callback=on_progress
            )

        render_jobs.complete_job(job_id, result)

    except Exception as e:
        render_jobs.fail_job(job_id, e)

@app.post("/api/render")
def trigger_render(req: RenderRequest, background_tasks: BackgroundTasks):
    """Triggers the video creation pipeline in the background."""
    job_id = str(uuid.uuid4())
    render_jobs.create_job(job_id)
    background_tasks.add_task(execute_render_job, job_id, req)
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/render/status/{job_id}")
def get_render_status(job_id: str):
    """Returns current status and progress of a render job."""
    if job_id not in ACTIVE_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return ACTIVE_JOBS[job_id]

# ----------------------------------------------------------------------
# Run Server directly if executed
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting TikTok Auto-Cutter FastAPI on http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
