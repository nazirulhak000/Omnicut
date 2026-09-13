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
from datetime import timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from scripts.config import ASSETS_DIR
from scripts.product_store import ProductStore
from scripts.tts_sanitizer import TTSSanitizer

router = APIRouter(prefix="/api/producer", tags=["Producer"])

REFS_DIR = ASSETS_DIR / "Refs"
REFS_DIR.mkdir(parents=True, exist_ok=True)
NOTES_FILE = REFS_DIR / "playbook_notes.json"
MAX_REF_MEDIA_BYTES = 10 * 1024 * 1024
MAX_NOTE_TEXT_LENGTH = 12000
MAX_NOTE_IMAGES = 12

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


def load_notes_from_disk() -> List[Dict[str, Any]]:
    if not NOTES_FILE.exists():
        return list(DEFAULT_STARTER_NOTES)
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
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
                return data
    except Exception:
        pass
    return list(DEFAULT_STARTER_NOTES)


def save_notes_to_disk(notes: List[Dict[str, Any]]) -> None:
    temp_file = NOTES_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    temp_file.replace(NOTES_FILE)


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
    return {
        "success": True,
        "notes": notes,
        "revision": notes_revision(notes),
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


@router.post("/upload-ref-media")
async def upload_ref_media(file: UploadFile = File(...)):
    """Upload a screenshot or photo reference from mobile or desktop."""
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
    dest_path = REFS_DIR / safe_name

    contents = await file.read()
    if len(contents) > MAX_REF_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="ไฟล์เรฟใหญ่เกิน 10 MB")
    with open(dest_path, "wb") as f:
        f.write(contents)

    # If iPhone HEIC/HEIF, convert to JPG with ffmpeg so browsers can render immediately
    if ext in [".heic", ".heif"]:
        jpg_name = f"{dest_path.stem}.jpg"
        jpg_path = REFS_DIR / jpg_name
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
        "url": f"/api/producer/ref-media/{safe_name}",
        "sizeBytes": len(contents),
    }


@router.get("/ref-media/{filename}")
def get_ref_media(filename: str):
    """Serve uploaded reference media."""
    safe_name = Path(filename).name
    file_path = REFS_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์สื่อเรฟ")
    return FileResponse(file_path)


@router.get("/notes")
def get_notes():
    """Get all saved idea and ref notes from server."""
    return notes_response(load_notes_from_disk())


@router.post("/notes")
def save_notes(payload: NotesPayload):
    """Save/overwrite full list of notes."""
    current = load_notes_from_disk()
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
    notes = [normalize_note(note) for note in payload.notes]
    save_notes_to_disk(notes)
    return notes_response(notes)


@router.post("/notes/add")
def add_note(payload: SingleNotePayload):
    """Add a single note to the server."""
    if payload.note is not None:
        note = dict(payload.note)
    else:
        note = payload.model_dump(exclude_unset=True)
    if "note" in note and isinstance(note["note"], dict):
        note = note["note"]

    note = normalize_note(note)

    if "id" not in note or not note["id"]:
        note["id"] = f"note-{uuid.uuid4().hex[:8]}"
    if "createdAt" not in note or not note["createdAt"]:
        note["createdAt"] = datetime.datetime.now(timezone.utc).isoformat()

    existing = load_notes_from_disk()
    updated = [note] + [n for n in existing if n.get("id") != note.get("id")]
    save_notes_to_disk(updated)
    return {**notes_response(updated), "note": note}


@router.delete("/notes/{note_id}")
def delete_note(note_id: str):
    """Delete a note by ID."""
    existing = load_notes_from_disk()
    updated = [n for n in existing if n.get("id") != note_id]
    save_notes_to_disk(updated)
    return notes_response(updated)


@router.post("/ai-idea-to-angle")
def ai_idea_to_angle(req: IdeaToAngleRequest):
    """Synthesize an idea/link/screenshot into a high-converting TikTok video angle proposal."""
    idea = (req.idea_text or "").strip()
    url = (req.ref_url or "").strip()
    product_id = req.product_id

    product_name = "สินค้าแนะนำ"
    product_desc = ""
    selling_points = []
    pain_points = []
    brand = ""

    if product_id:
        product = ProductStore.get(product_id)
        if product:
            product_name = product.get("name") or product.get("title") or product_name
            product_desc = product.get("description") or ""
            selling_points = product.get("selling_points") or []
            pain_points = product.get("pain_points") or []
            brand = product.get("brand") or ""

    # Generate synthesized video angle proposal
    # 1. Detect core angle theme from idea/url
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
        angle_name = "มุมป้ายยาโปรเดือดคุ้มสุด"
        hook_title = f"🔥 รีบดูก่อนหมดโปร! {product_name} ตัวนี้ลดราคาเดือดที่สุดในรอบปี!"
        core_pain = "ไม่อยากจ่ายแพงแต่อยากได้ของดีมีคุณภาพ"
    else:
        angle_name = f"มุมรีวิวจากไอเดีย: {idea[:24]}" if idea else f"มุมรีวิวเจาะลึก {product_name}"
        hook_title = f"⚡ ถ้าคุณกำลังเจอปัญหานี้ {product_name} จบได้ในตัวเดียว!"
        core_pain = pain_points[0] if pain_points else "มองหาตัวช่วยที่ตอบโจทย์และคุ้มค่า"

    clean_hook = TTSSanitizer.clean_text(hook_title)

    # Shoot brief guidance based on ref
    shoot_brief = (
        f"1. 0–3 วิแรก: วางสินค้า {product_name} กึ่งกลางจอ พร้อมแสดงสีหน้าหรือท่าทางตกใจตามฮุก\n"
        f"2. 3–15 วิ: ซูมอินให้เห็นจุดเด่นสินค้าชัดๆ สาธิตการใช้งานแก้ปัญหา {core_pain}\n"
        f"3. 15–30 วิ: ถือสินค้าโชว์มุมสวย พร้อมชี้ไปที่ตะกร้าเหลืองด้านล่างซ้าย"
    )

    # Voiceover script brief (3-part pacing)
    feature_text = selling_points[0] if selling_points else "ดีไซน์ทันสมัย ใช้งานสะดวก ทนทานคุ้มราคา"
    script_lines = [
        clean_hook,
        f"ใครที่มีปัญหา {core_pain} ต้องดูคลิปนี้ให้จบครับ",
        f"ตัวนี้คือ {product_name} {feature_text} แค่กดใช้งานปุ๊บก็พร้อมลุยทันที",
        "พิกัดของแท้พร้อมโปรพิเศษ กดที่ตะกร้าเหลืองมุมซ้ายล่างได้เลยครับ",
    ]
    script_brief = " ".join(script_lines)
    clean_script = TTSSanitizer.sanitize_script(script_brief)

    proposal = {
        "angle_name": angle_name,
        "hook_title": clean_hook,
        "target_audience": "กลุ่มลูกค้าที่มองหาของแท้ คุ้มค่า แก้ปัญหาได้ตรงจุด",
        "pain_point": core_pain,
        "shoot_angle_brief": shoot_brief,
        "script_brief": clean_script,
        "duration": "30s",
        "product_id": product_id,
        "product_name": product_name,
        "ref_url": url,
    }

    return {
        "success": True,
        "analysis": {
            "method": "heuristic",
            "source": "idea_text_and_product_catalog",
            "used_ref_url": bool(url),
            "used_ref_images": bool(req.ref_image or req.ref_images),
            "confidence": "low",
        },
        "proposal": proposal,
    }
