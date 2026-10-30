import sys
sys.path.insert(0, '.')
from tools.batch_tiktok_uploader import eval_js, resolve_tab, CLI_JS
import time
import json
import subprocess

sys.stdout.reconfigure(encoding='utf-8')
tid = resolve_tab()
print("1. Selecting radio on product row...")
sel_res = eval_js('''(() => {
    const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]') || document;
    const rows = Array.from(modal.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], tbody tr'))
        .filter(r => !r.querySelector('th'));
    if (rows.length === 0) return { success: false, reason: 'no rows' };
    const row = rows[0];
    
    const clickTarget = row.querySelector('.TUXRadioStandalone') ||
                        row.querySelector('.TUXRadio') ||
                        row.querySelector('input[type="radio"]') ||
                        row;
    
    clickTarget.scrollIntoView({ behavior: 'instant', block: 'center' });
    clickTarget.click();
    const rect = clickTarget.getBoundingClientRect();
    const input = row.querySelector('input[type="radio"]');
    return {
        success: true,
        checked: Boolean(input && input.checked),
        hasCheckedClass: Boolean(row.querySelector('[class*="--checked"]')),
        point: { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) }
    };
})()''', tid)
print("Select radio result:", json.dumps(sel_res, indent=2))

if sel_res.get('point'):
    pt = sel_res['point']
    cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', str(tid), '--method', 'Input.dispatchMouseEvent', '--params', json.dumps({'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']})]
    subprocess.run(cmd, capture_output=True, text=True)
    cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', str(tid), '--method', 'Input.dispatchMouseEvent', '--params', json.dumps({'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']})]
    subprocess.run(cmd, capture_output=True, text=True)
    cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', str(tid), '--method', 'Input.dispatchMouseEvent', '--params', json.dumps({'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']})]
    subprocess.run(cmd, capture_output=True, text=True)

time.sleep(1)

# Check Next button status
next_status = eval_js('''(() => {
    const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]') || document;
    const btns = Array.from(modal.querySelectorAll('button'));
    const nextBtn = btns.find(b => (b.innerText || '').trim() === 'Next' || (b.innerText || '').trim() === 'ถัดไป');
    if (nextBtn) {
        return {
            found: true,
            disabled: nextBtn.disabled,
            classes: nextBtn.className
        };
    }
    return { found: false };
})()''', tid)
print("Next button status:", json.dumps(next_status, indent=2))
