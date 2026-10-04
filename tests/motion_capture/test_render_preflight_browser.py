"""Exercise the production editor gate with isolated API data and synthetic media."""
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect

from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import vite_fs_url


def test_preflight_seek_reload_and_blocks_missing_source(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("render-preflight-") as directory:
        source = vite_fs_url(base, create_clip_source(Path(directory)))
        clips = [{"source_path": source, "trim_start": 0, "trim_end": 2, "speed": 1},
                 {"source_path": source, "trim_start": 0, "trim_end": 2, "speed": 1,
                  "freeze_tail": 3, "source_window": {"start": 0, "end": 2},
                  "footage_shortage": {"reason": "source_window_exhausted", "missing_seconds": 3}}]
        manifest = {"project_name": "editor-audit", "clip_list": clips, "transitions": [],
                    "cues": [], "artifacts": {}, "show_watermark": False}
        requests = []
        errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1600, "height": 1000}, ignore_https_errors=True)
                page.on("pageerror", lambda error: errors.append(str(error)))

                def api(route):
                    path = urlsplit(route.request.url).path
                    requests.append((route.request.method, path))
                    response = manifest if path == "/api/projects/editor-audit" else (
                        {"projects": ["editor-audit"]} if path == "/api/projects" else
                        {"products": [{"id": "fixture", "angles": [{"angle_id": "fixture-angle",
                         "project_name": "editor-audit", "status": "in_production", "cover_path": "fixture.webp"}]}]} if path == "/api/products" else
                        {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []} if path == "/api/assets/all" else
                        {"catalog": {}, "default": None} if path == "/api/hook-motion-presets" else
                        {"tasks": [], "milestones": [], "custom": []})
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(response))

                page.route("**/api/**", api)
                page.goto(f"{base}/editor_shell_audit.html?clip={source}&renderAudit=1", wait_until="domcontentloaded")
                notice = page.locator("[data-render-preflight]")
                notice.wait_for(state="visible", timeout=15000)
                notice.locator("summary").click()
                assert "00:04.00" in notice.inner_text()
                notice.get_by_role("button", name="ดูช่วงนี้").first.click()
                # The editor time readout uses seconds:frame rather than centiseconds.
                readout = page.locator('[title="เวลาปัจจุบัน / เวลาทั้งหมดของคลิป (นาที:วินาที:เฟรม ที่ 30 fps)"]')
                expect(readout.locator("span").first).to_have_text("00:04:00")
                page.reload(wait_until="domcontentloaded")
                notice.wait_for(state="visible", timeout=15000)
                assert "3.00" in notice.inner_text()

                clips[1]["source_path"] = ""
                page.reload(wait_until="domcontentloaded")
                notice.wait_for(state="visible", timeout=15000)
                assert "คลิปไม่มีตำแหน่งไฟล์ต้นฉบับ" in notice.inner_text()
                requests.clear()
                page.get_by_role("button", name="เรนเดอร์", exact=True).click()
                page.get_by_text("ช็อต 2 00:02.00: คลิปไม่มีตำแหน่งไฟล์ต้นฉบับ", exact=False).first.wait_for()
                assert not any(method == "POST" for method, _ in requests), requests
                assert errors == [], errors
            finally:
                browser.close()
