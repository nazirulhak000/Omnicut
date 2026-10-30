#!/usr/bin/env python3
"""Calibrate brightness (luminance Y) of exported clips and covers to target range 220-225.

Per user directive: "ขอเป็น 220-225 ได้ไหม เกินกว่านั้นเหมือนจะสว่างมากอ่ะ"
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = ROOT / "04_Exports" / "Ready_to_post"
COVERS_DIR = ROOT / "05_Covers_Thumbnails"
DOCS_DIR = ROOT / "_Docs"
TMP_DIR = ROOT / ".tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

TARGET_Y_MIN = 220.0
TARGET_Y_MAX = 225.5
BRIGHTNESS_EQ = "-0.042"  # Yields Frame 0 Y approx 221.8 - 223.0


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def measure_frame0_y(video_path: Path) -> tuple[float, list]:
    cap = cv2.VideoCapture(str(video_path))
    ret, frame0 = cap.read()
    cap.release()
    if not ret:
        return 0.0, [0, 0, 0]
    y0 = float(np.mean(cv2.cvtColor(frame0, cv2.COLOR_BGR2YCrCb)[:, :, 0]))
    corner = [int(x) for x in frame0[100, 100]]
    return y0, corner


def extract_covers(mp4_path: Path, seek_sec: float = 45.0) -> dict:
    """Extract WebP, 9:16 JPG, and 3:4 JPG from calibrated video."""
    stem = mp4_path.stem  # e.g. 20261013_ess02-pov-s01_v1
    webp_path = EXPORTS_DIR / f"{stem}.webp"
    cover_916 = COVERS_DIR / f"{stem}_cover.jpg"
    cover_34 = COVERS_DIR / f"{stem}_cover_3x4.jpg"

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


def update_cover_bindings(mp4_path: Path, covers: dict):
    bindings_file = DOCS_DIR / "export_cover_bindings.json"
    if not bindings_file.exists():
        return
    try:
        bindings = json.loads(bindings_file.read_text(encoding="utf-8"))
    except Exception:
        return

    rel_mp4 = f"04_Exports/Ready_to_post/{mp4_path.name}"
    c916 = covers.get("cover_916")
    c34 = covers.get("cover_34")
    if not (c916 and c34 and c916.exists() and c34.exists()):
        return

    sha_916 = compute_sha256(c916)
    sha_34 = compute_sha256(c34)
    rel_916 = str(c916.relative_to(ROOT)).replace("\\", "/")
    rel_34 = str(c34.relative_to(ROOT)).replace("\\", "/")

    entry = next((b for b in bindings if b.get("video_path") == rel_mp4), None)
    if entry:
        entry["selections"]["9:16"] = {"path": rel_916, "sha256": sha_916, "format": "9:16"}
        entry["selections"]["3:4"] = {"path": rel_34, "sha256": sha_34, "format": "3:4"}
        entry["updated_at"] = time.time()
        bindings_file.write_text(json.dumps(bindings, ensure_ascii=False, indent=2), encoding="utf-8")


def calibrate_single_clip(mp4_path: Path) -> dict:
    stem = mp4_path.stem
    y_before, corner_before = measure_frame0_y(mp4_path)

    tmp_calibrated = TMP_DIR / f"calibrated_{mp4_path.name}"

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin, "-y", "-i", str(mp4_path),
        "-vf", f"eq=brightness={BRIGHTNESS_EQ}",
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.2",
        "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-crf", "18", "-preset", "fast", "-g", "60", "-bf", "2",
        "-c:a", "copy", "-movflags", "+faststart",
        str(tmp_calibrated)
    ]

    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0 or not tmp_calibrated.exists() or tmp_calibrated.stat().st_size == 0:
        return {"ok": False, "name": mp4_path.name, "error": res.stderr[:200]}

    y_after, corner_after = measure_frame0_y(tmp_calibrated)
    dur = time.time() - t0

    # Overwrite target file
    shutil.move(str(tmp_calibrated), str(mp4_path))

    # Re-extract covers from CTA shot (approx dur - 4.5s)
    # Check duration with ffprobe
    cap = cv2.VideoCapture(str(mp4_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1800
    cap.release()
    total_dur = frame_count / fps
    seek_sec = max(0.5, total_dur - 4.5)

    covers = extract_covers(mp4_path, seek_sec)
    update_cover_bindings(mp4_path, covers)

    return {
        "ok": True,
        "name": mp4_path.name,
        "y_before": y_before,
        "y_after": y_after,
        "corner_after": corner_after,
        "dur": dur,
        "in_target": TARGET_Y_MIN <= y_after <= TARGET_Y_MAX,
    }


def main():
    clips = []
    # 20 Essager clips
    for i in range(1, 21):
        p = EXPORTS_DIR / f"20261013_ess02-pov-s{i:02d}_v1.mp4"
        if p.exists():
            clips.append(p)

    # 1 HOYAUP s01 clip
    hoy01 = EXPORTS_DIR / "20261013_hoy01-pov-s01_v1.mp4"
    if hoy01.exists():
        clips.append(hoy01)

    print(f"🎬 Starting Brightness Calibration for {len(clips)} clips to target range [{TARGET_Y_MIN}, {TARGET_Y_MAX}] ...")

    results = []
    for idx, cp in enumerate(clips, 1):
        print(f"[{idx:02d}/{len(clips)}] Processing {cp.name} ...", end=" ", flush=True)
        r = calibrate_single_clip(cp)
        results.append(r)
        if r["ok"]:
            status_tag = "✅ IN TARGET" if r["in_target"] else "⚠️ OUT OF RANGE"
            print(f"{status_tag} Y: {r['y_before']:.1f} -> {r['y_after']:.1f} (corner {r['corner_after']}) in {r['dur']:.1f}s")
        else:
            print(f"❌ FAILED: {r.get('error')}")

    success_count = sum(1 for r in results if r["ok"] and r["in_target"])
    print(f"\n🎉 Finished: {success_count}/{len(clips)} clips successfully calibrated to {TARGET_Y_MIN} - {TARGET_Y_MAX}!")


if __name__ == "__main__":
    main()
