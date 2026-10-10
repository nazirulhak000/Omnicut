"""
API Router for HyperFrames Creative Studio.
Manages programmatic video compositions, approved viral styles, headless Chrome rendering,
and automated export registry synchronization.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from scripts.config import BASE_DIR, EXPORTS_DIR
from scripts.export_registry import ExportRegistry
from scripts.product_store import ProductStore
from scripts import path_utils

logger = logging.getLogger("omnicut.api_hyperframes")

router = APIRouter(prefix="/api/hyperframes", tags=["HyperFrames"])

STUDIO_DIR = BASE_DIR / "03_Projects" / "_HyperFrames_Studio"
COMPOSITIONS_DIR = STUDIO_DIR / "compositions"
CLIPS_DIR = STUDIO_DIR / "clips"
KIT_DIR = STUDIO_DIR / "kit"
ASSETS_DIR = STUDIO_DIR / "assets"
TMP_DIR = BASE_DIR / ".tmp" / "hyperframes"

_WHISPER_LOCK = threading.Lock()
_RENDER_LOCK = threading.Lock()


# ── Pydantic Request/Response Models ──

class CreateClipRequest(BaseModel):
    clip_id: str = Field(..., description="Unique clip ID, e.g. ess02-battery-36s, hat01-meme-45s")
    product: str = Field(..., description="Product shortcode, e.g. ess02, hat01")
    vo_path: Optional[str] = Field(None, description="Path to voiceover WAV (relative to OmniCut or absolute)")
    script: Optional[str] = Field(None, description="Script text prompt for whisper alignment")
    style: Optional[str] = Field("meme_pas", description="One of: meme_pas, tech_explainer, vs_battle, pov_chat")


class RenderCompositionRequest(BaseModel):
    composition_id: str = Field(..., description="Stem of composition file, e.g. hat01-meme-45s")
    output_filename: Optional[str] = Field(None, description="Custom export filename (optional)")
    product_id: Optional[str] = Field(None, description="Linked product ID (e.g. HAT01)")
    angle_id: Optional[str] = Field(None, description="Linked angle ID")
    is_test: bool = Field(False, description="If True, renders to .tmp/ instead of 04_Exports/")


class OpenStudioRequest(BaseModel):
    port: int = Field(3002, description="Port for HyperFrames Studio web preview")


# ── Helper Functions ──

def _find_python() -> str:
    venv_py = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)
    return "python"


def _extract_composition_metadata(html_path: Path) -> Dict[str, Any]:
    """Parse title, duration, product and metadata from a composition HTML file."""
    content = ""
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass

    duration = 30.0
    dur_match = re.search(r'data-duration=["\']([\d.]+)s?["\']', content)
    if dur_match:
        try:
            duration = float(dur_match.group(1))
        except ValueError:
            pass

    title = html_path.stem
    title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
    if title_match and title_match.group(1).strip():
        title = title_match.group(1).strip()

    product = html_path.stem.split("-")[0] if "-" in html_path.stem else "general"

    stat = html_path.stat()
    return {
        "id": html_path.stem,
        "filename": html_path.name,
        "title": title,
        "product": product,
        "duration": duration,
        "size_bytes": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "has_script": (CLIPS_DIR / html_path.stem / "script.txt").exists(),
        "has_vo": (ASSETS_DIR / "clips" / html_path.stem / "vo.wav").exists(),
    }


def _extract_video_thumbnail(mp4_path: Path, webp_path: Path, seek_sec: float = 1.5) -> bool:
    """Generate a clean WebP thumbnail from an MP4 export using FFmpeg."""
    try:
        cmd = [
            "ffmpeg", "-v", "error", "-y",
            "-ss", str(seek_sec),
            "-i", str(mp4_path),
            "-frames:v", "1",
            "-vf", "scale=540:960",
            "-c:v", "libwebp",
            "-quality", "85",
            str(webp_path),
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=15)
        return res.returncode == 0 and webp_path.exists()
    except Exception as e:
        logger.warning("Failed to extract thumbnail for %s: %s", mp4_path, e)
        return False


# ── Endpoints ──

@router.get("/status")
def get_hyperframes_status() -> Dict[str, Any]:
    """Check availability of HyperFrames environment, CLI, Node, and Python packages."""
    node_ok = False
    node_version = ""
    try:
        res = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            node_ok = True
            node_version = res.stdout.strip()
    except Exception:
        pass

    cli_ok = False
    cli_version = ""
    try:
        # Check from package.json or fast version probe
        pkg_file = STUDIO_DIR / "package.json"
        if pkg_file.exists():
            pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
            cli_version = pkg_data.get("devDependencies", {}).get("@hyperframes/core", "")
            cli_ok = bool(cli_version)
    except Exception:
        pass

    whisper_ok = False
    try:
        py_exe = _find_python()
        w_res = subprocess.run([py_exe, "-c", "import faster_whisper; print('OK')"], capture_output=True, text=True, timeout=8)
        whisper_ok = (w_res.returncode == 0 and "OK" in w_res.stdout)
    except Exception:
        pass

    rembg_ok = False
    try:
        py_exe = _find_python()
        r_res = subprocess.run([py_exe, "-c", "import rembg; print('OK')"], capture_output=True, text=True, timeout=8)
        rembg_ok = (r_res.returncode == 0 and "OK" in r_res.stdout)
    except Exception:
        pass

    comps_count = len(list(COMPOSITIONS_DIR.glob("*.html"))) if COMPOSITIONS_DIR.exists() else 0

    return {
        "studio_installed": STUDIO_DIR.exists(),
        "studio_path": str(STUDIO_DIR),
        "node_installed": node_ok,
        "node_version": node_version,
        "hyperframes_cli_ready": cli_ok,
        "hyperframes_version": cli_version or "0.8.143",
        "faster_whisper_available": whisper_ok,
        "rembg_available": rembg_ok,
        "compositions_count": comps_count,
        "ready": STUDIO_DIR.exists() and node_ok and cli_ok,
    }


@router.get("/styles")
def get_approved_styles() -> List[Dict[str, Any]]:
    """Return catalog of 4 human-crafted styles approved for viral gadget videos."""
    return [
        {
            "id": "meme_pas",
            "name": "Meme-PAS (รีวิวสายมีม)",
            "tagline": "เจ็บ → ฮา → เปิดตัวสินค้าแก้ปัญหา → ขาย",
            "formula": "0-4s Hook ปัญหาคนเจอจริง + มีมปรอทแตก / 4-10s บิลค่าไฟพุ่ง + มีม Key&Peele + Meme Pause 0.8s / 10-14s หักมุมแตรลม / กลางคลิป จุดขายคู่กับ 1 มีมจริง + 1 SFX / ท้ายคลิป ตะกร้าเหลือง",
            "reference": "hat01-meme-45s, ess02-battery-36s",
            "recommended_duration_sec": 45,
            "has_voiceover": True,
            "badge": "ยอดนิยม ⭐",
            "pros": "คลิปมีอารมณ์ขันสูง คนหยุดดูด้วยมีม ไม่รู้สึกว่าโดนยัดเยียดขายของ",
        },
        {
            "id": "tech_explainer",
            "name": "Tech Explainer (สาย Vox)",
            "tagline": "เสียงสุขุม อธิบาย 'ทำไม' ด้วยภาพจริง + ไดอะแกรม 1 ภาพต่อ 1 ไอเดีย",
            "formula": "กราฟิกโมชั่นผ่าโครงสร้างภายใน, ตัวเลขวัตต์/อุณหภูมิ, วงจรชิปเซ็ต, ข้อเท็จจริงเชิงวิศวกรรม",
            "reference": "ess02-explainer-40s",
            "recommended_duration_sec": 40,
            "has_voiceover": True,
            "badge": "สายเทคโนโลยี 📊",
            "pros": "สร้างความน่าเชื่อถือสูงมาก เหมาะกับสินค้าแกดเจ็ตที่มีสเปกซับซ้อน",
        },
        {
            "id": "vs_battle",
            "name": "VS Battle (สายเกมต่อสู้)",
            "tagline": "HUD เกม Street Fighter ซัดกัน 3 ยก K.O.",
            "formula": "ภาพสินค้าสองฝั่ง (ของแถม/รุ่นเก่า VS รุ่นใหม่) เปรียบเทียบความเร็ว/ความร้อน/ราคา 3 ยก พร้อมแถบหลอดเลือดและเอฟเฟกต์ต่อสู้",
            "reference": "ess02-vs-25s",
            "recommended_duration_sec": 25,
            "has_voiceover": True,
            "badge": "เกมมิ่งไฟท์ติ้ง 🥊",
            "pros": "ชูความเหนือกว่าของสินค้าชัดเจน เห็นผลต่างภายใน 25 วินาที",
        },
        {
            "id": "pov_chat",
            "name": "POV Chat Story ⭐ (ไม่มีเสียงพากย์)",
            "tagline": "เล่าเรื่องชีวิตจริงผ่านแชท LINE แล้วเปิดตัวสินค้าเป็นทางออก",
            "formula": "จำลองหน้าจอ LINE Chat ดราม่าความสัมพันธ์/ความกังวลในชีวิต (เช่น แฟนบ่นร้อน, แบตหมดตอนฉุกเฉิน) สลับพิมพ์ตอบก่อนเปิดตัวสินค้าช่วยชีวิต",
            "reference": "ess02-pov-chat-28s",
            "recommended_duration_sec": 28,
            "has_voiceover": False,
            "badge": "ตัวโปรดเจ้าของช่อง 🔥",
            "pros": "ไม่ต้องอัดเสียงพากย์ ทำคลิปได้ไม่จำกัดเรื่องราว ดึงดูดสายตาคนอ่านแชท 100%",
        },
    ]


@router.get("/compositions")
def list_compositions() -> List[Dict[str, Any]]:
    """List all compositions in HyperFrames Studio with metadata."""
    if not COMPOSITIONS_DIR.exists():
        return []

    comps = []
    for file in sorted(COMPOSITIONS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        comps.append(_extract_composition_metadata(file))
    return comps


@router.post("/create-clip")
def create_clip(payload: CreateClipRequest) -> Dict[str, Any]:
    """Create a new HyperFrames clip draft by invoking kit/new_clip.py."""
    if not STUDIO_DIR.exists():
        raise HTTPException(status_code=500, detail="HyperFrames Studio directory not found")

    clip_id = payload.clip_id.strip()
    if not re.match(r'^[a-zA-Z0-9_-]+$', clip_id):
        raise HTTPException(status_code=400, detail="Invalid clip_id format. Use letters, numbers, dashes, underscores.")

    comp_file = COMPOSITIONS_DIR / f"{clip_id}.html"
    if comp_file.exists():
        raise HTTPException(status_code=409, detail=f"Composition '{clip_id}' already exists")

    product = payload.product.strip().lower()
    product_dir = ASSETS_DIR / product
    if not product_dir.exists():
        raise HTTPException(status_code=400, detail=f"Product folder 'assets/{product}' not found in HyperFrames Studio")

    # If vo_path provided, check existence
    vo_file = None
    if payload.vo_path:
        vo_candidate = Path(payload.vo_path)
        if not vo_candidate.is_absolute():
            vo_candidate = BASE_DIR / vo_candidate
        if not vo_candidate.exists():
            raise HTTPException(status_code=400, detail=f"Voiceover file not found: {payload.vo_path}")
        vo_file = vo_candidate

    # If no vo provided, look for project VO
    if not vo_file:
        for prj_dir in (BASE_DIR / "03_Projects").glob(f"*{product.upper()}*"):
            cand = prj_dir / "voiceover.wav"
            if cand.exists():
                vo_file = cand
                break

    if not vo_file and payload.style != "pov_chat":
        raise HTTPException(status_code=400, detail=f"No voiceover WAV found for product '{product}'. Please provide vo_path.")

    script_path = None
    if payload.script:
        tmp_script = TMP_DIR / f"{clip_id}_prompt.txt"
        tmp_script.parent.mkdir(parents=True, exist_ok=True)
        tmp_script.write_text(payload.script, encoding="utf-8")
        script_path = tmp_script

    with _WHISPER_LOCK:
        try:
            py_exe = _find_python()
            cmd = [py_exe, str(KIT_DIR / "new_clip.py"), clip_id, "--product", product]
            if vo_file:
                cmd += ["--vo", str(vo_file)]
            if script_path:
                cmd += ["--script", str(script_path)]

            res = subprocess.run(cmd, cwd=STUDIO_DIR, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                logger.error("new_clip failed: %s", res.stderr)
                raise HTTPException(status_code=500, detail=f"Failed to create clip: {res.stderr or res.stdout}")

        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Clip creation timed out (Whisper transcription took too long)")

    return {
        "status": "created",
        "clip_id": clip_id,
        "composition_path": f"compositions/{clip_id}.html",
        "message": f"Successfully created clip draft '{clip_id}'",
    }


@router.post("/render")
async def render_composition(payload: RenderCompositionRequest) -> Dict[str, Any]:
    """Render a HyperFrames composition into a 9:16 MP4 video via Chrome Headless."""
    comp_id = payload.composition_id.strip()
    comp_file = COMPOSITIONS_DIR / f"{comp_id}.html"
    if not comp_file.exists():
        raise HTTPException(status_code=404, detail=f"Composition '{comp_id}' not found")

    date_str = datetime.now().strftime("%Y%m%d")
    clean_name = payload.output_filename or f"{date_str}_{comp_id}_v1.mp4"
    if not clean_name.endswith(".mp4"):
        clean_name += ".mp4"

    if payload.is_test:
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        out_path = TMP_DIR / f"test_{clean_name}"
    else:
        # Standard Ready_to_post destination
        target_dir = EXPORTS_DIR / "Ready_to_post"
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / clean_name

    def _do_render():
        with _RENDER_LOCK:
            cmd = [
                "npx", "--yes", "hyperframes@0.8.143", "render",
                "-c", f"compositions/{comp_id}.html",
                "-o", str(out_path),
            ]
            log_file = TMP_DIR / f"render_{comp_id}.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(log_file, "w", encoding="utf-8") as lf:
                proc = subprocess.run(
                    cmd,
                    cwd=STUDIO_DIR,
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                    timeout=300,
                )

            if proc.returncode != 0 or not out_path.exists():
                err_text = ""
                try:
                    err_text = log_file.read_text(encoding="utf-8")[-1000:]
                except Exception:
                    pass
                raise RuntimeError(f"Render failed with code {proc.returncode}: {err_text}")

            # Generate thumbnail WebP
            webp_path = out_path.with_suffix(".webp")
            _extract_video_thumbnail(out_path, webp_path, seek_sec=1.5)

            # Register into export_registry if final export
            export_id = None
            if not payload.is_test and out_path.exists():
                rel_path = path_utils.to_relative(out_path, base_dir=BASE_DIR)
                reg_rows = ExportRegistry.ensure_many([
                    {
                        "path": rel_path,
                        "product_id": payload.product_id or comp_id.split("-")[0].upper(),
                        "angle_id": payload.angle_id or "hyperframes_creative",
                        "project_name": f"_HyperFrames_Studio/{comp_id}",
                        "status": "rendered",
                    }
                ])
                if reg_rows:
                    export_id = reg_rows[0].get("id")

            return {
                "output_path": str(out_path),
                "export_id": export_id,
                "thumbnail_path": str(webp_path) if webp_path.exists() else None,
                "size_bytes": out_path.stat().st_size,
            }

    try:
        result = await asyncio.to_thread(_do_render)
    except Exception as e:
        logger.error("HyperFrames render exception: %s", e)
        raise HTTPException(status_code=500, detail=f"Render execution failed: {str(e)}")

    return {
        "status": "rendered",
        "composition_id": comp_id,
        "is_test": payload.is_test,
        **result,
    }


@router.post("/open-studio")
def open_studio(payload: OpenStudioRequest = OpenStudioRequest()) -> Dict[str, Any]:
    """Launch HyperFrames Studio web preview server and open in browser."""
    if not STUDIO_DIR.exists():
        raise HTTPException(status_code=500, detail="Studio directory not found")

    port = payload.port or 3002
    studio_url = f"http://127.0.0.1:{port}/#project/_HyperFrames_Studio"

    # 1. Check if background preview server is already responding
    is_running = False
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}")
        with urllib.request.urlopen(req, timeout=1) as resp:
            if resp.status == 200:
                is_running = True
    except Exception:
        is_running = False

    # 2. If not running, start it in background
    if not is_running:
        npx_cmd = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
        try:
            subprocess.Popen(
                [npx_cmd, "--yes", "hyperframes@0.8.143", "preview", "--background", f"--port={port}"],
                cwd=STUDIO_DIR,
                shell=(sys.platform == "win32"),
            )
        except Exception as e:
            logger.warning("Failed to start preview process via npx: %s", e)

    # 3. Trigger OS default browser
    try:
        webbrowser.open(studio_url)
    except Exception as e:
        logger.warning("webbrowser.open failed: %s", e)

    return {
        "status": "started",
        "url": studio_url,
        "message": f"Opening HyperFrames Studio at {studio_url}",
    }
