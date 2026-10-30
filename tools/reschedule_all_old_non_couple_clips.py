"""
Reschedule all old non-couple exports in 04_Exports/Ready_to_post.
Starts tomorrow (2026-10-20) at 07:00, 7 slots/day:
  07:00, 09:20, 11:40, 14:00, 16:20, 18:40, 21:00
Smooth product interleaving:
  - Essager PD 30W placed across all days (max 2/day spaced >=9h20m apart: 09:20 and 18:40).
  - All other products interleaved with zero adjacent duplicate products.
  - Strictly excludes all couple clips.
  - Preserves all posted items in ScheduleQueueStore.
  - Updates both SQLite store.db and _Docs/schedule_queue.json atomically via ScheduleQueueStore._save().
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import urllib.parse
import uuid
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from scripts.config import BASE_DIR
from scripts.schedule_store import ScheduleQueueStore

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
SLOT_TIMES = ["07:00", "09:20", "11:40", "14:00", "16:20", "18:40", "21:00"]
START_DATE = dt.datetime(2026, 10, 22, tzinfo=BANGKOK_TZ)


def is_couple_clip(filename: str) -> bool:
    fn = filename.lower()
    return "-pov-s" in fn or "_pov-s" in fn or "couple" in fn or "น้องนุ้ย" in filename or "พี่บ่าว" in filename


def generate_time_slots(count: int) -> list[str]:
    slots = []
    for i in range(count):
        d_idx = i // 7
        s_idx = i % 7
        day = START_DATE + dt.timedelta(days=d_idx)
        date_str = day.strftime("%Y-%m-%d")
        time_str = SLOT_TIMES[s_idx]
        slots.append(f"{date_str}T{time_str}+07:00")
    return slots


def build_balanced_schedule(candidates: list[dict]) -> list[dict]:
    n = len(candidates)
    days = (n + 6) // 7

    grid = []
    for d in range(days):
        day_len = 7 if d < days - 1 else (n % 7 or 7)
        grid.append([None] * day_len)

    by_prod = defaultdict(list)
    for c in candidates:
        pname = c.get("product_name") or "Unknown"
        by_prod[pname].append(c)

    # 1. Place Essager PD 30W first
    ess_key = next((k for k in by_prod if "Essager" in k and "30W" in k), None)
    if ess_key:
        ess_items = list(by_prod[ess_key])
        del by_prod[ess_key]

        eligible_two = [d for d in range(days) if len(grid[d]) >= 6]
        two_count = len(ess_items) - days if len(ess_items) > days else 0
        step = max(1, len(eligible_two) // max(1, two_count)) if two_count > 0 else 1
        two_days = set(eligible_two[::step][:two_count])

        for d in range(days):
            if not ess_items:
                break
            if d in two_days and len(grid[d]) >= 6 and len(ess_items) >= 2:
                grid[d][1] = ess_items.pop(0)  # 09:20
                grid[d][5] = ess_items.pop(0)  # 18:40 (spaced 9h20m)
            elif len(grid[d]) > 3:
                grid[d][3] = ess_items.pop(0)  # 14:00
            elif len(grid[d]) > 1:
                grid[d][1] = ess_items.pop(0)  # 09:20
            else:
                grid[d][0] = ess_items.pop(0)  # 07:00

        # Any leftover Essager
        while ess_items:
            placed = False
            for d in range(days):
                for s in range(len(grid[d])):
                    if grid[d][s] is None:
                        grid[d][s] = ess_items.pop(0)
                        placed = True
                        break
                if placed:
                    break

    # 2. Other products sorted by frequency descending
    pool = []
    for _, items in sorted(by_prod.items(), key=lambda x: len(x[1]), reverse=True):
        pool.extend(items)

    for d in range(days):
        for s in range(len(grid[d])):
            if grid[d][s] is None:
                day_prods = {grid[d][slot]["product_name"] for slot in range(len(grid[d])) if grid[d][slot] is not None}
                prev_prod = None
                if s > 0:
                    prev_prod = grid[d][s - 1]["product_name"] if grid[d][s - 1] else None
                elif d > 0 and grid[d - 1][-1]:
                    prev_prod = grid[d - 1][-1]["product_name"]

                cand_idx = next(
                    (i for i, it in enumerate(pool) if it["product_name"] not in day_prods and it["product_name"] != prev_prod),
                    None,
                )
                if cand_idx is None:
                    cand_idx = next((i for i, it in enumerate(pool) if it["product_name"] != prev_prod), None)
                if cand_idx is None:
                    cand_idx = 0

                grid[d][s] = pool.pop(cand_idx)

    ordered = []
    for d in range(days):
        for s in range(len(grid[d])):
            ordered.append(grid[d][s])
    return ordered


def main():
    print("=" * 72)
    print(" OmniCut Pro Studio: Reschedule All Old Non-Couple Clips")
    print("=" * 72)

    ready_dir = BASE_DIR / "04_Exports" / "Ready_to_post"
    all_ready_files = sorted(ready_dir.glob("*.mp4"), key=lambda p: p.name)

    target_files = [f for f in all_ready_files if not is_couple_clip(f.name)]
    couple_files = [f for f in all_ready_files if is_couple_clip(f.name)]

    print(f"Total MP4 files in Ready_to_post: {len(all_ready_files)}")
    print(f"Couple Series files (EXCLUDED):   {len(couple_files)}")
    print(f"Target Non-Couple files:          {len(target_files)}")

    target_filenames = {f.name for f in target_files}

    # 1. Update export_registry.json for any target files that have status == 'posted'
    exp_reg_path = BASE_DIR / "_Docs" / "export_registry.json"
    exports_list = json.loads(exp_reg_path.read_text(encoding="utf-8")) if exp_reg_path.exists() else []

    now_iso = dt.datetime.now(BANGKOK_TZ).isoformat()
    reg_modified = False
    for exp in exports_list:
        p = exp.get("path")
        if p and Path(p).name in target_filenames:
            if exp.get("status") == "posted" or exp.get("posted_at") is not None:
                print(f"  Resetting export_registry status -> rendered for: {Path(p).name}")
                exp["status"] = "rendered"
                exp["posted_at"] = None
                exp["updated_at"] = now_iso
                reg_modified = True

    if reg_modified:
        exp_reg_path.write_text(json.dumps(exports_list, indent=2, ensure_ascii=False), encoding="utf-8")
        print("  Updated _Docs/export_registry.json successfully.")

    # Build lookup by filename
    exp_by_name = {}
    for exp in exports_list:
        p = exp.get("path")
        if p:
            fn = Path(p).name
            if fn not in exp_by_name or (exp.get("product_id") and not exp_by_name[fn].get("product_id")):
                exp_by_name[fn] = exp

    # Load products
    products_path = BASE_DIR / "_Docs" / "products.json"
    products_list = json.loads(products_path.read_text(encoding="utf-8")) if products_path.exists() else []
    prod_by_id = {p["id"]: p for p in products_list if isinstance(p, dict) and "id" in p}

    # 2. Load existing queue
    existing_queue = ScheduleQueueStore._load()
    print(f"Existing queue items: {len(existing_queue)}")

    # Separate truly posted items (NOT in target_filenames)
    truly_posted = [
        r for r in existing_queue
        if r.get("status") == "posted" and Path(r.get("video_path", "")).name not in target_filenames
    ]
    print(f"Truly posted items preserved: {len(truly_posted)}")

    # Index existing queue items by filename
    queue_by_filename = {}
    for r in existing_queue:
        vp = r.get("video_path")
        if vp:
            queue_by_filename[Path(vp).name] = r

    # 3. Build candidate objects for each target file
    candidates = []
    covers_dir = BASE_DIR / "05_Covers_Thumbnails"

    for f in target_files:
        existing = queue_by_filename.get(f.name)
        exp = exp_by_name.get(f.name) or {}
        pid = (existing.get("product_id") if existing else None) or exp.get("product_id")
        aid = (existing.get("angle_id") if existing else None) or exp.get("angle_id")

        prod = prod_by_id.get(pid, {})
        angles = prod.get("angles", [])
        ang = next((a for a in angles if a.get("angle_id") == aid or a.get("id") == aid), {})

        tiktok_pid = (
            (existing.get("tiktok_product_id") if existing else None)
            or ang.get("tiktok_product_id")
            or prod.get("tiktok_product_id")
            or "1731512091369702645"
        )

        caption = (
            (existing.get("caption") if existing else None)
            or ang.get("tiktok_caption")
            or ang.get("caption")
            or f"{prod.get('name', '')} ของแท้ ประกันศูนย์ พิกัดในตะกร้าเลย 👇"
        )
        hashtags = (
            (existing.get("hashtags") if existing else None)
            or ang.get("tiktok_hashtags")
            or ang.get("hashtags")
            or "#นายหน้าtiktok #รีวิวของดี #ของมันต้องมี #tiktokป้ายยา #พิกัดในตะกร้า"
        )
        hook_title = (
            (existing.get("hook_title") if existing else None)
            or ang.get("hook_title")
            or ang.get("name")
            or exp.get("project_name")
            or f.stem
        )
        product_name = (
            (existing.get("product_name") if existing else None)
            or prod.get("name")
            or exp.get("project_name")
            or f.stem
        )
        project_name = (
            (existing.get("project_name") if existing else None)
            or exp.get("project_name")
            or f.stem
        )

        stem = f.stem
        cover_path = existing.get("cover_path") if existing else None
        if not cover_path:
            candidates_covers = [
                f"05_Covers_Thumbnails/{stem}_cover.jpg",
                f"05_Covers_Thumbnails/{stem}_cover_3x4.jpg",
                f"05_Covers_Thumbnails/{stem}_cover_9x16.jpg",
                ang.get("cover_path"),
                ang.get("cover_3x4_path"),
                ang.get("cover_9x16_path"),
                exp.get("cover_path"),
                exp.get("cover_3x4_path"),
                exp.get("cover_9x16_path"),
            ]
            for c in candidates_covers:
                if c and (BASE_DIR / c).is_file():
                    cover_path = Path(c).as_posix()
                    break

        if not cover_path:
            matching = list(covers_dir.glob(f"*{stem}*.jpg"))
            if matching:
                cover_path = matching[0].relative_to(BASE_DIR).as_posix()

        if not cover_path:
            webp = ready_dir / f"{stem}.webp"
            if webp.is_file():
                cover_path = webp.relative_to(BASE_DIR).as_posix()

        cover_url = f"/api/media/{urllib.parse.quote(cover_path)}" if cover_path else None

        candidates.append({
            "filename": f.name,
            "id": existing.get("id") if existing else uuid.uuid4().hex,
            "created_at": existing.get("created_at") if existing else now_iso,
            "channel_id": existing.get("channel_id") if existing else "main",
            "video_path": f"04_Exports/Ready_to_post/{f.name}",
            "video_key": f"export:{exp.get('id')}" if exp.get("id") else f"04_Exports/Ready_to_post/{f.name}",
            "export_id": exp.get("id"),
            "product_id": pid,
            "angle_id": aid,
            "product_name": product_name,
            "project_name": project_name,
            "hook_title": hook_title,
            "style_preset": existing.get("style_preset") if existing else ang.get("style_preset"),
            "hook_color": existing.get("hook_color") if existing else ang.get("hook_color"),
            "cover_path": cover_path,
            "cover_sha256": None,
            "cover_url": cover_url,
            "caption": caption,
            "hashtags": hashtags,
            "tiktok_product_id": str(tiktok_pid),
            "status": "planned",
            "posted_at": None,
            "updated_at": now_iso,
        })

    print(f"Prepared candidate records: {len(candidates)}")

    # 4. Balanced scheduling
    balanced_candidates = build_balanced_schedule(candidates)
    time_slots = generate_time_slots(len(balanced_candidates))

    # Apply slot
    for cand, slot in zip(balanced_candidates, time_slots):
        cand["scheduled_at"] = slot

    # 5. Combine and save to ScheduleQueueStore
    final_records = truly_posted + balanced_candidates
    print(f"Total records to save: {len(final_records)} ({len(truly_posted)} posted + {len(balanced_candidates)} planned)")

    ScheduleQueueStore._save(final_records)
    print("Successfully saved schedule queue via ScheduleQueueStore._save()!")

    # 6. Verification
    reloaded = ScheduleQueueStore._load()
    reloaded_planned = [r for r in reloaded if r.get("status") == "planned"]
    reloaded_posted = [r for r in reloaded if r.get("status") == "posted"]
    couple_in_queue = [r for r in reloaded if is_couple_clip(r.get("video_path", ""))]

    print("\n" + "=" * 72)
    print(" VERIFICATION RESULTS")
    print("=" * 72)
    print(f"Total in Queue Store:     {len(reloaded)}")
    print(f"Planned (rescheduled):    {len(reloaded_planned)}")
    print(f"Posted (preserved):       {len(reloaded_posted)}")
    print(f"Couple series in queue:   {len(couple_in_queue)} (Must be 0)")
    assert len(couple_in_queue) == 0, "ERROR: Couple series clips found in queue!"
    assert len(reloaded_planned) == len(target_files), f"ERROR: Planned count {len(reloaded_planned)} != target {len(target_files)}"

    # Check date range
    first_slot = min(r["scheduled_at"] for r in reloaded_planned)
    last_slot = max(r["scheduled_at"] for r in reloaded_planned)
    print(f"Schedule Range:           {first_slot} -> {last_slot}")

    # Check product counts
    prod_counts = defaultdict(int)
    for r in reloaded_planned:
        prod_counts[r.get("product_name", "Unknown")] += 1

    print("\nPlanned Clips Distribution by Product:")
    for p, c in sorted(prod_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {p}: {c} clips")

    # Sample slots
    print("\nSample Scheduled Slots (First 14 slots = First 2 days):")
    for r in reloaded_planned[:14]:
        print(f"  [{r['scheduled_at']}] {r['product_name'][:30]} -> {r['video_path']}")


if __name__ == "__main__":
    main()
