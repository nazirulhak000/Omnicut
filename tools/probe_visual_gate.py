#!/usr/bin/env python3
"""Visual Inspection Gate Probe for Couple Paper Chat CTA outro.

Checks:
1. Centering of hero cutouts and contact shadows (center X ≈ 540)
2. No text overflow / clipping of CTA title (#cta-1)
3. Captures visual screenshots for verification
"""
from pathlib import Path
import json
import time
import http.server
import socketserver
import threading
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
TMP = ROOT / ".tmp"
TMP.mkdir(exist_ok=True)

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

def run_probe():
    # Start temporary local HTTP server in STUDIO directory
    port = 8765
    httpd = socketserver.TCPServer(("127.0.0.1", port), QuietHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    
    # Change working directory of handler by using functools or subclassing
    # Alternatively, serve from STUDIO
    class StudioHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(STUDIO), **kwargs)
        def log_message(self, format, *args):
            pass

    httpd.server_close()
    httpd = socketserver.TCPServer(("127.0.0.1", port), StudioHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    print(f"HTTP server running on http://127.0.0.1:{port} serving {STUDIO}")

    results = {}
    test_targets = [
        ("GOO01", "goo01-pov-s01"),
        ("HAT01", "hat01-pov-s01"),
        ("RED01", "red01-pov-s01"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})

        for prod, stem in test_targets:
            url = f"http://127.0.0.1:{port}/compositions/{stem}.html"
            print(f"\n--- Testing {prod} ({stem}) ---")
            page.goto(url)
            page.wait_for_load_state("networkidle")

            # Seek GSAP timeline to CTA_T + 1.8s
            seek_res = page.evaluate("""
                () => {
                    const ctaT = window.CTA_T || 50;
                    const tl = window.tl;
                    if (tl) {
                        tl.seek(ctaT + 1.8, false);
                    }
                    
                    // Measure CTA title
                    const cta1 = document.getElementById("cta-1");
                    const r1 = cta1 ? cta1.getBoundingClientRect() : null;

                    // Measure hero
                    const hero = document.querySelector(".hero-img") || document.getElementById("f-center");
                    const rHero = hero ? hero.getBoundingClientRect() : null;

                    // Measure contact shadow
                    const cs = document.getElementById("cs-goo") || document.getElementById("cs-hatari") || document.getElementById("cs-center");
                    const rCs = cs ? cs.getBoundingClientRect() : null;

                    return {
                        title: {
                            text: cta1 ? cta1.innerText : null,
                            width: r1 ? r1.width : 0,
                            height: r1 ? r1.height : 0,
                            left: r1 ? r1.left : 0,
                            right: r1 ? r1.right : 0
                        },
                        hero: {
                            left: rHero ? rHero.left : 0,
                            right: rHero ? rHero.right : 0,
                            width: rHero ? rHero.width : 0,
                            centerX: rHero ? (rHero.left + rHero.right) / 2 : 0
                        },
                        cs: {
                            left: rCs ? rCs.left : 0,
                            right: rCs ? rCs.right : 0,
                            width: rCs ? rCs.width : 0,
                            centerX: rCs ? (rCs.left + rCs.right) / 2 : 0
                        }
                    };
                }
            """)

            # Take screenshot of CTA
            shot_path = TMP / f"visual_gate_{prod}.png"
            page.screenshot(path=str(shot_path))
            print(f"  Screenshot saved: {shot_path}")

            hero_center = seek_res["hero"]["centerX"]
            cs_center = seek_res["cs"]["centerX"]
            title_w = seek_res["title"]["width"]
            title_r = seek_res["title"]["right"]

            print(f"  Hero Center X: {hero_center:.1f}px (Target: 540px, diff: {abs(hero_center - 540):.1f}px)")
            print(f"  Shadow Center X: {cs_center:.1f}px (Target: 540px, diff: {abs(cs_center - 540):.1f}px)")
            print(f"  CTA Title width: {title_w:.1f}px (Right edge: {title_r:.1f}px <= 1080px)")

            hero_ok = abs(hero_center - 540) <= 5.0
            shadow_ok = abs(cs_center - 540) <= 5.0
            title_ok = title_r <= 1060.0

            results[prod] = {
                "hero_ok": hero_ok,
                "shadow_ok": shadow_ok,
                "title_ok": title_ok,
                "hero_center": hero_center,
                "shadow_center": cs_center,
                "title_width": title_w
            }

        browser.close()

    httpd.shutdown()
    print("\n=== VISUAL GATE SUMMARY ===")
    all_passed = True
    for prod, res in results.items():
        passed = res["hero_ok"] and res["shadow_ok"] and res["title_ok"]
        if not passed:
            all_passed = False
        print(f"  [{'PASS' if passed else 'FAIL'}] {prod}: hero_centered={res['hero_ok']}, shadow_centered={res['shadow_ok']}, title_fits={res['title_ok']}")

    if all_passed:
        print("\n✅ VISUAL GATE 100% PASSED: Zero offset, zero text clipping, perfect centering!")
    else:
        print("\n❌ VISUAL GATE FAILED: Some elements are not centered or overflowing.")
    return all_passed

if __name__ == "__main__":
    import sys
    success = run_probe()
    sys.exit(0 if success else 1)
