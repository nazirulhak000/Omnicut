import subprocess
from pathlib import Path

out_video = Path(".tmp/gadget_demo/demo_xiaomi_mix_flip_60s_review.mp4")
art_dir = Path(r"C:\Users\Winon\.gemini\antigravity-ide\brain\17ebf3bb-f0a4-4947-8ff4-4269406b9ba0")

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
