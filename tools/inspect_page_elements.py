import sys, json, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import (
    clean_reset_upload_page, wait_for_file_input, wait_for_upload_badge,
    eval_js, run_cdp, sleep_s, resolve_tab
)

def run():
    sys.stdout.reconfigure(encoding='utf-8')
    tid = resolve_tab()
    clean_reset_upload_page(tid)
    sleep_s(1)

    vabs = str((BASE_DIR / "04_Exports/Ready_to_post/ess02-pov-chat-28s.mp4").resolve())
    nid = wait_for_file_input(tid)
    print(f"Uploading file...", flush=True)
    run_cdp('DOM.setFileInputFiles', {'files': [vabs], 'nodeId': nid}, tab_id=tid)

    if not wait_for_upload_badge(tid, timeout_s=180):
        print("Upload timeout!", flush=True)
        return

    # Inspect all elements on page containing link/add/anchor
    elements = eval_js('''(() => {
        const isVisible = (el) => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        };
        const all = Array.from(document.querySelectorAll('*')).filter(isVisible);
        const matches = all.filter(el => {
            const t = (el.innerText || el.textContent || '').trim().toLowerCase();
            return (t.includes('add') || t.includes('link') || t.includes('anchor') || t.includes('เพิ่ม') || t.includes('ลิงก์')) && el.children.length <= 1;
        });
        return matches.map(el => ({
            tag: el.tagName,
            class: el.className,
            text: (el.innerText || el.textContent || '').trim(),
            rect: { width: el.offsetWidth, height: el.offsetHeight, top: el.offsetTop, left: el.offsetLeft },
            parentTag: el.parentElement?.tagName,
            parentClass: el.parentElement?.className
        }));
    })()''', tab_id=tid)

    print("=== MATCHING ELEMENTS ===", flush=True)
    print(json.dumps(elements, ensure_ascii=False, indent=2), flush=True)

    # Do not clean up yet so we can inspect
if __name__ == '__main__':
    run()
