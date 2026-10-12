"""Real App HF7 controls with scoped offline HTTP fixtures and no production data."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.motion_capture.test_hyperframes_workflow_browser import CHANNELS, PRODUCT, app_url, workflow

PROJECT_ID = "b" * 32
GADGET_ID = "gadget-real-source"


def mock(page):
    state = {"project": None, "job": None, "writes": [], "counter": 0, "available": True, "delayed": []}
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
        data = request.post_data_json if request.post_data and request.method in {"POST", "PATCH"} else None
        if data is not None:
            state["writes"].append((owner, path, data))
        if path == "/api/channels":
            result = {"channels": CHANNELS, "revision": 1}
        elif path == "/api/products":
            result = {"products": [PRODUCT] if owner == "main" else []}
        elif path == "/api/gadget-media/projects":
            result = {"projects": [{"project_id": GADGET_ID, "product_identity": {"brand": "Exact", "model": "Gadget", "variant": "Source"}, "channel_id": "main"}] if owner == "main" else []}
        elif path == "/api/hyperframes/ai/capabilities":
            result = {"available": state["available"], "configured": state["available"], "status": "configured_unverified" if state["available"] else "missing_key", "default_model": "gemini-2.5-flash", "models": ["gemini-2.5-flash"]}
        elif path in {"/api/hyperframes/projects", "/api/hyperframes/overlay/projects"}:
            if request.method == "POST":
                state["project"] = {"project_id": PROJECT_ID, "project_name": "main/HF7_fixture", "channel_id": owner,
                    "revision": 1, "brief_revision": 1, "inputs": data["inputs"], "source_binding": data["source_binding"], "accepted_revision": None}
                if "overlay/projects" in path:
                    state["project"]["overlay_contract"] = {"master_sha256": "master-hash", "composition_sha256": "sealed-overlay"}
                    state["job"] = {"id": "creative-overlay", "status": "submitted", "generation": 1,
                        "project_id": PROJECT_ID, "base_revision": 1, "submitted_revision": {"id": "revision-overlay", "files": [{"path": "index.html", "sha256": "sealed-overlay"}]}}
                    result = {"project": state["project"], "job": state["job"]}
                else:
                    result = {"project": state["project"]}
            else:
                result = {"projects": [state["project"]] if state["project"] and owner == "main" else []}
        elif path == "/api/hyperframes/overlay/inspect":
            result = {"master": {"artifact_id": "approved-master-real", "master_digest": "explicit-master-digest",
                "specs": {"duration": 12, "width": 1080, "height": 1920, "fps": 30}}}
        elif path.endswith("/authoring-jobs") and request.method == "POST":
            state["counter"] += 1
            state["job"] = {"id": f'creative-hf7-{state["counter"]}', "status": "queued", "generation": 0,
                "project_id": PROJECT_ID, "base_revision": state["project"]["revision"], "created_at": 1000 + state["counter"]}
            result = {"job": state["job"]}
        elif path.endswith("/generate/cancel"):
            state["job"].update(status="interrupted", generation=state["job"]["generation"] + 1)
            result = {"job": state["job"]}
        elif path.endswith("/generate"):
            state["job"].update(status="authoring", generation=1, checkpoint={"provider": "gemini", "phase": "generating", "next_action": "Wait for the provider"})
            if state.get("hold_generate"):
                state["delayed"].append((route, owner, json.loads(json.dumps(state["job"]))))
                return
            result = {"job": state["job"]}
        elif path.endswith("/handoff"):
            result = {"handoff": {"work_id": state["job"]["id"], "channel_id": owner, "input_hash": "exact-input",
                "work_path": "03_Projects/_HyperFrames_Studio/work/" + state["job"]["id"], "next_action": "Claim and author locally"}}
        elif path.endswith("/accept-revision"):
            state["project"].update(accepted_revision=state["job"]["submitted_revision"], revision=2)
            result = {"project": state["project"]}
        elif path == f"/api/hyperframes/projects/{PROJECT_ID}":
            result = {"project": state["project"], "authoring_jobs": [state["job"]] if state["job"] else [], "render_jobs": []}
        elif path == "/api/hyperframes/status":
            result = {"ready": True, "installed": True, "cli_version": "offline-fixture"}
        else:
            result = {"products": [], "projects": [], "exports": [], "videos": [], "tasks": [], "queue": [], "catalog": {}, "items": [], "styles": [], "compositions": []}
        route.fulfill(status=200, headers=headers, content_type="application/json", body=json.dumps(result))
    page.route("**/api/**", api)
    return state


@pytest.fixture
def browser_context():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, ignore_https_errors=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        state = mock(page)
        try:
            yield page, state, errors
            assert not errors
        finally:
            browser.close()


def open_source(page, url, source="standalone"):
    page.goto(app_url(url), wait_until="domcontentloaded")
    surface = workflow(page)
    expect(surface).to_be_visible(timeout=15000)
    surface.get_by_label("ประเภทงาน", exact=True).select_option(source)
    if source == "standalone":
        surface.get_by_label("ชื่อคลิป", exact=True).fill("Standalone real title")
        surface.get_by_label("ข้อมูลประกอบคลิป", exact=True).fill("Saved standalone facts")
    else:
        surface.get_by_label("โปรเจกต์ Gadget", exact=True).select_option(GADGET_ID)
    surface.get_by_label("Brief ที่ต้องการให้ AI ทำ", exact=True).fill("HF7 fixture brief")
    surface.get_by_label("เสียง", exact=True).select_option("silent")
    return surface


def save(surface):
    surface.get_by_role("button", name="บันทึก brief และเจ้าของงาน", exact=True).click()
    expect(surface.get_by_role("button", name="เริ่มสร้างด้วย AI ในแอป", exact=True)).to_be_visible()


@pytest.mark.parametrize("width", [390, 1440])
def test_standalone_in_app_ai_cancel_and_manual_accept(motion_fixture_url, browser_context, tmp_path, width):
    page, state, errors = browser_context
    page.set_viewport_size({"width": width, "height": 1000})
    surface = open_source(page, motion_fixture_url)
    expect(surface.get_by_label("สินค้า", exact=True)).to_have_count(0)
    save(surface)
    creation = next(data for _, path, data in state["writes"] if path == "/api/hyperframes/projects")
    assert creation["source_binding"] == {"type": "standalone"}
    assert creation["inputs"]["title"] == "Standalone real title"
    assert "product_id" not in creation["source_binding"] and "angle_id" not in creation["source_binding"]
    generate = surface.get_by_role("button", name="เริ่มสร้างด้วย AI ในแอป", exact=True)
    generate.click()
    expect(surface.get_by_role("button", name="ยกเลิกการสร้างด้วย AI", exact=True)).to_be_visible()
    started = next(data for _, path, data in state["writes"] if path.endswith("/generate"))
    assert started == {"expected_generation": 0, "model": "gemini-2.5-flash", "timeout_seconds": 120, "max_output_tokens": 8192}
    surface.get_by_role("button", name="ยกเลิกการสร้างด้วย AI", exact=True).click()
    expect(generate).to_be_enabled()
    generate.click()
    expect(surface.get_by_role("button", name="ยกเลิกการสร้างด้วย AI", exact=True)).to_be_visible()
    state["job"].update(status="submitted", submitted_revision={"id": "revision-hf7", "files": [{"path": "index.html", "sha256": "sealed-hf7"}]})
    surface.get_by_role("button", name="ตรวจสถานะล่าสุด", exact=True).click()
    accept = surface.get_by_role("button", name="รับ revision นี้", exact=True)
    expect(accept).to_be_disabled()
    assert not any(path.endswith("/render-jobs") for _, path, _ in state["writes"])
    surface.get_by_role("checkbox", name="ตรวจ composition รุ่นนี้แล้ว", exact=False).check()
    accept.click()
    expect(surface.get_by_role("button", name="เริ่มเรนเดอร์", exact=True)).to_be_visible()
    assert not any(path.endswith("/render-jobs") for _, path, _ in state["writes"])
    assert all(owner == "main" for owner, _, _ in state["writes"])
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert surface.evaluate("element => element.scrollWidth <= element.clientWidth + 1")
    screenshot = tmp_path / f"hf7-{width}.png"
    try:
        page.screenshot(path=str(screenshot), full_page=True)
        from PIL import Image
        with Image.open(screenshot) as image:
            assert image.width == width and image.getbbox() is not None
        if os.environ.get("HF7_REVIEW_DIR"):
            review = Path(os.environ["HF7_REVIEW_DIR"])
            review.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(review / ("mobile.png" if width == 390 else "desktop.png")), full_page=True)
    finally:
        screenshot.unlink(missing_ok=True)


def test_gadget_selector_binds_actual_domain_project(motion_fixture_url, browser_context):
    page, state, errors = browser_context
    surface = open_source(page, motion_fixture_url, "gadget_project")
    save(surface)
    creation = next(data for _, path, data in state["writes"] if path == "/api/hyperframes/projects")
    assert creation["source_binding"] == {"type": "gadget_project", "project_id": GADGET_ID}
    assert "product_id" not in creation["source_binding"] and "angle_id" not in creation["source_binding"]


def test_missing_provider_key_keeps_external_handoff_available(motion_fixture_url, browser_context):
    page, state, errors = browser_context
    state["available"] = False
    surface = open_source(page, motion_fixture_url)
    save(surface)
    expect(surface.get_by_role("button", name="เริ่มสร้างด้วย AI ในแอป", exact=True)).to_be_disabled()
    expect(surface.get_by_text("ตั้งค่า Gemini API key ในการตั้งค่าเดิมก่อน หรือใช้ AI session ภายนอก", exact=True)).to_be_visible()
    surface.get_by_role("button", name="เตรียมแพ็กเกจงาน AI", exact=True).click()
    surface.get_by_role("button", name="คัดลอกคำสั่งให้ AI", exact=True).click()
    expect(page.get_by_role("status").filter(has_text="คัดลอกคำสั่ง")).to_be_visible()
    assert "creative-hf7-1" in page.evaluate("window.__hfCopied")
    assert not any(path.endswith("/generate") for _, path, _ in state["writes"])


@pytest.mark.parametrize("width", [390, 1440])
def test_overlay_inspection_digest_human_confirmation_and_locked_draft(motion_fixture_url, browser_context, width):
    page, state, errors = browser_context
    page.set_viewport_size({"width": width, "height": 1000})
    surface = open_source(page, motion_fixture_url, "gadget_project")
    surface.get_by_role("checkbox", name="เพิ่มกราฟิกบน approved master", exact=False).check()
    surface.get_by_label("ไฟล์ภาพ PNG/JPG/WebP", exact=True).fill("02_Assets/overlay.png")
    surface.get_by_role("button", name="ตรวจ approved master", exact=True).click()
    confirmation = surface.get_by_role("checkbox", name="ยืนยันใช้ master รุ่นนี้", exact=False)
    expect(confirmation).to_be_visible()
    surface.get_by_role("button", name="บันทึก brief และเจ้าของงาน", exact=True).click()
    expect(surface.get_by_text("ตรวจและยืนยัน approved master รุ่นนี้ก่อนสร้าง overlay", exact=True)).to_be_visible()
    assert not any(path.endswith("/overlay/projects") for _, path, _ in state["writes"])
    confirmation.check()
    save(surface)
    creation = next(data for _, path, data in state["writes"] if path.endswith("/overlay/projects"))
    assert creation["approval"] == {"approved": True, "master_digest": "explicit-master-digest"}
    assert creation["source_binding"] == {"type": "gadget_project", "project_id": GADGET_ID}
    assert creation["layers"][0]["path"] == "02_Assets/overlay.png"
    assert creation["inputs"]["duration_seconds"] == 12
    expect(surface.get_by_role("button", name="เริ่มสร้างด้วย AI ในแอป", exact=True)).to_be_disabled()
    expect(surface.get_by_role("button", name="รับ revision นี้", exact=True)).to_be_disabled()
    assert not any(path.endswith("/generate") or path.endswith("/render-jobs") for _, path, _ in state["writes"])


def test_late_ai_response_cannot_restore_old_channel_project(motion_fixture_url, browser_context):
    page, state, errors = browser_context
    surface = open_source(page, motion_fixture_url)
    save(surface)
    state["hold_generate"] = True
    surface.get_by_role("button", name="เริ่มสร้างด้วย AI ในแอป", exact=True).click()
    page.wait_for_timeout(150)
    assert state["delayed"]
    selector = page.get_by_role("combobox", name="เลือกช่อง", exact=True)
    selector.select_option("second")
    expect(selector).to_have_value("second")
    route, owner, old_job = state["delayed"].pop()
    route.fulfill(status=200, headers={"X-OmniCut-Channel": owner}, content_type="application/json", body=json.dumps({"job": old_job}))
    expect(surface.get_by_text("ช่อง second", exact=True)).to_be_visible()
    expect(surface.get_by_role("button", name="ยกเลิกการสร้างด้วย AI", exact=True)).to_have_count(0)
    expect(surface.get_by_label("Brief ที่ต้องการให้ AI ทำ", exact=True)).to_have_value("")
    assert not any(owner == "second" for owner, _, _ in state["writes"])
