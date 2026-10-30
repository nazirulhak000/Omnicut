# -*- coding: utf-8 -*-
"""Thread-safe export registration, cover binding, product status sync, and GDrive sync."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, Optional, Union
import uuid

try:
    from filelock import FileLock  # type: ignore
except ImportError:

    class FileLock:  # type: ignore[no-redef]
        """Stdlib atomic file lock fallback when `filelock` package is not installed."""

        def __init__(self, lock_file: Union[Path, str], timeout: float = 60.0) -> None:
            self.lock_file = Path(lock_file)
            self.timeout = timeout
            self._fd: Optional[int] = None

        def acquire(self) -> None:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            deadline = time.monotonic() + self.timeout
            while True:
                try:
                    self._fd = os.open(
                        str(self.lock_file),
                        os.O_CREAT | os.O_EXCL | os.O_RDWR,
                    )
                    os.write(self._fd, str(os.getpid()).encode("ascii"))
                    return
                except FileExistsError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out acquiring lock {self.lock_file}")
                    time.sleep(0.01)

        def release(self) -> None:
            if self._fd is not None:
                try:
                    os.close(self._fd)
                except OSError:
                    pass
                self._fd = None
            try:
                self.lock_file.unlink(missing_ok=True)
            except OSError:
                pass

        def __enter__(self) -> "FileLock":
            self.acquire()
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            self.release()

from scripts import colab_sync
from scripts.config import BASE_DIR
from scripts.couple_engine.inspect import _MINIMAL_WEBP_BYTES

_PROCESS_LOCK = threading.Lock()


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _read_json_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, list) else []
    except Exception:
        return []


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
    and `products.json` (`status="rendered"`), then trigger `colab_sync.sync_export_to_gdrive`.
    """
    mp4_file = Path(mp4_path)
    reg_dir = Path(registry_dir) if registry_dir is not None else (BASE_DIR / "_Docs")
    reg_dir.mkdir(parents=True, exist_ok=True)

    registry_file = reg_dir / "export_registry.json"
    bindings_file = reg_dir / "export_cover_bindings.json"
    products_file = reg_dir / "products.json"
    lock_file = reg_dir / ".export_finalize.lock"

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

    file_lock = FileLock(str(lock_file), timeout=60)
    with _PROCESS_LOCK, file_lock:
        now_iso = datetime.datetime.now().isoformat()
        now_ts = time.time()

        # Resolve product_id from products.json if present
        prods = _read_json_list(products_file)
        prod_record = next(
            (
                p
                for p in prods
                if str(p.get("product_code", "")).upper() == norm_code
                or str(p.get("code", "")).upper() == norm_code
                or (product_id and p.get("id") == product_id)
            ),
            None,
        )
        resolved_product_id = (
            product_id
            or (prod_record.get("id") if prod_record else None)
            or norm_code.lower()
        )

        # 1. Upsert into export_registry.json
        entries = _read_json_list(registry_file)
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
        webp_cov = resolved_covers.get("webp")
        cover_url = f"/exports/{webp_cov.name}" if webp_cov else None

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
        _atomic_write_json(registry_file, entries)

        # 2. Upsert into export_cover_bindings.json
        bindings = _read_json_list(bindings_file)
        p_916 = resolved_covers["9:16"]
        p_34 = resolved_covers["3:4"]
        rel_916 = f"05_Covers_Thumbnails/{p_916.name}"
        rel_34 = f"05_Covers_Thumbnails/{p_34.name}"
        sha_916 = _compute_sha256(p_916)
        sha_34 = _compute_sha256(p_34)

        b_entry = next((b for b in bindings if b.get("export_id") == export_id), None)
        selections_payload = {
            "9:16": {"path": rel_916, "sha256": sha_916, "format": "9:16"},
            "3:4": {"path": rel_34, "sha256": sha_34, "format": "3:4"},
        }
        if b_entry is None:
            bindings.append(
                {
                    "channel_id": "main",
                    "export_id": export_id,
                    "clip_id": clip_id,
                    "video_path": rel_mp4,
                    "selections": selections_payload,
                    "revision": 1,
                    "updated_at": now_ts,
                }
            )
        else:
            b_entry["clip_id"] = clip_id
            b_entry["video_path"] = rel_mp4
            b_entry["selections"] = selections_payload
            b_entry["revision"] = int(b_entry.get("revision", 1)) + 1
            b_entry["updated_at"] = now_ts
        _atomic_write_json(bindings_file, bindings)

        # 3. Sync status='rendered' & clip_id into products.json
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
                    "video_url": str(mp4_file.resolve()),
                    "cover_url": str(webp_cov.resolve()) if webp_cov else None,
                }
            )
        else:
            ang_record["angle_id"] = ang_record.get("angle_id") or angle_id
            ang_record["clip_id"] = clip_id
            ang_record["status"] = "rendered"
            ang_record["export_id"] = export_id
            ang_record["video_url"] = str(mp4_file.resolve())
            if webp_cov:
                ang_record["cover_url"] = str(webp_cov.resolve())

        _atomic_write_json(products_file, prods)

    gdrive_result: Dict[str, Any] = {"synced": False, "reason": "disabled"}
    if gdrive_sync:
        gdrive_result = colab_sync.sync_export_to_gdrive(
            mp4_file,
            caption_text=caption_text,
            metadata={
                "clip_id": clip_id,
                "product_code": norm_code,
                "product_id": resolved_product_id,
                "tiktok_product_id": resolved_product_id,
                "angle_id": angle_id,
                "export_id": export_id,
                "schedule_time": schedule_time,
            },
            cover_paths=resolved_covers,
            gdrive_root=gdrive_root,
            db_path=reg_dir / "store.db",
        )

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
