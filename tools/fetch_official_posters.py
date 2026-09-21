"""Fetch official marketing posters, press kit images, and product renders for Xiaomi Ecosystem products."""

import re
import urllib.request
import urllib.parse
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = BASE_DIR / ".tmp" / "gadget_products"

# Curated Official Marketing & Poster Asset Registry from mi.com, po.co, xiaomiev.com, 70mai
OFFICIAL_ASSETS = {
    "Xiaomi_MIX_Flip": [
        {
            "name": "poster_official_launch.png",
            "url": "https://i02.appmifile.com/562_operatorx_operatorx_opx/26/09/2024/dbd8ab2e47beb33c1e0b9aa96287b35c.png",
            "type": "official_render"
        },
        {
            "name": "poster_outer_display.png",
            "url": "https://i02.appmifile.com/398_operatorx_operatorx_opx/19/07/2024/09cfaadca7b5da7992cb918dfdf649f8.png",
            "type": "feature_infographic"
        },
        {
            "name": "poster_leica_optics.png",
            "url": "https://i02.appmifile.com/562_operatorx_operatorx_opx/19/07/2024/29bf6d65426b3a0fe11e74a8dbbcceb8.png",
            "type": "marketing_poster"
        }
    ],
    "Xiaomi_xiaomi_14_ultra": [
        {
            "name": "poster_official_hero.png",
            "url": "https://i02.appmifile.com/91_operatorx_operatorx_opx/24/02/2024/4eafcd40186edde466860564f9ff71e9.png",
            "type": "hero_poster"
        },
        {
            "name": "poster_photography_kit.png",
            "url": "https://i02.appmifile.com/830_operatorx_operatorx_opx/24/02/2024/e98be60251787c89736c920bf05bca4f.png",
            "type": "feature_poster"
        },
        {
            "name": "poster_leica_summilux.png",
            "url": "https://i02.appmifile.com/593_operatorx_operatorx_opx/24/02/2024/fa92a8316dfc64c8d5a1532f50684f88.png",
            "type": "camera_sensor_poster"
        }
    ],
    "Xiaomi_xiaomi_su7_ultra": [
        {
            "name": "poster_su7_ultra_track.png",
            "url": "https://i02.appmifile.com/46_operatorx_operatorx_opx/29/10/2024/ad44dfae18f2f25608b47a9ff336bfbb.png",
            "type": "official_poster"
        },
        {
            "name": "poster_su7_carbon_aero.png",
            "url": "https://i02.appmifile.com/264_operatorx_operatorx_opx/29/10/2024/ee3ec57564d787a718712e132890ff4f.png",
            "type": "feature_infographic"
        }
    ],
    "Redmi_redmi_note_13_pro_plus": [
        {
            "name": "poster_redmi_note_13_pro_plus_hero.png",
            "url": "https://i02.appmifile.com/225_operatorx_operatorx_opx/15/01/2024/a35f79a941efc1b824a7372d80c05877.png",
            "type": "hero_poster"
        },
        {
            "name": "poster_200mp_camera.png",
            "url": "https://i02.appmifile.com/805_operatorx_operatorx_opx/15/01/2024/918c5095817d3b55bc328905391216bc.png",
            "type": "feature_poster"
        }
    ],
    "POCO_poco_f6_pro": [
        {
            "name": "poster_poco_f6_pro_hero.png",
            "url": "https://i02.appmifile.com/152_operatorx_operatorx_opx/23/05/2024/8c7f3b89083efbe5658e4daef5ebaa78.png",
            "type": "hero_poster"
        },
        {
            "name": "poster_snapdragon_8_gen_2.png",
            "url": "https://i02.appmifile.com/978_operatorx_operatorx_opx/23/05/2024/2f2fa8a13a7e583e7ffdfbcf6e4eebe8.png",
            "type": "performance_poster"
        }
    ],
    "POCO_poco_x6_pro": [
        {
            "name": "poster_poco_x6_pro_hero.png",
            "url": "https://i02.appmifile.com/13_operatorx_operatorx_opx/11/01/2024/3cb1c1d8c1c548ea23ecad941a87b926.png",
            "type": "hero_poster"
        },
        {
            "name": "poster_dimensity_8300_ultra.png",
            "url": "https://i02.appmifile.com/463_operatorx_operatorx_opx/11/01/2024/2baef84218eb85c678a9cbb3d94cb0ea.png",
            "type": "gaming_poster"
        }
    ],
    "Xiaomi_xiaomi_smart_band_9": [
        {
            "name": "poster_smart_band_9_hero.png",
            "url": "https://i02.appmifile.com/264_operatorx_operatorx_opx/15/08/2024/3160a34b22c710d0a79744c8dc644485.png",
            "type": "hero_poster"
        }
    ]
}


def download_asset(url: str, target_path: Path):
    if target_path.exists() and target_path.stat().st_size > 1000:
        return True
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            target_path.write_bytes(data)
            return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def main():
    for prod_folder, assets in OFFICIAL_ASSETS.items():
        folder_path = PRODUCTS_DIR / prod_folder / "photos"
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"[*] Fetching marketing posters for {prod_folder}...")
        for asset in assets:
            dest = folder_path / asset["name"]
            ok = download_asset(asset["url"], dest)
            if ok:
                print(f"  [OK] Saved poster: {asset['name']} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
