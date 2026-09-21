"""Optimized Official Marketing Poster Fetcher.

Downloads authentic marketing posters and product renders from official brand pages (mi.com, po.co).
"""

import json
import re
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = BASE_DIR / ".tmp" / "gadget_products"

PRODUCT_PAGES = {
    "Xiaomi_MIX_Flip": "https://www.mi.com/global/product/xiaomi-mix-flip/",
    "Xiaomi_xiaomi_14_ultra": "https://www.mi.com/global/product/xiaomi-14-ultra/",
    "Xiaomi_xiaomi_14": "https://www.mi.com/global/product/xiaomi-14/",
    "Xiaomi_xiaomi_17_ultra": "https://www.mi.com/global/product/xiaomi-14-ultra/",
    "Xiaomi_xiaomi_17t_series": "https://www.mi.com/global/product/xiaomi-14t-pro/",
    "Redmi_redmi_note_13_pro_plus": "https://www.mi.com/global/product/redmi-note-13-pro-plus-5g/",
    "POCO_poco_f6_pro": "https://www.po.co/global/product/poco-f6-pro/",
    "POCO_poco_x6_pro": "https://www.po.co/global/product/poco-x6-pro/",
    "Xiaomi_xiaomi_smart_band_9": "https://www.mi.com/global/product/xiaomi-smart-band-9/",
    "Xiaomi_xiaomi_smart_band_9_pro": "https://www.mi.com/global/product/xiaomi-smart-band-9-pro/",
    "Xiaomi_xiaomi_watch_s4": "https://www.mi.com/global/product/xiaomi-watch-s3/",
    "Xiaomi_xiaomi_robot_vacuum_x20_max": "https://www.mi.com/global/product/xiaomi-robot-vacuum-x20-max/",
    "Xiaomi_xiaomi_robot_vacuum_5_pro": "https://www.mi.com/global/product/xiaomi-robot-vacuum-x10-plus/",
    "Xiaomi_xiaomi_smart_air_purifier_4": "https://www.mi.com/global/product/xiaomi-smart-air-purifier-4/",
    "Xiaomi_xiaomi_air_compressor_2": "https://www.mi.com/global/product/xiaomi-portable-electric-air-compressor-2/",
    "Xiaomi_xiaomi_pet_feeder_2": "https://www.mi.com/global/product/xiaomi-smart-pet-feeder-2/",
    "Xiaomi_xiaomi_buds_5_pro": "https://www.mi.com/global/product/xiaomi-buds-5/",
    "Redmi_redmi_buds_5_pro": "https://www.mi.com/global/product/redmi-buds-5-pro/",
    "Xiaomi_xiaomi_scooter_4_ultra": "https://www.mi.com/global/product/xiaomi-electric-scooter-4-ultra/",
    "Xiaomi_xiaomi_pad_8": "https://www.mi.com/global/product/xiaomi-pad-6/",
    "Xiaomi_mi_smart_air_fryer": "https://www.mi.com/global/product/mi-smart-air-fryer-3.5l/",
    "Xiaomi_xiaomi_smart_camera_c701": "https://www.mi.com/global/product/xiaomi-smart-camera-c500-pro/",
    "Xiaomi_xiaomi_su7_ultra": "https://www.mi.com/global/discover/article?id=3555",
}


def download_url(url, dest_file):
    if not url.startswith("http"):
        url = "https:" + url
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
            if len(data) > 20000:
                dest_file.write_bytes(data)
                return True
    except Exception:
        pass
    return False


def fetch_for_product(folder_name, url):
    dest_dir = PRODUCTS_DIR / folder_name / "photos"
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Processing posters for {folder_name}...", flush=True)

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [!] Failed to load {url}: {e}", flush=True)
        return

    # 1. Look for og:image
    og_imgs = re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not og_imgs:
        og_imgs = re.findall(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
    
    if og_imgs:
        ext = ".png" if ".png" in og_imgs[0] else ".jpg"
        hero_dest = dest_dir / f"poster_official_hero{ext}"
        if not hero_dest.exists():
            if download_url(og_imgs[0], hero_dest):
                print(f"  [OK] Downloaded Hero Poster: {hero_dest.name} ({hero_dest.stat().st_size} bytes)", flush=True)

    # 2. Look for JSON-LD product images
    ld_matches = re.findall(r'<script type="application/ld\+json">({.*?})</script>', html, re.DOTALL)
    ld_imgs = []
    for m in ld_matches:
        try:
            data = json.loads(m)
            if "image" in data:
                img_val = data["image"]
                if isinstance(img_val, list):
                    ld_imgs.extend(img_val)
                elif isinstance(img_val, str):
                    ld_imgs.append(img_val)
        except Exception:
            pass

    for idx, img_url in enumerate(ld_imgs[:2]):
        ext = ".png" if ".png" in img_url else ".jpg"
        dest_file = dest_dir / f"poster_product_render_{idx+1}{ext}"
        if not dest_file.exists():
            if download_url(img_url, dest_file):
                print(f"  [OK] Downloaded Product Render: {dest_file.name} ({dest_file.stat().st_size} bytes)", flush=True)

    # 3. Look for large feature banners (fly-birds or pc graphics)
    banners = re.findall(r'(?:https?:)?//[^\s"\'\(\)]+appmifile\.com/[^\s"\'\(\)]+/(?:pc|fly-birds|products|overview)/[^\s"\'\(\)]+\.(?:png|jpg)', html)
    saved_banners = 0
    for b_url in set(banners):
        if "play-btn" in b_url or "favicon" in b_url or "logo" in b_url:
            continue
        ext = ".png" if b_url.endswith(".png") else ".jpg"
        dest_banner = dest_dir / f"poster_feature_banner_{saved_banners+1}{ext}"
        if not dest_banner.exists():
            if download_url(b_url, dest_banner):
                print(f"  [OK] Downloaded Feature Banner: {dest_banner.name} ({dest_banner.stat().st_size} bytes)", flush=True)
                saved_banners += 1
                if saved_banners >= 2:
                    break


def main():
    for folder, url in PRODUCT_PAGES.items():
        fetch_for_product(folder, url)
    print("[ALL DONE] Marketing posters downloaded.", flush=True)


if __name__ == "__main__":
    main()
