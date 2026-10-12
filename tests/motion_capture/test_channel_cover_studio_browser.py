"""Cover draft switch guard and native generated media in the real App, offline."""
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.parametrize("outcome", ["unsaved", "failed", "saved_with_newer_edit", "saved_clean"])
def test_cover_studio_draft_blocks_switch_without_rendering(motion_fixture_url, outcome):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    writes, errors, pending = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, ignore_https_errors=True)
            page.set_default_timeout(8000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("localStorage.setItem('capcut_active_tab','gallery');localStorage.setItem('omnicut_export_gallery_view_mode','grid');")

            def api(route):
                request = route.request
                url = urlsplit(request.url)
                owner = request.headers.get("x-omnicut-channel", "main")
                if url.path.startswith("/api/media/"):
                    route.fulfill(status=404, body="offline media")
                    return
                if url.path == "/api/channels":
                    data = {"revision": 1, "channels": [{"id": name, "display_name": name, "status": "active", "revision": 1} for name in ["main", "second"]]}
                elif url.path == "/api/exports":
                    data = {"exports": [{"channel_id": owner, "export_id": "e", "name": "clip.mp4", "path": f"04_Exports/{owner}/clip.mp4", "rel_path": f"04_Exports/{owner}/clip.mp4", "hook_title": "Fixture hook", "product_name": "Fixture", "is_latest": True, "status": "rendered"}]}
                elif url.path == "/api/covers/highlights":
                    data = {"duration": 15, "candidates": [{"timestamp": 0.5, "label": "Fixture candidate", "thumb_url": f"/api/media/05_Covers_Thumbnails/{owner}/candidate.jpg"}]}
                elif url.path == "/api/covers/render-pro":
                    writes.append((owner, request.post_data_json))
                    if outcome == "failed":
                        route.fulfill(status=503, content_type="application/json", headers={"X-OmniCut-Channel": owner}, body='{"detail":"fixture cover save failed"}')
                    else:
                        pending.append((route, owner))
                    return
                else:
                    data = {"items": [], "products": [], "exports": [], "tasks": [], "videos": [], "badges": [], "hooks": [], "raw_sources": [], "ref_images": [], "catalog": {}, "custom": [], "milestones": []}
                route.fulfill(content_type="application/json", headers={} if url.path == "/api/channels" else {"X-OmniCut-Channel": owner}, body=json.dumps(data))

            page.route("**/api/**", api)
            page.goto(f"{origin}/?channel=second&mode=desktop", wait_until="domcontentloaded")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            expect(selector).to_have_value("second")
            page.get_by_title("4. Export Gallery", exact=True).click()
            page.get_by_role("button", name="ดูรายละเอียด", exact=True).click()
            page.get_by_role("button", name="ปิดหน้าต่าง", exact=True).click()
            page.get_by_role("button", name="สตูดิโอ 2 ฝั่ง", exact=False).click()
            page.get_by_role("button", name="สตูดิโอทำปก 9:16", exact=True).click()
            expect(page.get_by_role("img", name="Fixture candidate", exact=True)).to_be_visible()
            candidate = page.get_by_role("img", name="Fixture candidate", exact=True).get_attribute("src")
            assert parse_qs(urlsplit(candidate).query)["channel"] == ["second"]
            page.get_by_label("2. ข้อความ Hook บนปก (AI Copy & Positioning)").check()
            note = page.get_by_placeholder("ใส่ข้อความ Hook บนปก...")
            note.fill("Second unsaved cover")
            if outcome != "unsaved":
                page.get_by_role("dialog", name="สตูดิโอสร้างปก").get_by_role("button", name="บันทึกทั้งสองขนาด (9:16 + 3:4)", exact=True).click()
                if outcome == "failed":
                    expect(page.get_by_text("fixture cover save failed", exact=False)).to_be_visible()
                else:
                    expect(page.get_by_role("button", name="กำลังบันทึกภาพปก...", exact=True)).to_be_visible()
                    expect(page.get_by_role("dialog", name="สตูดิโอสร้างปก").get_by_role("button", name="ยกเลิก", exact=True)).to_be_disabled()
                    selector.select_option("main", force=True)
                    busy_switch = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
                    busy_switch.get_by_role("button", name="ทิ้งการแก้ไขและสลับ").evaluate("el => el.click()")
                    expect(busy_switch.get_by_role("alert")).to_contain_text("รอให้การสร้างหรือบันทึกปกเสร็จ")
                    expect(selector).to_have_value("second")
                    busy_switch.get_by_role("button", name="อยู่ช่องเดิม").evaluate("el => el.click()")
                    # Inputs remain editable while awaiting the original owned request.
                    if outcome == "saved_with_newer_edit":
                        note.fill("Newer edit during cover save")
                    assert len(pending) == 1
                    route, owner = pending.pop()
                    route.fulfill(content_type="application/json", headers={"X-OmniCut-Channel": owner}, body=json.dumps({"success": True, "cover_path": f"05_Covers_Thumbnails/{owner}/saved.jpg", "media_url": f"/api/media/05_Covers_Thumbnails/{owner}/saved.jpg"}))
                    expect(page.get_by_text("บันทึกภาพปก (ทั้ง 9:16 และ 3:4) สำเร็จแล้ว!", exact=True)).to_be_visible()
                assert len(writes) == 1
                assert writes[0][0] == "second" and writes[0][1]["video_path"] == "04_Exports/second/clip.mp4"
                assert writes[0][1]["hook_text"] == "Second unsaved cover"
            if outcome == "saved_clean":
                # Committed and unchanged cover has no unload prompt or extra writes.
                page.reload(wait_until="domcontentloaded")
                expect(selector).to_have_value("second")
                assert len(writes) == 1 and not errors
                return
            expected_note = "Newer edit during cover save" if outcome == "saved_with_newer_edit" else "Second unsaved cover"
            # Native F5/reload confirmation is raised without performing any save.
            writes_before_reload = len(writes)
            with page.expect_event("dialog", timeout=8000) as unload:
                page.evaluate("() => { setTimeout(() => window.location.reload(), 0); }")
            assert unload.value.type == "beforeunload"
            unload.value.dismiss()
            expect(note).to_have_value(expected_note)
            expect(selector).to_have_value("second")
            assert len(writes) == writes_before_reload
            # A real close-click must disclose discarded work; declining preserves text.
            confirmations = []
            def decline(dialog):
                confirmations.append(dialog.message)
                dialog.dismiss()
            page.on("dialog", decline)
            page.get_by_role("dialog", name="สตูดิโอสร้างปก").get_by_role("button", name="เสร็จสิ้น" if outcome == "saved_with_newer_edit" else "ยกเลิก", exact=True).click()
            assert confirmations and "ทิ้งการแก้ไข" in confirmations[-1]
            expect(note).to_have_value(expected_note)
            # Programmatic selection uses the actual rendered selector despite modal overlay.
            selector.select_option("main", force=True)
            switch = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            expect(switch).to_be_visible()
            switch.get_by_role("button", name="บันทึกและสลับ").evaluate("el => el.click()")
            expect(switch.get_by_role("alert")).to_contain_text("บันทึกปกก่อนสลับช่อง")
            expect(selector).to_have_value("second")
            expect(note).to_have_value(expected_note)
            expected_writes = 0 if outcome == "unsaved" else 1
            assert len(writes) == expected_writes, "Channel switch must never auto render or generate AI"
            switch.get_by_role("button", name="ทิ้งการแก้ไขและสลับ").evaluate("el => el.click()")
            expect(selector).to_have_value("main")
            assert len(writes) == expected_writes and not errors
            # Explicitly discarded work no longer blocks a real reload.
            page.reload(wait_until="domcontentloaded")
            expect(selector).to_have_value("main")
            assert len(writes) == expected_writes and not errors
        finally:
            browser.close()
