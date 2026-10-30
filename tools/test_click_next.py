import sys
sys.path.insert(0, '.')
from tools.batch_tiktok_uploader import eval_js, resolve_tab
import time

tid = resolve_tab()
print("Clicking Next on Add link modal...")
res = eval_js('''(() => {
    const root = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal') || document;
    const buttons = Array.from(root.querySelectorAll('button, div[role="button"]'));
    const nextBtn = buttons.reverse().find(b => {
        const t = (b.innerText || b.textContent || '').trim();
        return t === 'ถัดไป' || t === 'Next';
    });
    if (nextBtn) {
        nextBtn.click();
        return { success: true, text: nextBtn.innerText };
    }
    return { success: false };
})()''', tab_id=tid)
print("Click result:", res)
time.sleep(2)

dialogs = eval_js('''Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .TUXModal')).map(d => ({
    text: (d.innerText || "").substring(0, 300),
    classes: d.className
}))''', tab_id=tid)
import json
print("Dialogs after click:", json.dumps(dialogs, indent=2, ensure_ascii=False))
