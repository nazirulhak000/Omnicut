"""Safe filesystem cache helpers for ``BackgroundIsolationV1`` artifacts.

This module owns only derived cache files.  It never accepts or writes a
source-media path, and every artifact directory is derived from the validated
``bgiso1-<hex16>`` identity produced by :mod:`scripts.background_isolation`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.background_isolation import ARTIFACT_SCHEMA_VERSION
from scripts.background_isolation import ARTIFACT_STATUSES as CONTRACT_ARTIFACT_STATUSES

CACHE_NAMESPACE = "background-isolation"
MANIFEST_FILENAME = "manifest.json"
FOREGROUND_FILENAME = "foreground.png"
ALPHA_FILENAME = "alpha.png"
MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "status",
        "foreground_path",
        "alpha_path",
    }
)
ARTIFACT_STATUSES = frozenset(CONTRACT_ARTIFACT_STATUSES)
_ARTIFACT_ID_RE = re.compile(r"^bgiso1-[0-9a-f]{16}$")
_ARTIFACT_NAMES = frozenset(("foreground", "alpha"))


class ArtifactStoreError(ValueError):
    """Raised when a caller supplies an unsafe cache identity or manifest."""


@dataclass(frozen=True)
class BackgroundIsolationArtifactPaths:
    """Deterministic paths for one artifact identity under a caller root."""

    directory: Path
    manifest: Path
    foreground: Path
    alpha: Path


def _cache_root(cache_root: os.PathLike[str] | str) -> Path:
    """Resolve a caller-provided root without creating or touching it."""

    if not isinstance(cache_root, (str, os.PathLike)):
        raise ArtifactStoreError("cache root must be a path-like value")
    return Path(cache_root).expanduser().resolve(strict=False)


def _validate_artifact_id(artifact_id: Any) -> str:
    """Accept only the existing BackgroundIsolationV1 identity format."""

    if not isinstance(artifact_id, str) or not _ARTIFACT_ID_RE.fullmatch(artifact_id):
        raise ArtifactStoreError("invalid background isolation artifact id")
    return artifact_id


def _ensure_under_root(path: Path, root: Path) -> Path:
    """Return a resolved path only when it stays below the validated root."""

    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ArtifactStoreError("artifact path escapes cache root") from exc
    return resolved


def artifact_paths(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
) -> BackgroundIsolationArtifactPaths:
    """Derive deterministic manifest, foreground, and alpha paths.

    ``artifact_id`` is validated before it participates in path construction,
    so traversal segments and absolute paths are rejected rather than
    normalised into a potentially surprising location.
    """

    root = _cache_root(cache_root)
    safe_id = _validate_artifact_id(artifact_id)
    namespace = root / CACHE_NAMESPACE
    raw_directory = namespace / safe_id
    if namespace.is_symlink() or raw_directory.is_symlink():
        raise ArtifactStoreError("cache namespace or artifact directory must not be a symlink")
    _ensure_under_root(raw_directory, root)
    directory = raw_directory
    return BackgroundIsolationArtifactPaths(
        directory=directory,
        manifest=directory / MANIFEST_FILENAME,
        foreground=directory / FOREGROUND_FILENAME,
        alpha=directory / ALPHA_FILENAME,
    )


def get_artifact_paths(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
) -> BackgroundIsolationArtifactPaths:
    """Compatibility-friendly alias for :func:`artifact_paths`."""

    return artifact_paths(cache_root, artifact_id)


def build_artifact_manifest(artifact_id: str, *, status: str = "missing") -> dict[str, Any]:
    """Build the canonical manifest without touching the filesystem."""

    safe_id = _validate_artifact_id(artifact_id)
    if not isinstance(status, str) or status not in ARTIFACT_STATUSES:
        raise ArtifactStoreError("invalid background isolation artifact status")
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_id": safe_id,
        "status": status,
        "foreground_path": FOREGROUND_FILENAME,
        "alpha_path": ALPHA_FILENAME,
    }


def _validate_manifest(value: Any, expected_id: str) -> dict[str, Any] | None:
    """Validate a stored manifest; malformed data is never made consumable."""

    if not isinstance(value, Mapping) or set(value) != MANIFEST_KEYS:
        return None
    if value.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        return None
    if value.get("artifact_id") != expected_id:
        return None
    if not isinstance(value.get("status"), str) or value["status"] not in ARTIFACT_STATUSES:
        return None
    if value.get("foreground_path") != FOREGROUND_FILENAME:
        return None
    if value.get("alpha_path") != ALPHA_FILENAME:
        return None
    return build_artifact_manifest(expected_id, status=value["status"])


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Write beside the destination and replace it in one same-directory step."""

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


def write_artifact_bytes(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
    artifact_name: str,
    payload: bytes,
) -> Path:
    """Atomically write foreground or alpha bytes into the derived directory."""

    if not isinstance(artifact_name, str) or artifact_name not in _ARTIFACT_NAMES:
        raise ArtifactStoreError("artifact name must be foreground or alpha")
    if not isinstance(payload, bytes):
        raise ArtifactStoreError("artifact payload must be bytes")
    paths = artifact_paths(cache_root, artifact_id)
    destination = getattr(paths, artifact_name)
    _atomic_write_bytes(destination, payload)
    return destination


def write_artifact_manifest(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
    manifest: Mapping[str, Any] | None = None,
    *,
    status: str | None = None,
) -> dict[str, Any]:
    """Validate and atomically persist a canonical artifact manifest."""

    safe_id = _validate_artifact_id(artifact_id)
    if manifest is None:
        canonical = build_artifact_manifest(safe_id, status="missing" if status is None else status)
    else:
        candidate = dict(manifest)
        if status is not None:
            candidate["status"] = status
        canonical = _validate_manifest(candidate, safe_id)
        if canonical is None:
            raise ArtifactStoreError("invalid background isolation artifact manifest")

    paths = artifact_paths(cache_root, safe_id)
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _atomic_write_bytes(paths.manifest, payload)
    return canonical


def read_artifact_manifest(
    cache_root: os.PathLike[str] | str,
    artifact_id: str,
) -> dict[str, Any] | None:
    """Read a manifest or return ``None`` for missing/malformed data."""

    safe_id = _validate_artifact_id(artifact_id)
    paths = artifact_paths(cache_root, safe_id)
    if paths.manifest.is_symlink():
        return None
    try:
        value = json.loads(paths.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, TypeError, ValueError, json.JSONDecodeError):
        return None
    return _validate_manifest(value, safe_id)


def artifact_status(cache_root: os.PathLike[str] | str, artifact_id: str) -> str:
    """Return a fail-closed cache status, including missing ready payloads."""

    paths = artifact_paths(cache_root, artifact_id)
    if not paths.manifest.exists():
        return "missing"
    manifest = read_artifact_manifest(cache_root, artifact_id)
    if manifest is None:
        return "stale"
    if manifest["status"] == "ready" and not all(
        path.is_file() and not path.is_symlink()
        for path in (paths.foreground, paths.alpha)
    ):
        return "stale"
    return manifest["status"]


def is_artifact_ready(cache_root: os.PathLike[str] | str, artifact_id: str) -> bool:
    """Return true only when the manifest and both derived files are valid."""

    return artifact_status(cache_root, artifact_id) == "ready"


def clear_artifact(cache_root: os.PathLike[str] | str, artifact_id: str) -> bool:
    """Remove only one validated artifact directory below the caller root."""

    root = _cache_root(cache_root)
    paths = artifact_paths(root, artifact_id)
    target = paths.directory
    if not target.exists():
        return False
    if target.is_symlink() or not target.is_dir():
        raise ArtifactStoreError("artifact directory is not a real directory")
    _ensure_under_root(target, root)
    shutil.rmtree(target)
    return True
