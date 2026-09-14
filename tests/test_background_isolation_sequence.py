from __future__ import annotations

import subprocess
import threading
from pathlib import Path

import pytest

from scripts.background_isolation_sequence import (
    ERROR_CANCELLED,
    ERROR_FFMPEG,
    ERROR_INPUT_NOT_FOUND,
    ERROR_INVALID_REQUEST,
    ERROR_NO_FRAMES,
    ERROR_OUTPUT_EXISTS,
    FRAME_PATTERN,
    SEQUENCE_NAMESPACE,
    STATUS_CANCELLED,
    STATUS_ERROR,
    STATUS_READY,
    extract_background_isolation_sequence,
)


ARTIFACT_ID = "bgseq1-0123456789abcdef"


def source_file(tmp_path: Path) -> Path:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"source-must-stay-unchanged")
    return source


def fake_runner(frame_count: int = 3, *, cancel_event=None, fail: bool = False):
    calls: list[list[str]] = []

    def run(command: list[str]):
        calls.append(command)
        if cancel_event is not None:
            cancel_event.set()
        if fail:
            raise subprocess.CalledProcessError(1, command, stderr="decoder failed")
        output_pattern = Path(command[-1])
        output_pattern.parent.mkdir(parents=True, exist_ok=True)
        for index in range(frame_count):
            output_pattern.parent.joinpath(FRAME_PATTERN.replace("%06d", f"{index:06d}")).write_bytes(
                f"frame-{index}".encode()
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    run.calls = calls  # type: ignore[attr-defined]
    return run


def test_success_builds_deterministic_sequence_and_reports_progress(tmp_path):
    source = source_file(tmp_path)
    progress: list[dict] = []
    runner = fake_runner(3)

    result = extract_background_isolation_sequence(
        source,
        tmp_path / "cache",
        ARTIFACT_ID,
        start=1.25,
        duration=2.5,
        fps="30000/1001",
        timebase="1/90000",
        width=1080,
        height=1920,
        progress_callback=progress.append,
        runner=runner,
    )

    assert result["ok"] is True
    assert result["status"] == STATUS_READY
    assert result["artifact_id"] == ARTIFACT_ID
    assert result["frame_pattern"] == FRAME_PATTERN
    assert result["frame_count"] == 3
    assert result["fps"] == "30000/1001"
    assert result["timebase"] == "1/90000"
    assert [Path(path).name for path in result["frames"]] == [
        "frame_000000.png",
        "frame_000001.png",
        "frame_000002.png",
    ]
    assert progress[0]["progress"] == 0.0
    assert progress[-1] == {"stage": "extracted", "frame": 3, "progress": 1.0}
    assert source.read_bytes() == b"source-must-stay-unchanged"
    command = runner.calls[0]
    assert Path(command[-1]).parent.name == "frames"
    assert Path(command[-1]).name == FRAME_PATTERN
    assert "-ss" in command and command[command.index("-ss") + 1] == "1.25"
    assert "-t" in command and command[command.index("-t") + 1] == "2.5"
    assert "fps=30000/1001" in command[command.index("-vf") + 1]
    assert not list((tmp_path / "cache" / SEQUENCE_NAMESPACE).glob(".*.tmp"))


def test_second_call_is_a_safe_cache_hit_and_does_not_run_ffmpeg_again(tmp_path):
    source = source_file(tmp_path)
    cache = tmp_path / "cache"
    first_runner = fake_runner(2)
    first = extract_background_isolation_sequence(source, cache, ARTIFACT_ID, runner=first_runner)
    second_runner = fake_runner(9)
    second = extract_background_isolation_sequence(source, cache, ARTIFACT_ID, runner=second_runner)

    assert first["status"] == STATUS_READY
    assert second["status"] == STATUS_READY
    assert second["cache_hit"] is True
    assert second["frame_count"] == 2
    assert second_runner.calls == []


@pytest.mark.parametrize(
    ("kwargs", "error_code"),
    [
        ({"input_path": "missing.mp4"}, ERROR_INPUT_NOT_FOUND),
        ({"fps": 0}, ERROR_INVALID_REQUEST),
        ({"duration": 0}, ERROR_INVALID_REQUEST),
        ({"width": 0}, ERROR_INVALID_REQUEST),
        ({"artifact_id": "../outside"}, ERROR_INVALID_REQUEST),
        ({"output_sequence_root": ""}, ERROR_INVALID_REQUEST),
    ],
)
def test_invalid_request_is_rejected_before_ffmpeg(tmp_path, kwargs, error_code):
    source = source_file(tmp_path)
    values = {
        "input_path": source,
        "output_sequence_root": tmp_path / "cache",
        "artifact_id": ARTIFACT_ID,
        "runner": fake_runner(),
    }
    values.update(kwargs)

    result = extract_background_isolation_sequence(**values)

    assert result["ok"] is False
    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == error_code
    assert not (tmp_path / "cache").exists()


def test_protected_raw_or_assets_output_is_rejected(tmp_path):
    source = source_file(tmp_path)
    result = extract_background_isolation_sequence(
        source,
        tmp_path / "01_Raw" / "derived",
        ARTIFACT_ID,
        runner=fake_runner(),
    )

    assert result["error_code"] == ERROR_INVALID_REQUEST
    assert not (tmp_path / "01_Raw").exists()


def test_ffmpeg_error_cleans_temp_output_and_preserves_source(tmp_path):
    source = source_file(tmp_path)
    cache = tmp_path / "cache"
    result = extract_background_isolation_sequence(
        source,
        cache,
        ARTIFACT_ID,
        runner=fake_runner(fail=True),
    )

    assert result["ok"] is False
    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == ERROR_FFMPEG
    assert "decoder failed" in result["message"]
    assert not (cache / SEQUENCE_NAMESPACE / ARTIFACT_ID).exists()
    assert not list((cache / SEQUENCE_NAMESPACE).glob(".*"))
    assert source.read_bytes() == b"source-must-stay-unchanged"


def test_cancel_before_ffmpeg_and_cancel_during_runner_cleanup_without_ready_output(tmp_path):
    source = source_file(tmp_path)
    cache = tmp_path / "cache"
    before = threading.Event()
    before.set()
    result_before = extract_background_isolation_sequence(
        source,
        cache,
        ARTIFACT_ID,
        cancel_event=before,
        runner=fake_runner(),
    )
    assert result_before["status"] == STATUS_CANCELLED
    assert result_before["error_code"] == ERROR_CANCELLED
    assert not cache.exists()

    during = threading.Event()
    result_during = extract_background_isolation_sequence(
        source,
        cache,
        ARTIFACT_ID,
        cancel_event=during,
        runner=fake_runner(4, cancel_event=during),
    )
    assert result_during["status"] == STATUS_CANCELLED
    assert result_during["error_code"] == ERROR_CANCELLED
    assert not (cache / SEQUENCE_NAMESPACE / ARTIFACT_ID).exists()
    assert not list((cache / SEQUENCE_NAMESPACE).glob(".*"))


def test_no_frames_is_not_published(tmp_path):
    source = source_file(tmp_path)

    def empty_runner(command):
        return subprocess.CompletedProcess(command, 0)

    result = extract_background_isolation_sequence(source, tmp_path / "cache", ARTIFACT_ID, runner=empty_runner)

    assert result["error_code"] == ERROR_NO_FRAMES
    assert not (tmp_path / "cache" / SEQUENCE_NAMESPACE / ARTIFACT_ID).exists()


def test_existing_incomplete_output_is_never_overwritten(tmp_path):
    source = source_file(tmp_path)
    incomplete = tmp_path / "cache" / SEQUENCE_NAMESPACE / ARTIFACT_ID / "frames"
    incomplete.mkdir(parents=True)
    sentinel = incomplete / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    result = extract_background_isolation_sequence(source, tmp_path / "cache", ARTIFACT_ID, runner=fake_runner())

    assert result["error_code"] == ERROR_OUTPUT_EXISTS
    assert sentinel.read_text(encoding="utf-8") == "keep"
