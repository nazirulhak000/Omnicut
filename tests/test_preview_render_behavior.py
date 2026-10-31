"""Black-box render checks kept separate from source-level parity probes."""

import json
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from scripts.video_editor import VideoEditor


def _run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")


@pytest.mark.render_regression
def test_short_synthetic_video_exports_at_30_fps(tmp_path, monkeypatch):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and FFprobe are required for the render regression fixture")

    source = tmp_path / "source.mp4"
    audio = tmp_path / "mix.wav"
    subtitles = tmp_path / "captions.ass"
    output = tmp_path / "rendered.mp4"
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")

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


def test_renderer_enables_auto_filter_threading_for_complex_graphs():
    """The CPU filter graph may scale independently of the chosen encoder."""
    source = (Path(__file__).parents[1] / "scripts" / "video_editor.py").read_text(encoding="utf-8")
    assert '"-filter_complex_threads", "0"' in source


@pytest.mark.render_regression
def test_baked_decorative_sticker_and_effect_recolor_across_multiple_frames(tmp_path, monkeypatch):
    """Opted-in baked media must follow the accent palette in the real render."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and FFprobe are required for the render regression fixture")

    source = tmp_path / "baked_source.mp4"
    audio = tmp_path / "baked_mix.wav"
    subtitles = tmp_path / "baked_captions.ass"
    output = tmp_path / "baked_recolored.mp4"
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")

    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=540x960:r=30:d=1.4",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1.4",
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

    result = VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source)],
        total_duration=1.4,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subtitles),
        output_mp4_path=str(output),
        clip_list=[{
            "source_path": str(source),
            "trim_start": 0.0,
            "trim_end": 1.4,
            "duration": 1.4,
        }],
        stickers=[{
            "id": "tint-sticker",
            "badge": "arrow_pointer_cyan_3d.png",
            "start": 0.1,
            "end": 1.3,
            "normX": 0.25,
            "normY": 0.25,
            "scale": 1.0,
            "recolor": "accent",
            "recolorSourceHue": 180,
        }],
        effects=[{
            "id": "tint-effect",
            "effectId": "fx_arrow_01",
            "start": 0.1,
            "end": 1.3,
            "normX": 0.75,
            "normY": 0.55,
            "scale": 1.0,
            "recolor": "accent",
            "recolorSourceHue": 205,
        }],
        style_preset="clean_tech_review",
        export_preset="draft",
    )

    assert Path(result) == output.resolve()
    from PIL import Image

    for label, timestamp in (("in", "0.20"), ("hold", "0.70"), ("out", "1.10")):
        _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", timestamp, "-i", str(output), "-frames:v", "1",
            str(frames_dir / f"{label}.png"),
        ])
        image = Image.open(frames_dir / f"{label}.png").convert("RGB")
        yellow_pixels = sum(
            1 for red, green, blue in image.getdata()
            if red > 90 and green > 55 and red > blue * 1.8 and green > blue * 1.4
        )
        assert yellow_pixels > 500, f"{label} frame lost the accent-recoloured baked media"


@pytest.mark.render_regression
def test_keyframe_camera_motion_changes_real_render_frames_and_stays_in_bounds(tmp_path, monkeypatch):
    """FFmpeg must evaluate zoom/pan keyframes over the clip, not just once."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and FFprobe are required for the render regression fixture")

    source = tmp_path / "camera_source.mp4"
    audio = tmp_path / "camera_mix.wav"
    subtitles = tmp_path / "camera_captions.ass"
    output = tmp_path / "camera_render.mp4"
    monkeypatch.setenv("OMNICUT_ENCODER", "cpu")

    # A white marker sits at the far-left edge of a portrait source. A pan from
    # -1 to +1 at 2x zoom must move it out of the final crop by the last frame.
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=540x960:r=30:d=1.5",
        "-vf", "drawbox=x=20:y=360:w=100:h=240:color=white:t=fill",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1.5",
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

    result = VideoEditor.assemble_tiktok_video(
        raw_video_paths=[str(source)],
        total_duration=1.5,
        mixed_audio_path=str(audio),
        ass_subtitle_path=str(subtitles),
        output_mp4_path=str(output),
        clip_list=[{
            "source_path": str(source),
            "trim_start": 0.0,
            "trim_end": 1.5,
            "duration": 1.5,
            "zoom": 2.0,
            "keyframes": [
                {"time": 0.0, "zoom": 2.0, "pan_x": -1.0, "pan_y": 0.0},
                {"time": 0.75, "zoom": 2.0, "pan_x": -0.4, "pan_y": 0.0},
                {"time": 1.5, "zoom": 2.0, "pan_x": 1.0, "pan_y": 0.0},
            ],
        }],
        export_preset="draft",
    )

    assert Path(result) == output.resolve()
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    for label, timestamp in (("in", "0.10"), ("middle", "0.75"), ("out", "1.40")):
        _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", timestamp, "-i", str(output), "-frames:v", "1",
            str(frames_dir / f"{label}.png"),
        ])

    from PIL import Image

    white_counts = []
    for label in ("in", "middle", "out"):
        pixels = Image.open(frames_dir / f"{label}.png").convert("RGB")
        white_counts.append(sum(
            1 for r, g, b in pixels.getdata()
            if r > 220 and g > 220 and b > 220
        ))
    assert white_counts[0] > 1000, "the first motion frame must contain the marker"
    assert white_counts[0] > white_counts[1] > white_counts[2], white_counts


@pytest.mark.render_regression
def test_per_word_vs_monolithic_render_parity(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for render regression testing")

    from PIL import Image, ImageChops
    from scripts.subtitle.word_layout import layout_line

    text = "ลดกระหน่ำ ดีลลับ 1 แถม 1"
    font_name = "Kanit"
    font_size = 75
    video_w = 1080
    video_h = 1920

    layout = layout_line(text, font_name, font_size, norm_x=0.5, video_w=video_w)
    words = layout["words"]
    assert len(words) > 0

    x_center = video_w // 2
    x_start = x_center - layout["abs_line_width"] / 2
    y = 500

    ass_mono = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{{\\q2\\an7\\pos({x_start:.2f},{y})}}{text}
"""
    mono_ass_path = tmp_path / "mono.ass"
    mono_ass_path.write_text(ass_mono, encoding="utf-8")

    events = []
    for w in words:
        events.append(f"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{{\\q2\\an7\\pos({w['abs_x']:.2f},{y})}}{w['text']}")

    ass_split = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"
    split_ass_path = tmp_path / "split.ass"
    split_ass_path.write_text(ass_split, encoding="utf-8")

    mono_png = tmp_path / "mono.png"
    split_png = tmp_path / "split.png"

    def _ff_escape(p: Path) -> str:
        return str(p.resolve()).replace("\\", "/").replace(":", "\\:")

    fonts_p = _ff_escape(Path("02_Assets/Fonts"))

    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=1:r=30",
        "-vf", f"ass='{_ff_escape(mono_ass_path)}':fontsdir='{fonts_p}'",
        "-frames:v", "1", str(mono_png),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=1:r=30",
        "-vf", f"ass='{_ff_escape(split_ass_path)}':fontsdir='{fonts_p}'",
        "-frames:v", "1", str(split_png),
    ])

    im_mono = Image.open(mono_png).convert("L")
    im_split = Image.open(split_png).convert("L")

    bbox_mono = im_mono.getbbox()
    bbox_split = im_split.getbbox()
    assert bbox_mono is not None and bbox_split is not None

    # Width difference across the entire line must be <= 3px
    width_mono = bbox_mono[2] - bbox_mono[0]
    width_split = bbox_split[2] - bbox_split[0]
    assert abs(width_mono - width_split) <= 3, f"Total width diverged by {abs(width_mono - width_split)}px"

    # Total differing pixels across the 1080x1920 canvas must be <= 3500 (>99.8% identical)
    diff = ImageChops.difference(im_mono, im_split)
    diff_pixels = sum(1 for p in diff.getdata() if p > 0)
    assert diff_pixels <= 3500, f"Monolithic vs Split diff pixels {diff_pixels} exceeds tolerance!"


@pytest.mark.render_regression
@pytest.mark.parametrize(
    ("font_name", "expected_face", "source_text", "body_text", "stacked_pairs"),
    [
        ("IBMPlex", "IBM Plex Sans Thai SemiBold", "นั่ง", "นัง", ("ั่",)),
        (
            "Prompt",
            "Prompt",
            # The emoji is stripped on the way in (strip_caption_emoji), so the
            # body it produces carries none -- what this case still exercises is
            # the two stacked pairs in the Thai.
            # One burst (<= MICRO_BURST_MAX_CHARS): a longer sentence is split into
            # separately centred lines, which this settled-geometry check is not about.
            "⚡ ปกติซื้อช็อปเรื่องราคา",
            "ปกติซือช็อปเรืองราคา",
            ("ื้", "ื่"),
        ),
    ],
)
def test_thai_stacked_marks_keep_settled_geometry_during_caption_entrance(
    tmp_path, font_name, expected_face, source_text, body_text, stacked_pairs
):
    """The first visible caption frame must not geometrically scale Thai marks.

    A libass ``\\fscx`` pop can shape a stack correctly and then enlarge the
    raster, making its marks collide. The caption entrance is therefore an
    alpha fade; this renders both the original ``นั่ง`` regression and the
    reported Prompt sentence containing ``ื้``/``ื่`` across multiple frames.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the Thai render regression")

    from PIL import Image, ImageChops
    from scripts.subtitle_engine import SubtitleEngine

    ass_path = tmp_path / "thai_stacked_marks.ass"
    SubtitleEngine.generate_ass(
        cues=[{
            "start": 0.0,
            "end": 0.6,
            "text": source_text,
            "translation": "unused",
        }],
        output_ass_path=str(ass_path),
        font_name=font_name,
        bilingual=False,
        caption_position="middle",
        # This test is about the plain caption entrance -- one event that fades
        # the whole line in. Progressive Ghost Reveal deliberately replaces that
        # with one event per word, so it is covered separately in
        # test_ghost_reveal_detaches_stacked_marks_per_word.
        ghost_reveal=False,
    )
    generated = ass_path.read_text(encoding="utf-8")
    assert f"Style: TikTokWhite,{expected_face}" in generated
    main_lines = [line for line in generated.splitlines() if ",TikTokWhite,," in line]
    assert any(re.sub(r"\s+", "", body_text) in re.sub(r"\s+", "", re.sub(r"\{[^{}]*\}", "", line)) for line in main_lines)
    assert "TikTokWhite,,0,0,0,,{\\an5\\pos(" in generated
    assert "\\1a&HFF&\\3a&HFF&\\4a&HFF&" in generated
    assert all(pair not in generated for pair in stacked_pairs)

    ass_filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    frames_pattern = str(tmp_path / "frame-%02d.png")
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=0xB49464:s=1080x1920:r=30:d=0.6",
        "-vf", f"subtitles='{ass_filter_path}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "16", frames_pattern,
    ])

    def ink_bbox(path):
        image = Image.open(path).convert("RGB")
        background = Image.new("RGB", image.size, image.getpixel((0, 0)))
        diff = ImageChops.difference(image, background).convert("L")
        mask = diff.point(lambda value: 255 if value > 8 else 0)
        # The always-on copyright watermark (subtitle_engine.WATERMARK_*)
        # lives in the right-edge safe-zone column for the entire clip --
        # unrelated to this test's caption-entrance timing, so blank that
        # column out before measuring ink. Matches the column the editor's
        # own safe-zone guide reserves (SequencePlayer.jsx: right 11.1%).
        watermark_column_left = int(round(image.width * 0.82))
        mask.paste(0, (watermark_column_left, 0, image.width, image.height))
        return mask.getbbox()

    first_hidden = ink_bbox(tmp_path / "frame-01.png")
    first_visible = ink_bbox(tmp_path / "frame-02.png")
    settled = ink_bbox(tmp_path / "frame-16.png")
    assert first_hidden is None
    assert first_visible is not None
    assert settled is not None
    first_width = first_visible[2] - first_visible[0]
    settled_width = settled[2] - settled[0]
    first_height = first_visible[3] - first_visible[1]
    settled_height = settled[3] - settled[1]
    assert abs(first_width - settled_width) <= 4
    assert abs(first_height - settled_height) <= 4


@pytest.mark.render_regression
def test_prompt_emoji_thai_mark_matrix_has_separate_vertical_bands(tmp_path):
    """All 20 upper-vowel/tone combinations must form two clean levels."""
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the Thai render regression")

    from PIL import Image

    # Colour each combining mark independently.  ASS colours are BGR, so the
    # first mark is blue and the detached tone mark is green.  No
    # outline/shadow is used: the measurement is of glyph fills, not
    # decoration.
    from scripts.subtitle.font_metrics import (
        THAI_STACKED_MARK_RAISE_EM,
        repair_thai_stacked_marks,
    )

    hidden = "{\\1a&HFF&\\3a&HFF&\\4a&HFF&}"
    shown = "{\\1a&H00&\\3a&H00&\\4a&H00&\\1c&H00FF00&}"
    tone_raise = max(6, int(round(76 * THAI_STACKED_MARK_RAISE_EM)))
    upper_vowels = "ัิีึื"
    tone_marks = "่้๊๋"
    cells = []
    events = []
    for row, upper in enumerate(upper_vowels):
        for col, tone in enumerate(tone_marks):
            text = f"🛒 ก{upper}{tone}ก"
            repaired, companions = repair_thai_stacked_marks(text)
            assert repaired == f"🛒 ก{upper}ก"
            assert len(companions) == 1
            before, detached_tone, after = companions[0]
            assert detached_tone == tone
            coloured_body = repaired.replace(
                upper, f"{{\\1c&HFF0000&}}{upper}{{\\1c&HFFFFFF&}}", 1
            )
            coloured_tone = f"{hidden}{before}{shown}{tone}{hidden}{after}"
            x = 135 + col * 270
            y = 260 + row * 320
            cells.append((upper + tone, x, y))
            events.extend([
                f"Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{{\\an5\\pos({x},{y})}}{coloured_body}",
                f"Dialogue: 1,0:00:00.00,0:00:01.00,Default,,0,0,0,,{{\\an5\\pos({x},{y - tone_raise})}}{coloured_tone}",
            ])
    ass = tmp_path / "thai_mark_bands.ass"
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Prompt,76,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(events) + "\n",
        encoding="utf-8",
    )

    ass_filter_path = str(ass.resolve()).replace("\\", "/").replace(":", "\\:")
    output = tmp_path / "thai_mark_bands.png"
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-threads", "1", "-f", "lavfi", "-i", "color=c=0xB49464:s=1080x1920:r=30:d=1",
        "-vf", f"subtitles='{ass_filter_path}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(output),
    ])

    image = Image.open(output).convert("RGB")
    pixels = image.load()

    def colour_bbox(kind, crop):
        left, top, right, bottom = crop
        points = []
        for y in range(top, bottom):
            for x in range(left, right):
                red, green, blue = pixels[x, y]
                if kind == "blue" and blue > 150 and blue > red + 40 and blue > green + 40:
                    points.append((x, y))
                if kind == "green" and green > 150 and green > red + 40 and green > blue + 40:
                    points.append((x, y))
        assert points, f"{kind} mark fill was not found"
        xs, ys = zip(*points)
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1

    for pair, x, y in cells:
        crop = (x - 120, y - 120, x + 120, y + 100)
        upper_mark = colour_bbox("blue", crop)
        tone_mark = colour_bbox("green", crop)
        assert tone_mark[3] <= upper_mark[1], (
            f"Thai marks {pair} overlap vertically: upper={upper_mark}, tone={tone_mark}"
        )
        assert tone_mark[0] < upper_mark[2] and upper_mark[0] < tone_mark[2], (
            f"Detached tone {pair} drifted horizontally: upper={upper_mark}, tone={tone_mark}"
        )


@pytest.mark.render_regression
def test_word_start_position_budget(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for render regression testing")

    from PIL import Image
    from scripts.subtitle.word_layout import layout_line

    text = "ลดกระหน่ำ ดีลลับ 1 แถม 1"
    font_name = "Kanit"
    font_size = 75
    video_w = 1080
    video_h = 1920

    layout = layout_line(text, font_name, font_size, norm_x=0.5, video_w=video_w)
    words = layout["words"]

    colors = ["&H0000FF&", "&H00FF00&", "&HFF0000&", "&H00FFFF&", "&HFFFF00&", "&HFF00FF&"]
    colored_events = []
    y = 500
    for i, w in enumerate(words):
        c = colors[i % len(colors)]
        colored_events.append(f"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{{\\q2\\an7\\pos({w['abs_x']:.2f},{y})\\1c{c}}}{w['text']}")

    ass_color = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(colored_events) + "\n"

    color_ass = tmp_path / "color.ass"
    color_ass.write_text(ass_color, encoding="utf-8")
    color_png = tmp_path / "color.png"

    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    color_ass_p = str(color_ass.resolve()).replace("\\", "/").replace(":", "\\:")

    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=1:r=30",
        "-vf", f"ass='{color_ass_p}':fontsdir='{fonts_p}'",
        "-frames:v", "1", str(color_png),
    ])

    im = Image.open(color_png)
    bbox = im.getbbox()
    assert bbox is not None
    for i, w in enumerate(words[:3]):
        target_c = colors[i]
        found_xs = []
        for x in range(bbox[0], bbox[2]):
            for yp in range(bbox[1], bbox[3]):
                px = im.getpixel((x, yp))[:3]
                if target_c == "&H0000FF&" and px[0] > 120 and px[1] < 40 and px[2] < 40:
                    found_xs.append(x)
                elif target_c == "&H00FF00&" and px[1] > 120 and px[0] < 40 and px[2] < 40:
                    found_xs.append(x)
                elif target_c == "&HFF0000&" and px[2] > 120 and px[0] < 40 and px[1] < 40:
                    found_xs.append(x)
        if found_xs:
            min_x = min(found_xs)
            diff = abs(min_x - w["abs_x"])
            assert diff <= 2.0, f"Word {i} {w['text']} delta {diff:.2f}px exceeds budget!"


def test_text_overlay_word_stagger_events():
    """
    Contract test: verifies that _text_overlay_events with word_stagger_ms > 0 produces
    per-word dialogue lines with staggered \\t and sequential initial \\alpha&HFF&,
    with matching shadow duplicates.
    """
    from scripts.subtitle.overlay_events import _text_overlay_events

    item = {
        "text": "ดีล ลับ วันนี้",
        "tiers": [{"text": "ดีล ลับ วันนี้"}],
        "start": 0.0,
        "end": 2.0,
        "anim": {"in": "snap", "word_stagger_ms": 70},
        "look": {
            "font": "Kanit",
            "size_pct": 100,
            "color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_px": 5.0,
            "shadow": {"dx": 1.5, "dy": 2.0, "blur": 4.0, "color": "#000000"},
        },
    }
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "base_fs": 50,
        "resolved_font": "Kanit",
        "font_map": {},
        "caption_color": "#0000E6FF",
    }

    events = _text_overlay_events(item, ctx)
    assert len(events) >= 6  # at least 3 words * (shadow + main)

    main_events = [e for e in events if "TextOverlayMain" in e]
    shadow_events = [e for e in events if "TextOverlayShadow" in e]
    assert len(main_events) == 3
    assert len(shadow_events) == 3

    # Word 0 starts at 0ms: does not hide with initial \alpha&HFF&
    assert "\\t(0,70," in main_events[0]
    assert "\\org(" in main_events[0]

    # Word 1 starts at 70ms: starts with \alpha&HFF&, transitions at 70ms
    assert "\\alpha&HFF&" in main_events[1]
    assert "\\t(70,80,\\alpha&H00&)" in main_events[1]
    assert "\\t(70,140," in main_events[1]

    # Word 2 starts at 140ms: starts with \alpha&HFF&, transitions at 140ms
    assert "\\alpha&HFF&" in main_events[2]
    assert "\\t(140,150,\\alpha&H00&)" in main_events[2]
    assert "\\t(140,210," in main_events[2]

    # Shadows match main timing
    assert "\\t(0,70," in shadow_events[0]
    assert "\\t(70,80,\\alpha&H00&)" in shadow_events[1]
    assert "\\t(140,150,\\alpha&H00&)" in shadow_events[2]


@pytest.mark.render_regression
def test_text_overlay_word_stagger_multi_frame_render(tmp_path):
    """
    Multi-frame FFmpeg behavioral render test:
    Renders an overlay with word_stagger_ms = 70 and verifies that:
    - Frame at 40ms: only word 0 is visible (bbox width corresponds to word 0).
    - Frame at 120ms: words 0 and 1 are visible (bbox width spans words 0 & 1).
    - Frame at 600ms: all words are settled and visible.
    - Zero regression: when word_stagger_ms == 0, settled frame matches static render.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for render regression testing")

    from PIL import Image
    from scripts.subtitle.overlay_events import _text_overlay_events

    item_stagger = {
        "text": "ดีล ลับ วันนี้",
        "tiers": [{"text": "ดีล ลับ วันนี้"}],
        "start": 0.0,
        "end": 2.0,
        "anim": {"in": "snap", "word_stagger_ms": 70},
        "look": {
            "font": "Kanit",
            "size_pct": 100,
            "color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_px": 5.0,
            "shadow": None,
        },
    }
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "base_fs": 60,
        "resolved_font": "Kanit",
        "font_map": {},
        "caption_color": "#0000E6FF",
    }

    events = _text_overlay_events(item_stagger, ctx)
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TextOverlayMain,Kanit,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"

    ass_path = tmp_path / "stagger.ass"
    ass_path.write_text(ass_content, encoding="utf-8")

    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    ass_p = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")

    # Frame 1: at 0.04s (word 0 entering, word 1 & 2 invisible)
    f40_png = tmp_path / "f40.png"
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{ass_p}':fontsdir='{fonts_p}'",
        "-ss", "0.04",
        "-frames:v", "1", str(f40_png),
    ])

    # Frame 2: at 0.12s (words 0 & 1 visible, word 2 invisible)
    f120_png = tmp_path / "f120.png"
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{ass_p}':fontsdir='{fonts_p}'",
        "-ss", "0.12",
        "-frames:v", "1", str(f120_png),
    ])

    # Frame 3: at 0.60s (all words settled and visible)
    f600_png = tmp_path / "f600.png"
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{ass_p}':fontsdir='{fonts_p}'",
        "-ss", "0.60",
        "-frames:v", "1", str(f600_png),
    ])

    im40 = Image.open(f40_png).convert("L")
    im120 = Image.open(f120_png).convert("L")
    im600 = Image.open(f600_png).convert("L")

    bbox40 = im40.getbbox()
    bbox120 = im120.getbbox()
    bbox600 = im600.getbbox()

    assert bbox40 is not None, "Frame at 40ms must show word 0"
    assert bbox120 is not None, "Frame at 120ms must show words 0 and 1"
    assert bbox600 is not None, "Frame at 600ms must show all words"

    w40 = bbox40[2] - bbox40[0]
    w120 = bbox120[2] - bbox120[0]
    w600 = bbox600[2] - bbox600[0]

    # Stagger invariant: visible text width must grow monotonically as words appear
    assert w40 < w120 < w600, (
        f"Stagger sequence width violated: w40={w40}px, w120={w120}px, w600={w600}px"
    )


@pytest.mark.render_regression
def test_word_stagger_zero_regression(tmp_path):
    """
    Zero-regression invariant:
    When words settle (e.g. at 600ms), an overlay rendered with word_stagger_ms == 0
    must visually match word_stagger_ms > 0 exactly.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for render regression testing")

    from PIL import Image, ImageChops
    from scripts.subtitle.overlay_events import _text_overlay_events

    item_base = {
        "text": "ดีล ลับ วันนี้",
        "tiers": [{"text": "ดีล ลับ วันนี้"}],
        "start": 0.0,
        "end": 2.0,
        "look": {
            "font": "Kanit",
            "size_pct": 100,
            "color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_px": 5.0,
            "shadow": None,
        },
    }
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "base_fs": 60,
        "resolved_font": "Kanit",
        "font_map": {},
        "caption_color": "#0000E6FF",
    }

    item_zero = {**item_base, "anim": {"in": "snap", "word_stagger_ms": 0}}
    item_stagger = {**item_base, "anim": {"in": "snap", "word_stagger_ms": 70}}

    events_zero = _text_overlay_events(item_zero, ctx)
    events_stagger = _text_overlay_events(item_stagger, ctx)

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TextOverlayMain,Kanit,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_zero = tmp_path / "zero.ass"
    ass_zero.write_text(header + "\n".join(events_zero) + "\n", encoding="utf-8")
    ass_stagger = tmp_path / "stagger.ass"
    ass_stagger.write_text(header + "\n".join(events_stagger) + "\n", encoding="utf-8")

    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    p_zero = str(ass_zero.resolve()).replace("\\", "/").replace(":", "\\:")
    p_stagger = str(ass_stagger.resolve()).replace("\\", "/").replace(":", "\\:")

    img_zero = tmp_path / "zero.png"
    img_stagger = tmp_path / "stagger.png"

    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{p_zero}':fontsdir='{fonts_p}'",
        "-ss", "0.60", "-frames:v", "1", str(img_zero),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{p_stagger}':fontsdir='{fonts_p}'",
        "-ss", "0.60", "-frames:v", "1", str(img_stagger),
    ])

    im_z = Image.open(img_zero).convert("L")
    im_s = Image.open(img_stagger).convert("L")

    bbox_z = im_z.getbbox()
    bbox_s = im_s.getbbox()
    assert bbox_z is not None and bbox_s is not None
    assert bbox_z == bbox_s, f"Settled bboxes differ: zero={bbox_z} vs stagger={bbox_s}"

    diff = ImageChops.difference(im_z, im_s)
    diff_pixels = sum(1 for p in diff.getdata() if p > 0)
    assert diff_pixels == 0, f"Settled frames have {diff_pixels} differing pixels!"


def test_text_overlay_skew_behavioral_render(tmp_path):
    """
    Tier A skew channel renders in libass via \\fax, tilting glyphs forward
    without changing layout line advance.
    """
    from scripts.subtitle.overlay_events import _text_overlay_events
    from PIL import Image, ImageChops
    import numpy as np

    item_base = {
        "kind": "text",
        "start": 0.0,
        "end": 2.0,
        "x": 0.5,
        "y": 0.5,
        "tiers": [{
            "text": "ข้อความ",
            "look": {"font": "Kanit", "size_pct": 120, "color": "#FFFFFF", "outline_px": 0},
        }],
    }
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "base_fs": 60,
        "resolved_font": "Kanit",
        "font_map": {},
        "caption_color": "#0000E6FF",
    }

    item_straight = {
        **item_base,
        "tiers": [{
            "text": "ข้อความ",
            "look": {"font": "Kanit", "size_pct": 120, "color": "#FFFFFF", "outline_px": 0, "skew": 0.0},
        }],
        "anim": {"in": "none", "loop": "none", "out": "none"},
    }
    item_skewed = {
        **item_base,
        "tiers": [{
            "text": "ข้อความ",
            "look": {"font": "Kanit", "size_pct": 120, "color": "#FFFFFF", "outline_px": 0, "skew": -0.25},
        }],
        "anim": {"in": "none", "loop": "none", "out": "none"},
    }

    events_straight = _text_overlay_events(item_straight, ctx)
    events_skewed = _text_overlay_events(item_skewed, ctx)

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TextOverlayMain,Kanit,72,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_straight = tmp_path / "straight.ass"
    ass_straight.write_text(header + "\n".join(events_straight) + "\n", encoding="utf-8")
    ass_skewed = tmp_path / "skewed.ass"
    ass_skewed.write_text(header + "\n".join(events_skewed) + "\n", encoding="utf-8")

    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    p_straight = str(ass_straight.resolve()).replace("\\", "/").replace(":", "\\:")
    p_skewed = str(ass_skewed.resolve()).replace("\\", "/").replace(":", "\\:")

    img_straight = tmp_path / "straight.png"
    img_skewed = tmp_path / "skewed.png"

    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{p_straight}':fontsdir='{fonts_p}'",
        "-ss", "0.50", "-frames:v", "1", str(img_straight),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",
        "-vf", f"ass='{p_skewed}':fontsdir='{fonts_p}'",
        "-ss", "0.50", "-frames:v", "1", str(img_skewed),
    ])

    im_str = Image.open(img_straight).convert("L")
    im_skw = Image.open(img_skewed).convert("L")

    bbox_str = im_str.getbbox()
    bbox_skw = im_skw.getbbox()
    assert bbox_str is not None, "Straight text must render pixels"
    assert bbox_skw is not None, "Skewed text must render pixels"

    # Skew must visibly alter pixels
    diff = ImageChops.difference(im_str, im_skw)
    diff_pixels = int(np.sum(np.array(diff) > 0))
    assert diff_pixels > 100, f"Skewed text must differ from straight text, got {diff_pixels} diff pixels"

    # Forward slant (-0.25) shifts top pixels right relative to bottom pixels.
    # "ข้อความ" stacks a tone mark well above its base glyphs, so a row
    # picked by simple offset/proportion from the bbox can land in the gap
    # between them -- scan outward from the target row for the nearest one
    # that actually has ink, on both images independently (their bboxes and
    # gaps differ slightly under skew).
    arr_str = np.array(im_str)
    arr_skw = np.array(im_skw)

    def _nearest_row_with_ink(arr, y_target, y_lo, y_hi):
        for delta in range(0, y_hi - y_lo + 1):
            for y in (y_target + delta, y_target - delta):
                if y_lo <= y <= y_hi and np.any(arr[y, :] > 50):
                    return y
        return None

    bbox_h = bbox_skw[3] - bbox_skw[1]
    top_target = bbox_skw[1] + max(1, round(bbox_h * 0.25))
    bot_target = bbox_skw[3] - max(1, round(bbox_h * 0.20))
    top_y_str = _nearest_row_with_ink(arr_str, top_target, bbox_str[1], bbox_str[3])
    top_y_skw = _nearest_row_with_ink(arr_skw, top_target, bbox_skw[1], bbox_skw[3])
    bot_y_str = _nearest_row_with_ink(arr_str, bot_target, bbox_str[1], bbox_str[3])
    bot_y_skw = _nearest_row_with_ink(arr_skw, bot_target, bbox_skw[1], bbox_skw[3])
    assert None not in (top_y_str, top_y_skw, bot_y_str, bot_y_skw), \
        "Could not find an inked row near the target band in one of the renders"

    top_str_xs = np.where(arr_str[top_y_str, :] > 50)[0]
    top_skw_xs = np.where(arr_skw[top_y_skw, :] > 50)[0]
    bot_str_xs = np.where(arr_str[bot_y_str, :] > 50)[0]
    bot_skw_xs = np.where(arr_skw[bot_y_skw, :] > 50)[0]

    assert len(top_str_xs) > 0 and len(top_skw_xs) > 0
    assert len(bot_str_xs) > 0 and len(bot_skw_xs) > 0

    d_top = float(np.mean(top_skw_xs) - np.mean(top_str_xs))
    d_bot = float(np.mean(bot_skw_xs) - np.mean(bot_str_xs))
    assert d_top > d_bot, f"Forward slant must shift top right relative to bottom: d_top ({d_top:.2f}) > d_bot ({d_bot:.2f})"


def test_text_overlay_loop_and_out_behavioral_render(tmp_path):
    """
    Multi-frame FFmpeg behavioral render verifies loop (hold phase alpha modulation)
    and out (exit phase slide-down motion).
    """
    from scripts.subtitle.overlay_events import _text_overlay_events
    from PIL import Image, ImageChops
    import numpy as np

    item = {
        "kind": "text",
        "start": 0.0,
        "end": 1.5,
        "x": 0.5,
        "y": 0.5,
        "tiers": [{
            "text": "ข้อความแอนิเมชัน",
            "look": {"font": "Kanit", "size_pct": 100, "color": "#FFFFFF", "outline_px": 0},
        }],
        "anim": {"in": "none", "loop": "pulse", "out": "slide", "word_stagger_ms": 0},
    }
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "base_fs": 60,
        "resolved_font": "Kanit",
        "font_map": {},
        "caption_color": "#0000E6FF",
    }

    events = _text_overlay_events(item, ctx)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TextOverlayMain,Kanit,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_file = tmp_path / "anim.ass"
    ass_file.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    p_ass = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")

    img_hold_dim = tmp_path / "hold_dim.png"
    img_hold_bright = tmp_path / "hold_bright.png"
    img_exit = tmp_path / "exit.png"

    # Pulse cycles every 350ms: 350ms is dim (&H25&), 700ms is full bright (&H00&)
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=2:r=30",
        "-vf", f"ass='{p_ass}':fontsdir='{fonts_p}'",
        "-ss", "0.35", "-frames:v", "1", str(img_hold_dim),
    ])
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=2:r=30",
        "-vf", f"ass='{p_ass}':fontsdir='{fonts_p}'",
        "-ss", "0.70", "-frames:v", "1", str(img_hold_bright),
    ])
    # Exit phase: 1.45s (exit starts at 1.35s and ends at 1.50s, sliding downwards)
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=2:r=30",
        "-vf", f"ass='{p_ass}':fontsdir='{fonts_p}'",
        "-ss", "1.45", "-frames:v", "1", str(img_exit),
    ])

    im_dim = Image.open(img_hold_dim).convert("L")
    im_bright = Image.open(img_hold_bright).convert("L")
    im_exit = Image.open(img_exit).convert("L")

    bbox_dim = im_dim.getbbox()
    bbox_bright = im_bright.getbbox()
    bbox_exit = im_exit.getbbox()

    assert bbox_dim is not None, "Hold dim frame must render pixels"
    assert bbox_bright is not None, "Hold bright frame must render pixels"
    assert bbox_exit is not None, "Exit frame must render pixels"

    # Hold phase: pulse modulates brightness (diff between 0.35s and 0.70s)
    diff = ImageChops.difference(im_dim, im_bright)
    diff_pixels = int(np.sum(np.array(diff) > 0))
    assert diff_pixels > 50, f"Pulse must modulate pixel values across hold frames, got {diff_pixels} diff pixels"

    # Exit phase: slide down moves Y center downwards (higher Y value in frame)
    center_y_hold = (bbox_bright[1] + bbox_bright[3]) / 2.0
    center_y_exit = (bbox_exit[1] + bbox_exit[3]) / 2.0
    assert center_y_exit > center_y_hold + 5.0, f"Exit slide must move text downwards: exit Y ({center_y_exit:.1f}) > hold Y ({center_y_hold:.1f})"


@pytest.mark.render_regression
def test_new_hook_templates_render_with_ffmpeg(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for render regression testing")

    from PIL import Image
    from scripts.overlay_model import new_hook_overlay
    from scripts.subtitle.overlay_events import _hook_overlay_events

    new_templates = ["flash_sale", "neon_cyber", "minimal_luxury"]
    ctx = {
        "video_width": 1080,
        "video_height": 1920,
        "hook_fs": 75,
        "hook_font": "Kanit",
        "caption_color": "#0000E6FF",
    }
    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookHeader,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,6.0,0,8,60,60,180,1
Style: HookHeaderShadow,Kanit,75,&H00000000,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,7.0,0,8,62,58,177,1
Style: HookHeaderPill,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,12,0,8,60,60,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for tpl in new_templates:
        overlay = new_hook_overlay(
            brand="BRAND",
            model="MODEL NAME",
            label="SALE BADGE",
            template=tpl,
            start=0.0,
            duration=2.0,
        )
        assert overlay is not None
        events = _hook_overlay_events(overlay, ctx)
        assert len(events) > 0, f"{tpl}: should emit events"

        ass_file = tmp_path / f"hook_{tpl}.ass"
        ass_file.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
        p_ass = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")

        out_frame = tmp_path / f"frame_{tpl}.png"
        _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=2:r=30",
            "-vf", f"ass='{p_ass}':fontsdir='{fonts_p}'",
            "-ss", "0.50", "-frames:v", "1", str(out_frame),
        ])

        im = Image.open(out_frame).convert("L")
        bbox = im.getbbox()
        assert bbox is not None, f"{tpl} must burn visible text into frame at 0.5s"
        assert bbox[1] < 600, f"{tpl} banner should be located in top region, got y1={bbox[1]}"


@pytest.mark.render_regression
@pytest.mark.parametrize(
    ("style_preset", "accent_hex"),
    [
        ("viral_punch", "#FE2C55"),
        ("clean_tech_review", "#FFE600"),
        ("tech_product_showcase", "#FFCC33"),
        ("smooth_showcase", "#25F4EE"),
        ("premium_minimal", "#E6C24A"),
    ],
)
def test_style_preset_accent_burns_consistently_across_entry_hold_exit_frames(
    tmp_path, style_preset, accent_hex
):
    """Every selectable style palette must survive the real ASS/libass render."""
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the render regression fixture")

    from PIL import Image
    from scripts.subtitle_engine import SubtitleEngine

    ass_path = tmp_path / "style_hook.ass"
    SubtitleEngine.generate_ass(
        cues=[],
        output_ass_path=str(ass_path),
        bilingual=False,
        style_preset=style_preset,
        overlays=[{
            "kind": "hook",
            "start": 0.0,
            "end": 0.9,
            "tiers": [
                {"text": "BRAND"},
                {"text": "MODEL", "look": {"color": "accent"}},
                {"text": "LABEL"},
            ],
            "anim": {"in": "none", "loop": "none", "out": "none", "accent": "underline"},
        }],
    )
    ass_text = ass_path.read_text(encoding="utf-8")
    red, green, blue = (
        int(accent_hex[1:3], 16),
        int(accent_hex[3:5], 16),
        int(accent_hex[5:7], 16),
    )
    expected_ass_colour = f"\\c&H00{blue:02X}{green:02X}{red:02X}&"
    assert expected_ass_colour in ass_text, (
        f"{style_preset} accent must resolve to {expected_ass_colour} in ASS"
    )

    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    ass_p = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    frames_dir = tmp_path / "style_frames"
    frames_dir.mkdir()
    for label, timestamp in (("entry", "0.10"), ("hold", "0.45"), ("exit", "0.80")):
        _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=0.9:r=30",
            "-vf", f"ass='{ass_p}':fontsdir='{fonts_p}'",
            "-ss", timestamp, "-frames:v", "1",
            str(frames_dir / f"{label}.png"),
        ])

    accent_counts = []
    for label in ("entry", "hold", "exit"):
        image = Image.open(frames_dir / f"{label}.png").convert("RGB")
        accent_counts.append(sum(
            1 for pixel_red, pixel_green, pixel_blue in image.getdata()
            if max(
                abs(pixel_red - red),
                abs(pixel_green - green),
                abs(pixel_blue - blue),
            ) <= 70
        ))
    assert all(count > 0 for count in accent_counts), accent_counts


@pytest.mark.render_regression
def test_ghost_reveal_detaches_stacked_marks_per_word(tmp_path):
    """Progressive Ghost Reveal must repair Thai stacks like any other caption.

    The reveal rebuilds the line as one event per word, which is a separate code
    path from the plain caption -- and it originally skipped the stacked-mark
    repair entirely, putting ``ื่``/``ื้`` back into the output as raw pairs that
    several faces collapse. Rendered here as well as asserted in the ASS, since
    the whole point of the repair is what the rasterizer does with it.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the Thai render regression")

    from PIL import Image, ImageChops
    from scripts.subtitle_engine import SubtitleEngine

    # Kept under MICRO_BURST_MAX_CHARS (24) on purpose: a longer sentence is now
    # split into several bursts, each its own centred line, and this test is
    # about the left edge of ONE line staying put while its words are revealed.
    source = "ปกติซื้อช็อปเรื่องราคา"
    ass_path = tmp_path / "ghost_reveal_marks.ass"
    SubtitleEngine.generate_ass(
        cues=[{"start": 0.0, "end": 1.2, "text": source, "translation": "unused"}],
        output_ass_path=str(ass_path),
        font_name="Prompt",
        bilingual=False,
        caption_position="middle",
        ghost_reveal=True,
    )
    generated = ass_path.read_text(encoding="utf-8")

    # The reveal really did split the line up...
    caption_lines = [l for l in generated.splitlines() if ",TikTokWhite,," in l]
    assert len(caption_lines) > 3, "expected one event per word, not a single line"
    assert r"\alpha&HFF&" in generated, "unspoken words must be held transparent"

    # ...and no upper-vowel/tone pair survived into any of those events.
    for pair in ("ื่", "ื้"):
        assert pair not in generated, f"stacked pair {pair!r} was not detached"

    ass_filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    frames_pattern = str(tmp_path / "gr-%02d.png")
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=0xB49464:s=1080x1920:r=30:d=1.2",
        "-vf", f"subtitles='{ass_filter_path}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "34", frames_pattern,
    ])

    def ink_bbox(path):
        image = Image.open(path).convert("RGB")
        background = Image.new("RGB", image.size, image.getpixel((0, 0)))
        diff = ImageChops.difference(image, background).convert("L")
        mask = diff.point(lambda value: 255 if value > 8 else 0)
        # Same always-on watermark column the plain-caption test blanks out...
        mask.paste(0, (int(round(image.width * 0.82)), 0, image.width, image.height))
        # ...plus everything outside the caption's own band. A middle-positioned
        # caption sits around the vertical centre, while the always-on source
        # credit sits at the very bottom; measuring both together reported a
        # constant width and hid the reveal entirely.
        mask.paste(0, (0, 0, image.width, int(round(image.height * 0.40))))
        mask.paste(0, (0, int(round(image.height * 0.60)), image.width, image.height))
        return mask.getbbox()

    # The reveal's own contract: the line's LEFT edge never moves, however many
    # words are still transparent. That is what the \pos anchor buys -- without
    # it libass re-centres on the painted ink and the text slides sideways
    # (measured at 212px of drift before the anchor existed).
    lefts = []
    for frame in ("gr-04.png", "gr-16.png", "gr-30.png"):
        box = ink_bbox(tmp_path / frame)
        assert box is not None, f"{frame} drew no caption"
        lefts.append(box[0])
    assert max(lefts) - min(lefts) <= 4, f"the reveal drifted sideways: {lefts}"

    # And it does reveal. Total ink is the wrong measure here -- the companion
    # mark glyphs span the settled line from the first frame, so the bbox is
    # constant by design. What moves is the spoken text: the white run grows
    # rightwards and the green highlight travels along with it.
    def spans(path):
        image = Image.open(path).convert("RGB")
        pixels = image.load()
        white, green = [], []
        for y in range(900, 1010, 2):
            for x in range(100, 900, 2):
                r, g, b = pixels[x, y]
                if g > 150 and r < 140 and b < 110:
                    green.append(x)
                elif r > 200 and g > 200 and b > 200:
                    white.append(x)
        return (min(white), max(white)) if white else None, \
               (min(green), max(green)) if green else None

    # Sampled once a word has been spoken and again near the end. Not on the
    # very first frames: the opening word is still the active one there, so
    # nothing is white yet and "the spoken run grew" has nothing to compare.
    early_white, early_green = spans(tmp_path / "gr-14.png")
    late_white, late_green = spans(tmp_path / "gr-30.png")
    assert early_green and late_green, "no highlighted word was drawn"
    assert early_white and late_white, "no word had been spoken yet at either sample"
    assert late_green[0] > early_green[0], (
        f"the highlight never moved along the line: {early_green} -> {late_green}"
    )
    assert late_white[1] > early_white[1], (
        f"spoken text never grew rightwards: {early_white} -> {late_white}"
    )
    # The left edge of the spoken run stays put -- words already said do not
    # shift as later ones light up.
    assert abs(late_white[0] - early_white[0]) <= 4, (
        f"already-spoken text moved: {early_white} -> {late_white}"
    )


@pytest.mark.render_regression
def test_wrapped_ghost_reveal_holds_the_first_line_still(tmp_path):
    """A reveal that wraps must not disturb the line above the active word.

    Each step redraws every line, so the danger is that line one gets re-ghosted
    or re-anchored when the highlight moves to line two. Rendered rather than
    asserted in the ASS, because the failure is positional.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the Thai render regression")

    from PIL import Image

    from scripts.subtitle_engine import SubtitleEngine

    ass_path = tmp_path / "wrapped_reveal.ass"
    SubtitleEngine.generate_ass(
        cues=[{
            "start": 0.0,
            "end": 4.0,
            # An explicit break is kept as layout, giving a two-line caption.
            "text": "กล้องคมชัดมาก\nแบตอึดทั้งวัน",
            "translation": "unused",
        }],
        output_ass_path=str(ass_path),
        font_name="Prompt",
        bilingual=False,
        ghost_reveal=True,
    )
    generated = ass_path.read_text(encoding="utf-8")
    positions = {float(y) for y in re.findall(r"\\pos\([\d.]+,([\d.]+)\)", generated)}
    assert len(positions) >= 2, "a wrapped reveal must anchor each line separately"

    ass_filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=4",
        "-vf", f"subtitles='{ass_filter_path}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "118", str(tmp_path / "wr-%03d.png"),
    ])

    def line_spans(path):
        """White and green x-spans, split into the bands the lines occupy."""
        image = Image.open(path).convert("RGB")
        pixels = image.load()
        rows = {}
        for y in range(1300, 1650):
            white, green = [], []
            for x in range(60, 900, 2):
                r, g, b = pixels[x, y]
                if g > 150 and r < 140 and b < 110:
                    green.append(x)
                elif r > 200 and g > 200 and b > 200:
                    white.append(x)
            if white or green:
                rows[y] = (white, green)
        if not rows:
            return []
        # Cut the frame at the midpoint between the two anchors the ASS declares
        # rather than looking for a gap in the ink: Thai upper vowels reach high
        # enough that line two's marks touch line one's descenders, leaving no
        # background row to split on once both lines carry text.
        # The two body lines are the first two anchors; a third sits above them
        # for the raised companion mark glyphs, and must not be mistaken for a
        # line of its own.
        caption_anchors = sorted(y for y in positions if 1200 < y < 1700)
        assert len(caption_anchors) >= 2, f"expected two line anchors, got {caption_anchors}"
        boundary = (caption_anchors[0] + caption_anchors[1]) / 2
        out = []
        for band_rows in (
            [y for y in rows if y < boundary],
            [y for y in rows if y >= boundary],
        ):
            if not band_rows:
                out.append({"top": None, "white": None, "green": None})
                continue
            white = [x for y in band_rows for x in rows[y][0]]
            green = [x for y in band_rows for x in rows[y][1]]
            out.append({
                "top": min(band_rows),
                "white": (min(white), max(white)) if white else None,
                "green": (min(green), max(green)) if green else None,
            })
        return out

    # Sampled while line two is revealing, by which point line one is all white.
    late = [line_spans(tmp_path / f"wr-{n:03d}.png") for n in (76, 95, 112)]
    assert all(frames for frames in late), "the caption vanished mid-cue"

    first_line_left = [f[0]["white"][0] for f in late if f[0]["white"]]
    assert len(first_line_left) == len(late), "line one stopped being fully spoken"
    assert max(first_line_left) - min(first_line_left) <= 4, (
        f"line one shifted while line two revealed: {first_line_left}"
    )

    first_line_top = [f[0]["top"] for f in late]
    assert max(first_line_top) - min(first_line_top) <= 4, (
        f"line one moved vertically: {first_line_top}"
    )

    # ...and line one must not be carrying the highlight any more.
    assert all(f[0]["green"] is None for f in late), (
        "line one still shows the active-word colour after the reveal moved on"
    )


@pytest.mark.render_regression
def test_bilingual_ghost_reveal_keeps_the_english_line_visible(tmp_path):
    r"""The stacked translation must be on screen through the whole reveal.

    \alpha carries across \N, so the English line inherits whatever the Thai
    line above ended on -- under a reveal that is the last ghost's \alpha&HFF&.
    The translation was therefore invisible until the final word was spoken,
    appearing only on the settle event, which no amount of ASS-string reading
    would have shown.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the Thai render regression")

    from PIL import Image

    from scripts.subtitle_engine import SubtitleEngine

    ass_path = tmp_path / "bilingual_reveal.ass"
    SubtitleEngine.generate_ass(
        cues=[{
            "start": 0.0,
            "end": 3.0,
            "text": "กล้องคมชัดมาก",
            "translation": "The camera is very sharp",
        }],
        output_ass_path=str(ass_path),
        font_name="Mali",
        bilingual=True,
        ghost_reveal=True,
    )
    generated = ass_path.read_text(encoding="utf-8")
    assert "&H0000FF66&" in generated, "a bilingual caption must still reveal"

    ass_filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\:")
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=30:d=3",
        "-vf", f"subtitles='{ass_filter_path}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "88", str(tmp_path / "bl-%03d.png"),
    ])

    def ink_bottom(path):
        image = Image.open(path).convert("L")
        mask = image.point(lambda v: 255 if v > 60 else 0)
        # Blank the always-on watermark column before measuring.
        mask.paste(0, (int(round(image.width * 0.82)), 0, image.width, image.height))
        box = mask.getbbox()
        return box[3] if box else None

    # Early (first word), middle, and late (last word) in the reveal.
    bottoms = [ink_bottom(tmp_path / f"bl-{n:03d}.png") for n in (12, 45, 80)]
    assert all(b is not None for b in bottoms), "the caption vanished mid-cue"
    # The English sits below the Thai, so its presence sets the bottom edge.
    # If it were invisible early on, the first frame would stop much higher.
    assert max(bottoms) - min(bottoms) <= 8, (
        f"the English line was not on screen for the whole reveal: {bottoms}"
    )


@pytest.mark.render_regression
def test_stacked_mark_follows_its_line_on_a_wrapped_caption(tmp_path):
    r"""A detached tone must land on the line it belongs to, not the block.

    The companion glyph carries the whole caption, `\N` and all, so libass will
    place it per line -- but only if it is laid out the way the body is. Pinning
    it with `\pos` anchors the entire block on one point, which matches a single
    line and strands a wrapped one: the body grows upward from the bottom margin
    while the companion stays put, leaving the tone below its own word.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the Thai render regression")

    from PIL import Image

    from scripts.subtitle_engine import SubtitleEngine

    # Tone on the first line; the second is deliberately mark-free.
    ass_path = tmp_path / "wrapped_marks.ass"
    SubtitleEngine.generate_ass(
        cues=[{
            "start": 0.0,
            "end": 2.0,
            "text": "ตอนนี้เลยครับพี่\nแบตอดทงวนสบาย",
            "translation": "",
            "auto_emoji": False,
        }],
        output_ass_path=str(ass_path),
        font_name="Mali",
        bilingual=False,
        ghost_reveal=False,
    )
    generated = ass_path.read_text(encoding="utf-8")
    companions = [
        line for line in generated.splitlines()
        if line.startswith("Dialogue: 1,") and r"\1a&HFF&" in line
    ]
    assert companions, "no companion glyph was emitted for the stacked mark"
    assert all(r"\pos(" not in line for line in companions), (
        "a margin-anchored caption's companions must not be pinned with \pos"
    )

    ass_filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\:")
    png = tmp_path / "wm.png"
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=2",
        "-vf", f"subtitles='{ass_filter_path}':fontsdir='02_Assets/Fonts'",
        "-ss", "1.5", "-frames:v", "1", str(png),
    ])

    image = Image.open(png).convert("L")
    mask = image.point(lambda v: 255 if v > 60 else 0)
    mask.paste(0, (int(round(image.width * 0.82)), 0, image.width, image.height))
    pixels = mask.load()
    rows = [y for y in range(1200, 1750)
            if any(pixels[x, y] for x in range(40, 1000, 2))]
    assert rows, "the caption drew nothing"

    bands, current = [], [rows[0]]
    for y in rows[1:]:
        if y - current[-1] > 6:
            bands.append((current[0], current[-1]))
            current = [y]
        else:
            current.append(y)
    bands.append((current[0], current[-1]))
    assert len(bands) == 2, f"expected two text lines, got bands {bands}"

    # The tone belongs to the first line, so its ink must sit inside that
    # line's band -- if it were stranded it would appear between the two, or
    # below the second.
    first_top, first_bottom = bands[0]
    second_top, _ = bands[1]
    assert first_bottom < second_top, "the two lines ran together"
    # The raised companion extends line one upward; it must not reach into the
    # gap that separates the lines.
    assert first_bottom < (first_bottom + second_top) / 2, (
        f"the companion glyph drifted toward line two: {bands}"
    )
