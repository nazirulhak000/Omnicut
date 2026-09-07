"""
A completed reroll must leave the angle marked "rendered", not stuck on
"in_production" -- that status only means "a render is in flight."

_execute_reroll() read `result.get("mp4") or result.get("output_video") or
result.get("video_path")` to decide whether a render actually produced a
file. The pipeline's own result_paths key (video_assembly_stage.py) is
"mp4_video" -- none of those three ever matched it, so mp4_val was always
"", "rendered" was never chosen, and every reroll left the angle exactly
where it started even though the export existed on disk and the job's own
progress panel reported 100%. api_render.py's initial-render path already
checked "mp4_video" correctly; only the reroll path had the mismatch.

Confirmed against real data before writing this: a rendered
LOG02-แกะกล่องว้าว_1 export sat in 04_Exports/Ready_to_post with a real
mp4_video result, and product_store still read status: "in_production".
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import product_store, project_manifest
from scripts.product_store import ProductStore
from scripts.project_manifest import ProjectManifest


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    monkeypatch.setattr(product_store, "BASE_DIR", tmp_path)
    assert product_store.BASE_DIR == tmp_path, "the BASE_DIR patch did not take"
    return tmp_path


@pytest.fixture
def projects_dir(tmp_path, monkeypatch):
    target = tmp_path / "03_Projects"
    target.mkdir(exist_ok=True)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", target)
    return target


def _rendered_result(mp4_path: str, project_name: str):
    """What TikTokAutoCutterPipeline.run() actually returns on success --
    see video_assembly_stage.py's result_paths assignments."""
    return {
        "mp4_video": mp4_path,
        "project_name": project_name,
        "manifest": f"03_Projects/{project_name}/project.json",
        "clip_list": [],
    }


def _write_real_export(base_dir: Path, mp4_relpath: str, project_name: str):
    """Create the file on disk and the manifest artifact entry that
    reconcile_existing_projects() actually reads (art_mp4 =
    artifacts.mp4_video.path, checked via _to_absolute(art_mp4).exists()).

    Without both of these, reconcile finds no mp4 on its own scan and its
    "no exported MP4 yet -- MUST be in_production" branch reverts whatever
    update_angle_status() just set, which would make this test pass for the
    wrong reason (never truly exercising the fix) or fail for a reason
    unrelated to the bug being tested.
    """
    export_dir = base_dir / "04_Exports" / "Ready_to_post"
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / Path(mp4_relpath).name).write_bytes(b"\x00" * 64)

    from scripts.project_manifest import ProjectManifest
    ProjectManifest.save(project_name, artifacts={"mp4_video": {"path": mp4_relpath}})


def test_a_completed_reroll_marks_the_angle_rendered(isolated_store, projects_dir, monkeypatch):
    product = ProductStore.add(name="Widget", url="https://x.test/w")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "in_production",
        "script_lines": ["a"],
    }])

    project_name = "widget_test_1"
    ProjectManifest.save(
        project_name,
        script_data={"lines": [{"text": "a"}]},
        cues=[], micro_cues=[], total_duration=5.0,
        render_params={
            "raw_video_path": str(projects_dir / "nope.mp4"),
            "product_id": product["id"],
            "angle_id": "unboxing",
        },
    )

    mp4_path = f"04_Exports/Ready_to_post/{project_name}_20260907.mp4"
    _write_real_export(isolated_store, mp4_path, project_name)

    import scripts.pipeline as pipeline_mod
    monkeypatch.setattr(
        pipeline_mod.TikTokAutoCutterPipeline,
        "run",
        classmethod(lambda cls, **kw: _rendered_result(mp4_path, project_name)),
    )

    from scripts.api_phase1 import _execute_reroll
    from scripts import render_jobs
    render_jobs.create_job("job_test_1")

    _execute_reroll("job_test_1", project_name, "video", {})

    updated = ProductStore.get(product["id"])
    angle = next(a for a in updated["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "rendered", (
        f"expected 'rendered' after a completed reroll, got {angle['status']!r}"
    )
    assert angle["video_url"] == mp4_path


def test_a_reroll_with_no_output_stays_in_production(isolated_store, projects_dir, monkeypatch):
    """The other half of the same check: a reroll that produced nothing
    (e.g. export_mp4 was never true) must not be misreported as rendered."""
    product = ProductStore.add(name="Widget", url="https://x.test/w2")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "in_production",
        "script_lines": ["a"],
    }])

    project_name = "widget_test_2"
    ProjectManifest.save(
        project_name,
        script_data={"lines": [{"text": "a"}]},
        cues=[], micro_cues=[], total_duration=5.0,
        render_params={
            "raw_video_path": str(projects_dir / "nope.mp4"),
            "product_id": product["id"],
            "angle_id": "unboxing",
        },
    )

    import scripts.pipeline as pipeline_mod
    monkeypatch.setattr(
        pipeline_mod.TikTokAutoCutterPipeline,
        "run",
        classmethod(lambda cls, **kw: {"project_name": project_name, "manifest": "x"}),
    )

    from scripts.api_phase1 import _execute_reroll
    from scripts import render_jobs
    render_jobs.create_job("job_test_2")

    _execute_reroll("job_test_2", project_name, "hook", {})

    updated = ProductStore.get(product["id"])
    angle = next(a for a in updated["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "in_production"


def test_a_failed_reroll_restores_the_prior_rendered_state(isolated_store, projects_dir, monkeypatch):
    """A reroll attempted on an already-"rendered" angle (a good prior video
    exists) that then raises inside the pipeline must land back on
    "rendered" with the ORIGINAL video_url -- not get stuck on
    "in_production" with no video, which would require manual intervention
    since reconcile_existing_projects() never promotes in_production back to
    rendered on its own."""
    project_name = "widget_test_3"
    original_video_url = f"04_Exports/Ready_to_post/{project_name}_original.mp4"

    product = ProductStore.add(name="Widget", url="https://x.test/w3")
    ProductStore.update(product["id"], angles=[{
        "angle_id": "unboxing",
        "hook_title": "แกะกล่องว้าว",
        "status": "rendered",
        "video_url": original_video_url,
        "script_lines": ["a"],
    }])

    # A real export file (+ manifest artifact entry pointing at it) is
    # required -- ProductStore.get() runs reconcile_existing_projects() as a
    # side effect, and its "strict state validation" pass immediately wipes
    # any "rendered" angle whose video_url does not resolve to a real file on
    # disk, regardless of grace period. Without this, the pre-reroll snapshot
    # itself would already read "in_production", defeating the test.
    _write_real_export(isolated_store, original_video_url, project_name)

    ProjectManifest.save(
        project_name,
        script_data={"lines": [{"text": "a"}]},
        cues=[], micro_cues=[], total_duration=5.0,
        render_params={
            "raw_video_path": str(projects_dir / "nope.mp4"),
            "product_id": product["id"],
            "angle_id": "unboxing",
        },
    )

    import scripts.pipeline as pipeline_mod

    def _raise(cls, **kw):
        raise RuntimeError("ffmpeg exploded / source file moved")

    monkeypatch.setattr(
        pipeline_mod.TikTokAutoCutterPipeline,
        "run",
        classmethod(_raise),
    )

    from scripts.api_phase1 import _execute_reroll
    from scripts import render_jobs
    render_jobs.create_job("job_test_3")

    _execute_reroll("job_test_3", project_name, "video", {})

    updated = ProductStore.get(product["id"])
    angle = next(a for a in updated["angles"] if a["angle_id"] == "unboxing")
    assert angle["status"] == "rendered", (
        f"a failed reroll on a 'rendered' angle must restore 'rendered', "
        f"got {angle['status']!r}"
    )
    assert angle["video_url"] == original_video_url, (
        "a failed reroll must preserve the ORIGINAL video_url, not wipe it"
    )
