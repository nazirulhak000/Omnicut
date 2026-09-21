import subprocess
from pathlib import Path

ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Mali,90,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5.0,0,2,20,20,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{\\c&H66FF00&}นี่คือ{\\alpha&HFF&} Xiaomi MIX Flip
Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,{\\c&HFFFFFF&}นี่คือ {\\c&H66FF00&}Xiaomi{\\alpha&HFF&} MIX Flip
Dialogue: 0,0:00:02.00,0:00:03.00,Default,,0,0,0,,{\\c&HFFFFFF&}นี่คือ Xiaomi {\\c&H66FF00&}MIX Flip
"""
ass_path = Path('.tmp/gadget_demo/test_alpha.ass')
ass_path.write_text(ass_content, encoding='utf-8')

fonts_dir = str(Path('02_Assets/Fonts').resolve()).replace('\\', '/').replace(':', '\\:')
ass_filter = str(ass_path.resolve()).replace('\\', '/').replace(':', '\\:')

cmd1 = f'ffmpeg -y -f lavfi -i color=c=black:s=1080x1920:d=3 -vf "ass=\'{ass_filter}\':fontsdir=\'{fonts_dir}\'" -ss 0.5 -vframes 1 .tmp/gadget_demo/alpha_f1.jpg'
cmd2 = f'ffmpeg -y -f lavfi -i color=c=black:s=1080x1920:d=3 -vf "ass=\'{ass_filter}\':fontsdir=\'{fonts_dir}\'" -ss 1.5 -vframes 1 .tmp/gadget_demo/alpha_f2.jpg'
cmd3 = f'ffmpeg -y -f lavfi -i color=c=black:s=1080x1920:d=3 -vf "ass=\'{ass_filter}\':fontsdir=\'{fonts_dir}\'" -ss 2.5 -vframes 1 .tmp/gadget_demo/alpha_f3.jpg'

for c in [cmd1, cmd2, cmd3]:
    subprocess.run(c, shell=True, check=True)
print("Frames rendered successfully!")
