import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_VIDEO = PROJECT_ROOT / ".tmp" / "gadget_demo" / "demo_xiaomi_mix_flip_60s_review.mp4"
DEFAULT_ART_DIR = PROJECT_ROOT / ".tmp" / "artifacts"


def extract_60s_previews(out_video: Path = None, art_dir: Path = None):
    if out_video is None:
        out_video = DEFAULT_OUT_VIDEO
    if art_dir is None:
        art_dir = DEFAULT_ART_DIR

    art_dir.mkdir(parents=True, exist_ok=True)
    if not out_video.exists():
        print(f"[INFO] Video file not found: {out_video}")
        return

    moments = [
        (9.5, "preview_60s_outer_display.jpg"),
        (22.0, "preview_60s_inner_oled.jpg"),
        (32.5, "preview_60s_leica_optics.jpg"),
        (42.5, "preview_60s_snapdragon_cooling.jpg"),
        (52.0, "preview_60s_battery_charging.jpg")
    ]

    for sec, fname in moments:
        dst = art_dir / fname
        cmd = f'ffmpeg -y -ss {sec} -i "{out_video}" -vframes 1 -q:v 2 "{dst}"'
        subprocess.run(cmd, shell=True, check=True)
        print(f"Extracted {fname} at {sec}s")


if __name__ == '__main__':
    extract_60s_previews()
