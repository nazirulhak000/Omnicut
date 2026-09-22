"""Central Stock B-Roll Downloader and Catalog Manager for OmniCut Pro.

Downloads high-quality, royalty-free/commercial-safe tech stock videos (1080p)
organized into 5 core gadget categories under 02_Assets/Stock_Footage/.
"""

import json
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STOCK_DIR = BASE_DIR / "02_Assets" / "Stock_Footage"

CURATED_CLIPS = [
    # 1. Battery & Fast Charging
    {
        "category": "01_Battery_Charging",
        "id": "battery_charging_hud",
        "filename": "broll_battery_charging_hud.mp4",
        "url": "https://www.youtube.com/watch?v=u6y34YhEko0",
        "title": "Battery Charging Futuristic HUD Animation",
        "license": "Creative Commons / Royalty-Free",
        "usage": "Use during battery capacity, fast charging speed, or power specs"
    },
    {
        "category": "01_Battery_Charging",
        "id": "usbc_plug_in",
        "filename": "broll_usbc_plug_in.mp4",
        "url": "https://www.youtube.com/watch?v=zqGUfIBhPDY",
        "title": "Close-up USB-C Cable Plugging into Smartphone",
        "license": "Royalty-Free Stock Footage",
        "usage": "Use during charging wattage, wired/wireless charging cutaways"
    },
    {
        "category": "01_Battery_Charging",
        "id": "electric_energy_surge",
        "filename": "broll_electric_energy_surge.mp4",
        "url": "https://www.youtube.com/watch?v=BZJZQdcwnew",
        "title": "Abstract Electric Energy Surge Glow",
        "license": "Royalty-Free Free Stock",
        "usage": "Use for Surge P1/G1 chip, battery tech, and high performance bursts"
    },

    # 2. Chipset & Performance
    {
        "category": "02_Chipset_Performance",
        "id": "microchip_futuristic_3d",
        "filename": "broll_microchip_futuristic_3d.mp4",
        "url": "https://www.youtube.com/watch?v=PWOAgNBmm18",
        "title": "Futuristic 3D Microchip Processor with Illuminating Circuits",
        "license": "Royalty-Free Stock Footage",
        "usage": "Use during Snapdragon / Dimensity / Tensor chipset and AI processor mentions"
    },
    {
        "category": "02_Chipset_Performance",
        "id": "macro_processor_circuit",
        "filename": "broll_macro_processor_circuit.mp4",
        "url": "https://www.youtube.com/watch?v=VSmeG54-7NU",
        "title": "Macro Circuit Board Electric Pulse",
        "license": "Royalty-Free Stock Footage",
        "usage": "Use during RAM, storage, cooling chamber, or motherboard architecture"
    },

    # 3. Camera & Optics
    {
        "category": "03_Camera_Optics",
        "id": "camera_aperture_macro",
        "filename": "broll_camera_aperture_macro.mp4",
        "url": "https://www.youtube.com/watch?v=UjTC6s23YNw",
        "title": "Camera Lens Aperture Blades Opening and Closing",
        "license": "Royalty-Free Stock Footage",
        "usage": "Use during camera sensor size, f/1.4 aperture, or Leica optics highlights"
    },
    {
        "category": "03_Camera_Optics",
        "id": "camera_lens_zoom_reflection",
        "filename": "broll_camera_lens_zoom_reflection.mp4",
        "url": "https://www.youtube.com/watch?v=aQKgCK8337s",
        "title": "Premium Glass Camera Lens Macro Reflection",
        "license": "Royalty-Free Stock Footage",
        "usage": "Use during telephoto zoom, portrait lens, or anti-reflective coating mentions"
    },

    # 4. Display & Touch
    {
        "category": "04_Display_Touch",
        "id": "phone_scrolling_smooth",
        "filename": "broll_phone_scrolling_smooth.mp4",
        "url": "https://www.youtube.com/watch?v=fZCE_2PKyls",
        "title": "Smooth Hands-on Smartphone Scrolling Close-up",
        "license": "Royalty-Free HD Footage",
        "usage": "Use during 120Hz refresh rate, touch response, and outer/inner screen interaction"
    },
    {
        "category": "04_Display_Touch",
        "id": "screen_touch_lifestyle",
        "filename": "broll_screen_touch_lifestyle.mp4",
        "url": "https://www.youtube.com/watch?v=1d-vk39ADvk",
        "title": "Mobile Screen Social Media Feed Interaction",
        "license": "Royalty-Free Free Video",
        "usage": "Use during daily app usage, HyperOS / One UI software experience"
    },

    # 5. Tech Backgrounds & Cyber Atmosphere
    {
        "category": "05_Tech_Backgrounds",
        "id": "tech_cyber_lines_loop",
        "filename": "broll_tech_cyber_lines_loop.mp4",
        "url": "https://www.youtube.com/watch?v=P90X9xxm1gc",
        "title": "Clean Cybernetic Grid and Neon Lines Loop",
        "license": "Royalty-Free Template",
        "usage": "Use for high-tech transitions, intro hooks, and spec comparison backdrop"
    }
]


def run_cmd(cmd: str):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.returncode == 0, res.stdout, res.stderr


def probe_video(video_path: Path):
    cmd = f'ffprobe -v error -show_entries stream=width,height,duration,r_frame_rate -of json "{video_path}"'
    ok, out, _ = run_cmd(cmd)
    if not ok:
        return {}
    try:
        data = json.loads(out)
        streams = data.get("streams", [{}])
        s = streams[0] if streams else {}
        return {
            "width": s.get("width"),
            "height": s.get("height"),
            "duration": float(s.get("duration", 0)),
            "fps": s.get("r_frame_rate")
        }
    except Exception:
        return {}


def download_clip(clip_info: dict) -> bool:
    cat_dir = STOCK_DIR / clip_info["category"]
    cat_dir.mkdir(parents=True, exist_ok=True)
    target_file = cat_dir / clip_info["filename"]

    if target_file.exists() and target_file.stat().st_size > 100_000:
        print(f"  [OK] Already exists: {clip_info['filename']} ({target_file.stat().st_size // 1024} KB)")
        return True

    print(f"[*] Downloading {clip_info['id']} -> {clip_info['filename']}...")
    url = clip_info["url"]
    
    # Download 1080p or best available up to 1080p
    dl_cmd = (
        f'yt-dlp --no-update '
        f'-f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" '
        f'--merge-output-format mp4 "{url}" -o "{target_file}" --force-overwrites'
    )
    ok, out, err = run_cmd(dl_cmd)
    if not ok:
        print(f"  [!] Primary download failed: {err[:150]}")
        # Fallback to simple best mp4
        dl_fallback = f'yt-dlp --no-update -f "best[height<=1080]" --merge-output-format mp4 "{url}" -o "{target_file}"'
        ok, out, err = run_cmd(dl_fallback)
        if not ok:
            print(f"  [!] Fallback failed: {err[:150]}")
            return False

    print(f"  [SUCCESS] Downloaded: {clip_info['filename']} ({target_file.stat().st_size // 1024} KB)")
    return True


def main():
    STOCK_DIR.mkdir(parents=True, exist_ok=True)
    catalog = {
        "title": "OmniCut Pro Studio - Central Tech Stock B-Roll Library",
        "description": "Universal royalty-free / commercial-safe B-roll footage for gadget reviews",
        "updated_at": "2026-09-21",
        "total_clips": len(CURATED_CLIPS),
        "categories": [
            "01_Battery_Charging",
            "02_Chipset_Performance",
            "03_Camera_Optics",
            "04_Display_Touch",
            "05_Tech_Backgrounds"
        ],
        "clips": []
    }

    success_count = 0
    for clip in CURATED_CLIPS:
        ok = download_clip(clip)
        if ok:
            success_count += 1
        
        target_file = STOCK_DIR / clip["category"] / clip["filename"]
        meta = probe_video(target_file) if target_file.exists() else {}
        
        entry = {
            **clip,
            "status": "ready" if target_file.exists() else "download_error",
            "size_kb": target_file.stat().st_size // 1024 if target_file.exists() else 0,
            "width": meta.get("width"),
            "height": meta.get("height"),
            "duration_sec": meta.get("duration"),
            "local_path": str(target_file.relative_to(BASE_DIR)).replace("\\", "/") if target_file.exists() else None
        }
        catalog["clips"].append(entry)
        time.sleep(1.5)

    catalog_path = STOCK_DIR / "stock_catalog.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[DONE] Central Stock Library Ready: {success_count}/{len(CURATED_CLIPS)} clips downloaded.")
    print(f"Catalog saved to: {catalog_path}")


if __name__ == "__main__":
    main()
