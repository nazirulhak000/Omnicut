"""Channel registry (multi-channel foundation, phase P1).

``_Docs/channels.json`` is the single source of truth for TikTok channel
profiles.  This module owns reading, validating and writing it.  Contract
(see ``_Docs/Plans/ADR_MULTI_CHANNEL_20261010.md``):

* Reading never has side effects.  A missing file yields an in-memory
  registry containing only the implicit ``main`` channel; the file is only
  written by an explicit ``seed``/``create``/``update``/``activate``/
  ``archive``/``set_account_binding`` call.
* Writes are validated, atomic (temp file + ``os.replace``), serialized by an
  in-process lock plus an OS file lock (``<registry>.lock``), and guarded by
  optimistic concurrency (``expected_revision`` -> 409 on mismatch).
* ``id`` is an immutable slug; there is no delete.  ``archive`` keeps the
  record (reads keep working) and blocks new work.
* No cookies, API keys or login data are stored here.

Errors are raised as :class:`ChannelError` (a Starlette ``HTTPException``)
with a short Thai ``detail`` and a machine ``code``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from starlette.exceptions import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:  # pragma: no cover - script/CLI use
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import config  # noqa: E402

SCHEMA_VERSION = 1
ERROR_CODE_HEADER = "X-OmniCut-Error-Code"

CHANNEL_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_ARCHIVED = "archived"
STATUSES = (STATUS_DRAFT, STATUS_ACTIVE, STATUS_ARCHIVED)
BINDING_UNVERIFIED = "unverified"
BINDING_VERIFIED = "verified"
BINDING_STATUSES = (BINDING_UNVERIFIED, BINDING_VERIFIED)
DEFAULT_TIMEZONE = "Asia/Bangkok"
AVATAR_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
STATUS_LABEL_TH = {
    STATUS_DRAFT: "ฉบับร่าง (draft)",
    STATUS_ACTIVE: "ใช้งาน (active)",
    STATUS_ARCHIVED: "เก็บถาวร (archived)",
}

# Fields a client may set through create/update.  Everything else is owned by
# the store (status via activate/archive, binding via set_account_binding).
EDITABLE_FIELDS = (
    "display_name",
    "handle",
    "watermark_text",
    "avatar_asset_path",
    "follow_title",
    "timezone",
    "posting_enabled",
    "overrides",
)
CREATE_FIELDS = ("id",) + EDITABLE_FIELDS
IDENTITY_TEXT_FIELDS = ("display_name", "handle", "watermark_text", "follow_title")
REQUIRED_PROFILE_FIELDS = (
    "display_name",
    "handle",
    "watermark_text",
    "follow_title",
    "avatar_asset_path",
)
CHANNEL_FIELD_ORDER = (
    "id",
    "display_name",
    "handle",
    "watermark_text",
    "avatar_asset_path",
    "follow_title",
    "timezone",
    "status",
    "posting_enabled",
    "account_binding",
    "overrides",
    "created_at",
    "updated_at",
    "revision",
    "identity_hash",
)


# ---------------------------------------------------------------------------
# Layout limits.  Numbers come from the existing HyperFrames kit layout
# (03_Projects/_HyperFrames_Studio/kit/kit.css + follow.css) and the Global
# Editor watermark (scripts/subtitle_engine.py WATERMARK_*).  Values over a
# limit are rejected, never truncated.  Widths are measured with the project
# fonts in 02_Assets/Fonts (byte-identical to kit/fonts); when a font file is
# unavailable only the character cap applies.
#
# display_name   -> #fl-card .fl-who b: Anuphan 40px, nowrap+ellipsis, box
#                   width 910-68(padding)-128(avatar)-2*24(gap)-220(button)
#                   = 446px.  Seed value measures 321px.
# watermark_text -> kit #wm span: Anuphan 26px rotated 90deg ending 36px above
#                   the bottom edge; Global Editor draws the same text at
#                   ~41px centred at y=0.72*1920, so the frame bottom bounds
#                   it to ~682px in 26px-Anuphan units.  Limit 600px leaves
#                   margin for wider caption fonts.  Seed value: 503px.
# follow_title   -> kit #fl-title: Kanit Black 124px, nowrap, centred in the
#                   1080px frame; limit 960px keeps 60px from both edges.
#                   Seed value: 908px.
# handle         -> #fl-card .fl-who span (30px, wraps); bounded by the
#                   handle rule (max 24 chars), no width check.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TextFieldLimit:
    label_th: str
    max_chars: int
    font_file: str
    font_px: int
    max_width_px: float


TEXT_FIELD_LIMITS: dict[str, TextFieldLimit] = {
    "display_name": TextFieldLimit("ชื่อช่อง", 40, "Anuphan-Bold.ttf", 40, 446.0),
    "watermark_text": TextFieldLimit("ข้อความลายน้ำ", 64, "Anuphan-Bold.ttf", 26, 600.0),
    "follow_title": TextFieldLimit("หัวข้อชวนกดติดตาม", 24, "Kanit-Black.ttf", 124, 960.0),
}

# Seed/implicit ``main`` channel.  Every value below is copied from the
# existing HyperFrames kit config ``03_Projects/_HyperFrames_Studio/kit/
# channels.js`` (window.HF_CHANNELS.main, read 2026-10-10) -- the code does
# NOT read that gitignored folder at runtime.  display_name/handle also match
# plan §1; watermark_text equals subtitle_engine.WATERMARK_TEXT; the avatar is
# the kit's ``assets/shared/img/channel_avatar.jpg`` expressed relative to the
# project root.
MAIN_SEED: dict[str, Any] = {
    "id": "main",
    "display_name": "rizannTry",
    "handle": "@rizanntry",
    "watermark_text": "สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง",
    "avatar_asset_path": "03_Projects/_HyperFrames_Studio/assets/shared/img/channel_avatar.jpg",
    "follow_title": "กดติดตามด้วยนะ",
    "timezone": DEFAULT_TIMEZONE,
    "status": STATUS_ACTIVE,
    "posting_enabled": False,
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ChannelError(HTTPException):
    """Typed channel error. ``detail`` is a short Thai message.

    Status mapping (ADR): 422 invalid/unknown/missing scope or invalid input;
    404 resource of another channel / unknown channel id in a path; 409
    revision, uniqueness or status conflict; 500 corrupt registry.
    """

    def __init__(self, status_code: int, code: str, message: str, **extra: Any) -> None:
        super().__init__(status_code=status_code, detail=message, headers={ERROR_CODE_HEADER: code})
        self.code = code
        self.message = message
        self.extra = extra

    def to_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {"detail": self.message, "code": self.code}
        body.update(self.extra)
        return body


class HandleError(ChannelError):
    """Handle normalization failure; ``reason`` matches the shared fixture codes."""

    def __init__(self, reason: str) -> None:
        super().__init__(422, f"handle_{reason}", HANDLE_ERROR_MESSAGES[reason], field="handle")
        self.reason = reason


def _invalid(code: str, message: str, field_name: Optional[str] = None) -> ChannelError:
    extra = {"field": field_name} if field_name else {}
    return ChannelError(422, code, message, **extra)


# ---------------------------------------------------------------------------
# Handle normalization -- ONE rule shared with frontend/src/lib/channelHandle.js
# (parity enforced by tests/fixtures/channel_handle_cases.json in both suites).
#
# Order: type -> trim (explicit char set) -> empty -> TikTok URL extraction ->
# strip one leading "@" -> empty -> charset [A-Za-z0-9._] -> ASCII lowercase ->
# length 2..24 -> consecutive dots -> trailing dot.  Result: "@" + handle.
# ---------------------------------------------------------------------------

HANDLE_MIN_LEN = 2
HANDLE_MAX_LEN = 24
HANDLE_TRIM_CHARS = (
    " \t\n\r\f\v          "
    "       　﻿​"
)
_URL_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.IGNORECASE)
_TIKTOK_HOST_PREFIX_RE = re.compile(r"^(?:[a-z0-9-]+\.)*tiktok\.com(?:[:/]|$)", re.IGNORECASE)
_TIKTOK_URL_RE = re.compile(
    r"^(?:https?://)?(?:[a-z0-9-]+\.)*tiktok\.com(?::\d+)?(?:/(.*))?$",
    re.IGNORECASE | re.DOTALL,
)
_HANDLE_CHARS_RE = re.compile(r"^[A-Za-z0-9._]+$")

HANDLE_ERROR_MESSAGES = {
    "invalid_type": "handle ต้องเป็นข้อความ",
    "empty": "กรุณาระบุ handle ของช่อง เช่น @rizanntry",
    "not_tiktok_url": "ลิงก์นี้ไม่ใช่ลิงก์โปรไฟล์ TikTok",
    "url_without_handle": "ลิงก์ TikTok นี้ไม่มี @handle ให้ใช้ลิงก์โปรไฟล์ เช่น tiktok.com/@ชื่อช่อง",
    "invalid_chars": "handle ใช้ได้เฉพาะ a-z, 0-9, จุด และขีดล่าง",
    "too_short": f"handle ต้องยาวอย่างน้อย {HANDLE_MIN_LEN} ตัวอักษร",
    "too_long": f"handle ยาวได้ไม่เกิน {HANDLE_MAX_LEN} ตัวอักษร",
    "consecutive_dots": "handle มีจุดติดกันไม่ได้",
    "trailing_dot": "handle ลงท้ายด้วยจุดไม่ได้",
}


def normalize_handle(raw: Any) -> str:
    """Normalize a TikTok handle or profile URL to ``@lowercase``.

    Raises :class:`HandleError` (``.reason`` = fixture error code).
    """
    if raw is None:
        raise HandleError("empty")
    if not isinstance(raw, str):
        raise HandleError("invalid_type")
    text = raw.strip(HANDLE_TRIM_CHARS)
    if not text:
        raise HandleError("empty")
    if _URL_SCHEME_RE.match(text) or _TIKTOK_HOST_PREFIX_RE.match(text):
        match = _TIKTOK_URL_RE.match(text)
        if not match:
            raise HandleError("not_tiktok_url")
        rest = re.split(r"[?#]", match.group(1) or "", maxsplit=1)[0]
        segment = rest.split("/", 1)[0]
        if not segment.startswith("@") or segment == "@":
            raise HandleError("url_without_handle")
        text = segment
    if text.startswith("@"):
        text = text[1:]
    if not text:
        raise HandleError("empty")
    if not _HANDLE_CHARS_RE.match(text):
        raise HandleError("invalid_chars")
    text = text.translate(_ASCII_LOWER)
    if len(text) < HANDLE_MIN_LEN:
        raise HandleError("too_short")
    if len(text) > HANDLE_MAX_LEN:
        raise HandleError("too_long")
    if ".." in text:
        raise HandleError("consecutive_dots")
    if text.endswith("."):
        raise HandleError("trailing_dot")
    return "@" + text


_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def is_valid_channel_id(value: Any) -> bool:
    return isinstance(value, str) and bool(CHANNEL_ID_RE.match(value))


# ---------------------------------------------------------------------------
# Text validation (NFC, control chars, glyph coverage, char cap, pixel width)
# ---------------------------------------------------------------------------

_ALLOWED_FORMAT_CHARS = {"‍"}  # ZWJ (emoji sequences) -- rejected later by glyph coverage if unsupported


def _forbidden_chars(text: str) -> list[str]:
    bad: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat == "Cc" or cat in ("Zl", "Zp") or (cat == "Cf" and ch not in _ALLOWED_FORMAT_CHARS) or cat == "Cs":
            bad.append(ch)
    return bad


def _fallback_unsupported(text: str) -> list[str]:
    """Without a font file, reject what the kit fonts never cover: emoji/pictographs."""
    out = []
    for ch in text:
        cp = ord(ch)
        if cp >= 0x1F000 or 0x2600 <= cp <= 0x27BF or cp in (0xFE0F, 0x200D) or 0x1F1E6 <= cp <= 0x1F1FF:
            out.append(ch)
    return out


class TextMetrics:
    """Glyph coverage + advance-width measurement with the project fonts.

    ``fonts_dir`` defaults to ``config.FONTS_DIR`` (02_Assets/Fonts).  Tests
    inject a fake implementing ``width_px`` and ``unsupported_chars``.
    ``width_px`` returns ``None`` when the font is unavailable (only the
    character cap applies then).
    """

    def __init__(self, fonts_dir: Optional[Path] = None) -> None:
        self.fonts_dir = Path(fonts_dir) if fonts_dir is not None else Path(config.FONTS_DIR)

    def _font_path(self, font_file: str) -> Optional[Path]:
        path = self.fonts_dir / font_file
        return path if path.is_file() else None

    def width_px(self, text: str, font_file: str, size: int) -> Optional[float]:
        path = self._font_path(font_file)
        if path is None:
            return None
        try:
            font = _load_pil_font(str(path), path.stat().st_mtime_ns, size)
            return float(font.getlength(text))
        except Exception:
            return None

    def unsupported_chars(self, text: str, font_file: str) -> list[str]:
        path = self._font_path(font_file)
        cmap = None
        if path is not None:
            try:
                cmap = _load_cmap(str(path), path.stat().st_mtime_ns)
            except Exception:
                cmap = None
        if cmap is None:
            return _fallback_unsupported(text)
        return [ch for ch in text if not ch.isspace() and ord(ch) not in cmap]


@lru_cache(maxsize=16)
def _load_pil_font(path: str, _mtime_ns: int, size: int):
    from PIL import ImageFont

    return ImageFont.truetype(path, size)


@lru_cache(maxsize=8)
def _load_cmap(path: str, _mtime_ns: int) -> frozenset:
    from fontTools.ttLib import TTFont

    font = TTFont(path, lazy=True)
    try:
        return frozenset(font.getBestCmap().keys())
    finally:
        font.close()


_DEFAULT_METRICS = TextMetrics()


def normalize_text_field(field_name: str, value: Any, *, metrics: Optional[TextMetrics] = None) -> str:
    """Validate/normalize one identity text field. Empty string allowed (draft).

    NFC-normalizes, trims (handle trim set), rejects control/format chars,
    glyphs the layout font cannot draw, over-cap length and over-width text.
    """
    limit = TEXT_FIELD_LIMITS[field_name]
    if value is None:
        return ""
    if not isinstance(value, str):
        raise _invalid("text_invalid_type", f"{limit.label_th}ต้องเป็นข้อความ", field_name)
    text = unicodedata.normalize("NFC", value).strip(HANDLE_TRIM_CHARS)
    if not text:
        return ""
    if _forbidden_chars(text):
        raise _invalid(
            "text_control_chars",
            f"{limit.label_th}มีอักขระควบคุมหรืออักขระมองไม่เห็น กรุณาพิมพ์ใหม่",
            field_name,
        )
    if len(text) > limit.max_chars:
        raise _invalid(
            "text_too_long",
            f"{limit.label_th}ยาวเกิน {limit.max_chars} ตัวอักษร (ตอนนี้ {len(text)})",
            field_name,
        )
    m = metrics or _DEFAULT_METRICS
    unsupported = m.unsupported_chars(text, limit.font_file)
    if unsupported:
        sample = "".join(dict.fromkeys(unsupported))[:8]
        raise _invalid(
            "text_unsupported_chars",
            f"{limit.label_th}มีอักขระที่ฟอนต์ของช่องแสดงไม่ได้ (เช่น อีโมจิ): {sample}",
            field_name,
        )
    width = m.width_px(text, limit.font_file, limit.font_px)
    if width is not None and width > limit.max_width_px:
        raise _invalid(
            "text_too_wide",
            f"{limit.label_th}ยาวเกินพื้นที่ในคลิป ({int(round(width))}px จากที่ได้ {int(limit.max_width_px)}px) กรุณาย่อข้อความ",
            field_name,
        )
    return text


def normalize_timezone(value: Any) -> str:
    if value is None or value == "":
        return DEFAULT_TIMEZONE
    if not isinstance(value, str) or len(value) > 64:
        raise _invalid("timezone_invalid", "timezone ไม่ถูกต้อง เช่น Asia/Bangkok", "timezone")
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError, OSError):
        raise _invalid("timezone_invalid", f"ไม่รู้จัก timezone: {value}", "timezone")
    return value


def normalize_avatar_path(value: Any, *, project_root: Path) -> str:
    """Return a POSIX path relative to the project root, containment-checked.

    The file does not have to exist (missing file = readiness issue).
    """
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise _invalid("avatar_path_invalid", "ที่อยู่รูปโปรไฟล์ต้องเป็นข้อความ", "avatar_asset_path")
    raw = value.strip(HANDLE_TRIM_CHARS).replace("\\", "/")
    if not raw:
        return ""
    if _forbidden_chars(raw):
        raise _invalid("avatar_path_invalid", "ที่อยู่รูปโปรไฟล์มีอักขระไม่ถูกต้อง", "avatar_asset_path")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or re.match(r"^[A-Za-z]:", raw) or raw.startswith("//"):
        raise _invalid(
            "avatar_path_invalid",
            "ที่อยู่รูปโปรไฟล์ต้องเป็น path แบบสัมพัทธ์ภายในโปรเจกต์",
            "avatar_asset_path",
        )
    if any(part in ("..", ".") for part in pure.parts) or "" in raw.split("/"):
        raise _invalid("avatar_path_invalid", "ที่อยู่รูปโปรไฟล์มีส่วนที่ไม่อนุญาต (.. หรือ //)", "avatar_asset_path")
    if pure.suffix.lower() not in AVATAR_SUFFIXES:
        raise _invalid(
            "avatar_path_invalid",
            "รูปโปรไฟล์ต้องเป็นไฟล์ .jpg .jpeg .png หรือ .webp",
            "avatar_asset_path",
        )
    root = Path(project_root).resolve()
    resolved = (root / Path(*pure.parts)).resolve()
    if resolved != root and root not in resolved.parents:
        raise _invalid("avatar_path_invalid", "รูปโปรไฟล์ต้องอยู่ภายในโฟลเดอร์โปรเจกต์", "avatar_asset_path")
    return pure.as_posix()


def avatar_identity(avatar_path: str, *, project_root: Path) -> dict[str, Optional[str]]:
    """``{"path", "sha256"}``; sha256 is None when the file is missing/unsafe."""
    if not avatar_path:
        return {"path": "", "sha256": None}
    try:
        rel = normalize_avatar_path(avatar_path, project_root=project_root)
    except ChannelError:
        return {"path": avatar_path, "sha256": None}
    file_path = Path(project_root).resolve() / Path(*PurePosixPath(rel).parts)
    try:
        digest = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 16), b""):
                digest.update(chunk)
        return {"path": rel, "sha256": digest.hexdigest()}
    except OSError:
        return {"path": rel, "sha256": None}


def compute_identity_hash(channel: dict[str, Any], *, project_root: Path) -> str:
    """Stable sha256 (hex) of the identity fields.

    Hashed JSON (sorted keys, UTF-8, no whitespace)::

        {"avatar": {"path": <rel path>, "sha256": <file sha256|null>},
         "display_name": ..., "follow_title": ..., "handle": ...,
         "watermark_text": ...}

    ``id``/status/timezone are deliberately excluded (ADR).
    """
    payload = {
        "display_name": channel.get("display_name") or "",
        "handle": channel.get("handle") or "",
        "watermark_text": channel.get("watermark_text") or "",
        "follow_title": channel.get("follow_title") or "",
        "avatar": avatar_identity(channel.get("avatar_asset_path") or "", project_root=project_root),
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReadinessIssue:
    code: str
    message: str
    field: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "field": self.field}


_MISSING_MESSAGES = {
    "display_name": ("display_name_missing", "ยังไม่ได้ตั้งชื่อช่อง"),
    "handle": ("handle_missing", "ยังไม่ได้ระบุ handle ของช่อง"),
    "watermark_text": ("watermark_missing", "ยังไม่ได้ตั้งข้อความลายน้ำ"),
    "follow_title": ("follow_title_missing", "ยังไม่ได้ตั้งหัวข้อชวนกดติดตาม"),
    "avatar_asset_path": ("avatar_missing", "ยังไม่ได้เลือกรูปโปรไฟล์ช่อง"),
}


def profile_issues(
    channel: dict[str, Any],
    *,
    channels: Iterable[dict[str, Any]] = (),
    project_root: Optional[Path] = None,
    metrics: Optional[TextMetrics] = None,
) -> list[ReadinessIssue]:
    """Identity/profile completeness issues (status-independent).

    Re-validates stored values so a hand-edited registry cannot slip an
    over-long or invalid value into a final render.
    """
    root = Path(project_root) if project_root is not None else Path(config.CHANNELS_PROJECT_ROOT)
    issues: list[ReadinessIssue] = []
    for field_name in REQUIRED_PROFILE_FIELDS:
        if not (channel.get(field_name) or ""):
            code, message = _MISSING_MESSAGES[field_name]
            issues.append(ReadinessIssue(code, message, field_name))
    for field_name in TEXT_FIELD_LIMITS:
        value = channel.get(field_name) or ""
        if not value:
            continue
        try:
            normalized = normalize_text_field(field_name, value, metrics=metrics)
            if normalized != value:
                raise _invalid("text_not_normalized", f"{TEXT_FIELD_LIMITS[field_name].label_th}ยังไม่ผ่านการตรวจรูปแบบ กรุณาบันทึกใหม่", field_name)
        except ChannelError as exc:
            issues.append(ReadinessIssue(exc.code, exc.message, field_name))
    handle = channel.get("handle") or ""
    if handle:
        try:
            if normalize_handle(handle) != handle:
                raise HandleError("invalid_chars")
        except HandleError as exc:
            issues.append(ReadinessIssue("handle_invalid", exc.message, "handle"))
        else:
            for other in channels:
                if (
                    other.get("id") != channel.get("id")
                    and other.get("status") != STATUS_ARCHIVED
                    and (other.get("handle") or "") == handle
                ):
                    issues.append(
                        ReadinessIssue(
                            "handle_duplicate",
                            f"handle {handle} ซ้ำกับช่อง {other.get('id')}",
                            "handle",
                        )
                    )
    avatar = channel.get("avatar_asset_path") or ""
    if avatar:
        try:
            rel = normalize_avatar_path(avatar, project_root=root)
        except ChannelError as exc:
            issues.append(ReadinessIssue("avatar_path_invalid", exc.message, "avatar_asset_path"))
        else:
            if not (root.resolve() / Path(*PurePosixPath(rel).parts)).is_file():
                issues.append(
                    ReadinessIssue("avatar_file_missing", f"ไม่พบไฟล์รูปโปรไฟล์: {rel}", "avatar_asset_path")
                )
    try:
        normalize_timezone(channel.get("timezone"))
    except ChannelError as exc:
        issues.append(ReadinessIssue("timezone_invalid", exc.message, "timezone"))
    return issues


def readiness(
    channel: dict[str, Any],
    *,
    channels: Iterable[dict[str, Any]] = (),
    project_root: Optional[Path] = None,
    metrics: Optional[TextMetrics] = None,
) -> list[ReadinessIssue]:
    """Issues blocking final render/export for this channel (AC15).

    Empty list == ready.  Includes status (draft/archived) + profile issues.
    """
    issues: list[ReadinessIssue] = []
    status = channel.get("status")
    if status == STATUS_DRAFT:
        issues.append(ReadinessIssue("channel_draft", "ช่องยังเป็นฉบับร่าง (draft) ต้องเปิดใช้งานก่อน", "status"))
    elif status == STATUS_ARCHIVED:
        issues.append(ReadinessIssue("channel_archived", "ช่องถูกเก็บถาวร (archived) แล้ว", "status"))
    issues.extend(profile_issues(channel, channels=channels, project_root=project_root, metrics=metrics))
    return issues


def posting_issues(
    channel: dict[str, Any],
    *,
    channels: Iterable[dict[str, Any]] = (),
    project_root: Optional[Path] = None,
    metrics: Optional[TextMetrics] = None,
) -> list[ReadinessIssue]:
    """Issues blocking ``posting_enabled``/posting: readiness + verified account binding."""
    issues = readiness(channel, channels=channels, project_root=project_root, metrics=metrics)
    binding = channel.get("account_binding") or {}
    if binding.get("status") != BINDING_VERIFIED:
        issues.append(ReadinessIssue("account_unverified", "ยังไม่ได้ยืนยันบัญชี TikTok ของช่องนี้", "account_binding"))
    elif (binding.get("verified_handle") or "") != (channel.get("handle") or ""):
        issues.append(
            ReadinessIssue("account_handle_mismatch", "บัญชีที่ยืนยันไว้ไม่ตรงกับ handle ของช่อง", "account_binding")
        )
    return issues


# ---------------------------------------------------------------------------
# Registry document helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_binding() -> dict[str, Any]:
    return {"status": BINDING_UNVERIFIED, "verified_handle": None, "verified_at": None}


def _ordered_channel(channel: dict[str, Any]) -> dict[str, Any]:
    ordered = {key: channel[key] for key in CHANNEL_FIELD_ORDER if key in channel}
    for key, value in channel.items():  # preserve unknown (future) fields
        if key not in ordered:
            ordered[key] = value
    return ordered


def implicit_main_channel(*, project_root: Optional[Path] = None) -> dict[str, Any]:
    root = Path(project_root) if project_root is not None else Path(config.CHANNELS_PROJECT_ROOT)
    channel = dict(MAIN_SEED)
    channel.update(
        {
            "account_binding": _default_binding(),
            "overrides": {},
            "created_at": None,
            "updated_at": None,
            "revision": 0,
        }
    )
    channel["identity_hash"] = compute_identity_hash(channel, project_root=root)
    return _ordered_channel(channel)


def _corrupt(message: str) -> ChannelError:
    return ChannelError(500, "channel_registry_invalid", f"ไฟล์ทะเบียนช่อง (_Docs/channels.json) เสียหาย: {message}")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_document_shape(doc: Any) -> dict[str, Any]:
    """Structural validation on read; field-level problems surface via readiness."""
    if not isinstance(doc, dict):
        raise _corrupt("ต้องเป็น JSON object")
    version = doc.get("schema_version")
    if not _is_int(version):
        raise _corrupt("ไม่มี schema_version")
    if version > SCHEMA_VERSION:
        raise _corrupt(f"schema_version {version} ใหม่กว่าที่โปรแกรมรองรับ ({SCHEMA_VERSION})")
    if not _is_int(doc.get("revision")) or doc["revision"] < 0:
        raise _corrupt("revision ไม่ถูกต้อง")
    channels = doc.get("channels")
    if not isinstance(channels, list):
        raise _corrupt("channels ต้องเป็นรายการ")
    seen: set[str] = set()
    for channel in channels:
        if not isinstance(channel, dict):
            raise _corrupt("ข้อมูลช่องต้องเป็น object")
        cid = channel.get("id")
        if not is_valid_channel_id(cid):
            raise _corrupt(f"id ช่องไม่ถูกต้อง: {cid!r}")
        if cid in seen:
            raise _corrupt(f"id ช่องซ้ำ: {cid}")
        seen.add(cid)
        if channel.get("status") not in STATUSES:
            raise _corrupt(f"สถานะของช่อง {cid} ไม่ถูกต้อง")
        if not _is_int(channel.get("revision", 0)) or channel.get("revision", 0) < 0:
            raise _corrupt(f"revision ของช่อง {cid} ไม่ถูกต้อง")
        binding = channel.get("account_binding", _default_binding())
        if not isinstance(binding, dict) or binding.get("status") not in BINDING_STATUSES:
            raise _corrupt(f"account_binding ของช่อง {cid} ไม่ถูกต้อง")
        if not isinstance(channel.get("overrides", {}), dict):
            raise _corrupt(f"overrides ของช่อง {cid} ต้องเป็น object")
        if not isinstance(channel.get("posting_enabled", False), bool):
            raise _corrupt(f"posting_enabled ของช่อง {cid} ต้องเป็น true/false")
    return doc


def _fill_defaults(channel: dict[str, Any], *, project_root: Path) -> dict[str, Any]:
    out = dict(channel)
    for key in ("display_name", "handle", "watermark_text", "avatar_asset_path", "follow_title"):
        if out.get(key) is None:
            out[key] = ""
    out.setdefault("timezone", DEFAULT_TIMEZONE)
    out.setdefault("posting_enabled", False)
    out.setdefault("account_binding", _default_binding())
    out.setdefault("overrides", {})
    out.setdefault("created_at", None)
    out.setdefault("updated_at", None)
    out.setdefault("revision", 0)
    if not out.get("identity_hash"):
        out["identity_hash"] = compute_identity_hash(out, project_root=project_root)
    return _ordered_channel(out)


# ---------------------------------------------------------------------------
# Locks
# ---------------------------------------------------------------------------

_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock_for(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path))
    with _THREAD_LOCKS_GUARD:
        lock = _THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _THREAD_LOCKS[key] = lock
        return lock


class _FileLock:
    """Exclusive OS-level lock on ``<registry>.lock`` (released by the OS if the process dies)."""

    def __init__(self, path: Path, timeout: float = 15.0) -> None:
        self.path = path
        self.timeout = timeout
        self._fd: Optional[int] = None

    def __enter__(self) -> "_FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:  # pragma: no cover - POSIX
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise ChannelError(
                        409, "channel_registry_busy", "ทะเบียนช่องกำลังถูกบันทึกโดยงานอื่น กรุณาลองใหม่"
                    )
                time.sleep(0.01)
        self._fd = fd
        return self

    def __exit__(self, *exc: Any) -> None:
        fd = self._fd
        self._fd = None
        if fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - POSIX
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


# Read cache: path -> (stat signature, parsed document).  Invalidated by stat
# change and by every write from this process.
_READ_CACHE: dict[str, tuple[tuple[int, int, int], dict[str, Any]]] = {}
_READ_CACHE_GUARD = threading.Lock()


def _stat_signature(path: Path) -> Optional[tuple[int, int, int]]:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    return (st.st_mtime_ns, st.st_size, getattr(st, "st_ino", 0))


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class ChannelStore:
    """Validated, atomic, revisioned access to the channel registry.

    All public methods return deep copies; mutating a returned dict never
    touches the store.
    """

    def __init__(
        self,
        path: Optional[Path] = None,
        *,
        project_root: Optional[Path] = None,
        metrics: Optional[TextMetrics] = None,
        clock: Optional[Callable[[], str]] = None,
    ) -> None:
        self.path = Path(path) if path is not None else Path(config.CHANNELS_FILE)
        self.project_root = Path(project_root) if project_root is not None else Path(config.CHANNELS_PROJECT_ROOT)
        self.metrics = metrics or _DEFAULT_METRICS
        self._clock = clock or _utc_now
        self._lock = _thread_lock_for(self.path)

    @property
    def lock_path(self) -> Path:
        return self.path.with_name(self.path.name + ".lock")

    # -- reading -----------------------------------------------------------

    def exists(self) -> bool:
        return self.path.is_file()

    def _implicit_document(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "revision": 0,
            "channels": [implicit_main_channel(project_root=self.project_root)],
        }

    def _read_document(self) -> dict[str, Any]:
        """Parsed + defaulted document (shared cached object -- callers must copy).

        Runs under the per-path thread lock so an in-process reader's file
        handle never overlaps a writer's ``os.replace`` (Windows denies the
        replace while the target is open).
        """
        with self._lock:
            return self._read_document_locked()

    def _read_document_locked(self) -> dict[str, Any]:
        key = os.path.normcase(str(self.path))
        signature = _stat_signature(self.path)
        if signature is None:
            # Cache the implicit registry per avatar-file state (identity hash reads it).
            avatar = self.project_root / Path(*PurePosixPath(MAIN_SEED["avatar_asset_path"]).parts)
            implicit_key = f"{key}::implicit::{os.path.normcase(str(self.project_root))}"
            implicit_sig = _stat_signature(avatar) or (-1, -1, -1)
            with _READ_CACHE_GUARD:
                cached = _READ_CACHE.get(implicit_key)
                if cached and cached[0] == implicit_sig:
                    return cached[1]
            doc = self._implicit_document()
            with _READ_CACHE_GUARD:
                _READ_CACHE[implicit_key] = (implicit_sig, doc)
            return doc
        with _READ_CACHE_GUARD:
            cached = _READ_CACHE.get(key)
            if cached and cached[0] == signature:
                return cached[1]
        raw = None
        for attempt in range(100):
            try:
                raw = self.path.read_bytes()
                break
            except FileNotFoundError:
                # Only possible in the instant between unlink+rename on some
                # filesystems; os.replace itself never leaves the path missing.
                if attempt >= 5:
                    return self._implicit_document()
                time.sleep(0.01)
            except PermissionError as exc:
                # Windows: os.replace by another writer briefly locks the target.
                if attempt == 99:
                    raise _corrupt(f"อ่านไฟล์ไม่ได้ ({exc.__class__.__name__})")
                time.sleep(0.01)
            except OSError as exc:
                raise _corrupt(f"อ่านไฟล์ไม่ได้ ({exc.__class__.__name__})")
        # Cache under the signature taken BEFORE reading: if the file changed in
        # between, the next stat differs and forces a re-read (never stale).
        try:
            doc = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _corrupt(f"JSON ไม่ถูกต้อง ({exc.__class__.__name__})")
        doc = _validate_document_shape(doc)
        doc = dict(doc)
        doc["channels"] = [_fill_defaults(c, project_root=self.project_root) for c in doc["channels"]]
        if not any(c["id"] == config.DEFAULT_CHANNEL_ID for c in doc["channels"]):
            # The default channel is always resolvable; persisted on next write.
            doc["channels"].insert(0, implicit_main_channel(project_root=self.project_root))
        with _READ_CACHE_GUARD:
            _READ_CACHE[key] = (signature, doc)
        return doc

    def load(self) -> dict[str, Any]:
        """Whole registry document (deep copy). No side effects."""
        return copy.deepcopy(self._read_document())

    def revision(self) -> int:
        return int(self._read_document()["revision"])

    def list_channels(self, *, include_archived: bool = True) -> list[dict[str, Any]]:
        channels = self._read_document()["channels"]
        return [
            copy.deepcopy(c) for c in channels if include_archived or c.get("status") != STATUS_ARCHIVED
        ]

    def find(self, channel_id: Any) -> Optional[dict[str, Any]]:
        if not is_valid_channel_id(channel_id):
            return None
        for channel in self._read_document()["channels"]:
            if channel["id"] == channel_id:
                return copy.deepcopy(channel)
        return None

    def get(self, channel_id: Any) -> dict[str, Any]:
        channel = self.find(channel_id)
        if channel is None:
            raise ChannelError(404, "channel_not_found", f"ไม่พบช่อง {channel_id}")
        return channel

    def readiness(self, channel_id: str) -> list[ReadinessIssue]:
        doc = self._read_document()
        channel = self.get(channel_id)
        return readiness(channel, channels=doc["channels"], project_root=self.project_root, metrics=self.metrics)

    def posting_issues(self, channel_id: str) -> list[ReadinessIssue]:
        doc = self._read_document()
        channel = self.get(channel_id)
        return posting_issues(channel, channels=doc["channels"], project_root=self.project_root, metrics=self.metrics)

    # -- writing -----------------------------------------------------------

    def _write_document(self, doc: dict[str, Any]) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "revision": doc["revision"],
            "channels": [_ordered_channel(c) for c in doc["channels"]],
        }
        for key, value in doc.items():  # preserve unknown top-level keys
            if key not in payload:
                payload[key] = value
        _validate_document_shape(json.loads(json.dumps(payload)))
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent))
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            for attempt in range(50):
                try:
                    os.replace(tmp_path, self.path)
                    break
                except PermissionError:  # Windows: a reader briefly holds the target open
                    if attempt == 49:
                        raise
                    time.sleep(0.02)
        except BaseException:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        key = os.path.normcase(str(self.path))
        with _READ_CACHE_GUARD:
            _READ_CACHE.pop(key, None)

    def _mutate(self, fn: Callable[[dict[str, Any]], Any]) -> Any:
        """Run ``fn(doc)`` under the thread+file lock on a fresh read; write if changed.

        ``fn`` returns ``(result, changed)``.
        """
        with self._lock, _FileLock(self.lock_path):
            key = os.path.normcase(str(self.path))
            with _READ_CACHE_GUARD:
                _READ_CACHE.pop(key, None)  # always re-read under the lock
            doc = copy.deepcopy(self._read_document())
            result, changed = fn(doc)
            if changed:
                now = self._clock()
                for channel in doc["channels"]:
                    if not channel.get("created_at"):
                        # implicit main materialized by this first write
                        channel["created_at"] = now
                        channel["updated_at"] = channel.get("updated_at") or now
                        channel["revision"] = max(1, int(channel.get("revision", 0)))
                        if result is not None and isinstance(result, dict) and result.get("id") == channel["id"]:
                            result = channel
                doc["revision"] = int(doc["revision"]) + 1
                self._write_document(doc)
            return copy.deepcopy(result)

    @staticmethod
    def _index(doc: dict[str, Any], channel_id: Any) -> int:
        if is_valid_channel_id(channel_id):
            for i, channel in enumerate(doc["channels"]):
                if channel["id"] == channel_id:
                    return i
        raise ChannelError(404, "channel_not_found", f"ไม่พบช่อง {channel_id}")

    @staticmethod
    def _check_expected(actual: int, expected: Any, *, what: str, required: bool) -> None:
        if expected is None:
            if required:
                raise _invalid("expected_revision_required", "ต้องส่ง expected_revision ทุกครั้งที่แก้ไขช่อง", "expected_revision")
            return
        if not _is_int(expected) or expected < 0:
            raise _invalid("expected_revision_invalid", "expected_revision ต้องเป็นจำนวนเต็มไม่ติดลบ", "expected_revision")
        if expected != actual:
            raise ChannelError(
                409,
                "revision_conflict",
                f"ข้อมูล{what}ถูกแก้ไขไปแล้ว (revision ปัจจุบัน {actual}) กรุณาโหลดใหม่ก่อนบันทึก",
                current_revision=actual,
            )

    def _normalize_editable(self, changes: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in changes.items():
            if key in TEXT_FIELD_LIMITS:
                out[key] = normalize_text_field(key, value, metrics=self.metrics)
            elif key == "handle":
                out[key] = "" if value is None or (isinstance(value, str) and not value.strip(HANDLE_TRIM_CHARS)) else normalize_handle(value)
            elif key == "avatar_asset_path":
                out[key] = normalize_avatar_path(value, project_root=self.project_root)
            elif key == "timezone":
                out[key] = normalize_timezone(value)
            elif key == "posting_enabled":
                if not isinstance(value, bool):
                    raise _invalid("posting_enabled_invalid", "posting_enabled ต้องเป็น true หรือ false", key)
                out[key] = value
            elif key == "overrides":
                if not isinstance(value, dict):
                    raise _invalid("overrides_invalid", "overrides ต้องเป็น object", key)
                try:
                    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
                except (TypeError, ValueError):
                    raise _invalid("overrides_invalid", "overrides ต้องเป็น JSON ธรรมดา", key)
                if len(encoded.encode("utf-8")) > 16_384:
                    raise _invalid("overrides_invalid", "overrides ใหญ่เกิน 16KB", key)
                out[key] = json.loads(encoded)
            else:
                raise _invalid("field_not_editable", f"แก้ไขฟิลด์ {key} ผ่านคำสั่งนี้ไม่ได้", key)
        return out

    def _check_handle_unique(self, doc: dict[str, Any], channel: dict[str, Any]) -> None:
        handle = channel.get("handle") or ""
        if not handle or channel.get("status") == STATUS_ARCHIVED:
            return
        for other in doc["channels"]:
            if other["id"] != channel["id"] and other.get("status") != STATUS_ARCHIVED and other.get("handle") == handle:
                raise ChannelError(
                    409,
                    "handle_conflict",
                    f"handle {handle} ถูกใช้แล้วโดยช่อง {other['id']}",
                    field="handle",
                    conflicting_channel_id=other["id"],
                )

    def _check_posting(self, doc: dict[str, Any], channel: dict[str, Any]) -> None:
        if not channel.get("posting_enabled"):
            return
        issues = posting_issues(channel, channels=doc["channels"], project_root=self.project_root, metrics=self.metrics)
        if issues:
            raise ChannelError(
                409,
                "posting_not_allowed",
                f"ยังเปิดโพสต์ให้ช่อง {channel['id']} ไม่ได้: {issues[0].message}",
                issues=[i.to_dict() for i in issues],
            )

    def _check_active_profile(self, doc: dict[str, Any], channel: dict[str, Any]) -> None:
        issues = profile_issues(channel, channels=doc["channels"], project_root=self.project_root, metrics=self.metrics)
        if issues:
            raise ChannelError(
                409,
                "channel_not_ready",
                f"ช่อง {channel['id']} ข้อมูลยังไม่ครบ: {issues[0].message}",
                issues=[i.to_dict() for i in issues],
            )

    def _finalize(self, channel: dict[str, Any], before: Optional[dict[str, Any]]) -> tuple[dict[str, Any], bool]:
        channel["identity_hash"] = compute_identity_hash(channel, project_root=self.project_root)
        if before is not None and channel == before:
            return before, False
        now = self._clock()
        channel["updated_at"] = now
        if before is None:
            channel["created_at"] = now
            channel["revision"] = 1
        else:
            channel["revision"] = int(before.get("revision", 0)) + 1
        return _ordered_channel(channel), True

    def seed(self) -> dict[str, Any]:
        """Persist the registry (with ``main``) if the file is missing. Idempotent."""

        def apply(doc: dict[str, Any]):
            # Implicit channels (never written) have created_at None; _mutate stamps them.
            needs_write = not self.exists() or any(not c.get("created_at") for c in doc["channels"])
            return None, needs_write

        self._mutate(apply)
        return self.load()

    def create(self, data: dict[str, Any], *, expected_registry_revision: Any = None) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise _invalid("payload_invalid", "ข้อมูลช่องต้องเป็น object")
        unknown = set(data) - set(CREATE_FIELDS)
        if unknown:
            name = sorted(unknown)[0]
            raise _invalid("field_not_editable", f"ตั้งค่าฟิลด์ {name} ตอนสร้างช่องไม่ได้", name)
        channel_id = data.get("id")
        if not is_valid_channel_id(channel_id):
            raise _invalid(
                "channel_id_invalid",
                "id ช่องต้องขึ้นต้นด้วย a-z ตามด้วย a-z 0-9 _ - รวม 2-32 ตัว",
                "id",
            )
        fields = self._normalize_editable({k: v for k, v in data.items() if k != "id"})
        if not fields.get("display_name"):
            raise _invalid("display_name_required", "กรุณาตั้งชื่อช่อง", "display_name")
        if fields.get("posting_enabled"):
            raise ChannelError(409, "posting_not_allowed", "ช่องใหม่เป็นฉบับร่าง (draft) จึงยังเปิดโพสต์ไม่ได้", field="posting_enabled")

        def apply(doc: dict[str, Any]):
            self._check_expected(int(doc["revision"]), expected_registry_revision, what="ทะเบียนช่อง", required=False)
            if any(c["id"] == channel_id for c in doc["channels"]):
                raise ChannelError(409, "channel_exists", f"มีช่อง id {channel_id} อยู่แล้ว (id ใช้ซ้ำไม่ได้)", field="id")
            channel = _fill_defaults(
                {
                    "id": channel_id,
                    "display_name": "",
                    "handle": "",
                    "watermark_text": "",
                    "avatar_asset_path": "",
                    "follow_title": "",
                    "timezone": DEFAULT_TIMEZONE,
                    "status": STATUS_DRAFT,
                    "posting_enabled": False,
                    **fields,
                },
                project_root=self.project_root,
            )
            self._check_handle_unique(doc, channel)
            channel, _ = self._finalize(channel, None)
            doc["channels"].append(channel)
            return channel, True

        return self._mutate(apply)

    def update(self, channel_id: str, changes: dict[str, Any], *, expected_revision: Any) -> dict[str, Any]:
        if not isinstance(changes, dict):
            raise _invalid("payload_invalid", "ข้อมูลที่แก้ไขต้องเป็น object")
        if "id" in changes:
            raise _invalid("channel_id_immutable", "เปลี่ยน id ของช่องไม่ได้", "id")
        fields = self._normalize_editable(changes)

        def apply(doc: dict[str, Any]):
            idx = self._index(doc, channel_id)
            before = doc["channels"][idx]
            self._check_expected(int(before.get("revision", 0)), expected_revision, what=f"ช่อง {channel_id}", required=True)
            if before["status"] == STATUS_ARCHIVED:
                raise ChannelError(
                    409,
                    "channel_archived",
                    f"ช่อง {channel_id} อยู่ในสถานะ{STATUS_LABEL_TH[STATUS_ARCHIVED]} แก้ไขไม่ได้ ต้องเปิดใช้งานก่อน",
                )
            channel = copy.deepcopy(before)
            channel.update(fields)
            if "display_name" in fields and not channel["display_name"]:
                raise _invalid("display_name_required", "กรุณาตั้งชื่อช่อง", "display_name")
            if channel.get("handle") != before.get("handle"):
                # A verified binding belongs to the old handle: re-verify (P5).
                channel["account_binding"] = _default_binding()
                if "posting_enabled" not in fields:
                    channel["posting_enabled"] = False
            self._check_handle_unique(doc, channel)
            if channel["status"] == STATUS_ACTIVE:
                missing = [f for f in REQUIRED_PROFILE_FIELDS if not channel.get(f)]
                if missing:
                    code, message = _MISSING_MESSAGES[missing[0]]
                    raise _invalid(code, f"ช่องที่ใช้งานอยู่ต้องมีข้อมูลครบ: {message}", missing[0])
            if channel.get("posting_enabled") and not before.get("posting_enabled"):
                # Gate the false->true transition only; posting itself re-checks
                # readiness (P5), so an unrelated edit is never blocked by it.
                self._check_posting(doc, channel)
            channel, changed = self._finalize(channel, before)
            doc["channels"][idx] = channel
            return channel, changed

        return self._mutate(apply)

    def activate(self, channel_id: str, *, expected_revision: Any = None) -> dict[str, Any]:
        def apply(doc: dict[str, Any]):
            idx = self._index(doc, channel_id)
            before = doc["channels"][idx]
            self._check_expected(int(before.get("revision", 0)), expected_revision, what=f"ช่อง {channel_id}", required=False)
            if before["status"] == STATUS_ACTIVE:
                return before, False
            channel = copy.deepcopy(before)
            channel["status"] = STATUS_ACTIVE
            self._check_handle_unique(doc, channel)
            self._check_active_profile(doc, channel)
            channel, changed = self._finalize(channel, before)
            doc["channels"][idx] = channel
            return channel, changed

        return self._mutate(apply)

    def archive(self, channel_id: str, *, expected_revision: Any = None) -> dict[str, Any]:
        def apply(doc: dict[str, Any]):
            idx = self._index(doc, channel_id)
            before = doc["channels"][idx]
            self._check_expected(int(before.get("revision", 0)), expected_revision, what=f"ช่อง {channel_id}", required=False)
            if channel_id == config.DEFAULT_CHANNEL_ID:
                raise ChannelError(409, "default_channel_protected", "ช่องหลัก (main) เก็บถาวรไม่ได้")
            if before["status"] == STATUS_ARCHIVED:
                return before, False
            channel = copy.deepcopy(before)
            channel["status"] = STATUS_ARCHIVED
            channel["posting_enabled"] = False
            channel, changed = self._finalize(channel, before)
            doc["channels"][idx] = channel
            return channel, changed

        return self._mutate(apply)

    def set_account_binding(
        self,
        channel_id: str,
        *,
        status: str,
        verified_handle: Optional[str] = None,
        verified_at: Optional[str] = None,
        expected_revision: Any = None,
    ) -> dict[str, Any]:
        """Internal setter (no HTTP route in P1; P5 calls it after a real account check)."""
        if status not in BINDING_STATUSES:
            raise _invalid("account_binding_invalid", "สถานะการยืนยันบัญชีไม่ถูกต้อง", "account_binding")
        if status == BINDING_VERIFIED:
            handle = normalize_handle(verified_handle)
            if not isinstance(verified_at, str) or not verified_at:
                verified_at = self._clock()
            binding = {"status": status, "verified_handle": handle, "verified_at": verified_at}
        else:
            binding = _default_binding()

        def apply(doc: dict[str, Any]):
            idx = self._index(doc, channel_id)
            before = doc["channels"][idx]
            self._check_expected(int(before.get("revision", 0)), expected_revision, what=f"ช่อง {channel_id}", required=False)
            if status == BINDING_VERIFIED and binding["verified_handle"] != before.get("handle"):
                raise ChannelError(
                    409,
                    "account_handle_mismatch",
                    f"บัญชีที่ตรวจพบ {binding['verified_handle']} ไม่ตรงกับ handle ของช่อง ({before.get('handle') or '-'})",
                )
            channel = copy.deepcopy(before)
            channel["account_binding"] = binding
            if status != BINDING_VERIFIED:
                channel["posting_enabled"] = False
            channel, changed = self._finalize(channel, before)
            doc["channels"][idx] = channel
            return channel, changed

        return self._mutate(apply)


def get_default_store() -> ChannelStore:
    """Store bound to ``config.CHANNELS_FILE`` / ``config.CHANNELS_PROJECT_ROOT``.

    Both are looked up at call time so tests can monkeypatch them.
    """
    return ChannelStore(Path(config.CHANNELS_FILE), project_root=Path(config.CHANNELS_PROJECT_ROOT))
