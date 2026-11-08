"""
Capture live screenshots of OmniCut Pro Studio from https://localhost:5173
and copy to the artifact directory for user inspection.
"""
import os
import sys
import time
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ARTIFACT_DIR = Path(r"C:\Users\nazir\AppData\Roaming\AntigravityProfiles\Profile3\.gemini\antigravity\brain\b77e5ea7-30df-42da-82cc-823331993d51")
OUTPUT_DIR = Path("_Docs/Reports/live_snapshot")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = [
    {"name": "live_desktop_01_product_flow", "tab": "flow", "viewport": {"width": 1440, "height": 900}, "title": "สินค้า → คลิป (Obsidian Dark)"},
    {"name": "live_desktop_02_editor", "tab": "editor", "viewport": {"width": 1440, "height": 900}, "title": "ห้องตัดต่อ Editor"},
    {"name": "live_desktop_03_tracker", "tab": "tracker", "viewport": {"width": 1440, "height": 900}, "title": "Content Tracker 4 เฟส"},
    {"name": "live_desktop_04_assets", "tab": "assets", "viewport": {"width": 1440, "height": 900}, "title": "Media Assets Hub"},
    {"name": "live_desktop_05_analytics", "tab": "analytics", "viewport": {"width": 1440, "height": 900}, "title": "Analytics & Statistics Hub"},
    {"name": "live_mobile_01_product_flow", "tab": "flow", "viewport": {"width": 390, "height": 844}, "title": "Mobile: สินค้า → คลิป"},
    {"name": "live_mobile_02_editor", "tab": "editor", "viewport": {"width": 390, "height": 844}, "title": "Mobile: Editor Navbar & Controls"},
]

def capture():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for item in TARGETS:
            vp = item["viewport"]
            context = browser.new_context(
                viewport=vp,
                ignore_https_errors=True,
                is_mobile=(vp["width"] < 600),
            )
            page = context.new_page()
            url = f"https://localhost:5173/?tab={item['tab']}"
            print(f"Capturing {item['name']} ({vp['width']}x{vp['height']})...")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                print(f"Error loading {url}: {e}")
            time.sleep(2.5)

            out_file = OUTPUT_DIR / f"{item['name']}.png"
            page.screenshot(path=str(out_file), full_page=False)
            
            # Copy to artifact directory
            art_file = ARTIFACT_DIR / f"{item['name']}.png"
            shutil.copyfile(str(out_file), str(art_file))
            print(f"Saved: {out_file} -> {art_file}")
            results.append({
                "name": item["name"],
                "title": item["title"],
                "path": str(art_file).replace("\\", "/"),
                "bytes": os.path.getsize(out_file)
            })
            context.close()
        browser.close()
    return results

if __name__ == "__main__":
    res = capture()
    print(f"Done. Captured {len(res)} screenshots.")
