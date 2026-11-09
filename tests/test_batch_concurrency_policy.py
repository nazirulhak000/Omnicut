# -*- coding: utf-8 -*-
"""AGENTS rule 24 (audit S6-03/05/07/10): every tools/batch_render_*.py runs
on a >=3-worker pool, renders with --gpu --browser-gpu, gates resume/raw
output through scripts.media_validation, bounds the HyperFrames CLI with a
timeout, and never ships the raw MP4 when the enhancer fails."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = sorted((ROOT / "tools").glob("batch_render_*.py"))


def test_there_are_batch_render_tools():
    assert len(SCRIPTS) >= 7


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_batch_tool_policy(path):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    # >= 3 workers by default
    m = re.search(r'add_argument\("--workers",\s*type=int,\s*default=(\d+)', text)
    assert m and int(m.group(1)) >= 3, "needs --workers default >= 3"
    assert "ThreadPoolExecutor(" in text

    # GPU render
    assert '"--gpu"' in text and '"--browser-gpu"' in text

    # central validator, not a size/duration check
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "is_valid_mp4")
    assert "media_validation.is_valid_mp4" in ast.get_source_segment(text, fn)
    assert "st_size > 1024 * 1024 and skip_existing" not in text

    # HyperFrames CLI bounded by a timeout
    assert "timeout=HF_RENDER_TIMEOUT_SEC" in text

    # enhancer failure fails the clip
    for forbidden in ("keeping raw MP4", "copying raw MP4", "shutil.move(str(temp_raw), str(out_mp4))",
                      "shutil.copy2(raw_mp4, final_mp4)"):
        assert forbidden not in text


def test_server_hyperframes_paths_use_gpu_flags():
    api = (ROOT / "scripts" / "api_hyperframes.py").read_text(encoding="utf-8")
    assert '"--gpu", "--browser-gpu"' in api
    engine = (ROOT / "scripts" / "hyperframes_engine.py").read_text(encoding="utf-8")
    assert '"--browser-gpu"' in engine
