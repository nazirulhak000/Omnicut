"""Production Mobile Quick Studio UI, with every API request intercepted offline."""

import json
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


CATALOG = [{"id": "prod", "name": "Test Gadget", "angles": [{
    "id": "angle", "hook_headline": "Official Hook", "script_full": "Official script",
    "script_preview": "Official script", "shot_count": 1, "attached_raw": "raw/stale.mp4",
}]}]
RESULT = {"project_name": "mock-project", "video_url": "/api/media/mock-result.mp4", "hook_headline": "Official Hook"}


def mobile_url(fixture):
    parsed = urlsplit(fixture)
    return f"{parsed.scheme}://{parsed.netloc}/?mode=mobile"


def api_mock(page, tasks):
    requests = []
    state = {"task_reads": 0, "tasks": tasks}

    def handle(route):
        path = urlsplit(route.request.url).path
        if path.startswith("/api/mobile-studio"):
            requests.append((path, route.request.post_data_json))
        if path == "/api/mobile-studio/catalog":
            payload = {"success": True, "catalog": CATALOG}
        elif path == "/api/mobile-studio/session":
            payload = {"success": True, "session": {"id": "session1"}}
        elif path == "/api/mobile-studio/assemble":
            payload = {"success": True, "task_id": "render1"}
        elif path == "/api/mobile-studio/task/render1":
            idx = min(state["task_reads"], len(state["tasks"]) - 1)
            state["task_reads"] += 1
            reply = state["tasks"][idx]
            if reply == "offline":
                route.abort("failed")
                return
            payload = {"success": True, "task": reply}
        elif path == "/api/recording-sessions/session1":
            payload = {"id": "session1", "product_id": "prod", "angle_id": "angle", "status": "completed", "segments": [], "raw_video_path": "raw/fresh.mp4"}
        elif path.endswith("/shot-list"):
            payload = {"shot_list": [{"beat_index": 0, "role": "hook", "text": "Official script", "planned_duration": 1}]}
        elif path.startswith("/api/media/"):
            route.fulfill(status=200, content_type="video/mp4", body=b"test-owned mock media response")
            return
        else:
            payload = {"products": [], "videos": [], "tasks": [], "exports": [], "queue": []}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))

    page.route("**/api/**", handle)
    return requests, state


def start_render(page, url):
    page.goto(url, wait_until="domcontentloaded")
    page.get_by_role("button", name="ยืนยันสคริปต์ & ไปหน้าถ่ายทำ").click()
    page.get_by_role("button", name="ประกอบคลิปและเรนเดอร์", exact=True).click()


def test_mobile_success_reload_and_share_is_browser_menu(motion_fixture_url):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844}, ignore_https_errors=True)
            requests, state = api_mock(page, [{"status": "completed", "progress": 1, "result": RESULT}])
            page.add_init_script("""window.__shares=[]; Object.defineProperty(navigator,'share',{value: async args => window.__shares.push({...args, files:args.files?.map(f=>({name:f.name,type:f.type,size:f.size}))})}); Object.defineProperty(navigator,'canShare',{value:()=>true}); Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__caption=t;}}});""")
            start_render(page, mobile_url(motion_fixture_url))
            expect(page.get_by_text("เรนเดอร์สำเร็จ 100% พร้อมโพสต์!", exact=True)).to_be_visible()
            assert page.locator("video").get_attribute("src") == RESULT["video_url"]
            body = next(body for path, body in requests if path.endswith("/assemble"))
            assert body["session_id"] == "session1" and body["custom_raw_video"] is None
            page.get_by_role("button", name="เปิดเมนูแชร์วิดีโอ").click()
            page.wait_for_function("window.__shares.length === 1")
            shared = page.evaluate("window.__shares[0]")
            assert shared["files"][0]["name"] == "mock-project.mp4"
            assert "Official Hook" in page.evaluate("window.__caption")
            page.reload(wait_until="domcontentloaded")
            expect(page.get_by_text("เรนเดอร์สำเร็จ 100% พร้อมโพสต์!", exact=True)).to_be_visible()
            assert sum(path.endswith("/assemble") for path, _ in requests) == 1
        finally:
            browser.close()


@pytest.mark.parametrize("terminal", ["failed", "cancelled", "completed_without_file"])
def test_mobile_terminal_errors_leave_spinner_and_allow_retry(motion_fixture_url, terminal):
    task = {"status": "completed" if terminal == "completed_without_file" else terminal, "error": "offline render failed" if terminal == "failed" else None, "result": {}}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844}, ignore_https_errors=True)
            api_mock(page, [task])
            start_render(page, mobile_url(motion_fixture_url))
            expect(page.get_by_role("button", name="ประกอบคลิปและเรนเดอร์", exact=True)).to_be_visible()
            expect(page.get_by_text("กำลังประกอบคลิปอัตโนมัติ", exact=True)).to_have_count(0)
            expect(page.get_by_text("เรนเดอร์สำเร็จ 100% พร้อมโพสต์!", exact=True)).to_have_count(0)
        finally:
            browser.close()


def test_mobile_disconnection_reconnects_same_task_without_duplicate_render(motion_fixture_url):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844}, ignore_https_errors=True)
            requests, state = api_mock(page, ["offline"])
            start_render(page, mobile_url(motion_fixture_url))
            reconnect = page.get_by_role("button", name="ตรวจสถานะอีกครั้ง")
            expect(reconnect).to_be_visible(timeout=12000)
            state["tasks"] = [{"status": "completed", "progress": 1, "result": RESULT}]
            reconnect.click()
            expect(page.get_by_text("เรนเดอร์สำเร็จ 100% พร้อมโพสต์!", exact=True)).to_be_visible()
            assert sum(path.endswith("/assemble") for path, _ in requests) == 1
        finally:
            browser.close()


def test_filming_navigation_returns_to_same_mobile_workflow(motion_fixture_url):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844}, ignore_https_errors=True)
            api_mock(page, [])
            page.add_init_script("window.close=()=>{};")
            page.goto(mobile_url(motion_fixture_url), wait_until="domcontentloaded")
            page.get_by_role("button", name="ยืนยันสคริปต์ & ไปหน้าถ่ายทำ").click()
            page.get_by_role("button", name="กดเปิดกล้องถ่ายทำ (Guided Take)").click()
            page.wait_for_url("**/?film=1&session=session1&return=mobile&product=prod&angle=angle")
            page.get_by_role("button", name="เสร็จแล้ว กลับไปหน้าหลัก").click()
            page.wait_for_url("**/?mode=mobile&mobile_session=session1&product=prod&angle=angle")
            expect(page.get_by_role("button", name="ประกอบคลิปและเรนเดอร์", exact=True)).to_be_visible()
            expect(page.get_by_text("สเต็ป 2: ถ่ายคลิปหน้ากล้อง", exact=True)).to_be_visible()
        finally:
            browser.close()
