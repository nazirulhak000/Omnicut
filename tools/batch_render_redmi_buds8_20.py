#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch render and TikTok-enhance all 20 Redmi Buds 8 Active (RED01) compositions to 04_Exports/Ready_to_post/.

Adheres to Rule 24: Hardware-Aware Multi-Worker Default & Zero-Slowness Mandate (max_workers=4)
and Crash-Resilient Instant Resume Gate (is_valid_mp4).

Pipeline:
  1. Render compositions/red01-pov-s01..s20.html -> .tmp/raw_red01-pov-sXX.mp4 via hyperframes@0.8.149
  2. Enhance via TikTok Pro Sharpness Engine (scripts/tiktok_enhancer.py with brightness=-0.031, unsharp, BT.709)
     -> 04_Exports/Ready_to_post/YYYYMMDD_red01-pov-sXX_v1.mp4 (Target Y in [208.0, 225.5])
  3. Extract WebP (540x960) & Dual JPG covers (9:16 and 3:4 profile crop) from Style 3B Trio Hero Outro (cta_start + 1.8s)
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

PRODUCT_ID = "b0137078e2ff4c089b60131f60168b54"
PRODUCT_CODE = "RED01"
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
    angle_id = f"ang_red8_{angle_idx:02d}"

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
                "aspect_ratio": "9:16",
                "resolution": "1080x1920",
                "status": "rendered",
                "cover_url": f"/exports/{covers['webp'].name}" if covers.get("webp") else None,
                "created_at": now_iso,
                "updated_at": now_iso,
                "created_ts": now_ts,
                "updated_ts": now_ts,
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


def sync_products_json(export_id: str, mp4_path: Path, webp_path: Path, comp_stem: str, angle_idx: int):
    """Sync status = 'rendered', video_url, cover_url into _Docs/products.json."""
    products_file = DOCS_DIR / "products.json"
    if not products_file.exists():
        return

    angle_id = f"ang_red8_{angle_idx:02d}"

    with FILE_LOCK:
        try:
            prods = json.loads(products_file.read_text(encoding="utf-8"))
            p_found = next((p for p in prods if p.get("id") == PRODUCT_ID or p.get("product_code") == PRODUCT_CODE), None)
            if not p_found:
                return

            p_found["status"] = "rendered"
            p_found["updated_at"] = datetime.datetime.now().isoformat()

            for a in p_found.get("angles", []):
                if a.get("clip_id") == comp_stem or a.get("angle_id") == angle_id:
                    a["status"] = "rendered"
                    a["export_id"] = export_id
                    a["video_url"] = str(mp4_path.resolve())
                    if webp_path and webp_path.exists():
                        a["cover_url"] = str(webp_path.resolve())

            products_file.write_text(json.dumps(prods, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"  [Warn] Failed to sync products.json for {comp_stem}: {e}")


def render_single_clip(angle_idx: int, force: bool = False) -> dict:
    """Worker function to render, enhance, extract covers, and register 1 clip."""
    comp_stem = f"red01-pov-s{angle_idx:02d}"
    comp_file = COMPS_DIR / f"{comp_stem}.html"
    raw_mp4 = TMP_DIR / f"raw_{comp_stem}.mp4"
    final_mp4 = EXPORTS_DIR / f"{DATE_STR}_{comp_stem}_v1.mp4"

    t0 = time.time()

    if not comp_file.exists():
        return {"idx": angle_idx, "stem": comp_stem, "status": "missing_comp", "time": 0}

    # Instant Resume Gate
    if is_valid_mp4(final_mp4) and not force:
        seek_sec = get_cta_seek_time(comp_file)
        covers = extract_covers(final_mp4, comp_stem, seek_sec)
        exp_id = register_export_and_cover(final_mp4, covers, comp_stem, angle_idx)
        sync_products_json(exp_id, final_mp4, covers.get("webp"), comp_stem, angle_idx)
        print(f"  ⚡ [Resume] {comp_stem} already rendered & valid -> Synced!")
        return {"idx": angle_idx, "stem": comp_stem, "status": "resumed", "time": 0.5}

    print(f"🎬 [Start Worker] Rendering {comp_stem}...")

    # Step 1: Render raw MP4 with HyperFrames CLI (skip if raw already valid)
    if not is_valid_mp4(raw_mp4):
        npx_bin = "npx.cmd" if sys.platform == "win32" else "npx"
        cmd_render = [
            npx_bin, "--yes", "hyperframes@0.8.149", "render", ".",
            "-c", f"compositions/{comp_file.name}",
            "--gpu",
            "--browser-gpu",
            "-o", str(raw_mp4)
        ]
        p_render = subprocess.run(cmd_render, cwd=str(STUDIO), capture_output=True, text=True, check=False)
        if p_render.returncode != 0 or not is_valid_mp4(raw_mp4):
            err = p_render.stderr[-300:] if p_render.stderr else "Unknown render error"
            print(f"❌ [Error] Render failed for {comp_stem}: {err}")
            return {"idx": angle_idx, "stem": comp_stem, "status": "render_failed", "error": err}
    else:
        print(f"  ⚡ [Raw Cached] Using existing raw MP4 for {comp_stem}...")

    # Step 2: Enhance via TikTok Pro Sharpness Engine
    print(f"  ✨ [Enhance] {comp_stem} via TikTok Pro Sharpness Engine...")
    try:
        enhance_video_for_tiktok(raw_mp4, output_path=final_mp4, brightness=-0.031)
        if is_valid_mp4(final_mp4):
            raw_mp4.unlink(missing_ok=True)
        else:
            raise RuntimeError("Enhanced MP4 failed integrity check")
    except Exception as e:
        print(f"  ⚠️ [Fallback] Enhancer error ({e}), copying raw MP4...")
        shutil.copy2(raw_mp4, final_mp4)
        raw_mp4.unlink(missing_ok=True)

    # Step 3: Extract WebP and Dual JPG covers
    seek_sec = get_cta_seek_time(comp_file)
    covers = extract_covers(final_mp4, comp_stem, seek_sec)

    # Step 4: Register in registry & cover bindings
    exp_id = register_export_and_cover(final_mp4, covers, comp_stem, angle_idx)

    # Step 5: Sync products.json
    sync_products_json(exp_id, final_mp4, covers.get("webp"), comp_stem, angle_idx)

    elapsed = round(time.time() - t0, 1)
    file_mb = round(final_mp4.stat().st_size / (1024 * 1024), 2)
    print(f"✅ [Done Worker] {comp_stem} -> {final_mp4.name} ({file_mb} MB) in {elapsed}s")
    return {"idx": angle_idx, "stem": comp_stem, "status": "success", "time": elapsed, "mb": file_mb}


def main():
    parser = argparse.ArgumentParser(description="Parallel Batch Render for Redmi Buds 8 Active Compositions")
    parser.add_argument("--workers", type=int, default=4, help="Max parallel workers (Default: 4 per Rule 24)")
    parser.add_argument("--start", type=int, default=1, help="Start angle index (1-20)")
    parser.add_argument("--end", type=int, default=20, help="End angle index (1-20)")
    parser.add_argument("--force", action="store_true", help="Force re-render existing clips")
    args = parser.parse_args()

    indices = list(range(args.start, args.end + 1))
    print("=" * 70)
    print(f"🚀 Launching Parallel Batch Render for RED01: clips {args.start}..{args.end}")
    print(f"   Max Workers: {args.workers} (Hardware-Aware Concurrency)")
    print(f"   Sharpness: TikTok Pro Sharpness Engine (brightness=-0.031, unsharp)")
    print(f"   Exports: {EXPORTS_DIR}")
    print("=" * 70)

    t_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(render_single_clip, i, args.force): i for i in indices}
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                print(f"❌ Worker crashed on clip {idx}: {e}")
                results.append({"idx": idx, "status": "crashed", "error": str(e)})

    total_time = round(time.time() - t_start, 1)
    succeeded = sum(1 for r in results if r.get("status") in ("success", "resumed"))
    print("\n" + "=" * 70)
    print(f"🏁 Batch Render Completed: {succeeded}/{len(indices)} clips successful in {total_time}s ({total_time/60:.1f} mins)")
    print("=" * 70)


if __name__ == "__main__":
    main()
