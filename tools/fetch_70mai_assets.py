import argparse
import re
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET_DIR = PROJECT_ROOT / ".tmp" / "gadget_products" / "70mai_(Xiaomi_Eco)_70mai_dash_cam_omni" / "photos"


def fetch_70mai_assets(target_dir: Path = None):
    if target_dir is None:
        target_dir = DEFAULT_TARGET_DIR

    target_dir.mkdir(parents=True, exist_ok=True)
    url = "https://70mai.store/products/omni"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        og = re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
        if og:
            img_url = og[0]
            if not img_url.startswith("http"):
                img_url = "https:" + img_url
            dest = target_dir / "poster_official_hero.jpg"
            urllib.request.urlretrieve(img_url, dest)
            print("70mai Hero saved:", dest.stat().st_size)

        shopify_imgs = set(re.findall(r'(?:https?:)?//cdn\.shopify\.com/s/files/[^\s"\'\(\)]+\.(?:jpg|png)', html))
        count = 0
        for s_url in sorted(shopify_imgs):
            if not s_url.startswith("http"):
                s_url = "https:" + s_url
            dest = target_dir / f"poster_feature_{count+1}.jpg"
            try:
                urllib.request.urlretrieve(s_url, dest)
                if dest.stat().st_size > 40000:
                    print(f"70mai Feature {count+1} saved:", dest.stat().st_size)
                    count += 1
                    if count >= 2:
                        break
                else:
                    dest.unlink()
            except Exception:
                pass
    except Exception as e:
        print("70mai error:", e)


def main():
    parser = argparse.ArgumentParser(description="Fetch 70mai assets")
    parser.add_argument("--target-dir", type=str, default=None, help="Target directory for 70mai photos")
    args = parser.parse_args()

    target = Path(args.target_dir) if args.target_dir else DEFAULT_TARGET_DIR
    fetch_70mai_assets(target_dir=target)


if __name__ == '__main__':
    main()
