#!/usr/bin/env python3
"""Batch render and TikTok-enhance all 20 GOOJODOQ 5000mAh Mini Power Bank compositions to 04_Exports/Ready_to_post/.

Adheres to Rule 24: Hardware-Aware Multi-Worker Default & Zero-Slowness Mandate (max_workers=4)
and Crash-Resilient Instant Resume Gate (is_valid_mp4).

Pipeline:
  1. Render compositions/goo01-pov-s01..s20.html -> .tmp/raw_goo01-pov-sXX.mp4 via hyperframes@0.8.149
  2. Enhance via TikTok Pro Sharpness Engine (scripts/tiktok_enhancer.py with brightness=-0.031, unsharp, BT.709)
     -> 04_Exports/Ready_to_post/YYYYMMDD_goo01-pov-sXX_v1.mp4 (Target Y in [220.0, 225.5])
  3. Extract WebP (540x960) & Dual JPG covers (9:16 and 3:4 profile crop) from Style 3B Macro Hero Outro (cta_start + 1.8s)
  4. Register into _Docs/export_registry.json and _Docs/export_cover_bindings.json (Thread-safe)
  5. Sync status = 'rendered' in _Docs/products.json (Thread-safe)
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid

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

PRODUCT_ID = "7900bbca318d41ed964b5a721c0d951f"
PRODUCT_CODE = "GOO01"
DATE_STR = datetime.datetime.now().strftime("%Y%m%d")

sys.path.insert(0, str(ROOT))
from scripts.tiktok_enhancer import enhance_video_for_tiktok
from filelock import FileLock

FILE_LOCK = FileLock(str(TMP_DIR / "export_db.lock"), timeout=60)


def is_valid_mp4(path: Path) -> bool:
    """Validate MP4 file integrity using ffprobe duration and file size."""
    if not path.exists() or path.stat().st_size < 1024 * 1024:
        return False
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=False, timeout=10
        )
        return res.returncode == 0 and float(res.stdout.strip()) > 5.0
    except Exception:
        return False


def get_cta_seek_time(comp_path: Path) -> float:
    """Find the optimal thumbnail seek time (CTA frame fully animated)."""
    try:
        txt = comp_path.read_text(encoding="utf-8")
        m_dur = re.search(r'data-duration=["\']([\d\.]+)["\']', txt)
        dur = float(m_dur.group(1)) if m_dur else 65.0
        m_cta = re.search(r'const\s+CTA_?T\s*=\s*([\d\.]+);', txt, re.IGNORECASE)
        if not m_cta:
            m_cta = re.search(r'id=["\']b-cta["\'][^>]*data-start=["\']([\d\.]+)["\']', txt)
        cta_start = float(m_cta.group(1)) if m_cta else dur - 6.0
        seek_time = min(cta_start + 1.8, dur - 0.5)
        return max(0.5, seek_time)
    except Exception:
        return 60.0


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
        "-strict", "unofficial",
        "-q:v", "2",
        "-update", "1",
        str(cover_916)
    ]
    subprocess.run(cmd_916, check=False)

    # 3. 1080x1440 JPG (3:4 TikTok Profile Center-Crop)
    cmd_34 = [
        ffmpeg_bin, "-v", "error", "-y",
        "-ss", str(seek_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-vf", "crop=1080:1440:0:240",
        "-strict", "unofficial",
        "-q:v", "2",
        "-update", "1",
        str(cover_34)
    ]
    subprocess.run(cmd_34, check=False)

    return {
        "webp": webp_path if webp_path.exists() else None,
        "9:16": cover_916 if cover_916.exists() else None,
        "3:4": cover_34 if cover_34.exists() else None,
    }


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def register_export_and_cover(mp4_path: Path, covers: dict, comp_stem: str, angle_idx: int) -> str:
    """Register into export_registry.json and export_cover_bindings.json in a thread-safe manner."""
    registry_file = DOCS_DIR / "export_registry.json"
    bindings_file = DOCS_DIR / "export_cover_bindings.json"

    rel_mp4 = f"04_Exports/Ready_to_post/{mp4_path.name}"
    angle_id = f"ang_goo5k_{angle_idx:02d}"

    with FILE_LOCK:
        try:
            products_file = DOCS_DIR / "products.json"
            if products_file.exists():
                prods = json.loads(products_file.read_text(encoding="utf-8"))
                p_found = next((p for p in prods if p.get("id") == PRODUCT_ID or p.get("product_code") == PRODUCT_CODE), None)
                if p_found:
                    a_found = next((a for a in p_found.get("angles", []) if a.get("clip_id") == comp_stem or a.get("angle_id") == angle_id), None)
                    if a_found and a_found.get("angle_id"):
                        angle_id = a_found.get("angle_id")
        except Exception:
            pass

        entries = []
        if registry_file.exists():
            try:
                entries = json.loads(registry_file.read_text(encoding="utf-8"))
            except Exception:
                entries = []

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


def sync_products_json(export_mappings: dict):
    """Update angles in _Docs/products.json with rendered status (Thread-safe)."""
    products_file = DOCS_DIR / "products.json"
    if not products_file.exists():
        return

    with FILE_LOCK:
        try:
            products = json.loads(products_file.read_text(encoding="utf-8"))
            p_target = next((p for p in products if p.get("id") == PRODUCT_ID or p.get("product_code") == PRODUCT_CODE), None)
            if not p_target:
                print("  [Warn] GOOJODOQ product not found in products.json")
                return

            updated_count = 0
            for a in p_target.get("angles", []):
                cid = a.get("clip_id")
                aid = a.get("angle_id")
                info = export_mappings.get(cid) or export_mappings.get(aid)
                if info:
                    a["status"] = "rendered"
                    a["video_url"] = str(info["mp4_path"])
                    a["export_id"] = info["export_id"]
                    if info.get("webp_path"):
                        a["cover_url"] = str(info["webp_path"])
                    updated_count += 1

            products_file.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  -> Synced {updated_count} angles in _Docs/products.json to status='rendered'")
        except Exception as e:
            print(f"  [Warn] Failed to sync products.json: {e}")


def render_one(idx: int, skip_existing: bool = True) -> tuple:
    """Render and TikTok-enhance a single GOOJODOQ composition."""
    stem = f"goo01-pov-s{idx:02d}"
    comp_file = COMPS_DIR / f"{stem}.html"
    if not comp_file.exists():
        print(f"[{idx:02d}/20] Missing {comp_file.name}, skipping.")
        return False, None, None

    out_mp4 = EXPORTS_DIR / f"{DATE_STR}_{stem}_v1.mp4"
    temp_raw = TMP_DIR / f"raw_{DATE_STR}_{stem}.mp4"
    seek_sec = get_cta_seek_time(comp_file)

    if skip_existing and is_valid_mp4(out_mp4):
        size_mb = round(out_mp4.stat().st_size / (1024 * 1024), 2)
        print(f"[{idx:02d}/20] ⏩ Already exists & valid: {out_mp4.name} ({size_mb} MB) -> skipping render.")
        covers = extract_covers(out_mp4, stem, seek_sec)
        exp_id = register_export_and_cover(out_mp4, covers, stem, idx)
        return True, out_mp4, exp_id

    print(f"[{idx:02d}/20] 🎥 Rendering {stem}.html ... (CTA seek: {seek_sec:.2f}s)")
    t0 = time.time()

    # Step 1: Render raw MP4 with HyperFrames CLI (GPU-accelerated)
    cmd = [
        "npx.cmd", "--yes", "hyperframes@0.8.149", "render", ".",
        "-c", f"compositions/{comp_file.name}",
        "--gpu",
        "--browser-gpu",
        "-o", str(temp_raw)
    ]
    res = subprocess.run(cmd, cwd=str(STUDIO), capture_output=True, text=True, check=False)
    if res.returncode != 0 or not temp_raw.exists() or temp_raw.stat().st_size == 0:
        err_snippet = res.stderr[-250:] if res.stderr else "Unknown render error"
        print(f"   ❌ [RENDER FAILED] {comp_file.name}: {err_snippet}")
        return False, None, None

    render_dur = round(time.time() - t0, 1)

    # Step 2: TikTok Sharpness & Natural Brightness Enhancement (Target Y in [220.0, 225.5])
    print(f"   ⚡ Enhancing {stem} with TikTok Pro Sharpness Engine (brightness=-0.031, unsharp, BT.709) ...")
    try:
        enhance_video_for_tiktok(temp_raw, output_path=out_mp4, brightness=-0.031)
        temp_raw.unlink(missing_ok=True)
    except Exception as e:
        print(f"   ⚠️ Enhancer error ({e}), keeping raw MP4.")
        shutil.move(str(temp_raw), str(out_mp4))

    total_dur = round(time.time() - t0, 1)
    size_mb = round(out_mp4.stat().st_size / (1024 * 1024), 2)
    print(f"   ✅ [SUCCESS] {out_mp4.name} ({size_mb} MB in {total_dur}s)")

    # Step 3: Extract covers and register (Thread-safe)
    covers = extract_covers(out_mp4, stem, seek_sec)
    exp_id = register_export_and_cover(out_mp4, covers, stem, idx)

    return True, out_mp4, exp_id


def main():
    parser = argparse.ArgumentParser(description="Batch render & TikTok-enhance GOOJODOQ 20 compositions in parallel")
    parser.add_argument("--start", type=int, default=1, help="Start index (1-20)")
    parser.add_argument("--end", type=int, default=20, help="End index (1-20)")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent worker threads (default: 4 as per Rule 24)")
    parser.add_argument("--force", action="store_true", help="Re-render even if mp4 exists")
    args = parser.parse_args()

    indices = list(range(args.start, args.end + 1))
    print("=" * 68)
    print(f"🚀 MULTI-WORKER BATCH RENDER: GOOJODOQ 5000mAh Mini Power Bank")
    print(f"Scope: s{args.start:02d} to s{args.end:02d} ({len(indices)} clips)")
    print(f"Concurrency: {args.workers} Workers (Rule 24 Mandate)")
    print(f"Destination: {EXPORTS_DIR}")
    print(f"Sharpness & Brightness: TikTok Pro (brightness=-0.031, unsharp, BT.709)")
    print("=" * 68)

    t_start = time.time()
    results = {}
    failures = []

    if args.workers <= 1:
        # Sequential fallback if requested
        for idx in indices:
            ok, mp4_path, exp_id = render_one(idx, skip_existing=(not args.force))
            cid = f"goo01-pov-s{idx:02d}"
            if ok and mp4_path:
                webp = EXPORTS_DIR / f"{DATE_STR}_{cid}_v1.webp"
                results[cid] = {
                    "mp4_path": mp4_path,
                    "webp_path": webp if webp.exists() else None,
                    "export_id": exp_id
                }
            else:
                failures.append(cid)
    else:
        # Multi-worker parallel execution
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_idx = {
                executor.submit(render_one, idx, not args.force): idx
                for idx in indices
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                cid = f"goo01-pov-s{idx:02d}"
                try:
                    ok, mp4_path, exp_id = future.result()
                    if ok and mp4_path:
                        webp = EXPORTS_DIR / f"{DATE_STR}_{cid}_v1.webp"
                        results[cid] = {
                            "mp4_path": mp4_path,
                            "webp_path": webp if webp.exists() else None,
                            "export_id": exp_id
                        }
                    else:
                        failures.append(cid)
                except Exception as exc:
                    print(f"   ❌ [CRASH] {cid}: {exc}")
                    failures.append(cid)

    if results:
        print("\n📊 Syncing Content Tracker in _Docs/products.json...")
        sync_products_json(results)

    total_time = round(time.time() - t_start, 1)
    print("\n" + "=" * 68)
    print(f"🏁 Finished: {len(results)} success, {len(failures)} failed in {total_time}s ({total_time / 60:.1f} mins)")
    print("=" * 68)


if __name__ == "__main__":
    main()
