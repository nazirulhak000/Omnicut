"""
API Router for AI Producer Hub — Idea & Ref Vault
Provides:
- POST /api/producer/ai-idea-to-angle: AI-powered synthesis of references/links into actionable video angles
- POST /api/producer/upload-ref-media: Upload reference screenshot/photo
- GET /api/producer/ref-media/{filename}: Serve reference media files
"""

import os
import re
import uuid
import base64
import json
import hashlib
import datetime
import ipaddress
import socket
import urllib.parse
from urllib.parse import urlparse
import threading
from functools import wraps
from datetime import timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from scripts.channel_scope import ChannelScope, get_channel_scope, require_writable
from scripts.channel_store import ChannelError
from scripts.channel_workflows import api_store_kwargs
from scripts.channel_ownership import reject_foreign_body_channel
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from scripts.config import ASSETS_DIR, BASE_DIR
from scripts.product_store import ProductStore
from scripts.tts_sanitizer import TTSSanitizer

router = APIRouter(prefix="/api/producer", tags=["Producer"])

REFS_DIR = ASSETS_DIR / "Refs"
REFS_DIR.mkdir(parents=True, exist_ok=True)
NOTES_FILE = REFS_DIR / "playbook_notes.json"
MAX_REF_MEDIA_BYTES = 10 * 1024 * 1024
REF_MEDIA_NAME_RE = re.compile(r"^ref_[0-9a-f]{12}\.(?:jpg|jpeg|png|webp|gif|mp4|mov|heic|heif)$", re.IGNORECASE)
MAX_NOTE_TEXT_LENGTH = 12000
MAX_NOTE_IMAGES = 12
_NOTES_LOCK = threading.RLock()


def _channel_id(scope):
    return scope.channel_id if isinstance(scope, ChannelScope) else "main"


def _notes_path(channel_id):
    return NOTES_FILE if channel_id == "main" else BASE_DIR / "_Docs" / "producer" / channel_id / "playbook_notes.json"


def _refs_root(scope):
    return REFS_DIR if _channel_id(scope) == "main" else BASE_DIR / "_Docs" / "producer" / _channel_id(scope) / "Refs"


def _notes_transaction(fn):
    @wraps(fn)
    def locked(*args, **kwargs):
        with _NOTES_LOCK:
            return fn(*args, **kwargs)
    return locked


def _guard_write(scope):
    if isinstance(scope, ChannelScope):
        require_writable(scope)


DEFAULT_STARTER_NOTES = [
    {
        "id": "note-starter-1",
        "text": "ฮุกเปิดคลิปอย่าเกริ่นเวิ่นเว้อ 0.5 วินาทีแรกต้องมีภาพสินค้าและปัญหากระแทกตาคนดูทันที",
        "createdAt": "2026-09-12T10:00:00.000Z",
        "tag": "Hook",
        "images": [],
    },
    {
        "id": "note-starter-2",
        "text": "คลิปรีวิวอุปกรณ์อิเล็กทรอนิกส์ คนดูชอบฟังเสียงคลิกปุ่ม / เสียงพัดลมจริง อย่าลืมเปิดเสียง SFX ให้ชัด",
        "createdAt": "2026-09-12T14:30:00.000Z",
        "tag": "Audio",
        "images": [],
    },
]


def sort_notes(notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        notes,
        key=lambda n: (1 if n.get("isPinned") else 0, n.get("createdAt") or ""),
        reverse=True,
    )


def load_notes_from_disk(channel_id="main") -> List[Dict[str, Any]]:
    if not _notes_path(channel_id).exists():
        return sort_notes(list(DEFAULT_STARTER_NOTES))
    try:
        with open(_notes_path(channel_id), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for note in data:
                    if "images" not in note:
                        if note.get("imageUrl"):
                            note["images"] = [note["imageUrl"]]
                        else:
                            note["images"] = []
                    elif note["images"] and not note.get("imageUrl"):
                        note["imageUrl"] = note["images"][0]
                return sort_notes(data)
    except Exception:
        pass
    return sort_notes(list(DEFAULT_STARTER_NOTES))


def save_notes_to_disk(notes: List[Dict[str, Any]], channel_id="main") -> None:
    _notes_path(channel_id).parent.mkdir(parents=True, exist_ok=True)
    sorted_notes = sort_notes(notes)
    temp_file = _notes_path(channel_id).with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(sorted_notes, f, ensure_ascii=False, indent=2)
    temp_file.replace(_notes_path(channel_id))


def notes_revision(notes: List[Dict[str, Any]]) -> str:
    canonical = json.dumps(notes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def normalize_note(note: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(note, dict):
        raise HTTPException(status_code=400, detail="รูปแบบโน้ตไม่ถูกต้อง")
    normalized = dict(note)
    text = normalized.get("text") or ""
    if not isinstance(text, str) or len(text) > MAX_NOTE_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"ข้อความโน้ตยาวเกิน {MAX_NOTE_TEXT_LENGTH:,} ตัวอักษร")
    normalized["text"] = text
    images = normalized.get("images")
    if images is None:
        images = [normalized["imageUrl"]] if normalized.get("imageUrl") else []
    if not isinstance(images, list) or len(images) > MAX_NOTE_IMAGES:
        raise HTTPException(status_code=400, detail=f"แนบรูปได้ไม่เกิน {MAX_NOTE_IMAGES} รูปต่อโน้ต")
    if any(not isinstance(image, str) for image in images):
        raise HTTPException(status_code=400, detail="ลิงก์รูปภาพในโน้ตไม่ถูกต้อง")
    if any(image.startswith("data:") and len(image) > 2_000_000 for image in images):
        raise HTTPException(status_code=400, detail="รูปภาพยังอัปโหลดไม่เสร็จ กรุณารอแล้วลองบันทึกใหม่")
    normalized["images"] = images
    if images and not normalized.get("imageUrl"):
        normalized["imageUrl"] = images[0]
    return normalized


def notes_response(notes: List[Dict[str, Any]]) -> Dict[str, Any]:
    sorted_notes = sort_notes(notes)
    return {
        "success": True,
        "notes": sorted_notes,
        "revision": notes_revision(sorted_notes),
        "updatedAt": datetime.datetime.now(timezone.utc).isoformat(),
    }


class IdeaToAngleRequest(BaseModel):
    idea_text: str = ""
    ref_url: Optional[str] = ""
    ref_image: Optional[str] = ""
    ref_images: Optional[List[str]] = None
    product_id: Optional[str] = None


class NotesPayload(BaseModel):
    notes: List[Dict[str, Any]]
    base_revision: Optional[str] = None


class SingleNotePayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    note: Optional[Dict[str, Any]] = None


class UpdateNotePayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    text: Optional[str] = None
    tag: Optional[str] = None
    productName: Optional[str] = None
    productCode: Optional[str] = None
    url: Optional[str] = None
    images: Optional[List[str]] = None
    imageUrl: Optional[str] = None
    isPinned: Optional[bool] = None
    isFavorite: Optional[bool] = None
    base_revision: Optional[str] = None


@router.post("/upload-ref-media")
async def upload_ref_media(file: UploadFile = File(...), scope: ChannelScope = Depends(get_channel_scope)):
    """Upload a screenshot or photo reference from mobile or desktop."""
    _guard_write(scope)
    if not file.filename:
        raise HTTPException(status_code=400, detail="ไม่พบชื่อไฟล์")

    ext = Path(file.filename).suffix.lower()
    if not ext and file.content_type:
        content_type_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/heic": ".heic",
            "image/heif": ".heif",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
        }
        ext = content_type_map.get(file.content_type.lower(), ".png")

    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".heic", ".heif"]:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ภาพ (.jpg, .png, .webp, .heic) หรือวิดีโอสั้น")

    safe_name = f"ref_{uuid.uuid4().hex[:12]}{ext}"
    root = _refs_root(scope)
    root.mkdir(parents=True, exist_ok=True)
    dest_path = root / safe_name

    contents = await file.read()
    if len(contents) > MAX_REF_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="ไฟล์เรฟใหญ่เกิน 10 MB")
    with open(dest_path, "wb") as f:
        f.write(contents)

    # If iPhone HEIC/HEIF, convert to JPG with ffmpeg so browsers can render immediately
    if ext in [".heic", ".heif"]:
        jpg_name = f"{dest_path.stem}.jpg"
        jpg_path = root / jpg_name
        try:
            import subprocess
            res = subprocess.run(
                ["ffmpeg", "-y", "-i", str(dest_path), str(jpg_path)],
                capture_output=True,
                timeout=10,
            )
            if res.returncode == 0 and jpg_path.exists():
                safe_name = jpg_name
                dest_path = jpg_path
        except Exception:
            pass

    return {
        "success": True,
        "filename": safe_name,
        "url": f"/api/producer/ref-media/{safe_name}" + (f"?channel={_channel_id(scope)}" if isinstance(scope, ChannelScope) and not scope.is_implicit_default else ""),
        "sizeBytes": len(contents),
    }


@router.get("/ref-media/{filename}")
def get_ref_media(filename: str, scope: ChannelScope = Depends(get_channel_scope)):
    """Serve uploaded reference media."""
    safe_name = Path(filename).name
    refs_root = _refs_root(scope).resolve()
    file_path = (refs_root / safe_name).resolve()
    if safe_name != filename or not REF_MEDIA_NAME_RE.fullmatch(safe_name) or file_path.parent != refs_root or not file_path.is_file():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์สื่อเรฟ")
    return FileResponse(file_path)


@router.get("/notes")
@_notes_transaction
def get_notes(scope: ChannelScope = Depends(get_channel_scope)):
    """Get all saved idea and ref notes from server."""
    return notes_response(load_notes_from_disk(_channel_id(scope)))


@router.post("/notes")
@_notes_transaction
def save_notes(payload: NotesPayload, scope: ChannelScope = Depends(get_channel_scope)):
    """Save/overwrite full list of notes."""
    _guard_write(scope)
    current = load_notes_from_disk(_channel_id(scope))
    current_revision = notes_revision(current)
    if payload.base_revision and payload.base_revision != current_revision:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "ข้อมูลโน้ตถูกแก้จากอีกอุปกรณ์แล้ว กรุณาซิงก์ใหม่ก่อนบันทึก",
                "revision": current_revision,
                "notes": current,
            },
        )
    for note in payload.notes:
        reject_foreign_body_channel(note, _channel_id(scope))
    notes = [normalize_note(note) for note in payload.notes]
    save_notes_to_disk(notes, _channel_id(scope))
    return notes_response(notes)


@router.post("/notes/add")
@_notes_transaction
def add_note(payload: SingleNotePayload, scope: ChannelScope = Depends(get_channel_scope)):
    """Add a single note to the server."""
    _guard_write(scope)
    if payload.note is not None:
        note = dict(payload.note)
    else:
        note = payload.model_dump(exclude_unset=True)
    if "note" in note and isinstance(note["note"], dict):
        note = note["note"]

    reject_foreign_body_channel(note, _channel_id(scope))
    note = normalize_note(note)

    if "id" not in note or not note["id"]:
        note["id"] = f"note-{uuid.uuid4().hex[:8]}"
    if "createdAt" not in note or not note["createdAt"]:
        note["createdAt"] = datetime.datetime.now(timezone.utc).isoformat()

    existing = load_notes_from_disk(_channel_id(scope))
    updated = [note] + [n for n in existing if n.get("id") != note.get("id")]
    save_notes_to_disk(updated, _channel_id(scope))
    return {**notes_response(updated), "note": note}


@router.delete("/notes/{note_id}")
@_notes_transaction
def delete_note(note_id: str, scope: ChannelScope = Depends(get_channel_scope)):
    """Delete a note by ID."""
    _guard_write(scope)
    existing = load_notes_from_disk(_channel_id(scope))
    updated = [n for n in existing if n.get("id") != note_id]
    save_notes_to_disk(updated, _channel_id(scope))
    return notes_response(updated)


@router.put("/notes/{note_id}")
@_notes_transaction
def update_note(note_id: str, payload: UpdateNotePayload, scope: ChannelScope = Depends(get_channel_scope)):
    """Update an existing note (text, tag, product, images, isPinned, isFavorite, etc.)."""
    _guard_write(scope)
    existing = load_notes_from_disk(_channel_id(scope))
    current_rev = notes_revision(existing)

    if payload.base_revision and payload.base_revision != current_rev:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "ข้อมูลถูกแก้ไขจากเครื่องอื่น กรุณารีเฟรชแล้วลองใหม่อีกครั้ง",
                "revision": current_rev,
                "notes": existing,
            },
        )

    target_idx = next((i for i, n in enumerate(existing) if n.get("id") == note_id), None)
    if target_idx is None:
        raise HTTPException(status_code=404, detail=f"ไม่พบโน้ต id: {note_id}")

    target = dict(existing[target_idx])
    patch = payload.model_dump(exclude_unset=True)
    patch.pop("base_revision", None)

    target.update(patch)
    target["updatedAt"] = datetime.datetime.now(timezone.utc).isoformat()
    target = normalize_note(target)

    existing[target_idx] = target
    save_notes_to_disk(existing, _channel_id(scope))
    return {**notes_response(existing), "note": target}


def _resolve_image_bytes(img_ref: str, scope=None) -> Optional[tuple[bytes, str]]:
    """Resolve an image reference (file name, URL, local path, or base64 data URL) into (bytes, mime_type)."""
    if not img_ref or not isinstance(img_ref, str):
        return None
    raw = img_ref.strip()
    if not raw:
        return None

    # Case 1: Data URL (e.g. pasted directly before upload)
    if raw.startswith("data:image/"):
        try:
            header, encoded = raw.split(",", 1)
            mime = "image/jpeg"
            m = re.search(r"data:(image/[a-zA-Z0-9\+\-\.]+);", header)
            if m:
                mime = m.group(1).lower()
            data = base64.b64decode(encoded)
            if not data or len(data) > MAX_REF_MEDIA_BYTES:
                return None
            return data, mime
        except Exception:
            return None

    # Case 2: Remote URL.  Producer requests may be reachable from a LAN, so
    # never let an arbitrary URL probe loopback/private/link-local services.
    if raw.lower().startswith(("http://", "https://")):
        try:
            import urllib.request
            parsed = urllib.parse.urlparse(raw)
            hostname = parsed.hostname
            if not hostname or parsed.username or parsed.password:
                return None
            addresses = {
                addr[4][0]
                for addr in socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
            }
            if not addresses or any(
                (ip := ipaddress.ip_address(address)).is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_unspecified
                or ip.is_reserved
                or ip.is_multicast
                for address in addresses
            ):
                return None

            class _NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            req = urllib.request.Request(raw, headers={"User-Agent": "OmniCutPro/1.0"})
            opener = urllib.request.build_opener(_NoRedirect)
            with opener.open(req, timeout=5) as resp:
                data = resp.read(MAX_REF_MEDIA_BYTES + 1)
                if len(data) > MAX_REF_MEDIA_BYTES:
                    return None
                content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
                if not content_type.startswith("image/"):
                    return None
                mime = content_type
                return data, mime
        except Exception:
            return None

    # Case 3: Local file.  Only uploaded refs and the configured assets root
    # are readable; arbitrary absolute paths would disclose host files.
    filename = Path(urlparse(raw).path).name
    candidate_paths = [
        _refs_root(scope) / filename,
        ASSETS_DIR / raw,
    ]
    allowed_roots = [_refs_root(scope).resolve(), ASSETS_DIR.resolve()]
    for p in candidate_paths:
        try:
            resolved = p.resolve()
            if _channel_id(scope) != "main" and REFS_DIR.resolve() in resolved.parents:
                continue
            if not any(resolved == root or root in resolved.parents for root in allowed_roots):
                continue
            if resolved.is_file() and 0 < resolved.stat().st_size <= MAX_REF_MEDIA_BYTES:
                ext = resolved.suffix.lower().lstrip(".")
                mime = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                    "heic": "image/heic",
                    "heif": "image/heif",
                    "gif": "image/gif",
                }.get(ext, "image/jpeg")
                return resolved.read_bytes(), mime
        except Exception:
            continue

    return None


def _generate_angle_with_gemini(
    idea: str,
    url: str,
    product: Optional[Dict[str, Any]],
    resolved_images: List[tuple[bytes, str]],
) -> Optional[Dict[str, Any]]:
    """Synthesize angle proposal via Gemini 2.5 Flash Multimodal Vision."""
    # Pre-flight budget check
    try:
        from scripts.quota import check_budget
        check_budget(task="idea_to_angle")
    except Exception as q_err:
        print(f"[ProducerAI] Quota check note: {q_err}")
        return None

    # Collect configured API keys
    try:
        from scripts.ai_bridge import AIBridge
        api_keys = AIBridge.get_api_keys()
    except Exception:
        api_keys = []
    if not api_keys:
        fallback_k = os.environ.get("GEMINI_API_KEY", "").strip()
        if fallback_k:
            api_keys = [fallback_k]
    if not api_keys:
        return None

    product_name = (product.get("name") or product.get("title") or "สินค้าแนะนำ") if product else "สินค้าแนะนำ"
    brand = product.get("brand", "") if product else ""
    product_desc = product.get("description", "") if product else ""
    selling_points = (product.get("selling_points") or []) if product else []
    pain_points = (product.get("pain_points") or []) if product else []

    system_prompt = f"""คุณเป็น Creative Director & Video Strategist มืออาชีพระดับท็อปสำหรับ TikTok 9:16 (Short-form Video)
หน้าที่ของคุณคือวิเคราะห์ข้อมูลสินค้า, บันทึกไอเดียของผู้ใช้, ลิงก์อ้างอิง และภาพถ่าย/ภาพแคปหน้าจอที่แนบมา (เช่น แคปหน้าจอคลิปไวรัลใน TikTok, มุมกล้องตัวอย่าง, รูปสินค้าจริง)
จากนั้นสังเคราะห์ข้อเสนอมุมมองวิดีโอ (Video Angle) ที่ดึงดูดสายตาภายใน 0-3 วินาทีแรก และกระตุ้นยอดขายได้อย่างมีพลัง

ข้อมูลสินค้าเป้าหมาย:
- ชื่อสินค้า: {product_name}
- แบรนด์: {brand or '-'}
- รายละเอียด: {product_desc or '-'}
- จุดขายเด่น: {', '.join(selling_points) if selling_points else '-'}
- ปัญหาที่ช่วยแก้ (Pain Points): {', '.join(pain_points) if pain_points else '-'}

ไอเดีย / บันทึกของผู้ใช้:
{idea or '(ไม่มีข้อความระบุ ให้วิเคราะห์จากภาพเรฟเป็นหลัก)'}
{f'ลิงก์อ้างอิง: {url}' if url else ''}

แนวทางการวิเคราะห์ภาพเรฟ:
- หากเป็นภาพแคปหน้าจอ TikTok: ตรวจจับรูปแบบ Hook ที่ใช้, ตัวหนังสือพาดหัว, การแสดงอารมณ์, หรือการเปิดคลิป
- หากเป็นภาพสินค้า: ตรวจจับจุดเด่นของดีไซน์, พื้นผิว, มุมกล้องที่ดูสวยงาม (เช่น Macro shot, Hand-held demo)
- นำสิ่งที่เห็นในภาพมาระบุไว้ใน 'visual_insights' และนำไปปรับใช้ในแผนถ่ายทำ 'shoot_angle_brief'

กฎสำคัญของโปรเจกต์:
1. ห้ามใส่เครื่องหมายจุดไข่ปลา '...' หรือ '…' ในบทพูดหรือฮุกเด็ดขาด (ใช้การเว้นวรรคธรรมชาติ)
2. ห้ามทับศัพท์ชื่อแบรนด์/รุ่น/คำเทคนิคภาษาอังกฤษเป็นไทย ให้คงภาษาอังกฤษไว้ (เช่น Bluetooth, USB-C)
3. สเปกวิดีโอคือ 9:16 ความยาวประมาณ 30 วินาที
4. ห้ามพูด/เขียนถึงราคา ตัวเลขเงิน ส่วนลด โปรโมชั่น คูปอง ส่งฟรี หรือการเดาราคาในฮุก บทพูด และแคปชั่นเด็ดขาด (ผิดกฎ TikTok) ใช้ CTA กลางๆ เช่น "กดตะกร้าดูรายละเอียดได้เลยครับ"

โปรดตอบกลับเป็น JSON ภาษาไทย ตามโครงสร้างนี้เท่านั้น ห้ามมีคำอธิบายอื่นนอก JSON:
{{
  "angle_name": "ชื่อมุมมองสั้น กระชับ ชัดเจน (เช่น มุมเตือนภัยจากภาพเรฟ, มุมเทียบก่อน-หลังใช้)",
  "visual_insights": "สรุปสิ่งที่ตรวจพบจากภาพเรฟ 1-2 ประโยค (เช่น พบการซูมใกล้โชว์ตัวเครื่อง และตัวหนังสือพาดหัวเตือนภัยสีเหลืองชัดเจน)",
  "hook_title": "ประโยคฮุกเปิดคลิป 0-3 วินาทีแรกที่สะกดคนดูทันที (ห้ามมีจุดไข่ปลา)",
  "target_audience": "กลุ่มเป้าหมายที่ตรงกับคลิปนี้",
  "pain_point": "ปัญหาหลักที่คลิปนี้เน้นขยี้",
  "shoot_angle_brief": "แผนถ่ายทำ 3 สเต็ป (1. 0-3 วิแรก... 2. 3-15 วิ... 3. 15-30 วิ...) โดยดึงมุมภาพจากเรฟมาใช้",
  "script_brief": "บทพากย์ย่อสำหรับคลิป 30 วิ (ประมาณ 3-4 ประโยคกระชับ ได้จังหวะ TTS ที่ดี)",
  "duration": "30s"
}}"""

    try:
        from google import genai
        from google.genai import types
        import time

        image_parts = []
        for img_bytes, mime_type in resolved_images:
            try:
                image_parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
            except Exception as part_err:
                print(f"[ProducerAI] Error creating Part: {part_err}")

        contents = [system_prompt, *image_parts] if image_parts else [system_prompt]

        for key in api_keys:
            client = genai.Client(api_key=key)
            for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite"]:
                try:
                    t0 = time.time()
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                    )
                    if resp and resp.text:
                        raw_text = resp.text.strip()
                        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
                        clean_json = m.group(1).strip() if m else raw_text
                        parsed = json.loads(clean_json)
                        if isinstance(parsed, dict) and "hook_title" in parsed:
                            # Token tracking
                            try:
                                from scripts.token_tracker import TokenTracker
                                in_tok = max(100, len(system_prompt) // 2) + (len(image_parts) * 258)
                                out_tok = max(50, len(raw_text) // 2)
                                TokenTracker.record_event(
                                    task="idea_to_angle",
                                    model=model_name,
                                    provider="google_ai_studio",
                                    input_tokens=in_tok,
                                    output_tokens=out_tok,
                                    latency_seconds=time.time() - t0,
                                    project_name=product_name,
                                )
                            except Exception:
                                pass
                            return parsed
                except Exception as call_err:
                    print(f"[ProducerAI] Model {model_name} note: {call_err}")
                    continue
    except Exception as sdk_err:
        print(f"[ProducerAI] GenAI SDK note: {sdk_err}")

    return None


@router.post("/ai-idea-to-angle")
def ai_idea_to_angle(req: IdeaToAngleRequest, scope: ChannelScope = Depends(get_channel_scope)):
    """Synthesize an idea/link/screenshot into a high-converting TikTok video angle proposal using Gemini Vision."""
    idea = (req.idea_text or "").strip()
    url = (req.ref_url or "").strip()
    product_id = req.product_id

    product = None
    product_name = "สินค้าแนะนำ"
    product_desc = ""
    selling_points = []
    pain_points = []
    brand = ""

    if product_id:
        product = ProductStore.get(product_id, **(api_store_kwargs(scope) if isinstance(scope, ChannelScope) else {}))
        if not product and isinstance(scope, ChannelScope):
            raise ChannelError(404, "resource_not_found", "ไม่พบสินค้าที่ร้องขอ")
        if product:
            product_name = product.get("name") or product.get("title") or product_name
            product_desc = product.get("description") or ""
            selling_points = product.get("selling_points") or []
            pain_points = product.get("pain_points") or []
            brand = product.get("brand") or ""

    # Resolve attached reference images (max 3 for token & latency efficiency)
    raw_images: List[str] = []
    if req.ref_images:
        raw_images.extend([img for img in req.ref_images if img])
    if req.ref_image and req.ref_image not in raw_images:
        raw_images.insert(0, req.ref_image)

    resolved_images: List[tuple[bytes, str]] = []
    for img_ref in raw_images:
        if len(resolved_images) >= 3:
            break
        res_img = _resolve_image_bytes(img_ref, scope)
        if res_img:
            resolved_images.append(res_img)

    # 1. Try Multimodal Gemini Vision Synthesis
    gemini_result = _generate_angle_with_gemini(
        idea=idea,
        url=url,
        product=product,
        resolved_images=resolved_images,
    )

    if gemini_result:
        raw_hook = gemini_result.get("hook_title") or f"⚡ ถ้าคุณกำลังเจอปัญหานี้ {product_name} จบได้ในตัวเดียว!"
        clean_hook = TTSSanitizer.clean_display_text(raw_hook)
        raw_script = gemini_result.get("script_brief") or ""
        clean_script = TTSSanitizer.clean_display_text(raw_script) if raw_script else (
            f"{clean_hook} ใครเจอปัญหานี้ตัวนี้ช่วยได้ทันทีครับ พิกัดในตะกร้าด้านล่างได้เลยครับ"
        )
        shoot_brief = gemini_result.get("shoot_angle_brief") or (
            f"1. 0–3 วิ: วางสินค้า {product_name} โชว์ฮุกสะดุดตา\n"
            f"2. 3–15 วิ: ซูมอินสาธิตการใช้งานจริง\n"
            f"3. 15–30 วิ: ชี้พิกัดตะกร้าพร้อมปิดการขาย"
        )
        visual_insights = gemini_result.get("visual_insights") or (
            f"วิเคราะห์จากภาพเรฟ {len(resolved_images)} ภาพ โดย Gemini 2.5 Flash Vision" if resolved_images else ""
        )

        proposal = {
            "angle_name": gemini_result.get("angle_name") or f"มุมมองแนะนำ: {idea[:24] if idea else product_name}",
            "visual_insights": visual_insights,
            "hook_title": clean_hook,
            "hook": clean_hook,
            "target_audience": gemini_result.get("target_audience") or "กลุ่มลูกค้าที่มองหาของแท้ คุ้มค่า แก้ปัญหาได้ตรงจุด",
            "pain_point": gemini_result.get("pain_point") or (pain_points[0] if pain_points else "ปัญหาที่คนเจอบ่อย"),
            "shoot_angle_brief": shoot_brief,
            "shoot_brief": shoot_brief,
            "script_brief": clean_script,
            "script": clean_script,
            "duration": gemini_result.get("duration") or "30s",
            "product_id": product_id,
            "product_name": product_name,
            "ref_url": url,
        }

        return {
            "success": True,
            "analysis": {
                "method": "gemini_vision" if resolved_images else "gemini_flash",
                "source": "gemini_multimodal",
                "used_ref_url": bool(url),
                "used_ref_images": bool(resolved_images),
                "image_count": len(resolved_images),
                "confidence": "high",
            },
            "proposal": proposal,
        }

    # 2. Heuristic Rule-Based Fallback (Offline / No Key / Fallback)
    is_warning = any(w in idea.lower() for w in ["หยุด", "ระวัง", "อย่า", "เตือน", "พัง", "ห้าม"])
    is_curiosity = any(w in idea.lower() for w in ["ทำไม", "ความลับ", "ใครจะรู้", "เพิ่งรู้", "จริงไหม"])
    is_deal = any(w in idea.lower() for w in ["คุ้ม", "ลด", "ราคา", "โปร", "แจก", "ถูก"])

    if is_warning:
        angle_name = "มุมเตือนภัยแก้ปัญหาด่วน"
        hook_title = f"⚠️ อย่าเพิ่งใช้ {product_name} ถ้ายังไม่รู้สิ่งนี้เด็ดขาด!"
        core_pain = pain_points[0] if pain_points else "ปัญหาที่คนเจอบ่อยและทำให้หงุดหงิด"
    elif is_curiosity:
        angle_name = "มุมเปิดความลับ / ของมันต้องมี"
        hook_title = f"💡 ความลับที่คนใช้ {product_name} ไม่ค่อยบอกใครแต่ยอดขายถล่มทลาย!"
        core_pain = pain_points[0] if pain_points else "วิธีแก้ปัญหาที่ง่ายกว่าที่คิด"
    elif is_deal:
        # Deal-flavoured ideas still never put price/promo into the clip.
        angle_name = "มุมของมันต้องมี / ห้ามพลาด"
        hook_title = f"🔥 ของมันต้องมี! {product_name} ตัวนี้ใช้แล้วติดใจ"
        core_pain = "อยากได้ของดีมีคุณภาพที่ใช้ได้นาน"
    else:
        angle_name = f"มุมรีวิวจากไอเดีย: {idea[:24]}" if idea else f"มุมรีวิวเจาะลึก {product_name}"
        hook_title = f"⚡ ถ้าคุณกำลังเจอปัญหานี้ {product_name} จบได้ในตัวเดียว!"
        core_pain = pain_points[0] if pain_points else "มองหาตัวช่วยที่ตอบโจทย์และคุ้มค่า"

    clean_hook = TTSSanitizer.clean_display_text(hook_title)

    shoot_brief = (
        f"1. 0–3 วิแรก: วางสินค้า {product_name} กึ่งกลางจอ พร้อมแสดงสีหน้าหรือท่าทางตกใจตามฮุก\n"
        f"2. 3–15 วิ: ซูมอินให้เห็นจุดเด่นสินค้าชัดๆ สาธิตการใช้งานแก้ปัญหา {core_pain}\n"
        f"3. 15–30 วิ: ถือสินค้าโชว์มุมสวย พร้อมชี้ไปที่ตะกร้าเหลืองด้านล่างซ้าย"
    )

    feature_text = selling_points[0] if selling_points else "ดีไซน์ทันสมัย ใช้งานสะดวก ทนทาน"
    script_lines = [
        clean_hook,
        f"ใครที่มีปัญหา {core_pain} ต้องดูคลิปนี้ให้จบครับ",
        f"ตัวนี้คือ {product_name} {feature_text} แค่กดใช้งานปุ๊บก็พร้อมลุยทันที",
        "สนใจกดตะกร้าเหลืองมุมซ้ายล่าง ดูรายละเอียดได้เลยครับ",
    ]
    script_brief = " ".join(script_lines)
    clean_script = TTSSanitizer.clean_display_text(script_brief)

    visual_insights = (
        f"ตรวจพบภาพเรฟ {len(resolved_images)} ภาพ (สังเคราะห์มุมมองด้วย Heuristic Rule-based Engine)"
        if resolved_images
        else "สังเคราะห์มุมมองจากคีย์เวิร์ดและข้อมูลสินค้า (Heuristic Rule-based Engine)"
    )

    proposal = {
        "angle_name": angle_name,
        "visual_insights": visual_insights,
        "hook_title": clean_hook,
        "hook": clean_hook,
        "target_audience": "กลุ่มลูกค้าที่มองหาของแท้ คุ้มค่า แก้ปัญหาได้ตรงจุด",
        "pain_point": core_pain,
        "shoot_angle_brief": shoot_brief,
        "shoot_brief": shoot_brief,
        "script_brief": clean_script,
        "script": clean_script,
        "duration": "30s",
        "product_id": product_id,
        "product_name": product_name,
        "ref_url": url,
    }

    return {
        "success": True,
        "analysis": {
            "method": "heuristic_fallback",
            "source": "idea_text_and_product_catalog",
            "used_ref_url": bool(url),
            "used_ref_images": bool(resolved_images),
            "image_count": len(resolved_images),
            "confidence": "medium" if resolved_images else "low",
        },
        "proposal": proposal,
    }
