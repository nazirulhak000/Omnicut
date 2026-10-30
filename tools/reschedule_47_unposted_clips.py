"""
Reschedule 47 unposted clips (43 planned + 4 draft) in OmniCut Pro Studio.
Starts tomorrow (2026-10-20) at 07:00, 7 slots/day:
  07:00, 09:20, 11:40, 14:00, 16:20, 18:40, 21:00
Across 7 days: 2026-10-20 to 2026-10-26 (last day 5 slots = 47 total slots).
Smooth product interleaving:
  - Essager PD 30W (9 clips) placed across all 7 days (max 2/day spaced >=9h apart).
  - All other 14 products interleaved with rotating slot positions to eliminate consecutive repeats.
  - Resets all 4 draft clips to planned so all 47 clips are ready for manual posting via Extension.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
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
DATES = [
    "2026-10-20",
    "2026-10-21",
    "2026-10-22",
    "2026-10-23",
    "2026-10-24",
    "2026-10-25",
    "2026-10-26",
]


def generate_slots() -> list[str]:
    slots = []
    for d_idx, d in enumerate(DATES):
        times = SLOT_TIMES if d_idx < 6 else SLOT_TIMES[:5]
        for t in times:
            slots.append(f"{d}T{t}+07:00")
    return slots


def build_balanced_grid(candidates: list[dict]) -> list[dict]:
    by_prod = defaultdict(list)
    for c in candidates:
        pname = c.get("product_name") or "Unknown"
        by_prod[pname].append(c)

    # 7 days: 6 days of 7 slots, 1 day of 5 slots
    grid = [
        [None] * 7,
        [None] * 7,
        [None] * 7,
        [None] * 7,
        [None] * 7,
        [None] * 7,
        [None] * 5,
    ]

    # 1. Essager PD 30W (9 items)
    ess_key = next((k for k in by_prod if "ที่ชาร์จเร็ว, Essager" in k), None)
    if ess_key:
        ess_items = list(by_prod[ess_key])
        del by_prod[ess_key]

        # Day 0: 09:20 (slot 1) and 18:40 (slot 5) - spaced 9h20m apart
        grid[0][1] = ess_items.pop(0)
        grid[0][5] = ess_items.pop(0)

        # Day 3: 09:20 (slot 1) and 18:40 (slot 5) - spaced 9h20m apart
        grid[3][1] = ess_items.pop(0)
        grid[3][5] = ess_items.pop(0)

        # Days 1, 2, 4, 5, 6: rotated afternoon/midday slots
        grid[1][3] = ess_items.pop(0)  # 14:00
        grid[2][4] = ess_items.pop(0)  # 16:20
        grid[4][2] = ess_items.pop(0)  # 11:40
        grid[5][3] = ess_items.pop(0)  # 14:00
        grid[6][2] = ess_items.pop(0)  # 11:40
        assert len(ess_items) == 0, f"Unplaced Essager items: {len(ess_items)}"

    # 2. Group other items
    prod_items = sorted(by_prod.items(), key=lambda x: len(x[1]), reverse=True)

    # Place products with rotation across days and slots
    for pname, items in prod_items:
        placed = 0
        for d in range(7):
            if placed >= len(items):
                break
            slot_count = 7 if d < 6 else 5
            day_prods = {grid[d][s]["product_name"] for s in range(slot_count) if grid[d][s] is not None}
            if pname in day_prods:
                continue
            # Pick slot rotating by day
            pref_slots = [(d * 2 + offset) % slot_count for offset in range(slot_count)]
            for s in pref_slots:
                if grid[d][s] is None:
                    grid[d][s] = items[placed]
                    placed += 1
                    break

    # 3. Check remaining empty slots
    empty_slots = []
    for d in range(7):
        slot_count = 7 if d < 6 else 5
        for s in range(slot_count):
            if grid[d][s] is None:
                empty_slots.append((d, s))

    # 4. Check items left to place
    leftover_items = []
    for pname, items in prod_items:
        placed_count = sum(
            1
            for d in range(7)
            for s in range(7 if d < 6 else 5)
            if grid[d][s] and grid[d][s]["product_name"] == pname
        )
        if placed_count < len(items):
            for it in items[placed_count:]:
                leftover_items.append(it)

    # Fill remaining empty slots
    for it in leftover_items:
        pname = it["product_name"]
        cand = None
        for d, s in empty_slots:
            slot_count = 7 if d < 6 else 5
            day_prods = {grid[d][slot]["product_name"] for slot in range(slot_count) if grid[d][slot] is not None}
            if pname not in day_prods:
                cand = (d, s)
                break
        if cand is None:
            cand = empty_slots[0]
        d, s = cand
        grid[d][s] = it
        empty_slots.remove(cand)

    assert len(empty_slots) == 0, f"Remaining empty slots: {len(empty_slots)}"

    # 5. Flatten grid
    ordered = []
    for d in range(7):
        slot_count = 7 if d < 6 else 5
        for s in range(slot_count):
            ordered.append(grid[d][s])

    return ordered


def main():
    print("=" * 70)
    print(" OmniCut Rescheduler: 47 Unposted Clips (7 slots/day, 2026-10-20 to 2026-10-26)")
    print("=" * 70)

    # 1. Load all current items from store
    all_items = ScheduleQueueStore.list_items(all_channels=True)
    print(f"Total items in schedule queue: {len(all_items)}")

    # 2. Filter unposted items (planned + draft)
    unposted_items = [item for item in all_items if item.get("status") in ("planned", "draft")]
    posted_items = [item for item in all_items if item.get("status") not in ("planned", "draft")]

    print(f"Posted items (preserved untouched): {len(posted_items)}")
    print(f"Unposted items to reschedule:       {len(unposted_items)}")
    assert len(unposted_items) == 47, f"Expected 47 unposted items, found {len(unposted_items)}"

    # 3. Generate slots
    target_slots = generate_slots()
    assert len(target_slots) == 47, f"Expected 47 target slots, generated {len(target_slots)}"
    print(f"Generated slots: {len(target_slots)} slots from {target_slots[0]} to {target_slots[-1]}")

    # 4. Build balanced grid
    ordered_items = build_balanced_grid(unposted_items)
    assert len(ordered_items) == 47, f"Expected 47 ordered items, got {len(ordered_items)}"

    # 5. Update items with new schedule and status='planned'
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    updated_unposted = []

    for slot, item in zip(target_slots, ordered_items):
        updated_item = dict(item)
        updated_item["scheduled_at"] = slot
        updated_item["status"] = "planned"
        updated_item["updated_at"] = now_iso
        updated_unposted.append(updated_item)

    # 6. Combine and save to store
    # Keep original ordering: posted items + updated unposted items
    final_records = posted_items + updated_unposted
    print(f"Saving final records to store: {len(final_records)} total items")
    ScheduleQueueStore._save(final_records)

    # 7. Verification
    reloaded = ScheduleQueueStore.list_items(all_channels=True)
    reloaded_active = [r for r in reloaded if r.get("status") != "posted"]
    print(f"Verification: Reloaded active queue count: {len(reloaded_active)}")
    assert len(reloaded_active) == 47

    # Check that all active items have status 'planned'
    statuses = {r.get("status") for r in reloaded_active}
    print(f"Active queue statuses: {statuses}")
    assert statuses == {"planned"}

    # Check zero duplicate slot collisions in active queue
    active_slots = [r.get("scheduled_at") for r in reloaded_active]
    assert len(active_slots) == len(set(active_slots)), "Found duplicate scheduled_at in active queue!"
    print("Zero collision verified: all 47 slots are distinct!")

    # 8. Print Schedule Summary Table
    print("\n" + "=" * 70)
    print(" NEW SCHEDULE SUMMARY (7 DAYS, 2026-10-20 to 2026-10-26)")
    print("=" * 70)

    by_date = defaultdict(list)
    for r in updated_unposted:
        d = r["scheduled_at"][:10]
        by_date[d].append(r)

    for d in sorted(by_date.keys()):
        items_today = by_date[d]
        print(f"\n📅 วันที่ {d} ({len(items_today)} คลิป):")
        for it in items_today:
            t = it["scheduled_at"][11:16]
            pname = (it.get("product_name") or "Unknown")[:32]
            proj = it.get("project_name") or ""
            vpath = Path(it.get("video_path") or "").name
            print(f"   [{t}] {pname:<32} | {proj:<24} | {vpath}")

    print("\n" + "=" * 70)
    print(" ✅ Rescheduling 47 clips completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
