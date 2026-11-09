#!/usr/bin/env python3
"""Generate official 9:16 and 3:4 (TikTok Profile Grid) cover JPGs for all 20 Essager clips.

Outputs:
  - 05_Covers_Thumbnails/20261013_ess02-pov-sXX_v1_cover.jpg (1080x1920)
  - 05_Covers_Thumbnails/20261013_ess02-pov-sXX_v1_cover_3x4.jpg (1080x1440)
  - Registers into _Docs/export_cover_bindings.json
  - Updates _Docs/products.json with cover_path and cover_3x4_path
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# Windows UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = ROOT / "04_Exports" / "Ready_to_post"
COVERS_DIR = ROOT / "05_Covers_Thumbnails"
COMPS_ARCHIVE = ROOT / "06_Archive" / "HyperFrames_Studio" / "compositions"
DOCS_DIR = ROOT / "_Docs"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import store_io  # noqa: E402

COVERS_DIR.mkdir(parents=True, exist_ok=True)

PRODUCT_ID = "9505b042d58640f5aa58015bb86be097"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_cta_time(comp_path: Path) -> float:
    if not comp_path.exists():
        return 50.0
    txt = comp_path.read_text(encoding="utf-8")
    m_cta = re.search(r'const\s+CTA_T\s*=\s*([\d\.]+);', txt)
    if m_cta:
        return float(m_cta.group(1))
    return 50.0


def main():
    print("=== Generating Official Covers for 20 Essager Clips ===")

    # Load export registry to find export_ids (อ่านผ่าน store: error ต้อง raise ไม่กลายเป็น [])
    exports_map = {}
    for entry in store_io.load_export_registry(DOCS_DIR):
        p = entry.get("path") or ""
        if p:
            exports_map[Path(p).name] = entry.get("id")

    # Load products (read-only snapshot; the writes below go through the store)
    products = store_io.load_products(DOCS_DIR)

    target_product = next((p for p in products if p.get("id") == PRODUCT_ID), None)
    angles_map = {}
    if target_product:
        for a in target_product.get("angles", []):
            aid = a.get("angle_id") or a.get("id")
            if aid:
                angles_map[aid] = a

    generated_count = 0
    binding_updates = []   # binding_data ที่จะ upsert ผ่าน store หลังสร้างภาพครบ
    angle_updates = {}     # angle_id -> {cover_path, cover_3x4_path, cover_url}

    for i in range(1, 21):
        stem = f"20261013_ess02-pov-s{i:02d}_v1"
        mp4_path = EXPORTS_DIR / f"{stem}.mp4"
        if not mp4_path.exists():
            print(f"[Skip] {mp4_path.name} not found")
            continue

        comp_path = COMPS_ARCHIVE / f"ess02-pov-s{i:02d}.html"
        cta_t = get_cta_time(comp_path)
        
        # Probe MP4 duration
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(mp4_path)]
        try:
            probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            dur = float(json.loads(probe_res.stdout)["format"]["duration"])
        except Exception:
            dur = 60.0
        
        seek_sec = min(cta_t + 1.8, max(0.5, dur - 1.0))

        out_916 = COVERS_DIR / f"{stem}_cover.jpg"
        out_3x4 = COVERS_DIR / f"{stem}_cover_3x4.jpg"

        # 1. 9:16 (1080x1920)
        cmd_916 = [
            "ffmpeg", "-v", "error", "-y",
            "-ss", str(seek_sec),
            "-i", str(mp4_path),
            "-strict", "unofficial",
            "-frames:v", "1",
            "-q:v", "2",
            str(out_916)
        ]
        # 2. 3:4 TikTok Profile Grid Crop (1080x1440, center crop 0:240)
        cmd_3x4 = [
            "ffmpeg", "-v", "error", "-y",
            "-ss", str(seek_sec),
            "-i", str(mp4_path),
            "-strict", "unofficial",
            "-frames:v", "1",
            "-vf", "crop=1080:1440:0:240",
            "-q:v", "2",
            str(out_3x4)
        ]

        subprocess.run(cmd_916, check=True)
        subprocess.run(cmd_3x4, check=True)

        sha_916 = sha256_file(out_916)
        sha_3x4 = sha256_file(out_3x4)

        rel_video = f"04_Exports/Ready_to_post/{mp4_path.name}"
        rel_916 = f"05_Covers_Thumbnails/{out_916.name}"
        rel_3x4 = f"05_Covers_Thumbnails/{out_3x4.name}"
        exp_id = exports_map.get(mp4_path.name) or f"exp_ess30w_s{i:02d}"

        binding_data = {
            "id": f"cover_{sha_916[:32]}",
            "channel_id": "main",
            "export_id": exp_id,
            "video_path": rel_video,
            "selections": {
                "9:16": {
                    "path": rel_916,
                    "sha256": sha_916,
                    "format": "9:16"
                },
                "3:4": {
                    "path": rel_3x4,
                    "sha256": sha_3x4,
                    "format": "3:4"
                }
            },
            "revision": 1,
            "updated_at": 1791830000.0 + i
        }
        binding_updates.append(binding_data)

        # Update product angle in products.json
        angle_id = f"ang_ess30w_{i:02d}"
        if angle_id in angles_map:
            angle_updates[angle_id] = {
                "cover_path": rel_916,
                "cover_3x4_path": rel_3x4,
                "cover_url": f"/api/media/{rel_3x4}",
            }

        generated_count += 1
        print(f"[{i:02d}/20] Created covers for {stem}: 9:16 ({out_916.stat().st_size // 1024} KB), 3:4 ({out_3x4.stat().st_size // 1024} KB)")

    # Save bindings (ทรานแซกชันเดียวของ ExportCoverBindingStore)
    with store_io.mutate_cover_bindings(DOCS_DIR) as bindings:
        for binding_data in binding_updates:
            existing_binding = next(
                (b for b in bindings
                 if b.get("export_id") == binding_data["export_id"]
                 or b.get("video_path") == binding_data["video_path"]),
                None,
            )
            if existing_binding:
                existing_binding.update(binding_data)
            else:
                bindings.append(binding_data)
        total_bindings = len(bindings)
    print(f"Updated export_cover_bindings with {total_bindings} total bindings")

    # Save products (ทรานแซกชันเดียวของ ProductStore)
    if target_product:
        with store_io.mutate_products(DOCS_DIR) as rows:
            target = next((p for p in rows if p.get("id") == PRODUCT_ID), None)
            if target is not None:
                for ang in target.get("angles", []):
                    aid = ang.get("angle_id") or ang.get("id")
                    if aid in angle_updates:
                        ang.update(angle_updates[aid])
        print("Updated products with covers for 20 Essager angles")

    print(f"\nSUCCESS: Generated official 9:16 & 3:4 covers for all {generated_count} clips!")


if __name__ == "__main__":
    main()
