"""The product page's production-chain buttons, in a real browser with an offline API fixture."""
import json
from contextlib import contextmanager
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

PRODUCT_ID = "P1"
CHAIN_ROUTE = f"/api/products/{PRODUCT_ID}/production-chain"
CHAIN_ID = "chain-1"


def _angle(angle_id, **fields):
    return {"angle_id": angle_id, "id": angle_id, "batch": 1, "title": f"Fixture angle {angle_id}",
            "hook": "fixture hook", "status": "scripted", "script_lines": ["fixture line"], **fields}


def _angles(drafted=()):
    """Two scripted angles and one reviewed draft; `drafted` angles have become drafts too."""
    made = {angle_id: {"status": "in_production", "project_name": f"proj_{angle_id}"} for angle_id in drafted}
    return [
        _angle("a1", **made.get("a1", {})),
        _angle("a2", **made.get("a2", {})),
        _angle("a3", status="in_production", project_name="proj_a3"),
    ]


class _Fixture:
    """Offline API for the product page: one product and one chain task the test drives."""

    def __init__(self):
        self.angles = _angles()
        self.task = None
        self.started, self.cancelled, self.other_writes, self.page_errors = [], [], [], []

    def _chain_task(self, kind):
        return {"id": CHAIN_ID, "type": "production_chain", "title": "fixture chain", "status": "processing",
                "progress": 0.4, "step_label": "fixture step 2/3", "target_tab": "flow", "target_id": PRODUCT_ID,
                "payload": {"product_id": PRODUCT_ID, "kind": kind, "batch_index": None}, "result": None,
                "error": None}

    def finish(self, status, result=None):
        self.task = {**self.task, "status": status, "progress": 1.0, "result": result}

    def api(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if request.method == "POST" and path == CHAIN_ROUTE:
            body = request.post_data_json
            self.started.append(body)
            self.task = self._chain_task(body["kind"])
            route.fulfill(content_type="application/json",
                          body=json.dumps({"success": True, "task_id": CHAIN_ID, "task": self.task}))
            return
        if request.method == "POST" and path == f"/api/tasks/{CHAIN_ID}/cancel":
            self.cancelled.append(CHAIN_ID)
            self.finish("cancelled")
            route.fulfill(content_type="application/json", body='{"success": true}')
            return
        if request.method != "GET":
            self.other_writes.append((request.method, path))
            route.fulfill(status=503, content_type="application/json", body='{"detail":"fixture is read only"}')
            return
        if path == "/api/channels":
            data = {"revision": 1, "channels": [{"id": "main", "display_name": "main", "status": "active", "revision": 1}]}
        elif path == "/api/products":
            data = {"products": [{"id": PRODUCT_ID, "channel_id": "main", "product_code": PRODUCT_ID,
                                  "name": "Fixture product", "status": "scripted", "angles": self.angles}]}
        elif path == "/api/tasks/active":
            tasks = [self.task] if self.task else []
            data = {"tasks": tasks, "count": len(tasks)}
        elif path == f"/api/products/{PRODUCT_ID}/shot-list-status":
            data = {"status": {}}
        elif path == f"/api/products/{PRODUCT_ID}/scene-catalogs":
            data = {"catalogs": {}}
        else:
            data = {"items": [], "exports": [], "tasks": [], "videos": [], "products": [], "catalog": {},
                    "milestones": [], "custom": []}
        route.fulfill(content_type="application/json", headers={"X-OmniCut-Channel": "main"}, body=json.dumps(data))


@contextmanager
def _product_page(fixture_url, fixture):
    parsed = urlsplit(fixture_url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900}, ignore_https_errors=True)
            page.on("pageerror", lambda error: fixture.page_errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("""localStorage.setItem('capcut_active_tab','flow');
              localStorage.setItem('omnicut:channel:v1:main:capcut_active_tab','flow');
              localStorage.setItem('omnicut.ui_mode','desktop');
              localStorage.setItem('capcut_tracker_view_mode','kanban');""")
            page.route("**/api/**", fixture.api)
            page.goto(f"{parsed.scheme}://{parsed.netloc}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            yield page
        finally:
            browser.close()


def _confirm(page, text):
    return page.get_by_role("dialog").filter(has_text=text)


def _open_lot_tools(page):
    """The step-by-step chain lives in the lot panel, behind its toggle."""
    toggle = page.get_by_role("button", name="จัดการล็อต")
    expect(toggle).to_have_attribute("aria-expanded", "false", timeout=30000)
    toggle.click()
    expect(page.locator("#batch-secondary-tools")).to_be_visible()


def _filled_buttons(page):
    """Labels of the lot toolbar's filled (primary) buttons."""
    return page.evaluate("""() => [...document.querySelector('[aria-controls="batch-secondary-tools"]')
        .closest('section').querySelectorAll('button')]
        .filter((b) => b.offsetParent && b.className.split(' ').includes('bg-[#25F4EE]'))
        .map((b) => b.textContent.trim())""")


def test_draft_chain_starts_after_confirmation_and_refreshes_the_product_when_done(motion_fixture_url):
    fixture = _Fixture()
    with _product_page(motion_fixture_url, fixture) as page:
        draft = page.get_by_test_id("production-chain-draft")
        render = page.get_by_test_id("production-chain-render")
        full = page.get_by_test_id("production-chain-full")
        expect(full).to_have_text("ผลิตจนเรนเดอร์เสร็จ (2)", timeout=30000)
        expect(render).to_have_text("เรนเดอร์ดราฟต์ (1)")
        # one filled button: the chain that takes the lot furthest
        assert _filled_buttons(page) == ["ผลิตจนเรนเดอร์เสร็จ (2)"]
        expect(draft).to_have_count(0)
        _open_lot_tools(page)
        expect(page.get_by_role("group", name="ทีละขั้น")).to_contain_text("ผลิตถึงดราฟต์ (2)")
        expect(draft).to_have_text("ผลิตถึงดราฟต์ (2)")
        assert _filled_buttons(page) == ["ผลิตจนเรนเดอร์เสร็จ (2)"]

        # Cancelling the confirmation starts nothing.
        draft.click()
        confirm = _confirm(page, "สร้างดราฟต์ 2 มุม")
        expect(confirm).to_contain_text("ตรวจใน Editor ก่อนเรนเดอร์")
        confirm.get_by_role("button", name="ยกเลิก", exact=True).click()
        expect(confirm).to_be_hidden()
        assert fixture.started == []

        draft.click()
        confirm.get_by_role("button", name="ยืนยัน", exact=True).click()

        # While the chain runs the two buttons give way to its progress.
        chip = page.get_by_test_id("production-chain-progress")
        expect(chip).to_contain_text("ผลิตถึงดราฟต์ · fixture step 2/3")
        expect(chip).to_contain_text("40%")
        expect(draft).to_be_hidden()
        expect(render).to_be_hidden()
        expect(full).to_be_hidden()
        assert len(fixture.started) == 1
        assert fixture.started[0]["kind"] == "draft" and fixture.started[0]["batch_index"] is None
        assert fixture.started[0]["voice_preset"]

        # The chain ends at the drafts: the page reloads the product and stays where it is.
        fixture.angles = _angles(drafted=("a1", "a2"))
        fixture.finish("completed", {"kind": "draft", "ok": True, "drafts": {"created": [{}, {}]}})
        expect(chip).to_be_hidden(timeout=15000)
        expect(render).to_have_text("เรนเดอร์ดราฟต์ (3)", timeout=15000)
        expect(draft).to_be_hidden()
        # nothing left to produce: rendering the drafts becomes the one primary action
        assert _filled_buttons(page) == ["เรนเดอร์ดราฟต์ (3)"]
        expect(page.get_by_role("dialog").filter(has_text="จัดคิวอัตโนมัติ")).to_have_count(0)
        assert not fixture.other_writes
        assert not fixture.page_errors


def _assert_stays_on_the_product(page, render, fixture):
    """The chain ended: the product reloaded, the schedule was not opened, nothing was queued."""
    page.wait_for_timeout(600)
    expect(render).to_be_visible()
    expect(page.get_by_role("dialog").filter(has_text="จัดคิวอัตโนมัติ")).to_have_count(0)
    assert len(fixture.started) == 1
    assert not fixture.other_writes
    assert not fixture.page_errors


def test_render_chain_stays_on_the_product_and_does_not_open_the_schedule(motion_fixture_url):
    fixture = _Fixture()
    with _product_page(motion_fixture_url, fixture) as page:
        render = page.get_by_test_id("production-chain-render")
        expect(render).to_have_text("เรนเดอร์ดราฟต์ (1)", timeout=30000)
        render.click()
        confirm = _confirm(page, "เรนเดอร์ดราฟต์ที่ตรวจแล้ว 1 มุม")
        expect(confirm).to_contain_text("ไม่จัดคิวโพสต์")
        confirm.get_by_role("button", name="ยืนยัน", exact=True).click()
        expect(page.get_by_test_id("production-chain-progress")).to_contain_text("เรนเดอร์ดราฟต์ · fixture step 2/3")
        assert fixture.started == [{"kind": "render", "batch_index": None,
                                    "voice_preset": fixture.started[0]["voice_preset"]}]

        # a3 rendered; a fresh draft of a1 shows the product really reloaded
        fixture.angles = [_angle("a1", status="in_production", project_name="proj_a1"), _angles()[1],
                          _angle("a3", status="rendered", project_name="proj_a3")]
        fixture.finish("completed", {"kind": "render", "ok": True, "rendered": [{"angle_id": "a3"}]})
        expect(page.get_by_test_id("production-chain-progress")).to_be_hidden(timeout=15000)
        expect(render).to_have_text("เรนเดอร์ดราฟต์ (1)")
        _open_lot_tools(page)
        expect(page.get_by_test_id("production-chain-draft")).to_have_text("ผลิตถึงดราฟต์ (1)", timeout=15000)
        _assert_stays_on_the_product(page, render, fixture)


def test_full_chain_produces_and_renders_in_one_press_without_the_schedule(motion_fixture_url):
    fixture = _Fixture()
    with _product_page(motion_fixture_url, fixture) as page:
        full = page.get_by_test_id("production-chain-full")
        render = page.get_by_test_id("production-chain-render")
        expect(full).to_have_text("ผลิตจนเรนเดอร์เสร็จ (2)", timeout=30000)
        assert _filled_buttons(page) == ["ผลิตจนเรนเดอร์เสร็จ (2)"]  # the render button stays outlined
        _open_lot_tools(page)

        full.click()
        confirm = _confirm(page, "สร้างดราฟต์ และเรนเดอร์ 2 มุม")
        expect(confirm).to_contain_text("ไม่หยุดให้ตรวจดราฟต์ก่อนเรนเดอร์ และไม่จัดคิวโพสต์")
        confirm.get_by_role("button", name="ยืนยัน", exact=True).click()

        chip = page.get_by_test_id("production-chain-progress")
        expect(chip).to_contain_text("ผลิตจนเรนเดอร์เสร็จ · fixture step 2/3")
        expect(full).to_be_hidden()
        assert fixture.started == [{"kind": "full", "batch_index": None,
                                    "voice_preset": fixture.started[0]["voice_preset"]}]

        # Both new angles came back rendered; the old draft a3 is left for the render button.
        fixture.angles = [_angle("a1", status="rendered", project_name="proj_a1"),
                          _angle("a2", status="rendered", project_name="proj_a2"),
                          _angle("a3", status="in_production", project_name="proj_a3")]
        fixture.finish("completed", {"kind": "full", "ok": True,
                                     "render": {"rendered": [{"angle_id": "a1"}, {"angle_id": "a2"}]}})
        expect(chip).to_be_hidden(timeout=15000)
        expect(full).to_have_count(0, timeout=15000)
        expect(page.get_by_test_id("production-chain-draft")).to_have_count(0)
        expect(render).to_have_text("เรนเดอร์ดราฟต์ (1)")
        _assert_stays_on_the_product(page, render, fixture)


def test_cancelling_a_running_chain_asks_first_and_stays_on_the_product(motion_fixture_url):
    fixture = _Fixture()
    with _product_page(motion_fixture_url, fixture) as page:
        render = page.get_by_test_id("production-chain-render")
        expect(render).to_have_text("เรนเดอร์ดราฟต์ (1)", timeout=30000)
        render.click()
        page.get_by_role("dialog").get_by_role("button", name="ยืนยัน", exact=True).click()
        chip = page.get_by_test_id("production-chain-progress")
        expect(chip).to_be_visible()

        chip.get_by_role("button", name="ยกเลิก", exact=True).click()
        confirm = _confirm(page, "ยกเลิกเรนเดอร์ดราฟต์หรือไม่?")
        confirm.get_by_role("button", name="ยกเลิก", exact=True).click()
        expect(confirm).to_be_hidden()
        assert fixture.cancelled == []

        chip.get_by_role("button", name="ยกเลิก", exact=True).click()
        confirm.get_by_role("button", name="ยืนยัน", exact=True).click()
        expect(chip).to_be_hidden(timeout=15000)
        expect(render).to_have_text("เรนเดอร์ดราฟต์ (1)")
        expect(page.get_by_role("dialog").filter(has_text="จัดคิวอัตโนมัติ")).to_have_count(0)
        assert fixture.cancelled == [CHAIN_ID]
        assert not fixture.other_writes
        assert not fixture.page_errors
