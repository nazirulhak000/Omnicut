"""Angle list, angle panel and progress strip of the product page, in a real browser with an offline API fixture.

Each angle shows one filled button for the step that moves it forward; the
other actions of that state stay secondary (a menu on a phone). The list rows
carry the title, the hook and a worded state. The old six-tile status band is
folded into one progress row of the lot card.
"""
import json
from urllib.parse import urlsplit

from playwright.sync_api import expect

from tests.motion_capture import test_product_header_metadata_browser as base

CLIP = "D:/raw/fixture_clip.mp4"


def _angle(n, status="scripted", **fields):
    return {"angle_id": f"A{n}", "id": f"A{n}", "batch": 1, "angle_name": f"มุมทดสอบ {n}",
            "hook_title": f"hook ของมุม {n}", "status": status, "script_lines": ["บรรทัดหนึ่ง"], **fields}


ANGLES = [
    _angle(1),
    _angle(2, selected_videos=[CLIP]),
    _angle(3, selected_videos=[CLIP]),
    _angle(4, "in_production", selected_videos=[CLIP]),
    _angle(5, "rendered", selected_videos=[CLIP], video_url="/exports/fixture_5.mp4"),
    _angle(6, "posted", selected_videos=[CLIP], video_url="/exports/fixture_6.mp4", posted_at="2026-11-12T10:00:00"),
]
SHOT_LISTS = {"A3": {"has_shot_list": True, "is_edge_tts": False, "voice_preset": "fenrir_commercial"}}

# angle -> (state chip in the list, filled button of the panel, secondary buttons)
EXPECTED = {
    1: ("ยังไม่มีคลิป", "เลือกคลิป", ["ส่งเข้า Tracker"]),
    2: ("ยังไม่มีเสียง", "เตรียมเสียงและแผนถ่าย", ["ส่งเข้า Tracker", "ตั้งค่าเองใน Editor"]),
    3: ("พร้อมทำดราฟต์", "สร้างดราฟต์", ["ส่งเข้า Tracker", "ตั้งค่าเองใน Editor"]),
    4: ("มีดราฟต์", "เปิดทำต่อใน Editor", ["ดูใน Tracker", "ตัดใหม่"]),
    5: ("เรนเดอร์แล้ว", "ดูคลิป", ["เปิดใน Gallery", "เปิดดูใน Editor", "ตัดใหม่"]),
    6: ("โพสต์แล้ว", "ดูคลิป", ["เปิดใน Gallery", "ทำซ้ำเพื่อตัดใหม่"]),
}


class _Fixture(base._Fixture):
    def api(self, route):
        path = urlsplit(route.request.url).path
        if route.request.method == "GET" and path.endswith("/shot-list-status"):
            route.fulfill(content_type="application/json", headers={"X-OmniCut-Channel": "main"},
                          body=json.dumps({"status": SHOT_LISTS}))
            return
        super().api(route)


def _with_angles():
    original = base.PRODUCTS[0]["angles"]
    base.PRODUCTS[0]["angles"] = ANGLES
    return original


def _row(page, n):
    return page.get_by_role("button", name=f"มุมทดสอบ {n}").filter(visible=True).first


def test_each_angle_shows_one_next_step_and_a_worded_list_row(motion_fixture_url):
    original = _with_angles()
    fixture = _Fixture()
    try:
        with base._product_page(motion_fixture_url, fixture) as page:
            expect(page.get_by_text("พื้นที่ทำงานสคริปต์")).to_have_count(0)
            progress = page.get_by_role("list", name="ความคืบหน้าของสินค้านี้")
            expect(progress).to_be_visible()
            expect(progress.get_by_role("listitem")).to_have_count(5)

            for n, (chip, primary, secondary) in EXPECTED.items():
                row = _row(page, n)
                expect(row).to_contain_text(f"hook ของมุม {n}")
                expect(row).to_contain_text(chip)
                row.click()
                expect(page.get_by_role("heading", name=f"มุมทดสอบ {n}")).to_be_visible()
                bar = page.get_by_role("group", name="ขั้นต่อไปของมุมนี้")
                buttons = [b.strip() for b in bar.get_by_role("button").filter(visible=True).all_inner_texts()]
                assert buttons == secondary + [primary], (n, buttons)
                filled = bar.locator("button.bg-\\[\\#25F4EE\\]").filter(visible=True)
                expect(filled).to_have_count(1)
                expect(filled).to_have_text(primary)

            # The old competing buttons and the duplicate clip button are gone.
            for gone in ("เลือกคลิปก่อนส่งตัดต่อ", "ส่งมุมนี้เข้าสู่กระบวนการถ่ายทำ", "เปิดตัดต่อทันที", "สร้างแผนถ่าย"):
                expect(page.get_by_role("button", name=gone)).to_have_count(0)

            # The filled button runs the step: with no clips it opens the clip picker.
            _row(page, 1).click()
            page.get_by_role("group", name="ขั้นต่อไปของมุมนี้").get_by_role("button", name="เลือกคลิป").click()
            expect(page.get_by_role("dialog").filter(has_text="เลือกคลิปสำหรับมุม: มุมทดสอบ 1")).to_be_visible()
            assert fixture.writes == []
            assert not fixture.page_errors
    finally:
        base.PRODUCTS[0]["angles"] = original


def test_phone_brings_the_panel_into_view_and_keeps_its_bar_short(motion_fixture_url):
    original = _with_angles()
    fixture = _Fixture()
    try:
        with base._product_page(motion_fixture_url, fixture, viewport=(390, 844)) as page:
            _row(page, 5).click()
            expect(page.get_by_role("heading", name="มุมทดสอบ 5")).to_be_in_viewport()
            # The title keeps its own line instead of being squeezed out by the panel's tools.
            assert page.get_by_role("heading", name="มุมทดสอบ 5").bounding_box()["width"] > 60
            bar = page.get_by_role("group", name="ขั้นต่อไปของมุมนี้")
            expect(bar.get_by_role("button", name="ดูคลิป")).to_be_in_viewport()
            assert bar.bounding_box()["height"] < 80

            bar.get_by_role("button", name="ทางเลือกอื่นของมุมนี้").click()
            menu = page.get_by_role("menu", name="ทางเลือกอื่นของมุมนี้")
            for label in EXPECTED[5][2]:
                expect(menu.get_by_role("menuitem", name=label)).to_be_visible()
            page.keyboard.press("Escape")
            expect(menu).to_have_count(0)
            assert fixture.writes == []
            assert not fixture.page_errors
    finally:
        base.PRODUCTS[0]["angles"] = original


def test_wide_screen_puts_the_next_step_beside_the_script(motion_fixture_url):
    original = _with_angles()
    fixture = _Fixture()
    try:
        with base._product_page(motion_fixture_url, fixture, viewport=(1920, 945)) as page:
            _row(page, 3).click()
            bar = page.get_by_role("group", name="ขั้นต่อไปของมุมนี้").bounding_box()
            script = page.get_by_text("บรรทัดหนึ่ง").first.bounding_box()
            assert bar["x"] > script["x"] + 400, (bar, script)
            assert bar["y"] < script["y"] + script["height"], (bar, script)
            assert not fixture.page_errors
        with base._product_page(motion_fixture_url, fixture, viewport=(1440, 900)) as page:
            _row(page, 3).click()
            bar = page.get_by_role("group", name="ขั้นต่อไปของมุมนี้").bounding_box()
            assert bar["width"] > 600, bar  # one column below 1536px: the bar spans the panel
    finally:
        base.PRODUCTS[0]["angles"] = original
