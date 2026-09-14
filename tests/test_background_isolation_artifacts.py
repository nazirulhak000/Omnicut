from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.background_isolation import build_artifact_id
from scripts.background_isolation_artifacts import (
    ArtifactStoreError,
    artifact_paths,
    artifact_status,
    build_artifact_manifest,
    clear_artifact,
    is_artifact_ready,
    read_artifact_manifest,
    write_artifact_bytes,
    write_artifact_manifest,
)

ARTIFACT_ID = "bgiso1-0123456789abcdef"


def test_paths_are_deterministic_and_stay_under_caller_root(tmp_path):
    first = artifact_paths(tmp_path, ARTIFACT_ID)
    second = artifact_paths(tmp_path, ARTIFACT_ID)

    assert first == second
    assert first.directory == tmp_path / "background-isolation" / ARTIFACT_ID
    assert first.manifest.name == "manifest.json"
    assert first.foreground.name == "foreground.png"
    assert first.alpha.name == "alpha.png"
    assert first.directory.is_relative_to(tmp_path.resolve())


@pytest.mark.parametrize(
    "unsafe_id",
    [
        "../outside",
        "bgiso1-0123456789abcdef/../../outside",
        "/absolute/path",
        "C:\\outside\\artifact",
        "bgiso1-0123456789abcde/",
    ],
)
def test_path_traversal_and_absolute_ids_are_rejected(tmp_path, unsafe_id):
    with pytest.raises(ArtifactStoreError):
        artifact_paths(tmp_path, unsafe_id)
    with pytest.raises(ArtifactStoreError):
        clear_artifact(tmp_path, unsafe_id)


def test_manifest_write_is_atomic_same_directory_and_deterministic(tmp_path, monkeypatch):
    replacements: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def capture_replace(source, destination):
        replacements.append((Path(source), Path(destination)))
        return real_replace(source, destination)

    monkeypatch.setattr(os, "replace", capture_replace)
    written = write_artifact_manifest(tmp_path, ARTIFACT_ID, status="processing")
    paths = artifact_paths(tmp_path, ARTIFACT_ID)

    assert written == build_artifact_manifest(ARTIFACT_ID, status="processing")
    assert replacements and replacements[-1][0].parent == replacements[-1][1].parent
    assert replacements[-1][1] == paths.manifest
    assert not list(paths.directory.glob("*.tmp"))
    assert read_artifact_manifest(tmp_path, ARTIFACT_ID) == written


def test_foreground_and_alpha_bytes_use_atomic_replacement_without_touching_source(tmp_path, monkeypatch):
    source = tmp_path / "source-original.mov"
    source.write_bytes(b"original")
    replacements: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def capture_replace(source_path, destination):
        replacements.append((Path(source_path), Path(destination)))
        return real_replace(source_path, destination)

    monkeypatch.setattr(os, "replace", capture_replace)
    foreground = write_artifact_bytes(tmp_path, ARTIFACT_ID, "foreground", b"foreground")
    alpha = write_artifact_bytes(tmp_path, ARTIFACT_ID, "alpha", b"alpha")
    paths = artifact_paths(tmp_path, ARTIFACT_ID)

    assert foreground == paths.foreground
    assert alpha == paths.alpha
    assert foreground.read_bytes() == b"foreground"
    assert alpha.read_bytes() == b"alpha"
    assert source.read_bytes() == b"original"
    assert all(source_path.parent == destination.parent for source_path, destination in replacements)
    assert not list(paths.directory.glob("*.tmp"))


def test_status_reports_missing_ready_and_stale_fail_closed(tmp_path):
    assert artifact_status(tmp_path, ARTIFACT_ID) == "missing"
    write_artifact_manifest(tmp_path, ARTIFACT_ID, status="ready")
    assert artifact_status(tmp_path, ARTIFACT_ID) == "stale"
    assert not is_artifact_ready(tmp_path, ARTIFACT_ID)

    write_artifact_bytes(tmp_path, ARTIFACT_ID, "foreground", b"foreground")
    write_artifact_bytes(tmp_path, ARTIFACT_ID, "alpha", b"alpha")
    assert artifact_status(tmp_path, ARTIFACT_ID) == "ready"
    assert is_artifact_ready(tmp_path, ARTIFACT_ID)

    write_artifact_manifest(tmp_path, ARTIFACT_ID, status="stale")
    assert artifact_status(tmp_path, ARTIFACT_ID) == "stale"
    assert not is_artifact_ready(tmp_path, ARTIFACT_ID)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        {"schema_version": 999},
        {
            "schema_version": 1,
            "artifact_id": "bgiso1-fedcba9876543210",
            "status": "ready",
            "foreground_path": "foreground.png",
            "alpha_path": "alpha.png",
        },
        {
            "schema_version": 1,
            "artifact_id": ARTIFACT_ID,
            "status": "unknown",
            "foreground_path": "foreground.png",
            "alpha_path": "alpha.png",
        },
        {
            "schema_version": 1,
            "artifact_id": ARTIFACT_ID,
            "status": "ready",
            "foreground_path": "../outside.png",
            "alpha_path": "alpha.png",
        },
    ],
)
def test_manifest_schema_id_and_status_are_fail_closed(tmp_path, payload):
    paths = artifact_paths(tmp_path, ARTIFACT_ID)
    paths.directory.mkdir(parents=True)
    if isinstance(payload, str):
        paths.manifest.write_text(payload, encoding="utf-8")
    else:
        paths.manifest.write_text(json.dumps(payload), encoding="utf-8")

    assert read_artifact_manifest(tmp_path, ARTIFACT_ID) is None
    assert artifact_status(tmp_path, ARTIFACT_ID) == "stale"


def test_clear_removes_only_the_validated_artifact_directory(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"keep")
    write_artifact_manifest(tmp_path, ARTIFACT_ID, status="missing")
    write_artifact_bytes(tmp_path, ARTIFACT_ID, "alpha", b"alpha")

    assert clear_artifact(tmp_path, ARTIFACT_ID) is True
    assert not artifact_paths(tmp_path, ARTIFACT_ID).directory.exists()
    assert outside.read_bytes() == b"keep"
    assert clear_artifact(tmp_path, ARTIFACT_ID) is False


def test_existing_source_file_is_never_a_cache_target(tmp_path):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"do-not-touch")

    write_artifact_manifest(tmp_path, ARTIFACT_ID, status="missing")

    assert source.read_bytes() == b"do-not-touch"
    assert source.is_file()


def test_artifact_id_can_be_derived_from_background_isolation_contract(tmp_path):
    config = {
        "enabled": True,
        "mode": "cutout",
        "engine": "rembg",
        "model": "u2netp",
        "quality": "balanced",
    }
    artifact_id = build_artifact_id("clip:size=100:mtime=1", config)

    assert artifact_id is not None
    paths = artifact_paths(tmp_path, artifact_id)
    assert paths.directory.parent == tmp_path.resolve() / "background-isolation"
