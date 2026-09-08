"""
Regression test for Round POST-1.4: moving a clip to 04_Exports/Posted/ must
not make reconcile_existing_projects() think the export never happened.

Found by actually reading reconcile's no-mp4-found branch after wiring
mark-posted, rather than trusting that "reconcile preserves posted status"
(true only inside the if-mp4-found branch, at product_store.py:499) covered
this case too. It did not: the else branch unconditionally reset status to
"in_production" and video_url to None whenever it could not find an mp4 --
which is exactly what happens the instant a posted clip's file moves out of
Ready_to_post and its manifest's stale artifacts.mp4_video.path stops
resolving.

Uses tmp_path + monkeypatch throughout, per .agents/rules/testing_standard.md
rule 3 -- never touches the real _Docs/products.json or 03_Projects/.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_store as ps


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Real ProductStore/reconcile logic, entirely inside tmp_path."""
    # Must match where _seed() below actually writes -- BASE_DIR/_Docs/products.json,
    # same as the real STORE_PATH = BASE_DIR / "_Docs" / "products.json".
    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    return tmp_path


def _seed(tmp_path, *, angle_status, video_url):
    """One product/angle already linked to one project, plus that project's
    own manifest on disk -- the two things reconcile cross-references."""
    project_name = "demo_product_angle1_1"
    products = [{
        "id": "20260101000000_1",
        "name": "Demo Product",
        "angles": [{
            "angle_id": "angle1",
            "id": "angle1",
            "project_name": project_name,
            "status": angle_status,
            "video_url": video_url,
        }],
        "projects": [project_name],
    }]
    (tmp_path / "_Docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_Docs" / "products.json").write_text(
        json.dumps(products, ensure_ascii=False), encoding="utf-8",
    )

    project_dir = tmp_path / "03_Projects" / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.json").write_text(json.dumps({
        "script_data": {"hook": "test hook", "lines": []},
        "render_params": {"product_id": "20260101000000_1", "angle_id": "angle1"},
        # Stale on purpose: still points at Ready_to_post, the file has
        # already moved to Posted/ by the time reconcile runs.
        "artifacts": {"mp4_video": {"path": video_url}},
    }, ensure_ascii=False), encoding="utf-8")

    return project_name


def test_posted_status_survives_when_mp4_moved_to_posted_dir(isolated_store):
    tmp_path = isolated_store
    project_name = "demo_product_angle1_1"

    ready_path = tmp_path / "04_Exports" / "Ready_to_post" / f"{project_name}_20260101_000000.mp4"
    posted_dir = tmp_path / "04_Exports" / "Posted"
    posted_dir.mkdir(parents=True, exist_ok=True)
    posted_path = posted_dir / f"{project_name}_20260101_000000.mp4"

    _seed(tmp_path, angle_status="posted", video_url=str(ready_path))
    # The move itself: file physically at Posted/, manifest's own
    # artifacts.mp4_video.path is now a dead reference (mirrors what
    # api_exports.mark_posted's shutil.move produces before any manifest
    # patch-up).
    posted_path.write_bytes(b"fake mp4 bytes")

    changed = ps.ProductStore.reconcile_existing_projects()

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "posted", (
        f"reconcile downgraded a posted angle to {angle['status']!r} "
        "just because its stale artifacts path stopped resolving"
    )
    # video_url is allowed to update to the Posted/ file the widened scan
    # found, or to stay as-is -- either is fine. Going to None is not.
    assert angle["video_url"] is not None


def test_mobile_ready_status_also_survives(isolated_store):
    tmp_path = isolated_store
    project_name = "demo_product_angle1_1"
    ready_path = tmp_path / "04_Exports" / "Ready_to_post" / f"{project_name}_20260101_000000.mp4"

    _seed(tmp_path, angle_status="mobile_ready", video_url=str(ready_path))
    # Nothing on disk at all this time -- not in Ready_to_post, not in
    # Posted/, and the manifest path is stale. The most adversarial case:
    # reconcile truly cannot find the file anywhere.
    ps.ProductStore.reconcile_existing_projects()

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "mobile_ready"


def test_reconcile_still_promotes_a_genuinely_unrendered_project(isolated_store):
    """The fix must not swallow the real case it existed to catch: a project
    with no export anywhere and no advanced status stays in_production."""
    tmp_path = isolated_store
    _seed(tmp_path, angle_status="scripted", video_url=None)

    ps.ProductStore.reconcile_existing_projects()

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "in_production"
    assert angle["video_url"] is None


def test_reconcile_finds_mp4_that_moved_to_posted_dir_via_widened_scan(isolated_store):
    """When the manifest path is stale AND the angle is NOT yet in an
    advanced status, reconcile's fallback glob must check Posted/ too, not
    only Ready_to_post -- otherwise a file that moved (for any reason) before
    its manifest caught up looks identical to "never rendered"."""
    tmp_path = isolated_store
    project_name = "demo_product_angle1_1"
    stale_ready_path = tmp_path / "04_Exports" / "Ready_to_post" / f"{project_name}_stale.mp4"
    posted_dir = tmp_path / "04_Exports" / "Posted"
    posted_dir.mkdir(parents=True, exist_ok=True)
    (posted_dir / f"{project_name}_20260101_000000.mp4").write_bytes(b"fake mp4 bytes")

    _seed(tmp_path, angle_status="rendered", video_url=str(stale_ready_path))

    ps.ProductStore.reconcile_existing_projects()

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "rendered"
    assert "Posted" in angle["video_url"]


def test_reconcile_promotes_in_production_to_rendered_when_mp4_exists(isolated_store):
    """BUG-STATUS-1 regression: an angle stuck at in_production that already
    has a completed MP4 file on disk must be promoted to 'rendered' by
    reconcile_existing_projects(), not left permanently at in_production.

    Root cause: the previous guard at product_store.py:964 only synced
    video_url but never changed status when status == 'in_production'.
    This caused clips to stay at 'กำลังตัดต่อ' after a successful render.
    """
    tmp_path = isolated_store
    project_name = "demo_product_angle1_1"

    ready_dir = tmp_path / "04_Exports" / "Ready_to_post"
    ready_dir.mkdir(parents=True, exist_ok=True)
    mp4_file = ready_dir / f"{project_name}_20260908_172143.mp4"
    mp4_file.write_bytes(b"fake rendered mp4")

    # Angle is stuck at in_production even though the MP4 is present
    _seed(tmp_path, angle_status="in_production", video_url=str(mp4_file))

    ps.ProductStore.reconcile_existing_projects()

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "rendered", (
        f"Expected 'rendered' but got {angle['status']!r}: "
        "reconcile failed to promote an in_production angle that has an MP4 on disk"
    )
    assert angle["video_url"] is not None


def test_reconcile_does_not_promote_in_production_when_no_mp4(isolated_store):
    """Companion to BUG-STATUS-1: when status is in_production and there is
    genuinely no MP4 on disk, reconcile must NOT silently promote to rendered.
    The angle should stay in_production (it has a project folder, just no export).
    """
    tmp_path = isolated_store
    project_name = "demo_product_angle1_1"

    # No MP4 anywhere -- project dir exists but render hasn't finished
    _seed(tmp_path, angle_status="in_production", video_url=None)

    ps.ProductStore.reconcile_existing_projects()

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "in_production", (
        f"Expected 'in_production' (render not done) but got {angle['status']!r}"
    )

