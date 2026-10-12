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

Mirror atomicity contract (multi-channel P2.4a)
-----------------------------------------------
Every writer (``save``/``mutate``/``scoped_mutate``) serializes the table,
replaces the mirror file AND records its change token in
``_json_mirror_state`` while it still holds its own ``BEGIN IMMEDIATE``
write lock, and only then COMMITs.  An importer also needs that write lock
to import, so whenever an importer holds the lock and sees
``token(file) != marker`` the file was NOT produced by a committed writer:
it is either an external edit (imported -- the feature above) or an
uncommitted publication. A durable ``<mirror>.publish-pending`` intent
distinguishes these: its token matching the DB marker proves COMMIT;
otherwise the file is quarantined and rebuilt from committed SQLite rows.
It can never be a stale serialization of an older state, which is what
used to happen when the file + marker were written after COMMIT (another
process -- or another thread past its first check -- imported a stale
mirror in that gap and DELETEd rows committed meanwhile).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, TypeVar

# Maintenance (read-only) lock, multi-channel P2.3: while
# <root>/_Docs/.maintenance.lock exists, writes refuse with
# MaintenanceModeError and the JSON-mirror auto-import is skipped.
from scripts import maintenance_lock as _maintenance

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

# Windows: os.replace() onto a mirror that another handle holds open without
# FILE_SHARE_DELETE (a reader's stat/open, an indexer, antivirus) fails with
# PermissionError.  The writer retries with short exponential backoff while
# it still holds the db write lock (worst case ~1.3 s, far below
# _BUSY_TIMEOUT_MS); if every attempt fails the whole write is rolled back
# and the PermissionError surfaces -- DB, mirror and marker stay unchanged.
_MIRROR_REPLACE_ATTEMPTS = 8
_MIRROR_REPLACE_BACKOFF_S = 0.01
_MIRROR_REPLACE_BACKOFF_MAX_S = 0.25

# SAVEPOINT a writer opens just before flushing, so a failure after the
# mirror was already replaced can undo the rows yet keep the write lock long
# enough to re-publish the mirror of the restored state (see
# DocumentTable._flush_publish_commit).
_PUBLISH_SAVEPOINT = "omnicut_mirror_publish"


class NestedTransactionError(sqlite3.OperationalError):
    """A second write transaction was attempted on a connection that is
    already inside one (same thread + same db file share one connection --
    see ``_connection_for``).  Subclasses ``sqlite3.OperationalError`` so
    existing ``except sqlite3.OperationalError`` handlers keep working, but
    raised up front with a clear message instead of SQLite's own
    "cannot start a transaction within a transaction".

    Fix at the call site: never call another store's write from inside a
    ``mutate()``/``scoped_mutate()`` block -- collect the work and run it
    after the block commits (staged work), or fetch reads before opening it.
    """


class ChannelIsolationError(RuntimeError):
    """A scoped mutation tried to add/change/delete a row outside its channel
    scope (or change a row's owner).  The transaction is rolled back with
    zero rows written and the JSON mirror untouched.
    """

    code = "channel_isolation_violation"

    def __init__(self, message: str, *, record_ids: Iterable[str] = ()):
        super().__init__(message)
        self.record_ids = sorted(str(r) for r in record_ids)


_MISSING = object()


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


def _mirror_token(json_path: Path) -> int:
    """A change token for a JSON mirror: mtime combined with size.

    mtime alone misses an edit that lands inside the same filesystem
    timestamp tick, which on Windows is coarse enough to hit in practice --
    rewriting a record's path to another of a different length was reported
    as an intermittent "stale index" failure. Folding the size in catches
    those; the pair is compared for equality rather than ordering, since a
    newer file can be smaller.
    """
    stat = json_path.stat()
    # Kept inside SQLite's signed 64-bit INTEGER: shifting mtime_ns left
    # overflows it outright, so the two are mixed and masked instead.
    return ((stat.st_mtime_ns * 1_000_003) ^ (stat.st_size * 2_654_435_761)) & 0x7FFF_FFFF_FFFF_FFFF


def _upsert_mirror_marker(conn: sqlite3.Connection, source_key: str, table: str, token: int) -> None:
    conn.execute(
        "INSERT INTO _json_mirror_state (source_path, table_name, last_imported_mtime_ns) "
        "VALUES (?, ?, ?) ON CONFLICT(source_path) DO UPDATE SET last_imported_mtime_ns = excluded.last_imported_mtime_ns",
        (source_key, table, token),
    )


def _replace_mirror_file(tmp: Path, json_path: Path) -> None:
    """``tmp.replace(json_path)`` with retry on Windows PermissionError (see
    _MIRROR_REPLACE_ATTEMPTS).  os.replace is atomic: on failure the old
    mirror is left exactly as it was."""
    for attempt in range(_MIRROR_REPLACE_ATTEMPTS):
        try:
            tmp.replace(json_path)
        except PermissionError:
            if attempt == _MIRROR_REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(min(_MIRROR_REPLACE_BACKOFF_S * (2 ** attempt), _MIRROR_REPLACE_BACKOFF_MAX_S))
        else:
            # Per-thread count of successful mirror replaces: lets a failing
            # writer tell exactly whether its mirror was already swapped.
            _local.mirror_replaces = getattr(_local, "mirror_replaces", 0) + 1
            return


def _mirror_replace_count() -> int:
    return getattr(_local, "mirror_replaces", 0)


def _mirror_intent_path(json_path: Path) -> Path:
    return json_path.with_name(json_path.name + ".publish-pending")


def _write_mirror_intent(json_path: Path, table: str, token: int) -> None:
    intent_path = _mirror_intent_path(json_path)
    intent_tmp = intent_path.with_name(f"{intent_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with intent_tmp.open("w", encoding="utf-8") as intent_file:
            json.dump({"source_path": str(json_path.resolve()), "table_name": table, "token": token}, intent_file)
            intent_file.flush()
            os.fsync(intent_file.fileno())
        intent_tmp.replace(intent_path)
    finally:
        intent_tmp.unlink(missing_ok=True)


def _rollback_quietly(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass


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

        Why the re-check is sufficient (P2.4a): writers replace the mirror
        and upsert its marker inside their own write transaction (see
        ``_write_json_mirror``), so while this call holds the write lock the
        triple (rows, mirror file, marker) is exactly what the last
        committed writer left.  A mismatch seen here therefore means an
        external edit or an uncommitted publication (quarantined by its
        durable intent and repaired from SQLite, see ``_write_json_mirror``) --
        never a stale serialization racing a newer commit.  Before P2.4a
        the file + marker were written after COMMIT, and an importer that
        grabbed the lock in that gap imported a mirror serialized before
        another writer's commit, DELETEing that writer's rows (observed:
        ~4% of 4-thread stress rounds lost rows).
        """
        json_path: Path = self._json_path_fn()
        if not json_path.exists():
            return
        if _maintenance.is_blocked_db(self._db_path_fn()):
            # Maintenance mode: an import is a write (DELETE + re-INSERT).
            # Serve the database as-is; the next load after the lock is
            # released re-checks the mirror.
            return
        if conn.in_transaction:
            # Nested read on a connection already inside a write transaction
            # (same thread + same db file).  An import here would need a
            # second BEGIN IMMEDIATE and crash; the outer transaction already
            # holds the db write lock, so skip the import -- the next
            # top-level load()/mutate() of this table re-checks the mirror.
            return

        try:
            mtime_ns = _mirror_token(json_path)
        except OSError:
            return

        source_key = str(json_path.resolve())
        intent_path = _mirror_intent_path(json_path)

        def _already_imported(as_of_mtime_ns: int) -> bool:
            row = conn.execute(
                "SELECT last_imported_mtime_ns FROM _json_mirror_state WHERE source_path = ?",
                (source_key,),
            ).fetchone()
            # Equality, not >=: the token mixes in file size, so a newer file
            # can legitimately produce a numerically smaller token. A stored
            # token only means "this exact version was imported".
            return row is not None and row[0] == as_of_mtime_ns

        with _setup_lock:
            if _already_imported(mtime_ns) and not intent_path.exists():
                return  # already imported this version (or a newer one)

        # No lock held past this point. BEGIN IMMEDIATE below (SQLite's own
        # whole-file write lock) is what serializes the actual import now.
        conn.execute("BEGIN IMMEDIATE")
        try:
            # All intent inspection/removal is under the same DB write lock
            # as publication, including other processes. An intent survives
            # failed recovery I/O, so its uncommitted file cannot be mistaken
            # for a hand edit and replayed after the API reported failure.
            if intent_path.exists():
                try:
                    intent = json.loads(intent_path.read_text(encoding="utf-8"))
                    if (intent["source_path"] != source_key or intent["table_name"] != self._table
                            or type(intent["token"]) is not int):
                        raise ValueError("mirror publication intent scope mismatch")
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    raise sqlite3.OperationalError("invalid JSON mirror publication intent") from exc
                if _already_imported(intent["token"]):
                    # That exact publication committed. A later file edit
                    # remains eligible for normal external import below.
                    intent_path.unlink()
                else:
                    # SQLite rolled back the publication. Repair from DB
                    # truth before any importer can see the ahead mirror.
                    self._write_json_mirror(conn)
                    conn.execute("COMMIT")
                    return
            # Re-stat and re-check now that the write lock is held -- both
            # the file and the marker could have moved while this call was
            # waiting to acquire it above.
            try:
                fresh_mtime_ns = _mirror_token(json_path)
            except OSError:
                conn.execute("COMMIT")
                return
            if _already_imported(fresh_mtime_ns):
                conn.execute("COMMIT")
                return

            try:
                raw = json_path.read_text(encoding="utf-8")
                records = json.loads(raw)
            except (OSError, json.JSONDecodeError):
                conn.execute("COMMIT")
                return
            if not isinstance(records, list):
                conn.execute("COMMIT")
                return
            # An external editor may have replaced the file between the stat
            # above and the read: the content would then not be the version
            # the marker is about to record.  Skip; the next load re-checks.
            try:
                if _mirror_token(json_path) != fresh_mtime_ns:
                    conn.execute("COMMIT")
                    return
            except OSError:
                conn.execute("COMMIT")
                return

            # Validate the entire snapshot before replacing committed data.
            # A blank/truncated mirror is not an intentional JSON [] clear.
            seen_ids = set()
            for record in records:
                record_id = record.get("id") if isinstance(record, dict) else None
                if (type(record_id) not in (str, int)
                        or not str(record_id).strip()
                        or str(record_id) in seen_ids):
                    conn.execute("COMMIT")
                    return
                seen_ids.add(str(record_id))

            conn.execute(f"DELETE FROM {self._table}")
            for record in records:
                conn.execute(
                    f"INSERT OR REPLACE INTO {self._table} (id, updated_at, data) VALUES (?, ?, ?)",
                    (_id_of(record), _updated_at_of(record), json.dumps(record, ensure_ascii=False)),
                )
            _upsert_mirror_marker(conn, source_key, self._table, fresh_mtime_ns)
            conn.execute("COMMIT")
        except BaseException:
            _rollback_quietly(conn)
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
        _maintenance.assert_writable_db(self._db_path_fn())
        conn = self._conn()
        _refuse_nested(conn, self._table)
        with _setup_lock:
            _ensure_table(conn, self._table)

        def _flush() -> None:
            conn.execute(f"DELETE FROM {self._table}")
            for record in records:
                conn.execute(
                    f"INSERT OR REPLACE INTO {self._table} (id, updated_at, data) VALUES (?, ?, ?)",
                    (_id_of(record), _updated_at_of(record), json.dumps(record, ensure_ascii=False)),
                )

        def _do():
            conn.execute("BEGIN IMMEDIATE")
            self._flush_publish_commit(conn, _flush)

        _retry_on_locked(_do)

    def _flush_publish_commit(self, conn: sqlite3.Connection, flush: Callable[[], None]) -> None:
        """Writer tail shared by save/mutate/scoped_mutate.  The caller already
        holds ``BEGIN IMMEDIATE`` on ``conn``.  Runs ``flush()``, publishes the
        mirror + marker of the resulting in-transaction state (still under
        the write lock) and COMMITs.  On ANY failure the rows are undone and
        DB, mirror and marker are restored before the error is re-raised
        when recovery I/O succeeds:

        * nothing replaced yet (flush error, replace failed after all
          retries, ...): plain ROLLBACK -- the old mirror was never touched.
        * mirror already replaced (failure after the replace, or COMMIT
          itself failed): ``ROLLBACK TO`` the savepoint opened before the
          flush, re-publish the mirror of the restored state and COMMIT, all
          without releasing the write lock, so no importer can observe the
          not-committed mirror.  If the transaction is already gone (COMMIT
          failed and SQLite auto-rolled back) a best-effort re-publish runs
          in a fresh transaction; should that also fail, the durable intent
          blocks future import until publication recovery succeeds.
        """
        replaces_before = _mirror_replace_count()
        try:
            conn.execute(f"SAVEPOINT {_PUBLISH_SAVEPOINT}")
            flush()
            self._write_json_mirror(conn)
            conn.execute("COMMIT")
        except BaseException:
            if _mirror_replace_count() == replaces_before:
                _rollback_quietly(conn)
            else:
                self._restore_mirror_after_failed_write(conn)
            raise

    def _restore_mirror_after_failed_write(self, conn: sqlite3.Connection) -> None:
        if conn.in_transaction:
            try:
                conn.execute(f"ROLLBACK TO {_PUBLISH_SAVEPOINT}")
                self._write_json_mirror(conn)
                conn.execute("COMMIT")
                return
            except BaseException:
                _rollback_quietly(conn)
        try:
            self._write_json_mirror(conn)
        except Exception:
            pass

    def _write_json_mirror(self, conn: sqlite3.Connection) -> None:
        """Re-serialize the full JSON mirror file from the database state seen
        by ``conn`` (a fresh SELECT, not whatever list a caller happened to
        hold) and record its change token in ``_json_mirror_state``.

        Atomicity contract (P2.4a -- the fix for a lost-update race):

        * Called with ``conn`` inside a write transaction (every writer:
          save/mutate/scoped_mutate via ``_flush_publish_commit``): the
          SELECT sees the writer's own uncommitted rows, the file is
          replaced and the marker upserted INSIDE that transaction, and the
          caller COMMITs afterwards.  The caller MUST hold ``BEGIN
          IMMEDIATE`` (the db write lock) -- that lock, which importers also
          need, is what makes (rows, file, marker) change as one unit for
          every thread AND every process sharing the db file.  The old
          process-local ``_setup_lock`` could not cover other processes and
          left a gap after COMMIT in which an importer imported a stale
          mirror over newer committed rows.
        * Called outside a transaction (e.g. the channel migration's mirror
          repair): opens its own ``BEGIN IMMEDIATE``, publishes the committed
          state and COMMITs.  It changes no rows, so a failed COMMIT after
          the replace leaves a file identical to the DB -- at worst one
          harmless re-import.

        Order inside the transaction: write tmp -> stat tmp -> persist and
        fsync publication intent -> upsert marker -> atomic ``os.replace`` (with
        PermissionError retry) -> re-stat and fix the marker if a filesystem
        changed the timestamp on rename.  Between the replace and the
        caller's COMMIT only that (normally skipped) marker fix-up and
        COMMIT itself can fail; ``_flush_publish_commit`` restores the
        mirror if they do.

        Crash/failure recovery: the intent is retained through COMMIT. The
        next sync inspects it under BEGIN IMMEDIATE: a matching committed
        marker clears the intent and still permits later external edits;
        a mismatch repairs the mirror from committed SQLite rows instead
        of importing aborted rows. If recovery also fails, loads fail closed
        and retain the intent for retry. Cleanup cannot remove another
        writer's intent because it holds the same database write lock.
        This is not a power-loss durability guarantee for the two resources.
        """
        if not conn.in_transaction:
            def _standalone() -> None:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    self._publish_mirror_in_transaction(conn)
                    conn.execute("COMMIT")
                except BaseException:
                    _rollback_quietly(conn)
                    raise

            _retry_on_locked(_standalone)
            return
        self._publish_mirror_in_transaction(conn)

    def _publish_mirror_in_transaction(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute(f"SELECT data FROM {self._table}").fetchall()
        current_records = [json.loads(r[0]) for r in rows]

        json_path: Path = self._json_path_fn()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        source_key = str(json_path.resolve())
        # Unique per process + thread: writers of different db files (or a
        # leftover from a killed writer) never share a tmp path.
        tmp = json_path.parent / f"{json_path.stem}.{os.getpid()}.{threading.get_ident()}.json.tmp"
        try:
            tmp.write_text(json.dumps(current_records, ensure_ascii=False, indent=2), encoding="utf-8")
            token = _mirror_token(tmp)
            _write_mirror_intent(json_path, self._table, token)
            _upsert_mirror_marker(conn, source_key, self._table, token)
            _replace_mirror_file(tmp, json_path)
        finally:
            tmp.unlink(missing_ok=True)

        # Record the exact version now on disk so a later load() does not
        # re-import this file over itself.
        try:
            final_token = _mirror_token(json_path)
        except OSError:
            return
        if final_token != token:
            _write_mirror_intent(json_path, self._table, final_token)
            _upsert_mirror_marker(conn, source_key, self._table, final_token)

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

    def scoped_mutate(self, channel_id: str, *, include_legacy: bool = False, owner_key: str = "channel_id"):
        """Channel-scoped read-modify-write (multi-channel isolation primitive).

        Same transaction model as :meth:`mutate` (one ``BEGIN IMMEDIATE``
        held for the whole block) but the block only sees the rows owned by
        ``channel_id`` (plus legacy rows without ``owner_key`` when
        ``include_legacy``).  Rows of other channels are never exposed and
        never written; private copies are available read-only as
        ``records.out_of_scope`` for global uniqueness checks.

        At commit, inside the same transaction, every added/changed/deleted
        row is verified: new rows must carry ``owner_key == channel_id`` and
        an id not used by any existing row; changed rows must keep their
        owner value (presence included); rows to update/delete are re-read
        from the db and must still be in scope.  Any violation raises
        :class:`ChannelIsolationError` and rolls back with zero rows written
        (the JSON mirror is not touched).
        """
        return _ScopedMutateCtx(self, channel_id, include_legacy, owner_key)

    def scoped_load(self, channel_id: str, *, include_legacy: bool = False, owner_key: str = "channel_id") -> List[Dict[str, Any]]:
        """Rows owned by ``channel_id`` (+ legacy when ``include_legacy``)."""
        if not isinstance(channel_id, str) or not channel_id:
            raise ValueError("scoped_load ต้องระบุ channel_id")

        def owns(record: Dict[str, Any]) -> bool:
            owner = record.get(owner_key) if isinstance(record, dict) else None
            return include_legacy if owner is None else owner == channel_id

        return [record for record in self.load() if owns(record)]


def _refuse_nested(conn: sqlite3.Connection, table: str) -> None:
    if conn.in_transaction:
        raise NestedTransactionError(
            f"cannot start a transaction within a transaction: เขียนตาราง {table} ซ้อนใน "
            "transaction ที่เปิดอยู่บน connection เดียวกันไม่ได้ (ย้ายงานเขียนไปทำหลัง commit)"
        )


def _canonical(record: Any) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True)


def _index_unique(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed = {_id_of(record): record for record in records}
    if len(indexed) != len(records):
        raise ValueError("duplicate record id -- refusing ambiguous mutation flush")
    return indexed


def _flush_diff(
    conn: sqlite3.Connection,
    table: str,
    before: Dict[str, Dict[str, Any]],
    after: Dict[str, Dict[str, Any]],
) -> None:
    """Write only the difference between two id-indexed snapshots (inside
    the caller's open transaction)."""
    for record_id in before.keys() - after.keys():
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))

    for record_id in after.keys() - before.keys():
        record = after[record_id]
        conn.execute(
            f"INSERT INTO {table} (id, updated_at, data) VALUES (?, ?, ?)",
            (_id_of(record), _updated_at_of(record), json.dumps(record, ensure_ascii=False)),
        )

    for record_id in before.keys() & after.keys():
        record = after[record_id]
        if _canonical(before[record_id]) == _canonical(record):
            continue
        conn.execute(
            f"UPDATE {table} SET updated_at = ?, data = ? WHERE id = ?",
            (_updated_at_of(record), json.dumps(record, ensure_ascii=False), record_id),
        )


class _MutateCtx:
    def __init__(self, table: "DocumentTable"):
        self._table = table
        self._conn: sqlite3.Connection | None = None
        self._records: List[Dict[str, Any]] | None = None
        self._snapshot: str | None = None

    def __enter__(self) -> List[Dict[str, Any]]:
        t = self._table
        conn = t._conn()
        _refuse_nested(conn, t._table)
        t._sync_from_json_if_newer(conn)
        conn.execute("BEGIN IMMEDIATE")
        self._conn = conn
        try:
            rows = conn.execute(f"SELECT data FROM {t._table}").fetchall()
            self._records = [json.loads(r[0]) for r in rows]
            self._snapshot = json.dumps(self._records, ensure_ascii=False, sort_keys=True)
        except BaseException:
            _rollback_quietly(conn)
            raise
        # Remember what was read so __exit__ can tell a real mutation from a
        # block that turned out to change nothing. Some callers hold this
        # transaction only because they MIGHT write -- product_store's
        # reconcile_existing_projects() runs on every product listing, and
        # rewriting every row plus the JSON mirror each time the UI polls
        # would be pure churn.
        return self._records

    def __exit__(self, exc_type, exc, tb) -> bool:
        conn = self._conn
        assert conn is not None
        if exc_type is not None:
            _rollback_quietly(conn)
            return False

        t = self._table
        records = self._records or []
        try:
            if json.dumps(records, ensure_ascii=False, sort_keys=True) == self._snapshot:
                # A no-op still needs rollback cleanup if COMMIT fails.
                conn.execute("COMMIT")
                return False
            # Flush only the rows whose documents actually changed.  The
            # transaction still starts from a complete snapshot (the public
            # mutate() contract intentionally yields a list), but a normal
            # single-product update no longer DELETEs and re-inserts every
            # product in the table.  This keeps the compatibility surface of
            # _load()/_save() while bounding the write set for the common
            # row-level mutation paths.
            _maintenance.assert_writable_db(t._db_path_fn())
            before = _index_unique(json.loads(self._snapshot or "[]"))
            after = _index_unique(records)
        except BaseException:
            _rollback_quietly(conn)
            raise

        # Rows + JSON mirror + marker, committed as one unit (P2.4a).
        t._flush_publish_commit(conn, lambda: _flush_diff(conn, t._table, before, after))
        return False


class ScopedRecords(list):
    """The in-scope records of a :meth:`DocumentTable.scoped_mutate` block.

    Mutate/append/remove items exactly like the plain ``mutate()`` list.
    ``out_of_scope`` holds private copies of every other row (read-only by
    contract: changes to them are never written).  Use it only for global
    uniqueness checks (e.g. product codes), never to decide what to write.
    """

    out_of_scope: tuple = ()


class _ScopedMutateCtx:
    """See :meth:`DocumentTable.scoped_mutate`."""

    def __init__(self, table: "DocumentTable", channel_id: str, include_legacy: bool, owner_key: str):
        if not isinstance(channel_id, str) or not channel_id:
            raise ValueError("scoped_mutate ต้องระบุ channel_id")
        self._table = table
        self._channel_id = channel_id
        self._include_legacy = bool(include_legacy)
        self._owner_key = owner_key
        self._conn: sqlite3.Connection | None = None
        self._view: ScopedRecords | None = None
        self._snapshot: str | None = None
        self._existing_ids: set = set()

    def _owns(self, record: Dict[str, Any]) -> bool:
        owner = record.get(self._owner_key) if isinstance(record, dict) else None
        if owner is None:
            return self._include_legacy
        return owner == self._channel_id

    def __enter__(self) -> ScopedRecords:
        t = self._table
        conn = t._conn()
        _refuse_nested(conn, t._table)
        t._sync_from_json_if_newer(conn)
        conn.execute("BEGIN IMMEDIATE")
        self._conn = conn
        try:
            rows = conn.execute(f"SELECT id, data FROM {t._table}").fetchall()
            in_scope: List[Dict[str, Any]] = []
            out_of_scope: List[Dict[str, Any]] = []
            for row_id, data in rows:
                self._existing_ids.add(str(row_id))
                record = json.loads(data)
                (in_scope if self._owns(record) else out_of_scope).append(record)
            self._snapshot = json.dumps(in_scope, ensure_ascii=False, sort_keys=True)
            view = ScopedRecords(in_scope)
            view.out_of_scope = tuple(out_of_scope)
            self._view = view
        except BaseException:
            _rollback_quietly(conn)
            raise
        return view

    def _verify(self, before: Dict[str, Dict[str, Any]], after: Dict[str, Dict[str, Any]]) -> None:
        conn = self._conn
        assert conn is not None
        t = self._table
        key = self._owner_key
        violations: List[str] = []
        messages: List[str] = []

        for record_id in after.keys() - before.keys():
            record = after[record_id]
            if record_id in self._existing_ids:
                violations.append(record_id)
                messages.append(f"id {record_id} มีอยู่แล้วนอกขอบเขตช่อง {self._channel_id}")
            elif record.get(key) != self._channel_id:
                violations.append(record_id)
                messages.append(f"record ใหม่ {record_id} ต้องมี {key}={self._channel_id}")

        for record_id in before.keys() & after.keys():
            if before[record_id].get(key, _MISSING) != after[record_id].get(key, _MISSING):
                violations.append(record_id)
                messages.append(f"ห้ามเปลี่ยนเจ้าของ record {record_id}")

        # Defence in depth: re-read every row about to be UPDATEd/DELETEd from
        # the db inside this same transaction and confirm it is in scope.
        touched = (before.keys() - after.keys()) | {
            rid for rid in before.keys() & after.keys() if _canonical(before[rid]) != _canonical(after[rid])
        }
        for record_id in sorted(touched):
            row = conn.execute(f"SELECT data FROM {t._table} WHERE id = ?", (record_id,)).fetchone()
            if row is None or not self._owns(json.loads(row[0])):
                violations.append(record_id)
                messages.append(f"record {record_id} ไม่อยู่ในขอบเขตช่อง {self._channel_id}")

        if violations:
            raise ChannelIsolationError(
                "ยกเลิกการบันทึกทั้งหมด: " + "; ".join(messages[:5]),
                record_ids=set(violations),
            )

    def __exit__(self, exc_type, exc, tb) -> bool:
        conn = self._conn
        assert conn is not None
        if exc_type is not None:
            _rollback_quietly(conn)
            return False

        t = self._table
        records = list(self._view or [])
        try:
            if json.dumps(records, ensure_ascii=False, sort_keys=True) == self._snapshot:
                conn.execute("COMMIT")
                return False
            _maintenance.assert_writable_db(t._db_path_fn())
            before = _index_unique(json.loads(self._snapshot or "[]"))
            after = _index_unique(records)
            self._verify(before, after)
        except BaseException:
            _rollback_quietly(conn)
            raise

        # Rows + JSON mirror + marker, committed as one unit (P2.4a).  An
        # isolation violation above never reaches this: mirror untouched.
        t._flush_publish_commit(conn, lambda: _flush_diff(conn, t._table, before, after))
        return False
