"""Lazy, cache-safe rembg orchestration for foreground frame sequences.

The extractor in :mod:`background_isolation_sequence` produces source frames.
This module runs the existing one-image ``BackgroundIsolationWorker`` over
those frames and publishes a separate derived sequence only after every
foreground frame has been validated as RGBA.  It deliberately has no Preview,
Render, FFmpeg, or model-download side effects.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from PIL import Image

from .background_isolation import normalize_background_isolation
from .background_isolation_sequence_artifacts import (
    FRAME_PATTERN,
    SEQUENCE_SCHEMA_VERSION,
    SequenceArtifactStoreError,
    build_sequence_artifact_id,
    build_sequence_manifest,
)
from .background_isolation_worker import (
    STATUS_NOOP,
    STATUS_READY,
    BackgroundIsolationWorker,
)


DERIVED_CACHE_NAMESPACE = "background-isolation-foreground-sequences"
WORKER_VERSION = "sequence-rembg-worker-v1"
STATUS_ERROR = "error"
STATUS_CANCELLED = "cancelled"

ERROR_CONFIG_MISSING = "config_missing"
ERROR_CONFIG_DISABLED = "config_disabled"
ERROR_CONFIG_INVALID = "config_invalid"
ERROR_INPUT_MISSING = "input_missing"
ERROR_INPUT_INCOMPLETE = "input_sequence_incomplete"
ERROR_MANIFEST_MISSING = "manifest_missing"
ERROR_MANIFEST_INVALID = "manifest_invalid"
ERROR_OUTPUT_UNSAFE = "output_unsafe"
ERROR_CANCELLED = "cancelled"
ERROR_WORKER_FAILURE = "foreground_worker_failed"
ERROR_OUTPUT_COMMIT = "foreground_sequence_commit_failed"
ERROR_OUTPUT_INVALID = "invalid_foreground_output"

_ARTIFACT_ID_RE = re.compile(r"^bgseq1-[0-9a-f]{16}$")
_FRAME_RE = re.compile(r"^frame_(\d{6})\.png$")
_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "status",
        "source_fingerprint",
        "algorithm",
        "engine",
        "model",
        "quality",
        "worker_version",
        "frame_count",
        "fps",
        "timebase",
        "width",
        "height",
        "rotation",
        "frame_pattern",
    }
)

ProgressCallback = Callable[[Mapping[str, Any]], None]


def _result(
    *,
    ok: bool,
    status: str,
    message: str,
    error_code: str | None = None,
    artifact_id: str | None = None,
    source_artifact_id: str | None = None,
    output_directory: Path | None = None,
    frame_count: int | None = None,
    cache_hit: bool = False,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "status": status,
        "error_code": error_code,
        "message": message,
        "artifact_id": artifact_id,
        "source_sequence_artifact_id": source_artifact_id,
        "output_directory": str(output_directory) if output_directory is not None else None,
        "frames_directory": str(output_directory / "frames") if output_directory is not None else None,
        "frame_count": frame_count,
        "cache_hit": cache_hit,
    }


def _emit(callback: ProgressCallback | None, event: Mapping[str, Any]) -> None:
    """Progress is advisory and must never break artifact publication."""

    if callback is None:
        return
    try:
        callback(dict(event))
    except Exception:
        return


def _is_cancelled(cancel_event: Any) -> bool:
    if cancel_event is None:
        return False
    is_set = getattr(cancel_event, "is_set", None)
    if not callable(is_set):
        raise ValueError("cancel_event must expose is_set()")
    return bool(is_set())


def _path(value: Any, label: str) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError(f"{label} must be a path")
    candidate = Path(value).expanduser().resolve(strict=False)
    if not str(candidate):
        raise ValueError(f"{label} must be a path")
    return candidate


def _protected_path(path: Path) -> bool:
    return any(part.casefold() in {"01_raw", "02_assets"} for part in path.parts)


def _safe_artifact_id(value: Any) -> str:
    if not isinstance(value, str) or not _ARTIFACT_ID_RE.fullmatch(value):
        raise ValueError("manifest artifact_id must match bgseq1-<16 lowercase hex>")
    return value


def _load_manifest(
    source: Path,
    manifest: Mapping[str, Any] | str | os.PathLike[str] | None,
) -> dict[str, Any]:
    if manifest is None:
        candidates = []
        if source.name.casefold() == "frames":
            candidates.append(source.parent / "manifest.json")
        else:
            candidates.append(source / "manifest.json")
        selected = next((candidate for candidate in candidates if candidate.is_file()), None)
        if selected is None:
            raise FileNotFoundError("sequence manifest was not provided")
        manifest = selected

    if isinstance(manifest, Mapping):
        value = dict(manifest)
    else:
        manifest_path = _path(manifest, "sequence_manifest")
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise FileNotFoundError("sequence manifest does not exist")
        try:
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("sequence manifest is not valid JSON") from exc

    if not isinstance(value, Mapping) or set(value) != _MANIFEST_KEYS:
        raise ValueError("sequence manifest has an invalid schema")
    try:
        canonical = build_sequence_manifest(
            _safe_artifact_id(value["artifact_id"]),
            source_fingerprint=value["source_fingerprint"],
            algorithm=value["algorithm"],
            engine=value["engine"],
            model=value["model"],
            quality=value["quality"],
            worker_version=value["worker_version"],
            frame_count=value["frame_count"],
            fps=value["fps"],
            timebase=value["timebase"],
            width=value["width"],
            height=value["height"],
            rotation=value["rotation"],
            frame_pattern=value["frame_pattern"],
            status=value["status"],
        )
    except (KeyError, SequenceArtifactStoreError) as exc:
        raise ValueError("sequence manifest contains invalid metadata") from exc
    if canonical["schema_version"] != SEQUENCE_SCHEMA_VERSION or canonical["status"] != "ready":
        raise ValueError("source sequence manifest must be ready")
    if canonical["frame_count"] <= 0 or canonical["fps"] <= 0:
        raise ValueError("source sequence manifest has no usable frames")
    return canonical


def _resolve_source_frames(source: Path, manifest: Mapping[str, Any]) -> Path:
    artifact_id = _safe_artifact_id(manifest["artifact_id"])
    candidates = []
    if source.name.casefold() == "frames":
        candidates.append(source)
    candidates.extend(
        (
            source / "frames",
            source / "background-isolation-sequences" / artifact_id / "frames",
            source / artifact_id / "frames",
        )
    )
    for candidate in candidates:
        if candidate.is_dir() and not candidate.is_symlink():
            return candidate.resolve()
    raise FileNotFoundError("source frame directory does not exist")


def _frame_paths(directory: Path, frame_count: int) -> list[Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise FileNotFoundError("source frame directory does not exist")
    entries = list(directory.iterdir())
    expected_names = {f"frame_{index:06d}.png" for index in range(frame_count)}
    actual_names = {entry.name for entry in entries if _FRAME_RE.fullmatch(entry.name)}
    if actual_names != expected_names:
        raise ValueError("source frame sequence is incomplete or non-contiguous")
    paths = [directory / name for name in sorted(expected_names)]
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError("source frame sequence contains an unsafe frame")
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception as exc:
            raise ValueError(f"source frame is not a readable PNG: {path.name}") from exc
    return paths


def _derived_artifact_id(
    source_manifest: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    worker_version: str = WORKER_VERSION,
) -> str:
    normalized = normalize_background_isolation(config)
    source_identity = f"{source_manifest['source_fingerprint']}|sequence:{source_manifest['artifact_id']}"
    return build_sequence_artifact_id(
        source_identity,
        algorithm="background-isolation-v1",
        engine=normalized["engine"],
        model=normalized["model"],
        quality=normalized["quality"],
        worker_version=worker_version,
        fps=source_manifest["fps"],
        timebase=source_manifest["timebase"],
        width=source_manifest["width"],
        height=source_manifest["height"],
        rotation=source_manifest["rotation"],
    )


def _derived_manifest(
    artifact_id: str,
    source_manifest: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    status: str,
    worker_version: str = WORKER_VERSION,
) -> dict[str, Any]:
    normalized = normalize_background_isolation(config)
    return build_sequence_manifest(
        artifact_id,
        source_fingerprint=source_manifest["source_fingerprint"],
        algorithm="background-isolation-v1",
        engine=normalized["engine"],
        model=normalized["model"],
        quality=normalized["quality"],
        worker_version=worker_version,
        frame_count=source_manifest["frame_count"],
        fps=source_manifest["fps"],
        timebase=source_manifest["timebase"],
        width=source_manifest["width"],
        height=source_manifest["height"],
        rotation=source_manifest["rotation"],
        frame_pattern=FRAME_PATTERN,
        status=status,
    )


def _write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    payload = json.dumps(dict(manifest), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _read_manifest(path: Path) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            return None
        return dict(value)
    except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _rgba_frame_is_valid(path: Path, expected_size: tuple[int, int]) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return image.mode == "RGBA" and image.size == expected_size
    except Exception:
        return False


def _derived_frames_are_current(directory: Path, manifest: Mapping[str, Any]) -> bool:
    if manifest.get("status") != "ready":
        return False
    frame_count = manifest.get("frame_count")
    width = manifest.get("width")
    height = manifest.get("height")
    if not isinstance(frame_count, int) or frame_count <= 0 or not isinstance(width, int) or not isinstance(height, int):
        return False
    frames = directory / "frames"
    if frames.is_symlink() or not frames.is_dir():
        return False
    expected = {f"frame_{index:06d}.png" for index in range(frame_count)}
    actual = {entry.name for entry in frames.iterdir() if _FRAME_RE.fullmatch(entry.name)}
    if actual != expected:
        return False
    return all(_rgba_frame_is_valid(frames / name, (width, height)) for name in expected)


def _manifest_matches(expected: Mapping[str, Any], actual: Mapping[str, Any] | None) -> bool:
    if actual is None or set(actual) != _MANIFEST_KEYS:
        return False
    return all(actual.get(key) == value for key, value in expected.items())


def _cleanup(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
    except OSError:
        return


def _checkpoint_frame_paths(directory: Path, frame_count: int, expected_size: tuple[int, int]) -> list[Path]:
    """Return the valid contiguous prefix of a resumable checkpoint.

    A frame is considered committed only after the RGBA file has been fully
    written and passes verification.  A truncated frame left by a hard kill
    is removed and rebuilt; later frames are ignored until the prefix is
    contiguous again.
    """

    directory.mkdir(parents=True, exist_ok=True)
    committed: list[Path] = []
    for index in range(frame_count):
        path = directory / f"frame_{index:06d}.png"
        if not _rgba_frame_is_valid(path, expected_size):
            if path.exists() and not path.is_symlink():
                path.unlink(missing_ok=True)
            break
        committed.append(path)
    return committed


def _publish_atomically(temporary: Path, target: Path) -> None:
    """Publish without ever replacing an existing artifact directory.

    The ready manifest is moved last.  That makes the directory fail closed
    while it is being published, and ``mkdir`` gives us an exclusive,
    cross-platform no-clobber claim on the artifact ID.  An existing target
    is never moved, edited, or removed; callers must choose a new processing
    version when they intentionally regenerate an artifact.
    """

    created = False
    try:
        try:
            target.mkdir()
            created = True
        except FileExistsError:
            # If target exists without a ready manifest.json, it is an abandoned publication
            # that failed mid-flight before the manifest was committed. Clean it up and retry.
            if not (target / "manifest.json").is_file():
                _cleanup(target)
                target.mkdir()
                created = True
            else:
                raise
        os.replace(temporary / "frames", target / "frames")
        os.replace(temporary / "manifest.json", target / "manifest.json")
        temporary.rmdir()
    except OSError:
        if created:
            _cleanup(target)
        raise


class BackgroundIsolationSequenceWorker:
    """Run one reusable image worker over a validated source sequence."""

    def __init__(
        self,
        *,
        worker: BackgroundIsolationWorker | Any | None = None,
        loader: Callable[[], Any] | None = None,
    ) -> None:
        self._worker = worker or BackgroundIsolationWorker(loader=loader)

    def process(
        self,
        source_sequence: str | os.PathLike[str],
        derived_root: str | os.PathLike[str],
        config: Mapping[str, Any] | None,
        sequence_manifest: Mapping[str, Any] | str | os.PathLike[str] | None = None,
        *,
        cancel_event: Any = None,
        progress_callback: ProgressCallback | None = None,
        worker_version: str = WORKER_VERSION,
    ) -> dict[str, Any]:
        if config is None:
            return _result(ok=True, status=STATUS_NOOP, error_code=ERROR_CONFIG_MISSING, message="Background isolation is not configured; skipped.")
        normalized = normalize_background_isolation(config)
        if not normalized["enabled"]:
            reason = normalized.get("reason", "disabled")
            code = ERROR_CONFIG_DISABLED if reason == "disabled" else ERROR_CONFIG_INVALID
            return _result(ok=True, status=STATUS_NOOP, error_code=code, message=f"Background isolation is disabled or invalid ({reason}); skipped.")

        source_artifact_id: str | None = None
        output_directory: Path | None = None
        checkpoint: Path | None = None
        temporary: Path | None = None
        try:
            if _is_cancelled(cancel_event):
                return _result(ok=False, status=STATUS_CANCELLED, error_code=ERROR_CANCELLED, message="Foreground sequence processing was cancelled.")
            source = _path(source_sequence, "source_sequence")
            output_root = _path(derived_root, "derived_root")
            if _protected_path(output_root) or (output_root.exists() and output_root.is_symlink()):
                raise PermissionError("derived root is unsafe")
            manifest = _load_manifest(source, sequence_manifest)
            source_artifact_id = _safe_artifact_id(manifest["artifact_id"])
            source_frames = _resolve_source_frames(source, manifest)
            if output_root == source_frames or output_root.is_relative_to(source_frames):
                raise PermissionError("derived root cannot be inside source frames")
            source_paths = _frame_paths(source_frames, manifest["frame_count"])
            artifact_id = _derived_artifact_id(manifest, normalized, worker_version=worker_version)
            output_namespace = output_root / DERIVED_CACHE_NAMESPACE
            output_directory = output_namespace / artifact_id
            if output_namespace.is_symlink() or output_directory.is_symlink():
                raise PermissionError("derived cache namespace must not contain symlinks")
            if output_namespace.exists() and not output_namespace.is_dir():
                raise PermissionError("derived cache namespace must be a directory")
            expected_manifest = _derived_manifest(
                artifact_id,
                manifest,
                normalized,
                status="ready",
                worker_version=worker_version,
            )
            existing_manifest = _read_manifest(output_directory / "manifest.json")
            if _manifest_matches(expected_manifest, existing_manifest) and _derived_frames_are_current(output_directory, existing_manifest):
                return _result(ok=True, status=STATUS_READY, message="Foreground sequence cache hit.", artifact_id=artifact_id, source_artifact_id=source_artifact_id, output_directory=output_directory, frame_count=manifest["frame_count"], cache_hit=True)

            output_namespace.mkdir(parents=True, exist_ok=True)
            # A process can die after claiming the target and moving frames,
            # but before publishing the ready manifest. That directory is
            # never readable as an artifact, and its deterministic checkpoint
            # is still intact. Remove only this non-ready derived target so a
            # retry can publish it; a valid ready artifact returned above is
            # never touched.
            if output_directory.exists() and existing_manifest is None:
                _cleanup(output_directory)
            # The checkpoint has a deterministic name so a retry after a
            # network loss, process restart, or worker crash can reuse frames
            # already completed.  It is never exposed by the reader because
            # only the final artifact directory with a ready manifest is
            # considered publishable.
            checkpoint = output_namespace / f".{artifact_id}.checkpoint"
            if checkpoint.is_symlink() or (checkpoint.exists() and not checkpoint.is_dir()):
                raise PermissionError("foreground checkpoint must be a directory")
            checkpoint.mkdir(parents=True, exist_ok=True)
            checkpoint_frames = checkpoint / "frames"
            committed = _checkpoint_frame_paths(
                checkpoint_frames,
                len(source_paths),
                (manifest["width"], manifest["height"]),
            )
            _emit(progress_callback, {"stage": "isolating", "frame": len(committed), "frame_count": len(source_paths), "progress": len(committed) / len(source_paths), "artifact_id": artifact_id, "resumed": bool(committed)})
            for index, source_frame in enumerate(source_paths):
                if _is_cancelled(cancel_event):
                    return _result(ok=False, status=STATUS_CANCELLED, error_code=ERROR_CANCELLED, message="Foreground sequence processing was cancelled.", artifact_id=artifact_id, source_artifact_id=source_artifact_id)
                target_frame = checkpoint_frames / f"frame_{index:06d}.png"
                if index < len(committed):
                    continue
                try:
                    worker_result = self._worker.process(source_frame, target_frame, normalized)
                except Exception as exc:
                    return _result(ok=False, status=STATUS_ERROR, error_code=ERROR_WORKER_FAILURE, message=f"Foreground worker failed on frame {index}: {exc}", artifact_id=artifact_id, source_artifact_id=source_artifact_id)
                if not isinstance(worker_result, Mapping) or worker_result.get("status") != STATUS_READY:
                    error_code = worker_result.get("error_code") if isinstance(worker_result, Mapping) else None
                    message = worker_result.get("message") if isinstance(worker_result, Mapping) else "Foreground worker returned an invalid result."
                    return _result(ok=False, status=STATUS_ERROR, error_code=error_code or ERROR_WORKER_FAILURE, message=str(message), artifact_id=artifact_id, source_artifact_id=source_artifact_id)
                if not _rgba_frame_is_valid(target_frame, (manifest["width"], manifest["height"])):
                    return _result(ok=False, status=STATUS_ERROR, error_code=ERROR_OUTPUT_INVALID, message=f"Foreground worker did not produce a valid RGBA frame: {target_frame.name}", artifact_id=artifact_id, source_artifact_id=source_artifact_id)
                _emit(progress_callback, {"stage": "isolating", "frame": index + 1, "frame_count": len(source_paths), "progress": (index + 1) / len(source_paths), "artifact_id": artifact_id})
            if _is_cancelled(cancel_event):
                return _result(ok=False, status=STATUS_CANCELLED, error_code=ERROR_CANCELLED, message="Foreground sequence processing was cancelled.", artifact_id=artifact_id, source_artifact_id=source_artifact_id)
            # Copy the completed checkpoint into a private publish directory.
            # The checkpoint remains intact until publication succeeds, so a
            # failed commit can be retried without losing inference work.
            temporary = Path(tempfile.mkdtemp(prefix=f".{artifact_id}.publish.", dir=output_namespace))
            shutil.copytree(checkpoint_frames, temporary / "frames")
            _write_manifest(temporary / "manifest.json", expected_manifest)
            _publish_atomically(temporary, output_directory)
            temporary = None
            if not _manifest_matches(expected_manifest, _read_manifest(output_directory / "manifest.json")) or not _derived_frames_are_current(output_directory, expected_manifest):
                _cleanup(output_directory)
                return _result(ok=False, status=STATUS_ERROR, error_code=ERROR_OUTPUT_COMMIT, message="Published foreground sequence failed its ready verification.", artifact_id=artifact_id, source_artifact_id=source_artifact_id)
            _cleanup(checkpoint)
            return _result(ok=True, status=STATUS_READY, message="Foreground sequence created successfully.", artifact_id=artifact_id, source_artifact_id=source_artifact_id, output_directory=output_directory, frame_count=len(source_paths))
        except FileNotFoundError as exc:
            return _result(ok=False, status=STATUS_ERROR, error_code=ERROR_INPUT_MISSING if "manifest" not in str(exc).lower() else ERROR_MANIFEST_MISSING, message=str(exc), source_artifact_id=source_artifact_id)
        except ValueError as exc:
            code = ERROR_MANIFEST_INVALID if "manifest" in str(exc).lower() else ERROR_INPUT_INCOMPLETE
            return _result(ok=False, status=STATUS_ERROR, error_code=code, message=str(exc), source_artifact_id=source_artifact_id)
        except PermissionError as exc:
            return _result(ok=False, status=STATUS_ERROR, error_code=ERROR_OUTPUT_UNSAFE, message=str(exc), artifact_id=output_directory.name if output_directory else None, source_artifact_id=source_artifact_id)
        except (OSError, SequenceArtifactStoreError) as exc:
            return _result(ok=False, status=STATUS_ERROR, error_code=ERROR_OUTPUT_COMMIT, message=f"Could not publish foreground sequence: {exc}", artifact_id=output_directory.name if output_directory else None, source_artifact_id=source_artifact_id)
        finally:
            _cleanup(temporary)


def process_background_isolation_sequence(
    source_sequence: str | os.PathLike[str],
    derived_root: str | os.PathLike[str],
    config: Mapping[str, Any] | None,
    sequence_manifest: Mapping[str, Any] | str | os.PathLike[str] | None = None,
    *,
    worker: BackgroundIsolationWorker | Any | None = None,
    loader: Callable[[], Any] | None = None,
    cancel_event: Any = None,
    progress_callback: ProgressCallback | None = None,
    worker_version: str = WORKER_VERSION,
) -> dict[str, Any]:
    """Process a sequence with one lazy worker for the whole sequence.

    Pass a new, explicit ``worker_version`` for a reviewed quality
    regeneration.  The version participates in the artifact identity, so the
    old artifact remains available and byte-for-byte untouched.
    """

    return BackgroundIsolationSequenceWorker(worker=worker, loader=loader).process(
        source_sequence,
        derived_root,
        config,
        sequence_manifest,
        cancel_event=cancel_event,
        progress_callback=progress_callback,
        worker_version=worker_version,
    )


process_sequence = process_background_isolation_sequence
process_background_isolation_sequence_bundle = process_background_isolation_sequence


__all__ = [
    "DERIVED_CACHE_NAMESPACE",
    "ERROR_CANCELLED",
    "ERROR_CONFIG_DISABLED",
    "ERROR_CONFIG_INVALID",
    "ERROR_CONFIG_MISSING",
    "ERROR_INPUT_INCOMPLETE",
    "ERROR_INPUT_MISSING",
    "ERROR_MANIFEST_INVALID",
    "ERROR_MANIFEST_MISSING",
    "ERROR_OUTPUT_COMMIT",
    "ERROR_OUTPUT_INVALID",
    "ERROR_OUTPUT_UNSAFE",
    "ERROR_WORKER_FAILURE",
    "STATUS_CANCELLED",
    "STATUS_ERROR",
    "STATUS_NOOP",
    "STATUS_READY",
    "WORKER_VERSION",
    "BackgroundIsolationSequenceWorker",
    "process_background_isolation_sequence",
    "process_background_isolation_sequence_bundle",
    "process_sequence",
]
