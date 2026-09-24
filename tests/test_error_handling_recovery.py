"""
Unit tests for Error Handling and Recovery (Phase 10).
Validates error classification, actionable suggestions, manifest .bak recovery,
and task manager server restart recovery.
"""

import json
import errno
import pytest
from pathlib import Path

from scripts.error_handler import (
    ErrorCategory,
    AppError,
    classify_exception,
    truncate_stderr,
)
from scripts.project_manifest import ProjectManifest
from scripts.task_manager import TaskManager, TaskStatus


def test_error_classification_categories():
    # 1. User-correctable
    fnf = FileNotFoundError("No such file: raw/video.mp4")
    app_fnf = classify_exception(fnf, project_name="proj1", job_id="job1")
    assert app_fnf.category == ErrorCategory.USER_CORRECTABLE
    assert app_fnf.code == "FILE_NOT_FOUND"
    assert "ไม่พบไฟล์" in app_fnf.message_th
    assert "ตรวจสอบ" in app_fnf.suggestion_th

    # 2. System I/O
    perm = PermissionError("Permission denied: cannot write to project.json")
    app_perm = classify_exception(perm)
    assert app_perm.category == ErrorCategory.SYSTEM_IO
    assert app_perm.code == "PERMISSION_DENIED"

    disk = OSError("No space left on device")
    app_disk = classify_exception(disk)
    assert app_disk.category == ErrorCategory.SYSTEM_IO
    assert app_disk.code == "DISK_FULL"

    # 3. FFmpeg
    ff_err = RuntimeError("ffmpeg failed with code 1: Invalid data found when processing input")
    app_ff = classify_exception(ff_err)
    assert app_ff.category == ErrorCategory.FFMPEG
    assert app_ff.code == "FFMPEG_PROCESSING_ERROR"

    # 4. AI Provider
    quota_err = Exception("ResourceExhausted: 429 Resource has been exhausted (e.g. check quota)")
    app_quota = classify_exception(quota_err)
    assert app_quota.category == ErrorCategory.AI_PROVIDER
    assert app_quota.code == "AI_QUOTA_EXCEEDED"


def test_truncate_stderr():
    huge_stderr = "\n".join([f"Frame {i}: warning dropped packet" for i in range(200)])
    truncated = truncate_stderr(huge_stderr, max_chars=500, max_lines=10)
    assert len(truncated) <= 500
    assert len(truncated.splitlines()) <= 10
    assert "Frame 199" in truncated


def test_manifest_atomic_save_and_backup_recovery(tmp_path, monkeypatch):
    # Mock PROJECTS_DIR to tmp_path
    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", tmp_path)

    project_name = "test_recovery_proj"

    # Step 1: Initial save
    m1 = ProjectManifest.save(project_name, title="Version 1", step="initial")
    assert m1["title"] == "Version 1"

    # Step 2: Second save (should create .bak of Version 1)
    m2 = ProjectManifest.save(project_name, title="Version 2", step="updated")
    assert m2["title"] == "Version 2"

    main_file = ProjectManifest.path_for(project_name)
    bak_file = main_file.with_suffix(".json.bak")
    assert main_file.exists()
    assert bak_file.exists()

    # Step 3: Corrupt primary file (simulate power cut mid-write)
    main_file.write_text("{ corrupt json...", encoding="utf-8")

    # Step 4: Load should automatically fall back to .bak and recover Version 1 or 2 data
    recovered = ProjectManifest.load(project_name)
    assert recovered is not None
    assert "title" in recovered


def test_manifest_disk_full_keeps_last_good_save_and_cleans_partial_temp(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.project_manifest.PROJECTS_DIR", tmp_path)
    ProjectManifest.save("disk-full-probe", title="last good")
    project_dir = ProjectManifest.dir_for("disk-full-probe")
    original_write_text = Path.write_text

    def fail_temp_write(path, data, *args, **kwargs):
        if path.parent == project_dir and path.suffix == ".tmp":
            original_write_text(path, data[:20], *args, **kwargs)
            raise OSError(errno.ENOSPC, "No space left on device")
        return original_write_text(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_temp_write)
    with pytest.raises(OSError) as error:
        ProjectManifest.save("disk-full-probe", title="lost write")

    assert error.value.errno == errno.ENOSPC
    assert ProjectManifest.load("disk-full-probe")["title"] == "last good"
    assert not list(project_dir.glob("*.tmp"))


def test_task_manager_server_restart_recovery(tmp_path, monkeypatch):
    # Mock TASKS_FILE to tmp_path
    fake_tasks_file = tmp_path / "task_registry.json"
    monkeypatch.setattr("scripts.task_manager.TASKS_FILE", fake_tasks_file)
    monkeypatch.setattr("scripts.task_manager.STORAGE_DIR", tmp_path)

    # Seed an unfinished task
    fake_tasks = {
        "job_123": {
            "id": "job_123",
            "status": TaskStatus.PROCESSING,
            "title": "เรนเดอร์วิดีโอ",
            "progress": 0.45,
            "created_at": "2026-09-05 10:00:00",
        }
    }
    fake_tasks_file.write_text(json.dumps(fake_tasks), encoding="utf-8")

    # Reset TaskManager._initialized to simulate a fresh server boot
    TaskManager._initialized = False
    TaskManager._tasks = {}

    TaskManager.initialize()

    # The orphan processing task must be transitioned to FAILED, not stuck in PROCESSING
    task = TaskManager.get_task("job_123")
    assert task is not None
    assert task["status"] == TaskStatus.FAILED
    assert "รีสตาร์ท" in task["error"]
