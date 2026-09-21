import subprocess
from pathlib import Path

out_video = Path('.tmp/gadget_demo/demo_xiaomi_mix_flip_techmx.mp4')
art_dir = Path(r'C:\Users\Winon\.gemini\antigravity-ide\brain\17ebf3bb-f0a4-4947-8ff4-4269406b9ba0')

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
