"""Stable identity registry for every rendered export version.

``product_id`` and ``angle_id`` identify the logical content angle.  They do
not identify one rendered version of that angle, so every MP4 gets its own
``export_id`` here.  The path is stored as a locator only; it is never the
identity used to decide whether two versions are the same export.
"""

from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR
from scripts.db import DocumentTable
from scripts import path_utils


REGISTRY_PATH = BASE_DIR / "_Docs" / "export_registry.json"


def _db_path() -> Path:
    return REGISTRY_PATH.parent / "store.db"


def _json_path() -> Path:
    return REGISTRY_PATH


_TABLE = DocumentTable("export_registry", _db_path, _json_path)


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _normalise_path(raw_path: Any) -> str:
    if not raw_path:
        return ""
    path = Path(str(raw_path))
    if not path.is_absolute():
        path = BASE_DIR / path
    resolved = path.resolve()
    try:
        resolved.relative_to(BASE_DIR.resolve())
    except ValueError:
        # A foreign absolute path cannot be safely migrated into this app's
        # registry. Callers keep their legacy fallback behavior instead of
        # polluting the registry with test/temp or another machine's paths.
        return ""
    return path_utils.to_relative(resolved, base_dir=BASE_DIR) or ""


class ExportRegistry:
    """Transactional store for per-file export identities."""

    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def all(cls) -> List[Dict[str, Any]]:
        """Return a snapshot for callers that need to audit identities."""
        return [dict(row) for row in cls._load()]

    @classmethod
    def _mutate(cls):
        return _TABLE.mutate()

    @classmethod
    def get(cls, export_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not export_id:
            return None
        return next((row for row in cls._load() if str(row.get("id")) == str(export_id)), None)

    @classmethod
    def find_by_path(cls, path: Any) -> Optional[Dict[str, Any]]:
        key = _normalise_path(path)
        if not key:
            return None
        return next((row for row in cls._load() if _normalise_path(row.get("path")) == key), None)

    @classmethod
    def find_for_angle(
        cls,
        product_id: Optional[str],
        angle_id: Optional[str],
        *,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find every export version belonging to one logical angle."""
        if not product_id or not angle_id:
            return []
        rows = [
            dict(row)
            for row in cls._load()
            if str(row.get("product_id") or "") == str(product_id)
            and str(row.get("angle_id") or "") == str(angle_id)
            and (status is None or row.get("status") == status)
        ]
        return rows

    @classmethod
    def latest_for_angle(
        cls,
        product_id: Optional[str],
        angle_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Return the current file for an angle, preferring Posted evidence.

        A Ready/Posted pair with the same filename is a legacy duplicate of
        one export, not two versions. Prefer the Posted copy in that case;
        otherwise use the newest existing file by filesystem mtime.
        """
        rows = []
        for row in cls.find_for_angle(product_id, angle_id):
            raw_path = row.get("path")
            if not raw_path:
                continue
            path = Path(str(raw_path))
            if not path.is_absolute():
                path = BASE_DIR / path
            try:
                path = path.resolve()
                if not path.is_file():
                    continue
                rows.append((row, path))
            except OSError:
                continue
        if not rows:
            return None

        posted = [item for item in rows if item[0].get("status") == "posted"]
        if posted:
            posted.sort(key=lambda item: (item[1].stat().st_mtime, item[0].get("updated_at", "")), reverse=True)
            return posted[0][0]
        rows.sort(key=lambda item: (item[1].stat().st_mtime, item[0].get("updated_at", "")), reverse=True)
        return rows[0][0]

    @classmethod
    def ensure(
        cls,
        path: Any,
        *,
        product_id: Optional[str] = None,
        angle_id: Optional[str] = None,
        project_name: Optional[str] = None,
        status: str = "rendered",
        posted_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return the existing identity or create one for this exact file.

        This is also the one-time migration seam for exports made before the
        registry existed.  A later call can enrich a legacy record without
        changing its ID.
        """
        path_key = _normalise_path(path)
        if not path_key:
            raise ValueError("export path is required")
        now = _now()
        with cls._mutate() as records:
            record = next((row for row in records if _normalise_path(row.get("path")) == path_key), None)
            if record is None:
                record = {
                    "id": f"exp_{uuid.uuid4().hex}",
                    "path": path_key,
                    "product_id": product_id,
                    "angle_id": angle_id,
                    "project_name": project_name,
                    "status": status,
                    "created_at": now,
                    "updated_at": now,
                    "posted_at": posted_at,
                }
                records.append(record)
            else:
                if product_id and not record.get("product_id"):
                    record["product_id"] = product_id
                if angle_id and not record.get("angle_id"):
                    record["angle_id"] = angle_id
                if project_name and not record.get("project_name"):
                    record["project_name"] = project_name
                # Never downgrade a posted export during a later legacy scan.
                if record.get("status") != "posted" and status == "posted":
                    record["status"] = "posted"
                    record["posted_at"] = posted_at or record.get("posted_at") or now
                record["updated_at"] = now
            return dict(record)

    @classmethod
    def move_and_mark_posted(
        cls,
        export_id: str,
        path: Any,
        *,
        posted_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        path_key = _normalise_path(path)
        now = posted_at or _now()
        with cls._mutate() as records:
            record = next((row for row in records if str(row.get("id")) == str(export_id)), None)
            if record is None:
                raise KeyError(export_id)
            destination_records = [
                row for row in records
                if _normalise_path(row.get("path")) == path_key
                and str(row.get("id")) != str(export_id)
            ]
            posted_destination = next(
                (row for row in destination_records if row.get("status") == "posted"),
                None,
            )
            if posted_destination is not None:
                # Legacy mark-posted could leave a byte-identical Ready copy
                # and a second registry row for the Posted path. Collapse the
                # duplicate while keeping the already-posted identity as the
                # canonical proof record.
                for field in ("product_id", "angle_id", "project_name"):
                    if not posted_destination.get(field) and record.get(field):
                        posted_destination[field] = record[field]
                records[:] = [
                    row for row in records
                    if row is not record and row not in destination_records
                ]
                posted_destination["updated_at"] = now
                return dict(posted_destination)
            records[:] = [row for row in records if row not in destination_records]
            record["path"] = path_key
            record["status"] = "posted"
            record["posted_at"] = record.get("posted_at") or now
            record["updated_at"] = now
            return dict(record)

    @classmethod
    def update_path(cls, export_id: str, path: Any) -> Optional[Dict[str, Any]]:
        """Keep an export ID attached when its file is renamed."""
        path_key = _normalise_path(path)
        if not path_key:
            return None
        now = _now()
        with cls._mutate() as records:
            record = next((row for row in records if str(row.get("id")) == str(export_id)), None)
            if record is None:
                return None
            record["path"] = path_key
            record["updated_at"] = now
            return dict(record)

    @classmethod
    def remove(cls, export_id: Optional[str]) -> None:
        if not export_id:
            return
        with cls._mutate() as records:
            records[:] = [row for row in records if str(row.get("id")) != str(export_id)]
