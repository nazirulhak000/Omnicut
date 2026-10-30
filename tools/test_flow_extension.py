import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.schedule_store import ScheduleQueueStore
from tools.batch_tiktok_uploader import (
    resolve_tab, dismiss_native_dialog, navigate_to_upload,
    wait_for_file_input, type_caption, attach_product_link,
    upload_cover, switch_to_schedule_mode, submit_clip,
    sleep_s, run_cdp, eval_js, bring_tab_to_front, BASE_DIR
)

sys.stdout.reconfigure(encoding='utf-8')
tid = resolve_tab()
print(f"Testing on Tab ID: {tid}")

items = ScheduleQueueStore.list_items()
planned = [c for c in items if c.get('status') == 'planned' and not c.get('is_couple')]
valid_planned = [c for c in planned if c.get('tiktok_product_id') != '1731512091369702645']

test_clip = valid_planned[0] # Hatari 16"
cid = test_clip['id']
vabs = str((BASE_DIR / test_clip['video_path']).resolve())
cabs = str((BASE_DIR / test_clip.get('cover_path', '')).resolve()) if test_clip.get('cover_path') else ''
caption = test_clip.get('caption', '')
hashtags = test_clip.get('hashtags', '')
p_id = test_clip.get('tiktok_product_id', '')
p_name = test_clip.get('product_name', '')
sched_at = test_clip.get('scheduled_at', '')
s_date = sched_at[:10] if sched_at else ''
s_time = sched_at[11:16] if sched_at else ''

print(f"\n=======================================================")
print(f"🎬 TEST CLIP: {cid[:8]} | {p_name} (ID: {p_id})")
print(f"=======================================================")

# Step 1: Clean navigation to upload page
bring_tab_to_front(tab_id=tid)
navigate_to_upload(tab_id=tid)
sleep_s(1.5)

# Step 2: Upload file input
file_nid = wait_for_file_input(tab_id=tid)
print(f"File Input Node: {file_nid}")
assert file_nid, "File input not found"
print("Uploading video file...")
run_cdp('DOM.setFileInputFiles', {'files': [vabs], 'nodeId': file_nid}, tab_id=tid)
sleep_s(1)

# Step 3: Wait for caption editor to appear (background.js pattern)
print("Waiting for caption editor...")
editor_ready = False
for _ in range(45):
    has_ed = eval_js('''(() => {
        const el = document.querySelector('[contenteditable="true"]');
        return Boolean(el && (el.offsetWidth > 0 || el.offsetHeight > 0));
    })()''', tab_id=tid)
    if has_ed:
        editor_ready = True
        break
    sleep_s(1)
assert editor_ready, "Caption editor did not appear"
print("   Caption editor ready!")
sleep_s(1)

# Step 4: Type caption & hashtags
type_caption(caption, hashtags, tab_id=tid)
sleep_s(1)

# Step 5: Attach Product Link
print("Attaching product link...")
ok_prod = attach_product_link(p_id, cart_name=p_name, tab_id=tid)
assert ok_prod, "Product link attachment failed"
print("   Product attached successfully!")
sleep_s(1)

# Step 6: Wait for upload to complete before cover/schedule
print("Waiting for video upload to finish before cover upload...")
from tools.batch_tiktok_uploader import wait_for_upload_badge
wait_for_upload_badge(tab_id=tid, timeout_s=150)

# Step 7: Upload Cover
if cabs and Path(cabs).exists():
    upload_cover(cabs, tab_id=tid)
    sleep_s(1)

# Step 8: Schedule Mode
switch_to_schedule_mode(s_date, s_time, tab_id=tid)
sleep_s(1)

# Step 9: Submit
ok_submit = submit_clip(mode='schedule', tab_id=tid)
print(f"Submission result: {ok_submit}")

if ok_submit:
    def update_st(row, records):
        row['status'] = 'posted'
    ScheduleQueueStore.update_item(cid, update_st)
    print(f"🎉 CLIP {cid[:8]} POSTED AND RECORDED!")
