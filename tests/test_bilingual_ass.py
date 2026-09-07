# NOTE: this file has no `def test_*` functions -- it is a manual diagnostic
# script (see .agents/rules/testing_standard.md rule 4: side effects at
# import time are not allowed in tests/test_*.py). Output files are only
# written when main() actually runs under `if __name__ == "__main__":`,
# never on plain pytest collection/import.

import subprocess
from pathlib import Path


def main():
    ass_content = """[Script Info]
Title: Bilingual Thai English Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BilingualMain,IBM Plex Sans Thai SemiBold,76,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,420,1
Style: BilingualYellow,IBM Plex Sans Thai SemiBold,76,&H0000E6FF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,BilingualMain,,0,0,0,,{\fscx105\fscy105\t(0,70,\fscx100\fscy100)}อย่าเพิ่งซื้อสายชาร์จธรรมดา\\N{\\fscx62\\fscy62\\c&H00D0D0D0&}Don't buy normal cables yet
Dialogue: 0,0:00:03.00,0:00:06.00,BilingualYellow,,0,0,0,,{\fscx105\fscy105\t(0,70,\fscx100\fscy100)}สายชาร์จแม่เหล็ก 3-in-1\\N{\\fscx62\\fscy62\\c&H00FFFFFF&}3-in-1 Magnetic Fast Charger
Dialogue: 0,0:00:06.00,0:00:09.00,BilingualMain,,0,0,0,,{\fscx105\fscy105\t(0,70,\fscx100\fscy100)}ราคาพิเศษวันนี้แค่ 149 บาท\\N{\\fscx62\\fscy62\\c&H0000E6FF&}Special price today only 149 THB
"""

    Path("test_bilingual.ass").write_text(ass_content, encoding="utf-8")

    ass_p = str(Path("test_bilingual.ass").resolve()).replace("\\", "/").replace(":", "\\:")
    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#0E121D:s=1080x1920:d=1",
        "-vf", f"subtitles='{ass_p}':fontsdir='{fonts_p}'",
        "-frames:v", "1",
        "test_bilingual_result.png"
    ]
    subprocess.run(cmd)
    print("Rendered test_bilingual_result.png")


if __name__ == "__main__":
    main()
