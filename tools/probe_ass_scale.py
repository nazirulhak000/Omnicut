"""Read-only diagnostic probe for RENDER-BEHAVIOR-FIX-1.

Renders the same single Kanit line through FFmpeg/libass twice and measures
the ink width, then compares it against font_metrics' predicted advance.

Run:  python tools/probe_ass_scale.py
Writes PNG artifacts to a temp dir and prints measured numbers only.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.subtitle.font_metrics import (  # noqa: E402
    ass_glyph_scale,
    measure_text_width_px,
)

TEXT = "ลดกระหน่ำ ดีลลับ 1 แถม 1"
FONT = "Kanit"
FS = 75
W, H = 1080, 1920


def _esc(p: str) -> str:
    return p.replace("\\", "/").replace(":", "\\:")


def render(ass_path: Path, out_png: Path) -> None:
    fonts = _esc(str(Path("02_Assets/Fonts").resolve()))
    ass = _esc(str(ass_path.resolve()))
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d=1:r=30",
            "-vf", f"ass='{ass}':fontsdir='{fonts}'",
            "-frames:v", "1", str(out_png),
        ],
        check=True, capture_output=True,
    )


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="kanit_probe_"))
    ass = tmp / "probe.ass"
    ass.write_text(
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {W}\nPlayResY: {H}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{FONT},{FS},&H00FFFFFF,&H000000FF,&H00000000,"
        "&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
        f"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,"
        f"{{\\q2\\an7\\pos(153.50,500)}}{TEXT}\n",
        encoding="utf-8",
    )

    png = tmp / "probe.png"
    render(ass, png)

    img = Image.open(png).convert("L")
    bbox = img.getbbox()
    measured = (bbox[2] - bbox[0]) if bbox else 0

    scale = ass_glyph_scale(FONT)
    predicted_scaled = measure_text_width_px(TEXT, FONT, FS)  # already scaled?
    predicted_raw = predicted_scaled / scale if scale else predicted_scaled

    print(f"tmp dir       : {tmp}")
    print(f"font          : {FONT} @ {FS}px (Bold=1)")
    print(f"ass_glyph_scale: {scale:.4f}")
    print(f"libass ink width (rendered): {measured}px")
    print(f"font_metrics scaled advance:  {predicted_scaled:.1f}px")
    print(f"font_metrics raw advance:     {predicted_raw:.1f}px")
    print(f"measured/raw  : {measured / predicted_raw:.4f}")
    print(f"measured/scaled: {measured / predicted_scaled:.4f}")


if __name__ == "__main__":
    main()
