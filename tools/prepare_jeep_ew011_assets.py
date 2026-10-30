# -*- coding: utf-8 -*-
"""Prepare Assets for Jeep EW011 (JEE01).
1. Download gallery images from official PDP CDN.
2. Save to 01_Raw/JEE01_Jeep_EW011/.
3. Generate 520x520 square clean images in 03_Projects/_HyperFrames_Studio/assets/jee01/img/.
4. Generate transparent cutouts via rembg in 03_Projects/_HyperFrames_Studio/assets/jee01/cutouts/.
"""
import os
import sys
import urllib.request
from pathlib import Path
from PIL import Image
import rembg

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "01_Raw" / "JEE01_Jeep_EW011"
STUDIO_ASSETS = ROOT / "03_Projects" / "_HyperFrames_Studio" / "assets" / "jee01"
CUTOUTS_DIR = STUDIO_ASSETS / "cutouts"
IMG_DIR = STUDIO_ASSETS / "img"

for d in [RAW_DIR, STUDIO_ASSETS, CUTOUTS_DIR, IMG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

IMAGE_URLS = [
    "https://img.lazcdn.com/g/p/987f85dc607095b9ea06779844b4e344.jpg", # Hero / White
    "https://img.lazcdn.com/g/p/de985ec48311737b8cbc671437e58e42.jpg", # Black
    "https://img.lazcdn.com/g/p/51f5dc0b0b9ff458f2a8276e4b1e9c5a.jpg", # Earbuds close up
    "https://img.lazcdn.com/g/p/0488bc37183bd7f2404cdf62fcbac14f.jpg", # Driver 13mm
    "https://img.lazcdn.com/g/p/e62a73accdce2abe41bd2c5b328dd754.jpg", # Bluetooth 5.3
    "https://img.lazcdn.com/g/p/2c0b2b61924f823b0b3c04e45d49b6c2.jpg", # Battery / Case
    "https://img.lazcdn.com/g/p/430f706a92a0eaafdb0b83ba44b4dd89.jpg", # Wearing in ear
    "https://img.lazcdn.com/g/p/4014b3fc7b7e61f6c6ccf2b8a39f39b6.jpg", # Sport Waterproof
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("=== 1. Downloading Gallery Images ===")
downloaded_paths = []
for i, url in enumerate(IMAGE_URLS, 1):
    raw_path = RAW_DIR / f"gallery_{i:02d}.jpg"
    if not raw_path.exists() or raw_path.stat().st_size < 1000:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with open(raw_path, "wb") as f:
                f.write(data)
            print(f"  [Downloaded] {raw_path.name} ({len(data)} bytes)")
        except Exception as e:
            print(f"  [Error] {url}: {e}")
            continue
    else:
        print(f"  [Exist] {raw_path.name}")
    downloaded_paths.append(raw_path)

print("\n=== 2. Generating 520x520 WebP Clean Listing Images ===")
for i, raw_path in enumerate(downloaded_paths, 1):
    try:
        im = Image.open(raw_path).convert("RGB")
        w, h = im.size
        # Center crop to square
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        im_crop = im.crop((left, top, left + min_dim, top + min_dim))
        im_resized = im_crop.resize((520, 520), Image.Resampling.LANCZOS)
        out_webp = IMG_DIR / f"jee01_img_{i:02d}.webp"
        im_resized.save(out_webp, "WEBP", quality=92)
        print(f"  [Saved 520x520] {out_webp.name}")
    except Exception as e:
        print(f"  [Error webp] {raw_path.name}: {e}")

print("\n=== 3. Generating Transparent Cutouts (rembg) ===")
# Generate hero cutout from gallery_01 (White/Hero) and gallery_02 (Black)
for idx, label in [(1, "hero_white"), (2, "hero_black")]:
    raw_path = RAW_DIR / f"gallery_{idx:02d}.jpg"
    out_png = CUTOUTS_DIR / f"{label}.png"
    if raw_path.exists() and not out_png.exists():
        print(f"  Running rembg for {label}...")
        try:
            with open(raw_path, "rb") as f:
                input_data = f.read()
            output_data = rembg.remove(input_data)
            with open(out_png, "wb") as f:
                f.write(output_data)
            print(f"  [Cutout created] {out_png.name} ({len(output_data)} bytes)")
        except Exception as e:
            print(f"  [Rembg error] {label}: {e}")
    elif out_png.exists():
        print(f"  [Exist] {out_png.name}")

print("\n=== Jeep EW011 Assets Preparation Complete! ===")
