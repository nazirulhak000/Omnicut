"""
Product queue — the front of the funnel.

Affiliate work is a stream of products, not one project. This keeps the ones
worth filming, what the AI worked out about each, and how far each has got.

Storage is SQLite (see scripts/db.py) behind the exact same _load()/_save()
contract this module always had, mirrored out to a plain JSON file so it
stays readable, hand-editable, and diffable as a backup. The mirror file
lives at STORE_PATH, same path as before.

Path fields (angle.video_url, angle.selected_videos[], video.path,
video.rel_path) are stored BASE_DIR-relative wherever the path is actually
under BASE_DIR -- see scripts/path_utils.py for the full convention and why
(SAAS_READINESS_PLAN.md P0 item 4). Every write site below normalizes
through `path_utils.to_relative()` before saving; every read site that
touches disk (`Path(...).exists()`) resolves through
`path_utils.to_absolute()` first, so both newly-written relative paths and
old absolute ones already on disk keep working.
"""

import json
import re
import time
import uuid
import datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR, COVERS_DIR
from scripts.channel_ownership import (
    OWNER_KEY,
    StoreScope,
    owner_for_new_record,
    resolve_store_scope,
)
from scripts.channel_store import ChannelError
from scripts.db import DocumentTable
from scripts import path_utils
from scripts.export_registry import ExportRegistry, _normalise_path as _export_normalise_path

STORE_PATH = BASE_DIR / "_Docs" / "products.json"


def _require_export_in_product_channel(scope: StoreScope, product: Dict[str, Any], export_record: Dict[str, Any]) -> None:
    """P2.2: an angle may only point at an export of the product's own channel.

    Channel-scoped calls: the export must be visible to that scope (so in
    strict mode a legacy/unmigrated export is refused too).  Unscoped calls
    (compat ``None`` / maintenance): compare owners with legacy = ``main``.
    """
    if scope.channel_id is not None:
        same = scope.owns(export_record)
    else:
        from scripts.config import DEFAULT_CHANNEL_ID

        same = (export_record.get(OWNER_KEY) or DEFAULT_CHANNEL_ID) == (product.get(OWNER_KEY) or DEFAULT_CHANNEL_ID)
    if not same:
        raise ChannelError(
            409,
            "channel_child_mismatch",
            "คลิป export นี้เป็นของช่องอื่น จึงผูกกับสินค้าของช่องนี้ไม่ได้",
        )


def _to_relative(path: object) -> Optional[str]:
    """Wraps path_utils.to_relative(), pinned to THIS module's own BASE_DIR
    name rather than path_utils' own import of it -- tests monkeypatch
    `product_store.BASE_DIR` (see tests/test_rollback_all_statuses.py and
    friends), and that patch must be honored here too, not just by the
    BASE_DIR-derived directories (projects_dir, exports_dir, ...) already
    read directly off this module's BASE_DIR elsewhere in this file."""
    return path_utils.to_relative(path, base_dir=BASE_DIR)


def _to_absolute(path: object) -> Optional[Path]:
    """See _to_relative() above -- same reasoning, read direction."""
    return path_utils.to_absolute(path, base_dir=BASE_DIR)


# How long after a status change reconcile_existing_projects() gives that
# status the benefit of the doubt before trusting a single failed disk check
# enough to revert it. A real render pipeline takes far longer than this to
# even reach the point of setting "rendered", so a status stamped more
# recently than this was almost certainly just legitimately set -- any disk
# check that comes up empty in that window is far more likely a transient
# path-resolution/AV-lock/fsync-visibility miss than a genuine "this was
# never rendered".
RECONCILE_GRACE_PERIOD_SECONDS = 60


def _within_grace_period(status_updated_at: object, now: Optional[datetime.datetime] = None) -> bool:
    """True when `status_updated_at` (an angle's status_updated_at field, an
    ISO timestamp string in the same naive-local convention as
    ProductStore._now()) is newer than RECONCILE_GRACE_PERIOD_SECONDS ago.

    Missing or malformed input is treated as "no grace period, evaluate
    normally" (returns False) rather than raising -- reconcile_existing_projects()
    runs on every poll and must never be taken down by a bad/absent
    timestamp on one angle.
    """
    if not status_updated_at:
        return False
    try:
        stamped = datetime.datetime.fromisoformat(str(status_updated_at))
    except (TypeError, ValueError):
        print(
            f"[product_store] WARNING: could not parse status_updated_at "
            f"{status_updated_at!r} -- evaluating without a grace period."
        )
        return False
    reference = now or datetime.datetime.now()
    try:
        elapsed = (reference - stamped).total_seconds()
    except TypeError:
        # Mixed aware/naive datetimes -- same "don't crash reconcile" rule.
        print(
            f"[product_store] WARNING: status_updated_at {status_updated_at!r} "
            "is not comparable to the current timestamp -- evaluating "
            "without a grace period."
        )
        return False
    return 0 <= elapsed < RECONCILE_GRACE_PERIOD_SECONDS


def _find_mp4_by_glob(folder_name: str, *scan_dirs: Path) -> Optional[str]:
    """Fallback mp4 lookup shared by every place in this module that needs
    to answer "does an export for this project actually exist on disk"
    beyond trusting one stored/manifest path literally. Searches each
    scan_dir (in order) for f"{folder_name}*.mp4" and returns the
    BASE_DIR-relative path to the newest match (by mtime) it finds, or None.

    Newest-first (not candidates[0] off an unsorted glob) matters once a
    project has been re-rendered without its old export cleaned up first --
    otherwise which stale file wins is whatever order the filesystem
    happens to hand back, not the actual latest render.
    """
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        candidates = list(scan_dir.glob(f"{folder_name}*.mp4"))
        if not candidates:
            continue
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return _to_relative(str(candidates[0]))
    return None


def _extract_batch_from_name(name: Optional[str]) -> Optional[int]:
    """Extracts numeric batch index from a project name or export filename.
    Examples:
        BLU01-ปัญหาก่อนใช้_1 -> 1
        BLU01-ปัญหาก่อนใช้_2 -> 2
        04_Exports/Ready_to_post/BLU01-ปัญหาก่อนใช้_1_20260914_211453.mp4 -> 1
    """
    if not name:
        return None
    stem = Path(str(name)).stem
    parts = stem.split("_")
    # Strip timestamp suffixes like _20260914_211453 or _20260914
    if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) >= 6 and parts[-2].isdigit() and len(parts[-2]) >= 8:
        stem = "_".join(parts[:-2])
        parts = stem.split("_")
    elif len(parts) >= 2 and parts[-1].isdigit() and len(parts[-1]) >= 8:
        stem = "_".join(parts[:-1])
        parts = stem.split("_")

    if parts and parts[-1].isdigit():
        try:
            return int(parts[-1])
        except ValueError:
            pass
    return None


def _export_registry_find_by_path(export_records: List[Dict[str, Any]], raw_path: object) -> Optional[Dict[str, Any]]:
    """`ExportRegistry.find_by_path()`, but over a pre-fetched snapshot
    instead of a live call. See `_preferred_registered_export` for why."""
    key = _export_normalise_path(raw_path)
    if not key:
        return None
    return next((row for row in export_records if _export_normalise_path(row.get("path")) == key), None)


def _export_registry_latest_for_angle(
    export_records: List[Dict[str, Any]],
    product_id: Optional[str],
    angle_id: Optional[str],
    project_name: Optional[str] = None,
    batch: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """`ExportRegistry.latest_for_angle()`, but over a pre-fetched snapshot
    instead of a live call. See `_preferred_registered_export` for why."""
    if not product_id or not angle_id:
        return None
    target_batch = batch
    if target_batch is None and project_name:
        target_batch = _extract_batch_from_name(project_name)
    candidates = []
    for row in export_records:
        if str(row.get("product_id") or "") != str(product_id):
            continue
        if str(row.get("angle_id") or "") != str(angle_id):
            continue
        row_proj = row.get("project_name")
        if project_name and row_proj and row_proj != project_name:
            continue
        raw_path = row.get("path")
        if not raw_path:
            continue
        if target_batch is not None:
            r_batch = row.get("batch") or _extract_batch_from_name(row_proj) or _extract_batch_from_name(raw_path)
            if r_batch is not None and r_batch != target_batch:
                continue
        path = Path(str(raw_path))
        if not path.is_absolute():
            path = BASE_DIR / path
        try:
            path = path.resolve()
            if not path.is_file():
                continue
            candidates.append((row, path))
        except OSError:
            continue
    if not candidates:
        return None
    posted = [item for item in candidates if item[0].get("status") == "posted"]
    if posted:
        posted.sort(key=lambda item: (item[1].stat().st_mtime, item[0].get("updated_at", "")), reverse=True)
        return posted[0][0]
    candidates.sort(key=lambda item: (item[1].stat().st_mtime, item[0].get("updated_at", "")), reverse=True)
    return candidates[0][0]


def _registry_record_for_path(export_records: List[Dict[str, Any]], raw_path: object) -> Optional[Dict[str, Any]]:
    """Read an existing per-file identity without creating one in reconcile."""
    try:
        return _export_registry_find_by_path(export_records, _to_absolute(raw_path))
    except Exception:
        return None


def _preferred_registered_export(
    export_records: List[Dict[str, Any]],
    product_id: Optional[str],
    angle_id: Optional[str],
    candidate_path: Optional[str],
    project_name: Optional[str] = None,
    batch: Optional[int] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Return the path/ID pair that owns this angle's current export.

    The registry is authoritative once an export has an ID. In particular,
    a Posted record wins over a stale Ready copy left by the old move flow.

    `export_records` is a plain-data snapshot (see `ExportRegistry.all()`)
    fetched once *before* the products `_mutate()` transaction opened --
    see `reconcile_existing_projects`. ExportRegistry shares this store's
    own store.db connection (scripts/db.py), so calling its live
    load-backed methods from inside an already-open products transaction
    raises sqlite3.OperationalError: cannot start a transaction within a
    transaction.
    """
    try:
        record = _export_registry_latest_for_angle(
            export_records, product_id, angle_id, project_name=project_name, batch=batch
        )
        if record:
            path = _to_absolute(record.get("path"))
            if path and path.exists():
                return _to_relative(path), str(record.get("id"))
    except Exception:
        pass

    if candidate_path:
        record = _registry_record_for_path(export_records, candidate_path)
        if record:
            return candidate_path, str(record.get("id"))
    return candidate_path, None


# candidate      → the URL is saved, nothing else done yet
# scripted       → angles picked and a script exists
# in_production  → currently editing in Studio
# rendered       → clip rendered & QC checked
# posted         → clip is live on TikTok
STATUSES = ("candidate", "scripted", "in_production", "rendered", "posted")


import threading


def _store_db_path() -> Path:
    # STORE_PATH.parent is BASE_DIR/_Docs -- both products and posts share one
    # sqlite file there, but live in their own tables.
    return STORE_PATH.parent / "store.db"


def _store_json_path() -> Path:
    # Read STORE_PATH dynamically (not captured at import time) so tests that
    # monkeypatch scripts.product_store.STORE_PATH keep working.
    return STORE_PATH


_TABLE = DocumentTable("products", _store_db_path, _store_json_path)

# Optional cross-channel identity fields (plan §4.3).  Stored as given; no
# clone workflow exists (not approved) -- they only label "same model".
CANONICAL_KEY_FIELDS = ("canonical_product_key", "source_product_id")
_CANONICAL_MAX_LEN = 200


def _clean_canonical_value(field: str, value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} ต้องเป็นข้อความ")
    value = value.strip()
    if len(value) > _CANONICAL_MAX_LEN:
        raise ValueError(f"{field} ยาวเกิน {_CANONICAL_MAX_LEN} ตัวอักษร")
    return value or None


def _check_children_owner(owner: Optional[str], angles: Any) -> None:
    """Angles/batches inherit the product's owner and may never contradict it."""
    for angle in angles or []:
        if isinstance(angle, dict) and angle.get(OWNER_KEY) is not None and angle.get(OWNER_KEY) != owner:
            raise ChannelError(
                422,
                "channel_child_mismatch",
                f"angle '{angle.get('angle_id') or angle.get('id')}' ระบุช่อง {angle.get(OWNER_KEY)} "
                f"ไม่ตรงกับช่องของสินค้า ({owner or 'ข้อมูลเดิม'})",
            )


class ProductStore:
    """The list of products in play, with what the AI worked out about each."""

    # reconcile_existing_projects() opens a `_mutate()` transaction that holds
    # store.db's one write lock for the whole disk scan, and get_all()/list()/
    # get() all call it unconditionally -- meaning every UI poll re-scans and
    # re-locks, even seconds apart. Debounced to once per this window; a poll
    # inside it just reads whatever the last scan already reconciled, which is
    # correct within the window and self-corrects on the next one past it.
    # This is what actually failed under concurrent polling (see incident:
    # requests queuing on this lock stacked into 90+ second hangs even after
    # the busy_timeout fix, because the lock was being re-acquired far more
    # often than it needed to be).
    _RECONCILE_MIN_INTERVAL_S = 30.0
    _last_reconcile_at: float = 0.0
    _last_reconcile_scope: Optional[tuple[str, str]] = None

    # Kept only so any external code that still references ProductStore._lock
    # (none found in this repo, but this was public-by-convention before)
    # does not hit an AttributeError. No longer load-bearing for correctness
    # -- the real mutual exclusion is the SQLite transaction in _mutate().
    _lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def _save(cls, products: List[Dict[str, Any]]) -> None:
        _TABLE.save(products)

    @classmethod
    @contextmanager
    def _mutate(cls):
        """Context manager: read-modify-write the full product list as one
        SQLite transaction (fixes the lost-update race -- see class docs on
        the individual write methods below, and _Docs/SAAS_READINESS_PLAN.md
        P0 item 1). Every write method that used to do

            products = cls._load()
            ...mutate...
            cls._save(products)

        with the load OUTSIDE any lock now does

            with cls._mutate() as products:
                ...mutate...

        instead -- the save happens automatically (and only) on a clean
        exit, still inside the same transaction the load happened in, so
        two concurrent writers can no longer both read stale data and have
        one silently clobber the other's write.

        ProductStore operations also share one process-local lock. SQLite
        remains the cross-process coordination layer, while this lock keeps
        ProductStore's own threaded callers from entering the JSON mirror
        sync/transaction boundary at the same time. That matters because the
        mirror sync path is a separate write transaction in the shared
        database and cannot be retried safely from inside this context.
        """
        with cls._lock:
            with _TABLE.mutate() as products:
                yield products

    # ------------------------------------------------------------------
    # Channel scope (multi-channel P2 -- see ADR "P2 store contract")
    # ------------------------------------------------------------------
    # _load()/_save()/_mutate() above stay the INTERNAL full-table access
    # (all channels).  Public methods take keyword ``channel_id`` and go
    # through _scope()/_scoped_mutate()/_scoped_load() below:
    #   channel_id="a"       -> rows owned by "a" (+ legacy rows when "a" is
    #                           main and strict mode is off)
    #   channel_id=None      -> compat only: every row (old behaviour);
    #                           strict mode -> 422 channel_scope_missing
    #   all_channels=True    -> maintenance bypass (allowlisted modules only)
    @staticmethod
    def _scope(channel_id: Optional[str] = None, all_channels: bool = False) -> StoreScope:
        return resolve_store_scope(channel_id, all_channels=all_channels)

    @staticmethod
    def _creation_scope(scope: StoreScope) -> StoreScope:
        """Scope whose view a NEW product is deduplicated against.

        A compat unscoped call (``channel_id=None``) creates a ``main`` product,
        so its URL dedup must only ever see main (+ legacy) rows -- never
        silently merge into another channel's product.
        """
        if scope.channel_id is not None:
            return scope
        owner = owner_for_new_record(scope)
        return resolve_store_scope(owner)

    @classmethod
    @contextmanager
    def _scoped_mutate(cls, scope: StoreScope):
        """Read-modify-write the rows visible to ``scope`` in ONE transaction.

        Scoped calls use ``DocumentTable.scoped_mutate`` (other channels' rows
        are never exposed nor written, verified at commit).  Unscoped calls
        (compat ``None`` / ``all_channels``) keep the old full-table mutate.
        """
        # Unscoped calls go through cls._mutate()/cls._load() on purpose: they
        # are the long-standing patch points existing tests use to inject
        # fixture data -- bypassing them would send those tests to the real
        # store.  (cls._mutate() takes cls._lock itself; it is not reentrant.)
        if scope.unscoped:
            with cls._mutate() as products:
                yield products
            return
        with cls._lock:
            with _TABLE.scoped_mutate(scope.channel_id, include_legacy=scope.include_legacy) as products:
                yield products

    @classmethod
    def _scoped_load(cls, scope: StoreScope) -> List[Dict[str, Any]]:
        rows = cls._load()
        if scope.unscoped:
            return rows
        return [row for row in rows if scope.owns(row)]

    @staticmethod
    def _code_universe(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Every product (all channels + legacy) for global product_code uniqueness."""
        return list(products) + list(getattr(products, "out_of_scope", ()) or ())

    @classmethod
    def snapshot(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> List[Dict[str, Any]]:
        """Plain read of the products visible to the scope -- no reconcile scan,
        no write lock.  Replaces direct ``ProductStore._load()`` reads."""
        return cls._scoped_load(cls._scope(channel_id, all_channels))

    @classmethod
    def find(cls, product_id: str, *, channel_id: Optional[str] = None, all_channels: bool = False) -> Optional[Dict[str, Any]]:
        """One product by id within the scope (None for another channel's id), without reconcile."""
        for product in cls.snapshot(channel_id=channel_id, all_channels=all_channels):
            if product.get("id") == product_id:
                return product
        return None

    @classmethod
    def owner_of(cls, product_id: str) -> tuple[bool, Optional[str]]:
        """``(exists, channel_id)`` of a product across ALL channels (system read
        for ownership checks; ``channel_id`` None = legacy row)."""
        for product in cls._load():
            if product.get("id") == product_id:
                return True, product.get(OWNER_KEY)
        return False, None

    @classmethod
    def has_posted_angle_for_project(
        cls, project_name: str, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> bool:
        """True when any visible angle linked to ``project_name`` is posted
        (status or posted_at) -- the render/re-render guard."""
        if not project_name:
            return False
        for product in cls.snapshot(channel_id=channel_id, all_channels=all_channels):
            for angle in product.get("angles", []) or []:
                if angle.get("project_name") == project_name and (
                    angle.get("status") == "posted" or angle.get("posted_at")
                ):
                    return True
        return False

    @classmethod
    def rename_video_references(
        cls,
        *,
        old_abs: str,
        old_rel: str,
        old_name: str,
        new_info: Dict[str, Any],
        product_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> int:
        """Point every visible ``product.videos[]`` entry that referenced a
        renamed raw file at its new path/rel_path/name.  Returns entries changed."""
        scope = cls._scope(channel_id, all_channels)
        changed = 0
        with cls._scoped_mutate(scope) as products:
            for p in products:
                if product_id and p.get("id") != product_id:
                    continue
                for v in p.get("videos", []):
                    if v.get("path") == old_abs or v.get("rel_path") == old_rel or v.get("name") == old_name:
                        v["path"] = new_info["path"]
                        v["rel_path"] = new_info["rel_path"]
                        v["name"] = new_info["name"]
                        changed += 1
        return changed

    @classmethod
    def remove_video_references(
        cls,
        matches,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> int:
        """Drop every visible ``product.videos[]`` entry for which
        ``matches(video_entry)`` is true (a raw file was deleted).  Returns
        entries removed."""
        scope = cls._scope(channel_id, all_channels)
        removed = 0
        with cls._scoped_mutate(scope) as products:
            for p in products:
                v_list = p.get("videos", [])
                kept = [v for v in v_list if not matches(v)]
                if len(kept) != len(v_list):
                    removed += len(v_list) - len(kept)
                    p["videos"] = kept
        return removed

    @classmethod
    def backfill_missing_product_codes(
        cls, *, channel_id: Optional[str] = None, all_channels: bool = False, dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """Assign a product_code to visible products lacking one (oldest first),
        unique across ALL channels.  One transaction.  Returns
        ``[{id, name, product_code}]`` of what was (or would be) assigned."""
        scope = cls._scope(channel_id, all_channels)
        assigned: List[Dict[str, Any]] = []
        with cls._scoped_mutate(scope) as products:
            universe = cls._code_universe(products)
            pending = sorted(
                (p for p in products if not p.get("product_code")),
                key=lambda p: p.get("created_at") or "",
            )
            for product in pending:
                code = cls._generate_product_code(product.get("name", ""), universe)
                assigned.append({"id": product.get("id"), "name": product.get("name"), "product_code": code})
                if not dry_run:
                    product["product_code"] = code
                else:
                    universe.append({"product_code": code})
        return assigned

    @classmethod
    def apply_to_each_product(
        cls,
        fn,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
        dry_run: bool = False,
    ) -> List[Any]:
        """Maintenance helper: run ``fn(product) -> result`` on every visible
        product inside one transaction; ``fn`` mutates the product in place.
        ``dry_run`` runs ``fn`` on deep copies and writes nothing.  The
        product's ``channel_id`` cannot be changed through this helper."""
        import copy as _copy

        scope = cls._scope(channel_id, all_channels)
        if dry_run:
            return [fn(_copy.deepcopy(p)) for p in cls._scoped_load(scope)]
        results: List[Any] = []
        with cls._scoped_mutate(scope) as products:
            for product in products:
                had_owner = OWNER_KEY in product
                owner = product.get(OWNER_KEY)
                results.append(fn(product))
                if (OWNER_KEY in product) != had_owner or product.get(OWNER_KEY) != owner:
                    raise ValueError("apply_to_each_product เปลี่ยน channel_id ของสินค้าไม่ได้")
        return results

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------
    @classmethod
    def add(
        cls,
        name: str,
        url: str = "",
        platform: str = "",
        category: str = "",
        specs: Optional[List[Dict[str, str]]] = None,
        pain_points: Optional[List[str]] = None,
        selling_points: Optional[List[str]] = None,
        price_note: str = "",
        target_buyer: str = "",
        thumbnail: str = "",
        angles: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[Dict[str, Any]]] = None,
        tiktok_product_id: Optional[str] = None,
        product_code: Optional[str] = None,
        description: str = "",
        raw_text: str = "",
        metadata_source: str = "",
        source_warning: str = "",
        canonical_product_key: Optional[str] = None,
        source_product_id: Optional[str] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Add a product, or return the existing one when the URL is already queued.

        Multi-channel: the new product is stamped ``channel_id`` = the scope
        (compat ``None`` -> main).  URL dedup is per ``(channel, url)`` -- a
        product with the same URL in another channel is never touched.
        ``product_code`` stays unique across all channels.

        description/raw_text are the scraped product-page text (or typed
        spec text) the content matrix was generated from -- persisted here so
        a later single-angle reroll has the same source material to work
        from instead of only the angle's own already-condensed fields
        (pain_point/key_features), which lose detail the original text had.
        """
        if not name.strip():
            raise ValueError("ต้องมีชื่อสินค้า")
        canonical = {
            "canonical_product_key": _clean_canonical_value("canonical_product_key", canonical_product_key),
            "source_product_id": _clean_canonical_value("source_product_id", source_product_id),
        }
        scope = cls._scope(channel_id, all_channels)
        owner = owner_for_new_record(scope)
        write_scope = cls._creation_scope(scope)

        # The load-modify-save below used to run with the load OUTSIDE any
        # lock (P0 item 1 in SAAS_READINESS_PLAN.md): two concurrent adds for
        # the same new URL could both read "not found" and both append a
        # product, or a concurrent add-for-existing-URL update could vanish
        # under a concurrent unrelated add. _mutate() holds one SQLite
        # transaction across the whole read-modify-write.
        with cls._scoped_mutate(write_scope) as products:
            code_universe = cls._code_universe(products)
            if url.strip():
                for existing in products:
                    if existing.get("url", "").strip() == url.strip():
                        _check_children_owner(existing.get(OWNER_KEY), angles)
                        if angles:
                            existing["angles"] = angles
                            existing["status"] = "scripted"
                        if images:
                            existing["images"] = images
                        if tiktok_product_id and tiktok_product_id.strip():
                            existing["tiktok_product_id"] = tiktok_product_id.strip()
                        if description:
                            existing["description"] = description
                        if raw_text:
                            existing["raw_text"] = raw_text
                        if metadata_source:
                            existing["metadata_source"] = metadata_source
                        if source_warning:
                            existing["source_warning"] = source_warning
                        if not existing.get("product_code"):
                            existing["product_code"] = (
                                product_code.strip().upper()
                                if (product_code and product_code.strip())
                                else cls._generate_product_code(existing.get("name", ""), code_universe)
                            )
                        for field, value in canonical.items():
                            if value and not existing.get(field):
                                existing[field] = value
                        existing["updated_at"] = cls._now()
                        return existing

            _check_children_owner(owner, angles)
            now = cls._now()
            product = {
                "id": uuid.uuid4().hex,
                OWNER_KEY: owner,
                "name": name.strip(),
                "url": url.strip(),
                "platform": platform or cls.detect_platform(url),
                "category": category,
                "specs": specs or [],
                "pain_points": pain_points or [],
                "selling_points": selling_points or [],
                "price_note": price_note,
                "target_buyer": target_buyer,
                "thumbnail": thumbnail,
                "description": description,
                "raw_text": raw_text,
                "metadata_source": metadata_source,
                "source_warning": source_warning,
                "tiktok_product_id": tiktok_product_id.strip() if (tiktok_product_id and tiktok_product_id.strip()) else None,
                "product_code": (product_code.strip().upper() if (product_code and product_code.strip()) else cls._generate_product_code(name, code_universe)),
                "status": "scripted" if angles else "candidate",
                "angles": angles or [],
                "images": images or [],
                "videos": [],
                "projects": [],
                "created_at": now,
                "updated_at": now,
            }
            for field, value in canonical.items():
                if value:
                    product[field] = value
            products.append(product)
            return product

    @classmethod
    def update(
        cls,
        product_id: str,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
        **fields: Any,
    ) -> Dict[str, Any]:
        """Patch a product. Unknown keys are stored as-is so the UI can grow.

        ``channel_id`` is the SCOPE, never a field: the owner of a product
        cannot change here (a ``product_owner``-style field does not exist).
        Shot lists whose script changed are invalidated AFTER the products
        transaction commits (never nested on the same sqlite connection).
        """
        scope = cls._scope(channel_id, all_channels)
        for field in CANONICAL_KEY_FIELDS:
            if field in fields:
                fields[field] = _clean_canonical_value(field, fields[field])
        stale_shot_lists: List[tuple] = []
        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    fields.pop("id", None)
                    fields.pop("created_at", None)
                    if "angles" in fields:
                        _check_children_owner(product.get(OWNER_KEY), fields["angles"])

                    status = fields.get("status")
                    if status and status not in STATUSES:
                        raise ValueError(f"status '{status}' ไม่ถูกต้อง — ต้องเป็นหนึ่งใน {', '.join(STATUSES)}")

                    if "product_code" in fields and fields["product_code"]:
                        fields["product_code"] = fields["product_code"].strip().upper()

                    apply_to_angles = bool(fields.pop("apply_to_angles", False))
                    hook_brand = fields.get("hook_brand")
                    hook_model = fields.get("hook_model")
                    hook_label = fields.get("hook_label")

                    # If angles are updated, invalidate shot lists for angles whose scripts changed.
                    # Staged: ShotListsStore lives in the same store.db, so
                    # deleting from inside this transaction would be a nested
                    # write on the same connection (it used to fail silently
                    # here and the stale shot list survived).  Collected now,
                    # deleted after commit below.
                    if "angles" in fields and isinstance(fields["angles"], list):
                        try:
                            old_angles = {
                                (a.get("angle_id") or a.get("id"), a.get("batch") or 1): a
                                for a in product.get("angles", [])
                            }
                            for new_a in fields["angles"]:
                                aid = new_a.get("angle_id") or new_a.get("id")
                                a_batch = new_a.get("batch") or 1
                                key = (aid, a_batch)
                                if aid and key in old_angles:
                                    old_script = old_angles[key].get("script_lines") or []
                                    new_script = new_a.get("script_lines") or []
                                    if old_script != new_script:
                                        stale_shot_lists.append((aid, a_batch))
                        except Exception:
                            pass

                    if apply_to_angles:
                        target_angles = fields.get("angles") if ("angles" in fields and isinstance(fields["angles"], list)) else product.get("angles", [])
                        for angle in target_angles:
                            if hook_brand is not None:
                                angle["hook_brand"] = hook_brand
                            if hook_model is not None:
                                angle["hook_model"] = hook_model
                            if hook_label is not None:
                                angle["hook_label"] = hook_label

                    product.update(fields)
                    product["updated_at"] = cls._now()
                    updated = product
                    break
            else:
                raise ValueError(f"ไม่พบสินค้า id '{product_id}'")
        cls._invalidate_shot_lists(product_id, stale_shot_lists)
        return updated

    @staticmethod
    def _invalidate_shot_lists(product_id: str, keys: List[tuple]) -> None:
        """Delete cached shot lists AFTER the products transaction committed.

        Best effort (as before): a failure leaves a stale cached shot list,
        never a half-written product.  Idempotent, safe to re-run.
        """
        if not keys:
            return
        try:
            from scripts.shot_lists_store import ShotListsStore
        except Exception:
            return
        for angle_id, batch in keys:
            try:
                ShotListsStore.delete(product_id, angle_id, batch=batch)
            except Exception as err:
                print(f"[ProductStore] WARNING: ลบ shot list ที่ล้าสมัยไม่สำเร็จ ({product_id}/{angle_id}/b{batch}): {err}")

    @classmethod
    def attach_project(
        cls, product_id: str, project_name: str, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> Dict[str, Any]:
        """Link a rendered project back to the product it came from."""
        product = cls.get(product_id, channel_id=channel_id, all_channels=all_channels)
        if not product:
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

        projects = product.get("projects", [])
        if project_name not in projects:
            projects.append(project_name)

        return cls.update(
            product_id, channel_id=channel_id, all_channels=all_channels, projects=projects, status="rendered"
        )

    @classmethod
    def update_angle_status(
        cls,
        product_id: str,
        angle_id: str,
        status: str,
        video_url: Optional[str] = None,
        project_name: Optional[str] = None,
        qc_note: Optional[str] = None,
        clear_qc_note: bool = False,
        clear_conflict_note: bool = False,
        export_id: Optional[str] = None,
        mark_qc_passed: bool = False,
        batch: Optional[int] = None,
        cover_path: Optional[str] = None,
        cover_3x4_path: Optional[str] = None,
        cover_9x16_path: Optional[str] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
        require_latest_export: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Updates the lifecycle status of a specific script angle in a product.

        require_latest_export is the durable-post receipt CAS: a superseded
        angle returns None without mutation. Registry reads share this write
        transaction; normal callers retain their existing return contract.

        qc_note  – optional free-text reason for a QC failure; stored on the
                   angle so Studio can surface it the next time the angle is
                   opened for re-editing.
        clear_qc_note – pass True to wipe any previous qc_note (e.g. when the
                         angle passes QC and advances beyond 'rendered').
        clear_conflict_note – pass True to dismiss the `data_conflict_note`
                               reconcile_existing_projects() sets when it
                               auto-unlinks this angle from another angle's
                               project/video (Round BUG-3).
        mark_qc_passed – pass True only when a human actually clicked "QC
                         ผ่าน". Sets angle["qc_reviewed"]. A freshly-rendered
                         clip has no qc_note (nobody has rejected it yet),
                         but that is NOT the same fact as "a human reviewed
                         and approved it" -- qc_note alone used to be the
                         only signal the UI had, so every new render showed
                         as "QC ผ่าน" before anyone looked at it.
                         qc_reviewed is reset to False whenever video_url
                         actually changes (a new render is unreviewed by
                         definition) or a qc_note is freshly set (a
                         rejection un-approves it).
        batch          – optional batch index (e.g. 1, 2). When multiple angles
                         share the same template angle_id (e.g. 'pain_point')
                         across different batches, `batch` isolates the exact
                         angle being updated so other batches are never modified.
        """
        scope = cls._scope(channel_id, all_channels)
        # Validated *before* entering _mutate() on purpose: ExportRegistry
        # shares this store's own store.db file, and on the same thread
        # _connection_for() hands back that exact same cached connection
        # (keyed by resolved db path, not by table). Calling into it from
        # inside _mutate()'s `with` block -- which holds one SQLite write
        # transaction open for the block's whole body, by design (see
        # _mutate()'s docstring) -- meant a second nested write transaction
        # could be attempted on a connection already mid-transaction,
        # hanging that request (and, since it's the same file-level write
        # lock, every other request touching products/exports/post_log/
        # schedule) for up to busy_timeout x retry-attempts. Doing this
        # lookup first keeps ordinary mutation free of nested store calls.
        # The optional receipt CAS below performs only raw SELECT on this
        # already-open write connection, never another load/import/context.
        # Cross-channel read on purpose (P2.2): the export's owner is compared
        # with the product's owner below, so an export of another channel is
        # a 409 ``channel_child_mismatch`` instead of a silent link.
        export_record = ExportRegistry.get(export_id, all_channels=True) if export_id else None
        if export_id and export_record is None:
            raise ValueError(f"ไม่พบ export_id '{export_id}'")
        if export_id and video_url is not None:
            stored_path = _to_absolute(export_record.get("path"))
            requested_path = _to_absolute(video_url)
            if stored_path != requested_path:
                raise ValueError("export_id ไม่ตรงกับ video_url ของไฟล์ที่เลือก")

        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    if export_record is not None:
                        _require_export_in_product_channel(scope, product, export_record)
                    angles = product.get("angles", [])
                    matching_angles = []
                    for idx, a in enumerate(angles):
                        current_aid = a.get("angle_id") or a.get("id")
                        if current_aid == angle_id:
                            matching_angles.append(a)

                    if not matching_angles:
                        raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

                    target_angle = None
                    effective_batch = batch
                    if effective_batch is None:
                        match_b = re.search(r"_b(\d+)$", str(angle_id))
                        if match_b:
                            effective_batch = int(match_b.group(1))

                    # 1. Exact batch match if specified or extracted from compound angle_id
                    if effective_batch is not None:
                        for a in matching_angles:
                            if (a.get("batch") or 1) == effective_batch:
                                target_angle = a
                                break

                    # 2. Project name match if specified
                    if target_angle is None and project_name:
                        for a in matching_angles:
                            if a.get("project_name") == project_name:
                                target_angle = a
                                break
                        if target_angle is None:
                            proj_batch = _extract_batch_from_name(project_name)
                            if proj_batch is not None:
                                for a in matching_angles:
                                    if (a.get("batch") or 1) == proj_batch:
                                        target_angle = a
                                        break

                    # 3. Fallback: match first angle that has not been posted
                    if target_angle is None:
                        for a in matching_angles:
                            if a.get("status") != "posted" and not a.get("posted_at"):
                                target_angle = a
                                break

                    # 4. Final fallback: first angle
                    if target_angle is None:
                        target_angle = matching_angles[0]

                    angle = target_angle

                    if require_latest_export:
                        # The product mutation holds BEGIN IMMEDIATE. Read the
                        # registry on this same connection without load/import
                        # or a nested transaction: concurrent ensure() cannot
                        # commit a new export between this check and the write.
                        from scripts import export_registry as registry_module
                        from scripts.db import _connection_for
                        if not export_id or _TABLE._db_path_fn().resolve() != registry_module._TABLE._db_path_fn().resolve():
                            raise ChannelError(409, "posting_registry_transaction_required", "ต้องตรวจ export ใน transaction เดียวกับสินค้า")
                        conn = _connection_for(_TABLE._db_path_fn())
                        if not conn.in_transaction:
                            raise ChannelError(409, "posting_registry_transaction_required", "ต้องตรวจ export ขณะ transaction สินค้ายังเปิดอยู่")
                        rows = [json.loads(row[0]) for row in conn.execute("SELECT data FROM export_registry")]
                        candidates = [row for row in rows if scope.owns(row)
                                      and row.get("product_id") == product_id and row.get("angle_id") == angle_id]
                        expected = next((row for row in candidates if row.get("id") == export_id), None)
                        if expected is None:
                            raise ChannelError(409, "posting_export_changed", "export ไม่ตรงกับมุมใน transaction ปัจจุบัน")
                        if angle.get("export_id") and angle["export_id"] != export_id:
                            return None
                        try:
                            expected_created = datetime.datetime.fromisoformat(str(expected["created_at"]))
                        except (KeyError,ValueError,TypeError):
                            return None
                        expected_path = _to_absolute(expected.get("path"))
                        expected_mtime = expected_path.stat().st_mtime if expected_path and expected_path.is_file() else -1
                        for row in candidates:
                            if row.get("id") == export_id:
                                continue
                            # File metadata is portable/copyable; immutable
                            # registry creation is independent evidence. The
                            # registry has second precision and no monotonic
                            # sequence, so ties/missing timestamps abstain
                            # rather than inventing order from random UUIDs.
                            try:
                                created = datetime.datetime.fromisoformat(str(row["created_at"]))
                                if created >= expected_created:
                                    return None
                            except (KeyError,ValueError,TypeError):
                                return None
                            path = _to_absolute(row.get("path"))
                            if path and path.is_file() and path.stat().st_mtime > expected_mtime:
                                return None

                    # Strict guard: An angle that has been posted is permanently sealed as proof/archive.
                    # Never allow demoting status away from 'posted' under any circumstances.
                    if (angle.get("status") == "posted" or angle.get("posted_at")) and status != "posted":
                        return product
                    angle["status"] = status
                    # Dedicated "when did the status itself last
                    # change" stamp -- angle["updated_at"] below is
                    # touched by unrelated angle writes too (cover
                    # uploads, video attach), so it can't be used to
                    # tell a just-set status apart from a stale one.
                    # reconcile_existing_projects()'s grace-period
                    # guard reads this to avoid reverting a status
                    # this method JUST committed, on the strength of
                    # a single, non-retried disk check that happened
                    # to miss the file a moment later.
                    angle["status_updated_at"] = cls._now()
                    if video_url is not None:
                        new_video_url = _to_relative(video_url) if video_url else None
                        if new_video_url != angle.get("video_url"):
                            # A different rendered file is unreviewed by
                            # definition, regardless of what the angle's
                            # qc_reviewed flag said about the old one.
                            angle["qc_reviewed"] = False
                            # Round BUG-4: whatever upstream caller
                            # resolved product_id/angle_id for this
                            # write, enforce "at most one angle owns a
                            # given rendered file" as an invariant
                            # right here -- reconcile_existing_projects()
                            # only catches this on its own next pass,
                            # which left a stale duplicate claim
                            # visible (same clip/thumbnail under two
                            # different products' cards, no warning)
                            # for however long until that pass ran.
                            # Posted angles are permanently sealed
                            # proof (see the guard above) and are
                            # never touched here even if they
                            # collide -- that would mean a deeper bug
                            # than this check is meant to paper over.
                            if new_video_url:
                                for other_product in products:
                                    for other_angle in other_product.get("angles", []):
                                        if other_angle is angle:
                                            continue
                                        if other_angle.get("video_url") != new_video_url:
                                            continue
                                        if other_angle.get("status") == "posted" or other_angle.get("posted_at"):
                                            continue
                                        other_angle["project_name"] = None
                                        other_angle["video_url"] = None
                                        other_angle["export_id"] = None
                                        other_angle["status"] = "scripted"
                                        other_angle["qc_reviewed"] = False
                                        other_angle["data_conflict_note"] = (
                                            f"ปลดออกจาก '{project_name or new_video_url}' อัตโนมัติ "
                                            f"— ชนกับ angle อื่นที่เพิ่งผูกคลิปนี้ ({cls._now()})"
                                        )
                                        other_angle["updated_at"] = cls._now()
                        angle["video_url"] = new_video_url
                    if export_id is not None:
                        angle["export_id"] = export_id
                    if project_name is not None:
                        new_pname = project_name if project_name else None
                        if new_pname and new_pname != angle.get("project_name"):
                            # Also unbind other angles in this product that claimed this same project_name!
                            for other_angle in angles:
                                if other_angle is angle:
                                    continue
                                if other_angle.get("project_name") == new_pname:
                                    if other_angle.get("status") != "posted" and not other_angle.get("posted_at"):
                                        other_angle["project_name"] = None
                                        other_angle["video_url"] = None
                                        other_angle["export_id"] = None
                                        other_angle["status"] = "scripted"
                                        other_angle["qc_reviewed"] = False
                                        other_angle["data_conflict_note"] = (
                                            f"ปลดออกจาก '{new_pname}' อัตโนมัติ — ชนกับ angle อื่นในล็อตเดียวกัน ({cls._now()})"
                                        )
                                        other_angle["updated_at"] = cls._now()
                        angle["project_name"] = new_pname
                    # QC note handling
                    if qc_note is not None:
                        angle["qc_note"] = qc_note.strip() or None
                        if angle["qc_note"]:
                            angle["qc_reviewed"] = False
                    elif clear_qc_note:
                        angle["qc_note"] = None
                    if mark_qc_passed:
                        angle["qc_reviewed"] = True
                    if clear_conflict_note:
                        angle["data_conflict_note"] = None
                    if cover_path is not None:
                        angle["cover_path"] = _to_relative(cover_path) if cover_path else None
                    if cover_3x4_path is not None:
                        angle["cover_3x4_path"] = _to_relative(cover_3x4_path) if cover_3x4_path else None
                    if cover_9x16_path is not None:
                        angle["cover_9x16_path"] = _to_relative(cover_9x16_path) if cover_9x16_path else None
                    if status == "posted" and not angle.get("posted_at"):
                        angle["posted_at"] = cls._now()
                    angle["updated_at"] = cls._now()
                    product["updated_at"] = cls._now()
                    return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def replace_angle_content(
        cls,
        product_id: str,
        angle_id: str,
        new_content: Dict[str, Any],
        batch: Optional[int] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Overwrites an angle's script content (a rerolled script from the AI)
        while preserving everything about where the angle currently stands:
        angle_id, status, project_name, video_url, selected_videos/selected_video,
        qc_note, data_conflict_note, posted_at, created_at. A reroll producing
        a new script is not the same thing as the angle's production/render
        lifecycle moving forward or backward -- those stay exactly as they
        were, same as they would if the user had hand-edited the script text.
        """
        scope = cls._scope(channel_id, all_channels)
        CONTENT_KEYS = (
            "angle_name", "angle_description", "content_types", "badge", "product_name", "hook_title", "pain_point",
            "key_features", "price_deal", "ad_tone", "script_lines",
            "tts_lines", "tiktok_caption", "tiktok_hashtags",
            "duration", "extra_beats",
        )
        updated_product = None
        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    angles = product.get("angles", [])
                    matched_angle = None
                    effective_batch = batch
                    if effective_batch is None:
                        match_b = re.search(r"_b(\d+)$", str(angle_id))
                        if match_b:
                            effective_batch = int(match_b.group(1))

                    for angle in angles:
                        current_aid = angle.get("angle_id") or angle.get("id")
                        if current_aid == angle_id:
                            if effective_batch is not None and (angle.get("batch") or 1) == effective_batch:
                                matched_angle = angle
                                break
                            elif effective_batch is None and matched_angle is None:
                                matched_angle = angle
                    if matched_angle is not None:
                        for key in CONTENT_KEYS:
                            if key in new_content:
                                matched_angle[key] = new_content[key]
                        matched_angle["updated_at"] = cls._now()
                        product["updated_at"] = cls._now()
                        updated_product = product
                        break
        if updated_product is None:
            raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

        try:
            from scripts.shot_lists_store import ShotListsStore
            del_batch = effective_batch if effective_batch is not None else (matched_angle.get("batch") if matched_angle else None)
            ShotListsStore.delete(product_id, angle_id, batch=del_batch)
        except Exception:
            pass
        return updated_product

    @classmethod
    def append_angles(
        cls,
        product_id: str,
        new_angles: List[Dict[str, Any]],
        batch_index: Optional[int] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Appends a list of new angles (e.g. Batch 2, 3...) to an existing product.
        Preserves all existing angles and their statuses.
        """
        scope = cls._scope(channel_id, all_channels)
        if not new_angles:
            product = cls.get(product_id, channel_id=channel_id, all_channels=all_channels)
            if not product:
                raise ValueError(f"ไม่พบสินค้า id '{product_id}'")
            return product

        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    _check_children_owner(product.get(OWNER_KEY), new_angles)
                    existing = product.get("angles", [])
                    max_batch = 1
                    for a in existing:
                        b = a.get("batch")
                        if isinstance(b, int) and b > max_batch:
                            max_batch = b
                        elif not b:
                            a["batch"] = 1

                    assigned_batch = batch_index if batch_index is not None else (max_batch + 1 if existing else 1)
                    now = cls._now()
                    existing_aids = {a.get("angle_id") for a in existing if a.get("angle_id")}
                    for angle in new_angles:
                        angle_copy = dict(angle)
                        aid = angle_copy.get("angle_id") or angle_copy.get("id")
                        if not aid:
                            aid = f"ang_{uuid.uuid4().hex[:8]}"
                        if assigned_batch > 1 and not str(aid).endswith(f"_b{assigned_batch}"):
                            aid = f"{aid}_b{assigned_batch}"
                        if aid in existing_aids:
                            aid = f"{aid}_{uuid.uuid4().hex[:4]}"
                        existing_aids.add(aid)
                        angle_copy["angle_id"] = aid
                        angle_copy["batch"] = assigned_batch
                        angle_copy["status"] = angle_copy.get("status") or "scripted"
                        angle_copy["created_at"] = angle_copy.get("created_at") or now
                        angle_copy["updated_at"] = now
                        existing.append(angle_copy)

                    product["angles"] = existing
                    product["updated_at"] = now
                    return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def add_single_angle(
        cls,
        product_id: str,
        angle_data: Dict[str, Any],
        batch_index: Optional[int] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Appends a single custom or cloned angle to an existing product."""
        return cls.append_angles(
            product_id, [angle_data], batch_index=batch_index, channel_id=channel_id, all_channels=all_channels
        )


    @classmethod
    def update_angle_cover(
        cls,
        product_id: str,
        angle_id: str,
        cover_path: Optional[str] = None,
        cover_3x4_path: Optional[str] = None,
        cover_9x16_path: Optional[str] = None,
        batch: Optional[int] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Persist generated cover variants on the angle that owns them.

        Cover files are generated outside the product queue. Keeping their
        relative paths on the angle makes the association survive a page
        refresh while preserving the existing cover naming and media routes.
        Only files inside ``05_Covers_Thumbnails`` are accepted.
        """
        scope = cls._scope(channel_id, all_channels)

        def normalize_cover_path(raw_path: Optional[str], field_name: str) -> Optional[str]:
            if raw_path is None:
                return None
            rel_path = _to_relative(raw_path)
            absolute = _to_absolute(rel_path)
            if not rel_path or absolute is None:
                raise ValueError(f"{field_name} ต้องระบุไฟล์ปก")
            try:
                resolved = absolute.resolve()
                resolved.relative_to(COVERS_DIR.resolve())
            except (OSError, ValueError):
                raise ValueError(f"{field_name} ต้องอยู่ในโฟลเดอร์ 05_Covers_Thumbnails")
            if not resolved.is_file():
                raise ValueError(f"ไม่พบไฟล์ปก: {resolved.name}")
            return str(resolved.relative_to(BASE_DIR.resolve())).replace("\\", "/")

        normalized = {
            "cover_path": normalize_cover_path(cover_path, "cover_path"),
            "cover_3x4_path": normalize_cover_path(cover_3x4_path, "cover_3x4_path"),
            "cover_9x16_path": normalize_cover_path(cover_9x16_path, "cover_9x16_path"),
        }
        if not any(value for value in normalized.values()):
            raise ValueError("ต้องระบุไฟล์ปกอย่างน้อยหนึ่งไฟล์")

        def is_3x4(path: Optional[str]) -> bool:
            return bool(path and Path(path).name.casefold().endswith("_cover_3x4.jpg"))

        effective_batch = batch
        if effective_batch is None:
            match_b = re.search(r"_b(\d+)$", str(angle_id))
            if match_b:
                effective_batch = int(match_b.group(1))

        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product.get("id") != product_id:
                    continue
                for angle in product.get("angles", []):
                    current_aid = angle.get("angle_id") or angle.get("id")
                    if current_aid != angle_id:
                        continue
                    if effective_batch is not None and (angle.get("batch") or 1) != effective_batch:
                        continue

                    for key, value in normalized.items():
                        if value is not None:
                            angle[key] = value

                    # ``cover_path`` is the long-standing primary field.
                    # Mirror it into an explicit 9:16 field unless the only
                    # generated file is the 3:4 variant.
                    if normalized["cover_path"]:
                        if is_3x4(normalized["cover_path"]):
                            angle.setdefault("cover_3x4_path", normalized["cover_path"])
                        else:
                            angle.setdefault("cover_9x16_path", normalized["cover_path"])
                    if not angle.get("cover_path"):
                        angle["cover_path"] = angle.get("cover_9x16_path") or angle.get("cover_3x4_path")

                    angle["updated_at"] = cls._now()
                    product["updated_at"] = cls._now()
                    return product
                raise LookupError(f"ไม่พบ angle '{angle_id}' ในสินค้า '{product_id}'")
            raise LookupError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def rollback_by_video_or_project(
        cls,
        identifier: str,
        product_id: str = "",
        angle_id: str = "",
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> List[str]:
        """
        Finds the angle matching the given video filename or project_name,
        and rolls its status back.
        If only the video MP4 was removed but the timeline project still exists on disk,
        the angle transitions to 'in_production' (keeping project_name).
        If the project itself was deleted or does not exist, it rolls back to 'scripted'.

        `product_id`/`angle_id` scope the match to the specific angle the
        caller is actually rolling back. When given, only that exact angle is
        ever touched -- filename stems are not unique across products/angles
        (two angles can render to files that stem-match), so matching by
        filename alone risks rolling back an unrelated angle that happens to
        share the same stem. When omitted (legacy callers that only know the
        filename), at most ONE angle is still touched: the first match, and a
        warning is logged if more than one candidate exists, since silently
        mutating every stem-alike angle is exactly the bug this guards against.
        """
        scope = cls._scope(channel_id, all_channels)
        if not identifier:
            return []
        target_token = Path(identifier).stem.lower().strip()
        raw_id_low = identifier.lower().strip()
        projects_dir = BASE_DIR / "03_Projects"
        rolled_back = []

        def _roll(product, angle):
            # Deleting an older export of the same angle must not demote the
            # angle whose different export was already posted. The delete
            # API decides whether the exact file is protected; this guard
            # keeps the follow-up status rollback safe when that exact-file
            # check correctly allows an older version through.
            if angle.get("status") == "posted" or angle.get("posted_at"):
                return
            cur_p_name = angle.get("project_name")
            has_proj = False
            if cur_p_name:
                # If the identifier being deleted IS the project itself, project will not exist
                if cur_p_name.lower() != raw_id_low and cur_p_name.lower() != target_token:
                    proj_dir = projects_dir / cur_p_name
                    if proj_dir.exists() and proj_dir.is_dir():
                        has_proj = True

            if has_proj:
                angle["status"] = "in_production"
                angle["video_url"] = None
                angle["export_id"] = None
            else:
                angle["status"] = "scripted"
                angle["video_url"] = None
                angle["export_id"] = None
                angle["project_name"] = None

            angle["updated_at"] = cls._now()
            product["updated_at"] = cls._now()
            rolled_back.append(angle.get("angle_id", ""))

        with cls._scoped_mutate(scope) as products:
            # Scoped path: caller knows product_id and angle_id.
            # When multiple batches share angle_id, identify the exact angle using identifier/batch.
            if product_id and angle_id:
                target_batch = _extract_batch_from_name(identifier)
                for product in products:
                    if product.get("id") != product_id:
                        continue
                    candidates = []
                    for angle in product.get("angles", []):
                        current_aid = angle.get("angle_id") or angle.get("id")
                        if current_aid == angle_id:
                            candidates.append(angle)

                    if candidates:
                        chosen = None
                        # 1. Match angle directly referencing identifier
                        for a in candidates:
                            cur_p = (a.get("project_name") or "").lower()
                            cur_v = (a.get("video_url") or "").lower()
                            if cur_p in (raw_id_low, target_token) or (cur_v and target_token in cur_v):
                                chosen = a
                                break
                        # 2. Match target_batch extracted from identifier
                        if chosen is None and target_batch is not None:
                            for a in candidates:
                                if (a.get("batch") or 1) == target_batch:
                                    chosen = a
                                    break
                        # 3. Fallback to first candidate
                        if chosen is None:
                            chosen = candidates[0]

                        _roll(product, chosen)
                        return rolled_back
                return rolled_back

            # Legacy path: only the filename/project_name is known. Stop after
            # the first match -- and warn if more exist -- rather than silently
            # cascading the rollback onto every angle that happens to share the
            # same filename stem.
            matches = []
            for product in products:
                for angle in product.get("angles", []):
                    v_url = (angle.get("video_url") or "").lower()
                    p_name = (angle.get("project_name") or "").lower()
                    v_name = Path(v_url).name.lower() if v_url else ""
                    v_stem = Path(v_url).stem.lower() if v_url else ""

                    is_match = (
                        (p_name and (p_name == raw_id_low or p_name == target_token)) or
                        (v_name and (v_name == raw_id_low or v_name == Path(identifier).name.lower())) or
                        (v_stem and v_stem == target_token)
                    )
                    if is_match:
                        matches.append((product, angle))

            if not matches:
                return rolled_back

            if len(matches) > 1:
                print(
                    f"[ProductStore.rollback_by_video_or_project] WARNING: '{identifier}' matched "
                    f"{len(matches)} angles by filename/project stem alone -- rolling back only the "
                    "first (product_id="
                    f"{matches[0][0].get('id')!r}, angle_id={(matches[0][1].get('angle_id') or matches[0][1].get('id'))!r}). "
                    "Pass product_id/angle_id explicitly to avoid this ambiguity."
                )

            # Round BUG-3: used to skip posted angles entirely --
            # deleting the file behind an already-posted clip left its card
            # showing as if the video still existed. A user-triggered delete
            # (unlike reconcile's passive best-effort scan) should always
            # cascade, regardless of how far the angle's status advanced.
            product, angle = matches[0]
            _roll(product, angle)
            return rolled_back

    @classmethod
    def update_angle_videos(
        cls,
        product_id: str,
        angle_id: str,
        selected_videos: List[str],
        batch: Optional[int] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Persists selected raw footage attachments for a specific script angle in a product."""
        scope = cls._scope(channel_id, all_channels)
        rel_videos = [_to_relative(v) for v in selected_videos]
        effective_batch = batch
        if effective_batch is None:
            match_b = re.search(r"_b(\d+)$", str(angle_id))
            if match_b:
                effective_batch = int(match_b.group(1))

        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    angles = product.get("angles", [])
                    matched_angle = None
                    for angle in angles:
                        if (angle.get("angle_id") or angle.get("id")) == angle_id:
                            if effective_batch is not None and (angle.get("batch") or 1) == effective_batch:
                                matched_angle = angle
                                break
                            elif effective_batch is None and matched_angle is None:
                                matched_angle = angle
                    if matched_angle is not None:
                        matched_angle["selected_videos"] = rel_videos
                        matched_angle["selected_video"] = rel_videos[0] if rel_videos else None
                        matched_angle["updated_at"] = cls._now()
                        product["updated_at"] = cls._now()
                        return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def update_angle_voice(
        cls,
        product_id: str,
        angle_id: str,
        voice_preset: Optional[str] = None,
        voice_engine_type: Optional[str] = None,
        ad_tone: Optional[str] = None,
        batch: Optional[int] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Persists voice configuration for a specific script angle in a product."""
        scope = cls._scope(channel_id, all_channels)
        effective_batch = batch
        if effective_batch is None:
            match_b = re.search(r"_b(\d+)$", str(angle_id))
            if match_b:
                effective_batch = int(match_b.group(1))

        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    matched_angle = None
                    for angle in product.get("angles", []):
                        if (angle.get("angle_id") or angle.get("id")) == angle_id:
                            if effective_batch is not None and (angle.get("batch") or 1) == effective_batch:
                                matched_angle = angle
                                break
                            elif effective_batch is None and matched_angle is None:
                                matched_angle = angle
                    if matched_angle is not None:
                        if voice_preset is not None:
                            matched_angle["voice_preset"] = voice_preset
                        if voice_engine_type is not None:
                            matched_angle["voice_engine_type"] = voice_engine_type
                        if ad_tone is not None:
                            matched_angle["ad_tone"] = ad_tone
                        matched_angle["updated_at"] = cls._now()
                        product["updated_at"] = cls._now()
                        return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def update_angle_manual_shot_map(
        cls,
        product_id: str,
        angle_id: str,
        shot_map: List[Dict[str, Any]],
        batch: Optional[int] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Persists a user-curated shot map (list of pinned beat→scene assignments)
        for a specific script angle. Each entry: {beat_index, video_path, trim_start, trim_end}.
        The pipeline reads this during ShotMatchingStage to skip AI Vision for pinned beats.
        """
        scope = cls._scope(channel_id, all_channels)
        # Normalize video_path fields to relative paths so the store stays portable.
        normalized = []
        for entry in shot_map:
            norm = dict(entry)
            if norm.get("video_path"):
                v = _to_relative(norm["video_path"]) or norm["video_path"]
                norm["video_path"] = str(v).replace("\\", "/")
            normalized.append(norm)

        effective_batch = batch
        if effective_batch is None:
            match_b = re.search(r"_b(\d+)$", str(angle_id))
            if match_b:
                effective_batch = int(match_b.group(1))

        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    matched_angle = None
                    for angle in product.get("angles", []):
                        if (angle.get("angle_id") or angle.get("id")) == angle_id:
                            if effective_batch is not None and (angle.get("batch") or 1) == effective_batch:
                                matched_angle = angle
                                break
                            elif effective_batch is None and matched_angle is None:
                                matched_angle = angle

                    if matched_angle is not None:
                        matched_angle["manual_shot_map"] = normalized
                        matched_angle["updated_at"] = cls._now()
                        product["updated_at"] = cls._now()
                        return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}' หรือ angle '{angle_id}'")

    @classmethod
    def batch_update_manual_shot_maps(
        cls,
        product_id: str,
        updates_by_angle: Dict[str, List[Dict[str, Any]]],
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """Atomically updates manual shot maps for multiple angles in one mutation.
        updates_by_angle: { angle_id or angle_id_b{batch}: [ {beat_index, video_path, trim_start, trim_end}, ... ] }
        """
        scope = cls._scope(channel_id, all_channels)
        normalized_updates = {}
        for ang_id, shot_map in updates_by_angle.items():
            normalized = []
            for entry in shot_map:
                norm = dict(entry)
                if norm.get("video_path"):
                    v = _to_relative(norm["video_path"]) or norm["video_path"]
                    norm["video_path"] = str(v).replace("\\", "/")
                normalized.append(norm)
            normalized_updates[ang_id] = normalized

        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    for angle in product.get("angles", []):
                        ang_id = angle.get("angle_id")
                        ang_batch = angle.get("batch") or 1
                        batch_key = f"{ang_id}_b{ang_batch}"
                        if batch_key in normalized_updates:
                            angle["manual_shot_map"] = normalized_updates[batch_key]
                            angle["updated_at"] = cls._now()
                        elif ang_id in normalized_updates:
                            angle["manual_shot_map"] = normalized_updates[ang_id]
                            angle["updated_at"] = cls._now()
                    product["updated_at"] = cls._now()
                    return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")




    @classmethod
    def set_default_videos_for_all_angles(cls, product_id: str, selected_videos: List[str], *, channel_id: Optional[str] = None, all_channels: bool = False) -> Dict[str, Any]:
        """Sets default raw footage attachments for all script angles belonging to this product."""
        scope = cls._scope(channel_id, all_channels)
        rel_videos = [_to_relative(v) for v in selected_videos]
        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    for angle in product.get("angles", []):
                        # Do not overwrite angles that are actively in_production in timeline
                        if angle.get("status") == "in_production" or (angle.get("project_name") and angle.get("status") not in ("rendered", "posted")):
                            continue
                        angle["selected_videos"] = rel_videos
                        angle["selected_video"] = rel_videos[0] if rel_videos else None
                        angle["updated_at"] = cls._now()
                    # Also ensure each video is in product['videos']. `path`
                    # is kept absolute here -- scripts/api_videos.py (off
                    # limits for this change) does exact string comparisons
                    # like `v.get("path") == str(some_absolute_path)` when
                    # renaming/deleting raw files, so `path` must stay
                    # resolvable the same way it always was. `rel_path` is
                    # what actually becomes genuinely relative (it used to
                    # be a lie: the exact same absolute string as `path`).
                    v_list = product.setdefault("videos", [])
                    for v_path, rel in zip(selected_videos, rel_videos):
                        v_abs = str(_to_absolute(v_path))
                        if not any(v.get("path") == v_path or v.get("rel_path") == rel or v.get("path") == v_abs for v in v_list):
                            v_list.append({"rel_path": rel, "path": v_abs})
                    product["updated_at"] = cls._now()
                    return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def add_video_to_product(cls, product_id: str, video_info: Dict[str, Any], *, channel_id: Optional[str] = None, all_channels: bool = False) -> Dict[str, Any]:
        """Attaches a raw footage item specifically to a product.

        `video_info` normally comes from media_service.get_file_info(), whose
        `path` is already an absolute string and `rel_path` already
        BASE_DIR-relative -- that shape is preserved as-is here (not
        rewritten to relative) because scripts/api_videos.py (off limits for
        this change) does exact string comparisons against `path` as an
        absolute string when renaming/deleting raw files. A caller that
        passes only a bare/relative path in `path` or `rel_path` gets both
        fields filled in consistently (absolute in `path`, relative in
        `rel_path`) rather than stored as a half-formed dict.
        """
        scope = cls._scope(channel_id, all_channels)
        video_info = dict(video_info)
        raw_path = video_info.get("path") or video_info.get("rel_path")
        if raw_path:
            rel = _to_relative(raw_path)
            abs_path = str(_to_absolute(raw_path))
            video_info["path"] = video_info.get("path") or abs_path
            video_info["rel_path"] = rel
        else:
            rel = None

        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    v_list = product.setdefault("videos", [])
                    # Avoid duplicates
                    if not any(
                        v.get("path") == video_info.get("path")
                        or v.get("rel_path") == rel
                        for v in v_list
                    ):
                        v_list.append(video_info)
                    product["updated_at"] = cls._now()
                    return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def remove_video_from_product(cls, product_id: str, video_path: str, *, channel_id: Optional[str] = None, all_channels: bool = False) -> Dict[str, Any]:
        """Removes a footage link from a product."""
        scope = cls._scope(channel_id, all_channels)
        rel = _to_relative(video_path)
        abs_str = str(_to_absolute(video_path)) if video_path else None
        with cls._scoped_mutate(scope) as products:
            for product in products:
                if product["id"] == product_id:
                    v_list = product.get("videos", [])
                    product["videos"] = [
                        v for v in v_list
                        if v.get("path") != video_path and v.get("rel_path") != video_path
                        and v.get("path") != rel and v.get("rel_path") != rel
                        and v.get("path") != abs_str and v.get("rel_path") != abs_str
                    ]
                    product["updated_at"] = cls._now()
                    return product
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

    @classmethod
    def get_product_videos(
        cls, product_id: str, *, channel_id: Optional[str] = None, all_channels: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieves all footage assigned to a product."""
        product = cls.get(product_id, channel_id=channel_id, all_channels=all_channels)
        if not product:
            return []
        return product.get("videos", [])

    @classmethod
    def remove_angle(
        cls,
        product_id: str,
        angle_id: str,
        batch: Optional[int] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ) -> Dict[str, Any]:
        """
        Drop one angle (its hook, script and caption) from a product.

        Returns what happened, including whether the product itself was removed
        because that was its last angle -- a product with no angles left is an
        empty card in the tracker, not something to keep.

        Check + write happen in ONE scoped transaction (it used to read with
        get() and write back the whole angle list with update(), which could
        drop a concurrent writer's angle change).  The cached shot list is
        deleted after commit (never nested on the same sqlite connection).
        """
        scope = cls._scope(channel_id, all_channels)
        # Same get() (and so the same reconcile pass) the old code ran first;
        # the decision itself is re-made inside the transaction below.
        if not cls.get(product_id, channel_id=channel_id, all_channels=all_channels):
            raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

        effective_batch = batch
        if effective_batch is None:
            match_b = re.search(r"_b(\d+)$", str(angle_id))
            if match_b:
                effective_batch = int(match_b.group(1))

        result: Dict[str, Any]
        with cls._scoped_mutate(scope) as products:
            product = next((p for p in products if p.get("id") == product_id), None)
            if not product:
                raise ValueError(f"ไม่พบสินค้า id '{product_id}'")

            angles = product.get("angles") or []
            target = next(
                (
                    a for a in angles
                    if (a.get("angle_id") or a.get("id")) == angle_id
                    and (effective_batch is None or (a.get("batch") or 1) == effective_batch)
                ),
                None,
            )
            if not target:
                raise ValueError(f"ไม่พบมุม '{angle_id}' ในสินค้านี้")

            if target.get("status") == "posted" or target.get("posted_at"):
                raise ValueError(f"ไม่อนุญาตให้ลบมุม '{target.get('angle_name') or angle_id}' เนื่องจากถูกโพสต์ลง TikTok แล้ว (ต้องเก็บไว้เป็นหลักฐาน)")

            del_b = effective_batch or target.get("batch")
            remaining = [a for a in angles if a is not target]
            if not remaining:
                products[:] = [p for p in products if p.get("id") != product_id]
                result = {"angle_removed": angle_id, "product_removed": product_id, "angles_left": 0}
            else:
                product["angles"] = remaining
                product["updated_at"] = cls._now()
                result = {"angle_removed": angle_id, "product_removed": None, "angles_left": len(remaining)}

        cls._invalidate_shot_lists(product_id, [(angle_id, del_b)])
        return result

    @classmethod
    def find_by_project(
        cls,
        project_name: str,
        product_id: str = "",
        angle_id: str = "",
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
    ):
        """
        Which product/angle a rendered project came from.

        Prefers exact product_id/angle_id (the stable ids the render pipeline
        stamps into project.json's render_params -- see video_assembly_stage.py)
        or direct angle.project_name matching. Both are keyed off stable ids,
        never off display name/hook text: this feeds project/product deletion
        (DELETE /api/projects/{name}?scope=product), and matching by name text
        risks cascade-deleting the WRONG product when two share a display name.

        If none of that resolves anything, this refuses to guess rather than
        falling back to a name-string match -- old projects rendered before
        product_id/angle_id were recorded simply cannot be traced this way,
        and it's safer to say "not found" than to silently match on a
        collision-prone name.
        """
        products = cls._scoped_load(cls._scope(channel_id, all_channels))
        proj_batch = _extract_batch_from_name(project_name)

        # 1. Direct match on angle.project_name
        for product in products:
            if product_id and product.get("id") != product_id:
                continue
            for angle in product.get("angles") or []:
                if angle.get("project_name") == project_name:
                    return product, angle

        # 2. Match by product_id and angle_id (respecting batch)
        if product_id:
            for product in products:
                if product.get("id") == product_id:
                    if angle_id:
                        # If project_name has a batch suffix, prefer the angle with matching batch
                        if proj_batch is not None:
                            for angle in product.get("angles") or []:
                                if (angle.get("angle_id") or angle.get("id")) == angle_id and (angle.get("batch") or 1) == proj_batch:
                                    return product, angle
                        # Otherwise, find the first angle that doesn't claim a different existing project on disk
                        projects_dir = BASE_DIR / "03_Projects"
                        for angle in product.get("angles") or []:
                            if (angle.get("angle_id") or angle.get("id")) == angle_id:
                                cur_p = angle.get("project_name")
                                if not cur_p or cur_p == project_name or not (projects_dir / str(cur_p)).exists():
                                    return product, angle
                    return product, None

        # 3. Match in product.projects list (still id-based: project_name is
        # the same stable folder-name key recorded in product.projects, not
        # a display-name heuristic)
        for product in products:
            if project_name in (product.get("projects") or []):
                for angle in product.get("angles") or []:
                    if angle.get("project_name") == project_name:
                        return product, angle
                return product, None

        print(
            f"[ProductStore.find_by_project] WARNING: no stable-id match for project "
            f"'{project_name}' (product_id={product_id!r}, angle_id={angle_id!r}) -- "
            "refusing to fall back to a name-based guess."
        )
        return None, None

    @classmethod
    def delete(cls, product_id: str, force: bool = False, *, channel_id: Optional[str] = None, all_channels: bool = False) -> None:
        scope = cls._scope(channel_id, all_channels)
        with cls._scoped_mutate(scope) as products:
            target = next((p for p in products if p["id"] == product_id), None)
            if not target:
                raise ValueError(f"ไม่พบสินค้า id '{product_id}'")
            posted_angles = [
                a for a in target.get("angles", [])
                if a.get("status") == "posted" or a.get("posted_at")
            ]
            if posted_angles and not force:
                raise ValueError(
                    f"ไม่อนุญาตให้ลบสินค้า '{target.get('name')}' เนื่องจากมีคลิปที่โพสต์ลง TikTok แล้ว {len(posted_angles)} มุม (ต้องเก็บไว้เป็นหลักฐาน หรือระบุ force=True เพื่อยืนยันบังคับลบ)"
                )
            remaining = [p for p in products if p["id"] != product_id]
            products[:] = remaining

    # ------------------------------------------------------------------
    # Reading & Automatic Reconciliation
    # ------------------------------------------------------------------
    @classmethod
    def reconcile_existing_projects(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> bool:
        """
        Scans 03_Projects and 04_Exports to match existing rendered projects
        with their corresponding angles in products.json.

        Scoped: only the products visible to ``channel_id`` are matched and
        rewritten (another channel's products are never exposed to the scan,
        so a project folder can never unlink/claim another channel's angle).
        """
        scope = cls._scope(channel_id, all_channels)
        projects_dir = BASE_DIR / "03_Projects"
        exports_dir = BASE_DIR / "04_Exports" / "Ready_to_post"
        # A posted clip's mp4 lives here now (Round POST-1.4) -- if this scan
        # only checked Ready_to_post, a posted clip would look exactly like
        # "no export exists yet" the moment it was moved out.
        posted_dir = BASE_DIR / "04_Exports" / "Posted"

        # Checked before opening the transaction: there is nothing to
        # reconcile against without the folder, so no reason to take the
        # write lock.
        if not projects_dir.exists():
            return False

        now = time.monotonic()
        reconcile_scope = (str(BASE_DIR), str(STORE_PATH), scope.channel_id, scope.include_legacy)
        if (
            cls._last_reconcile_scope == reconcile_scope
            and now - cls._last_reconcile_at < cls._RECONCILE_MIN_INTERVAL_S
        ):
            return False
        cls._last_reconcile_scope = reconcile_scope
        cls._last_reconcile_at = now

        # Fetched ONCE, here, *before* the products transaction opens below.
        # ExportRegistry shares this store's own store.db connection (see
        # scripts/db.py): _reconcile_into() used to call
        # ExportRegistry.find_by_path()/latest_for_angle() live, from
        # *inside* the open _mutate() transaction below -- since that's the
        # same connection, a second nested `BEGIN IMMEDIATE` on an
        # already-open transaction raises sqlite3.OperationalError: cannot
        # start a transaction within a transaction (not caught by
        # _retry_on_locked in db.py, which only retries "database is
        # locked"). Snapshot everything the scan needs from ExportRegistry
        # here instead, and hand it in as plain data -- see
        # _preferred_registered_export / _registry_record_for_path.
        # P2.2: same scope as the products scan, so a channel's angles are
        # only ever matched against that channel's exports.
        if scope.channel_id is not None:
            export_records = ExportRegistry.all(channel_id=scope.channel_id)
        elif scope.all_channels:
            export_records = ExportRegistry.all(all_channels=True)
        else:
            export_records = ExportRegistry.all()

        changed = False
        # The scan below reads the disk and rewrites angle status/paths, so
        # it has to hold the same transaction the read happened in -- it used
        # to _load() here and _save() at the end, which is exactly the
        # lost-update race 83a9f1e closed everywhere else: get_all() calls
        # this on every product listing, so a UI poll and a finishing render
        # could each read the same list and one silently drop the other's
        # reconciliation. _mutate() commits without rewriting when nothing
        # actually changed, which is the common case here.
        with cls._scoped_mutate(scope) as products:
            if not products:
                return False
            changed = cls._reconcile_into(products, projects_dir, exports_dir, posted_dir, export_records)
        return changed

    @classmethod
    def _reconcile_into(
        cls,
        products,
        projects_dir,
        exports_dir,
        posted_dir,
        export_records: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """The scan itself, mutating `products` in place. Returns True when
        anything changed. Split out so the transaction boundary above stays
        readable; not meant to be called directly from inside a _mutate()
        block other than reconcile_existing_projects()'s own.

        `export_records` should be a pre-fetched `ExportRegistry.all()`
        snapshot when the caller is already inside a products _mutate()
        transaction (see reconcile_existing_projects). Defaults to a live
        fetch so direct callers (tests, tooling) outside any open
        transaction keep working unchanged.
        """
        if export_records is None:
            export_records = ExportRegistry.all()

        changed = False

        for p_folder in projects_dir.iterdir():
            if not p_folder.is_dir():
                continue
            manifest_file = p_folder / "project.json"
            if not manifest_file.exists():
                continue

            try:
                p_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            p_rp = p_data.get("render_params", {}) or {}
            p_pid = p_rp.get("product_id") or p_data.get("product_id")
            p_aid = p_rp.get("angle_id") or p_data.get("angle_id")

            # Check if an exported MP4 exists. project.json's own
            # artifacts.mp4_video.path is written absolute by
            # video_assembly_stage.py -- normalize to BASE_DIR-relative
            # before it ever reaches angle["video_url"] below, so this
            # store keeps its own data relative regardless of what other
            # writers put in project.json.
            mp4_path = None
            mp4_export_id = None
            art_mp4_obj = (p_data.get("artifacts") or {}).get("mp4_video")
            art_mp4 = art_mp4_obj.get("path") if isinstance(art_mp4_obj, dict) else None
            if art_mp4 and _to_absolute(art_mp4).exists():
                mp4_path = _to_relative(art_mp4)
            else:
                # Newest-match-wins fallback (see _find_mp4_by_glob) --
                # a project re-rendered without cleanup can leave more than
                # one export file behind; always prefer the latest one.
                mp4_path = _find_mp4_by_glob(p_folder.name, exports_dir, posted_dir)

            # An interrupted worker's partial manifest must not resurrect the
            # orphaned in_production state restored during restart recovery.
            # Existing completed output remains authoritative.
            if p_data.get("render_interrupted") and not mp4_path:
                continue

            # Match against products.
            #
            # Round BUG-3: this used to apply the update below to EVERY
            # angle that matched, with no cap -- if two angles both claimed
            # this same p_folder (one legitimately via its own manifest,
            # one only because its own project_name field already said so),
            # both got the same video_url/status, forever, since condition
            # #2 just re-confirms whatever project_name an angle already
            # has without ever verifying it's actually this angle's own
            # render. Now: condition #1 (this folder's OWN manifest names
            # this exact product+angle) is ground truth and always wins.
            # Condition #2 (self-referential -- "an angle already claims
            # this folder") is only a fallback, and at most ONE angle may
            # win it per folder per pass; every other angle claiming the
            # same folder is a data conflict and gets unlinked back to
            # scripted instead of silently mirroring the winner's clip.
            exact_name_match = None
            authoritative_match = None  # (product, angle) via condition #1
            self_ref_matches = []       # [(product, angle), ...] via condition #2
            folder_batch = _extract_batch_from_name(p_folder.name)

            for product in products:
                # If project explicitly specified a product_id, it MUST match product["id"]
                if p_pid and product.get("id") and p_pid != product.get("id"):
                    continue

                for angle in product.get("angles", []):
                    current_aid = angle.get("angle_id") or angle.get("id")
                    angle_batch = angle.get("batch") or 1

                    # 1. Exact Product ID + Angle ID match from project manifest
                    if p_pid and p_aid and product.get("id") == p_pid and current_aid == p_aid:
                        batch_matches = (folder_batch is None) or (folder_batch == angle_batch)
                        if angle.get("project_name") == p_folder.name:
                            if batch_matches or exact_name_match is None:
                                exact_name_match = (product, angle)
                        elif batch_matches and authoritative_match is None and not (
                            angle.get("project_name")
                            and angle.get("project_name") != p_folder.name
                            and (projects_dir / str(angle.get("project_name"))).exists()
                        ):
                            authoritative_match = (product, angle)
                    # 2. Already explicitly linked by project_name on this angle
                    elif angle.get("project_name") and angle.get("project_name") == p_folder.name:
                        self_ref_matches.append((product, angle))

            winner = exact_name_match or authoritative_match or (self_ref_matches[0] if self_ref_matches else None)

            if not winner and p_pid and p_aid:
                for product in products:
                    if product.get("id") == p_pid:
                        base_angle = next(
                            (
                                a for a in product.get("angles", [])
                                if (a.get("angle_id") or a.get("id")) == p_aid
                                and (folder_batch is None or (a.get("batch") or 1) == folder_batch)
                            ),
                            None,
                        )
                        if base_angle:
                            variant_angle = dict(base_angle)
                            suffix = p_folder.name.rsplit('_', 1)[-1] if '_' in p_folder.name else 'var'
                            cand_aid = f"{p_aid}_{suffix}"
                            existing_aids = {a.get("angle_id") for a in product.get("angles", [])}
                            if cand_aid in existing_aids:
                                cand_aid = f"{cand_aid}_{uuid.uuid4().hex[:4]}"
                            variant_angle["angle_id"] = cand_aid
                            variant_angle["project_name"] = p_folder.name
                            variant_angle["status"] = "in_production"
                            variant_angle["video_url"] = None
                            variant_angle["export_id"] = None
                            variant_angle["qc_reviewed"] = False
                            variant_angle["updated_at"] = cls._now()
                            product["angles"].append(variant_angle)
                            winner = (product, variant_angle)
                            changed = True
                        break

            # Any OTHER angle that also claimed this p_folder.name is a conflict and must be unlinked!
            for product in products:
                if p_pid and product.get("id") and p_pid != product.get("id"):
                    continue
                for angle in product.get("angles", []):
                    if winner and angle is winner[1]:
                        continue
                    if angle.get("project_name") == p_folder.name:
                        angle["project_name"] = None
                        angle["video_url"] = None
                        angle["export_id"] = None
                        angle["status"] = "scripted"
                        angle["data_conflict_note"] = (
                            f"ปลดออกจาก '{p_folder.name}' อัตโนมัติ — ชนกับ angle อื่นที่ผูกกับคลิปนี้ถูกต้องกว่า ({cls._now()})"
                        )
                        angle["updated_at"] = cls._now()
                        changed = True

            if winner:
                product, angle = winner

                # Resolve the actual per-file identity after the logical
                # product/angle match. This prevents a stale Ready copy from
                # winning over the Posted proof when both paths exist.
                mp4_path, mp4_export_id = _preferred_registered_export(
                    export_records,
                    product.get("id"),
                    angle.get("angle_id") or angle.get("id"),
                    mp4_path,
                    project_name=p_folder.name,
                    batch=angle.get("batch"),
                )

                # Ensure project is linked
                if angle.get("project_name") != p_folder.name:
                    angle["project_name"] = p_folder.name
                    changed = True

                if mp4_path:
                    # If angle has a QC failure note or is explicitly set to in_production,
                    # do NOT automatically overwrite it to 'rendered'!
                    if angle.get("qc_note"):
                        if angle.get("status") != "in_production":
                            angle["status"] = "in_production"
                            changed = True
                        if angle.get("video_url") != mp4_path:
                            angle["video_url"] = mp4_path
                            changed = True
                    elif angle.get("status") == "posted" or angle.get("posted_at"):
                        # Preserve permanent posted status
                        if angle.get("status") != "posted":
                            angle["status"] = "posted"
                            changed = True
                        if angle.get("video_url") != mp4_path:
                            angle["video_url"] = mp4_path
                            changed = True
                    elif angle.get("status") == "in_production":
                        # An MP4 was found on disk even though the angle is
                        # still flagged in_production.  This happens when the
                        # render pipeline completes successfully but the
                        # api_render.py status-write either runs after an
                        # earlier reconcile pass (rare but real) or the app
                        # restarted mid-render and the task-manager reverted
                        # the status before this pass ran.  Regardless of how
                        # we got here: a file on disk IS the proof the render
                        # finished -- promote to "rendered" exactly like the
                        # normal promotion path does.
                        if angle.get("status") != "rendered" or angle.get("video_url") != mp4_path:
                            if angle.get("video_url") != mp4_path:
                                # See update_angle_status()'s mark_qc_passed
                                # doc: a different rendered file is
                                # unreviewed by definition.
                                angle["qc_reviewed"] = False
                            angle["status"] = "rendered"
                            angle["video_url"] = mp4_path
                            angle["status_updated_at"] = cls._now()
                            changed = True
                    else:
                        if angle.get("status") != "rendered" or angle.get("video_url") != mp4_path:
                            if angle.get("video_url") != mp4_path:
                                angle["qc_reviewed"] = False
                            angle["status"] = "rendered"
                            angle["video_url"] = mp4_path
                            # Same stamp update_angle_status() sets -- this
                            # promotion is itself a legitimate status change,
                            # and without this stamp the strict-validation
                            # pass later in this same function (or the very
                            # next poll) has no way to tell this apart from
                            # a stale "rendered" and could revert it right
                            # back on a single disk-check miss.
                            angle["status_updated_at"] = cls._now()
                            changed = True

                    if mp4_export_id and angle.get("export_id") != mp4_export_id:
                        angle["export_id"] = mp4_export_id
                        changed = True
                elif angle.get("status") == "posted" or angle.get("posted_at"):
                    if angle.get("posted_at") and angle.get("status") != "posted":
                        angle["status"] = "posted"
                        changed = True
                    pass
                    # heuristic came up empty, which used to be read
                    # as "no export was ever made" and wiped the
                    # angle back to in_production. That is exactly
                    # what happened to a posted clip the instant its
                    # file moved to Posted/ and its manifest's
                    # artifacts.mp4_video.path (still pointing at the
                    # old Ready_to_post location) stopped resolving.
                    # An already-posted clip does not get less posted
                    # because this pass could not find its file.
                    pass
                else:
                    # Project timeline exists in 03_Projects, but this pass's
                    # own mp4_path lookup (manifest path + exports/posted
                    # glob) came up empty. If the angle isn't currently
                    # "rendered", there's nothing to protect -- just apply
                    # the "MUST be in_production" rule as before. If it IS
                    # "rendered", this is exactly the hazard described on
                    # product_store.py's module docstring history: a status
                    # just committed by update_angle_status() (or by the
                    # promotion above) can lose this one lookup to a
                    # transient path-resolution/AV-lock/fsync-visibility
                    # miss. Before reverting a "rendered" angle: (a) retry
                    # via the same glob fallback the lookup above already
                    # uses -- a stale/mismatched manifest path shouldn't cost
                    # a real file that's actually sitting in exports_dir/
                    # posted_dir under a different name, and (b) if that
                    # still finds nothing, give a freshly-set status a grace
                    # period before trusting this single check enough to
                    # revert it.
                    if angle.get("status") == "rendered":
                        retry_mp4 = _find_mp4_by_glob(p_folder.name, exports_dir, posted_dir)
                        if retry_mp4:
                            retry_record = _registry_record_for_path(export_records, retry_mp4)
                            retry_export_id = retry_record.get("id") if retry_record else None
                            if angle.get("video_url") != retry_mp4 or (
                                retry_export_id and angle.get("export_id") != retry_export_id
                            ):
                                angle["video_url"] = retry_mp4
                                if retry_export_id:
                                    angle["export_id"] = retry_export_id
                                changed = True
                        elif _within_grace_period(angle.get("status_updated_at")):
                            pass  # freshly rendered -- do not revert yet
                        elif angle.get("status") != "in_production" or angle.get("video_url") is not None:
                            angle["status"] = "in_production"
                            angle["video_url"] = None
                            changed = True
                    elif angle.get("status") != "in_production" or angle.get("video_url") is not None:
                        angle["status"] = "in_production"
                        angle["video_url"] = None
                        changed = True

                p_list = product.setdefault("projects", [])
                if p_folder.name not in p_list:
                    p_list.append(p_folder.name)
                    changed = True

        # Strict state validation: Clean up any angle whose project or video does not actually exist on disk,
        # or where non-posted angles claim duplicate project_names or video_urls across the product
        for product in products:
            # Resolve duplicate project_name claims and alien batch claims within the same product
            seen_projs: Dict[str, Any] = {}
            for angle in product.get("angles", []):
                if angle.get("status") == "posted" or angle.get("posted_at"):
                    continue
                p_name = angle.get("project_name")
                if not p_name:
                    continue
                p_batch = _extract_batch_from_name(p_name)
                a_batch = angle.get("batch") or 1

                if p_name in seen_projs:
                    prev_angle = seen_projs[p_name]
                    prev_batch = prev_angle.get("batch") or 1
                    if p_batch is not None and a_batch == p_batch and prev_batch != p_batch:
                        # Current angle matches project batch; demote previous claimant
                        prev_angle["project_name"] = None
                        prev_angle["video_url"] = None
                        prev_angle["export_id"] = None
                        prev_angle["status"] = "scripted"
                        prev_angle["updated_at"] = cls._now()
                        seen_projs[p_name] = angle
                        changed = True
                    else:
                        # Current angle loses
                        angle["project_name"] = None
                        angle["video_url"] = None
                        angle["export_id"] = None
                        angle["status"] = "scripted"
                        angle["updated_at"] = cls._now()
                        changed = True
                else:
                    # Check if p_name has a batch suffix that clearly belongs to another angle in this product
                    if p_batch is not None and a_batch != p_batch:
                        cur_aid = angle.get("angle_id") or angle.get("id")
                        has_other_match = any(
                            (o.get("batch") or 1) == p_batch and (o.get("angle_id") or o.get("id")) == cur_aid
                            for o in product.get("angles", []) if o is not angle
                        )
                        if has_other_match:
                            angle["project_name"] = None
                            angle["video_url"] = None
                            angle["export_id"] = None
                            angle["status"] = "scripted"
                            angle["updated_at"] = cls._now()
                            changed = True
                            continue
                    seen_projs[p_name] = angle

            for angle in product.get("angles", []):
                # An angle that has been posted is permanently sealed as proof/archive.
                # Never revert or demote posted angles under any circumstances.
                if angle.get("status") == "posted" or angle.get("posted_at"):
                    if angle.get("status") != "posted":
                        angle["status"] = "posted"
                        changed = True
                    continue

                p_name = angle.get("project_name")
                has_proj = False
                if p_name:
                    p_path = projects_dir / p_name
                    manifest_file = p_path / "project.json"
                    if p_path.exists() and p_path.is_dir() and manifest_file.exists():
                        try:
                            m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                            proj_pid = m_data.get("product_id") or m_data.get("render_params", {}).get("product_id")
                            # Verify that the project belongs to this product!
                            if not proj_pid or proj_pid == product.get("id"):
                                has_proj = True
                        except Exception:
                            has_proj = False

                # Also verify HyperFrames composition existence
                if not has_proj and (angle.get("draft_type") == "hyperframes" or angle.get("clip_id")):
                    c_id = angle.get("clip_id")
                    if c_id:
                        hf_file = projects_dir / "_HyperFrames_Studio" / "clips" / c_id / "index.html"
                        if hf_file.exists():
                            has_proj = True

                has_video = False
                v_url = angle.get("video_url")
                if v_url:
                    if _to_absolute(v_url).exists():
                        has_video = True
                    else:
                        ready_file = exports_dir / Path(v_url).name
                        if ready_file.exists():
                            has_video = True

                if angle.get("status") == "rendered" and not has_video:
                    # CRITICAL: do not treat "this one disk check didn't
                    # resolve the file" as "this was never rendered" --
                    # update_angle_status() can commit status="rendered" and
                    # the very next get()/get_all()/list() call (exactly
                    # what a caller does to confirm the write, or what the
                    # next frontend poll does) runs this same reconcile pass
                    # immediately afterward. A single non-retried .exists()
                    # check can miss a genuinely-written file for reasons
                    # that have nothing to do with whether it was rendered
                    # (a transient path-resolution mismatch, an AV lock, or
                    # a check that lands a few hundred ms before the write's
                    # fsync is visible) -- silently reverting on that alone
                    # would erase a just-completed, successfully-committed
                    # write with no error raised anywhere.
                    #
                    # Before concluding the video truly doesn't exist:
                    # 1. Retry via the same glob fallback used elsewhere in
                    #    this function -- the stored video_url can be
                    #    stale/mismatched (e.g. pointed at Ready_to_post
                    #    after the file moved to Posted/) even outside any
                    #    grace period, so this check alone fixes real false
                    #    negatives, not just transient ones.
                    # 2. Only if that also finds nothing, consult the grace
                    #    period: a status stamped within the last
                    #    RECONCILE_GRACE_PERIOD_SECONDS was almost certainly
                    #    just legitimately set (a real render pipeline takes
                    #    far longer than that to even reach "rendered"), so
                    #    hold off reverting it this pass -- the next poll(s)
                    #    will re-check once the transient condition (if any)
                    #    has had time to clear.
                    retry_mp4 = _find_mp4_by_glob(p_name or "", exports_dir, posted_dir) if p_name else None
                    if not retry_mp4 and v_url:
                        retry_mp4 = _find_mp4_by_glob(Path(v_url).stem, exports_dir, posted_dir)
                    if not retry_mp4 and angle.get("clip_id"):
                        retry_mp4 = _find_mp4_by_glob(angle.get("clip_id"), exports_dir, posted_dir)
                    if retry_mp4:
                        if angle.get("video_url") != retry_mp4:
                            angle["video_url"] = retry_mp4
                            changed = True
                    elif _within_grace_period(angle.get("status_updated_at")):
                        pass  # freshly rendered -- give it another pass before reverting
                    elif has_proj:
                        angle["status"] = "in_production"
                        angle["video_url"] = None
                        angle["export_id"] = None
                        changed = True
                    else:
                        angle["status"] = "scripted"
                        angle["project_name"] = None
                        angle["video_url"] = None
                        angle["export_id"] = None
                        changed = True
                elif angle.get("status") == "in_production" and not has_proj:
                    # No project folder on disk or belongs to another product! Revert strictly to scripted
                    angle["status"] = "scripted"
                    angle["project_name"] = None
                    angle["video_url"] = None
                    angle["export_id"] = None
                    changed = True
                elif not has_proj and angle.get("project_name"):
                    # Dangling, deleted, or cross-product project reference on scripted angle!
                    angle["project_name"] = None
                    changed = True

                # Clean up cover paths that reference a non-existent or foreign project
                if not has_proj and p_name:
                    for c_key in ("cover_path", "cover_3x4_path", "cover_9x16_path"):
                        c_val = angle.get(c_key)
                        if c_val and p_name in c_val:
                            angle[c_key] = None
                            changed = True

            # Also ensure product["projects"] only contains existing projects belonging to this product
            if "projects" in product and isinstance(product["projects"], list):
                valid_projs = []
                for p in product["projects"]:
                    p_dir = projects_dir / p
                    p_manifest = p_dir / "project.json"
                    if p_dir.exists() and p_dir.is_dir() and p_manifest.exists():
                        try:
                            m_data = json.loads(p_manifest.read_text(encoding="utf-8"))
                            proj_pid = m_data.get("product_id") or m_data.get("render_params", {}).get("product_id")
                            if not proj_pid or proj_pid == product.get("id"):
                                valid_projs.append(p)
                        except Exception:
                            pass
                if len(valid_projs) != len(product["projects"]):
                    product["projects"] = valid_projs
                    changed = True

        return changed

    @classmethod
    def get_all(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> List[Dict[str, Any]]:
        scope = cls._scope(channel_id, all_channels)
        cls.reconcile_existing_projects(channel_id=channel_id, all_channels=all_channels)
        return cls._scoped_load(scope)

    @classmethod
    def _to_lite_product(cls, p: Dict[str, Any], mode: Any = True) -> Dict[str, Any]:
        """Convert a full product record to a lightweight or summary representation."""
        mode_str = str(mode).lower() if mode is not True else "compact"
        is_summary = mode_str in ("summary", "ultra", "2")
        lite_p = {
            "id": p.get("id"),
            "name": p.get("name"),
            "product_code": p.get("product_code"),
            "status": p.get("status"),
            "cover_image": p.get("cover_image"),
            "thumbnail": p.get("thumbnail"),
            "images": (p.get("images") or [])[:3],
            "channel_id": p.get("channel_id"),
            "created_at": p.get("created_at"),
            "updated_at": p.get("updated_at"),
            "angles_count": len(p.get("angles", [])),
            "selling_points": (p.get("selling_points") or [])[:3],
            "tiktok_product_id": p.get("tiktok_product_id"),
        }
        if is_summary:
            return lite_p

        angles = []
        for a in p.get("angles", []):
            angles.append({
                "angle_id": a.get("angle_id"),
                "angle_name": a.get("angle_name"),
                "badge": a.get("badge"),
                "status": a.get("status"),
                "video_url": a.get("video_url"),
                "cover_image": a.get("cover_image"),
                "hook_title": a.get("hook_title"),
                "updated_at": a.get("updated_at"),
                "tiktok_caption": a.get("tiktok_caption"),
                "tiktok_hashtags": a.get("tiktok_hashtags"),
                "batch": a.get("batch"),
                "format": a.get("format"),
            })
        lite_p["angles"] = angles
        return lite_p

    @classmethod
    def list(
        cls,
        status: Optional[str] = None,
        *,
        channel_id: Optional[str] = None,
        all_channels: bool = False,
        lite: Optional[str] = None,
        reconcile: bool = True,
    ) -> List[Dict[str, Any]]:
        scope = cls._scope(channel_id, all_channels)
        if reconcile:
            cls.reconcile_existing_projects(channel_id=channel_id, all_channels=all_channels)
        products = cls._scoped_load(scope)
        if status:
            products = [p for p in products if p.get("status") == status]
        products = sorted(products, key=lambda p: p.get("updated_at", ""), reverse=True)
        if lite:
            products = [cls._to_lite_product(p, mode=lite) for p in products]
        return products

    @classmethod
    def get(cls, product_id: str, *, channel_id: Optional[str] = None, all_channels: bool = False) -> Optional[Dict[str, Any]]:
        """Product by id within the scope; another channel's id -> None (404)."""
        scope = cls._scope(channel_id, all_channels)
        cls.reconcile_existing_projects(channel_id=channel_id, all_channels=all_channels)
        for product in cls._scoped_load(scope):
            if product["id"] == product_id:
                return product
        return None

    @classmethod
    def summary(cls, *, channel_id: Optional[str] = None, all_channels: bool = False) -> Dict[str, int]:
        products = cls._scoped_load(cls._scope(channel_id, all_channels))
        counts = {status: 0 for status in STATUSES}
        for product in products:
            status = product.get("status")
            if status in counts:
                counts[status] += 1
        counts["total"] = len(products)
        return counts

    # ------------------------------------------------------------------
    @classmethod
    def _generate_product_code(cls, name: str, products: Optional[List[Dict[str, Any]]] = None) -> str:
        """Short scannable code for a product, e.g. 'ESS01' for 'ESSAGER สายชาร์จ...'.

        Prefix is a naive first-3-letters of the name's first Latin word (falls
        back to 'GEN' for pure-Thai names with no Latin brand token) — this is
        meant to be corrected by hand once via the edit UI, not to be a perfect
        brand abbreviation.
        """
        match = re.search(r"[A-Za-z]+", name or "")
        prefix = (match.group(0)[:3] if match else "GEN").upper()
        if len(prefix) < 3:
            prefix = (prefix + "XXX")[:3]

        existing = products if products is not None else cls._load()
        max_n = 0
        for product in existing:
            code = (product.get("product_code") or "").upper()
            m = re.match(rf"^{re.escape(prefix)}(\d+)$", code)
            if m:
                max_n = max(max_n, int(m.group(1)))
        next_n = max_n + 1
        suffix = f"{next_n:02d}" if next_n < 100 else str(next_n)
        return f"{prefix}{suffix}"

    @staticmethod
    def detect_platform(url: str) -> str:
        lowered = (url or "").lower()
        if "shopee" in lowered:
            return "shopee"
        if "tiktok" in lowered:
            return "tiktok"
        if "lazada" in lowered:
            return "lazada"
        return ""

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now().isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(ProductStore.summary(), ensure_ascii=False, indent=2))
