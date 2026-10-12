"""Channel-ownership migration (multi-channel P2.3): plan, apply, resume, rollback.

Contract: ``_Docs/Plans/PLAN_MULTI_CHANNEL_20261010.md`` §8 and the runbook
``_Docs/Plans/MIGRATION_RUNBOOK_MULTI_CHANNEL_20261010.md``.

What it does
------------
Backfills a top-level ``channel_id`` on legacy records (records without one)
of every channel-owned store, parents before children, using *evidence*
only (plan §11):

* products -> the legacy cohort owner (``main`` while the registry holds only
  ``main`` and no post shows a foreign TikTok handle; otherwise only with an
  explicit owner decision ``legacy_owner``);
* export_registry -> via ``product_id``; else via the project's
  ``project.json`` (``render_params.product_id``); else *unknown*;
* posts -> via ``export_id`` / ``product_id``; else a unique 1:1 basename match
  with an export of known owner; generic names (``clip.mp4``) are *unknown*;
  a post whose TikTok handle differs from the owner's handle is a *conflict*;
* schedule_queue -> via export/product (disagreeing parents = conflict);
* schedule_templates -> renamed ``default``/``week:<d>`` -> ``<owner>:default`` /
  ``<owner>:week:<d>`` (opt-in, see ``rename_templates``) + ``channel_id`` +
  ``legacy_id``;
* shot_lists / recording_sessions / batch_render_queue / task_registry
  (``payload.product_id``) / project manifests -> via product;
* tiktok_pending / tiktok_ignored / GadgetMedia -> never derived; only an
  explicit per-record owner decision can backfill legacy ownership. Gadget
  validates the P3 models, canonical layout, linked owners and materialized
  owner mirrors without regenerating stages, artifacts or frozen identity.

Unknown and conflicting rows are reported with ids, reason and a suggested
action and are left WITHOUT ``channel_id`` (legacy: visible in compat mode,
invisible in strict mode) until an explicit ``assignments`` mapping names an
owner row by row.  Nothing is ever assigned wholesale.

Safety model
------------
* dry-run (default) opens SQLite read-only (``mode=ro``; ``immutable=1`` when
  no ``-wal`` exists so no ``-wal``/``-shm`` file is created) and writes
  nothing;
* apply: preflight -> maintenance lock -> snapshot (SQLite online-backup API +
  byte copies + sha256 manifest) -> one transaction per store via
  ``DocumentTable.mutate()`` (so DB, JSON mirror and ``_json_mirror_state``
  stay in sync) -> atomic file rewrites for manifests/tasks -> validation ->
  release.  Every step is journaled (before/after hashes + exact fields
  added) under ``<root>/06_Archive/Migrations/multi_channel_v1/<run_id>/``;
* apply requires the plan hash shown by the dry-run (``expect_plan``): what
  is applied is exactly what was reviewed;
* resume re-runs unfinished steps idempotently from the persisted plan;
* rollback reverses only the journaled field additions (rows changed or
  created after cutover are kept); ``restore_snapshot_in_place`` is allowed
  only while the data still equals the post-apply fingerprint;
* every write is confined to ``root`` (plus explicitly named report /
  rehearsal paths).

Only ``root`` relative paths are used -- the default root comes from
``scripts.config.BASE_DIR``.  Never touches 01_Raw/, 02_Assets/, CapCut drafts,
media files, or moves/renames any file.
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from scripts import config
from scripts import db as _db
from scripts import maintenance_lock
from scripts.channel_store import ChannelError, ChannelStore, HandleError, normalize_handle

MIGRATION_ID = "multi_channel_v1"
PLAN_SCHEMA = 1
OWNER_KEY = "channel_id"
LEGACY_ID_KEY = "legacy_id"
LOCK_OWNER = "tools/migrate_channels.py"
GENERIC_CLIP_STEMS = frozenset(
    {"clip", "video", "output", "out", "final", "export", "render", "untitled", "temp", "tmp", "test", "movie"}
)
_TERMINAL_TASK = {"completed", "failed", "cancelled", "canceled", "error", "done"}
_ACTIVE_BATCH = {"queued", "processing", "running", "in_production"}
_SNAPSHOT_SAFETY_BYTES = 64 * 1024 * 1024

# --------------------------------------------------------------------------- errors


class MigrationError(RuntimeError):
    """Base error; ``exit_code`` is what the CLI returns."""

    exit_code = 1


class PreflightBlocked(MigrationError):
    exit_code = 2

    def __init__(self, message: str, checks: Sequence[Mapping[str, Any]] = ()):
        super().__init__(message)
        self.checks = list(checks)


class PlanMismatch(MigrationError):
    exit_code = 2


class AssignmentError(MigrationError):
    exit_code = 2

    def __init__(self, problems: Sequence[str]):
        self.problems = list(problems)
        super().__init__("ไฟล์ --assign ไม่ถูกต้อง: " + "; ".join(self.problems[:10]))


class DriftError(MigrationError):
    """Data changed between plan and apply (or under a crashed run)."""

    exit_code = 3


class ValidationFailed(MigrationError):
    exit_code = 3

    def __init__(self, problems: Sequence[str]):
        self.problems = list(problems)
        super().__init__("ตรวจผลหลังย้ายข้อมูลไม่ผ่าน: " + "; ".join(self.problems[:10]))


class RootViolation(MigrationError):
    """A write outside the allowed roots was attempted (bug guard)."""


class SimulatedCrash(BaseException):
    """Test hook: emulates the process being killed (no cleanup runs)."""


# --------------------------------------------------------------------------- helpers


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def row_hash(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _without(record: Mapping[str, Any], *keys: str) -> Dict[str, Any]:
    return {k: v for k, v in record.items() if k not in keys}


def _is_within(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve(strict=False).relative_to(Path(root).resolve(strict=False))
        return True
    except ValueError:
        return False


def _replace_with_retry(src: Path, dst: Path) -> None:
    last: Optional[BaseException] = None
    for attempt in range(25):
        try:
            os.replace(str(src), str(dst))
            return
        except PermissionError as exc:  # Windows: a reader holds the target briefly
            last = exc
            time.sleep(0.02 * (attempt + 1))
    assert last is not None
    raise last


def atomic_write_bytes(path: Path, data: bytes, *, allowed_roots: Sequence[Path]) -> None:
    """tmp (same dir) + fsync + os.replace; refuses targets outside ``allowed_roots``."""
    path = Path(path)
    if not any(_is_within(path, root) for root in allowed_roots):
        raise RootViolation(f"ปฏิเสธการเขียนนอก root: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:10]}.migtmp")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _mkdir(path: Path, *, allowed_roots: Sequence[Path]) -> None:
    if not any(_is_within(path, root) for root in allowed_roots):
        raise RootViolation(f"ปฏิเสธการสร้างโฟลเดอร์นอก root: {path}")
    path.mkdir(parents=True, exist_ok=True)


@contextlib.contextmanager
def ro_connect(db_path: Path) -> Iterator[Optional[sqlite3.Connection]]:
    """Read-only SQLite connection that creates no file in the data root.

    * no ``-wal``  -> ``mode=ro&immutable=1`` (the main file is complete);
    * ``-wal`` + ``-shm`` -> ``mode=ro`` (sees committed WAL pages; only the
      shared-memory index ``-shm`` is touched, as by any reader);
    * ``-wal`` without ``-shm`` -> copy db+wal to a private temp dir first.
    Yields ``None`` when the database file does not exist.
    """
    db_path = Path(db_path)
    if not db_path.is_file():
        yield None
        return
    wal = Path(str(db_path) + "-wal")
    shm = Path(str(db_path) + "-shm")
    tmpdir: Optional[str] = None
    if not wal.exists():
        uri = f"file:{db_path.resolve().as_posix()}?mode=ro&immutable=1"
    elif shm.exists():
        uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    else:
        tmpdir = tempfile.mkdtemp(prefix="omnicut_ro_")
        copy = Path(tmpdir) / db_path.name
        shutil.copyfile(db_path, copy)
        shutil.copyfile(wal, Path(str(copy) + "-wal"))
        uri = f"file:{copy.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        yield conn
    finally:
        conn.close()
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


def _read_rows(conn: Optional[sqlite3.Connection], table: str) -> Optional[List[Dict[str, Any]]]:
    if conn is None or not _table_exists(conn, table):
        return None
    rows = conn.execute(f"SELECT data FROM {table} ORDER BY rowid").fetchall()
    return [json.loads(r[0]) for r in rows]


def _integrity(conn: Optional[sqlite3.Connection]) -> str:
    if conn is None:
        return "missing"
    row = conn.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "no result"


def _mirror_state(conn: Optional[sqlite3.Connection]) -> Dict[str, int]:
    if conn is None or not _table_exists(conn, "_json_mirror_state"):
        return {}
    return {
        str(path): int(token)
        for path, token in conn.execute("SELECT source_path, last_imported_mtime_ns FROM _json_mirror_state")
    }


def sqlite_contents_digest(conn: Optional[sqlite3.Connection]) -> Dict[str, str]:
    """Protect every user table, including future stores, without importing mirrors."""
    result = {}
    if conn is None:
        return result
    for name, schema in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_json_mirror_state'"):
        quoted = '"' + name.replace('"', '""') + '"'
        rows = conn.execute(f"SELECT * FROM {quoted}").fetchall()
        normalized = [[{"bytes": value.hex()} if isinstance(value, bytes) else value for value in row] for row in rows]
        result[name] = row_hash({"schema": schema, "rows": sorted(normalized, key=canon)})
    return result


def sqlite_online_backup(source: Path, destination: Path) -> str:
    """WAL-consistent copy via the SQLite backup API (source opened read-only).

    Same technique as ``BackupEngine._backup_sqlite_database``; kept here so the
    source open never creates ``-wal``/``-shm`` files (see :func:`ro_connect`).
    Returns the destination's ``integrity_check`` result.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise MigrationError(f"ไฟล์ปลายทาง backup มีอยู่แล้ว: {destination}")
    with ro_connect(source) as src:
        if src is None:
            raise MigrationError(f"ไม่พบฐานข้อมูล {source}")
        dst = sqlite3.connect(str(destination), timeout=5)
        try:
            src.backup(dst)
            dst.execute("PRAGMA journal_mode=DELETE")
            integrity = _integrity(dst)
        finally:
            dst.close()
    if integrity != "ok":
        raise MigrationError(f"integrity_check ของสำเนา {destination.name} ไม่ผ่าน: {integrity}")
    return integrity


def _mirror_token(path: Path) -> Optional[int]:
    try:
        return _db._mirror_token(path)
    except OSError:
        return None


def _close_cached_connections(root: Path) -> None:
    """Close this thread's cached store connections under ``root`` (Windows
    keeps files locked while a connection is open)."""
    cache = getattr(_db._local, "conns", None) or {}
    prefix = os.path.normcase(str(Path(root).resolve()))
    for key in list(cache):
        if os.path.normcase(key).startswith(prefix):
            try:
                cache.pop(key).close()
            except Exception:
                pass
            _db._wal_enabled_paths.discard(key)


# --------------------------------------------------------------------------- layout


@dataclasses.dataclass(frozen=True)
class TableSpec:
    name: str  # store name used in plans/reports/assignments
    db_key: str  # "store" | "batch"
    table: str
    mirror_rel: str


TABLES: Tuple[TableSpec, ...] = (
    TableSpec("products", "store", "products", "_Docs/products.json"),
    TableSpec("export_registry", "store", "export_registry", "_Docs/export_registry.json"),
    TableSpec("posts", "store", "posts", "_Docs/post_log.json"),
    TableSpec("schedule_queue", "store", "schedule_queue", "_Docs/schedule_queue.json"),
    TableSpec("schedule_templates", "store", "schedule_templates", "_Docs/schedule_templates.json"),
    TableSpec("shot_lists", "store", "shot_lists", "_Docs/shot_lists.json"),
    TableSpec("recording_sessions", "store", "recording_sessions", "_Docs/recording_sessions.json"),
    TableSpec("tiktok_pending", "store", "tiktok_pending", "_Docs/tiktok_pending.json"),
    TableSpec("tiktok_ignored", "store", "tiktok_ignored", "_Docs/tiktok_ignored.json"),
    TableSpec("batch_render_queue", "batch", "batch_render_queue", "03_Projects/batch_render_queue.json"),
)
TABLE_BY_NAME = {spec.name: spec for spec in TABLES}
# These stores are not backfilled by this migration, but a whole-DB restore
# must protect their newer rows and recover their mirrors just like P2 stores.
RECOVERY_TABLES = TABLES + tuple(
    TableSpec(name, "store", name, f"_Docs/{name}.json")
    for name in ("posting_jobs", "posting_account_audit", "channel_artifacts",
                 "creative_jobs", "hyperframes_render_jobs", "publication_observations", "export_cover_bindings")
)
GADGET_STORES = ("gadget_media_campaigns", "gadget_media_projects")
FILE_STORES = ("task_registry", "manifests") + GADGET_STORES
UNSUPPORTED_STORES = ()
ASSIGNABLE_STORES = frozenset([spec.name for spec in TABLES] + list(FILE_STORES))
DATA_STEPS: Tuple[str, ...] = tuple(spec.name for spec in TABLES) + FILE_STORES
STEP_ORDER: Tuple[str, ...] = ("preflight", "lock", "snapshot") + DATA_STEPS + ("validate", "release")


@dataclasses.dataclass(frozen=True)
class MigrationPaths:
    root: Path

    @classmethod
    def for_root(cls, root: Optional[Path] = None) -> "MigrationPaths":
        return cls(Path(os.path.abspath(root if root is not None else config.BASE_DIR)))

    @property
    def docs(self) -> Path:
        return self.root / "_Docs"

    @property
    def projects(self) -> Path:
        return self.root / "03_Projects"

    @property
    def store_db(self) -> Path:
        return self.docs / "store.db"

    @property
    def batch_db(self) -> Path:
        return self.projects / "batch_render_queue.db"

    def db_for(self, spec: TableSpec) -> Path:
        return self.store_db if spec.db_key == "store" else self.batch_db

    def mirror_for(self, spec: TableSpec) -> Path:
        return self.root / Path(*PurePosixPath(spec.mirror_rel).parts)

    @property
    def task_registry(self) -> Path:
        return self.projects / "task_registry.json"

    @property
    def channels_json(self) -> Path:
        return self.docs / "channels.json"

    @property
    def campaigns_json(self) -> Path:
        return self.docs / "gadget_media_campaigns.json"

    @property
    def gadget_index(self) -> Path:
        return self.docs / "gadget_media" / "project_index.json"

    @property
    def gadget_projects(self) -> Path:
        return self.projects / "GadgetMedia"

    @property
    def migrations(self) -> Path:
        return self.root / "06_Archive" / "Migrations" / MIGRATION_ID

    @property
    def current_pointer(self) -> Path:
        return self.migrations / "current.json"

    def run_dir(self, run_id: str) -> Path:
        return self.migrations / run_id

    def rel(self, path: Path) -> str:
        return Path(os.path.abspath(path)).relative_to(self.root).as_posix()

    def manifest_path(self, project_name: str) -> Path:
        return self.projects / project_name / "project.json"


def _manifest_dirs(paths: MigrationPaths) -> Tuple[List[Path], List[str]]:
    """``03_Projects/<name>/project.json`` of render projects (+ skipped system dirs)."""
    found: List[Path] = []
    skipped: List[str] = []
    if not paths.projects.is_dir():
        return found, skipped
    for manifest in sorted(paths.projects.rglob("project.json")):
        name = manifest.parent.relative_to(paths.projects).as_posix()
        if any(part.startswith(("_", ".")) for part in PurePosixPath(name).parts) or PurePosixPath(name).parts[0] == "GadgetMedia":
            skipped.append(name)
            continue
        found.append(manifest)
    return found, skipped


def manifest_product_id(data: Mapping[str, Any]) -> Optional[str]:
    params = data.get("render_params") if isinstance(data.get("render_params"), Mapping) else {}
    product = data.get("product") if isinstance(data.get("product"), Mapping) else {}
    value = params.get("product_id") or data.get("product_id") or product.get("id")
    return str(value) if value else None


# --------------------------------------------------------------------------- world (read-only)


@dataclasses.dataclass
class FileDoc:
    rel: str
    sha256: Optional[str]
    data: Any
    error: Optional[str] = None
    raw: Optional[bytes] = None


@dataclasses.dataclass
class World:
    paths: MigrationPaths
    tables: Dict[str, Optional[List[Dict[str, Any]]]]
    mirrors: Dict[str, FileDoc]
    mirror_pending: Dict[str, bool]
    mirror_state: Dict[str, Dict[str, int]]
    integrity: Dict[str, str]
    manifests: Dict[str, FileDoc]
    skipped_project_dirs: List[str]
    project_dirs_without_manifest: List[str]
    tasks: FileDoc
    campaigns: FileDoc
    gadget_projects: Dict[str, FileDoc]
    gadget_index_exists: bool
    registry: List[Dict[str, Any]]
    registry_exists: bool
    registry_error: Optional[str]

    def rows(self, name: str) -> List[Dict[str, Any]]:
        return list(self.tables.get(name) or [])


def _read_json_file(path: Path, rel: str) -> FileDoc:
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return FileDoc(rel, None, None, "missing")
    except OSError as exc:
        return FileDoc(rel, None, None, f"unreadable: {exc.__class__.__name__}")
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return FileDoc(rel, sha256_bytes(raw), None, f"invalid_json: {exc.__class__.__name__}", raw)
    return FileDoc(rel, sha256_bytes(raw), data, None, raw)


def load_world(paths: MigrationPaths) -> World:
    """Read every store under ``paths.root`` without writing anything."""
    tables: Dict[str, Optional[List[Dict[str, Any]]]] = {}
    mirror_state: Dict[str, Dict[str, int]] = {}
    integrity: Dict[str, str] = {}
    for key, db_path in (("store", paths.store_db), ("batch", paths.batch_db)):
        with ro_connect(db_path) as conn:
            integrity[key] = _integrity(conn)
            mirror_state[key] = _mirror_state(conn)
            for spec in TABLES:
                if spec.db_key == key:
                    tables[spec.name] = _read_rows(conn, spec.table)

    mirrors: Dict[str, FileDoc] = {}
    pending: Dict[str, bool] = {}
    for spec in TABLES:
        mpath = paths.mirror_for(spec)
        mirrors[spec.name] = _read_json_file(mpath, spec.mirror_rel)
        if mirrors[spec.name].error == "missing":
            pending[spec.name] = False
            continue
        token = _mirror_token(mpath)
        stored = mirror_state.get(spec.db_key, {}).get(str(mpath.resolve()))
        pending[spec.name] = token is None or stored != token

    manifests: Dict[str, FileDoc] = {}
    found, skipped = _manifest_dirs(paths)
    for manifest in found:
        manifests[manifest.parent.relative_to(paths.projects).as_posix()] = _read_json_file(manifest, paths.rel(manifest))
    without: List[str] = []
    if paths.projects.is_dir():
        for child in sorted(paths.projects.iterdir()):
            if child.is_dir() and not child.name.startswith(("_", ".")) and child.name != "GadgetMedia":
                if not (child / "project.json").exists():
                    without.append(child.name)

    gadget: Dict[str, FileDoc] = {}
    if paths.gadget_projects.is_dir():
        for project_file in sorted(paths.gadget_projects.rglob("project.json")):
            if not _is_within(project_file, paths.gadget_projects):
                raise MigrationError("Gadget project path ออกนอก namespace")
            name = project_file.parent.relative_to(paths.gadget_projects).as_posix()
            gadget[name] = _read_json_file(project_file, paths.rel(project_file))

    registry: List[Dict[str, Any]] = []
    registry_error: Optional[str] = None
    store = ChannelStore(paths.channels_json, project_root=paths.root)
    try:
        registry = store.list_channels(include_archived=True)
    except ChannelError as exc:
        registry_error = f"{exc.code}: {exc}"

    return World(
        paths=paths,
        tables=tables,
        mirrors=mirrors,
        mirror_pending=pending,
        mirror_state=mirror_state,
        integrity=integrity,
        manifests=manifests,
        skipped_project_dirs=skipped,
        project_dirs_without_manifest=without,
        tasks=_read_json_file(paths.task_registry, "03_Projects/task_registry.json"),
        campaigns=_read_json_file(paths.campaigns_json, "_Docs/gadget_media_campaigns.json"),
        gadget_projects=gadget,
        gadget_index_exists=paths.gadget_index.exists(),
        registry=registry,
        registry_exists=paths.channels_json.exists(),
        registry_error=registry_error,
    )


# --------------------------------------------------------------------------- reasons (Thai)

REASONS: Dict[str, Tuple[str, str]] = {
    # code: (คำอธิบาย, สิ่งที่ควรทำ)
    "legacy_single_channel_era": ("ข้อมูลเดิมยุคมีช่องเดียว: registry มีแค่ main และไม่มีโพสต์ของบัญชีอื่น", ""),
    "legacy_owner_option": ("เจ้าของระบุ legacy owner เอง (--legacy-owner)", ""),
    "legacy_owner_undecided": (
        "มีหลายช่องใน registry หรือพบโพสต์ของบัญชีอื่น จึงสรุปเจ้าของข้อมูลเดิมไม่ได้",
        "เจ้าของระบุ --legacy-owner หรือ --assign รายแถว",
    ),
    "via_product": ("สืบจาก product_id ของสินค้า", ""),
    "via_export": ("สืบจาก export_id", ""),
    "via_manifest": ("สืบจาก project.json (render_params.product_id)", ""),
    "basename_unique_export": ("ชื่อไฟล์คลิปตรงกับ export เพียงรายการเดียว", ""),
    "owner_assignment": ("เจ้าของกำหนดผ่าน --assign", ""),
    "existing_owner": ("มี channel_id อยู่แล้ว (ไม่แตะ)", ""),
    "product_not_found": (
        "product_id ชี้สินค้าที่ไม่มีอยู่แล้ว (orphan)",
        "ตรวจว่าเป็นขยะเทสหรือไม่: ถ้าใช่ให้เจ้าของสั่งลบผ่านเครื่องมือของ store, ถ้าไม่ใช่ให้ระบุ --assign",
    ),
    "export_not_found": ("export_id ชี้ export ที่ไม่มีแล้ว", "ระบุ --assign หรือแก้ export_id ก่อน"),
    "parent_unknown": ("parent ยังไม่ทราบเจ้าของ", "กำหนดเจ้าของ parent ก่อน แล้วรัน dry-run ใหม่"),
    "no_parent_reference": ("ไม่มี product_id/export_id ให้สืบเจ้าของ", "ระบุ --assign ถ้าต้องการให้เป็นของช่องใด"),
    "no_product_no_project": ("export ไม่มีทั้ง product_id และ project_name", "ระบุ --assign"),
    "manifest_missing": ("export ไม่มี product_id และโฟลเดอร์โปรเจกต์ไม่มี project.json", "ระบุ --assign"),
    "manifest_unreadable": ("project.json อ่านไม่ได้", "ซ่อม project.json หรือระบุ --assign"),
    "manifest_without_product": ("project.json ไม่มี product_id", "ระบุ --assign"),
    "manifest_product_not_found": ("project.json ชี้สินค้าที่ไม่มีแล้ว", "ระบุ --assign"),
    "generic_clip_name": (
        "ชื่อไฟล์กลาง (เช่น clip.mp4) โยงกับ export ไม่ได้ ห้ามเดา",
        "ตรวจโพสต์บน TikTok แล้วระบุ --assign",
    ),
    "no_matching_export": ("ไม่มี export ที่ชื่อไฟล์ตรงกัน", "ระบุ --assign"),
    "ambiguous_basename": ("ชื่อไฟล์ตรงกับ export มากกว่า 1 รายการ", "ระบุ --assign"),
    "source_account_unknown": ("ข้อมูลจาก TikTok sync ไม่ระบุบัญชีต้นทาง", "ระบุ --assign ตามบัญชีที่ sync"),
    "handle_mismatch": ("handle ใน tiktok_url ไม่ตรงกับ handle ของช่องเจ้าของ", "ตรวจบัญชีจริงแล้วระบุ --assign"),
    "parents_disagree": ("export กับ product ชี้คนละช่อง", "แก้ข้อมูล parent ให้ตรงกันก่อน"),
    "unregistered_channel_id": ("channel_id ที่มีอยู่ไม่อยู่ใน registry", "สร้างช่องใน registry หรือแก้ข้อมูล"),
    "existing_owner_differs": ("channel_id ที่มีอยู่ไม่ตรงกับเจ้าของของ parent", "ตรวจและแก้ด้วยมือ (ไม่แตะอัตโนมัติ)"),
    "angle_owner_mismatch": ("angle ในสินค้ามี channel_id ไม่ตรงกับสินค้า", "แก้ angle ให้ตรงกันก่อน"),
    "template_rename_not_enabled": (
        "การเปลี่ยน id template เป็น <channel>:<key> ยังไม่เปิด (ต้องใช้ --rename-templates)",
        "เปิดเมื่อโค้ดคิว/เทมเพลต (P2.2/P5) อ่าน id แบบมี prefix แล้วเท่านั้น",
    ),
    "unrecognized_template_id": ("id template ไม่ใช่ default หรือ week:<วันที่>", "ระบุ --assign"),
    "target_id_exists": ("มี template id ปลายทางอยู่แล้ว", "ตรวจและรวมด้วยมือ"),
    "schema_without_channel_field": (
        "store นี้ยังไม่เก็บ channel_id (dataclass ตัดฟิลด์ทิ้งตอนบันทึก)",
        "รอ P3 เพิ่มฟิลด์ channel_id ใน model แล้วรัน migration ใหม่",
    ),
    "gadget_owner_required": ("Gadget legacy ต้องให้เจ้าของระบุช่องอย่างชัดเจน", "ระบุ --assign ราย campaign/project; ไม่เดาจาก account_role หรือสินค้า"),
}


def reason_text(code: str) -> str:
    return REASONS.get(code, (code, ""))[0]


def reason_action(code: str) -> str:
    return REASONS.get(code, ("", ""))[1]


# --------------------------------------------------------------------------- assignments


def load_assignments(path: Path) -> List[Dict[str, str]]:
    """``{"schema": "omnicut.channel_assign.v1", "assignments": [{store, id, channel_id, note?}]}``."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssignmentError([f"อ่านไฟล์ไม่ได้: {exc.__class__.__name__}"])
    problems: List[str] = []
    if not isinstance(doc, dict) or not isinstance(doc.get("assignments"), list):
        raise AssignmentError(["ต้องเป็น object ที่มี assignments เป็น list"])
    if doc.get("schema") not in (None, "omnicut.channel_assign.v1"):
        problems.append(f"schema ไม่รองรับ: {doc.get('schema')}")
    out: List[Dict[str, str]] = []
    for index, item in enumerate(doc["assignments"]):
        if not isinstance(item, dict):
            problems.append(f"แถว {index}: ต้องเป็น object")
            continue
        store, rid, channel = item.get("store"), item.get("id"), item.get("channel_id")
        if not all(isinstance(v, str) and v.strip() for v in (store, rid, channel)):
            problems.append(f"แถว {index}: ต้องมี store, id, channel_id เป็นข้อความ")
            continue
        out.append({"store": store.strip(), "id": rid.strip(), "channel_id": channel.strip()})
    if problems:
        raise AssignmentError(problems)
    return out


# --------------------------------------------------------------------------- plan


@dataclasses.dataclass
class Decision:
    store: str
    id: str
    status: str  # backfill | already | unknown | conflict | deferred | unsupported
    owner: Optional[str]
    reason: str
    detail: Dict[str, Any] = dataclasses.field(default_factory=dict)
    before_hash: Optional[str] = None
    new_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "store": self.store,
            "id": self.id,
            "status": self.status,
            "owner": self.owner,
            "reason": self.reason,
            "reason_th": reason_text(self.reason),
        }
        action = reason_action(self.reason)
        if action and self.status in ("unknown", "conflict", "deferred", "unsupported"):
            out["suggested_action"] = action
        if self.detail:
            out["detail"] = self.detail
        if self.new_id:
            out["new_id"] = self.new_id
        return out


def _handle_from_url(url: Any) -> Optional[str]:
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        return normalize_handle(url)
    except HandleError:
        match = re.search(r"tiktok\.com/(@[A-Za-z0-9._]+)", url)
        if not match:
            return None
        try:
            return normalize_handle(match.group(1))
        except HandleError:
            return None


def _basename(raw: Any) -> str:
    if not isinstance(raw, str):
        return ""
    return raw.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].strip()


class _Planner:
    def __init__(
        self,
        world: World,
        *,
        assignments: Sequence[Mapping[str, str]],
        rename_templates: bool,
        legacy_owner: Optional[str],
    ):
        self.world = world
        self.rename_templates = bool(rename_templates)
        self.registry = {c["id"]: c for c in world.registry}
        self.decisions: List[Decision] = []
        self.owner: Dict[Tuple[str, str], Optional[str]] = {}
        self.problems: List[str] = []
        self.assign: Dict[Tuple[str, str], str] = {}
        self.assign_used: set = set()
        self._load_assignments(assignments)
        self.handles = {
            cid: (c.get("handle") or "").strip().lower() for cid, c in self.registry.items() if c.get("handle")
        }
        self.post_handles: Dict[str, int] = {}
        for post in world.rows("posts"):
            handle = _handle_from_url(post.get("tiktok_url"))
            if handle:
                self.post_handles[handle] = self.post_handles.get(handle, 0) + 1
        self.legacy_owner, self.legacy_reason = self._legacy_owner(legacy_owner)
        self._exists = {
            "product": {str(p.get("id")) for p in world.rows("products")},
            "export": {str(e.get("id")) for e in world.rows("export_registry")},
        }

    # -- setup ---------------------------------------------------------
    def _load_assignments(self, assignments: Sequence[Mapping[str, str]]) -> None:
        for item in assignments:
            store, rid, channel = item["store"], item["id"], item["channel_id"]
            if store in UNSUPPORTED_STORES:
                self.problems.append(f"{store}/{rid}: store นี้ยังกำหนดเจ้าของไม่ได้ (รอ P3)")
                continue
            if store not in ASSIGNABLE_STORES:
                self.problems.append(f"{store}/{rid}: ไม่รู้จัก store '{store}'")
                continue
            channel_doc = self.registry.get(channel)
            if channel_doc is None:
                self.problems.append(f"{store}/{rid}: ไม่มีช่อง '{channel}' ใน registry")
                continue
            if channel_doc.get("status") == "archived":
                self.problems.append(f"{store}/{rid}: ช่อง '{channel}' ถูก archive แล้ว")
                continue
            key = (store, rid)
            if key in self.assign and self.assign[key] != channel:
                self.problems.append(f"{store}/{rid}: ระบุเจ้าของซ้ำไม่ตรงกัน")
                continue
            self.assign[key] = channel

    def _legacy_owner(self, explicit: Optional[str]) -> Tuple[Optional[str], str]:
        main = config.DEFAULT_CHANNEL_ID
        if explicit:
            doc = self.registry.get(explicit)
            if doc is None or doc.get("status") == "archived":
                self.problems.append(f"--legacy-owner '{explicit}' ไม่มีใน registry หรือถูก archive")
                return None, "legacy_owner_undecided"
            return explicit, "legacy_owner_option"
        others = [cid for cid in self.registry if cid != main]
        main_handle = self.handles.get(main)
        foreign = [h for h in self.post_handles if h != main_handle]
        if main in self.registry and not others and not foreign:
            return main, "legacy_single_channel_era"
        return None, "legacy_owner_undecided"

    # -- core ----------------------------------------------------------
    def _finalize(
        self,
        store: str,
        rid: str,
        row: Mapping[str, Any],
        owner: Optional[str],
        reason: str,
        detail: Optional[Dict[str, Any]] = None,
        *,
        conflict: Optional[str] = None,
        before_hash: Optional[str] = None,
        unsupported: bool = False,
    ) -> Decision:
        detail = dict(detail or {})
        key = (store, rid)
        existing = row.get(OWNER_KEY) if isinstance(row, Mapping) else None
        bh = before_hash if before_hash is not None else row_hash(row)
        if existing is not None:
            if key in self.assign:
                self.assign_used.add(key)
                if self.assign[key] != existing:
                    self.problems.append(f"{store}/{rid}: มี channel_id={existing} อยู่แล้ว ไม่เปลี่ยนเป็น {self.assign[key]}")
            if existing not in self.registry:
                decision = Decision(store, rid, "conflict", existing, "unregistered_channel_id", detail, bh)
            elif owner is not None and owner != existing:
                detail["evidence_owner"] = owner
                decision = Decision(store, rid, "conflict", existing, "existing_owner_differs", detail, bh)
            else:
                decision = Decision(store, rid, "already", existing, "existing_owner", detail, bh)
            self.owner[key] = existing if decision.status == "already" else None
            self.decisions.append(decision)
            return decision
        if unsupported:
            if key in self.assign:
                self.assign_used.add(key)
            decision = Decision(store, rid, "unsupported", None, "schema_without_channel_field", detail, bh)
        elif key in self.assign:
            self.assign_used.add(key)
            chosen = self.assign[key]
            if owner is not None and owner != chosen and conflict is None:
                self.problems.append(
                    f"{store}/{rid}: --assign={chosen} ขัดกับหลักฐาน ({reason_text(reason)} -> {owner})"
                )
            parent = detail.get("parent_owner")
            if parent is not None and parent != chosen:
                self.problems.append(f"{store}/{rid}: --assign={chosen} ไม่ตรงกับเจ้าของ parent ({parent})")
            detail["evidence_reason"] = reason
            decision = Decision(store, rid, "backfill", chosen, "owner_assignment", detail, bh)
        elif conflict is not None:
            if owner is not None:
                detail["evidence_owner"] = owner
            decision = Decision(store, rid, "conflict", None, conflict, detail, bh)
        elif owner is None:
            decision = Decision(store, rid, "unknown", None, reason, detail, bh)
        else:
            decision = Decision(store, rid, "backfill", owner, reason, detail, bh)
        self.owner[key] = decision.owner if decision.status in ("backfill", "already") else None
        self.decisions.append(decision)
        return decision

    def _owner_of(self, store: str, rid: Any) -> Optional[str]:
        if rid is None:
            return None
        return self.owner.get((store, str(rid)))

    def _from_parents(self, refs: Sequence[Tuple[str, Any]]) -> Tuple[Optional[str], str, Dict[str, Any], Optional[str]]:
        """refs: [("product", id) | ("export", id)].  Returns owner, reason, detail, conflict."""
        stores = {"product": "products", "export": "export_registry"}
        exists = self._exists
        found: List[Tuple[str, str, str]] = []
        missing: List[Tuple[str, str]] = []
        unknown_parent: List[Tuple[str, str]] = []
        for kind, value in refs:
            if not value:
                continue
            value = str(value)
            if value not in exists[kind]:
                missing.append((kind, value))
                continue
            owner = self._owner_of(stores[kind], value)
            if owner is None:
                unknown_parent.append((kind, value))
            else:
                found.append((kind, value, owner))
        detail: Dict[str, Any] = {}
        for kind, value, owner in found:
            detail[f"{kind}_id"] = value
        owners = {o for _, _, o in found}
        if len(owners) > 1:
            detail["parent_owners"] = {f"{k}:{v}": o for k, v, o in found}
            return None, "parents_disagree", detail, "parents_disagree"
        if owners:
            owner = owners.pop()
            detail["parent_owner"] = owner
            reason = "via_export" if any(k == "export" for k, _, _ in found) else "via_product"
            return owner, reason, detail, None
        if unknown_parent:
            detail["unknown_parents"] = [f"{k}:{v}" for k, v in unknown_parent]
            return None, "parent_unknown", detail, None
        if missing:
            detail["missing_parents"] = [f"{k}:{v}" for k, v in missing]
            kind = missing[0][0]
            return None, ("export_not_found" if kind == "export" else "product_not_found"), detail, None
        return None, "no_parent_reference", detail, None

    # -- stores ---------------------------------------------------------
    def plan_products(self) -> None:
        for product in self.world.rows("products"):
            rid = str(product.get("id"))
            owner, reason = self.legacy_owner, self.legacy_reason
            conflict = None
            existing = product.get(OWNER_KEY)
            target = existing if existing is not None else (self.assign.get(("products", rid)) or owner)
            bad = [
                str(a.get("angle_id") or i)
                for i, a in enumerate(product.get("angles") or [])
                if isinstance(a, Mapping) and a.get(OWNER_KEY) is not None and a.get(OWNER_KEY) != target
            ]
            detail = {"angle_mismatch": bad} if bad else {}
            if bad and existing is None:
                conflict = "angle_owner_mismatch"
            self._finalize("products", rid, product, owner, reason, detail, conflict=conflict)

    def plan_exports(self) -> None:
        products = {str(p.get("id")) for p in self.world.rows("products")}
        for export in self.world.rows("export_registry"):
            rid = str(export.get("id"))
            pid = export.get("product_id")
            if pid:
                owner, reason, detail, conflict = self._from_parents([("product", pid)])
            else:
                project = export.get("project_name")
                detail = {"project_name": project} if project else {}
                owner, reason, conflict = None, "no_product_no_project", None
                if project:
                    manifest = self.world.manifests.get(str(project))
                    if manifest is None:
                        reason = "manifest_missing"
                    elif manifest.data is None or not isinstance(manifest.data, Mapping):
                        reason = "manifest_unreadable"
                    else:
                        mpid = manifest_product_id(manifest.data)
                        if not mpid:
                            reason = "manifest_without_product"
                        elif mpid not in products:
                            reason = "manifest_product_not_found"
                            detail["manifest_product_id"] = mpid
                        else:
                            owner = self._owner_of("products", mpid)
                            detail["manifest_product_id"] = mpid
                            detail["parent_owner"] = owner
                            reason = "via_manifest" if owner else "parent_unknown"
            self._finalize("export_registry", rid, export, owner, reason, detail, conflict=conflict)

    def plan_posts(self) -> None:
        exports = self.world.rows("export_registry")
        by_name: Dict[str, List[Dict[str, Any]]] = {}
        for export in exports:
            name = _basename(export.get("path")).casefold()
            if name:
                by_name.setdefault(name, []).append(export)
        for post in self.world.rows("posts"):
            rid = str(post.get("id"))
            handle = _handle_from_url(post.get("tiktok_url"))
            if post.get("export_id") or post.get("product_id"):
                owner, reason, detail, conflict = self._from_parents(
                    [("export", post.get("export_id")), ("product", post.get("product_id"))]
                )
            else:
                conflict = None
                name = _basename(post.get("clip_file"))
                detail = {"clip_basename": name} if name else {}
                stem = name.rsplit(".", 1)[0].strip().casefold()
                matches = by_name.get(name.casefold(), []) if name else []
                if not name or stem in GENERIC_CLIP_STEMS:
                    owner, reason = None, "generic_clip_name"
                elif not matches:
                    owner, reason = None, "no_matching_export"
                elif len(matches) > 1:
                    owner, reason = None, "ambiguous_basename"
                    detail["candidate_exports"] = sorted(str(m.get("id")) for m in matches)
                else:
                    export_id = str(matches[0].get("id"))
                    detail["matched_export_id"] = export_id
                    owner = self._owner_of("export_registry", export_id)
                    detail["parent_owner"] = owner
                    reason = "basename_unique_export" if owner else "parent_unknown"
            if handle:
                detail["tiktok_handle"] = handle
                matching = sorted(cid for cid, h in self.handles.items() if h == handle)
                if owner is not None and self.handles.get(owner) and self.handles[owner] != handle:
                    conflict = conflict or "handle_mismatch"
                if owner is None and matching:
                    detail["handle_matches_channel"] = matching
            self._finalize("posts", rid, post, owner, reason, detail, conflict=conflict)

    def plan_queue(self) -> None:
        for item in self.world.rows("schedule_queue"):
            rid = str(item.get("id"))
            owner, reason, detail, conflict = self._from_parents(
                [("export", item.get("export_id")), ("product", item.get("product_id"))]
            )
            self._finalize("schedule_queue", rid, item, owner, reason, detail, conflict=conflict)

    def plan_templates(self) -> None:
        rows = self.world.rows("schedule_templates")
        ids = {str(r.get("id")) for r in rows}
        for row in rows:
            rid = str(row.get("id"))
            if row.get(OWNER_KEY) is not None:
                self._finalize("schedule_templates", rid, row, None, "existing_owner")
                continue
            legacy = rid == "default" or rid.startswith("week:")
            if not legacy:
                self._finalize("schedule_templates", rid, row, None, "unrecognized_template_id")
                continue
            if not self.rename_templates:
                if ("schedule_templates", rid) in self.assign:
                    self.assign_used.add(("schedule_templates", rid))
                    self.problems.append(f"schedule_templates/{rid}: ต้องใช้ --rename-templates ร่วมกับ --assign")
                decision = Decision(
                    "schedule_templates", rid, "deferred", self.legacy_owner, "template_rename_not_enabled",
                    {}, row_hash(row),
                )
                self.decisions.append(decision)
                continue
            decision = self._finalize(
                "schedule_templates", rid, row, self.legacy_owner, self.legacy_reason
            )
            if decision.status == "backfill":
                new_id = f"{decision.owner}:{rid}"
                if new_id in ids:
                    decision.status = "conflict"
                    decision.reason = "target_id_exists"
                    decision.detail["target_id"] = new_id
                    decision.owner = None
                else:
                    decision.new_id = new_id

    def plan_by_product(self, store: str) -> None:
        for row in self.world.rows(store):
            rid = str(row.get("id"))
            owner, reason, detail, conflict = self._from_parents([("product", row.get("product_id"))])
            self._finalize(store, rid, row, owner, reason, detail, conflict=conflict)

    def plan_unowned(self, store: str) -> None:
        for row in self.world.rows(store):
            self._finalize(store, str(row.get("id")), row, None, "source_account_unknown")

    def plan_tasks(self) -> None:
        tasks = self.world.tasks.data
        if not isinstance(tasks, Mapping):
            return
        for tid, task in tasks.items():
            if not isinstance(task, Mapping):
                continue
            payload = task.get("payload") if isinstance(task.get("payload"), Mapping) else {}
            owner, reason, detail, conflict = self._from_parents([("product", payload.get("product_id"))])
            self._finalize("task_registry", str(tid), task, owner, reason, detail, conflict=conflict)

    def plan_manifests(self) -> None:
        for name, doc in sorted(self.world.manifests.items()):
            if not isinstance(doc.data, Mapping):
                self._finalize(
                    "manifests", name, {}, None, "manifest_unreadable", {"path": doc.rel}, before_hash=doc.sha256
                )
                continue
            refs = [("product", manifest_product_id(doc.data))]
            owner, reason, detail, conflict = self._from_parents(refs)
            export_id = doc.data.get("export_id")
            export_owner = self._owner_of("export_registry", export_id) if export_id else None
            if owner and export_owner and export_owner != owner:
                conflict = "parents_disagree"
                detail["export_owner"] = export_owner
            detail["path"] = doc.rel
            self._finalize("manifests", name, doc.data, owner, reason, detail, conflict=conflict, before_hash=doc.sha256)

    def plan_gadget(self) -> None:
        campaigns = self.world.campaigns.data
        if isinstance(campaigns, list):
            for campaign in campaigns:
                if isinstance(campaign, Mapping):
                    detail = {"account_role": campaign.get("account_role"), "slots": len(campaign.get("slots") or [])}
                    self._finalize(
                        "gadget_media_campaigns", str(campaign.get("campaign_id")), campaign, None,
                        "gadget_owner_required", detail,
                    )
        for pid, doc in sorted(self.world.gadget_projects.items()):
            data = doc.data if isinstance(doc.data, Mapping) else {}
            self._finalize(
                "gadget_media_projects", pid, data, None, "gadget_owner_required",
                {"path": doc.rel}, before_hash=doc.sha256,
            )
        assigned = [d for d in self.decisions if d.store in GADGET_STORES and d.status == "backfill"]
        for decision in assigned:
            try:
                decision.detail["files"] = _plan_gadget_files(self.world, decision)
            except (ValueError, TypeError, KeyError, OSError) as exc:
                self.problems.append(f"{decision.store}/{decision.id}: Gadget schema/layout ไม่รองรับ: {exc}")
        self.problems.extend(_gadget_ownership_problems(self.world, self.owner, assigned))

    def run(self) -> None:
        self.plan_products()
        self.plan_exports()
        self.plan_posts()
        self.plan_queue()
        self.plan_templates()
        for store in ("shot_lists", "recording_sessions", "batch_render_queue"):
            self.plan_by_product(store)
        for store in ("tiktok_pending", "tiktok_ignored"):
            self.plan_unowned(store)
        self.plan_tasks()
        self.plan_manifests()
        self.plan_gadget()
        for key in self.assign:
            if key not in self.assign_used:
                self.problems.append(f"{key[0]}/{key[1]}: ไม่พบแถวนี้ใน store")


def _gadget_selected(data: Any, selector: Optional[Mapping[str, str]]) -> Dict[str, Any]:
    if selector is None:
        if not isinstance(data, dict):
            raise ValueError("owner mirror ต้องเป็น object")
        return data
    records = data if selector["kind"] == "campaign" else data.get("projects") if isinstance(data, dict) else None
    if not isinstance(records, list):
        raise ValueError("owner mirror ต้องมีรายการ records")
    key = "campaign_id" if selector["kind"] == "campaign" else "project_id"
    matching = [row for row in records if isinstance(row, dict) and str(row.get(key)) == selector["id"]]
    if len(matching) != 1:
        raise ValueError(f"{key} ต้องมีรายการเดียวใน owner mirror")
    return matching[0]


def _plan_gadget_files(world: World, decision: Decision) -> List[Dict[str, Any]]:
    """Validate P3 models, preserving raw fields instead of calling writers."""
    paths = world.paths
    if decision.store == "gadget_media_campaigns":
        from scripts.gadget_media_campaign import GadgetMediaCampaign
        selector = {"kind": "campaign", "id": decision.id}
        row = _gadget_selected(world.campaigns.data, selector)
        GadgetMediaCampaign.from_dict({**row, OWNER_KEY: decision.owner}).validate()
        return [{"rel": world.campaigns.rel, "before_hash": world.campaigns.sha256, "selector": selector}]
    from scripts.gadget_media_project import ProductVideoProject
    from scripts.gadget_media_paths import validate_project_id
    doc = world.gadget_projects[decision.id]
    row = doc.data
    project_id = validate_project_id(row.get("project_id"))
    if sum(1 for item in world.gadget_projects.values() if isinstance(item.data, Mapping) and item.data.get("project_id") == project_id) != 1:
        raise ValueError("duplicate Gadget project_id ในคนละ path")
    if project_id != decision.id or paths.gadget_projects / project_id / "project.json" != paths.root / doc.rel:
        raise ValueError("nested/noncanonical Gadget layout เปิดผ่าน scoped repository ไม่ได้")
    ProductVideoProject.from_dict({**row, OWNER_KEY: decision.owner}).validate()
    for snapshot in (row.get("channel_identity_snapshot"), (row.get("edit") or {}).get("channel_identity_snapshot"),
                     (row.get("presentation") or {}).get("channel_identity_snapshot"),
                     *[artifact.get("channel_identity_snapshot") for artifact in row.get("artifacts") or []]):
        if isinstance(snapshot, Mapping) and snapshot.get(OWNER_KEY) not in (None, decision.owner):
            raise ValueError("frozen channel identity ไม่ตรงเจ้าของที่ assign")
    files = [{"rel": doc.rel, "before_hash": doc.sha256, "selector": None}]
    for path, selector in ((paths.root / doc.rel.replace("/project.json", "/product.json"), None),
                           (paths.gadget_index, {"kind": "project", "id": project_id})):
        if not path.exists():
            continue  # Optional materialized mirrors are never recreated.
        if not _is_within(path, paths.root):
            raise ValueError("Gadget mirror path ออกนอก root")
        mirror = _read_json_file(path, paths.rel(path))
        record = _gadget_selected(mirror.data, selector)
        if record.get(OWNER_KEY) not in (None, decision.owner) or (selector is None and record.get("project_id") != project_id):
            raise ValueError("Gadget materialized owner mirror ไม่ตรง project")
        files.append({"rel": mirror.rel, "before_hash": mirror.sha256, "selector": selector})
    return files


def _gadget_ownership_problems(world: World, owners: Mapping[Tuple[str, str], Optional[str]],
                               assigned: Sequence[Decision]) -> List[str]:
    problems: List[str] = []
    campaigns = {str(row.get("campaign_id")): row for row in world.campaigns.data or [] if isinstance(row, Mapping)}
    projects = {str(doc.data.get("project_id")): (name, doc.data) for name, doc in world.gadget_projects.items() if isinstance(doc.data, Mapping)}
    for decision in assigned:
        owner = decision.owner
        if decision.store == "gadget_media_campaigns":
            for slot in campaigns.get(decision.id, {}).get("slots") or []:
                target = slot.get("product_project_id") if isinstance(slot, Mapping) else None
                if target and (target not in projects or owners.get(("gadget_media_projects", projects[target][0])) != owner):
                    problems.append(f"campaign/{decision.id}: linked project {target} ไม่มีเจ้าของช่องเดียวกัน")
            continue
        row = world.gadget_projects[decision.id].data or {}
        if not isinstance(row, Mapping):
            continue
        for link in row.get("campaign_links") or []:
            if not isinstance(link, Mapping):
                problems.append(f"project/{decision.id}: campaign link ไม่ใช่ object")
                continue
            campaign = campaigns.get(str(link.get("campaign_id")))
            slot = next((s for s in (campaign or {}).get("slots") or [] if s.get("slot_id") == link.get("slot_id")), None)
            if (campaign is None or slot is None or owners.get(("gadget_media_campaigns", str(link.get("campaign_id")))) != owner
                    or slot.get("product_project_id") not in (None, "", row.get("project_id"))):
                problems.append(f"project/{decision.id}: campaign/slot parent ไม่ตรงเจ้าของหรือ linked project")
        with ro_connect(world.paths.store_db) as conn:
            artifacts = _read_rows(conn, "channel_artifacts") or []
        for artifact in row.get("artifacts") or []:
            snapshot = artifact.get("channel_identity_snapshot")
            if isinstance(snapshot, Mapping) and snapshot.get(OWNER_KEY) not in (None, owner):
                problems.append(f"project/{decision.id}: artifact frozen identity ต่างช่อง")
            value = artifact.get("path")
            if not value:
                continue
            path = Path(str(value))
            path = (path if path.is_absolute() else world.paths.root / path).resolve()
            if not _is_within(path, world.paths.root):
                problems.append(f"project/{decision.id}: artifact path ออกนอก root")
                continue
            relative = path.relative_to(world.paths.root).as_posix()
            key = relative.casefold()
            claimed = {a.get(OWNER_KEY) for a in artifacts if str(a.get("path_key") or a.get("path") or "").replace("\\", "/").casefold() == key}
            # Media serving consults this index before the enclosing project.
            # Stamping the project cannot override a contradictory indexed owner.
            if relative.startswith(("03_Projects/", "04_Exports/", "05_Covers_Thumbnails/")) and claimed:
                if claimed != {owner}:
                    problems.append(f"project/{decision.id}: indexed artifact ต่างเจ้าของ ({relative})")
                if relative.startswith("03_Projects/"):
                    continue
            if relative.startswith("03_Projects/"):
                # Unindexed companions inherit the nearest manifest, just as
                # require_media_owner does. Do not require a new index entry.
                parent_owner = None
                for parent in (path.parent, *path.parents):
                    if parent == world.paths.projects:
                        break
                    if (parent / "project.json").is_file():
                        name = parent.relative_to(world.paths.projects).as_posix()
                        gadget_name = name.removeprefix("GadgetMedia/")
                        doc = world.gadget_projects.get(gadget_name) if name.startswith("GadgetMedia/") else world.manifests.get(name)
                        store = "gadget_media_projects" if name.startswith("GadgetMedia/") else "manifests"
                        if doc and isinstance(doc.data, Mapping):
                            parent_owner = owners.get((store, gadget_name if store == "gadget_media_projects" else name), doc.data.get(OWNER_KEY))
                        break
                if parent_owner != owner:
                    problems.append(f"project/{decision.id}: artifact project ไม่มีเจ้าของช่องเดียวกัน ({relative})")
                continue
            if owner == config.DEFAULT_CHANNEL_ID or not relative.startswith(("04_Exports/", "05_Covers_Thumbnails/")):
                continue
            for export in world.rows("export_registry"):
                for field in ("rel_path", "path", "video_path", "cover_path", "cover_9x16_path", "cover_3x4_path"):
                    raw = export.get(field)
                    if raw and (Path(raw) if Path(raw).is_absolute() else world.paths.root / raw).resolve() == path:
                        claimed.add(owners.get(("export_registry", str(export.get("id"))), export.get(OWNER_KEY)))
            if claimed != {owner}:
                problems.append(f"project/{decision.id}: secondary artifact ไม่มี verified owner เดียวกัน ({relative})")
    return problems


def _gadget_group_files(actions: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for action in actions:
        for spec in action.get("files") or []:
            rel = spec["rel"]
            path = PurePosixPath(rel)
            allowed = rel in ("_Docs/gadget_media_campaigns.json", "_Docs/gadget_media/project_index.json") or (
                rel.startswith("03_Projects/GadgetMedia/") and path.name in ("project.json", "product.json"))
            if path.is_absolute() or ".." in path.parts or "\\" in rel or not allowed:
                raise MigrationError("Gadget migration file path ไม่อยู่ใน namespace")
            entry = grouped.setdefault(rel, {"before_hash": spec["before_hash"], "changes": []})
            if entry["before_hash"] != spec["before_hash"]:
                raise MigrationError("Gadget mirror planned hashes ไม่ตรงกัน")
            entry["changes"].append({"selector": spec["selector"], "owner": action["owner"], "id": action["id"]})
    return grouped


def _action_of(decision: Decision) -> Dict[str, Any]:
    action = {
        "store": decision.store,
        "id": decision.id,
        "op": "rename_template" if decision.new_id else "set_owner",
        "owner": decision.owner,
        "before_hash": decision.before_hash,
    }
    if decision.new_id:
        action["new_id"] = decision.new_id
    if decision.store in GADGET_STORES:
        action["files"] = decision.detail.get("files", [])
    return action


def build_plan(
    world: World,
    *,
    assignments: Sequence[Mapping[str, str]] = (),
    rename_templates: bool = False,
    legacy_owner: Optional[str] = None,
) -> Dict[str, Any]:
    """Pure function of the world + owner decisions.  Raises AssignmentError."""
    planner = _Planner(world, assignments=assignments, rename_templates=rename_templates, legacy_owner=legacy_owner)
    planner.run()
    if planner.problems:
        raise AssignmentError(planner.problems)

    stores: Dict[str, Dict[str, Any]] = {}
    order = list(DATA_STEPS) + list(UNSUPPORTED_STORES)
    for name in order:
        stores[name] = {"total": 0, "already": 0, "backfill": {}, "unknown": 0, "conflict": 0, "deferred": 0, "unsupported": 0}
    for d in planner.decisions:
        bucket = stores.setdefault(d.store, {"total": 0, "already": 0, "backfill": {}, "unknown": 0, "conflict": 0, "deferred": 0, "unsupported": 0})
        bucket["total"] += 1
        if d.status == "backfill":
            bucket["backfill"][d.owner] = bucket["backfill"].get(d.owner, 0) + 1
        else:
            bucket[d.status] += 1
        if d.status in ("unknown", "conflict"):
            reasons = bucket.setdefault("reasons", {})
            reasons[d.reason] = reasons.get(d.reason, 0) + 1
    for name, spec in TABLE_BY_NAME.items():
        stores[name]["table_present"] = world.tables.get(name) is not None

    actions = [_action_of(d) for d in planner.decisions if d.status == "backfill"]
    options = {"rename_templates": bool(rename_templates), "legacy_owner": legacy_owner}
    plan_hash = row_hash({"migration": MIGRATION_ID, "actions": actions, "options": options})
    return {
        "schema": PLAN_SCHEMA,
        "migration": MIGRATION_ID,
        "plan_hash": plan_hash,
        "options": options,
        "assignments": [dict(a) for a in assignments],
        "registry": {
            "exists": world.registry_exists,
            "error": world.registry_error,
            "channels": [
                {"id": c.get("id"), "status": c.get("status"), "handle": c.get("handle")} for c in world.registry
            ],
        },
        "evidence": {
            "post_handles": dict(sorted(planner.post_handles.items())),
            "legacy_owner": planner.legacy_owner,
            "legacy_owner_reason": planner.legacy_reason,
            "legacy_owner_reason_th": reason_text(planner.legacy_reason),
        },
        "stores": stores,
        "decisions": [d.to_dict() for d in planner.decisions if d.status != "already"],
        "already_owned": sum(1 for d in planner.decisions if d.status == "already"),
        "actions": actions,
    }


# --------------------------------------------------------------------------- preflight


def _mirror_matches(world: World, name: str) -> Optional[bool]:
    doc = world.mirrors.get(name)
    rows = world.tables.get(name)
    if doc is None or doc.error == "missing" or rows is None:
        return None
    if not isinstance(doc.data, list):
        return False
    try:
        mirror = {str(r["id"]): canon(r) for r in doc.data}
    except (KeyError, TypeError):
        return False
    return len(mirror) == len(doc.data) and mirror == {str(r["id"]): canon(r) for r in rows}


def preflight(
    world: World,
    plan: Mapping[str, Any],
    *,
    server_probe: Optional[Callable[[], bool]] = None,
    current_run: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    paths = world.paths
    checks: List[Dict[str, Any]] = []

    def add(name: str, level: str, ok: bool, message: str, **extra: Any) -> None:
        checks.append({"name": name, "level": level, "ok": bool(ok), "message": message, **extra})

    add("root_layout", "blocker", paths.docs.is_dir(), f"โฟลเดอร์ _Docs ใต้ root ({paths.root})")
    for key, label in (("store", "_Docs/store.db"), ("batch", "03_Projects/batch_render_queue.db")):
        status = world.integrity.get(key, "missing")
        if status == "missing":
            add(f"integrity_{key}", "info", True, f"{label} ไม่มีอยู่ (ข้าม)")
        else:
            add(f"integrity_{key}", "blocker", status == "ok", f"{label} integrity_check = {status}")

    for spec in TABLES:
        match = _mirror_matches(world, spec.name)
        pending = world.mirror_pending.get(spec.name, False)
        if match is None:
            add(f"mirror_{spec.name}", "info", True, f"{spec.mirror_rel}: ไม่มีไฟล์ mirror หรือไม่มีตาราง")
        elif match:
            note = " (ไฟล์จะถูก import ซ้ำแต่เนื้อหาเท่ากัน)" if pending else ""
            add(f"mirror_{spec.name}", "info", True, f"{spec.mirror_rel} ตรงกับ DB ทุกแถว{note}")
        elif pending:
            add(
                f"mirror_{spec.name}", "blocker", False,
                f"{spec.mirror_rel} ไม่ตรงกับ DB และกำลังจะถูก auto-import ทับ DB — ต้องแก้ให้ตรงก่อน",
            )
        else:
            add(f"mirror_{spec.name}", "warning", False, f"{spec.mirror_rel} เก่ากว่า DB (DB เป็นตัวจริง; จะเขียนใหม่เมื่อ store นี้ถูกแก้)")

    foreign = 0
    for rows in world.mirror_state.values():
        for source in rows:
            if not _is_within(Path(source), paths.root):
                foreign += 1
    add("mirror_state_foreign_rows", "info", True, f"_json_mirror_state มีแถว path นอก root {foreign} แถว (เฉื่อย ไม่แตะ)", count=foreign)

    channels = {c["id"] for c in world.registry}
    add(
        "registry", "blocker", world.registry_error is None and config.DEFAULT_CHANNEL_ID in channels,
        f"registry อ่านได้และมีช่อง {config.DEFAULT_CHANNEL_ID}" + (f" (ผิดพลาด: {world.registry_error})" if world.registry_error else ""),
    )
    evidence = plan.get("evidence", {})
    add(
        "legacy_owner", "warning", evidence.get("legacy_owner") is not None,
        f"เจ้าของข้อมูลเดิม: {evidence.get('legacy_owner')} ({evidence.get('legacy_owner_reason_th')})",
    )

    lock = maintenance_lock.read_lock(paths.root)
    if lock is None:
        add("maintenance_lock", "blocker", True, "ไม่มี maintenance lock ค้าง")
    else:
        add(
            "maintenance_lock", "blocker", False,
            f"มี maintenance lock อยู่แล้ว (owner={lock.get('owner')}, run_id={lock.get('run_id')}, stale={lock.get('stale')})",
        )
    if current_run and current_run.get("status") == "corrupt":
        add("run_in_progress", "blocker", False, "ไฟล์สถานะ migration (current.json) เสีย ต้องตรวจด้วยมือ")
    elif current_run and current_run.get("status") in ("in_progress", "needs_attention"):
        add(
            "run_in_progress", "blocker", False,
            f"migration รอบ {current_run.get('run_id')} ยังค้าง ({current_run.get('status')}) ใช้ --resume หรือ --rollback",
        )
    else:
        add("run_in_progress", "blocker", True, "ไม่มี migration ค้าง")

    tasks = world.tasks.data if isinstance(world.tasks.data, Mapping) else {}
    active_tasks = sorted(
        str(tid) for tid, t in tasks.items()
        if isinstance(t, Mapping) and str(t.get("status") or "").lower() not in _TERMINAL_TASK
    )
    add("active_tasks", "blocker", not active_tasks, f"งานเบื้องหลังที่ยังไม่จบ {len(active_tasks)} งาน", ids=active_tasks)
    active_batches = sorted(
        str(b.get("id")) for b in world.rows("batch_render_queue")
        if str(b.get("status") or "").lower() in _ACTIVE_BATCH and not b.get("cancelled")
    )
    add("active_batches", "blocker", not active_batches, f"batch render ที่ยังไม่จบ {len(active_batches)} รายการ", ids=active_batches)
    live_recording = sorted(
        str(r.get("id")) for r in world.rows("recording_sessions")
        if str(r.get("status") or "").lower() in ("active", "recording", "uploading", "open")
    )
    add("recording_sessions", "warning", not live_recording, f"recording session ที่ยังเปิด {len(live_recording)}", ids=live_recording)
    preparing = sorted(
        str(q.get("id")) for q in world.rows("schedule_queue")
        if str(q.get("status") or "").lower() in ("ready_for_extension", "preparing", "posting")
    )
    add(
        "posting_in_flight", "warning", not preparing,
        f"คิวที่เตรียมให้ extension โพสต์ {len(preparing)} รายการ — ปิด extension ก่อน apply", ids=preparing,
    )

    estimate = _snapshot_estimate(paths, world)
    try:
        free = shutil.disk_usage(paths.root).free
    except OSError:
        free = 0
    need = estimate * 2 + _SNAPSHOT_SAFETY_BYTES
    add("disk_space", "blocker", free >= need, f"พื้นที่ว่าง {free // (1024*1024)} MB ต้องการ ≥ {need // (1024*1024)} MB", free_bytes=free, need_bytes=need)

    if server_probe is not None:
        try:
            listening = bool(server_probe())
        except Exception:
            listening = False
        add("api_server_stopped", "blocker", not listening, "API server ต้องหยุดก่อน apply" if listening else "ไม่พบ API server ทำงานอยู่")

    conflicts = sum(1 for d in plan.get("decisions", []) if d["status"] == "conflict")
    unknown = sum(1 for d in plan.get("decisions", []) if d["status"] == "unknown")
    add("conflicts", "warning", conflicts == 0, f"แถวที่หลักฐานขัดกัน {conflicts} (จะไม่ถูกแตะ)")
    add("unknown", "warning", unknown == 0, f"แถวที่ไม่ทราบเจ้าของ {unknown} (จะไม่ถูกแตะ จนกว่าจะ --assign)")
    blockers = [c for c in checks if c["level"] == "blocker" and not c["ok"]]
    return {"checks": checks, "blockers": len(blockers), "snapshot_estimate_bytes": estimate}


def _snapshot_files(paths: MigrationPaths) -> Tuple[List[Path], List[Path]]:
    """(sqlite files, plain files) that a pre-apply snapshot must contain."""
    sqlite_files = [p for p in (paths.store_db, paths.batch_db) if p.is_file()]
    plain: List[Path] = []
    for spec in RECOVERY_TABLES:
        mirror = paths.mirror_for(spec)
        if mirror.is_file():
            plain.append(mirror)
    for extra in (paths.channels_json, paths.task_registry, paths.campaigns_json, paths.gadget_index):
        if extra.is_file():
            plain.append(extra)
    for extra_name in ("posting_jobs.json", "posting_account_audit.json", "channel_artifacts.json"):
        extra = paths.docs / extra_name
        if extra.is_file():
            plain.append(extra)
    for spec in RECOVERY_TABLES:
        intent = paths.mirror_for(spec).with_name(paths.mirror_for(spec).name + ".publish-pending")
        if intent.is_file():
            plain.append(intent)
    if paths.gadget_projects.is_dir():
        plain.extend(sorted(p for p in paths.gadget_projects.rglob("*.json") if p.is_file()))
    found, _ = _manifest_dirs(paths)
    plain.extend(found)
    seen: Dict[str, Path] = {}
    for p in plain:
        seen.setdefault(os.path.normcase(str(p)), p)
    return sqlite_files, list(seen.values())


def _snapshot_estimate(paths: MigrationPaths, world: Optional[World] = None) -> int:
    sqlite_files, plain = _snapshot_files(paths)
    total = 0
    for p in sqlite_files:
        total += p.stat().st_size
        wal = Path(str(p) + "-wal")
        if wal.exists():
            total += wal.stat().st_size
    for p in plain:
        total += p.stat().st_size
    return total


# --------------------------------------------------------------------------- snapshot / restore


def _table_digest(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    ids = sorted(str(r.get("id")) for r in rows)
    by_id = sorted((str(r.get("id")), canon(r)) for r in rows)
    return {"count": len(rows), "ids_sha256": row_hash(ids), "rows_sha256": row_hash(by_id)}


def create_snapshot(paths: MigrationPaths, dest: Path, *, allowed_roots: Sequence[Path]) -> Dict[str, Any]:
    """Pre-apply snapshot of every store under ``paths.root`` into ``dest``.

    SQLite databases go through the online-backup API (WAL-consistent, never a
    raw file copy); JSON mirrors, registry, task registry, GadgetMedia files and
    project manifests are byte copies.  ``dest/manifest.json`` lists sha256 per
    file plus per-table count/id/row digests for :func:`verify_restore`.
    """
    dest = Path(dest)
    _mkdir(dest, allowed_roots=allowed_roots)
    if any(dest.iterdir()):
        raise MigrationError(f"โฟลเดอร์ snapshot ต้องว่าง: {dest}")
    sqlite_files, plain = _snapshot_files(paths)
    entries: List[Dict[str, Any]] = []
    for src in sqlite_files:
        rel = paths.rel(src)
        target = dest / Path(*PurePosixPath(rel).parts)
        if not any(_is_within(target, r) for r in allowed_roots):
            raise RootViolation(f"ปฏิเสธการเขียนนอก root: {target}")
        integrity = sqlite_online_backup(src, target)
        tables: Dict[str, Any] = {}
        with ro_connect(target) as conn:
            all_tables = sqlite_contents_digest(conn)
            for spec in RECOVERY_TABLES:
                if paths.db_for(spec) == src:
                    rows = _read_rows(conn, spec.table)
                    if rows is not None:
                        tables[spec.table] = _table_digest(rows)
        entries.append({
            "rel": rel, "kind": "sqlite", "sha256": sha256_file(target), "size": target.stat().st_size,
            "integrity": integrity, "tables": tables, "all_tables": all_tables,
        })
    for src in plain:
        rel = paths.rel(src)
        data = src.read_bytes()
        target = dest / Path(*PurePosixPath(rel).parts)
        atomic_write_bytes(target, data, allowed_roots=allowed_roots)
        if sha256_file(target) != sha256_bytes(data):
            raise MigrationError(f"สำเนา {rel} ไม่ตรงต้นฉบับ")
        entry = {"rel": rel, "kind": "file", "sha256": sha256_bytes(data), "size": len(data)}
        if src.name.endswith(".json.publish-pending"):
            entry["mirror_intent"] = json.loads(data)
        entries.append(entry)
    manifest = {
        "schema": 1,
        "migration": MIGRATION_ID,
        "created_at": _now_iso(),
        "source_root": str(paths.root),
        "files": entries,
        "not_included": [
            "01_Raw/, 02_Assets/, 04_Exports/, 05_Covers_Thumbnails/ (media ไม่ถูกแก้โดย migration)",
            "03_Projects/<project>/ ไฟล์อื่นนอกจาก project.json (migration ไม่แตะ)",
            "browser localStorage / chrome.storage / หน่วยความจำของ server",
        ],
    }
    atomic_write_bytes(dest / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"), allowed_roots=allowed_roots)
    return manifest


def _load_manifest(manifest_path: Path) -> Dict[str, Any]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("migration") != MIGRATION_ID or not isinstance(manifest.get("files"), list):
        raise MigrationError("manifest ของ snapshot ไม่ถูกต้อง")
    seen = set()
    for entry in manifest["files"]:
        if not isinstance(entry, Mapping):
            raise MigrationError("entry ของ snapshot ไม่ถูกต้อง")
        rel = PurePosixPath(str(entry.get("rel", "")))
        if rel.is_absolute() or ".." in rel.parts or not rel.parts or "\\" in str(rel) or ":" in str(rel):
            raise MigrationError(f"path ใน manifest ไม่ปลอดภัย: {entry.get('rel')}")
        if str(rel).casefold() in seen:
            raise MigrationError("path ใน manifest ซ้ำกัน")
        seen.add(str(rel).casefold())
        if entry.get("kind") not in {"sqlite", "file"} or not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("sha256", ""))):
            raise MigrationError("kind/checksum ของ snapshot ไม่ถูกต้อง")
    return manifest


def restore_snapshot(manifest_path: Path, target_root: Path) -> Dict[str, Any]:
    """Restore a snapshot into an EMPTY (or new) ``target_root`` -- rehearsal.

    Verifies every snapshot file's sha256 before copying; refuses to
    overwrite any existing file (use ``Migrator.restore_snapshot_in_place`` for
    the guarded production path).
    """
    manifest_path = Path(manifest_path)
    snap_dir = manifest_path.parent
    manifest = _load_manifest(manifest_path)
    target_root = Path(os.path.abspath(target_root))
    if target_root.exists() and any(target_root.iterdir()):
        raise MigrationError("ปลายทางมีไฟล์อยู่แล้ว (ไม่เขียนทับ)")
    # Validate the COMPLETE input before creating or writing any destination.
    restored = []
    for entry in manifest["files"]:
        rel = PurePosixPath(entry["rel"])
        source = snap_dir / Path(*rel.parts)
        if sha256_file(source) != entry["sha256"]:
            raise MigrationError(f"ไฟล์ใน snapshot เสีย/ถูกแก้: {entry['rel']}")
        target = target_root / Path(*rel.parts)
        if target.exists():
            raise MigrationError(f"ปลายทางมีไฟล์อยู่แล้ว (ไม่เขียนทับ): {target}")
        if entry.get("mirror_intent"):
            intent = entry["mirror_intent"]
            if json.loads(source.read_text(encoding="utf-8")) != intent:
                raise MigrationError("mirror intent metadata ไม่ตรง snapshot")
            mirror_rel = str(rel).removesuffix(".publish-pending")
            expected_source = str((Path(manifest["source_root"]) / mirror_rel).resolve())
            if (intent.get("source_path") != expected_source or type(intent.get("token")) is not int
                    or not any(spec.mirror_rel == mirror_rel and spec.table == intent.get("table_name") for spec in RECOVERY_TABLES)):
                raise MigrationError("mirror intent ไม่ตรงกับ root/table ของ snapshot")
    target_root.mkdir(parents=True, exist_ok=True)
    for entry in manifest["files"]:
        rel = PurePosixPath(entry["rel"])
        source = snap_dir / Path(*rel.parts)
        target = target_root / Path(*rel.parts)
        atomic_write_bytes(target, source.read_bytes(), allowed_roots=[target_root])
        restored.append(entry["rel"])
    return {"restored": restored, "target_root": str(target_root)}


def verify_restore(manifest_path: Path, target_root: Path) -> Dict[str, Any]:
    """Compare a restored root with the snapshot manifest: sha256 per file,
    integrity_check, per-table counts/ids/rows, and that every store opens
    through ``DocumentTable`` with the same rows (JSON mirror import included)."""
    manifest = _load_manifest(Path(manifest_path))
    target_root = Path(os.path.abspath(target_root))
    paths = MigrationPaths.for_root(target_root)
    problems: List[str] = []
    checked = 0
    recoverable_mirrors = {entry["rel"].removesuffix(".publish-pending") for entry in manifest["files"] if entry.get("mirror_intent")}
    for entry in manifest["files"]:
        target = target_root / Path(*PurePosixPath(entry["rel"]).parts)
        if entry.get("mirror_intent") and not target.exists():
            # Successful store recovery consumes its durable intent. Canonical
            # DB and store-row digests are verified below on every invocation.
            checked += 1
            continue
        if not target.is_file():
            problems.append(f"ไม่มีไฟล์ {entry['rel']}")
            continue
        if entry.get("mirror_intent"):
            original = entry["mirror_intent"]
            actual = json.loads(target.read_text(encoding="utf-8"))
            expected_source = str(target.with_name(target.name.removesuffix(".publish-pending")).resolve())
            if actual != original and actual != {**original, "source_path": expected_source}:
                problems.append(f"mirror intent ไม่ตรง: {entry['rel']}")
        elif entry["kind"] != "sqlite" and sha256_file(target) != entry["sha256"]:
            recovered_digest = None
            for spec in RECOVERY_TABLES:
                if spec.mirror_rel == entry["rel"] and entry["rel"] in recoverable_mirrors:
                    db_rel = paths.rel(paths.db_for(spec))
                    recovered_digest = next((item.get("tables", {}).get(spec.table) for item in manifest["files"] if item["rel"] == db_rel), None)
                    break
            try:
                actual_digest = _table_digest(json.loads(target.read_text(encoding="utf-8"))) if recovered_digest else None
            except (ValueError, TypeError, KeyError):
                actual_digest = None
            if recovered_digest is None or actual_digest != recovered_digest:
                problems.append(f"sha256 ไม่ตรง: {entry['rel']}")
        if entry["kind"] == "sqlite":
            # Compared by content: opening a restored db through the stores
            # legitimately rewrites _json_mirror_state (file bytes change).
            with ro_connect(target) as conn:
                if "all_tables" in entry and sqlite_contents_digest(conn) != entry["all_tables"]:
                    problems.append(f"ตาราง SQLite ไม่ตรง snapshot: {entry['rel']}")
                integrity = _integrity(conn)
                if integrity != "ok":
                    problems.append(f"integrity_check {entry['rel']} = {integrity}")
                for table, digest in entry.get("tables", {}).items():
                    rows = _read_rows(conn, table) or []
                    if _table_digest(rows) != digest:
                        problems.append(f"ตาราง {table} ไม่ตรง snapshot")
        checked += 1
    opened: Dict[str, int] = {}
    if not problems:
        try:
            for spec in RECOVERY_TABLES:
                db_path = paths.db_for(spec)
                if not db_path.exists():
                    continue
                expected = None
                for entry in manifest["files"]:
                    if entry["kind"] == "sqlite" and entry["rel"] == paths.rel(db_path):
                        expected = entry.get("tables", {}).get(spec.table)
                if expected is None:
                    continue
                table = _db.DocumentTable(spec.table, (lambda p=db_path: p), (lambda s=spec: paths.mirror_for(s)))
                mirror = paths.mirror_for(spec)
                intent_path = mirror.with_name(mirror.name + ".publish-pending")
                if intent_path.is_file():
                    intent = json.loads(intent_path.read_text(encoding="utf-8"))
                    source_mirror = Path(manifest["source_root"]) / Path(paths.rel(mirror))
                    old_source = str(source_mirror.resolve())
                    new_source = str(mirror.resolve())
                    if (intent.get("source_path") not in {old_source, new_source}
                            or intent.get("table_name") != spec.table or type(intent.get("token")) is not int):
                        raise MigrationError("mirror intent ไม่ตรงกับ root/table ของ snapshot")
                    if old_source != new_source:
                        with sqlite3.connect(str(db_path)) as conn:
                            marker = conn.execute("SELECT last_imported_mtime_ns FROM _json_mirror_state WHERE source_path=? AND table_name=?",
                                                  (old_source, spec.table)).fetchone()
                            if marker:
                                _db._upsert_mirror_marker(conn, new_source, spec.table, marker[0])
                        intent["source_path"] = new_source
                        atomic_write_bytes(intent_path, json.dumps(intent).encode(), allowed_roots=[target_root])
                rows = table.load()
                opened[spec.name] = len(rows)
                if _table_digest(rows) != expected:
                    problems.append(f"{spec.name}: เปิดผ่าน store แล้วไม่ตรง snapshot (mirror ไม่ตรง DB?)")
        finally:
            _close_cached_connections(target_root)
    return {"ok": not problems, "problems": problems, "files_checked": checked, "stores_opened": opened}


# --------------------------------------------------------------------------- fingerprint / validation


def fingerprint(paths: MigrationPaths) -> Dict[str, Any]:
    """Read-only digest of everything the migration may change."""
    world = load_world(paths)
    # Restoring a database replaces ALL its tables, even ones P2 does not
    # migrate. Include every user table so new jobs (or future stores) block it.
    databases = {}
    for key, database in (("store", paths.store_db), ("batch", paths.batch_db)):
        with ro_connect(database) as conn:
            databases[key] = sqlite_contents_digest(conn)
    recovery_files = {}
    for path in (paths.channels_json, paths.campaigns_json, paths.gadget_index):
        recovery_files[paths.rel(path)] = sha256_file(path) if path.is_file() else None
    if paths.gadget_projects.is_dir():
        for path in sorted(paths.gadget_projects.rglob("*.json")):
            recovery_files[paths.rel(path)] = sha256_file(path)
    for spec in RECOVERY_TABLES:
        mirror = paths.mirror_for(spec)
        intent = mirror.with_name(mirror.name + ".publish-pending")
        recovery_files[paths.rel(intent)] = sha256_file(intent) if intent.is_file() else None
        if spec not in TABLES:
            recovery_files[paths.rel(mirror)] = sha256_file(mirror) if mirror.is_file() else None
    return {
        "tables": {name: (row_hash(sorted((str(r.get("id")), canon(r)) for r in rows)) if rows is not None else None)
                   for name, rows in world.tables.items()},
        "manifests": {name: doc.sha256 for name, doc in sorted(world.manifests.items())},
        "task_registry": world.tasks.sha256,
        "databases": databases,
        "recovery_files": recovery_files,
    }


def ownership_violations(world: World, *, ignore: Iterable[Tuple[str, str]] = ()) -> List[str]:
    """Children with ``channel_id`` whose parent's ``channel_id`` differs."""
    ignore = set(ignore)
    products = {str(p.get("id")): p.get(OWNER_KEY) for p in world.rows("products")}
    exports = {str(e.get("id")): e.get(OWNER_KEY) for e in world.rows("export_registry")}
    problems: List[str] = []

    def check(store: str, rid: str, owner: Any, parents: Sequence[Tuple[str, Any]]) -> None:
        if owner is None or (store, rid) in ignore:
            return
        for kind, pid in parents:
            if not pid:
                continue
            table = products if kind == "product" else exports
            parent_owner = table.get(str(pid))
            if parent_owner is not None and parent_owner != owner:
                problems.append(f"{store}/{rid}: channel_id={owner} แต่ {kind} {pid} เป็นของ {parent_owner}")

    for product in world.rows("products"):
        for angle in product.get("angles") or []:
            if isinstance(angle, Mapping) and angle.get(OWNER_KEY) is not None and product.get(OWNER_KEY) is not None:
                if angle.get(OWNER_KEY) != product.get(OWNER_KEY) and ("products", str(product.get("id"))) not in ignore:
                    problems.append(f"products/{product.get('id')}: angle {angle.get('angle_id')} ต่างช่อง")
    for e in world.rows("export_registry"):
        check("export_registry", str(e.get("id")), e.get(OWNER_KEY), [("product", e.get("product_id"))])
    for p in world.rows("posts"):
        check("posts", str(p.get("id")), p.get(OWNER_KEY), [("export", p.get("export_id")), ("product", p.get("product_id"))])
    for q in world.rows("schedule_queue"):
        check("schedule_queue", str(q.get("id")), q.get(OWNER_KEY), [("export", q.get("export_id")), ("product", q.get("product_id"))])
    for store in ("shot_lists", "recording_sessions", "batch_render_queue"):
        for r in world.rows(store):
            check(store, str(r.get("id")), r.get(OWNER_KEY), [("product", r.get("product_id"))])
    tasks = world.tasks.data if isinstance(world.tasks.data, Mapping) else {}
    for tid, t in tasks.items():
        if isinstance(t, Mapping):
            payload = t.get("payload") if isinstance(t.get("payload"), Mapping) else {}
            check("task_registry", str(tid), t.get(OWNER_KEY), [("product", payload.get("product_id"))])
    for name, doc in world.manifests.items():
        if isinstance(doc.data, Mapping):
            check("manifests", name, doc.data.get(OWNER_KEY), [("product", manifest_product_id(doc.data)), ("export", doc.data.get("export_id"))])
    return problems


# --------------------------------------------------------------------------- manifest text edits


_FIRST_KEY_RE = re.compile(r"\A(?P<bom>﻿?)(?P<lead>\s*)\{(?P<nl>\r?\n)(?P<indent>[ \t]+)\"")


def insert_top_level_key(text: str, key: str, value: Any) -> Tuple[str, str]:
    """Insert ``"key": value,`` as the first member of a JSON object WITHOUT
    touching any other byte.  Returns (new_text, inserted_segment)."""
    encoded_key = json.dumps(key, ensure_ascii=False)
    encoded_value = json.dumps(value, ensure_ascii=False)
    match = _FIRST_KEY_RE.match(text)
    if match:
        segment = f"{match.group('nl')}{match.group('indent')}{encoded_key}: {encoded_value},"
        pos = match.end("lead") + 1  # right after "{" (bom + lead precede it)
    else:
        stripped = text.lstrip("﻿ \t\r\n")
        if not stripped.startswith("{"):
            raise MigrationError("project.json ไม่ใช่ JSON object")
        pos = len(text) - len(stripped) + 1
        rest = stripped[1:].lstrip()
        segment = f"{encoded_key}:{encoded_value}" + ("" if rest.startswith("}") else ",")
    new_text = text[:pos] + segment + text[pos:]
    return new_text, segment


# --------------------------------------------------------------------------- journal / state


class Journal:
    def __init__(self, path: Path, allowed_roots: Sequence[Path]):
        self.path = path
        self._allowed = allowed_roots

    def append(self, event: Dict[str, Any]) -> None:
        if not any(_is_within(self.path, r) for r in self._allowed):
            raise RootViolation(f"ปฏิเสธการเขียนนอก root: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"ts": _now_iso(), **event}, ensure_ascii=False) + "\n"
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def events(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                break  # a torn last line from a crash: ignore the tail
        return out

    def done_steps(self) -> set:
        return {e["step"] for e in self.events() if e.get("event") == "done"}


# --------------------------------------------------------------------------- migrator


Hook = Callable[[str, str], None]


class Migrator:
    """Runs dry-run / apply / resume / rollback against one data root."""

    def __init__(
        self,
        root: Optional[Path] = None,
        *,
        hook: Optional[Hook] = None,
        server_probe: Optional[Callable[[], bool]] = None,
    ):
        self.paths = MigrationPaths.for_root(root)
        self.hook = hook
        self.server_probe = server_probe
        self.allowed_roots = [self.paths.root]

    # -- small utilities ------------------------------------------------
    def _hook(self, step: str, when: str) -> None:
        if self.hook is not None:
            self.hook(step, when)

    def _write_json(self, path: Path, doc: Any) -> None:
        atomic_write_bytes(path, json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"), allowed_roots=self.allowed_roots)

    def _table(self, spec: TableSpec) -> _db.DocumentTable:
        db_path = self.paths.db_for(spec)
        mirror = self.paths.mirror_for(spec)
        return _db.DocumentTable(spec.table, lambda: db_path, lambda: mirror)

    def current_run(self) -> Optional[Dict[str, Any]]:
        pointer = self.paths.current_pointer
        if not pointer.exists():
            return None
        try:
            ref = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise MigrationError(f"ไฟล์สถานะ migration เสีย: {pointer}")
        run_id = ref.get("run_id")
        state = self._read_state(run_id) if run_id else None
        return state or ref

    def _read_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        path = self.paths.run_dir(run_id) / "state.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_state(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = _now_iso()
        self._write_json(self.paths.run_dir(state["run_id"]) / "state.json", state)
        self._write_json(self.paths.current_pointer, {"run_id": state["run_id"], "status": state["status"]})

    def _journal(self, run_id: str) -> Journal:
        return Journal(self.paths.run_dir(run_id) / "journal.jsonl", self.allowed_roots)

    def _plan_of(self, run_id: str) -> Dict[str, Any]:
        return json.loads((self.paths.run_dir(run_id) / "plan.json").read_text(encoding="utf-8"))

    # -- dry run ------------------------------------------------------------
    def dry_run(
        self,
        *,
        assignments: Sequence[Mapping[str, str]] = (),
        rename_templates: bool = False,
        legacy_owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read-only: plan + preflight + estimated write set.  Writes nothing."""
        world = load_world(self.paths)
        plan = build_plan(world, assignments=assignments, rename_templates=rename_templates, legacy_owner=legacy_owner)
        current = None
        try:
            current = self.current_run()
        except MigrationError:
            current = {"status": "corrupt"}
        if current is not None:
            # never leak the lock bypass token / fingerprints into a report
            current = {k: current.get(k) for k in ("run_id", "status", "created_at", "applied_at", "rolled_back_at", "error") if k in current}
        checks = preflight(world, plan, server_probe=self.server_probe, current_run=current)
        return {
            "mode": "dry-run",
            "generated_at": _now_iso(),
            "root": str(self.paths.root),
            "plan": plan,
            "preflight": checks,
            "write_set": self._write_set(world, plan),
            "not_touched": NOT_TOUCHED,
            "inventory": {
                "table_counts": {k: (len(v) if v is not None else None) for k, v in world.tables.items()},
                "manifests": len(world.manifests),
                "project_dirs_without_manifest": world.project_dirs_without_manifest,
                "skipped_project_dirs": world.skipped_project_dirs,
                "tasks": len(world.tasks.data) if isinstance(world.tasks.data, Mapping) else None,
                "gadget_media_projects": len(world.gadget_projects),
                "gadget_media_index_exists": world.gadget_index_exists,
                "integrity": world.integrity,
            },
            "current_run": current,
        }

    def _write_set(self, world: World, plan: Mapping[str, Any]) -> Dict[str, Any]:
        by_store: Dict[str, int] = {}
        for action in plan["actions"]:
            by_store[action["store"]] = by_store.get(action["store"], 0) + 1
        files: List[str] = []
        for spec in TABLES:
            if by_store.get(spec.name):
                files.append(f"{self.paths.rel(self.paths.db_for(spec))} (ตาราง {spec.table}: {by_store[spec.name]} แถว)")
                files.append(f"{spec.mirror_rel} (เขียนใหม่ทั้งไฟล์จาก DB ผ่าน DocumentTable)")
        if by_store.get("task_registry"):
            files.append(f"03_Projects/task_registry.json ({by_store['task_registry']} งาน)")
        if by_store.get("manifests"):
            files.append(f"03_Projects/<project>/project.json {by_store['manifests']} ไฟล์ (แทรก channel_id บรรทัดเดียว)")
        for rel in _gadget_group_files([a for a in plan["actions"] if a["store"] in GADGET_STORES]):
            files.append(f"{rel} (Gadget channel_id เท่านั้น; ไม่สร้าง stage/artifact ใหม่)")
        files.append("06_Archive/Migrations/multi_channel_v1/<run_id>/ (plan, journal, state, snapshot)")
        files.append("_Docs/.maintenance.lock (ระหว่าง apply)")
        return {"rows_by_store": by_store, "files": files, "snapshot_estimate_bytes": _snapshot_estimate(self.paths, world)}

    # -- apply ----------------------------------------------------------------
    def apply(
        self,
        *,
        expect_plan: str,
        assignments: Sequence[Mapping[str, str]] = (),
        rename_templates: bool = False,
        legacy_owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        current = self.current_run()
        if current and current.get("status") in ("in_progress", "needs_attention"):
            raise PreflightBlocked(
                f"migration รอบ {current.get('run_id')} ยังค้าง ({current.get('status')}) ใช้ --resume หรือ --rollback"
            )
        world = load_world(self.paths)
        plan = build_plan(world, assignments=assignments, rename_templates=rename_templates, legacy_owner=legacy_owner)
        if not expect_plan or plan["plan_hash"] != expect_plan:
            raise PlanMismatch(
                f"plan ไม่ตรงกับที่ตรวจไว้ (ตอนนี้ {plan['plan_hash'][:16]}…, ระบุ {str(expect_plan)[:16]}…) "
                "ข้อมูลหรือการตัดสินใจเปลี่ยนไป ให้รัน dry-run แล้วตรวจรายงานใหม่"
            )
        if not plan["actions"]:
            return {"status": "noop", "writes": 0, "plan_hash": plan["plan_hash"], "message": "ไม่มีอะไรต้องย้าย (0 แถว)"}
        checks = preflight(world, plan, server_probe=self.server_probe, current_run=current)
        if checks["blockers"]:
            failing = [c for c in checks["checks"] if c["level"] == "blocker" and not c["ok"]]
            raise PreflightBlocked("preflight ไม่ผ่าน: " + "; ".join(c["message"] for c in failing), failing)

        run_id = _dt.datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        run_dir = self.paths.run_dir(run_id)
        _mkdir(run_dir, allowed_roots=self.allowed_roots)
        token = uuid.uuid4().hex
        plan_doc = dict(plan)
        plan_doc["run_id"] = run_id
        plan_doc["created_at"] = _now_iso()
        self._write_json(run_dir / "plan.json", plan_doc)
        state = {
            "run_id": run_id, "status": "in_progress", "token": token, "plan_hash": plan["plan_hash"],
            "created_at": _now_iso(), "options": plan["options"], "data_written": False,
            "pre_fingerprint": fingerprint(self.paths), "post_fingerprint": None, "snapshot_manifest": None,
        }
        self._save_state(state)
        journal = self._journal(run_id)
        journal.append({"step": "preflight", "event": "done", "blockers": 0, "plan_hash": plan["plan_hash"]})
        return self._execute(state, plan_doc, journal, fresh=True)

    def resume(self) -> Dict[str, Any]:
        state = self.current_run()
        if not state or state.get("status") not in ("in_progress", "needs_attention"):
            raise MigrationError("ไม่มี migration ค้างให้ resume")
        plan = self._plan_of(state["run_id"])
        journal = self._journal(state["run_id"])
        journal.append({"step": "resume", "event": "start", "previous_status": state.get("status")})
        state["status"] = "in_progress"
        self._save_state(state)
        return self._execute(state, plan, journal, fresh=False)

    def _acquire_lock(self, state: Dict[str, Any], *, adopt: bool) -> None:
        maintenance_lock.acquire(
            self.paths.root,
            owner=LOCK_OWNER,
            reason=f"ย้ายข้อมูลหลายช่อง ({MIGRATION_ID}) รอบ {state['run_id']}",
            run_id=state["run_id"],
            token=state["token"],
            take_over_token=state["token"] if adopt else None,
            take_over_stale=adopt,
        )

    def _execute(self, state: Dict[str, Any], plan: Dict[str, Any], journal: Journal, *, fresh: bool) -> Dict[str, Any]:
        run_id = state["run_id"]
        done = journal.done_steps()
        try:
            if "lock" not in done or not fresh:
                self._acquire_lock(state, adopt=not fresh)
                journal.append({"step": "lock", "event": "done", "token_sha256": sha256_bytes(state["token"].encode())})
            with maintenance_lock.bypass(state["token"]):
                if "snapshot" not in done:
                    self._hook("snapshot", "before")
                    journal.append({"step": "snapshot", "event": "start"})
                    snap_dir = self.paths.run_dir(run_id) / "snapshot"
                    if snap_dir.exists() and any(snap_dir.iterdir()):
                        snap_dir = self.paths.run_dir(run_id) / f"snapshot-{uuid.uuid4().hex[:6]}"
                    manifest = create_snapshot(self.paths, snap_dir, allowed_roots=self.allowed_roots)
                    state["snapshot_manifest"] = self.paths.rel(snap_dir / "manifest.json")
                    self._save_state(state)
                    self._hook("snapshot", "after")
                    journal.append({
                        "step": "snapshot", "event": "done", "manifest": state["snapshot_manifest"],
                        "files": len(manifest["files"]),
                    })
                actions_by_store: Dict[str, List[Dict[str, Any]]] = {}
                for action in plan["actions"]:
                    actions_by_store.setdefault(action["store"], []).append(action)
                for step in DATA_STEPS:
                    if step in done:
                        continue
                    actions = actions_by_store.get(step, [])
                    if not actions:
                        journal.append({"step": step, "event": "skip", "reason": "no actions"})
                        continue
                    self._hook(step, "before")
                    journal.append({"step": step, "event": "start", "actions": len(actions)})
                    if step in TABLE_BY_NAME:
                        rows = self._apply_table(TABLE_BY_NAME[step], actions, state)
                    elif step == "task_registry":
                        rows = self._apply_tasks(actions, state)
                    elif step in GADGET_STORES:
                        rows = self._apply_gadget(step, actions, state, journal)
                    else:
                        rows = self._apply_manifests(actions, state, journal)
                    self._hook(step, "after")
                    journal.append({"step": step, "event": "done", "rows": rows})
                self._hook("validate", "before")
                problems = self.validate(state, plan)
                if problems:
                    journal.append({"step": "validate", "event": "failed", "problems": problems[:200]})
                    raise ValidationFailed(problems)
                state["post_fingerprint"] = fingerprint(self.paths)
                journal.append({"step": "validate", "event": "done", "post_fingerprint": state["post_fingerprint"]})
            # Release first, then mark applied: a crash in between leaves an
            # in_progress run without a lock, which --resume finishes
            # (re-validates) instead of a stranded lock on an "applied" run.
            self._hook("release", "before")
            maintenance_lock.release(self.paths.root, state["token"])
            journal.append({"step": "release", "event": "done"})
            state["status"] = "applied"
            state["applied_at"] = _now_iso()
            self._save_state(state)
            return {
                "status": "applied", "run_id": run_id, "plan_hash": state["plan_hash"],
                "rows": sum(1 for _ in plan["actions"]), "snapshot_manifest": state["snapshot_manifest"],
            }
        except SimulatedCrash:
            raise  # emulated kill: no cleanup, lock stays (stale) for --resume/--rollback
        except Exception as exc:
            journal.append({"step": "error", "event": "error", "error": f"{exc.__class__.__name__}: {exc}"})
            if state.get("data_written"):
                state["status"] = "needs_attention"
                state["error"] = str(exc)
                self._save_state(state)
            else:
                state["status"] = "failed_clean"
                state["error"] = str(exc)
                self._save_state(state)
                maintenance_lock.release(self.paths.root, state["token"])
            raise
        finally:
            _close_cached_connections(self.paths.root)

    # -- data steps -------------------------------------------------------------
    def _guard_mirror(self, spec: TableSpec) -> None:
        """Refuse when a pending auto-import would replace DB rows with
        different mirror content (it would clobber committed data)."""
        mirror = self.paths.mirror_for(spec)
        if not mirror.exists():
            return
        world_rows: Optional[List[Dict[str, Any]]]
        with ro_connect(self.paths.db_for(spec)) as conn:
            world_rows = _read_rows(conn, spec.table)
            state = _mirror_state(conn)
        token = _mirror_token(mirror)
        pending = token is None or state.get(str(mirror.resolve())) != token
        if not pending or world_rows is None:
            return
        doc = _read_json_file(mirror, spec.mirror_rel)
        if not isinstance(doc.data, list):
            return  # db.py refuses to import an invalid mirror
        try:
            same = {str(r["id"]): canon(r) for r in doc.data} == {str(r["id"]): canon(r) for r in world_rows}
        except (KeyError, TypeError):
            return
        if not same:
            raise DriftError(f"{spec.mirror_rel} ถูกแก้ตรงและไม่ตรงกับ DB — หยุดก่อน auto-import ทับข้อมูล")

    def _repair_mirror(self, spec: TableSpec, table: _db.DocumentTable) -> None:
        conn = table._conn()
        rows = [json.loads(r[0]) for r in conn.execute(f"SELECT data FROM {spec.table}").fetchall()]
        mirror = self.paths.mirror_for(spec)
        doc = _read_json_file(mirror, spec.mirror_rel)
        ok = isinstance(doc.data, list) and [canon(r) for r in doc.data] == [canon(r) for r in rows]
        if not ok:
            table._write_json_mirror(conn)

    def _apply_table(self, spec: TableSpec, actions: List[Dict[str, Any]], state: Dict[str, Any]) -> List[Dict[str, Any]]:
        self._guard_mirror(spec)
        table = self._table(spec)
        journal_rows: List[Dict[str, Any]] = []
        with table.mutate() as records:
            index = {str(r.get("id")): pos for pos, r in enumerate(records)}
            for action in actions:
                rid, owner = action["id"], action["owner"]
                if action["op"] == "rename_template":
                    journal_rows.append(self._rename_row(records, index, action))
                    continue
                pos = index.get(rid)
                if pos is None:
                    raise DriftError(f"{spec.name}/{rid}: แถวหายไประหว่าง plan กับ apply")
                row = records[pos]
                current = row.get(OWNER_KEY)
                if current is not None:
                    if current == owner and row_hash(_without(row, OWNER_KEY)) == action["before_hash"]:
                        journal_rows.append({"id": rid, "added": {OWNER_KEY: owner}, "before_hash": action["before_hash"], "after_hash": row_hash(row), "already": True})
                        continue
                    raise DriftError(f"{spec.name}/{rid}: channel_id เปลี่ยนไประหว่าง plan กับ apply")
                if row_hash(row) != action["before_hash"]:
                    raise DriftError(f"{spec.name}/{rid}: ข้อมูลแถวเปลี่ยนไประหว่าง plan กับ apply")
                row[OWNER_KEY] = owner
                journal_rows.append({"id": rid, "added": {OWNER_KEY: owner}, "before_hash": action["before_hash"], "after_hash": row_hash(row)})
            changed = any(not r.get("already") for r in journal_rows)
            if changed:
                state["data_written"] = True
        if changed:
            self._save_state(state)
        self._hook(spec.name, "after_commit")
        self._repair_mirror(spec, table)
        return journal_rows

    @staticmethod
    def _rename_row(records: List[Dict[str, Any]], index: Dict[str, int], action: Dict[str, Any]) -> Dict[str, Any]:
        old, new, owner = action["id"], action["new_id"], action["owner"]
        if old in index:
            if new in index:
                raise DriftError(f"schedule_templates: มี {new} อยู่แล้ว")
            row = records[index[old]]
            if row.get(OWNER_KEY) is not None or row_hash(row) != action["before_hash"]:
                raise DriftError(f"schedule_templates/{old}: ข้อมูลเปลี่ยนไประหว่าง plan กับ apply")
            renamed = dict(row)
            renamed["id"] = new
            renamed[OWNER_KEY] = owner
            renamed[LEGACY_ID_KEY] = old
            records[index[old]] = renamed
            return {"id": old, "new_id": new, "added": {OWNER_KEY: owner, LEGACY_ID_KEY: old}, "before_hash": action["before_hash"], "after_hash": row_hash(renamed)}
        if new in index:
            row = records[index[new]]
            restored = _without(row, OWNER_KEY, LEGACY_ID_KEY)
            restored["id"] = old
            if row.get(LEGACY_ID_KEY) == old and row.get(OWNER_KEY) == owner and row_hash(restored) == action["before_hash"]:
                return {"id": old, "new_id": new, "added": {OWNER_KEY: owner, LEGACY_ID_KEY: old}, "before_hash": action["before_hash"], "after_hash": row_hash(row), "already": True}
        raise DriftError(f"schedule_templates/{old}: ไม่พบแถวต้นทาง")

    def _apply_gadget(self, step: str, actions: List[Dict[str, Any]], state: Dict[str, Any], journal: Journal) -> List[Dict[str, Any]]:
        pending = []
        for rel, entry in _gadget_group_files(actions).items():
            path = self.paths.root / rel
            if not _is_within(path, self.paths.root):
                raise RootViolation("Gadget file ออกนอก root")
            original = self._snapshot_file(state, rel)
            if original is None or sha256_bytes(original) != entry["before_hash"]:
                raise DriftError(f"Gadget/{rel}: snapshot ไม่ตรง plan")
            expected = json.loads(original.decode("utf-8-sig"))
            for change in entry["changes"]:
                _gadget_selected(expected, change["selector"])[OWNER_KEY] = change["owner"]
            raw = path.read_bytes()
            if raw != original and canon(json.loads(raw.decode("utf-8-sig"))) != canon(expected):
                raise DriftError(f"Gadget/{rel}: ข้อมูลเปลี่ยนหลัง plan (ไม่เขียนทับ)")
            pending.append((path, rel, original, raw, expected))
        # Prevalidate every materialized file before the first mutation.
        rows = []
        for path, rel, original, raw, expected in pending:
            already = raw != original
            if not already:
                state["data_written"] = True
                self._save_state(state)
                raw = json.dumps(expected, ensure_ascii=False, indent=2).encode("utf-8")
                atomic_write_bytes(path, raw, allowed_roots=self.allowed_roots)
            event = {"rel": rel, "before_hash": sha256_bytes(original), "after_hash": sha256_bytes(raw), "already": already}
            journal.append({"step": step, "event": "item", **event})
            rows.append(event)
            self._hook(step, "after_item")
        self._hook(step, "after_commit")
        return rows

    def _apply_tasks(self, actions: List[Dict[str, Any]], state: Dict[str, Any]) -> List[Dict[str, Any]]:
        path = self.paths.task_registry
        raw = path.read_bytes()
        tasks = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(tasks, dict):
            raise DriftError("task_registry.json ไม่ใช่ object")
        rows: List[Dict[str, Any]] = []
        changed = False
        for action in actions:
            task = tasks.get(action["id"])
            if not isinstance(task, dict):
                raise DriftError(f"task_registry/{action['id']}: งานหายไประหว่าง plan กับ apply")
            if task.get(OWNER_KEY) is not None:
                if task.get(OWNER_KEY) == action["owner"] and row_hash(_without(task, OWNER_KEY)) == action["before_hash"]:
                    rows.append({"id": action["id"], "added": {OWNER_KEY: action["owner"]}, "before_hash": action["before_hash"], "after_hash": row_hash(task), "already": True})
                    continue
                raise DriftError(f"task_registry/{action['id']}: channel_id เปลี่ยนไป")
            if row_hash(task) != action["before_hash"]:
                raise DriftError(f"task_registry/{action['id']}: ข้อมูลงานเปลี่ยนไประหว่าง plan กับ apply")
            task[OWNER_KEY] = action["owner"]
            changed = True
            rows.append({"id": action["id"], "added": {OWNER_KEY: action["owner"]}, "before_hash": action["before_hash"], "after_hash": row_hash(task)})
        if changed:
            new = json.dumps(tasks, ensure_ascii=False, indent=2).encode("utf-8")
            state["data_written"] = True
            self._save_state(state)
            atomic_write_bytes(path, new, allowed_roots=self.allowed_roots)
            for r in rows:
                r["file_before_sha256"] = sha256_bytes(raw)
                r["file_after_sha256"] = sha256_bytes(new)
        self._hook("task_registry", "after_commit")
        return rows

    def _apply_manifests(self, actions: List[Dict[str, Any]], state: Dict[str, Any], journal: Journal) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for action in actions:
            name, owner = action["id"], action["owner"]
            path = self.paths.manifest_path(name)
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            data = json.loads(text.lstrip("﻿"))
            if sha256_bytes(raw) != action["before_hash"]:
                if isinstance(data, dict) and data.get(OWNER_KEY) == owner:
                    # Done by a crashed earlier attempt: re-derive the exact
                    # inserted segment from the snapshot so rollback stays byte-exact.
                    entry = {"id": name, "added": {OWNER_KEY: owner}, "before_hash": action["before_hash"], "after_hash": sha256_bytes(raw), "already": True}
                    original = self._snapshot_file(state, f"03_Projects/{name}/project.json")
                    if original is not None and sha256_bytes(original) == action["before_hash"]:
                        redo, segment = insert_top_level_key(original.decode("utf-8"), OWNER_KEY, owner)
                        if sha256_bytes(redo.encode("utf-8")) == sha256_bytes(raw):
                            entry["segment"] = segment
                            journal.append({"step": "manifests", "event": "item", **entry})
                    rows.append(entry)
                    continue
                raise DriftError(f"manifests/{name}: project.json เปลี่ยนไประหว่าง plan กับ apply")
            if not isinstance(data, dict) or OWNER_KEY in data:
                raise DriftError(f"manifests/{name}: project.json ไม่ใช่ object หรือมี channel_id แล้ว")
            new_text, segment = insert_top_level_key(text, OWNER_KEY, owner)
            check = json.loads(new_text.lstrip("﻿"))
            if _without(check, OWNER_KEY) != data or check.get(OWNER_KEY) != owner:
                raise MigrationError(f"manifests/{name}: แทรก channel_id แล้วเนื้อหาเปลี่ยน (หยุด)")
            new = new_text.encode("utf-8")
            state["data_written"] = True
            self._save_state(state)
            atomic_write_bytes(path, new, allowed_roots=self.allowed_roots)
            entry = {"id": name, "added": {OWNER_KEY: owner}, "before_hash": action["before_hash"], "after_hash": sha256_bytes(new), "segment": segment}
            journal.append({"step": "manifests", "event": "item", **entry})
            rows.append(entry)
            self._hook("manifests", "after_item")
        return rows

    def _snapshot_file(self, state: Mapping[str, Any], rel: str) -> Optional[bytes]:
        if not state.get("snapshot_manifest"):
            return None
        snap_root = (self.paths.root / Path(*PurePosixPath(state["snapshot_manifest"]).parts)).parent
        path = snap_root / Path(*PurePosixPath(rel).parts)
        return path.read_bytes() if path.is_file() else None

    # -- validation -----------------------------------------------------------------
    def validate(self, state: Mapping[str, Any], plan: Mapping[str, Any]) -> List[str]:
        """Counts/ids preserved, only planned fields changed, children match
        parents, mirrors == DB, integrity_check -- against the snapshot."""
        problems: List[str] = []
        snap_manifest_rel = state.get("snapshot_manifest")
        if not snap_manifest_rel:
            return ["ไม่มี snapshot ให้เทียบ"]
        snap_root = (self.paths.root / Path(*PurePosixPath(snap_manifest_rel).parts)).parent
        snap_paths = MigrationPaths.for_root(snap_root)
        world_before = load_world(snap_paths)
        world_after = load_world(self.paths)
        actions: Dict[Tuple[str, str], Dict[str, Any]] = {(a["store"], a["id"]): a for a in plan["actions"]}

        for key, status in world_after.integrity.items():
            if status not in ("ok", "missing"):
                problems.append(f"integrity_check {key} = {status}")
        for spec in TABLES:
            before = {str(r.get("id")): r for r in world_before.rows(spec.name)}
            after = {str(r.get("id")): r for r in world_after.rows(spec.name)}
            renames = {a["new_id"]: a["id"] for (s, _), a in actions.items() if s == spec.name and a.get("new_id")}
            mapped_after = {renames.get(rid, rid): row for rid, row in after.items()}
            if set(before) != set(mapped_after):
                problems.append(f"{spec.name}: ids ไม่ครบ/เกิน (ก่อน {len(before)}, หลัง {len(after)})")
            for rid, old in before.items():
                new = mapped_after.get(rid)
                if new is None:
                    continue
                action = actions.get((spec.name, rid))
                expected = dict(old)
                if action is not None:
                    expected[OWNER_KEY] = action["owner"]
                    if action.get("new_id"):
                        expected["id"] = action["new_id"]
                        expected[LEGACY_ID_KEY] = rid
                if canon(new) != canon(expected):
                    problems.append(f"{spec.name}/{rid}: มีการเปลี่ยนนอกฟิลด์ที่วางแผนไว้")
            if spec.name in {a["store"] for a in actions.values()} and _mirror_matches(world_after, spec.name) is False:
                problems.append(f"{spec.mirror_rel}: mirror ไม่ตรงกับ DB")
        # task registry
        before_tasks = world_before.tasks.data if isinstance(world_before.tasks.data, Mapping) else None
        after_tasks = world_after.tasks.data if isinstance(world_after.tasks.data, Mapping) else None
        if before_tasks is not None:
            if after_tasks is None or set(before_tasks) != set(after_tasks):
                problems.append("task_registry: ids ไม่ครบ")
            else:
                for tid, old in before_tasks.items():
                    expected = dict(old) if isinstance(old, Mapping) else old
                    action = actions.get(("task_registry", str(tid)))
                    if action is not None:
                        expected[OWNER_KEY] = action["owner"]
                    if canon(after_tasks[tid]) != canon(expected):
                        problems.append(f"task_registry/{tid}: มีการเปลี่ยนนอกฟิลด์ที่วางแผนไว้")
        # manifests
        for name, old in world_before.manifests.items():
            new = world_after.manifests.get(name)
            if new is None:
                problems.append(f"manifests/{name}: หายไป")
                continue
            action = actions.get(("manifests", name))
            if action is None:
                if new.sha256 != old.sha256:
                    problems.append(f"manifests/{name}: ถูกแก้ทั้งที่ไม่ได้วางแผน")
                continue
            if not isinstance(new.data, Mapping) or new.data.get(OWNER_KEY) != action["owner"] or _without(new.data, OWNER_KEY) != old.data:
                problems.append(f"manifests/{name}: เนื้อหาไม่ตรง (ต้องเพิ่มเฉพาะ channel_id)")
        if set(world_after.manifests) != set(world_before.manifests):
            problems.append("manifests: จำนวนไฟล์เปลี่ยน")
        gadget_files = _gadget_group_files([a for a in plan["actions"] if a["store"] in GADGET_STORES])
        for rel, entry in gadget_files.items():
            original = self._snapshot_file(state, rel)
            expected = json.loads(original.decode("utf-8-sig"))
            for change in entry["changes"]:
                _gadget_selected(expected, change["selector"])[OWNER_KEY] = change["owner"]
            current = _read_json_file(self.paths.root / rel, rel)
            if canon(current.data) != canon(expected):
                problems.append(f"Gadget/{rel}: ต้องเปลี่ยนเฉพาะ channel_id ที่วางแผนไว้")
        snapshot_manifest = _load_manifest(self.paths.root / state["snapshot_manifest"])
        for item in snapshot_manifest["files"]:
            rel = item["rel"]
            if (rel.startswith(("03_Projects/GadgetMedia/", "_Docs/gadget_media/")) or rel == "_Docs/gadget_media_campaigns.json") and rel not in gadget_files:
                path = self.paths.root / rel
                if not path.is_file() or sha256_file(path) != item["sha256"]:
                    problems.append(f"Gadget/{rel}: unassigned/stage data ถูกแก้ (ไม่อยู่ในแผน)")
        conflicts = {(d["store"], d["id"]) for d in plan["decisions"] if d["status"] == "conflict"}
        problems.extend(ownership_violations(world_after, ignore=conflicts))
        return problems

    # -- rollback ---------------------------------------------------------------------
    def rollback(self) -> Dict[str, Any]:
        """Reverse the journaled field additions of the current run.

        Rows/files changed after cutover keep their newer content (only the
        migration-added fields are removed); rows created after cutover are not
        touched.  Exact pre-state is restored where nothing changed since.
        """
        state = self.current_run()
        if not state or state.get("status") not in ("in_progress", "needs_attention", "applied", "failed_clean"):
            raise MigrationError("ไม่มี migration ให้ rollback")
        run_id = state["run_id"]
        plan = self._plan_of(run_id)
        journal = self._journal(run_id)
        token = state["token"]
        lock = maintenance_lock.read_lock(self.paths.root)
        if lock is None:
            maintenance_lock.acquire(self.paths.root, owner=LOCK_OWNER, reason=f"rollback {run_id}", run_id=run_id, token=token)
        elif lock.get("token") != token:
            maintenance_lock.acquire(
                self.paths.root, owner=LOCK_OWNER, reason=f"rollback {run_id}", run_id=run_id, token=token,
                take_over_stale=True,
            )
        else:
            maintenance_lock.acquire(
                self.paths.root, owner=LOCK_OWNER, reason=f"rollback {run_id}", run_id=run_id, token=token,
                take_over_token=token,
            )
        journal.append({"step": "rollback", "event": "start"})
        report: Dict[str, Any] = {"exact": 0, "kept_newer": 0, "skipped": []}
        snap_root = None
        if state.get("snapshot_manifest"):
            snap_root = (self.paths.root / Path(*PurePosixPath(state["snapshot_manifest"]).parts)).parent
        item_events = {e["id"]: e for e in journal.events() if e.get("step") == "manifests" and e.get("event") == "item"}
        try:
            with maintenance_lock.bypass(token):
                by_store: Dict[str, List[Dict[str, Any]]] = {}
                for action in plan["actions"]:
                    by_store.setdefault(action["store"], []).append(action)
                for step in reversed(DATA_STEPS):
                    actions = by_store.get(step)
                    if not actions:
                        continue
                    if step in TABLE_BY_NAME:
                        self._rollback_table(TABLE_BY_NAME[step], actions, report)
                    elif step == "task_registry":
                        self._rollback_tasks(actions, report, snap_root)
                    elif step in GADGET_STORES:
                        self._rollback_gadget(actions, report, state)
                    else:
                        self._rollback_manifests(actions, report, snap_root, item_events)
                    journal.append({"step": f"rollback:{step}", "event": "done"})
            state["status"] = "rolled_back"
            state["rolled_back_at"] = _now_iso()
            state["rollback_report"] = report
            self._save_state(state)
            maintenance_lock.release(self.paths.root, token)
            journal.append({"step": "rollback", "event": "done", **{k: v for k, v in report.items() if k != "skipped"}})
            return {"status": "rolled_back", "run_id": run_id, **report}
        except SimulatedCrash:
            raise
        except Exception as exc:
            journal.append({"step": "rollback", "event": "error", "error": f"{exc.__class__.__name__}: {exc}"})
            state["status"] = "needs_attention"
            state["error"] = f"rollback: {exc}"
            self._save_state(state)
            raise
        finally:
            _close_cached_connections(self.paths.root)

    def _rollback_table(self, spec: TableSpec, actions: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
        self._guard_mirror(spec)
        table = self._table(spec)
        with table.mutate() as records:
            index = {str(r.get("id")): pos for pos, r in enumerate(records)}
            for action in actions:
                if action["op"] == "rename_template":
                    old, new = action["id"], action["new_id"]
                    pos = index.get(new)
                    if pos is None:
                        if old in index:
                            continue  # never renamed
                        report["skipped"].append(f"{spec.name}/{new}: ถูกลบหลัง cutover")
                        continue
                    if old in index:
                        report["skipped"].append(f"{spec.name}/{old}: มี id เดิมเกิดขึ้นใหม่หลัง cutover (ไม่ย้อนชื่อ)")
                        continue
                    row = records[pos]
                    if row.get(LEGACY_ID_KEY) != old:
                        report["skipped"].append(f"{spec.name}/{new}: legacy_id ไม่ตรง")
                        continue
                    restored = _without(row, OWNER_KEY, LEGACY_ID_KEY)
                    restored["id"] = old
                    records[pos] = restored
                    report["exact" if row_hash(restored) == action["before_hash"] else "kept_newer"] += 1
                    continue
                pos = index.get(action["id"])
                if pos is None:
                    report["skipped"].append(f"{spec.name}/{action['id']}: ถูกลบหลัง cutover")
                    continue
                row = records[pos]
                if OWNER_KEY not in row:
                    continue  # never applied / already reverted
                if row.get(OWNER_KEY) != action["owner"]:
                    report["skipped"].append(f"{spec.name}/{action['id']}: channel_id ถูกเปลี่ยนหลัง cutover (ไม่แตะ)")
                    continue
                restored = _without(row, OWNER_KEY)
                records[pos] = restored
                report["exact" if row_hash(restored) == action["before_hash"] else "kept_newer"] += 1
        self._repair_mirror(spec, table)

    def _rollback_tasks(self, actions: List[Dict[str, Any]], report: Dict[str, Any], snap_root: Optional[Path]) -> None:
        path = self.paths.task_registry
        if not path.exists():
            return
        raw = path.read_bytes()
        tasks = json.loads(raw.decode("utf-8-sig"))
        changed = False
        for action in actions:
            task = tasks.get(action["id"]) if isinstance(tasks, dict) else None
            if not isinstance(task, dict):
                report["skipped"].append(f"task_registry/{action['id']}: หายไปหลัง cutover")
                continue
            if OWNER_KEY not in task:
                continue
            if task.get(OWNER_KEY) != action["owner"]:
                report["skipped"].append(f"task_registry/{action['id']}: channel_id ถูกเปลี่ยน (ไม่แตะ)")
                continue
            del task[OWNER_KEY]
            changed = True
            report["exact" if row_hash(task) == action["before_hash"] else "kept_newer"] += 1
        if not changed:
            return
        new = json.dumps(tasks, ensure_ascii=False, indent=2).encode("utf-8")
        original = snap_root / "03_Projects" / "task_registry.json" if snap_root else None
        if original is not None and original.exists():
            original_bytes = original.read_bytes()
            try:
                if json.loads(original_bytes.decode("utf-8-sig")) == tasks:
                    new = original_bytes  # byte-exact pre-state
            except json.JSONDecodeError:
                pass
        atomic_write_bytes(path, new, allowed_roots=self.allowed_roots)

    def _rollback_gadget(self, actions: List[Dict[str, Any]], report: Dict[str, Any], state: Dict[str, Any]) -> None:
        for rel, entry in _gadget_group_files(actions).items():
            path = self.paths.root / rel
            original = self._snapshot_file(state, rel)
            if original is None or sha256_bytes(original) != entry["before_hash"]:
                raise DriftError(f"Gadget/{rel}: snapshot เสีย (ไม่ rollback)")
            if not path.exists():
                report["skipped"].append(f"Gadget/{rel}: ไฟล์หายหลัง cutover")
                continue
            before = json.loads(original.decode("utf-8-sig"))
            raw = path.read_bytes()
            current = json.loads(raw.decode("utf-8-sig"))
            changed = False
            for change in entry["changes"]:
                try:
                    row = _gadget_selected(current, change["selector"])
                    old = _gadget_selected(before, change["selector"])
                except ValueError:
                    report["skipped"].append(f"Gadget/{rel}/{change['id']}: record หาย/ซ้ำหลัง cutover")
                    continue
                if row.get(OWNER_KEY) != change["owner"]:
                    if row.get(OWNER_KEY) != old.get(OWNER_KEY):
                        report["skipped"].append(f"Gadget/{rel}/{change['id']}: owner ถูกเปลี่ยนหลัง cutover")
                    continue
                if OWNER_KEY in old:
                    row[OWNER_KEY] = old[OWNER_KEY]
                else:
                    row.pop(OWNER_KEY, None)
                changed = True
            if changed:
                exact = canon(current) == canon(before)
                new = original if exact else json.dumps(current, ensure_ascii=False, indent=2).encode("utf-8")
                atomic_write_bytes(path, new, allowed_roots=self.allowed_roots)
                report["exact" if exact else "kept_newer"] += 1

    def _rollback_manifests(
        self, actions: List[Dict[str, Any]], report: Dict[str, Any], snap_root: Optional[Path],
        item_events: Mapping[str, Mapping[str, Any]],
    ) -> None:
        for action in actions:
            name = action["id"]
            path = self.paths.manifest_path(name)
            if not path.exists():
                report["skipped"].append(f"manifests/{name}: ไฟล์หายหลัง cutover")
                continue
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            data = json.loads(text.lstrip("﻿"))
            if not isinstance(data, dict) or OWNER_KEY not in data:
                continue
            if data.get(OWNER_KEY) != action["owner"]:
                report["skipped"].append(f"manifests/{name}: channel_id ถูกเปลี่ยน (ไม่แตะ)")
                continue
            event = item_events.get(name) or {}
            original = snap_root / "03_Projects" / name / "project.json" if snap_root else None
            if event.get("after_hash") == sha256_bytes(raw) and original is not None and original.exists() \
                    and sha256_file(original) == action["before_hash"]:
                new = original.read_bytes()
                report["exact"] += 1
            else:
                segment = event.get("segment")
                if segment and text.count(segment) == 1:
                    new_text = text.replace(segment, "", 1)
                else:
                    without = _without(data, OWNER_KEY)
                    new_text = json.dumps(without, ensure_ascii=False, indent=2)
                check = json.loads(new_text.lstrip("﻿"))
                if check != _without(data, OWNER_KEY):
                    raise MigrationError(f"manifests/{name}: ถอด channel_id แล้วเนื้อหาเปลี่ยน (หยุด)")
                new = new_text.encode("utf-8")
                report["exact" if sha256_bytes(new) == action["before_hash"] else "kept_newer"] += 1
            atomic_write_bytes(path, new, allowed_roots=self.allowed_roots)

    # -- snapshot restore (production rollback of last resort) --------------------------
    def restore_snapshot_in_place(self) -> Dict[str, Any]:
        """Put the pre-apply snapshot back -- ONLY while the data still equals
        the post-apply fingerprint (no newer work would be lost)."""
        state = self.current_run()
        if not state or state.get("status") != "applied" or not state.get("post_fingerprint"):
            raise MigrationError("restore snapshot ได้เฉพาะรอบที่ apply สำเร็จและมี fingerprint หลัง apply")
        now = fingerprint(self.paths)
        if now != state["post_fingerprint"]:
            raise MigrationError("มีข้อมูลใหม่หลัง cutover (fingerprint ไม่ตรง) — ห้ามคืน snapshot ทับ ให้ใช้ --rollback")
        manifest_path = self.paths.root / Path(*PurePosixPath(state["snapshot_manifest"]).parts)
        manifest = _load_manifest(manifest_path)
        snap_dir = manifest_path.parent
        token = state["token"]
        maintenance_lock.acquire(self.paths.root, owner=LOCK_OWNER, reason=f"restore snapshot {state['run_id']}", run_id=state["run_id"], token=token)
        journal = self._journal(state["run_id"])
        journal.append({"step": "restore_snapshot", "event": "start"})
        try:
            with maintenance_lock.bypass(token):
                _close_cached_connections(self.paths.root)
                for entry in manifest["files"]:
                    rel = PurePosixPath(entry["rel"])
                    source = snap_dir / Path(*rel.parts)
                    if sha256_file(source) != entry["sha256"]:
                        raise MigrationError(f"ไฟล์ใน snapshot เสีย: {entry['rel']}")
                for entry in manifest["files"]:
                    rel = PurePosixPath(entry["rel"])
                    source = snap_dir / Path(*rel.parts)
                    target = self.paths.root / Path(*rel.parts)
                    if entry["kind"] == "sqlite":
                        src = sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True)
                        dst = sqlite3.connect(str(target), timeout=5)
                        try:
                            src.backup(dst)
                            if _integrity(dst) != "ok":
                                raise MigrationError(f"integrity_check หลังคืน {entry['rel']} ไม่ผ่าน")
                        finally:
                            src.close()
                            dst.close()
                    else:
                        atomic_write_bytes(target, source.read_bytes(), allowed_roots=self.allowed_roots)
            after = fingerprint(self.paths)
            if after != state["pre_fingerprint"]:
                raise MigrationError("คืน snapshot แล้ว fingerprint ไม่ตรงก่อน apply")
            state["status"] = "restored"
            state["restored_at"] = _now_iso()
            self._save_state(state)
            maintenance_lock.release(self.paths.root, token)
            journal.append({"step": "restore_snapshot", "event": "done"})
            return {"status": "restored", "run_id": state["run_id"], "files": len(manifest["files"])}
        except Exception as exc:
            journal.append({"step": "restore_snapshot", "event": "error", "error": str(exc)})
            state["status"] = "needs_attention"
            state["error"] = f"restore: {exc}"
            self._save_state(state)
            raise
        finally:
            _close_cached_connections(self.paths.root)

    def release_stale_lock(self) -> Dict[str, Any]:
        lock = maintenance_lock.read_lock(self.paths.root)
        if lock is None:
            return {"status": "no_lock"}
        if not lock.get("stale"):
            raise MigrationError("lock ยังไม่ stale (process เจ้าของยังทำงาน หรืออยู่คนละเครื่อง) — ไม่ปลด")
        state = self.current_run()
        if state and state.get("status") in ("in_progress", "needs_attention") and state.get("token") == lock.get("token"):
            raise MigrationError("lock นี้เป็นของ migration ที่ยังค้าง ใช้ --resume หรือ --rollback แทนการปลด")
        if not maintenance_lock.release(self.paths.root, str(lock.get("token"))):
            raise MigrationError("ปลด lock ไม่สำเร็จ")
        return {"status": "released", "lock": {k: lock.get(k) for k in ("owner", "pid", "run_id", "started_at")}}


NOT_TOUCHED = [
    "01_Raw/, 00_Inbox/, 02_Assets/ (วัตถุดิบ/asset ร่วม)",
    "04_Exports/ และ 05_Covers_Thumbnails/ (ไฟล์ MP4/ปก — ไม่ย้าย/ไม่เปลี่ยนชื่อ/ไม่แก้เนื้อหา)",
    "CapCut drafts (draft_content.json / .cloud_cache_*)",
    "ไฟล์อื่นใน 03_Projects/<project>/ นอกจาก project.json (ไม่สร้าง .bak ใหม่ด้วย)",
    "_HyperFrames_Studio/ (compositions/kit)",
    "แถวที่ไม่ทราบเจ้าของ/ขัดแย้ง (คง legacy ไว้จนกว่าจะ --assign)",
    "แถวที่มี channel_id อยู่แล้ว",
    "_json_mirror_state แถวของเครื่องอื่น (เฉื่อย)",
    "03_Projects/omnicut.db (ไฟล์ 0 byte ไม่มีโค้ดใช้)",
    "GadgetMedia ที่ไม่ได้ --assign (คง unknown); stage/artifact/identity เดิมไม่เปลี่ยน และไม่ย้ายไฟล์",
    "tiktok_pending / tiktok_ignored (ต้องรู้บัญชีต้นทาง)",
]


# --------------------------------------------------------------------------- reports


def _fmt_owner_counts(counts: Mapping[str, int]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "0"


def render_report_markdown(result: Mapping[str, Any]) -> str:
    plan = result["plan"]
    pre = result["preflight"]
    lines: List[str] = []
    lines.append("# Multi-channel migration — dry-run report (P2.3)")
    lines.append("")
    lines.append(f"- **สร้างเมื่อ:** {result['generated_at']}")
    lines.append(f"- **root:** `{result['root']}`")
    lines.append(f"- **plan_hash:** `{plan['plan_hash']}` (ต้องใช้กับ `--apply --expect-plan`)")
    lines.append(f"- **ตัวเลือก:** rename_templates={plan['options']['rename_templates']}, legacy_owner={plan['options']['legacy_owner']}, assignments={len(plan['assignments'])}")
    ev = plan["evidence"]
    lines.append(f"- **registry:** มีไฟล์={plan['registry']['exists']} ช่อง=" + ", ".join(f"{c['id']}({c['status']}, {c['handle']})" for c in plan["registry"]["channels"]))
    lines.append(f"- **หลักฐานบัญชีจากโพสต์:** " + (", ".join(f"{h}={n}" for h, n in ev["post_handles"].items()) or "ไม่มี"))
    lines.append(f"- **เจ้าของข้อมูลเดิม (legacy cohort):** {ev['legacy_owner']} — {ev['legacy_owner_reason_th']}")
    lines.append(f"- **แถวที่จะเขียน:** {len(plan['actions'])} · มี channel_id อยู่แล้ว {plan['already_owned']}")
    lines.append("")
    lines.append("## 1. Preflight")
    lines.append("")
    lines.append(f"blockers ที่ไม่ผ่าน: **{pre['blockers']}**")
    lines.append("")
    lines.append("| ตรวจ | ระดับ | ผล | รายละเอียด |")
    lines.append("|---|---|---|---|")
    for c in pre["checks"]:
        lines.append(f"| {c['name']} | {c['level']} | {'ผ่าน' if c['ok'] else 'ไม่ผ่าน'} | {c['message']} |")
    lines.append("")
    lines.append("## 2. ต่อ store")
    lines.append("")
    lines.append("| store | ทั้งหมด | มีเจ้าของแล้ว | จะ backfill | unknown | conflict | deferred | unsupported | เหตุผล unknown/conflict |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for name, s in plan["stores"].items():
        reasons = ", ".join(f"{reason_text(k)} ({k})={v}" for k, v in sorted(s.get("reasons", {}).items()))
        lines.append(
            f"| {name} | {s['total']} | {s['already']} | {_fmt_owner_counts(s['backfill'])} | {s['unknown']} | {s['conflict']} | {s['deferred']} | {s['unsupported']} | {reasons} |"
        )
    lines.append("")
    lines.append("## 3. รายการที่ต้องให้เจ้าของตัดสิน (unknown / conflict / deferred / unsupported)")
    lines.append("")
    pending = [d for d in plan["decisions"] if d["status"] != "backfill"]
    if not pending:
        lines.append("ไม่มี")
    else:
        lines.append("| store | id | สถานะ | เหตุผล | รายละเอียด | ควรทำ |")
        lines.append("|---|---|---|---|---|---|")
        for d in pending:
            detail = canon(d.get("detail", {})) if d.get("detail") else ""
            if len(detail) > 160:
                detail = detail[:157] + "..."
            lines.append(f"| {d['store']} | `{d['id']}` | {d['status']} | {d['reason_th']} | {detail} | {d.get('suggested_action', '')} |")
    lines.append("")
    lines.append("## 4. การ backfill ตามหลักฐาน (สรุปตามเหตุผล)")
    lines.append("")
    summary: Dict[Tuple[str, str, str], int] = {}
    for d in plan["decisions"]:
        if d["status"] == "backfill":
            key = (d["store"], d["owner"], d["reason"])
            summary[key] = summary.get(key, 0) + 1
    lines.append("| store | owner | เหตุผล | แถว |")
    lines.append("|---|---|---|---|")
    for (store, owner, reason), n in sorted(summary.items()):
        lines.append(f"| {store} | {owner} | {reason_text(reason)} | {n} |")
    lines.append("")
    lines.append("## 5. ชุดที่จะเขียน (estimated write set)")
    lines.append("")
    for f in result["write_set"]["files"]:
        lines.append(f"- {f}")
    lines.append(f"- snapshot โดยประมาณ {result['write_set']['snapshot_estimate_bytes'] // 1024} KB")
    lines.append("")
    lines.append("## 6. สิ่งที่ไม่แตะ")
    lines.append("")
    for item in result["not_touched"]:
        lines.append(f"- {item}")
    inv = result["inventory"]
    lines.append("")
    lines.append("## 7. Inventory ที่อ่านได้")
    lines.append("")
    lines.append(f"- ตาราง: " + ", ".join(f"{k}={v}" for k, v in inv["table_counts"].items()))
    lines.append(f"- project.json {inv['manifests']} ไฟล์; โฟลเดอร์ไม่มี manifest: {', '.join(inv['project_dirs_without_manifest']) or '-'}; ข้ามโฟลเดอร์ระบบ: {', '.join(inv['skipped_project_dirs']) or '-'}")
    lines.append(f"- task_registry {inv['tasks']} งาน; GadgetMedia projects {inv['gadget_media_projects']}; index มี={inv['gadget_media_index_exists']}")
    lines.append(f"- integrity: {inv['integrity']}")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_report(result: Mapping[str, Any], report_path: Path) -> Tuple[Path, Path]:
    """Write ``<stem>.md`` + ``<stem>.json`` next to ``report_path`` (explicit path, atomic)."""
    report_path = Path(os.path.abspath(report_path))
    stem = report_path.with_suffix("") if report_path.suffix.lower() in (".md", ".json") else report_path
    md = stem.with_name(stem.name + ".md")
    js = stem.with_name(stem.name + ".json")
    allowed = [report_path.parent]
    atomic_write_bytes(md, render_report_markdown(result).encode("utf-8"), allowed_roots=allowed)
    atomic_write_bytes(js, json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"), allowed_roots=allowed)
    return md, js


def tcp_probe(host: str = "127.0.0.1", port: int = 8000, timeout: float = 0.5) -> Callable[[], bool]:
    def probe() -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    return probe


def rehearse_restore(root: Path, workdir: Path) -> Dict[str, Any]:
    """Plan §8.1 step 4–5: snapshot ``root`` (read-only) into ``workdir/snapshot``,
    restore into ``workdir/restored`` and verify counts/ids/hashes."""
    paths = MigrationPaths.for_root(root)
    workdir = Path(os.path.abspath(workdir))
    if _is_within(workdir, paths.root):
        raise MigrationError("workdir ของการซ้อม restore ต้องอยู่นอก root (กันเขียนลงข้อมูลจริง)")
    snap = workdir / "snapshot"
    target = workdir / "restored"
    if snap.exists() or target.exists():
        raise MigrationError(f"workdir ต้องว่าง: {workdir}")
    manifest = create_snapshot(paths, snap, allowed_roots=[workdir])
    restore_snapshot(snap / "manifest.json", target)
    verdict = verify_restore(snap / "manifest.json", target)
    verdict["files"] = len(manifest["files"])
    verdict["snapshot"] = str(snap)
    verdict["restored_root"] = str(target)
    return verdict
