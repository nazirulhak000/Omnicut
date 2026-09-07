# NOTE: this file has no `def test_*` functions -- it is a manual diagnostic
# script (see .agents/rules/testing_standard.md rule 4: side effects at
# import time are not allowed in tests/test_*.py). Output files are only
# written when main() actually runs under `if __name__ == "__main__":`,
# never on plain pytest collection/import.

import subprocess
from pathlib import Path


def main():
    ass_content = """[Script Info]
Title: Test Windows & OpenType Thai Fonts
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Leelawadee,Leelawadee UI,75,&H0000E6FF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,400,1
Style: IBMPlex,IBM Plex Sans Thai,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,600,1
Style: Tahoma,Tahoma,75,&H0000E6FF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,800,1
Style: Mitr,Mitr,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,1000,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Leelawadee,,0,0,0,,1. Leelawadee UI: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ
Dialogue: 0,0:00:00.00,0:00:05.00,IBMPlex,,0,0,0,,2. IBM Plex: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ
Dialogue: 0,0:00:00.00,0:00:05.00,Tahoma,,0,0,0,,3. Tahoma: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ
Dialogue: 0,0:00:00.00,0:00:05.00,Mitr,,0,0,0,,4. Mitr: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ
"""

    Path("test_fixed_thai_fonts.ass").write_text(ass_content, encoding="utf-8")

    ass_p = str(Path("test_fixed_thai_fonts.ass").resolve()).replace("\\", "/").replace(":", "\\:")
    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#101420:s=1080x1920:d=1",
        "-vf", f"subtitles='{ass_p}':fontsdir='{fonts_p}'",
        "-frames:v", "1",
        "test_fixed_thai_fonts_result.png"
    ]
    subprocess.run(cmd)
    print("Rendered test_fixed_thai_fonts_result.png")


if __name__ == "__main__":
    main()
