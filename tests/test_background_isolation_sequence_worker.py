from __future__ import annotations

import io
import json
import threading
from pathlib import Path

from PIL import Image

from scripts.background_isolation import SCHEMA_VERSION
from scripts.background_isolation_sequence_artifacts import (
    FRAME_PATTERN,
    build_sequence_artifact_id,
    build_sequence_manifest,
)
from scripts.background_isolation_sequence_worker import (
    DERIVED_CACHE_NAMESPACE,
    ERROR_CANCELLED,
    ERROR_CONFIG_DISABLED,
    ERROR_INPUT_INCOMPLETE,
    ERROR_OUTPUT_COMMIT,
    ERROR_OUTPUT_INVALID,
    ERROR_WORKER_FAILURE,
    STATUS_CANCELLED,
    STATUS_ERROR,
    STATUS_NOOP,
    STATUS_READY,
    WORKER_VERSION,
    BackgroundIsolationSequenceWorker,
    process_background_isolation_sequence,
)
from scripts.background_isolation_worker import BackgroundIsolationWorker


def enabled_config(**overrides):
    value = {
        "schema_version": SCHEMA_VERSION,
        "enabled": True,
        "mode": "cutout",
        "engine": "rembg",
        "model": "u2netp",
        "quality": "balanced",
        "fallback": "spotlight",
    }
    value.update(overrides)
    return value


def png_bytes(mode: str = "RGBA", size: tuple[int, int] = (4, 3), color=None) -> bytes:
    if color is None:
        color = (10, 20, 30, 127) if mode == "RGBA" else (10, 20, 30)
    output = io.BytesIO()
    Image.new(mode, size, color).save(output, format="PNG")
    return output.getvalue()


def plausible_foreground_bytes(size: tuple[int, int] = (4, 3)) -> bytes:
    image = Image.new("RGBA", size, (10, 20, 30, 0))
    for x in range(max(1, size[0] // 2)):
        for y in range(size[1]):
            image.putpixel((x, y), (90, 100, 110, 127))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def make_source_sequence(tmp_path: Path, frame_count: int = 3, *, fingerprint: str = "sha256:source-sequence"):
    source = tmp_path / "source-sequence"
    frames = source / "frames"
    frames.mkdir(parents=True)
    artifact_id = build_sequence_artifact_id(fingerprint, fps=30, timebase="1/30", width=4, height=3)
    manifest = build_sequence_manifest(
        artifact_id,
        source_fingerprint=fingerprint,
        frame_count=frame_count,
        fps=30.0,
        timebase="1/30",
        width=4,
        height=3,
        rotation=0,
        frame_pattern=FRAME_PATTERN,
        status="ready",
    )
    for index in range(frame_count):
        (frames / f"frame_{index:06d}.png").write_bytes(png_bytes("RGB", (4, 3), (index, 20, 30)))
    (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return source, manifest


class FakeForegroundWorker:
    def __init__(self, *, fail_on: int | None = None, cancel_event=None, invalid=False, alpha: int = 80):
        self.calls: list[tuple[Path, Path]] = []
        self.fail_on = fail_on
        self.cancel_event = cancel_event
        self.invalid = invalid
        self.alpha = alpha

    def process(self, source: Path, target: Path, config):
        index = len(self.calls)
        self.calls.append((Path(source), Path(target)))
        if self.cancel_event is not None and index == 0:
            self.cancel_event.set()
        if self.fail_on == index:
            return {"ok": False, "status": "error", "error_code": "fake_runtime_missing", "message": "fake runtime unavailable"}
        if self.invalid:
            target.write_bytes(png_bytes("RGB"))
        else:
            target.write_bytes(png_bytes("RGBA", (4, 3), (100 + index, 120, 140, self.alpha)))
        return {"ok": True, "status": STATUS_READY, "output_path": str(target)}


class FakeRembg:
    def __init__(self):
        self.sessions = 0
        self.removes = 0

    def new_session(self, **kwargs):
        assert kwargs == {"model_name": "u2netp"}
        self.sessions += 1
        return object()

    def remove(self, source, *, session):
        assert source
        assert session is not None
        self.removes += 1
        return plausible_foreground_bytes()


def test_success_writes_all_frames_as_rgba_and_reports_progress(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 3)
    fake = FakeForegroundWorker()
    progress = []

    result = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=fake,
        progress_callback=progress.append,
    )

    assert result["status"] == STATUS_READY
    assert result["source_sequence_artifact_id"] == manifest["artifact_id"]
    assert result["cache_hit"] is False
    output_frames = sorted(Path(result["frames_directory"]).glob("frame_*.png"))
    assert len(output_frames) == 3
    for frame in output_frames:
        with Image.open(frame) as image:
            assert image.mode == "RGBA"
            assert image.size == (4, 3)
    assert progress[0]["progress"] == 0.0
    assert progress[-1]["progress"] == 1.0
    assert all(source_frame.parent == source / "frames" for source_frame, _ in fake.calls)
    assert not list((tmp_path / "derived" / DERIVED_CACHE_NAMESPACE).glob(".*"))


def test_sequence_worker_reuses_one_image_worker_session_and_cache_hit_skips_calls(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 2)
    first_fake = FakeForegroundWorker()
    sequence_worker = BackgroundIsolationSequenceWorker(worker=first_fake)

    first = sequence_worker.process(source, tmp_path / "derived", enabled_config(), manifest)
    second = sequence_worker.process(source, tmp_path / "derived", enabled_config(), manifest)

    assert first["status"] == STATUS_READY
    assert second["status"] == STATUS_READY
    assert second["cache_hit"] is True
    assert len(first_fake.calls) == 2


def test_real_image_worker_adapter_reuses_fake_rembg_session_across_frames_and_cache_hit(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 2)
    runtime = FakeRembg()
    sequence_worker = BackgroundIsolationSequenceWorker(
        worker=BackgroundIsolationWorker(loader=lambda: runtime)
    )

    first = sequence_worker.process(source, tmp_path / "derived", enabled_config(), manifest)

    def fail_loader():
        raise AssertionError("cache hit must not load rembg")

    second = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=BackgroundIsolationWorker(loader=fail_loader),
    )

    assert first["status"] == STATUS_READY
    assert second["status"] == STATUS_READY
    assert second["cache_hit"] is True
    assert runtime.sessions == 1
    assert runtime.removes == 2


def test_missing_runtime_never_publishes_ready_or_leaves_partial_frames(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 2)

    def missing_runtime():
        raise ModuleNotFoundError("No module named 'onnxruntime'", name="onnxruntime")

    result = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=BackgroundIsolationWorker(loader=missing_runtime),
    )

    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == "onnxruntime_missing"
    assert len(list((tmp_path / "derived" / DERIVED_CACHE_NAMESPACE).glob(".*.checkpoint"))) == 1
    assert not list((tmp_path / "derived" / DERIVED_CACHE_NAMESPACE).glob("bgseq1-*/manifest.json"))


def test_retry_resumes_from_valid_checkpoint_frames(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 3)
    first = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=FakeForegroundWorker(fail_on=1),
    )
    assert first["status"] == STATUS_ERROR

    retry_worker = FakeForegroundWorker()
    retry = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=retry_worker,
    )

    assert retry["status"] == STATUS_READY
    assert len(retry_worker.calls) == 2
    assert [call[0].name for call in retry_worker.calls] == ["frame_000001.png", "frame_000002.png"]


def test_cancel_cleans_partial_derived_output_and_never_publishes_ready(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 3)
    cancel_event = threading.Event()
    fake = FakeForegroundWorker(cancel_event=cancel_event)

    result = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=fake,
        cancel_event=cancel_event,
    )

    assert result["status"] == STATUS_CANCELLED
    assert result["error_code"] == ERROR_CANCELLED
    namespace = tmp_path / "derived" / DERIVED_CACHE_NAMESPACE
    assert len(list(namespace.glob(".*.checkpoint"))) == 1
    assert not list(namespace.glob("bgseq1-*/manifest.json"))


def test_worker_failure_cleans_partial_frames_and_keeps_source_untouched(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 3)
    before = [(path.name, path.read_bytes()) for path in sorted((source / "frames").iterdir())]
    result = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=FakeForegroundWorker(fail_on=1),
    )

    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == "fake_runtime_missing"
    namespace = tmp_path / "derived" / DERIVED_CACHE_NAMESPACE
    assert len(list(namespace.glob(".*.checkpoint"))) == 1
    assert not list(namespace.glob("bgseq1-*/manifest.json"))
    assert before == [(path.name, path.read_bytes()) for path in sorted((source / "frames").iterdir())]


def test_disabled_config_is_noop_without_loading_or_creating_output(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 2)
    loader_called = False

    def loader():
        nonlocal loader_called
        loader_called = True
        raise AssertionError("disabled config must not load rembg")

    result = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        {"enabled": False},
        manifest,
        loader=loader,
    )

    assert result["status"] == STATUS_NOOP
    assert result["error_code"] == ERROR_CONFIG_DISABLED
    assert loader_called is False
    assert not (tmp_path / "derived").exists()


def test_incomplete_input_is_rejected_before_worker_and_output(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 3)
    (source / "frames" / "frame_000001.png").unlink()
    fake = FakeForegroundWorker()

    result = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=fake,
    )

    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == ERROR_INPUT_INCOMPLETE
    assert fake.calls == []
    assert not (tmp_path / "derived").exists()


def test_invalid_foreground_mode_is_not_ready_and_is_cleaned(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 1)
    result = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=FakeForegroundWorker(invalid=True),
    )

    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == ERROR_OUTPUT_INVALID
    assert len(list((tmp_path / "derived" / DERIVED_CACHE_NAMESPACE).glob(".*.checkpoint"))) == 1


def test_existing_incomplete_artifact_is_never_replaced_during_recovery(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 1)
    artifact_id = build_sequence_artifact_id(
        f"{manifest['source_fingerprint']}|sequence:{manifest['artifact_id']}",
        algorithm="background-isolation-v1",
        engine="rembg",
        model="u2netp",
        quality="balanced",
        worker_version=WORKER_VERSION,
        fps=manifest["fps"],
        timebase=manifest["timebase"],
        width=manifest["width"],
        height=manifest["height"],
        rotation=manifest["rotation"],
    )
    target = tmp_path / "derived" / DERIVED_CACHE_NAMESPACE / artifact_id
    frames = target / "frames"
    frames.mkdir(parents=True)
    expected_manifest = build_sequence_manifest(
            artifact_id,
            source_fingerprint=manifest["source_fingerprint"],
            algorithm="background-isolation-v1",
            engine="rembg",
            model="u2netp",
            quality="balanced",
            worker_version=WORKER_VERSION,
            frame_count=manifest["frame_count"],
            fps=manifest["fps"],
            timebase=manifest["timebase"],
            width=manifest["width"],
            height=manifest["height"],
            rotation=manifest["rotation"],
            frame_pattern=FRAME_PATTERN,
            status="ready",
        )
    manifest_path = target / "manifest.json"
    manifest_path.write_text(json.dumps(expected_manifest), encoding="utf-8")
    frame_path = frames / "frame_000000.png"
    frame_path.write_bytes(png_bytes("RGB"))
    before_manifest = manifest_path.read_bytes()
    before_frame = frame_path.read_bytes()

    result = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=FakeForegroundWorker(),
    )

    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == ERROR_OUTPUT_COMMIT
    assert manifest_path.read_bytes() == before_manifest
    assert frame_path.read_bytes() == before_frame
    assert len(list((tmp_path / "derived" / DERIVED_CACHE_NAMESPACE).glob(".*.checkpoint"))) == 1


def test_quality_rerun_uses_new_worker_version_and_preserves_previous_artifact(tmp_path):
    source, manifest = make_source_sequence(tmp_path, 1)
    first = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        # The sequence worker's technical check accepts this, but a human
        # quality review would reject a fully opaque cutout as low quality.
        worker=FakeForegroundWorker(alpha=255),
    )
    previous = Path(first["output_directory"])
    before_manifest = (previous / "manifest.json").read_bytes()
    before_frame = (previous / "frames" / "frame_000000.png").read_bytes()

    rerun = process_background_isolation_sequence(
        source,
        tmp_path / "derived",
        enabled_config(),
        manifest,
        worker=FakeForegroundWorker(),
        worker_version="sequence-rembg-worker-quality-rerun-v2",
    )

    assert rerun["status"] == STATUS_READY
    assert rerun["cache_hit"] is False
    assert rerun["artifact_id"] != first["artifact_id"]
    assert previous.is_dir()
    assert (previous / "manifest.json").read_bytes() == before_manifest
    assert (previous / "frames" / "frame_000000.png").read_bytes() == before_frame
    rerun_manifest = json.loads((Path(rerun["output_directory"]) / "manifest.json").read_text(encoding="utf-8"))
    assert rerun_manifest["worker_version"] == "sequence-rembg-worker-quality-rerun-v2"
