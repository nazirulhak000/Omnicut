import subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = ROOT / "tests" / "scratch_spike"
SCRATCH.mkdir(parents=True, exist_ok=True)
FONTS_DIR = ROOT / "02_Assets" / "Fonts"

for val in [-0.25, 0.0, 0.25]:
    tag = f"\\fax{val:.2f}" if val != 0 else ""
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Kanit,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,0,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{{\\pos(540,960){tag}}}SAMPLE
"""
    ass_file = SCRATCH / f"fax_{val}.ass"
    ass_file.write_text(ass, encoding="utf-8")
    out_png = SCRATCH / f"fax_{val}.png"
    rel_ass = f"tests/scratch_spike/fax_{val}.ass"
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1",
        "-vf", f"subtitles='{rel_ass}':fontsdir='02_Assets/Fonts'",
        "-frames:v", "1", str(out_png)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    if res.returncode != 0:
        print("ERR:", res.stderr[:300])
    im = Image.open(out_png).convert("L")
    bbox = im.getbbox()
    print(f"val: {val}, bbox: {bbox}")
