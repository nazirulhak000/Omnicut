"""One-frame Canvas-vs-ASS comparison for the existing motion capture fixture.

The seam is deliberately opt-in and test-side only.  It refuses to compare a
wall-clock canvas capture: both sides must expose the same frame index,
timestamp, preset, text contract, and raster dimensions before any image
metric is calculated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Tuple
from urllib.parse import parse_qs, urlparse

from PIL import Image

from .app_capture import AppCaptureConfig, capture_app_canvas
from .ass_fixture import (
    ComparisonThresholds,
    FixtureSpec,
    compare_frames,
    render_ass_fixture,
)
from .capture import REPO_ROOT, temp_capture_dir


PAIR_SCHEMA_VERSION = 1
LIVE_FIXTURE_PATH = REPO_ROOT / "frontend" / "src" / "motionCaptureFixture.jsx"
LIVE_TEXT_LAYERS: Tuple[str, str] = (
    "Motion capture fixture",
    "SequencePlayer Canvas",
)
PAIR_TEXT = "\n".join(LIVE_TEXT_LAYERS)


class FramePairUnavailable(RuntimeError):
    """Raised when a deterministic live Canvas pair cannot be established."""


@dataclass(frozen=True)
class FramePairSpec:
    """Shared input contract for the live fixture and the ASS fixture."""

    preset_id: str = "hook.in.bounce"
    phase: str = "in"
    frame_index: int = 6
    timestamp_ms: int = 200
    fps: int = 30
    phase_window_ms: Tuple[int, int] = (0, 500)
    text: str = PAIR_TEXT
    ass_render_text: str = "Motion capture fixture\nSequencePlayer\nCanvas"
    background: str = "0x000000"
    font_name: str = "IBM Plex Sans Thai"
    font_size: int = 40
    bold: bool = True
    outline_px: int = 3


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _background_rgb(value: str) -> tuple[int, int, int]:
    raw = str(value).strip().lower()
    if raw.startswith("0x"):
        raw = raw[2:]
    if raw.startswith("#"):
        raw = raw[1:]
    if len(raw) != 6:
        raise ValueError(f"background must be RGB hex, got {value!r}")
    try:
        return tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"background must be RGB hex, got {value!r}") from exc


def _validate_spec(spec: FramePairSpec) -> None:
    if spec.phase not in {"in", "loop", "out"}:
        raise ValueError(f"unsupported phase: {spec.phase!r}")
    if spec.frame_index < 0 or spec.timestamp_ms < 0:
        raise ValueError("frame_index and timestamp_ms must be non-negative")
    if spec.fps <= 0:
        raise ValueError("fps must be positive")
    expected_timestamp = round(spec.frame_index * 1000 / spec.fps)
    if expected_timestamp != spec.timestamp_ms:
        raise ValueError(
            "frame_index/timestamp mismatch: "
            f"frame {spec.frame_index} at {spec.fps} FPS is {expected_timestamp} ms, "
            f"not {spec.timestamp_ms} ms"
        )
    window_start, window_end = spec.phase_window_ms
    if window_start < 0 or window_end <= window_start:
        raise ValueError("phase_window_ms must be an increasing non-negative range")
    if not window_start <= spec.timestamp_ms < window_end:
        raise ValueError("timestamp_ms must be inside phase_window_ms")
    if spec.text != PAIR_TEXT:
        raise ValueError("pair text must match the existing motion capture fixture")
    if spec.ass_render_text.replace("\n", " ") != PAIR_TEXT.replace("\n", " "):
        raise ValueError("ASS render text must contain the same logical text as the Canvas fixture")
    _background_rgb(spec.background)


def _phase_query_key(phase: str) -> str:
    return "loop" if phase == "loop" else phase


def _source_text_evidence() -> dict[str, Any]:
    if not LIVE_FIXTURE_PATH.exists():
        return {"status": "missing", "path": str(LIVE_FIXTURE_PATH)}
    source = LIVE_FIXTURE_PATH.read_text(encoding="utf-8")
    found = {text: f"text: '{text}'" in source for text in LIVE_TEXT_LAYERS}
    return {
        "status": "matched" if all(found.values()) else "mismatch",
        "path": str(LIVE_FIXTURE_PATH.relative_to(REPO_ROOT)),
        "layers": found,
    }


def _resolve_live_frame(manifest: Mapping[str, Any], spec: FramePairSpec) -> Mapping[str, Any]:
    if manifest.get("mode") != "app_canvas":
        raise FramePairUnavailable("live capture did not use app_canvas mode")
    frame = next((item for item in manifest.get("frames", []) if item.get("index") == spec.frame_index), None)
    if frame is None:
        raise FramePairUnavailable(f"live capture did not return frame index {spec.frame_index}")
    if frame.get("frameIndex") != spec.frame_index:
        raise FramePairUnavailable("live frame index was not returned by the deterministic seek hook")
    if frame.get("timestampMs") != spec.timestamp_ms:
        raise FramePairUnavailable(
            f"live timestamp is {frame.get('timestampMs')!r} ms, expected {spec.timestamp_ms} ms"
        )
    hook = frame.get("hook_metadata") or {}
    preset_ids = hook.get("presetIds") or {}
    if preset_ids.get(spec.phase) != spec.preset_id:
        raise FramePairUnavailable(
            f"live preset for phase {spec.phase!r} is {preset_ids.get(spec.phase)!r}, "
            f"expected {spec.preset_id!r}"
        )
    return frame


def _composite_canvas_frame(
    source_path: Path,
    output_path: Path,
    background: str,
) -> dict[str, Any]:
    with Image.open(source_path) as source:
        rgba = source.convert("RGBA")
        background_rgb = _background_rgb(background)
        canvas = Image.new("RGBA", rgba.size, (*background_rgb, 255))
        canvas.alpha_composite(rgba)
        canvas.convert("RGB").save(output_path, format="PNG", optimize=False)
        size = rgba.size
    return {"path": output_path.name, "sha256": _sha256(output_path), "size": list(size)}


def compare_live_frame_pair(
    config: AppCaptureConfig,
    spec: FramePairSpec = FramePairSpec(),
) -> dict[str, Any]:
    """Capture and compare one real SequencePlayer frame against ASS/libass."""

    _validate_spec(spec)
    parsed = urlparse(config.url)
    if not parsed.path.endswith("/motion_capture.html"):
        raise FramePairUnavailable(
            "deterministic P1-F pairing requires the existing frontend/motion_capture.html fixture"
        )
    query = parse_qs(parsed.query)
    query_key = _phase_query_key(spec.phase)
    if query.get(query_key, [None])[0] != spec.preset_id:
        raise FramePairUnavailable(
            f"URL query {query_key!r} must select {spec.preset_id!r} for the pair"
        )
    source_evidence = _source_text_evidence()
    if source_evidence["status"] != "matched":
        raise FramePairUnavailable("live fixture text source no longer matches the pair text")

    with temp_capture_dir("motion-frame-pair-") as temp_root:
        output_dir = Path(temp_root)
        live_dir = output_dir / "live"
        manifest = capture_app_canvas(
            AppCaptureConfig(
                **{
                    **asdict(config),
                    "output_dir": live_dir,
                    "frame_count": spec.frame_index + 1,
                }
            )
        )
        live_frame = _resolve_live_frame(manifest, spec)
        live_path = live_dir / str(live_frame["path"])
        canvas_path = output_dir / "canvas_composited.png"
        canvas_artifact = _composite_canvas_frame(live_path, canvas_path, spec.background)

        window_start, window_end = spec.phase_window_ms
        ass_spec = FixtureSpec(
            preset_id=spec.preset_id,
            role=spec.preset_id.split(".", 2)[0],
            phase=spec.phase,
            sample_ms=spec.timestamp_ms,
            width=int(live_frame["width"]),
            height=int(live_frame["height"]),
            fps=spec.fps,
            font_name=spec.font_name,
            text=spec.text,
            render_text=spec.ass_render_text,
            background=spec.background,
            base_position=(int(live_frame["width"]) // 2, int(live_frame["height"]) // 2),
            motion_window_ms=window_end - window_start,
            font_size=spec.font_size,
            bold=spec.bold,
            outline_px=spec.outline_px,
        )
        ass_paths = render_ass_fixture(ass_spec, output_dir / "ass")
        ass_metadata = json.loads(ass_paths["metadata"].read_text(encoding="utf-8"))
        ass_image = ass_paths["png"]
        comparison = compare_frames(canvas_path, ass_image, ComparisonThresholds())

        identity = {
            "timestamp_ms": {
                "canvas": live_frame.get("timestampMs"),
                "ass": ass_metadata["spec"]["sample_ms"],
                "match": live_frame.get("timestampMs") == ass_metadata["spec"]["sample_ms"],
            },
            "preset_id": {
                "canvas": (live_frame.get("hook_metadata") or {}).get("presetIds", {}).get(spec.phase),
                "ass": ass_metadata["contract_id"],
                "match": (live_frame.get("hook_metadata") or {}).get("presetIds", {}).get(spec.phase)
                == ass_metadata["contract_id"],
            },
            "text": {
                "canvas_source": list(LIVE_TEXT_LAYERS),
                "ass": spec.text.split("\n"),
                "match": source_evidence["status"] == "matched" and spec.text == PAIR_TEXT,
            },
            "dimensions": {
                "canvas": [live_frame.get("width"), live_frame.get("height")],
                "ass": [ass_metadata["spec"]["width"], ass_metadata["spec"]["height"]],
                "match": [live_frame.get("width"), live_frame.get("height")]
                == [ass_metadata["spec"]["width"], ass_metadata["spec"]["height"]],
            },
        }
        identity["all_match"] = all(item["match"] for item in identity.values())
        blockers = []
        if not comparison.passed:
            blockers.append(
                "real Canvas and FFmpeg/libass frames were paired, but the recorded "
                "cross-rasterizer thresholds did not pass"
            )
        result = {
            "schema_version": PAIR_SCHEMA_VERSION,
            "status": (
                "passed"
                if identity["all_match"] and comparison.passed
                else "blocked"
                if identity["all_match"]
                else "invalid_pair"
            ),
            "mode": "real_canvas_vs_ffmpeg_libass",
            "pixel_parity_claim": bool(identity["all_match"] and comparison.passed),
            "blockers": blockers,
            "pair_identity": identity,
            "source_text_evidence": source_evidence,
            "comparison": comparison.to_dict(),
            "live_capture": {
                "url": config.url,
                "selector": config.selector,
                "frame": dict(live_frame),
                "manifest_schema_version": manifest.get("schema_version"),
            },
            "ass_fixture": {
                "spec": asdict(ass_spec),
                "artifacts": {key: {"path": str(value.name), "sha256": _sha256(value)} for key, value in ass_paths.items()},
            },
            "canvas_artifact": canvas_artifact,
            "thresholds": asdict(ComparisonThresholds()),
            "notes": [
                "Canvas pixels came from SequencePlayer via HTMLCanvasElement.toDataURL().",
                "ASS pixels came from the existing motion contract and FFmpeg/libass fixture.",
                "The Canvas alpha channel was composited over the same black fixture background before comparison.",
                "Exact RGBA equality is diagnostic only; the acceptance gate uses the recorded structural metrics.",
            ],
        }
        (output_dir / "pair_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result


def default_pair_config(url: str, output_dir: Path) -> AppCaptureConfig:
    """Build the documented opt-in config without inventing a selector."""

    return AppCaptureConfig(
        url=url,
        selector="[data-testid='motion-capture-sequence-player'] canvas",
        ready_selector="[data-testid='motion-capture-sequence-player']",
        output_dir=output_dir,
        frame_count=FramePairSpec().frame_index + 1,
    )
