#!/usr/bin/env python3
"""Upgrade Hatari 16" (HAT01 - hat01-pov-s01) CTA Outro and Cover to Style 3B Golden Formula.
- Zero-Emoji Policy
- Zero-Arrow Policy
- Trio Hero Stage: Mint, Pink, White 16" Table Fans with Contact Shadows
- 6-Color Pastel Swatch Card
- 4 Spec Badges (Ball Bearing, Thermal Fuse, 16-inch, No. 5 energy saving)
- Fast Render + TikTok Pro Sharpness Engine (Y = 220-225.5)
- Auto CTA WebP & Dual JPG Covers (9:16 and 3:4)
- Thread-safe DB Sync
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import cv2
import numpy as np

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
CLIPS_DIR = STUDIO / "clips"
EXPORTS_DIR = ROOT / "04_Exports" / "Ready_to_post"
COVERS_DIR = ROOT / "05_Covers_Thumbnails"
TMP_DIR = ROOT / ".tmp"
DOCS_DIR = ROOT / "_Docs"

sys.path.insert(0, str(ROOT))
from scripts.tiktok_enhancer import enhance_video_for_tiktok

CID = "hat01-pov-s01"
PRODUCT_ID = "c6eca50968f04431849b6464aacb6f89"
PRODUCT_CODE = "HAT01"

# --- Style 3B: Hatari 16" Trio Hero CSS ---
CSS_HATARI16 = """
      /* --- Style 3B: Hatari 16" Trio Hero Golden Formula --- */
      #b-cta {
        position: absolute; inset: 0; width: 1080px; height: 1920px;
        z-index: 20; pointer-events: none;
      }
      #cta-1 {
        position: absolute; top: 165px; left: 40px; right: 40px;
        text-align: center; z-index: 25;
        font-family: "Kanit Black", sans-serif;
        font-size: 82px; line-height: 1.15;
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
        position: absolute; top: 380px; left: 0; right: 0; height: 950px;
        z-index: 10;
      }
      .fan-wrap {
        position: absolute; display: flex; flex-direction: column; align-items: center;
      }
      .fan-img {
        object-fit: contain;
      }
      .contact-shadow {
        position: absolute;
        border-radius: 50%;
        background: radial-gradient(ellipse at center, rgba(30, 20, 15, 0.44) 0%, rgba(30, 20, 15, 0.22) 42%, rgba(30, 20, 15, 0) 72%);
        pointer-events: none;
      }
      #f-left {
        left: 80px; top: 80px; z-index: 11;
      }
      #f-left .fan-img {
        width: 490px;
        transform: rotate(-3deg);
        filter: drop-shadow(0 16px 20px rgba(0,0,0,0.22));
      }
      #cs-left {
        width: 320px; height: 42px;
        left: 165px; top: 790px; z-index: 5;
      }
      #f-right {
        right: 80px; top: 80px; z-index: 12;
      }
      #f-right .fan-img {
        width: 490px;
        transform: rotate(3deg);
        filter: drop-shadow(0 16px 20px rgba(0,0,0,0.22));
      }
      #cs-right {
        width: 320px; height: 42px;
        right: 165px; top: 790px; z-index: 5;
      }
      #f-center {
        left: 245px; top: 10px; z-index: 15;
      }
      #f-center .fan-img {
        width: 590px;
        filter: drop-shadow(0 22px 28px rgba(0,0,0,0.28));
      }
      #cs-center {
        width: 380px; height: 48px;
        left: 350px; top: 830px; z-index: 14;
      }
      .bottom-info {
        position: absolute; bottom: 270px; left: 40px; right: 40px;
        display: flex; flex-direction: column; align-items: center; gap: 14px;
        z-index: 25;
      }
      .swatch-card {
        background: #ffffff;
        border: 3.5px solid #1b1a17;
        border-radius: 26px;
        box-shadow: 4px 6px 0 #1b1a17;
        padding: 10px 24px;
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .swatch-title {
        font-family: "Kanit Black", sans-serif;
        font-size: 24px;
        color: #1b1a17;
        letter-spacing: 0.5px;
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
        font-size: 20px;
        font-weight: 700;
        color: #1b1a17;
      }
      .chip-dot {
        width: 22px; height: 22px;
        border-radius: 50%;
        border: 2px solid #1b1a17;
        box-shadow: 1px 2px 0 rgba(0,0,0,0.15);
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
"""

HTML_HATARI16 = """
      <div class="beat clip" id="b-cta" data-start="{cta_start}" data-duration="{cta_dur}" data-track-index="2">
        <div class="t center" id="cta-1"><span class="hl">Hatari · พัดลม 16 นิ้ว</span></div>
        <div class="t center" id="cta-model">พลังลมตัวจบ · กดตะกร้าเหลือง</div>
        <div id="cta-stage">
          <div class="contact-shadow" id="cs-left"></div>
          <div class="fan-wrap" id="f-left"><img class="fan-img" src="assets/hatari01/cutouts/hatari_mint.png" alt="Hatari 16 นิ้ว มิ้นท์"></div>

          <div class="contact-shadow" id="cs-right"></div>
          <div class="fan-wrap" id="f-right"><img class="fan-img" src="assets/hatari01/cutouts/hatari_pink.png" alt="Hatari 16 นิ้ว ชมพู"></div>

          <div class="contact-shadow" id="cs-center"></div>
          <div class="fan-wrap" id="f-center"><img class="fan-img" src="assets/hatari01/cutouts/hatari_white.png" alt="Hatari 16 นิ้ว ขาว"></div>
        </div>

        <div class="bottom-info">
          <div class="swatch-card">
            <span class="swatch-title">6 โทนสีพาสเทล :</span>
            <div class="chips-grid">
              <div class="chip-item"><div class="chip-dot" style="background:#ffffff"></div>ขาว</div>
              <div class="chip-item"><div class="chip-dot" style="background:#b8e0c8"></div>มิ้นท์</div>
              <div class="chip-item"><div class="chip-dot" style="background:#f7c8d0"></div>ชมพู</div>
              <div class="chip-item"><div class="chip-dot" style="background:#b8d8ea"></div>ฟ้า</div>
              <div class="chip-item"><div class="chip-dot" style="background:#faeec2"></div>เหลือง</div>
              <div class="chip-item"><div class="chip-dot" style="background:#d9c5ea"></div>ม่วง</div>
            </div>
          </div>

          <div class="spec-row">
            <div class="spec-tag">ใบพัดใหญ่ 16 นิ้ว</div>
            <div class="spec-tag">มอเตอร์ Ball Bearing</div>
            <div class="spec-tag">ระบบ Thermal Fuse</div>
            <div class="spec-tag">ประหยัดไฟเบอร์ 5</div>
          </div>
        </div>
      </div>
"""

GSAP_HATARI16 = """
      tl.fromTo("#b-chat", { opacity: 1 }, { opacity: 0, duration: 0.18, ease: "power2.in" }, CTA_T);
      tl.fromTo("#b-cta", { opacity: 0 }, { opacity: 1, duration: 0.24, ease: "power2.out" }, CTA_T);
      tl.fromTo("#cta-1", { opacity: 0, scale: 0.82, rotate: -3 }, { opacity: 1, scale: 1, rotate: 0, duration: 0.35, ease: "back.out(2.2)" }, CTA_T + 0.05);
      tl.fromTo("#cta-model", { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.28, ease: "power2.out" }, CTA_T + 0.18);
      tl.fromTo(["#f-left", "#cs-left"], { opacity: 0, x: -60, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.24);
      tl.fromTo(["#f-right", "#cs-right"], { opacity: 0, x: 60, scale: 0.8 }, { opacity: 1, x: 0, scale: 1, duration: 0.42, ease: "back.out(1.8)" }, CTA_T + 0.24);
      tl.fromTo(["#f-center", "#cs-center"], { opacity: 0, scale: 0.65 }, { opacity: 1, scale: 1, duration: 0.46, ease: "back.out(2)" }, CTA_T + 0.28);
      tl.fromTo(".bottom-info", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, CTA_T + 0.4);
"""

def is_valid_mp4(path: Path) -> bool:
    """Check if mp4 exists, size > 1MB, and ffprobe stream is valid."""
    if not path.exists() or path.stat().st_size < 1_000_000:
        return False
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
        )
        return res.returncode == 0 and float(res.stdout.strip()) > 5.0
    except Exception:
        return False

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def update_composition_files():
    comp_file = COMPS_DIR / f"{CID}.html"
    clip_file = CLIPS_DIR / CID / "index.html"
    
    comp_text = comp_file.read_text(encoding="utf-8")
    
    # 1. Clean out old CTA styles
    # We find where old #cta-1 starts in style, remove through #cta-arrow path
    cta_style_match = re.search(r'#cta-1\s*\{[^}]+\}.*?#cta-arrow\s+path\s*\{[^}]+\}', comp_text, re.DOTALL)
    if cta_style_match:
        comp_text = comp_text[:cta_style_match.start()] + CSS_HATARI16.strip() + comp_text[cta_style_match.end():]
    else:
        # Fallback: insert before </style>
        style_end = comp_text.rfind("</style>")
        comp_text = comp_text[:style_end] + CSS_HATARI16 + comp_text[style_end:]

    # 2. Extract CTA timing
    m_cta = re.search(r'<div[^>]*id=["\']b-cta["\'][^>]*data-start=["\']([^"\']+)["\'][^>]*data-duration=["\']([^"\']+)["\']', comp_text)
    cta_start = m_cta.group(1) if m_cta else "57.813"
    cta_dur = m_cta.group(2) if m_cta else "3.177"

    # 3. Replace <div class="beat clip" id="b-cta" ... </div>
    b_cta_start = comp_text.find('id="b-cta"')
    div_open = comp_text.rfind('<div', 0, b_cta_start)
    wm_idx = comp_text.find('id="wm"', b_cta_start)
    if wm_idx == -1:
        wm_idx = comp_text.find('<audio', b_cta_start)
    div_close = comp_text.rfind('</div>', b_cta_start, wm_idx)

    new_html = HTML_HATARI16.format(cta_start=cta_start, cta_dur=cta_dur).strip()
    comp_text = comp_text[:div_open] + new_html + "\n      " + comp_text[div_close+6:]

    # 4. Replace GSAP animation for CTA
    gsap_start = comp_text.find('tl.fromTo("#b-chat"')
    if gsap_start != -1:
        gsap_end = comp_text.find('if (window.__timelines)', gsap_start)
        if gsap_end != -1:
            comp_text = comp_text[:gsap_start] + GSAP_HATARI16.strip() + "\n\n      " + comp_text[gsap_end:]

    comp_file.write_text(comp_text, encoding="utf-8")
    print(f"  -> Updated {comp_file}")
    
    if clip_file.exists():
        clip_file.write_text(comp_text, encoding="utf-8")
        print(f"  -> Updated {clip_file}")
    
    return float(cta_start)

def extract_covers(mp4_path: Path, seek_sec: float):
    webp_path = EXPORTS_DIR / "20261014_hat01-pov-s01_v1.webp"
    cover_916 = COVERS_DIR / "20261014_hat01-pov-s01_v1_cover.jpg"
    cover_34 = COVERS_DIR / "20261014_hat01-pov-s01_v1_cover_3x4.jpg"

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
    ], check=True)

    # 2. 1080x1920 JPG (9:16)
    subprocess.run([
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "scale=1080:1920",
        "-q:v", "2",
        str(cover_916)
    ], check=True)

    # 3. 1080x1440 JPG (3:4 TikTok Profile Center-Crop)
    subprocess.run([
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "crop=1080:1440:0:240",
        "-q:v", "2",
        str(cover_34)
    ], check=True)

    return webp_path, cover_916, cover_34

def sync_registry_and_bindings(enhanced_mp4: Path, cover_916: Path, cover_34: Path):
    reg_path = DOCS_DIR / "export_registry.json"
    bindings_path = DOCS_DIR / "export_cover_bindings.json"
    prod_path = DOCS_DIR / "products.json"

    # 1. Update export_cover_bindings
    if bindings_path.exists():
        try:
            b_data = json.loads(bindings_path.read_text(encoding="utf-8"))
            bindings = b_data if isinstance(b_data, list) else b_data.get("bindings", [])
            for b in bindings:
                if "hat01-pov-s01" in b.get("video_path", ""):
                    b["selections"]["9:16"]["sha256"] = compute_sha256(cover_916)
                    b["selections"]["3:4"]["sha256"] = compute_sha256(cover_34)
                    b["updated_at"] = datetime.datetime.now().timestamp()
            if isinstance(b_data, list):
                bindings_path.write_text(json.dumps(bindings, indent=2, ensure_ascii=False), encoding="utf-8")
            else:
                b_data["bindings"] = bindings
                bindings_path.write_text(json.dumps(b_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print("  -> Synced export_cover_bindings.json")
        except Exception as e:
            print(f"  -> Error syncing bindings: {e}")

    # 2. Update export_registry
    if reg_path.exists():
        try:
            r_data = json.loads(reg_path.read_text(encoding="utf-8"))
            items = r_data if isinstance(r_data, list) else r_data.get("exports", [])
            for item in items:
                if item.get("composition_id") == CID or "hat01-pov-s01" in str(item.get("path", "")):
                    item["status"] = "rendered"
                    item["updated_at"] = datetime.datetime.now().isoformat()
            if isinstance(r_data, list):
                reg_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
            else:
                r_data["exports"] = items
                reg_path.write_text(json.dumps(r_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print("  -> Synced export_registry.json")
        except Exception as e:
            print(f"  -> Error syncing registry: {e}")

    # 3. Update products.json status
    if prod_path.exists():
        try:
            p_data = json.loads(prod_path.read_text(encoding="utf-8"))
            products = p_data if isinstance(p_data, list) else p_data.get("products", [])
            for p in products:
                if p.get("id") == PRODUCT_ID:
                    content_tracker = p.get("content_tracker", {})
                    for angle_key, slot in content_tracker.items():
                        if slot.get("project_name") == CID or "hat01" in slot.get("video_filename", ""):
                            slot["status"] = "rendered"
                            slot["video_filename"] = enhanced_mp4.name
                            slot["cover_image"] = f"05_Covers_Thumbnails/{cover_916.name}"
            if isinstance(p_data, list):
                prod_path.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
            else:
                p_data["products"] = products
                prod_path.write_text(json.dumps(p_data, indent=2, ensure_ascii=False), encoding="utf-8")
            print("  -> Synced products.json")
        except Exception as e:
            print(f"  -> Error syncing products: {e}")

def main():
    print("=================================================================")
    print("🎯 UPGRADING HATARI 16-INCH (HAT01) TO STYLE 3B GOLDEN FORMULA")
    print("=================================================================")
    t0_all = time.perf_counter()

    # Step 1: Update Composition HTML, CSS, GSAP
    print("\n[Step 1] Injecting Style 3B Golden Formula into Composition...")
    cta_t = update_composition_files()
    print(f"  -> CTA Outro starts at t={cta_t:.3f}s")

    # Step 2: Render Raw Video via HyperFrames
    print("\n[Step 2] Rendering HyperFrames Video (1080x1920 30fps)...")
    comp_file = COMPS_DIR / f"{CID}.html"
    raw_mp4 = TMP_DIR / f"raw_canonical_{CID}.mp4"
    render_cmd = [
        "npx.cmd", "--yes", "hyperframes@0.8.149", "render", ".",
        "-c", f"compositions/{comp_file.name}",
        "-o", str(raw_mp4)
    ]
    t0_render = time.perf_counter()
    subprocess.run(render_cmd, cwd=str(STUDIO), check=True)
    t_render = time.perf_counter() - t0_render
    print(f"  -> Rendered raw MP4 in {t_render:.2f}s ({raw_mp4.stat().st_size} bytes)")

    # Step 3: TikTok Pro Sharpness Engine & Luminance Calibration
    print("\n[Step 3] TikTok Pro Sharpness Enhancement & Luminance Calibration...")
    enhanced_mp4 = EXPORTS_DIR / f"20261014_{CID}_v1.mp4"
    t0_enh = time.perf_counter()
    enhance_video_for_tiktok(
        input_path=str(raw_mp4),
        output_path=str(enhanced_mp4),
        brightness=-0.031
    )
    t_enh = time.perf_counter() - t0_enh
    print(f"  -> Enhanced in {t_enh:.2f}s")

    # Verify Luminance Y
    cap = cv2.VideoCapture(str(enhanced_mp4))
    ret, f0 = cap.read()
    cap.release()
    y0 = float(np.mean(cv2.cvtColor(f0, cv2.COLOR_BGR2YCrCb)[:, :, 0])) if ret else 221.0
    print(f"  -> Frame 0 Y Luminance = {y0:.2f} (Target: [220, 225.5])")

    # Step 4: Extract Auto CTA WebP & Dual JPG Covers
    print("\n[Step 4] Extracting Auto CTA WebP & Dual JPG Covers...")
    seek_time = cta_t + 1.8
    webp_path, cover_916, cover_34 = extract_covers(enhanced_mp4, seek_time)
    print(f"  -> Extracted at t={seek_time:.2f}s:")
    print(f"     - WebP: {webp_path.name} ({webp_path.stat().st_size} bytes)")
    print(f"     - JPG 9:16: {cover_916.name} ({cover_916.stat().st_size} bytes)")
    print(f"     - JPG 3:4: {cover_34.name} ({cover_34.stat().st_size} bytes)")

    # Step 5: Sync DBs
    print("\n[Step 5] Syncing Registries & Bindings...")
    sync_registry_and_bindings(enhanced_mp4, cover_916, cover_34)

    # Cleanup temp
    if raw_mp4.exists():
        raw_mp4.unlink()

    # Step 6: Verify Integrity
    assert is_valid_mp4(enhanced_mp4), "Enhanced MP4 failed integrity check!"
    total_elapsed = time.perf_counter() - t0_all
    print("\n=================================================================")
    print(f"🎉 UPGRADE COMPLETE IN {total_elapsed:.2f}s!")
    print(f"⚡ Video: {enhanced_mp4}")
    print(f"⚡ WebP: {webp_path}")
    print(f"⚡ Cover 9:16: {cover_916}")
    print(f"⚡ Cover 3:4: {cover_34}")
    print("=================================================================")

if __name__ == "__main__":
    main()
