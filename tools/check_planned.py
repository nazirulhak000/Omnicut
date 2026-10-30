import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.schedule_store import ScheduleQueueStore

sys.stdout.reconfigure(encoding='utf-8')
items = ScheduleQueueStore.list_items(all_channels=True)
non_couple = [x for x in items if not x.get('is_couple')]
planned = [x for x in non_couple if x.get('status') == 'planned']
posted = [x for x in non_couple if x.get('status') == 'posted']
drafts = [x for x in non_couple if x.get('status') == 'draft']

print(f"Total non-couple: {len(non_couple)}")
print(f"Posted: {len(posted)}")
print(f"Drafts: {len(drafts)}")
print(f"Planned: {len(planned)}")

print("\n--- NEXT 20 PLANNED CLIPS ---")
for i, c in enumerate(planned[:20]):
    print(f"[{i+1}] {c['id'][:8]} | {c.get('product_name')} | ID: {c.get('tiktok_product_id')} | Sched: {c.get('scheduled_at')}")

# Check Orsen S6
orsen = [c for c in planned if c.get('tiktok_product_id') == '1731512091369702645']
print(f"\nOrsen S6 clips in planned: {len(orsen)}")
