"""
Download Minimal & Aesthetic Thai Google Fonts for TikTok/CapCut
Downloads Mitr, IBM Plex Sans Thai, Chakra Petch, Noto Sans Thai, and Prompt.
"""

import os
import sys
import urllib.request
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass

FONTS_DIR = Path("02_Assets/Fonts")
FONTS_DIR.mkdir(parents=True, exist_ok=True)

FONTS_TO_DOWNLOAD = {
    # 1. Mitr (Minimal, Rounded, Friendly Aesthetic)
    "Mitr-SemiBold.ttf": "https://github.com/google/fonts/raw/main/ofl/mitr/Mitr-SemiBold.ttf",
    "Mitr-Medium.ttf": "https://github.com/google/fonts/raw/main/ofl/mitr/Mitr-Medium.ttf",
    "Mitr-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/mitr/Mitr-Bold.ttf",
    
    # 2. IBM Plex Sans Thai (Tech, Ultra-clean, Premium Minimal)
    "IBMPlexSansThai-SemiBold.ttf": "https://github.com/google/fonts/raw/main/ofl/ibmplexsansthai/IBMPlexSansThai-SemiBold.ttf",
    "IBMPlexSansThai-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/ibmplexsansthai/IBMPlexSansThai-Bold.ttf",
    "IBMPlexSansThai-Medium.ttf": "https://github.com/google/fonts/raw/main/ofl/ibmplexsansthai/IBMPlexSansThai-Medium.ttf",

    # 3. Chakra Petch (Sleek Tech & Cyber Minimal)
    "ChakraPetch-SemiBold.ttf": "https://github.com/google/fonts/raw/main/ofl/chakrapetch/ChakraPetch-SemiBold.ttf",
    "ChakraPetch-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/chakrapetch/ChakraPetch-Bold.ttf",

    # 4. Noto Sans Thai (Modern Crisp Minimal)
    "NotoSansThai-SemiBold.ttf": "https://github.com/google/fonts/raw/main/ofl/notosansthai/NotoSansThai%5Bwdth%2Cwght%5D.ttf"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

print("\n📦 Downloading Aesthetic & Minimal Thai Google Fonts...\n")

for font_name, url in FONTS_TO_DOWNLOAD.items():
    dest = FONTS_DIR / font_name
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  ✓ Already exists: {font_name}")
        continue
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            if len(content) > 1000:
                dest.write_bytes(content)
                print(f"  ✓ Downloaded: {font_name} ({len(content)/1024:.1f} KB)")
            else:
                print(f"  ✗ Failed (file too small): {font_name}")
    except Exception as e:
        print(f"  ✗ Error downloading {font_name}: {e}")

print("\n🎉 Font Library Download Finished!\n")
