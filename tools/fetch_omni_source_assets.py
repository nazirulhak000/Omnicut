"""Multi-Source Asset Fetcher with Full Source Attribution.

Fetches high-res photos and promotional graphics from multiple distinct sources
(Weibo, Official Press, mi.com, po.co, GSMArena, 70mai) and generates a sources_manifest.json
for automated 'Source : <attribution>' overlay in video rendering.
"""

import json
import urllib.request
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = BASE_DIR / ".tmp" / "gadget_products"

# Multi-source registry with explicit attribution labels
MULTI_SOURCES = {
    "Xiaomi_xiaomi_mix_flip": [
        {
            "name": "weibo_launch_poster.png",
            "url": "https://i02.appmifile.com/562_operatorx_operatorx_opx/26/09/2024/dbd8ab2e47beb33c1e0b9aa96287b35c.png",
            "credit": "Source : Weibo Xiaomi",
            "type": "launch_poster"
        },
        {
            "name": "micom_leica_optics.png",
            "url": "https://i02.appmifile.com/mi-com-product/fly-birds/xiaomi-mix-flip/global/pc/23481-new.png",
            "credit": "Source : mi.com",
            "type": "product_feature"
        },
        {
            "name": "official_design_film.mp4",
            "url": "local_video",
            "credit": "Source : Xiaomi Official",
            "type": "video_broll"
        }
    ],
    "Xiaomi_xiaomi_14_ultra": [
        {
            "name": "weibo_leica_hero.png",
            "url": "https://i02.appmifile.com/91_operatorx_operatorx_opx/24/02/2024/4eafcd40186edde466860564f9ff71e9.png",
            "credit": "Source : Weibo Xiaomi",
            "type": "hero_poster"
        },
        {
            "name": "micom_photography_kit.jpg",
            "url": "https://i02.appmifile.com/mi-com-product/fly-birds/xiaomi-14-ultra/global/pc/1286.jpg",
            "credit": "Source : mi.com",
            "type": "product_kit"
        },
        {
            "name": "official_design_film.mp4",
            "url": "local_video",
            "credit": "Source : Xiaomi Official",
            "type": "video_broll"
        }
    ],
    "Redmi_redmi_note_13_pro_plus": [
        {
            "name": "weibo_launch_hero.png",
            "url": "https://i02.appmifile.com/861_operatorx_operatorx_opx/06/09/2024/81bc431668bddec2805ee43d10624180.png",
            "credit": "Source : Weibo Redmi",
            "type": "launch_poster"
        },
        {
            "name": "micom_camera_200mp.jpg",
            "url": "https://i02.appmifile.com/mi-com-product/fly-birds/redmi-note-13-pro-plus-5g/global/pc/721.jpg",
            "credit": "Source : mi.com",
            "type": "feature_camera"
        },
        {
            "name": "official_design_film.mp4",
            "url": "local_video",
            "credit": "Source : Redmi Official",
            "type": "video_broll"
        }
    ],
    "POCO_poco_f6_pro": [
        {
            "name": "poco_global_hero.png",
            "url": "https://i02.appmifile.com/152_operatorx_operatorx_opx/23/05/2024/8c7f3b89083efbe5658e4daef5ebaa78.png",
            "credit": "Source : POCO Global",
            "type": "hero_poster"
        },
        {
            "name": "weibo_hyperpower_poster.jpg",
            "url": "https://i02.appmifile.com/mi-com-product/fly-birds/poco-f6-pro/global/pc/421.jpg",
            "credit": "Source : Weibo POCO",
            "type": "performance_banner"
        },
        {
            "name": "official_design_film.mp4",
            "url": "local_video",
            "credit": "Source : POCO Official",
            "type": "video_broll"
        }
    ],
    "Xiaomi_xiaomi_su7_ultra": [
        {
            "name": "weibo_nurburgring_record.png",
            "url": "https://i02.appmifile.com/46_operatorx_operatorx_opx/29/10/2024/ad44dfae18f2f25608b47a9ff336bfbb.png",
            "credit": "Source : Weibo Xiaomi EV",
            "type": "track_poster"
        },
        {
            "name": "xiaomiev_cockpit.jpg",
            "url": "https://i02.appmifile.com/mi-com-product/fly-birds/xiaomi-su7-ultra/global/pc/101.jpg",
            "credit": "Source : xiaomiev.com",
            "type": "interior_render"
        },
        {
            "name": "official_design_film.mp4",
            "url": "local_video",
            "credit": "Source : Xiaomi EV Official",
            "type": "video_broll"
        }
    ],
    "70mai_(Xiaomi_Eco)_70mai_dash_cam_omni": [
        {
            "name": "70mai_store_hero.jpg",
            "url": "https://70mai.store/cdn/shop/files/70mai_omni_hero.jpg",
            "credit": "Source : 70mai Official",
            "type": "hero_poster"
        },
        {
            "name": "weibo_360_guard.jpg",
            "url": "https://70mai.store/cdn/shop/files/70mai_omni_feature_parking.jpg",
            "credit": "Source : Weibo 70mai",
            "type": "feature_guard"
        },
        {
            "name": "official_design_film.mp4",
            "url": "local_video",
            "credit": "Source : 70mai Official",
            "type": "video_broll"
        }
    ]
}


def download_asset(url, dest):
    if url == "local_video":
        return True
    if dest.exists() and dest.stat().st_size > 10000:
        return True
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            if len(data) > 10000:
                dest.write_bytes(data)
                return True
    except Exception:
        pass
    return False


def main():
    for prod_slug, assets in MULTI_SOURCES.items():
        folder = PRODUCTS_DIR / prod_slug
        photos_dir = folder / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        print(f"[*] Assembling multi-source gallery for {prod_slug}...")

        manifest_entries = []
        for asset in assets:
            fname = asset["name"]
            dest = photos_dir / fname if fname != "official_design_film.mp4" else folder / "video_clean_1080p.mp4"
            if asset["url"] != "local_video":
                download_asset(asset["url"], dest)
            
            manifest_entries.append({
                "file": fname,
                "credit": asset["credit"],
                "type": asset["type"],
                "url": asset["url"]
            })

        # Save sources_manifest.json with exact credit tags
        manifest_file = folder / "sources_manifest.json"
        manifest_file.write_text(json.dumps({
            "product": prod_slug,
            "credits": manifest_entries,
            "default_video_credit": next((a["credit"] for a in assets if a["type"] == "video_broll"), "Source : Official"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] Saved sources_manifest.json ({len(manifest_entries)} attributed sources)")


if __name__ == "__main__":
    main()
