import subprocess
from pathlib import Path

fonts_dir = Path("02_Assets/Fonts").resolve()
ass_test = Path(".tmp/04_Sandbox/test_font.ass")

ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Subtitle,IBM Plex Sans Thai SemiBold,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,3.5,0,2,54,54,420,1
Style: CalloutTop,Prompt,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,4.0,2.0,8,40,40,240,1
Style: CalloutBottom,Prompt-Black,92,&H002266FF,&H002266FF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,5.0,2.0,2,40,40,540,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,CalloutTop,,0,0,0,,INNER LTPO OLED
Dialogue: 0,0:00:00.00,0:00:02.00,CalloutBottom,,0,0,0,,6.86" 3,000 NITS
Dialogue: 0,0:00:00.00,0:00:02.00,Subtitle,,0,0,0,,มอบภาพที่คมชัด และ{{\\c&H00FF66&}}สบายตา{{\\c&HFFFFFF&}}ในทุกสภาพแสง
"""

with open(ass_test, "w", encoding="utf-8") as f:
    f.write(ass_content)

out_frame = Path(".tmp/04_Sandbox/test_font_frame.jpg")
ass_esc = str(ass_test.resolve()).replace("\\", "/").replace(":", "\\:")
fonts_esc = str(fonts_dir).replace("\\", "/").replace(":", "\\:")

cmd = [
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1",
    "-vf", f"subtitles='{ass_esc}':fontsdir='{fonts_esc}'",
    "-vframes", "1",
    str(out_frame)
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Returncode:", res.returncode)
if res.returncode != 0:
    print(res.stderr[-300:])
else:
    print("Success! Rendered test font frame.")
