"""
scripts/api_uploads.py — Resumable Chunked Upload Router with SHA-256 Deduplication (Phase 8.1).

Handles large mobile video/photo uploads (>100MB over Cloudflare Tunnel) via 8MB chunks:
- `POST /api/uploads/init`: Initialize a staging upload session.
- `GET /api/uploads/{upload_id}`: Query current byte offset for seamless resume after network drop.
- `PATCH /api/uploads/{upload_id}`: Append chunk at exact `Upload-Offset` (409 on mismatch).
- `POST /api/uploads/{upload_id}/complete`: Verify total size, validate media magic bytes (415 on invalid),
  enforce Rule 13 Strict Zero-Duplicate SHA-256 guard, and never overwrite existing files.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from scripts import config

logger = logging.getLogger("omnicut.api_uploads")

router = APIRouter(prefix="/api/uploads", tags=["ChunkedUploads"])

DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB (safe under Cloudflare 100MB request limit)

# Optional overrides for testing with tmp_path
STAGING_DIR: Optional[Path] = None
TARGET_DIR: Optional[Path] = None


def get_staging_dir() -> Path:
    base = STAGING_DIR if STAGING_DIR is not None else (config.PROJECTS_DIR / ".cache" / "uploads")
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_target_dir(product_code: Optional[str] = None) -> Path:
    if TARGET_DIR is not None:
        base = TARGET_DIR
    else:
        base = config.INBOX_DIR
    if product_code:
        safe_code = re.sub(r"[^A-Za-z0-9_\-]", "", product_code.strip())
        if safe_code:
            base = base / safe_code
    base.mkdir(parents=True, exist_ok=True)
    return base


# ============================================================================
# Schemas
# ============================================================================

class UploadInitRequest(BaseModel):
    filename: str = Field(..., description="ชื่อไฟล์ต้นฉบับ เช่น clip_01.mp4")
    total_size: int = Field(..., gt=0, description="ขนาดไฟล์รวมทั้งหมด (bytes)")
    mime_type: Optional[str] = Field("video/mp4", description="MIME type ของไฟล์")
    product_code: Optional[str] = Field(None, description="รหัสสินค้า (ถ้ามี)")
    sha256: Optional[str] = Field(None, description="SHA-256 checksum จากฝั่งไคลเอนต์ (ถ้ามี)")


# ============================================================================
# Helpers: Metadata, Magic Bytes, and SHA-256 Deduplication
# ============================================================================

def _sanitize_filename(filename: str) -> str:
    raw_name = Path(filename or "upload.mp4").name
    cleaned = re.sub(r"[^A-Za-z0-9._\-\u0E00-\u0E7F]", "_", raw_name)
    if not cleaned or cleaned.startswith("."):
        cleaned = f"upload_{uuid.uuid4().hex[:8]}.mp4"
    return cleaned


def _meta_path(upload_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_\-]", "", upload_id)
    return get_staging_dir() / f"{safe_id}.meta.json"


def _part_path(upload_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_\-]", "", upload_id)
    return get_staging_dir() / f"{safe_id}.part"


def _load_session(upload_id: str) -> Dict[str, Any]:
    mp = _meta_path(upload_id)
    if not mp.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบเซสชันอัปโหลด '{upload_id}'")
    try:
        return json.loads(mp.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"อ่านข้อมูลเซสชันอัปโหลดไม่ได้: {exc}")


def _save_session(upload_id: str, meta: Dict[str, Any]) -> None:
    mp = _meta_path(upload_id)
    mp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_media_magic_bytes(file_path: Path) -> bool:
    """Validate that the uploaded file starts with a valid video or image magic header."""
    try:
        with file_path.open("rb") as f:
            header = f.read(16)
    except Exception:
        return False

    if len(header) < 4:
        return False

    # Reject common executable / script headers immediately
    if (
        header.startswith(b"MZ")
        or header.startswith(b"\x7fELF")
        or header.startswith(b"#!")
        or header.startswith(b"<?php")
        or header.lower().startswith(b"<script")
        or header.lower().startswith(b"<!doctype html")
    ):
        return False

    # MP4 / QuickTime MOV ISO Base Media File Format: atom at bytes 4..8
    if len(header) >= 8 and header[4:8] in (
        b"ftyp",
        b"moov",
        b"wide",
        b"mdat",
        b"free",
        b"skip",
        b"pnot",
    ):
        return True

    # WebM / Matroska EBML header
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    # PNG
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return True

    # JPEG
    if header.startswith(b"\xff\xd8\xff"):
        return True

    # WebP (RIFF....WEBP)
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return True

    return False


def _compute_file_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _find_duplicate_by_sha256(target_dir: Path, sha256_hex: str, expected_size: int) -> Optional[Path]:
    """Rule 13 Strict Zero-Duplicate Guard: scan target directory for identical SHA-256."""
    if not target_dir.exists():
        return None
    for candidate in target_dir.iterdir():
        if not candidate.is_file():
            continue
        try:
            if candidate.stat().st_size != expected_size:
                continue
            if _compute_file_sha256(candidate) == sha256_hex:
                return candidate
        except Exception:
            continue
    return None


def _allocate_unique_path(target_dir: Path, filename: str) -> Path:
    """Never overwrite an existing file with different content."""
    candidate = target_dir / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        alt = target_dir / f"{stem}_{counter}{suffix}"
        if not alt.exists():
            return alt
        counter += 1


# ============================================================================
# Endpoints: /api/uploads/*
# ============================================================================

@router.post("/init")
def init_chunked_upload(req: UploadInitRequest) -> Dict[str, Any]:
    """Create a resumable chunked upload session in the staging area."""
    upload_id = f"up_{uuid.uuid4().hex[:16]}"
    clean_name = _sanitize_filename(req.filename)

    part = _part_path(upload_id)
    part.write_bytes(b"")

    meta = {
        "upload_id": upload_id,
        "filename": clean_name,
        "total_size": int(req.total_size),
        "mime_type": req.mime_type or "video/mp4",
        "product_code": req.product_code,
        "expected_sha256": (req.sha256 or "").strip().lower() or None,
        "offset": 0,
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "status": "initiated",
        "created_at": time.time(),
        "updated_at": time.time(),
        "final_path": None,
        "sha256": None,
        "deduplicated": False,
    }
    _save_session(upload_id, meta)

    return {
        "upload_id": upload_id,
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "offset": 0,
        "total_size": int(req.total_size),
        "status": "initiated",
    }


@router.get("/{upload_id}")
def get_upload_status(upload_id: str) -> Dict[str, Any]:
    """Return current server byte offset so mobile clients can resume after a disconnect."""
    meta = _load_session(upload_id)
    part = _part_path(upload_id)
    actual_offset = part.stat().st_size if part.exists() else int(meta.get("offset", 0))
    if actual_offset != meta.get("offset") and meta.get("status") != "completed":
        meta["offset"] = actual_offset
        _save_session(upload_id, meta)

    return {
        "upload_id": meta["upload_id"],
        "filename": meta["filename"],
        "offset": int(meta["offset"]),
        "total_size": int(meta["total_size"]),
        "chunk_size": int(meta.get("chunk_size", DEFAULT_CHUNK_SIZE)),
        "status": meta.get("status", "uploading"),
        "final_path": meta.get("final_path"),
        "sha256": meta.get("sha256"),
        "deduplicated": bool(meta.get("deduplicated", False)),
    }


@router.patch("/{upload_id}")
async def append_upload_chunk(
    upload_id: str,
    request: Request,
    upload_offset: Optional[int] = Header(default=None, alias="Upload-Offset"),
    offset: Optional[int] = Query(default=None),
):
    """Append raw chunk bytes at the exact current offset."""
    meta = _load_session(upload_id)
    if meta.get("status") == "completed":
        return {
            "upload_id": upload_id,
            "offset": int(meta["total_size"]),
            "total_size": int(meta["total_size"]),
            "status": "completed",
        }

    client_offset = upload_offset if upload_offset is not None else offset
    if client_offset is None:
        raise HTTPException(status_code=400, detail="ต้องระบุ Upload-Offset header หรือ query offset")

    part = _part_path(upload_id)
    current_offset = part.stat().st_size if part.exists() else 0

    if int(client_offset) != current_offset:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "offset_mismatch",
                "current_offset": current_offset,
                "client_offset": int(client_offset),
            },
        )

    body = await request.body()
    chunk_len = len(body)
    new_offset = current_offset + chunk_len
    total_size = int(meta["total_size"])

    if new_offset > total_size:
        raise HTTPException(
            status_code=400,
            detail=f"ข้อมูลเกินขนาดไฟล์ที่แจ้งไว้ ({new_offset} > {total_size})",
        )

    with part.open("ab") as f:
        f.write(body)

    meta["offset"] = new_offset
    meta["status"] = "uploading"
    meta["updated_at"] = time.time()
    _save_session(upload_id, meta)

    return {
        "upload_id": upload_id,
        "offset": new_offset,
        "total_size": total_size,
        "status": "uploading",
    }


@router.post("/{upload_id}/complete")
def complete_chunked_upload(upload_id: str) -> Dict[str, Any]:
    """Finalize upload: check total size, verify magic bytes, and deduplicate by SHA-256."""
    meta = _load_session(upload_id)
    if meta.get("status") == "completed" and meta.get("final_path"):
        return {
            "ok": True,
            "upload_id": upload_id,
            "deduplicated": bool(meta.get("deduplicated", False)),
            "path": meta["final_path"],
            "sha256": meta["sha256"],
            "size": int(meta["total_size"]),
        }

    part = _part_path(upload_id)
    if not part.exists():
        raise HTTPException(status_code=400, detail="ไม่พบไฟล์พักสำหรับเซสชันนี้")

    actual_size = part.stat().st_size
    total_size = int(meta["total_size"])
    if actual_size != total_size:
        raise HTTPException(
            status_code=400,
            detail=f"ขนาดไฟล์ยังไม่ครบ ({actual_size} / {total_size} bytes)",
        )

    # Validate magic bytes (reject executables / non-media with 415)
    if not _validate_media_magic_bytes(part):
        try:
            part.unlink()
        except Exception:
            pass
        meta["status"] = "rejected_invalid_media"
        _save_session(upload_id, meta)
        raise HTTPException(
            status_code=415,
            detail="รูปแบบไฟล์ไม่ถูกต้อง อนุญาตเฉพาะไฟล์วิดีโอหรือรูปภาพ (MP4, MOV, WebM, PNG, JPEG, WebP)",
        )

    digest = _compute_file_sha256(part)
    expected_sha = meta.get("expected_sha256")
    if expected_sha and expected_sha != digest:
        raise HTTPException(
            status_code=400,
            detail="SHA-256 checksum ไม่ตรงกับไฟล์ต้นฉบับ",
        )

    dest_dir = get_target_dir(meta.get("product_code"))

    # Rule 13 Strict Zero-Duplicate Guard
    existing_dup = _find_duplicate_by_sha256(dest_dir, digest, total_size)
    if existing_dup is not None:
        try:
            part.unlink()
        except Exception:
            pass
        meta["status"] = "completed"
        meta["deduplicated"] = True
        meta["final_path"] = str(existing_dup)
        meta["sha256"] = digest
        meta["updated_at"] = time.time()
        _save_session(upload_id, meta)
        return {
            "ok": True,
            "upload_id": upload_id,
            "deduplicated": True,
            "path": str(existing_dup),
            "sha256": digest,
            "size": total_size,
        }

    final_path = _allocate_unique_path(dest_dir, meta["filename"])
    shutil.move(str(part), str(final_path))

    meta["status"] = "completed"
    meta["deduplicated"] = False
    meta["final_path"] = str(final_path)
    meta["sha256"] = digest
    meta["updated_at"] = time.time()
    _save_session(upload_id, meta)

    return {
        "ok": True,
        "upload_id": upload_id,
        "deduplicated": False,
        "path": str(final_path),
        "sha256": digest,
        "size": total_size,
    }
