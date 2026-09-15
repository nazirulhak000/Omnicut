"""
Regression tests for the JSON -> SQLite persistence swap behind ProductStore
and PostLog (scripts/db.py).

Covers, per the task:
  - Every store method still behaves identically (round-trips through the
    new SQLite-backed _load()/_save(), same shapes, same errors).
  - The lost-update race (SAAS_READINESS_PLAN.md P0 item 1) is actually gone:
    concurrent writers no longer silently clobber each other.
  - The migration script imports real-shaped records losslessly and is
    idempotent.
  - New ids (uuid4 hex) don't collide, including under concurrent creation.

Uses tmp_path + monkeypatch throughout, per .agents/rules/testing_standard.md
rule 3 -- never touches the real _Docs/products.json or _Docs/post_log.json.
"""
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import post_log as pl
from scripts import product_store as ps
from scripts import migrate_json_to_sqlite as mig


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Redirect both stores' STORE_PATH/LOG_PATH/BASE_DIR into tmp_path, and
    point the migration script's module-level path references there too."""
    store_path = tmp_path / "_Docs" / "products.json"
    log_path = tmp_path / "_Docs" / "post_log.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    monkeypatch.setattr(pl, "LOG_PATH", log_path)
    monkeypatch.setattr(mig, "STORE_PATH", store_path)
    monkeypatch.setattr(mig, "LOG_PATH", log_path)
    return tmp_path


# ----------------------------------------------------------------------
# Behavior parity: SQLite-backed stores behave exactly as the JSON version
# ----------------------------------------------------------------------

def test_add_persists_and_get_round_trips(isolated_store):
    product = ps.ProductStore.add(name="Widget", url="https://x.test/widget")
    assert product["status"] == "candidate"
    assert product["id"]  # non-empty id assigned

    fetched = ps.ProductStore.get(product["id"])
    assert fetched is not None
    assert fetched["name"] == "Widget"
    assert fetched["url"] == "https://x.test/widget"


def test_add_same_url_twice_updates_existing_instead_of_duplicating(isolated_store):
    first = ps.ProductStore.add(name="Widget", url="https://x.test/widget")
    second = ps.ProductStore.add(
        name="Widget Renamed",
        url="https://x.test/widget",
        angles=[{"angle_id": "a1", "status": "scripted"}],
    )
    assert second["id"] == first["id"]
    assert second["status"] == "scripted"
    assert len(ps.ProductStore._load()) == 1


def test_update_rejects_invalid_status_and_leaves_record_unchanged(isolated_store):
    product = ps.ProductStore.add(name="Widget")
    with pytest.raises(ValueError):
        ps.ProductStore.update(product["id"], status="not_a_real_status")

    # The transaction must not have partially applied -- the record on disk
    # (and in SQLite) should be exactly what it was before the failed update.
    unchanged = ps.ProductStore.get(product["id"])
    assert unchanged["status"] == "candidate"


def test_update_angle_status_sets_posted_at_once(isolated_store):
    product = ps.ProductStore.add(
        name="Widget",
        angles=[{"angle_id": "a1", "status": "rendered"}],
    )
    updated = ps.ProductStore.update_angle_status(product["id"], "a1", "posted")
    angle = updated["angles"][0]
    assert angle["status"] == "posted"
    assert angle["posted_at"]

    posted_at_first = angle["posted_at"]
    # Calling again with status already "posted" must not stomp posted_at.
    updated_again = ps.ProductStore.update_angle_status(product["id"], "a1", "posted")
    assert updated_again["angles"][0]["posted_at"] == posted_at_first


def test_delete_removes_product_and_raises_for_unknown_id(isolated_store):
    product = ps.ProductStore.add(name="Widget")
    ps.ProductStore.delete(product["id"])
    assert ps.ProductStore.get(product["id"]) is None

    with pytest.raises(ValueError):
        ps.ProductStore.delete("does-not-exist")


def test_underscore_load_save_still_used_directly_by_external_callers(isolated_store):
    """api_videos.py and backfill_product_codes.py call ProductStore._load()/
    _save() directly (not through a public method), mutating the returned
    dicts in place and passing the same list back to _save(). This pattern
    must keep working exactly as before."""
    ps.ProductStore.add(name="Widget", url="https://x.test/1")
    ps.ProductStore.add(name="Gadget", url="https://x.test/2")

    products = ps.ProductStore._load()
    assert len(products) == 2
    for p in products:
        p["videos"].append({"path": "C:/fake.mp4", "rel_path": "fake.mp4"})
    ps.ProductStore._save(products)

    reloaded = ps.ProductStore._load()
    assert all(len(p["videos"]) == 1 for p in reloaded)


def test_postlog_add_and_update_metrics_round_trip(isolated_store):
    post = pl.PostLog.add_post(product_name="Widget", clip_file="clip.mp4")
    assert post["metrics"] is None

    updated = pl.PostLog.update_metrics(post["id"], {"views": "100", "orders": "3", "commission_thb": "50.5"})
    assert updated["metrics"] == {"views": 100, "orders": 3, "commission_thb": 50.5}

    with pytest.raises(ValueError):
        pl.PostLog.update_metrics(post["id"], {"views": "not-a-number"})

    with pytest.raises(ValueError):
        pl.PostLog.update_metrics("missing-id", {"views": "1"})


def test_postlog_angle_performance_and_summary(isolated_store):
    p1 = pl.PostLog.add_post(product_name="A", clip_file="a.mp4", angle_key="pain_point", angle_title="Pain")
    pl.PostLog.update_metrics(p1["id"], {"views": "1000", "cart_clicks": "10", "orders": "2", "commission_thb": "60"})
    p2 = pl.PostLog.add_post(product_name="B", clip_file="b.mp4", angle_key="pain_point", angle_title="Pain")
    pl.PostLog.update_metrics(p2["id"], {"views": "2000", "cart_clicks": "20", "orders": "4", "commission_thb": "120"})

    perf = pl.PostLog.angle_performance()
    assert len(perf) == 1
    bucket = perf[0]
    assert bucket["clips"] == 2
    assert bucket["views"] == 3000
    assert bucket["commission_thb"] == 180.0

    summary = pl.PostLog.summary()
    assert summary["total_posted"] == 2
    assert summary["measured"] == 2
    assert summary["total_orders"] == 6


# ----------------------------------------------------------------------
# JSON-file mirroring: seeded-by-file tests and file-as-backup both hold
# ----------------------------------------------------------------------

def test_seeding_via_raw_json_file_write_is_picked_up_by_load(isolated_store, tmp_path):
    """Several existing tests (test_product_code.py, test_reconcile_*.py,
    ...) seed products.json by writing JSON straight to STORE_PATH and then
    call into ProductStore. The SQLite-backed store must still see that."""
    (tmp_path / "_Docs").mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(
        json.dumps([{"id": "seeded-1", "name": "Seeded Product", "status": "candidate", "angles": []}]),
        encoding="utf-8",
    )

    loaded = ps.ProductStore.get("seeded-1")
    assert loaded is not None
    assert loaded["name"] == "Seeded Product"


def test_save_mirrors_to_json_file_on_disk(isolated_store):
    product = ps.ProductStore.add(name="Widget")
    on_disk = json.loads(ps.STORE_PATH.read_text(encoding="utf-8"))
    assert len(on_disk) == 1
    assert on_disk[0]["id"] == product["id"]
    assert on_disk[0]["name"] == "Widget"


def test_mutate_flushes_only_changed_rows(isolated_store):
    """The list-shaped mutate API remains compatible while its SQLite flush
    is row-scoped. A one-record patch must not rewrite the whole table, since
    that expands lock/write work with every unrelated product in the store."""
    table = ps._TABLE
    table.save([
        {"id": "p1", "name": "One"},
        {"id": "p2", "name": "Two"},
        {"id": "p3", "name": "Three"},
    ])
    conn = table._conn()
    statements = []
    conn.set_trace_callback(statements.append)
    try:
        with table.mutate() as records:
            next(record for record in records if record["id"] == "p2")["name"] = "Updated"
    finally:
        conn.set_trace_callback(None)

    table_name_sql = "products"
    writes = [statement.upper() for statement in statements if table_name_sql in statement.lower()]
    assert any("UPDATE PRODUCTS SET" in statement and "WHERE ID = 'P2'" in statement for statement in writes)
    assert not any("DELETE FROM PRODUCTS" in statement for statement in writes)
    assert not any("INSERT INTO PRODUCTS" in statement for statement in writes)
    assert table.load() == [
        {"id": "p1", "name": "One"},
        {"id": "p2", "name": "Updated"},
        {"id": "p3", "name": "Three"},
    ]


# ----------------------------------------------------------------------
# The lost-update race (P0 item 1) is fixed
# ----------------------------------------------------------------------

def test_concurrent_add_does_not_lose_either_write(isolated_store):
    """Before the fix: _load() ran outside the lock. Two threads could both
    read the same product list, both append a different new product, and
    whichever _save() ran last would silently overwrite the other's row --
    no error, no log. With _mutate() holding one SQLite transaction across
    the whole read-modify-write, a concurrent writer must block until the
    first one commits, so both new products must survive."""
    barrier = threading.Barrier(2)
    errors = []

    def add_one(name):
        try:
            barrier.wait(timeout=5)
            ps.ProductStore.add(name=name, url=f"https://x.test/{name}")
        except Exception as e:  # pragma: no cover - failure path
            errors.append(e)

    threads = [threading.Thread(target=add_one, args=(f"Product-{i}",)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors
    products = ps.ProductStore._load()
    assert len(products) == 2
    assert {p["name"] for p in products} == {"Product-0", "Product-1"}


def test_concurrent_updates_to_different_products_both_survive(isolated_store):
    """A more direct simulation of the scenario described in the plan: two
    concurrent writers, each updating a DIFFERENT existing product. Under
    the old bug, A reads all products, B reads all products, A saves its
    change, then B's save (built from B's now-stale read) overwrites A's
    change back out. This must no longer happen."""
    p1 = ps.ProductStore.add(name="Product A")
    p2 = ps.ProductStore.add(name="Product B")

    barrier = threading.Barrier(2)
    errors = []

    def do_update(product_id, new_status):
        try:
            barrier.wait(timeout=5)
            ps.ProductStore.update(product_id, status=new_status)
        except Exception as e:  # pragma: no cover - failure path
            errors.append(e)

    t1 = threading.Thread(target=do_update, args=(p1["id"], "scripted"))
    t2 = threading.Thread(target=do_update, args=(p2["id"], "in_production"))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not errors
    reloaded_1 = ps.ProductStore.get(p1["id"])
    reloaded_2 = ps.ProductStore.get(p2["id"])
    assert reloaded_1["status"] == "scripted"
    assert reloaded_2["status"] == "in_production"


def test_concurrent_add_post_creates_no_duplicate_and_no_lost_row(isolated_store):
    """Same race, for PostLog.add_post -- and simultaneously proves the new
    id scheme (uuid4 hex) does not collide even when many rows are added at
    once, unlike the old f'{timestamp}_{len(posts)+1}' scheme which collided
    whenever two adds landed in the same second at the same list length."""
    barrier = threading.Barrier(8)
    errors = []

    def add_one(i):
        try:
            barrier.wait(timeout=5)
            pl.PostLog.add_post(product_name=f"P{i}", clip_file=f"clip{i}.mp4")
        except Exception as e:  # pragma: no cover - failure path
            errors.append(e)

    threads = [threading.Thread(target=add_one, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors
    posts = pl.PostLog._load()
    assert len(posts) == 8
    ids = [p["id"] for p in posts]
    assert len(ids) == len(set(ids))  # no id collisions


# ----------------------------------------------------------------------
# New id scheme: uuid4 hex, no collisions
# ----------------------------------------------------------------------

def test_new_product_ids_are_uuid4_hex_not_timestamp_based(isolated_store):
    import re
    product = ps.ProductStore.add(name="Widget")
    # 32 lowercase hex chars, no underscore/timestamp shape like the old
    # f"{timestamp}_{len(products)+1}" scheme.
    assert re.fullmatch(r"[0-9a-f]{32}", product["id"])


def test_new_post_ids_are_uuid4_hex(isolated_store):
    import re
    post = pl.PostLog.add_post(product_name="Widget", clip_file="clip.mp4")
    assert re.fullmatch(r"[0-9a-f]{32}", post["id"])


def test_many_rapid_adds_produce_unique_ids(isolated_store):
    """Regression for the exact collision described in the plan: adding two
    records in the same second at the same list length used to produce the
    same id. uuid4 has no such dependency on timing or list length."""
    ids = [ps.ProductStore.add(name=f"P{i}")["id"] for i in range(50)]
    assert len(ids) == len(set(ids))


# ----------------------------------------------------------------------
# Migration: lossless + idempotent
# ----------------------------------------------------------------------

def _real_products_fixture_path() -> Path:
    return ROOT / "_Docs" / "products.json"


def _real_post_log_fixture_path() -> Path:
    return ROOT / "_Docs" / "post_log.json"


def test_migration_imports_real_shaped_product_records_losslessly(isolated_store, tmp_path):
    real_path = _real_products_fixture_path()
    if not real_path.exists():
        pytest.skip("no real _Docs/products.json present in this checkout")

    original_bytes = real_path.read_bytes()
    original_records = json.loads(original_bytes)

    # Copy the real file's bytes into the isolated STORE_PATH -- this reads
    # the real file but never writes to it, and the isolated_store fixture
    # already redirected ps.STORE_PATH/mig.STORE_PATH into tmp_path.
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_bytes(original_bytes)

    rc = mig.migrate(dry_run=False)
    assert rc == 0

    # The copy in tmp_path must be untouched by the migration itself.
    assert ps.STORE_PATH.read_bytes() == original_bytes
    # And the real file on disk was never opened for writing.
    assert real_path.read_bytes() == original_bytes

    imported = {p["id"]: p for p in ps.ProductStore._load()}
    for record in original_records:
        assert record["id"] in imported, f"id {record['id']!r} missing after migration"
        assert imported[record["id"]] == record, f"record {record['id']!r} changed by migration"


def test_migration_imports_real_shaped_post_records_losslessly(isolated_store, tmp_path):
    real_path = _real_post_log_fixture_path()
    if not real_path.exists():
        pytest.skip("no real _Docs/post_log.json present in this checkout")

    original_bytes = real_path.read_bytes()
    original_records = json.loads(original_bytes)

    pl.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    pl.LOG_PATH.write_bytes(original_bytes)

    rc = mig.migrate(dry_run=False)
    assert rc == 0
    assert pl.LOG_PATH.read_bytes() == original_bytes
    assert real_path.read_bytes() == original_bytes

    imported = {p["id"]: p for p in pl.PostLog._load()}
    for record in original_records:
        assert record["id"] in imported
        assert imported[record["id"]] == record


def test_migration_is_idempotent(isolated_store):
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(
        json.dumps([
            {"id": "p1", "name": "One", "status": "candidate", "angles": []},
            {"id": "p2", "name": "Two", "status": "scripted", "angles": []},
        ]),
        encoding="utf-8",
    )

    for _ in range(3):
        rc = mig.migrate(dry_run=False)
        assert rc == 0
        products = ps.ProductStore._load()
        assert len(products) == 2
        assert {p["id"] for p in products} == {"p1", "p2"}


def test_migration_dry_run_does_not_write_anything(isolated_store):
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(
        json.dumps([{"id": "p1", "name": "One", "status": "candidate", "angles": []}]),
        encoding="utf-8",
    )
    rc = mig.migrate(dry_run=True)
    assert rc == 0
    # dry-run must not create the sqlite file at all.
    db_path = ps.STORE_PATH.parent / "store.db"
    assert not db_path.exists()


def test_migration_preserves_existing_ids_does_not_regenerate_them(isolated_store):
    """Existing ids are referenced by project manifests and export
    filenames -- the migration must never mint new ids for pre-existing
    records, even ones using the OLD timestamp-based id scheme."""
    old_style_id = "20260904233315_1"
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(
        json.dumps([{"id": old_style_id, "name": "Legacy Product", "status": "candidate", "angles": []}]),
        encoding="utf-8",
    )
    rc = mig.migrate(dry_run=False)
    assert rc == 0
    assert ps.ProductStore.get(old_style_id) is not None
