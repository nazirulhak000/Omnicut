import subprocess
import json
from pathlib import Path

base = Path(r"d:\Winona\Programmer\Capcut\.tmp\gadget_products")
results = []

for p in sorted(base.glob("*")):
    if not p.is_dir():
        continue
    vid = p / "video_clean_1080p.mp4"
    if not vid.exists():
        results.append((p.name, "NO VIDEO", 0, 0))
        continue
    cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json "{vid}"'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        data = json.loads(res.stdout)
        s = data["streams"][0]
        w, h = s["width"], s["height"]
        is_fhd = (w >= 1920 or h >= 1080)
        status = "FHD" if is_fhd else f"LOW_RES ({w}x{h})"
        results.append((p.name, status, w, h))
    except Exception as e:
        results.append((p.name, f"ERROR {e}", 0, 0))

print(f"{'PRODUCT':<45} | {'STATUS':<15} | {'RESOLUTION'}")
print("-" * 75)
for name, status, w, h in results:
    print(f"{name:<45} | {status:<15} | {w}x{h}")
