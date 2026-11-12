"""The schedule table's "แก้ caption ที่ติดราคา" flow in a real browser, offline API fixture (owner decision 2026-11-13)."""
import json
from urllib.parse import urlsplit

from playwright.sync_api import expect

from tests.motion_capture.test_schedule_prepare_all_browser import _Fixture, _row, _schedule_tab

OLD = "ของดีราคาพิเศษในตะกร้าเลยครับ"
NEW = "ของดีสุดคุ้มกดดูตรงตะกร้าได้เลยครับ"


class _CaptionFixture(_Fixture):
    def __init__(self, queue):
        super().__init__(queue, hold_id=None)
        self.previews, self.commits = 0, []

    def api(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if request.method == "POST" and path == "/api/schedule-queue/fix-price-captions/preview":
            self.previews += 1
            body = {"items": [{"id": "pricey", "scheduled_at": self.queue[0]["scheduled_at"], "product_name": "Fixture pricey",
                               "from_caption": OLD, "from_hashtags": "", "caption": NEW, "hashtags": "", "method": "ai"}],
                    "locked_count": 0}
            route.fulfill(content_type="application/json", body=json.dumps(body))
            return
        if request.method == "POST" and path == "/api/schedule-queue/fix-price-captions":
            items = json.loads(request.post_data)["items"]
            self.commits.append(items)
            row = self.queue[0]
            row["caption"] = NEW
            row.pop("caption_blocked", None)
            route.fulfill(content_type="application/json", body=json.dumps({"success": True, "count": 1, "angles_updated": 1}))
            return
        super().api(route)


def test_caption_fix_previews_before_saving_and_clears_the_warning(motion_fixture_url):
    pricey = {**_row("pricey", "planned", 1), "caption": OLD, "caption_blocked": "price_in_caption"}
    fixture = _CaptionFixture([pricey, _row("clean", "planned", 2)])
    with _schedule_tab(motion_fixture_url, fixture) as page:
        button = page.get_by_role("button", name="แก้ caption ที่ติดราคา (1)", exact=True)
        expect(button).to_be_visible(timeout=30000)
        button.click()
        dialog = page.get_by_role("dialog").filter(has_text="แก้ caption ที่ติดราคา")
        expect(dialog).to_contain_text(OLD)
        expect(dialog).to_contain_text(NEW)
        expect(dialog).to_contain_text("AI เขียนใหม่")
        assert fixture.commits == []                                   # opening the preview saves nothing

        dialog.get_by_role("button", name="บันทึก caption ใหม่ 1 คลิป", exact=True).click()
        expect(page.get_by_text("แก้ caption แล้ว 1 คลิป · อัปเดตมุมต้นทาง 1 มุม", exact=True)).to_be_visible()
        assert fixture.commits[0][0]["id"] == "pricey" and fixture.commits[0][0]["caption"] == NEW
        expect(button).to_be_hidden()                                   # the reloaded queue has no blocked row left
        assert [w for w in fixture.other_writes if "fix-price-captions" not in w[1]] == []
        assert not fixture.page_errors
