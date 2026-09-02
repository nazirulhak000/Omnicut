import subprocess
from pathlib import Path

ass_content = """[Script Info]
Title: Test Thai Vowels
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MitrTest,Mitr,80,&H0000E6FF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,600,1
Style: PromptTest,Prompt,80,&H0000E6FF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,800,1
Style: IBMTest,IBM Plex Sans Thai,80,&H0000E6FF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,1000,1
Style: NotoTest,Noto Sans Thai,80,&H0000E6FF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0.5,0,1,5.5,2.5,2,60,60,1200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,MitrTest,,0,0,0,,1. Mitr: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ
Dialogue: 0,0:00:00.00,0:00:05.00,PromptTest,,0,0,0,,2. Prompt: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ
Dialogue: 0,0:00:00.00,0:00:05.00,IBMTest,,0,0,0,,3. IBM Plex: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ
Dialogue: 0,0:00:00.00,0:00:05.00,NotoTest,,0,0,0,,4. Noto: ลดพิเศษวันนี้ อย่าเพิ่งซื้อ
"""

Path("test_thai_vowels.ass").write_text(ass_content, encoding="utf-8")

# Render 1 frame image with FFmpeg
ass_p = str(Path("test_thai_vowels.ass").resolve()).replace("\\", "/").replace(":", "\\:")
fonts_p = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")

cmd = [
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=#1A1E2E:s=1080x1920:d=1",
    "-vf", f"subtitles='{ass_p}':fontsdir='{fonts_p}'",
    "-frames:v", "1",
    "test_thai_vowels_result.png"
]
subprocess.run(cmd)
print("Rendered test_thai_vowels_result.png")
