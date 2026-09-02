import urllib.request
from pathlib import Path

FONTS_DIR = Path("d:/Winona/Programmer/Capcut/02_Assets/Fonts")
FONTS_DIR.mkdir(parents=True, exist_ok=True)

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

print("Downloading new distinct Thai fonts...")
for fname, url in NEW_FONTS.items():
    dest = FONTS_DIR / fname
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
