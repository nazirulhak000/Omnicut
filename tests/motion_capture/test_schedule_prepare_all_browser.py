"""The schedule table's bulk prepare button, in a real browser with an offline API fixture."""
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

BANGKOK = timezone(timedelta(hours=7))
REFUSAL = "คลิปนี้ถูกโพสต์ไปแล้ว ไม่ต้องส่งเข้า Extension ซ้ำ"


def _row(queue_id, status, days):
    when = (datetime.now(BANGKOK) + timedelta(days=days)).replace(microsecond=0)
    return {"id": queue_id, "status": status, "scheduled_at": when.isoformat(),
            "export_id": f"export-{queue_id}", "video_path": f"04_Exports/main/{queue_id}.mp4",
            "product_name": f"Fixture {queue_id}", "caption": "", "hashtags": ""}


class _Fixture:
    """Offline API for the schedule tab. The prepare call for `hold_id` stays open until `release()`."""

    def __init__(self, queue, hold_id):
        self.queue, self.hold_id = queue, hold_id
        self.prepared, self.other_writes, self.held, self.page_errors = [], [], [], []

    def answer_prepare(self, route, queue_id):
        if queue_id == "refused":
            route.fulfill(status=409, content_type="application/json", body=json.dumps({"detail": REFUSAL}))
            return
        row = next(item for item in self.queue if item["id"] == queue_id)
        row["status"] = "ready_for_extension"
        route.fulfill(content_type="application/json", body=json.dumps(row))

    def release(self):
        self.answer_prepare(self.held[0], self.hold_id)

    def api(self, route):
        request = route.request
        path = urlsplit(request.url).path
        parts = path.split("/")
        if request.method == "POST" and path.startswith("/api/schedule-queue/") and parts[-1] == "prepare":
            queue_id = parts[-2]
            self.prepared.append(queue_id)
            if queue_id == self.hold_id:
                self.held.append(route)
            else:
                self.answer_prepare(route, queue_id)
            return
        if request.method != "GET":
            self.other_writes.append((request.method, path))
            route.fulfill(status=503, content_type="application/json", body='{"detail":"fixture is read only"}')
            return
        if path == "/api/channels":
            data = {"revision": 1, "channels": [{"id": "main", "display_name": "main", "status": "active", "revision": 1}]}
        elif path == "/api/schedule-queue":
            data = {"items": self.queue}
        else:
            data = {"items": [], "exports": [], "tasks": [], "videos": [], "products": [], "catalog": {},
                    "milestones": [], "custom": []}
        route.fulfill(content_type="application/json", headers={"X-OmniCut-Channel": "main"}, body=json.dumps(data))

    def wait_for_held_request(self, page):
        for _ in range(50):
            if self.held:
                break
            page.wait_for_timeout(100)
        page.wait_for_timeout(400)  # room for a second request to show up, if one were sent
        assert len(self.held) == 1 and self.prepared == [self.hold_id]


@contextmanager
def _schedule_tab(fixture_url, fixture):
    parsed = urlsplit(fixture_url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900}, ignore_https_errors=True)
            page.on("pageerror", lambda error: fixture.page_errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("""localStorage.setItem('capcut_active_tab','tracker');
              localStorage.setItem('omnicut.ui_mode','desktop');
              localStorage.setItem('capcut_tracker_view_mode','schedule');""")
            page.route("**/api/**", fixture.api)
            page.goto(f"{parsed.scheme}://{parsed.netloc}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            yield page
        finally:
            browser.close()


def test_prepare_all_sends_waiting_rows_one_at_a_time_and_reports_refusals(motion_fixture_url):
    fixture = _Fixture([
        _row("third", "planned", 3),
        _row("first", "planned", 1),
        _row("refused", "planned", 2),
        _row("overdue", "planned", -1),
        _row("failed", "failed", 1),
        _row("sent", "ready_for_extension", 1),
    ], hold_id="first")
    with _schedule_tab(motion_fixture_url, fixture) as page:
        button = page.get_by_role("button", name="เตรียมทั้งหมด (3)", exact=True)
        expect(button).to_be_visible(timeout=30000)

        # Cancelling the confirmation sends nothing.
        button.click()
        confirm = page.get_by_role("dialog").filter(has_text="ส่ง 3 คิวให้ Extension หรือไม่?")
        expect(confirm).to_contain_text("ข้าม: เลยกำหนด 1 คิว · ล้มเหลว 1 คิว")
        confirm.get_by_role("button", name="ยกเลิก", exact=True).click()
        expect(confirm).to_be_hidden()
        assert fixture.prepared == []

        button.click()
        confirm.get_by_role("button", name="ยืนยัน", exact=True).click()

        # The first request is still open: nothing else was sent, and the button shows progress.
        expect(page.get_by_role("button", name="กำลังเตรียม 0/3", exact=True)).to_be_disabled()
        fixture.wait_for_held_request(page)

        fixture.release()
        expect(page.get_by_text(f"ส่งให้ Extension 2 คิว · ส่งไม่ได้ 1 คิว ({REFUSAL})", exact=True)).to_be_visible()
        assert fixture.prepared == ["first", "refused", "third"]  # schedule order, one at a time
        # The refused row is still waiting; overdue, failed and already-sent rows were never touched.
        expect(page.get_by_role("button", name="เตรียมทั้งหมด (1)", exact=True)).to_be_enabled()
        assert not fixture.other_writes
        assert not fixture.page_errors


def test_prepare_all_stops_when_the_schedule_table_is_closed(motion_fixture_url):
    fixture = _Fixture([_row("first", "planned", 1), _row("second", "planned", 2), _row("third", "planned", 3)],
                       hold_id="first")
    with _schedule_tab(motion_fixture_url, fixture) as page:
        button = page.get_by_role("button", name="เตรียมทั้งหมด (3)", exact=True)
        expect(button).to_be_visible(timeout=30000)
        button.click()
        page.get_by_role("dialog").get_by_role("button", name="ยืนยัน", exact=True).click()
        fixture.wait_for_held_request(page)

        # Leave the schedule table while the first request is still open.
        page.get_by_title("มุมมองบอร์ด 4 เฟส (Kanban)").click()
        expect(button).to_be_hidden()
        fixture.release()

        expect(page.get_by_text(
            "หยุดก่อนครบเพราะออกจากตารางโพสต์หรือเปลี่ยนช่อง · ส่งให้ Extension แล้ว 1 คิว ยังไม่ได้ส่ง 2 คิว", exact=True,
        )).to_be_visible()
        page.wait_for_timeout(600)
        assert fixture.prepared == ["first"]  # the two rows after it stay waiting
        assert not fixture.other_writes
        assert not fixture.page_errors
