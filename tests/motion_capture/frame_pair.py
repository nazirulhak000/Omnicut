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
    compare_frames,
    render_caption_fixture,
    render_production_overlay_fixture,
    write_frame_diff_artifacts,
)
from .capture import REPO_ROOT
from scripts.subtitle.motion_contract import get_motion_preset


PAIR_SCHEMA_VERSION = 2
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
    text_layers: Tuple[str, ...] = LIVE_TEXT_LAYERS
    background: str = "0x000000"
    font_name: str = "IBM Plex Sans Thai"
    bold: bool = True
    outline_px: int = 3
    anchor: str = "top"
    x: float = 0.5
    y: float = 180.0 / 1920.0
    base_fs_ratio: float = 0.065
    comfortable_lines: int = 4


@dataclass(frozen=True)
class CaptionPairSpec:
    """Shared input contract for the live Caption fixture and ASS renderer."""

    text: str = "นั่งนิ่งจริงครับ"
    frame_index: int = 18
    timestamp_ms: int = 600
    fps: int = 30
    duration_ms: int = 2000
    background: str = "0x000000"
    font_name: str = "IBM Plex Sans Thai"
    caption_position: str = "bottom"


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
    if not 1 <= len(spec.text_layers) <= 3 or any(not str(line).strip() for line in spec.text_layers):
        raise ValueError("text_layers must contain one to three non-empty lines")
    _background_rgb(spec.background)


def _production_overlay(spec: FramePairSpec) -> dict[str, Any]:
    preset_ids = {
        "in": spec.preset_id if spec.phase == "in" else "hook.in.bounce",
        "loop": spec.preset_id if spec.phase == "loop" else "hook.loop.pulse",
        "out": spec.preset_id if spec.phase == "out" else "hook.out.fade",
    }
    contracts: dict[str, Mapping[str, Any]] = {}
    for phase, identifier in preset_ids.items():
        role, contract_phase, preset = identifier.split(".", 2)
        contract = get_motion_preset(role, contract_phase, preset)
        if contract is None:
            raise FramePairUnavailable(f"unknown production motion preset: {identifier}")
        contracts[phase] = contract
    return {
        "id": "motion-capture-overlay",
        "kind": "hook",
        "start": 0,
        "end": 2,
        "position": "top",
        "anchor": spec.anchor,
        "x": spec.x,
        "y": spec.y,
        "base_fs_ratio": spec.base_fs_ratio,
        "comfortable_lines": spec.comfortable_lines,
        "layer": 4,
        "look": {
            "font": spec.font_name,
            "color": "#FFFFFF",
            "accent_color": "#25F4EE",
            "outline_color": "#000000",
            "outline_px": spec.outline_px,
            "shadow": {"color": "#000000", "blur": 8, "dx": 0, "dy": 4},
            "bold": spec.bold,
        },
        "tiers": [
            {"text": text, "look": {"color": "#FFFFFF" if index == 0 else "#25F4EE"}}
            for index, text in enumerate(spec.text_layers)
        ],
        "anim": {"in": preset_ids["in"].split(".", 2)[2], "loop": preset_ids["loop"].split(".", 2)[2], "out": preset_ids["out"].split(".", 2)[2], "accent": "none", "stagger": False},
        "motion_contracts": contracts,
        "scrim": False,
        "hidden": False,
    }


def _expected_live_overlay_contract(spec: FramePairSpec) -> dict[str, Any]:
    return {
        "anchor": spec.anchor,
        "x": spec.x,
        "y": spec.y,
        "baseFsRatio": spec.base_fs_ratio,
        "comfortableLines": spec.comfortable_lines,
        "font": spec.font_name,
        "outlinePx": spec.outline_px,
        "bold": spec.bold,
        "tiers": [
            {"text": text, "color": "#FFFFFF" if index == 0 else "#25F4EE"}
            for index, text in enumerate(spec.text_layers)
        ],
    }


def _phase_query_key(phase: str) -> str:
    return "loop" if phase == "loop" else phase


def _source_text_evidence() -> dict[str, Any]:
    if not LIVE_FIXTURE_PATH.exists():
        return {"status": "missing", "path": str(LIVE_FIXTURE_PATH)}
    source = LIVE_FIXTURE_PATH.read_text(encoding="utf-8")
    found = {text: f"'{text}'" in source for text in LIVE_TEXT_LAYERS}
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
    if hook.get("fontReady") is not True:
        raise FramePairUnavailable("live fixture did not confirm the render-critical font was ready")
    preset_ids = hook.get("presetIds") or {}
    if preset_ids.get(spec.phase) != spec.preset_id:
        raise FramePairUnavailable(
            f"live preset for phase {spec.phase!r} is {preset_ids.get(spec.phase)!r}, "
            f"expected {spec.preset_id!r}"
        )
    return frame


def _resolve_live_caption_frame(manifest: Mapping[str, Any], spec: CaptionPairSpec) -> Mapping[str, Any]:
    if manifest.get("mode") != "app_canvas":
        raise FramePairUnavailable("caption capture did not use app_canvas mode")
    frame = next((item for item in manifest.get("frames", []) if item.get("index") == spec.frame_index), None)
    if frame is None:
        raise FramePairUnavailable(f"caption capture did not return frame index {spec.frame_index}")
    if frame.get("frameIndex") != spec.frame_index or frame.get("timestampMs") != spec.timestamp_ms:
        raise FramePairUnavailable("caption capture returned a non-deterministic frame identity")
    hook = frame.get("hook_metadata") or {}
    if hook.get("mode") != "caption":
        raise FramePairUnavailable("live fixture did not confirm caption mode")
    if hook.get("fontReady") is not True:
        raise FramePairUnavailable("caption fixture did not confirm the render-critical font was ready")
    contract = hook.get("captionContract") or {}
    expected = {
        "text": spec.text,
        "position": spec.caption_position,
        "font": spec.font_name,
        "bilingual": False,
    }
    if contract != expected:
        raise FramePairUnavailable(f"caption contract mismatch: {contract!r} != {expected!r}")
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
    query_lines = tuple(query.get("line", []))
    if query_lines and query_lines != spec.text_layers:
        raise FramePairUnavailable("URL line parameters must match the frame-pair text layers")
    if not query_lines and spec.text_layers != LIVE_TEXT_LAYERS:
        raise FramePairUnavailable("non-default frame-pair text requires repeated URL line parameters")
    source_evidence = _source_text_evidence()
    if spec.text_layers == LIVE_TEXT_LAYERS and source_evidence["status"] != "matched":
        raise FramePairUnavailable("live fixture text source no longer matches the pair text")

    output_dir = config.output_dir.resolve()
    allowed_root = (REPO_ROOT / ".tmp").resolve()
    if not output_dir.is_relative_to(allowed_root):
        raise ValueError(f"frame pair output must be under {allowed_root}")
    output_dir.mkdir(parents=True, exist_ok=True)
    live_dir = output_dir / "live"
    manifest = capture_app_canvas(
        AppCaptureConfig(
            **{
                **asdict(config),
                "output_dir": live_dir,
                "frame_count": 1,
                "frame_indices": (spec.frame_index,),
            }
        )
    )
    live_frame = _resolve_live_frame(manifest, spec)
    live_path = live_dir / str(live_frame["path"])
    canvas_path = output_dir / "canvas_composited.png"
    canvas_artifact = _composite_canvas_frame(live_path, canvas_path, spec.background)

    production_overlay = _production_overlay(spec)
    ass_paths = render_production_overlay_fixture(
            production_overlay,
            sample_ms=spec.timestamp_ms,
            width=int(live_frame["width"]),
            height=int(live_frame["height"]),
            fps=spec.fps,
            background=spec.background,
            output_dir=output_dir / "ass",
    )
    ass_metadata = json.loads(ass_paths["metadata"].read_text(encoding="utf-8"))
    ass_image = ass_paths["png"]
    comparison = compare_frames(canvas_path, ass_image, ComparisonThresholds())
    diff_artifacts = write_frame_diff_artifacts(canvas_path, ass_image, output_dir / "diff")

    identity = {
            "timestamp_ms": {
                "canvas": live_frame.get("timestampMs"),
                "ass": ass_metadata["sample_ms"],
                "match": live_frame.get("timestampMs") == ass_metadata["sample_ms"],
            },
            "preset_id": {
                "canvas": (live_frame.get("hook_metadata") or {}).get("presetIds", {}).get(spec.phase),
                "ass": production_overlay["motion_contracts"][spec.phase]["id"],
                "match": (live_frame.get("hook_metadata") or {}).get("presetIds", {}).get(spec.phase)
                == production_overlay["motion_contracts"][spec.phase]["id"],
            },
            "text": {
                "canvas_source": [
                    item.get("text")
                    for item in ((live_frame.get("hook_metadata") or {}).get("overlayContract") or {}).get("tiers", [])
                ],
                "ass": list(spec.text_layers),
                "match": [
                    item.get("text")
                    for item in ((live_frame.get("hook_metadata") or {}).get("overlayContract") or {}).get("tiers", [])
                ] == list(spec.text_layers),
            },
            "dimensions": {
                "canvas": [live_frame.get("width"), live_frame.get("height")],
                "ass": ass_metadata["canvas_size"],
                "match": [live_frame.get("width"), live_frame.get("height")]
                == ass_metadata["canvas_size"],
            },
            "layout_contract": {
                "canvas": (live_frame.get("hook_metadata") or {}).get("overlayContract"),
                "ass": _expected_live_overlay_contract(spec),
                "match": (live_frame.get("hook_metadata") or {}).get("overlayContract")
                == _expected_live_overlay_contract(spec),
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
            "diff_artifacts": diff_artifacts,
            "runtime": manifest["runtime"],
            "live_capture": {
                "url": config.url,
                "selector": config.selector,
                "frame": dict(live_frame),
                "manifest_schema_version": manifest.get("schema_version"),
            },
            "ass_fixture": {
                "spec": ass_metadata,
                "artifacts": {key: {"path": str(value.name), "sha256": _sha256(value)} for key, value in ass_paths.items()},
            },
            "canvas_artifact": canvas_artifact,
            "thresholds": asdict(ComparisonThresholds()),
            "notes": [
                "Canvas pixels came from SequencePlayer via HTMLCanvasElement.toDataURL().",
                "ASS pixels came from SubtitleEngine, overlay_events, and FFmpeg/libass at export resolution.",
                "The export frame was downsampled once to the fixed SequencePlayer canvas dimensions.",
                "The Canvas alpha channel was composited over the same black fixture background before comparison.",
                "Exact RGBA equality is diagnostic only; the acceptance gate uses the recorded structural metrics.",
            ],
    }
    (output_dir / "pair_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def compare_live_caption_pair(
    config: AppCaptureConfig,
    spec: CaptionPairSpec = CaptionPairSpec(),
) -> dict[str, Any]:
    """Capture one real caption frame and compare it with production ASS/libass."""

    if not spec.text.strip():
        raise ValueError("caption text must not be empty")
    if spec.frame_index < 0 or spec.timestamp_ms < 0:
        raise ValueError("caption frame identity must be non-negative")
    if round(spec.frame_index * 1000 / spec.fps) != spec.timestamp_ms:
        raise ValueError("caption frame_index/timestamp mismatch")
    if spec.timestamp_ms >= spec.duration_ms:
        raise ValueError("caption sample must be inside the caption duration")
    parsed = urlparse(config.url)
    if not parsed.path.endswith("/motion_capture.html"):
        raise FramePairUnavailable("caption pairing requires the motion capture fixture")
    query = parse_qs(parsed.query)
    if query.get("mode", [None])[0] != "caption":
        raise FramePairUnavailable("caption pairing requires mode=caption")
    if query.get("caption", [spec.text])[0] != spec.text:
        raise FramePairUnavailable("caption query must match the pair text")

    output_dir = config.output_dir.resolve()
    allowed_root = (REPO_ROOT / ".tmp").resolve()
    if not output_dir.is_relative_to(allowed_root):
        raise ValueError(f"caption pair output must be under {allowed_root}")
    live_dir = output_dir / "live"
    manifest = capture_app_canvas(
        AppCaptureConfig(
            **{
                **asdict(config),
                "output_dir": live_dir,
                "frame_count": 1,
                "frame_indices": (spec.frame_index,),
            }
        )
    )
    live_frame = _resolve_live_caption_frame(manifest, spec)
    live_path = live_dir / str(live_frame["path"])
    canvas_path = output_dir / "canvas_composited.png"
    canvas_artifact = _composite_canvas_frame(live_path, canvas_path, spec.background)
    cues = [{
        "id": "caption-capture-cue",
        "start": 0,
        "end": spec.duration_ms / 1000,
        "text": spec.text,
        "bilingual": False,
        "position": spec.caption_position,
    }]
    ass_paths = render_caption_fixture(
        cues,
        sample_ms=spec.timestamp_ms,
        width=int(live_frame["width"]),
        height=int(live_frame["height"]),
        fps=spec.fps,
        background=spec.background,
        output_dir=output_dir / "ass",
        font_name=spec.font_name,
        caption_position=spec.caption_position,
    )
    ass_metadata = json.loads(ass_paths["metadata"].read_text(encoding="utf-8"))
    comparison = compare_frames(canvas_path, ass_paths["png"], ComparisonThresholds())
    diff_artifacts = write_frame_diff_artifacts(canvas_path, ass_paths["png"], output_dir / "diff")
    contract = (live_frame.get("hook_metadata") or {}).get("captionContract")
    identity = {
        "timestamp_ms": {
            "canvas": live_frame.get("timestampMs"),
            "ass": ass_metadata["sample_ms"],
            "match": live_frame.get("timestampMs") == ass_metadata["sample_ms"],
        },
        "caption_contract": {
            "canvas": contract,
            "ass": {"text": spec.text, "position": spec.caption_position, "font": spec.font_name, "bilingual": False},
            "match": contract == {"text": spec.text, "position": spec.caption_position, "font": spec.font_name, "bilingual": False},
        },
        "dimensions": {
            "canvas": [live_frame.get("width"), live_frame.get("height")],
            "ass": ass_metadata["canvas_size"],
            "match": [live_frame.get("width"), live_frame.get("height")] == ass_metadata["canvas_size"],
        },
    }
    identity["all_match"] = all(item["match"] for item in identity.values())
    result = {
        "schema_version": PAIR_SCHEMA_VERSION,
        "status": "passed" if identity["all_match"] and comparison.passed else "blocked" if identity["all_match"] else "invalid_pair",
        "mode": "real_canvas_vs_ffmpeg_libass_caption",
        "pixel_parity_claim": bool(identity["all_match"] and comparison.passed),
        "blockers": [] if comparison.passed else ["caption Canvas and FFmpeg/libass thresholds did not pass"],
        "pair_identity": identity,
        "comparison": comparison.to_dict(),
        "diff_artifacts": diff_artifacts,
        "runtime": manifest["runtime"],
        "live_capture": {"url": config.url, "selector": config.selector, "frame": dict(live_frame)},
        "ass_fixture": {"spec": ass_metadata, "artifacts": {key: {"path": str(value.name), "sha256": _sha256(value)} for key, value in ass_paths.items()}},
        "canvas_artifact": canvas_artifact,
        "thresholds": asdict(ComparisonThresholds()),
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
        frame_count=1,
        frame_indices=(FramePairSpec().frame_index,),
    )
