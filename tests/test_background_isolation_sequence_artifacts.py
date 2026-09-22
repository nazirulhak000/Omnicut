from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.background_isolation_sequence_artifacts import (
    CACHE_NAMESPACE,
    FRAME_PATTERN,
    ArtifactStoreError,
    SequenceArtifactStoreError,
    build_sequence_artifact_id,
    build_sequence_manifest,
    clear_sequence,
    is_sequence_current,
    is_sequence_ready,
    read_sequence_manifest,
    sequence_frame_path,
    sequence_paths,
    sequence_status,
    write_sequence_frame,
    write_sequence_manifest,
)

SOURCE_FINGERPRINT = "sha256:source-001"
ARTIFACT_ID = build_sequence_artifact_id(SOURCE_FINGERPRINT)


def ready_manifest(**overrides):
    values = {
        "source_fingerprint": SOURCE_FINGERPRINT,
        "frame_count": 3,
        "fps": 30.0,
        "timebase": "1/30",
        "width": 1080,
        "height": 1920,
        "rotation": 0,
        "status": "ready",
    }
    values.update(overrides)
    return build_sequence_manifest(ARTIFACT_ID, **values)


def make_ready_sequence(tmp_path: Path, **overrides):
    manifest = ready_manifest(**overrides)
    write_sequence_manifest(tmp_path, ARTIFACT_ID, {**manifest, "status": "processing"})
    for index in range(manifest["frame_count"]):
        write_sequence_frame(tmp_path, ARTIFACT_ID, index, f"frame-{index}".encode())
    write_sequence_manifest(tmp_path, ARTIFACT_ID, manifest)
    return manifest


def test_paths_are_deterministic_and_use_a_separate_namespace(tmp_path):
    first = sequence_paths(tmp_path, ARTIFACT_ID)
    second = sequence_paths(tmp_path, ARTIFACT_ID)

    assert first == second
    assert first.directory == tmp_path / CACHE_NAMESPACE / ARTIFACT_ID
    assert first.manifest.name == "manifest.json"
    assert first.frames == first.directory / "frames"
    assert first.directory.is_relative_to(tmp_path.resolve())


@pytest.mark.parametrize(
    "unsafe_id",
    [
        "../outside",
        "bgseq1-0123456789abcdef/../../outside",
        "/absolute/path",
        "C:\\outside\\artifact",
        "bgiso1-0123456789abcdef",
        "bgseq1-0123456789abcde/",
    ],
)
def test_path_traversal_and_foreign_ids_are_rejected(tmp_path, unsafe_id):
    with pytest.raises(SequenceArtifactStoreError):
        sequence_paths(tmp_path, unsafe_id)
    with pytest.raises(ArtifactStoreError):
        sequence_frame_path(tmp_path, unsafe_id, 0)


def test_sequence_id_is_deterministic_and_excludes_clip_index():
    first = build_sequence_artifact_id(SOURCE_FINGERPRINT)
    second = build_sequence_artifact_id(SOURCE_FINGERPRINT)

    assert first == second
    assert first.startswith("bgseq1-")
    assert first != build_sequence_artifact_id("sha256:source-002")


def test_sequence_id_and_manifest_capture_the_source_window():
    first = build_sequence_artifact_id(
        SOURCE_FINGERPRINT,
        source_start=1.0,
        source_duration=2.0,
    )
    second = build_sequence_artifact_id(
        SOURCE_FINGERPRINT,
        source_start=8.0,
        source_duration=2.0,
    )
    manifest = build_sequence_manifest(
        first,
        source_fingerprint=SOURCE_FINGERPRINT,
        source_start=1.0,
        source_duration=2.0,
    )

    assert first != second
    assert manifest["source_start"] == 1.0
    assert manifest["source_duration"] == 2.0


def test_manifest_round_trips_atomically_with_complete_metadata(tmp_path, monkeypatch):
    replacements: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def capture_replace(source, destination):
        replacements.append((Path(source), Path(destination)))
        return real_replace(source, destination)

    monkeypatch.setattr(os, "replace", capture_replace)
    manifest = ready_manifest(status="processing")
    written = write_sequence_manifest(tmp_path, ARTIFACT_ID, manifest)
    paths = sequence_paths(tmp_path, ARTIFACT_ID)

    assert written == manifest
    assert set(written) == {
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
        "source_start",
        "source_duration",
    }
    assert replacements[-1][0].parent == replacements[-1][1].parent
    assert replacements[-1][1] == paths.manifest
    assert read_sequence_manifest(tmp_path, ARTIFACT_ID) == manifest
    assert not list(paths.directory.glob("*.tmp"))


def test_ready_requires_every_zero_based_frame(tmp_path):
    manifest = ready_manifest()
    processing = {**manifest, "status": "processing"}
    write_sequence_manifest(tmp_path, ARTIFACT_ID, processing)

    write_sequence_frame(tmp_path, ARTIFACT_ID, 0, b"zero")
    write_sequence_frame(tmp_path, ARTIFACT_ID, 1, b"one")
    assert sequence_status(tmp_path, ARTIFACT_ID) == "processing"
    assert not is_sequence_ready(tmp_path, ARTIFACT_ID)
    with pytest.raises(SequenceArtifactStoreError):
        write_sequence_manifest(tmp_path, ARTIFACT_ID, manifest)

    write_sequence_frame(tmp_path, ARTIFACT_ID, 2, b"two")
    write_sequence_manifest(tmp_path, ARTIFACT_ID, manifest)
    assert sequence_status(tmp_path, ARTIFACT_ID) == "ready"
    assert is_sequence_ready(tmp_path, ARTIFACT_ID)


@pytest.mark.parametrize("status", ["processing", "stale", "error", "cancelled"])
def test_cancelled_or_error_states_can_never_be_ready(tmp_path, status):
    manifest = ready_manifest(status=status)
    write_sequence_manifest(tmp_path, ARTIFACT_ID, manifest)
    for index in range(manifest["frame_count"]):
        write_sequence_frame(tmp_path, ARTIFACT_ID, index, b"frame")

    assert sequence_status(tmp_path, ARTIFACT_ID) == status
    assert not is_sequence_ready(tmp_path, ARTIFACT_ID)
    assert not is_sequence_current(tmp_path, ARTIFACT_ID)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        {"schema_version": 999},
        {**ready_manifest(), "artifact_id": "bgseq1-fedcba9876543210"},
        {**ready_manifest(), "status": "unknown"},
        {**ready_manifest(), "frame_pattern": "../outside/frame_%06d.png"},
        {**ready_manifest(), "timebase": "0/30"},
        {**ready_manifest(), "frame_count": -1},
        {**ready_manifest(), "fps": "30"},
    ],
)
def test_malformed_manifest_is_fail_closed(tmp_path, payload):
    paths = sequence_paths(tmp_path, ARTIFACT_ID)
    paths.directory.mkdir(parents=True)
    if isinstance(payload, str):
        paths.manifest.write_text(payload, encoding="utf-8")
    else:
        paths.manifest.write_text(json.dumps(payload), encoding="utf-8")

    assert read_sequence_manifest(tmp_path, ARTIFACT_ID) is None
    assert sequence_status(tmp_path, ARTIFACT_ID) == "stale"
    assert not is_sequence_ready(tmp_path, ARTIFACT_ID)


def test_current_detection_checks_source_and_processing_signature(tmp_path):
    manifest = make_ready_sequence(tmp_path)
    assert is_sequence_current(tmp_path, ARTIFACT_ID)
    assert is_sequence_current(
        tmp_path,
        ARTIFACT_ID,
        {
            "source_fingerprint": SOURCE_FINGERPRINT,
            "model": manifest["model"],
            "fps": 30,
            "timebase": (1, 30),
        },
    )
    assert not is_sequence_current(tmp_path, ARTIFACT_ID, {"source_fingerprint": "changed"})
    assert not is_sequence_current(tmp_path, ARTIFACT_ID, {"quality": "draft"})
    assert not is_sequence_current(tmp_path, ARTIFACT_ID, {"unknown": "value"})


def test_symlink_namespace_artifact_frame_and_manifest_are_rejected_or_stale(tmp_path):
    namespace = tmp_path / CACHE_NAMESPACE
    namespace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (namespace / ARTIFACT_ID).symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is unavailable")
        raise
    with pytest.raises(SequenceArtifactStoreError):
        sequence_paths(tmp_path, ARTIFACT_ID)

    (namespace / ARTIFACT_ID).unlink()
    paths = sequence_paths(tmp_path, ARTIFACT_ID)
    paths.frames.mkdir(parents=True)
    write_sequence_frame(tmp_path, ARTIFACT_ID, 0, b"real")
    write_sequence_manifest(tmp_path, ARTIFACT_ID, ready_manifest(frame_count=1))
    (paths.frames / "frame_000000.png").unlink()
    (paths.frames / "frame_000000.png").symlink_to(outside / "not-here.png")
    assert sequence_status(tmp_path, ARTIFACT_ID) == "stale"
    with pytest.raises(SequenceArtifactStoreError):
        write_sequence_frame(tmp_path, ARTIFACT_ID, 0, b"nope")

    paths.manifest.unlink(missing_ok=True)
    (paths.manifest).symlink_to(outside / "manifest.json")
    assert read_sequence_manifest(tmp_path, ARTIFACT_ID) is None


def test_invalid_builder_values_are_rejected_and_missing_metadata_is_not_implicit_ready():
    with pytest.raises(SequenceArtifactStoreError):
        build_sequence_manifest(ARTIFACT_ID, source_fingerprint="", frame_count=1)
    with pytest.raises(SequenceArtifactStoreError):
        build_sequence_manifest(ARTIFACT_ID, source_fingerprint=SOURCE_FINGERPRINT, rotation=45)
    with pytest.raises(SequenceArtifactStoreError):
        build_sequence_manifest(ARTIFACT_ID, source_fingerprint=SOURCE_FINGERPRINT, frame_pattern="frames/../x")


def test_clear_removes_only_one_sequence_cache(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"keep")
    write_sequence_manifest(tmp_path, ARTIFACT_ID, ready_manifest(status="cancelled"))
    assert clear_sequence(tmp_path, ARTIFACT_ID) is True
    assert not sequence_paths(tmp_path, ARTIFACT_ID).directory.exists()
    assert outside.read_bytes() == b"keep"
    assert clear_sequence(tmp_path, ARTIFACT_ID) is False


def test_frame_index_and_payload_are_strictly_validated(tmp_path):
    with pytest.raises(SequenceArtifactStoreError):
        sequence_frame_path(tmp_path, ARTIFACT_ID, -1)
    with pytest.raises(SequenceArtifactStoreError):
        sequence_frame_path(tmp_path, ARTIFACT_ID, 1_000_000)
    with pytest.raises(SequenceArtifactStoreError):
        write_sequence_frame(tmp_path, ARTIFACT_ID, 0, "not-bytes")


def test_frame_pattern_is_canonical():
    assert FRAME_PATTERN == "frames/frame_%06d.png"
