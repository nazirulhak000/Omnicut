"""Creative menu retired: persisted-tab migration and Tracker/Gallery remain usable."""
import json
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("saved_tab", ["creative", "gadget"])
@pytest.mark.parametrize("width,via_activity", [(390, False), (1440, False), (1440, True)])
def test_removed_creative_menu_migrates_saved_tab_and_preserves_tracker_gallery(motion_fixture_url, width, via_activity, saved_tab, populated):
    origin = urlsplit(motion_fixture_url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": 1000}, ignore_https_errors=True)
            errors, writes = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("localStorage.setItem('capcut_active_tab','creative');localStorage.setItem('omnicut.ui_mode','desktop');".replace("'creative'", json.dumps(saved_tab)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            def api(route):
                path = urlsplit(route.request.url).path
                owner = route.request.headers.get("x-omnicut-channel", "main")
                if route.request.method in {"POST", "PATCH", "DELETE"}:
                    writes.append(path)
                if path == "/api/channels":
                    data = {"revision": 1, "channels": [{"id": c, "display_name": c, "status": "active", "revision": 1} for c in ("main", "second")]}
                elif path == "/api/exports":
                    data = {"exports": [{"export_id": "existing-export", "name": "Gallery regression clip.mp4", "path": "04_Exports/gallery-regression.mp4", "rel_path": "04_Exports/gallery-regression.mp4", "channel_id": owner, "size_mb": 1, "is_latest": True}] if populated else []}
                elif path == "/api/products":
                    data = {"products": [{"id": "existing-product", "name": "Tracker existing product", "channel_id": owner,
                        "angles": [{"angle_id": "existing-angle", "status": "rendered", "qc_reviewed": True, "hook_title": "Existing tracker phase", "export_id": "existing-export"}]}]}
                elif path == "/api/tasks/active" and via_activity:
                    data = {"tasks": [{"id": "saved-hf-job", "type": "hyperframes_render", "title": "Existing HF job", "status": "processing", "channel_id": owner, "read_only_projection": True, "progress": None, "payload": {"project_id": "saved-hf-project", "channel_id": owner}}]}
                elif path == "/api/hyperframes/status":
                    data = {"ready": True, "installed": True, "cli_version": "offline-fixture"}
                else:
                    data = {"items": [], "exports": [], "tasks": [], "videos": [], "products": [], "styles": [], "compositions": [], "catalog": {}, "milestones": [], "custom": []}
                route.fulfill(status=200, headers={} if path == "/api/channels" else {"X-OmniCut-Channel": owner}, content_type="application/json", body=json.dumps(data))
            page.route("**/api/**", api)
            page.goto(f"{origin.scheme}://{origin.netloc}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            expect(page.get_by_text("Tracker existing product", exact=True).first).to_be_visible(timeout=15000)
            expect(page.get_by_title("3.1 Creative Studio", exact=True)).to_have_count(0)
            expect(page.get_by_text("Creative Studio", exact=True)).to_have_count(0)
            expect(page.get_by_title("Gadget Media", exact=True)).to_have_count(0)
            expect(page.get_by_text("Gadget Media", exact=True)).to_have_count(0)
            expect(page.get_by_text("3.1 HyperFrames Motion", exact=True)).to_have_count(0)
            assert page.evaluate("localStorage.getItem('capcut_active_tab')") == "tracker"
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            if width == 390:
                page.get_by_role("button", name="อื่นๆ", exact=True).click()
                expect(page.get_by_text("เมนูเพิ่มเติม", exact=True)).to_be_visible()
                expect(page.get_by_text("Creative", exact=True)).to_have_count(0)
                page.get_by_text("เมนูเพิ่มเติม", exact=True).locator("..").locator("..").get_by_role("button").click()
            if via_activity:
                page.get_by_title("คลิกเพื่อเปิดศูนย์ติดตามกิจกรรม (Activity Center)", exact=True).click()
                expect(page.get_by_text("Existing HF job", exact=True).first).to_be_visible()
                page.get_by_role("button", name="เปิด Tracker", exact=True).last.click()
            expect(page.get_by_text("Tracker existing product", exact=True).first).to_be_visible()
            assert page.evaluate("localStorage.getItem('capcut_active_tab')") == "tracker"
            if width == 390:
                page.get_by_role("button", name="Gallery", exact=True).click()
            else:
                page.get_by_title("4. Export Gallery", exact=True).click()
            page.wait_for_function("localStorage.getItem('capcut_active_tab') === 'gallery'")
            # Switching the tab happens before the lazy component finishes loading.
            # Await the actual gallery before checking errors (the old check raced it).
            expect(page.get_by_text(f"คลิปตัดเสร็จ ({1 if populated else 0})", exact=True)).to_be_visible(timeout=15000)
            if populated:
                expect(page.get_by_text("Gallery regression clip.mp4", exact=True).locator("visible=true").first).to_be_visible()
                page.get_by_title("โหมดสตูดิโอ 2 ฝั่ง (เลือกคลิปซ้าย ดู QC ขวา)", exact=True).click()
                expect(page.get_by_text("Gallery regression clip.mp4", exact=True).locator("visible=true").first).to_be_visible()
                page.get_by_title("โหมดตารางการ์ด 9:16 ทั้งหมด", exact=True).click()
                page.get_by_role("button", name="ดูรายละเอียด", exact=True).first.click()
                expect(page.get_by_role("dialog")).to_be_visible()
            else:
                expect(page.get_by_text("ยังไม่มีคลิปวิดีโอที่ตัดเสร็จในคลัง", exact=True)).to_be_visible()
            expect(page.get_by_text("เกิดข้อผิดพลาดที่ไม่คาดคิดในระบบ", exact=True)).to_have_count(0)
            assert not writes and not errors
        finally:
            browser.close()
