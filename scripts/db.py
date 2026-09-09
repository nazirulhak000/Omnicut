"""
SQLite backing store shared by ProductStore and PostLog.

Design
------
Both stores keep their existing public contract: `_load()` returns the full
list of records as plain dicts, `_save(records)` replaces the full list.
Callers (including a few external ones -- api_videos.py, backfill_product_codes.py
-- that reach into `ProductStore._load()`/`_save()` directly) mutate those
dicts freely and pass the whole list back to `_save()`. That rules out a
normalized, column-per-field schema without a rewrite of every call site, so
each table here is a simple "one row per record, keyed by id, full record as
a JSON blob" document store -- SQLite gives us a real transaction around the
read-modify-write cycle (fixing the lost-update race) and indexed lookups by
id (fixing the O(n) full-file rewrite), without forcing a shape change on
any caller.

One extra column per table (`updated_at`) is kept in sync with the blob
purely as an index for the handful of hot lookups (sort-by-updated_at). It
is NOT a second source of truth -- the JSON blob column is authoritative,
this is just an indexed shadow of a field already inside it. There is no
`url` column or index here: duplicate-URL detection (e.g. ProductStore.add)
is done with a Python-side scan over the loaded records instead.

JSON-file mirroring
--------------------
Several existing tests seed data by writing straight to `products.json` /
`post_log.json` on disk (bypassing the store's own `add()`/`add_post()`)
and later assert against that same file's contents. To keep that contract
alive without special-casing tests, `_load()` re-imports the JSON file into
SQLite whenever the file's mtime is newer than the last import recorded in
the DB (see `sync_from_json_if_newer`), and `_save()` writes the DB AND
re-serializes the full JSON file (atomic tmp+replace, exactly as before)
in the same call. So: SQLite is the real transactional store (source of
truth for concurrent writers), the JSON file is a live mirror kept for
back-compat, hand-editability, and as the offline backup the task asked
for.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, TypeVar

_T = TypeVar("_T")

# One SQLite connection per (thread, db path). sqlite3 connections are not
# safe to share across threads; FastAPI's threadpool means every request can
# land on a different thread, so this is not optional.
_local = threading.local()

# Process-wide lock guarding the *file-level* import-from-JSON step (the
# db path -> table creation -> mtime check -> import) so two threads racing
# to open a brand-new DB file don't both try to create the schema/import
# at once. The actual read-modify-write transaction safety comes from
# SQLite's own locking (WAL + busy_timeout + `BEGIN IMMEDIATE`), not this.
_setup_lock = threading.Lock()

# Paths for which WAL mode has already been switched on. `PRAGMA
# journal_mode=WAL` itself needs a momentary exclusive lock on the database
# -- unlike a normal write, it does NOT respect busy_timeout (confirmed: it
# raises "database is locked" immediately, not after the timeout, if another
# connection is mid-transaction). So it must run exactly once per db file,
# from a connection opened before any concurrent writer exists, never
# re-issued by every new per-thread connection.
_wal_enabled_paths: set = set()

# Was 30_000. Found a real deadlock risk: DocumentTable.mutate() (see below)
# holds one SQLite write transaction open across its ENTIRE `with` block body
# -- by design, per its own docstring, that transaction IS the mutual-
# exclusion mechanism. ProductStore.update_angle_status() calls
# ExportRegistry.get(export_id) *inside* that block; ExportRegistry shares
# the same store.db file, and on the same thread `_connection_for()` hands
# back the SAME cached connection (keyed by resolved db path, not by table).
# If that nested call's own _sync_from_json_if_newer() decides a re-import is
# due, it tries to open a second write transaction on a connection that's
# already mid-transaction -- at 30s busy_timeout x 3 retries, a stall there
# hung every request touching this file for ~90-110s and read as the whole
# backend being offline. Shortening this doesn't fix the nesting (that needs
# its own fix -- tracked separately), but it turns a 100s silent hang into a
# ~5s failure the caller can see and retry, which is the more urgent half.
_BUSY_TIMEOUT_MS = 5_000

# `PRAGMA busy_timeout` already makes SQLite itself retry a blocked
# BEGIN IMMEDIATE for up to _BUSY_TIMEOUT_MS before giving up -- but under a
# burst of concurrent requests (several threads' DocumentTable.load() calls
# noticing the JSON mirror changed at once, see _sync_from_json_if_newer's
# docstring) that window can still be exhausted, and the caller sees a raw
# "database is locked" OperationalError. Retrying the whole operation a
# couple more times, each after its own fresh busy_timeout wait, absorbs
# that without ever needing to touch the locking design itself.
_LOCK_RETRY_ATTEMPTS = 3


def _retry_on_locked(fn: Callable[[], _T]) -> _T:
    for attempt in range(_LOCK_RETRY_ATTEMPTS):
        try:
            return fn()
        except sqlite3.OperationalError as err:
            if "database is locked" not in str(err) or attempt == _LOCK_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(0.2 * (attempt + 1))
    raise AssertionError("unreachable")  # pragma: no cover


def _ensure_wal_mode(db_path: Path, key: str) -> None:
    if key in _wal_enabled_paths:
        return
    with _setup_lock:
        if key in _wal_enabled_paths:
            return
        db_path.parent.mkdir(parents=True, exist_ok=True)
        setup_conn = sqlite3.connect(str(db_path), timeout=_BUSY_TIMEOUT_MS / 1000)
        try:
            setup_conn.execute("PRAGMA journal_mode=WAL")
        finally:
            setup_conn.close()
        _wal_enabled_paths.add(key)


def _connection_for(db_path: Path) -> sqlite3.Connection:
    cache = getattr(_local, "conns", None)
    if cache is None:
        cache = {}
        _local.conns = cache

    key = str(db_path.resolve())
    conn = cache.get(key)
    if conn is not None:
        return conn

    db_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_wal_mode(db_path, key)
    conn = sqlite3.connect(str(db_path), timeout=_BUSY_TIMEOUT_MS / 1000, isolation_level=None)
    # busy_timeout is a per-connection, non-exclusive pragma -- safe to set
    # on every new connection, unlike journal_mode above.
    conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys=ON")
    cache[key] = conn
    return conn


def _ensure_table(conn: sqlite3.Connection, table: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id TEXT PRIMARY KEY,
            updated_at TEXT,
            data TEXT NOT NULL
        )
        """
    )
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_updated_at ON {table}(updated_at)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS _json_mirror_state (
            source_path TEXT PRIMARY KEY,
            table_name TEXT NOT NULL,
            last_imported_mtime_ns INTEGER NOT NULL
        )
        """
    )


def _updated_at_of(record: Dict[str, Any]) -> str:
    value = record.get("updated_at") or record.get("posted_at") or record.get("created_at") or ""
    return str(value)


def _id_of(record: Dict[str, Any]) -> str:
    rid = record.get("id")
    if rid is None:
        raise ValueError("record has no 'id' field -- cannot store it")
    return str(rid)


class DocumentTable:
    """A JSON-document table: full-list load/save, keyed by each record's 'id'.

    `db_path` and `json_path` are read fresh on every call (never cached at
    construction) because tests monkeypatch the module-level STORE_PATH /
    LOG_PATH Path objects that this is derived from -- the store must follow
    those patches per-call, not capture a stale value at import time.
    """

    def __init__(self, table: str, db_path_fn, json_path_fn):
        self._table = table
        self._db_path_fn = db_path_fn
        self._json_path_fn = json_path_fn

    # -- setup -----------------------------------------------------------
    def _conn(self) -> sqlite3.Connection:
        db_path = self._db_path_fn()
        conn = _connection_for(db_path)
        with _setup_lock:
            _ensure_table(conn, self._table)
        return conn

    def _sync_from_json_if_newer(self, conn: sqlite3.Connection) -> None:
        """Import the JSON file into SQLite if it changed since last import.

        Covers: (a) first run against a JSON file left over from before this
        migration, (b) tests/tools that write the JSON file directly and
        expect the store to pick it up on the next read.

        Only the cheap "do we even need to import?" check -- a SELECT
        against `_json_mirror_state` plus an mtime comparison -- runs under
        `_setup_lock`. The import itself (JSON read + `BEGIN IMMEDIATE` +
        DELETE + re-INSERT) runs WITHOUT that lock. It used to run the
        *whole* check-and-import under `_setup_lock`, which is one
        process-wide lock shared by every DocumentTable this module manages
        (products, post_log, export_registry, schedule_queue,
        schedule_templates -- all in the same store.db file, see the module
        docstring). That meant any one table noticing its JSON mirror had
        changed would block every other table's load()/mutate() for as long
        as its own `BEGIN IMMEDIATE` took to acquire SQLite's write lock --
        up to _BUSY_TIMEOUT_MS (5s). A burst of concurrent requests each
        noticing a mirror change at once could stall the entire backend for
        several seconds even though only one table's data was changing.

        Safe without the lock: `BEGIN IMMEDIATE` below is itself a real
        SQLite write-lock acquisition, and SQLite locks the whole database
        file, not per table -- so two importers, whether for the same table
        or two different ones, still cannot run their DELETE+re-INSERT at
        the same time; the second one simply blocks (on busy_timeout) until
        the first commits. The only thing the outer lock bought beyond that
        was deciding *whether* to import without two threads duplicating the
        same work, so that decision is re-checked once more right after
        `BEGIN IMMEDIATE`, against a fresh stat/read done only once the
        write lock is actually held -- if another thread's import (or an
        unrelated writer's own commit) already landed while this call
        waited for the lock, this one no-ops instead of blindly re-applying
        whatever (possibly now-stale) file content it noticed before
        acquiring it.
        """
        json_path: Path = self._json_path_fn()
        if not json_path.exists():
            return

        try:
            mtime_ns = json_path.stat().st_mtime_ns
        except OSError:
            return

        source_key = str(json_path.resolve())

        def _already_imported(as_of_mtime_ns: int) -> bool:
            row = conn.execute(
                "SELECT last_imported_mtime_ns FROM _json_mirror_state WHERE source_path = ?",
                (source_key,),
            ).fetchone()
            return row is not None and row[0] >= as_of_mtime_ns

        with _setup_lock:
            if _already_imported(mtime_ns):
                return  # already imported this version (or a newer one)

        # No lock held past this point. BEGIN IMMEDIATE below (SQLite's own
        # whole-file write lock) is what serializes the actual import now.
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Re-stat and re-check now that the write lock is held -- both
            # the file and the marker could have moved while this call was
            # waiting to acquire it above.
            try:
                fresh_mtime_ns = json_path.stat().st_mtime_ns
            except OSError:
                conn.execute("COMMIT")
                return
            if _already_imported(fresh_mtime_ns):
                conn.execute("COMMIT")
                return

            try:
                raw = json_path.read_text(encoding="utf-8")
                records = json.loads(raw) if raw.strip() else []
            except (OSError, json.JSONDecodeError):
                conn.execute("COMMIT")
                return
            if not isinstance(records, list):
                conn.execute("COMMIT")
                return

            conn.execute(f"DELETE FROM {self._table}")
            for record in records:
                if not isinstance(record, dict) or "id" not in record:
                    continue
                conn.execute(
                    f"INSERT OR REPLACE INTO {self._table} (id, updated_at, data) VALUES (?, ?, ?)",
                    (_id_of(record), _updated_at_of(record), json.dumps(record, ensure_ascii=False)),
                )
            conn.execute(
                "INSERT INTO _json_mirror_state (source_path, table_name, last_imported_mtime_ns) "
                "VALUES (?, ?, ?) ON CONFLICT(source_path) DO UPDATE SET last_imported_mtime_ns = excluded.last_imported_mtime_ns",
                (source_key, self._table, fresh_mtime_ns),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    # -- public: load/save (mirrors ProductStore/PostLog._load/_save) ----
    def load(self) -> List[Dict[str, Any]]:
        conn = self._conn()

        def _do():
            self._sync_from_json_if_newer(conn)
            rows = conn.execute(f"SELECT data FROM {self._table}").fetchall()
            return [json.loads(r[0]) for r in rows]

        return _retry_on_locked(_do)

    def save(self, records: Iterable[Dict[str, Any]]) -> None:
        records = list(records)
        conn = self._conn()
        with _setup_lock:
            _ensure_table(conn, self._table)

        def _do():
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(f"DELETE FROM {self._table}")
                for record in records:
                    conn.execute(
                        f"INSERT OR REPLACE INTO {self._table} (id, updated_at, data) VALUES (?, ?, ?)",
                        (_id_of(record), _updated_at_of(record), json.dumps(record, ensure_ascii=False)),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        _retry_on_locked(_do)
        self._write_json_mirror(conn)

    def _write_json_mirror(self, conn: sqlite3.Connection) -> None:
        """Re-serialize the full JSON mirror file from the CURRENT database
        state (a fresh SELECT, not whatever list a caller happened to hold),
        so that if two writers commit close together, the mirror converges
        on whichever commit actually landed last in SQLite.

        Guarded by the SAME process-wide lock (_setup_lock) that
        _sync_from_json_if_newer uses for its whole check-then-import
        sequence, and the whole read-DB -> write-file -> record-marker
        sequence here runs under that one lock too. This is deliberate and
        load-bearing, not just belt-and-suspenders against the Windows
        PermissionError on a racing Path.replace(): without it, two mirror
        writers can interleave with a sync-from-json import like this --

            writer A: SELECT (sees 7 rows, is about to write 7-row file)
            writer B: commits an 8th row, writes an 8-row file (mtime T2)
            writer A: (delayed) writes its stale 7-row file (mtime T3 > T2),
                      records T3 as "last imported" for this exact file
            reader:   _mutate()/load() calls _sync_from_json_if_newer,
                      sees file mtime T3 > whatever was recorded before
                      writer A ran, re-imports the 7-row file, DELETEs and
                      re-INSERTs the table -- writer B's 8th row is now
                      gone from SQLite itself, not just the mirror.

        Holding _setup_lock across the read+write+marker-update here makes
        that interleaving impossible: a sync-from-json cannot start
        checking/importing while a mirror write is still in the middle of
        reading DB state and writing the file (and vice versa), so the
        marker recorded always matches content that is at least as new as
        whatever SQLite held at the moment of that same lock acquisition.
        """
        with _setup_lock:
            rows = conn.execute(f"SELECT data FROM {self._table}").fetchall()
            current_records = [json.loads(r[0]) for r in rows]

            json_path: Path = self._json_path_fn()
            json_path.parent.mkdir(parents=True, exist_ok=True)
            # Per-thread tmp name so concurrent mirror writes for DIFFERENT
            # tables sharing this lock momentarily (rare, but _setup_lock is
            # shared across tables) never collide on the same tmp path.
            tmp = json_path.parent / f"{json_path.stem}.{threading.get_ident()}.json.tmp"
            try:
                tmp.write_text(json.dumps(current_records, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(json_path)
            finally:
                tmp.unlink(missing_ok=True)

            # Record that we just wrote this exact file, so a subsequent
            # load() doesn't immediately think the file is "newer" (e.g.
            # filesystems with coarse mtime resolution) and re-import it
            # over itself.
            try:
                mtime_ns = json_path.stat().st_mtime_ns
                source_key = str(json_path.resolve())
                _retry_on_locked(lambda: conn.execute(
                    "INSERT INTO _json_mirror_state (source_path, table_name, last_imported_mtime_ns) "
                    "VALUES (?, ?, ?) ON CONFLICT(source_path) DO UPDATE SET last_imported_mtime_ns = excluded.last_imported_mtime_ns",
                    (source_key, self._table, mtime_ns),
                ))
            except OSError:
                pass

    # -- transaction helper for read-modify-write call sites --------------
    def mutate(self):
        """Context manager: yields the full record list inside one SQLite
        write transaction (BEGIN IMMEDIATE ... COMMIT), and persists it (DB +
        JSON mirror) on clean exit. This is the fix for the lost-update race:
        the load and the save now happen under the same lock, held for the
        whole read-modify-write, instead of a `threading.Lock` that only
        wrapped `_save()`.

        `BEGIN IMMEDIATE` acquires SQLite's write lock up front (rather than
        on first write), so a second concurrent `mutate()` blocks at the
        start of its transaction -- on `load()`, effectively -- until this
        one commits, exactly like a real transactional read-modify-write
        should.
        """
        return _MutateCtx(self)


class _MutateCtx:
    def __init__(self, table: "DocumentTable"):
        self._table = table
        self._conn: sqlite3.Connection | None = None
        self._records: List[Dict[str, Any]] | None = None
        self._snapshot: str | None = None

    def __enter__(self) -> List[Dict[str, Any]]:
        t = self._table
        conn = t._conn()
        t._sync_from_json_if_newer(conn)
        conn.execute("BEGIN IMMEDIATE")
        self._conn = conn
        rows = conn.execute(f"SELECT data FROM {t._table}").fetchall()
        self._records = [json.loads(r[0]) for r in rows]
        # Remember what was read so __exit__ can tell a real mutation from a
        # block that turned out to change nothing. Some callers hold this
        # transaction only because they MIGHT write -- product_store's
        # reconcile_existing_projects() runs on every product listing, and
        # rewriting every row plus the JSON mirror each time the UI polls
        # would be pure churn.
        self._snapshot = json.dumps(self._records, ensure_ascii=False, sort_keys=True)
        return self._records

    def __exit__(self, exc_type, exc, tb) -> bool:
        conn = self._conn
        assert conn is not None
        if exc_type is not None:
            conn.execute("ROLLBACK")
            return False

        t = self._table
        records = self._records or []
        if json.dumps(records, ensure_ascii=False, sort_keys=True) == self._snapshot:
            # Nothing changed. Close the transaction without touching the
            # table; the write lock was held for the duration either way, so
            # a concurrent writer still could not have raced this block.
            conn.execute("COMMIT")
            return False

        try:
            conn.execute(f"DELETE FROM {t._table}")
            for record in records:
                conn.execute(
                    f"INSERT OR REPLACE INTO {t._table} (id, updated_at, data) VALUES (?, ?, ?)",
                    (_id_of(record), _updated_at_of(record), json.dumps(record, ensure_ascii=False)),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        t._write_json_mirror(conn)
        return False
