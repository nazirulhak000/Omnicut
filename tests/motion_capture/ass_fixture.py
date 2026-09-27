"""ASS/libass fixture seam for Canvas-vs-ASS motion parity work.

This module intentionally owns no production rendering code.  It consumes the
existing declarative motion catalog and ASS adapter, renders into a caller
provided temporary directory, and records enough metadata to reproduce the
frame.  A fixture is not a Canvas parity result until a real Canvas capture is
provided to :func:`compare_frames`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, Mapping, Optional, Tuple

from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat

from scripts.subtitle.motion_ass_adapter import build_ass_motion_segments
from scripts.subtitle.motion_contract import get_motion_preset
from scripts.subtitle.translation_service import ass_escape_text
from scripts.subtitle_engine import SubtitleEngine


FRAME_WIDTH = 1080
FRAME_HEIGHT = 1920
FRAME_RATE = 30
DEFAULT_FONT = "Kanit"
DEFAULT_TEXT = "\u0e17\u0e14\u0e2a\u0e2d\u0e1a Motion"
DEFAULT_BACKGROUND = "0x101827"
DEFAULT_BASE_POSITION = (540, 760)


@dataclass(frozen=True)
class FixtureSpec:
    preset_id: str
    role: str
    phase: str
    sample_ms: int
    width: int = FRAME_WIDTH
    height: int = FRAME_HEIGHT
    fps: int = FRAME_RATE
    font_name: str = DEFAULT_FONT
    text: str = DEFAULT_TEXT
    render_text: Optional[str] = None
    background: str = DEFAULT_BACKGROUND
    base_position: Tuple[int, int] = DEFAULT_BASE_POSITION
    motion_window_ms: Optional[int] = None
    font_size: int = 72
    bold: bool = False
    outline_px: int = 4


@dataclass(frozen=True)
class ComparisonThresholds:
    """Cross-rasterizer acceptance limits, not exact pixel equality.

    Canvas and libass use different text rasterizers.  Exact RGBA equality is
    therefore diagnostic only; structural mask geometry is the acceptance
    gate.  These defaults are deliberately conservative for a 1080x1920
    overlay and must be calibrated with real Canvas captures before promotion.
    """

    mask_iou_min: float = 0.90
    mask_tolerance_px: int = 7
    bbox_edge_delta_px_max: int = 6
    centroid_delta_px_max: float = 4.0
    mean_abs_error_max: float = 0.08


@dataclass(frozen=True)
class FrameComparison:
    width: int
    height: int
    mean_abs_error: float
    raw_mask_iou: Optional[float]
    mask_iou: Optional[float]
    bbox_edge_delta_px: Optional[int]
    centroid_delta_px: Optional[float]
    passed: bool
    exact_pixel_match: bool
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _split_preset(identifier: str) -> Tuple[str, str, str]:
    parts = identifier.strip().split(".")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    raise ValueError("preset_id must use role.phase.preset form, e.g. hook.in.snap")


def _safe_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if "04_exports" in {part.casefold() for part in resolved.parts}:
        raise ValueError("motion fixtures must never be written under 04_Exports")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _ffmpeg_path(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    return value.replace(":", r"\:").replace("'", r"\'")


def _ass_time(seconds: float) -> str:
    total_cs = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(total_cs, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _fixture_ass_header(spec: FixtureSpec) -> str:
    return "\n".join(
        [
            "[Script Info]",
            "; OmniCutMotionFixture: ass-libass-v1",
            "ScriptType: v4.00+",
            f"PlayResX: {spec.width}",
            f"PlayResY: {spec.height}",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Fixture,{spec.font_name},{spec.font_size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,{int(spec.bold)},0,0,0,100,100,0,0,1,{spec.outline_px},2,5,0,0,0,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )


def build_ass_fixture(spec: FixtureSpec) -> Tuple[str, Dict[str, Any]]:
    contract = get_motion_preset(spec.role, spec.phase, spec.preset_id.split(".")[-1])
    if contract is None:
        raise ValueError(f"unknown motion preset: {spec.role}.{spec.phase}.{spec.preset_id}")

    duration_ms = (
        max(1, int(spec.motion_window_ms))
        if spec.motion_window_ms is not None
        else max(1000, int(round(float(contract.get("duration_ms", 0)))) + 200)
    )
    sample_ms = max(0, min(int(spec.sample_ms), duration_ms - 1))
    plan = build_ass_motion_segments(
        contract,
        start_ms=0,
        end_ms=duration_ms,
        base_position=spec.base_position,
        unsupported="report",
    )
    position_tag = "" if (r"\pos(" in plan.ass or r"\move(" in plan.ass) else f"\\pos({spec.base_position[0]},{spec.base_position[1]})"
    text = ass_escape_text(spec.render_text if spec.render_text is not None else spec.text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", r"\N")
    event = (
        f"Dialogue: 0,{_ass_time(0)},{_ass_time(duration_ms / 1000)},Fixture,,0,0,0,,"
        f"{{\\an5{position_tag}{plan.ass}}}{text}"
    )
    ass_text = _fixture_ass_header(spec) + "\n" + event + "\n"
    metadata = {
        "fixture_schema": "ass-libass-motion-v1",
        "renderer": "ffmpeg/libass",
        "pixel_diff_status": "not_compared",
        "canvas_capture_required": True,
        "spec": {**asdict(spec), "sample_ms": sample_ms},
        "contract_id": contract["id"],
        "ass_plan": plan.to_dict(),
        "comparison": {
            "mode": "cross-rasterizer-structural",
            "exact_pixel_match_is_diagnostic_only": True,
            "thresholds": asdict(ComparisonThresholds()),
            "caveats": [
                "Canvas and libass may use different glyph rasterizers and antialiasing.",
                "Golden acceptance requires a real Canvas frame at the same size and timestamp.",
                "Unsupported ASS tracks remain visible in ass_plan.unsupported and are not silently approximated.",
            ],
        },
    }
    return ass_text, metadata


def render_ass_fixture(spec: FixtureSpec, output_dir: Path) -> Dict[str, Path]:
    """Write ASS, one PNG frame, and metadata under a safe temp directory."""

    output_dir = _safe_output_dir(output_dir)
    ass_text, metadata = build_ass_fixture(spec)
    stem = spec.preset_id.replace(".", "_")
    ass_path = output_dir / f"{stem}_{spec.sample_ms:04d}ms.ass"
    png_path = output_dir / f"{stem}_{spec.sample_ms:04d}ms.png"
    metadata_path = output_dir / f"{stem}_{spec.sample_ms:04d}ms.json"
    ass_path.write_text(ass_text, encoding="utf-8", newline="\n")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render an ASS fixture")
    project_root = Path(__file__).resolve().parents[2]
    fonts_dir = project_root / "02_Assets" / "Fonts"
    subtitle_filter = f"subtitles='{_ffmpeg_path(ass_path)}':fontsdir='{_ffmpeg_path(fonts_dir)}'"
    duration_sec = max(1.0, (max(spec.sample_ms, 0) + 100) / 1000)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c={spec.background}:s={spec.width}x{spec.height}:r={spec.fps}:d={duration_sec:.3f}",
        "-vf",
        subtitle_filter,
        "-ss",
        f"{max(spec.sample_ms, 0) / 1000:.3f}",
        "-frames:v",
        "1",
        "-pix_fmt",
        "rgb24",
        str(png_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg fixture render failed: {completed.stderr.strip()}")

    metadata.update(
        {
            "command": command,
            "ffmpeg_version": _ffmpeg_version(ffmpeg),
            "artifacts": {
                "ass": {"path": ass_path.name, "sha256": _sha256(ass_path)},
                "png": {"path": png_path.name, "sha256": _sha256(png_path)},
            },
        }
    )
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return {"ass": ass_path, "png": png_path, "metadata": metadata_path}


def render_production_overlay_fixture(
    overlay: Mapping[str, Any],
    *,
    sample_ms: int,
    width: int,
    height: int,
    fps: int,
    background: str,
    output_dir: Path,
) -> Dict[str, Path]:
    """Render a real editor overlay through the production ASS writer.

    ``SequencePlayer`` owns a half-resolution 540x960 canvas while exports are
    1080x1920.  Rendering ASS directly at canvas size changes both libass font
    metrics and outline thickness, so this fixture renders at export scale and
    downsamples the completed frame exactly once for the comparison.
    """

    output_dir = _safe_output_dir(output_dir)
    render_width = int(width) * 2
    render_height = int(height) * 2
    ass_path = output_dir / "production_overlay.ass"
    png_path = output_dir / f"production_overlay_{int(sample_ms):04d}ms.png"
    metadata_path = output_dir / f"production_overlay_{int(sample_ms):04d}ms.json"
    font_name = str((overlay.get("look") or {}).get("font") or DEFAULT_FONT)
    SubtitleEngine.generate_ass(
        [],
        str(ass_path),
        font_name=font_name,
        overlays=[dict(overlay)],
        bilingual=False,
        video_width=render_width,
        video_height=render_height,
        show_watermark=False,
    )

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render a production overlay fixture")
    project_root = Path(__file__).resolve().parents[2]
    fonts_dir = project_root / "02_Assets" / "Fonts"
    subtitle_filter = f"subtitles='{_ffmpeg_path(ass_path)}':fontsdir='{_ffmpeg_path(fonts_dir)}'"
    scale_filter = f"scale={int(width)}:{int(height)}:flags=lanczos"
    duration_sec = max(1.0, (max(int(sample_ms), 0) + 100) / 1000)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c={background}:s={render_width}x{render_height}:r={int(fps)}:d={duration_sec:.3f}",
        "-vf",
        f"{subtitle_filter},{scale_filter}",
        "-ss",
        f"{max(int(sample_ms), 0) / 1000:.3f}",
        "-frames:v",
        "1",
        "-pix_fmt",
        "rgb24",
        str(png_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(f"Production overlay fixture render failed: {completed.stderr.strip()}")

    metadata = {
        "fixture_schema": "production-overlay-motion-v1",
        "renderer": "subtitle_engine/overlay_events + ffmpeg/libass",
        "sample_ms": int(sample_ms),
        "canvas_size": [int(width), int(height)],
        "render_size": [render_width, render_height],
        "fps": int(fps),
        "background": background,
        "overlay": dict(overlay),
        "command": command,
        "ffmpeg_version": _ffmpeg_version(ffmpeg),
        "artifacts": {
            "ass": {"path": ass_path.name, "sha256": _sha256(ass_path)},
            "png": {"path": png_path.name, "sha256": _sha256(png_path)},
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"ass": ass_path, "png": png_path, "metadata": metadata_path}


def render_caption_fixture(
    cues: list[dict[str, Any]],
    *,
    sample_ms: int,
    width: int,
    height: int,
    fps: int,
    background: str,
    output_dir: Path,
    font_name: str = "IBM Plex Sans Thai",
    caption_position: str = "bottom",
) -> Dict[str, Path]:
    """Render production captions at export scale, then match Canvas size."""

    output_dir = _safe_output_dir(output_dir)
    render_width = int(width) * 2
    render_height = int(height) * 2
    ass_path = output_dir / "production_caption.ass"
    png_path = output_dir / f"production_caption_{int(sample_ms):04d}ms.png"
    metadata_path = output_dir / f"production_caption_{int(sample_ms):04d}ms.json"
    source_cues = [dict(cue) for cue in cues]
    expanded_cues: list[dict[str, Any]] = []
    for cue in source_cues:
        lines = str(cue.get("text") or "").replace("\\N", "\n").splitlines()
        if len(lines) <= 1:
            expanded_cues.append({**cue, "auto_emoji": False})
            continue
        canvas_font_size = max(14, round(int(width) * 0.0463))
        anchor_y = int(height) * (1 - 420 / 1920)
        block_top = anchor_y - len(lines) * canvas_font_size
        for index, line in enumerate(lines):
            line_center = block_top + (index + 0.5) * canvas_font_size
            expanded_cues.append({
                **cue,
                "text": line,
                "y": line_center / int(height),
                "auto_emoji": False,
            })
    SubtitleEngine.generate_ass(
        expanded_cues,
        str(ass_path),
        font_name=font_name,
        bilingual=False,
        # This fixture compares the ASS against a Canvas frame captured ahead of
        # time, from a browser session that knows nothing about Progressive
        # Ghost Reveal. Leaving the reveal on would compare a half-revealed line
        # against a fully-drawn one -- a fixture mismatch, not a parity failure.
        # The reveal's own preview/render parity is covered by
        # test_ghost_reveal_detaches_stacked_marks_per_word and the constants in
        # test_preview_render_parity.py.
        ghost_reveal=False,
        video_width=render_width,
        video_height=render_height,
        caption_position=caption_position,
        show_watermark=False,
    )

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to render a production caption fixture")
    project_root = Path(__file__).resolve().parents[2]
    fonts_dir = project_root / "02_Assets" / "Fonts"
    subtitle_filter = f"subtitles='{_ffmpeg_path(ass_path)}':fontsdir='{_ffmpeg_path(fonts_dir)}'"
    scale_filter = f"scale={int(width)}:{int(height)}:flags=lanczos"
    duration_sec = max(1.0, (max(int(sample_ms), 0) + 100) / 1000)
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c={background}:s={render_width}x{render_height}:r={int(fps)}:d={duration_sec:.3f}",
        "-vf",
        f"{subtitle_filter},{scale_filter}",
        "-ss",
        f"{max(int(sample_ms), 0) / 1000:.3f}",
        "-frames:v",
        "1",
        "-pix_fmt",
        "rgb24",
        str(png_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(f"Production caption fixture render failed: {completed.stderr.strip()}")

    metadata = {
        "fixture_schema": "production-caption-v1",
        "renderer": "SubtitleEngine + FFmpeg/libass",
        "sample_ms": int(sample_ms),
        "canvas_size": [int(width), int(height)],
        "render_size": [render_width, render_height],
        "fps": int(fps),
        "background": background,
        "font_name": font_name,
        "caption_position": caption_position,
        "cues": source_cues,
        "command": command,
        "ffmpeg_version": _ffmpeg_version(ffmpeg),
        "artifacts": {
            "ass": {"path": ass_path.name, "sha256": _sha256(ass_path)},
            "png": {"path": png_path.name, "sha256": _sha256(png_path)},
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"ass": ass_path, "png": png_path, "metadata": metadata_path}


def _ffmpeg_version(binary: str) -> str:
    result = subprocess.run([binary, "-version"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    return result.stdout.splitlines()[0] if result.stdout else "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _foreground_mask(image: Image.Image, background: Optional[Tuple[int, int, int]] = None, tolerance: int = 8) -> Image.Image:
    rgb = image.convert("RGB")
    bg = background or rgb.getpixel((0, 0))
    difference = ImageChops.difference(rgb, Image.new("RGB", rgb.size, bg))
    red, green, blue = difference.split()
    strongest_channel = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    threshold = max(0, min(255, int(tolerance)))
    return strongest_channel.point(lambda value: 255 if value > threshold else 0)


def _bbox_center(bbox: Optional[Tuple[int, int, int, int]]) -> Optional[Tuple[float, float]]:
    if bbox is None:
        return None
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _mask_iou(reference_mask: Image.Image, candidate_mask: Image.Image) -> float:
    intersection = ImageChops.darker(reference_mask, candidate_mask).histogram()[255]
    union = ImageChops.lighter(reference_mask, candidate_mask).histogram()[255]
    return intersection / union if union else 1.0


def _tolerant_mask(mask: Image.Image, tolerance_px: int) -> Image.Image:
    radius = max(0, int(tolerance_px))
    if radius == 0:
        return mask
    return mask.filter(ImageFilter.MaxFilter(radius * 2 + 1))


def compare_frames(reference_path: Path, candidate_path: Path, thresholds: ComparisonThresholds = ComparisonThresholds()) -> FrameComparison:
    """Compare two frames with exact diagnostics plus tolerant geometry gates."""

    with Image.open(reference_path) as reference_image, Image.open(candidate_path) as candidate_image:
        reference = reference_image.convert("RGB")
        candidate = candidate_image.convert("RGB")
        if reference.size != candidate.size:
            raise ValueError(f"frame sizes differ: {reference.size} != {candidate.size}")
        diff = ImageChops.difference(reference, candidate)
        mean_abs_error = sum(ImageStat.Stat(diff).mean) / (3 * 255.0)
        exact = not diff.getbbox()
        reference_mask = _foreground_mask(reference)
        candidate_mask = _foreground_mask(candidate)
        ref_bbox = reference_mask.getbbox()
        cand_bbox = candidate_mask.getbbox()
        if ref_bbox is None or cand_bbox is None:
            return FrameComparison(
                width=reference.width,
                height=reference.height,
                mean_abs_error=mean_abs_error,
                raw_mask_iou=None,
                mask_iou=None,
                bbox_edge_delta_px=None,
                centroid_delta_px=None,
                passed=exact,
                exact_pixel_match=exact,
                reason="one frame has no foreground mask",
            )

        raw_mask_iou = _mask_iou(reference_mask, candidate_mask)
        mask_iou = _mask_iou(
            _tolerant_mask(reference_mask, thresholds.mask_tolerance_px),
            _tolerant_mask(candidate_mask, thresholds.mask_tolerance_px),
        )
        edge_delta = max(abs(ref_bbox[index] - cand_bbox[index]) for index in range(4))
        ref_center = _bbox_center(ref_bbox)
        cand_center = _bbox_center(cand_bbox)
        centroid_delta = max(abs(ref_center[index] - cand_center[index]) for index in range(2))
        passed = (
            mask_iou >= thresholds.mask_iou_min
            and edge_delta <= thresholds.bbox_edge_delta_px_max
            and centroid_delta <= thresholds.centroid_delta_px_max
            and mean_abs_error <= thresholds.mean_abs_error_max
        )
        return FrameComparison(
            width=reference.width,
            height=reference.height,
            mean_abs_error=mean_abs_error,
            raw_mask_iou=raw_mask_iou,
            mask_iou=mask_iou,
            bbox_edge_delta_px=edge_delta,
            centroid_delta_px=centroid_delta,
            passed=passed,
            exact_pixel_match=exact,
        )


def write_frame_diff_artifacts(
    reference_path: Path,
    candidate_path: Path,
    output_dir: Path,
) -> Dict[str, Dict[str, Any]]:
    """Write inspectable diff images for one comparison under a safe directory."""

    output_dir = _safe_output_dir(output_dir)
    with Image.open(reference_path) as reference_image, Image.open(candidate_path) as candidate_image:
        reference = reference_image.convert("RGB")
        candidate = candidate_image.convert("RGB")
        if reference.size != candidate.size:
            raise ValueError(f"frame sizes differ: {reference.size} != {candidate.size}")
        absolute_diff = ImageChops.difference(reference, candidate)
        luminance = ImageOps.grayscale(absolute_diff)
        amplified = luminance.point(lambda value: min(255, value * 4))
        heatmap = ImageOps.colorize(amplified, black="#000000", mid="#FF5500", white="#FFFFFF")
        artifacts = {
            "absolute_diff": ("absolute_diff.png", absolute_diff),
            "heatmap": ("heatmap.png", heatmap),
            "reference_mask": ("reference_mask.png", _foreground_mask(reference)),
            "candidate_mask": ("candidate_mask.png", _foreground_mask(candidate)),
        }
        result: Dict[str, Dict[str, Any]] = {}
        for key, (filename, image) in artifacts.items():
            path = output_dir / filename
            image.save(path, format="PNG", optimize=False)
            result[key] = {
                "path": filename,
                "sha256": _sha256(path),
                "size": list(image.size),
            }
        return result


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Render a deterministic ASS/libass motion fixture into .tmp")
    parser.add_argument("--preset", default="hook.in.snap")
    parser.add_argument("--sample-ms", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path(".tmp") / "motion_capture")
    args = parser.parse_args()
    role, phase, preset = _split_preset(args.preset)
    contract = get_motion_preset(role, phase, preset)
    if contract is None:
        parser.error(f"unknown preset: {args.preset}")
    default_sample = max(1, int(round(float(contract.get("duration_ms", 500)) / 2)))
    spec = FixtureSpec(args.preset, role, phase, args.sample_ms if args.sample_ms is not None else default_sample)
    paths = render_ass_fixture(spec, args.output_dir)
    print(json.dumps({key: str(value) for key, value in paths.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
