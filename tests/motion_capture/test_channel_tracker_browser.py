"""Tracker QC note drafts per channel, QC server-failure retention and storage-blocked switch guard in the real App."""
import json
from urllib.parse import urlsplit, parse_qs

from playwright.sync_api import sync_playwright, expect


def test_tracker_qc_draft_survives_channel_switch_and_storage_block(motion_fixture_url):
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

            def open_qc_fail():
                # QC-fail lives in the card's "More Actions" dropdown (unslop rounds).
                page.get_by_title("เมนูเพิ่มเติม (More Actions)", exact=True).first.click()
                page.get_by_role("button", name="QC ไม่ผ่าน — ส่งตัดใหม่", exact=True).click()

            # The Tracker "ส่ง TikTok" caption draft + mobile-QR were removed in 6c8c9af (posting is
            # prepared from Export Gallery, whose QR owner is covered by test_channel_gallery_browser.py).
            expect(page.get_by_title("เมนูเพิ่มเติม (More Actions)", exact=True).first).to_be_visible(timeout=15000)
            page.get_by_title("คลิกเพื่อพรีวิวคลิปเต็ม",exact=True).first.click()
            page.get_by_role("button",name="QC ผ่าน (เป็นสีฟ้า)",exact=True).click()
            expect(page.get_by_text("ไม่สามารถอัปเดตสถานะได้:",exact=False)).to_be_visible()
            expect(page.get_by_role("button",name="QC ผ่าน (เป็นสีฟ้า)",exact=True)).to_be_visible()
            expect(page.get_by_text("QC ผ่านเรียบร้อยแล้ว!",exact=False)).to_have_count(0)
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            # Server failure retains the QC note/modal and channel-owned draft.
            open_qc_fail()
            note=page.get_by_placeholder("เช่น เสียงพากย์เร็วเกินไป, ตัดจังหวะไม่เรียบร้อย, ข้อความตกขอบจอ")
            note.fill("Main failed QC private note")
            page.get_by_role("button",name="ยืนยันส่งตัดใหม่",exact=True).click()
            expect(note).to_have_value("Main failed QC private note")
            expect(page.get_by_text("ไม่สามารถอัปเดตสถานะได้:",exact=False)).to_be_visible()
            assert writes[-1][0]=="main" and writes[-1][2]["qc_note"]=="Main failed QC private note"
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            selector.select_option("second");expect(selector).to_have_value("second")
            open_qc_fail()
            expect(note).to_have_value("")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            selector.select_option("main");expect(selector).to_have_value("main")
            open_qc_fail()
            expect(note).to_have_value("Main failed QC private note")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            # Browser storage denial keeps a volatile draft and blocks save-switch.
            page.evaluate("""() => { window.trackerSetItem=Storage.prototype.setItem;
                Storage.prototype.setItem=function(key,value){
                    if(this===localStorage && key.endsWith(':tracker.manualDrafts')) throw new Error('fixture draft storage blocked');
                    return window.trackerSetItem.call(this,key,value);
                }; }""")
            open_qc_fail()
            note.fill("Main volatile storage-blocked draft")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            selector.select_option("second")
            switch=page.get_by_role("dialog",name="บันทึกก่อนสลับช่อง")
            switch.get_by_role("button",name="บันทึกและสลับ",exact=True).click()
            expect(switch.get_by_role("alert")).to_contain_text("fixture draft storage blocked")
            expect(selector).to_have_value("main")
            switch.get_by_role("button",name="ทิ้งการแก้ไขและสลับ",exact=True).click()
            expect(selector).to_have_value("second")
            page.evaluate("() => { Storage.prototype.setItem=window.trackerSetItem; }")
            open_qc_fail()
            expect(note).to_have_value("")
            page.get_by_role("button",name="ปิดหน้าต่าง",exact=True).click()
            assert not errors
            assert all(parse_qs(urlsplit(src).query).get("channel") == ["second"] for src in page.locator("video").evaluate_all("els=>els.map(el=>el.getAttribute('src'))"))
        finally:
            browser.close()
