#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical Couple Paper Chat (#5) Composition Producer for OmniCut.
100% Golden Master Parity with ors01-pov-s01.html & batch_produce_orsen_20.py.

Supported Products:
  - RED01: Redmi Buds 8 Active (Trio Hero Outro)
  - HAT01: Hatari พัดลมตั้งโต๊ะ 16 นิ้ว (Macro Hero + 6 Pastel Swatches)
  - GOO01: GOOJODOQ 5000mAh Mini Power Bank (Macro Hero + Floating Badges + 4 Colors)

Strict Compliance:
  - Container: <div id="root" ...>
  - Video Paper loop: assets/shared/paper_bg.mp4 (0.5x, transparent CTA overlay)
  - Chat window: #chatwin (top: 470px, height: 1170px), #thread
  - Avatar: 80x80px, position: absolute, top: 0, padding 96px
  - Name: font-size 32px, padding 0 104px, color #55514a (aligned above bubble)
  - Bubble: border-radius 34px, font-size 44px, line-height 1.25, comic ink border 4px
  - Listing photo: square clean frame (padding 10px, radius 18px, 520x520px)
  - Strict Zero-Emoji: No emojis in badges, swatches, or outro text
  - Strict Zero-Arrow: No SVG or PNG arrows
  - 3-Tier CTA layout: #cta-1 (top: 165px), #cta-model (top: 275px), #cta-stage (top: 370px)
"""
import argparse
import html
import json
import os
from pathlib import Path
import sys

# Force UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
COMPS_DIR = STUDIO / "compositions"
DOCS_DIR = ROOT / "_Docs"

WIN_TOP, WIN_H = 470, 1170
NAME_H, BUBBLE_H, GAP, TURN_GAP = 44, 104, 12, 30
PHOTO_H, STICKER_H = 540, 460
SCROLL_PAD = 40

CANONICAL_COUPLE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="th">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="kit/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/kit.css">
    <script src="kit/channels.js"></script>
    <script src="kit/kit.js"></script>
    <style>
      /* __CID__ — Canonical Couple Paper Chat (#5) 100% Golden Master Parity */
      @font-face {
        font-family: "Kanit Black";
        src: url("kit/fonts/Kanit-Black.ttf") format("truetype");
        font-weight: 900;
      }
      @font-face {
        font-family: "Anuphan";
        src: url("kit/fonts/Anuphan-Bold.ttf") format("truetype");
        font-weight: 700;
      }
      :root {
        --ink: #1b1a17;
        --line-red: #d90429;
      }
      #root {
        background: #efece6;
      }
      #paper {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        filter: brightness(1.02);
      }
      /* Headline overlay */
      .hd {
        position: absolute;
        left: 60px;
        right: 60px;
        top: 110px;
        text-align: center;
        color: var(--ink);
        opacity: 0;
        will-change: transform, opacity;
      }
      .hd-sub {
        font-family: "Anuphan", sans-serif;
        font-size: 50px;
        line-height: 1.2;
      }
      .hd-t {
        margin-top: 10px;
        font-size: 92px;
        line-height: 1.12;
      }
      .hl {
        padding: 0 14px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.92) 52%, rgba(255, 230, 0, 0.92) 92%, transparent 92%);
      }
      /* Chat window bounds */
      #chatwin {
        position: absolute;
        left: 0;
        right: 0;
        top: __WINTOP__px;
        height: __WINH__px;
        overflow: hidden;
      }
      #thread {
        position: absolute;
        inset: 0;
        will-change: transform;
      }
      .row,
      .nm {
        position: absolute;
        left: 40px;
        right: 40px;
        display: flex;
        align-items: flex-start;
        gap: 16px;
        opacity: 0;
        will-change: transform, opacity;
      }
      .row.out,
      .nm.out {
        justify-content: flex-end;
      }
      .nm {
        font-family: "Anuphan", sans-serif;
        font-size: 32px;
        color: #55514a;
        padding: 0 104px;
      }
      .row.in {
        padding-left: 96px;
      }
      .row.out {
        padding-right: 96px;
      }
      .ava {
        position: absolute;
        top: 0;
        width: 80px;
        height: 80px;
        border-radius: 50%;
        border: 4px solid var(--ink);
        color: #fff;
        font-family: "Anuphan", sans-serif;
        font-size: 40px;
        line-height: 72px;
        text-align: center;
      }
      .row.in .ava {
        left: 0;
      }
      .row.out .ava {
        right: 0;
      }
      .ava.f {
        background: linear-gradient(135deg, #ff9eb5, #ff5277);
      }
      .ava.m {
        background: linear-gradient(135deg, #60a5fa, #2563eb);
      }
      /* Comic paper sticker bubble */
      .msg {
        display: inline-block;
        padding: 18px 28px;
        border-radius: 34px;
        border: 4px solid var(--ink);
        box-shadow: 4px 6px 0 var(--ink);
        font-family: "Anuphan", sans-serif;
        font-size: 44px;
        line-height: 1.25;
        color: var(--ink);
        will-change: transform;
      }
      .row.in .msg {
        background: #fff;
      }
      .row.out .msg {
        background: #8de07a;
      }
      /* Official listing photo sticker */
      .photo,
      .sticker {
        display: inline-block;
        border: 4px solid var(--ink);
        box-shadow: 5px 8px 0 var(--ink);
        background: #fff;
        padding: 10px;
        border-radius: 18px;
      }
      .photo img {
        display: block;
        width: 520px;
        height: 520px;
        object-fit: cover;
        border-radius: 10px;
      }
      .sticker img {
        display: block;
        width: 440px;
        height: 440px;
        object-fit: contain;
      }

      /* ==================== CTA OUTRO SHOT (STYLE 3B GOLDEN MASTER) ==================== */
      #b-cta {
        position: absolute;
        inset: 0;
        width: 1080px;
        height: 1920px;
        background: transparent;
        z-index: 20;
        pointer-events: none;
      }
      .t {
        font-family: "Kanit Black", sans-serif;
        color: var(--ink);
        text-align: center;
        line-height: 1.1;
      }
      .t.center {
        text-align: center;
        width: 100%;
        left: 0;
        right: 0;
      }
      #cta-1 {
        position: absolute;
        top: 165px;
        left: 0;
        right: 0;
        width: 100%;
        text-align: center;
        z-index: 25;
        font-family: "Kanit Black", sans-serif;
        font-size: __CTA_TITLE_FONT_SIZE__px;
        line-height: 1.15;
        color: #1b1a17;
      }
      #cta-1 .hl {
        padding: 0 16px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
      }
      #cta-model {
        position: absolute;
        top: 275px;
        left: 0;
        right: 0;
        width: 100%;
        text-align: center;
        z-index: 25;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 44px;
        color: #d90429;
      }
      #cta-stage {
        position: absolute;
        top: 370px;
        left: 0;
        width: 1080px;
        height: 880px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 10;
      }
      .contact-shadow {
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
        z-index: 5;
        pointer-events: none;
      }
      __CTA_STAGE_CSS__

      .bottom-info {
        position: absolute;
        bottom: 270px;
        left: 40px;
        right: 40px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 14px;
        z-index: 25;
      }
      .swatch-card {
        background: #ffffff;
        border: 3px solid #1b1a17;
        border-radius: 18px;
        box-shadow: 3px 5px 0 #1b1a17;
        padding: 8px 24px;
        display: flex;
        align-items: center;
        gap: 16px;
      }
      .swatch-title {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 24px;
        color: #1b1a17;
      }
      .chips-grid {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .chip-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 22px;
        color: #1b1a17;
      }
      .chip-dot {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: 2px solid #1b1a17;
      }
      .spec-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        max-width: 960px;
        gap: 10px;
        margin: 0 auto;
      }
      .spec-tag {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 26px;
        background: #ffffff;
        color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 6px 18px;
        border-radius: 12px;
        box-shadow: 3px 5px 0 #1b1a17;
      }
      #wm {
        left: 0 !important;
        right: 0;
        top: auto !important;
        bottom: 26px;
        width: 100% !important;
        height: auto !important;
        text-align: center;
      }
      #wm span {
        position: static !important;
        display: inline-block;
        transform: none !important;
        background: transparent !important;
        font-size: 28px;
        color: rgba(217, 4, 41, 0.75) !important;
      }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="__CID__" data-start="0" data-duration="__TOTAL__" data-width="1080" data-height="1920">
      <video id="paper" class="clip" src="assets/shared/paper_bg.mp4" muted playsinline data-playback-rate="0.5" data-start="0" data-duration="__TOTAL__" data-media-start="0" data-track-index="0"></video>

      <div class="beat clip" id="b-chat" data-start="0" data-duration="__CHATDUR__" data-track-index="2">
        __HEADS__
        <div id="chatwin">
          <div id="thread">
            __ROWS__
          </div>
        </div>
      </div>

      <div class="beat clip" id="b-cta" data-start="__CTA__" data-duration="__CTADUR__" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">__CTA_TITLE__</span></div>
        <div class="t center" id="cta-model">__CTA_SUB__</div>
        <div id="cta-stage">
          __CTA_STAGE_HTML__
        </div>

        <div class="bottom-info">
          __BOTTOM_INFO_HTML__
        </div>
      </div>

      <div id="wm"><span>rizannTry</span></div>

      <audio id="vo" src="assets/clips/__CID__/vo.wav" data-start="0" data-duration="__VODUR__" data-track-index="10" data-volume="1.0"></audio>
      <audio id="bgm" src="assets/shared/bgm_lofi.wav" data-start="0" data-duration="__TOTAL__" data-track-index="11" data-volume="0.05" data-fade-in="0.6" data-fade-out="1.5"></audio>
      __SFX__
    </div>

    <script>
      const ITEMS = __ITEMS__;
      const HEADS = __HEADSJS__;
      const SCROLLS = __SCROLLS__;
      const CTA_T = __CTA__;
      const TOTAL = __TOTAL__;

      const tl = gsap.timeline({ paused: true });

      HEADS.forEach((h, k) => {
        const el = "#" + h.id;
        tl.fromTo(el, { opacity: 0, y: -20, scale: 0.94 }, { opacity: 1, y: 0, scale: 1, duration: 0.28, ease: "back.out(1.8)" }, h.t0);
        if (k + 1 < HEADS.length) {
          tl.to(el, { opacity: 0, y: 15, duration: 0.22, ease: "power2.in" }, h.t1 - 0.22);
        } else {
          tl.to(el, { opacity: 0, scale: 0.9, duration: 0.25, ease: "power2.in" }, CTA_T - 0.25);
        }
      });

      ITEMS.forEach((it) => {
        const el = "#" + it.id;
        const fromX = it.side === "F" ? -40 : 40;
        tl.fromTo(
          el,
          { opacity: 0, x: fromX, scale: 0.88 },
          { opacity: 1, x: 0, scale: 1, duration: 0.24, ease: "back.out(2)" },
          it.t
        );
      });

      SCROLLS.forEach(([t, y]) => {
        tl.to("#thread", { y: -y, duration: 0.32, ease: "power3.out" }, t);
      });

      tl.fromTo("#b-chat", { opacity: 1 }, { opacity: 0, duration: 0.18, ease: "power2.in" }, CTA_T);
      tl.fromTo("#b-cta", { opacity: 0 }, { opacity: 1, duration: 0.24, ease: "power2.out" }, CTA_T);
      tl.fromTo("#cta-1", { opacity: 0, scale: 0.82, rotate: -3 }, { opacity: 1, scale: 1, rotate: 0, duration: 0.35, ease: "back.out(2.2)" }, CTA_T + 0.05);
      tl.fromTo("#cta-model", { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }, CTA_T + 0.18);
      __CTA_GSAP_TIMELINE__
      tl.fromTo(".bottom-info", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, CTA_T + 0.35);

      window.__timelines = window.__timelines || {};
      window.__timelines["__CID__"] = tl;
    </script>
  </body>
</html>"""

def layout_thread(timings, turns_spec, cta_phrase):
    """Calculate deterministic vertical scroll and item positions."""
    items, scrolls, y, scroll = [], [], 16, 0
    ti_clamp = min(cta_phrase[0], len(timings) - 1)
    pi_clamp = min(cta_phrase[1], len(timings[ti_clamp]) - 1)
    cta_t = timings[ti_clamp][pi_clamp][0]
    tilt = [-1.2, 0.8, -0.6, 1.1, -0.9, 0.5]
    n = 0

    def place(h, t):
        nonlocal y, scroll
        top = y
        y += h
        if y - scroll > WIN_H - SCROLL_PAD:
            scroll = y - (WIN_H - SCROLL_PAD)
            scrolls.append((round(t - 0.05, 3), scroll))
        return top

    for ti, (spk, phrases, photo) in enumerate(turns_spec):
        if ti >= len(timings):
            break
        if ti == cta_phrase[0]:
            phrases = phrases[: cta_phrase[1] + 1]
        t0 = timings[ti][0][0]
        items.append({"kind": "name", "spk": spk, "t": t0, "top": place(NAME_H, t0)})
        for pi, (disp, _) in enumerate(phrases):
            if pi >= len(timings[ti]):
                break
            s, e = timings[ti][pi]
            if pi:
                y += GAP
            items.append({"kind": "msg", "spk": spk, "text": disp, "t": s, "e": e, "first": pi == 0, "top": place(BUBBLE_H, s), "rot": tilt[n % len(tilt)]})
            n += 1
            if photo and photo[0] == pi:
                tp = round(s + 0.25, 3)
                y += GAP + 6
                h = PHOTO_H if photo[2] == "photo" else STICKER_H
                photo_src = str(photo[1]).replace("03_Projects/_HyperFrames_Studio/", "").replace("\\", "/").lstrip("/")
                items.append({"kind": photo[2], "spk": spk, "src": photo_src, "t": tp, "top": place(h, tp), "rot": -2.5 if spk == "M" else 2.5})
        y += TURN_GAP
    return items, scrolls, cta_t

# Product Configurations
CONFIGS = {
    "RED01": {
        "title": "Redmi Buds 8 Active",
        "title_font_size": 66,
        "sub": "หูฟังบลูทูธไดรเวอร์ 14.2mm · กดตะกร้าเหลือง",
        "cta_stage_css": """
      .earbuds-wrap {
        position: absolute;
      }
      .earbuds-img {
        display: block;
        width: 100%;
        height: 100%;
        object-fit: contain;
        filter: drop-shadow(0 16px 28px rgba(0, 0, 0, 0.22));
      }
      #f-left {
        width: 450px;
        height: 487px;
        left: 80px;
        bottom: 35px;
        transform: rotate(-6deg);
        z-index: 2;
      }
      #f-right {
        width: 450px;
        height: 487px;
        right: 80px;
        bottom: 35px;
        transform: rotate(6deg);
        z-index: 2;
      }
      #f-center {
        width: 520px;
        height: 563px;
        left: 50%;
        margin-left: -260px;
        bottom: 15px;
        z-index: 5;
      }
      #cs-center {
        width: 440px;
        height: 55px;
        bottom: 12px;
        left: 50%;
        margin-left: -220px;
        z-index: 4;
      }
      #cs-left {
        width: 350px;
        height: 45px;
        bottom: 30px;
        left: 110px;
        z-index: 1;
      }
      #cs-right {
        width: 350px;
        height: 45px;
        bottom: 30px;
        right: 110px;
        z-index: 1;
      }
        """,
        "cta_stage_html": """
          <div class="contact-shadow" id="cs-left"></div>
          <div class="contact-shadow" id="cs-right"></div>
          <div class="contact-shadow" id="cs-center"></div>
          <div class="earbuds-wrap" id="f-left"><img class="earbuds-img" src="assets/red01/cutouts/redmi_black.png" alt="Black"></div>
          <div class="earbuds-wrap" id="f-right"><img class="earbuds-img" src="assets/red01/cutouts/redmi_blue.png" alt="Blue"></div>
          <div class="earbuds-wrap" id="f-center"><img class="earbuds-img" src="assets/red01/cutouts/redmi_white.png" alt="White"></div>
        """,
        "cta_gsap_timeline": """
      tl.fromTo(["#f-left", "#cs-left"], { opacity: 0, x: -50, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.22);
      tl.fromTo(["#f-right", "#cs-right"], { opacity: 0, x: 50, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.22);
      tl.fromTo(["#f-center", "#cs-center"], { opacity: 0, scale: 0.75 }, { opacity: 1, scale: 1, duration: 0.46, ease: "back.out(2)" }, CTA_T + 0.26);
        """,
        "bottom_info_html": """
          <div class="swatch-card">
            <span class="swatch-title">3 โทนสีโมเดิร์น :</span>
            <div class="chips-grid">
              <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว White</div>
              <div class="chip-item"><div class="chip-dot" style="background:#222222"></div>ดำ Black</div>
              <div class="chip-item"><div class="chip-dot" style="background:#5b9bd5"></div>ฟ้า Blue</div>
            </div>
          </div>
          <div class="spec-row">
            <span class="spec-tag">ไดรเวอร์ 14.2mm Titanium</span>
            <span class="spec-tag">กึ่งอินเอียร์ ไม่เจ็บหู</span>
            <span class="spec-tag">ไมค์คู่ Dual-Mic AI ENC</span>
            <span class="spec-tag">แบตเตอรี่รวมเคส 37 ชม.</span>
          </div>
        """,
        "scripts_file": DOCS_DIR / "redmi_buds8_20_scripts.json",
        "clip_prefix": "red01-pov-s",
        "photos_dir": "assets/red01/img",
        "default_photos": [
            "assets/red01/img/red01_img_01.webp",
            "assets/red01/img/red01_img_02.webp",
            "assets/red01/img/red01_img_04.webp",
            "assets/red01/img/red01_img_05.webp"
        ]
    },
    "HAT01": {
        "title": "Hatari · พัดลมตั้งโต๊ะ 16 นิ้ว",
        "title_font_size": 60,
        "sub": "รุ่น T16M1 สไตล์มินิมอล · กดตะกร้าเหลือง",
        "cta_stage_css": """
      .hero-img {
        width: 680px;
        height: 680px;
        object-fit: contain;
        filter: drop-shadow(0 16px 30px rgba(0, 0, 0, 0.22));
        position: absolute;
        top: 30px;
        left: 50%;
        margin-left: -340px;
        z-index: 10;
      }
      #cs-hatari {
        width: 580px;
        height: 85px;
        bottom: 110px;
        left: 50%;
        margin-left: -290px;
        z-index: 5;
      }
      .floating-badge {
        position: absolute;
        z-index: 22;
        font-family: 'Anuphan', sans-serif;
        font-weight: 700;
        font-size: 24px;
        background: #ffffff;
        color: var(--ink);
        border: 3.5px solid var(--ink);
        padding: 7px 16px;
        border-radius: 18px;
        box-shadow: 3px 5px 0 var(--ink);
        white-space: nowrap;
      }
      #fb-1 { top: 70px; left: 70px; rotate: -4deg; }
      #fb-2 { top: 60px; right: 70px; rotate: 4deg; }
      #fb-3 { bottom: 180px; left: 65px; rotate: 3deg; }
      #fb-4 { bottom: 190px; right: 65px; rotate: -3deg; }
        """,
        "cta_stage_html": """
          <div class="contact-shadow" id="cs-hatari"></div>
          <img class="hero-img" src="assets/hatari01/cutouts/hatari_sand_hi.png" alt="Hatari 16 Inch Fan">
          <div class="floating-badge" id="fb-1">ใบพัด 16 นิ้ว ลมแรง</div>
          <div class="floating-badge" id="fb-2">ปรับแรงลม 3 ระดับ</div>
          <div class="floating-badge" id="fb-3">มอเตอร์ Ball Bearing</div>
          <div class="floating-badge" id="fb-4">ระบบ Thermal Fuse</div>
        """,
        "cta_gsap_timeline": """
      tl.fromTo([".hero-img", "#cs-hatari"], { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.2);
      tl.fromTo(".floating-badge", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.32, stagger: 0.08, ease: "back.out(2)" }, CTA_T + 0.28);
        """,
        "bottom_info_html": """
          <div class="swatch-card">
            <span class="swatch-title">6 โทนสีพาสเทล :</span>
            <div class="chips-grid">
              <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว</div>
              <div class="chip-item"><div class="chip-dot" style="background:#98d8c8"></div>มิ้นท์</div>
              <div class="chip-item"><div class="chip-dot" style="background:#f9c5d1"></div>ชมพู</div>
              <div class="chip-item"><div class="chip-dot" style="background:#dfd7ca"></div>ทราย</div>
              <div class="chip-item"><div class="chip-dot" style="background:#d4c4fb"></div>ม่วง</div>
              <div class="chip-item"><div class="chip-dot" style="background:#b3d9ff"></div>ฟ้า</div>
            </div>
          </div>
          <div class="spec-row">
            <span class="spec-tag">สไตล์มินิมอลโมเดิร์น</span>
            <span class="spec-tag">ประหยัดไฟเบอร์ 5</span>
            <span class="spec-tag">รับประกันมอเตอร์ 3 ปี</span>
            <span class="spec-tag">มาตรฐาน มอก. แท้ 100%</span>
          </div>
        """,
        "scripts_file": DOCS_DIR / "hatari_16inch_20_scripts.json",
        "clip_prefix": "hat01-pov-s",
        "photos_dir": "assets/hatari01/img",
        "default_photos": [
            "assets/hatari01/img/hatari_clean_main.webp",
            "assets/hatari01/img/hatari_clean_angle.webp",
            "assets/hatari01/img/hatari_clean_side.webp",
            "assets/hatari01/img/hatari_clean_motor.webp"
        ]
    },
    "GOO01": {
        "title": "GOOJODOQ · พาวเวอร์แบงค์แคปซูล",
        "title_font_size": 54,
        "sub": "5000mAh มี 2 หัวในตัว · กดตะกร้าเหลือง",
        "cta_stage_css": """
      .hero-img {
        width: 680px;
        height: 680px;
        object-fit: contain;
        filter: drop-shadow(0 16px 30px rgba(0, 0, 0, 0.22));
        position: absolute;
        top: 30px;
        left: 50%;
        margin-left: -340px;
        z-index: 10;
      }
      #cs-goo {
        width: 580px;
        height: 85px;
        bottom: 110px;
        left: 50%;
        margin-left: -290px;
        z-index: 5;
      }
      .floating-badge {
        position: absolute;
        z-index: 22;
        font-family: 'Anuphan', sans-serif;
        font-weight: 700;
        font-size: 24px;
        background: #ffffff;
        color: var(--ink);
        border: 3.5px solid var(--ink);
        padding: 7px 16px;
        border-radius: 18px;
        box-shadow: 3px 5px 0 var(--ink);
        white-space: nowrap;
      }
      #fb-1 { top: 70px; left: 70px; rotate: -4deg; }
      #fb-2 { top: 60px; right: 70px; rotate: 4deg; }
      #fb-3 { bottom: 180px; left: 65px; rotate: 3deg; }
      #fb-4 { bottom: 190px; right: 65px; rotate: -3deg; }
        """,
        "cta_stage_html": """
          <div class="contact-shadow" id="cs-goo"></div>
          <img class="hero-img" src="assets/goo01/img/hero_cutout.png" alt="GOOJODOQ 5000mAh">
          <div class="floating-badge" id="fb-1">2in1 iOS + Type-C</div>
          <div class="floating-badge" id="fb-2">5000mAh เต็มพลัง</div>
          <div class="floating-badge" id="fb-3">เบาแค่ 100 กรัม</div>
          <div class="floating-badge" id="fb-4">มีขาตั้ง + มอก. แท้</div>
        """,
        "cta_gsap_timeline": """
      tl.fromTo([".hero-img", "#cs-goo"], { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.2);
      tl.fromTo(".floating-badge", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.32, stagger: 0.08, ease: "back.out(2)" }, CTA_T + 0.28);
        """,
        "bottom_info_html": """
          <div class="swatch-card">
            <span class="swatch-title">4 สีมินิมอล :</span>
            <div class="chips-grid">
              <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว White</div>
              <div class="chip-item"><div class="chip-dot" style="background:#ffccd5"></div>ชมพู Pink</div>
              <div class="chip-item"><div class="chip-dot" style="background:#e0bbf8"></div>ม่วง Purple</div>
              <div class="chip-item"><div class="chip-dot" style="background:#222222"></div>ดำ Black</div>
            </div>
          </div>
          <div class="spec-row">
            <span class="spec-tag">หัวชาร์จ 2in1 เสียบตรง</span>
            <span class="spec-tag">ไม่ต้องพกสายชาร์จ</span>
            <span class="spec-tag">หน้าจอดิจิทัล LED</span>
            <span class="spec-tag">มาตรฐาน มอก. แท้ 100%</span>
          </div>
        """,
        "scripts_file": DOCS_DIR / "goojodoq_5000mah_20_scripts.json",
        "clip_prefix": "goo01-pov-s",
        "photos_dir": "assets/goo01/img",
        "default_photos": [
            "assets/goo01/img/goo01_img_01.webp",
            "assets/goo01/img/goo01_img_02.webp",
            "assets/goo01/img/goo01_img_03.webp",
            "assets/goo01/img/goo01_img_06.webp"
        ]
    }
}

def generate_product_compositions(product_code: str):
    cfg = CONFIGS[product_code]
    print(f"\n>>> GENERATING COMPOSITIONS FOR {product_code}: {cfg['title']}")

    with open(cfg["scripts_file"], "r", encoding="utf-8") as f:
        scripts = json.load(f)

    generated = 0
    for idx, s in enumerate(scripts, start=1):
        cid = f"{cfg['clip_prefix']}{idx:02d}"
        clip_dir = STUDIO / "clips" / cid
        vo_p = STUDIO / "assets" / "clips" / cid / "vo.wav"
        timings_p = clip_dir / "timings.json"

        if not vo_p.exists() or not timings_p.exists():
            print(f"  [SKIP] {cid}: Missing audio or timings.json")
            continue

        with open(timings_p, "r", encoding="utf-8") as f:
            t_data = json.load(f)
            timings = t_data.get("turns", t_data) if isinstance(t_data, dict) else t_data

        # Get audio duration
        import wave
        with wave.open(str(vo_p), "rb") as wf:
            vo_dur = round(wf.getnframes() / float(wf.getframerate()), 3)

        # Build turns spec
        turns = s.get("turns") or s.get("dialogue_turns", [])
        turns_spec = []
        for ti, turn in enumerate(turns):
            if isinstance(turn, (list, tuple)):
                spk = turn[0]
                p_tuples = turn[1]
                photo = turn[2] if len(turn) > 2 else None
            else:
                spk = turn.get("speaker", "F")[0].upper()
                phrases = turn.get("phrases", [])
                p_tuples = [(p.get("display_text", ""), p.get("spoken_text", "")) for p in phrases]
                photo = turn.get("product_photo")
            turns_spec.append((spk, p_tuples, photo))

        # CTA phrase is typically the last turn's last phrase
        last_ti = min(len(turns_spec) - 1, len(timings) - 1)
        last_pi = min(len(turns_spec[last_ti][1]) - 1, len(timings[last_ti]) - 1)
        cta_phrase = (last_ti, last_pi)

        # Layout thread
        items, scrolls, cta_t = layout_thread(timings, turns_spec, cta_phrase)

        # Headlines spec
        headlines = s.get("top_headlines", [])
        if not headlines:
            headlines = [
                {"turn": 0, "sub": "POV: สไตล์คู่รักสายใต้", "t": cfg["title"], "hl": cfg["sub"].split("·")[0]},
                {"turn": min(3, len(turns_spec)-1), "sub": "พี่บ่าวแนะนำตัวเด็ด", "t": "ของดีต้องมีติดตัว", "hl": "ชี้เป้าตัวจบ"},
                {"turn": min(6, len(turns_spec)-1), "sub": "ของแท้ ปลอดภัย 100%", "t": "สเปกจัดเต็มคุ้มราคา", "hl": "ลองแล้วจะรัก"},
                {"turn": len(turns_spec)-1, "sub": "พิกัดโปรสุดคุ้ม", "t": "กดตะกร้าเหลือง", "hl": "มีจำนวนจำกัด"}
            ]

        total = round(vo_dur + 1.4, 2)
        turn_starts = [t[0][0] for t in timings]
        n_turns = len(turn_starts)

        turn_indices = []
        for k, h in enumerate(headlines):
            target = h.get("turn", 0)
            if target >= n_turns:
                target = min(int(k * (n_turns - 1) / max(1, len(headlines) - 1)), n_turns - 1)
            turn_indices.append(target)
        for i_idx in range(1, len(turn_indices)):
            if turn_indices[i_idx] <= turn_indices[i_idx - 1]:
                turn_indices[i_idx] = min(turn_indices[i_idx - 1] + 1, n_turns - 1)

        heads = []
        for k, h in enumerate(headlines):
            ti = turn_indices[k]
            sub = h.get("sub", "")
            l1 = h.get("t", "")
            l2 = h.get("hl", "")
            t0 = 0 if k == 0 else round(turn_starts[ti] - 0.1, 3)
            if k + 1 == len(headlines):
                t1 = round(cta_t, 3)
            else:
                next_ti = turn_indices[k + 1]
                t1 = round(turn_starts[next_ti] - 0.1, 3) if next_ti > ti else round(cta_t, 3)
            if t1 <= t0:
                t1 = round(t0 + 2.0, 3)
            heads.append((k, t0, t1, sub, l1, l2))

        rows = []
        for i, it in enumerate(items):
            side = "in" if it["spk"] == "F" else "out"
            if it["kind"] == "name":
                label = "น้องนุ้ย" if it["spk"] == "F" else "พี่บ่าว"
                rows.append(f'<div class="nm {side}" id="i{i}" style="top: {it["top"]}px">{label}</div>')
            elif it["kind"] == "msg":
                ava = ""
                if it["first"]:
                    ava = f'<div class="ava {"f" if side == "in" else "m"}">{"น" if side == "in" else "บ"}</div>'
                rows.append(f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px">{ava}<div class="msg" style="rotate: {it["rot"]}deg">{html.escape(it["text"], quote=True)}</div></div>')
            else:
                cls = "photo" if it["kind"] == "photo" else "sticker"
                rows.append(f'<div class="row {side}" id="i{i}" style="top: {it["top"]}px"><div class="{cls}" style="rotate: {it["rot"]}deg"><img src="{it["src"]}" alt=""></div></div>')

        head_html = "\n        ".join(
            f'<div class="hd" id="hd{k}"><div class="hd-sub">{html.escape(sub, quote=True)}</div><div class="hd-t"><span class="hl">{html.escape(l1, quote=True)}</span><br><span class="hl">{html.escape(l2, quote=True)}</span></div></div>'
            for k, t0, t1, sub, l1, l2 in heads
        )

        sfx = []
        for ti, (spk, _, _) in enumerate(turns_spec):
            if ti == cta_phrase[0] + 1:
                break
            sfx.append(("msg_recv.mp3" if spk == "F" else "msg_send.mp3", turn_starts[ti] + 0.01, 0.5, 0.3))
        for it in items:
            if it["kind"] in ("photo", "sticker"):
                sfx.append(("paper.mp3", it["t"], 0.45, 0.40))
        sfx.append(("ding.wav", timings[min(5, len(timings)-1)][0][0] + 0.3, 0.8, 0.3))
        sfx.append(("punch.mp3", timings[min(8, len(timings)-1)][0][0] + 0.3, 0.5, 0.35))
        sfx.append(("wow.mp3", timings[min(10, len(timings)-1)][0][0] + 0.2, 1.0, 0.3))
        sfx.append(("whoosh.mp3", cta_t - 0.05, 0.5, 0.18))
        sfx.append(("boom.wav", cta_t + 0.07, 0.8, 0.15))
        sfx.append(("cash_register.mp3", cta_t + 0.55, 1.0, 0.20))

        sfx_html = "\n      ".join(
            f'<audio id="sx{k:02d}" src="assets/shared/sfx/{f}" data-start="{round(t, 3)}" data-duration="{d}" data-track-index="{12 + k % 2}" data-volume="{v}"></audio>'
            for k, (f, t, d, v) in enumerate(sorted(sfx, key=lambda x: x[1]))
        )

        js_items = json.dumps([{"id": f"i{i}", "kind": it["kind"], "side": it["spk"], "t": it["t"], "e": it.get("e")} for i, it in enumerate(items)])
        js_heads = json.dumps([{"id": f"hd{k}", "t0": t0, "t1": t1} for k, t0, t1, *_ in heads])
        js_scrolls = json.dumps(scrolls)
        rows_html = "\n            ".join(rows)

        page = CANONICAL_COUPLE_TEMPLATE
        replacements = {
            "__CID__": cid,
            "__TOTAL__": str(total),
            "__VODUR__": str(vo_dur),
            "__CTA__": str(round(cta_t, 3)),
            "__CTADUR__": str(round(total - cta_t, 3)),
            "__CHATDUR__": str(round(cta_t, 3)),
            "__ROWS__": rows_html,
            "__HEADS__": head_html,
            "__SFX__": sfx_html,
            "__ITEMS__": js_items,
            "__HEADSJS__": js_heads,
            "__SCROLLS__": js_scrolls,
            "__WINTOP__": str(WIN_TOP),
            "__WINH__": str(WIN_H),
            "__CTA_TITLE__": cfg["title"],
            "__CTA_TITLE_FONT_SIZE__": str(cfg.get("title_font_size", 82)),
            "__CTA_SUB__": cfg["sub"],
            "__CTA_STAGE_CSS__": cfg["cta_stage_css"],
            "__CTA_STAGE_HTML__": cfg["cta_stage_html"],
            "__CTA_GSAP_TIMELINE__": cfg["cta_gsap_timeline"],
            "__BOTTOM_INFO_HTML__": cfg["bottom_info_html"]
        }
        for k, v in replacements.items():
            page = page.replace(k, v)

        out_comp = COMPS_DIR / f"{cid}.html"
        out_comp.parent.mkdir(parents=True, exist_ok=True)
        out_comp.write_text(page, encoding="utf-8")

        out_clip = clip_dir / "index.html"
        out_clip.write_text(page, encoding="utf-8")
        generated += 1
        print(f"  [OK] {cid}.html (dur: {total}s, cta_t: {round(cta_t, 2)}s)")

    print(f"✅ Finished generating {generated}/20 compositions for {product_code}")
    return generated

def main():
    parser = argparse.ArgumentParser(description="Canonical Couple Composition Producer")
    parser.add_argument("--product", choices=["RED01", "HAT01", "GOO01", "ALL"], default="ALL", help="Target product")
    args = parser.parse_args()

    targets = ["GOO01", "HAT01", "RED01"] if args.product == "ALL" else [args.product]
    for prod in targets:
        generate_product_compositions(prod)

if __name__ == "__main__":
    main()
