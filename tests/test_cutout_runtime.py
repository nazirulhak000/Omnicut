"""Offline contracts for the isolated SAM2 environment and model portability."""
from pathlib import Path
import json
import subprocess
from types import SimpleNamespace

import pytest

import scripts.cutout_runtime as runtime
import scripts.api_background_isolation as api
from scripts.background_isolation import normalize_background_isolation


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    workspace = tmp_path / "relocated" / "Omnicut"
    monkeypatch.setattr(runtime, "WORKSPACE_ROOT", workspace)
    monkeypatch.delenv("OMNICUT_SAM2_PYTHON", raising=False)
    monkeypatch.delenv("OMNICUT_SAM2_CHECKPOINT_DIR", raising=False)
    runtime._probe_runtime.cache_clear()
    yield workspace
    runtime._probe_runtime.cache_clear()


def test_interpreter_relative_override_and_platform_layout(monkeypatch, isolated):
    monkeypatch.setattr(runtime.sys, "platform", "win32")
    assert runtime.sam2_python() == isolated / "tools/cutout_runtime/.venv/Scripts/python.exe"
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    assert runtime.sam2_python() == isolated / "tools/cutout_runtime/.venv/bin/python"
    monkeypatch.setenv("OMNICUT_SAM2_PYTHON", "custom/bin/python")
    assert runtime.sam2_python() == isolated / "custom/bin/python"


def test_checkpoint_search_uses_selected_model_without_tiny_fallback(isolated):
    directory = isolated.parent / "external_repos/sam2/checkpoints"
    directory.mkdir(parents=True)
    tiny = directory / "sam2.1_hiera_tiny.pt"
    tiny.write_bytes(b"tiny")
    assert runtime.resolve_checkpoint() == tiny
    with pytest.raises(FileNotFoundError, match="sam2.1_hiera_small.pt"):
        runtime.resolve_checkpoint("sam2.1_hiera_small")
    with pytest.raises(FileNotFoundError, match="missing.pt"):
        runtime.resolve_checkpoint(checkpoint=directory / "missing.pt")
    with pytest.raises(ValueError, match="unsupported"):
        runtime.resolve_checkpoint("u2net")


def test_checkpoint_override_precedes_cache_and_is_portable(monkeypatch, isolated):
    directory = isolated / "models"
    directory.mkdir(parents=True)
    checkpoint = directory / "sam2.1_hiera_small.pt"
    checkpoint.write_bytes(b"small")
    monkeypatch.setenv("OMNICUT_SAM2_CHECKPOINT_DIR", "models")
    assert runtime.resolve_checkpoint("sam2.1_hiera_small", cache_root=isolated / "temp/.cache") == checkpoint


def test_missing_runtime_and_cuda_failure_are_actionable(monkeypatch, isolated):
    assert runtime.probe_sam2_runtime()["sam2_runtime"] is False
    interpreter = runtime.sam2_python()
    interpreter.parent.mkdir(parents=True)
    interpreter.write_bytes(b"fake")
    monkeypatch.setattr(runtime.subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=1, stdout="", stderr="ModuleNotFoundError: torch"))
    report = runtime.probe_sam2_runtime()
    assert report["sam2_runtime"] is True and report["cuda"] is False
    assert "torch" in report["error"]


def test_successful_probe_cache_does_not_mutate_shared_report(monkeypatch, isolated):
    interpreter = runtime.sam2_python()
    interpreter.parent.mkdir(parents=True)
    interpreter.write_bytes(b"fake")
    calls = []
    def probe(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
            "sam2_runtime": True, "cuda": True, "device_name": "test GPU"}))
    monkeypatch.setattr(runtime.subprocess, "run", probe)
    runtime.probe_sam2_runtime()["cuda"] = False
    assert runtime.probe_sam2_runtime()["cuda"] is True
    assert len(calls) == 1


@pytest.mark.parametrize("report,code", [
    ({"sam2_runtime": False, "cuda": False}, "sam2_runtime_missing"),
    ({"sam2_runtime": True, "cuda": False, "error": "no NVIDIA GPU"}, "sam2_cuda_unavailable"),
])
def test_preflight_rejects_runtime_unready(monkeypatch, tmp_path, report, code):
    monkeypatch.setattr(api, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(api, "probe_sam2_runtime", lambda: report)
    monkeypatch.setattr(api, "resolve_checkpoint", lambda *a, **kw: tmp_path / "tiny.pt")
    req = api.BackgroundIsolationProcessRequest(source_path="source.mp4", duration=.2,
        config={"enabled": True, "engine": "sam2", "model": "sam2.1_hiera_tiny"})
    result = api._background_isolation_preflight(req, tmp_path / "source.mp4")
    assert result["ok"] is False
    assert code in [issue["code"] for issue in result["issues"]]


def test_preflight_missing_model_is_error_not_download_promise(monkeypatch, isolated):
    monkeypatch.setattr(api, "PROJECTS_DIR", isolated)
    monkeypatch.setattr(api, "probe_sam2_runtime", lambda: {"sam2_runtime": True, "cuda": True})
    req = api.BackgroundIsolationProcessRequest(source_path="source.mp4", duration=.2,
        config={"enabled": True, "engine": "sam2", "model": "sam2.1_hiera_small"})
    result = api._background_isolation_preflight(req, isolated / "source.mp4")
    assert result["ok"] is False and result["model_cached"] is False
    assert any(issue["code"] == "model_not_cached" and issue["severity"] == "error"
               for issue in result["issues"])


@pytest.mark.parametrize("config,engine,model", [
    ({"enabled": True}, "rembg", "u2net"),
    ({"enabled": True, "model": "u2netp"}, "rembg", "u2netp"),
    ({"enabled": True, "model": "sam2.1_hiera_small"}, "sam2", "sam2.1_hiera_small"),
    ({"enabled": True, "engine": "sam2"}, "sam2", "sam2.1_hiera_tiny"),
])
def test_engine_inference_preserves_legacy_defaults(config, engine, model):
    normalized = normalize_background_isolation(config)
    assert normalized["enabled"] is True
    assert (normalized["engine"], normalized["model"]) == (engine, model)


@pytest.mark.parametrize("engine,model", [("sam2", "u2net"), ("rembg", "sam2.1_hiera_tiny")])
def test_explicit_engine_model_mismatch_is_rejected(engine, model):
    normalized = normalize_background_isolation({"enabled": True, "engine": engine, "model": model})
    assert normalized["enabled"] is False
    assert normalized["reason"] == "invalid_engine_model"


def test_interval_boundaries_are_source_time_begin_inclusive_end_exclusive():
    intervals = [(1 + 2 / 30, 1 + 5 / 30), (1 + 8 / 30, 1 + 11 / 30)]
    actual = [index for index in range(12) if runtime.frame_in_intervals(index, 1, 30, intervals)]
    assert actual == [2, 3, 4, 8, 9, 10]
    assert runtime.frame_in_intervals(0, 0, 30, None) is True
    assert runtime.frame_in_intervals(0, 0, 30, []) is False


def test_sam2_preflight_accounts_for_all_frames_even_with_sparse_alpha(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(api, "probe_sam2_runtime", lambda: {"sam2_runtime": True, "cuda": True})
    monkeypatch.setattr(api, "resolve_checkpoint", lambda *a, **kw: tmp_path / "tiny.pt")
    monkeypatch.setattr(api.importlib.util, "find_spec", lambda name: True)
    monkeypatch.setattr(api.importlib, "import_module", lambda name: SimpleNamespace(
        virtual_memory=lambda: SimpleNamespace(available=2 * 1024**3)))
    req = api.BackgroundIsolationProcessRequest(source_path="source.mp4", duration=60,
        active_intervals=[(0, 1)], config={"enabled": True, "engine": "sam2", "model": "sam2.1_hiera_tiny"})
    report = api._background_isolation_preflight(req, tmp_path / "source.mp4")
    assert report["frame_count"] == 1800 and report["isolated_frame_count"] == 30
    assert report["required_memory_bytes"] == 1024**3 + 1800 * 12 * 1024**2
    issue = next(issue for issue in report["issues"] if issue["code"] == "memory_low")
    assert issue["severity"] == "error"
    assert "source" in issue["message"] and "u2netp" not in issue["message"]


@pytest.mark.parametrize("source_duration,expected_frames", [(61, 1800), (0, None), (float("nan"), None)])
def test_sam2_preflight_unknown_window_probes_duration_and_refuses_unknown_capacity(monkeypatch, tmp_path, source_duration, expected_frames):
    import scripts.silence_detect as silence
    monkeypatch.setattr(api, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(api, "probe_sam2_runtime", lambda: {"sam2_runtime": True, "cuda": True})
    monkeypatch.setattr(api, "resolve_checkpoint", lambda *a, **kw: tmp_path / "tiny.pt")
    monkeypatch.setattr(silence, "_probe_duration", lambda source: source_duration)
    req = api.BackgroundIsolationProcessRequest(source_path="source.mp4", start=1,
        config={"enabled": True, "engine": "sam2", "model": "sam2.1_hiera_tiny"})
    report = api._background_isolation_preflight(req, tmp_path / "source.mp4")
    assert report["frame_count"] == expected_frames
    if expected_frames is not None:
        assert report["duration"] == 60 and report["duration_inferred"] is True
        assert report["required_memory_bytes"] == runtime.sam2_input_memory_bytes(1800)
        assert not any(issue["code"] == "duration_unknown" for issue in report["issues"])
    else:
        assert report["ok"] is False and report["duration_inferred"] is False
        assert any(issue["code"] == "duration_unknown" and issue["severity"] == "error"
                   for issue in report["issues"])
