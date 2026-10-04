import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC_VIDEO = PROJECT_ROOT / ".tmp" / "gadget_products" / "Xiaomi_xiaomi_mix_flip" / "video_clean_1080p.mp4"
DEFAULT_ART_DIR = PROJECT_ROOT / ".tmp" / "artifacts"


def test_spec_callout(src_video: Path = None, art_dir: Path = None):
    if src_video is None:
        src_video = DEFAULT_SRC_VIDEO
    if art_dir is None:
        art_dir = DEFAULT_ART_DIR

    art_dir.mkdir(parents=True, exist_ok=True)
    if not src_video.exists():
        print(f"[INFO] Source video not found: {src_video}")
        return

    fonts_dir = str((PROJECT_ROOT / "02_Assets" / "Fonts").resolve()).replace("\\", "/").replace(":", "\\:")
    ass_filter_path = str((PROJECT_ROOT / ".tmp" / "gadget_demo" / "subtitles_with_callout.ass").resolve()).replace("\\", "/").replace(":", "\\:")
    out_img = art_dir / "preview_spec_callout_techmx_style.jpg"

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

    try:
        subprocess.run(ff_cmd, shell=True, check=True)
        print(f"Rendered callout preview to {out_img}")
    except Exception as e:
        print(f"Error rendering callout preview: {e}")


if __name__ == '__main__':
    test_spec_callout()
