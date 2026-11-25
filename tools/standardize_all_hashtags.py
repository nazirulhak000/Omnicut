"""
Maintenance tool to standardize all TikTok hashtags in OmniCut Pro Studio.

Enforces:
1. Strict Max 5 Hashtags across all products, angles, and schedule queue.
2. Removes price/discount/promo wording in hashtags.
3. Preserves high-converting booster tags (#TikTokป้ายยา, #ของดีบอกต่อ, #พิกัดในตะกร้า).
4. Synchronizes both ProductStore (SQLite + _Docs/products.json) and ScheduleQueueStore.
"""

import sys
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.hashtag_utils import normalize_tiktok_hashtags
from scripts.product_store import ProductStore
from scripts.schedule_store import ScheduleQueueStore


def run_standardization(apply: bool = True):
    print(f"=== Running TikTok Hashtags Standardization (Apply={apply}) ===")

    # 1. ProductStore
    print("\n1. Standardizing ProductStore angles...")
    res = ProductStore.standardize_hashtags(apply=apply, include_posted=True)
    changes = res.get("changes", [])
    print(f"   Total angles modified: {len(changes)}")
    if changes:
        print("   Sample changes:")
        for c in changes[:5]:
            print(f"     [{c.get('product')}] Angle: {c.get('angle_id')}")
            print(f"       Old: {c.get('old')}")
            print(f"       New: {c.get('new')}")

    # 2. ScheduleQueueStore
    print("\n2. Standardizing ScheduleQueueStore items...")
    queue_changes = 0
    with ScheduleQueueStore.transaction(all_channels=True) as items:
        for item in items:
            raw_tags = item.get("hashtags")
            if not raw_tags:
                continue
            norm = normalize_tiktok_hashtags(raw_tags, product_name=item.get("product_name"), max_count=5)
            if norm != raw_tags:
                queue_changes += 1
                if apply:
                    item["hashtags"] = norm

    print(f"   Total queue items modified: {queue_changes}")

    # 3. Verification & Summary
    print("\n3. Verification after standardization:")
    all_prods = ProductStore.snapshot(all_channels=True)
    all_tags = []
    for p in all_prods:
        for a in p.get("angles", []):
            t = a.get("tiktok_hashtags") or a.get("hashtags")
            if t:
                all_tags.append(t)

    lengths = [len(t.split()) if isinstance(t, str) else len(t) for t in all_tags]
    cnt = Counter(lengths)
    print(f"   Current hashtag lengths distribution across {len(all_tags)} angles:")
    for length in sorted(cnt):
        print(f"     {length} hashtags: {cnt[length]} angles")

    over_5 = sum(c for l, c in cnt.items() if l > 5)
    print(f"\n   Total angles exceeding 5 hashtags: {over_5}")
    if over_5 == 0:
        print("   ✅ SUCCESS: 100% of angles now have <= 5 hashtags!")
    else:
        print(f"   ⚠️ WARNING: Still {over_5} angles exceeding 5 hashtags.")


if __name__ == "__main__":
    apply_mode = "--preview" not in sys.argv
    run_standardization(apply=apply_mode)
