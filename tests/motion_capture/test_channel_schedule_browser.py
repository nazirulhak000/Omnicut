"""Real App/Hub/Schedule/Provider channel switching with offline API fixtures."""
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.parametrize("width", [390, 1440])
def test_schedule_template_failed_save_and_pending_discard_are_channel_fenced(motion_fixture_url, width):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    channels = [{"id": owner, "display_name": owner, "handle": f"@{owner}", "status": "active", "revision": 1}
                for owner in ["main", "second"]]
    writes, reads, pending = [], [], []
    hold = {"enabled": False, "fail": True}
    stored = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": 900}, ignore_https_errors=True)
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("""localStorage.setItem('capcut_active_tab','tracker');
              localStorage.setItem('omnicut.ui_mode','desktop');
              localStorage.setItem('capcut_tracker_view_mode','schedule');""")

            def route_api(route):
                request = route.request
                url = urlsplit(request.url)
                owner = request.headers.get("x-omnicut-channel", "main")
                headers = {"X-OmniCut-Channel": owner}
                if url.path == "/api/schedule-queue/template" and request.method == "PUT":
                    writes.append((owner, request.post_data_json))
                    if hold["enabled"]:
                        pending.append(route)
                    elif not hold["fail"]:
                        stored[owner] = request.post_data_json
                        route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(stored[owner]))
                    else:
                        route.fulfill(status=503, headers=headers, content_type="application/json", body='{"detail":"fixture save unavailable"}')
                    return
                if url.path == "/api/channels":
                    result = {"channels": channels, "revision": 1}
                elif url.path == "/api/schedule-queue/template":
                    reads.append(owner)
                    week = parse_qs(url.query).get("week_start", ["2026-10-05"])[0]
                    result = {"week_start": week, "days": {str(i): {"enabled": True, "times": ["09:00", "12:30", "16:00", "19:00", "21:30"]} for i in range(7)}}
                    if owner in stored:
                        result = stored[owner]
                elif url.path == "/api/products":
                    result = {"products": []}
                elif url.path == "/api/assets/all":
                    result = {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []}
                else:
                    result = {"items": [], "products": [], "projects": [], "videos": [], "exports": [], "tasks": [], "milestones": [], "custom": [], "catalog": {}}
                route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(result))

            page.route("**/api/**", route_api)
            page.goto(f"{origin}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            expect(selector).to_be_visible()

            def open_template():
                page.get_by_role("button", name="เมนูเพิ่มเติม", exact=True).click()
                page.get_by_role("menuitem", name="ตั้งค่าเวลารายสัปดาห์").click()
                dialog = page.get_by_role("dialog").filter(has=page.get_by_role("heading", name="ตั้งค่าเวลารายสัปดาห์", exact=True))
                expect(dialog).to_be_visible()
                expect(dialog.get_by_role("button", name="บันทึกเทมเพลต")).to_be_enabled()
                return dialog

            template = open_template()
            template.get_by_role("combobox").first.select_option("08:00")
            template.get_by_role("button", name="ปิดหน้าต่าง").click()
            selector.select_option("second")
            switch = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            expect(switch).to_be_visible()
            switch.get_by_role("button", name="บันทึกและสลับ").click()
            expect(switch.get_by_role("alert")).to_contain_text("fixture save unavailable")
            expect(selector).to_have_value("main")
            assert writes[0][0] == "main"
            assert writes[0][1]["days"]["0"]["times"][0] == "08:00"
            switch.get_by_role("button", name="อยู่ช่องเดิม").click()
            template = open_template()
            expect(template.get_by_role("combobox").first).to_have_value("08:00")
            hold["enabled"] = True
            template.get_by_role("button", name="บันทึกเทมเพลต").click()
            expect(template.get_by_role("button", name="บันทึกเทมเพลต")).to_be_disabled()
            template.get_by_role("button", name="ปิดหน้าต่าง").click()
            selector.select_option("second")
            switch.get_by_role("button", name="ทิ้งการแก้ไขและสลับ").click()
            expect(selector).to_have_value("main")
            expect(switch.get_by_role("button", name="ทิ้งการแก้ไขและสลับ")).to_be_disabled()
            assert len(pending) == 1
            pending.pop().fulfill(status=503, headers={"X-OmniCut-Channel": "main"}, content_type="application/json", body='{"detail":"fixture delayed save unavailable"}')
            expect(selector).to_have_value("second")
            selector.select_option("main")
            template = open_template()
            expect(template.get_by_role("combobox").first).to_have_value("09:00")
            template.get_by_role("combobox").first.select_option("07:00")
            template.get_by_role("button", name="ปิดหน้าต่าง").click()
            hold.update(enabled=False, fail=False)
            selector.select_option("second")
            switch.get_by_role("button", name="บันทึกและสลับ").click()
            expect(selector).to_have_value("second")
            assert stored["main"]["days"]["0"]["times"][0] == "07:00"
            selector.select_option("main")
            template = open_template()
            expect(template.get_by_role("combobox").first).to_have_value("07:00")
            assert "second" in reads
            assert all(owner == "main" for owner, _ in writes)
            assert errors == []
        finally:
            browser.close()


def test_schedule_bulk_stale_preview_cannot_submit_after_queue_refresh(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    queue, writes, errors = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900}, ignore_https_errors=True)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("localStorage.setItem('capcut_active_tab','tracker');localStorage.setItem('capcut_tracker_view_mode','schedule');")

            def api(route):
                request = route.request
                path = urlsplit(request.url).path
                owner = request.headers.get("x-omnicut-channel", "main")
                if request.method != "GET":
                    writes.append((owner, path, request.post_data_json))
                if path == "/api/channels":
                    data = {"revision": 1, "channels": [{"id": name, "display_name": name, "status": "active", "revision": 1} for name in ["main", "second"]]}
                elif path == "/api/products":
                    data = {"products": [{"id": "prod", "name": "Fixture product", "angles": [{"angle_id": "angle", "status": "rendered", "export_id": "fixture-export", "hook_title": "Fixture hook", "video_url": "04_Exports/main/clip.mp4"}]}]}
                elif path == "/api/schedule-queue":
                    data = {"items": queue}
                else:
                    data = {"items": [], "exports": [], "tasks": [], "videos": [], "products": [], "catalog": {}, "milestones": [], "custom": []}
                route.fulfill(content_type="application/json", headers={"X-OmniCut-Channel": owner}, body=json.dumps(data))

            page.route("**/api/**", api)
            page.goto(f"{origin}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            page.get_by_role("button", name="เพิ่มเป็นชุด", exact=True).click()
            bulk = page.get_by_role("dialog").filter(has=page.get_by_role("heading", name="เพิ่มคลิปเป็นชุด", exact=True))
            bulk.get_by_role("checkbox").check()
            expect(bulk.get_by_text("ตัวอย่างคิวที่จะบันทึก (1)", exact=True)).to_be_visible()
            bulk.get_by_role("button", name="ปิดหน้าต่าง").click()
            queue.append({"id": "already-queued", "export_id": "fixture-export", "video_path": "04_Exports/main/clip.mp4", "scheduled_at": "2026-10-12T09:00:00+07:00", "status": "scheduled"})
            page.get_by_role("button", name="เมนูเพิ่มเติม", exact=True).click()
            with page.expect_response(lambda response: urlsplit(response.url).path == "/api/schedule-queue"):
                page.get_by_role("menuitem", name="รีเฟรชคิว", exact=True).click()
            page.get_by_role("button", name="เพิ่มเป็นชุด", exact=True).click()
            expect(bulk.get_by_text("ไม่มีคลิปที่ว่างสำหรับจัดคิว", exact=True)).to_be_visible()
            expect(bulk.get_by_text("ตัวอย่างคิวที่จะบันทึก (1)", exact=True)).to_be_visible()
            bulk.get_by_role("button", name="ปิดหน้าต่าง").click()
            selector.select_option("second")
            switch = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            switch.get_by_role("button", name="บันทึกและสลับ").click()
            expect(switch.get_by_role("alert")).to_contain_text("รายการคลิปเปลี่ยนแล้ว")
            expect(selector).to_have_value("main")
            assert not writes
            switch.get_by_role("button", name="ทิ้งการแก้ไขและสลับ").click()
            expect(selector).to_have_value("second")
            assert not errors
        finally:
            browser.close()
