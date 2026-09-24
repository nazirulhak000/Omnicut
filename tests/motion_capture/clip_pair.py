"""Production SequencePlayer vs FFmpeg frame pairs for clip edits."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlencode, urlsplit, urlunsplit

from PIL import Image

from scripts.video_editor import VideoEditor
from tests.motion_capture.ass_fixture import ComparisonThresholds, compare_frames
from tests.motion_capture.app_capture import AppCaptureConfig, AppCaptureUnavailable, capture_app_canvas
from tests.motion_capture.frame_pair import _composite_canvas_frame
from tests.motion_capture.overlay_pair import create_empty_ass, create_silent_audio, vite_fs_url


FPS = 30


@dataclass(frozen=True)
class ClipPairResult:
    comparisons: tuple[dict, ...]
    live_contracts: tuple[dict, ...]
    rendered_video: Path
    output_dir: Path


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "command failed")


def _ffmpeg() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("FFmpeg is required for clip parity")
    return binary


def create_clip_source(output_dir: Path, *, landscape: bool = False, variant: int = 0) -> Path:
    """Create moving, high-contrast test footage in a temp directory."""

    width, height = (1920, 1080) if landscape else (1080, 1920)
    source = output_dir / f"clip_source_{variant}_{'landscape' if landscape else 'portrait'}.mp4"
    backgrounds = ("0x24445a", "0x4a243a", "0x264a30")
    background = backgrounds[variant % len(backgrounds)]
    _run([
        _ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c={background}:size={width}x{height}:rate={FPS}:duration=4",
        "-vf", (
            "drawbox=x=0:y=0:w=iw/2:h=ih:color=0x315f79:t=fill,"
            "drawbox=x=iw/2:y=0:w=iw/2:h=ih/2:color=0x8c4a63:t=fill,"
            "drawbox=x=iw/3:y=ih*2/3:w=iw/3:h=ih/4:color=0xd59b4a:t=fill,"
            "drawbox=x='mod(t*240,iw-220)':y='mod(t*130,ih-260)':w=220:h=260:color=white:t=fill"
        ),
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", str(source),
    ])
    return source


def _fixture_url(base_url: str, **params: str) -> str:
    parsed = urlsplit(base_url)
    return urlunsplit((parsed.scheme, parsed.netloc, "/motion_capture.html", urlencode(params), ""))


def _capture_frames(base_url: str, output_dir: Path, params: dict[str, str], frame_indices: tuple[int, ...]) -> tuple[list[Path], dict]:
    capture_dir = output_dir / "live"
    manifest = capture_app_canvas(AppCaptureConfig(
        url=_fixture_url(base_url, **params),
        selector="[data-testid='motion-capture-sequence-player'] canvas",
        ready_selector="[data-testid='motion-capture-sequence-player']",
        output_dir=capture_dir,
        frame_indices=frame_indices,
        fail_on_runtime_errors=False,
    ))
    if not manifest["runtime"]["clean"]:
        raise AppCaptureUnavailable(json.dumps(manifest["runtime"], ensure_ascii=False))
    frames = [capture_dir / str(entry["path"]) for entry in manifest["frames"]]
    return frames, manifest


def _render_frames(video: Path, output_dir: Path, sample_times: tuple[float, ...]) -> list[Path]:
    frames: list[Path] = []
    for index, sample_time in enumerate(sample_times):
        frame = output_dir / f"rendered_{index:02d}.png"
        _run([
            _ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(video), "-ss", f"{sample_time:.6f}", "-frames:v", "1",
            "-vf", "scale=540:960:flags=lanczos", "-pix_fmt", "rgb24", str(frame),
        ])
        frames.append(frame)
    return frames


def compare_clip_pair(
    *,
    base_url: str,
    output_dir: Path,
    sources: tuple[Path, ...],
    clip_configs: tuple[dict, ...],
    duration: float,
    sample_times: tuple[float, ...],
    transitions: tuple[dict | str, ...] = (),
    landscape: bool = False,
) -> ClipPairResult:
    """Capture the live canvas, render with VideoEditor and compare sampled frames."""

    output_dir.mkdir(parents=True, exist_ok=True)
    audio = create_silent_audio(output_dir)
    ass = create_empty_ass(output_dir)
    params: dict[str, str] = {
        "mode": "clip",
        "clip": vite_fs_url(base_url, sources[0]),
        "duration": str(duration),
        "clipConfig": json.dumps(clip_configs[0], separators=(",", ":")),
    }
    if len(sources) > 1:
        params["clip2"] = vite_fs_url(base_url, sources[1])
        params["clip2Config"] = json.dumps(clip_configs[1], separators=(",", ":"))

    frame_indices = tuple(round(time * FPS) for time in sample_times)
    live_frames, manifest = _capture_frames(base_url, output_dir, params, frame_indices)
    live_composited: list[Path] = []
    for index, live in enumerate(live_frames):
        composited = output_dir / f"live_composited_{index:02d}.png"
        _composite_canvas_frame(live, composited, "0x000000")
        live_composited.append(composited)

    clip_list = [
        {
            "source_path": str(source),
            "trim_start": 0.0,
            "trim_end": duration,
            "duration": duration,
            "zoom": 1.0,
            "pan_x": 0.0,
            "pan_y": 0.0,
            **config,
        }
        for source, config in zip(sources, clip_configs, strict=True)
    ]
    rendered_video = output_dir / "rendered.mp4"
    VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source) for source in sources],
        total_duration=duration,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(ass),
        output_mp4_path=str(rendered_video),
        clip_list=clip_list,
        transitions=list(transitions),
        export_preset="draft",
        style_preset="clean_tech_review",
    )
    rendered_frames = _render_frames(rendered_video, output_dir, sample_times)
    comparisons = tuple(
        compare_frames(live, rendered, ComparisonThresholds()).to_dict()
        for live, rendered in zip(live_composited, rendered_frames, strict=True)
    )
    hook = manifest["frames"][0].get("hook_metadata") or {}
    contracts = tuple(hook.get("clipContracts") or ())
    return ClipPairResult(comparisons, contracts, rendered_video, output_dir)
