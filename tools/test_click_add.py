import sys
sys.path.insert(0, '.')
from tools.batch_tiktok_uploader import eval_js, resolve_tab
import time

tid = resolve_tab()
print("Clicking Add button in .anchor-tag-container...")
res = eval_js('''(() => {
    const btn = document.querySelector('.anchor-tag-container button') ||
                Array.from(document.querySelectorAll('button')).find(b => (b.innerText || '').trim() === 'Add');
    if (btn) {
        btn.scrollIntoView({ behavior: 'instant', block: 'center' });
        btn.click();
        return { success: true, text: btn.innerText };
    }
    return { success: false };
})()''', tab_id=tid)
print("Click result:", res)
time.sleep(1.5)

dialogs = eval_js('''Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .TUXModal')).map(d => ({
    text: (d.innerText || "").substring(0, 200),
    classes: d.className
}))''', tab_id=tid)
import json
print("Dialogs after click:", json.dumps(dialogs, indent=2, ensure_ascii=False))
