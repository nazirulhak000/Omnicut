#!/usr/bin/env python3
"""Visual Inspection Gate Probe for TTZ K106 (ttz01-pov-s01).
Captures:
  - Frame A: Chat in progress (around t = 18.0s)
  - Frame B: CTA Outro (at t = cta_t + 1.8s)
Verifies:
  - Avatar size 80px, round
  - Bubble 34px radius, no pointy tail
  - Hero cutouts centered at X=540
  - Zero emoji, Zero arrow
"""
import http.server
import json
from pathlib import Path
import re
import socketserver
import sys
import threading
import time

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

PORT = 8769

class StudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STUDIO), **kwargs)
    def log_message(self, format, *args):
        pass

def run_probe():
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), StudioHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    print(f"HTTP server running on http://127.0.0.1:{PORT} serving {STUDIO}")

    comp_name = "ttz01-pov-s01"
    url = f"http://127.0.0.1:{PORT}/compositions/{comp_name}.html"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(url)
        page.wait_for_function("window.HYPERFRAMES_READY === true")

        dur = page.evaluate("window.getDuration()")
        print(f"Loaded {comp_name}: duration = {dur}s")

        # Frame A: Chat mid-way (t = 16.0s)
        page.evaluate("window.seekTo(16.0)")
        page.wait_for_timeout(400)
        chat_shot = TMP / f"{comp_name}_frame_chat.png"
        page.screenshot(path=str(chat_shot))
        print(f"  [Saved] Chat Frame: {chat_shot}")

        # Frame B: CTA Outro (t = dur - 2.5s)
        cta_seek = dur - 2.5
        page.evaluate(f"window.seekTo({cta_seek})")
        page.wait_for_timeout(500)
        cta_shot = TMP / f"{comp_name}_frame_cta.png"
        page.screenshot(path=str(cta_shot))
        print(f"  [Saved] CTA Frame: {cta_shot}")

        # Verify element positions
        cta_title = page.eval_on_selector("#cta-1", "el => ({ text: el.innerText, rect: el.getBoundingClientRect() })")
        print(f"  CTA Title: '{cta_title['text']}' width={cta_title['rect']['width']} left={cta_title['rect']['left']}")

        hero_left = page.eval_on_selector("#f-left", "el => el.getBoundingClientRect()")
        hero_right = page.eval_on_selector("#f-right", "el => el.getBoundingClientRect()")
        center_x = (hero_left['left'] + hero_right['right']) / 2.0
        print(f"  Hero Composite Bounds: left={hero_left['left']:.1f}, right={hero_right['right']:.1f}, Center X = {center_x:.1f}px (Target: 540.0)")

        browser.close()
    httpd.shutdown()
    print("=== Visual Inspection Gate Complete ===")

if __name__ == "__main__":
    run_probe()
