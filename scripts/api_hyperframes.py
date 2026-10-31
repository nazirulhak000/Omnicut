"""
API Router for HyperFrames Creative Studio.
Manages programmatic video compositions, approved viral styles, headless Chrome rendering,
and automated export registry synchronization.
"""

from __future__ import annotations

import asyncio
import hashlib
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
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Depends
from starlette.exceptions import HTTPException
from pydantic import BaseModel, Field

from scripts.config import BASE_DIR, EXPORTS_DIR, SOURCE_ROOT
from scripts.export_registry import ExportRegistry
from scripts.hyperframes_finalize import hyperframes_style_metadata
from scripts.product_store import ProductStore
from scripts import path_utils
from scripts.channel_scope import ChannelScope, ensure_same_channel, require_active_for_new_work, require_final_ready
from scripts.channel_store import ChannelError, MAIN_SEED
from scripts.channel_workflows import get_workflow_scope, capture_job_scope, require_media_owner, require_record_owner, require_project_owner
from scripts.channel_identity import resolve_channel_identity, require_identity_avatar

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
    channel_id: Optional[str] = None
    product_id: Optional[str] = None
    angle_id: Optional[str] = None
    project_name: Optional[str] = None


class RenderCompositionRequest(BaseModel):
    composition_id: str = Field(..., description="Stem of composition file, e.g. hat01-meme-45s")
    output_filename: Optional[str] = Field(None, description="Custom export filename (optional)")
    product_id: Optional[str] = Field(None, description="Linked product ID (e.g. HAT01)")
    angle_id: Optional[str] = Field(None, description="Linked angle ID")
    is_test: bool = Field(False, description="If True, renders to .tmp/ instead of 04_Exports/")
    channel_id: Optional[str] = None


class OpenStudioRequest(BaseModel):
    port: int = Field(3002, description="Port for HyperFrames Studio web preview")


# ── Helper Functions ──

def _find_python() -> str:
    venv_py = SOURCE_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)
    return "python"


def _effective_scope(value) -> ChannelScope:
    return value if isinstance(value, ChannelScope) else ChannelScope("main", "default", False, channel=MAIN_SEED)


def _safe_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ChannelError(422, "composition_id_invalid", "ชื่อ composition ไม่ถูกต้อง")
    return value


def _embedded_json(content: str, node_id: str):
    matches = re.findall(r'<script\b[^>]*\bid=["\']' + re.escape(node_id) + r'["\'][^>]*>(.*?)</script\s*>', content, re.I | re.S)
    if len(matches) > 1:
        raise ChannelError(422, "composition_metadata_invalid", "metadata composition ซ้ำ")
    if not matches:
        return None
    try:
        result = json.loads(matches[0])
    except (TypeError, ValueError) as exc:
        raise ChannelError(422, "composition_metadata_invalid", "metadata composition ไม่ถูกต้อง") from exc
    if not isinstance(result, dict):
        raise ChannelError(422, "composition_metadata_invalid", "metadata composition ไม่ถูกต้อง")
    return result


def _composition_scope(html_path: Path, scope: ChannelScope) -> dict:
    content = html_path.read_text(encoding="utf-8")
    metadata = _embedded_json(content, "omnicut-composition-metadata")
    identity = _embedded_json(content, "omnicut-channel-identity")
    declared = re.search(r'\bdata-channel=["\']([^"\']+)["\']', content)
    declared_id = declared.group(1) if declared else "main"
    owner = (metadata or {}).get("channel_id", declared_id)
    ensure_same_channel(scope, owner, resource_label="composition", allow_legacy_main=not scope.strict)
    if declared_id != owner:
        raise ChannelError(422, "channel_scope_conflict", "ช่องใน composition ไม่ตรงกับ metadata")
    if identity is None and (owner != "main" or scope.strict):
        raise ChannelError(422, "channel_identity_missing", "composition ต้องมี identity snapshot")
    snapshot = resolve_channel_identity(identity, channel_id=owner)
    metadata = metadata or {"channel_id": owner}
    if metadata.get("channel_identity_snapshot") is not None:
        prior = resolve_channel_identity(metadata["channel_identity_snapshot"], channel_id=owner)
        if prior != snapshot:
            raise ChannelError(422, "channel_scope_conflict", "identity ของ composition ไม่ตรงกัน")
    for key in ("product_id", "angle_id"):
        if metadata.get(key) and key == "product_id":
            require_record_owner(scope, ProductStore.get(metadata[key], channel_id=owner), resource_label="สินค้า")
    if metadata.get("project_name"):
        require_project_owner(scope, metadata["project_name"])
    return {**metadata, "channel_identity_snapshot": snapshot}


def _freeze_composition(content: str, identity: dict, metadata: dict) -> str:
    avatar = BASE_DIR / identity["avatar_asset_path"]
    if avatar.is_file():
        # Studio serves its own root. Freeze any valid workspace avatar into
        # that root without changing the user's reusable source asset.
        payload = avatar.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if identity.get("avatar_sha256") and digest != identity["avatar_sha256"]:
            raise ChannelError(409, "channel_identity_asset_changed", "รูปโปรไฟล์ของ snapshot เปลี่ยนหรือหายไป")
        cached = STUDIO_DIR / "assets" / "shared" / "channel-identities" / (digest + avatar.suffix.lower())
        cached.parent.mkdir(parents=True, exist_ok=True)
        try:
            with cached.open("xb") as output:
                output.write(payload)
        except FileExistsError:
            if hashlib.sha256(cached.read_bytes()).hexdigest() != digest:
                raise ChannelError(409, "channel_identity_asset_changed", "สำเนารูปโปรไฟล์ของ snapshot ไม่ตรงกัน") from None
        avatar_path = cached.relative_to(STUDIO_DIR).as_posix()
    else:
        # Compatibility main may have no packaged avatar yet. Preserve its
        # existing URL rather than inventing a live profile lookup.
        try:
            avatar_path = avatar.resolve().relative_to(STUDIO_DIR.resolve()).as_posix()
        except ValueError as exc:
            raise ChannelError(422, "channel_identity_avatar_missing", "ไม่พบรูปโปรไฟล์ของ snapshot") from exc
    frozen = {**identity, "hyperframes_avatar_path": avatar_path}
    def script(node_id, value):
        encoded = json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        return f'<script type="application/json" id="{node_id}">{encoded}</script>'
    block = script("omnicut-channel-identity", frozen) + script("omnicut-composition-metadata", metadata)
    if not re.search(r"<head\b[^>]*>", content, re.I):
        raise ChannelError(422, "composition_metadata_invalid", "composition ไม่มี head")
    return re.sub(r"(<head\b[^>]*>)", lambda match: match.group(1) + block, content, count=1, flags=re.I)


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
def list_compositions(scope: ChannelScope = Depends(get_workflow_scope)) -> List[Dict[str, Any]]:
    """List all compositions in HyperFrames Studio with metadata."""
    if not COMPOSITIONS_DIR.exists():
        return []

    comps = []
    scope = _effective_scope(scope)
    for file in sorted(COMPOSITIONS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            provenance = _composition_scope(file, scope)
        except ChannelError as exc:
            if exc.status_code == 404:
                continue
            raise
        comps.append({**_extract_composition_metadata(file), **provenance})
    return comps


@router.post("/create-clip")
def create_clip(payload: CreateClipRequest, scope: ChannelScope = Depends(get_workflow_scope)) -> Dict[str, Any]:
    """Create a new HyperFrames clip draft by invoking kit/new_clip.py."""
    scope = _effective_scope(scope)
    require_active_for_new_work(scope)
    if payload.channel_id is not None and payload.channel_id != scope.channel_id:
        raise ChannelError(422, "channel_scope_conflict", "ช่องของ request ไม่ตรงกัน")
    if payload.product_id:
        product_record = require_record_owner(scope, ProductStore.get(payload.product_id, channel_id=scope.channel_id), resource_label="สินค้า")
        if payload.angle_id and not any((a.get("angle_id") or a.get("id")) == payload.angle_id for a in product_record.get("angles", [])):
            raise ChannelError(404, "channel_resource_not_found", "ไม่พบมุมมองของสินค้า")
    elif payload.angle_id:
        raise ChannelError(422, "composition_parent_missing", "angle ต้องมีสินค้าเจ้าของ")
    clip_id = _safe_id(payload.clip_id)
    product = _safe_id(payload.product).lower()
    pinned = capture_job_scope(scope)
    identity = resolve_channel_identity(pinned["channel_identity_snapshot"], channel_id=scope.channel_id)
    require_identity_avatar(identity, allow_legacy_missing=scope.is_implicit_default and not scope.strict)
    _freeze_composition("<head></head>", identity, {})  # Validate the kit avatar path before invoking generation.
    if not STUDIO_DIR.exists():
        raise HTTPException(status_code=500, detail="HyperFrames Studio directory not found")

    comp_file = COMPOSITIONS_DIR / f"{clip_id}.html"
    if comp_file.exists():
        raise HTTPException(status_code=409, detail=f"Composition '{clip_id}' already exists")

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
        require_media_owner(scope, vo_file, base_dir=BASE_DIR)

    # If no vo provided, look for project VO
    if payload.project_name:
        manifest = require_project_owner(scope, payload.project_name)
        if not vo_file:
            from scripts.project_manifest import ProjectManifest
            vo_file = ProjectManifest.artifact_path(manifest, "voice_audio")
            if vo_file:
                require_media_owner(scope, vo_file, base_dir=BASE_DIR)

    if not vo_file:
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
            cmd = [py_exe, str(KIT_DIR / "new_clip.py"), clip_id, "--product", product, "--channel", scope.channel_id]
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
        finally:
            if script_path:
                script_path.unlink(missing_ok=True)

    metadata = {**pinned, "channel_identity_snapshot": identity, "product_id": payload.product_id,
                "angle_id": payload.angle_id, "project_name": payload.project_name}
    content = comp_file.read_text(encoding="utf-8")
    content = _freeze_composition(content, identity, metadata)
    staged = comp_file.with_suffix(f".html.{uuid.uuid4().hex}.tmp")
    try:
        staged.write_text(content, encoding="utf-8")
        staged.replace(comp_file)
    finally:
        staged.unlink(missing_ok=True)

    return {
        "status": "created",
        "clip_id": clip_id,
        "composition_path": f"compositions/{clip_id}.html",
        **metadata,
        "message": f"Successfully created clip draft '{clip_id}'",
    }


@router.post("/render")
async def render_composition(payload: RenderCompositionRequest, scope: ChannelScope = Depends(get_workflow_scope)) -> Dict[str, Any]:
    """Render a HyperFrames composition into a 9:16 MP4 video via Chrome Headless."""
    scope = _effective_scope(scope)
    require_active_for_new_work(scope)
    if payload.channel_id is not None and payload.channel_id != scope.channel_id:
        raise ChannelError(422, "channel_scope_conflict", "ช่องของ request ไม่ตรงกัน")
    if not payload.is_test and not (scope.is_implicit_default and not scope.strict):
        require_final_ready(scope)
    comp_id = _safe_id(payload.composition_id)
    comp_file = COMPOSITIONS_DIR / f"{comp_id}.html"
    if not comp_file.exists():
        clip_index = CLIPS_DIR / comp_id / "index.html"
        if clip_index.exists():
            comp_file = clip_index
        else:
            raise HTTPException(status_code=404, detail=f"Composition '{comp_id}' not found")
    metadata = _composition_scope(comp_file, scope)
    identity = metadata["channel_identity_snapshot"]
    require_identity_avatar(identity, allow_legacy_missing=scope.is_implicit_default and not scope.strict)
    product_id = metadata.get("product_id") or payload.product_id
    angle_id = metadata.get("angle_id") or payload.angle_id
    if metadata.get("product_id") and payload.product_id and metadata["product_id"] != payload.product_id:
        raise ChannelError(422, "composition_parent_conflict", "สินค้าไม่ตรงกับ composition")
    if metadata.get("angle_id") and payload.angle_id and metadata["angle_id"] != payload.angle_id:
        raise ChannelError(422, "composition_parent_conflict", "มุมมองไม่ตรงกับ composition")
    source_angle = None
    if product_id:
        product = require_record_owner(scope, ProductStore.get(product_id, channel_id=scope.channel_id), resource_label="สินค้า")
        if angle_id and not any((a.get("angle_id") or a.get("id")) == angle_id for a in product.get("angles", [])):
            raise ChannelError(404, "channel_resource_not_found", "ไม่พบมุมมองของสินค้า")
        source_angle = next((a for a in product.get("angles", []) if angle_id and (a.get("angle_id") or a.get("id")) == angle_id), None)
    elif angle_id:
        raise ChannelError(422, "composition_parent_missing", "angle ต้องมีสินค้าเจ้าของ")

    date_str = datetime.now().strftime("%Y%m%d")
    clean_name = payload.output_filename or f"{date_str}_{comp_id}_v1.mp4"
    if not clean_name.endswith(".mp4"):
        clean_name += ".mp4"
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.mp4", clean_name) or clean_name.startswith("."):
        raise ChannelError(422, "export_filename_invalid", "ชื่อไฟล์ส่งออกไม่ถูกต้อง")

    if payload.is_test:
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        out_path = TMP_DIR / scope.channel_id / f"test_{clean_name}"
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        # Standard Ready_to_post destination
        target_dir = EXPORTS_DIR if scope.channel_id == "main" else EXPORTS_DIR / scope.channel_id
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / clean_name

    def _do_render():
        with _RENDER_LOCK:
            version = 2
            target = out_path
            while target.exists():
                target = out_path.with_name(f"{out_path.stem}_v{version}{out_path.suffix}")
                version += 1
            render_file = comp_file
            legacy_clone = None
            content = comp_file.read_text(encoding="utf-8")
            if _embedded_json(content, "omnicut-channel-identity") is None:
                parent_dir = render_file.parent
                legacy_clone = parent_dir / f".{comp_id}.{uuid.uuid4().hex}.render.html"
                legacy_clone.write_text(_freeze_composition(content, identity, metadata), encoding="utf-8")
                render_file = legacy_clone
            
            npx_bin = shutil.which("npx") or ("npx.cmd" if os.name == "nt" else "npx")
            rel_comp = render_file.relative_to(STUDIO_DIR).as_posix()
            cmd = [
                npx_bin, "--yes", "hyperframes@0.8.143", "render",
                "-c", rel_comp,
                "-o", str(target),
            ]
            log_file = TMP_DIR / f"render_{comp_id}.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(log_file, "w", encoding="utf-8") as lf:
                    proc = subprocess.run(cmd, cwd=STUDIO_DIR, stdout=lf,
                                          stderr=subprocess.STDOUT, timeout=300)
            finally:
                if legacy_clone:
                    legacy_clone.unlink(missing_ok=True)

            if proc.returncode != 0 or not target.exists():
                err_text = ""
                try:
                    err_text = log_file.read_text(encoding="utf-8")[-1000:]
                except Exception:
                    pass
                raise RuntimeError(f"Render failed with code {proc.returncode}: {err_text}")

            # Generate thumbnail WebP
            webp_path = target.with_suffix(".webp")
            _extract_video_thumbnail(target, webp_path, seek_sec=1.5)

            # Register into export_registry if final export
            export_id = None
            if not payload.is_test and target.exists():
                rel_path = path_utils.to_relative(target, base_dir=BASE_DIR)
                reg_rows = ExportRegistry.ensure_many([
                    {
                        "path": rel_path,
                        "product_id": product_id,
                        "angle_id": angle_id,
                        "project_name": f"_HyperFrames_Studio/{comp_id}",
                        "status": "rendered",
                        # Hook line / story format from the source angle; no
                        # probe here, so duration is filled later if at all.
                        "style_metadata": hyperframes_style_metadata(source_angle),
                    }
                ], channel_id=scope.channel_id, job_scope={
                    **{key: value for key, value in metadata.items() if key.startswith("channel_")},
                    "channel_identity_snapshot": identity,
                })
                if reg_rows:
                    export_id = reg_rows[0].get("id")

                # Sync status in ProductStore
                if product_id:
                    try:
                        prod = ProductStore.get(product_id, channel_id=scope.channel_id)
                        if prod:
                            for a in prod.get("angles", []):
                                if (a.get("angle_id") or a.get("id")) == angle_id or a.get("clip_id") == comp_id:
                                    a["status"] = "rendered"
                                    a["video_url"] = str(target)
                                    if export_id:
                                        a["export_id"] = export_id
                                    break
                            ProductStore.update(product_id, channel_id=scope.channel_id, angles=prod.get("angles", []))
                    except Exception as store_err:
                        logger.warning("ProductStore update on render: %s", store_err)

            return {
                "output_path": str(target),
                "export_id": export_id,
                "thumbnail_path": str(webp_path) if webp_path.exists() else None,
                "size_bytes": target.stat().st_size,
                "channel_id": scope.channel_id,
                "channel_identity_snapshot": identity,
            }

    try:
        result = await asyncio.to_thread(_do_render)
    except HTTPException:
        raise
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
