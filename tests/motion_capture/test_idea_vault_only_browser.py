"""Idea-only Producer route keeps existing notes, uploads and channel ownership."""
import base64
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.parametrize("width", [390, 1440])
def test_idea_vault_only_save_image_reload_and_channel_isolation(motion_fixture_url, width):
    parsed = urlsplit(motion_fixture_url)
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ7sAAAAASUVORK5CYII=")
    notes = {"main": [{"id": "old-note", "text": "Existing preserved idea", "tag": "Hook"}], "second": []}
    writes, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": 1000}, ignore_https_errors=True)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("localStorage.setItem('capcut_active_tab','producer');localStorage.setItem('omnicut.ui_mode','desktop');")
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            def api(route):
                path = urlsplit(route.request.url).path
                owner = route.request.headers.get("x-omnicut-channel", "main")
                if path.endswith("ref-fixture.png"):
                    route.fulfill(status=200, content_type="image/png", body=png)
                    return
                if path == "/api/channels":
                    data = {"revision": 1, "channels": [{"id": c, "display_name": c, "status": "active", "revision": 1} for c in notes]}
                elif path == "/api/products":
                    data = {"products": [{"id": "product-" + owner, "name": "Fixture product", "channel_id": owner, "angles": []}]}
                elif path in ("/api/producer/notes", "/api/producer/notes/add"):
                    if route.request.method == "POST":
                        payload = route.request.post_data_json
                        notes[owner].insert(0, payload["note"])
                        writes.append((owner, path, payload))
                    data = {"success": True, "notes": notes[owner], "revision": "revision-" + owner + str(len(notes[owner]))}
                elif path == "/api/producer/upload-ref-media":
                    writes.append((owner, path, None))
                    data = {"success": True, "url": f"/api/producer/{owner}/ref-fixture.png"}
                else:
                    data = {"tasks": [], "items": [], "products": [], "exports": [], "videos": [], "catalog": {}, "milestones": [], "custom": []}
                route.fulfill(status=200, content_type="application/json", headers={} if path == "/api/channels" else {"X-OmniCut-Channel": owner}, body=json.dumps(data))
            page.route("**/api/**", api)
            page.goto(f"{parsed.scheme}://{parsed.netloc}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            heading = page.get_by_role("heading", name="คลังไอเดีย & เรฟ TikTok / Pinterest (Idea & Ref Vault)", exact=True)
            expect(heading).to_be_visible(timeout=15000)
            expect(page.get_by_text("Existing preserved idea", exact=True)).to_be_visible()
            for retired in ("เป้าหมายสัปดาห์นี้", "เป้าหมายตัดต่อวันนี้", "เป้าหมายโพสต์วันนี้", "ภารกิจอันดับ 1", "สิ่งที่ต้องทำวันนี้ (Daily Action Queue)"):
                expect(page.get_by_text(retired, exact=False)).to_have_count(0)
            expect(page.get_by_role("button", name="ตั้งค่าเป้าหมายการผลิต")).to_have_count(0)
            assert not writes
            page.get_by_placeholder("แปะลิงก์คลิปเรฟที่ชอบ", exact=False).fill("https://www.tiktok.com/@fixture/video/123")
            page.get_by_placeholder("เช่น เปิดด้วยภาพแช่แข็งมือถือ", exact=False).fill("New saved reference idea")
            page.locator('input[type="file"]').set_input_files({"name": "ref.png", "mimeType": "image/png", "buffer": png})
            expect(page.get_by_text("รูปภาพที่แนบ (1 รูป)", exact=True)).to_be_visible()
            page.get_by_role("button", name="บันทึกไอเดีย", exact=True).click()
            expect(page.get_by_text("New saved reference idea", exact=True)).to_be_visible()
            assert len(notes["main"]) == 2
            assert notes["main"][0]["images"] == ["/api/producer/main/ref-fixture.png"]
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_text("New saved reference idea", exact=True)).to_be_visible()
            expect(page.get_by_text("Existing preserved idea", exact=True)).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            if os.environ.get("IDEA_VAULT_REVIEW_DIR"):
                folder = Path(os.environ["IDEA_VAULT_REVIEW_DIR"])
                folder.mkdir(parents=True, exist_ok=True)
                heading.scroll_into_view_if_needed()
                page.screenshot(path=str(folder / ("mobile.png" if width == 390 else "desktop.png")), full_page=True)
            selector = page.get_by_role("combobox", name="เลือกช่อง", exact=True)
            selector.select_option("second")
            expect(selector).to_have_value("second")
            expect(page.get_by_text("New saved reference idea", exact=True)).to_have_count(0)
            selector.select_option("main")
            expect(page.get_by_text("New saved reference idea", exact=True)).to_be_visible()
            assert all(owner == "main" for owner, _, _ in writes) and not errors
        finally:
            browser.close()
