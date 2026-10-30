# -*- coding: utf-8 -*-
"""Prepare Assets for TTZ K106 Magnetic Wireless Power Bank (TTZ01).
1. Copy raw gallery images to 01_Raw/TTZ01_PowerBank_K106/.
2. Generate 520x520 square clean images in 03_Projects/_HyperFrames_Studio/assets/ttz01/img/.
3. Generate transparent cutouts via rembg in 03_Projects/_HyperFrames_Studio/assets/ttz01/cutouts/.
"""
import os
import sys
import shutil
from pathlib import Path
from PIL import Image
import rembg

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "01_Raw" / "TTZ01_PowerBank_K106"
STUDIO_ASSETS = ROOT / "03_Projects" / "_HyperFrames_Studio" / "assets" / "ttz01"
CUTOUTS_DIR = STUDIO_ASSETS / "cutouts"
IMG_DIR = STUDIO_ASSETS / "img"

for d in [RAW_DIR, STUDIO_ASSETS, CUTOUTS_DIR, IMG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Map gallery images from .tmp/product_inspect/gallery/
SOURCE_MAP = {
    "gallery_01.webp": ".tmp/product_inspect/gallery/img_21.webp", # Black
    "gallery_02.webp": ".tmp/product_inspect/gallery/img_06.webp", # White
    "gallery_03.webp": ".tmp/product_inspect/gallery/img_08.webp", # Blue
    "gallery_04.webp": ".tmp/product_inspect/gallery/img_05.webp", # Yellow
    "gallery_05.webp": ".tmp/product_inspect/gallery/img_10.webp", # Lifestyle Desk Stand
    "gallery_06.webp": ".tmp/product_inspect/gallery/img_01.webp", # MagSafe 15W Charging
    "gallery_07.webp": ".tmp/product_inspect/gallery/img_02.webp", # 4 Ports & Dual Built-in Cables
    "gallery_08.webp": ".tmp/product_inspect/gallery/img_15.webp", # Feature Overview
}

print("=== 1. Copying Raw Images to 01_Raw ===")
for target_name, src_rel in SOURCE_MAP.items():
    src_path = ROOT / src_rel
    dest_path = RAW_DIR / target_name
    if src_path.exists():
        shutil.copy2(src_path, dest_path)
        print(f"  [Copied] {target_name} ({dest_path.stat().st_size} bytes)")
    else:
        print(f"  [Warning] Missing {src_path}")

print("\n=== 2. Generating 520x520 WebP Clean Listing Images ===")
# Generate clean square 520x520 WebP
for i in range(1, 9):
    raw_file = RAW_DIR / f"gallery_{i:02d}.webp"
    out_file = IMG_DIR / f"img_{i:02d}.webp"
    if raw_file.exists():
        with Image.open(raw_file) as im:
            im = im.convert("RGB")
            # Crop to square center
            w, h = im.size
            min_dim = min(w, h)
            left = (w - min_dim) // 2
            top = (h - min_dim) // 2
            im_cropped = im.crop((left, top, left + min_dim, top + min_dim))
            im_resized = im_cropped.resize((520, 520), Image.Resampling.LANCZOS)
            im_resized.save(out_file, "WEBP", quality=90)
            print(f"  [Generated] {out_file.name} (520x520 WebP)")

print("\n=== 3. Generating Transparent Cutouts via Rembg ===")
# 3.1 Hero Black: crop from gallery_01 (Black)
black_raw = RAW_DIR / "gallery_01.webp"
if black_raw.exists():
    with Image.open(black_raw) as im:
        im = im.convert("RGBA")
        # Crop to device region (remove bottom labels / qr codes)
        w, h = im.size
        # The devices are in the center/upper area:
        # crop top 0.15 to 0.82, width 0.10 to 0.90
        crop_box = (int(w * 0.10), int(h * 0.15), int(w * 0.90), int(h * 0.80))
        im_crop = im.crop(crop_box)
        cutout = rembg.remove(im_crop)
        # trim empty alpha
        bbox = cutout.getbbox()
        if bbox:
            cutout = cutout.crop(bbox)
        # resize maintaining aspect ratio with height ~ 600px
        ch_target = 600
        cw_target = int(cutout.width * (ch_target / cutout.height))
        cutout_resized = cutout.resize((cw_target, ch_target), Image.Resampling.LANCZOS)
        out_hero_black = CUTOUTS_DIR / "hero_black.png"
        cutout_resized.save(out_hero_black, "PNG")
        print(f"  [Cutout] hero_black.png ({cutout_resized.size})")

# 3.2 Hero White: crop from gallery_02 (White)
white_raw = RAW_DIR / "gallery_02.webp"
if white_raw.exists():
    with Image.open(white_raw) as im:
        im = im.convert("RGBA")
        w, h = im.size
        crop_box = (int(w * 0.10), int(h * 0.15), int(w * 0.90), int(h * 0.80))
        im_crop = im.crop(crop_box)
        cutout = rembg.remove(im_crop)
        bbox = cutout.getbbox()
        if bbox:
            cutout = cutout.crop(bbox)
        ch_target = 600
        cw_target = int(cutout.width * (ch_target / cutout.height))
        cutout_resized = cutout.resize((cw_target, ch_target), Image.Resampling.LANCZOS)
        out_hero_white = CUTOUTS_DIR / "hero_white.png"
        cutout_resized.save(out_hero_white, "PNG")
        print(f"  [Cutout] hero_white.png ({cutout_resized.size})")

# 3.3 Hero Duo: Composite Black & White side-by-side for CTA Outro
# Black standing on left, White standing on right, or Duo presentation
if (CUTOUTS_DIR / "hero_black.png").exists() and (CUTOUTS_DIR / "hero_white.png").exists():
    b_img = Image.open(CUTOUTS_DIR / "hero_black.png").convert("RGBA")
    w_img = Image.open(CUTOUTS_DIR / "hero_white.png").convert("RGBA")
    
    # Scale to ~540px height each
    scale_factor = 540 / b_img.height
    b_scaled = b_img.resize((int(b_img.width * scale_factor), 540), Image.Resampling.LANCZOS)
    w_scaled = w_img.resize((int(w_img.width * scale_factor), 540), Image.Resampling.LANCZOS)
    
    duo_w = b_scaled.width + w_scaled.width - 60
    duo_h = 560
    duo_canvas = Image.new("RGBA", (duo_w, duo_h), (0, 0, 0, 0))
    # Paste Black on left, White slightly overlapping on right
    duo_canvas.paste(b_scaled, (0, 10), b_scaled)
    duo_canvas.paste(w_scaled, (b_scaled.width - 60, 10), w_scaled)
    
    out_hero_duo = CUTOUTS_DIR / "hero_duo.png"
    duo_canvas.save(out_hero_duo, "PNG")
    print(f"  [Cutout Composite] hero_duo.png ({duo_canvas.size})")

# 3.4 Single Macro Hero: Single black power bank with kickstand upright (from img_15 pedestal)
ped_raw = RAW_DIR / "gallery_08.webp"
if ped_raw.exists():
    with Image.open(ped_raw) as im:
        im = im.convert("RGBA")
        w, h = im.size
        # Crop the upright powerbank standing on right side of img_15
        crop_box = (int(w * 0.35), int(h * 0.18), int(w * 0.95), int(h * 0.72))
        im_crop = im.crop(crop_box)
        cutout = rembg.remove(im_crop)
        bbox = cutout.getbbox()
        if bbox:
            cutout = cutout.crop(bbox)
        # target width ~500px, height ~640px
        cutout = cutout.resize((int(cutout.width * 640 / cutout.height), 640), Image.Resampling.LANCZOS)
        out_hero_single = CUTOUTS_DIR / "hero_single.png"
        cutout.save(out_hero_single, "PNG")
        print(f"  [Cutout Single Hero] hero_single.png ({cutout.size})")

print("\n=== Asset Preparation Complete ===")
