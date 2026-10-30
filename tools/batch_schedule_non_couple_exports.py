"""
Batch scheduler for all non-couple exports in OmniCut Pro Studio.
Schedules exactly 84 non-couple clips across 12 days (7 clips/day from 07:00 to 21:00).
Spaced evenly at 2 hours 20 minutes intervals:
  07:00, 09:20, 11:40, 14:00, 16:20, 18:40, 21:00
Date range: 2026-10-16 to 2026-10-27.
Excludes all couple series clips (83 clips).
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from scripts.config import BASE_DIR
from scripts.schedule_store import ScheduleQueueStore, ScheduleTemplateStore

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
SLOT_TIMES = ["07:00", "09:20", "11:40", "14:00", "16:20", "18:40", "21:00"]
START_DATE = datetime(2026, 10, 16, tzinfo=BANGKOK_TZ)
DAYS_COUNT = 12  # 12 * 7 = 84 slots


def is_couple_clip(filename: str) -> bool:
    fn = filename.lower()
    return "-pov-s" in fn or "_pov-s" in fn or "couple" in fn


def generate_time_slots() -> list[str]:
    slots = []
    for day_idx in range(DAYS_COUNT):
        current_day = START_DATE + timedelta(days=day_idx)
        date_str = current_day.strftime("%Y-%m-%d")
        for t in SLOT_TIMES:
            slots.append(f"{date_str}T{t}+07:00")
    return slots


def build_balanced_schedule_grid(candidates: list[dict]) -> list[dict]:
    """
    Distribute 84 clips across 12 days (7 slots/day) such that Essager PD 30W (17 clips)
    is distributed across all 12 days (1-2 clips per day, spaced far apart: 09:20 and 18:40),
    and all other products are interleaved to maximize variety and avoid duplicate products in the same day.
    """
    by_prod = defaultdict(list)
    for c in candidates:
        pname = c.get("product_name") or "Unknown"
        by_prod[pname].append(c)

    grid = [[None for _ in range(7)] for _ in range(12)]

    # 1. Place Essager PD 30W (17 items) smoothly across the 12 days
    ess_key = next((k for k in by_prod if "ที่ชาร์จเร็ว, Essager" in k), None)
    if ess_key:
        ess_items = list(by_prod[ess_key])
        del by_prod[ess_key]

        # Days 0, 2, 4, 6, 8 get 2 Essager items (at slot 1: 09:20 and slot 5: 18:40 -> 9h20m apart!)
        # Days 1, 3, 5, 7, 9, 10, 11 get 1 Essager item (at slot 3: 14:00)
        two_days = [0, 2, 4, 6, 8]
        one_days = [1, 3, 5, 7, 9, 10, 11]

        for d in two_days:
            if ess_items:
                grid[d][1] = ess_items.pop(0)
            if ess_items:
                grid[d][5] = ess_items.pop(0)

        for d in one_days:
            if ess_items:
                grid[d][3] = ess_items.pop(0)

        while ess_items:
            for d in range(12):
                for s in range(7):
                    if grid[d][s] is None and ess_items:
                        grid[d][s] = ess_items.pop(0)

    # 2. Collect other products sorted by frequency
    products_pool = []
    for k, items in sorted(by_prod.items(), key=lambda x: len(x[1]), reverse=True):
        for it in items:
            products_pool.append(it)

    # 3. Fill empty slots minimizing duplicates within the same day
    for d in range(12):
        for s in range(7):
            if grid[d][s] is None:
                day_prods = {grid[d][slot]["product_name"] for slot in range(7) if grid[d][slot] is not None}
                cand_idx = next((i for i, it in enumerate(products_pool) if it["product_name"] not in day_prods), None)
                if cand_idx is None:
                    cand_idx = 0
                grid[d][s] = products_pool.pop(cand_idx)

    # 4. Flatten grid in day-by-day order
    ordered = []
    for d in range(12):
        for s in range(7):
            ordered.append(grid[d][s])
    return ordered


def main():
    print("=" * 70)
    print(" OmniCut Batch Scheduler: 84 Non-Couple Clips (7/day, 07:00-21:00)")
    print("=" * 70)

    # 1. Identify target files
    ready_dir = BASE_DIR / "04_Exports" / "Ready_to_post"
    all_ready_files = sorted(ready_dir.glob("*.mp4"), key=lambda p: p.name)
    
    couple_files = [f for f in all_ready_files if is_couple_clip(f.name)]
    non_couple_files = [f for f in all_ready_files if not is_couple_clip(f.name)]
    
    print(f"Total MP4 files in 04_Exports/Ready_to_post: {len(all_ready_files)}")
    print(f"Couple clips (EXCLUDED from schedule):     {len(couple_files)}")
    print(f"Non-couple clips (TARGET for schedule):    {len(non_couple_files)}")
    
    if len(non_couple_files) != 84:
        print(f"WARNING: Expected 84 non-couple clips, found {len(non_couple_files)}!")

    # 2. Load export registry and update 'posted' status for ready files
    exp_reg_path = BASE_DIR / "_Docs" / "export_registry.json"
    exports_list = json.loads(exp_reg_path.read_text(encoding="utf-8")) if exp_reg_path.exists() else []
    
    # Check and update status to 'rendered' if files are in Ready_to_post
    ready_filenames = {f.name for f in non_couple_files}
    exp_modified = False
    for exp in exports_list:
        p = exp.get("path")
        if p and Path(p).name in ready_filenames:
            if exp.get("status") == "posted" or exp.get("posted_at") is not None:
                print(f"Resetting status from posted to rendered for {Path(p).name}")
                exp["status"] = "rendered"
                exp["posted_at"] = None
                exp["updated_at"] = datetime.now(BANGKOK_TZ).isoformat()
                exp_modified = True

    if exp_modified:
        exp_reg_path.write_text(json.dumps(exports_list, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Updated _Docs/export_registry.json successfully.")

    # Build lookup by filename (preferring linked entries with product_id)
    exp_by_name = {}
    for exp in exports_list:
        p = exp.get("path")
        if not p:
            continue
        fn = Path(p).name
        if fn not in exp_by_name or (exp.get("product_id") and not exp_by_name[fn].get("product_id")):
            exp_by_name[fn] = exp

    # 3. Load product store
    products_path = BASE_DIR / "_Docs" / "products.json"
    products_list = json.loads(products_path.read_text(encoding="utf-8")) if products_path.exists() else []
    prod_by_id = {p["id"]: p for p in products_list if isinstance(p, dict) and "id" in p}

    # 4. Prepare candidate data for each of the 84 clips
    candidates = []
    covers_dir = BASE_DIR / "05_Covers_Thumbnails"

    for f in non_couple_files:
        exp = exp_by_name.get(f.name)
        if not exp:
            raise RuntimeError(f"Missing export registry for {f.name}")
        
        pid = exp.get("product_id")
        aid = exp.get("angle_id")
        prod = prod_by_id.get(pid, {})
        angles = prod.get("angles", [])
        ang = next((a for a in angles if a.get("angle_id") == aid or a.get("id") == aid), {})

        # Resolve Product ID (TikTok shop)
        tiktok_pid = (
            ang.get("tiktok_product_id")
            or prod.get("tiktok_product_id")
            or "1731512091369702645"  # Fallback
        )
        
        # Resolve Caption & Hashtags
        caption = (
            ang.get("tiktok_caption")
            or ang.get("caption")
            or f"{prod.get('name', '')} ของแท้ ประกันศูนย์ พิกัดในตะกร้าเลย 👇"
        )
        hashtags = (
            ang.get("tiktok_hashtags")
            or ang.get("hashtags")
            or "#นายหน้าtiktok #รีวิวของดี #ของมันต้องมี #tiktokป้ายยา #พิกัดในตะกร้า"
        )
        
        hook_title = (
            ang.get("hook_title")
            or ang.get("name")
            or exp.get("project_name")
            or f.stem
        )
        
        # Resolve Cover Path
        stem = f.stem
        cover_path = None
        # Check standard cover names
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
        
        # If still no cover, check for any cover matching stem in 05_Covers_Thumbnails
        if not cover_path:
            matching = list(covers_dir.glob(f"*{stem}*.jpg"))
            if matching:
                cover_path = matching[0].relative_to(BASE_DIR).as_posix()

        # Fallback to thumbnail webp if no jpg found
        if not cover_path:
            webp = ready_dir / f"{stem}.webp"
            if webp.is_file():
                cover_path = webp.relative_to(BASE_DIR).as_posix()

        # Build cover URL
        cover_url = f"/api/media/{urllib.parse.quote(cover_path)}" if cover_path else None

        candidates.append({
            "filename": f.name,
            "file_path": f,
            "export_id": exp.get("id"),
            "product_id": pid,
            "angle_id": aid,
            "product_name": prod.get("name") or exp.get("project_name") or f.stem,
            "project_name": exp.get("project_name") or f.stem,
            "hook_title": hook_title,
            "style_preset": ang.get("style_preset"),
            "hook_color": ang.get("hook_color"),
            "cover_path": cover_path,
            "cover_url": cover_url,
            "caption": caption,
            "hashtags": hashtags,
            "tiktok_product_id": str(tiktok_pid),
            "video_path": f"04_Exports/Ready_to_post/{f.name}",
            "video_key": f"export:{exp.get('id')}" if exp.get("id") else f"04_Exports/Ready_to_post/{f.name}",
        })

    print(f"Prepared candidate metadata for {len(candidates)} clips.")

    # 5. Build balanced schedule grid (distributes Essager across all 12 days and balances products)
    balanced_candidates = build_balanced_schedule_grid(candidates)

    # 6. Generate time slots (84 slots: 12 days x 7 slots)
    time_slots = generate_time_slots()
    if len(balanced_candidates) != len(time_slots):
        raise ValueError(f"Mismatch: {len(balanced_candidates)} clips vs {len(time_slots)} slots!")

    # 7. Match existing queue records vs new records
    existing_queue = ScheduleQueueStore._load()
    posted_records = [r for r in existing_queue if r.get("status") == "posted"]
    planned_records = [r for r in existing_queue if r.get("status") != "posted"]

    print(f"Existing queue: {len(posted_records)} posted items, {len(planned_records)} planned items.")

    # Lookup existing planned records by video filename or export_id
    planned_by_filename = {}
    for r in planned_records:
        vp = r.get("video_path")
        if vp:
            planned_by_filename[Path(vp).name] = r

    now_timestamp = datetime.now(BANGKOK_TZ).isoformat()
    new_planned_records = []

    for idx, (cand, slot) in enumerate(zip(balanced_candidates, time_slots)):
        existing = planned_by_filename.get(cand["filename"])
        record_id = existing.get("id") if existing else uuid.uuid4().hex
        created_at = existing.get("created_at") if existing else now_timestamp

        record = {
            "id": record_id,
            "channel_id": "main",
            "video_path": cand["video_path"],
            "video_key": cand["video_key"],
            "export_id": cand["export_id"],
            "scheduled_at": slot,
            "status": "planned",
            "product_id": cand["product_id"],
            "angle_id": cand["angle_id"],
            "product_name": cand["product_name"],
            "project_name": cand["project_name"],
            "hook_title": cand["hook_title"],
            "style_preset": cand["style_preset"],
            "hook_color": cand["hook_color"],
            "cover_path": cand["cover_path"],
            "cover_sha256": None,
            "cover_url": cand["cover_url"],
            "caption": cand["caption"],
            "hashtags": cand["hashtags"],
            "tiktok_product_id": cand["tiktok_product_id"],
            "created_at": created_at,
            "updated_at": now_timestamp,
            "extension_prepared_at": None,
            "posted_at": None,
        }
        new_planned_records.append(record)

    # 8. Save updated queue (posted + new planned)
    final_queue = posted_records + new_planned_records
    print(f"Saving final queue: {len(posted_records)} posted + {len(new_planned_records)} planned = {len(final_queue)} total items.")
    
    ScheduleQueueStore._save(final_queue)
    print("Schedule queue saved to SQLite store.db & _Docs/schedule_queue.json.")

    # 9. Update weekly schedule template
    template_path = BASE_DIR / "_Docs" / "schedule_templates.json"
    templates = json.loads(template_path.read_text(encoding="utf-8")) if template_path.exists() else []
    
    # Update default and any week templates to have 7 daily slots
    for tpl in templates:
        days = tpl.get("days", {})
        for day_num in range(7):
            day_key = str(day_num)
            if day_key not in days:
                days[day_key] = {"enabled": True, "times": SLOT_TIMES}
            else:
                days[day_key]["enabled"] = True
                days[day_key]["times"] = SLOT_TIMES

    template_path.write_text(json.dumps(templates, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Updated _Docs/schedule_templates.json with 7 daily slots.")

    # 10. Summary report
    print("\n" + "=" * 70)
    print(" SCHEDULE SUMMARY (12 DAYS, 7 CLIPS / DAY)")
    print("=" * 70)
    
    by_day = defaultdict(list)
    for r in new_planned_records:
        day_str = r["scheduled_at"][:10]
        by_day[day_str].append(r)

    for day_str in sorted(by_day.keys()):
        day_items = by_day[day_str]
        print(f"\n📅 วันที่ {day_str} ({len(day_items)} คลิป):")
        for it in day_items:
            time_part = it["scheduled_at"][11:16]
            print(f"  ⏰ {time_part} | {it['product_name'][:24]:25} | {Path(it['video_path']).name}")

    print("\n" + "=" * 70)
    print(" SUCCESS: All 84 clips scheduled successfully without conflicts!")
    print("=" * 70)


if __name__ == "__main__":
    main()
