"""
reconcile_existing_projects() writes inside the store transaction now.

It was the one method left doing the pattern 83a9f1e removed everywhere
else -- `products = cls._load()` at the top, mutate, `cls._save(products)`
at the bottom, with the read outside any lock. get_all() calls it on every
product listing, and the UI polls every 1.5s while renders finish in the
background, so two callers could each read the same list and one silently
drop the other's reconciliation. No second user required.

The commit-only-when-changed behaviour matters as much as the transaction:
holding the write lock is fine, but rewriting every row and touching the
JSON mirror on each poll would be pure churn, since the scan finds nothing
to change almost every time.
"""
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.product_store as ps


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Point the store and its disk scan at tmp_path.

    Both names are bound at import in product_store, so patching
    scripts.config would not reach them.
    """
    monkeypatch.setattr(ps, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    assert ps.BASE_DIR == tmp_path, "the BASE_DIR patch did not take"
    return tmp_path


def _project(base, name, *, angle_id, product_id, with_export=False):
    """A rendered project folder the way the pipeline leaves one."""
    pdir = base / "03_Projects" / name
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "project.json").write_text(
        json.dumps({
            "project_name": name,
            "render_params": {"product_id": product_id, "angle_id": angle_id},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    if with_export:
        exports = base / "04_Exports" / "Ready_to_post"
        exports.mkdir(parents=True, exist_ok=True)
        (exports / f"{name}.mp4").write_bytes(b"\x00" * 64)
    return pdir


def test_no_project_folder_leaves_the_store_alone(isolated_store):
    """The early return happens before the write lock is taken."""
    product = ps.ProductStore.add(name="Widget", url="https://x.test/w")
    before = ps.ProductStore.get(product["id"])

    assert ps.ProductStore.reconcile_existing_projects() is False
    assert ps.ProductStore.get(product["id"]) == before


def test_an_unchanged_scan_does_not_rewrite_the_json_mirror(isolated_store):
    """The common case: nothing to reconcile, so nothing should be written.

    get_all() runs this on every listing; if it committed regardless, the
    mirror's mtime would move every time the UI polled.
    """
    ps.ProductStore.add(name="Widget", url="https://x.test/w")
    (isolated_store / "03_Projects").mkdir(parents=True, exist_ok=True)

    # Settle any write from the add above, then watch the mirror.
    ps.ProductStore.reconcile_existing_projects()
    mirror = ps.STORE_PATH
    assert mirror.exists(), "the JSON mirror should exist after a write"
    before = mirror.stat().st_mtime_ns

    for _ in range(3):
        assert ps.ProductStore.reconcile_existing_projects() is False

    assert mirror.stat().st_mtime_ns == before, (
        "an unchanged reconcile rewrote the mirror"
    )


def test_a_real_reconciliation_still_persists(isolated_store):
    """The transaction must not swallow an actual change."""
    product = ps.ProductStore.add(name="Widget", url="https://x.test/w")
    angles = [{
        "angle_id": "pain_point",
        "hook_title": "ปัญหาก่อนใช้",
        "status": "scripted",
        "script_lines": ["a", "b"],
    }]
    ps.ProductStore.update(product["id"], angles=angles)

    _project(
        isolated_store, "widget_1",
        angle_id="pain_point", product_id=product["id"], with_export=True,
    )

    assert ps.ProductStore.reconcile_existing_projects() is True

    angle = ps.ProductStore.get(product["id"])["angles"][0]
    assert angle["project_name"] == "widget_1"
    assert angle["status"] != "scripted", "the status should have advanced"

    # And it is durable, not just in memory.
    reloaded = json.loads(ps.STORE_PATH.read_text(encoding="utf-8"))
    assert reloaded[0]["angles"][0]["project_name"] == "widget_1"


def test_a_concurrent_write_is_not_lost_to_the_scan(isolated_store):
    """A reconcile and an unrelated write must both survive.

    Before the fix the scan read the list outside any lock, so a write that
    landed while it scanned the disk was overwritten by its own _save().
    """
    product = ps.ProductStore.add(name="Widget", url="https://x.test/w")
    ps.ProductStore.update(product["id"], angles=[{
        "angle_id": "pain_point",
        "hook_title": "ปัญหาก่อนใช้",
        "status": "scripted",
        "script_lines": ["a"],
    }])
    _project(
        isolated_store, "widget_1",
        angle_id="pain_point", product_id=product["id"], with_export=True,
    )

    barrier = threading.Barrier(2)
    errors = []

    def reconcile():
        try:
            barrier.wait(timeout=10)
            ps.ProductStore.reconcile_existing_projects()
        except Exception as e:  # pragma: no cover - surfaced via `errors`
            errors.append(e)

    def add_another():
        try:
            barrier.wait(timeout=10)
            ps.ProductStore.add(name="Second", url="https://x.test/second")
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=reconcile), threading.Thread(target=add_another)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"a writer raised: {errors}"

    names = {p["name"] for p in ps.ProductStore.get_all()}
    assert names == {"Widget", "Second"}, (
        f"a concurrent write was lost: {names}"
    )
