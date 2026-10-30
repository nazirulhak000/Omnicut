import sys
import subprocess
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import (
    resolve_tab, run_cdp, eval_js, sleep_s, clean_reset_upload_page,
    wait_for_file_input, wait_for_upload_badge
)

sys.stdout.reconfigure(encoding='utf-8')
tid = resolve_tab()
print(f"Tab ID: {tid}")

# Reset dropzone cleanly
clean_reset_upload_page(tab_id=tid)

# Set a small test video
test_video = str(BASE_DIR / '04_Exports' / 'Ready_to_post' / 'ESS02-เทียบของเดิม_1_20260916_201005.mp4')
nid = wait_for_file_input(tab_id=tid)
print(f"File input nid: {nid}")
run_cdp('DOM.setFileInputFiles', {'files': [test_video], 'nodeId': nid}, tab_id=tid)

# Wait for editor
for _ in range(40):
    has_ed = eval_js('Boolean(document.querySelector(\'[contenteditable="true"]\'))', tab_id=tid)
    if has_ed:
        print("Editor appeared!")
        break
    sleep_s(1)

# Click Add
eval_js('''(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const btn = btns.find(b => {
        const t = (b.innerText || '').trim();
        const p = b.parentElement ? (b.parentElement.innerText || '') : '';
        const gp = b.parentElement && b.parentElement.parentElement ? (b.parentElement.parentElement.innerText || '') : '';
        return (t === 'Add' || t === 'เพิ่ม') && (p.includes('link') || gp.includes('link'));
    });
    if (btn) btn.click();
})()''', tab_id=tid)
sleep_s(1.5)

# Click Next on Add link
eval_js('''(() => {
    const dialog = document.querySelector('.common-modal-width--medium') || document.querySelector('[role="dialog"]');
    const n = Array.from(dialog.querySelectorAll('button')).find(b => (b.innerText||'').trim() === 'Next');
    if (n) n.click();
})()''', tab_id=tid)
sleep_s(2)

# Click Showcase products
eval_js('''(() => {
    const btn = Array.from(document.querySelectorAll('.TUXTabBar-itemTitle')).find(b => (b.innerText||'').trim() === 'Showcase products');
    if (btn) btn.click();
})()''', tab_id=tid)
sleep_s(2)

# Search Hatari
clean_id = '1730405090572077252'
eval_js(f'''(() => {{
    const s = document.querySelector('input.TUXTextInputCore-input');
    if (s) {{
        s.focus();
        s.select();
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
        if (setter) setter.call(s, "{clean_id}"); else s.value = "{clean_id}";
        s.dispatchEvent(new Event('input', {{ bubbles: true }}));
        s.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}
}})()''', tab_id=tid)

# Click search icon
eval_js('''(() => {
    const icon = document.querySelector('.TUXTextInputCore-trailingIconWrapper');
    if (icon) icon.click();
})()''', tab_id=tid)
run_cdp('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13}, tab_id=tid)
run_cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13}, tab_id=tid)
sleep_s(3)

# Inspect row and radio button
info = eval_js('''(() => {
    const rows = Array.from(document.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr')).filter(r => !r.querySelector('th'));
    return rows.map(r => ({
        text: (r.innerText||'').substring(0, 100),
        radio: Array.from(r.querySelectorAll('input[type="radio"], .TUXRadioStandalone, [class*="Radio"]')).map(el => ({
            tag: el.tagName,
            class: el.className,
            rect: el.getBoundingClientRect(),
            checked: el.checked
        }))
    }));
})()''', tab_id=tid)
print("Rows and radio info:\n", json.dumps(info, ensure_ascii=False, indent=2))
