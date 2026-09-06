"""
Spike and test word layout positioning.
Verifies cumulative advance layout and compares 1 Dialogue per line vs 1 Dialogue per word in libass.
"""

import sys
import subprocess
from pathlib import Path
from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.asset_registry import AssetRegistry
from scripts.subtitle.font_metrics import prefix_advances

OUT_DIR = ROOT / "tests" / "scratch_round4"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run_ffmpeg(args):
    res = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
                         capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {res.stderr}")

def test_thai_per_word_rendering():
    # "ลดกระหน่ำ ดีลลับ 1 แถม 1"
    text = "\u0e25\u0e14\u0e01\u0e23\u0e30\u0e2b\u0e19\u0e48\u0e33 \u0e14\u0e35\u0e25\u0e25\u0e31\u0e1a 1 \u0e41\u0e16\u0e21 1"
    font_name = "Kanit"
    font_size = 75
    video_w = 1080
    video_h = 1920
    
    # Let's tokenize
    from pythainlp.tokenize import word_tokenize
    tokens = word_tokenize(text, engine="newmm")
    print(f"Raw tokens: {tokens}")
    
    # Keep tokens separate, but group whitespace
    # Each item has: text (trimmed), lead_x (start x including preceding spaces), width
    from scripts.subtitle.font_metrics import ass_glyph_scale
    family_to_path = {f["family"]: f["path"] for f in AssetRegistry.fonts()}
    path = family_to_path[font_name]
    scale = ass_glyph_scale(font_name)
    scaled_fs = font_size * scale
    font = ImageFont.truetype(path, scaled_fs)

    # Calculate cumulative advances at each token boundary
    advances = [0.0]
    cum = ""
    for tok in tokens:
        cum += tok
        advances.append(font.getlength(cum))
    
    for i, tok in enumerate(tokens):
        w_adv = advances[i+1] - advances[i]
        print(f"Token {i}: {repr(tok)} -> advance={w_adv:.2f}, cum={advances[i+1]:.2f}")
    
    total_w = advances[-1]
    x_center = video_w // 2
    x_start = x_center - total_w / 2
    y = 500

    # Build word items (skip purely whitespace tokens for dialogue emission)
    word_items = []
    for i, tok in enumerate(tokens):
        if not tok.isspace():
            w_x = x_start + advances[i]
            w_w = advances[i+1] - advances[i]
            word_items.append({"text": tok, "x": w_x, "w": w_w})

    # 1. Monolithic ASS: 1 Dialogue for the whole line
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
    (OUT_DIR / "mono.ass").write_text(ass_mono, encoding="utf-8")
    
    # 2. Per-word ASS: 1 Dialogue per non-space word using exact w_x
    events = []
    for item in word_items:
        events.append(f"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{{\\q2\\an7\\pos({item['x']:.2f},{y})}}{item['text']}")
    
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
    (OUT_DIR / "split.ass").write_text(ass_split, encoding="utf-8")
    
    # Render both via ffmpeg
    rel_mono = (OUT_DIR / "mono.ass").relative_to(ROOT).as_posix()
    rel_split = (OUT_DIR / "split.ass").relative_to(ROOT).as_posix()
    
    run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=1:r=30",
        "-vf", f"ass='{rel_mono}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(OUT_DIR / "mono.png")
    ])
    run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=1:r=30",
        "-vf", f"ass='{rel_split}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(OUT_DIR / "split.png")
    ])
    
    # Let's test color-per-word scan to verify word-start error <= 1px
    colors = [
        "&H0000FF&", # Red
        "&H00FF00&", # Green
        "&HFF0000&", # Blue
        "&H00FFFF&", # Yellow
        "&HFFFF00&", # Cyan
        "&HFF00FF&", # Magenta
        "&H8000FF&", # Orange
    ]
    
    # Build mono ASS with colored tags for non-space tokens
    colored_text = ""
    color_idx = 0
    for tok in tokens:
        if not tok.isspace():
            c = colors[color_idx % len(colors)]
            colored_text += f"{{\\1c{c}}}{tok}"
            color_idx += 1
        else:
            colored_text += tok
            
    ass_color = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{{\\q2\\an7\\pos({x_start:.2f},{y})}}{colored_text}
"""
    (OUT_DIR / "color_mono.ass").write_text(ass_color, encoding="utf-8")
    run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={video_w}x{video_h}:d=1:r=30",
        "-vf", f"ass='tests/scratch_round4/color_mono.ass':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(OUT_DIR / "color_mono.png")
    ])
    
    im_color = Image.open(OUT_DIR / "color_mono.png")
    w_im, h_im = im_color.size
    
    # Expected colors in RGB
    rgb_targets = [
        ("Red", (255, 0, 0)),
        ("Green", (0, 255, 0)),
        ("Blue", (0, 0, 255)),
        ("Yellow", (255, 255, 0)),
        ("Cyan", (0, 255, 255)),
        ("Magenta", (255, 0, 255)),
        ("Orange", (255, 0, 128)),
    ]
    
    # Measure ink left for each word in mono
    print("\n--- Word Start Parity Scan ---")
    for i, item in enumerate(word_items):
        name, rgb = rgb_targets[i % len(rgb_targets)]
        matching_xs = []
        for x in range(w_im):
            for y_p in range(h_im):
                px = im_color.getpixel((x, y_p))[:3]
                # Check dominant color
                if name == "Red" and px[0] > 120 and px[1] < 40 and px[2] < 40:
                    matching_xs.append(x)
                elif name == "Green" and px[1] > 120 and px[0] < 40 and px[2] < 40:
                    matching_xs.append(x)
                elif name == "Blue" and px[2] > 120 and px[0] < 40 and px[1] < 40:
                    matching_xs.append(x)
                elif name == "Yellow" and px[0] > 120 and px[1] > 120 and px[2] < 40:
                    matching_xs.append(x)
                elif name == "Cyan" and px[1] > 120 and px[2] > 120 and px[0] < 40:
                    matching_xs.append(x)
                elif name == "Magenta" and px[0] > 120 and px[2] > 120 and px[1] < 40:
                    matching_xs.append(x)
                elif name == "Orange" and px[0] > 120 and px[2] > 40 and px[1] < 40:
                    matching_xs.append(x)
        
        measured_left = min(matching_xs) if matching_xs else -1
        calc_x = item['x']
        diff_px = abs(measured_left - calc_x) if measured_left >= 0 else -1
        print(f"Word {i} [{item['text']}]: calc_x={calc_x:.2f}, measured_left={measured_left}, delta={diff_px:.2f}px")
        
if __name__ == "__main__":
    test_thai_per_word_rendering()
