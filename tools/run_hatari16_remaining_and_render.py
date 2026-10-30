#!/usr/bin/env python3
"""Run remaining Hatari 16" clips (s09-s20) production and full 20-clip parallel render."""
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

# UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

def main():
    print("=" * 68)
    print("🚀 [14:00 TRIGGER] STARTING HATARI 16\" REMAINING CLIPS (s09-s20)")
    print("=" * 68)

    # Step 1: Batch produce audio & compositions s09-s20
    print("\n[Step 1/3] Producing TTS Audio & Compositions for clips s09 to s20...")
    cmd_produce = [PY, "-u", str(ROOT / "tools" / "batch_produce_hatari_16inch_20.py"), "--start", "9", "--end", "20"]
    res_p = subprocess.run(cmd_produce, cwd=str(ROOT))
    if res_p.returncode != 0:
        print("⚠️ Produce had errors, but proceeding to render available compositions...")

    # Step 2: Multi-worker parallel render s01-s20 (Concurrency = 4)
    print("\n[Step 2/3] Multi-Worker Parallel Render s01 to s20 (Concurrency = 4)...")
    cmd_render = [PY, "-u", str(ROOT / "tools" / "batch_render_hatari16_20.py"), "--start", "1", "--end", "20", "--workers", "4"]
    res_r = subprocess.run(cmd_render, cwd=str(ROOT))

    # Step 3: Verify and summary
    print("\n[Step 3/3] Verifying final exports in 04_Exports/Ready_to_post/...")
    exports_dir = ROOT / "04_Exports" / "Ready_to_post"
    found = list(exports_dir.glob("*hat01-pov-s*.mp4"))
    print(f"✅ Total Hatari 16\" MP4 exports found: {len(found)}/20")
    for f in sorted(found):
        print(f"  - {f.name} ({round(f.stat().st_size / (1024*1024), 2)} MB)")

    print("\n" + "=" * 68)
    print("🎉 ALL HATARI 16\" PROCESSING FINISHED!")
    print("=" * 68)

if __name__ == "__main__":
    main()
