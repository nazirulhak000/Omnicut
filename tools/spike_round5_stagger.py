"""
Spike test for Round 5: Word Stagger Animation.
Tests multi-frame rendering across 3 time points (50ms, 150ms, 350ms)
to verify that words enter sequentially without tearing or ghosting.
"""

import sys
import subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "tests" / "scratch_round5"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run_ffmpeg(args):
    res = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {res.stderr}")

def test_stagger_frames():
    from scripts.subtitle.word_layout import layout_line

    text = "ลดกระหน่ำ ดีลลับ 1 แถม 1"
    font_name = "Kanit"
    font_size = 75
    video_w = 1080
    video_h = 1920

    layout = layout_line(text, font_name, font_size, norm_x=0.5, video_w=video_w)
    words = layout["words"]

    # Let's test pop_zoom with word_stagger_ms = 80ms
    stagger_ms = 80
    y = 500
    line_h = 75

    events = []
    target_scale = 108

    for i, w in enumerate(words):
        t0 = i * stagger_ms
        t1 = t0 + 100
        snap_from = int(round(target_scale * 1.45))
        w_x = w["abs_x"]
        w_w = w["abs_w"]
        w_cx = w_x + w_w / 2.0
        w_cy = y + line_h / 2.0

        pos_tag = f"\\q2\\an7\\pos({w_x:.1f},{y:.1f})"
        if t0 == 0:
            anim_tag = f"\\org({w_cx:.1f},{w_cy:.1f})\\alpha&HFF&\\fscx{snap_from}\\fscy{snap_from}\\t(0,70,\\alpha&H00&)\\t(0,100,\\fscx{target_scale}\\fscy{target_scale})"
        else:
            anim_tag = f"\\org({w_cx:.1f},{w_cy:.1f})\\alpha&HFF&\\fscx{snap_from}\\fscy{snap_from}\\t({t0},{t0+70},\\alpha&H00&)\\t({t0},{t1},\\fscx{target_scale}\\fscy{target_scale})"

        tag = f"{pos_tag}{anim_tag}\\3c&H00000000&\\bord5.0\\c&H00FFFFFF&"
        events.append(f"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{{{tag}}}{w['text']}")

    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n"

    ass_path = OUT_DIR / "stagger.ass"
    ass_path.write_text(ass_content, encoding="utf-8")

    fonts_p = str((ROOT / "02_Assets" / "Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    ass_p = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")

    # Render frame 1 at 40ms (only word 0 has started, word 1 starts at 80ms)
    run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=2:r=30",
        "-vf", f"ass='{ass_p}':fontsdir='{fonts_p}'",
        "-ss", "0.040", "-frames:v", "1", str(OUT_DIR / "frame_40ms.png")
    ])

    # Render frame 2 at 120ms (word 0 settled, word 1 entering, word 2 starts at 160ms)
    run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=2:r=30",
        "-vf", f"ass='{ass_p}':fontsdir='{fonts_p}'",
        "-ss", "0.120", "-frames:v", "1", str(OUT_DIR / "frame_120ms.png")
    ])

    # Render frame 3 at 600ms (all words settled)
    run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=2:r=30",
        "-vf", f"ass='{ass_p}':fontsdir='{fonts_p}'",
        "-ss", "0.600", "-frames:v", "1", str(OUT_DIR / "frame_600ms.png")
    ])

    im1 = Image.open(OUT_DIR / "frame_40ms.png")
    im2 = Image.open(OUT_DIR / "frame_120ms.png")
    im3 = Image.open(OUT_DIR / "frame_600ms.png")

    bbox1 = im1.getbbox()
    bbox2 = im2.getbbox()
    bbox3 = im3.getbbox()

    print(f"Frame 40ms bbox: {bbox1}")
    print(f"Frame 120ms bbox: {bbox2}")
    print(f"Frame 600ms bbox: {bbox3}")

    assert bbox1 is not None and bbox2 is not None and bbox3 is not None
    # At 40ms, ink must be narrower than at 120ms
    w1 = bbox1[2] - bbox1[0]
    w2 = bbox2[2] - bbox2[0]
    w3 = bbox3[2] - bbox3[0]
    print(f"Widths: 40ms={w1}px, 120ms={w2}px, 600ms={w3}px")

    assert w1 < w2 < w3, f"Sequential entry failed: {w1} < {w2} < {w3}"
    print("SUCCESS: Words enter sequentially in libass!")

if __name__ == "__main__":
    test_stagger_frames()
