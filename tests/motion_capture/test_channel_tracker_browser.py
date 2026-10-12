"""Tracker draft retention and native file carriers in the real App."""
import json
from urllib.parse import urlsplit, parse_qs

from playwright.sync_api import sync_playwright, expect


def test_tracker_post_draft_survives_channel_switch_and_qr_keeps_owner(motion_fixture_url):
    url = urlsplit(motion_fixture_url)
    origin = f"{url.scheme}://{url.netloc}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, ignore_https_errors=True)
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("localStorage.setItem('capcut_active_tab','tracker');localStorage.setItem('omnicut.uiMode','desktop');")
            errors, writes = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def api(route):
                path = urlsplit(route.request.url).path
                owner = route.request.headers.get("x-omnicut-channel", "main")
                if route.request.method in {"PATCH","POST"} and path.startswith("/api/products/"):
                    writes.append((owner,path,route.request.post_data_json))
                    route.fulfill(status=503,content_type="application/json",headers={"X-OmniCut-Channel":owner},body='{"detail":"fixture QC save unavailable"}')
                    return
                if path == "/api/channels":
                    data = {"revision": 1, "channels": [{"id": name, "display_name": name, "status": "active", "revision": 1} for name in ["main", "second"]]}
                elif path == "/api/products":
                    data = {"products": [{"id": "prod", "name": "Fixture product", "angles": [{"angle_id": "angle", "status": "rendered", "qc_reviewed": True, "export_id": "same-export", "hook_title": "Fixture hook", "video_url": f"04_Exports/{owner}/clip.mp4"}]}]}
                else:
                    data = {"items": [], "exports": [], "tasks": [], "videos": [], "products": [], "catalog": {}, "milestones": [], "custom": []}
                route.fulfill(content_type="application/json", headers={} if path == "/api/channels" else {"X-OmniCut-Channel": owner}, body=json.dumps(data))

            page.route("**/api/**", api)
            page.goto(f"{origin}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            post = page.get_by_role("button", name="ส่ง TikTok", exact=True).first
            try:
                expect(post).to_be_visible(timeout=15000)
            except AssertionError:
                raise AssertionError({"errors": errors, "body": page.locator("body").inner_text()[:3000]})
            post.click()
            caption = page.get_by_placeholder("เขียนแคปชั่นดึงดูดใจ...")
            caption.fill("Main private draft")
            selector.select_option("second")
            page.get_by_role("button", name="ส่ง TikTok", exact=True).first.click()
            expect(caption).not_to_have_value("Main private draft")
            caption.fill("Second private draft")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            page.get_by_title("ดูตัวอย่างบนมือถือ (QR Code)",exact=True).first.click()
            href=page.get_by_role("link",name="ทดสอบเปิดหน้านี้บนเบราว์เซอร์นี้").get_attribute("href")
            qr=parse_qs(urlsplit(href).query)
            assert qr["channel"]==["second"] and qr["eid"]==["same-export"] and qr["pid"]==["prod"]
            assert qr["video"]==["04_Exports/second/clip.mp4"]
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            selector.select_option("main")
            page.get_by_role("button", name="ส่ง TikTok", exact=True).first.click()
            expect(caption).to_have_value("Main private draft")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            page.get_by_title("คลิกเพื่อพรีวิวคลิปเต็ม",exact=True).first.click()
            page.get_by_role("button",name="QC ผ่าน (เป็นสีฟ้า)",exact=True).click()
            expect(page.get_by_text("ไม่สามารถอัปเดตสถานะได้:",exact=False)).to_be_visible()
            expect(page.get_by_role("button",name="QC ผ่าน (เป็นสีฟ้า)",exact=True)).to_be_visible()
            expect(page.get_by_text("QC ผ่านเรียบร้อยแล้ว!",exact=False)).to_have_count(0)
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            # Server failure retains the QC note/modal and channel-owned draft.
            page.get_by_title("QC ไม่ผ่าน -- ส่งตัดใหม่",exact=True).first.click()
            note=page.get_by_placeholder("เช่น เสียงพากย์เร็วเกินไป, ตัดจังหวะไม่เรียบร้อย, ข้อความตกขอบจอ")
            note.fill("Main failed QC private note")
            page.get_by_role("button",name="ยืนยันส่งตัดใหม่",exact=True).click()
            expect(note).to_have_value("Main failed QC private note")
            expect(page.get_by_text("ไม่สามารถอัปเดตสถานะได้:",exact=False)).to_be_visible()
            assert writes[-1][0]=="main" and writes[-1][2]["qc_note"]=="Main failed QC private note"
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            selector.select_option("second");expect(selector).to_have_value("second")
            page.get_by_title("QC ไม่ผ่าน -- ส่งตัดใหม่",exact=True).first.click()
            expect(note).to_have_value("")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            selector.select_option("main");expect(selector).to_have_value("main")
            page.get_by_title("QC ไม่ผ่าน -- ส่งตัดใหม่",exact=True).first.click()
            expect(note).to_have_value("Main failed QC private note")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            # Browser storage denial keeps a volatile draft and blocks save-switch.
            page.evaluate("""() => { window.trackerSetItem=Storage.prototype.setItem;
                Storage.prototype.setItem=function(key,value){
                    if(this===localStorage && key.endsWith(':tracker.manualDrafts')) throw new Error('fixture draft storage blocked');
                    return window.trackerSetItem.call(this,key,value);
                }; }""")
            page.get_by_role("button",name="ส่ง TikTok",exact=True).first.click()
            caption.fill("Main volatile storage-blocked draft")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            selector.select_option("second")
            switch=page.get_by_role("dialog",name="บันทึกก่อนสลับช่อง")
            switch.get_by_role("button",name="บันทึกและสลับ",exact=True).click()
            expect(switch.get_by_role("alert")).to_contain_text("fixture draft storage blocked")
            expect(selector).to_have_value("main")
            switch.get_by_role("button",name="ทิ้งการแก้ไขและสลับ",exact=True).click()
            expect(selector).to_have_value("second")
            page.evaluate("() => { Storage.prototype.setItem=window.trackerSetItem; }")
            page.get_by_role("button",name="ส่ง TikTok",exact=True).first.click()
            expect(caption).to_have_value("Second private draft")
            assert not errors
            assert all(parse_qs(urlsplit(src).query).get("channel") == ["second"] for src in page.locator("video").evaluate_all("els=>els.map(el=>el.getAttribute('src'))"))
        finally:
            browser.close()
