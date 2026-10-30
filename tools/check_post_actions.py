import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.stdout.reconfigure(encoding='utf-8')

from tools.batch_tiktok_uploader import eval_js

def check_actions():
    res = eval_js('''(() => {
        const rows = Array.from(document.querySelectorAll('[data-tt*="RowLayout"], [class*="RowLayout"], tr, [role="row"]'));
        const targetRow = rows.find(r => (r.innerText || '').includes('Orsen S6'));
        if (!targetRow) return { found: false };
        const buttons = Array.from(targetRow.querySelectorAll('button, svg, [role="button"], div[class*="action"]'));
        return {
            found: true,
            text: targetRow.innerText.slice(0, 200),
            actionButtons: buttons.map(b => ({
                tag: b.tagName,
                cls: b.className,
                aria: b.getAttribute('aria-label'),
                text: b.innerText
            }))
        };
    })()''')
    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    check_actions()
