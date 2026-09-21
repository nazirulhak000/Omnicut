import subprocess
from pathlib import Path

src_video = Path(".tmp/gadget_products/Xiaomi_xiaomi_mix_flip/video_clean_1080p.mp4")
fonts_dir = str(Path("02_Assets/Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
ass_filter_path = str(Path(".tmp/gadget_demo/subtitles_with_callout.ass").resolve()).replace("\\", "/").replace(":", "\\:")
art_dir = Path(r"C:\Users\Winon\.gemini\antigravity-ide\brain\17ebf3bb-f0a4-4947-8ff4-4269406b9ba0")
out_img = art_dir / "preview_spec_callout_techmx_style.jpg"

# Put -ss AFTER -i so libass sees the real PTS time (9.5s)
ff_cmd = (
    f'ffmpeg -y -i "{src_video}" -ss 00:00:09.500 '
    f'-filter_complex "'
    f'[0:v]split=2[bg_raw][fg_raw];'
    f'[bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35,eq=brightness=-0.08[bg];'
    f'[fg_raw]scale=1080:-2[fg];'
    f'[bg][fg]overlay=0:(H-h)/2[base];'
    f'[base]ass=\'{ass_filter_path}\':fontsdir=\'{fonts_dir}\'[v]" '
    f'-map "[v]" -vframes 1 -q:v 2 "{out_img}"'
)

subprocess.run(ff_cmd, shell=True, check=True)
print(f"Rendered callout preview to {out_img}")
