"""Browser check for the shared overlay primitives (ui/ModalLayer, ui/Modal,
ui/dialogService, ui/Toast, ui/PopoverPanel).

Drives frontend/overlay_primitives.html in Chromium, Firefox and WebKit (the
Safari engine), on desktop and on emulated iPhone 15 / Pixel 7, and prints
pass/fail per engine. The fixture talks to no API and stores nothing.

    cd frontend && npx vite --port 5199 --strictPort      # dev server (https)
    .venv/Scripts/python.exe tools/overlay_browser_check.py [url] [label-filter]

Needs the Playwright browsers once: python -m playwright install chromium firefox webkit
Exit code is the number of failed checks.
"""
import json
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://localhost:5199/overlay_primitives.html"
ONLY = sys.argv[2] if len(sys.argv) > 2 else ""


def run(page, touch, results, mobile):
    def ok(name, cond, detail=""):
        results.append((name, bool(cond), str(detail)[:160]))

    def act(testid):
        loc = page.get_by_test_id(testid)
        loc.tap() if touch else loc.click()

    js = page.evaluate
    tid = lambda t: f'[data-testid="{t}"]'
    page.goto(URL)
    page.wait_for_selector(tid("open-modal"))

    # ---- Modal (focus the trigger first: Safari does not focus buttons on click)
    page.get_by_test_id("open-modal").focus()
    act("open-modal")
    page.wait_for_selector("dialog[open]")
    ok("modal is :modal and fills viewport", js("""() => { const d=document.querySelector('dialog'); const r=d.getBoundingClientRect();
        return d.matches(':modal') && Math.abs(r.width-innerWidth)<2 && Math.abs(r.height-innerHeight)<2 && r.top===0 }"""))
    ok("autoFocus lands on first field", js("() => document.activeElement?.dataset.testid") == "modal-input",
       js("() => document.activeElement?.tagName + ':' + (document.activeElement?.dataset.testid||'')"))
    ok("no body scroll lock style", js("() => document.body.style.overflow + '|' + document.documentElement.style.overflow") == "|")
    if not touch:
        escaped = False
        for _ in range(14):
            page.keyboard.press("Tab")
            inside = js("() => { const a=document.activeElement; return a===document.body || !!a.closest('dialog') }")
            if not inside:
                escaped = True
        ok("Tab never leaves the dialog", not escaped)
        ok("page behind is inert (not hit-testable)", js(f"""() => {{ const r=document.querySelector('{tid("page-counter")}').getBoundingClientRect();
            const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); return !!hit && !!hit.closest('dialog') }}"""))
        page.get_by_test_id("modal-last").hover()
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(250)
        ok("wheel in dialog does not scroll the page", js("() => scrollY") == 0, js("() => scrollY"))
    if mobile:
        ok("bottom sheet sits on the bottom edge", js("""() => { const p=document.querySelector('dialog .glass-panel').getBoundingClientRect();
            return Math.abs(p.bottom-innerHeight)<2 && p.left===0 }"""))

    # ---- nested confirm
    act("modal-confirm")
    page.wait_for_function("() => document.querySelectorAll('dialog[open]').length === 2")
    ok("confirm stacks above the modal", True)
    ok("initial focus is the safe action", js("() => document.activeElement.textContent.trim()") == "ยกเลิก",
       js("() => document.activeElement.textContent.trim()"))
    ok("confirm text keeps line break", js("() => getComputedStyle([...document.querySelectorAll('dialog p')].find(p=>p.textContent.includes('บรรทัดที่สอง'))).whiteSpace") == "pre-line")
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelectorAll('dialog[open]').length === 1")
    ok("Escape answers no and keeps the modal", js(f"() => document.querySelector('{tid('confirm-result')}').textContent") == "no")
    act("modal-confirm")
    page.wait_for_function("() => document.querySelectorAll('dialog[open]').length === 2")
    btn = page.locator("dialog button", has_text="ลบ").last
    btn.tap() if touch else btn.click()
    page.wait_for_function("() => document.querySelectorAll('dialog[open]').length === 1")
    ok("confirm button answers yes", js(f"() => document.querySelector('{tid('confirm-result')}').textContent") == "yes")

    # ---- toast above modal
    act("modal-toast")
    page.wait_for_selector(".toast-layer")
    ok("toast is on top of the open dialog", js("""() => { const t=document.querySelector('.toast-layer'); const r=t.firstElementChild.getBoundingClientRect();
        const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); return !!hit && t.contains(hit) }"""),
       js("() => { const t=document.querySelector('.toast-layer'); return (t.matches(':popover-open')?'popover':'no-popover') }"))
    close = page.locator(".toast-layer button")
    close.tap() if touch else close.click()
    page.wait_for_timeout(200)
    ok("toast close button works while the modal is open", js("() => !document.querySelector('.toast-layer')"))
    act("modal-toast")
    page.wait_for_selector(".toast-layer")
    ok("toast has no UA popover chrome", js("""() => { const c=getComputedStyle(document.querySelector('.toast-layer'));
        return c.borderTopWidth==='0px' && (c.backgroundColor==='rgba(0, 0, 0, 0)' || c.backgroundColor==='transparent') }"""))

    # ---- close + focus return
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelectorAll('dialog[open]').length === 0")
    ok("Escape closes the modal", True)
    page.wait_for_timeout(200)
    ok("focus returns to the invoker", js("() => document.activeElement?.dataset.testid") == "open-modal",
       js("() => document.activeElement?.tagName + ':' + (document.activeElement?.dataset.testid||'')"))

    # ---- locked layer
    act("open-locked")
    page.wait_for_selector("dialog[open]")
    for _ in range(3):
        page.keyboard.press("Escape")
        page.wait_for_timeout(120)
    ok("layer without onClose survives Escape x3", js("() => document.querySelectorAll('dialog[open]').length") == 1)
    act("locked-close")
    page.wait_for_function("() => document.querySelectorAll('dialog').length === 0")

    # ---- guarded layer (owner refuses to close)
    act("open-guarded")
    page.wait_for_selector("dialog[open]")
    for _ in range(3):
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
    ok("guarded layer stays open and is still modal", js("() => { const d=document.querySelector('dialog'); return !!d && d.open && d.matches(':modal') }"))
    ok("owner was asked each time", int(js(f"() => document.querySelector('{tid('guard-hits')}').textContent")) >= 3,
       js(f"() => document.querySelector('{tid('guard-hits')}').textContent"))
    act("guarded-close")
    page.wait_for_function("() => document.querySelectorAll('dialog').length === 0")

    # ---- page-level confirm
    act("page-confirm")
    page.wait_for_selector("dialog[open]")
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelectorAll('dialog[open]').length === 0")
    ok("page-level confirm resolves", js(f"() => document.querySelector('{tid('confirm-result')}').textContent") == "no")

    # ---- dropdowns
    for name, align in (("dd-end", "end"), ("dd-start", "start")):
        act(f"{name}-trigger")
        page.wait_for_selector(tid(f"{name}-panel"))
        geo = js(f"""() => {{ const p=document.querySelector('{tid(name + "-panel")}').getBoundingClientRect();
            const a=document.querySelector('{tid(name + "-trigger")}').getBoundingClientRect();
            return {{pl:p.left,pr:p.right,pt:p.top,pb:p.bottom,al:a.left,ar:a.right,ab:a.bottom,vw:innerWidth,vh:innerHeight}} }}""")
        below = abs(geo["pt"] - (geo["ab"] + 6)) < 3
        inside = geo["pl"] >= 0 and geo["pr"] <= geo["vw"] + 0.5
        want = geo["ar"] - (geo["pr"] - geo["pl"]) if align == "end" else geo["al"]
        want = max(8, min(want, geo["vw"] - (geo["pr"] - geo["pl"]) - 8))
        ok(f"{name}: panel under trigger, aligned, in viewport", below and inside and abs(geo["pl"] - want) < 3, json.dumps(geo))
        act(f"{name}-trigger")
        page.wait_for_timeout(250)
        ok(f"{name}: pressing the trigger again closes (no reopen)", js(f"() => !document.querySelector('{tid(name + '-panel')}')"))
        act(f"{name}-trigger")
        page.wait_for_selector(tid(f"{name}-panel"))
        if touch:
            page.touchscreen.tap(20, page.viewport_size["height"] - 200)
        else:
            page.mouse.click(20, page.viewport_size["height"] - 200)
        page.wait_for_timeout(250)
        ok(f"{name}: outside press closes", js(f"() => !document.querySelector('{tid(name + '-panel')}')"))
        act(f"{name}-trigger")
        page.wait_for_selector(tid(f"{name}-panel"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        ok(f"{name}: Escape closes and refocuses trigger",
           js(f"() => !document.querySelector('{tid(name + '-panel')}') && document.activeElement?.dataset.testid === '{name}-trigger'"),
           js("() => document.activeElement?.dataset.testid || document.activeElement?.tagName"))
        act(f"{name}-trigger")
        page.wait_for_selector(tid(f"{name}-panel"))
        act(f"{name}-item-สอง")
        page.wait_for_timeout(200)
        ok(f"{name}: picking an item closes and applies",
           js(f"() => !document.querySelector('{tid(name + '-panel')}') && document.querySelector('{tid(name + '-trigger')}').textContent.includes('สอง')"))

    act("dd-bottom-trigger")
    page.wait_for_selector(tid("dd-bottom-panel"))
    ok("dd-bottom: flips above when no room below", js(f"""() => {{ const p=document.querySelector('{tid("dd-bottom-panel")}').getBoundingClientRect();
        const a=document.querySelector('{tid("dd-bottom-trigger")}').getBoundingClientRect(); return p.bottom <= a.top && p.top >= 0 }}"""))
    page.keyboard.press("Escape")

    # ---- focus ring
    if not touch:
        page.get_by_test_id("page-counter").focus()
        page.keyboard.press("Tab")
        ok("outline-none control still shows a focus ring", js("""() => { const a=document.activeElement; const c=getComputedStyle(a);
            return a.dataset.testid==='bare-outline' && c.outlineStyle!=='none' && parseFloat(c.outlineWidth)>=2 }"""),
           js("() => { const c=getComputedStyle(document.activeElement); return document.activeElement.dataset.testid+' '+c.outlineStyle+' '+c.outlineWidth }"))


def run_reduced(page, results):
    page.goto(URL)
    page.get_by_test_id("open-modal").click()
    page.wait_for_selector("dialog[open]")
    name = page.evaluate("() => getComputedStyle(document.querySelector('dialog')).animationName")
    results.append(("reduced motion: entrance animation off", name == "none", name))
    dur = page.evaluate("""() => { const e=document.createElement('div'); e.className='animate-spin'; document.body.append(e);
        const d=getComputedStyle(e).animationDuration; e.remove(); return d }""")
    results.append(("reduced motion: spinner keeps turning, slower", dur == "2.4s", dur))
    tr = page.evaluate("""() => { const e=document.createElement('button'); e.className='transition-colors'; document.body.append(e);
        const d=getComputedStyle(e).transitionDuration; e.remove(); return d }""")
    results.append(("reduced motion: colour transitions kept", tr not in ("0s", "1e-05s", "0.00001s"), tr))


MATRIX = [
    ("chromium desktop", "chromium", dict(viewport={"width": 1280, "height": 800}), False),
    ("firefox desktop", "firefox", dict(viewport={"width": 1280, "height": 800}), False),
    ("webkit desktop (Safari engine)", "webkit", dict(viewport={"width": 1280, "height": 800}), False),
    ("webkit iPhone 15", "webkit", "iPhone 15", True),
    ("webkit iPhone 15 landscape", "webkit", "iPhone 15 landscape", True),
    ("chromium Pixel 7", "chromium", "Pixel 7", True),
]

with sync_playwright() as p:
    total_fail = 0
    for label, engine, cfg, touch in MATRIX:
        if ONLY and ONLY not in label:
            continue
        browser = getattr(p, engine).launch()
        opts = dict(p.devices[cfg]) if isinstance(cfg, str) else dict(cfg)
        ctx = browser.new_context(ignore_https_errors=True, **opts)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.on("console", lambda m: errors.append(m.text[:200]) if m.type == "error" else None)
        results = []
        mobile = bool(page.viewport_size and page.viewport_size["width"] < 640)
        try:
            run(page, touch, results, mobile)
        except Exception as exc:  # noqa: BLE001
            results.append(("RUN ABORTED", False, repr(exc)[:300]))
        fails = [r for r in results if not r[1]]
        total_fail += len(fails)
        print(f"== {label}: {len(results) - len(fails)}/{len(results)} pass, console errors: {len(errors)}")
        for name, _, detail in fails:
            print(f"   FAIL {name} :: {detail}")
        for e in errors[:3]:
            print(f"   console: {e}")
        ctx.close()
        if engine in ("chromium", "webkit") and not touch and not ONLY:
            ctx = browser.new_context(ignore_https_errors=True, reduced_motion="reduce", viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            results = []
            run_reduced(page, results)
            fails = [r for r in results if not r[1]]
            total_fail += len(fails)
            print(f"== {label} reduced-motion: {len(results) - len(fails)}/{len(results)} pass")
            for name, _, detail in fails:
                print(f"   FAIL {name} :: {detail}")
            ctx.close()
        browser.close()
    print("TOTAL FAIL", total_fail)
    sys.exit(min(total_fail, 99))
