"""Black-box render checks kept separate from source-level parity probes."""

import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from scripts.video_editor import VideoEditor


def _run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")


@pytest.mark.render_regression
def test_short_synthetic_video_exports_at_30_fps(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and FFprobe are required for the render regression fixture")

    source = tmp_path / "source.mp4"
    audio = tmp_path / "mix.wav"
    subtitles = tmp_path / "captions.ass"
    output = tmp_path / "rendered.mp4"

    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=0x275DAD:s=540x960:r=30:d=0.8",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.8",
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
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:00.70,Default,,0,0,0,,Baseline\n",
        encoding="utf-8",
    )

    result = VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source)],
        total_duration=0.8,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subtitles),
        output_mp4_path=str(output),
        clip_list=[{
            "source_path": str(source),
            "trim_start": 0.0,
            "trim_end": 0.8,
            "duration": 0.8,
        }],
        export_preset="draft",
    )

    assert Path(result) == output.resolve()
    assert output.is_file() and output.stat().st_size > 0
    probe = json.loads(_run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate",
        "-of", "json", str(output),
    ]).stdout)["streams"][0]
    assert (probe["width"], probe["height"]) == (720, 1280)
    assert Fraction(probe["avg_frame_rate"]) == 30
