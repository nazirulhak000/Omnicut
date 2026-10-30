import sys
sys.path.insert(0, '.')
from tools.batch_tiktok_uploader import eval_js, resolve_tab
import time
import json

sys.stdout.reconfigure(encoding='utf-8')
tid = resolve_tab()
print("Clicking Showcase products tab...")
res = eval_js('''(() => {
    const isVisible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
    };
    const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]') || document;
    const all = Array.from(modal.querySelectorAll('*')).filter(isVisible);
    const target = all.find(el => {
        const t = (el.innerText || el.textContent || '').trim();
        return (t === 'Showcase products' || t === 'นำเสนอสินค้า' || t === 'Showcase') && el.children.length === 0;
    });
    if (target) {
        const clickable = target.closest('button, [role="tab"], .TUXTabBar-item') || target;
        clickable.focus();
        clickable.click();
        const r = clickable.getBoundingClientRect();
        return { success: true, text: target.innerText, tag: clickable.tagName, class: clickable.className };
    }
    return { success: false };
})()''', tab_id=tid)
print("Click result:", json.dumps(res, indent=2))
time.sleep(2)

modal_text = eval_js('''(() => {
    const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]');
    return modal ? modal.innerText.substring(0, 300) : 'modal not found';
})()''', tab_id=tid)
print("Modal text after click:", modal_text)
