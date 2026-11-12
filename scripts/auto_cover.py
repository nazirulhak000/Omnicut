"""Default cover for a freshly rendered export.

After a successful render the clip gets a clean-frame cover (9:16 + 3:4, no
hook text) so it never reaches the posting queue without one.  The frame is
the same recommended moment Cover Studio opens on.

Rules:
- A cover a person saved is never replaced (export binding or product angle).
- A cover this module made is tagged ``auto`` and is regenerated when the
  export's video is newer than the cover file.
- Failure never propagates: the render that triggered it still succeeds.
- ``OMNICUT_AUTO_COVER=0`` switches the whole step off.
- Superseded automatic cover files stay on disk (deleting needs the owner).
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from scripts import config
from scripts.channel_ownership import OWNER_KEY
from scripts.channel_scope import ChannelError
from scripts.export_cover_bindings import ExportCoverBindingStore
from scripts.export_registry import ExportRegistry
from scripts.product_store import ProductStore

logger = logging.getLogger(__name__)

ENV_SWITCH = "OMNICUT_AUTO_COVER"
FALLBACK_SECONDS = 1.0
_OFF_VALUES = {"0", "false", "off", "no"}
_COVER_KEYS = ("cover_path", "cover_9x16_path", "cover_3x4_path")


def is_enabled() -> bool:
    return os.environ.get(ENV_SWITCH, "1").strip().lower() not in _OFF_VALUES


def ensure_default_cover(
    export_id: Optional[str],
    *,
    channel_id: Optional[str] = None,
    product_id: Optional[str] = None,
    angle_id: Optional[str] = None,
    batch: Optional[int] = None,
) -> Dict[str, Any]:
    """Give ``export_id`` a default cover unless one already stands.

    Returns ``{"status": "created" | "kept" | "skipped" | "failed", ...}`` and
    never raises.
    """
    if not is_enabled():
        return {"status": "skipped", "reason": "disabled"}
    if not export_id:
        return {"status": "skipped", "reason": "no_export_id"}
    try:
        outcome = _ensure(export_id, channel_id, product_id, angle_id, batch)
    except Exception as exc:  # a default cover must never fail the render
        logger.warning("[AutoCover] สร้างปกอัตโนมัติไม่สำเร็จ (%s): %s", export_id, exc)
        return {"status": "failed", "reason": str(exc)}
    if outcome["status"] == "created":
        logger.info("[AutoCover] สร้างปกอัตโนมัติให้ %s ที่ %.2f วิ", export_id, outcome["at_seconds"])
    return outcome


def _find_angle(product_id, angle_id, batch, channel_id) -> Optional[Dict[str, Any]]:
    """Same matching as ``ProductStore.update_angle_cover``."""
    if not product_id or not angle_id:
        return None
    product = ProductStore.get(product_id, channel_id=channel_id)
    if not product:
        return None
    if batch is None:
        suffix = re.search(r"_b(\d+)$", str(angle_id))
        if suffix:
            batch = int(suffix.group(1))
    for angle in product.get("angles", []):
        if (angle.get("angle_id") or angle.get("id")) != angle_id:
            continue
        if batch is not None and (angle.get("batch") or 1) != batch:
            continue
        return angle
    return None


def _is_current(cover_rel: Optional[str], video: Path) -> bool:
    if not cover_rel:
        return False
    cover = config.BASE_DIR / cover_rel
    try:
        return cover.is_file() and cover.stat().st_mtime >= video.stat().st_mtime
    except OSError:
        return False


def _ensure(export_id, channel_id, product_id, angle_id, batch) -> Dict[str, Any]:
    row = ExportRegistry.get(export_id, channel_id=channel_id)
    if not row or not row.get("path"):
        return {"status": "skipped", "reason": "export_not_found"}
    video = Path(row["path"])
    video = video if video.is_absolute() else config.BASE_DIR / video
    if not video.is_file():
        return {"status": "skipped", "reason": "video_missing"}
    channel = row.get(OWNER_KEY) or channel_id or config.DEFAULT_CHANNEL_ID

    bindings = ExportCoverBindingStore(config.BASE_DIR)
    bound_by = bindings.source_of(channel, export_id)
    if bound_by == "manual":
        return {"status": "kept", "reason": "manual_cover"}

    angle = _find_angle(product_id, angle_id, batch, channel_id)
    angle_has_cover = bool(angle and any(angle.get(key) for key in _COVER_KEYS))
    if angle_has_cover and angle.get("cover_source") != "auto":
        return {"status": "kept", "reason": "manual_cover"}

    if bound_by == "auto":
        try:
            current = (bindings.get(channel, export_id) or {}).get("path")
        except ChannelError:  # bound file missing or changed -> make a new one
            current = None
        if _is_current(current, video):
            return {"status": "kept", "reason": "auto_cover_current", "cover_path": current}

    # Imported here: api_covers pulls in FastAPI routes and Pillow, which a
    # render worker should not pay for unless it actually builds a cover.
    from scripts.api_covers import recommended_cover_timestamp, register_companion, render_pro_cover

    at_seconds = recommended_cover_timestamp(video)
    if at_seconds is None:
        at_seconds = FALLBACK_SECONDS
    cover_root = config.COVERS_DIR / channel / uuid.uuid4().hex
    primary, three_four = render_pro_cover(
        video_path_str=str(video),
        at_seconds=at_seconds,
        aspect_ratio="both",
        enable_hook_text=False,
        enable_badge=False,
        output_dir=cover_root,
    )
    rel_9x16 = primary.relative_to(config.BASE_DIR).as_posix()
    register_companion(rel_9x16, channel)
    selections = {"9:16": rel_9x16}
    rel_3x4 = None
    if three_four and three_four.exists():
        rel_3x4 = three_four.relative_to(config.BASE_DIR).as_posix()
        register_companion(rel_3x4, channel)
        selections["3:4"] = rel_3x4

    outcome: Dict[str, Any] = {
        "status": "created", "cover_path": rel_9x16, "cover_3x4_path": rel_3x4,
        "at_seconds": float(at_seconds), "bound": False, "angle_updated": False,
    }
    try:
        bindings.save(channel, export_id, str(video), selections, source="auto")
        outcome["bound"] = True
    except Exception as exc:  # legacy export rows have no channel to bind under
        logger.warning("[AutoCover] ผูกปกกับ export %s ไม่สำเร็จ: %s", export_id, exc)

    if angle is not None:
        try:
            ProductStore.update_angle_cover(
                product_id, angle_id,
                cover_path=rel_9x16, cover_3x4_path=rel_3x4, cover_9x16_path=rel_9x16,
                batch=batch, channel_id=channel_id, cover_source="auto",
            )
            outcome["angle_updated"] = True
        except Exception as exc:
            logger.warning("[AutoCover] บันทึกปกลง angle %s ไม่สำเร็จ: %s", angle_id, exc)
    return outcome
