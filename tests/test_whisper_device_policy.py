# -*- coding: utf-8 -*-
"""AGENTS rule 21 (audit S6-08, S2-19): faster-whisper is GPU-first.

No tracked script under scripts/, tools/ or the HyperFrames kit/clips may build
``WhisperModel(..., device="cpu")`` except as the fallback inside an
``except`` handler after CUDA failed.
"""

from __future__ import annotations

import ast
import inspect
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PREFIXES = ("scripts/", "tools/", "03_Projects/_HyperFrames_Studio/kit/", "03_Projects/_HyperFrames_Studio/clips/")


def _tracked_python_files():
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", check=True, timeout=60).stdout
    return [ROOT / line for line in out.splitlines() if line.startswith(SCAN_PREFIXES)]


def _cpu_whisper_calls_outside_fallback(tree: ast.AST):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name != "WhisperModel":
            continue
        device = next((kw.value for kw in node.keywords if kw.arg == "device"), None)
        if not (isinstance(device, ast.Constant) and device.value == "cpu"):
            continue
        cur, in_fallback = node, False
        while cur in parents:
            cur = parents[cur]
            if isinstance(cur, ast.ExceptHandler):
                in_fallback = True
                break
        if not in_fallback:
            bad.append(node.lineno)
    return bad


def test_no_hardcoded_cpu_whisper_outside_cuda_fallback():
    offenders = []
    files = _tracked_python_files()
    assert files, "git ls-files returned nothing to scan"
    for path in files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "WhisperModel" not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for line in _cpu_whisper_calls_outside_fallback(tree):
            offenders.append(f"{path.relative_to(ROOT).as_posix()}:{line}")
    assert offenders == [], f'WhisperModel(device="cpu") outside a CUDA-failure fallback: {offenders}'


def test_cloud_runner_whisper_defaults_to_gpu_detection():
    from scripts import cloud_runner

    for fn in (cloud_runner.verify_turns_with_whisper, cloud_runner.build_and_render_couple_chat_clip):
        assert inspect.signature(fn).parameters["device"].default is None
    assert cloud_runner._resolve_whisper_device("cuda") == ("cuda", "float16")
    assert cloud_runner._resolve_whisper_device("cpu") == ("cpu", "int8")
