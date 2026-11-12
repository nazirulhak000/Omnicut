# -*- coding: utf-8 -*-
"""Thread-safe export registration, cover binding, product status sync, and GDrive sync."""

from __future__ import annotations

import datetime
import hashlib
from pathlib import Path
import threading
import time
from typing import Any, Dict, Optional, Union
import uuid

from scripts import path_utils, store_io
from scripts.config import BASE_DIR
from scripts.couple_engine.inspect import _MINIMAL_WEBP_BYTES

_PROCESS_LOCK = threading.Lock()


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def finalize_clip_export(
    clip_id: str,
    mp4_path: Union[Path, str],
    product_code: str,
    angle_id: str,
    registry_dir: Optional[Union[Path, str]] = None,
    gdrive_sync: bool = True,
    *,
    product_id: Optional[str] = None,
    covers: Optional[Dict[str, Union[Path, str]]] = None,
    caption_text: str = "",
    schedule_time: str = "",
    gdrive_root: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """Thread-safely register a rendered clip into `export_registry.json`, `export_cover_bindings.json`,
    and `products.json` (`status="rendered"`).
    """
    mp4_file = Path(mp4_path)
    reg_dir = Path(registry_dir) if registry_dir is not None else (BASE_DIR / "_Docs")
    reg_dir.mkdir(parents=True, exist_ok=True)

    registry_file = reg_dir / "export_registry.json"
    bindings_file = reg_dir / "export_cover_bindings.json"
    products_file = reg_dir / "products.json"

    norm_code = (product_code or "").strip().upper()
    rel_mp4 = f"04_Exports/Ready_to_post/{mp4_file.name}"

    # Ensure default cover files exist next to registry/covers when not explicitly supplied
    resolved_covers: Dict[str, Path] = {}
    if covers:
        for k, v in covers.items():
            if v and Path(v).exists():
                resolved_covers[k] = Path(v)
    if "9:16" not in resolved_covers or "3:4" not in resolved_covers:
        covers_dir = reg_dir.parent / "05_Covers_Thumbnails"
        covers_dir.mkdir(parents=True, exist_ok=True)
        c916 = covers_dir / f"{mp4_file.stem}_cover.jpg"
        c34 = covers_dir / f"{mp4_file.stem}_cover_3x4.jpg"
        cwebp = mp4_file.parent / f"{mp4_file.stem}.webp"
        for cp in (c916, c34, cwebp):
            if not cp.exists():
                cp.parent.mkdir(parents=True, exist_ok=True)
                cp.write_bytes(_MINIMAL_WEBP_BYTES)
        resolved_covers.setdefault("9:16", c916)
        resolved_covers.setdefault("3:4", c34)
        resolved_covers.setdefault("webp", cwebp)

    # All three stores are written through their SQLite-backed tables
    # (scripts.store_io): one transaction per store, mirrors re-published by
    # scripts.db, read errors raise instead of becoming [] (audit S1-01 /
    # S6-01). _PROCESS_LOCK only keeps this process's own threads from
    # interleaving the three steps.
    with _PROCESS_LOCK:
        now_iso = datetime.datetime.now().isoformat()
        now_ts = time.time()

        def _matches_product(p: Dict[str, Any]) -> bool:
            return (
                str(p.get("product_code", "")).upper() == norm_code
                or str(p.get("code", "")).upper() == norm_code
                or bool(product_id and p.get("id") == product_id)
            )

        # Resolve product_id from the product store if present
        prods = store_io.load_products(reg_dir)
        prod_record = next((p for p in prods if _matches_product(p)), None)
        resolved_product_id = (
            product_id
            or (prod_record.get("id") if prod_record else None)
            or norm_code.lower()
        )

        webp_cov = resolved_covers.get("webp")
        cover_url = f"/exports/{webp_cov.name}" if webp_cov else None

        # 1. Upsert into the export registry
        with store_io.mutate_export_registry(reg_dir) as entries:
            existing_entry = next(
                (
                    e
                    for e in entries
                    if e.get("clip_id") == clip_id
                    or e.get("path") == rel_mp4
                    or e.get("path_key") == rel_mp4
                ),
                None,
            )
            if existing_entry is not None:
                export_id = str(existing_entry.get("id") or f"exp_{uuid.uuid4().hex}")
                existing_entry.update(
                    {
                        "id": export_id,
                        "clip_id": clip_id,
                        "path": rel_mp4,
                        "path_key": rel_mp4,
                        "product_id": resolved_product_id,
                        "product_code": norm_code,
                        "angle_id": angle_id,
                        "status": "rendered",
                        "cover_url": cover_url or existing_entry.get("cover_url"),
                        "updated_at": now_iso,
                        "updated_ts": now_ts,
                    }
                )
            else:
                export_id = f"exp_{uuid.uuid4().hex}"
                entries.append(
                    {
                        "id": export_id,
                        "channel_id": "main",
                        "clip_id": clip_id,
                        "path": rel_mp4,
                        "path_key": rel_mp4,
                        "product_id": resolved_product_id,
                        "product_code": norm_code,
                        "angle_id": angle_id,
                        "project_name": f"_HyperFrames_Studio/{clip_id}",
                        "aspect_ratio": "9:16",
                        "resolution": "1080x1920",
                        "status": "rendered",
                        "cover_url": cover_url,
                        "created_at": now_iso,
                        "updated_at": now_iso,
                        "created_ts": now_ts,
                        "updated_ts": now_ts,
                    }
                )

        # 2. Upsert the cover binding
        p_916 = resolved_covers["9:16"]
        p_34 = resolved_covers["3:4"]
        selections_payload = {
            "9:16": {"path": f"05_Covers_Thumbnails/{p_916.name}", "sha256": _compute_sha256(p_916), "format": "9:16"},
            "3:4": {"path": f"05_Covers_Thumbnails/{p_34.name}", "sha256": _compute_sha256(p_34), "format": "3:4"},
        }
        store_io.upsert_cover_binding(
            export_id,
            rel_mp4,
            selections_payload,
            channel_id="main",
            extra={"clip_id": clip_id},
            bump_revision=True,
            docs_dir=reg_dir,
            clock=lambda: now_ts,
        )

        # 3. Sync status='rendered' & clip_id into the product store.
        # Paths are stored BASE_DIR-relative (audit S1-16, AGENTS rule 2).
        workspace_root = reg_dir.parent
        video_url = path_utils.to_relative(mp4_file.resolve(), base_dir=workspace_root)
        webp_url = path_utils.to_relative(webp_cov.resolve(), base_dir=workspace_root) if webp_cov else None
        with store_io.mutate_products(reg_dir) as prods:
            prod_record = next((p for p in prods if _matches_product(p)), None)
            if prod_record is None:
                prod_record = {
                    "id": resolved_product_id,
                    "product_code": norm_code,
                    "name": norm_code,
                    "status": "rendered",
                    "updated_at": now_iso,
                    "angles": [],
                }
                prods.append(prod_record)
            else:
                prod_record["status"] = "rendered"
                prod_record["updated_at"] = now_iso
                prod_record.setdefault("angles", [])

            angles = prod_record["angles"]
            ang_record = next(
                (
                    a
                    for a in angles
                    if a.get("angle_id") == angle_id
                    or a.get("id") == angle_id
                    or a.get("clip_id") == clip_id
                ),
                None,
            )
            if ang_record is None:
                angles.append(
                    {
                        "angle_id": angle_id,
                        "clip_id": clip_id,
                        "status": "rendered",
                        "export_id": export_id,
                        "video_url": video_url,
                        "cover_url": webp_url,
                    }
                )
            else:
                ang_record["angle_id"] = ang_record.get("angle_id") or angle_id
                ang_record["clip_id"] = clip_id
                ang_record["status"] = "rendered"
                ang_record["export_id"] = export_id
                ang_record["video_url"] = video_url
                if webp_url:
                    ang_record["cover_url"] = webp_url

    gdrive_result: Dict[str, Any] = {"synced": False, "reason": "disabled"}

    return {
        "export_id": export_id,
        "clip_id": clip_id,
        "product_code": norm_code,
        "product_id": resolved_product_id,
        "angle_id": angle_id,
        "status": "rendered",
        "mp4_path": mp4_file,
        "registry_file": registry_file,
        "bindings_file": bindings_file,
        "products_file": products_file,
        "gdrive": gdrive_result,
    }
