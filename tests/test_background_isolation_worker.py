from __future__ import annotations

import builtins
import io
import sys
import types
from pathlib import Path

from PIL import Image

from scripts.background_isolation import (
    SCHEMA_VERSION,
    build_artifact_id,
    with_artifact_id,
)
from scripts.background_isolation_artifacts import (
    artifact_paths,
    artifact_status,
    write_artifact_bytes,
    write_artifact_manifest,
)
from scripts.background_isolation_worker import (
    ERROR_CONFIG_DISABLED,
    ERROR_CONFIG_INVALID,
    ERROR_CONFIG_MISSING,
    ERROR_INPUT_NOT_FOUND,
    ERROR_ONNXRUNTIME_MISSING,
    ERROR_OUTPUT_EQUALS_INPUT,
    ERROR_REMBG_OUTPUT,
    ERROR_REMBG_QUALITY,
    ERROR_SOURCE_FINGERPRINT_INVALID,
    ERROR_SOURCE_FINGERPRINT_MISSING,
    STATUS_ERROR,
    STATUS_NOOP,
    STATUS_READY,
    BackgroundIsolationWorker,
    process_background_isolation,
    process_background_isolation_bundle,
)


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


def write_source(path: Path, size: tuple[int, int] = (4, 3)) -> None:
    Image.new("RGB", size, (20, 40, 60)).save(path, format="PNG")


def png_bytes_with_alpha() -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGBA", (4, 3), (10, 20, 30, 0))
    for x in range(3):
        for y in range(3):
            image.putpixel((x, y), (10, 20, 30, 127))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def png_bytes_with_solid_alpha(alpha: int, size: tuple[int, int] = (4, 3)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, (10, 20, 30, alpha)).save(buffer, format="PNG")
    return buffer.getvalue()


def png_bytes_with_sparse_alpha(size: tuple[int, int] = (100, 100)) -> bytes:
    image = Image.new("RGBA", size, (10, 20, 30, 0))
    image.putpixel((size[0] // 2, size[1] // 2), (10, 20, 30, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def alpha_png_bytes(size: tuple[int, int] = (4, 3), value: int = 127) -> bytes:
    buffer = io.BytesIO()
    Image.new("L", size, value).save(buffer, format="PNG")
    return buffer.getvalue()


def fake_rembg(monkeypatch, *, output=None, new_session=None):
    calls = {"remove": 0, "new_session": 0}

    def remove(source, **kwargs):
        calls["remove"] += 1
        assert source
        return output if output is not None else png_bytes_with_alpha()

    def make_session(**kwargs):
        calls["new_session"] += 1
        assert kwargs == {"model_name": "u2netp"}
        return "fake-session"

    module = types.SimpleNamespace(
        remove=remove,
        new_session=new_session or make_session,
    )
    monkeypatch.setitem(sys.modules, "rembg", module)
    return calls


def test_module_import_does_not_import_rembg(monkeypatch):
    import importlib

    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "rembg":
            raise AssertionError("rembg must be lazy-loaded")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "scripts.background_isolation_worker", raising=False)
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    importlib.import_module("scripts.background_isolation_worker")


def test_missing_disabled_and_invalid_config_are_noops_without_output(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    write_source(source)
    output = tmp_path / "foreground.png"
    loader_called = False

    def loader():
        nonlocal loader_called
        loader_called = True
        raise AssertionError("disabled config must not load rembg")

    worker = BackgroundIsolationWorker(loader=loader)
    results = [
        worker.process(source, output, None),
        worker.process(source, output, {"enabled": False}),
        worker.process(source, output, {"enabled": True, "model": "unknown"}),
    ]

    assert [item["status"] for item in results] == [STATUS_NOOP] * 3
    assert results[0]["error_code"] == ERROR_CONFIG_MISSING
    assert results[1]["error_code"] == ERROR_CONFIG_DISABLED
    assert results[2]["error_code"] == ERROR_CONFIG_INVALID
    assert not output.exists()
    assert loader_called is False


def test_enabled_request_writes_rgba_png_atomically_and_reuses_session(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    output = tmp_path / "foreground.png"
    write_source(source)
    calls = fake_rembg(monkeypatch)
    worker = BackgroundIsolationWorker()

    first = worker.process(source, output, enabled_config())
    second = worker.process(source, output, enabled_config())

    assert first["ok"] is True
    assert first["status"] == STATUS_READY
    assert first["output_path"] == str(output)
    assert second["status"] == STATUS_READY
    assert calls == {"remove": 2, "new_session": 1}
    with Image.open(output) as result:
        assert result.format == "PNG"
        assert result.mode == "RGBA"
        assert result.getpixel((0, 0))[3] == 127
    assert not list(tmp_path.glob("*.tmp.png"))


def test_success_uses_temp_path_then_atomic_replace(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    output = tmp_path / "foreground.png"
    write_source(source)
    fake_rembg(monkeypatch)
    import scripts.background_isolation_worker as worker_module

    real_replace = worker_module.os.replace
    replace_calls = []

    def replace_spy(temp_path, target_path):
        replace_calls.append((Path(temp_path), Path(target_path)))
        real_replace(temp_path, target_path)

    monkeypatch.setattr(worker_module.os, "replace", replace_spy)
    result = BackgroundIsolationWorker().process(source, output, enabled_config())

    assert result["status"] == STATUS_READY
    assert len(replace_calls) == 1
    temporary_path, target_path = replace_calls[0]
    assert temporary_path != target_path
    assert target_path == output
    assert output.is_file()


def test_worker_never_overwrites_input_even_when_output_is_same_file(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    write_source(source)
    calls = fake_rembg(monkeypatch)

    result = process_background_isolation(source, source, enabled_config())

    assert result["ok"] is False
    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == ERROR_OUTPUT_EQUALS_INPUT
    assert calls == {"remove": 0, "new_session": 0}
    with Image.open(source) as unchanged:
        assert unchanged.getpixel((0, 0)) == (20, 40, 60)


def test_missing_input_returns_structured_failure_without_loading_runtime(tmp_path):
    loader_called = False

    def loader():
        nonlocal loader_called
        loader_called = True
        raise AssertionError("missing input must fail before loading rembg")

    result = BackgroundIsolationWorker(loader=loader).process(
        tmp_path / "missing.png",
        tmp_path / "foreground.png",
        enabled_config(),
    )

    assert result["ok"] is False
    assert result["error_code"] == ERROR_INPUT_NOT_FOUND
    assert loader_called is False


def test_onnxruntime_failure_is_actionable_and_does_not_create_output(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "foreground.png"
    write_source(source)

    def loader():
        raise ModuleNotFoundError("No module named 'onnxruntime'", name="onnxruntime")

    result = BackgroundIsolationWorker(loader=loader).process(source, output, enabled_config())

    assert result["ok"] is False
    assert result["status"] == STATUS_ERROR
    assert result["error_code"] == ERROR_ONNXRUNTIME_MISSING
    assert "ONNX Runtime" in result["message"]
    assert not output.exists()


def test_invalid_rembg_output_keeps_existing_output_untouched(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    output = tmp_path / "foreground.png"
    write_source(source)
    output.write_bytes(b"previous-good-output")
    fake_rembg(monkeypatch, output=b"not-an-image")

    result = BackgroundIsolationWorker().process(source, output, enabled_config())

    assert result["ok"] is False
    assert result["error_code"] == ERROR_REMBG_OUTPUT
    assert output.read_bytes() == b"previous-good-output"
    assert not list(tmp_path.glob("*.tmp.png"))


def test_quality_gate_rejects_effectively_empty_mask_and_preserves_output(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    output = tmp_path / "foreground.png"
    write_source(source)
    output.write_bytes(b"previous-good-output")
    fake_rembg(monkeypatch, output=png_bytes_with_solid_alpha(0))

    result = BackgroundIsolationWorker().process(source, output, enabled_config())

    assert result["ok"] is False
    assert result["error_code"] == ERROR_REMBG_QUALITY
    assert "transparent" in result["message"]
    assert output.read_bytes() == b"previous-good-output"
    assert not list(tmp_path.glob("*.tmp.png"))


def test_quality_gate_rejects_full_frame_and_sparse_subject_masks(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    write_source(source, size=(100, 100))

    output = tmp_path / "opaque.png"
    fake_rembg(monkeypatch, output=png_bytes_with_solid_alpha(255, size=(100, 100)))
    opaque_result = BackgroundIsolationWorker().process(source, output, enabled_config())

    assert opaque_result["error_code"] == ERROR_REMBG_QUALITY
    assert "frame" in opaque_result["message"]
    assert not output.exists()

    sparse_output = tmp_path / "sparse.png"
    fake_rembg(monkeypatch, output=png_bytes_with_sparse_alpha())
    sparse_result = BackgroundIsolationWorker().process(source, sparse_output, enabled_config())

    assert sparse_result["error_code"] == ERROR_REMBG_QUALITY
    assert "small" in sparse_result["message"]
    assert not sparse_output.exists()


def test_quality_gate_rejects_output_size_mismatch_before_commit(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    output = tmp_path / "foreground.png"
    write_source(source, size=(100, 100))
    fake_rembg(monkeypatch, output=png_bytes_with_alpha())

    result = BackgroundIsolationWorker().process(source, output, enabled_config())

    assert result["ok"] is False
    assert result["error_code"] == ERROR_REMBG_QUALITY
    assert "dimensions" in result["message"]
    assert not output.exists()


def test_invalid_paths_are_structured_and_do_not_touch_real_project_folders(tmp_path):
    output = tmp_path / "foreground.png"
    result = BackgroundIsolationWorker(loader=lambda: None).process(None, output, enabled_config())

    assert result["ok"] is False
    assert result["error_code"] == "input_missing"
    assert not output.exists()


def test_artifact_bundle_writes_rgba_foreground_alpha_and_ready_manifest(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    cache_root = tmp_path / "cache"
    write_source(source)
    fake_rembg(monkeypatch)

    result = process_background_isolation_bundle(
        source,
        cache_root,
        enabled_config(),
        "source-v1",
    )
    artifact_id = build_artifact_id("source-v1", enabled_config())
    paths = artifact_paths(cache_root, artifact_id)

    assert result["ok"] is True
    assert result["status"] == STATUS_READY
    assert result["artifact_id"] == artifact_id
    assert artifact_status(cache_root, artifact_id) == STATUS_READY
    assert paths.manifest.is_file()
    with Image.open(paths.foreground) as foreground:
        assert foreground.mode == "RGBA"
        assert foreground.getpixel((0, 0)) == (10, 20, 30, 127)
    with Image.open(paths.alpha) as alpha:
        assert alpha.mode == "L"
        assert alpha.getpixel((0, 0)) == 127


def test_artifact_bundle_cache_hit_does_not_load_rembg_again(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    cache_root = tmp_path / "cache"
    write_source(source)
    config = enabled_config()
    prepared = with_artifact_id(config, "source-v1")
    artifact_id = prepared["artifact"]["id"]
    paths = artifact_paths(cache_root, artifact_id)
    paths.directory.mkdir(parents=True)
    write_artifact_bytes(cache_root, artifact_id, "foreground", png_bytes_with_alpha())
    write_artifact_bytes(cache_root, artifact_id, "alpha", alpha_png_bytes())
    write_artifact_manifest(cache_root, artifact_id, status=STATUS_READY)

    def loader():
        raise AssertionError("cache hit must not load rembg")

    result = BackgroundIsolationWorker(loader=loader).process_artifact_bundle(
        source,
        cache_root,
        config,
        "source-v1",
    )

    assert result["ok"] is True
    assert result["status"] == STATUS_READY
    assert result["artifact_id"] == artifact_id
    with Image.open(paths.foreground) as foreground:
        assert foreground.mode == "RGBA"
    with Image.open(paths.alpha) as alpha:
        assert alpha.mode == "L"


def test_artifact_bundle_failure_cleans_partial_files_and_never_writes_ready(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    cache_root = tmp_path / "cache"
    write_source(source)
    fake_rembg(monkeypatch, output=b"not-an-image")

    result = process_background_isolation_bundle(
        source,
        cache_root,
        enabled_config(),
        "source-v1",
    )
    artifact_id = result["artifact_id"]
    paths = artifact_paths(cache_root, artifact_id)

    assert result["ok"] is False
    assert result["error_code"] == ERROR_REMBG_OUTPUT
    assert artifact_status(cache_root, artifact_id) == "missing"
    assert not paths.directory.exists()
    assert not list(cache_root.rglob("*.tmp")) if cache_root.exists() else True


def test_artifact_bundle_quality_failure_preserves_preexisting_non_ready_artifact(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    cache_root = tmp_path / "cache"
    write_source(source)
    config = enabled_config()
    artifact_id = build_artifact_id("source-v1", config)
    paths = artifact_paths(cache_root, artifact_id)
    paths.directory.mkdir(parents=True)
    old_foreground = b"old-foreground"
    old_alpha = b"old-alpha"
    write_artifact_bytes(cache_root, artifact_id, "foreground", old_foreground)
    write_artifact_bytes(cache_root, artifact_id, "alpha", old_alpha)
    write_artifact_manifest(cache_root, artifact_id, status="processing")
    fake_rembg(monkeypatch, output=png_bytes_with_solid_alpha(0))

    result = process_background_isolation_bundle(source, cache_root, config, "source-v1")

    assert result["ok"] is False
    assert result["error_code"] == ERROR_REMBG_QUALITY
    assert paths.foreground.read_bytes() == old_foreground
    assert paths.alpha.read_bytes() == old_alpha
    assert artifact_status(cache_root, artifact_id) == "processing"
    assert not list(cache_root.glob(".*"))


def test_invalid_ready_artifact_is_not_consumed_and_is_replaced_only_after_new_quality_passes(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    cache_root = tmp_path / "cache"
    write_source(source)
    config = enabled_config()
    artifact_id = build_artifact_id("source-v1", config)
    paths = artifact_paths(cache_root, artifact_id)
    paths.directory.mkdir(parents=True)
    write_artifact_bytes(cache_root, artifact_id, "foreground", b"invalid-old-foreground")
    write_artifact_bytes(cache_root, artifact_id, "alpha", b"invalid-old-alpha")
    write_artifact_manifest(cache_root, artifact_id, status=STATUS_READY)
    calls = fake_rembg(monkeypatch)

    result = process_background_isolation_bundle(source, cache_root, config, "source-v1")

    assert result["ok"] is True
    assert result["status"] == STATUS_READY
    assert calls["remove"] == 1
    with Image.open(paths.foreground) as foreground:
        assert foreground.mode == "RGBA"
    assert artifact_status(cache_root, artifact_id) == STATUS_READY


def test_artifact_publish_failure_restores_preexisting_artifact(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    cache_root = tmp_path / "cache"
    write_source(source)
    config = enabled_config()
    artifact_id = build_artifact_id("source-v1", config)
    paths = artifact_paths(cache_root, artifact_id)
    paths.directory.mkdir(parents=True)
    old_foreground = png_bytes_with_alpha()
    old_alpha = alpha_png_bytes()
    write_artifact_bytes(cache_root, artifact_id, "foreground", old_foreground)
    write_artifact_bytes(cache_root, artifact_id, "alpha", old_alpha)
    write_artifact_manifest(cache_root, artifact_id, status="processing")
    fake_rembg(monkeypatch)

    import scripts.background_isolation_worker as worker_module

    real_replace = worker_module.os.replace
    publish_failed = False

    def fail_new_artifact_publish(source_path, target_path):
        nonlocal publish_failed
        if (
            not publish_failed
            and Path(target_path) == paths.directory
            and Path(source_path).name.startswith(".")
        ):
            publish_failed = True
            raise OSError("simulated artifact publish failure")
        real_replace(source_path, target_path)

    monkeypatch.setattr(worker_module.os, "replace", fail_new_artifact_publish)
    result = process_background_isolation_bundle(source, cache_root, config, "source-v1")

    assert result["ok"] is False
    assert result["error_code"] == "artifact_commit_failed"
    assert paths.foreground.read_bytes() == old_foreground
    assert paths.alpha.read_bytes() == old_alpha
    assert artifact_status(cache_root, artifact_id) == "processing"
    assert not list(paths.directory.parent.glob(".*stale.*"))


def test_artifact_bundle_rejects_missing_or_invalid_fingerprint_without_files(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    cache_root = tmp_path / "cache"
    write_source(source)
    loader_called = False

    def loader():
        nonlocal loader_called
        loader_called = True
        raise AssertionError("invalid fingerprint must fail before rembg")

    worker = BackgroundIsolationWorker(loader=loader)
    missing = worker.process_artifact_bundle(source, cache_root, enabled_config(), None)
    invalid = worker.process_artifact_bundle(source, cache_root, enabled_config(), " ")

    assert missing["error_code"] == ERROR_SOURCE_FINGERPRINT_MISSING
    assert invalid["error_code"] == ERROR_SOURCE_FINGERPRINT_INVALID
    assert loader_called is False
    assert not cache_root.exists()


def test_artifact_bundle_missing_runtime_leaves_no_ready_manifest(tmp_path):
    source = tmp_path / "source.png"
    cache_root = tmp_path / "cache"
    write_source(source)

    def loader():
        raise ModuleNotFoundError("No module named 'onnxruntime'", name="onnxruntime")

    result = BackgroundIsolationWorker(loader=loader).process_artifact_bundle(
        source,
        cache_root,
        enabled_config(),
        "source-v1",
    )
    artifact_id = result["artifact_id"]

    assert result["ok"] is False
    assert result["error_code"] == ERROR_ONNXRUNTIME_MISSING
    assert artifact_status(cache_root, artifact_id) == "missing"
    assert not list(cache_root.rglob("manifest.json"))
