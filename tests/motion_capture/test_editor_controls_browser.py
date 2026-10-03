"""Real Chromium interaction gate for production ClipInspector controls."""

from __future__ import annotations

import json
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright


def test_clip_inspector_keyboard_edit_and_save_reload_in_real_browser(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    url = f"{parsed.scheme}://{parsed.netloc}/editor_controls.html"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 820, "height": 1100}, ignore_https_errors=True)
            page.goto(url, wait_until="domcontentloaded")
            page.get_by_test_id("editor-controls-ready").wait_for()

            trim_in = page.get_by_role("spinbutton", name="Trim เข้า (วิ)")
            trim_in.fill("0.5")
            page.get_by_role("button", name="2x", exact=True).click()
            page.get_by_role("button", name="90°", exact=True).click()
            blur = page.get_by_role("button", name="พื้นหลังเบลอ", exact=True)
            blur.click()
            assert page.get_by_role("button", name="✓ พื้นหลังเบลอ").get_attribute("aria-pressed") == "true"
            assert page.get_by_role("button", name="2x", exact=True).get_attribute("aria-pressed") == "true"

            page.get_by_role("button", name="Save fixture").click()
            page.get_by_role("button", name="1x", exact=True).click()
            page.get_by_role("button", name="Reload fixture").click()
            snapshot = json.loads(page.get_by_test_id("editor-controls-state").inner_text())
            clip = snapshot["clip"]
            assert clip["trim_start"] == 0.5
            assert clip["speed"] == 2
            assert clip["rotation"] == 90
            assert clip["fit_mode"] == "blur"
            assert page.get_by_role("button", name="2x", exact=True).get_attribute("aria-pressed") == "true"

            trim_in.fill("99")
            bounded = json.loads(page.get_by_test_id("editor-controls-state").inner_text())
            assert bounded["clip"]["trim_start"] == 2.8

            page.get_by_role("button", name="Save fixture").focus()
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement?.textContent?.trim()") == "Reload fixture"
        finally:
            browser.close()


def test_timeline_keyboard_reorder_context_split_and_save_reload_in_real_browser(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    url = f"{parsed.scheme}://{parsed.netloc}/editor_controls.html"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
            page.goto(url, wait_until="domcontentloaded")
            timeline = page.get_by_test_id("timeline-controls-ready")
            timeline.wait_for()
            clips = timeline.locator('[data-timeline-item="clip"]')
            assert clips.count() == 2

            clips.first.focus()
            page.keyboard.press("]")
            state = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert [item["source_path"] for item in state["timelineClips"]] == ["right.mp4", "left.mp4"]

            clips.first.click(button="right")
            page.get_by_role("button", name="ผ่าคลิปตรงหัวอ่าน").click()
            assert clips.count() == 3
            state = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert state["timelineClips"][0]["trim_end"] == 1
            assert state["timelineClips"][1]["trim_start"] == 1

            page.get_by_role("button", name="Save timeline").click()
            clips.first.click(button="right")
            page.keyboard.press("Escape")
            assert page.locator("[data-context-menu]").count() == 0
            clips.first.click(button="right")
            page.get_by_role("button", name="ลบคลิป").click()
            assert clips.count() == 2
            page.get_by_role("button", name="Reload timeline").click()
            assert clips.count() == 3
            reloaded = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert [item["source_path"] for item in reloaded["timelineClips"]] == [
                "right.mp4", "right.mp4", "left.mp4",
            ]
        finally:
            browser.close()


def test_timeline_trim_drag_snaps_to_boundary_in_real_browser(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    url = f"{parsed.scheme}://{parsed.netloc}/editor_controls.html"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
            page.goto(url, wait_until="domcontentloaded")
            timeline = page.get_by_test_id("timeline-controls-ready")
            clip = timeline.locator('[data-timeline-item="clip"]').first
            clip.click()
            handle = clip.locator('[data-trim-handle][title="ลากปรับจุดเริ่ม"]')
            box = handle.bounding_box()
            start_x = box["x"] + box["width"] / 2
            start_y = box["y"] + box["height"] / 2
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(start_x + 46, start_y, steps=3)
            page.mouse.up()
            state = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert state["timelineClips"][0]["trim_start"] == 0.5
            page.get_by_role("button", name="Undo timeline").click()
            undone = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert undone["timelineClips"][0]["trim_start"] == 0
            page.get_by_role("button", name="Redo timeline").click()
            redone = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert redone["timelineClips"][0]["trim_start"] == 0.5
        finally:
            browser.close()


def test_timeline_drop_adds_clip_and_persists_after_reload(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    url = f"{parsed.scheme}://{parsed.netloc}/editor_controls.html"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            # The timeline sits below the clip inspector on this fixture page, so
            # the viewport must be tall enough to keep the drop target on screen
            # as the inspector grows. A drag onto an off-screen target never lands.
            page = browser.new_page(viewport={"width": 1100, "height": 1500}, ignore_https_errors=True)
            page.goto(url, wait_until="domcontentloaded")
            timeline = page.get_by_test_id("timeline-controls-ready")
            source = page.get_by_test_id("timeline-source-clip")
            video_track = page.get_by_test_id("timeline-video-track")
            source.drag_to(video_track)
            state = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert len(state["timelineClips"]) == 3
            assert any(item["source_path"] == "added.mp4" for item in state["timelineClips"])

            page.get_by_role("button", name="Save timeline").click()
            timeline.locator('[data-timeline-item="clip"]').last.click(button="right")
            page.get_by_role("button", name="ลบคลิป").click()
            page.get_by_role("button", name="Reload timeline").click()
            restored = json.loads(page.get_by_test_id("timeline-controls-state").inner_text())
            assert len(restored["timelineClips"]) == 3
            assert any(item["source_path"] == "added.mp4" for item in restored["timelineClips"])
        finally:
            browser.close()


def test_missing_media_shows_actionable_preview_error(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    url = f"{parsed.scheme}://{parsed.netloc}/editor_controls.html?missingClip=1"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
            page.goto(url, wait_until="domcontentloaded")
            alert = page.get_by_test_id("missing-media-preview").get_by_role("alert")
            alert.wait_for(timeout=5000)
            assert "ไม่พบวิดีโอสำหรับคลิปนี้" in alert.inner_text()
            assert "ตรวจสอบไฟล์ต้นฉบับ" in alert.inner_text()
        finally:
            browser.close()


def test_visible_editor_fixture_controls_have_accessible_names(motion_fixture_url):
    parsed = urlsplit(motion_fixture_url)
    url = f"{parsed.scheme}://{parsed.netloc}/editor_controls.html"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1100, "height": 1100}, ignore_https_errors=True)
            page.goto(url, wait_until="domcontentloaded")
            page.get_by_test_id("editor-controls-ready").wait_for()
            unnamed = page.evaluate("""() => [...document.querySelectorAll(
                'button,input,select,textarea,[role="button"]'
            )].filter(node => {
                const rect = node.getBoundingClientRect();
                if (!rect.width || !rect.height || getComputedStyle(node).visibility === 'hidden') return false;
                const labels = [...(node.labels || [])].map(label => label.textContent).join(' ');
                const name = node.getAttribute('aria-label') || node.getAttribute('title')
                    || node.getAttribute('aria-labelledby') || labels || node.textContent;
                return !name?.trim();
            }).map(node => node.outerHTML.slice(0, 240))""")
            assert not unnamed, unnamed
        finally:
            browser.close()


@pytest.mark.parametrize("kind", ["clip", "caption", "text_overlay", "hook", "sticker", "effect", "project", "cues"])
def test_inspector_panel_visible_controls_have_accessible_names(motion_fixture_url, kind):
    parsed = urlsplit(motion_fixture_url)
    url = f"{parsed.scheme}://{parsed.netloc}/editor_controls.html?inspectorAudit=1"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 900, "height": 1000}, ignore_https_errors=True)
            page.set_default_timeout(5000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url, wait_until="domcontentloaded")
            page.get_by_test_id(f"inspector-audit-{kind}").click()
            panel = page.get_by_test_id("inspector-audit-panel")
            if kind in ("project", "cues"):
                panel.get_by_role("button", name="ภาพรวม" if kind == "project" else "บทพูด", exact=False).first.click()
            assert not errors, errors
            panel.get_by_role("button").first.wait_for()
            unnamed = panel.evaluate("""root => [...root.querySelectorAll(
                'button,input,select,textarea,[role="button"]'
            )].filter(node => {
                const rect = node.getBoundingClientRect();
                if (!rect.width || !rect.height || getComputedStyle(node).visibility === 'hidden') return false;
                const labels = [...(node.labels || [])].map(label => label.textContent).join(' ');
                const name = node.getAttribute('aria-label') || node.getAttribute('title')
                    || node.getAttribute('aria-labelledby') || labels || node.textContent;
                return !name?.trim();
            }).map(node => node.outerHTML.slice(0, 240))""")
            assert not errors, errors
            assert not unnamed, {"kind": kind, "unnamed": unnamed}
        finally:
            browser.close()
