# -*- coding: utf-8 -*-
"""
Prepare Assets for [New] Redmi Buds 8 Active (RED01)
1. Download gallery, SKU, and detail images from TikTok Shop CDN
2. Save to 01_Raw/1734226045478406079/ and 01_Raw/RED01_Redmi_Buds_8_Active/
3. Generate transparent PNG cutouts via rembg for Black, White, Blue, and Hero
4. Save to 03_Projects/_HyperFrames_Studio/assets/red01/cutouts/ and assets/red01/img/
"""

import os
import sys
import json
import urllib.request
from pathlib import Path
from PIL import Image
import rembg

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR_ID = BASE_DIR / "01_Raw" / "1734226045478406079"
RAW_DIR_ALIAS = BASE_DIR / "01_Raw" / "RED01_Redmi_Buds_8_Active"
STUDIO_ASSETS = BASE_DIR / "03_Projects" / "_HyperFrames_Studio" / "assets" / "red01"
CUTOUTS_DIR = STUDIO_ASSETS / "cutouts"
IMG_DIR = STUDIO_ASSETS / "img"

for d in [RAW_DIR_ID, RAW_DIR_ALIAS, STUDIO_ASSETS, CUTOUTS_DIR, IMG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Load scraped PDP data
with open(BASE_DIR / ".tmp" / "redmi_pdp.json", "r", encoding="utf-8") as f:
    pdp_raw = json.load(f)

pinfo = pdp_raw['loaderData']['(region)/pdp/(product_name_slug$)/(product_id)/page']['page_config']['components_map'][3]['component_data']['product_info']

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

def download_file(url, target_path):
    if target_path.exists() and target_path.stat().st_size > 500:
        print(f"  [Exist] {target_path.name}")
        return
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        content = resp.read()
    with open(target_path, "wb") as f:
        f.write(content)
    print(f"  [Downloaded] {target_path.name} ({len(content)} bytes)")

print("=== 1. Downloading Gallery Images ===")
gallery_imgs = pinfo.get('images', [])
for i, img_obj in enumerate(gallery_imgs):
    url = img_obj.get('url_list', [None])[0]
    if not url:
        continue
    fn = f"gallery_{i:02d}.webp"
    p1 = RAW_DIR_ID / fn
    p2 = RAW_DIR_ALIAS / fn
    download_file(url, p1)
    if not p2.exists():
        import shutil
        shutil.copy2(p1, p2)
    # also copy to studio img
    st_p = IMG_DIR / f"red01_img_{i+1:02d}.webp"
    if not st_p.exists():
        import shutil
        shutil.copy2(p1, st_p)

print("\n=== 2. Downloading SKU Images (Colors) ===")
sku_map = {
    "Black": "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/8268fb9af7f7438f8a1a75bb62f3e1db~tplv-aphluv4xwc-resize-webp:800:800.webp",
    "White": "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/d45dbd9ea6c64f84a21692b695126d32~tplv-aphluv4xwc-resize-webp:800:800.webp",
    "Blue": "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/77c8f3e01e334bddb1c4a976e64a6aeb~tplv-aphluv4xwc-resize-webp:800:800.webp"
}

for color, url in sku_map.items():
    fn = f"sku_{color.lower()}.webp"
    p1 = RAW_DIR_ID / fn
    p2 = RAW_DIR_ALIAS / fn
    download_file(url, p1)
    if not p2.exists():
        import shutil
        shutil.copy2(p1, p2)

print("\n=== 3. Generating Transparent Cutouts via rembg ===")
session = rembg.new_session()

cutout_targets = [
    ("sku_black.webp", "redmi_black.png"),
    ("sku_white.webp", "redmi_white.png"),
    ("sku_blue.webp", "redmi_blue.png"),
    ("gallery_00.webp", "redmi_clean_cutout.png")
]

for src_name, out_name in cutout_targets:
    src_file = RAW_DIR_ID / src_name
    out_file = CUTOUTS_DIR / out_name
    print(f"Processing cutout: {src_name} -> {out_name}...")
    with Image.open(src_file) as im:
        im_rgba = im.convert("RGBA")
        output = rembg.remove(im_rgba, session=session)
        # Crop transparent bounding box
        bbox = output.getbbox()
        if bbox:
            output = output.crop(bbox)
        output.save(out_file, format="PNG")
        print(f"  Saved {out_file.name}: size={output.size}, bbox={bbox}")

print("\n=== 4. Verifying Assets in Studio ===")
cutout_files = list(CUTOUTS_DIR.glob("*.png"))
print(f"Total cutouts generated: {len(cutout_files)}")
for cf in cutout_files:
    with Image.open(cf) as im:
        print(f"  {cf.name}: {im.size}, mode={im.mode}")

print("\nAll assets prepared successfully!")
