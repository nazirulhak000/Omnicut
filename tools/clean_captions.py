#!/usr/bin/env python
"""Take price / discount / promo wording out of the captions of clips that have not been posted yet (rule: no price in TikTok clips).

    python tools/clean_captions.py            # PREVIEW only: nothing is written
    python tools/clean_captions.py --apply    # write the replacements shown in the preview

What it touches: tiktok_caption, tiktok_hashtags, price_deal (and hook_title while the clip is not rendered yet) of every angle that
is NOT posted. A caption with price wording is replaced as a whole by a neutral one ("<product> ดูรายละเอียดในตะกร้าเลยครับ"), never
half-cut. Posted angles are history and are never changed. A rendered clip keeps its hook title (it is inside the video: re-render
the clip to change it) -- those are listed. Spoken script lines are only counted.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.product_store import ProductStore  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes (default: preview)")
    parser.add_argument("--limit", type=int, default=15, help="how many examples to print")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    report = ProductStore.scrub_price_text(apply=args.apply)
    changes = report["changes"]
    by_field: dict = {}
    for change in changes:
        by_field[change["field"]] = by_field.get(change["field"], 0) + 1
    print(f"{'APPLIED' if args.apply else 'PREVIEW'}: {len(changes)} field(s) to rewrite {by_field}")
    for change in changes[:args.limit]:
        print(f"  [{change['status']}] {str(change['product'])[:28]} / {change['angle_id']} / {change['field']}")
        print(f"      -  {str(change['old'])[:100]}")
        print(f"      +  {str(change['new'])[:100]}")
    if len(changes) > args.limit:
        print(f"  ... and {len(changes) - args.limit} more")
    if report["kept_hook"]:
        print(f"{len(report['kept_hook'])} rendered clip(s) keep a price hook title (inside the video; re-render to change):")
        for item in report["kept_hook"][:args.limit]:
            print(f"  {str(item['product_id'])[:8]} / {item['angle_id']} / {item['hook_title'][:70]}")
    print(f"spoken script lines with price wording (not changed): {report['script_lines']}")
    print(f"posted angles left as they are: {report['posted_untouched']}")
    if not args.apply and changes:
        print("Nothing written. Run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
