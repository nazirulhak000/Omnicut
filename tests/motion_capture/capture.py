"""Deterministic browser Canvas capture seam for motion parity.

The browser path is authoritative for Canvas pixels.  When Playwright or its
Chromium runtime is unavailable, the fallback still invokes the real
``sampleCanvasMotion`` JavaScript adapter through Node and rasterizes the same
state into deterministic PNGs with Pillow.  The fallback is intentionally
labelled and is never reported as browser pixel parity.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import io
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import tempfile
from threading import Thread
from typing import Any, Iterable, Mapping, Sequence

from scripts.subtitle.motion_ass_adapter import build_ass_motion_segments
from scripts.subtitle.motion_contract import MOTION_PRESETS, get_motion_preset


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = "/tests/motion_capture/fixture.html"
DEFAULT_SAMPLE_TIMES = (0.0, 0.25, 0.5, 0.75, 1.0)
DEFAULT_SIZE = (256, 256)
CAPTURE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BrowserProbe:
    available: bool
    engine: str
    executable: str | None
    reason: str | None = None


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def _serve_repo() -> tuple[ThreadingHTTPServer, Thread]:
    handler = lambda *args, **kwargs: _QuietHandler(  # noqa: E731
        *args, directory=str(REPO_ROOT), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def probe_browser() -> BrowserProbe:
    """Probe Playwright Chromium without creating project artifacts."""

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return BrowserProbe(False, "chromium", None, f"playwright import failed: {exc}")

    try:
        with sync_playwright() as playwright:
            executable = Path(playwright.chromium.executable_path)
            if not executable.exists():
                return BrowserProbe(False, "chromium", str(executable), "Chromium executable is missing")
            browser = playwright.chromium.launch(headless=True)
            version = browser.version
            browser.close()
            return BrowserProbe(True, "chromium", str(executable), version)
    except Exception as exc:  # pragma: no cover - depends on local browser install
        return BrowserProbe(False, "chromium", None, f"browser launch failed: {exc}")


def _validate_output_dir(output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    allowed_root = (REPO_ROOT / ".tmp").resolve()
    if not output_dir.is_relative_to(allowed_root):
        raise ValueError(f"capture output must be under {allowed_root}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _preset_ids(preset_ids: Iterable[str] | None) -> tuple[str, ...]:
    values = tuple(sorted(preset_ids or MOTION_PRESETS.keys()))
    unknown = sorted(set(values) - set(MOTION_PRESETS))
    if unknown:
        raise ValueError(f"unknown motion preset ids: {unknown}")
    return values


def _sample_times(sample_times: Iterable[float] | None) -> tuple[float, ...]:
    values = tuple(float(value) for value in (sample_times or DEFAULT_SAMPLE_TIMES))
    if not values or any(value < 0 or value > 1 for value in values):
        raise ValueError("sample_times must contain values in the normalized 0..1 range")
    return values


def _browser_capture(
    preset_ids: Sequence[str], sample_times: Sequence[float], width: int, height: int
) -> tuple[dict[str, Any], BrowserProbe]:
    from playwright.sync_api import sync_playwright

    server, _thread = _serve_repo()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                    color_scheme="dark",
                )
                page.goto(f"http://127.0.0.1:{server.server_port}{FIXTURE_PATH}", wait_until="load")
                result = page.evaluate(
                    "args => window.motionCapture.capture(args)",
                    {
                        "preset_ids": list(preset_ids),
                        "sample_times": list(sample_times),
                        "width": width,
                        "height": height,
                    },
                )
                probe = BrowserProbe(True, "chromium", str(playwright.chromium.executable_path), browser.version)
                return result, probe
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()


def _run_node_sampler(
    preset_ids: Sequence[str], sample_times: Sequence[float], width: int, height: int
) -> dict[str, Any]:
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise RuntimeError("Node.js executable is unavailable for sampleCanvasMotion fallback")
    payload = json.dumps(
        {
            "preset_ids": list(preset_ids),
            "sample_times": list(sample_times),
            "width": width,
            "height": height,
        }
    )
    completed = subprocess.run(
        [node, str(Path(__file__).with_name("sample_motion.mjs"))],
        input=payload,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "sampleCanvasMotion fallback failed")
    return json.loads(completed.stdout)


def _clamp(value: Any, low: float, high: float) -> float:
    return max(low, min(high, float(value or 0)))


def _fallback_png(state: Mapping[str, Any], width: int, height: int) -> bytes:
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (width, height), (11, 16, 32, 255))
    layer = Image.new("RGBA", (220, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    reveal = _clamp(state.get("reveal", 1), 0, 1)
    alpha = int(round(_clamp(state.get("alpha", 1), 0, 1) * 255))
    draw.rectangle((10, 16, 10 + int(round(192 * reveal)), 30), fill=(33, 212, 253, alpha))
    draw.rectangle((10, 42, 10 + int(round(150 * reveal)), 54), fill=(255, 77, 141, alpha))
    draw.rectangle((10, 66, 10 + int(round(104 * reveal)), 76), fill=(255, 230, 0, alpha))

    scale = float(state.get("scale", 1) or 1)
    if scale != 1:
        scaled = layer.resize(
            (max(1, round(layer.width * scale)), max(1, round(layer.height * scale))),
            Image.Resampling.BICUBIC,
        )
    else:
        scaled = layer
    rotation = float(state.get("rotation", 0) or 0)
    if rotation:
        scaled = scaled.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)

    position = state.get("position") or {}
    x = width / 2 + float(position.get("x", 0) or 0)
    y = height / 2 + float(position.get("y", 0) or 0) + float(state.get("dy", 0) or 0)
    image.alpha_composite(scaled, (round(x - scaled.width / 2), round(y - scaled.height / 2)))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False, compress_level=9)
    return buffer.getvalue()


def _write_frames(result: Mapping[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    frames = []
    for index, frame in enumerate(result["frames"]):
        filename = f"{index:04d}_{frame['preset_id'].replace('.', '__')}_t{frame['normalized_time']:.2f}.png"
        png = base64.b64decode(frame["png_base64"])
        path = output_dir / filename
        path.write_bytes(png)
        frames.append(
            {
                "preset_id": frame["preset_id"],
                "normalized_time": frame["normalized_time"],
                "path": filename,
                "sha256": hashlib.sha256(png).hexdigest(),
                "state": frame["state"],
                "metadata": frame["metadata"],
            }
        )
    return frames


def _write_fallback_frames(result: Mapping[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    frames = []
    for index, frame in enumerate(result["frames"]):
        filename = f"{index:04d}_{frame['preset_id'].replace('.', '__')}_t{frame['normalized_time']:.2f}.png"
        png = _fallback_png(frame["state"], int(result["width"]), int(result["height"]))
        path = output_dir / filename
        path.write_bytes(png)
        frames.append(
            {
                "preset_id": frame["preset_id"],
                "normalized_time": frame["normalized_time"],
                "path": filename,
                "sha256": hashlib.sha256(png).hexdigest(),
                "state": frame["state"],
                "metadata": frame["metadata"],
            }
        )
    return frames


def _ass_manifest(preset_ids: Sequence[str]) -> dict[str, Any]:
    plans = {}
    for identifier in preset_ids:
        role, phase, preset_id = identifier.split(".", 2)
        contract = get_motion_preset(role, phase, preset_id)
        assert contract is not None
        plans[identifier] = build_ass_motion_segments(contract).to_dict()
    return plans


def capture_motion(
    output_dir: Path,
    *,
    preset_ids: Iterable[str] | None = None,
    sample_times: Iterable[float] | None = None,
    prefer_browser: bool = True,
) -> dict[str, Any]:
    """Capture a deterministic motion catalog into a `.tmp` directory."""

    output_dir = _validate_output_dir(Path(output_dir))
    ids = _preset_ids(preset_ids)
    times = _sample_times(sample_times)
    width, height = DEFAULT_SIZE
    probe = probe_browser() if prefer_browser else BrowserProbe(False, "chromium", None, "browser path disabled")
    blockers: list[str] = []

    if prefer_browser and probe.available:
        try:
            result, probe = _browser_capture(ids, times, width, height)
            frames = _write_frames(result, output_dir)
            mode = "browser_canvas"
        except Exception as exc:  # pragma: no cover - exercised on broken browser installs
            blockers.append(f"browser capture failed: {exc}")
            result = _run_node_sampler(ids, times, width, height)
            frames = _write_fallback_frames(result, output_dir)
            mode = "sampleCanvasMotion_raster_fallback"
    else:
        blockers.append(probe.reason or "browser capture was not requested")
        result = _run_node_sampler(ids, times, width, height)
        frames = _write_fallback_frames(result, output_dir)
        mode = "sampleCanvasMotion_raster_fallback"

    manifest = {
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "mode": mode,
        "pixel_parity_claim": False,
        "browser": {
            "available": probe.available,
            "engine": probe.engine,
            "executable": probe.executable,
            "reason": probe.reason,
        },
        "blockers": blockers,
        "width": width,
        "height": height,
        "sample_times": list(times),
        "preset_count": len(ids),
        "frames": frames,
        "ass_plans": _ass_manifest(ids),
        "notes": [
            "ASS plans are structural references only; they are not raster pixels.",
            "pixel_parity_claim remains false until Canvas and FFmpeg frames are compared.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def compare_capture_runs(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Compare deterministic frame/state output without claiming cross-renderer parity."""

    left_frames = {(item["preset_id"], item["normalized_time"]): item for item in left["frames"]}
    right_frames = {(item["preset_id"], item["normalized_time"]): item for item in right["frames"]}
    keys = sorted(set(left_frames) | set(right_frames))
    mismatches = []
    for key in keys:
        before = left_frames.get(key)
        after = right_frames.get(key)
        if before is None or after is None or before["sha256"] != after["sha256"] or before["state"] != after["state"]:
            mismatches.append(key)
    return {
        "same_mode": left.get("mode") == right.get("mode"),
        "frame_count": len(keys),
        "mismatches": mismatches,
        "deterministic": not mismatches and left.get("mode") == right.get("mode"),
    }


def temp_capture_dir(prefix: str = "motion-capture-") -> tempfile.TemporaryDirectory[str]:
    tmp_root = REPO_ROOT / ".tmp"
    tmp_root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(prefix=prefix, dir=tmp_root)
