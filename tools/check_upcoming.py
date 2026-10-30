import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.schedule_store import ScheduleQueueStore

items = ScheduleQueueStore.list_items()
planned = [c for c in items if c.get('status') == 'planned' and not c.get('is_couple')]
valid_pool = [c for c in planned if c.get('tiktok_product_id') != '1731512091369702645']
orsen_clips = [c for c in planned if c.get('tiktok_product_id') == '1731512091369702645']

print(f"Total planned non-couple: {len(planned)}")
print(f"Valid pool: {len(valid_pool)}")
print(f"Orsen clips (out of stock): {len(orsen_clips)}")
print("\nNext 10 planned clips in valid pool:")
for i, c in enumerate(valid_pool[:10]):
    print(f"[{i+1}] {c.get('id')[:8]} | {c.get('product_name')[:25]} | {c.get('video_path')} | product_id={c.get('tiktok_product_id')}")
