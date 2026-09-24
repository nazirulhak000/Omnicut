"""Tests for the live app-level Playwright Canvas capture seam."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest

from tests.motion_capture.app_capture import (
    AppCaptureConfig,
    AppCaptureUnavailable,
    _is_expected_media_seek_abort,
    capture_app_canvas,
    temp_app_capture_dir,
)


@pytest.mark.parametrize(
    ("resource_type", "failure", "expected"),
    [
        ("media", "net::ERR_ABORTED", True),
        ("fetch", "net::ERR_ABORTED", False),
        ("media", "net::ERR_CONNECTION_RESET", False),
    ],
)
def test_only_cancelled_stale_media_seeks_are_nonfatal(resource_type, failure, expected):
    assert _is_expected_media_seek_abort(resource_type, failure) is expected


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
        assert manifest["runtime"]["clean"] is True
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


def test_capture_uses_explicit_deterministic_frame_indices():
    html = """
    <!doctype html>
    <canvas id="sequence-player-canvas" width="32" height="24"></canvas>
    <script>
      const canvas = document.querySelector('#sequence-player-canvas');
      const ctx = canvas.getContext('2d');
      window.motionCapture = {
        capture: ({ frameIndex }) => {
          ctx.fillStyle = `rgb(${frameIndex}, 0, 0)`;
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          return { frameIndex, timestampMs: Math.round(frameIndex * 1000 / 30), dataUrl: canvas.toDataURL('image/png') };
        },
      };
    </script>
    """
    tmp = temp_app_capture_dir("motion-explicit-frames-")
    try:
        manifest = capture_app_canvas(
            AppCaptureConfig(
                url=f"data:text/html,{quote(html)}",
                selector="#sequence-player-canvas",
                output_dir=Path(tmp.name) / "capture",
                frame_indices=(0, 6, 30),
            )
        )
        assert manifest["frame_indices"] == [0, 6, 30]
        assert [frame["frameIndex"] for frame in manifest["frames"]] == [0, 6, 30]
        assert [frame["timestampMs"] for frame in manifest["frames"]] == [0, 200, 1000]
        assert (Path(tmp.name) / "capture" / "frame_0030.png").exists()
    finally:
        tmp.cleanup()


def test_browser_runtime_error_is_not_silently_accepted():
    html = """
    <!doctype html>
    <canvas id="sequence-player-canvas" width="32" height="24"></canvas>
    <script>console.error('intentional parity harness error')</script>
    """
    tmp = temp_app_capture_dir("motion-runtime-error-")
    output = Path(tmp.name) / "capture"
    try:
        with pytest.raises(AppCaptureUnavailable, match="browser runtime errors"):
            capture_app_canvas(
                AppCaptureConfig(
                    url=f"data:text/html,{quote(html)}",
                    selector="#sequence-player-canvas",
                    output_dir=output,
                )
            )
        assert (output / "manifest.json").exists()
    finally:
        tmp.cleanup()


def test_self_hosted_sequence_player_canvas_capture(motion_fixture_url: str):
    """Open the real Vite fixture without user-supplied environment variables."""

    tmp = temp_app_capture_dir("motion-live-sequence-player-")
    try:
        manifest = capture_app_canvas(
            AppCaptureConfig(
                url=motion_fixture_url,
                selector="[data-testid='motion-capture-sequence-player'] canvas",
                ready_selector="[data-testid='motion-capture-sequence-player']",
                output_dir=Path(tmp.name) / "capture",
                frame_indices=(0, 6, 30, 59),
                timeout_ms=20_000,
            )
        )
        assert manifest["mode"] == "app_canvas"
        assert manifest["pixel_parity_claim"] is False
        assert manifest["frame_indices"] == [0, 6, 30, 59]
        assert [frame["frameIndex"] for frame in manifest["frames"]] == [0, 6, 30, 59]
        assert manifest["runtime"]["clean"] is True
    finally:
        tmp.cleanup()


def test_sequence_player_seek_order_and_loop_frames_are_deterministic(motion_fixture_url: str):
    """Forward, backward, and cycle-equivalent seeks must return the same pixels."""

    tmp = temp_app_capture_dir("motion-live-seek-determinism-")
    try:
        manifests = []
        for name, frame_indices in (
            ("forward", (6, 18, 30, 39)),
            ("backward", (39, 30, 18, 6)),
        ):
            manifests.append(capture_app_canvas(
                AppCaptureConfig(
                    url=motion_fixture_url,
                    selector="[data-testid='motion-capture-sequence-player'] canvas",
                    ready_selector="[data-testid='motion-capture-sequence-player']",
                    output_dir=Path(tmp.name) / name,
                    frame_indices=frame_indices,
                    timeout_ms=20_000,
                )
            ))

        forward, backward = manifests
        forward_hashes = {frame["frameIndex"]: frame["sha256"] for frame in forward["frames"]}
        backward_hashes = {frame["frameIndex"]: frame["sha256"] for frame in backward["frames"]}

        assert forward["runtime"]["clean"] is True
        assert backward["runtime"]["clean"] is True
        assert forward_hashes == backward_hashes
        assert forward_hashes[18] == forward_hashes[39], "pulse loop must repeat exactly after 700 ms"
    finally:
        tmp.cleanup()
