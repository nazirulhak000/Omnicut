import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from tools.batch_tiktok_uploader import eval_js, run_cdp, sleep_s

def check_btns():
    btns = eval_js('''(() => {
        const rows = Array.from(document.querySelectorAll('[data-tt*="RowLayout"], [class*="RowLayout"], tr, [role="row"]'));
        const row = rows.find(r => (r.innerText || '').includes('Orsen S6'));
        if (!row) return null;
        return Array.from(row.querySelectorAll('button')).map((b, i) => {
            const r = b.getBoundingClientRect();
            return {
                index: i,
                className: b.className,
                text: b.innerText,
                point: { x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2) }
            };
        });
    })()''')
    print(json.dumps(btns, indent=2, ensure_ascii=False))

    if btns and len(btns) > 1:
        # The last button is usually the 3 dots action menu
        last_b = btns[-1]
        print(f"Clicking button {last_b['index']} at point {last_b['point']}...")
        pt = last_b['point']
        run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']})
        run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']})
        run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']})
        sleep_s(1.5)

        # Check all visible elements on body
        menu_items = eval_js('''(() => {
            const all = Array.from(document.querySelectorAll('div, li, span, button, p')).filter(el => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && el.childElementCount === 0;
            });
            return all.map(el => el.innerText.trim()).filter(t => t === 'Delete' || t === 'ลบ' || t === 'Edit' || t === 'แก้ไข' || t.includes('Delete') || t.includes('ลบ'));
        })()''')
        print("Menu items found:", menu_items)

if __name__ == '__main__':
    check_btns()
