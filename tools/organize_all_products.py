"""Product-Centric Storage Organizer for All Gadget Media Sources.

Organizes existing downloaded native 1080p footage and creates dedicated
folders for all 24 Xiaomi Ecosystem products with standard 01_Raw, 02_Workspace, 03_Export structure
and clean, human-readable folder names.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = BASE_DIR / ".tmp" / "Products"
NATIVE_SOURCES_DIR = BASE_DIR / ".tmp" / "02_Sources" / "Native_1080p_Sources" / "source"
MANIFEST_FILE = BASE_DIR / ".tmp" / "02_Sources" / "News_Sources" / "source_manifest.json"


def run_cmd(cmd: str):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.returncode == 0, res.stdout, res.stderr


def clean_slug(brand: str, pid: str) -> str:
    if pid == "xiaomi-mix-flip":
        return "Xiaomi_MIX_Flip"
    if pid == "70mai-dash-cam-omni":
        return "70mai_Dash_Cam_Omni"
    
    # Capitalize parts cleanly
    parts = pid.split("-")
    cap_parts = []
    for p in parts:
        if p.lower() in ["su7", "c701", "x20", "f6", "x6", "s4", "14", "17", "17t", "13", "4", "5", "8", "9", "2", "3"]:
            cap_parts.append(p.upper())
        elif p.lower() in ["pro", "plus", "ultra", "max", "feeder", "air", "compressor", "smart", "band", "watch", "camera", "buds", "vacuum", "robot", "pad", "scooter", "fryer", "purifier", "series"]:
            cap_parts.append(p.capitalize())
        else:
            cap_parts.append(p.capitalize())
    
    brand_clean = brand.split()[0].capitalize()
    # Avoid duplicate brand prefix like Xiaomi_Xiaomi_14
    if cap_parts and cap_parts[0].lower() == brand_clean.lower():
        cap_parts.pop(0)
        
    return f"{brand_clean}_" + "_".join(cap_parts)


def create_product_skeleton(product_path: Path):
    dirs = [
        product_path / "01_Raw" / "videos",
        product_path / "01_Raw" / "photos",
        product_path / "01_Raw" / "metadata",
        product_path / "02_Workspace" / "audio",
        product_path / "02_Workspace" / "draft_versions",
        product_path / "02_Workspace" / "subtitles",
        product_path / "02_Workspace" / "temp_cuts",
        product_path / "03_Export",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def extract_photos(video_path: Path, photos_dir: Path):
    if not video_path.exists():
        return
    dur_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
    ok, out, _ = run_cmd(dur_cmd)
    try:
        dur = float(out.strip())
    except Exception:
        dur = 30.0

    for idx, pct in enumerate([0.25, 0.50, 0.75]):
        t = max(1.0, dur * pct)
        out_img = photos_dir / f"frame_{idx+1}.jpg"
        if not out_img.exists():
            cmd = f'ffmpeg -ss {t:.2f} -i "{video_path}" -vframes 1 -q:v 2 "{out_img}" -y'
            run_cmd(cmd)


def organize_existing_native_sources():
    print("[*] Organizing existing native 1080p video sources...")
    native_map = [
        {
            "slug": "Google_Pixel_11_Pro",
            "brand": "Google",
            "title": "Google Pixel 11 Pro Official Product Video",
            "file": "google_pixel_GNuXueQ1BYc.mp4",
            "url": "https://www.youtube.com/watch?v=GNuXueQ1BYc",
            "usage_note": "Clean 1080p product reveal for Pixel 11 Pro flagship."
        },
        {
            "slug": "Samsung_Galaxy_S26_FE",
            "brand": "Samsung",
            "title": "Samsung Galaxy S26 FE Official Design Video",
            "file": "samsung_webembedded_cdC0sSWM3Bo.mp4",
            "url": "https://www.youtube.com/watch?v=cdC0sSWM3Bo",
            "usage_note": "Clean 1080p web-embedded showcase for Galaxy S26 FE."
        },
        {
            "slug": "Motorola_IFA_2026",
            "brand": "Motorola",
            "title": "Motorola IFA 2026 Showcase",
            "file": "motorola_Pi2eSkBP9dM.mp4",
            "url": "https://www.youtube.com/watch?v=Pi2eSkBP9dM",
            "usage_note": "Clean 1080p IFA presentation footage."
        },
        {
            "slug": "Anker_Soundcore_IFA_2026",
            "brand": "Anker",
            "title": "Anker Soundcore IFA 2026 Brand Clip",
            "file": "anker_native_WBsbzFxRy9I.mp4",
            "url": "https://www.youtube.com/watch?v=WBsbzFxRy9I",
            "usage_note": "High quality audio product lifestyle and design footage."
        },
        {
            "slug": "Google_Event_2026",
            "brand": "Google",
            "title": "Made by Google Event 2026 Keynote Slices",
            "file": "google_event_native_c84y9gAY90c.mp4",
            "url": "https://www.youtube.com/watch?v=c84y9gAY90c",
            "usage_note": "Keynote and ecosystem showcase."
        }
    ]

    for item in native_map:
        prod_path = PRODUCTS_DIR / item["slug"]
        create_product_skeleton(prod_path)
        
        src_video = NATIVE_SOURCES_DIR / item["file"]
        dest_video = prod_path / "01_Raw" / "videos" / "clean_1080p.mp4"
        
        if src_video.exists() and not dest_video.exists():
            shutil.copy2(src_video, dest_video)
            print(f"  -> Copied {src_video.name} to {item['slug']}/01_Raw/videos/clean_1080p.mp4")

        photos_dir = prod_path / "01_Raw" / "photos"
        extract_photos(dest_video, photos_dir)

        info = {
            "product_name": item["slug"].replace("_", " "),
            "brand": item["brand"],
            "title": item["title"],
            "source_url": item["url"],
            "usage_note": item["usage_note"],
            "status": "READY_FOR_EDITING",
            "has_raw_video": dest_video.exists(),
            "raw_video_path": str(dest_video.relative_to(BASE_DIR)).replace("\\", "/") if dest_video.exists() else None
        }
        (prod_path / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def organize_xiaomi_manifest():
    print("[*] Organizing 24 Xiaomi Ecosystem products from manifest...")
    if not MANIFEST_FILE.exists():
        print(f"  [!] Manifest file not found: {MANIFEST_FILE}")
        return

    data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    sources = data.get("sources", [])

    # Clean up any clumsy old directories that had lowercase duplicates
    old_clumsy_dirs = [
        "70mai_(Xiaomi_Eco)_70mai_dash_cam_omni",
        "Xiaomi_xiaomi_su7_ultra",
        "Xiaomi_xiaomi_air_compressor_2",
        "Xiaomi_xiaomi_pet_feeder_2",
        "Xiaomi_xiaomi_14_ultra",
        "Xiaomi_xiaomi_14",
        "Xiaomi_xiaomi_17t_series",
        "Xiaomi_xiaomi_17_ultra",
        "Redmi_redmi_note_13_pro_plus",
        "POCO_poco_f6_pro",
        "POCO_poco_x6_pro",
        "Xiaomi_xiaomi_smart_band_9",
        "Xiaomi_xiaomi_smart_band_9_pro",
        "Xiaomi_xiaomi_watch_s4",
        "Xiaomi_xiaomi_robot_vacuum_x20_max",
        "Xiaomi_xiaomi_robot_vacuum_5_pro",
        "Xiaomi_xiaomi_smart_air_purifier_4",
        "Xiaomi_xiaomi_smart_camera_c701",
        "Xiaomi_xiaomi_buds_5_pro",
        "Redmi_redmi_buds_5_pro",
        "Xiaomi_xiaomi_scooter_4_ultra",
        "Xiaomi_xiaomi_pad_8",
        "Xiaomi_mi_smart_air_fryer"
    ]
    for old_name in old_clumsy_dirs:
        old_p = PRODUCTS_DIR / old_name
        if old_p.exists() and old_p.is_dir():
            shutil.rmtree(old_p)

    for s in sources:
        pid = s.get("id")
        brand = s.get("brand", "Xiaomi")
        topic = s.get("topic", "")
        slug = clean_slug(brand, pid)

        prod_path = PRODUCTS_DIR / slug
        create_product_skeleton(prod_path)

        has_export = (prod_path / "03_Export" / "Xiaomi_MIX_Flip_60s_Master.mp4").exists()
        has_video = (prod_path / "01_Raw" / "videos" / "clean_1080p.mp4").exists() or list((prod_path / "01_Raw" / "videos").glob("*.mp4"))

        current_status = "APPROVED_MASTER" if has_export else ("READY_FOR_EDITING" if has_video else "CATALOGED_READY_TO_PULL")

        info_path = prod_path / "info.json"
        if not info_path.exists() or current_status != "APPROVED_MASTER":
            info = {
                "product_name": slug.replace("_", " "),
                "product_id": pid,
                "brand": brand,
                "topic": topic,
                "published_at": s.get("published_at", ""),
                "source_url": s.get("source_url", ""),
                "duration_seconds": s.get("duration_seconds", 0),
                "usage_note": s.get("usage_note", ""),
                "status": current_status,
                "download_command": f"python tools/download_gadget_pack.py {pid}"
            }
            info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  -> {slug} [{current_status}]")


def generate_registry():
    print("[*] Generating master products_registry.json...")
    registry = {
        "title": "OmniCut Pro Studio - Gadget Media Product Registry",
        "updated_at": "2026-09-21",
        "total_products": 0,
        "approved_masters": 0,
        "ready_for_editing": 0,
        "cataloged_ready_to_pull": 0,
        "products": []
    }

    for prod_dir in sorted(PRODUCTS_DIR.iterdir()):
        if not prod_dir.is_dir():
            continue
        info_file = prod_dir / "info.json"
        if not info_file.exists():
            continue
        try:
            info = json.loads(info_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        status = info.get("status", "UNKNOWN")
        raw_videos = list((prod_dir / "01_Raw" / "videos").glob("*.mp4"))
        raw_photos = list((prod_dir / "01_Raw" / "photos").glob("*.jpg")) + list((prod_dir / "01_Raw" / "photos").glob("*.png"))
        exports = list((prod_dir / "03_Export").glob("*.mp4"))

        item = {
            "folder_name": prod_dir.name,
            "product_name": info.get("product_name", prod_dir.name),
            "brand": info.get("brand", ""),
            "topic": info.get("topic", info.get("title", "")),
            "status": status,
            "raw_video_count": len(raw_videos),
            "raw_photo_count": len(raw_photos),
            "export_count": len(exports),
            "source_url": info.get("source_url", ""),
            "folder_path": f".tmp/Products/{prod_dir.name}"
        }
        registry["products"].append(item)

        registry["total_products"] += 1
        if status == "APPROVED_MASTER":
            registry["approved_masters"] += 1
        elif status == "READY_FOR_EDITING":
            registry["ready_for_editing"] += 1
        elif status == "CATALOGED_READY_TO_PULL":
            registry["cataloged_ready_to_pull"] += 1

    reg_path = PRODUCTS_DIR / "products_registry.json"
    reg_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Master registry written: {reg_path} ({registry['total_products']} products total)")


def main():
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    organize_existing_native_sources()
    organize_xiaomi_manifest()
    generate_registry()


if __name__ == "__main__":
    main()
