# -*- coding: utf-8 -*-
"""S6-04/S6-07/S6-12: /api/hyperframes/render writes a .partial.mp4 with
--gpu --browser-gpu, promotes it only through the real probe gate (1080x1920,
30 FPS, tail decode) and removes the partial on failure or timeout."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import api_hyperframes as api
from scripts.channel_store import ChannelError
from tests.test_channel_hyperframes import composition, setup as channel_setup

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                                reason="ffmpeg/ffprobe required")
_REAL_RUN = subprocess.run


def _real_clip(path: Path, seconds: float = 2.0) -> bytes:
    _REAL_RUN([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"testsrc2=size=1080x1920:rate=30:duration={seconds}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(path),
    ], check=True, capture_output=True, timeout=120)
    return path.read_bytes()


def _render(monkeypatch, isolated_storage, writer):
    current, snapshot = channel_setup(isolated_storage, monkeypatch)
    (api.COMPOSITIONS_DIR / "owned.html").write_text(composition(snapshot), encoding="utf-8")
    seen = {}

    def run(command, **kwargs):
        if "render" not in command:  # ffprobe / ffmpeg gate runs for real
            return _REAL_RUN(command, **kwargs)
        seen["cmd"] = list(command)
        return writer(Path(command[command.index("-o") + 1]), command)

    monkeypatch.setattr(api.subprocess, "run", run)
    monkeypatch.setattr(api, "_extract_video_thumbnail", lambda *args, **kwargs: False)
    request = api.RenderCompositionRequest(composition_id="owned", output_filename="film.mp4")
    return seen, lambda: asyncio.run(api.render_composition(request, current))


def _exports():
    root = api.EXPORTS_DIR / "second"
    return sorted(p.name for p in root.glob("*.mp4")) if root.exists() else []


def test_valid_render_is_promoted_from_partial_with_gpu_flags(monkeypatch, isolated_storage, tmp_path):
    clip = _real_clip(tmp_path / "src.mp4")

    def writer(out, cmd):
        assert out.name == "film.partial.mp4"
        out.write_bytes(clip)
        return SimpleNamespace(returncode=0)

    seen, go = _render(monkeypatch, isolated_storage, writer)
    result = go()
    assert "--gpu" in seen["cmd"] and "--browser-gpu" in seen["cmd"]
    assert Path(result["output_path"]).name == "film.mp4"
    assert _exports() == ["film.mp4"]


def test_truncated_render_fails_and_leaves_nothing(monkeypatch, isolated_storage, tmp_path):
    clip = _real_clip(tmp_path / "src.mp4")

    def writer(out, cmd):
        out.write_bytes(clip[: len(clip) // 2])
        return SimpleNamespace(returncode=0)

    _, go = _render(monkeypatch, isolated_storage, writer)
    with pytest.raises((RuntimeError, ChannelError, Exception)):
        go()
    assert _exports() == []
    assert api.ExportRegistry.all(channel_id="second") == []


def test_timeout_removes_partial(monkeypatch, isolated_storage):
    def writer(out, cmd):
        out.write_bytes(b"half written")
        raise subprocess.TimeoutExpired(cmd, api.HF_RENDER_TIMEOUT_SEC)

    _, go = _render(monkeypatch, isolated_storage, writer)
    with pytest.raises(Exception):
        go()
    assert _exports() == []
