import subprocess
from pathlib import Path

# Test FFmpeg drawtext with fontfile
font_file = "02_Assets/Fonts/Mitr-Bold.ttf"
text = "ลดพิเศษวันนี้ อย่าเพิ่งซื้อ"

cmd_drawtext = [
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=#101420:s=1080x1920:d=1",
    "-vf", f"drawtext=fontfile='{font_file}':text='{text}':fontsize=80:fontcolor=white:borderw=5:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2",
    "-frames:v", "1",
    "test_drawtext_result.png"
]
subprocess.run(cmd_drawtext)
print("Rendered test_drawtext_result.png")
