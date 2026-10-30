import os
import sys
import json
import urllib.request
from pathlib import Path
from PIL import Image
import rembg

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "_Docs"
RAW_DIR = ROOT / "01_Raw" / "cde38b1c07e54ea69a3d50a6c1bb3f18" / "img"
STUDIO_ASSETS = ROOT / "03_Projects" / "_HyperFrames_Studio" / "assets" / "hatari02" / "img"

RAW_DIR.mkdir(parents=True, exist_ok=True)
STUDIO_ASSETS.mkdir(parents=True, exist_ok=True)

# 1. Load product metadata
products_file = DOCS_DIR / "products.json"
products = json.loads(products_file.read_text(encoding="utf-8"))
p = next(p for p in products if p.get("id") == "cde38b1c07e54ea69a3d50a6c1bb3f18")

print(f"Product: {p.get('name')}")
images_list = p.get("images", [])
print(f"Found {len(images_list)} official images")

downloaded_files = []
for i, img in enumerate(images_list):
    url = img["url"].replace("&amp;", "&")
    raw_dest = RAW_DIR / f"hatari_official_{i}.webp"
    studio_dest = STUDIO_ASSETS / f"img_{i}.webp"
    
    if not raw_dest.exists() or raw_dest.stat().st_size == 0:
        print(f"  Downloading image {i} -> {raw_dest.name} ...")
        urllib.request.urlretrieve(url, raw_dest)
    
    # Copy to studio assets
    studio_dest.write_bytes(raw_dest.read_bytes())
    downloaded_files.append(raw_dest)
    print(f"  Saved {studio_dest.name} ({raw_dest.stat().st_size} bytes)")

# 2. Generate Transparent Hero Cutout from White Fan (img_3.webp)
hero_src = STUDIO_ASSETS / "img_3.webp"
cutout_dest = STUDIO_ASSETS / "hatari_cyclone_clean_cutout.png"
raw_cutout_dest = RAW_DIR / "hatari_cyclone_clean_cutout.png"

print("\n⚡ Processing Transparent Hero Cutout with rembg...")
with open(hero_src, "rb") as f_in:
    input_bytes = f_in.read()

output_bytes = rembg.remove(input_bytes)
cutout_dest.write_bytes(output_bytes)
raw_cutout_dest.write_bytes(output_bytes)

# Verify cutout image
img_cut = Image.open(cutout_dest)
print(f"✅ Cutout created successfully: {cutout_dest.name} ({img_cut.size}, mode={img_cut.mode})")

# Also resize/pad to a square 630x630 hero cutout with soft shadow if needed, or maintain clean alpha
img_cut_rgba = img_cut.convert("RGBA")
bbox = img_cut_rgba.getbbox()
if bbox:
    cropped = img_cut_rgba.crop(bbox)
    # Fit into 630x630 keeping aspect ratio
    max_dim = max(cropped.size)
    scale = 600.0 / max_dim
    new_w = int(cropped.width * scale)
    new_h = int(cropped.height * scale)
    resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    canvas = Image.new("RGBA", (630, 630), (0, 0, 0, 0))
    pos_x = (630 - new_w) // 2
    pos_y = (630 - new_h) // 2
    canvas.paste(resized, (pos_x, pos_y), resized)
    canvas.save(cutout_dest, "PNG")
    canvas.save(raw_cutout_dest, "PNG")
    print(f"✅ Hero Cutout 630x630 ready: {cutout_dest} ({cutout_dest.stat().st_size} bytes)")

print("\n🎉 Asset Preparation Completed Successfully!")
