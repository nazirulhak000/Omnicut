"""Real App profile editing with offline API/session fixtures only."""
import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


def run_profile_browser(motion_fixture_url, width, screenshot_path, busy_screenshot_path=None):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    profiles = [{"id": owner, "display_name": label, "handle": f"@{owner}user", "status": status,
                 "revision": 1, "watermark_text": label, "follow_title": "Follow", "avatar_asset_path": "02_Assets/Brand/avatar.jpg",
                 "posting_enabled": False, "account_binding": {"status": "unverified"}}
                for owner, label, status in [("main", "Main fixture", "active"), ("second", "Second fixture", "draft")]]
    registry_revision = [7]
    writes, held = [], []
    defer_patch = [False]
    source_root = Path(__file__).resolve().parents[2]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": 900}, ignore_https_errors=True)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("""localStorage.setItem('capcut_active_tab','settings');
                localStorage.setItem('omnicut.ui_mode','desktop');""")

            def complete_patch(route, profile, payload):
                assert payload["expected_revision"] == profile["revision"]
                profile.update({key: value for key, value in payload.items() if key != "expected_revision"})
                profile["revision"] += 1
                registry_revision[0] += 1
                route.fulfill(status=200, content_type="application/json", body=json.dumps({"channel": deepcopy(profile)}))

            def route_api(route):
                request = route.request
                path = urlsplit(request.url).path
                if path.startswith("/api/media/02_Assets/Fonts/"):
                    font = source_root / path.removeprefix("/api/media/")
                    if font.is_file(): route.fulfill(status=200, path=str(font), content_type="font/ttf")
                    else: route.fulfill(status=404, body="fixture font unavailable")
                    return
                result = {"items": [], "exports": [], "videos": [], "tasks": [], "milestones": [], "custom": [], "catalog": {}, "projects": []}
                if path == "/api/channels" and request.method == "GET":
                    result = {"channels": deepcopy(profiles), "revision": registry_revision[0]}
                elif path == "/api/channels" and request.method == "POST":
                    payload = request.post_data_json
                    writes.append(("create", deepcopy(payload)))
                    assert payload["expected_registry_revision"] == registry_revision[0]
                    assert payload["posting_enabled"] is False and "account_binding" not in payload
                    new = {**payload, "status": "draft", "revision": 1, "account_binding": {"status": "unverified"}}
                    new.pop("expected_registry_revision", None)
                    profiles.append(new); registry_revision[0] += 1
                    result = {"channel": deepcopy(new)}
                elif path.startswith("/api/channels/"):
                    parts = path.split("/")
                    profile = next(item for item in profiles if item["id"] == parts[3])
                    if path.endswith("/readiness"):
                        result = {"channel_id": profile["id"], "revision": profile["revision"], "status": profile["status"],
                                  "ready": True, "posting_ready": False, "issues": [],
                                  "posting_issues": [{"code": "account_unverified", "message": "ต้องตรวจบัญชีจริงก่อนโพสต์"}]}
                    elif request.method == "PATCH":
                        payload = request.post_data_json
                        writes.append((profile["id"], deepcopy(payload)))
                        assert "account_binding" not in payload
                        if defer_patch[0]: held.append((route, profile, payload)); return
                        complete_patch(route, profile, payload); return
                    elif request.method == "POST":
                        payload = request.post_data_json
                        writes.append((path, deepcopy(payload)))
                        assert payload == {"expected_revision": profile["revision"]}
                        profile["status"] = "active" if path.endswith("/activate") else "archived"
                        profile["revision"] += 1; registry_revision[0] += 1
                        result = {"channel": deepcopy(profile)}
                headers = {} if path.startswith("/api/channels") else {"X-OmniCut-Channel": request.headers.get("x-omnicut-channel", "main")}
                route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(result))

            page.route("**/api/**", route_api)
            page.goto(f"{origin}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            def open_profiles():
                page.get_by_text("ช่องและตัวตนคลิป", exact=True).locator("visible=true").first.click()
            open_profiles()
            section = page.get_by_role("region", name="ตั้งค่าช่อง")
            expect(section).to_be_visible()
            name = section.get_by_label("ชื่อช่อง", exact=True)
            save = section.get_by_role("button", name="บันทึกตัวตนช่อง", exact=True)
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            expect(name).to_have_value("Main fixture")
            expect(save).to_be_disabled()
            expect(section.get_by_label("เปิดโพสต์สำหรับช่องนี้")).to_be_disabled()
            expect(section.get_by_text("ต้องตรวจบัญชีจริงก่อนโพสต์", exact=True)).to_be_visible()
            name.fill("Main edited"); save.click()
            expect(name).to_have_value("Main edited")
            expect(save).to_be_disabled()
            assert writes[-1] == ("main", {"display_name": "Main edited", "expected_revision": 1})

            # Discard cannot switch ownership while a profile PATCH is in flight.
            defer_patch[0] = True
            name.fill("Main slow"); save.click()
            expect(section.get_by_role("button", name="กำลังบันทึก", exact=True)).to_be_visible()
            selector.select_option("second")
            dialog = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            expect(dialog).to_be_visible()
            dialog.get_by_role("button", name="ทิ้งการแก้ไขและสลับ").click()
            expect(dialog.get_by_role("alert")).to_contain_text("กำลังบันทึกช่อง")
            expect(selector).to_have_value("main")
            if busy_screenshot_path:
                busy_screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(busy_screenshot_path), full_page=True)
            assert len(held) == 1
            defer_patch[0] = False
            complete_patch(*held.pop())
            expect(section.get_by_role("button", name="บันทึกตัวตนช่อง", exact=True)).to_be_disabled()
            dialog.get_by_role("button", name="อยู่ช่องเดิม").click()

            name.fill("Main switch")
            selector.select_option("second")
            dialog.get_by_role("button", name="บันทึกและสลับ").click()
            expect(selector).to_have_value("second")
            open_profiles()
            expect(name).to_have_value("Second fixture")
            assert writes[-1] == ("main", {"display_name": "Main switch", "expected_revision": 3})
            name.fill("Second discarded")
            selector.select_option("main")
            dialog.get_by_role("button", name="ทิ้งการแก้ไขและสลับ").click()
            expect(selector).to_have_value("main")
            open_profiles()
            expect(name).to_have_value("Main switch")
            assert profiles[1]["display_name"] == "Second fixture"

            section.get_by_role("button", name="สร้างช่องใหม่", exact=True).click()
            section.get_by_label("รหัสช่อง", exact=True).fill("new-channel")
            section.get_by_label("ชื่อช่อง", exact=True).first.fill("New draft")
            section.get_by_role("button", name="สร้างแบบร่าง", exact=True).click()
            expect(selector.locator('option[value="new-channel"]')).to_have_count(1)
            create = next(payload for target, payload in writes if target == "create")
            assert create["expected_registry_revision"] == 10

            selector.select_option("second")
            expect(selector).to_have_value("second")
            open_profiles()
            expect(name).to_have_value("Second fixture")
            activation = section.get_by_role("button", name="เปิดใช้งานช่อง", exact=True)
            try:
                expect(activation).to_be_enabled()
            except AssertionError as error:
                raise AssertionError(section.inner_text()) from error
            activation.click()
            confirm = section.get_by_role("alertdialog", name="ยืนยันสถานะช่อง")
            confirm.get_by_role("button", name="ยืนยัน", exact=True).click()
            expect(section.get_by_role("button", name="เปิดใช้งานช่อง", exact=True)).to_have_count(0)
            section.get_by_role("button", name="เก็บช่องถาวร", exact=True).click()
            confirm.get_by_role("button", name="ยืนยัน", exact=True).click()
            expect(name).to_be_disabled()
            expect(save).to_be_disabled()
            assert profiles[1]["status"] == "archived"
            assert ("/api/channels/second/activate", {"expected_revision": 1}) in writes
            assert ("/api/channels/second/archive", {"expected_revision": 2}) in writes
            expect(section.get_by_text("ช่องเก็บถาวร อ่านข้อมูลได้เท่านั้น", exact=True)).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.evaluate("for (const node of document.querySelectorAll('*')) if (node.scrollTop) node.scrollTop = 0")
            page.screenshot(path=str(screenshot_path), full_page=True)
            assert not errors, errors
            geometry = selector.evaluate("""node => {
                const header=node.closest('header');
                const bounds=element=>{const r=element.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};};
                const visible=element=>element.getBoundingClientRect().width>0 && element.getBoundingClientRect().height>0;
                return {selector:bounds(node),icon:bounds(header.firstElementChild.firstElementChild),
                    actions:[...header.querySelectorAll('button,select')].filter(visible).map(bounds),width:window.innerWidth};
            }""")
            def overlaps(a,b):
                return a['left']<b['right'] and b['left']<a['right'] and a['top']<b['bottom'] and b['top']<a['bottom']
            assert not overlaps(geometry['selector'],geometry['icon']),geometry
            for bounds in geometry['actions']:
                assert bounds['left'] >= 0 and bounds['right'] <= geometry['width'],geometry
                if bounds != geometry['selector']:
                    assert not overlaps(geometry['selector'],bounds),geometry
            return writes
        finally:
            browser.close()


@pytest.mark.parametrize("width", [320, 390, 1440])
def test_channel_profile_save_switch_create_lifecycle(motion_fixture_url, tmp_path, width):
    screenshot = tmp_path / f"channel-profile-{width}.png"
    try:
        assert run_profile_browser(motion_fixture_url, width, screenshot)
    finally:
        screenshot.unlink(missing_ok=True)
