import json
from pathlib import Path

capcut_root = Path(r"C:\Users\Winon\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
real_project = capcut_root / "0812(1)" / "draft_content.json"

if real_project.exists():
    with open(real_project, "r", encoding="utf-8") as f:
        d = json.load(f)

    print("Keys in draft_content.json:", list(d.keys()))
    print("Version:", d.get("version"), "New Version:", d.get("new_version"))
    print("Tracks count:", len(d.get("tracks", [])))
    for i, trk in enumerate(d.get("tracks", [])):
        print(f"Track {i}: type={trk.get('type')}, segments={len(trk.get('segments', []))}")
        if trk.get("segments"):
            first_seg = trk["segments"][0]
            print(f"   First segment keys: {list(first_seg.keys())}")
            print(f"   Clip keys: {list(first_seg.get('clip', {}).keys()) if first_seg.get('clip') else None}")
            
    print("\nMaterials keys:", list(d.get("materials", {}).keys()))
    for mat_k, mat_v in d.get("materials", {}).items():
        if isinstance(mat_v, list):
            print(f"Material '{mat_k}': {len(mat_v)} items")
            if mat_v:
                print(f"   First {mat_k} item: {mat_v[0]}")
