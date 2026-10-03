"""Tests for SAM 2 GPU video background isolation integration."""

import json
import os
import subprocess
from pathlib import Path
import pytest

from scripts.background_isolation import (
    normalize_background_isolation,
    SUPPORTED_ENGINES,
    SUPPORTED_MODELS,
)
from scripts.background_isolation_video_worker import (
    video_artifact_id,
    process_background_isolation_video,
    VIDEO_NAME,
    PREVIEW_NAME,
)


def test_sam2_contract_normalization():
    """Verify sam2 engine and models normalize properly in the contract."""
    assert "sam2" in SUPPORTED_ENGINES
    assert "sam2.1_hiera_tiny" in SUPPORTED_MODELS
    assert "sam2.1_hiera_small" in SUPPORTED_MODELS

    config = {
        "enabled": True,
        "mode": "cutout",
        "engine": "sam2",
        "model": "sam2.1_hiera_tiny",
        "quality": "quality",
    }
    normalized = normalize_background_isolation(config)
    assert normalized["enabled"] is True
    assert normalized["engine"] == "sam2"
    assert normalized["model"] == "sam2.1_hiera_tiny"
    assert normalized["quality"] == "quality"


def test_sam2_video_artifact_id_is_deterministic():
    """Verify artifact id is stable and contains sam2 engine signature."""
    config = {
        "enabled": True,
        "mode": "cutout",
        "engine": "sam2",
        "model": "sam2.1_hiera_tiny",
        "quality": "quality",
    }
    artifact_id_1 = video_artifact_id(
        "test_fingerprint_12345", config,
        start=0.0, duration=2.0, fps=30.0, timebase="1/30",
        width=540, height=960, rotation=0
    )
    artifact_id_2 = video_artifact_id(
        "test_fingerprint_12345", config,
        start=0.0, duration=2.0, fps=30.0, timebase="1/30",
        width=540, height=960, rotation=0
    )
    assert artifact_id_1 == artifact_id_2
    assert artifact_id_1.startswith("bgseq1-")


def test_sam2_models_config_and_resolution(monkeypatch, tmp_path):
    """Verify SAM 2 model configurations and checkpoints resolve correctly."""
    from scripts.background_isolation_sam2_worker import MODEL_CONFIGS, resolve_checkpoint
    monkeypatch.setenv("OMNICUT_SAM2_CHECKPOINT_DIR", str(tmp_path))
    for name in ("sam2.1_hiera_tiny", "sam2.1_hiera_small"):
        (tmp_path / f"{name}.pt").write_bytes(b"checkpoint-fixture")

    assert "sam2.1_hiera_tiny" in MODEL_CONFIGS
    assert "sam2.1_hiera_small" in MODEL_CONFIGS
    assert "sam2.1_hiera_base_plus" in MODEL_CONFIGS

    ckpt_tiny = resolve_checkpoint("sam2.1_hiera_tiny")
    assert ckpt_tiny.is_file()
    assert ckpt_tiny.name == "sam2.1_hiera_tiny.pt"

    ckpt_small = resolve_checkpoint("sam2.1_hiera_small")
    assert ckpt_small.is_file()
    assert ckpt_small.name == "sam2.1_hiera_small.pt"


def test_sam2_preflight_check(monkeypatch, tmp_path):
    """Verify SAM 2 preflight reports positive GPU runtime and model status."""
    from scripts.api_background_isolation import (
        BackgroundIsolationProcessRequest,
        _background_isolation_preflight,
    )
    import scripts.api_background_isolation as api
    monkeypatch.setattr(api, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(api, "probe_sam2_runtime", lambda: {"sam2_runtime": True, "cuda": True})
    monkeypatch.setattr(api, "resolve_checkpoint", lambda *args, **kwargs: tmp_path / "model.pt")

    req = BackgroundIsolationProcessRequest(
        source_path="01_Raw/test.mp4",
        config={
            "enabled": True,
            "mode": "cutout",
            "engine": "sam2",
            "model": "sam2.1_hiera_tiny",
            "quality": "quality",
        },
        start=0.0,
        duration=2.0,
        fps=30.0,
    )
    dummy_source = Path("tests")
    res = _background_isolation_preflight(req, dummy_source)
    assert res["ok"] is True
    assert res["model"] == "sam2.1_hiera_tiny"
    assert res["model_cached"] is True
    assert res["runtime"]["sam2_runtime"] is True


def test_sam2_process_background_isolation_video_gpu(tmp_path):
    """Verify SAM 2 GPU worker processes a real video clip into a valid cutout artifact."""
    if os.environ.get("OMNICUT_TEST_SAM2_GPU") != "1":
        pytest.skip("explicit local GPU diagnostic: set OMNICUT_TEST_SAM2_GPU=1")

    source = tmp_path / "test_source.mp4"
    cmd_gen = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
        "-i", "color=c=black:s=540x960:r=30:d=0.5",
        "-vf", "drawbox=x=170:y=380:w=200:h=200:color=red@1.0:t=fill",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)
    ]
    subprocess.run(cmd_gen, check=True)

    cache_root = tmp_path / ".cache"
    config = {
        "enabled": True,
        "mode": "cutout",
        "engine": "sam2",
        "model": "sam2.1_hiera_tiny",
        "quality": "quality",
    }
    progress_events = []

    res = process_background_isolation_video(
        source,
        cache_root,
        config,
        source_fingerprint="sam2_fp_test_1",
        start=0.0,
        duration=0.5,
        fps=30.0,
        timebase="1/30",
        width=540,
        height=960,
        rotation=0,
        progress_callback=lambda p: progress_events.append(p),
    )

    assert res["status"] == "ready"
    assert res["frame_count"] == 15
    out_dir = Path(res["output_directory"])
    assert (out_dir / "cutout.webm").is_file()
    assert (out_dir / "manifest.json").is_file()

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["engine"] == "sam2"
    assert manifest["model"] == "sam2.1_hiera_tiny"
    assert manifest["status"] == "ready"
    assert manifest["frame_count"] == 15
    assert len(progress_events) > 0
