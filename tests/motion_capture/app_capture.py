"""Playwright capture seam for a live SequencePlayer canvas.

This module is intentionally test-side only.  It does not import or modify the
React renderer; it opens a caller-provided URL, validates a caller-provided
``<canvas>`` selector, and reads the canvas pixels through ``toDataURL``.
Artifacts are restricted to ``.tmp`` so an exploratory capture cannot become a
production export.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .capture import REPO_ROOT


APP_CAPTURE_SCHEMA_VERSION = 1


class AppCaptureUnavailable(RuntimeError):
    """Raised when a live app canvas cannot be captured safely."""


@dataclass(frozen=True)
class AppCaptureConfig:
    url: str
    selector: str
    output_dir: Path
    frame_count: int = 1
    interval_ms: int = 0
    ready_selector: str | None = None
    timeout_ms: int = 10_000
    headless: bool = True
    local_storage: Mapping[str, str] | None = None


def _validate_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    allowed_root = (REPO_ROOT / ".tmp").resolve()
    if not resolved.is_relative_to(allowed_root):
        raise ValueError(f"app capture output must be under {allowed_root}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _validate_config(config: AppCaptureConfig) -> AppCaptureConfig:
    if not config.url.strip():
        raise ValueError("url must not be empty")
    if not config.selector.strip():
        raise ValueError("selector must not be empty")
    if config.frame_count < 1:
        raise ValueError("frame_count must be at least 1")
    if config.interval_ms < 0:
        raise ValueError("interval_ms must be non-negative")
    if config.timeout_ms < 1:
        raise ValueError("timeout_ms must be positive")
    return AppCaptureConfig(
        **{**config.__dict__, "output_dir": _validate_output_dir(config.output_dir)}
    )


def _decode_data_url(data_url: str) -> bytes:
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise AppCaptureUnavailable("SequencePlayer canvas did not return a PNG data URL")
    try:
        return base64.b64decode(data_url[len(prefix) :], validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise AppCaptureUnavailable("SequencePlayer canvas returned invalid PNG data") from exc


def _capture_canvas_data(page: Any, selector: str) -> dict[str, Any]:
    try:
        return page.locator(selector).evaluate(
            """canvas => {
                if (!(canvas instanceof HTMLCanvasElement)) {
                    throw new Error(`selector resolved to ${canvas?.tagName || 'no element'}, not CANVAS`);
                }
                const dataUrl = canvas.toDataURL('image/png');
                const rect = canvas.getBoundingClientRect();
                return {
                    data_url: dataUrl,
                    width: canvas.width,
                    height: canvas.height,
                    css_width: rect.width,
                    css_height: rect.height,
                };
            }"""
        )
    except Exception as exc:
        raise AppCaptureUnavailable(f"canvas selector {selector!r} was not capturable: {exc}") from exc


def _capture_frame_data(page: Any, selector: str, frame_index: int) -> dict[str, Any]:
    """Use an app-provided deterministic seek hook when the page exposes one."""

    has_hook = page.evaluate("Boolean(window.motionCapture && window.motionCapture.capture)")
    if not has_hook:
        return _capture_canvas_data(page, selector)
    try:
        return page.evaluate(
            """({ selector, frameIndex }) => {
                const result = window.motionCapture.capture({ frameIndex });
                const canvas = document.querySelector(selector);
                if (!(canvas instanceof HTMLCanvasElement)) {
                    throw new Error(`selector resolved to ${canvas?.tagName || 'no element'}, not CANVAS`);
                }
                const rect = canvas.getBoundingClientRect();
                const { dataUrl, ...motionMetadata } = result;
                return {
                    ...motionMetadata,
                    data_url: dataUrl,
                    width: canvas.width,
                    height: canvas.height,
                    css_width: rect.width,
                    css_height: rect.height,
                };
            }""",
            {"selector": selector, "frameIndex": frame_index},
        )
    except Exception as exc:
        raise AppCaptureUnavailable(f"motionCapture hook could not capture frame {frame_index}: {exc}") from exc


def capture_app_canvas(config: AppCaptureConfig) -> dict[str, Any]:
    """Capture one or more frames from a live app canvas.

    The returned manifest is marked ``app_canvas`` and never claims parity with
    ASS/FFmpeg.  A caller can provide ``frame_count > 1`` to capture the same
    live SequencePlayer at successive wall-clock instants; deterministic
    timeline seeking remains an app-specific concern and is deliberately not
    guessed here.
    """

    config = _validate_config(config)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise AppCaptureUnavailable(f"Playwright is unavailable: {exc}") from exc

    frames: list[dict[str, Any]] = []
    try:
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=config.headless)
            except Exception as exc:  # pragma: no cover - environment dependent
                raise AppCaptureUnavailable(f"Chromium could not launch: {exc}") from exc
            context = None
            try:
                context = browser.new_context(
                    ignore_https_errors=True,
                    device_scale_factor=1,
                    color_scheme="dark",
                    viewport={"width": 1440, "height": 1000},
                )
                if config.local_storage:
                    storage_json = json.dumps(dict(config.local_storage), ensure_ascii=True)
                    context.add_init_script(
                        f"for (const [key, value] of Object.entries({storage_json})) "
                        "localStorage.setItem(key, value);"
                    )
                page = context.new_page()
                # App shells can keep polling APIs, so waiting for network idle
                # would make a valid Canvas capture hang unnecessarily.
                page.goto(config.url, wait_until="domcontentloaded", timeout=config.timeout_ms)
                if config.ready_selector:
                    page.wait_for_selector(config.ready_selector, timeout=config.timeout_ms)
                page.wait_for_selector(config.selector, state="attached", timeout=config.timeout_ms)

                canvas_info: dict[str, Any] | None = None
                for index in range(config.frame_count):
                    if index and config.interval_ms:
                        page.wait_for_timeout(config.interval_ms)
                    captured = _capture_frame_data(page, config.selector, index)
                    png = _decode_data_url(captured.pop("data_url"))
                    filename = f"frame_{index:04d}.png"
                    (config.output_dir / filename).write_bytes(png)
                    canvas_info = captured
                    frames.append(
                        {
                            "index": index,
                            "path": filename,
                            "sha256": hashlib.sha256(png).hexdigest(),
                            **captured,
                        }
                    )
            finally:
                if context is not None:
                    context.close()
                browser.close()
    except AppCaptureUnavailable:
        raise
    except Exception as exc:
        raise AppCaptureUnavailable(f"live app navigation/capture failed: {exc}") from exc

    manifest = {
        "schema_version": APP_CAPTURE_SCHEMA_VERSION,
        "status": "captured",
        "mode": "app_canvas",
        "pixel_parity_claim": False,
        "url": config.url,
        "selector": config.selector,
        "ready_selector": config.ready_selector,
        "frame_count": len(frames),
        "interval_ms": config.interval_ms,
        "canvas": canvas_info,
        "frames": frames,
        "notes": [
            "Pixels came from the live app canvas via HTMLCanvasElement.toDataURL().",
            "This manifest does not claim Canvas-vs-ASS/FFmpeg parity.",
            "Use an app-specific seek hook before comparing timeline timestamps.",
        ],
    }
    (config.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest


def temp_app_capture_dir(prefix: str = "motion-app-capture-") -> tempfile.TemporaryDirectory[str]:
    """Return a temporary capture directory constrained to the repository .tmp."""

    root = REPO_ROOT / ".tmp"
    root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix=prefix, dir=root)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture a live SequencePlayer canvas with Playwright")
    parser.add_argument("--url", required=True, help="live app URL")
    parser.add_argument("--selector", required=True, help="CSS selector resolving to the SequencePlayer canvas")
    parser.add_argument("--output-dir", type=Path, required=True, help="must be under .tmp")
    parser.add_argument("--ready-selector", help="optional selector to wait for before capturing")
    parser.add_argument("--frames", type=int, default=1, dest="frame_count")
    parser.add_argument("--interval-ms", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=10_000)
    parser.add_argument("--headed", action="store_true", help="show Chromium while capturing")
    parser.add_argument("--active-tab", help="set capcut_active_tab before navigation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    config = AppCaptureConfig(
        url=args.url,
        selector=args.selector,
        output_dir=args.output_dir,
        frame_count=args.frame_count,
        interval_ms=args.interval_ms,
        ready_selector=args.ready_selector,
        timeout_ms=args.timeout_ms,
        headless=not args.headed,
        local_storage=(
            {"capcut_active_tab": args.active_tab}
            if args.active_tab
            else None
        ),
    )
    try:
        manifest = capture_app_canvas(config)
    except (AppCaptureUnavailable, ValueError) as exc:
        print(json.dumps({"status": "skipped", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI smoke is covered by function tests
    raise SystemExit(main())
