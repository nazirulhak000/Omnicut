"""Deterministic, fail-closed video frame extraction for BG isolation.

The extractor is intentionally independent from ``rembg`` and from the
existing image-artifact worker.  It creates a temporary frame directory and
publishes it with one atomic directory rename only after FFmpeg succeeds and
all expected frames have been discovered.  A caller can therefore treat the
published directory as the ready boundary without relying on a half-written
manifest.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from fractions import Fraction
from pathlib import Path
from typing import Any


SEQUENCE_NAMESPACE = "background-isolation-sequences"
FRAME_PATTERN = "frame_%06d.png"
FRAME_RE = re.compile(r"^frame_(\d{6})\.png$")
SEQUENCE_ARTIFACT_ID_RE = re.compile(r"^bgseq1-[0-9a-f]{16}$")
STATUS_READY = "ready"
STATUS_ERROR = "error"
STATUS_CANCELLED = "cancelled"

ERROR_INVALID_REQUEST = "invalid_request"
ERROR_INPUT_NOT_FOUND = "input_not_found"
ERROR_INPUT_UNSAFE = "input_unsafe"
ERROR_OUTPUT_UNSAFE = "output_unsafe"
ERROR_OUTPUT_EXISTS = "output_exists"
ERROR_FFMPEG = "ffmpeg_error"
ERROR_NO_FRAMES = "no_frames"
ERROR_CANCELLED = "cancelled"

ProgressCallback = Callable[[Mapping[str, Any]], None]
Runner = Callable[[list[str]], Any]


class SequenceValidationError(ValueError):
    """Raised internally when a request cannot be made safe and canonical."""


class SequenceCancelled(RuntimeError):
    """Raised internally when cancellation is observed before publication."""


def _error(
    error_code: str,
    message: str,
    *,
    artifact_id: str | None = None,
    sequence_dir: Path | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "status": STATUS_CANCELLED if error_code == ERROR_CANCELLED else STATUS_ERROR,
        "error_code": error_code,
        "message": message,
    }
    if artifact_id is not None:
        result["artifact_id"] = artifact_id
    if sequence_dir is not None:
        result["sequence_dir"] = str(sequence_dir)
    return result


def _emit(callback: ProgressCallback | None, event: Mapping[str, Any]) -> None:
    """Notify observers without allowing a UI callback to break extraction."""

    if callback is None:
        return
    try:
        callback(dict(event))
    except Exception:
        # Progress is advisory.  FFmpeg output and cache safety must not depend
        # on a disconnected editor/UI observer.
        return


def _cancelled(cancel_event: Any) -> bool:
    if cancel_event is None:
        return False
    is_set = getattr(cancel_event, "is_set", None)
    if not callable(is_set):
        raise SequenceValidationError("cancel_event must expose is_set()")
    return bool(is_set())


def _ratio(value: Any, name: str, *, positive: bool = True) -> tuple[int, int]:
    if isinstance(value, bool):
        raise SequenceValidationError(f"{name} must be a positive number or ratio")
    try:
        if isinstance(value, (tuple, list)):
            if len(value) != 2 or any(isinstance(item, bool) for item in value):
                raise ValueError
            numerator, denominator = int(value[0]), int(value[1])
            if numerator <= 0 or denominator <= 0:
                raise ValueError
            fraction = Fraction(numerator, denominator)
        elif isinstance(value, str) and "/" in value:
            numerator_text, denominator_text = value.split("/", 1)
            numerator, denominator = int(numerator_text.strip()), int(denominator_text.strip())
            if numerator <= 0 or denominator <= 0:
                raise ValueError
            fraction = Fraction(numerator, denominator)
        else:
            fraction = Fraction(str(value))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise SequenceValidationError(f"{name} must be a valid ratio") from exc
    if positive and fraction <= 0:
        raise SequenceValidationError(f"{name} must be positive")
    return fraction.numerator, fraction.denominator


def _seconds(value: Any, name: str, *, allow_none: bool = False) -> float | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool):
        raise SequenceValidationError(f"{name} must be a non-negative number")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SequenceValidationError(f"{name} must be a non-negative number") from exc
    if parsed < 0 or parsed != parsed or parsed == float("inf"):
        raise SequenceValidationError(f"{name} must be a finite non-negative number")
    if name == "duration" and parsed == 0:
        raise SequenceValidationError("duration must be greater than zero")
    return parsed


def _path(value: Any, name: str) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise SequenceValidationError(f"{name} must be a path")
    try:
        raw_value = os.fspath(value)
    except TypeError as exc:
        raise SequenceValidationError(f"{name} must be a path") from exc
    if isinstance(raw_value, bytes):
        raw_value = os.fsdecode(raw_value)
    if not raw_value.strip():
        raise SequenceValidationError(f"{name} must be a path")
    candidate = Path(value).expanduser()
    return candidate.resolve(strict=False)


def _artifact_id(value: Any) -> str:
    if not isinstance(value, str) or not SEQUENCE_ARTIFACT_ID_RE.fullmatch(value):
        raise SequenceValidationError("artifact_id must match bgseq1-<16 lowercase hex>")
    return value


def _protected_path(path: Path) -> bool:
    protected = {"01_raw", "02_assets"}
    return any(part.casefold() in protected for part in path.parts)


def _validate_request(
    input_path: Any,
    output_sequence_root: Any,
    artifact_id: Any,
    start: Any,
    duration: Any,
    fps: Any,
    timebase: Any,
    width: Any,
    height: Any,
    cancel_event: Any,
) -> dict[str, Any]:
    source = _path(input_path, "input_path")
    output_root = _path(output_sequence_root, "output_sequence_root")
    safe_id = _artifact_id(artifact_id)
    start_seconds = _seconds(start, "start")
    duration_seconds = _seconds(duration, "duration", allow_none=True)
    fps_ratio = _ratio(fps, "fps")
    if timebase is None:
        timebase_ratio = (fps_ratio[1], fps_ratio[0])
    else:
        timebase_ratio = _ratio(timebase, "timebase")
    try:
        target_width, target_height = int(width), int(height)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SequenceValidationError("width and height must be positive integers") from exc
    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or target_width <= 0
        or target_height <= 0
        or target_width > 8192
        or target_height > 8192
    ):
        raise SequenceValidationError("width and height must be between 1 and 8192")
    if duration_seconds is not None and duration_seconds <= 0:
        raise SequenceValidationError("duration must be greater than zero")
    if not source.is_file() or source.is_symlink():
        raise SequenceValidationError("input_path must be an existing regular, non-symlink file")
    if output_root.exists() and (output_root.is_file() or output_root.is_symlink()):
        raise SequenceValidationError("output_sequence_root must be a directory path")
    if _protected_path(output_root):
        raise SequenceValidationError("output_sequence_root cannot be inside 01_Raw or 02_Assets")
    if output_root == source or output_root.is_relative_to(source):
        raise SequenceValidationError("output_sequence_root cannot be the input file")
    if cancel_event is not None:
        _cancelled(cancel_event)
    return {
        "source": source,
        "output_root": output_root,
        "artifact_id": safe_id,
        "start": start_seconds,
        "duration": duration_seconds,
        "fps_ratio": fps_ratio,
        "timebase_ratio": timebase_ratio,
        "width": target_width,
        "height": target_height,
    }


def _seconds_arg(value: float) -> str:
    rendered = f"{value:.6f}".rstrip("0").rstrip(".")
    return rendered or "0"


def _filter(fps_ratio: tuple[int, int], width: int, height: int) -> str:
    fps = f"{fps_ratio[0]}/{fps_ratio[1]}"
    return (
        f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
    )


def _command(request: Mapping[str, Any], frames_dir: Path) -> list[str]:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-ss",
        _seconds_arg(request["start"]),
        "-i",
        str(request["source"]),
    ]
    if request["duration"] is not None:
        command.extend(("-t", _seconds_arg(request["duration"])))
    command.extend(
        (
            "-vf",
            _filter(request["fps_ratio"], request["width"], request["height"]),
            "-vsync",
            "0",
            "-progress",
            "pipe:1",
            "-nostats",
            "-start_number",
            "0",
            str(frames_dir / FRAME_PATTERN),
        )
    )
    return command


def _frame_files(frames_dir: Path) -> list[Path]:
    if frames_dir.is_symlink() or not frames_dir.is_dir():
        return []
    files = []
    for candidate in frames_dir.iterdir():
        if candidate.is_symlink() or not candidate.is_file() or not FRAME_RE.fullmatch(candidate.name):
            continue
        files.append(candidate)
    return sorted(files, key=lambda path: int(FRAME_RE.fullmatch(path.name).group(1)))


def _frames_are_contiguous(files: list[Path]) -> bool:
    """A published sequence is valid only when it starts at frame zero."""

    return [int(FRAME_RE.fullmatch(path.name).group(1)) for path in files] == list(range(len(files)))


def _result(request: Mapping[str, Any], sequence_dir: Path, frames: list[Path], *, cache_hit: bool) -> dict[str, Any]:
    fps = f"{request['fps_ratio'][0]}/{request['fps_ratio'][1]}"
    timebase = f"{request['timebase_ratio'][0]}/{request['timebase_ratio'][1]}"
    return {
        "ok": True,
        "status": STATUS_READY,
        "artifact_id": request["artifact_id"],
        "sequence_dir": str(sequence_dir),
        "frames_dir": str(sequence_dir / "frames"),
        "frame_pattern": FRAME_PATTERN,
        "frames": [str(path) for path in frames],
        "frame_count": len(frames),
        "fps": fps,
        "timebase": timebase,
        "start": request["start"],
        "duration": request["duration"],
        "width": request["width"],
        "height": request["height"],
        "cache_hit": cache_hit,
    }


def _run_fake(command: list[str], runner: Runner) -> tuple[int, str, str]:
    try:
        completed = runner(command)
    except subprocess.CalledProcessError as exc:
        return int(exc.returncode or 1), str(exc.stdout or ""), str(exc.stderr or exc)
    except Exception as exc:
        return 1, "", str(exc)
    if isinstance(completed, int):
        return completed, "", ""
    return (
        int(getattr(completed, "returncode", 0)),
        str(getattr(completed, "stdout", "") or ""),
        str(getattr(completed, "stderr", "") or ""),
    )


def _run_real(
    command: list[str],
    cancel_event: Any,
    progress_callback: ProgressCallback | None,
    estimated_frames: int | None,
) -> tuple[int, str, str]:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    progress_lines: list[str] = []
    try:
        while process.poll() is None:
            if _cancelled(cancel_event):
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
                raise SequenceCancelled
            if process.stdout is not None:
                line = process.stdout.readline()
                if line:
                    progress_lines.append(line)
                    match = re.match(r"frame=(\d+)", line.strip())
                    if match:
                        frame = int(match.group(1))
                        progress = None if not estimated_frames else min(frame / estimated_frames, 0.99)
                        _emit(
                            progress_callback,
                            {"stage": "extracting", "frame": frame, "progress": progress},
                        )
                        continue
            time.sleep(0.02)
        stdout, stderr = process.communicate()
        return process.returncode or 0, "".join(progress_lines) + (stdout or ""), stderr or ""
    except SequenceCancelled:
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        raise


def extract_background_isolation_sequence(
    input_path: os.PathLike[str] | str,
    output_sequence_root: os.PathLike[str] | str,
    artifact_id: str,
    *,
    start: int | float = 0,
    duration: int | float | None = None,
    fps: int | float | str | tuple[int, int] = 30,
    timebase: str | tuple[int, int] | None = None,
    width: int = 1080,
    height: int = 1920,
    cancel_event: Any = None,
    progress_callback: ProgressCallback | None = None,
    runner: Runner | None = None,
) -> dict[str, Any]:
    """Extract a trimmed video into a safely published PNG frame sequence.

    ``runner`` exists for deterministic offline tests and must accept the
    exact FFmpeg argv list.  Production calls leave it as ``None`` and use
    ``subprocess.Popen``.  ``timebase`` is persisted as sequence metadata;
    PNG extraction itself is driven by the requested ``fps``.
    """

    try:
        request = _validate_request(
            input_path,
            output_sequence_root,
            artifact_id,
            start,
            duration,
            fps,
            timebase,
            width,
            height,
            cancel_event,
        )
    except SequenceValidationError as exc:
        code = ERROR_INPUT_NOT_FOUND if "input_path must be an existing" in str(exc) else ERROR_INVALID_REQUEST
        return _error(code, str(exc), artifact_id=artifact_id if isinstance(artifact_id, str) else None)

    namespace = request["output_root"] / SEQUENCE_NAMESPACE
    sequence_dir = namespace / request["artifact_id"]
    frames_dir = sequence_dir / "frames"
    if namespace.is_symlink() or sequence_dir.is_symlink() or frames_dir.is_symlink():
        return _error(
            ERROR_OUTPUT_UNSAFE,
            "sequence cache namespace, artifact directory, and frames directory must not be symlinks",
            artifact_id=request["artifact_id"],
            sequence_dir=sequence_dir,
        )
    if namespace.exists() and not namespace.is_dir():
        return _error(
            ERROR_OUTPUT_UNSAFE,
            "sequence cache namespace must be a directory",
            artifact_id=request["artifact_id"],
            sequence_dir=sequence_dir,
        )
    if sequence_dir.exists():
        if frames_dir.is_dir():
            existing = _frame_files(frames_dir)
            if existing and _frames_are_contiguous(existing):
                return _result(request, sequence_dir, existing, cache_hit=True)
        return _error(ERROR_OUTPUT_EXISTS, "sequence output already exists and is not a complete cache", artifact_id=request["artifact_id"], sequence_dir=sequence_dir)

    temporary_dir: Path | None = None
    try:
        if _cancelled(cancel_event):
            raise SequenceCancelled
        namespace.mkdir(parents=True, exist_ok=True)
        temporary_dir = Path(tempfile.mkdtemp(prefix=f".{request['artifact_id']}.", dir=namespace))
        temporary_frames = temporary_dir / "frames"
        temporary_frames.mkdir()
        _emit(progress_callback, {"stage": "extracting", "frame": 0, "progress": 0.0})
        command = _command(request, temporary_frames)
        estimated_frames = None
        if request["duration"] is not None:
            estimated_frames = max(1, round(request["duration"] * request["fps_ratio"][0] / request["fps_ratio"][1]))
        if runner is None:
            return_code, _, stderr = _run_real(command, cancel_event, progress_callback, estimated_frames)
        else:
            return_code, _, stderr = _run_fake(command, runner)
        if _cancelled(cancel_event):
            raise SequenceCancelled
        if return_code != 0:
            message = stderr.strip() or f"FFmpeg exited with code {return_code}"
            return _error(ERROR_FFMPEG, message, artifact_id=request["artifact_id"])
        frames = _frame_files(temporary_frames)
        if not frames:
            return _error(ERROR_NO_FRAMES, "FFmpeg completed without producing PNG frames", artifact_id=request["artifact_id"])
        if not _frames_are_contiguous(frames):
            return _error(ERROR_NO_FRAMES, "FFmpeg produced a non-contiguous frame sequence", artifact_id=request["artifact_id"])
        _emit(progress_callback, {"stage": "extracted", "frame": len(frames), "progress": 1.0})
        if _cancelled(cancel_event):
            raise SequenceCancelled
        os.replace(temporary_dir, sequence_dir)
        temporary_dir = None
        published_frames = _frame_files(frames_dir)
        if len(published_frames) != len(frames) or not _frames_are_contiguous(published_frames):
            shutil.rmtree(sequence_dir, ignore_errors=True)
            return _error(ERROR_NO_FRAMES, "published frame sequence is incomplete", artifact_id=request["artifact_id"], sequence_dir=sequence_dir)
        return _result(request, sequence_dir, published_frames, cache_hit=False)
    except SequenceCancelled:
        return _error(ERROR_CANCELLED, "frame extraction was cancelled", artifact_id=request["artifact_id"])
    except (OSError, subprocess.SubprocessError) as exc:
        return _error(ERROR_FFMPEG, str(exc), artifact_id=request["artifact_id"])
    finally:
        if temporary_dir is not None:
            shutil.rmtree(temporary_dir, ignore_errors=True)


__all__ = [
    "ERROR_CANCELLED",
    "ERROR_FFMPEG",
    "ERROR_INPUT_NOT_FOUND",
    "ERROR_INVALID_REQUEST",
    "ERROR_NO_FRAMES",
    "ERROR_OUTPUT_EXISTS",
    "ERROR_OUTPUT_UNSAFE",
    "FRAME_PATTERN",
    "SEQUENCE_NAMESPACE",
    "SEQUENCE_ARTIFACT_ID_RE",
    "STATUS_CANCELLED",
    "STATUS_ERROR",
    "STATUS_READY",
    "SequenceCancelled",
    "SequenceValidationError",
    "extract_background_isolation_sequence",
]
