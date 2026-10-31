"""Stable identity registry for every rendered export version.

``product_id`` and ``angle_id`` identify the logical content angle.  They do
not identify one rendered version of that angle, so every MP4 gets its own
``export_id`` here.  The path is stored as a locator only; it is never the
identity used to decide whether two versions are the same export.

Channel ownership (multi-channel P2.2, ADR "P2 store contract" + §13):
every row carries a top-level ``channel_id``; rows without it are legacy
(``main`` in compat mode only).  Public methods take keyword
``channel_id``/``all_channels`` exactly like ``ProductStore``:

* ``channel_id="a"`` -> only rows of channel ``a`` (+ legacy when ``a`` is
  main and strict mode is off).  A path or export id owned by another
  channel is never returned, merged or written.
* ``channel_id=None`` -> compat only: the old unscoped behaviour; strict
  mode raises 422 ``channel_scope_missing`` (fail closed).
* ``all_channels=True`` -> maintenance bypass (allowlisted modules only);
  it can never create a row.

``_load()/_mutate()`` stay the INTERNAL full-table access and are the patch
points existing tests use; unscoped public calls run through them.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import threading
import uuid
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from scripts.config import BASE_DIR
from scripts.channel_ownership import OWNER_KEY, StoreScope, owner_for_new_record, resolve_store_scope
from scripts.channel_store import ChannelError
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


# ----------------------------------------------------------------------
# Style metadata (Q6 feedback loop): which look/hook/format a clip used, so
# measured TikTok results can later be grouped by it.  Every field is
# optional -- rows written before this existed load and behave unchanged.
# ----------------------------------------------------------------------
STYLE_METADATA_FIELDS = ("style_preset", "hook_style", "story_format", "duration_sec", "hook_text")
DEFAULT_STORY_FORMAT = "classic"
_HOOK_TEXT_MAX = 200


def normalize_style_metadata(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Keep only known, non-empty, well-typed style fields.

    ``duration_sec`` must be a positive number (rounded to 0.01 s); text
    fields are stripped strings (``hook_text`` capped).  Unknown keys and
    empty values are dropped, so the result can be merged "fill only what
    is missing" without ever blanking a stored value.
    """
    clean: Dict[str, Any] = {}
    for key in STYLE_METADATA_FIELDS:
        value = (raw or {}).get(key)
        if value is None or isinstance(value, bool):
            continue
        if key == "duration_sec":
            try:
                seconds = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(seconds) and seconds > 0:
                clean[key] = round(seconds, 2)
            continue
        if not isinstance(value, str):
            continue
        text = " ".join(value.split())
        if key == "hook_text":
            text = text[:_HOOK_TEXT_MAX]
        if text:
            clean[key] = text
    return clean


def style_metadata_from_manifest(manifest: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive the export's style metadata from its project manifest.

    Reads only fields the render already persists -- no media probe:
    ``style_preset`` (manifest or ``render_params``), ``hook_style_id``
    (written by /api/hooks/apply-* when a hook variant is chosen; the
    manifest's ``hook_style`` key is the banner *template dict* and is used
    only when it is a plain id string), ``story_format`` (default
    ``"classic"``), ``total_duration`` and the spoken hook line
    (``script_data.hook`` -> first script line -> ``hook_title``).
    """
    if not isinstance(manifest, dict):
        return {}
    render_params = manifest.get("render_params") if isinstance(manifest.get("render_params"), dict) else {}
    script = manifest.get("script_data") if isinstance(manifest.get("script_data"), dict) else {}

    hook_style = manifest.get("hook_style_id") or render_params.get("hook_style_id")
    if not hook_style and isinstance(manifest.get("hook_style"), str):
        hook_style = manifest.get("hook_style")

    hook_text = script.get("hook") if isinstance(script.get("hook"), str) else ""
    if not hook_text:
        lines = script.get("lines") if isinstance(script.get("lines"), list) else []
        first = lines[0] if lines else None
        if isinstance(first, dict):
            hook_text = first.get("text") or ""
        elif isinstance(first, str):
            hook_text = first
    if not hook_text:
        hook_text = manifest.get("hook_text") or manifest.get("hook_title") or ""

    return normalize_style_metadata({
        "style_preset": manifest.get("style_preset") or render_params.get("style_preset"),
        "hook_style": hook_style,
        "story_format": manifest.get("story_format") or render_params.get("story_format") or DEFAULT_STORY_FORMAT,
        "duration_sec": manifest.get("duration_sec") or manifest.get("total_duration"),
        "hook_text": hook_text,
    })


def _fill_style_metadata(record: Dict[str, Any], metadata: Dict[str, Any], *, overwrite: bool = False) -> bool:
    """Write ``metadata`` onto ``record`` (fill-missing unless ``overwrite``); True when changed."""
    changed = False
    for key, value in normalize_style_metadata(metadata).items():
        if record.get(key) in (None, "") or (overwrite and record.get(key) != value):
            record[key] = value
            changed = True
    return changed


def _foreign_export_error() -> ChannelError:
    # ADR §2: a resource of another channel must look like it does not exist.
    return ChannelError(404, "resource_not_found", "ไม่พบไฟล์ export ที่ร้องขอในช่องที่เลือก")


def _path_conflict_error(path_key: str) -> ChannelError:
    return ChannelError(
        409,
        "export_path_conflict",
        f"ปลายทาง {Path(path_key).name} ถูกใช้โดยข้อมูลของช่องอื่นอยู่แล้ว จึงหยุดเพื่อไม่ให้ทับไฟล์ของอีกช่อง",
    )


class ExportRegistry:
    """Transactional store for per-file export identities."""

    _path_index_lock = threading.Lock()
    # Serialises style-metadata stamping across worker threads (AGENTS rule
    # 24).  SQLite's BEGIN IMMEDIATE already serialises the transaction; the
    # lock keeps same-process writers from spinning on busy_timeout.
    _metadata_lock = threading.Lock()
    # Cached ``[(path_key, export_id, owner)]`` in registry order, rebuilt
    # once per registry change (signature).  Filtered per scope on read.
    _path_index: Optional[List[Tuple[str, str, Optional[str]]]] = None
    _path_index_signature: Optional[tuple[int, int]] = None

    @classmethod
    def _registry_signature(cls) -> tuple[int, int]:
        """Return a cheap change token for external JSON mirror edits.

        Only guards this class's in-memory path index. The deeper staleness
        window -- a mirror edit landing inside one filesystem timestamp tick
        -- belongs to the JSON-to-SQLite import and is handled by
        db._mirror_token, so this does not need to read the file.
        """
        try:
            stat = REGISTRY_PATH.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return (0, 0)

    # ------------------------------------------------------------------
    # internal full-table access (all channels) + scope plumbing
    # ------------------------------------------------------------------
    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def _mutate(cls):
        return _TABLE.mutate()

    @staticmethod
    def _scope(channel_id: Optional[str] = None, all_channels: bool = False) -> StoreScope:
        return resolve_store_scope(channel_id, all_channels=all_channels)

    @classmethod
    @contextmanager
    def _scoped_mutate(cls, scope: StoreScope):
        """One transaction over the rows visible to ``scope``.

        Scoped calls use ``DocumentTable.scoped_mutate`` (other channels'
        rows are never exposed nor written; ``.out_of_scope`` holds read-only
        copies used for the path-collision guard).  Unscoped calls keep the
        old full-table ``cls._mutate()`` (a patch point for existing tests).
        """
        if scope.unscoped:
            with cls._mutate() as records:
                yield records
            return
        with _TABLE.scoped_mutate(scope.channel_id, include_legacy=scope.include_legacy) as records:
            yield records

    @classmethod
    def _scoped_load(cls, scope: StoreScope) -> List[Dict[str, Any]]:
        rows = cls._load()
        if scope.unscoped:
            return rows
        return [row for row in rows if scope.owns(row)]

    @classmethod
    def _invalidate_index(cls) -> None:
        cls._path_index = None
        cls._path_index_signature = None

    # ------------------------------------------------------------------
    # reads
    # ------------------------------------------------------------------
    @classmethod
    def all(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> List[Dict[str, Any]]:
        """Return a snapshot for callers that need to audit identities."""
        return [dict(row) for row in cls._scoped_load(cls._scope(channel_id, all_channels))]

    @classmethod
    def path_index(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> Dict[str, str]:
        """Return canonical-path → export-id lookup for the scope, built once per change.

        Windows ``Path.resolve`` is expensive. Schedule reads only need the
        identity lookup, not a fresh normalization of every historic export.
        The cache holds every row once; each scope gets its own filtered
        view, so a path registered to channel B never maps to an id for A.
        """
        scope = cls._scope(channel_id, all_channels)
        with cls._path_index_lock:
            signature = cls._registry_signature()
            if cls._path_index is None or cls._path_index_signature != signature:
                entries: List[Tuple[str, str, Optional[str]]] = []
                for row in cls._load():
                    key = row.get("path_key") or _normalise_path(row.get("path"))
                    export_id = row.get("id")
                    if key and export_id:
                        entries.append((key, str(export_id), row.get(OWNER_KEY)))
                cls._path_index = entries
                cls._path_index_signature = cls._registry_signature()
            entries = list(cls._path_index)
        index: Dict[str, str] = {}
        for key, export_id, owner in entries:
            if key in index:
                continue
            if scope.unscoped or scope.owns({OWNER_KEY: owner}):
                index[key] = export_id
        return index

    @classmethod
    def get(
        cls, export_id: Optional[str], *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> Optional[Dict[str, Any]]:
        if not export_id:
            return None
        scope = cls._scope(channel_id, all_channels)
        return next(
            (row for row in cls._scoped_load(scope) if str(row.get("id")) == str(export_id)),
            None,
        )

    @classmethod
    def owner_of(cls, export_id: Optional[str]) -> tuple[bool, Optional[str]]:
        """``(exists, channel_id)`` across ALL channels (system read for 404 guards;
        ``channel_id`` None = legacy row)."""
        if not export_id:
            return False, None
        for row in cls._load():
            if str(row.get("id")) == str(export_id):
                return True, row.get(OWNER_KEY)
        return False, None

    @classmethod
    def path_owners(cls, path: Any) -> List[tuple[str, Optional[str]]]:
        """``[(export_id, channel_id)]`` of every row registered at ``path``,
        across ALL channels (system read for ownership guards on file routes)."""
        key = _normalise_path(path)
        if not key:
            return []
        return [
            (str(row.get("id")), row.get(OWNER_KEY))
            for row in cls._load()
            if _normalise_path(row.get("path")) == key
        ]

    @classmethod
    def out_of_scope_paths(cls, *, channel_id: Optional[str] = None) -> List[str]:
        """Stored ``path`` values of every row NOT visible to ``channel_id``
        (system read; ``None`` -> ``[]``).  Lets a listing hide files that are
        registered to another channel without exposing those rows."""
        if channel_id is None:
            return []
        scope = cls._scope(channel_id)
        return [str(row.get("path")) for row in cls._load() if row.get("path") and not scope.owns(row)]

    @classmethod
    def find_by_path(
        cls, path: Any, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> Optional[Dict[str, Any]]:
        key = _normalise_path(path)
        if not key:
            return None
        scope = cls._scope(channel_id, all_channels)
        return next(
            (row for row in cls._scoped_load(scope) if _normalise_path(row.get("path")) == key),
            None,
        )

    @classmethod
    def lookup(
        cls,
        *,
        export_id: Optional[str] = None,
        path: Any = None,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Scoped lookup for route guards: by ``export_id`` when given, else by path.

        Returns the in-scope row, or ``None`` when nothing is registered there
        at all (unknown id / unregistered file -- each route keeps its old
        response for that case).  An id or path that IS registered but only
        outside the scope (another channel, or a legacy row hidden by strict
        mode) raises 404 ``resource_not_found`` -- before any side effect.
        """
        scope = cls._scope(channel_id, all_channels)
        if export_id:
            record = cls.get(export_id, channel_id=channel_id, all_channels=all_channels)
            if record is None and not scope.unscoped and cls.owner_of(export_id)[0]:
                raise _foreign_export_error()
            return record
        record = cls.find_by_path(path, channel_id=channel_id, all_channels=all_channels)
        if record is None and not scope.unscoped and cls.path_owners(path):
            raise _foreign_export_error()
        return record

    @classmethod
    def find_for_angle(
        cls,
        product_id: Optional[str],
        angle_id: Optional[str],
        *,
        status: Optional[str] = None,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> List[Dict[str, Any]]:
        """Find every export version belonging to one logical angle."""
        if not product_id or not angle_id:
            return []
        scope = cls._scope(channel_id, all_channels)
        rows = [
            dict(row)
            for row in cls._scoped_load(scope)
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
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Return the current file for an angle, preferring Posted evidence.

        A Ready/Posted pair with the same filename is a legacy duplicate of
        one export, not two versions. Prefer the Posted copy in that case;
        otherwise use the newest existing file by filesystem mtime.
        """
        rows = []
        for row in cls.find_for_angle(product_id, angle_id, channel_id=channel_id, all_channels=all_channels):
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

    # ------------------------------------------------------------------
    # writes
    # ------------------------------------------------------------------
    @staticmethod
    def _check_parent_products(scope: StoreScope, product_ids: List[Any]) -> None:
        """An export's channel must equal its parent product's channel (409).

        Checked for channel-scoped calls only (compat ``None`` callers keep the
        old behaviour; strict mode already rejects them).  A product id that
        exists nowhere is not checked (deleted product / legacy data), exactly
        as before.  Runs BEFORE the registry transaction is opened: ProductStore
        shares store.db's connection (no nested transactions).
        """
        if scope.unscoped:
            return
        from scripts.product_store import ProductStore  # lazy: product_store imports this module

        for product_id in sorted({str(pid) for pid in product_ids if pid}):
            exists, owner = ProductStore.owner_of(product_id)
            if exists and not scope.owns({OWNER_KEY: owner}):
                raise ChannelError(
                    409,
                    "channel_child_mismatch",
                    "คลิป export ต้องอยู่ช่องเดียวกับสินค้าที่ผูกไว้ (สินค้านี้เป็นของช่องอื่น)",
                )

    @classmethod
    def ensure_many(
        cls,
        entries: List[Dict[str, Any]],
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
        job_scope: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Ensure many file identities inside one read-modify-write transaction.

        Export listings can contain hundreds of MP4s. Calling ``ensure`` once
        per file opens and commits a SQLite transaction for every row, which
        turns a harmless read into a linear series of database writes. Keep
        the returned order aligned with ``entries`` so callers can attach the
        stable identity to the matching file without another path scan.

        Scoped: a path already registered to ANOTHER channel (or to a legacy
        row hidden by strict mode) is never re-registered or merged -- the
        whole batch is refused with 404 before anything is written.
        """
        prepared = []
        for entry in entries:
            path_key = _normalise_path(entry.get("path"))
            if not path_key:
                raise ValueError("export path is required")
            prepared.append((path_key, entry))

        if not prepared:
            return []

        scope = cls._scope(channel_id, all_channels)
        if job_scope is not None and job_scope.get("channel_id") != scope.effective_owner:
            raise ChannelError(422, "channel_scope_conflict", "ข้อมูลช่องของงานไม่ตรงกับคลิป export")
        provenance = {
            key: deepcopy(job_scope[key]) for key in (
                "channel_revision", "channel_identity_hash", "channel_identity_snapshot"
            ) if job_scope is not None and key in job_scope
        }
        cls._check_parent_products(scope, [entry.get("product_id") for _, entry in prepared])

        now = _now()
        with cls._scoped_mutate(scope) as records:
            by_path = {}
            for row in records:
                row_key = _normalise_path(row.get("path"))
                if row_key and row_key not in by_path:
                    by_path[row_key] = row
            foreign_paths = {
                _normalise_path(row.get("path"))
                for row in getattr(records, "out_of_scope", ()) or ()
            }

            result = []
            for path_key, entry in prepared:
                product_id = entry.get("product_id")
                angle_id = entry.get("angle_id")
                project_name = entry.get("project_name")
                status = entry.get("status") or "rendered"
                posted_at = entry.get("posted_at")
                record = by_path.get(path_key)
                if record is None and path_key in foreign_paths:
                    raise _foreign_export_error()
                if record is None:
                    owner = owner_for_new_record(scope)
                    record = {
                        "id": f"exp_{uuid.uuid4().hex}",
                        OWNER_KEY: owner,
                        "path": path_key,
                        "path_key": path_key,
                        "product_id": product_id,
                        "angle_id": angle_id,
                        "project_name": project_name,
                        "status": status,
                        "created_at": now,
                        "updated_at": now,
                        "posted_at": posted_at,
                        **provenance,
                    }
                    # Optional style metadata: only keys with real values are
                    # added, so rows without it keep the exact old shape.
                    _fill_style_metadata(record, entry.get("style_metadata") or {})
                    records.append(record)
                    by_path[path_key] = record
                else:
                    changed = False
                    old_identity = record.get("channel_identity_hash")
                    new_identity = provenance.get("channel_identity_hash")
                    if old_identity and new_identity and old_identity != new_identity:
                        raise ChannelError(409, "export_identity_snapshot_conflict", "ชื่อไฟล์นี้ผูกกับข้อมูลช่องรุ่นเดิม ต้องสร้าง export รุ่นใหม่")
                    for key, value in provenance.items():
                        if key not in record:
                            record[key] = deepcopy(value)
                            changed = True
                    if record.get("path_key") != path_key:
                        record["path_key"] = path_key
                        changed = True
                    if product_id and not record.get("product_id"):
                        record["product_id"] = product_id
                        changed = True
                    if angle_id and not record.get("angle_id"):
                        record["angle_id"] = angle_id
                        changed = True
                    if project_name and not record.get("project_name"):
                        record["project_name"] = project_name
                        changed = True
                    # Never downgrade a posted export during a later legacy scan.
                    if record.get("status") != "posted" and status == "posted":
                        record["status"] = "posted"
                        record["posted_at"] = posted_at or record.get("posted_at") or now
                        changed = True
                    if _fill_style_metadata(record, entry.get("style_metadata") or {}):
                        changed = True
                    if changed:
                        record["updated_at"] = now
                result.append(dict(record))
            cls._invalidate_index()
            return result

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
        channel_id: Optional[str] = None,
        all_channels: bool = False,
        job_scope: Optional[Dict[str, Any]] = None,
        style_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return the existing identity or create one for this exact file.

        This is also the one-time migration seam for exports made before the
        registry existed.  A later call can enrich a legacy record without
        changing its ID.  ``style_metadata`` (see STYLE_METADATA_FIELDS) is
        optional and only fills fields the record does not have yet.
        """
        return cls.ensure_many([{
            "path": path,
            "product_id": product_id,
            "angle_id": angle_id,
            "project_name": project_name,
            "status": status,
            "posted_at": posted_at,
            "style_metadata": style_metadata,
        }], channel_id=channel_id, all_channels=all_channels, job_scope=job_scope)[0]

    @classmethod
    def set_style_metadata(
        cls,
        export_id: Optional[str],
        metadata: Optional[Dict[str, Any]],
        *,
        overwrite: bool = False,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Stamp style metadata on one export (fill-missing unless ``overwrite``).

        Returns the stored row, or ``None`` when the export is unknown in this
        scope (another channel's export looks absent).  The read-modify-write
        runs inside one ``BEGIN IMMEDIATE`` transaction and under
        ``_metadata_lock`` (AGENTS rule 24) so concurrent finalizers in worker
        threads never lose each other's fields.
        """
        clean = normalize_style_metadata(metadata)
        if not export_id:
            return None
        scope = cls._scope(channel_id, all_channels)
        with cls._metadata_lock:
            with cls._scoped_mutate(scope) as records:
                record = next((row for row in records if str(row.get("id")) == str(export_id)), None)
                if record is None:
                    return None
                if clean and _fill_style_metadata(record, clean, overwrite=overwrite):
                    record["updated_at"] = _now()
                return dict(record)

    @classmethod
    def move_and_mark_posted(
        cls,
        export_id: str,
        path: Any,
        *,
        posted_at: Optional[str] = None,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        path_key = _normalise_path(path)
        now = posted_at or _now()
        scope = cls._scope(channel_id, all_channels)
        with cls._scoped_mutate(scope) as records:
            record = next((row for row in records if str(row.get("id")) == str(export_id)), None)
            if record is None:
                raise KeyError(export_id)
            if path_key and any(
                _normalise_path(row.get("path")) == path_key
                for row in getattr(records, "out_of_scope", ()) or ()
            ):
                # Another channel already has a row at the destination: never
                # collapse/merge across channels (the route preflights this
                # before moving any file).
                raise _path_conflict_error(path_key)
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
                for field in ("product_id", "angle_id", "project_name", *STYLE_METADATA_FIELDS):
                    if not posted_destination.get(field) and record.get(field):
                        posted_destination[field] = record[field]
                records[:] = [
                    row for row in records
                    if row is not record and row not in destination_records
                ]
                posted_destination["updated_at"] = now
                cls._invalidate_index()
                return dict(posted_destination)
            records[:] = [row for row in records if row not in destination_records]
            record["path"] = path_key
            record["path_key"] = path_key
            record["status"] = "posted"
            record["posted_at"] = record.get("posted_at") or now
            record["updated_at"] = now
            cls._invalidate_index()
            return dict(record)

    @classmethod
    def update_path(
        cls, export_id: str, path: Any, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Keep an export ID attached when its file is renamed."""
        path_key = _normalise_path(path)
        if not path_key:
            return None
        now = _now()
        scope = cls._scope(channel_id, all_channels)
        with cls._scoped_mutate(scope) as records:
            record = next((row for row in records if str(row.get("id")) == str(export_id)), None)
            if record is None:
                return None
            if any(
                _normalise_path(row.get("path")) == path_key
                for row in getattr(records, "out_of_scope", ()) or ()
            ):
                raise _path_conflict_error(path_key)
            record["path"] = path_key
            record["path_key"] = path_key
            record["updated_at"] = now
            cls._invalidate_index()
            return dict(record)

    @classmethod
    def remove(cls, export_id: Optional[str], *, channel_id: Optional[str] = None, all_channels: bool = False) -> None:
        if not export_id:
            return
        scope = cls._scope(channel_id, all_channels)
        with cls._scoped_mutate(scope) as records:
            records[:] = [row for row in records if str(row.get("id")) != str(export_id)]
            cls._invalidate_index()

    @classmethod
    def apply_to_each(
        cls,
        fn: Callable[[Dict[str, Any]], None],
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> int:
        """Maintenance: call ``fn(row)`` (in-place edit) on every visible row in
        ONE transaction; returns how many rows changed.  ``fn`` may not change
        a row's ``channel_id`` (owner) -- that is migration-tool work."""
        scope = cls._scope(channel_id, all_channels)
        changed = 0
        with cls._scoped_mutate(scope) as records:
            for row in records:
                before = json.dumps(row, ensure_ascii=False, sort_keys=True)
                owner_before = (OWNER_KEY in row, row.get(OWNER_KEY))
                fn(row)
                if (OWNER_KEY in row, row.get(OWNER_KEY)) != owner_before:
                    raise ValueError("apply_to_each ห้ามเปลี่ยน channel_id ของ export")
                if json.dumps(row, ensure_ascii=False, sort_keys=True) != before:
                    changed += 1
            if changed:
                cls._invalidate_index()
        return changed
