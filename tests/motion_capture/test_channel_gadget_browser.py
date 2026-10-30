"""Production Gadget stages and Canvas identity, with offline scoped API rows."""
import json
import base64
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright
from tests.motion_capture.clip_pair import create_clip_source
from tests.motion_capture.overlay_pair import vite_fs_url


def _setup(page, owner, project, timeline=None, tab="gadget"):
    page.set_default_timeout(10000)
    writes = []
    state = {"fail_save": True}
    channels = [{"id": key, "display_name": key, "handle": "@" + key,
                 "status": "active", "watermark_text": "changed live " + key, "revision": 9}
                for key in ("main", "second")]
    page.add_init_script("""localStorage.setItem('capcut_active_tab','gadget');
      for (const id of ['main','second']) localStorage.setItem(`omnicut:channel:v1:${id}:capcut_active_tab`,
        JSON.stringify({schema_version:1,channel_id:id,data:'gadget'}));
      localStorage.setItem('omnicut.ui_mode','desktop');
      window.__drawn=[];
      for (const method of ['fillText','strokeText']) {
        const original=CanvasRenderingContext2D.prototype[method];
        CanvasRenderingContext2D.prototype[method]=function(text,...args) {
          if (!window.__drawn.some(row=>row.method===method&&row.text===String(text)))
            window.__drawn.push({method,text:String(text)});
          return original.call(this,text,...args);
        };
      }""".replace("'gadget'", json.dumps(tab)))
    page.route("**/fonts.googleapis.com/**", lambda route: route.abort())
    page.route("**/fonts.gstatic.com/**", lambda route: route.abort())

    def api(route):
        request = route.request
        path = urlsplit(request.url).path
        channel = request.headers.get("x-omnicut-channel", "main")
        status = 200
        if path == "/api/channels":
            result = {"channels": channels, "revision": 9}
        elif path == "/api/gadget-media/projects":
            if request.method == "POST":
                writes.append((channel, request.post_data_json))
                result = {**project, "product_identity": {"brand": request.post_data_json["brand"], "model": request.post_data_json["model"]}}
            else:
                result = {"projects": [project] if channel == owner else []}
        elif path == "/api/gadget-media/projects/gadget-owned":
            assert channel == owner
            if request.method == "PATCH":
                writes.append((channel, request.post_data_json))
                if state["fail_save"]:
                    status, result = 503, {"detail": "offline fixture save"}
                else:
                    project.update(request.post_data_json)
                    project["updated_at"] = "updated-server-ack"
                    result = project
            else:
                result = project
        elif path == "/api/gadget-media/projects/gadget-owned/timeline":
            if timeline is None:
                status, result = 404, {"detail": "No timeline"}
            else:
                result = timeline
        elif path.startswith("/api/media/02_Assets/Fonts/"):
            font = Path(__file__).resolve().parents[2] / path.removeprefix("/api/media/")
            route.fulfill(status=200, content_type="font/ttf", body=font.read_bytes())
            return
        elif path == "/api/assets/all":
            result = {key: [] for key in ("sfx", "music", "fonts", "stickers", "luts", "effects")}
        else:
            result = {"products": [], "videos": [], "tasks": [], "exports": [], "projects": [], "queue": [], "catalog": []}
        response_headers = {"X-OmniCut-Channel": channel} if request.headers.get("x-omnicut-channel") else {}
        route.fulfill(status=status, headers=response_headers,
                      content_type="application/json", body=json.dumps(result))
    page.route("**/api/**", api)
    return writes, state


def _project(owner, status="brief", snapshot=None):
    return {"project_id": "gadget-owned", "channel_id": owner, "updated_at": "initial", "status": status,
            "product_identity": {"brand": "Fixture", "model": "Exact", "category": "Gadget"},
            "audience": "Original audience", "editorial_promise": "Original promise",
            "presentation": {"mode": "product_only", "channel_identity_snapshot": snapshot},
            "facts": [], "source_assets": [], "story": {"blocks": []}, "edit": {"edl": {"shots": []}}, "artifacts": []}


def _manual_hub(page, tab, hf_state=None):
    writes, state = _setup(page, "main", _project("main"), tab=tab)
    note = {"id": "owned-note", "text": "Original note", "tag": "Hook", "images": []}

    def api(route):
        path = urlsplit(route.request.url).path
        channel = route.request.headers.get("x-omnicut-channel", "main")
        status = 200
        if path == "/api/products":
            angles = [{"id": "A1", "title": "Saved fixture angle"}] if hf_state is not None else []
            result = {"products": [{"id": "P1", "channel_id": "main", "product_code": "P1", "name": "Fixture product", "angles": angles}] if hf_state is None or channel == "main" else []}
        elif hf_state is not None and path == "/api/hyperframes/projects":
            if route.request.method == "POST":
                body = route.request.post_data_json
                writes.append((channel, body))
                if hf_state["fail_save"]:
                    status, result = 503, {"detail": "offline fixture save"}
                else:
                    hf_state["project"] = {"project_id": "a" * 32, "project_name": "main/HF_fixture", "channel_id": "main", "revision": 1,
                                            "brief_revision": 1, "accepted_revision": None, "source_binding": body["source_binding"], "inputs": body["inputs"]}
                    result = {"project": hf_state["project"]}
            else:
                result = {"projects": [hf_state["project"]] if hf_state["project"] and channel == "main" else []}
        elif hf_state is not None and path == "/api/hyperframes/projects/" + "a" * 32:
            assert channel == "main"
            result = {"project": hf_state["project"], "authoring_jobs": [], "render_jobs": []}
        elif path == "/api/hyperframes/status":
            result = {"ready": True, "hyperframes_version": "fixture"}
        elif path == "/api/hyperframes/styles":
            result = {"styles": []}
        elif path == "/api/hyperframes/compositions":
            result = {"compositions": []}
        elif path == "/api/hyperframes/create-clip" or path == "/api/producer/notes/add":
            writes.append((channel, route.request.post_data_json))
            status, result = 503, {"detail": "offline fixture save"}
        elif path == "/api/producer/notes/owned-note" and route.request.method == "PUT":
            writes.append((channel, route.request.post_data_json))
            if "isPinned" in route.request.post_data_json:
                note["isPinned"] = route.request.post_data_json["isPinned"]
                result = {"success": True, "notes": [note], "revision": "revision-main-2"}
            else:
                status, result = 409, {"detail": "fixture revision conflict"}
        elif path == "/api/producer/notes":
            result = {"success": True, "notes": [note] if channel == "main" else [], "revision": "revision-main-1"}
        elif path == "/api/producer/ai-idea-to-angle":
            result = {"success": True, "proposal": {"angle_name": "Fixture AI angle", "hook_title": "Fixture hook", "script_brief": "Fixture script"}}
        else:
            route.fallback()
            return
        headers = {"X-OmniCut-Channel": channel} if route.request.headers.get("x-omnicut-channel") else {}
        route.fulfill(status=status, headers=headers, content_type="application/json", body=json.dumps(result))
    page.route("**/api/**", api)
    return writes


@pytest.mark.parametrize("tab", ["producer"])
def test_manual_hub_failed_write_retains_draft_across_channel_switch(motion_fixture_url, tab):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900}, ignore_https_errors=True)
            hf_state = {"fail_save": True, "project": None} if tab == "creative" else None
            writes = _manual_hub(page, tab, hf_state)
            page.goto(f"{origin}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            if tab == "creative":
                surface = page.get_by_role("region", name="ผลิตคลิปด้วย AI และส่งออกเข้าคิวเดิม")
                surface.get_by_label("สินค้า", exact=True).select_option("P1")
                surface.get_by_label("Angle", exact=True).select_option("A1")
                surface.get_by_label("เสียง", exact=True).select_option("silent")
                field = surface.get_by_label("Brief ที่ต้องการให้ AI ทำ", exact=True)
                field.fill("Unsaved main draft")
                surface.get_by_role("button", name="บันทึก brief และเจ้าของงาน", exact=True).click()
                expect(surface.get_by_role("alert")).to_contain_text("offline fixture save")
                expect(field).to_have_value("Unsaved main draft")
                selector = page.get_by_role("combobox", name="เลือกช่อง")
                selector.select_option("second")
                dialog = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
                dialog.get_by_role("button", name="บันทึกและสลับ", exact=True).click()
                expect(dialog.get_by_role("alert")).to_contain_text("offline fixture save")
                expect(selector).to_have_value("main")
                expect(field).to_have_value("Unsaved main draft")
                hf_state["fail_save"] = False
                dialog.get_by_role("button", name="บันทึกและสลับ", exact=True).click()
                expect(selector).to_have_value("second")
                expect(field).to_have_value("")
                selector.select_option("main")
                expect(selector).to_have_value("main")
                expect(surface.get_by_text("Unsaved main draft", exact=True)).to_be_visible()
                surface.get_by_role("button", name="แก้ brief เพื่อสร้าง revision ใหม่", exact=True).click()
                expect(field).to_have_value("Unsaved main draft")
                field.fill("Discard this new edit")
                selector.select_option("second")
                page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง").get_by_role("button", name="ทิ้งการแก้ไขและสลับ").click()
                expect(selector).to_have_value("second")
                assert hf_state["project"]["inputs"]["brief"] == "Unsaved main draft"
                assert len(writes) == 3 and all(owner == "main" for owner, _ in writes)
                assert all(body["source_binding"] == {"type": "product_angle", "product_id": "P1", "angle_id": "A1"} for _, body in writes)
                assert all(body["inputs"]["audio_mode"] == "silent" and "voiceover_path" not in body["inputs"] for _, body in writes)
                return
            else:
                field = page.get_by_placeholder("เช่น เปิดด้วยภาพแช่แข็งมือถือ", exact=False)
                button = page.get_by_role("button", name="บันทึกไอเดีย", exact=True)
            field.fill("Unsaved main draft")
            button.click()
            expect(page.get_by_text("สร้างคลิปไม่สำเร็จ:" if tab == "creative" else "บันทึกไม่สำเร็จ ข้อมูลที่พิมพ์ยังอยู่", exact=False)).to_be_visible()
            expect(field).to_have_value("Unsaved main draft")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            page.evaluate("""() => {
              window.__storageSet = Storage.prototype.setItem;
              Storage.prototype.setItem = function(key, value) {
                if (key.includes('hyperframes_create_draft') || key.includes('producer_manual_draft'))
                  throw new Error('fixture draft storage unavailable');
                return window.__storageSet.call(this, key, value);
              };
            }""")
            selector.select_option("second")
            dialog = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            dialog.get_by_role("button", name="บันทึกและสลับ", exact=True).click()
            expect(dialog.get_by_role("alert")).to_contain_text("fixture draft storage unavailable")
            expect(selector).to_have_value("main")
            expect(field).to_have_value("Unsaved main draft")
            page.evaluate("() => { Storage.prototype.setItem = window.__storageSet; }")
            dialog.get_by_role("button", name="บันทึกและสลับ", exact=True).click()
            expect(selector).to_have_value("second")
            if tab == "creative":
                page.get_by_role("button", name="เริ่มคลิปดราฟต์ใหม่", exact=True).click()
            expect(field).to_have_value("")
            selector.select_option("main")
            expect(selector).to_have_value("main")
            if tab == "creative":
                page.get_by_role("button", name="เริ่มคลิปดราฟต์ใหม่", exact=True).click()
            expect(field).to_have_value("Unsaved main draft")
            assert len(writes) == 1 and writes[0][0] == "main"
            field.fill("Discard this new edit")
            selector.select_option("second")
            page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง").get_by_role("button", name="ทิ้งการแก้ไขและสลับ").click()
            expect(selector).to_have_value("second")
            assert len(writes) == 1
        finally:
            browser.close()


@pytest.mark.parametrize("form", ["note", "proposal"])
def test_producer_modal_drafts_retain_owner_and_edit_revision(motion_fixture_url, form):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, ignore_https_errors=True)
            writes = _manual_hub(page, "producer")
            page.goto(f"{origin}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            if form == "note":
                page.get_by_role("button", name="ปักหมุดให้อยู่บนสุด", exact=True).click()
                expect(page.get_by_role("button", name="ยกเลิกการปักหมุด", exact=True)).to_be_visible()
                page.get_by_role("button", name="แก้ไขข้อความโน้ต", exact=True).click()
                field = page.get_by_placeholder("พิมพ์ข้อความไอเดียหรือสรุปประเด็น...", exact=True)
                field.fill("Retained note edit")
                page.get_by_role("button", name="บันทึกการแก้ไข", exact=True).click()
                expect(page.get_by_text("ไม่สามารถบันทึกการแก้ไขได้ กรุณาลองใหม่", exact=True)).to_be_visible()
                expect(field).to_have_value("Retained note edit")
                assert writes == [("main", {"isPinned": True, "base_revision": "revision-main-1"}),
                                  ("main", {"text": "Retained note edit", "tag": "Hook", "base_revision": "revision-main-2"})]
            elif form == "proposal":
                page.get_by_role("button", name="คิดสคริปต์จากเรฟ", exact=True).click()
                field = page.get_by_role("dialog", name="AI สังเคราะห์สคริปต์จากเรฟ").locator('input[type="text"]').first
                field.fill("Retained AI proposal")
            else:
                page.get_by_role("button", name="ตั้งค่าเป้าหมายการผลิต (Quota)").click()
                field = page.get_by_role("dialog").locator('input[type="number"]').first
                field.fill("41")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            selector.select_option("second")
            page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง").get_by_role("button", name="บันทึกและสลับ", exact=True).click()
            expect(selector).to_have_value("second")
            expect(field).to_have_count(0)
            selector.select_option("main")
            expect(selector).to_have_value("main")
            expect(field).to_have_value({"note": "Retained note edit", "targets": "41", "proposal": "Retained AI proposal"}[form])
            assert len(writes) == (2 if form == "note" else 0)
        finally:
            browser.close()


@pytest.mark.parametrize("action", ["note", "upload"])
def test_producer_pending_save_fences_switch_and_retains_newer_edit(motion_fixture_url, action):
    parsed = urlsplit(motion_fixture_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, ignore_https_errors=True)
            _manual_hub(page, "producer")
            pending, writes = [], []

            def hold(route):
                writes.append((route.request.headers.get("x-omnicut-channel"), route.request.post_data_json if action == "note" else {"upload": True}))
                pending.append(route)

            page.route("**/api/producer/notes/add" if action == "note" else "**/api/producer/upload-ref-media", hold)
            page.goto(f"{origin}/?channel=main&mode=desktop", wait_until="domcontentloaded")
            field = page.get_by_placeholder("เช่น เปิดด้วยภาพแช่แข็งมือถือ", exact=False)
            field.fill("Saved original idea")
            if action == "note":
                page.get_by_role("button", name="บันทึกไอเดีย", exact=True).click()
            else:
                page.locator('input[type="file"]').set_input_files({"name": "reference.png", "mimeType": "image/png", "buffer": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=")})
            field.fill("Newer idea during save")
            selector = page.get_by_role("combobox", name="เลือกช่อง")
            selector.select_option("second")
            dialog = page.get_by_role("dialog", name="บันทึกก่อนสลับช่อง")
            dialog.get_by_role("button", name="บันทึกและสลับ", exact=True).click()
            expect(dialog).to_have_attribute("aria-busy", "true")
            expect(selector).to_have_value("main")
            assert len(pending) == len(writes) == 1 and writes[0][0] == "main"
            if action == "note":
                note = writes[0][1]["note"]
                assert note["text"] == "Saved original idea"
                response = {"success": True, "notes": [note], "revision": "revision-main-2"}
            else:
                response = {"url": "/api/media/03_Projects/reference.png"}
            pending[0].fulfill(status=200, headers={"X-OmniCut-Channel": "main"}, content_type="application/json",
                               body=json.dumps(response))
            if action == "upload":
                expect(dialog.get_by_role("alert")).to_contain_text("บันทึกการแก้ไขยังไม่เสร็จ")
                expect(selector).to_have_value("main")
                expect(field).to_have_value("Newer idea during save")
                dialog.get_by_role("button", name="บันทึกและสลับ", exact=True).click()
            expect(selector).to_have_value("second")
            selector.select_option("main")
            expect(field).to_have_value("Newer idea during save")
            if action == "upload":
                expect(page.get_by_role("img", name="Preview 1", exact=True)).to_have_attribute("src", "/api/media/03_Projects/reference.png?channel=main")
            assert len(writes) == 1
        finally:
            browser.close()


def _open(page, origin, owner):
    page.goto(f"{origin}/?channel={owner}&mode=desktop", wait_until="domcontentloaded")
    try:
        page.get_by_role("button", name="Fixture Exact").click()
    except Exception as exc:
        raise AssertionError(page.locator("body").inner_text()[:2000]) from exc








def _campaign_api(page, *, empty=False, hold_create=False):
    slot = {"slot_id": "slot1", "hook": "Original campaign hook", "script": "Official campaign script",
            "series": "watch_before_buy", "status": "planned", "source_refs": [], "metrics": {}}
    campaign = {"campaign_id": "campaign1", "name": "Offline campaign", "slots": [slot]}
    state = {"fail": True, "writes": [], "pending": []}
    def route_api(route):
        request = route.request
        path = urlsplit(request.url).path
        owner = request.headers.get("x-omnicut-channel", "main")
        headers = {"X-OmniCut-Channel": owner} if request.headers.get("x-omnicut-channel") else {}
        status = 200
        if request.method == "PATCH":
            state["writes"].append((owner, request.post_data_json))
            if state["fail"]:
                status, result = 503, {"detail": "campaign fixture offline"}
            else:
                slot.update(request.post_data_json)
                result = slot
        elif request.method == "POST":
            state["writes"].append((owner, request.post_data_json))
            if hold_create:
                state["pending"].append(route)
                return
            result = campaign
        elif path.endswith("/readiness"):
            result = {"blockers": {}, "slots": []}
        else:
            result = {"campaigns": [] if empty or owner != "main" else [campaign]}
        route.fulfill(status=status, headers=headers, content_type="application/json", body=json.dumps(result))
    page.route("**/api/gadget-media/campaigns**", route_api)
    return state, campaign
