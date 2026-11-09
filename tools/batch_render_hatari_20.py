#!/usr/bin/env python3
"""Batch render and TikTok-enhance all 20 Hatari Cyclone Max compositions to 04_Exports/Ready_to_post/.

Pipeline:
  1. Render compositions/hat02-pov-s01..s20.html -> .tmp/raw_hat02-pov-sXX.mp4
  2. Enhance via TikTok Pro Sharpness Engine (scripts/tiktok_enhancer.py with brightness=-0.031)
     -> 04_Exports/Ready_to_post/20261014_hat02-pov-sXX_v1.mp4 (Target Y in [220.0, 225.5])
  3. Extract WebP & Dual JPG covers (9:16 and 3:4 TikTok Profile crop) from Brand-First CTA shot at cta_start + 1.8s
  4. Register into _Docs/export_registry.json and _Docs/export_cover_bindings.json
  5. Sync status = 'rendered' in _Docs/products.json
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
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

PRODUCT_ID = "cde38b1c07e54ea69a3d50a6c1bb3f18"
PRODUCT_CODE = "HAT02"
DATE_STR = datetime.datetime.now().strftime("%Y%m%d")

sys.path.insert(0, str(ROOT))
from scripts.tiktok_enhancer import enhance_video_for_tiktok
from scripts import store_io  # noqa: E402
from scripts import media_validation

# S6-10: a hung HyperFrames/Chromium render must not block a worker forever.
HF_RENDER_TIMEOUT_SEC = 1800
_REGISTRY_LOCK = threading.Lock()


def _run_hf_render(cmd, raw_out: Path):
    """HyperFrames CLI with a disk guard (S6-11) and a timeout (S6-10).

    Never raises: a hung render or a full disk comes back as a failed result,
    and the half-written raw file is removed."""
    try:
        media_validation.require_disk_space(EXPORTS_DIR)
        return subprocess.run(cmd, cwd=str(STUDIO), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False, timeout=HF_RENDER_TIMEOUT_SEC)
    except (subprocess.TimeoutExpired, media_validation.InsufficientDiskSpace) as exc:
        raw_out.unlink(missing_ok=True)
        return subprocess.CompletedProcess(cmd, -1, stdout="", stderr=f"เรนเดอร์ไม่สำเร็จ: {exc}")


def is_valid_mp4(path: Path) -> bool:
    """Central gate (S6-03): ffprobe streams + 1080x1920 + 30fps + tail decode."""
    return media_validation.is_valid_mp4(path)


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
    """Register into the export registry and cover bindings through the
    SQLite-backed stores (scripts.store_io, audit S6-01): no direct JSON
    mirror writes, and a read error raises instead of becoming []."""
    rel_mp4 = f"04_Exports/Ready_to_post/{mp4_path.name}"
    angle_id = f"ang_hat02_{angle_idx:02d}"

    prods = store_io.load_products(DOCS_DIR)
    p_found = next((p for p in prods if p.get("id") == PRODUCT_ID or p.get("product_code") == PRODUCT_CODE), None)
    if p_found:
        a_found = next((a for a in p_found.get("angles", []) if a.get("clip_id") == comp_stem), None)
        if a_found and a_found.get("angle_id"):
            angle_id = a_found.get("angle_id")

    now_ts = time.time()
    export_id = store_io.upsert_rendered_export(
        rel_mp4,
        product_id=PRODUCT_ID,
        angle_id=angle_id,
        project_name=f"_HyperFrames_Studio/{comp_stem}",
        docs_dir=DOCS_DIR,
    )

    # Cover bindings
    p_916 = covers.get("cover_916")
    p_34 = covers.get("cover_34")
    if p_916 and p_916.exists() and p_34 and p_34.exists():
        rel_916 = str(p_916.relative_to(ROOT)).replace("\\", "/")
        rel_34 = str(p_34.relative_to(ROOT)).replace("\\", "/")
        sha_916 = compute_sha256(p_916)
        sha_34 = compute_sha256(p_34)
        store_io.upsert_cover_binding(
            export_id,
            rel_mp4,
            {
                "9:16": {"path": rel_916, "sha256": sha_916, "format": "9:16"},
                "3:4": {"path": rel_34, "sha256": sha_34, "format": "3:4"},
            },
            binding_id=f"cover_{sha_916}",
            docs_dir=DOCS_DIR,
            clock=lambda: now_ts,
        )

    return export_id


def sync_products_json(export_mappings: dict):
    """Update angles in the product store with rendered status (via
    scripts.store_io, audit S1-01 -- no direct products.json write)."""
    with store_io.mutate_products(DOCS_DIR) as products:
        p_target = next((p for p in products if p.get("id") == PRODUCT_ID or p.get("product_code") == PRODUCT_CODE), None)
        if not p_target:
            print("  [Warn] Hatari Cyclone Max product not found in products.json")
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
    print(f"  -> Synced {updated_count} angles in _Docs/products.json to status='rendered'")


def render_one(idx: int, skip_existing: bool = True) -> tuple:
    """Render and TikTok-enhance a single composition."""
    stem = f"hat02-pov-s{idx:02d}"
    comp_file = COMPS_DIR / f"{stem}.html"
    if not comp_file.exists():
        print(f"[{idx:02d}/20] Missing {comp_file.name}, skipping.")
        return False, None, None

    out_mp4 = EXPORTS_DIR / f"{DATE_STR}_{stem}_v1.mp4"
    temp_raw = TMP_DIR / f"raw_{DATE_STR}_{stem}.mp4"
    seek_sec = get_cta_seek_time(comp_file)

    if skip_existing and is_valid_mp4(out_mp4):
        print(f"[{idx:02d}/20] MP4 already exists: {out_mp4.name} ({round(out_mp4.stat().st_size / 1024 / 1024, 2)} MB)")
        with _REGISTRY_LOCK:
            covers = extract_covers(out_mp4, stem, seek_sec)
            exp_id = register_export_and_cover(out_mp4, covers, stem, idx)
        return True, out_mp4, exp_id

    print(f"[{idx:02d}/20] 🎥 Rendering {comp_file.name} ... (CTA seek: {seek_sec:.2f}s)")
    t0 = time.time()

    # Step 1: Render raw MP4 with HyperFrames CLI
    cmd = [
        "npx.cmd", "--yes", "hyperframes@0.8.149", "render", ".",
        "-c", f"compositions/{comp_file.name}",
        "--gpu",
        "--browser-gpu",
        "-o", str(temp_raw)
    ]
    res = _run_hf_render(cmd, temp_raw)
    if res.returncode != 0 or not is_valid_mp4(temp_raw):
        print(f"   ❌ [RENDER FAILED] {comp_file.name}: {res.stderr[:200]}")
        return False, None, None

    render_dur = round(time.time() - t0, 1)

    # Step 2: TikTok Sharpness & Natural Brightness Enhancement (Target Y = 220-225)
    print(f"   ⚡ Enhancing with TikTok Pro Sharpness Engine (brightness=-0.031, unsharp, BT.709) ...")
    try:
        enhance_video_for_tiktok(temp_raw, output_path=out_mp4, brightness=-0.031)
    except Exception as e:
        # S6-05: never ship the raw, unenhanced MP4 -- the clip fails instead.
        print(f"   ❌ [ENHANCE FAILED] {out_mp4.name}: {e}")
        return False, None, None
    finally:
        temp_raw.unlink(missing_ok=True)

    total_dur = round(time.time() - t0, 1)
    size_mb = round(out_mp4.stat().st_size / (1024 * 1024), 2)
    print(f"   ✅ [SUCCESS] {out_mp4.name} ({size_mb} MB in {total_dur}s)")

    # Step 3: Extract covers and register
    with _REGISTRY_LOCK:
        covers = extract_covers(out_mp4, stem, seek_sec)
        exp_id = register_export_and_cover(out_mp4, covers, stem, idx)

    return True, out_mp4, exp_id


def main():
    parser = argparse.ArgumentParser(description="Batch render & TikTok-enhance Hatari Cyclone Max 20 compositions")
    parser.add_argument("--start", type=int, default=1, help="Start index (1-20)")
    parser.add_argument("--end", type=int, default=20, help="End index (1-20)")
    parser.add_argument("--force", action="store_true", help="Re-render even if mp4 exists")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent worker threads (default: 4 as per Rule 24)")
    args = parser.parse_args()

    print("=" * 65)
    print(f"🚀 BATCH RENDER & TIKTOK ENHANCE: Hatari Cyclone Max 8 นิ้ว (s{args.start:02d} to s{args.end:02d})")
    print(f"Destination: {EXPORTS_DIR}")
    print(f"Sharpness & Brightness: TikTok Pro (-0.031 brightness, unsharp 5:5:0.8, BT.709)")
    print("=" * 65)

    results = {}
    failures = []
    t_start = time.time()

    indices = list(range(args.start, args.end + 1))
    outcomes = {}
    # AGENTS rule 24 / S6-07: 4 concurrent workers, GPU render + NVENC encode,
    # per-clip resume gate -- never one clip at a time.
    print(f"Concurrency: {args.workers} workers (Rule 24)")
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_to_idx = {executor.submit(render_one, idx, not args.force): idx for idx in indices}
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                outcomes[idx] = future.result()
            except Exception as exc:
                print(f"   ❌ [CRASH] index {idx:02d}: {exc}")
                outcomes[idx] = (False, None, None)

    for idx in indices:
        ok, mp4_path, exp_id = outcomes[idx]
        cid = f"hat02-pov-s{idx:02d}"
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
