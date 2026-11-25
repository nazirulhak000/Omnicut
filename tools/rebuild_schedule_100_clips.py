"""
Rebuild schedule queue for 100 clips across 10 days (10 clips/day from 06:30 to 22:15).
Rule 1: All never-posted products are scheduled first (1 clip each continuously).
Rule 2: From clip 15 onwards, round-robin through all available products (10 distinct products per day).
Rule 3: Preserves all 173 historical posted / scheduled_on_platform items.
"""
import json
import uuid
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_PATH = Path(__file__).resolve().parent.parent
if str(BASE_PATH) not in sys.path:
    sys.path.insert(0, str(BASE_PATH))

from scripts.config import BASE_DIR
from scripts.schedule_store import ScheduleQueueStore, now_iso
from scripts.cart_name_cleaner import get_clean_cart_name

PROJECT_TZ = ZoneInfo("Asia/Bangkok")

products_list = json.load(open(BASE_DIR / "_Docs" / "products.json", encoding="utf-8"))
products_map = {p["id"]: p for p in products_list}
exports = json.load(open(BASE_DIR / "_Docs" / "export_registry.json", encoding="utf-8"))
queue = ScheduleQueueStore.list_items(all_channels=True)

# 1. Preserve posted and scheduled_on_platform items
preserved_items = [q for q in queue if q.get("status") in ("posted", "scheduled_on_platform")]
posted_pids = set()
for q in preserved_items:
    if q.get("status") == "posted" and q.get("product_id"):
        posted_pids.add(q["product_id"])

# Also check export registry posted status
for e in exports:
    if (e.get("status") == "posted" or e.get("is_posted")) and e.get("product_id"):
        posted_pids.add(e.get("product_id"))

# 2. Gather valid unposted exports that exist on disk
unposted_by_pid = {}
for e in exports:
    if e.get("status") == "posted" or e.get("is_posted"):
        continue
    p = e.get("path") or e.get("export_path")
    if not p:
        continue
    full_p = Path(p) if Path(p).is_absolute() else BASE_DIR / p
    if not full_p.exists():
        continue
    pid = e.get("product_id")
    if pid and pid in products_map:
        unposted_by_pid.setdefault(pid, []).append(e)

never_pids = [pid for pid in unposted_by_pid if pid not in posted_pids]
already_pids = [pid for pid in unposted_by_pid if pid in posted_pids]

daily_slots = ["06:30", "08:15", "10:00", "11:45", "13:30", "15:15", "17:00", "18:45", "20:30", "22:15"]
start_date = dt.date(2026, 11, 23)
total_days = 10

scheduled_plan = []
clip_pools = {pid: list(clips) for pid, clips in unposted_by_pid.items()}

# Day 1: 10 clips from never-posted products 0..9
for i in range(10):
    pid = never_pids[i]
    clip = clip_pools[pid].pop(0)
    slot_dt = dt.datetime.combine(start_date, dt.time.fromisoformat(daily_slots[i]), tzinfo=PROJECT_TZ)
    scheduled_plan.append((slot_dt, clip, pid))

# Day 2:
# slots 0..3: remaining 4 never-posted products (10..13)
for i in range(4):
    pid = never_pids[10 + i]
    clip = clip_pools[pid].pop(0)
    slot_dt = dt.datetime.combine(start_date + dt.timedelta(days=1), dt.time.fromisoformat(daily_slots[i]), tzinfo=PROJECT_TZ)
    scheduled_plan.append((slot_dt, clip, pid))

# slots 4..9 of Day 2: 6 distinct already-posted products
for i in range(6):
    pid = already_pids[i]
    clip = clip_pools[pid].pop(0)
    slot_dt = dt.datetime.combine(start_date + dt.timedelta(days=1), dt.time.fromisoformat(daily_slots[4 + i]), tzinfo=PROJECT_TZ)
    scheduled_plan.append((slot_dt, clip, pid))

# Days 3..10:
all_pids = list(unposted_by_pid.keys())
for d_idx in range(2, total_days):
    cur_date = start_date + dt.timedelta(days=d_idx)
    available = [p for p in all_pids if len(clip_pools[p]) > 0]
    available.sort(key=lambda p: len(clip_pools[p]), reverse=True)
    day_pids = available[:10]
    for s_idx, pid in enumerate(day_pids):
        clip = clip_pools[pid].pop(0)
        slot_dt = dt.datetime.combine(cur_date, dt.time.fromisoformat(daily_slots[s_idx]), tzinfo=PROJECT_TZ)
        scheduled_plan.append((slot_dt, clip, pid))

print(f"Generated {len(scheduled_plan)} scheduled plan items.")

# 3. Build rich queue records
# Load cover bindings mapping (by export_id and by video filename)
bindings_file = BASE_DIR / "_Docs" / "export_cover_bindings.json"
cover_bindings_by_export = {}
cover_bindings_by_stem = {}
if bindings_file.exists():
    try:
        with open(bindings_file, "r", encoding="utf-8") as f:
            b_list = json.load(f)
            for b in b_list:
                eid = b.get("export_id")
                v_path = b.get("video_path") or ""
                v_stem = Path(v_path).stem if v_path else ""
                sels = b.get("selections") or {}
                p34 = (sels.get("3:4") or {}).get("path")
                p916 = (sels.get("9:16") or {}).get("path")
                chosen = p34 or p916
                if chosen:
                    if eid:
                        cover_bindings_by_export[eid] = chosen
                    if v_stem:
                        cover_bindings_by_stem[v_stem] = chosen
    except Exception as e:
        print(f"Warning loading cover bindings: {e}")

def get_cover_info(export_item, project_name):
    # 1. Check export bindings first (both by ID and by stem)
    eid = export_item.get("id") or export_item.get("export_id")
    p = export_item.get("path") or export_item.get("export_path") or ""
    p_stem = Path(p).stem if p else ""

    bound_rel = cover_bindings_by_export.get(eid) or cover_bindings_by_stem.get(p_stem)
    if bound_rel:
        full_bound = BASE_DIR / bound_rel
        if full_bound.exists():
            rel_c = str(bound_rel).replace("\\", "/")
            return rel_c, f"/api/media/{rel_c}"

    # 2. Check 05_Covers_Thumbnails recursively for 3:4 cover
    covers_dir = BASE_DIR / "05_Covers_Thumbnails"
    if p_stem:
        for match in covers_dir.glob(f"**/*{p_stem}*_cover_3x4.jpg"):
            if match.is_file():
                rel_c = str(match.relative_to(BASE_DIR)).replace("\\", "/")
                return rel_c, f"/api/media/{rel_c}"

    if project_name:
        for match in covers_dir.glob(f"**/*{project_name}*_cover_3x4.jpg"):
            if match.is_file():
                rel_c = str(match.relative_to(BASE_DIR)).replace("\\", "/")
                return rel_c, f"/api/media/{rel_c}"

    # 3. Check 05_Covers_Thumbnails recursively for standard cover
    if p_stem:
        for match in covers_dir.glob(f"**/*{p_stem}*_cover.jpg"):
            if match.is_file():
                rel_c = str(match.relative_to(BASE_DIR)).replace("\\", "/")
                return rel_c, f"/api/media/{rel_c}"

    if project_name:
        for match in covers_dir.glob(f"**/*{project_name}*_cover.jpg"):
            if match.is_file():
                rel_c = str(match.relative_to(BASE_DIR)).replace("\\", "/")
                return rel_c, f"/api/media/{rel_c}"

    # 4. Fallback to webp video thumbnail only if no custom cover exists
    if p:
        p_path = Path(p)
        webp_path = p_path.with_suffix(".webp")
        if webp_path.exists():
            rel_c = str(webp_path.relative_to(BASE_DIR)).replace("\\", "/") if webp_path.is_absolute() else str(webp_path).replace("\\", "/")
            return rel_c, f"/api/media/{rel_c}"

    return None, None

new_queue_records = []
stamp = now_iso()

for slot_dt, clip, pid in scheduled_plan:
    prod = products_map.get(pid, {})
    pname = clip.get("project_name") or prod.get("name") or "สินค้า"
    aid = clip.get("angle_id") or "angle_1"

    # Find matching angle
    angle = None
    for a in prod.get("angles", []):
        if a.get("project_name") == pname or a.get("angle_id") == aid or a.get("id") == aid:
            angle = a
            break

    # Extract metadata
    hook_title = (angle.get("hook_title") or angle.get("name") or angle.get("tts_hook_title") if angle else None) or pname
    caption = (angle.get("tiktok_caption") or angle.get("caption") if angle else None)
    if not caption:
        caption = f"{hook_title} คุณภาพดี คุ้มค่าที่สุด พิกัดในตะกร้าสีเหลืองซ้ายล่างเลยครับ 👇"
    hashtags = (angle.get("tiktok_hashtags") or angle.get("hashtags") if angle else None)
    if not hashtags:
        hashtags = f"#รีวิวของดี #ของมันต้องมี #tiktokป้ายยา #{prod.get('code', 'GADGET')} #พิกัดในตะกร้า"

    cover_p, cover_u = get_cover_info(clip, pname)
    video_p = clip.get("path") or clip.get("export_path")
    if video_p:
        try:
            video_p = str(Path(video_p).relative_to(BASE_DIR)).replace("\\", "/")
        except Exception:
            video_p = str(video_p).replace("\\", "/")

    record = {
        "id": uuid.uuid4().hex,
        "channel_id": "main",
        "filename": Path(video_p).name if video_p else f"{pname}.mp4",
        "video_path": video_p,
        "video_key": f"export:{clip.get('id', uuid.uuid4().hex)}",
        "export_id": clip.get("id"),
        "product_id": pid,
        "angle_id": aid,
        "product_name": prod.get("name") or pname,
        "cart_name": prod.get("cart_name") or get_clean_cart_name(pid, prod.get("name")),
        "project_name": pname,
        "hook_title": hook_title,
        "style_preset": angle.get("style_preset") if angle else None,
        "hook_color": None,
        "cover_path": cover_p,
        "cover_sha256": None,
        "cover_url": cover_u,
        "caption": caption,
        "hashtags": hashtags,
        "tiktok_product_id": prod.get("tiktok_product_id") or prod.get("tiktok_id"),
        "status": "planned",
        "posted_at": None,
        "created_at": stamp,
        "updated_at": stamp,
        "scheduled_at": slot_dt.isoformat(timespec="minutes"),
    }
    new_queue_records.append(record)

final_all_records = preserved_items + new_queue_records
print(f"Total final records to save: {len(final_all_records)} (Preserved: {len(preserved_items)}, Planned: {len(new_queue_records)})")

ScheduleQueueStore._save(final_all_records)
print("ScheduleQueueStore successfully updated!")
