import argparse
import re
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PHOTOS_DIR = PROJECT_ROOT / ".tmp" / "gadget_products" / "Xiaomi_xiaomi_mix_flip" / "photos"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.gsmarena.com/'
}


def download_gsm_photos(photos_dir: Path = None):
    if photos_dir is None:
        photos_dir = DEFAULT_PHOTOS_DIR

    photos_dir.mkdir(parents=True, exist_ok=True)
    url = 'https://www.gsmarena.com/xiaomi_mix_flip-review-2729.php'
    print(f"Connecting to {url}...")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')

        # Extract all img and picture elements
        img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)
        print(f"Total img tags: {len(img_srcs)}")

        # Filter for xiaomi pics
        matches = [u for u in img_srcs if "xiaomi" in u or "reviews" in u or "pics" in u]
        unique_urls = list(set(matches))
        print(f"Filtered images: {len(unique_urls)}")

        downloaded = 0
        for u in unique_urls:
            if "thumb" in u or "-3.jpg" in u:
                highres_u = u.replace("-3.jpg", "-1.jpg").replace("/thumb/", "/")
            else:
                highres_u = u

            fname = highres_u.split('/')[-1]
            out_file = photos_dir / fname
            if not out_file.exists():
                try:
                    r_img = urllib.request.Request(highres_u, headers=HEADERS)
                    data = urllib.request.urlopen(r_img, timeout=10).read()
                    out_file.write_bytes(data)
                    downloaded += 1
                    print(f"Saved: {fname} ({len(data)} bytes)")
                except Exception:
                    try:
                        r_img2 = urllib.request.Request(u, headers=HEADERS)
                        data2 = urllib.request.urlopen(r_img2, timeout=10).read()
                        out_file.write_bytes(data2)
                        downloaded += 1
                        print(f"Saved fallback: {fname} ({len(data2)} bytes)")
                    except Exception:
                        pass
        print(f"Successfully downloaded {downloaded} GSMArena photos!")
    except Exception as e:
        print(f"Error fetching GSMArena: {e}")


def main():
    parser = argparse.ArgumentParser(description="Download GSMArena photos for Xiaomi Mix Flip")
    parser.add_argument("--photos-dir", type=str, default=None, help="Photos directory")
    args = parser.parse_args()

    target = Path(args.photos_dir) if args.photos_dir else DEFAULT_PHOTOS_DIR
    download_gsm_photos(photos_dir=target)


if __name__ == '__main__':
    main()
