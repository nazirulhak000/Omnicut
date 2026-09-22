import os
from pathlib import Path

photos_dir = Path(r".tmp/Products/Xiaomi_MIX_Flip/01_Raw/photos")
for p in sorted(photos_dir.glob("*.*")):
    print(f"{p.name} ({p.stat().st_size / 1024:.1f} KB)")
