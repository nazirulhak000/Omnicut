import json
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from playwright.sync_api import sync_playwright
from tests.motion_capture.capture import temp_capture_dir
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import vite_fs_url


@pytest.mark.parametrize("width", [390, 1600])
def test_coverage_notice_survives_editor_reload(motion_fixture_url, width):
    parsed = urlsplit(motion_fixture_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    with temp_capture_dir("footage-coverage-") as directory:
        clip_url = vite_fs_url(base, create_clip_source(Path(directory)))
        manifest = {"project_name": "editor-audit", "clip_list": [{"source_path": clip_url,
                    "trim_start": 0, "trim_end": 2, "speed": 1, "freeze_tail": 6,
                    "source_window": {"start": 0, "end": 2},
                    "footage_shortage": {"reason": "source_window_exhausted", "missing_seconds": 6}}],
                    "transitions": [], "cues": [], "artifacts": {}, "show_watermark": False}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": width, "height": 1000}, ignore_https_errors=True)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                def api(route):
                    path = urlsplit(route.request.url).path
                    response = manifest if path == "/api/projects/editor-audit" else (
                        {"projects": ["editor-audit"]} if path == "/api/projects" else
                        {"products": [{"id": "fixture", "angles": [{"angle_id": "fixture-angle", "project_name": "editor-audit", "status": "in_production"}]}]} if path == "/api/products" else
                        {"sfx": [], "music": [], "fonts": [], "stickers": [], "luts": [], "effects": []} if path == "/api/assets/all" else
                        {"catalog": {}, "default": None} if path == "/api/hook-motion-presets" else
                        {"tasks": [], "milestones": [], "custom": []})
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(response))
                page.route("**/api/**", api)
                page.goto(f"{base}/editor_shell_audit.html?clip={clip_url}&renderAudit=1", wait_until="domcontentloaded")
                page.locator('[data-timeline-item="clip"]:visible').first.wait_for(timeout=15000)
                assert errors == [], errors
                notice = page.locator("[data-footage-coverage-notice]")
                assert notice.count() > 0, page.locator('body').inner_text()[:1800]
                notice.wait_for(state="visible", timeout=15000)
                assert "6.00" in notice.inner_text()
                page.reload(wait_until="domcontentloaded")
                notice.wait_for(state="visible", timeout=15000)
                assert "6.00" in notice.inner_text()
                assert errors == []
            finally:
                browser.close()
