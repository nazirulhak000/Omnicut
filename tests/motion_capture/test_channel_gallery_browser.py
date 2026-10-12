"""Real secondary Gallery native carriers and decoded QR; all APIs are offline."""
import json
from urllib.parse import parse_qs, urlsplit

import cv2
import numpy as np
from playwright.sync_api import expect, sync_playwright


def test_secondary_gallery_preview_download_cover_and_qr_keep_channel(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    media_reads, errors, writes = [], [], []
    clip = {"channel_id": "second", "export_id": "e", "product_id": "p", "angle_id": "a",
            "name": "clip.mp4", "path": "04_Exports/second/clip.mp4", "rel_path": "04_Exports/second/clip.mp4",
            "cover_path": "05_Covers_Thumbnails/second/cover.jpg", "hook_title": "Fixture hook",
            "product_name": "Fixture", "is_latest": True, "status": "rendered"}
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
                if request.method != "GET":
                    writes.append((owner, url.path))
                if url.path.startswith("/api/media/"):
                    if "/04_Exports/" in url.path or "/05_Covers_Thumbnails/" in url.path:
                        media_reads.append((url.path, parse_qs(url.query)))
                    route.fulfill(status=404, body="offline fixture media")
                    return
                if url.path == "/api/channels":
                    data = {"revision": 1, "channels": [{"id": name, "display_name": name, "status": "active", "revision": 1} for name in ["main", "second"]]}
                elif url.path == "/api/exports":
                    data = {"exports": [{**clip, "channel_id": owner, "path": f"04_Exports/{owner}/clip.mp4", "rel_path": f"04_Exports/{owner}/clip.mp4", "cover_path": f"05_Covers_Thumbnails/{owner}/cover.jpg"}]}
                elif url.path == "/api/status":
                    data = {"mobile_url": origin}
                elif url.path == "/api/products":
                    data = {"products": [{"id": "p", "name": "Fixture", "angles": [{"angle_id": "a", "export_id": "e", "status": "rendered", "video_url": clip["rel_path"]}]}]}
                else:
                    data = {"items": [], "products": [], "exports": [], "tasks": [], "videos": [], "catalog": {}, "custom": [], "milestones": []}
                route.fulfill(content_type="application/json", headers={} if url.path == '/api/channels' else {"X-OmniCut-Channel": owner}, body=json.dumps(data))

            page.route("**/api/**", api)
            page.goto(f"{origin}/?channel=second&mode=desktop", wait_until="domcontentloaded")
            expect(page.get_by_role("combobox", name="เลือกช่อง")).to_have_value("second")
            gallery = page.get_by_title("4. Export Gallery", exact=True)
            try:
                expect(gallery).to_be_visible(timeout=5000)
            except AssertionError:
                raise AssertionError({"errors": errors, "body": page.locator("body").inner_text()[:3000]})
            gallery.click()
            page.get_by_role("button", name="ดูรายละเอียด", exact=True).click()
            dialog = page.get_by_role("dialog").filter(has=page.get_by_role("heading", name="Fixture hook", exact=True))
            expect(dialog.locator("video")).to_have_count(1)
            assert parse_qs(urlsplit(dialog.locator("video").get_attribute("src")).query)["channel"] == ["second"]
            downloads = dialog.locator("a[download]").evaluate_all("els=>els.map(el=>el.href)")
            assert any("04_Exports" in href for href in downloads)
            assert any("05_Covers_Thumbnails" in href for href in downloads)
            assert all(parse_qs(urlsplit(href).query).get("channel") == ["second"] for href in downloads)
            cover = dialog.get_by_role("img", name="ปก 9:16")
            assert parse_qs(urlsplit(cover.get_attribute("src")).query)["channel"] == ["second"]
            qr = dialog.locator("svg[width='150'][height='150']")
            expect(qr).to_have_count(1)
            qr.evaluate("el=>{el.setAttribute('width','512');el.setAttribute('height','512')}")
            png = dialog.locator("svg[width='512'][height='512']").screenshot()
            image = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_COLOR)
            image = cv2.copyMakeBorder(image, 32, 32, 32, 32, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            qr_url, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
            assert qr_url, "Rendered Gallery QR must be decodable"
            query = parse_qs(urlsplit(qr_url).query)
            assert query["channel"] == ["second"] and query["eid"] == ["e"]
            assert media_reads and all(query.get("channel") == ["second"] for _, query in media_reads)
            dialog.get_by_role("button", name="ปิดหน้าต่าง").click()
            page.get_by_role("button", name="สตูดิโอ 2 ฝั่ง", exact=False).click()
            labels = page.get_by_role("button", name="ใส่ข้อความบนปก (ไม่บังคับ)", exact=True)
            try:
                expect(labels).to_be_visible(timeout=3000)
            except AssertionError:
                raise AssertionError({"errors": errors, "body": page.locator("body").inner_text()[-3000:]})
            labels.click()
            page.get_by_placeholder("แบรนด์", exact=True).fill("Second brand")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            selector.select_option("main")
            page.get_by_title("4. Export Gallery", exact=True).click()
            page.get_by_role("button", name="ใส่ข้อความบนปก (ไม่บังคับ)", exact=True).click()
            expect(page.get_by_placeholder("แบรนด์", exact=True)).to_have_value("")
            page.get_by_placeholder("แบรนด์", exact=True).fill("Main brand")
            selector.select_option("second")
            page.get_by_role("button", name="ใส่ข้อความบนปก (ไม่บังคับ)", exact=True).click()
            expect(page.get_by_placeholder("แบรนด์", exact=True)).to_have_value("Second brand")
            page.evaluate("""() => { window.originalStorageSet=Storage.prototype.setItem;
              Storage.prototype.setItem=function(key,value){if(String(key).includes('gallery_cover_labels')) throw new Error('fixture storage unavailable'); return window.originalStorageSet.call(this,key,value)}; }""")
            page.get_by_placeholder("ป้ายท้าย", exact=True).fill("Unsaved label")
            expect(page.get_by_role("alert")).to_contain_text("เก็บข้อความบนปกไม่สำเร็จ")
            selector.select_option("main")
            switch = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            switch.get_by_role("button", name="บันทึกและสลับ").click()
            expect(switch.get_by_role("alert")).to_contain_text("fixture storage unavailable")
            expect(selector).to_have_value("second")
            page.evaluate("() => { Storage.prototype.setItem=window.originalStorageSet; }")
            switch.get_by_role("button", name="บันทึกและสลับ").click()
            expect(selector).to_have_value("main")
            selector.select_option("second")
            page.get_by_role("button", name="ใส่ข้อความบนปก (ไม่บังคับ)", exact=True).click()
            expect(page.get_by_placeholder("ป้ายท้าย", exact=True)).to_have_value("Unsaved label")
            page.evaluate("""() => { Storage.prototype.setItem=function(key,value){
              if(String(key).includes('gallery_cover_labels')) throw new Error('fixture storage unavailable');
              return window.originalStorageSet.call(this,key,value)}; }""")
            page.get_by_placeholder("ป้ายท้าย", exact=True).fill("Discard this edit")
            selector.select_option("main")
            switch.get_by_role("button", name="ทิ้งการแก้ไขและสลับ").click()
            expect(selector).to_have_value("main")
            page.evaluate("() => { Storage.prototype.setItem=window.originalStorageSet; }")
            selector.select_option("second")
            page.get_by_role("button", name="ใส่ข้อความบนปก (ไม่บังคับ)", exact=True).click()
            expect(page.get_by_placeholder("ป้ายท้าย", exact=True)).to_have_value("Unsaved label")
            assert not writes, "Cover-label caching and channel switching must never generate or post"
            # Open the actual decoded QR, with an explicitly foreign native
            # carrier. QuickPost must refuse it before a main media request.
            foreign = qr_url.replace("video=04_Exports%2Fsecond%2Fclip.mp4", "video=%2Fapi%2Fmedia%2F04_Exports%2Fsecond%2Fclip.mp4%3Fchannel%3Dmain")
            assert foreign != qr_url
            before = len(media_reads)
            page.goto(foreign, wait_until="domcontentloaded")
            expect(page.get_by_role("alert")).to_contain_text("ลิงก์ไฟล์ไม่ตรงกับช่องนี้")
            expect(page.locator("video")).to_have_count(0)
            assert len(media_reads) == before
            assert not errors
        finally:
            browser.close()
