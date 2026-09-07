# NOTE: this file has no `def test_*` functions -- it is a manual diagnostic
# script (see .agents/rules/testing_standard.md rule 4: side effects at
# import time are not allowed in tests/test_*.py). Output files are only
# written when main() actually runs under `if __name__ == "__main__":`,
# never on plain pytest collection/import.

import subprocess
from pathlib import Path


def main():
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


if __name__ == "__main__":
    main()
