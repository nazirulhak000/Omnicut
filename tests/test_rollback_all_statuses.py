"""
Regression test for Round BUG-3.2: deleting a clip's file must roll its
angle back for removable lifecycle states. A posted angle is permanent
history and must remain untouched even when an older export is deleted.

rollback_by_video_or_project() used to only touch angles whose status was
"rendered" or "in_production" -- once an angle reached "mobile_ready",
deleting its file via ExportGallery's delete button silently did nothing,
leaving Content Tracker Hub's card looking like the video still existed.
The later Posted protection contract intentionally excludes "posted".

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


def _seed(tmp_path, *, angle_status, with_project_dir):
    project_name = "demo_product_angle1_1"
    video_path = tmp_path / "04_Exports" / "Posted" / f"{project_name}_20260101_000000.mp4"
    products = [{
        "id": "demo_product",
        "name": "Demo Product",
        "angles": [{
            "angle_id": "angle1",
            "id": "angle1",
            "project_name": project_name,
            "status": angle_status,
            "video_url": str(video_path),
        }],
        "projects": [project_name],
    }]
    (tmp_path / "_Docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_Docs" / "products.json").write_text(
        json.dumps(products, ensure_ascii=False), encoding="utf-8",
    )
    if with_project_dir:
        (tmp_path / "03_Projects" / project_name).mkdir(parents=True, exist_ok=True)
    return video_path.name


@pytest.mark.parametrize("angle_status", ["rendered", "in_production"])
def test_rollback_fires_for_every_status_when_project_dir_still_exists(isolated_store, angle_status):
    tmp_path = isolated_store
    filename = _seed(tmp_path, angle_status=angle_status, with_project_dir=True)

    rolled_back = ps.ProductStore.rollback_by_video_or_project(filename)

    assert rolled_back == ["angle1"], f"status={angle_status!r} was not rolled back"
    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "in_production"
    assert angle["video_url"] is None


@pytest.mark.parametrize("angle_status", ["rendered"])
def test_rollback_fires_even_when_project_dir_is_also_gone(isolated_store, angle_status):
    tmp_path = isolated_store
    filename = _seed(tmp_path, angle_status=angle_status, with_project_dir=False)

    rolled_back = ps.ProductStore.rollback_by_video_or_project(filename)

    assert rolled_back == ["angle1"]
    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "scripted"
    assert angle["video_url"] is None
    assert angle["project_name"] is None


@pytest.mark.parametrize("with_project_dir", [True, False])
def test_rollback_never_changes_posted_angle(isolated_store, with_project_dir):
    """A delete of an older version cannot demote the posted version's angle."""
    tmp_path = isolated_store
    filename = _seed(tmp_path, angle_status="posted", with_project_dir=with_project_dir)

    rolled_back = ps.ProductStore.rollback_by_video_or_project(filename)

    assert rolled_back == []
    products = json.loads((tmp_path / "_Docs" / "products.json").read_text(encoding="utf-8"))
    angle = products[0]["angles"][0]
    assert angle["status"] == "posted"
    assert angle["video_url"] is not None
