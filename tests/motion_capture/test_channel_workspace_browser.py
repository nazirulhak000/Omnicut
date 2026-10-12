"""Actual App/Provider/Editor paths with isolated API fixtures, never live data."""
import json
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright, expect
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import vite_fs_url


@pytest.fixture
def channel_browser_media():
    root = Path(__file__).resolve().parents[2] / ".tmp"
    with tempfile.TemporaryDirectory(prefix="channel-browser-", dir=root) as directory:
        yield Path(directory)


@pytest.mark.parametrize("width", [390, 1440])
def test_channel_switch_preserves_unsaved_owner_and_mobile_context(motion_fixture_url, channel_browser_media, width):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    source = create_clip_source(channel_browser_media)
    clip = vite_fs_url(origin, source)
    channels = [{"id": owner, "display_name": label, "handle": f"@{owner}", "status": "active", "revision": 1}
                for owner, label in [("main", "Main fixture"), ("second", "Second fixture")]]
    reads, writes = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": 900}, ignore_https_errors=True)
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            errors = []
            console_errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.add_init_script("""localStorage.setItem('capcut_active_tab','editor');
              localStorage.setItem('omnicut.ui_mode','desktop');
              for (const id of ['main','second']) localStorage.setItem(`omnicut:channel:v1:${id}:omnicut_active_project`,
                JSON.stringify({schema_version:1,channel_id:id,data:'same'}));""")

            def route_api(route):
                request = route.request
                path = urlsplit(request.url).path
                owner = request.headers.get("x-omnicut-channel", "main")
                headers = {"X-OmniCut-Channel": owner}
                if path.endswith("/state") and request.method == "PATCH":
                    writes.append((owner, request.post_data_json))
                    route.fulfill(status=503, headers=headers, content_type="application/json", body='{"detail":"fixture save unavailable"}')
                    return
                if path == "/api/channels":
                    result = {"channels": channels, "revision": 1}
                elif path == "/api/projects/same":
                    reads.append(owner)
                    result = {"project_name": "same", "channel_id": owner, "_editor_revision": ("a" if owner == "main" else "b") * 64,
                              "channel_identity_snapshot": {"channel_id": owner, "watermark_text": f"frozen {owner}"},
                              "clip_list": [{"source_path": clip, "trim_start": 0, "trim_end": 2, "duration": 2}],
                              "cues": [], "transitions": [], "artifacts": {}, "show_watermark": False}
                elif path == "/api/projects":
                    result = {"projects": ["same"]}
                elif path == "/api/products":
                    result = {"products": []}
                elif path == "/api/mobile-studio/catalog":
                    result = {"catalog": [], "has_more": False, "total": 0}
                elif path == "/api/assets/all":
                    result = {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []}
                else:
                    result = {"videos": [], "exports": [], "tasks": [], "milestones": [], "custom": [], "catalog": {}, "items": []}
                route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(result))

            page.route("**/api/**", route_api)
            page.goto(f"{origin}/?channel=main&project=same&mode=desktop", wait_until="domcontentloaded")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            try:
                expect(selector).to_be_visible()
            except AssertionError:
                raise AssertionError({"runtime": errors, "console": console_errors[-6:], "body": page.locator("body").inner_text()[:1500]})
            timeline = page.locator('[data-timeline-item="clip"]:visible').first
            expect(timeline).to_be_visible(timeout=15000)
            timeline.click(position={"x": 5, "y": 5})
            page.evaluate("document.activeElement.blur()")
            page.keyboard.press("Shift+ArrowRight")
            page.keyboard.press("w")
            selector.select_option("second")
            dialog = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            expect(dialog).to_be_visible()
            dialog.get_by_role("button", name="อยู่ช่องเดิม").click()
            expect(selector).to_have_value("main")
            selector.select_option("second")
            expect(dialog).to_be_visible()
            dialog.get_by_role("button", name="บันทึกและสลับ").click()
            expect(dialog.get_by_role("alert")).to_be_visible()
            expect(selector).to_have_value("main")
            dialog.get_by_role("button", name="อยู่ช่องเดิม").focus()
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.closest('[role=dialog]') !== null")
            dialog.get_by_role("button", name="ทิ้งการแก้ไขและสลับ").click()
            expect(selector).to_have_value("second")
            expect(dialog).not_to_be_visible()
            expect(timeline).to_be_visible()
            assert "second" in reads
            assert writes
            assert all(owner == "main" for owner, _ in writes)
            assert "channel=second" in page.url
            assert not errors
            page.goto(f"{origin}/?channel=second&mode=mobile", wait_until="domcontentloaded")
            expect(page.get_by_role("combobox", name="เลือกช่อง")).to_have_value("second")
            expect(page.get_by_role("combobox", name="เลือกช่อง")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            assert not errors
        finally:
            browser.close()


def test_invalid_explicit_channel_never_dispatches_main_work_before_recovery(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    work = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844}, ignore_https_errors=True)
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            def route_api(route):
                path = urlsplit(route.request.url).path
                if path.startswith('/api/media/02_Assets/'):
                    route.fulfill(status=200, body=(Path(__file__).resolve().parents[2] / path.removeprefix('/api/media/')).read_bytes())
                    return
                if path == "/api/channels":
                    data = {"revision": 1, "channels": [{"id": "main", "display_name": "Main fixture", "status": "active", "revision": 1}]}
                else:
                    work.append(path)
                    data = {"products": [], "videos": [], "tasks": [], "exports": [], "catalog": [], "items": []}
                route.fulfill(status=200, content_type="application/json", body=json.dumps(data))
            page.route("**/api/**", route_api)
            page.goto(f"{origin}/?mode=mobile&channel=BAD&mobile_session=foreign", wait_until="domcontentloaded")
            recover = page.get_by_role("button", name="เปิดช่องหลัก")
            expect(recover).to_be_visible()
            assert not work
            recover.click()
            expect(page.get_by_role("combobox", name="เลือกช่อง")).to_have_value("main")
            page.wait_for_function("new URL(location.href).searchParams.get('channel') === 'main'")
            assert "mobile_session=" not in page.url
            expect(page.get_by_text("ยังไม่มีสินค้าในคลัง เพิ่มสินค้าใหม่เพื่อเริ่มผลิตคลิป", exact=True)).to_be_visible()
            assert any(path.startswith("/api/mobile-studio") for path in work)
        finally:
            browser.close()
