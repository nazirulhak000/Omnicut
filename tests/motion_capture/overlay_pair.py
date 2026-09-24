"""Live Canvas vs production VideoEditor frame pairs for editor overlays.

These tests deliberately use a short deterministic source generated under
``.tmp``. The browser loads that same file through Vite's ``/@fs`` route and
the render side goes through ``VideoEditor.assemble_tiktok_video``. This keeps
the comparison on the real UI and real export consumers without polluting
``03_Projects`` or ``04_Exports``.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

from PIL import Image, ImageChops

from scripts.video_editor import VideoEditor
from tests.motion_capture.ass_fixture import ComparisonThresholds, compare_frames
from tests.motion_capture.app_capture import AppCaptureConfig, capture_app_canvas
from tests.motion_capture.capture import REPO_ROOT
from tests.motion_capture.frame_pair import _composite_canvas_frame


FPS = 30
DURATION = 2.0
SAMPLE_MS = 600
CANVAS_SIZE = (540, 960)


@dataclass(frozen=True)
class OverlayPairResult:
    feature: str
    comparison: dict
    delta_comparison: dict
    live_contract: dict
    render_contract: dict


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "command failed")


def _ffmpeg() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("FFmpeg is required for overlay parity")
    return binary


def create_overlay_source(output_dir: Path) -> Path:
    """Create a constant-colour portrait source with deterministic markers."""

    source = output_dir / "overlay_source.mp4"
    _run([
        _ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=0x24445a:s=1080x1920:r={FPS}:d={DURATION}",
        "-vf", (
            "drawbox=x=0:y=0:w=540:h=1920:color=0x315f79:t=fill,"
            "drawbox=x=600:y=440:w=360:h=360:color=0x8c4a63:t=fill,"
            "drawbox=x=180:y=1300:w=300:h=380:color=0xd59b4a:t=fill"
        ),
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    return source


def create_silent_audio(output_dir: Path) -> Path:
    audio = output_dir / "overlay_silence.wav"
    _run([
        _ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", str(DURATION), "-c:a", "pcm_s16le", str(audio),
    ])
    return audio


def create_empty_ass(output_dir: Path) -> Path:
    ass = output_dir / "overlay_empty.ass"
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8",
        newline="\n",
    )
    return ass


def vite_fs_url(base_url: str, path: Path) -> str:
    encoded = quote(str(path.resolve()).replace("\\", "/"), safe="/:~!$&'()*+,;=@")
    parsed = urlsplit(base_url)
    return f"{parsed.scheme}://{parsed.netloc}/@fs/{encoded}"


def _fixture_url(base_url: str, **params: str) -> str:
    return urlunsplit((
        urlsplit(base_url).scheme,
        urlsplit(base_url).netloc,
        "/motion_capture.html",
        urlencode(params),
        "",
    ))


def _capture(
    url: str,
    output_dir: Path,
    frame_index: int,
) -> tuple[Path, dict]:
    capture_dir = output_dir / "live"
    manifest = capture_app_canvas(AppCaptureConfig(
        url=url,
        selector="[data-testid='motion-capture-sequence-player'] canvas",
        ready_selector="[data-testid='motion-capture-sequence-player']",
        output_dir=capture_dir,
        frame_indices=(frame_index,),
    ))
    frame = manifest["frames"][0]
    return capture_dir / str(frame["path"]), manifest


def _render(
    output_dir: Path,
    source: Path,
    audio: Path,
    ass: Path,
    *,
    stickers: list[dict] | None = None,
    effects: list[dict] | None = None,
    spotlight: dict | None = None,
) -> Path:
    output = output_dir / "rendered.mp4"
    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source)],
        total_duration=DURATION,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(ass),
        output_mp4_path=str(output),
        clip_list=[{
            "source_path": str(source),
            "trim_start": 0.0,
            "trim_end": DURATION,
            "duration": DURATION,
            "zoom": 1.0,
            "pan_x": 0.0,
            "pan_y": 0.0,
        }],
        stickers=stickers,
        effects=effects,
        spotlight=spotlight,
        export_preset="draft",
        style_preset="clean_tech_review",
    )
    return output


def _extract_frame(video: Path, output_dir: Path) -> Path:
    frame = output_dir / "rendered_frame.png"
    _run([
        _ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video), "-ss", f"{SAMPLE_MS / 1000:.3f}",
        "-frames:v", "1", "-vf", "scale=540:960:flags=lanczos",
        "-pix_fmt", "rgb24", str(frame),
    ])
    return frame


def _overlay_delta(image: Path, baseline: Path, output: Path) -> None:
    with Image.open(image) as candidate, Image.open(baseline) as base:
        delta = ImageChops.difference(candidate.convert("RGB"), base.convert("RGB"))
        # compare_frames uses the top-left pixel as the background reference.
        # Keep that pixel neutral even when a full-frame spotlight dim is active.
        delta.putpixel((0, 0), (0, 0, 0))
        delta.save(output, format="PNG", optimize=False)


def _crop_frame(source: Path, output: Path, box: tuple[int, int, int, int]) -> None:
    with Image.open(source) as image:
        image.crop(box).save(output, format="PNG", optimize=False)


def _render_contract(feature: str, config: dict) -> dict:
    if feature == "sticker":
        return {
            "feature": feature,
            "start": 0.5,
            "end": DURATION,
            "normX": 0.72,
            "normY": 0.22,
            "scale": 1.0,
            "asset": config["asset"],
        }
    if feature == "effect":
        return {
            "feature": feature,
            "effectId": config["effect_id"],
            "start": 0.5,
            "end": DURATION,
            "normX": 0.52,
            "normY": 0.34,
            "scale": 1.0,
            "asset": config["asset"],
        }
    return {"feature": feature, **config["spotlight"]}


def compare_overlay_pair(
    *,
    base_url: str,
    output_dir: Path,
    feature: str,
    source: Path,
    audio: Path,
    ass: Path,
    asset: Path | None = None,
    spotlight: dict | None = None,
) -> OverlayPairResult:
    """Capture one overlay and its baseline, then compare both render paths."""

    frame_index = SAMPLE_MS * FPS // 1000
    asset_url = vite_fs_url(base_url, asset) if asset else ""
    params = {"mode": feature, "clip": vite_fs_url(base_url, source)}
    if feature == "sticker":
        params["sticker"] = asset_url
    elif feature == "effect":
        params.update({"effect": asset_url, "effectId": asset.stem})
    elif feature == "spotlight":
        params["spotlight"] = json.dumps(spotlight, separators=(",", ":"))

    live_url = _fixture_url(base_url, **params)
    live_path, live_manifest = _capture(live_url, output_dir, frame_index)
    live_composited = output_dir / "live_composited.png"
    _composite_canvas_frame(live_path, live_composited, "0x000000")

    baseline_url = _fixture_url(base_url, mode="baseline", clip=vite_fs_url(base_url, source))
    baseline_path, _ = _capture(baseline_url, output_dir / "baseline", frame_index)
    baseline_composited = output_dir / "baseline_composited.png"
    _composite_canvas_frame(baseline_path, baseline_composited, "0x000000")

    feature_payload: dict = {}
    if feature == "sticker":
        feature_payload["stickers"] = [{
            "id": "sticker-capture",
            "badge": str(asset),
            "start": 0.5,
            "end": DURATION,
            "norm_x": 0.72,
            "norm_y": 0.22,
            "scale": 1.0,
        }]
    elif feature == "effect":
        feature_payload["effects"] = [{
            "id": "effect-capture",
            "effectId": asset.stem if asset else "",
            "start": 0.5,
            "end": DURATION,
            "norm_x": 0.52,
            "norm_y": 0.34,
            "scale": 1.0,
        }]
    elif feature == "spotlight":
        feature_payload["spotlight"] = spotlight

    rendered = _render(output_dir / "render", source, audio, ass, **feature_payload)
    rendered_frame = _extract_frame(rendered, output_dir / "render")
    baseline_render = _render(output_dir / "baseline_render", source, audio, ass)
    baseline_render_frame = _extract_frame(baseline_render, output_dir / "baseline_render")

    if feature == "sticker":
        # The source clip is intentionally a real encoded video. Its crop and
        # colour pipeline can differ by a few pixels outside the overlay ROI
        # between Chromium and FFmpeg. The sticker itself has a fixed contract
        # box, so gate the actual visual consumer without letting unrelated
        # source-codec noise dominate the result.
        live_roi = output_dir / "live_sticker_roi.png"
        render_roi = output_dir / "render_sticker_roi.png"
        _crop_frame(live_composited, live_roi, (260, 80, 500, 340))
        _crop_frame(rendered_frame, render_roi, (260, 80, 500, 340))
        comparison = compare_frames(live_roi, render_roi, ComparisonThresholds())
    else:
        comparison = compare_frames(live_composited, rendered_frame, ComparisonThresholds())
    live_delta = output_dir / "live_delta.png"
    render_delta = output_dir / "render_delta.png"
    _overlay_delta(live_composited, baseline_composited, live_delta)
    _overlay_delta(rendered_frame, baseline_render_frame, render_delta)
    delta_comparison = compare_frames(live_delta, render_delta, ComparisonThresholds())

    hook = live_manifest["frames"][0].get("hook_metadata") or {}
    live_contract = (hook.get("overlayFeatureContract") or {}).get(feature)
    render_contract = _render_contract(feature, {
        "asset": str(asset) if asset else None,
        "effect_id": asset.stem if asset else None,
        "spotlight": spotlight,
    })
    return OverlayPairResult(
        feature=feature,
        comparison=comparison.to_dict(),
        delta_comparison=delta_comparison.to_dict(),
        live_contract=live_contract or {},
        render_contract=render_contract,
    )
