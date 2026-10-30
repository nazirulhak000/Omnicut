#!/usr/bin/env python3
"""Master Batch Upgrader & Renderer for 80 HyperFrames Compositions.
Upgrades all 4 products (Orsen S6, Hatari Cyclone Max, HOYAUP Cooler, Essager 30W)
to the approved Style 3B Golden Formula (Zero-Emoji, Zero-Arrow, Quad Heads & Macro Hero Standards).

Products:
  1. ORS01 (Orsen by Eloop S6 240W): Style 1B Quad Heads Lineup (s01 - s20)
  2. HAT02 (Hatari Cyclone Max 8"): Style 3B Trio Hero + 6-Color Swatch Strip (s01 - s20)
  3. HOY01 (HOYAUP Magnetic Cooler): Macro Hero 780px + 4 Floating Badges (s01 - s20)
  4. ESS02 (Essager PD 30W Fast Charger): Macro Hero 730px + 4 Floating Badges (s01 - s20)
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

REGISTRY_LOCK = threading.Lock()


def is_valid_mp4(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1024 * 1024:
        return False
    try:
        res = subprocess.run(["ffprobe", "-v", "error", str(path)], capture_output=True, timeout=10)
        return res.returncode == 0
    except Exception:
        return False

# Force UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
COMPS_DIR = STUDIO / "compositions"
CLIPS_DIR = STUDIO / "clips"
ARCHIVE_DIR = ROOT / "06_Archive" / "HyperFrames_Studio"
ARCHIVE_COMPS = ARCHIVE_DIR / "compositions"
ARCHIVE_CLIPS = ARCHIVE_DIR / "clips"

EXPORTS_DIR = ROOT / "04_Exports" / "Ready_to_post"
COVERS_DIR = ROOT / "05_Covers_Thumbnails"
TMP_DIR = ROOT / ".tmp"
DOCS_DIR = ROOT / "_Docs"

EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
COMPS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))
from scripts.tiktok_enhancer import enhance_video_for_tiktok


# ==============================================================================
# 1. Product Definitions & Templates
# ==============================================================================

PRODUCTS = {
    "ors01": {
        "code": "ORS01",
        "product_id": "37521e0dae1a419e8037e159254d4fdf",
        "slug": "ors01-pov",
        "brightness": -0.031,
        "brand_title": "ORSEN · S6 240W",
        "sub_cta": "สายชาร์จเร็วตัวจบ · กดตะกร้าเหลือง",
    },
    "hat02": {
        "code": "HAT02",
        "product_id": "cde38b1c07e54ea69a3d50a6c1bb3f18",
        "slug": "hat02-pov",
        "brightness": -0.031,
        "brand_title": "HATARI · CYCLONE MAX",
        "sub_cta": "พลังลมตัวจบ · กดตะกร้าเหลือง",
    },
    "hoy01": {
        "code": "HOY01",
        "product_id": "673882d55bd84c57ba805000a910c466",
        "slug": "hoy01-pov",
        "brightness": -0.031,
        "brand_title": "HOYAUP · พัดลมแม่เหล็ก",
        "sub_cta": "ไอทีสายเกมตัวจบ · กดตะกร้าเหลือง",
    },
    "ess02": {
        "code": "ESS02",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "slug": "ess02-pov",
        "brightness": -0.015,
        "brand_title": "ESSAGER · PD 30W",
        "sub_cta": "ชาร์จเร็วตัวจบ · กดตะกร้าเหลือง",
    },
}

# --- 1A. Orsen S6 (Quad Heads Lineup - Style 1B) ---
CSS_ORSEN = """
      /* --- Style 1B: Quad Heads Lineup Standard --- */
      #b-cta {
        position: absolute; inset: 0; width: 1080px; height: 1920px;
        z-index: 20; pointer-events: none;
      }
      #cta-1 {
        position: absolute; top: 165px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Kanit Black", sans-serif;
        font-size: 86px; line-height: 1.15;
        color: #1b1a17;
      }
      #cta-1 .hl {
        padding: 0 16px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
      }
      #cta-model {
        position: absolute; top: 275px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Anuphan", sans-serif;
        font-weight: 700; font-size: 50px;
        color: #d90429;
      }
      #cta-stage {
        position: absolute; top: 370px; left: 0; width: 1080px; height: 880px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        z-index: 10;
      }
      .coil-bg {
        width: 610px; height: 610px;
        object-fit: contain;
        filter: drop-shadow(0 14px 28px rgba(0,0,0,0.18));
        position: absolute;
        top: 30px; left: 50%;
        transform: translateX(-50%);
        z-index: 10;
        opacity: 0.95;
      }
      .contact-shadow {
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
        z-index: 5;
        pointer-events: none;
      }
      #cs-coil {
        width: 560px; height: 85px;
        bottom: 220px; left: 50%;
        transform: translateX(-50%);
      }
      .heads-lineup {
        position: absolute;
        bottom: 60px;
        display: flex;
        justify-content: center;
        align-items: flex-end;
        gap: 36px;
        z-index: 20;
      }
      .head-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
      }
      .head-img {
        height: 380px;
        width: auto;
        object-fit: contain;
        filter: drop-shadow(0 10px 18px rgba(0,0,0,0.25));
      }
      .head-label {
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 22px;
        background: #ffffff;
        color: #1b1a17;
        border: 2.5px solid #1b1a17;
        padding: 3px 12px;
        border-radius: 12px;
        box-shadow: 2px 3px 0 #1b1a17;
        white-space: nowrap;
      }
      .floating-badge {
        position: absolute;
        z-index: 22;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 25px;
        background: #ffffff;
        color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 8px 18px;
        border-radius: 20px;
        box-shadow: 3px 5px 0 #1b1a17;
        white-space: nowrap;
      }
      .bottom-info {
        position: absolute; bottom: 270px; left: 40px; right: 40px;
        display: flex; flex-direction: column; align-items: center; gap: 14px;
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
      .spec-row {
        display: flex; flex-wrap: wrap; justify-content: center;
        max-width: 960px; gap: 10px; margin: 0 auto;
      }
      .spec-tag {
        font-family: "Anuphan", sans-serif;
        font-weight: 700; font-size: 26px;
        background: #ffffff; color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 6px 18px; border-radius: 12px;
        box-shadow: 3px 5px 0 #1b1a17;
      }
"""

HTML_ORSEN = """
      <div class="beat clip" id="b-cta" data-start="{cta_start}" data-duration="{cta_dur}" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">Orsen · S6 240W</span></div>
        <div class="t center" id="cta-model">สายชาร์จเร็วตัวจบ · กดตะกร้าเหลือง</div>
        <div id="cta-stage">
          <div class="contact-shadow" id="cs-coil"></div>
          <img class="coil-bg" src="assets/ors01/img/cut_coil_240w.png">

          <div class="heads-lineup">
            <div class="head-item" style="transform: rotate(-3deg);">
              <img class="head-img" src="assets/ors01/img/head_black.png">
              <span class="head-label">ดำด้าน</span>
            </div>
            <div class="head-item" style="transform: rotate(-1deg); margin-bottom: 12px;">
              <img class="head-img" src="assets/ors01/img/head_white.png">
              <span class="head-label">ขาวคลีน</span>
            </div>
            <div class="head-item" style="transform: rotate(1deg); margin-bottom: 12px;">
              <img class="head-img" src="assets/ors01/img/head_green.png">
              <span class="head-label">เขียวเซจ</span>
            </div>
            <div class="head-item" style="transform: rotate(3deg);">
              <img class="head-img" src="assets/ors01/img/head_pink.png">
              <span class="head-label">ชมพูพาสเทล</span>
            </div>
          </div>

          <div class="floating-badge" style="top: 40px; right: 90px; transform: rotate(3deg);">
            ชาร์จไวแรง 240W เต็มสปีด
          </div>
          <div class="floating-badge" style="top: 60px; left: 90px; transform: rotate(-3deg);">
            ยาว 1.5 เมตร สายถัก 48 เส้น
          </div>
        </div>

        <div class="bottom-info">
          <div class="swatch-card">
            <span class="swatch-title">ดีไซน์พรีเมียม 4 สไตล์ เข้ากับทุกอุปกรณ์ Type-C</span>
          </div>

          <div class="spec-row">
            <div class="spec-tag">กำลังไฟสูงสุด 240W</div>
            <div class="spec-tag">ชิปอัจฉริยะ E-MARK</div>
            <div class="spec-tag">สายถักทนทาน 48 เส้น</div>
            <div class="spec-tag">ถ่ายโอนไว 480Mbps</div>
          </div>
        </div>
      </div>
"""

GSAP_ORSEN = """
      tl.fromTo("#b-chat", { opacity: 1 }, { opacity: 0, duration: 0.18, ease: "power2.in" }, CTA_T);
      tl.fromTo("#b-cta", { opacity: 0 }, { opacity: 1, duration: 0.24, ease: "power2.out" }, CTA_T);
      tl.fromTo("#cta-1", { opacity: 0, scale: 0.82, rotate: -3 }, { opacity: 1, scale: 1, rotate: 0, duration: 0.35, ease: "back.out(2.2)" }, CTA_T + 0.05);
      tl.fromTo("#cta-model", { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }, CTA_T + 0.18);
      tl.fromTo(".coil-bg", { opacity: 0, scale: 0.65 }, { opacity: 0.95, scale: 1, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.22);
      tl.fromTo("#cs-coil", { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.45, ease: "power2.out" }, CTA_T + 0.22);
      tl.fromTo(".head-item", { opacity: 0, y: 50, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, stagger: 0.08, duration: 0.38, ease: "back.out(2)" }, CTA_T + 0.32);
      tl.fromTo(".floating-badge", { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, stagger: 0.1, duration: 0.35, ease: "back.out(2)" }, CTA_T + 0.45);
      tl.fromTo(".bottom-info", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, CTA_T + 0.4);
"""


# --- 1B. Hatari Cyclone Max (Trio Hero + 6-Color Swatch - Style 3B) ---
CSS_HATARI = """
      /* --- Style 3B: Hatari Cyclone Max Trio Hero Standard --- */
      #b-cta {
        position: absolute; inset: 0; width: 1080px; height: 1920px;
        z-index: 20; pointer-events: none;
      }
      #cta-1 {
        position: absolute; top: 165px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Kanit Black", sans-serif;
        font-size: 84px; line-height: 1.15;
        color: #1b1a17;
      }
      #cta-1 .hl {
        padding: 0 16px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
      }
      #cta-model {
        position: absolute; top: 275px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Anuphan", sans-serif;
        font-weight: 700; font-size: 50px;
        color: #d90429;
      }
      #cta-stage {
        position: absolute; top: 370px; left: 0; width: 1080px; height: 880px;
        z-index: 10;
      }
      .fan-wrapper {
        position: absolute;
      }
      .fan-img {
        object-fit: contain;
      }
      .contact-shadow {
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
        z-index: 5;
        pointer-events: none;
      }
      #f-left {
        top: 130px; left: 80px;
        transform: rotate(-5deg);
        z-index: 11;
      }
      #f-left .fan-img {
        width: 460px; height: 460px;
        filter: drop-shadow(0 14px 28px rgba(0,0,0,0.22));
      }
      #cs-left {
        width: 380px; height: 65px;
        bottom: -15px; left: 40px;
      }
      #f-right {
        top: 130px; right: 80px;
        transform: rotate(5deg);
        z-index: 12;
      }
      #f-right .fan-img {
        width: 460px; height: 460px;
        filter: drop-shadow(0 14px 28px rgba(0,0,0,0.22));
      }
      #cs-right {
        width: 380px; height: 65px;
        bottom: -15px; left: 40px;
      }
      #f-center {
        top: 40px; left: 50%;
        transform: translateX(-50%);
        z-index: 15;
      }
      #f-center .fan-img {
        width: 580px; height: 580px;
        filter: drop-shadow(0 22px 42px rgba(0,0,0,0.30));
      }
      #cs-center {
        width: 500px; height: 85px;
        bottom: -20px; left: 40px;
      }
      .floating-badge {
        position: absolute;
        z-index: 22;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 25px;
        background: #ffffff;
        color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 8px 18px;
        border-radius: 20px;
        box-shadow: 3px 5px 0 #1b1a17;
        white-space: nowrap;
      }
      .bottom-info {
        position: absolute; bottom: 270px; left: 40px; right: 40px;
        display: flex; flex-direction: column; align-items: center; gap: 14px;
        z-index: 25;
      }
      .swatch-card {
        background: #ffffff;
        border: 3px solid #1b1a17;
        border-radius: 18px;
        box-shadow: 3px 5px 0 #1b1a17;
        padding: 10px 22px;
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
      .swatch-dots {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .swatch-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 20px;
        color: #1b1a17;
      }
      .dot {
        width: 20px; height: 20px;
        border-radius: 50%;
        border: 2px solid #1b1a17;
        display: inline-block;
        box-shadow: 1px 2px 0 rgba(0,0,0,0.15);
      }
      .spec-row {
        display: flex; flex-wrap: wrap; justify-content: center;
        max-width: 960px; gap: 10px; margin: 0 auto;
      }
      .spec-tag {
        font-family: "Anuphan", sans-serif;
        font-weight: 700; font-size: 26px;
        background: #ffffff; color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 6px 18px; border-radius: 12px;
        box-shadow: 3px 5px 0 #1b1a17;
      }
"""

HTML_HATARI = """
      <div class="beat clip" id="b-cta" data-start="{cta_start}" data-duration="{cta_dur}" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">Hatari · Cyclone Max</span></div>
        <div class="t center" id="cta-model">พลังลมตัวจบ · กดตะกร้าเหลือง</div>
        <div id="cta-stage">
          <div class="fan-wrapper" id="f-left">
            <div class="contact-shadow" id="cs-left"></div>
            <img class="fan-img" src="assets/hatari02/img/hatari_cyclone_clean_cutout.png">
          </div>
          <div class="fan-wrapper" id="f-right">
            <div class="contact-shadow" id="cs-right"></div>
            <img class="fan-img" src="assets/hatari02/img/hatari_cyclone_clean_cutout.png">
          </div>
          <div class="fan-wrapper" id="f-center">
            <div class="contact-shadow" id="cs-center"></div>
            <img class="fan-img" src="assets/hatari02/img/hatari_cyclone_clean_cutout.png">
          </div>

          <div class="floating-badge" style="top: 70px; right: 80px; transform: rotate(3deg);">
            ใบพัดทรงพลัง 8 นิ้ว
          </div>
          <div class="floating-badge" style="top: 90px; left: 80px; transform: rotate(-3deg);">
            ปรับแรงลมได้ 3 ระดับ
          </div>
        </div>

        <div class="bottom-info">
          <div class="swatch-card">
            <span class="swatch-title">มีให้เลือกครบ 6 สีพาสเทล :</span>
            <div class="swatch-dots">
              <div class="swatch-item"><span class="dot" style="background: #ffffff;"></span> ขาว</div>
              <div class="swatch-item"><span class="dot" style="background: #d4e09b;"></span> มิ้นท์</div>
              <div class="swatch-item"><span class="dot" style="background: #f6c8d5;"></span> ชมพู</div>
              <div class="swatch-item"><span class="dot" style="background: #c3d9f0;"></span> ฟ้า</div>
              <div class="swatch-item"><span class="dot" style="background: #fae4a8;"></span> เหลือง</div>
              <div class="swatch-item"><span class="dot" style="background: #d8c8e8;"></span> ม่วง</div>
            </div>
          </div>

          <div class="spec-row">
            <div class="spec-tag">มอเตอร์ Ball Bearing</div>
            <div class="spec-tag">ระบบเซฟตี้ Thermal Fuse</div>
            <div class="spec-tag">ปรับก้มเงยได้ 90 องศา</div>
            <div class="spec-tag">รับประกันนาน 3 ปี</div>
          </div>
        </div>
      </div>
"""

GSAP_HATARI = """
      tl.fromTo("#b-chat", { opacity: 1 }, { opacity: 0, duration: 0.18, ease: "power2.in" }, CTA_T);
      tl.fromTo("#b-cta", { opacity: 0 }, { opacity: 1, duration: 0.24, ease: "power2.out" }, CTA_T);
      tl.fromTo("#cta-1", { opacity: 0, scale: 0.82, rotate: -3 }, { opacity: 1, scale: 1, rotate: 0, duration: 0.35, ease: "back.out(2.2)" }, CTA_T + 0.05);
      tl.fromTo("#cta-model", { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }, CTA_T + 0.18);
      tl.fromTo("#f-left", { opacity: 0, x: -60, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.24);
      tl.fromTo("#f-right", { opacity: 0, x: 60, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.24);
      tl.fromTo("#f-center", { opacity: 0, scale: 0.65 }, { opacity: 1, scale: 1, duration: 0.46, ease: "back.out(2)" }, CTA_T + 0.28);
      tl.fromTo(".floating-badge", { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, stagger: 0.1, duration: 0.35, ease: "back.out(2)" }, CTA_T + 0.42);
      tl.fromTo(".bottom-info", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, CTA_T + 0.4);
"""


# --- 1C. HOYAUP Cooler (Macro Hero 780px) ---
CSS_HOYAUP = """
      /* --- Macro Hero 780px: HOYAUP Cooler Standard --- */
      #b-cta {
        position: absolute; inset: 0; width: 1080px; height: 1920px;
        z-index: 20; pointer-events: none;
      }
      #cta-1 {
        position: absolute; top: 165px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Kanit Black", sans-serif;
        font-size: 86px; line-height: 1.15;
        color: #1b1a17;
      }
      #cta-1 .hl {
        padding: 0 16px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
      }
      #cta-model {
        position: absolute; top: 275px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Anuphan", sans-serif;
        font-weight: 700; font-size: 50px;
        color: #d90429;
      }
      #cta-stage {
        position: absolute; top: 350px; left: 0; width: 1080px; height: 910px;
        display: flex; justify-content: center; align-items: center;
        z-index: 10;
      }
      .cooler-img {
        width: 780px; height: 780px;
        object-fit: contain;
        filter: drop-shadow(0 24px 48px rgba(0,0,0,0.30));
        z-index: 10;
      }
      .contact-shadow {
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
        z-index: 5;
        pointer-events: none;
      }
      #cs-cooler {
        width: 640px; height: 110px;
        bottom: 75px; left: 50%;
        transform: translateX(-50%);
      }
      .floating-badge {
        position: absolute;
        z-index: 22;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 25px;
        background: #ffffff;
        color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 8px 18px;
        border-radius: 20px;
        box-shadow: 3px 5px 0 #1b1a17;
        white-space: nowrap;
      }
      .bottom-info {
        position: absolute; bottom: 270px; left: 40px; right: 40px;
        display: flex; flex-direction: column; align-items: center; gap: 14px;
        z-index: 25;
      }
      .swatch-card {
        background: #ffffff;
        border: 3px solid #1b1a17;
        border-radius: 18px;
        box-shadow: 3px 5px 0 #1b1a17;
        padding: 9px 26px;
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
      .spec-row {
        display: flex; flex-wrap: wrap; justify-content: center;
        max-width: 960px; gap: 10px; margin: 0 auto;
      }
      .spec-tag {
        font-family: "Anuphan", sans-serif;
        font-weight: 700; font-size: 26px;
        background: #ffffff; color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 6px 18px; border-radius: 12px;
        box-shadow: 3px 5px 0 #1b1a17;
      }
"""

HTML_HOYAUP = """
      <div class="beat clip" id="b-cta" data-start="{cta_start}" data-duration="{cta_dur}" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">HOYAUP · พัดลมแม่เหล็ก</span></div>
        <div class="t center" id="cta-model">ไอทีสายเกมตัวจบ · กดตะกร้าเหลือง</div>
        <div id="cta-stage">
          <div class="contact-shadow" id="cs-cooler"></div>
          <img class="cooler-img" src="assets/hoy01/img/hoyaup_clean_cutout.png">

          <div class="floating-badge" style="top: 100px; left: 60px; transform: rotate(-3deg);">
            จอดิจิทัลบอกอุณหภูมิจริง
          </div>
          <div class="floating-badge" style="top: 140px; right: 60px; transform: rotate(3deg);">
            แม่เหล็ก MagSafe ดูดแน่น
          </div>
          <div class="floating-badge" style="bottom: 120px; right: 70px; transform: rotate(-2deg);">
            ไฟ RGB Gaming สวยงาม
          </div>
          <div class="floating-badge" style="bottom: 120px; left: 70px; transform: rotate(2deg);">
            เย็นเร็วทันใจใน 3 วิ
          </div>
        </div>

        <div class="bottom-info">
          <div class="swatch-card">
            <span class="swatch-title">ลดความร้อนทันที เล่นเกมลื่น เฟรมเรตไม่ดรอป</span>
          </div>

          <div class="spec-row">
            <div class="spec-tag">ลดอุณหภูมิ 20°C</div>
            <div class="spec-tag">ชิปเซมิคอนดักเตอร์</div>
            <div class="spec-tag">น้ำหนักเบา 83g</div>
            <div class="spec-tag">เสียงเงียบกริบ 25dB</div>
          </div>
        </div>
      </div>
"""

GSAP_HOYAUP = """
      tl.fromTo("#b-chat", { opacity: 1 }, { opacity: 0, duration: 0.18, ease: "power2.in" }, CTA_T);
      tl.fromTo("#b-cta", { opacity: 0 }, { opacity: 1, duration: 0.24, ease: "power2.out" }, CTA_T);
      tl.fromTo("#cta-1", { opacity: 0, scale: 0.82, rotate: -3 }, { opacity: 1, scale: 1, rotate: 0, duration: 0.35, ease: "back.out(2.2)" }, CTA_T + 0.05);
      tl.fromTo("#cta-model", { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }, CTA_T + 0.18);
      tl.fromTo(".cooler-img", { opacity: 0, scale: 0.65 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.22);
      tl.fromTo("#cs-cooler", { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.45, ease: "power2.out" }, CTA_T + 0.22);
      tl.fromTo(".floating-badge", { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, stagger: 0.08, duration: 0.35, ease: "back.out(2)" }, CTA_T + 0.38);
      tl.fromTo(".bottom-info", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, CTA_T + 0.4);
"""


# --- 1D. Essager PD 30W (Macro Hero 730px 3D Perspective) ---
CSS_ESSAGER = """
      /* --- Macro Hero 730px: Essager PD 30W Standard --- */
      #b-cta {
        position: absolute; inset: 0; width: 1080px; height: 1920px;
        z-index: 20; pointer-events: none;
      }
      #cta-1 {
        position: absolute; top: 165px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Kanit Black", sans-serif;
        font-size: 86px; line-height: 1.15;
        color: #1b1a17;
      }
      #cta-1 .hl {
        padding: 0 16px;
        background: linear-gradient(transparent 52%, rgba(255, 230, 0, 0.94) 52%, rgba(255, 230, 0, 0.94) 92%, transparent 92%);
      }
      #cta-model {
        position: absolute; top: 275px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Anuphan", sans-serif;
        font-weight: 700; font-size: 50px;
        color: #d90429;
      }
      #cta-stage {
        position: absolute; top: 350px; left: 0; width: 1080px; height: 910px;
        display: flex; justify-content: center; align-items: center;
        z-index: 10;
      }
      .charger-img {
        width: 730px; height: 730px;
        object-fit: contain;
        filter: drop-shadow(0 22px 44px rgba(0,0,0,0.26));
        z-index: 10;
      }
      .contact-shadow {
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
        z-index: 5;
        pointer-events: none;
      }
      #cs-charger {
        width: 560px; height: 100px;
        bottom: 95px; left: 50%;
        transform: translateX(-50%);
      }
      .floating-badge {
        position: absolute;
        z-index: 22;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 25px;
        background: #ffffff;
        color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 8px 18px;
        border-radius: 20px;
        box-shadow: 3px 5px 0 #1b1a17;
        white-space: nowrap;
      }
      .bottom-info {
        position: absolute; bottom: 270px; left: 40px; right: 40px;
        display: flex; flex-direction: column; align-items: center; gap: 14px;
        z-index: 25;
      }
      .swatch-card {
        background: #ffffff;
        border: 3px solid #1b1a17;
        border-radius: 18px;
        box-shadow: 3px 5px 0 #1b1a17;
        padding: 10px 22px;
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
      .swatch-dots {
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .swatch-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: "Anuphan", sans-serif;
        font-weight: 700;
        font-size: 22px;
        color: #1b1a17;
      }
      .dot {
        width: 22px; height: 22px;
        border-radius: 50%;
        border: 2px solid #1b1a17;
        display: inline-block;
        box-shadow: 1px 2px 0 rgba(0,0,0,0.15);
      }
      .spec-row {
        display: flex; flex-wrap: wrap; justify-content: center;
        max-width: 960px; gap: 10px; margin: 0 auto;
      }
      .spec-tag {
        font-family: "Anuphan", sans-serif;
        font-weight: 700; font-size: 26px;
        background: #ffffff; color: #1b1a17;
        border: 3px solid #1b1a17;
        padding: 6px 18px; border-radius: 12px;
        box-shadow: 3px 5px 0 #1b1a17;
      }
"""

HTML_ESSAGER = """
      <div class="beat clip" id="b-cta" data-start="{cta_start}" data-duration="{cta_dur}" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">Essager · PD 30W</span></div>
        <div class="t center" id="cta-model">ชาร์จเร็วตัวจบ · กดตะกร้าเหลือง</div>
        <div id="cta-stage">
          <div class="contact-shadow" id="cs-charger"></div>
          <img class="charger-img" src="assets/ess02/img/essager_clean_cutout.png">

          <div class="floating-badge" style="top: 110px; left: 60px; transform: rotate(-3deg);">
            ชิปคุมความร้อนอัจฉริยะ
          </div>
          <div class="floating-badge" style="top: 180px; right: 60px; transform: rotate(3deg);">
            แบต 0-60% ใน 30 นาที
          </div>
          <div class="floating-badge" style="bottom: 140px; left: 70px; transform: rotate(2deg);">
            ขาพับเก็บได้ พกพาสะดวก
          </div>
          <div class="floating-badge" style="bottom: 140px; right: 70px; transform: rotate(-2deg);">
            ขนาดจิ๋ว น้ำหนักเบา
          </div>
        </div>

        <div class="bottom-info">
          <div class="swatch-card">
            <span class="swatch-title">มีให้เลือก 2 สีคลาสสิก :</span>
            <div class="swatch-dots">
              <div class="swatch-item"><span class="dot" style="background: #1a1a1a;"></span> ดำด้าน</div>
              <div class="swatch-item"><span class="dot" style="background: #ffffff;"></span> ขาวเซรามิก</div>
            </div>
          </div>

          <div class="spec-row">
            <div class="spec-tag">ชาร์จเร็ว PD 30W</div>
            <div class="spec-tag">เทคโนโลยีชิป GaN</div>
            <div class="spec-tag">ไม่ร้อน ปลอดภัย</div>
            <div class="spec-tag">ระบบเซฟตี้ 6 ชั้น</div>
          </div>
        </div>
      </div>
"""

GSAP_ESSAGER = """
      tl.fromTo("#b-chat", { opacity: 1 }, { opacity: 0, duration: 0.18, ease: "power2.in" }, CTA_T);
      tl.fromTo("#b-cta", { opacity: 0 }, { opacity: 1, duration: 0.24, ease: "power2.out" }, CTA_T);
      tl.fromTo("#cta-1", { opacity: 0, scale: 0.82, rotate: -3 }, { opacity: 1, scale: 1, rotate: 0, duration: 0.35, ease: "back.out(2.2)" }, CTA_T + 0.05);
      tl.fromTo("#cta-model", { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }, CTA_T + 0.18);
      tl.fromTo(".charger-img", { opacity: 0, scale: 0.65 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)" }, CTA_T + 0.22);
      tl.fromTo("#cs-charger", { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.45, ease: "power2.out" }, CTA_T + 0.22);
      tl.fromTo(".floating-badge", { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, stagger: 0.08, duration: 0.35, ease: "back.out(2)" }, CTA_T + 0.38);
      tl.fromTo(".bottom-info", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, CTA_T + 0.4);
"""


# ==============================================================================
# 2. Composition Transformer
# ==============================================================================

def transform_composition(comp_text: str, prod_key: str) -> str:
    """Inject updated CSS, HTML, and GSAP timeline for the given product."""
    if prod_key == "ors01":
        css_inject, html_tpl, gsap_inject = CSS_ORSEN, HTML_ORSEN, GSAP_ORSEN
    elif prod_key == "hat02":
        css_inject, html_tpl, gsap_inject = CSS_HATARI, HTML_HATARI, GSAP_HATARI
    elif prod_key == "hoy01":
        css_inject, html_tpl, gsap_inject = CSS_HOYAUP, HTML_HOYAUP, GSAP_HOYAUP
    elif prod_key == "ess02":
        css_inject, html_tpl, gsap_inject = CSS_ESSAGER, HTML_ESSAGER, GSAP_ESSAGER
    else:
        raise ValueError(f"Unknown product key: {prod_key}")

    # 1. Clean out any previous injected style or old CTA style
    # Insert new CSS before </style>
    style_end = comp_text.rfind("</style>")
    comp_text = comp_text[:style_end] + css_inject + comp_text[style_end:]

    # 2. Extract CTA timing
    m_cta = re.search(r'<div[^>]*id=["\']b-cta["\'][^>]*data-start=["\']([^"\']+)["\'][^>]*data-duration=["\']([^"\']+)["\']', comp_text)
    cta_start = m_cta.group(1) if m_cta else "52.0"
    cta_dur = m_cta.group(2) if m_cta else "6.0"

    # 3. Replace <div class="beat clip" id="b-cta" ... </div>
    b_cta_start = comp_text.find('id="b-cta"')
    # Walk backward to find the opening <div
    div_open = comp_text.rfind('<div', 0, b_cta_start)
    
    # Find end of b-cta before wm or audio
    wm_idx = comp_text.find('id="wm"', b_cta_start)
    if wm_idx == -1:
        wm_idx = comp_text.find('<audio', b_cta_start)
    
    div_close = comp_text.rfind('</div>', b_cta_start, wm_idx)
    
    new_html = html_tpl.format(cta_start=cta_start, cta_dur=cta_dur).strip()
    comp_text = comp_text[:div_open] + new_html + "\n      " + comp_text[div_close+6:]

    # 4. Replace GSAP animation for CTA
    gsap_start = comp_text.find('tl.fromTo("#b-chat"')
    if gsap_start != -1:
        gsap_end = comp_text.find('if (window.__timelines)', gsap_start)
        if gsap_end != -1:
            comp_text = comp_text[:gsap_start] + gsap_inject.strip() + "\n\n      " + comp_text[gsap_end:]

    return comp_text


# ==============================================================================
# 3. Helpers: Covers, Registry & Bindings
# ==============================================================================

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_cta_seek_time(comp_path: Path) -> float:
    txt = comp_path.read_text(encoding="utf-8")
    m_dur = re.search(r'data-duration=["\']([\d\.]+)["\']', txt)
    dur = float(m_dur.group(1)) if m_dur else 60.0
    m_cta = re.search(r'const\s+CTA_T\s*=\s*([\d\.]+);', txt)
    if not m_cta:
        m_cta = re.search(r'id=["\']b-cta["\'][^>]*data-start=["\']([\d\.]+)["\']', txt)
    cta_start = float(m_cta.group(1)) if m_cta else dur - 6.0
    seek_time = min(cta_start + 1.8, dur - 0.5)
    return max(0.5, seek_time)


def extract_covers(mp4_path: Path, stem: str, seek_sec: float, date_str: str) -> dict:
    webp_path = EXPORTS_DIR / f"{date_str}_{stem}_v1.webp"
    cover_916 = COVERS_DIR / f"{date_str}_{stem}_v1_cover.jpg"
    cover_34 = COVERS_DIR / f"{date_str}_{stem}_v1_cover_3x4.jpg"

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    # 1. 540x960 WebP
    subprocess.run([
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "scale=540:960",
        "-c:v", "libwebp", "-quality", "88",
        str(webp_path)
    ], check=False)

    # 2. 1080x1920 JPG (9:16)
    subprocess.run([
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "scale=1080:1920",
        "-q:v", "2",
        str(cover_916)
    ], check=False)

    # 3. 1080x1440 JPG (3:4 TikTok Profile Center-Crop)
    subprocess.run([
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "crop=1080:1440:0:240",
        "-q:v", "2",
        str(cover_34)
    ], check=False)

    return {
        "webp": webp_path if webp_path.exists() else None,
        "9:16": cover_916 if cover_916.exists() else None,
        "3:4": cover_34 if cover_34.exists() else None,
    }


def register_export_and_cover(mp4_path: Path, covers: dict, comp_stem: str, angle_idx: int, prod_cfg: dict) -> str:
    with REGISTRY_LOCK:
        registry_file = DOCS_DIR / "export_registry.json"
        bindings_file = DOCS_DIR / "export_cover_bindings.json"

        entries = []
        if registry_file.exists():
            try:
                entries = json.loads(registry_file.read_text(encoding="utf-8"))
            except Exception:
                entries = []

        rel_mp4 = f"04_Exports/Ready_to_post/{mp4_path.name}"
        angle_id = f"ang_{prod_cfg['code'].lower()}_{angle_idx:02d}"

        try:
            products_file = DOCS_DIR / "products.json"
            if products_file.exists():
                prods = json.loads(products_file.read_text(encoding="utf-8"))
                p_found = next((p for p in prods if p.get("id") == prod_cfg["product_id"] or p.get("product_code") == prod_cfg["code"]), None)
                if p_found:
                    a_found = next((a for a in p_found.get("angles", []) if a.get("clip_id") == comp_stem or a.get("angle_id") == angle_id), None)
                    if a_found and a_found.get("angle_id"):
                        angle_id = a_found.get("angle_id")
        except Exception:
            pass

        existing = next((e for e in entries if e.get("path") == rel_mp4 or e.get("path_key") == rel_mp4 or comp_stem in e.get("path", "") or e.get("project_name") == f"_HyperFrames_Studio/{comp_stem}"), None)
        now_iso = datetime.datetime.now().isoformat()
        now_ts = time.time()

        if existing:
            export_id = existing.get("id")
            old_path_str = existing.get("path")
            if old_path_str and old_path_str != rel_mp4:
                old_file = ROOT / old_path_str
                if old_file.exists():
                    old_file.unlink(missing_ok=True)
                old_webp = old_file.with_suffix(".webp")
                if old_webp.exists():
                    old_webp.unlink(missing_ok=True)
            existing["path"] = rel_mp4
            existing["path_key"] = rel_mp4
            existing["product_id"] = prod_cfg["product_id"]
            existing["angle_id"] = angle_id
            existing["status"] = "rendered"
            existing["updated_at"] = now_iso
        else:
            export_id = f"exp_{uuid.uuid4().hex}"
            entry = {
                "id": export_id,
                "channel_id": "main",
                "path": rel_mp4,
                "path_key": rel_mp4,
                "product_id": prod_cfg["product_id"],
                "angle_id": angle_id,
                "project_name": f"_HyperFrames_Studio/{comp_stem}",
                "status": "rendered",
                "created_at": now_iso,
                "updated_at": now_iso,
                "posted_at": None,
            }
            entries.append(entry)

        registry_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

        # Cover bindings
        p_916 = covers.get("9:16")
        p_34 = covers.get("3:4")
        if p_916 and p_916.exists() and p_34 and p_34.exists():
            rel_916 = f"05_Covers_Thumbnails/{p_916.name}"
            rel_34 = f"05_Covers_Thumbnails/{p_34.name}"
            sha_916 = compute_sha256(p_916)
            sha_34 = compute_sha256(p_34)

            bindings = []
            if bindings_file.exists():
                try:
                    bindings = json.loads(bindings_file.read_text(encoding="utf-8"))
                except Exception:
                    bindings = []

            b_entry = next((b for b in bindings if b.get("export_id") == export_id), None)
            if not b_entry:
                b_entry = {
                    "channel_id": "main",
                    "export_id": export_id,
                    "video_path": rel_mp4,
                    "selections": {
                        "9:16": {"path": rel_916, "sha256": sha_916, "format": "9:16"},
                        "3:4": {"path": rel_34, "sha256": sha_34, "format": "3:4"}
                    },
                    "revision": 1,
                    "updated_at": now_ts,
                }
                bindings.append(b_entry)
            else:
                b_entry["video_path"] = rel_mp4
                b_entry["selections"]["9:16"] = {"path": rel_916, "sha256": sha_916, "format": "9:16"}
                b_entry["selections"]["3:4"] = {"path": rel_34, "sha256": sha_34, "format": "3:4"}
                b_entry["updated_at"] = now_ts

            bindings_file.write_text(json.dumps(bindings, ensure_ascii=False, indent=2), encoding="utf-8")

        return export_id


# ==============================================================================
# 4. Render Pipeline
# ==============================================================================

def process_single_clip(prod_key: str, idx: int, date_str: str, force: bool = False, covers_only: bool = False) -> bool:
    prod_cfg = PRODUCTS[prod_key]
    stem = f"{prod_cfg['slug']}-s{idx:02d}"
    comp_name = f"{stem}.html"

    # 1. Locate composition in archive or compositions dir
    src_comp = ARCHIVE_COMPS / comp_name
    if not src_comp.exists():
        src_comp = COMPS_DIR / comp_name
    if not src_comp.exists():
        print(f"[{prod_cfg['code']} {idx:02d}/20] Missing composition: {comp_name}, skipping.")
        return False

    # 2. Read and transform composition
    orig_text = src_comp.read_text(encoding="utf-8")
    updated_text = transform_composition(orig_text, prod_key)

    # Save to active compositions dir and update archive
    active_comp = COMPS_DIR / comp_name
    active_comp.write_text(updated_text, encoding="utf-8")
    (ARCHIVE_COMPS / comp_name).write_text(updated_text, encoding="utf-8")

    out_mp4 = EXPORTS_DIR / f"{date_str}_{stem}_v1.mp4"
    temp_raw = TMP_DIR / f"raw_{date_str}_{stem}.mp4"
    seek_sec = get_cta_seek_time(active_comp)

    # If covers only:
    if covers_only:
        if out_mp4.exists():
            covers = extract_covers(out_mp4, stem, seek_sec, date_str)
            register_export_and_cover(out_mp4, covers, stem, idx, prod_cfg)
            print(f"[{prod_cfg['code']} {idx:02d}/20] Covers refreshed: {stem}")
            active_comp.unlink(missing_ok=True)
            return True
        else:
            print(f"[{prod_cfg['code']} {idx:02d}/20] Cannot extract covers, MP4 missing: {out_mp4.name}")
            active_comp.unlink(missing_ok=True)
            return False

    if out_mp4.exists() and out_mp4.stat().st_size > 1024 * 1024:
        age_hours = (time.time() - out_mp4.stat().st_mtime) / 3600.0
        if age_hours < 24.0 and is_valid_mp4(out_mp4):
            print(f"[{prod_cfg['code']} {idx:02d}/20] MP4 freshly rendered ({age_hours:.1f}h ago): {out_mp4.name}, skipping re-render.", flush=True)
            covers = extract_covers(out_mp4, stem, seek_sec, date_str)
            register_export_and_cover(out_mp4, covers, stem, idx, prod_cfg)
            active_comp.unlink(missing_ok=True)
            return True
        elif not force:
            print(f"[{prod_cfg['code']} {idx:02d}/20] MP4 already exists: {out_mp4.name} ({round(out_mp4.stat().st_size/1024/1024, 2)} MB)", flush=True)
            covers = extract_covers(out_mp4, stem, seek_sec, date_str)
            register_export_and_cover(out_mp4, covers, stem, idx, prod_cfg)
            active_comp.unlink(missing_ok=True)
            return True

    print(f"\n[{prod_cfg['code']} {idx:02d}/20] 🎥 Rendering {stem}.html ... (CTA seek: {seek_sec:.2f}s)")
    t0 = time.time()

    # Step A: Render raw with hyperframes
    cmd = [
        "npx.cmd", "--yes", "hyperframes@0.8.149", "render", ".",
        "-c", f"compositions/{comp_name}",
        "-o", str(temp_raw)
    ]
    res = subprocess.run(cmd, cwd=str(STUDIO), capture_output=True, text=True, check=False)
    if res.returncode != 0 or not temp_raw.exists() or temp_raw.stat().st_size == 0:
        print(f"   ❌ [RENDER FAILED] {comp_name}: {res.stderr[:250]}")
        active_comp.unlink(missing_ok=True)
        return False

    # Step B: TikTok Pro Sharpness Enhancement
    b_val = prod_cfg["brightness"]
    print(f"   ⚡ Enhancing with TikTok Pro Sharpness Engine (brightness={b_val}, unsharp, BT.709) ...")
    try:
        enhance_video_for_tiktok(temp_raw, output_path=out_mp4, brightness=b_val)
        temp_raw.unlink(missing_ok=True)
    except Exception as e:
        print(f"   ⚠️ Enhancer error ({e}), keeping raw MP4.")
        shutil.move(str(temp_raw), str(out_mp4))

    total_dur = round(time.time() - t0, 1)
    size_mb = round(out_mp4.stat().st_size / (1024 * 1024), 2)
    print(f"   ✅ [SUCCESS] {out_mp4.name} ({size_mb} MB in {total_dur}s)")

    # Step C: Extract covers & register
    covers = extract_covers(out_mp4, stem, seek_sec, date_str)
    register_export_and_cover(out_mp4, covers, stem, idx, prod_cfg)

    # Step D: Archive composition back to keep studio clean
    active_comp.unlink(missing_ok=True)
    return True


def sync_all_products_json(date_str: str):
    with REGISTRY_LOCK:
        products_file = DOCS_DIR / "products.json"
        if not products_file.exists():
            return
        prods = json.loads(products_file.read_text(encoding="utf-8"))

        for p_key, p_cfg in PRODUCTS.items():
            p_target = next((p for p in prods if p.get("id") == p_cfg["product_id"] or p.get("product_code") == p_cfg["code"]), None)
            if not p_target:
                continue
            for a in p_target.get("angles", []):
                cid = a.get("clip_id")
                if cid and p_cfg["slug"] in cid:
                    a["status"] = "rendered"
                    mp4_name = f"{date_str}_{cid}_v1.mp4"
                    mp4_path = EXPORTS_DIR / mp4_name
                    if mp4_path.exists():
                        a["video_url"] = f"04_Exports/Ready_to_post/{mp4_name}"
                    webp_name = f"{date_str}_{cid}_v1.webp"
                    webp_path = EXPORTS_DIR / webp_name
                    if webp_path.exists():
                        a["cover_url"] = f"04_Exports/Ready_to_post/{webp_name}"

        products_file.write_text(json.dumps(prods, ensure_ascii=False, indent=2), encoding="utf-8")
        print("-> Synced all 4 products in _Docs/products.json to status='rendered'", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Master Batch Upgrade for 80 HyperFrames CTA Outros & Covers")
    parser.add_argument("--product", type=str, default="all", choices=["all", "ors01", "hat02", "hoy01", "ess02"], help="Product to process")
    parser.add_argument("--start", type=int, default=1, help="Start index (1-20)")
    parser.add_argument("--end", type=int, default=20, help="End index (1-20)")
    parser.add_argument("--force", action="store_true", help="Force re-render")
    parser.add_argument("--covers-only", action="store_true", help="Only extract and bind high-res covers")
    parser.add_argument("--concurrency", type=int, default=4, help="Number of concurrent render workers (default: 4)")
    args = parser.parse_args()

    date_str = datetime.datetime.now().strftime("%Y%m%d")

    target_products = ["ors01", "hat02", "hoy01", "ess02"] if args.product == "all" else [args.product]
    
    total_count = len(target_products) * (args.end - args.start + 1)
    print(f"=================================================================", flush=True)
    print(f"🚀 Master Batch Upgrade: {len(target_products)} Products, {total_count} Clips Total", flush=True)
    print(f"   Products: {', '.join([PRODUCTS[p]['code'] for p in target_products])}", flush=True)
    print(f"   Range: s{args.start:02d} to s{args.end:02d}", flush=True)
    print(f"   Force re-render: {args.force} | Covers only: {args.covers_only}", flush=True)
    print(f"   ⚡ Concurrency: {args.concurrency} parallel workers", flush=True)
    print(f"=================================================================\n", flush=True)

    t_start = time.time()
    success_count = 0

    tasks = []
    for p_key in target_products:
        for idx in range(args.start, args.end + 1):
            tasks.append((p_key, idx, date_str, args.force, args.covers_only))

    if args.concurrency > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            future_to_task = {
                executor.submit(process_single_clip, p_key, idx, d_str, f, cov_only): (p_key, idx)
                for (p_key, idx, d_str, f, cov_only) in tasks
            }
            for future in concurrent.futures.as_completed(future_to_task):
                p_key, idx = future_to_task[future]
                try:
                    ok = future.result()
                    if ok:
                        success_count += 1
                except Exception as exc:
                    print(f"[{PRODUCTS[p_key]['code']} {idx:02d}/20] Worker exception: {exc}", flush=True)
    else:
        for (p_key, idx, d_str, f, cov_only) in tasks:
            ok = process_single_clip(p_key, idx, d_str, force=f, covers_only=cov_only)
            if ok:
                success_count += 1

    sync_all_products_json(date_str)
    
    elapsed = round(time.time() - t_start, 1)
    print(f"\n=================================================================", flush=True)
    print(f"🎉 Batch Finished: {success_count}/{total_count} succeeded in {elapsed}s", flush=True)
    print(f"=================================================================", flush=True)

if __name__ == "__main__":
    main()
