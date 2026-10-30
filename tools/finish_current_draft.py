import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.batch_tiktok_uploader import eval_js, run_cdp, upload_cover, submit_clip, sleep_s, BASE_DIR
from scripts.schedule_store import ScheduleQueueStore

sys.stdout.reconfigure(encoding='utf-8')
tid = 1319910483

print("1. Clicking Add button on product cart modal...")
res = eval_js("""(() => {
    const btns = Array.from(document.querySelectorAll('[role="dialog"] button, [aria-modal="true"] button, .TUXModal button, button'));
    const addBtn = btns.find(b => (b.innerText || '').trim() === 'Add' || (b.innerText || '').trim() === 'เพิ่ม');
    if (addBtn) {
        const rect = addBtn.getBoundingClientRect();
        addBtn.click();
        return { point: { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) } };
    }
    return null;
})()""", tab_id=tid)

if res and res.get('point'):
    pt = res['point']
    run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']}, tab_id=tid)
    run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tid)
    run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tid)
    print("   Clicked Add button successfully!")

sleep_s(2)

# Check clip in store
cid = '2860fe96bd6f4fb49a8732093650511e'
clip = ScheduleQueueStore.get_item(cid)
if clip:
    crel = clip.get('cover_path', '')
    cabs = str((BASE_DIR / crel).resolve()) if crel else ''
    if cabs and Path(cabs).exists():
        print(f"2. Uploading cover: {cabs}...")
        upload_cover(cabs, tab_id=tid)
        sleep_s(1)

print("3. Submitting SAVE DRAFT...")
ok = submit_clip(mode='draft', tab_id=tid)
if ok:
    def update_st(row, records):
        row['status'] = 'draft'
    ScheduleQueueStore.update_item(cid, update_st)
    print(f"✅ Clip {cid[:8]} saved as draft!")
