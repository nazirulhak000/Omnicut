"""
Error Handling and Recovery Architecture for OmniCut Pro Studio.
Provides structured error taxonomy, exception classification, actionable Thai guidance,
and bounded log reporting.
"""

import json
import logging
import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

logger = logging.getLogger("omnicut.error_handler")


class ErrorCategory(str, Enum):
    USER_CORRECTABLE = "user_correctable"
    FFMPEG = "ffmpeg"
    AI_PROVIDER = "ai_provider"
    SYSTEM_IO = "system_io"
    INTERNAL = "internal"


@dataclass
class AppError(Exception):
    category: ErrorCategory
    code: str
    message_th: str
    suggestion_th: str
    details: Optional[str] = None
    project_name: Optional[str] = None
    job_id: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self) -> str:
        return f"[{self.category.value.upper()}:{self.code}] {self.message_th}"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data


def truncate_stderr(stderr: Optional[str], max_chars: int = 2000, max_lines: int = 40) -> str:
    """Safely extracts and bounds the tail of stderr to prevent log explosion."""
    if not stderr:
        return ""
    lines = stderr.strip().splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    tail = "\n".join(lines)
    if len(tail) > max_chars:
        tail = tail[-max_chars:]
    return tail


def classify_exception(
    exc: Exception,
    project_name: Optional[str] = None,
    job_id: Optional[str] = None,
    details: Optional[str] = None,
) -> AppError:
    """
    Classifies any Python Exception into a structured AppError with
    actionable Thai instructions for the user.
    """
    if isinstance(exc, AppError):
        if project_name and not exc.project_name:
            exc.project_name = project_name
        if job_id and not exc.job_id:
            exc.job_id = job_id
        return exc

    err_str = str(exc).strip()
    err_type = type(exc).__name__
    combined_details = details or err_str

    # 1. System I/O: Disk Full or Permission
    if isinstance(exc, PermissionError) or "permission denied" in err_str.lower():
        return AppError(
            category=ErrorCategory.SYSTEM_IO,
            code="PERMISSION_DENIED",
            message_th="ไม่มีสิทธิ์เข้าถึงหรือบันทึกไฟล์ในโฟลเดอร์นี้",
            suggestion_th="กรุณาตรวจสอบสิทธิ์การเขียนไฟล์ หรือปิดโปรแกรมอื่นที่กำลังเปิดไฟล์นี้อยู่ (เช่น CapCut หรือ Media Player)",
            details=combined_details,
            project_name=project_name,
            job_id=job_id,
        )

    if "no space left on device" in err_str.lower() or "disk full" in err_str.lower():
        return AppError(
            category=ErrorCategory.SYSTEM_IO,
            code="DISK_FULL",
            message_th="พื้นที่จัดเก็บข้อมูลบนฮาร์ดดิสก์ไม่เพียงพอ",
            suggestion_th="กรุณาเพิ่มพื้นที่ว่างบนไดรฟ์อย่างน้อย 2-5 GB แล้วลองใหม่อีกครั้ง",
            details=combined_details,
            project_name=project_name,
            job_id=job_id,
        )

    # 2. User-correctable: Missing file or bad input
    if isinstance(exc, FileNotFoundError) or "not found" in err_str.lower() or "does not exist" in err_str.lower():
        return AppError(
            category=ErrorCategory.USER_CORRECTABLE,
            code="FILE_NOT_FOUND",
            message_th="ไม่พบไฟล์มีเดียหรือวัตถุดิบต้นฉบับที่ระบุ",
            suggestion_th="กรุณาตรวจสอบว่ามีไฟล์วิดีโอหรือเสียงอยู่ในโฟลเดอร์ หรืออัปโหลดไฟล์ใหม่อีกครั้ง",
            details=combined_details,
            project_name=project_name,
            job_id=job_id,
        )

    # 3. FFmpeg Errors
    if "ffmpeg" in err_str.lower() or "invalid data found" in err_str.lower() or "codec" in err_str.lower() or "timeout" in err_str.lower():
        return AppError(
            category=ErrorCategory.FFMPEG,
            code="FFMPEG_PROCESSING_ERROR",
            message_th="การประมวลผลวิดีโอด้วย FFmpeg ขัดข้อง",
            suggestion_th="กรุณาตรวจสอบว่าไฟล์วิดีโอต้นทางไม่เสียหาย และเป็นฟอร์แมตมาตรฐาน (MP4, MOV)",
            details=truncate_stderr(combined_details),
            project_name=project_name,
            job_id=job_id,
        )

    # 4. AI Provider Errors (Gemini / TTS)
    if "quota" in err_str.lower() or "rate limit" in err_str.lower() or "429" in err_str or "resourceexhausted" in err_str.lower():
        return AppError(
            category=ErrorCategory.AI_PROVIDER,
            code="AI_QUOTA_EXCEEDED",
            message_th="โควต้าการใช้งาน AI ชั่วคราวเต็ม",
            suggestion_th="ระบบจะสลับไปใช้โมเดลหรือเสียงพากย์สำรอง หรือกรุณารอสักครู่แล้วลองอีกครั้ง",
            details=combined_details,
            project_name=project_name,
            job_id=job_id,
        )

    if "edge_tts" in err_str.lower() or "handshake" in err_str.lower() or "connection" in err_str.lower():
        return AppError(
            category=ErrorCategory.AI_PROVIDER,
            code="TTS_NETWORK_ERROR",
            message_th="การเชื่อมต่อระบบเสียงสังเคราะห์ขัดข้อง",
            suggestion_th="กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต ระบบจะพยายามเชื่อมต่อใหม่โดยอัตโนมัติ",
            details=combined_details,
            project_name=project_name,
            job_id=job_id,
        )

    # 5. Internal / General fallback
    return AppError(
        category=ErrorCategory.INTERNAL,
        code=f"INTERNAL_{err_type.upper()}",
        message_th=f"เกิดข้อผิดพลาดในการประมวลผล: {err_str[:120]}",
        suggestion_th="กรุณากดลองใหม่อีกครั้ง หากยังพบปัญหาตรวจสอบประวัติใน Activity Center",
        details=combined_details,
        project_name=project_name,
        job_id=job_id,
    )


def log_structured_error(app_err: AppError) -> None:
    """Logs the structured error as JSON for monitoring and diagnostics."""
    payload = app_err.to_dict()
    logger.error(f"[OmniCutError] {json.dumps(payload, ensure_ascii=False)}")
    print(f"❌ [{payload['category'].upper()}:{payload['code']}] {payload['message_th']} (Project: {payload.get('project_name') or 'N/A'})")
    if payload.get("suggestion_th"):
        print(f"💡 คำแนะนำ: {payload['suggestion_th']}")
