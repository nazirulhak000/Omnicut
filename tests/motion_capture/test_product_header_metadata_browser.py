"""Product page header and the product metadata modal, in a real browser with an offline API fixture.

The header splits actions on the open product (next to its title) from actions
on the product list (with the cards). The modal edits specs stored as labelled
objects without turning them into "[object Object]", and saves them back in
their stored shape.
"""
import json
from contextlib import contextmanager
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

KEY_SPECS = [{"key": "ความจุ", "value": "30,000mAh"}, {"key": "กำลังไฟ", "value": "22.5W"}]
SELLING = ["ชาร์จไร้สาย 15W", "มีสายในตัว"]


def _product(pid, code, name, **fields):
    return {"id": pid, "channel_id": "main", "product_code": code, "name": name, "status": "scripted",
            "angles": [{"angle_id": f"{pid}_a1", "id": f"{pid}_a1", "batch": 1, "title": "Fixture angle",
                        "hook": "fixture hook", "status": "scripted", "script_lines": ["fixture line"]}],
            **fields}


PRODUCTS = [
    _product("P1", "POW01", "Fixture power bank", url="https://example.test/p1", price_note="฿313.50",
             description="power bank 30000mAh", raw_text="power bank 30000mAh", specs=KEY_SPECS,
             selling_points=SELLING, pain_points=[]),
    _product("P2", "CAB01", "Fixture cable"),
    _product("P3", "OLD01", "Fixture hidden product", is_hidden=True),
]


class _Fixture:
    def __init__(self):
        self.writes, self.page_errors = [], []

    def api(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if request.method != "GET":
            body = request.post_data_json if request.post_data else None
            self.writes.append((request.method, path, body))
            if request.method == "PATCH" and path == "/api/products/P1":
                route.fulfill(content_type="application/json",
                              body=json.dumps({"product": {**PRODUCTS[0], **(body or {})}}))
                return
            route.fulfill(status=503, content_type="application/json", body='{"detail":"fixture is read only"}')
            return
        if path == "/api/channels":
            data = {"revision": 1, "channels": [{"id": "main", "display_name": "main", "status": "active", "revision": 1}]}
        elif path == "/api/products":
            data = {"products": PRODUCTS}
        elif path == "/api/tasks/active":
            data = {"tasks": [], "count": 0}
        elif path.endswith("/shot-list-status"):
            data = {"status": {}}
        elif path.endswith("/scene-catalogs"):
            data = {"catalogs": {}}
        else:
            data = {"items": [], "exports": [], "tasks": [], "videos": [], "products": [], "catalog": {},
                    "milestones": [], "custom": []}
        route.fulfill(content_type="application/json", headers={"X-OmniCut-Channel": "main"}, body=json.dumps(data))


@contextmanager
def _product_page(fixture_url, fixture, viewport=(1440, 900)):
    parsed = urlsplit(fixture_url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]}, ignore_https_errors=True)
            page.on("pageerror", lambda error: fixture.page_errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("""localStorage.setItem('capcut_active_tab','flow');
              localStorage.setItem('omnicut:channel:v1:main:capcut_active_tab','flow');
              localStorage.setItem('omnicut.ui_mode','desktop');""")
            page.route("**/api/**", fixture.api)
            page.goto(f"{parsed.scheme}://{parsed.netloc}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            page.get_by_role("button", name="Fixture power bank").first.wait_for(timeout=30000)
            page.get_by_role("button", name="Fixture power bank").first.click()
            expect(page.get_by_role("heading", level=1, name="POW01 Fixture power bank")).to_be_visible()
            yield page
        finally:
            browser.close()


def test_header_keeps_product_actions_by_the_title_and_list_tools_with_the_cards(motion_fixture_url):
    fixture = _Fixture()
    with _product_page(motion_fixture_url, fixture) as page:
        own = page.get_by_role("group", name="จัดการสินค้านี้")
        for label in ("ข้อมูล AI", "ตั้งค่าป้าย Hook", "ลบสินค้า"):
            expect(own.get_by_role("button", name=label)).to_be_visible()

        # Search is always there; nothing to open first.
        search = page.get_by_role("searchbox", name="ค้นหาสินค้า")
        expect(search).to_be_visible()
        expect(page.get_by_role("button", name="เครื่องมือสินค้า")).to_have_count(0)
        expect(page.get_by_text("คืบหน้า", exact=True)).to_have_count(0)

        shown = page.get_by_role("group", name="แสดงสินค้า")
        expect(shown.get_by_role("button", name="หลัก 2")).to_have_attribute("aria-pressed", "true")
        shown.get_by_role("button", name="ซ่อนอยู่ 1").click()
        expect(page.get_by_role("button", name="Fixture hidden product").first).to_be_visible()
        shown.get_by_role("button", name="หลัก 2").click()

        search.fill("cable")
        expect(page.get_by_role("button", name="Fixture cable").first).to_be_visible()
        expect(page.get_by_role("button", name="Fixture power bank")).to_have_count(0)
        search.fill("")

        page.get_by_role("button", name="เครื่องมือรายการสินค้าเพิ่มเติม").click()
        menu = page.get_by_role("menu", name="เครื่องมือรายการสินค้าเพิ่มเติม")
        expect(menu.get_by_role("menuitem", name="รีเฟรชข้อมูล")).to_be_visible()
        expect(menu.get_by_role("menuitem", name="ซ่อนสินค้าที่ยังไม่ทำ (2)")).to_be_visible()
        page.keyboard.press("Escape")
        expect(menu).to_have_count(0)

        assert fixture.writes == []
        assert not fixture.page_errors


def test_metadata_modal_edits_labelled_specs_and_saves_them_in_their_shape(motion_fixture_url):
    fixture = _Fixture()
    with _product_page(motion_fixture_url, fixture) as page:
        page.get_by_role("group", name="จัดการสินค้านี้").get_by_role("button", name="ข้อมูล AI").click()
        dialog = page.get_by_role("dialog", name="ข้อมูลสินค้าและแหล่งข้อมูล AI")
        expect(dialog).to_be_visible()

        specs = dialog.get_by_role("textbox", name="สเปก")
        expect(specs).to_have_value("ความจุ: 30,000mAh\nกำลังไฟ: 22.5W")
        assert "[object Object]" not in dialog.inner_text()
        expect(dialog.get_by_text("2 รายการ").first).to_be_visible()

        save = dialog.get_by_role("button", name="บันทึกการแก้ไข")
        expect(save).to_be_disabled()
        expect(dialog.get_by_role("status").filter(has_text="ข้อมูลตรงกับที่บันทึกไว้")).to_be_visible()

        specs.fill("ความจุ: 30,000mAh\nกำลังไฟ: 15W")
        expect(dialog.get_by_role("status").filter(has_text="มีการแก้ไขที่ยังไม่บันทึก")).to_be_visible()
        # The save button stays on screen while the long form is scrolled.
        expect(save).to_be_in_viewport()
        save.click()

        page.wait_for_timeout(500)
        patches = [body for method, path, body in fixture.writes if method == "PATCH" and path == "/api/products/P1"]
        assert len(patches) == 1, fixture.writes
        body = patches[0]
        assert body["specs"] == [{"key": "ความจุ", "value": "30,000mAh"}, {"key": "กำลังไฟ", "value": "15W"}]
        assert body["selling_points"] == SELLING  # untouched list goes back as it was
        assert body["pain_points"] == []
        expect(dialog.get_by_role("status").filter(has_text="ข้อมูลตรงกับที่บันทึกไว้")).to_be_visible()
        assert not fixture.page_errors
