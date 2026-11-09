"""Single-writer IO for the JSON-mirrored stores used by batch tools.

Audit S1-01 / S6-01 / X-01: batch tools used to read-modify-write
``_Docs/products.json``, ``_Docs/export_registry.json`` and
``_Docs/export_cover_bindings.json`` directly (plain ``write_text``, outside
the SQLite write lock, read errors silently turned into ``[]``).  A stale or
empty snapshot written back could wipe rows the server had just committed.

Every write now goes through the stores' own SQLite-backed tables
(``ProductStore`` / ``ExportRegistry`` / ``ExportCoverBindingStore``):
one ``BEGIN IMMEDIATE`` transaction per read-modify-write, the JSON mirror is
re-published by ``scripts.db`` itself, and a read error raises -- nothing is
written from an empty fallback.

``docs_dir`` defaults to ``BASE_DIR/_Docs`` (the real stores).  Passing
another directory (tests, sandboxes) uses an equivalent table on
``<docs_dir>/store.db`` with ``<docs_dir>/<table>.json`` as its mirror.
"""

from __future__ import annotations

import datetime
import hashlib
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from scripts.config import BASE_DIR
from scripts.db import DocumentTable

PRODUCTS = "products"
EXPORT_REGISTRY = "export_registry"
COVER_BINDINGS = "export_cover_bindings"
# Sibling stores that batch / reconcile tools also touch next to the three
# mirrors above (same SQLite-backed ``DocumentTable`` contract).
SCHEDULE_QUEUE = "schedule_queue"
POSTS = "posts"
_TABLE_NAMES = (PRODUCTS, EXPORT_REGISTRY, COVER_BINDINGS, SCHEDULE_QUEUE, POSTS)
_MIRROR_FILES = {POSTS: "post_log.json"}

PathLike = Union[str, Path]


def _default_docs_dir() -> Path:
    return BASE_DIR / "_Docs"


def _is_default(docs_dir: Optional[PathLike]) -> bool:
    if docs_dir is None:
        return True
    try:
        return Path(docs_dir).resolve() == _default_docs_dir().resolve()
    except OSError:
        return False


def _table(name: str, docs_dir: Optional[PathLike]) -> DocumentTable:
    if name not in _TABLE_NAMES:
        raise ValueError(f"ไม่รู้จักตารางข้อมูล: {name}")
    if _is_default(docs_dir):
        if name == PRODUCTS:
            from scripts.product_store import _TABLE as products_table
            return products_table
        if name == EXPORT_REGISTRY:
            from scripts.export_registry import _TABLE as registry_table
            return registry_table
        if name == SCHEDULE_QUEUE:
            from scripts.schedule_store import _TABLE as schedule_table
            return schedule_table
        if name == POSTS:
            from scripts.post_log import _TABLE as posts_table
            return posts_table
        from scripts.export_cover_bindings import ExportCoverBindingStore
        return ExportCoverBindingStore(BASE_DIR).table
    folder = Path(docs_dir)  # type: ignore[arg-type]
    folder.mkdir(parents=True, exist_ok=True)
    mirror_name = _MIRROR_FILES.get(name, f"{name}.json")
    return DocumentTable(name, lambda: folder / "store.db", lambda: folder / mirror_name)


def load(name: str, docs_dir: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    """Read every row of a store table. Errors raise (never ``[]``)."""
    return _table(name, docs_dir).load()


@contextmanager
def mutate(name: str, docs_dir: Optional[PathLike] = None) -> Iterator[List[Dict[str, Any]]]:
    """One transactional read-modify-write over a whole store table.

    Mutate the yielded list in place; it is persisted (SQLite + mirror) on a
    clean exit and discarded if the block raises.
    """
    default = _is_default(docs_dir)
    if name == PRODUCTS and default:
        from scripts.product_store import ProductStore
        with ProductStore._mutate() as rows:
            yield rows
        return
    with _table(name, docs_dir).mutate() as rows:
        yield rows
    if name == EXPORT_REGISTRY and default:
        from scripts.export_registry import ExportRegistry
        ExportRegistry._invalidate_index()


def load_products(docs_dir: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    return load(PRODUCTS, docs_dir)


def mutate_products(docs_dir: Optional[PathLike] = None):
    return mutate(PRODUCTS, docs_dir)


def load_export_registry(docs_dir: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    return load(EXPORT_REGISTRY, docs_dir)


def mutate_export_registry(docs_dir: Optional[PathLike] = None):
    return mutate(EXPORT_REGISTRY, docs_dir)


def load_cover_bindings(docs_dir: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    return load(COVER_BINDINGS, docs_dir)


def mutate_cover_bindings(docs_dir: Optional[PathLike] = None):
    return mutate(COVER_BINDINGS, docs_dir)


def load_schedule_queue(docs_dir: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    return load(SCHEDULE_QUEUE, docs_dir)


def mutate_schedule_queue(docs_dir: Optional[PathLike] = None):
    return mutate(SCHEDULE_QUEUE, docs_dir)


def load_posts(docs_dir: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    return load(POSTS, docs_dir)


def mutate_posts(docs_dir: Optional[PathLike] = None):
    return mutate(POSTS, docs_dir)


def apply_row_changes(
    name: str,
    baseline: List[Dict[str, Any]],
    working: List[Dict[str, Any]],
    docs_dir: Optional[PathLike] = None,
) -> int:
    """Persist only what a tool changed on a *snapshot* of a table.

    A tool that loaded ``baseline`` and edited a copy (``working``) must not
    write the whole snapshot back (that is the lost-update bug); instead the
    changed fields of each edited row are merged by ``id`` into the live rows
    inside one store transaction, so rows added by the app meanwhile survive.
    Returns the number of rows that were updated.
    """
    before = {r.get("id"): r for r in baseline if isinstance(r, dict)}
    changes: Dict[Any, Dict[str, Any]] = {}
    for row in working:
        old = before.get(row.get("id"))
        if old is None:
            continue
        diff = {k: v for k, v in row.items() if k not in old or old[k] != v}
        if diff:
            changes[row.get("id")] = diff
    if not changes:
        return 0
    updated = 0
    with mutate(name, docs_dir) as live_rows:
        for live in live_rows:
            diff = changes.get(live.get("id"))
            if diff:
                live.update(diff)
                updated += 1
    return updated


def upsert_rendered_export(
    rel_path: str,
    *,
    product_id: Optional[str],
    angle_id: Optional[str],
    project_name: Optional[str],
    channel_id: str = "main",
    docs_dir: Optional[PathLike] = None,
    now_iso: Optional[str] = None,
    new_fields: Optional[Dict[str, Any]] = None,
) -> str:
    """Register (or refresh) a rendered export the way the batch tools did:
    match by ``path``/``path_key``; an existing row gets product/angle/status
    refreshed, otherwise a new ``exp_<uuid>`` row is created (plus any
    ``new_fields``). Returns the export id. Runs in one store transaction."""
    stamp = now_iso or datetime.datetime.now().isoformat()
    with mutate(EXPORT_REGISTRY, docs_dir) as entries:
        existing = next(
            (e for e in entries if e.get("path") == rel_path or e.get("path_key") == rel_path),
            None,
        )
        if existing is not None:
            existing["product_id"] = product_id
            existing["angle_id"] = angle_id
            existing["status"] = "rendered"
            existing["updated_at"] = stamp
            return str(existing.get("id"))
        export_id = f"exp_{uuid.uuid4().hex}"
        entries.append({
            "id": export_id,
            "channel_id": channel_id,
            "path": rel_path,
            "path_key": rel_path,
            "product_id": product_id,
            "angle_id": angle_id,
            "project_name": project_name,
            "status": "rendered",
            "created_at": stamp,
            "updated_at": stamp,
            "posted_at": None,
            **(new_fields or {}),
        })
        return export_id


def default_binding_id(channel_id: str, export_id: str) -> str:
    return "cover_" + hashlib.sha256(f"{channel_id}\0{export_id}".encode()).hexdigest()


def upsert_cover_binding(
    export_id: str,
    video_path: str,
    selections: Dict[str, Dict[str, Any]],
    *,
    channel_id: str = "main",
    binding_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    bump_revision: bool = False,
    docs_dir: Optional[PathLike] = None,
    clock: Callable[[], float] = time.time,
) -> Dict[str, Any]:
    """Create or refresh the cover binding of one export in one store
    transaction (same record shape the batch tools wrote)."""
    now_ts = clock()
    with mutate(COVER_BINDINGS, docs_dir) as bindings:
        entry = next((b for b in bindings if b.get("export_id") == export_id), None)
        if entry is None:
            # Every store row needs an id; default to the canonical id that
            # ExportCoverBindingStore.save() assigns.
            entry = {"id": binding_id or default_binding_id(channel_id, export_id)}
            entry.update({
                "channel_id": channel_id,
                "export_id": export_id,
                **(extra or {}),
                "video_path": video_path,
                "selections": dict(selections),
                "revision": 1,
                "updated_at": now_ts,
            })
            bindings.append(entry)
        else:
            entry.setdefault("id", binding_id or default_binding_id(channel_id, export_id))
            entry.update(extra or {})
            entry["video_path"] = video_path
            current = entry.get("selections") if isinstance(entry.get("selections"), dict) else {}
            entry["selections"] = {**current, **selections}
            if bump_revision:
                entry["revision"] = int(entry.get("revision", 1) or 1) + 1
            entry["updated_at"] = now_ts
        return dict(entry)
