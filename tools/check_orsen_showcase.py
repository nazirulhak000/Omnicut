import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from tools.batch_tiktok_uploader import eval_js, run_cdp, sleep_s

def check_orsen_showcase():
    # The modal is currently open right now!
    res = eval_js('''(() => {
        const rows = Array.from(document.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, [role="row"], tbody tr'))
            .filter(r => r.offsetWidth > 0 && !r.querySelector('th'));
        return rows.map(r => (r.innerText || '').trim());
    })()''')
    print("Current table rows in modal:", json.dumps(res, indent=2, ensure_ascii=False))

    # Now let's search "Orsen" to see all Orsen products
    eval_js('''(() => {
        const search = document.querySelector('input.TUXTextInputCore-input, input[placeholder*="ค้นหา"], input[placeholder*="Search"]');
        if (search) {
            search.focus();
            search.select();
            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
            if (nativeSetter) nativeSetter.call(search, "Orsen"); else search.value = "Orsen";
            search.dispatchEvent(new Event('input', { bubbles: true }));
            search.dispatchEvent(new Event('change', { bubbles: true }));
        }
    })()''')
    sleep_s(0.5)
    run_cdp('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13})
    run_cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13})
    sleep_s(2.5)

    res_search = eval_js('''(() => {
        const rows = Array.from(document.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, [role="row"], tbody tr'))
            .filter(r => r.offsetWidth > 0 && !r.querySelector('th'));
        return rows.map(r => (r.innerText || '').trim());
    })()''')
    print("Search 'Orsen' results:", json.dumps(res_search, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    check_orsen_showcase()
