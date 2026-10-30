import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from tools.batch_tiktok_uploader import eval_js, run_cdp, sleep_s

def find_orsen_showcase():
    # 1. Click "+ Add" under Add link
    print("Clicking + Add link...")
    eval_js('''(() => {
        const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"]'));
        const allButtons = Array.from(document.querySelectorAll('button, div[role="button"], span'));
        const addBtn = allButtons.find(el => {
            if (isNav(el)) return false;
            const text = (el.innerText || el.textContent || '').trim();
            return text === '+ เพิ่ม' || text === '+เพิ่ม' || text === '+ Add' || text === '+Add' ||
                ((text.startsWith('+') || text.includes('+')) && (text.includes('เพิ่ม') || text.includes('Add')) && text.length < 15);
        });
        if (addBtn) addBtn.click();
    })()''')
    sleep_s(1.5)

    # 2. Click Next on link type
    print("Clicking Next on link type...")
    eval_js('''(() => {
        const root = document.querySelector('[role="dialog"], [aria-modal="true"]') || document;
        const buttons = Array.from(root.querySelectorAll('button, div[role="button"]'));
        const nextBtn = buttons.reverse().find(b => {
            const t = (b.innerText || b.textContent || '').trim();
            return t === 'ถัดไป' || t === 'Next';
        });
        if (nextBtn) nextBtn.click();
    })()''')
    sleep_s(2)

    # 3. Switch to Showcase tab
    print("Switching to Showcase tab...")
    eval_js('''(() => {
        const tabs = Array.from(document.querySelectorAll('.TUXTabBar-item, button, [role="tab"]'));
        const scTab = tabs.find(t => (t.innerText || '').includes('Showcase') || (t.innerText || '').includes('นำเสนอสินค้า'));
        if (scTab) scTab.click();
    })()''')
    sleep_s(1.5)

    # 4. Search "Orsen"
    print("Typing 'Orsen' into search box...")
    eval_js('''(() => {
        const search = document.querySelector('input.TUXTextInputCore-input, .product-search-input input, input[placeholder*="ค้นหา"], input[placeholder*="Search"]');
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

    # 5. Get rows
    rows = eval_js('''(() => {
        const rList = Array.from(document.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, [role="row"], tbody tr'))
            .filter(r => r.offsetWidth > 0 && !r.querySelector('th'));
        return rList.map(r => ({
            text: (r.innerText || '').trim(),
            radioDisabled: Boolean(r.querySelector('input[type="radio"]:disabled, [class*="disabled"]'))
        }));
    })()''')
    print("Found rows for 'Orsen':", json.dumps(rows, indent=2, ensure_ascii=False))

    # Close modal by clicking Cancel
    eval_js('''(() => {
        const cancelBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === 'Cancel' || b.innerText.trim() === 'ยกเลิก');
        if (cancelBtn) cancelBtn.click();
    })()''')

if __name__ == '__main__':
    find_orsen_showcase()
