import json
from pathlib import Path

root = Path(r"C:\Users\Winon\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
p = root / "TikTok_Esseger_Working"

with open(p / "draft_content.json", "r", encoding="utf-8") as f:
    c = json.load(f)

print("Project id:", c.get("id"))
print("Duration:", c.get("duration"))
print("Tracks count:", len(c.get("tracks", [])))
for i, trk in enumerate(c.get("tracks", [])):
    print(f"Track {i}: id={trk.get('id')}, type={trk.get('type')}, segments={len(trk.get('segments', []))}")
    if trk.get("segments"):
        s0 = trk["segments"][0]
        print(f"   seg0 target: {s0.get('target_timerange')}, source: {s0.get('source_timerange')}")

# Check materials
videos = c.get("materials", {}).get("videos", [])
print("\nVideos count:", len(videos))
for v in videos:
    print("Video:", v.get("id"), v.get("material_name"), "path:", v.get("path"), "duration:", v.get("duration"))

# Check subdraft folder
subdraft = p / "subdraft"
print("\nSubdraft exists:", subdraft.exists())
if subdraft.exists():
    for sf in subdraft.glob("*"):
        print("  subdraft file:", sf.name)
