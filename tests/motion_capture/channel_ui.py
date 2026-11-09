"""Channel-selector access for browser tests.

Below the `md` breakpoint the Topbar hides the channel <select>; it lives in the
Sidebar's "อื่นๆ" bottom sheet instead (Sidebar.jsx, "moved off the phone topbar").
`ChannelSelect` hides that difference so a test can pick/assert a channel at any width.
The sheet overlay blocks pointer events, so call `settle()` before touching page content.
"""
from playwright.sync_api import expect

PHONE_MAX_WIDTH = 767  # Tailwind `md` starts at 768


class ChannelSelect:
    def __init__(self, page, width):
        self.page = page
        self.phone = width <= PHONE_MAX_WIDTH
        self.select = page.get_by_role("combobox", name="เลือกช่อง")
        self.sheet = page.get_by_role("dialog", name="เมนูเพิ่มเติม")

    def open(self):
        if self.phone and self.sheet.count() == 0:
            self.page.get_by_role("button", name="อื่นๆ", exact=True).click()
            expect(self.sheet).to_be_visible()

    def settle(self):
        if self.phone and self.sheet.count():
            self.page.get_by_role("button", name="ปิดเมนูเพิ่มเติม", exact=True).click()
            expect(self.sheet).to_have_count(0)

    def pick(self, channel_id):
        self.open()
        self.select.select_option(channel_id)

    def expect(self, channel_id):
        if self.phone:  # do not open the sheet while a switch is still settling
            self.page.wait_for_function("id => new URL(location.href).searchParams.get('channel') === id", arg=channel_id)
        self.open()
        expect(self.select).to_have_value(channel_id)

    def expect_visible(self):
        self.open()
        expect(self.select).to_be_visible()
        self.settle()
