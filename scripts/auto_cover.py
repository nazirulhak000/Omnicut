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
- Superseded automatic UUID cover folders that are no longer referenced by
  ``ExportCoverBindingStore``, ``ProductStore``, or ``PostingJobStore`` are
  cleaned up safely after replacement.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

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
_HEX_UUID_RE = re.compile(r"^[0-9a-f]{32}$")


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


def _binding_state(bindings: ExportCoverBindingStore, channel_id: str, export_id: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Determine binding source and valid current cover paths.

    Returns: (source, path_9x16, path_3x4)
    If source == "auto" and either format is missing, invalid, or changed,
    catches ChannelError and returns ("auto", None, None).
    """
    source = bindings.source_of(channel_id, export_id)
    if source != "auto":
        return source, None, None
    try:
        e9 = bindings.get(channel_id, export_id, format="9:16")
        e3 = bindings.get(channel_id, export_id, format="3:4")
        p9 = (e9 or {}).get("path")
        p3 = (e3 or {}).get("path")
        if not p9 or not p3:
            return "auto", None, None
        return "auto", p9, p3
    except ChannelError:
        return "auto", None, None


def _is_current(cover_rel: Optional[str], video: Path) -> bool:
    if not cover_rel:
        return False
    cover = config.BASE_DIR / cover_rel
    try:
        return cover.is_file() and cover.stat().st_mtime >= video.stat().st_mtime
    except OSError:
        return False


def _normalize_rel_cover_path(raw: Any, base_dir: Path) -> Optional[str]:
    if not isinstance(raw, str) or not raw.strip():
        return None
    p = Path(raw.strip())
    if p.is_absolute():
        try:
            p = p.resolve(strict=False).relative_to(base_dir.resolve(strict=False))
        except ValueError:
            return None
    return p.as_posix()


def _is_auto_uuid_dir(path: Path, covers_dir: Path, channel: Optional[str] = None) -> bool:
    if not path.is_dir() or not _HEX_UUID_RE.match(path.name):
        return False
    try:
        resolved_covers = covers_dir.resolve(strict=False)
        resolved_dir = path.resolve(strict=False)
        if resolved_dir.parent.parent != resolved_covers:
            return False
        if channel and resolved_dir.parent.name != channel:
            return False
        return True
    except OSError:
        return False


def _referenced_cover_paths(base_dir: Path, bindings: Optional[ExportCoverBindingStore] = None) -> Set[str]:
    """Collect every cover path still referenced by bindings, products, or posting jobs."""
    store = bindings or ExportCoverBindingStore(base_dir)
    referenced: Set[str] = set()
    for row in store._rows("export_cover_bindings"):
        for sel in (row.get("selections") or {}).values():
            if isinstance(sel, dict):
                norm = _normalize_rel_cover_path(sel.get("path"), base_dir)
                if norm:
                    referenced.add(norm)
    for prod in store._rows("products"):
        for angle in prod.get("angles") or []:
            if not isinstance(angle, dict):
                continue
            for key in _COVER_KEYS:
                norm = _normalize_rel_cover_path(angle.get(key), base_dir)
                if norm:
                    referenced.add(norm)
    for job in store._rows("posting_jobs"):
        norm = _normalize_rel_cover_path(job.get("cover_path"), base_dir)
        if norm:
            referenced.add(norm)
    return referenced


def _cleanup_superseded_auto_dirs(
    base_dir: Path,
    covers_dir: Path,
    channel: str,
    superseded_paths: Iterable[Optional[str]],
    *,
    exclude_dir: Optional[Path] = None,
    bindings: Optional[ExportCoverBindingStore] = None,
) -> List[str]:
    """Remove superseded auto UUID cover directories once no store references them."""
    candidates: List[Path] = []
    seen_dirs: Set[Path] = set()
    for raw in superseded_paths:
        rel = _normalize_rel_cover_path(raw, base_dir)
        if not rel:
            continue
        candidate_dir = (base_dir / rel).parent
        if exclude_dir is not None and candidate_dir.resolve(strict=False) == exclude_dir.resolve(strict=False):
            continue
        if candidate_dir not in seen_dirs and _is_auto_uuid_dir(candidate_dir, covers_dir, channel=channel):
            seen_dirs.add(candidate_dir)
            candidates.append(candidate_dir)

    if not candidates:
        return []

    referenced = _referenced_cover_paths(base_dir, bindings=bindings)
    removed: List[str] = []
    for cand in candidates:
        files = [
            f.relative_to(base_dir).as_posix()
            for f in cand.rglob("*")
            if f.is_file() and f.parent.name != ".cache"
        ]
        if any(f in referenced for f in files):
            continue
        shutil.rmtree(cand, ignore_errors=True)
        if not cand.exists():
            removed.append(cand.relative_to(base_dir).as_posix())
    return removed


def cleanup_orphaned_auto_covers(
    base_dir: Optional[Path] = None,
    *,
    channel_id: Optional[str] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Scan 05_Covers_Thumbnails/<channel>/<32-hex-uuid>/ for unreferenced auto cover folders."""
    root = Path(base_dir) if base_dir is not None else config.BASE_DIR
    covers_dir = (root / "05_Covers_Thumbnails") if base_dir is not None else config.COVERS_DIR
    if not covers_dir.is_dir():
        return {"dry_run": dry_run, "scanned": 0, "orphans": [], "removed": []}

    referenced = _referenced_cover_paths(root)
    channels = [covers_dir / channel_id] if channel_id else [p for p in covers_dir.iterdir() if p.is_dir()]
    scanned = 0
    orphans: List[str] = []
    removed: List[str] = []
    for ch_dir in channels:
        if not ch_dir.is_dir():
            continue
        for sub in sorted(ch_dir.iterdir()):
            if not _is_auto_uuid_dir(sub, covers_dir, channel=ch_dir.name):
                continue
            scanned += 1
            files = [
                f.relative_to(root).as_posix()
                for f in sub.rglob("*")
                if f.is_file() and f.parent.name != ".cache"
            ]
            if any(f in referenced for f in files):
                continue
            rel_dir = sub.relative_to(root).as_posix()
            orphans.append(rel_dir)
            if not dry_run:
                shutil.rmtree(sub, ignore_errors=True)
                if not sub.exists():
                    removed.append(rel_dir)
    return {"dry_run": dry_run, "scanned": scanned, "orphans": orphans, "removed": removed}


def _ensure(export_id, channel_id, product_id, angle_id, batch) -> Dict[str, Any]:
    row = ExportRegistry.get(export_id, channel_id=channel_id)
    if not row or not row.get("path"):
        return {"status": "skipped", "reason": "export_not_found"}
    video = Path(row["path"])
    video = video if video.is_absolute() else config.BASE_DIR / video
    if not video.is_file():
        return {"status": "skipped", "reason": "video_missing"}
    channel = row.get(OWNER_KEY) or channel_id or config.DEFAULT_CHANNEL_ID
    if not product_id:
        product_id = row.get("product_id")
    if not angle_id:
        angle_id = row.get("angle_id")
    if batch is None:
        batch = row.get("batch")

    bindings = ExportCoverBindingStore(config.BASE_DIR)
    bound_by, current_9, current_3 = _binding_state(bindings, channel, export_id)
    if bound_by == "manual":
        return {"status": "kept", "reason": "manual_cover"}

    angle = _find_angle(product_id, angle_id, batch, channel_id)
    angle_has_cover = bool(angle and any(angle.get(key) for key in _COVER_KEYS))
    if angle_has_cover and angle.get("cover_source") != "auto":
        return {"status": "kept", "reason": "manual_cover"}

    if bound_by == "auto":
        if (
            current_9
            and current_3
            and _is_current(current_9, video)
            and _is_current(current_3, video)
        ):
            return {"status": "kept", "reason": "auto_cover_current", "cover_path": current_9}

    superseded_paths: List[Optional[str]] = []
    if bound_by == "auto":
        superseded_paths.extend([current_9, current_3])
        for row_b in bindings._rows("export_cover_bindings"):
            if row_b.get("channel_id") == channel and row_b.get("export_id") == export_id:
                for sel in (row_b.get("selections") or {}).values():
                    if isinstance(sel, dict):
                        superseded_paths.append(sel.get("path"))
    if angle and angle.get("cover_source") == "auto":
        superseded_paths.extend(angle.get(k) for k in _COVER_KEYS)

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

    if (outcome["bound"] or outcome["angle_updated"]) and superseded_paths:
        removed_dirs = _cleanup_superseded_auto_dirs(
            config.BASE_DIR,
            config.COVERS_DIR,
            channel,
            superseded_paths,
            exclude_dir=cover_root,
            bindings=bindings,
        )
        if removed_dirs:
            outcome["cleaned_dirs"] = removed_dirs
    return outcome


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Clean up unreferenced auto-generated cover UUID folders.")
    parser.add_argument("--channel", default=None, help="Restrict scan to one channel id")
    parser.add_argument("--apply", action="store_true", help="Delete orphaned folders (default is --dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Report orphaned folders without deleting (default)")
    args = parser.parse_args()
    summary = cleanup_orphaned_auto_covers(channel_id=args.channel, dry_run=not args.apply)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
