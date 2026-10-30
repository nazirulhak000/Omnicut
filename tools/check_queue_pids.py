import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from scripts.schedule_store import ScheduleQueueStore

def check_pids():
    items = ScheduleQueueStore.list_items()
    planned = [c for c in items if c.get('status') == 'planned' and not c.get('is_couple')]
    
    products = {}
    for c in planned:
        pid = c.get('tiktok_product_id', '')
        pname = c.get('product_name', '')
        if pid not in products:
            products[pid] = {'name': pname, 'count': 0}
        products[pid]['count'] += 1

    print("Unique Products in Planned Queue:")
    for pid, info in products.items():
        print(f"ID: {pid} | Count: {info['count']} | Name: {info['name'][:40]}")

if __name__ == '__main__':
    check_pids()
