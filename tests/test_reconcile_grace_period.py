"""
reconcile_existing_projects()'s "strict state validation" pass (and the
sibling "no exported MP4 yet" branch in _reconcile_into()) ran on EVERY
call -- which itself runs on every ProductStore.get()/get_all()/list(), i.e.
on every poll from the frontend. It treated "the file didn't resolve on
this one disk .exists() check" as identical to "this was never rendered":

    if angle.get("status") == "rendered" and not has_video:
        angle["status"] = "in_production" (or "scripted")
        angle["video_url"] = None

update_angle_status() commits status="rendered" successfully, and the very
next get()/get_all() call -- exactly what a caller does to confirm the
write, or what the next frontend poll does -- ran reconcile immediately
afterward. A single, non-retried .exists() check can miss a genuinely
just-written file for reasons that have nothing to do with whether it was
rendered (transient path-resolution mismatch, AV lock, a check that lands
before the write's fsync is visible), silently erasing a just-completed,
successfully-committed status write with no error raised anywhere.

The fix: angle["status_updated_at"], stamped by update_angle_status() (and
by reconcile's own promotion-to-rendered branch) every time status
actually changes, gives reconcile a grace period (60s) during which a
"rendered" status is not reverted even if this pass's own disk checks
(including the same-project glob fallback used elsewhere in the function)
come up empty. Only once that window has passed does reconcile trust a
persistently-missing file enough to revert the status -- proving the grace
period delays reconciliation rather than disabling it.

Uses tmp_path + monkeypatch on product_store.STORE_PATH/BASE_DIR and
project_manifest.PROJECTS_DIR, same isolation pattern as
tests/test_reroll_status_sync.py.
"""
import datetime
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_store
from scripts.product_store import ProductStore


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(product_store, "BASE_DIR", tmp_path)
    assert product_store.BASE_DIR == tmp_path, "the BASE_DIR patch did not take"
    # reconcile_existing_projects() only does anything once 03_Projects
    # exists -- without it, it early-returns before the strict-validation
    # pass ever runs, which would make these tests pass for the wrong
    # reason (never touching the code under test at all).
    (tmp_path / "03_Projects").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _seed_angle(product_id: str, angle_id: str = "unboxing"):
    ProductStore.update(product_id, angles=[{
        "angle_id": angle_id,
        "hook_title": "แกะกล่องว้าว",
        "status": "in_production",
        "script_lines": ["a"],
    }])


def test_freshly_rendered_status_survives_a_transient_disk_miss(isolated_store):
    """The core bug: update_angle_status("rendered") commits, then the very
    next ProductStore.get() -- simulating either the caller confirming its
    own write, or the next frontend poll -- must NOT see the status
    silently reverted just because no matching project folder or video file
    exists on disk for this angle (the transient-miss scenario: nothing was
    ever cleaned up wrong, the disk check for THIS angle just has nothing
    to find because the test deliberately creates no file)."""
    product = ProductStore.add(name="Widget", url="https://x.test/w1")
    _seed_angle(product["id"])

    updated = ProductStore.update_angle_status(
        product["id"], "unboxing", "rendered",
        video_url="04_Exports/Ready_to_post/widget_never_created.mp4",
        project_name="widget_never_created",
    )
    angle = next(a for a in updated["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "rendered"
    assert angle.get("status_updated_at"), "update_angle_status() must stamp status_updated_at"

    # No "widget_never_created" folder in 03_Projects and no matching mp4
    # anywhere under 04_Exports -- exactly the transient-miss shape: the
    # write really happened (status_updated_at is fresh), but this pass's
    # own disk checks find nothing for it.
    fetched = ProductStore.get(product["id"])
    fetched_angle = next(a for a in fetched["angles"] if a["angle_id"] == "unboxing")
    assert fetched_angle["status"] == "rendered", (
        "a status_updated_at within the grace period must not be reverted "
        f"by a single failed disk check, got {fetched_angle['status']!r}"
    )
    assert fetched_angle["video_url"] == "04_Exports/Ready_to_post/widget_never_created.mp4"

    # And it must keep surviving repeated polls within the grace window,
    # not just the first one.
    fetched_again = ProductStore.get(product["id"])
    angle_again = next(a for a in fetched_again["angles"] if a["angle_id"] == "unboxing")
    assert angle_again["status"] == "rendered"


def test_stale_rendered_status_still_gets_reverted_after_grace_period(isolated_store):
    """The other half: the grace period must delay reconciliation, not
    disable it. Once status_updated_at is old enough, a "rendered" angle
    with no project folder and no video file on disk anywhere DOES get
    reverted to "scripted" -- proving genuinely-stale/incorrect state is
    still cleaned up."""
    product = ProductStore.add(name="Widget", url="https://x.test/w2")
    _seed_angle(product["id"])

    ProductStore.update_angle_status(
        product["id"], "unboxing", "rendered",
        video_url="04_Exports/Ready_to_post/widget_old.mp4",
        project_name="widget_old",
    )

    # Backdate status_updated_at past RECONCILE_GRACE_PERIOD_SECONDS, as if
    # this status had genuinely been sitting for a long time with nothing
    # ever actually rendered (or the file was later removed).
    old_stamp = (
        datetime.datetime.now()
        - datetime.timedelta(seconds=product_store.RECONCILE_GRACE_PERIOD_SECONDS + 30)
    ).isoformat(timespec="seconds")
    with ProductStore._mutate() as products:
        for p in products:
            if p["id"] == product["id"]:
                for a in p["angles"]:
                    if a["angle_id"] == "unboxing":
                        a["status_updated_at"] = old_stamp

    fetched = ProductStore.get(product["id"])
    angle = next(a for a in fetched["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "scripted", (
        "an old status_updated_at must not block reconciliation forever, "
        f"got {angle['status']!r}"
    )
    assert angle["video_url"] is None
    assert angle["project_name"] is None


def test_missing_status_updated_at_does_not_crash_and_reconciles_normally(isolated_store):
    """Defensive parsing: an angle with no status_updated_at at all (e.g.
    data written before this field existed) must not crash reconcile --
    it's treated as "no grace period", so a genuinely-missing render still
    gets reverted exactly like before this fix."""
    product = ProductStore.add(name="Widget", url="https://x.test/w3")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "rendered",
        "video_url": "04_Exports/Ready_to_post/widget_legacy.mp4",
        "project_name": "widget_legacy",
        "script_lines": ["a"],
        # deliberately no status_updated_at
    }])

    fetched = ProductStore.get(product["id"])
    angle = next(a for a in fetched["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "scripted"


def test_reconcile_prefers_newest_export_when_multiple_candidates_exist(isolated_store):
    """A re-render without cleanup can leave more than one exported mp4 for
    the same project folder name. The glob-fallback lookup must prefer the
    most recently modified file, not whatever order glob() happens to
    return (candidates[0] off an unsorted list is non-deterministic)."""
    import time

    tmp_path = isolated_store
    project_name = "widget_multi"
    proj_dir = tmp_path / "03_Projects" / project_name
    proj_dir.mkdir(parents=True, exist_ok=True)

    product = ProductStore.add(name="Widget", url="https://x.test/w4")
    # "scripted" (not "in_production") -- an angle explicitly in_production
    # is intentionally never auto-promoted to "rendered" by reconcile (see
    # _reconcile_into's own comment on that branch); "scripted" is the
    # status this test actually needs to exercise the promotion-to-rendered
    # path where the multi-candidate glob fallback matters.
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "scripted",
        "script_lines": ["a"],
    }])

    ready_dir = tmp_path / "04_Exports" / "Ready_to_post"
    ready_dir.mkdir(parents=True, exist_ok=True)
    old_file = ready_dir / f"{project_name}_old.mp4"
    new_file = ready_dir / f"{project_name}_new.mp4"
    old_file.write_bytes(b"\x00" * 16)
    time.sleep(0.05)
    new_file.write_bytes(b"\x00" * 16)

    # Manifest names this angle so the authoritative-match path (condition
    # #1) picks it up, but points artifacts.mp4_video.path nowhere real --
    # forcing the glob fallback to decide between old_file and new_file.
    (proj_dir / "project.json").write_text(
        __import__("json").dumps({
            "render_params": {"product_id": product["id"], "angle_id": "unboxing"},
            "artifacts": {"mp4_video": {"path": str(tmp_path / "nope.mp4")}},
        }),
        encoding="utf-8",
    )

    fetched = ProductStore.get(product["id"])
    angle = next(a for a in fetched["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "rendered"
    assert angle["video_url"].endswith("_new.mp4"), (
        f"expected the newest export to win, got {angle['video_url']!r}"
    )
