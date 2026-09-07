# NOTE: this file has no `def test_*` functions -- it is a manual diagnostic
# script (see .agents/rules/testing_standard.md rule 4: side effects at
# import time are not allowed in tests/test_*.py). Output files are only
# written when main() actually runs under `if __name__ == "__main__":`,
# never on plain pytest collection/import.

import subprocess
from pathlib import Path


def main():
    fonts = [
        ("IBM Plex Bold", "IBMPlexSansThai-Bold", "IBM Plex Sans Thai Bold"),
        ("IBM Plex SemiBold", "IBMPlexSansThai-SemiBold", "IBM Plex Sans Thai SemiBold"),
        ("Chakra Petch Bold", "ChakraPetch-Bold", "Chakra Petch Bold"),
        ("Kanit ExtraBold", "Kanit-ExtraBold", "Kanit ExtraBold"),
        ("Prompt Black", "Prompt-Black", "Prompt Black"),
        ("Mitr SemiBold", "Mitr-SemiBold", "Mitr SemiBold")
    ]

    styles = []
    dialogues = []
    y_pos = 250

    for idx, (display, font_face, full_name) in enumerate(fonts):
        style_name = f"Style{idx}"
        styles.append(f"Style: {style_name},{full_name},68,&H0000E6FF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,{y_pos},1")
        dialogues.append(f"Dialogue: 0,0:00:00.00,0:00:05.00,{style_name},,0,0,0,,{display}: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ สายชาร์จนี้")
        y_pos += 220

    ass_content = f"""[Script Info]
Title: Comprehensive Thai Vowel Tone Test
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{chr(10).join(styles)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(dialogues)}
"""

    Path("test_all_vowels.ass").write_text(ass_content, encoding="utf-8")

    ass_p = str(Path("test_all_vowels.ass").resolve()).replace("\\", "/").replace(":", "\\:")
    fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=#0D1117:s=1080x1920:d=1",
        "-vf", f"subtitles='{ass_p}':fontsdir='{fonts_p}'",
        "-frames:v", "1",
        "test_all_vowels_result.png"
    ]
    subprocess.run(cmd)
    print("Rendered test_all_vowels_result.png")


if __name__ == "__main__":
    main()
