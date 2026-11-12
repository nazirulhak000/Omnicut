"""TikTok sharpness for a freshly rendered export, in place.

After a successful render the clip goes through the same sharpness pass as the
gallery's manual button (``scripts.tiktok_enhancer``), but the result replaces
the rendered file: same path, same export id, so the cover binding, the
product angle and the posting queue keep pointing at one clip.

Rules:
- Runs before the default cover, so the cover frame comes from the final file.
- The export record keeps a marker with the sharpened file's size and
  modified time.  A clip counts as sharpened only while the file still matches
  it, so a re-render to the same path is sharpened again and never shown as
  already done.
- Failure never propagates: the render that triggered it still succeeds and
  the unsharpened clip stays exactly as rendered.
- ``OMNICUT_AUTO_TIKTOK_SHARP=0`` switches the whole step off.
"""
from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from scripts import config
from scripts.export_registry import TIKTOK_SHARP_FIELD, ExportRegistry

logger = logging.getLogger(__name__)

ENV_SWITCH = "OMNICUT_AUTO_TIKTOK_SHARP"
# The manual button writes a second file with this suffix; it is already sharp.
MANUAL_SUFFIX = "_tiktok_sharp"
_OFF_VALUES = {"0", "false", "off", "no"}
# Coarse filesystems (exFAT, network shares) round modified times to 2 s.
_MTIME_TOLERANCE_NS = 2_000_000_000


def is_enabled() -> bool:
    return os.environ.get(ENV_SWITCH, "1").strip().lower() not in _OFF_VALUES


def fingerprint(video: Path) -> Dict[str, int]:
    stat = video.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def is_sharpened(record: Optional[Mapping[str, Any]], video: Path) -> bool:
    """True while ``video`` is still the file the marker on ``record`` describes."""
    marker = (record or {}).get(TIKTOK_SHARP_FIELD)
    if not isinstance(marker, Mapping):
        return False
    try:
        now = fingerprint(video)
        return (int(marker["size"]) == now["size"]
                and abs(int(marker["mtime_ns"]) - now["mtime_ns"]) <= _MTIME_TOLERANCE_NS)
    except (KeyError, TypeError, ValueError, OSError):
        return False


def ensure_tiktok_sharp(export_id: Optional[str], *, channel_id: Optional[str] = None) -> Dict[str, Any]:
    """Sharpen the export's file in place unless it already is.

    Returns ``{"status": "sharpened" | "kept" | "skipped" | "failed", ...}`` and
    never raises.
    """
    if not is_enabled():
        return {"status": "skipped", "reason": "disabled"}
    if not export_id:
        return {"status": "skipped", "reason": "no_export_id"}
    try:
        outcome = _sharpen(export_id, channel_id)
    except Exception as exc:  # sharpness must never fail the render
        logger.warning("[AutoSharp] ปรับความคมชัดอัตโนมัติไม่สำเร็จ (%s) ใช้ไฟล์เรนเดอร์เดิมต่อ: %s", export_id, exc)
        return {"status": "failed", "reason": str(exc)}
    if outcome["status"] == "sharpened":
        logger.info("[AutoSharp] ปรับความคมชัด TikTok ให้ %s แล้ว (%.1f MB)", export_id, outcome["size_bytes"] / 1024 ** 2)
    return outcome


def _sharpen(export_id: str, channel_id: Optional[str]) -> Dict[str, Any]:
    row = ExportRegistry.get(export_id, channel_id=channel_id)
    if not row or not row.get("path"):
        return {"status": "skipped", "reason": "export_not_found"}
    video = Path(row["path"])
    video = video if video.is_absolute() else config.BASE_DIR / video
    if not video.is_file():
        return {"status": "skipped", "reason": "video_missing"}
    if MANUAL_SUFFIX in video.stem:
        return {"status": "kept", "reason": "manual_sharp_copy"}
    if is_sharpened(row, video):
        return {"status": "kept", "reason": "already_sharp"}

    # Imported here: the enhancer probes ffmpeg encoders on import, which a
    # caller with the switch off should not pay for.
    from scripts.tiktok_enhancer import enhance_video_for_tiktok

    # Output == input: the enhancer encodes to a ``.partial.mp4`` sibling
    # (ignored by every export scanner), verifies it against the source and
    # only then replaces the file, so a failed pass leaves the render intact.
    enhance_video_for_tiktok(video, video)

    marker = {"at": datetime.datetime.now().isoformat(timespec="seconds"), **fingerprint(video)}
    ExportRegistry.set_tiktok_sharp(export_id, marker, channel_id=channel_id)
    return {"status": "sharpened", "size_bytes": marker["size"]}
