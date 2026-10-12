"""Mounted Schedule publication review with offline TikTok/API fixtures."""
from datetime import datetime
import json
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.parametrize("width,missing_id", [(390, False), (1440, False), (390, True)])
def test_publication_review_requires_exact_link_actual_time_and_manual_confirmation(motion_fixture_url, width, missing_id):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    local_today = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d")
    job = {"id": "job-review", "job_id": "job-review", "channel_id": "main", "revision": 7,
           "target_handle": "@mainuser", "status": "scheduled_on_platform",
           "receipt": {"outcome": "scheduled_on_platform", "source_account": "@mainuser",
                       "proof": {} if missing_id else {"platform_post_id": "123456789"}}}
    item = {"id": "queue-review", "channel_id": "main", "posting_job_id": "job-review",
            "export_id": "export-review", "status": "scheduled_on_platform", "product_name": "Review fixture",
            "video_path": "04_Exports/fixture.mp4", "scheduled_at": f"{local_today}T09:00:00+07:00"}
    writes, unexpected = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": 900}, ignore_https_errors=True)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
            page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
            page.add_init_script("""localStorage.setItem('capcut_active_tab','tracker');
              localStorage.setItem('omnicut.ui_mode','desktop');
              localStorage.setItem('capcut_tracker_view_mode','schedule');""")

            def route_api(route):
                request = route.request
                path = urlsplit(request.url).path
                owner = request.headers.get("x-omnicut-channel", "main")
                headers = {"X-OmniCut-Channel": owner}
                if request.method == "POST":
                    if path.endswith("/publication-observations"):
                        writes.append((owner, request.post_data_json))
                        route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps({"observation": {"id": "event-review", "status": "verified", "effects_applied": True}, "review_mode": "manual_platform_review"}))
                        item["status"] = "posted"
                    else:
                        unexpected.append(path)
                        route.fulfill(status=500, headers=headers, content_type="application/json", body='{"detail":"unexpected write"}')
                    return
                if path == "/api/channels":
                    data = {"channels": [{"id": "main", "display_name": "main", "handle": "@mainuser", "status": "active", "revision": 1}], "revision": 1}
                elif path == "/api/schedule-queue":
                    data = {"items": [item], "timezone": "Asia/Bangkok"}
                elif path == "/api/tiktok-autopost/jobs/job-review":
                    data = job
                elif path.endswith("/publication-observations"):
                    data = {"items": []}
                elif path == "/api/schedule-queue/template":
                    data = {"days": {str(i): {"enabled": True, "times": ["09:00", "12:30", "16:00", "19:00", "21:30"]} for i in range(7)}}
                elif path == "/api/assets/all":
                    data = {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []}
                else:
                    data = {"items": [], "products": [], "projects": [], "videos": [], "exports": [], "tasks": [], "milestones": [], "custom": [], "catalog": {}}
                route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(data))

            page.route("**/api/**", route_api)
            page.goto(f"{origin}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            button = page.get_by_role("button", name="ตรวจว่าโพสต์จริงแล้ว", exact=True)
            expect(button).to_be_visible(timeout=20000)
            button.click()
            dialog = page.get_by_role("dialog").filter(has=page.get_by_role("heading", name="ตรวจการเผยแพร่จริง", exact=True))
            expect(dialog).to_be_visible()
            if missing_id:
                expect(dialog.get_by_role("alert")).to_contain_text("ยังไม่มีรหัสวิดีโอ")
                expect(dialog.get_by_role("button", name="บันทึกการเผยแพร่จริง", exact=True)).to_have_count(0)
                assert writes == []
            else:
                submit = dialog.get_by_role("button", name="บันทึกการเผยแพร่จริง", exact=True)
                expect(submit).to_be_disabled()
                dialog.get_by_label("วันและเวลาที่เผยแพร่จริง (เวลาไทย UTC+7)").fill("2026-10-10T09:30")
                expect(submit).to_be_disabled()
                dialog.get_by_role("checkbox").check()
                expect(submit).to_be_enabled()
                dialog.get_by_label("ลิงก์วิดีโอที่เผยแพร่แล้ว").fill("https://www.tiktok.com/@seconduser/video/123456789")
                submit.click()
                expect(dialog.get_by_role("alert")).to_contain_text("ลิงก์ต้องตรงบัญชี")
                assert writes == []
                dialog.get_by_label("ลิงก์วิดีโอที่เผยแพร่แล้ว").fill("https://www.tiktok.com/@mainuser/video/123456789")
                submit.click()
                expect(dialog).not_to_be_visible()
                assert len(writes) == 1
                assert writes[0][0] == "main"
                assert writes[0][1]["review_confirmation"] == "reviewed_published_video"
                assert writes[0][1]["expected_job_revision"] == 7
                assert writes[0][1]["observed_published_at"].endswith("+07:00")
                assert "published" not in writes[0][1]
            assert unexpected == []
            assert errors == []
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        finally:
            browser.close()
