"""Safe cache primitives for frame-sequence background-isolation artifacts.

The image artifact store intentionally remains untouched.  A sequence has a
different lifecycle and identity: one source asset may be used by multiple
clips, while each clip can choose a different trim.  Consequently this module
keys the cache by the source fingerprint and processing signature, never by a
clip index.

This module owns metadata and derived frame files only.  It does not import
``rembg``, open source media, invoke FFmpeg, or make a ``ready`` claim for an
incomplete/cancelled/failed sequence.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.background_isolation import (
    DEFAULT_ENGINE,
    DEFAULT_MODEL,
    DEFAULT_QUALITY,
    MAX_SOURCE_FINGERPRINT_LENGTH,
    SUPPORTED_ENGINES,
    SUPPORTED_MODELS,
    SUPPORTED_QUALITIES,
)

CACHE_NAMESPACE = "background-isolation-sequences"
MANIFEST_FILENAME = "manifest.json"
FRAMES_DIRECTORY = "frames"
FRAME_PATTERN = f"{FRAMES_DIRECTORY}/frame_%06d.png"
SEQUENCE_ARTIFACT_PREFIX = "bgseq1-"
SEQUENCE_SCHEMA_VERSION = 1
DEFAULT_ALGORITHM = "background-isolation-v1"
DEFAULT_WORKER_VERSION = "sequence-worker-v1"

SEQUENCE_STATUSES = frozenset(
    {"missing", "processing", "ready", "stale", "error", "cancelled"}
)
_ARTIFACT_ID_RE = re.compile(r"^bgseq1-[0-9a-f]{16}$")
_TIMEBASE_RE = re.compile(r"^[1-9][0-9]*/[1-9][0-9]*$")
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
_SIGNATURE_KEYS = frozenset(
    {
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


class SequenceArtifactStoreError(ValueError):
    """Raised when a sequence identity, manifest, or frame is unsafe."""


# A short alias makes call sites read naturally while preserving the explicit
# name for callers that also use the image artifact store.
ArtifactStoreError = SequenceArtifactStoreError


@dataclass(frozen=True)
class BackgroundIsolationSequencePaths:
    """Deterministic paths for one sequence identity below a caller root."""

    directory: Path
    manifest: Path
    frames: Path


def _cache_root(cache_root: os.PathLike[str] | str) -> Path:
    if not isinstance(cache_root, (str, os.PathLike)):
        raise SequenceArtifactStoreError("cache root must be a path-like value")
    return Path(cache_root).expanduser().resolve(strict=False)


def _validate_artifact_id(artifact_id: Any) -> str:
    if not isinstance(artifact_id, str) or not _ARTIFACT_ID_RE.fullmatch(artifact_id):
        raise SequenceArtifactStoreError("invalid background isolation sequence artifact id")
    return artifact_id


def _ensure_under_root(path: Path, root: Path) -> Path:
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise SequenceArtifactStoreError("sequence artifact path escapes cache root") from exc
    return resolved


def sequence_paths(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
) -> BackgroundIsolationSequencePaths:
    """Return guarded manifest/frame paths without creating anything."""

    root = _cache_root(cache_root)
    safe_id = _validate_artifact_id(artifact_id)
    namespace = root / CACHE_NAMESPACE
    directory = namespace / safe_id
    frames = directory / FRAMES_DIRECTORY
    if namespace.is_symlink() or directory.is_symlink() or frames.is_symlink():
        raise SequenceArtifactStoreError("sequence cache namespace must not contain symlinks")
    _ensure_under_root(directory, root)
    return BackgroundIsolationSequencePaths(
        directory=directory,
        manifest=directory / MANIFEST_FILENAME,
        frames=frames,
    )


def artifact_paths(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
) -> BackgroundIsolationSequencePaths:
    """Compatibility alias matching the image artifact store naming style."""

    return sequence_paths(cache_root, artifact_id)


def get_sequence_paths(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
) -> BackgroundIsolationSequencePaths:
    return sequence_paths(cache_root, artifact_id)


def _validate_source_fingerprint(value: Any) -> str:
    if not isinstance(value, str):
        raise SequenceArtifactStoreError("source fingerprint must be a string")
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_SOURCE_FINGERPRINT_LENGTH:
        raise SequenceArtifactStoreError("invalid source fingerprint")
    return candidate


def _validate_choice(value: Any, allowed: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise SequenceArtifactStoreError(f"invalid sequence {label}")
    return value


def _validate_positive_int(value: Any, label: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SequenceArtifactStoreError(f"invalid sequence {label}")
    if value < 0 or (value == 0 and not allow_zero):
        raise SequenceArtifactStoreError(f"invalid sequence {label}")
    return value


def _validate_fps(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SequenceArtifactStoreError("invalid sequence fps")
    candidate = float(value)
    if not math.isfinite(candidate) or candidate < 0:
        raise SequenceArtifactStoreError("invalid sequence fps")
    return candidate


def _normalise_timebase(value: Any) -> str:
    if isinstance(value, tuple) and len(value) == 2:
        value = f"{value[0]}/{value[1]}"
    if not isinstance(value, str) or not _TIMEBASE_RE.fullmatch(value):
        raise SequenceArtifactStoreError("invalid sequence timebase")
    return value


def _validate_rotation(value: Any) -> int:
    if isinstance(value, bool) or value not in (0, 90, 180, 270):
        raise SequenceArtifactStoreError("invalid sequence rotation")
    return value


def _validate_frame_pattern(value: Any) -> str:
    # Keep the pattern fixed.  It makes the frame path derivation auditable
    # and prevents a manifest from redirecting consumers outside ``frames``.
    if value != FRAME_PATTERN:
        raise SequenceArtifactStoreError("invalid sequence frame pattern")
    return FRAME_PATTERN


def _validate_status(value: Any) -> str:
    if not isinstance(value, str) or value not in SEQUENCE_STATUSES:
        raise SequenceArtifactStoreError("invalid background isolation sequence status")
    return value


def build_sequence_artifact_id(
    source_fingerprint: Any,
    *,
    algorithm: str = DEFAULT_ALGORITHM,
    engine: str = DEFAULT_ENGINE,
    model: str = DEFAULT_MODEL,
    quality: str = DEFAULT_QUALITY,
    worker_version: str = DEFAULT_WORKER_VERSION,
    fps: Any = 30.0,
    timebase: Any = "1/30",
    width: Any = 1080,
    height: Any = 1920,
    rotation: Any = 0,
) -> str:
    """Build an ID from source/settings, deliberately excluding clip index."""

    fingerprint = _validate_source_fingerprint(source_fingerprint)
    identity = {
        "source_fingerprint": fingerprint,
        "algorithm": _validate_non_empty_text(algorithm, "algorithm"),
        "engine": _validate_choice(engine, SUPPORTED_ENGINES, "engine"),
        "model": _validate_choice(model, SUPPORTED_MODELS, "model"),
        "quality": _validate_choice(quality, SUPPORTED_QUALITIES, "quality"),
        "worker_version": _validate_non_empty_text(worker_version, "worker version"),
        "fps": _validate_fps(fps),
        "timebase": _normalise_timebase(timebase),
        "width": _validate_positive_int(width, "width"),
        "height": _validate_positive_int(height, "height"),
        "rotation": _validate_rotation(rotation),
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return f"{SEQUENCE_ARTIFACT_PREFIX}{digest}"


def _validate_non_empty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise SequenceArtifactStoreError(f"invalid sequence {label}")
    return value.strip()


def build_sequence_manifest(
    artifact_id: str,
    *,
    source_fingerprint: str,
    algorithm: str = DEFAULT_ALGORITHM,
    engine: str = DEFAULT_ENGINE,
    model: str = DEFAULT_MODEL,
    quality: str = DEFAULT_QUALITY,
    worker_version: str = DEFAULT_WORKER_VERSION,
    frame_count: int = 0,
    fps: float = 0.0,
    timebase: str = "1/1",
    width: int = 0,
    height: int = 0,
    rotation: int = 0,
    frame_pattern: str = FRAME_PATTERN,
    status: str = "missing",
) -> dict[str, Any]:
    """Build a canonical manifest without touching the filesystem."""

    safe_id = _validate_artifact_id(artifact_id)
    canonical_status = _validate_status(status)
    manifest = {
        "schema_version": SEQUENCE_SCHEMA_VERSION,
        "artifact_id": safe_id,
        "status": canonical_status,
        "source_fingerprint": _validate_source_fingerprint(source_fingerprint),
        "algorithm": _validate_non_empty_text(algorithm, "algorithm"),
        "engine": _validate_choice(engine, SUPPORTED_ENGINES, "engine"),
        "model": _validate_choice(model, SUPPORTED_MODELS, "model"),
        "quality": _validate_choice(quality, SUPPORTED_QUALITIES, "quality"),
        "worker_version": _validate_non_empty_text(worker_version, "worker version"),
        "frame_count": _validate_positive_int(frame_count, "frame count", allow_zero=True),
        "fps": _validate_fps(fps),
        "timebase": _normalise_timebase(timebase),
        "width": _validate_positive_int(width, "width", allow_zero=True),
        "height": _validate_positive_int(height, "height", allow_zero=True),
        "rotation": _validate_rotation(rotation),
        "frame_pattern": _validate_frame_pattern(frame_pattern),
    }
    return manifest


def _validate_manifest(value: Any, expected_id: str) -> dict[str, Any] | None:
    if not isinstance(value, Mapping) or set(value) != _MANIFEST_KEYS:
        return None
    try:
        candidate = build_sequence_manifest(
            expected_id,
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
    except SequenceArtifactStoreError:
        return None
    if value.get("schema_version") != SEQUENCE_SCHEMA_VERSION:
        return None
    if value.get("artifact_id") != expected_id:
        return None
    return candidate


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def write_sequence_manifest(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
    manifest: Mapping[str, Any] | None = None,
    *,
    status: str | None = None,
) -> dict[str, Any]:
    """Validate and atomically persist one canonical sequence manifest."""

    safe_id = _validate_artifact_id(artifact_id)
    if manifest is None:
        if status not in (None, "missing", "processing", "error", "cancelled", "stale"):
            raise SequenceArtifactStoreError("metadata is required before a ready sequence manifest")
        raise SequenceArtifactStoreError("sequence manifest metadata is required")
    candidate = dict(manifest)
    if status is not None:
        candidate["status"] = status
    canonical = _validate_manifest(candidate, safe_id)
    if canonical is None:
        raise SequenceArtifactStoreError("invalid background isolation sequence manifest")
    paths = sequence_paths(cache_root, safe_id)
    if canonical["status"] == "ready" and (
        not _ready_metadata_is_valid(canonical)
        or not _frames_complete(paths, canonical["frame_count"])
    ):
        raise SequenceArtifactStoreError("sequence cannot be ready before all frames are present")
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _atomic_write_bytes(paths.manifest, payload)
    return canonical


def read_sequence_manifest(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
) -> dict[str, Any] | None:
    """Read a manifest, returning ``None`` for malformed or unsafe data."""

    safe_id = _validate_artifact_id(artifact_id)
    paths = sequence_paths(cache_root, safe_id)
    if paths.manifest.is_symlink():
        return None
    try:
        value = json.loads(paths.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return _validate_manifest(value, safe_id)


def sequence_frame_path(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
    frame_index: int,
) -> Path:
    """Return a guarded zero-based frame path for FFmpeg's frame pattern."""

    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or not 0 <= frame_index <= 999999:
        raise SequenceArtifactStoreError("invalid sequence frame index")
    paths = sequence_paths(cache_root, artifact_id)
    destination = paths.frames / f"frame_{frame_index:06d}.png"
    _ensure_under_root(destination, paths.directory)
    if destination.is_symlink():
        raise SequenceArtifactStoreError("sequence frame must not be a symlink")
    return destination


def write_sequence_frame(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
    frame_index: int,
    payload: bytes,
) -> Path:
    """Atomically write one derived frame without accepting arbitrary names."""

    if not isinstance(payload, bytes):
        raise SequenceArtifactStoreError("sequence frame payload must be bytes")
    destination = sequence_frame_path(cache_root, artifact_id, frame_index)
    if destination.parent.is_symlink():
        raise SequenceArtifactStoreError("sequence frames directory must not be a symlink")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(destination, payload)
    return destination


def _frames_complete(paths: BackgroundIsolationSequencePaths, frame_count: int) -> bool:
    if not paths.frames.is_dir() or paths.frames.is_symlink():
        return False
    for index in range(frame_count):
        frame = paths.frames / f"frame_{index:06d}.png"
        if not frame.is_file() or frame.is_symlink():
            return False
    return True


def _ready_metadata_is_valid(manifest: Mapping[str, Any]) -> bool:
    return (
        manifest["frame_count"] > 0
        and manifest["fps"] > 0
        and manifest["width"] > 0
        and manifest["height"] > 0
    )


def sequence_status(cache_root: os.PathLike[str] | str, artifact_id: str) -> str:
    """Return a fail-closed status; an incomplete ``ready`` is ``stale``."""

    paths = sequence_paths(cache_root, artifact_id)
    if paths.manifest.is_symlink():
        return "stale"
    if not paths.manifest.exists():
        return "missing"
    manifest = read_sequence_manifest(cache_root, artifact_id)
    if manifest is None:
        return "stale"
    if manifest["status"] == "ready" and (
        not _ready_metadata_is_valid(manifest)
        or not _frames_complete(paths, manifest["frame_count"])
    ):
        return "stale"
    return manifest["status"]


def is_sequence_ready(cache_root: os.PathLike[str] | str, artifact_id: str) -> bool:
    return sequence_status(cache_root, artifact_id) == "ready"


def is_sequence_current(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
    expected: Mapping[str, Any] | None = None,
) -> bool:
    """Return true only for a complete ready sequence matching ``expected``."""

    if not is_sequence_ready(cache_root, artifact_id):
        return False
    manifest = read_sequence_manifest(cache_root, artifact_id)
    if manifest is None:
        return False
    if expected is None:
        return True
    if not isinstance(expected, Mapping) or not set(expected).issubset(_SIGNATURE_KEYS):
        return False
    for key, value in expected.items():
        if key == "timebase":
            try:
                value = _normalise_timebase(value)
            except SequenceArtifactStoreError:
                return False
        elif key == "frame_pattern":
            if value != FRAME_PATTERN:
                return False
        elif key in {"fps"}:
            try:
                value = _validate_fps(value)
            except SequenceArtifactStoreError:
                return False
        if manifest[key] != value:
            return False
    return True


def sequence_is_current(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
    expected: Mapping[str, Any] | None = None,
) -> bool:
    """Alias for callers that prefer the predicate naming of the old store."""

    return is_sequence_current(cache_root, artifact_id, expected)


def clear_sequence(cache_root: os.PathLike[str] | str, artifact_id: str) -> bool:
    """Remove exactly one validated sequence directory below ``cache_root``."""

    root = _cache_root(cache_root)
    paths = sequence_paths(root, artifact_id)
    target = paths.directory
    if not target.exists():
        return False
    if target.is_symlink() or not target.is_dir():
        raise SequenceArtifactStoreError("sequence artifact directory is not a real directory")
    _ensure_under_root(target, root)
    shutil.rmtree(target)
    return True


__all__ = [
    "ArtifactStoreError",
    "BackgroundIsolationSequencePaths",
    "CACHE_NAMESPACE",
    "DEFAULT_ALGORITHM",
    "DEFAULT_WORKER_VERSION",
    "FRAME_PATTERN",
    "MANIFEST_FILENAME",
    "SEQUENCE_ARTIFACT_PREFIX",
    "SEQUENCE_SCHEMA_VERSION",
    "SEQUENCE_STATUSES",
    "SequenceArtifactStoreError",
    "artifact_paths",
    "build_sequence_artifact_id",
    "build_sequence_manifest",
    "clear_sequence",
    "get_sequence_paths",
    "is_sequence_current",
    "is_sequence_ready",
    "read_sequence_manifest",
    "sequence_frame_path",
    "sequence_is_current",
    "sequence_paths",
    "sequence_status",
    "write_sequence_frame",
    "write_sequence_manifest",
]
