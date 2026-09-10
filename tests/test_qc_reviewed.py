"""
Regression: a freshly-rendered clip showed the same blue "QC ผ่าน" badge as
one a human had actually reviewed and approved. qc_note (a rejection reason)
was the only signal the UI had -- absent by default on a brand new render,
which read as "passed" even though nobody had looked at it yet.

Fix: a separate qc_reviewed flag, set only when a human clicks "QC ผ่าน"
(mark_qc_passed=True), and reset to False whenever the rendered video_url
actually changes or a qc_note is freshly set -- either one makes whatever
review happened before stale.

Uses tmp_path + monkeypatch on product_store.STORE_PATH/BASE_DIR, same
isolation pattern as tests/test_reconcile_grace_period.py and
tests/test_reroll_status_sync.py -- update_angle_status() goes through
ProductStore._mutate() (the SQLite-backed table), not the legacy
_load()/_save() pair, so those are what must be patched, not the latter.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_store
from scripts.product_store import ProductStore
from scripts.api_server import app


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(product_store, "BASE_DIR", tmp_path)
    assert product_store.BASE_DIR == tmp_path, "the BASE_DIR patch did not take"
    return tmp_path


def _seed_product_with_angle(**overrides):
    angle = {
        "angle_id": "review",
        "hook_title": "รีวิว",
        "status": "rendered",
        "video_url": "04_Exports/Ready_to_post/DEMO01-review_1_v1.mp4",
        "qc_note": None,
        "qc_reviewed": False,
    }
    angle.update(overrides)
    product = ProductStore.add(name="Widget", url=f"https://x.test/{overrides.get('angle_id', 'w')}-{id(angle)}")
    ProductStore.update(product["id"], angles=[angle])
    return product["id"]


def test_mark_qc_passed_sets_qc_reviewed(isolated_store):
    product_id = _seed_product_with_angle()

    updated = ProductStore.update_angle_status(
        product_id, "review", "rendered",
        clear_qc_note=True, mark_qc_passed=True,
    )

    angle = updated["angles"][0]
    assert angle["qc_reviewed"] is True
    assert angle["qc_note"] is None


def test_qc_reviewed_stays_false_without_mark_qc_passed(isolated_store):
    """Merely re-saving status="rendered" (e.g. a routine sync) must not by
    itself flip an unreviewed clip to "reviewed" -- only an explicit
    mark_qc_passed=True (the actual button click) may do that."""
    product_id = _seed_product_with_angle()

    updated = ProductStore.update_angle_status(product_id, "review", "rendered")

    assert updated["angles"][0]["qc_reviewed"] is False


def test_new_render_resets_qc_reviewed(isolated_store):
    """A previously-approved angle gets re-rendered (new video_url) -- the
    old approval must not silently carry over to output nobody has seen."""
    product_id = _seed_product_with_angle(qc_reviewed=True)

    updated = ProductStore.update_angle_status(
        product_id, "review", "rendered",
        video_url="04_Exports/Ready_to_post/DEMO01-review_1_v2.mp4",
    )

    angle = updated["angles"][0]
    assert angle["qc_reviewed"] is False
    assert angle["video_url"] == "04_Exports/Ready_to_post/DEMO01-review_1_v2.mp4"


def test_same_video_url_does_not_reset_qc_reviewed(isolated_store):
    """Passing back the SAME video_url (e.g. an unrelated field update) must
    not spuriously un-approve an already-reviewed clip."""
    product_id = _seed_product_with_angle(qc_reviewed=True)

    updated = ProductStore.update_angle_status(
        product_id, "review", "rendered",
        video_url="04_Exports/Ready_to_post/DEMO01-review_1_v1.mp4",
    )

    assert updated["angles"][0]["qc_reviewed"] is True


def test_rejecting_qc_resets_qc_reviewed(isolated_store):
    """Setting a fresh qc_note (a rejection) must un-approve the clip even
    if it had somehow been marked reviewed before."""
    product_id = _seed_product_with_angle(qc_reviewed=True)

    updated = ProductStore.update_angle_status(
        product_id, "review", "in_production",
        qc_note="เสียงเบาไป",
    )

    angle = updated["angles"][0]
    assert angle["qc_reviewed"] is False
    assert angle["qc_note"] == "เสียงเบาไป"


def test_api_endpoint_accepts_mark_qc_passed(isolated_store):
    product_id = _seed_product_with_angle()
    client = TestClient(app)

    response = client.patch(
        f"/api/products/{product_id}/angles/review",
        json={"status": "rendered", "clear_qc_note": True, "mark_qc_passed": True},
    )

    assert response.status_code == 200, response.text
    assert response.json()["product"]["angles"][0]["qc_reviewed"] is True
