"""JSON-mirror atomicity of ``scripts/db.py`` DocumentTable (multi-channel P2.4a).

Regression for a lost-update race: writers used to replace the JSON mirror
and record its token in ``_json_mirror_state`` AFTER their COMMIT, so an
importer (another process, or another thread) could grab the write lock in
that gap, see "mirror changed", and import a mirror serialized before a newer
commit -- DELETE + re-INSERT dropped that commit's rows for good.  The fix
publishes mirror + marker inside the writer's own write transaction.

Every test loads a private copy of the db module (``_load_db_copy``) so two
copies behave like two processes (own ``_setup_lock`` and connection cache)
sharing one sqlite file.  ``OMNICUT_DB_IMPL_UNDER_TEST=<path to db.py>`` runs
the same tests against another implementation (used to prove the forced
interleaving fails on the pre-fix code).

Offline + tmp_path only; never touches the real ``_Docs/store.db``.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import os
import sqlite3
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DB_IMPL = Path(os.environ.get("OMNICUT_DB_IMPL_UNDER_TEST") or REPO / "scripts" / "db.py")
_copy_ids = itertools.count()
_LOADED = []


def _load_db_copy():
    spec = importlib.util.spec_from_file_location(f"_db_mirror_copy_{next(_copy_ids)}", DB_IMPL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _LOADED.append(module)
    return module


@pytest.fixture(autouse=True)
def _close_copy_connections():
    yield
    while _LOADED:
        module = _LOADED.pop()
        for conn in list((getattr(module._local, "conns", None) or {}).values()):
            try:
                conn.close()
            except Exception:
                pass


def _paths(tmp_path: Path, name: str = "items"):
    root = tmp_path / "_Docs"
    return root / "store.db", root / f"{name}.json"


def _table(module, tmp_path: Path, name: str = "items"):
    db_path, json_path = _paths(tmp_path, name)
    return module.DocumentTable(name, lambda: db_path, lambda: json_path)


def _raw_ids(tmp_path: Path, name: str = "items") -> set:
    db_path, _ = _paths(tmp_path, name)
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0] for row in conn.execute(f"SELECT id FROM {name}")}
    finally:
        conn.close()


def _raw_marker(tmp_path: Path, name: str = "items"):
    db_path, json_path = _paths(tmp_path, name)
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT last_imported_mtime_ns FROM _json_mirror_state WHERE source_path = ?",
            (str(json_path.resolve()),),
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _mirror_ids(tmp_path: Path, name: str = "items") -> list:
    _, json_path = _paths(tmp_path, name)
    return [r["id"] for r in json.loads(json_path.read_text(encoding="utf-8"))]


def _assert_consistent(module, tmp_path: Path, name: str = "items") -> set:
    """Committed rows == mirror rows and marker == token(mirror): nothing is
    pending import, nothing can be clobbered by the next load."""
    _, json_path = _paths(tmp_path, name)
    ids = _raw_ids(tmp_path, name)
    mirror = _mirror_ids(tmp_path, name)
    assert sorted(mirror) == sorted(ids) and len(mirror) == len(set(mirror))
    assert _raw_marker(tmp_path, name) == module._mirror_token(json_path)
    return ids


def _trace_deletes(module, tmp_path: Path, name: str = "items") -> list:
    db_path, _ = _paths(tmp_path, name)
    statements: list = []
    module._connection_for(db_path).set_trace_callback(statements.append)
    return statements


def _count_imports(statements: list, name: str = "items") -> int:
    return sum(1 for s in statements if s.strip() == f"DELETE FROM {name}")


# -- (a) forced interleaving -----------------------------------------------------

class _ReplaceGate:
    """Pauses ONE designated thread right before and right after it replaces
    the mirror file (``Path.replace`` onto ``mirror``)."""

    def __init__(self, mirror: Path, real_replace):
        self.mirror = mirror.resolve()
        self.real = real_replace
        self.thread_id = None
        self.before, self.go_replace = threading.Event(), threading.Event()
        self.after, self.go_on = threading.Event(), threading.Event()

    def replace(self, path_self, target):
        gated = threading.get_ident() == self.thread_id and Path(target).resolve() == self.mirror
        if gated:
            self.before.set()
            assert self.go_replace.wait(20)
        result = self.real(path_self, target)
        if gated:
            self.after.set()
            assert self.go_on.wait(20)
        return result


def _run(target, errors):
    def body():
        try:
            target()
        except BaseException as exc:  # noqa: BLE001 - reported by the test
            errors.append(exc)

    thread = threading.Thread(target=body, daemon=True)
    thread.start()
    return thread


def test_stale_mirror_in_commit_gap_is_never_imported_over_newer_rows(tmp_path, monkeypatch):
    """Old bad schedule, forced deterministically with two "processes":

    1. P1 writer A commits row ``a`` and serializes the mirror, then pauses
       right before replacing the file.
    2. P2 writer D commits row ``d`` (and publishes its own mirror).
    3. A replaces the mirror with its now-stale {seed, a} copy and pauses
       before recording the marker.
    4. P2 importer C loads: "mirror changed" -> imports the stale file.

    Pre-fix code loses ``d`` here.  Fixed code: A holds the write lock until
    its mirror + marker are committed, so D and C simply wait (bounded waits
    below) and nothing is lost.
    """
    p1, p2 = _load_db_copy(), _load_db_copy()
    t1, t2 = _table(p1, tmp_path), _table(p2, tmp_path)
    with t1.mutate() as records:
        records.append({"id": "seed"})
    _, mirror = _paths(tmp_path)

    gate = _ReplaceGate(mirror, Path.replace)
    monkeypatch.setattr(Path, "replace", lambda self, target: gate.replace(self, target))
    errors: list = []

    def writer_a():
        gate.thread_id = threading.get_ident()
        with t1.mutate() as records:
            records.append({"id": "a"})

    def writer_d():
        with t2.mutate() as records:
            records.append({"id": "d"})

    a = _run(writer_a, errors)
    assert gate.before.wait(20), "writer A never reached the mirror replace"
    d = _run(writer_d, errors)
    d.join(1.0)  # pre-fix: finishes at once; fixed: blocked on A's write lock
    gate.go_replace.set()
    assert gate.after.wait(20)
    c = _run(t2.load, errors)
    c.join(1.0)  # pre-fix: imports the stale mirror; fixed: waits for A
    gate.go_on.set()
    for thread in (a, d, c):
        thread.join(30)
        assert not thread.is_alive()

    assert errors == []
    assert _raw_ids(tmp_path) == {"seed", "a", "d"}
    assert {r["id"] for r in _table(_load_db_copy(), tmp_path).load()} == {"seed", "a", "d"}
    _assert_consistent(p1, tmp_path)


# -- (b) multi-thread stress ---------------------------------------------------------

def test_threaded_mixed_writers_lose_no_rows(tmp_path):
    rounds, ops = 12, 12
    for round_no in range(rounds):
        base = tmp_path / f"r{round_no}"
        module = _load_db_copy()
        items, posts = _table(module, base), _table(module, base, "posts")
        errors: list = []
        expected: set = set()
        saved: list = []
        guard = threading.Lock()

        def writer(kind, channel, prefix):
            for i in range(ops):
                rid = f"{prefix}{i}"
                ctx = items.scoped_mutate(channel, include_legacy=channel == "main") if kind == "scoped" else items.mutate()
                with ctx as records:
                    records.append({"id": rid, "channel_id": channel})
                with guard:
                    expected.add(rid)

        def saver():
            for i in range(ops):
                rows = [{"id": f"s{j}", "v": i} for j in range(i + 1)]
                posts.save(rows)
                saved[:] = rows

        def reader():
            for _ in range(ops):
                items.load()
                items.scoped_load("second")
                posts.load()

        threads = [
            _run(lambda: writer("plain", "main", "a"), errors),
            _run(lambda: writer("plain", "second", "b"), errors),
            _run(lambda: writer("scoped", "main", "c"), errors),
            _run(lambda: writer("scoped", "second", "d"), errors),
            _run(lambda: writer("scoped", "second", "e"), errors),
            _run(saver, errors),
            _run(reader, errors),
            _run(reader, errors),
        ]
        for thread in threads:
            thread.join(60)
            assert not thread.is_alive()
        assert errors == [], f"round {round_no}: {errors[:3]}"
        assert _raw_ids(base) == expected, f"round {round_no}: lost {sorted(expected - _raw_ids(base))}"
        assert posts.load() == saved
        _assert_consistent(module, base)
        _assert_consistent(module, base, "posts")


# -- (c) multi-process stress --------------------------------------------------------

_CHILD = textwrap.dedent(
    """
    import importlib.util, sys
    sys.path.insert(0, sys.argv[1])
    spec = importlib.util.spec_from_file_location("child_db", sys.argv[2])
    db = importlib.util.module_from_spec(spec); spec.loader.exec_module(db)
    from pathlib import Path
    db_path, json_path, prefix, ops = Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5], int(sys.argv[6])
    table = db.DocumentTable("items", lambda: db_path, lambda: json_path)
    for i in range(ops):
        channel = "main" if i % 2 else "second"
        ctx = table.scoped_mutate(channel) if i % 3 else table.mutate()
        with ctx as records:
            records.append({"id": f"{prefix}{i}", "channel_id": channel})
        table.load()
    """
)


def test_multi_process_writers_lose_no_rows(tmp_path):
    procs, ops = 3, 40
    for round_no in range(2):
        base = tmp_path / f"r{round_no}"
        db_path, json_path = _paths(base)
        module = _load_db_copy()
        with _table(module, base).mutate() as records:
            records.append({"id": "seed", "channel_id": "main"})
        children = [
            subprocess.Popen(
                [sys.executable, "-c", _CHILD, str(REPO), str(DB_IMPL), str(db_path), str(json_path), f"p{n}_", str(ops)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            for n in range(procs)
        ]
        outputs = [child.communicate(timeout=120)[0].decode("utf-8", "replace") for child in children]
        assert [child.returncode for child in children] == [0] * procs, outputs
        expected = {"seed"} | {f"p{n}_{i}" for n in range(procs) for i in range(ops)}
        assert _raw_ids(base) == expected, f"lost {sorted(expected - _raw_ids(base))}"
        _assert_consistent(module, base)


# -- (d) Windows PermissionError on replace --------------------------------------------

def _failing_replace(mirror: Path, failures, real_replace):
    calls = {"n": 0}

    def replace(path_self, target):
        if Path(target).resolve() == mirror.resolve():
            calls["n"] += 1
            if failures is None or calls["n"] <= failures:
                raise PermissionError(13, "simulated sharing violation", str(target))
        return real_replace(path_self, target)

    return replace, calls


def _write(kind, table):
    if kind == "save":
        table.save(table.load() + [{"id": "new", "channel_id": "main"}])
    elif kind == "scoped":
        with table.scoped_mutate("main") as records:
            records.append({"id": "new", "channel_id": "main"})
    else:
        with table.mutate() as records:
            records.append({"id": "new", "channel_id": "main"})


@pytest.mark.parametrize("kind", ["mutate", "scoped", "save"])
def test_replace_permission_error_is_retried(tmp_path, monkeypatch, kind):
    module = _load_db_copy()
    monkeypatch.setattr(module, "_MIRROR_REPLACE_BACKOFF_S", 0.0)
    table = _table(module, tmp_path)
    with table.mutate() as records:
        records.append({"id": "seed", "channel_id": "main"})
    _, mirror = _paths(tmp_path)
    replace, calls = _failing_replace(mirror, 3, Path.replace)
    monkeypatch.setattr(Path, "replace", replace)

    _write(kind, table)

    assert calls["n"] == 4
    assert _assert_consistent(module, tmp_path) == {"seed", "new"}
    assert not list(mirror.parent.glob("*.tmp"))


@pytest.mark.parametrize("kind", ["mutate", "scoped", "save"])
def test_replace_that_always_fails_rolls_back_everything(tmp_path, monkeypatch, kind):
    module = _load_db_copy()
    monkeypatch.setattr(module, "_MIRROR_REPLACE_BACKOFF_S", 0.0)
    table = _table(module, tmp_path)
    with table.mutate() as records:
        records.append({"id": "seed", "channel_id": "main"})
    _, mirror = _paths(tmp_path)
    before_bytes, before_marker = mirror.read_bytes(), _raw_marker(tmp_path)
    replace, calls = _failing_replace(mirror, None, Path.replace)
    monkeypatch.setattr(Path, "replace", replace)

    with pytest.raises(PermissionError):
        _write(kind, table)

    assert calls["n"] == module._MIRROR_REPLACE_ATTEMPTS
    assert _raw_ids(tmp_path) == {"seed"}
    assert mirror.read_bytes() == before_bytes
    assert _raw_marker(tmp_path) == before_marker
    assert not list(mirror.parent.glob("*.tmp"))
    monkeypatch.undo()
    statements = _trace_deletes(module, tmp_path)
    assert {r["id"] for r in table.load()} == {"seed"}
    assert _count_imports(statements) == 0  # nothing pending import


# -- (e) external edit still auto-imports, exactly once ---------------------------------

def test_external_mirror_edit_is_imported_exactly_once(tmp_path):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    with table.mutate() as records:
        records.append({"id": "seed"})
    _, mirror = _paths(tmp_path)
    statements = _trace_deletes(module, tmp_path)

    assert {r["id"] for r in table.load()} == {"seed"}
    assert _count_imports(statements) == 0  # a writer's own mirror is never re-imported

    mirror.write_text(json.dumps([{"id": "hand-1"}, {"id": "hand-2", "note": "edited by hand"}]), encoding="utf-8")
    assert {r["id"] for r in table.load()} == {"hand-1", "hand-2"}
    assert {r["id"] for r in table.load()} == {"hand-1", "hand-2"}
    with table.mutate() as records:
        records.append({"id": "after"})
    assert {r["id"] for r in table.load()} == {"hand-1", "hand-2", "after"}
    assert _count_imports(statements) == 1
    _assert_consistent(module, tmp_path)


# -- (f) failure / crash between mirror replace and COMMIT -----------------------------------

class _CommitFailingConn:
    """Proxy for the cached sqlite connection whose next COMMIT fails."""

    def __init__(self, conn, auto_rollback: bool):
        self._conn = conn
        self._auto_rollback = auto_rollback
        self.armed = True

    def execute(self, sql, *args):
        if self.armed and sql == "COMMIT":
            self.armed = False
            if self._auto_rollback:
                self._conn.execute("ROLLBACK")
            raise sqlite3.OperationalError("disk I/O error (simulated)")
        return self._conn.execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self._conn, name)


@pytest.mark.parametrize("auto_rollback", [False, True], ids=["tx_still_open", "tx_already_gone"])
@pytest.mark.parametrize("kind", ["mutate", "scoped", "save"])
def test_commit_failure_after_replace_restores_mirror(tmp_path, monkeypatch, kind, auto_rollback):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    with table.mutate() as records:
        records.append({"id": "seed", "channel_id": "main"})
    table.load()  # finalize the seed's committed publication intent
    db_path, _ = _paths(tmp_path)
    real_conn = module._connection_for(db_path)
    proxy = _CommitFailingConn(real_conn, auto_rollback)
    monkeypatch.setattr(module, "_connection_for", lambda path: proxy)
    with pytest.raises(sqlite3.OperationalError, match="simulated"):
        _write(kind, table)
    assert not proxy.armed
    monkeypatch.undo()

    assert not real_conn.in_transaction
    assert _assert_consistent(module, tmp_path) == {"seed"}  # caller saw an error -> not applied
    statements = _trace_deletes(module, tmp_path)
    assert {r["id"] for r in table.load()} == {"seed"}
    assert _count_imports(statements) == 0


_CRASH_CHILD = textwrap.dedent(
    """
    import importlib.util, os, sys
    sys.path.insert(0, sys.argv[1])
    spec = importlib.util.spec_from_file_location("child_db", sys.argv[2])
    db = importlib.util.module_from_spec(spec); spec.loader.exec_module(db)
    from pathlib import Path
    db_path, json_path = Path(sys.argv[3]), Path(sys.argv[4])
    real = Path.replace
    def replace(self, target):
        result = real(self, target)
        if Path(target).resolve() == json_path.resolve():
            os._exit(3)  # killed after the mirror replace, before COMMIT
        return result
    Path.replace = replace
    table = db.DocumentTable("items", lambda: db_path, lambda: json_path)
    with table.mutate() as records:
        records.append({"id": "crashed"})
    """
)


@pytest.mark.parametrize("next_op", ["load", "mutate", "save"])
def test_process_killed_between_replace_and_commit(tmp_path, next_op):
    """A dead writer's uncommitted publication is repaired from SQLite,
    preserving prior commits without replaying the aborted transaction."""
    module = _load_db_copy()
    table = _table(module, tmp_path)
    with table.mutate() as records:
        records.append({"id": "seed"})
    db_path, json_path = _paths(tmp_path)
    for conn in list(module._local.conns.values()):
        conn.close()
    module._local.conns.clear()

    child = subprocess.run(
        [sys.executable, "-c", _CRASH_CHILD, str(REPO), str(DB_IMPL), str(db_path), str(json_path)],
        capture_output=True, timeout=120,
    )
    assert child.returncode == 3, child.stdout + child.stderr
    assert _raw_ids(tmp_path) == {"seed"}  # sqlite rolled the rows back
    assert sorted(_mirror_ids(tmp_path)) == ["crashed", "seed"]  # mirror is ahead

    statements = _trace_deletes(module, tmp_path)
    if next_op == "load":
        assert {r["id"] for r in table.load()} == {"seed"}
        expected = {"seed"}
    elif next_op == "mutate":
        with table.mutate() as records:
            records.append({"id": "later"})
        expected = {"seed", "later"}
    else:
        table.save([{"id": "only"}])
        expected = {"only"}
    assert {r["id"] for r in table.load()} == expected
    # load/mutate: repair publishes DB truth without importing; save: its
    # own intentional full-table DELETE and no import afterwards.
    assert _count_imports(statements) == (1 if next_op == "save" else 0)
    assert _assert_consistent(module, tmp_path) == expected


@pytest.mark.parametrize("kind", ["mutate", "scoped", "save"])
def test_commit_and_persistent_recovery_failure_quarantines_aborted_rows(tmp_path, monkeypatch, kind):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    table.save([{"id": "seed", "channel_id": "main"}])
    # Clear a prior successful intent before injecting failures.
    table.load()
    real_conn = table._conn()
    proxy = _CommitFailingConn(real_conn, auto_rollback=False)
    monkeypatch.setattr(module, "_connection_for", lambda path: proxy)
    real_replace = module._replace_mirror_file
    calls = []

    def replace_once(tmp, target):
        calls.append(target)
        if len(calls) > 1:
            raise PermissionError("persistent recovery publication failure")
        return real_replace(tmp, target)

    monkeypatch.setattr(module, "_replace_mirror_file", replace_once)
    with pytest.raises(sqlite3.OperationalError, match="simulated"):
        _write(kind, table)
    assert _raw_ids(tmp_path) == {"seed"}
    assert set(_mirror_ids(tmp_path)) == {"seed", "new"}
    assert module._mirror_intent_path(_paths(tmp_path)[1]).exists()
    # While publication remains unavailable, loading fails closed.
    with pytest.raises(PermissionError, match="persistent"):
        table.load()
    assert _raw_ids(tmp_path) == {"seed"}
    monkeypatch.undo()
    other = _table(_load_db_copy(), tmp_path)
    assert {r["id"] for r in other.load()} == {"seed"}
    with other.mutate() as records:
        records.append({"id": "later", "channel_id": "second"})
    assert _assert_consistent(module, tmp_path) == {"seed", "later"}


@pytest.mark.parametrize("kind", ["mutate", "scoped"])
@pytest.mark.parametrize("bad_value", [object(), "cycle"], ids=["unsupported", "circular"])
def test_unserializable_mutation_releases_write_lock(tmp_path, kind, bad_value):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    table.save([{"id": "seed", "channel_id": "main"}])
    _, mirror = _paths(tmp_path)
    before_bytes, before_marker = mirror.read_bytes(), _raw_marker(tmp_path)
    ctx = table.mutate() if kind == "mutate" else table.scoped_mutate("main")
    with pytest.raises((TypeError, ValueError)):
        with ctx as records:
            if bad_value == "cycle":
                records[0]["bad"] = records[0]
            else:
                records[0]["bad"] = bad_value
    assert not table._conn().in_transaction
    assert mirror.read_bytes() == before_bytes
    assert _raw_marker(tmp_path) == before_marker
    # An independent connection must be able to acquire the lock and write.
    other = _table(_load_db_copy(), tmp_path)
    with other.mutate() as records:
        records.append({"id": "after", "channel_id": "main"})
    assert _assert_consistent(module, tmp_path) == {"seed", "after"}


@pytest.mark.parametrize("kind", ["mutate", "scoped"])
def test_corrupt_database_document_does_not_leave_transaction_open(tmp_path, kind):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    table.save([{"id": "seed", "channel_id": "main"}])
    conn = table._conn()
    conn.execute("UPDATE items SET data = ? WHERE id = ?", ("{invalid", "seed"))
    ctx = table.mutate() if kind == "mutate" else table.scoped_mutate("main")
    with pytest.raises(json.JSONDecodeError):
        with ctx:
            pytest.fail("corrupt document was exposed")
    assert not conn.in_transaction
    other = _table(_load_db_copy(), tmp_path)
    other.save([{"id": "repaired", "channel_id": "main"}])
    assert _assert_consistent(module, tmp_path) == {"repaired"}


@pytest.mark.parametrize("kind", ["mutate", "scoped"])
def test_noop_commit_failure_releases_transaction(tmp_path, monkeypatch, kind):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    table.save([{"id": "seed", "channel_id": "main"}])
    table.load()
    real_conn = table._conn()
    proxy = _CommitFailingConn(real_conn, auto_rollback=False)
    monkeypatch.setattr(module, "_connection_for", lambda path: proxy)
    ctx = table.mutate() if kind == "mutate" else table.scoped_mutate("main")
    with pytest.raises(sqlite3.OperationalError, match="simulated"):
        with ctx:
            pass
    assert not real_conn.in_transaction
    assert _assert_consistent(module, tmp_path) == {"seed"}


@pytest.mark.parametrize("kind", ["mutate", "scoped", "save"])
def test_marker_fixup_failure_after_replace_restores_committed_rows(tmp_path, monkeypatch, kind):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    table.save([{"id": "seed", "channel_id": "main"}])
    token = module._mirror_token
    upsert = module._upsert_mirror_marker
    calls = []

    # Model a filesystem that changes the token during rename so publication
    # needs a second marker write after the mirror has already been replaced.
    monkeypatch.setattr(module, "_mirror_token", lambda path: token(path) + (1 if path.suffix == ".tmp" else 0))

    def fail_once(conn, source_key, name, value):
        calls.append(value)
        if len(calls) == 2:
            raise sqlite3.OperationalError("marker fixup failed")
        return upsert(conn, source_key, name, value)

    monkeypatch.setattr(module, "_upsert_mirror_marker", fail_once)
    with pytest.raises(sqlite3.OperationalError, match="marker fixup failed"):
        _write(kind, table)
    assert not table._conn().in_transaction
    monkeypatch.undo()
    assert _assert_consistent(module, tmp_path) == {"seed"}
    assert {row["id"] for row in table.load()} == {"seed"}


def test_committed_pending_intent_does_not_hide_later_external_edit(tmp_path):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    table.save([{"id": "seed"}])
    _, mirror = _paths(tmp_path)
    intent = module._mirror_intent_path(mirror)
    assert intent.exists()
    mirror.write_text(json.dumps([{"id": "external", "note": "later hand edit"}]), encoding="utf-8")
    assert {r["id"] for r in table.load()} == {"external"}
    assert not intent.exists()
    _assert_consistent(module, tmp_path)


@pytest.mark.parametrize("bad_intent", ["not-json", '{"source_path":"another","table_name":"items","token":1}'])
def test_invalid_intent_refuses_import_without_changing_committed_rows(tmp_path, bad_intent):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    table.save([{"id": "seed"}])
    _, mirror = _paths(tmp_path)
    intent = module._mirror_intent_path(mirror)
    intent.write_text(bad_intent, encoding="utf-8")
    mirror.write_text(json.dumps([{"id": "foreign"}]), encoding="utf-8")
    with pytest.raises(sqlite3.OperationalError, match="invalid JSON mirror publication intent"):
        table.load()
    assert _raw_ids(tmp_path) == {"seed"}
    assert not table._conn().in_transaction
    assert intent.read_text(encoding="utf-8") == bad_intent


def test_intent_fsync_failure_prevents_mirror_publication(tmp_path, monkeypatch):
    module = _load_db_copy()
    table = _table(module, tmp_path)
    table.save([{"id": "seed"}])
    table.load()
    _, mirror = _paths(tmp_path)
    before = mirror.read_bytes()
    def fail_fsync(fd):
        raise OSError("intent durability failed")
    monkeypatch.setattr(module.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="intent durability failed"):
        with table.mutate() as records:
            records.append({"id": "new"})
    assert _raw_ids(tmp_path) == {"seed"}
    assert mirror.read_bytes() == before
    assert not module._mirror_intent_path(mirror).exists()
    assert not list(mirror.parent.glob("*.tmp"))
