"""
Regression test for Round BUG-3: two angles bound to the same project
folder / video must not both keep pointing at it forever.

Found by reading real _Docs/products.json data (read-only, never written
by this test) -- Logitech Wave Keys' "unboxing" angle had the exact same
project_name and video_url as its "pain_point" angle, even though
"unboxing" has no project folder of its own. reconcile_existing_projects()
had no cap on how many angles could match a single project folder per
pass, so once that happened (by whatever original mistake), every later
reconcile pass just re-confirmed the collision instead of catching it.

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
    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    return tmp_path


def _seed_collision(tmp_path):
    """One real project folder (its own manifest says angle_id=pain_point),
    plus a second angle (unboxing) that has already had its project_name
    wrongly set to that same folder -- mirrors the real corrupted state,
    reproduced with fake data instead of the user's real product."""
    project_name = "demo_product_pain_point_1"
    products = [{
        "id": "demo_product",
        "name": "Demo Product",
        "angles": [
            {
                "angle_id": "pain_point",
                "id": "pain_point",
                "hook_title": "hook A",
                "project_name": project_name,
                "status": "rendered",
                "video_url": None,
            },
            {
                "angle_id": "unboxing",
                "id": "unboxing",
                "hook_title": "hook B",
                "project_name": project_name,  # wrongly claims pain_point's folder
                "status": "rendered",
                "video_url": None,
            },
        ],
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
        "render_params": {"product_id": "demo_product", "angle_id": "pain_point"},
        "artifacts": {"mp4_video": {"path": ""}},
    }, ensure_ascii=False), encoding="utf-8")

    mp4_path = tmp_path / "04_Exports" / "Ready_to_post" / f"{project_name}_20260101_000000.mp4"
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"fake mp4 bytes")

    return project_name, str(mp4_path)


def test_authoritative_match_wins_and_self_referential_loser_gets_unlinked(isolated_store):
    tmp_path = isolated_store
    project_name, mp4_path = _seed_collision(tmp_path)

    ps.ProductStore.reconcile_existing_projects()

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angles = {a["angle_id"]: a for a in products[0]["angles"]}

    pain_point = angles["pain_point"]
    unboxing = angles["unboxing"]

    assert pain_point["project_name"] == project_name
    assert pain_point["video_url"] is not None
    assert pain_point["status"] == "rendered"

    assert unboxing["project_name"] is None, (
        "unboxing kept claiming pain_point's project folder -- the collision "
        "guard did not unlink the loser"
    )
    assert unboxing["video_url"] is None
    assert unboxing["status"] == "scripted"
    assert unboxing.get("data_conflict_note"), (
        "loser angle should carry a visible explanation of why it got unlinked"
    )


def test_two_self_referential_claims_with_no_authoritative_owner_keep_only_the_first(isolated_store):
    """Adversarial case: neither angle's project manifest actually names it
    (e.g. the manifest is for a third, deleted angle) -- both angles only
    claim the folder via their own stale project_name. Must still pick
    exactly one winner, not silently duplicate the video onto both."""
    tmp_path = isolated_store
    project_name = "demo_product_orphan_1"
    products = [{
        "id": "demo_product",
        "name": "Demo Product",
        "angles": [
            {"angle_id": "angle_a", "id": "angle_a", "project_name": project_name,
             "status": "rendered", "video_url": None},
            {"angle_id": "angle_b", "id": "angle_b", "project_name": project_name,
             "status": "rendered", "video_url": None},
        ],
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
        # No render_params at all -- nobody's manifest actually owns this folder.
        "artifacts": {"mp4_video": {"path": ""}},
    }, ensure_ascii=False), encoding="utf-8")

    mp4_path = tmp_path / "04_Exports" / "Ready_to_post" / f"{project_name}_20260101_000000.mp4"
    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    mp4_path.write_bytes(b"fake mp4 bytes")

    ps.ProductStore.reconcile_existing_projects()

    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angles = {a["angle_id"]: a for a in products[0]["angles"]}

    linked = [a for a in angles.values() if a.get("project_name") == project_name]
    unlinked = [a for a in angles.values() if a.get("project_name") is None]

    assert len(linked) == 1, f"expected exactly 1 angle to keep the folder, got {len(linked)}"
    assert len(unlinked) == 1
    assert unlinked[0].get("data_conflict_note")
