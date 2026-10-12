"""Exact HyperFrames export cover selection survives Gallery reload (offline APIs)."""
import copy
import json
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.parametrize("prepare_view", ["split", "detail"])
@pytest.mark.parametrize("reload_after_save", [True, False])
@pytest.mark.parametrize("invalid_binding", [False, True])
def test_hf_cover_save_reload_prepare_keeps_exact_export_and_existing_queue(motion_fixture_url, prepare_view, invalid_binding, reload_after_save):
    url = urlsplit(motion_fixture_url)
    origin = f"{url.scheme}://{url.netloc}"
    selected_cover = "05_Covers_Thumbnails/second/cover-selection/hf_exact_cover_3x4.jpg"
    vertical_cover = "05_Covers_Thumbnails/second/cover-selection/hf_exact_cover.jpg"
    clip = {"channel_id": "second", "export_id": "hf-exact-export", "engine": "hyperframes",
            "product_id": "p", "angle_id": "a", "name": "hf_exact.mp4",
            "path": "04_Exports/second/hf_exact.mp4", "rel_path": "04_Exports/second/hf_exact.mp4",
            "hook_title": "Frozen HF fixture", "product_name": "Fixture", "is_latest": True,
            "status": "rendered", "cover_path": None, "tiktok_caption": "Frozen caption",
            "tiktok_hashtags": "#Frozen", "tiktok_product_id": "basket-exact"}
    if invalid_binding:
        clip["cover_selection_error"] = "export_cover_selection_changed"
    old_queue = {"id": "existing-queue", "export_id": clip["export_id"], "cover_path": None,
                 "revision": 3, "status": "planned", "channel_id": "second"}
    old_queue_before = copy.deepcopy(old_queue)
    writes, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, ignore_https_errors=True)
            page.set_default_timeout(10000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("""localStorage.setItem('capcut_active_tab','gallery');
              localStorage.setItem('omnicut.ui_mode','desktop');
              localStorage.setItem('omnicut_tiktok_autopost_enabled','true');
              localStorage.setItem('omnicut_export_gallery_view_mode','grid');
              window.open = () => null;""")

            def api(route):
                request = route.request
                path = urlsplit(request.url).path
                owner = request.headers.get("x-omnicut-channel", "main")
                headers = {"X-OmniCut-Channel": owner}
                if path.startswith("/api/media/"):
                    route.fulfill(status=404, body="offline fixture media")
                    return
                if request.method != "GET":
                    payload = request.post_data_json
                    writes.append((owner, path, payload))
                    if path == "/api/covers/render-pro":
                        assert owner == "second" and payload["export_id"] == clip["export_id"]
                        assert payload["video_path"] in (clip.get("path"), clip["rel_path"])
                        clip.update(cover_path=selected_cover, cover_url=f"/api/media/{selected_cover}")
                        clip.pop("cover_selection_error", None)
                        data = {"success": True, "cover_path": vertical_cover,
                                "cover_3x4_path": selected_cover, "media_url": f"/api/media/{selected_cover}"}
                    elif path == "/api/tiktok-autopost/prepare":
                        data = {"success": True, "job_id": "new-prepared-job"}
                    elif path in ("/api/covers/raw-sources", "/api/covers/product-ref-images"):
                        data = {"sources": [], "images": []}
                    else:
                        route.fulfill(status=500, headers=headers, content_type="application/json",
                                      body=json.dumps({"detail": f"unexpected write {path}"}))
                        return
                elif path == "/api/channels":
                    data = {"revision": 1, "channels": [{"id": name, "display_name": name,
                            "status": "active", "revision": 1} for name in ("main", "second")]}
                elif path == "/api/exports":
                    data = {"exports": [clip] if owner == "second" else []}
                elif path == "/api/products":
                    data = {"products": [{"id": "p", "name": "Fixture", "angles": [{
                        "angle_id": "a", "export_id": clip["export_id"], "status": "rendered",
                        "video_url": clip["rel_path"], "cover_path": "05_Covers_Thumbnails/second/wrong-angle.jpg"}]}]}
                elif path == "/api/schedule-queue":
                    data = {"items": [old_queue]}
                elif path == "/api/status":
                    data = {"mobile_url": origin}
                else:
                    data = {"items": [], "products": [], "exports": [], "tasks": [], "videos": [],
                            "catalog": {}, "custom": [], "milestones": []}
                route.fulfill(content_type="application/json", headers={} if path == "/api/channels" else headers, body=json.dumps(data))

            page.route("**/api/**", api)
            page.goto(f"{origin}/?channel=second&mode=desktop", wait_until="domcontentloaded")
            page.get_by_title("4. Export Gallery", exact=True).click()
            if invalid_binding:
                if prepare_view == "detail":
                    page.get_by_role("button", name="ดูรายละเอียด", exact=True).click()
                    dialog = page.get_by_role("dialog").filter(has=page.get_by_role("heading", name="Frozen HF fixture", exact=True))
                    dialog.get_by_role("button", name="โพสต์ TikTok อัตโนมัติ (ทดลอง)", exact=True).click()
                else:
                    page.get_by_role("button", name="สตูดิโอ 2 ฝั่ง", exact=False).click()
                    page.get_by_role("button", name="โพสต์ TikTok อัตโนมัติ (ทดลอง)", exact=True).click()
                expect(page.get_by_text("ปกที่เลือกไว้ไม่ผ่านการตรวจสอบ", exact=False)).to_be_visible()
                assert not any(path == "/api/tiktok-autopost/prepare" for _, path, _ in writes)
                if prepare_view == "detail":
                    dialog.get_by_role("button", name="ปิดหน้าต่าง", exact=True).click()
            page.get_by_role("button", name="สตูดิโอ 2 ฝั่ง", exact=False).click()
            page.get_by_role("button", name="สตูดิโอทำปก 9:16", exact=True).click()
            studio = page.get_by_role("dialog", name="สตูดิโอสร้างปก", exact=True)
            expect(studio).to_be_visible()
            studio.get_by_role("button", name="บันทึกทั้งสองขนาด (9:16 + 3:4)", exact=True).click()
            expect(studio).to_contain_text("สำเร็จแล้ว")
            assert clip["cover_path"] == selected_cover
            # An invalid existing selection explicitly requires a Gallery reload
            # before preparing; normal fresh selections also work immediately.
            if reload_after_save or invalid_binding:
                page.reload(wait_until="domcontentloaded")
                page.get_by_title("4. Export Gallery", exact=True).click()
            else:
                studio.get_by_role("button", name="ปิดสตูดิโอสร้างปก", exact=True).click()
            if prepare_view == "detail":
                page.get_by_role("button", name="ตารางการ์ด", exact=False).click()
                page.get_by_role("button", name="ดูรายละเอียด", exact=True).click()
                dialog = page.get_by_role("dialog").filter(has=page.get_by_role("heading", name="Frozen HF fixture", exact=True))
                dialog.get_by_role("button", name="โพสต์ TikTok อัตโนมัติ (ทดลอง)", exact=True).click()
            else:
                page.get_by_role("button", name="สตูดิโอ 2 ฝั่ง", exact=False).click()
                page.get_by_role("button", name="โพสต์ TikTok อัตโนมัติ (ทดลอง)", exact=True).click()
            expect(page.get_by_text("เตรียมข้อมูลคลิปเข้า Extension สำเร็จ!", exact=False)).to_be_visible()
            prepared = [entry for entry in writes if entry[1] == "/api/tiktok-autopost/prepare"]
            assert len(prepared) == 1
            owner, _, payload = prepared[0]
            assert owner == "second"
            assert payload["export_id"] == clip["export_id"]
            assert payload["video_path"] == clip["rel_path"]
            assert payload["cover_path"] == selected_cover
            assert payload["caption"] == "Frozen caption" and payload["hashtags"] == "#Frozen"
            assert old_queue == old_queue_before
            assert not any(path.startswith("/api/schedule-queue") for _, path, _ in writes)
            assert not errors
        finally:
            browser.close()
