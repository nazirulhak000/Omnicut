"""Shared, relocatable SAM2 runtime/checkpoint discovery without downloading.

OMNICUT_SAM2_PYTHON overrides the isolated interpreter; OMNICUT_SAM2_CHECKPOINT_DIR
overrides the model directory. Relative overrides resolve against the workspace.
"""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MODEL_CONFIGS = {
    "sam2.1_hiera_tiny": "configs/sam2.1/sam2.1_hiera_t.yaml",
    "sam2.1_hiera_small": "configs/sam2.1/sam2.1_hiera_s.yaml",
    "sam2.1_hiera_base_plus": "configs/sam2.1/sam2.1_hiera_b+.yaml",
    "sam2.1_hiera_large": "configs/sam2.1/sam2.1_hiera_l.yaml",
}


def _workspace_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def sam2_python() -> Path:
    override = os.environ.get("OMNICUT_SAM2_PYTHON")
    if override:
        return _workspace_path(override)
    executable = Path("Scripts/python.exe") if sys.platform == "win32" else Path("bin/python")
    return WORKSPACE_ROOT / "tools" / "cutout_runtime" / ".venv" / executable


def resolve_checkpoint(model: str = "sam2.1_hiera_tiny", checkpoint: Path | None = None,
                       *, cache_root: Path | None = None) -> Path:
    if model not in MODEL_CONFIGS:
        raise ValueError(f"unsupported SAM2 model: {model}")
    if checkpoint is not None:
        checkpoint = Path(checkpoint)
        if not checkpoint.is_file():
            raise FileNotFoundError(f"SAM2 checkpoint not found: {checkpoint}")
        return checkpoint
    directories = []
    override = os.environ.get("OMNICUT_SAM2_CHECKPOINT_DIR")
    if override:
        directories.append(_workspace_path(override))
    if cache_root is not None:
        directories.append(Path(cache_root).parent / "cutout-models")
    directories.extend([
        WORKSPACE_ROOT / "03_Projects" / ".cache" / "cutout-models",
        WORKSPACE_ROOT.parent / "external_repos" / "sam2" / "checkpoints",
    ])
    for directory in directories:
        candidate = directory / f"{model}.pt"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"SAM2 checkpoint {model}.pt not found; set OMNICUT_SAM2_CHECKPOINT_DIR "
        "or place the selected model in the project cutout-models cache"
    )


@lru_cache(maxsize=4)
def _probe_runtime(interpreter: str, modified_ns: int) -> dict[str, Any]:
    # Separate interpreter: the backend venv intentionally need not carry torch.
    command = (
        "import json,torch,sam2,numpy,PIL; "
        "available=torch.cuda.is_available(); "
        "print(json.dumps({'sam2_runtime':True,'cuda':available,"
        "'torch_version':torch.__version__,"
        "'device_name':torch.cuda.get_device_name(0) if available else None}))"
    )
    try:
        result = subprocess.run([interpreter, "-c", command], capture_output=True,
                                text=True, timeout=20)
        if result.returncode:
            return {"sam2_runtime": True, "cuda": False,
                    "error": f"SAM2 runtime import failed: {result.stderr[-600:].strip()}"}
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError) as exc:
        return {"sam2_runtime": True, "cuda": False,
                "error": f"SAM2 runtime probe failed: {exc}"}


def probe_sam2_runtime() -> dict[str, Any]:
    interpreter = sam2_python()
    if not interpreter.is_file():
        return {"sam2_runtime": False, "cuda": False,
                "error": "SAM2 interpreter missing; configure OMNICUT_SAM2_PYTHON "
                         "or tools/cutout_runtime/.venv"}
    return dict(_probe_runtime(str(interpreter), interpreter.stat().st_mtime_ns))


def cutout_frame_filter(width: int, height: int) -> str:
    """Match the editor/auto-prompt/rembg fit while keeping source proportions."""
    return (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black")


def frame_in_intervals(index: int, start: float, fps: float,
                       intervals: list[tuple[float, float]] | None) -> bool:
    """Intervals use source time and include begin but exclude end."""
    if intervals is None:
        return True
    source_time = start + index / fps
    return any(begin <= source_time < end for begin, end in intervals)


def sam2_input_memory_bytes(frame_count: int) -> int:
    """Capacity estimate for eager 1024² RGB float32 input plus overhead."""
    return 1024**3 + max(0, frame_count) * 3 * 1024 * 1024 * 4
