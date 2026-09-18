"""Tests for the live app-level Playwright Canvas capture seam."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import pytest

from tests.motion_capture.app_capture import (
    AppCaptureConfig,
    AppCaptureUnavailable,
    capture_app_canvas,
    temp_app_capture_dir,
)


def test_app_capture_reads_real_canvas_pixels_from_url():
    html = """
    <!doctype html>
    <canvas id="sequence-player-canvas" width="32" height="24"></canvas>
    <script>
      const canvas = document.querySelector('#sequence-player-canvas');
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#12abef';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    </script>
    """
    tmp = temp_app_capture_dir()
    output = Path(tmp.name) / "capture"
    try:
        manifest = capture_app_canvas(
            AppCaptureConfig(
                url=f"data:text/html,{quote(html)}",
                selector="#sequence-player-canvas",
                output_dir=output,
            )
        )
        assert manifest["status"] == "captured"
        assert manifest["mode"] == "app_canvas"
        assert manifest["pixel_parity_claim"] is False
        assert manifest["canvas"]["width"] == 32
        assert (output / "frame_0000.png").read_bytes().startswith(b"\x89PNG")
        assert (output / "manifest.json").exists()
    finally:
        tmp.cleanup()


def test_app_capture_rejects_non_tmp_output(tmp_path: Path):
    with pytest.raises(ValueError, match="must be under"):
        capture_app_canvas(
            AppCaptureConfig(
                url="data:text/html,<canvas></canvas>",
                selector="canvas",
                output_dir=tmp_path / "outside-repo-tmp",
            )
        )


def test_app_capture_reports_missing_canvas_as_unavailable():
    tmp = temp_app_capture_dir()
    try:
        with pytest.raises(AppCaptureUnavailable, match="canvas selector"):
            capture_app_canvas(
                AppCaptureConfig(
                    url="data:text/html,<div id='not-a-canvas'></div>",
                    selector="#not-a-canvas",
                    output_dir=Path(tmp.name) / "capture",
                )
            )
    finally:
        tmp.cleanup()


@pytest.mark.skipif(
    not os.getenv("MOTION_CAPTURE_APP_URL"),
    reason=(
        "live app capture is opt-in: set MOTION_CAPTURE_APP_URL and "
        "MOTION_CAPTURE_APP_CANVAS_SELECTOR to capture the real SequencePlayer canvas"
    ),
)
def test_live_sequence_player_canvas_capture():
    """Run only when a user-supplied local app session is available."""

    tmp = temp_app_capture_dir("motion-live-sequence-player-")
    selector = os.getenv("MOTION_CAPTURE_APP_CANVAS_SELECTOR", "canvas")
    try:
        try:
            manifest = capture_app_canvas(
                AppCaptureConfig(
                    url=os.environ["MOTION_CAPTURE_APP_URL"],
                    selector=selector,
                    ready_selector=os.getenv("MOTION_CAPTURE_APP_READY_SELECTOR"),
                    output_dir=Path(tmp.name) / "capture",
                    frame_count=int(os.getenv("MOTION_CAPTURE_APP_FRAMES", "1")),
                )
            )
        except AppCaptureUnavailable as exc:
            pytest.skip(f"live app capture unavailable: {exc}")
        assert manifest["mode"] == "app_canvas"
        assert manifest["pixel_parity_claim"] is False
        assert manifest["frames"]
    finally:
        tmp.cleanup()
