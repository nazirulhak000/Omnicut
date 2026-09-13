"""Regression tests for the optional video-editor SpotlightV1 composition."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.video_editor import VideoEditor, _append_spotlight_filter


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")


def _enabled_spotlight() -> dict:
    return {
        "schema_version": 1,
        "enabled": True,
        "shape": "ellipse",
        "focus": {"x": 0.5, "y": 0.5, "width": 0.42, "height": 0.40},
        "dim_opacity": 0.4,
        "feather": 0.02,
        "corner_radius": 0.08,
    }


@pytest.mark.parametrize("value", [None, {"enabled": False}])
def test_disabled_spotlight_is_a_graph_noop(value):
    graph: list[str] = []

    result = _append_spotlight_filter(graph, "[v_composed]", value)

    assert result == "[v_composed]"
    assert graph == []


def test_enabled_spotlight_re_roots_and_namespaces_filter_labels():
    graph: list[str] = []

    result = _append_spotlight_filter(graph, "[v_graded]", _enabled_spotlight())
    fragment = "".join(graph)

    assert result.startswith("[spotlight_")
    assert len(graph) == 1
    assert "[v_graded]split=2" in fragment
    assert "[0:v]" not in fragment
    assert "[spotlight_0_spot_src]" in fragment
    assert result in fragment
    assert "colorchannelmixer" in fragment
    assert "overlay=0:0" in fragment
    assert "rembg" not in fragment.lower()
    assert "onnx" not in fragment.lower()


def test_spotlight_matches_preview_layer_order_in_video_editor():
    source = Path(__file__).resolve().parents[1] / "scripts" / "video_editor.py"
    editor = source.read_text(encoding="utf-8")

    assemble_start = editor.index("def assemble_tiktok_video")
    spotlight_call = editor.index("current_v = _append_spotlight_filter", assemble_start)
    assert editor.index("lut3d=", assemble_start) < spotlight_call
    assert spotlight_call < editor.index("sticker_scaled", spotlight_call)
    assert spotlight_call < editor.index("subtitles=", spotlight_call)


@pytest.mark.render_regression
def test_assemble_spotlight_keeps_focus_bright_across_multiple_frames(tmp_path, monkeypatch):
    """The enabled graph must dim outside the focus without touching audio."""

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and FFprobe are required for the render regression fixture")

    source = tmp_path / "spotlight_source.mp4"
    audio = tmp_path / "spotlight_audio.wav"
    subtitles = tmp_path / "spotlight_subtitles.ass"
    output = tmp_path / "spotlight_render.mp4"
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")

    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=white:s=540x960:r=30:d=1.2",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1.2",
        "-c:a", "pcm_s16le", str(audio),
    ])
    subtitles.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8",
    )

    result = VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source)],
        total_duration=1.2,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subtitles),
        output_mp4_path=str(output),
        clip_list=[{
            "source_path": str(source),
            "trim_start": 0.0,
            "trim_end": 1.2,
            "duration": 1.2,
        }],
        spotlight=_enabled_spotlight(),
        export_preset="draft",
    )

    assert Path(result) == output.resolve()
    assert output.is_file() and output.stat().st_size > 0

    from PIL import Image

    for label, timestamp in (("in", "0.10"), ("hold", "0.60"), ("out", "1.00")):
        frame_path = frames_dir / f"{label}.png"
        _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", timestamp, "-i", str(output), "-frames:v", "1", str(frame_path),
        ])
        image = Image.open(frame_path).convert("RGB")
        center = sum(image.getpixel((360, 640))) / 3
        corner = sum(image.getpixel((20, 20))) / 3
        assert center > corner + 35, f"{label} frame lost the bright focus window"
