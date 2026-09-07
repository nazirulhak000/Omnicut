"""
A render that fails partway used to leave its folder untraceable.

SourceResolutionStage invents a project name when the caller sends none,
and that name lived only on the context until run() returned. Any stage
raising after it took the name along, so:

- api_render.py classified the failure with req_data.project_name, which
  is None in exactly that case, and render_jobs.fail_job's fallback read
  job["result"], which only complete_job() ever populates -- so a failed
  job could never name the project it failed on.
- The folder kept whatever voiceover, subtitles and mixed audio had
  already succeeded, with nothing recording where it came from, and the
  next attempt (still without a project_name) took the next free folder
  name and abandoned this one.

The pipeline now stamps the resolved name onto the exception, and
SourceResolutionStage drops a .run_started.json breadcrumb. Note the
breadcrumb is deliberately not project.json: ProjectManifest.require()
treats a manifest as proof of a completed render, so a partial one there
would let a reroll run against artifacts that do not exist.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def projects_dir(tmp_path, monkeypatch):
    """Point every module that binds PROJECTS_DIR at tmp_path.

    Each binds it at import, so patching scripts.config alone would not
    reach them.
    """
    import scripts.stages.source_resolution as sr
    import scripts.project_manifest as pm

    d = tmp_path / "03_Projects"
    d.mkdir()
    monkeypatch.setattr(sr, "PROJECTS_DIR", d)
    monkeypatch.setattr(pm, "PROJECTS_DIR", d)
    assert sr.PROJECTS_DIR == d, "the PROJECTS_DIR patch did not take"
    return d


def _ctx(raw_video_path, **over):
    """A context with just the inputs SourceResolutionStage reads.

    The stage validates the source file before it creates the project
    folder, so a usable (non-empty) path is required to reach the folder
    setup this module is about.
    """
    from scripts.pipeline_context import PipelineContext

    fields = {"product_name": "หูฟังบลูทูธ", "raw_video_path": str(raw_video_path)}
    fields.update(over)
    return PipelineContext(**fields)


@pytest.fixture
def raw_video(tmp_path):
    """A non-empty file, since the stage rejects a 0-byte source."""
    v = tmp_path / "clip.mp4"
    v.write_bytes(b"\x00" * 2048)
    return v


# ----------------------------------------------------------------------
# The breadcrumb
# ----------------------------------------------------------------------
def test_source_resolution_leaves_a_breadcrumb_naming_the_run(projects_dir, raw_video):
    import scripts.stages.source_resolution as sr

    ctx = _ctx(raw_video)
    sr.SourceResolutionStage.run(ctx)

    assert ctx.project_name, "the stage should have invented a project name"
    crumb = projects_dir / ctx.project_name / ".run_started.json"
    assert crumb.exists(), f"no breadcrumb in {projects_dir / ctx.project_name}"

    data = json.loads(crumb.read_text(encoding="utf-8"))
    assert data["project_name"] == ctx.project_name
    assert data["product_name"] == "หูฟังบลูทูธ"
    assert data["started_at"]


def test_the_breadcrumb_is_not_a_manifest(projects_dir, raw_video):
    """require() must still refuse a folder that never completed a render.

    This is why the breadcrumb is its own file: ProjectManifest.require()
    reads any manifest as proof of a finished render, so writing a partial
    one would let a reroll start against artifacts that do not exist.
    """
    import scripts.stages.source_resolution as sr
    from scripts.project_manifest import ProjectManifest

    ctx = _ctx(raw_video)
    sr.SourceResolutionStage.run(ctx)

    assert (projects_dir / ctx.project_name / ".run_started.json").exists()
    with pytest.raises(ValueError):
        ProjectManifest.require(ctx.project_name)


# ----------------------------------------------------------------------
# The project name surviving a mid-pipeline failure
# ----------------------------------------------------------------------
def test_a_failing_stage_carries_the_project_name_out(monkeypatch):
    """pipeline.run() stamps ctx.project_name onto whatever propagates."""
    import scripts.pipeline as pl

    class _Boom(RuntimeError):
        pass

    def _name_it(ctx):
        ctx.project_name = "auto_named_1"

    def _fail(ctx):
        raise _Boom("voice synthesis died")

    monkeypatch.setattr(pl.SourceResolutionStage, "run", staticmethod(_name_it))
    monkeypatch.setattr(pl.ScriptStage, "run", staticmethod(_fail))

    with pytest.raises(_Boom) as excinfo:
        pl.TikTokAutoCutterPipeline.run(
            product_name="หูฟัง", raw_video_path="", project_name=None
        )

    assert getattr(excinfo.value, "pipeline_project_name", None) == "auto_named_1", (
        "the resolved project name did not survive the raise"
    )


def test_fail_job_classifies_with_the_name_the_pipeline_resolved(monkeypatch):
    """render_jobs.fail_job reads the name off the exception.

    Its old fallback read job["result"], which only complete_job() ever
    populates, so on a failure path it was always absent and the
    classified error could never name the project it failed on.
    """
    from scripts import render_jobs

    job = render_jobs.create_job("render")
    job_id = job["id"] if isinstance(job, dict) else job

    seen = {}
    import scripts.error_handler as eh

    original = eh.classify_exception

    def _spy(exc, project_name=None, job_id=None, **kw):
        seen["project_name"] = project_name
        return original(exc, project_name=project_name, job_id=job_id, **kw)

    monkeypatch.setattr(eh, "classify_exception", _spy)

    err = RuntimeError("ffmpeg exited 1")
    err.pipeline_project_name = "auto_named_7"
    render_jobs.fail_job(job_id, err)

    assert seen.get("project_name") == "auto_named_7", (
        "the name stamped on the exception did not reach classify_exception"
    )


def test_fail_job_without_a_stamped_name_still_works(monkeypatch):
    """An exception carrying no name must not break the failure path."""
    from scripts import render_jobs

    job = render_jobs.create_job("render")
    job_id = job["id"] if isinstance(job, dict) else job

    render_jobs.fail_job(job_id, RuntimeError("ffmpeg exited 1"))

    record = render_jobs.get_job(job_id)
    assert record["status"] == "failed"
    assert record["error"]
