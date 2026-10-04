import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = PROJECT_ROOT / "02_Assets" / "Fonts"

# Google Fonts Raw TTF URLs from google/fonts repo
NEW_FONTS = {
    "Anuphan-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/anuphan/Anuphan%5Bwght%5D.ttf",
    "Sarabun-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/sarabun/Sarabun-Bold.ttf",
    "Krub-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/krub/Krub-Bold.ttf",
    "Mali-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/mali/Mali-Bold.ttf",
    "Itim-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/itim/Itim-Regular.ttf",
    "Chonburi-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/chonburi/Chonburi-Regular.ttf",
    "BaiJamjuree-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/baijamjuree/BaiJamjuree-Bold.ttf",
    "Pridi-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/pridi/Pridi-Bold.ttf"
}


def download_fonts(target_dir: Path = None):
    if target_dir is None:
        target_dir = FONTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    print("Downloading new distinct Thai fonts...")
    for fname, url in NEW_FONTS.items():
        dest = target_dir / fname
        if not dest.exists() or dest.stat().st_size < 1000:
            try:
                print(f"Downloading {fname}...")
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp, open(dest, 'wb') as f:
                    f.write(resp.read())
                print(f"[OK] Downloaded {fname} ({dest.stat().st_size} bytes)")
            except Exception as e:
                print(f"[ERR] Failed {fname}: {e}")
        else:
            print(f"[OK] Already exists {fname}")

    print("Done downloading all fonts.")


if __name__ == '__main__':
    download_fonts()
