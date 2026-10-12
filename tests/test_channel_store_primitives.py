"""Channel isolation primitives (multi-channel P2.1).

Covers ``DocumentTable.scoped_mutate`` / ``scoped_load`` (scripts/db.py), the
store-scope rules in ``scripts/channel_ownership.py``, the nested-write guard
on the shared sqlite connection, the JSON mirror after scoped writes, and the
repo rule that ``all_channels=True`` only appears in allowlisted modules.

Offline + tmp_path only: every sqlite connection opened during these tests is
asserted to live under tmp_path (see ``_only_tmp_databases``).
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path

import pytest

from scripts import channel_ownership as co
from scripts import config, db
from scripts.channel_store import ChannelError
from scripts.db import ChannelIsolationError, DocumentTable, NestedTransactionError

REPO = Path(__file__).resolve().parent.parent
STRICT_ENV = config.MULTI_CHANNEL_STRICT_ENV


@pytest.fixture(autouse=True)
def _only_tmp_databases(tmp_path, monkeypatch):
    """Fail loudly if anything here opens a sqlite file outside tmp_path
    (e.g. the real _Docs/store.db)."""
    real = db._connection_for
    tmp_root = tmp_path.resolve()

    def guarded(db_path):
        resolved = Path(db_path).resolve()
        assert tmp_root in resolved.parents, f"opened a non-tmp database: {resolved}"
        return real(db_path)

    monkeypatch.setattr(db, "_connection_for", guarded)
    monkeypatch.delenv(STRICT_ENV, raising=False)
    monkeypatch.setattr(config, "CHANNELS_FILE", tmp_path / "_Docs" / "channels.json")


def _table(tmp_path: Path, name: str = "items") -> DocumentTable:
    root = tmp_path / "_Docs"
    return DocumentTable(name, lambda: root / "store.db", lambda: root / f"{name}.json")


def _raw_rows(tmp_path: Path, name: str = "items") -> dict:
    conn = sqlite3.connect(str(tmp_path / "_Docs" / "store.db"))
    try:
        return {row[0]: row[1] for row in conn.execute(f"SELECT id, data FROM {name}")}
    finally:
        conn.close()


def _seed(table: DocumentTable) -> None:
    table.save(
        [
            {"id": "a1", "channel_id": "a", "n": 0},
            {"id": "a2", "channel_id": "a", "n": 0},
            {"id": "b1", "channel_id": "b", "n": 0},
            {"id": "legacy1", "n": 0},
        ]
    )


# --------------------------------------------------------------------------- scoped view


def test_scoped_view_exposes_only_own_rows_and_flushes_only_them(tmp_path):
    table = _table(tmp_path)
    _seed(table)
    before = _raw_rows(tmp_path)
    with table.scoped_mutate("a") as rows:
        assert sorted(r["id"] for r in rows) == ["a1", "a2"]
        assert sorted(r["id"] for r in rows.out_of_scope) == ["b1", "legacy1"]
        rows[0]["n"] = 1
        # private copies: editing them must never be written
        for other in rows.out_of_scope:
            other["n"] = 999
        rows.append({"id": "a3", "channel_id": "a", "n": 0})
    after = _raw_rows(tmp_path)
    assert after["b1"] == before["b1"]
    assert after["legacy1"] == before["legacy1"]
    assert json.loads(after["a3"])["channel_id"] == "a"
    assert sum(json.loads(after[k])["n"] for k in ("a1", "a2")) == 1


def test_scoped_delete_only_removes_own_rows(tmp_path):
    table = _table(tmp_path)
    _seed(table)
    with table.scoped_mutate("a") as rows:
        rows[:] = []  # "delete everything I can see"
    assert sorted(_raw_rows(tmp_path)) == ["b1", "legacy1"]


def test_include_legacy_controls_legacy_visibility(tmp_path):
    table = _table(tmp_path)
    _seed(table)
    assert sorted(r["id"] for r in table.scoped_load("main", include_legacy=True)) == ["legacy1"]
    assert table.scoped_load("main", include_legacy=False) == []
    with table.scoped_mutate("main", include_legacy=True) as rows:
        rows[0]["n"] = 5
    legacy = json.loads(_raw_rows(tmp_path)["legacy1"])
    assert legacy == {"id": "legacy1", "n": 5}  # still legacy: no owner stamped


# --------------------------------------------------------------------------- isolation violations


@pytest.mark.parametrize(
    "mutation",
    [
        "add_foreign_id",
        "add_unowned",
        "add_other_owner",
        "owner_change",
        "owner_drop",
        "stamp_legacy",
    ],
)
def test_isolation_violation_rolls_back_everything(tmp_path, mutation):
    table = _table(tmp_path)
    _seed(table)
    mirror = tmp_path / "_Docs" / "items.json"
    before_rows = _raw_rows(tmp_path)
    before_mirror = mirror.read_bytes()
    scope, legacy = ("main", True) if mutation == "stamp_legacy" else ("a", False)
    with pytest.raises(ChannelIsolationError) as info:
        with table.scoped_mutate(scope, include_legacy=legacy) as rows:
            # legitimate in-scope edits in the same block must be rolled back too
            for row in rows:
                row["n"] = 42
            if mutation == "add_foreign_id":
                rows.append({"id": "b1", "channel_id": "a", "n": 1})
            elif mutation == "add_unowned":
                rows.append({"id": "x1", "n": 1})
            elif mutation == "add_other_owner":
                rows.append({"id": "x1", "channel_id": "b", "n": 1})
            elif mutation == "owner_change":
                rows[0]["channel_id"] = "b"
            elif mutation == "owner_drop":
                rows[0].pop("channel_id")
            elif mutation == "stamp_legacy":
                rows[0]["channel_id"] = "main"
    assert info.value.record_ids
    assert _raw_rows(tmp_path) == before_rows  # zero rows written
    assert mirror.read_bytes() == before_mirror  # mirror untouched


def test_commit_reverifies_rows_against_the_database(tmp_path):
    """Defence in depth: a row that is no longer in scope at commit time (here
    re-owned through the raw connection inside the same transaction) is never
    written, even though the in-memory view still holds it."""
    table = _table(tmp_path)
    _seed(table)
    with pytest.raises(ChannelIsolationError):
        with table.scoped_mutate("a") as rows:
            conn = table._conn()
            conn.execute(
                "UPDATE items SET data = ? WHERE id = 'a1'",
                (json.dumps({"id": "a1", "channel_id": "b", "n": 0}),),
            )
            next(r for r in rows if r["id"] == "a1")["n"] = 7
    stored = json.loads(_raw_rows(tmp_path)["a1"])
    assert stored == {"id": "a1", "channel_id": "a", "n": 0}  # whole transaction rolled back


def test_batch_with_one_foreign_item_writes_nothing(tmp_path):
    """AC03: a batch for A that sneaks in an item of B is rejected before any
    write -- A's own items in the same batch are not applied either."""
    table = _table(tmp_path)
    _seed(table)
    before = _raw_rows(tmp_path)
    batch = ["a1", "a2", "b1"]
    with pytest.raises(ChannelIsolationError):
        with table.scoped_mutate("a") as rows:
            by_id = {r["id"]: r for r in rows}
            for item_id in batch:
                if item_id in by_id:
                    by_id[item_id]["n"] += 1
                else:  # not visible -> a caller trying to force it in
                    rows.append({"id": item_id, "channel_id": "a", "n": 1})
    assert _raw_rows(tmp_path) == before


def test_duplicate_ids_in_view_are_refused(tmp_path):
    table = _table(tmp_path)
    _seed(table)
    before = _raw_rows(tmp_path)
    with pytest.raises(ValueError):
        with table.scoped_mutate("a") as rows:
            rows.append(dict(rows[0]))
    assert _raw_rows(tmp_path) == before


def test_unchanged_block_does_not_rewrite_mirror(tmp_path):
    table = _table(tmp_path)
    _seed(table)
    mirror = tmp_path / "_Docs" / "items.json"
    stamp = mirror.stat().st_mtime_ns
    with table.scoped_mutate("a"):
        pass
    assert mirror.stat().st_mtime_ns == stamp


# --------------------------------------------------------------------------- concurrency


def test_concurrent_scoped_writers_lose_no_update(tmp_path):
    table = _table(tmp_path)
    _seed(table)
    rounds = 40
    errors = []

    def worker(channel: str, record_id: str, legacy: bool = False):
        try:
            for _ in range(rounds):
                with table.scoped_mutate(channel, include_legacy=legacy) as rows:
                    next(r for r in rows if r["id"] == record_id)["n"] += 1
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    def unscoped_worker():
        try:
            for _ in range(rounds):
                with table.mutate() as rows:
                    next(r for r in rows if r["id"] == "legacy1")["n"] += 1
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=("a", "a1")),
        threading.Thread(target=worker, args=("b", "b1")),
        threading.Thread(target=worker, args=("a", "a2")),
        threading.Thread(target=unscoped_worker),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert not errors, errors
    rows = {k: json.loads(v) for k, v in _raw_rows(tmp_path).items()}
    assert {k: v["n"] for k, v in rows.items()} == {"a1": rounds, "a2": rounds, "b1": rounds, "legacy1": rounds}
    assert {k: v.get("channel_id") for k, v in rows.items()} == {"a1": "a", "a2": "a", "b1": "b", "legacy1": None}
    mirror = json.loads((tmp_path / "_Docs" / "items.json").read_text(encoding="utf-8"))
    assert {r["id"]: r["n"] for r in mirror} == {"a1": rounds, "a2": rounds, "b1": rounds, "legacy1": rounds}


# --------------------------------------------------------------------------- JSON mirror


def test_mirror_keeps_all_channels_and_reload_does_not_resurrect(tmp_path):
    table = _table(tmp_path)
    _seed(table)
    mirror = tmp_path / "_Docs" / "items.json"
    with table.scoped_mutate("a") as rows:
        rows[:] = [r for r in rows if r["id"] != "a2"]
        rows[0]["n"] = 3
    data = json.loads(mirror.read_text(encoding="utf-8"))
    assert sorted(r["id"] for r in data) == ["a1", "b1", "legacy1"]
    # a later load (and a later scoped write by B) neither re-imports the
    # mirror over the db nor brings the deleted row back
    assert sorted(r["id"] for r in table.load()) == ["a1", "b1", "legacy1"]
    with table.scoped_mutate("b") as rows:
        rows[0]["n"] = 9
    assert sorted(r["id"] for r in table.load()) == ["a1", "b1", "legacy1"]
    assert {r["id"]: r["n"] for r in json.loads(mirror.read_text(encoding="utf-8"))} == {"a1": 3, "b1": 9, "legacy1": 0}


def test_hand_edited_mirror_import_keeps_every_channel(tmp_path):
    table = _table(tmp_path)
    _seed(table)
    mirror = tmp_path / "_Docs" / "items.json"
    data = json.loads(mirror.read_text(encoding="utf-8"))
    data.append({"id": "b2", "channel_id": "b", "n": 0, "pad": "x" * 7})
    mirror.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    assert sorted(r["id"] for r in table.scoped_load("b")) == ["b1", "b2"]
    assert sorted(r["id"] for r in table.scoped_load("a")) == ["a1", "a2"]


# --------------------------------------------------------------------------- nested writes


def test_nested_write_on_shared_connection_is_refused_cleanly(tmp_path):
    outer = _table(tmp_path, "items")
    inner = _table(tmp_path, "others")
    _seed(outer)
    inner.save([{"id": "o1", "channel_id": "a"}])
    with outer.scoped_mutate("a") as rows:
        rows[0]["n"] = 1
        with pytest.raises(NestedTransactionError) as info:
            with inner.mutate() as other_rows:
                other_rows.append({"id": "o2"})  # pragma: no cover
        assert isinstance(info.value, sqlite3.OperationalError)  # old handlers still match
        with pytest.raises(NestedTransactionError):
            with inner.scoped_mutate("a"):
                pass  # pragma: no cover
        with pytest.raises(NestedTransactionError):
            inner.save([])
        # a nested READ still works and never tries to import a newer mirror
        mirror = tmp_path / "_Docs" / "others.json"
        mirror.write_text(json.dumps([{"id": "o1", "channel_id": "a"}, {"id": "zz"}]), encoding="utf-8")
        assert [r["id"] for r in inner.load()] == ["o1"]
    assert json.loads(_raw_rows(tmp_path)["a1"])["n"] == 1  # outer committed normally
    assert sorted(r["id"] for r in inner.load()) == ["o1", "zz"]  # imported on next top-level read


# --------------------------------------------------------------------------- store scope rules


def test_resolve_store_scope_compat_and_strict(monkeypatch):
    compat_main = co.resolve_store_scope("main")
    assert (compat_main.channel_id, compat_main.include_legacy) == ("main", True)
    other = co.resolve_store_scope("second")
    assert (other.channel_id, other.include_legacy) == ("second", False)
    unscoped = co.resolve_store_scope(None)
    assert unscoped.unscoped and not unscoped.all_channels and unscoped.effective_owner == "main"
    everything = co.resolve_store_scope(None, all_channels=True)
    assert everything.unscoped and everything.all_channels and everything.effective_owner is None
    with pytest.raises(ValueError):
        co.resolve_store_scope("main", all_channels=True)
    for bad in ("Main", "", "x", "../a"):
        with pytest.raises(ChannelError) as info:
            co.resolve_store_scope(bad)
        assert info.value.code == "channel_scope_invalid"

    monkeypatch.setenv(STRICT_ENV, "1")
    with pytest.raises(ChannelError) as info:
        co.resolve_store_scope(None)
    assert (info.value.status_code, info.value.code) == (422, "channel_scope_missing")
    strict_main = co.resolve_store_scope("main")
    assert strict_main.include_legacy is False
    assert not strict_main.owns({"id": "legacy"})
    assert co.resolve_store_scope(None, all_channels=True).all_channels


def test_owner_helpers():
    scope = co.resolve_store_scope("second")
    assert co.owner_for_new_record(scope) == "second"
    assert co.owner_for_new_record(scope, "second") == "second"
    with pytest.raises(ChannelError) as info:
        co.owner_for_new_record(scope, "main")
    assert (info.value.status_code, info.value.code) == (422, "channel_scope_conflict")
    with pytest.raises(ValueError):
        co.owner_for_new_record(co.resolve_store_scope(None, all_channels=True))
    co.reject_owner_change({"channel_id": "a"}, "a")
    with pytest.raises(ChannelError) as info:
        co.reject_owner_change({"channel_id": "a"}, "b")
    assert info.value.code == "channel_id_immutable"
    with pytest.raises(ChannelError):
        co.reject_owner_change({}, "main")  # legacy -> main is a migration, not an edit
    co.reject_foreign_body_channel({"channel_id": "a"}, "a")
    co.reject_foreign_body_channel({"x": 1}, "a")
    with pytest.raises(ChannelError):
        co.reject_foreign_body_channel({"channel_id": "b"}, "a")


# --------------------------------------------------------------------------- repo rule


ALL_CHANNELS_RE = re.compile(r"all_channels\s*=\s*True")


def test_all_channels_only_in_allowlisted_modules():
    offenders = []
    for folder in ("scripts", "tools"):
        for path in (REPO / folder).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(REPO).as_posix()
            if ALL_CHANNELS_RE.search(path.read_text(encoding="utf-8", errors="replace")):
                if rel not in co.ALL_CHANNELS_ALLOWED_MODULES:
                    offenders.append(rel)
    assert offenders == [], f"all_channels=True outside the allowlist: {offenders}"
    route_modules = [m for m in co.ALL_CHANNELS_ALLOWED_MODULES if Path(m).name.startswith("api_")]
    assert route_modules == [], "route handler modules must never bypass channel scope"


def test_all_channels_guard_detects_a_new_offender(tmp_path):
    """The scanner itself works (guards against a regex that never matches)."""
    sample = "ProductStore.snapshot(all_channels = True)\n"
    assert ALL_CHANNELS_RE.search(sample)
    assert not ALL_CHANNELS_RE.search("ProductStore.snapshot(all_channels=False)")
