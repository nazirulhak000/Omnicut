# -*- coding: utf-8 -*-
"""Colab persistence & Google Drive Export Architecture synchronization helper."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Dict, Optional, Union

from scripts.config import BASE_DIR
from scripts.couple_engine.inspect import _MINIMAL_WEBP_BYTES

DEFAULT_COLAB_GDRIVE_ROOT = Path("/content/drive/MyDrive/Omnicut_Exports")


def _resolve_ready_dir(gdrive_root: Optional[Union[Path, str]]) -> Optional[Path]:
    """Resolve the target `01_Ready_to_post` directory on Google Drive if mounted/configured."""
    raw = gdrive_root or os.environ.get("OMNICUT_GDRIVE_ROOT", "").strip()
    if raw:
        root_p = Path(raw)
        if root_p.name == "01_Ready_to_post":
            return root_p
        return root_p / "01_Ready_to_post"

    # Default Colab path check
    colab_drive_mount = Path("/content/drive/MyDrive")
    if colab_drive_mount.exists():
        return DEFAULT_COLAB_GDRIVE_ROOT / "01_Ready_to_post"
    return None


def snapshot_store_db(
    db_path: Optional[Union[Path, str]] = None,
    snapshot_dir: Optional[Union[Path, str]] = None,
) -> Optional[Path]:
    """Create a crash-safe offline snapshot of `store.db` onto Google Drive without live locking."""
    src_db = Path(db_path) if db_path is not None else (BASE_DIR / "_Docs" / "store.db")
    if not src_db.exists():
        return None

    target_dir = Path(snapshot_dir) if snapshot_dir is not None else (DEFAULT_COLAB_GDRIVE_ROOT / "_snapshots")
    target_dir.mkdir(parents=True, exist_ok=True)
    dst_db = target_dir / "store.db"
    tmp_db = target_dir / "store.db.tmp"

    try:
        src_conn = sqlite3.connect(str(src_db), timeout=15.0)
        dst_conn = sqlite3.connect(str(tmp_db), timeout=15.0)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        os.replace(tmp_db, dst_db)
    except Exception:
        shutil.copy2(src_db, dst_db)
    return dst_db


def sync_export_to_gdrive(
    mp4_path: Union[Path, str],
    caption_text: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    cover_paths: Optional[Dict[str, Any]] = None,
    gdrive_root: Optional[Union[Path, str]] = None,
    db_path: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """Copy `{stem}.mp4`, `{stem}.txt`, `{stem}.json`, and `{stem}_cover.webp` to Google Drive.

    Also snapshots `store.db` safely when present.
    """
    src_mp4 = Path(mp4_path)
    ready_dir = _resolve_ready_dir(gdrive_root)
    if ready_dir is None:
        return {
            "synced": False,
            "reason": "gdrive_not_mounted",
            "mp4_path": None,
            "txt_path": None,
            "json_path": None,
            "cover_path": None,
            "db_snapshot_path": None,
        }

    if not src_mp4.exists():
        raise FileNotFoundError(f"Cannot sync missing MP4 to Google Drive: {src_mp4}")

    ready_dir.mkdir(parents=True, exist_ok=True)
    stem = src_mp4.stem

    dest_mp4 = ready_dir / f"{stem}.mp4"
    dest_txt = ready_dir / f"{stem}.txt"
    dest_json = ready_dir / f"{stem}.json"
    dest_cover = ready_dir / f"{stem}_cover.webp"

    # 1. Copy MP4
    shutil.copy2(src_mp4, dest_mp4)

    # 2. Write caption/hashtags .txt
    meta = dict(metadata or {})
    final_caption = caption_text or str(meta.get("caption_text") or meta.get("caption") or "").strip()
    dest_txt.write_text(final_caption, encoding="utf-8")

    # 3. Write companion metadata .json (tiktok_product_id, schedule_time, clip_id, etc.)
    json_payload = {
        "clip_id": meta.get("clip_id") or stem,
        "product_code": meta.get("product_code") or "",
        "product_id": meta.get("product_id") or "",
        "tiktok_product_id": meta.get("tiktok_product_id") or meta.get("product_id") or "",
        "angle_id": meta.get("angle_id") or "",
        "schedule_time": meta.get("schedule_time") or "",
        "export_id": meta.get("export_id") or "",
        "stem": stem,
    }
    for k, v in meta.items():
        if k not in json_payload:
            json_payload[k] = v
    dest_json.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. Copy or create {stem}_cover.webp
    src_cover: Optional[Path] = None
    if isinstance(cover_paths, dict):
        cand = cover_paths.get("webp") or cover_paths.get("9:16") or cover_paths.get("3:4")
        if cand and Path(cand).exists():
            src_cover = Path(cand)
    elif isinstance(cover_paths, (Path, str)) and Path(cover_paths).exists():
        src_cover = Path(cover_paths)
    else:
        sibling_webp = src_mp4.with_suffix(".webp")
        if sibling_webp.exists():
            src_cover = sibling_webp

    if src_cover is not None and src_cover.exists():
        shutil.copy2(src_cover, dest_cover)
    else:
        dest_cover.write_bytes(_MINIMAL_WEBP_BYTES)

    # 5. Snapshot store.db safely
    snap_parent = ready_dir.parent / "_snapshots"
    db_snap = snapshot_store_db(db_path=db_path, snapshot_dir=snap_parent)

    return {
        "synced": True,
        "ready_dir": ready_dir,
        "mp4_path": dest_mp4,
        "txt_path": dest_txt,
        "json_path": dest_json,
        "cover_path": dest_cover,
        "db_snapshot_path": db_snap,
    }
