from pathlib import Path

import pytest
from fastapi import HTTPException

from scripts import api_videos
from scripts.api_schemas import RenameVideoPayload


class _FlakyRenameSource:
    def __init__(self, failures: int):
        self.failures = failures
        self.attempts = 0

    def rename(self, _target: Path) -> None:
        self.attempts += 1
        if self.attempts <= self.failures:
            error = PermissionError(32, "file is locked")
            error.winerror = 32
            raise error


def test_rename_with_retry_waits_for_transient_windows_lock(monkeypatch):
    source = _FlakyRenameSource(failures=2)
    monkeypatch.setattr(api_videos.time, "sleep", lambda _seconds: None)

    api_videos._rename_with_retry(source, Path("renamed.mov"))

    assert source.attempts == 3


def test_rename_video_file_returns_conflict_when_lock_remains(tmp_path, monkeypatch):
    raw_dir = tmp_path / "01_Raw"
    raw_dir.mkdir()
    source = raw_dir / "locked.mov"
    source.write_bytes(b"raw")
    monkeypatch.setattr(api_videos, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_videos, "RAW_DIR", raw_dir)

    def always_locked(_source: Path, _target: Path) -> None:
        error = PermissionError(32, "file is locked")
        error.winerror = 32
        raise error

    monkeypatch.setattr(api_videos, "_rename_with_retry", always_locked)

    with pytest.raises(HTTPException) as exc_info:
        api_videos.rename_video_file(
            RenameVideoPayload(video_path=str(source), new_name="renamed")
        )

    assert exc_info.value.status_code == 409
    assert "ปิดพรีวิว" in str(exc_info.value.detail)
    assert source.exists()


def test_rename_video_file_moves_clip_and_keeps_extension(tmp_path, monkeypatch):
    raw_dir = tmp_path / "01_Raw"
    raw_dir.mkdir()
    source = raw_dir / "camera_take.mov"
    source.write_bytes(b"raw")
    monkeypatch.setattr(api_videos, "BASE_DIR", tmp_path)
    monkeypatch.setattr(api_videos, "RAW_DIR", raw_dir)
    monkeypatch.setattr(api_videos.ProductStore, "_load", staticmethod(lambda: []))
    monkeypatch.setattr(
        api_videos,
        "get_file_info",
        lambda path: {
            "name": path.name,
            "path": str(path),
            "rel_path": str(path.relative_to(tmp_path)).replace("\\", "/"),
        },
    )

    result = api_videos.rename_video_file(
        RenameVideoPayload(video_path=str(source), new_name="Logitech Lift")
    )

    target = raw_dir / "Logitech Lift.mov"
    assert result["success"] is True
    assert result["file"]["name"] == target.name
    assert target.read_bytes() == b"raw"
    assert not source.exists()
