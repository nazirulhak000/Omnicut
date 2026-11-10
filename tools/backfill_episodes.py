#!/usr/bin/env python
"""Give the clips that already went out (posted, or accepted by TikTok as scheduled) their permanent EP numbers.

    python tools/backfill_episodes.py                    # PREVIEW only: nothing is written
    python tools/backfill_episodes.py --apply            # write the numbers shown in the preview
    python tools/backfill_episodes.py --channel main --next 1731     # optional: end the backfill just below 1731

How the numbers are laid out: one number per lineage (product + angle; a clip without them is its own lineage), oldest first, counting
from EP1 (EP1 = the oldest clip that went out); the first number the app issues from now on follows the last one. With `--next N` the
numbers instead END at N-1 and the app continues at N. Nothing is written to TikTok
and no caption of an old post is touched -- the numbers live in the app only. Run it once, before the app issues numbers to new clips
(it refuses to run over numbers that already exist).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import config  # noqa: E402
from scripts.episode_registry import DEFAULT_FIRST_NUMBER, EpisodeRegistry, lineage_key  # noqa: E402
from scripts.export_registry import ExportRegistry  # noqa: E402
from scripts.schedule_store import ScheduleQueueStore  # noqa: E402

SENT_QUEUE_STATUSES = {"posted", "scheduled_on_platform"}


def _stamp(value) -> str:
    """Sortable text of an ISO time (queue rows carry offsets, registry rows do not): the date and clock are what we order by."""
    return str(value or "")[:19]


def collect(channel_id: str):
    """[(first_time, lineage_key, product_id, angle_id, [export ids], title)] oldest first, one entry per lineage."""
    exports = {row["id"]: row for row in ExportRegistry.all(channel_id=channel_id)}
    sent = []   # (time, export_id, product_id, angle_id, title)
    seen_exports = set()
    for row in ScheduleQueueStore.list_items(channel_id=channel_id):
        if row.get("status") not in SENT_QUEUE_STATUSES or not row.get("export_id"):
            continue
        export = exports.get(row["export_id"], {})
        when = row.get("posted_at") or row.get("scheduled_at") or export.get("posted_at") or export.get("created_at")
        sent.append((_stamp(when), row["export_id"], export.get("product_id") or row.get("product_id"),
                     export.get("angle_id") or row.get("angle_id"), row.get("hook_title") or row.get("video_path")))
        seen_exports.add(row["export_id"])
    for export_id, export in exports.items():                     # posted outside the queue
        if export.get("status") == "posted" and export_id not in seen_exports:
            sent.append((_stamp(export.get("posted_at") or export.get("created_at")), export_id, export.get("product_id"),
                         export.get("angle_id"), export.get("project_name") or export.get("path")))
    lineages = {}
    for when, export_id, product_id, angle_id, title in sorted(sent, key=lambda item: (item[0], item[1])):
        key = lineage_key(product_id, angle_id, export_id)
        entry = lineages.setdefault(key, {"first_time": when, "key": key, "product_id": product_id, "angle_id": angle_id,
                                          "export_ids": [], "title": title})
        if export_id not in entry["export_ids"]:
            entry["export_ids"].append(export_id)
    return sorted(lineages.values(), key=lambda entry: (entry["first_time"], entry["key"]))


def plan(channel_id: str, next_number: int):
    entries = collect(channel_id)
    start = next_number - len(entries)
    return entries, start


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--channel", default="main")
    parser.add_argument("--next", type=int, default=None, help="first number the app will issue from now on; the backfill then ends at N-1 (default: count from EP1 and continue after the last)")
    parser.add_argument("--apply", action="store_true", help="write the numbers (default is a preview that writes nothing)")
    args = parser.parse_args(argv)

    registry = EpisodeRegistry(config.BASE_DIR)
    if registry.list(args.channel):
        print(f"ไม่ทำต่อ: ช่อง {args.channel} มีเลข EP ที่ออกไปแล้ว {len(registry.list(args.channel))} เลข (backfill ต้องรันก่อนออกเลขให้คลิปใหม่)")
        return 2
    entries = collect(args.channel)
    next_number = args.next if args.next is not None else len(entries) + DEFAULT_FIRST_NUMBER
    start = next_number - len(entries)
    print(f"ช่อง {args.channel}: คลิป (lineage) ที่ออกไปแล้ว {len(entries)} รายการ")
    if not entries:
        print("ไม่มีอะไรต้องใส่เลข")
        return 0
    if start < 1:
        print(f"ไม่ทำต่อ: ต้องใช้เลข {len(entries)} เลขก่อน EP{next_number} แต่เลขเริ่มต้นจะเป็น {start} (< 1) — ใช้ --next ที่มากกว่านี้")
        return 2
    print(f"จะใส่เลข EP{start} .. EP{next_number - 1} (เก่าสุดก่อน = EP{start}) และคลิปใหม่จะเริ่มที่ EP{next_number}")
    numbered = [(start + index, entry) for index, entry in enumerate(entries)]
    head, tail = (numbered[:4], numbered[-4:]) if len(numbered) > 8 else (numbered, [])
    for n, entry in head:
        print(f"  EP{n}  {entry['first_time'][:16]}  {str(entry['title'])[:60]}")
    if tail:
        print("   ...")
        for n, entry in tail:
            print(f"  EP{n}  {entry['first_time'][:16]}  {str(entry['title'])[:60]}")
    if not args.apply:
        print("\n(ตัวอย่างเท่านั้น ยังไม่ได้เขียนอะไร — ใส่ --apply เพื่อบันทึก)")
        return 0
    for index, entry in enumerate(entries):
        number = start + index
        first = True
        for export_id in entry["export_ids"]:
            registry.ensure(args.channel, product_id=entry["product_id"], angle_id=entry["angle_id"], export_id=export_id,
                            source="backfill", number=number if first else None)
            first = False
    if registry.next_number(args.channel) != next_number:
        registry.set_next(args.channel, next_number)
    print(f"\nเขียนแล้ว {len(entries)} เลข (EP{start}..EP{next_number - 1}) เลขถัดไปที่ระบบจะออก: EP{registry.next_number(args.channel)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
