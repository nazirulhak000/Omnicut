"""
Phase 00 Baseline Screenshot Capture Tool
Captures live UI states from https://localhost:5173 across desktop and mobile viewports.
"""
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("_Docs/Reports/baseline_phase00")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    {"name": "desktop_01_product_to_clip", "tab": "product-to-clip", "viewport": {"width": 1440, "height": 900}},
    {"name": "desktop_02_editor", "tab": "editor", "viewport": {"width": 1440, "height": 900}},
    {"name": "desktop_03_tracker", "tab": "tracker", "viewport": {"width": 1440, "height": 900}},
    {"name": "desktop_04_assets", "tab": "assets", "viewport": {"width": 1440, "height": 900}},
    {"name": "desktop_05_analytics", "tab": "analytics", "viewport": {"width": 1440, "height": 900}},
    {"name": "desktop_06_settings", "tab": "settings", "viewport": {"width": 1440, "height": 900}},
    {"name": "mobile_01_product_to_clip", "tab": "product-to-clip", "viewport": {"width": 390, "height": 844}},
    {"name": "mobile_02_tracker", "tab": "tracker", "viewport": {"width": 390, "height": 844}},
    {"name": "mobile_03_editor", "tab": "editor", "viewport": {"width": 390, "height": 844}},
]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for item in PAGES:
            vp = item["viewport"]
            context = browser.new_context(
                viewport=vp,
                ignore_https_errors=True,
                is_mobile=(vp["width"] < 600),
            )
            page = context.new_page()
            url = f"https://localhost:5173/?tab={item['tab']}"
            print(f"Capturing {item['name']} from {url} ({vp['width']}x{vp['height']})...")
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception as e:
                print(f"Network idle timeout on {url}, continuing after wait... ({e})")
            time.sleep(2)
            out_path = OUTPUT_DIR / f"{item['name']}.png"
            page.screenshot(path=str(out_path), full_page=False)
            print(f"Saved: {out_path} ({os.path.getsize(out_path)} bytes)")
            context.close()
        browser.close()
    print("All baseline screenshots captured successfully.")

if __name__ == "__main__":
    main()
