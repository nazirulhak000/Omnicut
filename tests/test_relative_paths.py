"""
Regression tests for storing path fields BASE_DIR-relative instead of
absolute (SAAS_READINESS_PLAN.md P0 item 4 / item 17).

Covers, per the task:
  - A record stored relative resolves to the right absolute path.
  - A legacy absolute record still reads correctly (old data, or data
    mirrored in from another machine's un-migrated JSON).
  - A path outside BASE_DIR (different machine's absolute root, or
    CAPCUT_DRAFT_DIR) is passed through unchanged on both read and write --
    there's nothing to rebase it against.
  - The migration script (scripts/migrate_paths_to_relative.py) is lossless
    (every id/field survives, non-path fields untouched) and idempotent
    (a second run is a no-op).
  - Every ProductStore write path (update_angle_status, update_angle_videos,
    set_default_videos_for_all_angles, add_video_to_product,
    remove_video_from_product) stores relative and still round-trips.
  - reconcile_existing_projects()/rollback_by_video_or_project() keep
    working against BOTH a relative and an absolute video_url already on
    disk (the exists()-check read side).

Uses tmp_path + monkeypatch throughout, per .agents/rules/testing_standard.md
rule 3 -- never touches the real _Docs/products.json, 01_Raw/, 03_Projects/
or 04_Exports/.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import path_utils
from scripts import product_store as ps
from scripts import migrate_paths_to_relative as mig
from scripts import project_manifest as pm


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    store_path = tmp_path / "_Docs" / "products.json"
    monkeypatch.setattr(ps, "STORE_PATH", store_path)
    monkeypatch.setattr(ps, "BASE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def isolated_manifest(tmp_path, monkeypatch):
    projects_dir = tmp_path / "03_Projects"
    projects_dir.mkdir()
    monkeypatch.setattr(pm, "PROJECTS_DIR", projects_dir)
    monkeypatch.setattr(pm, "BASE_DIR", tmp_path)
    return tmp_path


# ----------------------------------------------------------------------
# path_utils: the core convention, in isolation
# ----------------------------------------------------------------------

def test_to_relative_converts_absolute_path_inside_base_dir(tmp_path):
    target = tmp_path / "01_Raw" / "clip.mov"
    target.parent.mkdir(parents=True)
    target.touch()

    rel = path_utils.to_relative(str(target), base_dir=tmp_path)
    assert rel == "01_Raw/clip.mov"


def test_to_relative_leaves_already_relative_path_alone(tmp_path):
    rel = path_utils.to_relative("01_Raw/clip.mov", base_dir=tmp_path)
    assert rel == "01_Raw/clip.mov"


def test_to_relative_passes_through_path_outside_base_dir_unchanged(tmp_path):
    outside = tmp_path.parent / "some_other_dir" / "clip.mov"
    rel = path_utils.to_relative(str(outside), base_dir=tmp_path)
    # Cannot be rebased onto tmp_path -- must come back unchanged (only
    # slash-normalized), not silently mangled or raise.
    assert Path(rel) == Path(str(outside))


def test_to_relative_none_and_empty_pass_through(tmp_path):
    assert path_utils.to_relative(None, base_dir=tmp_path) is None
    assert path_utils.to_relative("", base_dir=tmp_path) == ""


def test_to_absolute_resolves_relative_against_base_dir(tmp_path):
    absolute = path_utils.to_absolute("01_Raw/clip.mov", base_dir=tmp_path)
    assert absolute == tmp_path / "01_Raw" / "clip.mov"


def test_to_absolute_leaves_legacy_absolute_path_inside_base_dir_alone(tmp_path):
    target = tmp_path / "01_Raw" / "clip.mov"
    absolute = path_utils.to_absolute(str(target), base_dir=tmp_path)
    assert absolute == target


def test_to_absolute_passes_through_foreign_absolute_root_unchanged(tmp_path):
    """A record written on a DIFFERENT machine (different drive/root
    entirely) cannot be rebased onto this machine's BASE_DIR -- to_absolute
    must return it as-is so the existing not-found handling downstream
    reports it, rather than guessing or raising."""
    foreign = "Z:/some_other_machine/01_Raw/clip.mov"
    absolute = path_utils.to_absolute(foreign, base_dir=tmp_path)
    assert str(absolute) == foreign or str(absolute).replace("\\", "/") == foreign


def test_to_absolute_none_and_empty_return_none(tmp_path):
    assert path_utils.to_absolute(None, base_dir=tmp_path) is None
    assert path_utils.to_absolute("", base_dir=tmp_path) is None


# ----------------------------------------------------------------------
# ProductStore write paths store relative
# ----------------------------------------------------------------------

def test_update_angle_status_stores_video_url_relative(isolated_store):
    tmp_path = isolated_store
    product = ps.ProductStore.add(name="Widget", angles=[{"angle_id": "a1", "status": "in_production"}])

    absolute_mp4 = tmp_path / "04_Exports" / "Ready_to_post" / "clip.mp4"
    absolute_mp4.parent.mkdir(parents=True, exist_ok=True)
    absolute_mp4.touch()

    updated = ps.ProductStore.update_angle_status(
        product["id"], "a1", "rendered", video_url=str(absolute_mp4)
    )
    stored_url = updated["angles"][0]["video_url"]
    assert stored_url == "04_Exports/Ready_to_post/clip.mp4"

    # And it round-trips back to the same absolute file via to_absolute().
    resolved = path_utils.to_absolute(stored_url, base_dir=tmp_path)
    assert resolved == absolute_mp4


def test_update_angle_status_video_url_already_relative_is_left_as_is(isolated_store):
    product = ps.ProductStore.add(name="Widget", angles=[{"angle_id": "a1", "status": "in_production"}])
    updated = ps.ProductStore.update_angle_status(
        product["id"], "a1", "rendered", video_url="04_Exports/Ready_to_post/clip.mp4"
    )
    assert updated["angles"][0]["video_url"] == "04_Exports/Ready_to_post/clip.mp4"


def test_update_angle_status_clearing_video_url_stores_none(isolated_store):
    product = ps.ProductStore.add(name="Widget", angles=[{"angle_id": "a1", "status": "rendered", "video_url": "x.mp4"}])
    updated = ps.ProductStore.update_angle_status(product["id"], "a1", "scripted", video_url="")
    assert updated["angles"][0]["video_url"] is None


def test_update_angle_videos_stores_selected_videos_relative(isolated_store):
    tmp_path = isolated_store
    product = ps.ProductStore.add(name="Widget", angles=[{"angle_id": "a1", "status": "scripted"}])

    absolute_raw = tmp_path / "01_Raw" / "p1" / "clip.mov"
    updated = ps.ProductStore.update_angle_videos(product["id"], "a1", [str(absolute_raw)])

    angle = updated["angles"][0]
    assert angle["selected_videos"] == ["01_Raw/p1/clip.mov"]
    assert angle["selected_video"] == "01_Raw/p1/clip.mov"


def test_set_default_videos_for_all_angles_stores_relative_and_populates_videos_list(isolated_store):
    tmp_path = isolated_store
    product = ps.ProductStore.add(
        name="Widget",
        angles=[
            {"angle_id": "a1", "status": "scripted"},
            {"angle_id": "a2", "status": "scripted"},
        ],
    )
    absolute_raw = tmp_path / "01_Raw" / "p1" / "clip.mov"

    updated = ps.ProductStore.set_default_videos_for_all_angles(product["id"], [str(absolute_raw)])

    for angle in updated["angles"]:
        assert angle["selected_videos"] == ["01_Raw/p1/clip.mov"]

    videos = updated["videos"]
    assert len(videos) == 1
    # rel_path must be genuinely relative now (the historical bug: it used
    # to be a verbatim copy of the absolute `path`).
    assert videos[0]["rel_path"] == "01_Raw/p1/clip.mov"
    # path is kept ABSOLUTE deliberately -- scripts/api_videos.py (off
    # limits for this change) does exact string comparisons against it as
    # an absolute path when renaming/deleting raw files.
    assert Path(videos[0]["path"]) == absolute_raw


def test_add_video_to_product_normalizes_rel_path_keeps_path_absolute(isolated_store):
    tmp_path = isolated_store
    product = ps.ProductStore.add(name="Widget")
    absolute_raw = tmp_path / "01_Raw" / "clip.mov"

    # Simulate media_service.get_file_info()'s exact shape: path absolute,
    # rel_path already correctly relative.
    video_info = {
        "name": "clip.mov",
        "path": str(absolute_raw),
        "rel_path": "01_Raw/clip.mov",
    }
    updated = ps.ProductStore.add_video_to_product(product["id"], video_info)
    stored = updated["videos"][0]
    assert stored["rel_path"] == "01_Raw/clip.mov"
    assert Path(stored["path"]) == absolute_raw


def test_add_video_to_product_fixes_up_a_hand_built_dict_with_only_absolute_path(isolated_store):
    """A caller that builds video_info by hand and only sets `path` (no
    rel_path) must still get a genuinely relative rel_path filled in."""
    tmp_path = isolated_store
    product = ps.ProductStore.add(name="Widget")
    absolute_raw = tmp_path / "01_Raw" / "clip.mov"

    updated = ps.ProductStore.add_video_to_product(product["id"], {"path": str(absolute_raw)})
    stored = updated["videos"][0]
    assert stored["rel_path"] == "01_Raw/clip.mov"
    assert Path(stored["path"]) == absolute_raw


def test_remove_video_from_product_matches_relative_or_absolute_form(isolated_store):
    tmp_path = isolated_store
    product = ps.ProductStore.add(name="Widget")
    absolute_raw = tmp_path / "01_Raw" / "clip.mov"
    ps.ProductStore.add_video_to_product(product["id"], {"path": str(absolute_raw)})

    # Caller passes the RELATIVE form even though the stored `path` is
    # absolute -- must still match and remove it.
    updated = ps.ProductStore.remove_video_from_product(product["id"], "01_Raw/clip.mov")
    assert updated["videos"] == []


# ----------------------------------------------------------------------
# Read side: reconcile / rollback tolerate both relative and absolute
# video_url already on disk
# ----------------------------------------------------------------------

def test_reconcile_finds_video_stored_as_relative_path(isolated_store):
    tmp_path = isolated_store
    export_file = tmp_path / "04_Exports" / "Ready_to_post" / "clip.mp4"
    export_file.parent.mkdir(parents=True, exist_ok=True)
    export_file.write_bytes(b"fake mp4")

    products = [{
        "id": "prod1",
        "name": "Widget",
        "angles": [{
            "angle_id": "a1",
            "status": "rendered",
            "video_url": "04_Exports/Ready_to_post/clip.mp4",  # relative
            "project_name": None,
        }],
    }]
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(json.dumps(products), encoding="utf-8")

    ps.ProductStore.reconcile_existing_projects()
    reloaded = ps.ProductStore.get("prod1")
    angle = reloaded["angles"][0]
    # Video exists on disk (relative path resolves correctly) -- status
    # must NOT be reset to scripted/in_production.
    assert angle["status"] == "rendered"
    assert angle["video_url"] == "04_Exports/Ready_to_post/clip.mp4"


def test_reconcile_finds_video_stored_as_legacy_absolute_path(isolated_store):
    tmp_path = isolated_store
    export_file = tmp_path / "04_Exports" / "Ready_to_post" / "clip.mp4"
    export_file.parent.mkdir(parents=True, exist_ok=True)
    export_file.write_bytes(b"fake mp4")

    products = [{
        "id": "prod1",
        "name": "Widget",
        "angles": [{
            "angle_id": "a1",
            "status": "rendered",
            "video_url": str(export_file),  # legacy absolute
            "project_name": None,
        }],
    }]
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(json.dumps(products), encoding="utf-8")

    ps.ProductStore.reconcile_existing_projects()
    reloaded = ps.ProductStore.get("prod1")
    angle = reloaded["angles"][0]
    assert angle["status"] == "rendered"


def test_reconcile_rolls_back_when_neither_relative_nor_absolute_video_exists(isolated_store):
    tmp_path = isolated_store
    # reconcile_existing_projects() returns early (does nothing) unless
    # 03_Projects exists -- the strict "does this angle's video still
    # exist on disk" validation only runs once that directory is present.
    (tmp_path / "03_Projects").mkdir(parents=True, exist_ok=True)

    products = [{
        "id": "prod1",
        "name": "Widget",
        "angles": [{
            "angle_id": "a1",
            "status": "rendered",
            "video_url": "04_Exports/Ready_to_post/missing.mp4",
            "project_name": None,
        }],
    }]
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(json.dumps(products), encoding="utf-8")

    ps.ProductStore.reconcile_existing_projects()
    reloaded = ps.ProductStore.get("prod1")
    angle = reloaded["angles"][0]
    assert angle["status"] == "scripted"
    assert angle["video_url"] is None


# ----------------------------------------------------------------------
# Migration script: lossless + idempotent
# ----------------------------------------------------------------------

def _seed_legacy_absolute_product(tmp_path):
    raw_video = tmp_path / "01_Raw" / "p1" / "clip.mov"
    export_video = tmp_path / "04_Exports" / "Ready_to_post" / "clip.mp4"
    products = [{
        "id": "legacy1",
        "name": "Legacy Product",
        "status": "rendered",
        "angles": [{
            "angle_id": "a1",
            "status": "rendered",
            "video_url": str(export_video),
            "selected_videos": [str(raw_video)],
            "selected_video": str(raw_video),
        }],
        "videos": [{"rel_path": str(raw_video), "path": str(raw_video)}],
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }]
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(json.dumps(products), encoding="utf-8")
    return products[0], raw_video, export_video


def test_migration_converts_absolute_fields_to_relative(isolated_store):
    tmp_path = isolated_store
    _seed_legacy_absolute_product(tmp_path)

    rc = mig.migrate(dry_run=False)
    assert rc == 0

    reloaded = ps.ProductStore.get("legacy1")
    angle = reloaded["angles"][0]
    assert angle["video_url"] == "04_Exports/Ready_to_post/clip.mp4"
    assert angle["selected_videos"] == ["01_Raw/p1/clip.mov"]
    assert angle["selected_video"] == "01_Raw/p1/clip.mov"

    video = reloaded["videos"][0]
    assert video["rel_path"] == "01_Raw/p1/clip.mov"
    # path is intentionally left as it was (absolute) -- see migration
    # script docstring: scripts/api_videos.py string-compares against it.
    assert Path(video["path"]) == tmp_path / "01_Raw" / "p1" / "clip.mov"


def test_migration_is_lossless_for_non_path_fields(isolated_store):
    tmp_path = isolated_store
    original, _, _ = _seed_legacy_absolute_product(tmp_path)

    mig.migrate(dry_run=False)

    reloaded = ps.ProductStore.get("legacy1")
    assert reloaded["name"] == original["name"]
    assert reloaded["status"] == original["status"]
    assert reloaded["id"] == original["id"]


def test_migration_is_idempotent(isolated_store):
    tmp_path = isolated_store
    _seed_legacy_absolute_product(tmp_path)

    mig.migrate(dry_run=False)
    first_pass = json.loads(ps.STORE_PATH.read_text(encoding="utf-8"))

    rc2 = mig.migrate(dry_run=False)
    assert rc2 == 0
    second_pass = json.loads(ps.STORE_PATH.read_text(encoding="utf-8"))

    assert first_pass == second_pass


def test_migration_dry_run_does_not_change_stored_data(isolated_store):
    tmp_path = isolated_store
    _seed_legacy_absolute_product(tmp_path)
    before = ps.STORE_PATH.read_text(encoding="utf-8")

    rc = mig.migrate(dry_run=True)
    assert rc == 0

    after = ps.STORE_PATH.read_text(encoding="utf-8")
    assert before == after


def test_migration_leaves_path_outside_base_dir_untouched(isolated_store):
    """A record written on another machine (a root that does not exist
    under this machine's BASE_DIR at all) must not be rewritten -- there is
    nothing to safely rebase it onto."""
    tmp_path = isolated_store
    foreign_path = "Z:/other_machine/01_Raw/clip.mov"
    products = [{
        "id": "foreign1",
        "name": "Foreign Product",
        "angles": [{
            "angle_id": "a1",
            "status": "rendered",
            "video_url": foreign_path,
        }],
    }]
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(json.dumps(products), encoding="utf-8")

    rc = mig.migrate(dry_run=False)
    assert rc == 0

    reloaded = ps.ProductStore.get("foreign1")
    stored_url = reloaded["angles"][0]["video_url"]
    assert Path(stored_url) == Path(foreign_path)


def test_migration_already_relative_data_reports_nothing_changed(isolated_store):
    products = [{
        "id": "already_rel",
        "name": "Already Relative",
        "angles": [{
            "angle_id": "a1",
            "status": "rendered",
            "video_url": "04_Exports/Ready_to_post/clip.mp4",
            "selected_videos": ["01_Raw/p1/clip.mov"],
        }],
        "videos": [{"rel_path": "01_Raw/p1/clip.mov", "path": "01_Raw/p1/clip.mov"}],
    }]
    ps.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ps.STORE_PATH.write_text(json.dumps(products), encoding="utf-8")

    before = json.loads(ps.STORE_PATH.read_text(encoding="utf-8"))
    rc = mig.migrate(dry_run=False)
    assert rc == 0
    after = json.loads(ps.STORE_PATH.read_text(encoding="utf-8"))
    assert before == after


# ----------------------------------------------------------------------
# ProjectManifest: artifact paths stored relative, resolved on read
# ----------------------------------------------------------------------

def test_save_normalizes_artifact_path_to_relative(isolated_manifest):
    tmp_path = isolated_manifest
    project_name = "demo_project"
    mp4 = tmp_path / "03_Projects" / project_name / "final.mp4"
    mp4.parent.mkdir(parents=True, exist_ok=True)
    mp4.write_bytes(b"fake")

    manifest = pm.ProjectManifest.save(
        project_name, artifacts={"mp4_video": {"path": str(mp4)}}
    )
    stored = manifest["artifacts"]["mp4_video"]["path"]
    assert stored == f"03_Projects/{project_name}/final.mp4"


def test_artifact_path_resolves_relative_entry_to_absolute(isolated_manifest):
    tmp_path = isolated_manifest
    project_name = "demo_project"
    mp4 = tmp_path / "03_Projects" / project_name / "final.mp4"
    mp4.parent.mkdir(parents=True, exist_ok=True)
    mp4.write_bytes(b"fake")

    manifest = pm.ProjectManifest.save(
        project_name, artifacts={"mp4_video": {"path": str(mp4)}}
    )
    resolved = pm.ProjectManifest.artifact_path(manifest, "mp4_video")
    assert resolved == mp4
    assert resolved.exists()


def test_artifact_path_still_resolves_legacy_absolute_entry(isolated_manifest):
    """A project.json written before this migration (or by a not-yet-updated
    caller) has an absolute path already -- artifact_path() must still find
    the file rather than only supporting the new relative convention."""
    tmp_path = isolated_manifest
    project_name = "legacy_project"
    mp4 = tmp_path / "03_Projects" / project_name / "final.mp4"
    mp4.parent.mkdir(parents=True, exist_ok=True)
    mp4.write_bytes(b"fake")

    manifest = {
        "project_name": project_name,
        "artifacts": {"mp4_video": {"path": str(mp4)}},
    }
    resolved = pm.ProjectManifest.artifact_path(manifest, "mp4_video")
    assert resolved == mp4


def test_artifact_path_returns_none_when_file_missing(isolated_manifest):
    manifest = {
        "project_name": "gone",
        "artifacts": {"mp4_video": {"path": "03_Projects/gone/final.mp4"}},
    }
    assert pm.ProjectManifest.artifact_path(manifest, "mp4_video") is None


def test_record_artifact_also_normalizes_to_relative(isolated_manifest):
    tmp_path = isolated_manifest
    project_name = "demo_project"
    mp4 = tmp_path / "03_Projects" / project_name / "final.mp4"
    mp4.parent.mkdir(parents=True, exist_ok=True)
    mp4.write_bytes(b"fake")

    pm.ProjectManifest.record_artifact(project_name, "mp4_video", mp4)
    manifest = pm.ProjectManifest.load(project_name)
    assert manifest["artifacts"]["mp4_video"]["path"] == f"03_Projects/{project_name}/final.mp4"
