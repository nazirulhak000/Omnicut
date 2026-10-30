#!/usr/bin/env python3
"""Batch render and TikTok-enhance all 20 HOYAUP compositions to 04_Exports/Ready_to_post/.

Pipeline:
  1. Render compositions/hoy01-pov-s01..s20.html -> .tmp/raw_hoy01-pov-sXX.mp4
  2. Enhance via TikTok Pro Sharpness Engine (scripts/tiktok_enhancer.py with brightness=+0.02)
     -> 04_Exports/Ready_to_post/20261013_hoy01-pov-sXX_v1.mp4
  3. Extract WebP & Dual JPG covers (9:16 and 3:4 TikTok Profile crop) from Brand-First CTA shot
  4. Register into _Docs/export_registry.json and _Docs/export_cover_bindings.json
  5. Sync status = 'rendered' in _Docs/products.json
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

# UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "03_Projects" / "_HyperFrames_Studio"
COMPS_DIR = STUDIO / "compositions"
EXPORTS_DIR = ROOT / "04_Exports" / "Ready_to_post"
COVERS_DIR = ROOT / "05_Covers_Thumbnails"
TMP_DIR = ROOT / ".tmp"
DOCS_DIR = ROOT / "_Docs"

EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

PRODUCT_ID = "673882d55bd84c57ba805000a910c466"
DATE_STR = datetime.datetime.now().strftime("%Y%m%d")

sys.path.insert(0, str(ROOT))
from scripts.tiktok_enhancer import enhance_video_for_tiktok


def get_cta_seek_time(comp_path: Path) -> float:
    """Find the best thumbnail seek time (CTA frame fully animated)."""
    txt = comp_path.read_text(encoding="utf-8")
    m_dur = re.search(r'data-duration=["\']([\d\.]+)["\']', txt)
    dur = float(m_dur.group(1)) if m_dur else 60.0
    m_cta = re.search(r'const\s+CTA_T\s*=\s*([\d\.]+);', txt)
    if not m_cta:
        m_cta = re.search(r'id=["\']b-cta["\'][^>]*data-start=["\']([\d\.]+)["\']', txt)
    cta_start = float(m_cta.group(1)) if m_cta else dur - 6.0
    seek_time = min(cta_start + 1.8, dur - 0.5)
    return max(0.5, seek_time)


def extract_covers(mp4_path: Path, stem: str, seek_sec: float) -> dict:
    """Extract WebP (for gallery), 9:16 JPG cover, and 3:4 profile crop JPG."""
    webp_path = EXPORTS_DIR / f"{DATE_STR}_{stem}_v1.webp"
    cover_916 = COVERS_DIR / f"{DATE_STR}_{stem}_v1_cover.jpg"
    cover_34 = COVERS_DIR / f"{DATE_STR}_{stem}_v1_cover_3x4.jpg"

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    # 1. 540x960 WebP
    cmd_webp = [
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "scale=540:960",
        "-c:v", "libwebp", "-quality", "88",
        str(webp_path)
    ]
    subprocess.run(cmd_webp, check=False)

    # 2. 1080x1920 JPG (9:16)
    cmd_916 = [
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "scale=1080:1920",
        "-q:v", "2",
        str(cover_916)
    ]
    subprocess.run(cmd_916, check=False)

    # 3. 1080x1440 JPG (3:4 TikTok Profile Center-Crop)
    cmd_34 = [
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "scale=1080:1920,crop=1080:1440:0:240",
        "-q:v", "2",
        str(cover_34)
    ]
    subprocess.run(cmd_34, check=False)

    return {
        "webp": webp_path if webp_path.exists() else None,
        "cover_916": cover_916 if cover_916.exists() else None,
        "cover_34": cover_34 if cover_34.exists() else None,
    }


def compute_sha256(path: Path) -> str:
    """Calculate SHA256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def register_export_and_cover(mp4_path: Path, covers: dict, comp_stem: str, angle_idx: int) -> str:
    """Register export in export_registry.json and export_cover_bindings.json."""
    registry_file = DOCS_DIR / "export_registry.json"
    bindings_file = DOCS_DIR / "export_cover_bindings.json"

    entries = []
    if registry_file.exists():
        try:
            entries = json.loads(registry_file.read_text(encoding="utf-8"))
        except Exception:
            entries = []

    rel_mp4 = f"04_Exports/Ready_to_post/{mp4_path.name}"
    angle_id = f"ang_hoy01_{angle_idx:02d}"
    try:
        products_file = DOCS_DIR / "products.json"
        if products_file.exists():
            prods = json.loads(products_file.read_text(encoding="utf-8"))
            p_found = next((p for p in prods if p.get("id") == PRODUCT_ID or p.get("product_code") == "HOY01"), None)
            if p_found:
                a_found = next((a for a in p_found.get("angles", []) if a.get("clip_id") == comp_stem), None)
                if a_found and a_found.get("angle_id"):
                    angle_id = a_found.get("angle_id")
    except Exception:
        pass

    existing = next((e for e in entries if e.get("path") == rel_mp4 or e.get("path_key") == rel_mp4), None)
    now_iso = datetime.datetime.now().isoformat()
    now_ts = time.time()

    if existing:
        export_id = existing.get("id")
        existing["product_id"] = PRODUCT_ID
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
            "product_id": PRODUCT_ID,
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
    bindings = []
    if bindings_file.exists():
        try:
            bindings = json.loads(bindings_file.read_text(encoding="utf-8"))
        except Exception:
            bindings = []

    c916 = covers.get("cover_916")
    c34 = covers.get("cover_34")
    if c916 and c34 and c916.exists() and c34.exists():
        sha_916 = compute_sha256(c916)
        sha_34 = compute_sha256(c34)
        rel_916 = str(c916.relative_to(ROOT)).replace("\\", "/")
        rel_34 = str(c34.relative_to(ROOT)).replace("\\", "/")

        b_entry = next((b for b in bindings if b.get("export_id") == export_id), None)
        if not b_entry:
            b_entry = {
                "id": f"cover_{sha_916}",
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


def sync_products_json(export_mappings: dict):
    """Update angles in _Docs/products.json with rendered status."""
    products_file = DOCS_DIR / "products.json"
    if not products_file.exists():
        return
    products = json.loads(products_file.read_text(encoding="utf-8"))

    p_target = next((p for p in products if p.get("id") == PRODUCT_ID or p.get("product_code") == "HOY01"), None)
    if not p_target:
        print("  [Warn] HOYAUP product not found in products.json")
        return

    updated_count = 0
    for a in p_target.get("angles", []):
        cid = a.get("clip_id")
        if cid in export_mappings:
            info = export_mappings[cid]
            a["status"] = "rendered"
            a["video_url"] = str(info["mp4_path"])
            a["export_id"] = info["export_id"]
            if info.get("webp_path"):
                a["cover_url"] = str(info["webp_path"])
            updated_count += 1

    products_file.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> Synced {updated_count} angles in _Docs/products.json to status='rendered'")


def render_one(idx: int, skip_existing: bool = True) -> tuple:
    """Render and TikTok-enhance a single composition."""
    stem = f"hoy01-pov-s{idx:02d}"
    comp_file = COMPS_DIR / f"{stem}.html"
    if not comp_file.exists():
        print(f"[{idx:02d}/20] Missing {comp_file.name}, skipping.")
        return False, None, None

    out_mp4 = EXPORTS_DIR / f"{DATE_STR}_{stem}_v1.mp4"
    temp_raw = TMP_DIR / f"raw_{DATE_STR}_{stem}.mp4"
    seek_sec = get_cta_seek_time(comp_file)

    if out_mp4.exists() and out_mp4.stat().st_size > 1024 * 1024 and skip_existing:
        print(f"[{idx:02d}/20] MP4 already exists: {out_mp4.name} ({round(out_mp4.stat().st_size / 1024 / 1024, 2)} MB)")
        covers = extract_covers(out_mp4, stem, seek_sec)
        exp_id = register_export_and_cover(out_mp4, covers, stem, idx)
        return True, out_mp4, exp_id

    print(f"[{idx:02d}/20] 🎥 Rendering {stem}.html ... (CTA seek: {seek_sec:.2f}s)")
    t0 = time.time()

    # Step 1: Render raw MP4 with HyperFrames CLI
    cmd = [
        "npx.cmd", "--yes", "hyperframes@0.8.149", "render", ".",
        "-c", f"compositions/{comp_file.name}",
        "-o", str(temp_raw)
    ]
    res = subprocess.run(cmd, cwd=str(STUDIO), capture_output=True, text=True, check=False)
    if res.returncode != 0 or not temp_raw.exists() or temp_raw.stat().st_size == 0:
        print(f"   ❌ [RENDER FAILED] {comp_file.name}: {res.stderr[:200]}")
        return False, None, None

    render_dur = round(time.time() - t0, 1)

    # Step 2: TikTok Sharpness & Natural Brightness Enhancement (Target Y = 220-225)
    print(f"   ⚡ Enhancing with TikTok Pro Sharpness Engine (brightness=-0.031, unsharp, BT.709) ...")
    try:
        enhance_video_for_tiktok(temp_raw, output_path=out_mp4, brightness=-0.031)
        temp_raw.unlink(missing_ok=True)
    except Exception as e:
        print(f"   ⚠️ Enhancer error ({e}), keeping raw MP4.")
        shutil.move(str(temp_raw), str(out_mp4))

    total_dur = round(time.time() - t0, 1)
    size_mb = round(out_mp4.stat().st_size / (1024 * 1024), 2)
    print(f"   ✅ [SUCCESS] {out_mp4.name} ({size_mb} MB in {total_dur}s)")

    # Step 3: Extract covers and register
    covers = extract_covers(out_mp4, stem, seek_sec)
    exp_id = register_export_and_cover(out_mp4, covers, stem, idx)

    return True, out_mp4, exp_id


def main():
    parser = argparse.ArgumentParser(description="Batch render & TikTok-enhance HOYAUP 20 compositions")
    parser.add_argument("--start", type=int, default=1, help="Start index (1-20)")
    parser.add_argument("--end", type=int, default=20, help="End index (1-20)")
    parser.add_argument("--force", action="store_true", help="Re-render even if mp4 exists")
    args = parser.parse_args()

    print("=" * 65)
    print(f"🚀 BATCH RENDER & TIKTOK ENHANCE: HOYAUP พัดลมแม่เหล็ก (s{args.start:02d} to s{args.end:02d})")
    print(f"Destination: {EXPORTS_DIR}")
    print(f"Sharpness & Brightness: TikTok Pro (+0.02 brightness, unsharp 5:5:0.8, BT.709)")
    print("=" * 65)

    results = {}
    failures = []
    t_start = time.time()

    for idx in range(args.start, args.end + 1):
        ok, mp4_path, exp_id = render_one(idx, skip_existing=(not args.force))
        cid = f"hoy01-pov-s{idx:02d}"
        if ok and mp4_path:
            webp = EXPORTS_DIR / f"{DATE_STR}_{cid}_v1.webp"
            results[cid] = {
                "mp4_path": mp4_path,
                "webp_path": webp if webp.exists() else None,
                "export_id": exp_id
            }
        else:
            failures.append(cid)

    if results:
        sync_products_json(results)

    total_time = round(time.time() - t_start, 1)
    print("\n" + "=" * 65)
    print(f"🏁 Finished: {len(results)} success, {len(failures)} failed in {total_time}s")
    print("=" * 65)


if __name__ == "__main__":
    main()
