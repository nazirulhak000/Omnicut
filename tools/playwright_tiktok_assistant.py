import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = Path(__file__).resolve().parent / "tiktok_browser_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def run():
    print(f"[*] เปิดเบราว์เซอร์ Playwright (Persistent Profile: {PROFILE_DIR})...")
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                channel="chrome",
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
                viewport=None
            )
        except Exception:
            context = p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=False,
                args=["--start-maximized"],
                viewport=None
            )

        page = context.pages[0] if context.pages else context.new_page()
        print("[*] กำลังเปิดหน้า TikTok Studio Upload...")
        page.goto("https://www.tiktok.com/tiktokstudio/upload")

        print("=" * 60)
        print(">>> เบราว์เซอร์เปิดเรียบร้อยแล้ว!")
        print(">>> รบกวนพี่ล็อกอินบัญชี TikTok Studio บนหน้าต่างที่เปิดขึ้นมาได้เลยครับ")
        print(">>> ระบบจะเปิดค้างไว้ให้พี่ล็อกอินได้ตามสะดวกเลยครับ")
        print("=" * 60)

        while True:
            time.sleep(2)
            try:
                if page.is_closed():
                    print("[*] หน้าต่างเบราว์เซอร์ถูกปิดแล้ว")
                    break
            except Exception:
                break

if __name__ == "__main__":
    run()
