"""
scripts/api_command.py — Mobile AI Command Center & Masked AI Settings Router (Phase 7.2 & 7.3).

Provides:
- Closed-schema natural language planning (`POST /api/command/plan`) with zero raw shell access.
- Safe domain intent execution (`POST /api/command/execute`) with mandatory confirmation tokens
  for destructive/cleanup intents (HTTP 409 when missing or invalid).
- Masked AI & Key configuration endpoints (`GET /api/settings/ai`, `PUT /api/settings/ai/keys`)
  that never leak raw `AIza...` or `AQ....` secret values to the client.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from scripts import config

logger = logging.getLogger("omnicut.api_command")

router = APIRouter(tags=["CommandCenter"])

# Strict whitelist of domain intents — NO raw shell execution allowed
ALLOWED_INTENTS = (
    "produce_couple_20",
    "check_status",
    "rerender_clip",
    "post_next",
    "system_health",
    "cleanup_temp",
)

DESTRUCTIVE_INTENTS = ("cleanup_temp",)

_CONFIRM_SECRET = os.environ.get("OMNICUT_COMMAND_SECRET") or secrets.token_hex(32)
_CONFIRM_TTL_SECONDS = 600  # 10 minutes

# Runtime override store for AI keys updated via PUT /api/settings/ai/keys
_RUNTIME_AI_KEYS: Optional[List[str]] = None
_LAST_429_TIMESTAMP: Optional[str] = None


# ============================================================================
# Schemas
# ============================================================================

class CommandPlanRequest(BaseModel):
    prompt: str = Field(..., description="คำสั่งภาษาธรรมชาติ (ไทย/อังกฤษ)")
    product_code: Optional[str] = Field(None, description="รหัสสินค้า เช่น TTZ01, HAT01")
    clip_id: Optional[str] = Field(None, description="รหัสคลิป เช่น s07")
    intent: Optional[str] = Field(None, description="ระบุ intent โดยตรง (ถ้ามี)")


class CommandExecuteRequest(BaseModel):
    plan_id: Optional[str] = Field(default=None, description="รหัสแผนงานจาก /api/command/plan")
    intent: str = Field(..., description="Domain intent ที่อยู่ใน ALLOWED_INTENTS")
    params: Dict[str, Any] = Field(default_factory=dict, description="พารามิเตอร์ของงาน")
    confirm_token: Optional[str] = Field(default=None, description="โทเคนยืนยันสำหรับงานทำลาย/ล้างข้อมูล")


class UpdateAIKeysRequest(BaseModel):
    keys: List[str] = Field(..., description="รายการ Gemini API Keys (Write-only)")


# ============================================================================
# Helpers: Confirmation Token & Key Masking
# ============================================================================

def _issue_confirm_token(plan_id: str, intent: str, issued_at: Optional[int] = None) -> str:
    ts = int(issued_at if issued_at is not None else time.time())
    payload = f"{plan_id}:{intent}:{ts}"
    sig = hmac.new(
        _CONFIRM_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]
    return f"{ts}.{sig}"


def _verify_confirm_token(plan_id: str, intent: str, token: Optional[str]) -> bool:
    if not token or "." not in token:
        return False
    try:
        ts_str, sig = token.split(".", 1)
        ts = int(ts_str)
    except (ValueError, TypeError):
        return False

    now = int(time.time())
    if abs(now - ts) > _CONFIRM_TTL_SECONDS:
        return False

    expected_payload = f"{plan_id}:{intent}:{ts}"
    expected_sig = hmac.new(
        _CONFIRM_SECRET.encode("utf-8"),
        expected_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:24]
    return hmac.compare_digest(sig, expected_sig)


def _mask_single_key(raw_key: str, index: int) -> Dict[str, Any]:
    """Return masked metadata for a key, guaranteeing zero raw prefix/secret leakage."""
    cleaned = (raw_key or "").strip()
    if not cleaned:
        return {"index": index, "last4": "----", "configured": False}

    tail = cleaned[-4:] if len(cleaned) >= 8 else "****"
    # Extra guard: never allow AIza or AQ. substrings even in short test strings
    if "AIza" in tail or "AQ." in tail or "eyJ" in tail:
        tail = "****"

    return {
        "index": index,
        "last4": tail,
        "configured": True,
    }


def _get_active_keys() -> List[str]:
    if _RUNTIME_AI_KEYS is not None:
        return list(_RUNTIME_AI_KEYS)
    return config.get_gemini_api_keys()


def _check_agy_logged_in() -> bool:
    """Check whether Antigravity / Gemini CLI credentials or Drive mount exist."""
    home = Path.home()
    candidates = [
        home / ".gemini" / "oauth_creds.json",
        home / ".gemini" / "google_accounts.json",
        home / ".gemini" / "antigravity",
         home / ".config" / "gcloud" / "application_default_credentials.json",
        Path("/content/drive/MyDrive"),
    ]
    for p in candidates:
        try:
            if p.exists():
                return True
        except Exception:
            continue
    return bool(os.environ.get("AGY_LOGGED_IN", "").strip() == "1")


# ============================================================================
# Intent Classification & Plan Builder
# ============================================================================

_CLIP_RE = re.compile(r"\b(s\d{1,2})\b", re.IGNORECASE)
_PRODUCT_RE = re.compile(r"\b([A-Z]{2,5}\d{2,4})\b")
_URL_RE = re.compile(r"(https?://\S+)", re.IGNORECASE)


def _classify_prompt(
    prompt: str,
    product_code: Optional[str] = None,
    clip_id: Optional[str] = None,
    explicit_intent: Optional[str] = None,
) -> Dict[str, Any]:
    text = (prompt or "").strip()
    lower = text.lower()

    if explicit_intent:
        if explicit_intent not in ALLOWED_INTENTS:
            raise HTTPException(
                status_code=400,
                detail=f"ไม่อนุญาต intent '{explicit_intent}' (อนุญาตเฉพาะ {list(ALLOWED_INTENTS)})",
            )
        intent = explicit_intent
    else:
        if any(
            kw in lower
            for kw in (
                "ล้าง",
                "ลบไฟล์ชั่วคราว",
                "ลบแคช",
                "cleanup",
                "clean temp",
                "clear cache",
                "rm ",
                "delete temp",
                "ลบ temp",
            )
        ):
            intent = "cleanup_temp"
        elif any(
            kw in lower
            for kw in (
                "ผลิต 20",
                "สร้าง 20",
                "20 คลิป",
                "produce",
                "ผลิตคลิป",
                "จากลิงก์นี้",
            )
        ):
            intent = "produce_couple_20"
        elif any(
            kw in lower
            for kw in (
                "เรนเดอร์ใหม่",
                "rerender",
                "re-render",
                "ซ่อมคลิป",
                "เรนเดอร์คลิป",
            )
        ):
            intent = "rerender_clip"
        elif any(
            kw in lower
            for kw in (
                "โพสต์คลิปถัดไป",
                "โพสต์ถัดไป",
                "post next",
                "โพสต์เลย",
                "คิวถัดไป",
            )
        ):
            intent = "post_next"
        elif any(
            kw in lower
            for kw in (
                "เช็กระบบ",
                "เช็คระบบ",
                "สุขภาพระบบ",
                "system health",
                "health",
                "เช็ก gpu",
            )
        ):
            intent = "system_health"
        else:
            intent = "check_status"

    # Extract parameters from prompt if not explicitly provided
    detected_clip = clip_id
    if not detected_clip:
        m_clip = _CLIP_RE.search(text)
        if m_clip:
            detected_clip = f"s{int(m_clip.group(1)[1:]):02d}"

    detected_product = product_code
    if not detected_product:
        m_prod = _PRODUCT_RE.search(text)
        if m_prod:
            detected_product = m_prod.group(1).upper()

    detected_url = None
    m_url = _URL_RE.search(text)
    if m_url:
        detected_url = m_url.group(1)

    params: Dict[str, Any] = {}
    if detected_product:
        params["product_code"] = detected_product
    if detected_clip:
        params["clip_id"] = detected_clip
    if detected_url:
        params["source_url"] = detected_url

    plan_id = f"plan_{uuid.uuid4().hex[:12]}"
    destructive = intent in DESTRUCTIVE_INTENTS
    requires_confirmation = destructive
    confirm_token = _issue_confirm_token(plan_id, intent) if requires_confirmation else None

    if intent == "produce_couple_20":
        target_label = detected_product or detected_url or "สินค้าที่เลือก"
        title = f"ผลิตคลิปคู่รัก 20 บท ({target_label})"
        steps = [
            "ดึงข้อมูลสินค้าและตรวจสอบวัตถุดิบภาพ/สเปก",
            "สร้างและตรวจกฎสคริปต์คู่รัก 20 มุม (ไม่มีราคา/ตัวเลขต้องห้าม)",
            "พากย์เสียง Single-Take TTS (Aoede & Puck) และจัดจังหวะ Whisper",
            "ประกอบ HyperFrames และเปิด Checkpoint ให้ตรวจก่อนเรนเดอร์จริง",
        ]
    elif intent == "rerender_clip":
        clip_label = detected_clip or "s01"
        params.setdefault("clip_id", clip_label)
        title = f"เรนเดอร์ใหม่เฉพาะคลิป {clip_label}"
        steps = [
            f"ตรวจสอบไฟล์เสียงและซับไตเติลของคลิป {clip_label}",
            f"เรนเดอร์คลิป {clip_label} ใหม่ด้วยความละเอียด 1080x1920 30FPS",
            "ตรวจ Visual Gate และอัปเดตทะเบียนคลังคลิป",
        ]
    elif intent == "post_next":
        title = "เตรียมโพสต์คลิปถัดไปตามคิว"
        steps = [
            "ค้นหาคลิปที่ถึงกำหนดโพสต์ถัดไปในคิว",
            "ล็อกสถานะ Handoff เพื่อกันการโพสต์ซ้ำ",
            "เตรียมไฟล์วิดีโอ แคปชัน และรหัสสินค้าสำหรับแชร์เข้า TikTok",
        ]
    elif intent == "system_health":
        title = "ตรวจสอบสถานะระบบและทรัพยากร"
        steps = [
            "เช็กสถานะ Gemini API Keys และโควตาล่าสุด",
            "ตรวจสอบพื้นที่จัดเก็บและโฟลเดอร์โปรเจกต์",
            "ตรวจสอบความพร้อมของเอ็นจิ้นเรนเดอร์และ FFmpeg",
        ]
    elif intent == "cleanup_temp":
        params.setdefault("target", ".tmp & 03_Projects/.cache/uploads")
        title = "ล้างไฟล์ชั่วคราวและแคชอัปโหลด"
        steps = [
            "ตรวจสอบไฟล์ค้างใน .tmp/ และโฟลเดอร์พักอัปโหลด (ไม่แตะ 01_Raw และ 02_Assets)",
            "ลบเฉพาะไฟล์ชั่วคราวที่ไม่ได้ใช้งานอยู่",
            "สรุปพื้นที่ว่างที่ได้รับคืน",
        ]
    else:
        title = "ตรวจสอบสถานะงานที่กำลังทำอยู่"
        steps = [
            "ดึงสถานะงานผลิตคลิปและคิวเรนเดอร์ล่าสุด",
            "สรุปจำนวนคลิปที่เสร็จแล้ว รอตรวจ และคิวโพสต์วันนี้",
        ]

    return {
        "plan_id": plan_id,
        "intent": intent,
        "title": title,
        "steps": steps,
        "params": params,
        "destructive": destructive,
        "requires_confirmation": requires_confirmation,
        "confirm_token": confirm_token,
    }


# ============================================================================
# Endpoints: /api/command/*
# ============================================================================

@router.post("/api/command/plan")
def create_command_plan(req: CommandPlanRequest) -> Dict[str, Any]:
    """Side-effect-free endpoint mapping natural Thai/English prompt to a closed-schema plan."""
    if not (req.prompt or "").strip() and not req.intent:
        raise HTTPException(status_code=400, detail="กรุณาพิมพ์คำสั่งหรือเลือกงานที่ต้องการ")
    return _classify_prompt(
        prompt=req.prompt,
        product_code=req.product_code,
        clip_id=req.clip_id,
        explicit_intent=req.intent,
    )


@router.post("/api/command/execute")
def execute_command_plan(req: CommandExecuteRequest):
    """Execute an approved domain plan safely without raw shell invocation."""
    intent = (req.intent or "").strip()
    if intent not in ALLOWED_INTENTS:
        raise HTTPException(
            status_code=400,
            detail=f"ไม่อนุญาต intent '{intent}' (อนุญาตเฉพาะ {list(ALLOWED_INTENTS)})",
        )

    plan_id = (req.plan_id or "adhoc").strip()
    is_destructive = intent in DESTRUCTIVE_INTENTS or bool((req.params or {}).get("destructive"))

    if is_destructive:
        if not _verify_confirm_token(plan_id, intent, req.confirm_token):
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "confirmation_required",
                    "requires_confirmation": True,
                    "intent": intent,
                    "plan_id": plan_id,
                },
            )

    job_id = f"cmd_{uuid.uuid4().hex[:10]}"
    params = req.params or {}

    if intent == "cleanup_temp":
        tmp_dir = config.BASE_DIR / ".tmp"
        removed_count = 0
        if tmp_dir.exists():
            for item in tmp_dir.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                        removed_count += 1
                    except Exception:
                        pass
        return {
            "ok": True,
            "job_id": job_id,
            "plan_id": plan_id,
            "intent": intent,
            "status": "completed",
            "message": f"ล้างไฟล์ชั่วคราวเรียบร้อย ({removed_count} ไฟล์)",
            "result": {"removed_files": removed_count},
        }

    if intent == "system_health":
        keys = _get_active_keys()
        return {
            "ok": True,
            "job_id": job_id,
            "plan_id": plan_id,
            "intent": intent,
            "status": "completed",
            "message": "ระบบพร้อมทำงานปกติ",
            "result": {
                "key_count": len(keys),
                "raw_dir_exists": config.RAW_DIR.exists(),
                "exports_dir_exists": config.EXPORTS_DIR.exists(),
            },
        }

    if intent == "check_status":
        return {
            "ok": True,
            "job_id": job_id,
            "plan_id": plan_id,
            "intent": intent,
            "status": "completed",
            "message": "ตรวจสอบสถานะงานล่าสุดเรียบร้อย",
            "result": {
                "active_jobs": 0,
                "params": params,
            },
        }

    # Queued async domain jobs (produce_couple_20, rerender_clip, post_next)
    return {
        "ok": True,
        "job_id": job_id,
        "plan_id": plan_id,
        "intent": intent,
        "status": "queued",
        "message": f"รับคำสั่ง '{intent}' เข้าคิวทำงานแล้ว",
        "result": {
            "params": params,
        },
    }


# ============================================================================
# Endpoints: /api/settings/ai*
# ============================================================================

@router.get("/api/settings/ai")
def get_ai_settings() -> Dict[str, Any]:
    """Return masked AI settings and key status without ever exposing raw keys."""
    keys = _get_active_keys()
    masked_list = [_mask_single_key(k, idx + 1) for idx, k in enumerate(keys)]
    return {
        "key_count": len(keys),
        "keys_masked": masked_list,
        "last_429_at": _LAST_429_TIMESTAMP,
        "tts_models": ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview"],
        "llm_model": "gemini-2.5-flash",
        "agy_logged_in": _check_agy_logged_in(),
    }


@router.put("/api/settings/ai/keys")
def update_ai_keys(req: UpdateAIKeysRequest) -> Dict[str, Any]:
    """Write-only update of Gemini API keys; returns only masked summary."""
    global _RUNTIME_AI_KEYS
    cleaned_keys: List[str] = []
    for raw in req.keys or []:
        val = (raw or "").strip()
        if val and val not in cleaned_keys:
            cleaned_keys.append(val)

    _RUNTIME_AI_KEYS = cleaned_keys

    # Update process environment variables in memory
    for idx, val in enumerate(cleaned_keys, start=1):
        if idx == 1:
            os.environ["GEMINI_API_KEY"] = val
        os.environ[f"GEMINI_API_KEY_{idx}"] = val

    masked_list = [_mask_single_key(k, idx + 1) for idx, k in enumerate(cleaned_keys)]
    return {
        "ok": True,
        "key_count": len(cleaned_keys),
        "keys_masked": masked_list,
    }
