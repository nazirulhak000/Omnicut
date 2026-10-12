"""Actual HF/App UI with isolated API fixtures; never touches live stores."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright


CHANNELS = [{"id": owner, "display_name": label, "handle": "@" + owner, "status": "active", "revision": 1}
            for owner, label in [("main", "Main fixture"), ("second", "Second fixture")]]
PRODUCT = {"id": "product-real", "name": "HF fixture product", "product_code": "HFF01", "channel_id": "main",
           "angles": [{"id": "angle-real", "title": "Saved fixture angle", "hook_headline": "Approved hook"}]}


def app_url(fixture):
    parsed = urlsplit(fixture)
    return f"{parsed.scheme}://{parsed.netloc}/?channel=main&mode=desktop"


def install_mock(page):
    state = {"project": None, "creative": None, "render": None, "writes": [], "delayed": []}
    page.add_init_script("""localStorage.setItem('capcut_active_tab','creative');
      localStorage.setItem('omnicut.ui_mode','desktop');
      Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>{window.__hfCopied=text;}}});""")
    page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
    page.route("https://fonts.gstatic.com/**", lambda route: route.abort())

    def api(route):
        request = route.request
        path = urlsplit(request.url).path
        owner = request.headers.get("x-omnicut-channel", "main")
        headers = {} if path == "/api/channels" else {"X-OmniCut-Channel": owner}
        data = request.post_data_json if request.method in {"POST", "PATCH"} and request.post_data else None
        if data:
            state["writes"].append((owner, path, data))
        if path == "/api/channels":
            result = {"channels": CHANNELS, "revision": 1}
        elif path == "/api/products":
            result = {"products": [PRODUCT] if owner == "main" else []}
        elif path == "/api/hyperframes/projects":
            if request.method == "POST":
                state["project"] = {"project_id": "a" * 32, "project_name": "main/HF_fixture", "channel_id": owner,
                                    "revision": 1, "brief_revision": 1, "accepted_revision": None,
                                    "inputs": data["inputs"], "source_binding": data["source_binding"]}
                result = {"project": state["project"]}
            else:
                result = {"projects": [state["project"]] if state["project"] and owner == "main" else []}
        elif path.endswith("/authoring-jobs") and request.method == "POST":
            state["creative"] = {"id": "creative-fixture", "status": "queued", "base_revision": state["project"]["revision"],
                                 "project_id": state["project"]["project_id"], "created_at": 1000, "checkpoint": None}
            result = {"job": state["creative"]}
        elif path.endswith("/handoff"):
            result = {"handoff": {"work_id": "creative-fixture", "channel_id": owner, "input_hash": "input-fixture",
                                    "work_path": "03_Projects/_HyperFrames_Studio/work/creative-fixture",
                                    "checkpoint": state["creative"].get("checkpoint"), "next_action": "Claim and author locally"}}
        elif path.endswith("/accept-revision"):
            state["project"]["accepted_revision"] = state["creative"]["submitted_revision"]
            state["project"]["revision"] += 1
            result = {"project": state["project"]}
        elif path.endswith("/render-jobs") and request.method == "POST":
            state["render"] = {"id": "render-fixture", "status": "queued", "phase": "queued", "revision": 4,
                               "snapshot": {"id": "revision-fixture"}, "created_at": 1001, "artifact": None}
            result = {"job": state["render"]}
        elif path.endswith("/finalize"):
            state["render"].update(status="finalized", phase="finalized", export_id="export-fixture")
            result = {"job": state["render"]}
        elif "/artifact/" in path:
            route.fulfill(status=200, content_type="video/mp4", headers=headers, body=b"isolated fixture response")
            return
        elif path == "/api/hyperframes/projects/" + "a" * 32:
            if state.get("hold_project_read"):
                state["delayed"].append((route, owner))
                return
            if request.method == "PATCH":
                state["project"].update(inputs=data["inputs"], accepted_revision=None)
                state["project"]["revision"] += 1
                state["project"]["brief_revision"] += 1
            result = {"project": state["project"], "authoring_jobs": [state["creative"]] if state["creative"] else [],
                      "render_jobs": [state["render"]] if state["render"] else []}
        elif path == "/api/hyperframes/status":
            result = {"ready": True, "installed": True, "cli_version": "fixture"}
        elif path == "/api/hyperframes/styles":
            result = {"styles": []}
        elif path == "/api/hyperframes/compositions":
            result = {"compositions": []}
        else:
            result = {"products": [], "exports": [], "videos": [], "tasks": [], "queue": [], "catalog": {}, "items": [], "styles": []}
        route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(result))

    page.route("**/api/**", api)
    return state


def workflow(page):
    return page.get_by_role("region", name="ผลิตคลิปด้วย AI และส่งออกเข้าคิวเดิม")


def create_silent(page):
    surface = workflow(page)
    expect(surface).to_be_visible(timeout=15000)
    expect(surface.get_by_label("สินค้า", exact=True)).to_have_count(1)
    surface.get_by_label("สินค้า", exact=True).select_option("product-real")
    surface.get_by_label("Angle", exact=True).select_option("angle-real")
    surface.get_by_label("Brief ที่ต้องการให้ AI ทำ", exact=True).fill("Fixture brief")
    surface.get_by_label("เสียง", exact=True).select_option("silent")
    surface.get_by_role("button", name="บันทึก brief และเจ้าของงาน", exact=True).click()
    expect(surface.get_by_role("button", name="เตรียมแพ็กเกจงาน AI", exact=True)).to_be_visible()
    return surface


@pytest.mark.parametrize("width", [390, 1440])
def test_hf_creation_ai_revision_render_finalize_real_ui(motion_fixture_url, tmp_path, width):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        screenshot = tmp_path / f"hf-workflow-{width}.png"
        try:
            page = browser.new_page(viewport={"width": width, "height": 900}, ignore_https_errors=True)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            state = install_mock(page)
            page.goto(app_url(motion_fixture_url), wait_until="domcontentloaded")
            legacy = page.get_by_text("เปิดเครื่องมือเดิมและตัวอย่างสไตล์", exact=True)
            expect(legacy).to_be_visible()
            assert legacy.evaluate("element => element.closest('details').open") is False
            surface = create_silent(page)
            creation = next(body for _, path, body in state["writes"] if path == "/api/hyperframes/projects")
            assert creation["source_binding"] == {"type": "product_angle", "product_id": "product-real", "angle_id": "angle-real"}
            assert creation["inputs"]["audio_mode"] == "silent" and "voiceover_path" not in creation["inputs"]
            surface.get_by_role("button", name="เตรียมแพ็กเกจงาน AI", exact=True).click()
            surface.get_by_role("button", name="คัดลอกคำสั่งให้ AI", exact=True).click()
            expect(page.get_by_role("status").filter(has_text="คัดลอกคำสั่ง")).to_be_visible()
            assert "creative-fixture" in page.evaluate("window.__hfCopied")
            state["creative"].update(status="authoring", checkpoint={"next_action": "Finish scene two"})
            surface.get_by_role("button", name="ตรวจสถานะล่าสุด", exact=True).click()
            expect(surface.get_by_text("ทำต่อ: Finish scene two", exact=True)).to_be_visible()
            state["creative"].update(status="submitted", submitted_revision={"id": "revision-fixture", "files": [{"path": "index.html", "sha256": "snapshot-hash"}]})
            surface.get_by_role("button", name="ตรวจสถานะล่าสุด", exact=True).click()
            accept = surface.get_by_role("button", name="รับ revision นี้", exact=True)
            expect(accept).to_be_disabled()
            surface.get_by_role("checkbox", name="ตรวจ composition รุ่นนี้แล้ว", exact=False).check()
            accept.click()
            surface.get_by_role("button", name="เริ่มเรนเดอร์", exact=True).click()
            state["render"].update(status="qc_ready", phase="awaiting_final_review", artifact={"path": ".tmp/fixture/video.mp4", "sha256": "exact-artifact", "specs": {"width": 1080, "height": 1920}, "composition_revision": "revision-fixture"})
            surface.get_by_role("button", name="ตรวจสถานะล่าสุด", exact=True).click()
            expect(surface.locator("video")).to_be_visible()
            assert "/render-fixture/artifact/video?channel=main" in surface.locator("video").get_attribute("src")
            surface.get_by_label("Caption", exact=True).fill("Saved final caption")
            surface.get_by_label("Hashtags (คั่นด้วยช่องว่าง)", exact=True).fill("#fixture #verified")
            if os.environ.get("HF_WORKFLOW_REVIEW_DIR"):
                review_dir = Path(os.environ["HF_WORKFLOW_REVIEW_DIR"])
                review_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(review_dir / ("mobile.png" if width == 390 else "desktop.png")), full_page=True)
            finalize = surface.get_by_role("button", name="ส่งออกและลงทะเบียนใน Gallery", exact=True)
            expect(finalize).to_be_disabled()
            surface.get_by_role("checkbox", name="ดูคลิปจริงรุ่นนี้", exact=False).check()
            finalize.click()
            expect(surface.get_by_text("ลงทะเบียนผลงานแล้ว export-fixture", exact=True)).to_be_visible()
            final = next(body for _, path, body in state["writes"] if path.endswith("/finalize"))
            assert final["expected_revision"] == 4 and final["artifact_hash"] == "exact-artifact"
            assert final["publish_package"]["hashtags"] == ["#fixture", "#verified"]
            assert all(owner == "main" for owner, _, _ in state["writes"])
            assert not any("posting" in path or "tiktok-autopost" in path for _, path, _ in state["writes"])
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
            assert surface.evaluate("element => element.scrollWidth <= element.clientWidth + 1")
            page.screenshot(path=str(screenshot), full_page=False)
            from PIL import Image
            with Image.open(screenshot) as image:
                assert image.size == (width, 900)
                assert image.getbbox() is not None
            assert not errors
        finally:
            browser.close()
            screenshot.unlink(missing_ok=True)


def test_hf_dirty_scope_guard_and_late_old_channel_reply(motion_fixture_url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900}, ignore_https_errors=True)
            state = install_mock(page)
            page.goto(app_url(motion_fixture_url), wait_until="domcontentloaded")
            surface = workflow(page)
            surface.get_by_label("Brief ที่ต้องการให้ AI ทำ", exact=True).fill("Unsaved main brief")
            page.evaluate("window.dispatchEvent(new CustomEvent('omnicut:open-hyperframes', {detail:{channelId:'main',projectId:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}}))")
            expect(surface.get_by_text("บันทึกหรือทิ้งการแก้ไขก่อนเปิดงานจาก Activity Center", exact=True)).to_be_visible()
            selector = page.get_by_role("combobox", name="เลือกช่อง", exact=True)
            selector.select_option("second")
            dialog = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            expect(dialog).to_be_visible()
            dialog.get_by_role("button", name="อยู่ช่องเดิม", exact=True).click()
            expect(selector).to_have_value("main")
            surface.get_by_role("button", name="ยกเลิก brief ที่ยังไม่บันทึก", exact=True).click()
            create_silent(page)
            state["hold_project_read"] = True
            surface.get_by_role("button", name="ตรวจสถานะล่าสุด", exact=True).click()
            page.wait_for_timeout(150)
            assert state["delayed"]
            selector.select_option("second")
            expect(selector).to_have_value("second")
            state["hold_project_read"] = False
            route, owner = state["delayed"].pop()
            route.fulfill(status=200, headers={"X-OmniCut-Channel": owner}, content_type="application/json", body=json.dumps({"project": state["project"], "authoring_jobs": [], "render_jobs": []}))
            expect(surface.get_by_text("ช่อง second", exact=True)).to_be_visible()
            expect(surface.get_by_text("Fixture brief", exact=True)).to_have_count(0)
            expect(surface.get_by_label("Brief ที่ต้องการให้ AI ทำ", exact=True)).to_have_value("")
            page.evaluate("window.dispatchEvent(new CustomEvent('omnicut:open-hyperframes', {detail:{channelId:'main',projectId:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}}))")
            expect(surface.get_by_label("Brief ที่ต้องการให้ AI ทำ", exact=True)).to_have_value("")
            assert not any(owner == "second" for owner, _, _ in state["writes"])
        finally:
            browser.close()
