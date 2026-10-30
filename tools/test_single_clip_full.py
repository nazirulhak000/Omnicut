import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.schedule_store import ScheduleQueueStore
from tools.batch_tiktok_uploader import process_single_clip

sys.stdout.reconfigure(encoding='utf-8')

items = ScheduleQueueStore.list_items()
planned = [c for c in items if c.get('status') == 'planned' and not c.get('is_couple')]
valid = [c for c in planned if c.get('tiktok_product_id') != '1731512091369702645']

print(f"Total valid planned non-couple clips: {len(valid)}")
if valid:
    target = valid[0]
    print(f"Testing 1 Clip: {target['id'][:8]} | {target['product_name']} | Video: {target['video_path']}")
    ok = process_single_clip(target, mode='schedule')
    print(f"Result: {ok}")
