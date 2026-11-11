"""Browser check for the TikTok autopost extension's side panel.

The panel is served as plain files and `chrome.*` is replaced by an in-memory
stub, so background.js never runs: nothing here can post to TikTok. GET
requests to the OmniCut API are forwarded read-only (the real clip list is
used); every other method is swallowed and reported.

Checks: tab keyboard pattern, the video preview and confirm dialogs (modal,
focus, Escape, safe default answer), and axe-core with each dialog open.

    npm pack axe-core@4 && tar -xzf axe-core-*.tgz package/axe.min.js
    .venv/Scripts/python.exe tools/extension_panel_check.py package/axe.min.js

Run from the project root with the OmniCut API on port 8000. Exit code is the
number of failed checks.
"""
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

EXT = Path("tiktok_autopost_extension").resolve()
AXE = Path(sys.argv[1]).read_text(encoding="utf-8")
SHOT = sys.argv[2] if len(sys.argv) > 2 else ""
PORT = 5196

STUB = r"""
(() => {
  const mem = {};
  const calls = [];
  window.__chromeCalls = calls;
  const port = () => ({ onMessage: { addListener() {} }, onDisconnect: { addListener() {} }, postMessage() {}, disconnect() {} });
  window.chrome = {
    runtime: {
      lastError: null, id: 'stub',
      getManifest: () => ({ version: '0.0.0-audit', name: 'audit' }),
      sendMessage(msg, cb) { calls.push(msg && msg.type); const res = { ok: true, items: [], queue: [], channels: [], data: null };
        if (typeof cb === 'function') { setTimeout(() => cb(res), 0); return undefined; } return Promise.resolve(res); },
      connect: port,
      onMessage: { addListener() {}, removeListener() {} },
    },
    storage: {
      local: {
        get(keys, cb) { const out = {}; const list = typeof keys === 'string' ? [keys] : Array.isArray(keys) ? keys : keys ? Object.keys(keys) : Object.keys(mem);
          list.forEach((k) => { if (k in mem) out[k] = mem[k]; else if (keys && !Array.isArray(keys) && typeof keys === 'object') out[k] = keys[k]; });
          if (typeof cb === 'function') { setTimeout(() => cb(out), 0); return undefined; } return Promise.resolve(out); },
        set(obj, cb) { Object.assign(mem, obj); if (typeof cb === 'function') setTimeout(cb, 0); return Promise.resolve(); },
        remove(k, cb) { [].concat(k).forEach((x) => delete mem[x]); if (typeof cb === 'function') setTimeout(cb, 0); return Promise.resolve(); },
      },
      onChanged: { addListener() {} },
    },
    tabs: { query: (q, cb) => { if (typeof cb === 'function') { setTimeout(() => cb([]), 0); return undefined; } return Promise.resolve([]); }, update() {}, create() {} },
    windows: { update() {} },
    scripting: { executeScript: () => Promise.resolve([]) },
  };
})();
"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(EXT), **k)

    def log_message(self, *a):
        pass


socketserver.TCPServer.allow_reuse_address = True
server = socketserver.TCPServer(("127.0.0.1", PORT), Quiet)
threading.Thread(target=server.serve_forever, daemon=True).start()


AXE_COUNT = """async () => { const r = await axe.run(document); return r.violations.map(v => v.id + ' x' + v.nodes.length + ' ' + (v.nodes[0].html || '').slice(0, 90)); }"""
fails = 0


def report(name, cond, detail=""):
    global fails
    if not cond:
        fails += 1
    print(("  ok   " if cond else "  FAIL ") + name + (f" :: {detail}" if not cond else ""))


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 400, "height": 900})
    ctx.add_init_script(STUB)
    page = ctx.new_page()
    writes = []
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)[:160]))

    def api(route):
        req = route.request
        if req.method != "GET":
            writes.append(req.method + " " + req.url.split("8000")[-1][:60])
            route.fulfill(status=200, content_type="application/json", body="{}")
            return
        try:
            import urllib.request
            r0 = urllib.request.Request(req.url.replace("localhost", "127.0.0.1"),
                                        headers={k: v for k, v in req.headers.items() if k.lower() == "range"})
            with urllib.request.urlopen(r0, timeout=20) as r:
                route.fulfill(status=r.status, content_type=r.headers.get("Content-Type", "application/json"), body=r.read(),
                              headers={"Access-Control-Allow-Origin": "*"})
        except Exception:
            route.fulfill(status=200, content_type="application/json", body="{}", headers={"Access-Control-Allow-Origin": "*"})

    page.route("http://127.0.0.1:8000/**", api)
    page.route("http://localhost:8000/**", api)
    page.goto(f"http://127.0.0.1:{PORT}/sidepanel.html")
    page.wait_for_timeout(3500)
    page.add_script_tag(content=AXE)

    # ---- tabs
    page.locator("#tabBtnList").focus()
    page.keyboard.press("ArrowRight")
    st = page.evaluate("() => ({ active: document.activeElement.id, sel: document.getElementById('tabBtnChecklist').getAttribute('aria-selected'), list: document.getElementById('tabBtnList').getAttribute('aria-selected'), panel: document.getElementById('panelChecklist').classList.contains('active'), tabindex: [document.getElementById('tabBtnList').tabIndex, document.getElementById('tabBtnChecklist').tabIndex] })")
    report("ArrowRight selects the next tab and moves focus",
           st == {"active": "tabBtnChecklist", "sel": "true", "list": "false", "panel": True, "tabindex": [-1, 0]}, st)
    page.keyboard.press("End")
    report("End jumps to the last tab",
           page.evaluate("() => document.activeElement.id + '|' + document.getElementById('panelTools').classList.contains('active')") == "tabBtnTools|true")
    page.keyboard.press("ArrowRight")
    report("ArrowRight wraps to the first tab", page.evaluate("() => document.activeElement.id") == "tabBtnList")
    page.locator("#tabBtnChecklist").click()
    report("clicking a tab still works and updates aria-selected",
           page.evaluate("() => document.getElementById('tabBtnChecklist').getAttribute('aria-selected')") == "true")
    page.locator("#tabBtnList").click()
    page.wait_for_timeout(300)

    # ---- video preview dialog from the keyboard
    thumb = page.locator(".card-thumb-wrap").first
    label = thumb.get_attribute("aria-label") or ""
    report("clip thumbnail is a named keyboard control",
           thumb.get_attribute("role") == "button" and thumb.get_attribute("tabindex") == "0" and len(label) > 8, label)
    thumb.focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(600)
    st = page.evaluate("() => { const d = document.getElementById('videoPreviewModal'); const r = d.getBoundingClientRect(); return { open: d.open, modal: d.matches(':modal'), full: Math.abs(r.width - innerWidth) < 2 && Math.abs(r.height - innerHeight) < 2, src: !!document.getElementById('previewVideoPlayer').getAttribute('src'), inside: !!document.activeElement.closest('dialog') } }")
    report("Enter on the thumbnail opens the preview as a modal dialog",
           st["open"] and st["modal"] and st["full"] and st["src"] and st["inside"], st)
    v = page.evaluate(AXE_COUNT)
    report("no accessibility violations while the preview is open", not v, v)
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    st = page.evaluate("() => ({ open: document.getElementById('videoPreviewModal').open, src: document.getElementById('previewVideoPlayer').getAttribute('src'), back: document.activeElement.classList.contains('card-thumb-wrap') })")
    report("Escape closes the preview, stops the video, returns focus to the thumbnail",
           st == {"open": False, "src": None, "back": True}, st)
    thumb.click()
    page.wait_for_timeout(500)
    page.locator("#previewCloseBtn").click()
    page.wait_for_timeout(300)
    report("close button closes the preview", page.evaluate("() => document.getElementById('videoPreviewModal').open") is False)
    thumb.click()
    page.wait_for_timeout(500)
    page.mouse.click(5, 5)
    page.wait_for_timeout(300)
    report("clicking the backdrop closes the preview", page.evaluate("() => document.getElementById('videoPreviewModal').open") is False)

    # ---- confirm dialog (the gate in front of real posting)
    page.evaluate("() => { window.__answers = []; askConfirm('question 1').then(v => window.__answers.push(v)); }")
    page.wait_for_timeout(300)
    st = page.evaluate("() => { const d = document.getElementById('confirmOverlay'); return { open: d.open, modal: d.matches(':modal'), text: document.getElementById('confirmText').textContent, focus: document.activeElement.id, shown: getComputedStyle(d).display } }")
    report("confirm opens as a modal dialog with focus on the safe answer",
           st == {"open": True, "modal": True, "text": "question 1", "focus": "confirmCancelBtn", "shown": "flex"}, st)
    v = page.evaluate(AXE_COUNT)
    report("no accessibility violations while the confirm is open", not v, v)
    hit = page.evaluate("() => { const b = document.getElementById('batchStartBtn').getBoundingClientRect(); const e = document.elementFromPoint(b.left + 5, b.top + 5); return !!e && !!e.closest('dialog') }")
    report("the start-upload button behind the confirm cannot be clicked", hit)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    report("Escape answers no and closes",
           page.evaluate("() => JSON.stringify(window.__answers) + '|' + document.getElementById('confirmOverlay').open") == "[false]|false")
    page.evaluate("() => { askConfirm('question 2').then(v => window.__answers.push(v)); }")
    page.wait_for_timeout(300)
    page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    got = page.evaluate("() => JSON.stringify(window.__answers)")
    report("Enter on the default focus answers no (never confirms by accident)", got == "[false,false]", got)
    page.evaluate("() => { askConfirm('question 3').then(v => window.__answers.push(v)); }")
    page.wait_for_timeout(300)
    page.locator("#confirmOkBtn").click()
    page.wait_for_timeout(300)
    report("the confirm button answers yes and closes",
           page.evaluate("() => JSON.stringify(window.__answers) + '|' + document.getElementById('confirmOverlay').open") == "[false,false,true]|false")
    page.evaluate("() => { askConfirm('A').then(v => window.__answers.push('a:' + v)); askConfirm('B').then(v => window.__answers.push('b:' + v)); }")
    page.wait_for_timeout(300)
    st = page.evaluate("() => ({ a: window.__answers.slice(3), text: document.getElementById('confirmText').textContent, open: document.getElementById('confirmOverlay').open })")
    report("a second question answers the first no and stays open", st == {"a": ["a:false"], "text": "B", "open": True}, st)
    page.locator("#confirmCancelBtn").click()
    page.wait_for_timeout(300)
    report("cancel button answers no", page.evaluate("() => window.__answers.slice(4).join()") == "b:false")

    report("no write request was sent during the whole check", not writes, writes[:4])
    report("no page errors", not errors, errors[:3])
    b.close()
server.shutdown()
print("TOTAL FAIL", fails)
sys.exit(min(fails, 99))
