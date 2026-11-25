"""
Batch repair script for TikTok 3:4 covers from last week.
1. Re-crops defective 3:4 covers from 9:16 sibling with Smart Safe-Zone guard (>=80px margin).
2. Fixes missing cover_path in _Docs/schedule_queue.json and _Docs/posting_jobs.json.
3. Generates 3:4 covers for couple clips that lacked covers (frame grab at t=2.5s).
"""

import json
import subprocess
from pathlib import Path
from PIL import Image
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
COVERS_DIR = BASE_DIR / "05_Covers_Thumbnails"
EXPORTS_DIR = BASE_DIR / "04_Exports" / "Ready_to_post"
DOCS_DIR = BASE_DIR / "_Docs"


def smart_recrop_3x4(p_9x16: Path, p_3x4: Path) -> bool:
    """Re-crops 9:16 cover into 3:4 protecting top banner/text."""
    if not p_9x16.exists():
        return False
    try:
        im = Image.open(p_9x16).convert("RGB")
        if im.size != (1080, 1920):
            return False

        # Default center crop: y=240
        crop_3x4_y = 240
        top_slice = np.array(im.convert("L"))[80:260, :]
        if top_slice.std() > 20.0:
            row_stds = [top_slice[r].std() for r in range(top_slice.shape[0])]
            for r_idx, r_std in enumerate(row_stds):
                if r_std > 20.0:
                    first_y = 80 + r_idx
                    if first_y < crop_3x4_y + 80:
                        crop_3x4_y = max(0, min(crop_3x4_y, first_y - 80))
                    break

        im_3x4 = im.crop((0, crop_3x4_y, 1080, crop_3x4_y + 1440))
        im_3x4.save(p_3x4, format="JPEG", quality=95)
        return True
    except Exception as e:
        print(f"Error recropping {p_3x4}: {e}")
        return False


def generate_couple_cover(video_path: Path, out_3x4: Path) -> bool:
    """Grabs a frame at 2.5s (active chat state) for couple paper chat."""
    if not video_path.exists():
        return False
    try:
        out_9x16 = out_3x4.parent / out_3x4.name.replace("_cover_3x4.jpg", "_cover.jpg")
        cmd = [
            "ffmpeg", "-y", "-ss", "2.5", "-i", str(video_path),
            "-vframes", "1", "-q:v", "2", str(out_9x16)
        ]
        subprocess.run(cmd, capture_output=True, timeout=15)
        if out_9x16.exists():
            im = Image.open(out_9x16).convert("RGB")
            # 3:4 center crop
            im_3x4 = im.crop((0, 240, 1080, 1680))
            im_3x4.save(out_3x4, format="JPEG", quality=95)
            return True
    except Exception as e:
        print(f"Error generating couple cover for {video_path}: {e}")
    return False


def main():
    print("=== 1. Repairing Defective 3:4 Covers in 05_Covers_Thumbnails ===")
    repaired_count = 0
    for p_3x4 in COVERS_DIR.glob("**/*_cover_3x4.jpg"):
        try:
            im = Image.open(p_3x4)
            arr = np.array(im)
            # If text is touching top edge (top 40px std > 35)
            if arr[:40].std() > 35.0:
                p_9x16 = p_3x4.parent / p_3x4.name.replace("_cover_3x4.jpg", "_cover.jpg")
                if smart_recrop_3x4(p_9x16, p_3x4):
                    repaired_count += 1
        except Exception:
            pass
    print(f"Repaired {repaired_count} covers with safe-zone top margin.")

    print("\n=== 2. Resolving Missing Covers for Schedule Queue and Posting Jobs ===")
    # Index all 3:4 covers by stem
    covers_by_stem = {}
    for p in COVERS_DIR.glob("**/*_cover_3x4.jpg"):
        clean_stem = p.name.replace("_cover_3x4.jpg", "")
        covers_by_stem[clean_stem] = str(p.relative_to(BASE_DIR)).replace("\\", "/")

    # Check schedule_queue.json
    queue_file = DOCS_DIR / "schedule_queue.json"
    queue_fixed = 0
    if queue_file.exists():
        with open(queue_file, "r", encoding="utf-8") as f:
            queue_items = json.load(f)

        for it in queue_items:
            cp = it.get("cover_path")
            vp = it.get("video_path") or ""
            v_stem = Path(vp).stem if vp else ""

            # Needs fix if cp is None, or not 3:4, or ends with .webp
            needs_fix = (not cp) or ("_3x4" not in cp) or cp.endswith(".webp")
            if needs_fix and v_stem:
                matched_cover = covers_by_stem.get(v_stem)
                if not matched_cover:
                    # Check if couple clip
                    if "pov" in v_stem.lower() and vp:
                        full_v = BASE_DIR / vp
                        out_dir = COVERS_DIR / "main" / v_stem
                        out_dir.mkdir(parents=True, exist_ok=True)
                        out_cov = out_dir / f"{v_stem}_cover_3x4.jpg"
                        if generate_couple_cover(full_v, out_cov):
                            matched_cover = str(out_cov.relative_to(BASE_DIR)).replace("\\", "/")
                            covers_by_stem[v_stem] = matched_cover

                if matched_cover:
                    it["cover_path"] = matched_cover
                    it["cover_url"] = f"/api/media/{matched_cover}"
                    queue_fixed += 1

        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue_items, f, ensure_ascii=False, indent=2)
        print(f"Updated {queue_fixed} items in schedule_queue.json with valid 3:4 covers.")

    # Check posting_jobs.json
    jobs_file = DOCS_DIR / "posting_jobs.json"
    jobs_fixed = 0
    if jobs_file.exists():
        with open(jobs_file, "r", encoding="utf-8") as f:
            jobs = json.load(f)

        for j in jobs:
            cp = j.get("cover_path")
            vp = j.get("video_path") or ""
            v_stem = Path(vp).stem if vp else ""

            needs_fix = (not cp) or ("_3x4" not in str(cp)) or str(cp).endswith(".webp")
            if needs_fix and v_stem:
                matched_cover = covers_by_stem.get(v_stem)
                if matched_cover:
                    full_p = BASE_DIR / matched_cover
                    j["cover_path"] = str(full_p)
                    j["cover_url"] = f"/api/media/{matched_cover}"
                    jobs_fixed += 1

        with open(jobs_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"Updated {jobs_fixed} items in posting_jobs.json with valid 3:4 covers.")


if __name__ == "__main__":
    main()
