import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from tools.batch_tiktok_uploader import eval_js, run_cdp, sleep_s

def click_popover():
    res = eval_js('''(() => {
        const rows = Array.from(document.querySelectorAll('[data-tt*="RowLayout"], [class*="RowLayout"], tr, [role="row"]'));
        const row = rows.find(r => (r.innerText || '').includes('Orsen S6'));
        if (!row) return { success: false, reason: 'no row' };
        const popoverBtn = row.querySelector('[data-tt="components_ActionCell_Clickable"], [data-tt*="Popover"] button');
        if (!popoverBtn) return { success: false, reason: 'no popover btn' };
        popoverBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
        popoverBtn.click();
        const r = popoverBtn.getBoundingClientRect();
        return { success: true, point: { x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2) } };
    })()''')
    print("Click result:", res)
    if res and res.get('point'):
        pt = res['point']
        run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']})
        run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']})
        run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']})

    sleep_s(1)
    popover_content = eval_js('''(() => {
        const popovers = Array.from(document.querySelectorAll('[class*="popover"], [class*="Popover"], [role="tooltip"], [data-tt*="Popover"]'));
        return popovers.map(p => ({
            html: p.outerHTML.slice(0, 300),
            text: p.innerText
        }));
    })()''')
    print("Popovers:", json.dumps(popover_content, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    click_popover()
