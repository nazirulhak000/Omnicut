#!/usr/bin/env python3
"""
Open TikTok Browser Profile for 1-time manual login without automated test banner.
Cookies and session are saved in tools/tiktok_browser_profile for OmniCut scraper.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

def open_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] Playwright is not installed. Run: pip install playwright && playwright install chromium")
        return

    profile_dir = BASE_DIR / "tools" / "tiktok_browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    print(f"[*] Opening TikTok browser profile at: {profile_dir}")
    print("[*] Please log in to your TikTok account or solve any challenge.")
    print("[*] Once logged in, close the browser window. Session will be saved automatically.")

    stealth_args = [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--lang=th-TH,th",
        "--start-maximized",
    ]

    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                str(profile_dir),
                channel="chrome",
                headless=False,
                ignore_default_args=["--enable-automation"],
                args=stealth_args,
                viewport=None,
            )
        except Exception:
            context = p.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,
                ignore_default_args=["--enable-automation"],
                args=stealth_args,
                viewport=None,
            )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.tiktok.com", wait_until="domcontentloaded")

        # Keep open until page is closed by user
        try:
            page.wait_for_timeout(300000)  # 5 minutes max
        except Exception:
            pass
        finally:
            try:
                context.close()
            except Exception:
                pass
    print("[✓] Session saved successfully in tools/tiktok_browser_profile!")

if __name__ == "__main__":
    open_browser()
