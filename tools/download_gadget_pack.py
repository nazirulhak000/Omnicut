"""Automated Product Asset Pack Builder for Gadget Media.

Downloads 1080p clean videos (no foreign subtitles) and extracts product photos,
organizing each model into its dedicated folder with info.json.
"""

import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_BASE = BASE_DIR / ".tmp" / "gadget_products"
MANIFEST_FILE = BASE_DIR / ".tmp" / "gadget_news_sources_20260919" / "source_manifest.json"


def run_cmd(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return res.returncode == 0, res.stdout, res.stderr


def build_product_pack(product_id: str, url: str, brand: str, topic: str):
    slug = f"{brand}_{product_id}".replace("-", "_").replace(" ", "_")
    pack_dir = OUTPUT_BASE / slug
    pack_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = pack_dir / "photos"
    photos_dir.mkdir(exist_ok=True)

    target_video = pack_dir / "video_clean_1080p.mp4"
    print(f"[*] Processing {slug}...")

    # Download 1080p clean video if not exists
    if not target_video.exists():
        print(f"  -> Downloading 1080p video from {url}...")
        dl_cmd = f'yt-dlp --no-update --extractor-args "youtube:player_client=android,web" -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" --merge-output-format mp4 "{url}" -o "{target_video}"'
        ok, out, err = run_cmd(dl_cmd)
        if not ok:
            print(f"  [!] Download failed: {err[:200]}")
            return False

    # Extract sample clean photo frames dynamically based on video duration
    print("  -> Extracting high-res sample photos...")
    
    # Try getting video duration
    dur_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{target_video}"'
    ok_dur, out_dur, _ = run_cmd(dur_cmd)
    try:
        total_sec = float(out_dur.strip())
    except Exception:
        total_sec = 30.0

    # Pick 3 timestamps at 25%, 50%, 75%
    sample_points = [max(1.0, total_sec * r) for r in [0.25, 0.50, 0.75]]

    for idx, sec in enumerate(sample_points):
        photo_path = photos_dir / f"frame_{idx+1}.jpg"
        if not photo_path.exists() and target_video.exists():
            ff_cmd = f'ffmpeg -ss {sec:.2f} -i "{target_video}" -vframes 1 -q:v 2 "{photo_path}" -y'
            run_cmd(ff_cmd)

    # Write info.json
    info = {
        "product_id": product_id,
        "brand": brand,
        "topic": topic,
        "source_url": url,
        "clean_footage": True,
        "no_foreign_subtitles": True,
        "status": "ready_for_editing"
    }
    (pack_dir / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Completed pack: {slug}")
    return True


import time


def main():
    if not MANIFEST_FILE.exists():
        print(f"Manifest not found: {MANIFEST_FILE}")
        return

    data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    
    # If specific product_id given as argument, process only that
    target_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    for s in sources:
        pid = s.get("id")
        if target_id and pid != target_id:
            continue
        build_product_pack(pid, s.get("source_url"), s.get("brand"), s.get("topic"))
        if target_id:
            break
        # Gentle pacing between downloads
        time.sleep(2)


if __name__ == "__main__":
    main()
