import argparse
import re
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PHOTOS_DIR = PROJECT_ROOT / ".tmp" / "gadget_products" / "Xiaomi_xiaomi_mix_flip" / "photos"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

URLS = [
    'https://www.mi.com/global/product/xiaomi-mix-flip/',
    'https://www.gsmarena.com/xiaomi_mix_flip-review-2729p2.php',
    'https://www.gsmarena.com/xiaomi_mix_flip-review-2729p3.php',
    'https://www.gsmarena.com/xiaomi_mix_flip-review-2729p5.php'
]


def scrape_official_mi_assets(photos_dir: Path = None) -> int:
    if photos_dir is None:
        photos_dir = DEFAULT_PHOTOS_DIR

    photos_dir.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for url in URLS:
        print(f"Scraping {url}...")
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')

            # find image links
            img_candidates = re.findall(r'https://[^\s"\'\)<>]+(?:\.jpg|\.png|\.webp)', html)
            print(f"Found {len(img_candidates)} raw image links on {url}")

            for u in set(img_candidates):
                # filter for relevant images
                u_clean = u.split('?')[0]
                is_relevant = any(k in u_clean.lower() for k in [
                    'mix-flip', 'mix_flip', 'xiaomi', 'appmifile', 'gsmarena'
                ]) and not any(bad in u_clean.lower() for bad in ['vivo', 'poco', 'logo', 'icon', 'banner', 'avatar'])

                if is_relevant and ('reviews/24/xiaomi-mix-flip' in u_clean or 'appmifile' in u_clean):
                    fname = f"asset_{abs(hash(u_clean)) % 100000}_{Path(u_clean).name}"
                    out_path = photos_dir / fname
                    if not out_path.exists():
                        try:
                            r = urllib.request.Request(u, headers=HEADERS)
                            data = urllib.request.urlopen(r, timeout=10).read()
                            if len(data) > 30000:  # at least 30KB
                                out_path.write_bytes(data)
                                saved_count += 1
                                print(f"Saved: {fname} ({len(data)} bytes)")
                        except Exception:
                            pass
        except Exception as e:
            print(f"Failed {url}: {e}")

    print(f"\nFinished! Total new high-res photos saved: {saved_count}")
    return saved_count


def main():
    parser = argparse.ArgumentParser(description="Scrape official Xiaomi Mix Flip assets")
    parser.add_argument("--photos-dir", type=str, default=None, help="Target photos directory")
    args = parser.parse_args()

    target = Path(args.photos_dir) if args.photos_dir else DEFAULT_PHOTOS_DIR
    scrape_official_mi_assets(photos_dir=target)


if __name__ == '__main__':
    main()
