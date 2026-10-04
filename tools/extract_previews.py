import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_VIDEO = PROJECT_ROOT / '.tmp' / 'gadget_demo' / 'demo_xiaomi_mix_flip_techmx.mp4'
DEFAULT_ART_DIR = PROJECT_ROOT / '.tmp' / 'artifacts'


def extract_previews(out_video: Path = None, art_dir: Path = None):
    if out_video is None:
        out_video = DEFAULT_OUT_VIDEO
    if art_dir is None:
        art_dir = DEFAULT_ART_DIR

    art_dir.mkdir(parents=True, exist_ok=True)
    if not out_video.exists():
        print(f"[INFO] Video file not found: {out_video}")
        return

    timestamps = [
        (0.8, 'preview_karaoke_step1.jpg'),
        (1.5, 'preview_karaoke_step2.jpg'),
        (2.1, 'preview_karaoke_step3.jpg'),
        (3.2, 'preview_karaoke_step4.jpg'),
        (16.5, 'preview_speccard_sync.jpg'),
    ]

    for ts, name in timestamps:
        dst = art_dir / name
        cmd = f'ffmpeg -y -ss {ts} -i "{out_video}" -vframes 1 -q:v 2 "{dst}"'
        subprocess.run(cmd, shell=True, check=True)
        print(f"Extracted {name} at {ts}s")


if __name__ == '__main__':
    extract_previews()
