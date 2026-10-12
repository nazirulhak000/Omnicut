"""Real QuickPost native-media ownership; all requests use isolated fixtures."""
import json
from urllib.parse import urlencode, urlsplit, parse_qs

import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.mark.parametrize("foreign", [False, True])
def test_secondary_quick_post_native_download_and_foreign_url_guard(motion_fixture_url, foreign):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    native = "/api/media/04_Exports/second/clip.mp4"
    media_reads = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 900}, ignore_https_errors=True)
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("""window.downloads=[];
                HTMLAnchorElement.prototype.click=function(){window.downloads.push(this.href)};""")

            def api(route):
                request = route.request
                path = urlsplit(request.url).path
                owner = request.headers.get("x-omnicut-channel", "main")
                if path == native:
                    media_reads.append(parse_qs(urlsplit(request.url).query))
                    route.fulfill(status=404, body="fixture media absent")
                    return
                if path == "/api/channels":
                    data = {"revision": 1, "channels": [
                        {"id": name, "display_name": name, "status": "active", "revision": 1}
                        for name in ["main", "second"]]}
                else:
                    data = {"products": [], "tasks": [], "items": []}
                route.fulfill(content_type="application/json", headers={} if path == "/api/channels" else {"X-OmniCut-Channel": owner}, body=json.dumps(data))

            page.route("**/api/**", api)
            video = native + ("?channel=main" if foreign else "")
            query = urlencode({"quick_post": "1", "channel": "second", "pid": "prod", "aid": "angle", "eid": "export", "video": video})
            page.goto(f"{origin}/?{query}", wait_until="domcontentloaded")
            expect(page.get_by_role("combobox", name="เลือกช่อง")).to_have_value("second")
            if foreign:
                expect(page.get_by_role("alert")).to_be_visible()
                expect(page.get_by_role("alert")).to_contain_text("ลิงก์ไฟล์ไม่ตรงกับช่องนี้")
                expect(page.locator("video")).to_have_count(0)
                assert not media_reads
            else:
                try:
                    expect(page.locator("video")).to_have_count(1)
                except AssertionError:
                    raise AssertionError(page.locator("body").inner_text()[:2200])
                assert parse_qs(urlsplit(page.locator("video").get_attribute("src")).query)["channel"] == ["second"]
                page.get_by_role("button", name="ดาวน์โหลดวิดีโอ MP4", exact=False).click()
                downloads = page.evaluate("window.downloads")
                assert len(downloads) == 1
                assert parse_qs(urlsplit(downloads[0]).query)["channel"] == ["second"]
                assert all(read.get("channel") == ["second"] for read in media_reads)
        finally:
            browser.close()


@pytest.mark.parametrize("case", ["missing_file","missing_export","rejected_unlinked","rejected_bound","newer_angle_posted"])
def test_quick_post_status_requires_exact_export_and_confirmed_server_effect(motion_fixture_url,case):
    parsed=urlsplit(motion_fixture_url)
    origin=f"{parsed.scheme}://{parsed.netloc}"
    writes,errors=[],[]
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={"width":390,"height":900},ignore_https_errors=True)
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**",lambda route:route.abort())
            page.route("https://fonts.gstatic.com/**",lambda route:route.abort())
            def api(route):
                request=route.request;path=urlsplit(request.url).path
                owner=request.headers.get("x-omnicut-channel","main")
                if path=="/api/exports/mark-posted":
                    writes.append((owner,request.post_data_json))
                    route.fulfill(status=503,content_type="application/json",headers={"X-OmniCut-Channel":owner},body='{"detail":"fixture post record unavailable"}')
                    return
                if path=="/api/channels":
                    data={"revision":1,"channels":[{"id":name,"display_name":name,"status":"active","revision":1} for name in ["main","second"]]}
                elif path=="/api/products" and case=="newer_angle_posted":
                    data={"products":[{"id":"prod","name":"Fixture product","angles":[{"angle_id":"angle","status":"posted","export_id":"newer-export","video_url":"04_Exports/second/newer.mp4"}]}]}
                else:data={"products":[],"tasks":[],"items":[]}
                route.fulfill(content_type="application/json",headers={} if path=="/api/channels" else {"X-OmniCut-Channel":owner},body=json.dumps(data))
            page.route("**/api/**",api)
            query={"quick_post":"1","channel":"second"}
            if case!="missing_file":query["video"]="04_Exports/second/clip.mp4"
            if case!="missing_export":query["eid"]="export"
            if case in {"rejected_bound","newer_angle_posted"}:query.update(pid="prod",aid="angle")
            page.goto(f"{origin}/?{urlencode(query)}",wait_until="domcontentloaded")
            button=page.get_by_role("button",name='5. มาร์กว่า "โพสต์ลง TikTok แล้ว"',exact=True)
            if case in {"missing_file","missing_export"}:
                expect(button).to_be_disabled()
                expect(page.get_by_role("alert")).to_contain_text("ไม่พบ export_id หรือไฟล์คลิป")
                assert not writes
            else:
                expect(button).to_be_enabled()
                button.click()
                expect(page.get_by_text("ไม่สามารถอัปเดตสถานะได้:",exact=False)).to_be_visible()
                expect(button).to_be_enabled()
                assert writes[0][0]=="second" and writes[0][1]["export_id"]=="export"
                assert writes[0][1]["file_path"]=="04_Exports/second/clip.mp4"
            expect(page.get_by_role("button",name="✓ โพสต์ลง TikTok เรียบร้อยแล้ว",exact=True)).to_have_count(0)
            assert not errors,errors
        finally:browser.close()
