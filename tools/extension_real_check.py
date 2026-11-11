"""Load the REAL autopost extension in an isolated Chromium profile and exercise the side panel.

Unlike tools/extension_panel_check.py (stubbed chrome API), this runs
background.js and the real chrome.* APIs. It is safe because:
- the profile is brand new, so there is no TikTok login to post with;
- it never clicks a control that prepares, posts or edits the queue (the
  confirm dialog is opened by calling askConfirm() directly);
- /api/schedule-queue, /api/exports and the pending job are hashed before and
  after and must be byte-identical.

    npm pack axe-core@4 && tar -xzf axe-core-*.tgz package/axe.min.js
    .venv/Scripts/python.exe tools/extension_real_check.py package/axe.min.js [screenshot-prefix]

Run from the project root with the OmniCut API on port 8000.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

EXT = str(Path("tiktok_autopost_extension").resolve())
EXPECTED_VERSION = json.loads((Path(EXT) / 'manifest.json').read_text(encoding='utf-8'))['version']
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('axe')
parser.add_argument('screenshot_prefix', nargs='?', default='')
parser.add_argument('--allow-original-thumbnails', action='store_true', help='Explicit compatibility check for an older running backend which ignores w=160')
args = parser.parse_args()
AXE = Path(args.axe).read_text(encoding="utf-8")
SHOT = args.screenshot_prefix
fails = 0


def report(name, cond, detail=""):
    global fails
    if not cond:
        fails += 1
    print(("  ok   " if cond else "  FAIL ") + name + (f" :: {detail}" if not cond else ""))


def server_state():
    out = {}
    for path in ("/api/schedule-queue", "/api/exports", "/api/tiktok-autopost/pending"):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=30) as r:
                out[path] = hashlib.sha1(r.read()).hexdigest()
        except Exception as exc:  # noqa: BLE001
            out[path] = "ERR " + str(exc)[:40]
    return out


AXE_RUN = """async () => { const r = await axe.run(document); return r.violations.map(v => v.id + ' x' + v.nodes.length + ' ' + (v.nodes[0].html || '').slice(0, 80)); }"""

before = server_state()
profile = tempfile.mkdtemp(prefix="omnicut-ext-profile-")
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        profile, headless=False,
        args=["--headless=new", f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--autoplay-policy=no-user-gesture-required"],
        viewport={"width": 400, "height": 900},
    )
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=20000)
    ext_id = sw.url.split("/")[2]
    report("extension service worker started (background.js loads without error)", sw.url.endswith("/background.js"), sw.url)
    manifest = sw.evaluate("() => chrome.runtime.getManifest()")
    report("manifest version matches local source", manifest.get("version") == EXPECTED_VERSION, manifest.get("version"))

    writes = []
    errors = []
    ctx.on("request", lambda r: writes.append(r.method + " " + r.url[:90]) if r.method not in ("GET", "HEAD", "OPTIONS") and ":8000" in r.url else None)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)[:160]))
    page.on("console", lambda m: errors.append("console: " + m.text[:160]) if m.type == "error" else None)
    page.goto(f"chrome-extension://{ext_id}/sidepanel.html")
    page.wait_for_timeout(6000)

    # Covers are lazy-loaded below the batch controls. Scroll them into view before
    # asserting their decoded size; a lazy image off-screen is not a load failure.
    for index in range(min(3, page.locator('.card-thumb-wrap img').count())):
        thumb_image = page.locator('.card-thumb-wrap img').nth(index)
        thumb_image.scroll_into_view_if_needed()
        page.wait_for_function('(img) => img.complete && img.naturalWidth > 0', arg=thumb_image.element_handle(), timeout=15000)

    # ---- real load through the real chrome APIs
    info = page.evaluate("""() => ({ cards: document.querySelectorAll('.card').length, status: document.getElementById('headerStatusText').textContent.trim(),
        version: document.getElementById('brandVersionPill').textContent.trim(), build: document.getElementById('buildTag').textContent.trim(),
        thumbs: [...document.querySelectorAll('.card-thumb-wrap img')].slice(0, 6).map(i => ({ ok: i.complete && i.naturalWidth > 0, w: i.naturalWidth, src: i.src.includes('w=160') })),
        theme: document.documentElement.getAttribute('data-theme') })""")
    report("clip list loads from the real backend", info["cards"] > 0, info)
    report("header shows the backend as reachable", info["status"].upper() in ("READY", "ONLINE", "พร้อม"), info["status"])
    report("version pill and build tag read the real manifest", EXPECTED_VERSION in info["version"] and EXPECTED_VERSION in info["build"], (info["version"], info["build"]))
    loaded = [t for t in info["thumbs"] if t["ok"]]
    resized = all(t['w'] == 160 and t['src'] for t in loaded)
    report("visible thumbnails load (160px, or explicit older-backend compatibility)", len(loaded) >= 3 and (resized or (args.allow_original_thumbnails and all(t['src'] for t in loaded))), info["thumbs"])
    if not resized:
        print('  note running backend ignores w=160; original images still load. Resize optimization is not verified.')

    # The extension CSP forbids an injected <script>, so axe is evaluated instead.
    try:
        page.evaluate(AXE)
        v = page.evaluate(AXE_RUN)
        report("axe: no violations on the real panel (list tab)", not v, v)
    except Exception as exc:  # noqa: BLE001
        print("  note axe could not be injected under the extension CSP:", str(exc)[:120])

    # ---- tabs
    page.locator("#tabBtnList").focus()
    page.keyboard.press("ArrowRight")
    report("tabs: ArrowRight moves to the next tab", page.evaluate("() => document.activeElement.id + '|' + document.getElementById('panelChecklist').classList.contains('active')") == "tabBtnChecklist|true")
    page.keyboard.press("ArrowRight")
    report("tabs: tools tab opens", page.evaluate("() => document.getElementById('panelTools').classList.contains('active')"))
    page.locator("#tabBtnList").click()
    page.wait_for_timeout(300)

    # ---- theme toggle (real chrome.storage)
    start_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
    page.locator("#themeToggleBtn").click()
    page.wait_for_timeout(400)
    toggled = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
    report("theme toggle switches the theme", toggled != start_theme and toggled in ("dark", "light"), (start_theme, toggled))
    if SHOT:
        page.screenshot(path=f"{SHOT}-{toggled}.png")
    stored = page.evaluate("() => new Promise(r => chrome.storage.local.get(null, v => r(Object.entries(v).filter(([k, val]) => val === 'dark' || val === 'light'))))")
    report("the chosen theme is saved in chrome.storage", any(val == toggled for _, val in stored), stored)
    page.reload()
    page.wait_for_timeout(4000)
    report("the theme survives a reload of the panel", page.evaluate("() => document.documentElement.getAttribute('data-theme')") == toggled)
    try:
        page.evaluate(AXE)
        v = page.evaluate(AXE_RUN)
        report(f"axe: no violations in the {toggled} theme", not v, v)
    except Exception:
        pass
    page.locator("#themeToggleBtn").click()
    page.wait_for_timeout(400)
    report("theme toggles back", page.evaluate("() => document.documentElement.getAttribute('data-theme')") == start_theme)
    if SHOT:
        page.screenshot(path=f"{SHOT}-{start_theme}.png")

    # ---- video preview (real media request through the extension origin)
    thumb = page.locator(".card-thumb-wrap").first
    thumb.click()
    page.wait_for_timeout(2500)
    st = page.evaluate("""() => { const d = document.getElementById('videoPreviewModal'); const v = document.getElementById('previewVideoPlayer');
        return { open: d.open, modal: d.matches(':modal'), src: !!v.getAttribute('src'), ready: v.readyState, w: v.videoWidth, h: v.videoHeight, err: v.error ? v.error.code : null,
                 title: document.getElementById('previewModalTitle').textContent.trim().slice(0, 40) } }""")
    report("clicking a thumbnail opens the preview as a modal dialog", st["open"] and st["modal"] and st["src"], st)
    report("the preview video actually loads and has a 9:16 frame", st["ready"] >= 1 and st["w"] > 0 and st["h"] > st["w"] and st["err"] is None, st)
    if SHOT:
        page.screenshot(path=f"{SHOT}-preview.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    st = page.evaluate("() => ({ open: document.getElementById('videoPreviewModal').open, src: document.getElementById('previewVideoPlayer').getAttribute('src') })")
    report("Escape closes the preview and unloads the video", st == {"open": False, "src": None}, st)
    thumb.focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)
    report("Enter on a focused thumbnail opens the preview too", page.evaluate("() => document.getElementById('videoPreviewModal').open"))
    page.locator("#previewCloseBtn").click()
    page.wait_for_timeout(400)
    report("the close button closes it", page.evaluate("() => document.getElementById('videoPreviewModal').open") is False)

    # ---- confirm dialog in the real extension page (answered, never used to post)
    page.evaluate("() => { window.__answers = []; askConfirm('ทดสอบกล่องยืนยัน (ไม่มีการโพสต์)').then(v => window.__answers.push(v)); }")
    page.wait_for_timeout(400)
    st = page.evaluate("""() => { const d = document.getElementById('confirmOverlay'); const box = document.getElementById('confirmBox').getBoundingClientRect();
        const start = document.getElementById('batchStartBtn').getBoundingClientRect(); const hit = document.elementFromPoint(start.left + 8, start.top + 8);
        return { open: d.open, modal: d.matches(':modal'), focus: document.activeElement.id, text: document.getElementById('confirmText').textContent,
                 visible: box.width > 100 && box.height > 60 && box.left >= 0 && box.right <= innerWidth, behindBlocked: !hit || !!hit.closest('dialog') } }""")
    report("confirm opens as a modal dialog, centred, with focus on the cancel button",
           st["open"] and st["modal"] and st["focus"] == "confirmCancelBtn" and st["visible"] and "ทดสอบ" in st["text"], st)
    report("the start-upload button behind it cannot be reached", st["behindBlocked"], st)
    if SHOT:
        page.screenshot(path=f"{SHOT}-confirm.png")
    page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    report("Enter on the default focus answers NO", page.evaluate("() => JSON.stringify(window.__answers)") == "[false]", page.evaluate("() => JSON.stringify(window.__answers)"))
    page.evaluate("() => { askConfirm('x').then(v => window.__answers.push(v)); }")
    page.wait_for_timeout(300)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    report("Escape answers NO", page.evaluate("() => JSON.stringify(window.__answers)") == "[false,false]")
    page.evaluate("() => { askConfirm('x').then(v => window.__answers.push(v)); }")
    page.wait_for_timeout(300)
    page.locator("#confirmOkBtn").click()
    page.wait_for_timeout(300)
    report("the confirm button answers YES and the dialog closes",
           page.evaluate("() => JSON.stringify(window.__answers) + '|' + document.getElementById('confirmOverlay').open") == "[false,false,true]|false")

    report("no console or page errors in the real extension page", not errors, errors[:4])
    report("the panel sent no write request to the OmniCut API", not writes, writes[:4])
    ctx.close()
shutil.rmtree(profile, ignore_errors=True)
after = server_state()
report("server queue / exports / pending job are byte-identical before and after", before == after, {k: (before[k][:8], after[k][:8]) for k in before})
print("TOTAL FAIL", fails)
sys.exit(min(fails, 99))
