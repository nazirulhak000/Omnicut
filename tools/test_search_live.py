import sys
sys.path.insert(0, '.')
from tools.batch_tiktok_uploader import eval_js, resolve_tab
import time
import json

sys.stdout.reconfigure(encoding='utf-8')
tid = resolve_tab()

dump = eval_js('''(() => {
    const s = document.querySelector('.product-selector-modal input.TUXTextInputCore-input');
    if (!s) return 'not found';
    const parent = s.parentElement;
    const grandparent = parent ? parent.parentElement : null;
    return {
        inputTag: s.tagName,
        inputClass: s.className,
        inputPlaceholder: s.placeholder,
        inputValue: s.value,
        parentHTML: parent ? parent.outerHTML : null,
        grandparentHTML: grandparent ? grandparent.outerHTML.substring(0, 500) : null
    };
})()''', tab_id=tid)
print("Search Container Dump:", json.dumps(dump, indent=2, ensure_ascii=False))

# Press Enter on the input element
press_enter = eval_tab('''(() => {
    const input = document.querySelector('input.TUXTextInputCore-input[placeholder*="Search"], input[placeholder*="Search products"]');
    if (!input) return false;
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
    input.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
    input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
    
    // Also click search icon if present
    const icon = input.parentElement ? input.parentElement.querySelector('.TUXTextInputCore-trailingIconWrapper, svg, button') : null;
    if (icon) {
        try { icon.click(); } catch(e) {}
    }
    return true;
})()''', tid)
print("Press enter via JS:", press_enter)

# Also dispatch Enter via CDP
cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', str(tid), '--method', 'Input.dispatchKeyEvent', '--params', json.dumps({'type': 'rawKeyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13})]
subprocess.run(cmd, capture_output=True, text=True)
cmd = ['node', CLI_JS, 'cdp', '--profile', 'Profile 1', '--tab-id', str(tid), '--method', 'Input.dispatchKeyEvent', '--params', json.dumps({'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13})]
subprocess.run(cmd, capture_output=True, text=True)

time.sleep(2.5)

# Check results
rows = eval_tab('''(() => {
    const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]') || document;
    const r = Array.from(modal.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, tbody tr'))
        .filter(x => !x.querySelector('th') && (x.innerText || '').trim().length > 0);
    return r.map(x => ({
        text: (x.innerText || '').trim(),
        hasRadio: Boolean(x.querySelector('input[type="radio"], .TUXRadioStandalone')),
        checked: Boolean(x.querySelector('input:checked, .TUXRadioStandalone--checked'))
    }));
})()''', tid)
print("Rows in table:", json.dumps(rows, indent=2, ensure_ascii=False))
