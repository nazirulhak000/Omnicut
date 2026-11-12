"""Gallery sharpness state: a clip sharpened in place after its render shows as done. All APIs offline."""
import json
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ENHANCE = "/api/exports/enhance-tiktok"
DONE = "คมชัดระดับ TikTok แล้ว"
TODO = "ปรับความคมชัด TikTok"
REFUSED = "คลิปนี้ปรับความคมชัด TikTok แล้วตั้งแต่ตอนเรนเดอร์ ไม่ต้องปรับซ้ำ"


def _clip(key, name, hook, **extra):
    return {"channel_id": "main", "export_id": f"e_{key}", "product_id": "p", "angle_id": f"a_{key}",
            "name": name, "path": f"04_Exports/main/{name}", "rel_path": f"04_Exports/main/{name}",
            "hook_title": hook, "product_name": "Fixture", "status": "rendered", **extra}


CLIPS = [
    _clip("auto", "20261112_auto_hook_v1.mp4", "Sharpened after render", tiktok_enhanced=True, timestamp=300),
    _clip("plain", "20261111_plain_hook_v1.mp4", "Rendered before the change", tiktok_enhanced=False, timestamp=200),
    _clip("copy", "20261110_copy_hook_v1_tiktok_sharp.mp4", "Manual copy", timestamp=100),
]


def test_gallery_shows_in_place_sharpened_clips_as_done_and_reports_a_refused_pass(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    errors, writes = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, ignore_https_errors=True)
            page.set_default_timeout(8000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script(
                "localStorage.setItem('capcut_active_tab','gallery');"
                "localStorage.setItem('omnicut_export_gallery_view_mode','grid');")

            def api(route):
                request = route.request
                url = urlsplit(request.url)
                if url.path.startswith("/api/media/"):
                    route.fulfill(status=404, body="offline fixture media")
                    return
                if request.method != "GET":
                    writes.append((url.path, request.post_data_json))
                    if url.path == ENHANCE:
                        # what the backend answers when the listing on screen is stale
                        route.fulfill(status=409, content_type="application/json",
                                      body=json.dumps({"detail": REFUSED}))
                        return
                if url.path == "/api/channels":
                    data = {"revision": 1, "channels": [
                        {"id": "main", "display_name": "main", "status": "active", "revision": 1}]}
                elif url.path == "/api/exports":
                    data = {"exports": CLIPS}
                elif url.path == "/api/status":
                    data = {"mobile_url": origin}
                elif url.path == "/api/products":
                    data = {"products": [{"id": "p", "name": "Fixture", "angles": [
                        {"angle_id": clip["angle_id"], "export_id": clip["export_id"], "status": "rendered",
                         "video_url": clip["rel_path"]} for clip in CLIPS]}]}
                else:
                    data = {"items": [], "products": [], "exports": [], "tasks": [], "videos": [],
                            "catalog": {}, "custom": [], "milestones": []}
                route.fulfill(content_type="application/json", body=json.dumps(data))

            page.route("**/api/**", api)
            page.goto(f"{origin}/?mode=desktop", wait_until="domcontentloaded")
            gallery = page.get_by_title("4. Export Gallery", exact=True)
            try:
                expect(gallery).to_be_visible(timeout=5000)
            except AssertionError:
                raise AssertionError({"errors": errors, "body": page.locator("body").inner_text()[:3000]})
            gallery.click()
            menus = page.get_by_title("เมนูเพิ่มเติม (More Actions)", exact=True)
            expect(menus).to_have_count(len(CLIPS))
            # badge on the cards: the in-place clip and the manual copy, not the plain render
            expect(page.get_by_title("วิดีโอผ่านการปรับความคมชัดสำหรับ TikTok แล้ว", exact=True)).to_have_count(2)

            # the manual button lives in the studio (split) view workbench
            page.get_by_title("โหมดสตูดิโอ 2 ฝั่ง (เลือกคลิปซ้าย ดู QC ขวา)", exact=True).click()
            done = page.get_by_role("button", name=DONE, exact=True)
            todo = page.get_by_role("button", name=TODO, exact=True)
            # the state flips on every step, so a workbench that did not follow the selection cannot pass
            for hook, sharp in (("Sharpened after render", True), ("Rendered before the change", False),
                                ("Manual copy", True)):
                page.locator(f'text="{hook}" >> visible=true').first.click()
                if sharp:
                    expect(done).to_be_visible()
                    expect(done).to_be_disabled()
                    expect(todo).to_have_count(0)
                else:
                    expect(todo).to_be_enabled()
                    expect(done).to_have_count(0)
                    todo.click()
                    expect(page.get_by_text(REFUSED, exact=True)).to_be_visible()
                    expect(todo).to_be_enabled()

            # only the plain render could ask for a pass, with its own identity
            assert writes == [(ENHANCE, {"export_id": "e_plain", "path": "04_Exports/main/20261111_plain_hook_v1.mp4"})], writes
            assert not errors, errors
        finally:
            browser.close()
