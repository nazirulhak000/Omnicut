"""L5-02: an effect window longer than its media file must loop in the render.

The editor preview plays effect media on a looping <video> wrapped to the
timeline clock (frontend/src/lib/effectPlayback.js wrapEffectTime), and keeps
drawing it until the effect's own `end`. The render used to stop at the
media file's natural length, so a 3 s effect on a 1 s file showed for 1 s in
the export. This renders a real VideoEditor job in tmp_path and samples frames
past the file's length.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

import scripts.video_editor as video_editor_module
from scripts.video_editor import VideoEditor


def _run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")


def _wrap_effect_time(timeline_time, effect_start, media_duration):
    """Python mirror of effectPlayback.js wrapEffectTime (the preview's rule)."""
    elapsed = max(0.0, timeline_time - effect_start)
    return elapsed % media_duration


def _center_luma(frame_path):
    from PIL import Image

    image = Image.open(frame_path).convert("L")
    width, height = image.size
    # Effect centre: normX 0.5, normY 0.35 of the frame.
    cx, cy = int(width * 0.5), int(height * 0.35)
    box = image.crop((cx - 20, cy - 20, cx + 20, cy + 20))
    pixels = list(box.tobytes())
    return sum(pixels) / len(pixels)


@pytest.mark.render_regression
def test_effect_loops_past_its_media_length_like_the_preview(tmp_path, monkeypatch):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and FFprobe are required for the render regression fixture")

    effects_dir = tmp_path / "Effects"
    effects_dir.mkdir()
    effect_file = effects_dir / "fx_loop_probe.mov"
    source = tmp_path / "white.mp4"
    audio = tmp_path / "mix.wav"
    subtitles = tmp_path / "captions.ass"
    output = tmp_path / "render.mp4"
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")
    monkeypatch.setattr(video_editor_module, "EFFECTS_DIR", effects_dir)

    media_duration = 1.0
    # 1.0 s effect: black for the first half, white for the second. Multiply
    # blend over white footage leaves black only during the black half.
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i",
        "color=c=black:s=360x360:r=10:d=1.0,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='gte(t,0.5)'",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(effect_file),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=white:s=540x960:r=30:d=3.0",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3.0",
        "-c:a", "pcm_s16le", str(audio),
    ])
    subtitles.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,40,40,420,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n",
        encoding="utf-8",
    )

    # End at 2.6 so the 2.30 s sample is past the 0.2 s exit fade
    # (video_editor.overlay_anim_filters, same in the preview) and still
    # inside the looped black half.
    effect_start, effect_end = 0.2, 2.6
    result = VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source)],
        total_duration=3.0,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subtitles),
        output_mp4_path=str(output),
        clip_list=[{
            "source_path": str(source),
            "trim_start": 0.0,
            "trim_end": 3.0,
            "duration": 3.0,
        }],
        effects=[{
            "id": "loop-probe",
            "effectId": "fx_loop_probe",
            "start": effect_start,
            "end": effect_end,
            "normX": 0.5,
            "normY": 0.35,
            "scale": 1.0,
        }],
        export_preset="draft",
    )
    assert Path(result) == output.resolve()

    def expected_dark(t):
        if t < effect_start or t > effect_end:
            return False
        return _wrap_effect_time(t, effect_start, media_duration) < 0.5

    # 1.45 s and 2.30 s are past the 1.0 s media length: the preview shows the
    # looped black half there, so the render must too. 2.70 s is past `end`.
    samples = (0.45, 0.95, 1.45, 1.95, 2.30, 2.70)
    observed = {}
    for t in samples:
        frame = frames_dir / f"t_{int(t * 100):03d}.png"
        _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{t:.2f}", "-i", str(output), "-frames:v", "1", str(frame),
        ])
        observed[t] = _center_luma(frame)

    print(f"effect-loop centre luma by time: {observed}")
    for t in samples:
        luma = observed[t]
        if expected_dark(t):
            assert luma < 60, f"t={t}: preview shows the looped effect, render luma {luma:.0f} ({observed})"
        else:
            # Limited-range white multiplied by white lands near 200, not 255.
            assert luma > 150, f"t={t}: no effect expected, render luma {luma:.0f} ({observed})"
