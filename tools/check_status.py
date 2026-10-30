import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import eval_js, resolve_tab

import json
sys.stdout.reconfigure(encoding='utf-8')
tid = resolve_tab()
print("Tab ID:", tid)
url = eval_js("window.location.href", tab_id=tid)
print("URL:", url)
# Click Add on the title dialog
add_res = eval_js('''(() => {
    const dialogs = Array.from(document.querySelectorAll('.common-modal'));
    const dialog = dialogs.at(-1);
    if (!dialog) return { found: false };
    const btns = Array.from(dialog.querySelectorAll('button'));
    const addBtn = btns.find(b => (b.innerText||'').trim() === 'Add');
    if (addBtn) {
        addBtn.click();
        return { clicked: true, text: addBtn.innerText };
    }
    return { clicked: false };
})()''', tab_id=tid)
print("Click Add result:", json.dumps(add_res, indent=2))

import time
time.sleep(2)

anchors = eval_js('''(() => {
    const els = Array.from(document.querySelectorAll('.anchor-tag-container, [class*="anchor"]'));
    return els.map(e => ({ class: e.className, text: e.innerText }));
})()''', tab_id=tid)
print("Anchors after Add:", json.dumps(anchors, indent=2, ensure_ascii=False))
