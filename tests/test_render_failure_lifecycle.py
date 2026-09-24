"""Offline render-worker fault gates; never touch real projects or exports."""

from unittest.mock import Mock

import pytest

from scripts import api_render, render_jobs, task_manager
from scripts.api_schemas import RenderRequest
from scripts.render_jobs import RenderCancelled
from scripts.task_manager import TaskManager


@pytest.fixture
def isolated_render_job(tmp_path, monkeypatch):
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    monkeypatch.setattr(api_render.TaskManager, "fail_task", Mock())
    monkeypatch.setattr(api_render.TaskManager, "cancel_task", Mock())
    monkeypatch.setattr(api_render.TaskManager, "complete_task", Mock())
    job_id = "fault-injection-render"
    render_jobs.create_job(job_id)
    request = RenderRequest(
        product_name="Fault Probe",
        raw_video_path=str(tmp_path / "missing-source.mp4"),
        project_name="fault-probe",
        key_features="offline",
        pain_point="offline",
        price_deal="offline",
    )
    return job_id, request


def test_render_rechecks_disk_space_and_fails_without_running_pipeline(isolated_render_job, monkeypatch):
    job_id, request = isolated_render_job
    pipeline = Mock()
    monkeypatch.setattr(api_render.TikTokAutoCutterPipeline, "run", pipeline)
    monkeypatch.setattr(api_render, "check_disk_space", lambda *_args: {
        "is_sufficient": False, "free_gb": 0.1, "min_required_gb": 3.0,
    })

    api_render.execute_render_job(job_id, request)

    pipeline.assert_not_called()
    assert render_jobs.get_job(job_id)["status"] == "failed"
    api_render.TaskManager.fail_task.assert_called_once()
    api_render.TaskManager.complete_task.assert_not_called()


@pytest.mark.parametrize("failure, expected_status, terminal_call", [
    (FileNotFoundError("missing-source.mp4"), "failed", "fail_task"),
    (RenderCancelled(), "cancelled", "cancel_task"),
])
def test_render_worker_reports_missing_media_and_cancel_as_distinct_terminal_states(
    isolated_render_job, monkeypatch, failure, expected_status, terminal_call,
):
    job_id, request = isolated_render_job
    monkeypatch.setattr(api_render, "check_disk_space", lambda *_args: {"is_sufficient": True})
    monkeypatch.setattr(api_render.TikTokAutoCutterPipeline, "run", Mock(side_effect=failure))

    api_render.execute_render_job(job_id, request)

    assert render_jobs.get_job(job_id)["status"] == expected_status
    getattr(api_render.TaskManager, terminal_call).assert_called_once()
    api_render.TaskManager.complete_task.assert_not_called()


def test_ffmpeg_failure_remains_failed_after_registry_restart(tmp_path, monkeypatch):
    """A failed export must not turn into a lost or still-processing job after restart."""
    monkeypatch.setattr(task_manager, "TASKS_FILE", tmp_path / "task_registry.json")
    monkeypatch.setattr(TaskManager, "_tasks", {})
    monkeypatch.setattr(TaskManager, "_initialized", False)
    monkeypatch.setattr(TaskManager, "_last_disk_save", 0.0)
    monkeypatch.setattr(render_jobs, "ACTIVE_JOBS", {})
    monkeypatch.setattr(api_render.ProductStore, "_load", lambda: [])
    monkeypatch.setattr(api_render, "check_disk_space", lambda *_args: {"is_sufficient": True})
    monkeypatch.setattr(
        api_render.TikTokAutoCutterPipeline, "run",
        Mock(side_effect=RuntimeError("FFmpeg render failed: encoder exited with code 1")),
    )
    job_id = "ffmpeg-failure-restart"
    TaskManager.create_task(task_type="render", title="FFmpeg failure probe", task_id=job_id)
    render_jobs.create_job(job_id)
    request = RenderRequest(
        product_name="Fault Probe", raw_video_path=str(tmp_path / "source.mp4"),
        key_features="offline", pain_point="offline", price_deal="offline",
    )

    api_render.execute_render_job(job_id, request)

    assert render_jobs.get_job(job_id)["status"] == "failed"
    assert TaskManager.get_task(job_id)["status"] == "failed"
    assert (tmp_path / "task_registry.json").exists()

    # Recreate the server's memory but keep only its persisted task registry.
    render_jobs.ACTIVE_JOBS.clear()
    TaskManager._tasks = {}
    TaskManager._initialized = False
    TaskManager.initialize()
    status = api_render.get_render_status(job_id)
    assert status["status"] == "failed"
    assert status["error"]
