import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Mali,96,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.5,0,2,20,20,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\c&HFFFFFF&}ห้าม{\\c&H66FF00&\\fscx112\\fscy112}มี{\\r\\c&H66FF00&}โลโก้
"""

def test_mali_render(out_jpg=None):
    tmp_dir = PROJECT_ROOT / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ass_file = tmp_dir / "test_mali.ass"
    ass_file.write_text(ass_content, encoding="utf-8")

    fonts_dir = str((PROJECT_ROOT / "02_Assets" / "Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    ass_path_esc = str(ass_file.resolve()).replace("\\", "/").replace(":", "\\:")
    out_mp4 = tmp_dir / "test_mali.mp4"

    cmd = (
        f'ffmpeg -y -f lavfi -i color=c=black:s=1080x1920:d=2 '
        f'-vf "ass=\'{ass_path_esc}\':fontsdir=\'{fonts_dir}\'" '
        f'-c:v libx264 -preset ultrafast "{out_mp4}"'
    )
    subprocess.run(cmd, shell=True, check=True)

    if out_jpg is None:
        out_jpg = tmp_dir / "test_mali_render.jpg"
    out_jpg = Path(out_jpg)
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(f'ffmpeg -y -ss 00:00:01.000 -i "{out_mp4}" -vframes 1 -q:v 2 "{out_jpg}"', shell=True, check=True)
    print(f"Render complete: {out_jpg}")
    return out_jpg

if __name__ == "__main__":
    test_mali_render()
