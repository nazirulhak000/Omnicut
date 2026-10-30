import sys
sys.path.insert(0, '.')
from tools.probe_tab import eval_tab, get_active_tab

tid = get_active_tab()
res = eval_tab('''(() => {
    const isVisible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
    };
    const texts = Array.from(document.querySelectorAll('h1, h2, h3, h4, [role="tab"], div, span'))
        .filter(isVisible)
        .map(el => (el.innerText || el.textContent || '').trim());
    const matches = texts.filter(t => t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase' || t.includes('Showcase products'));
    return {
        already_open: matches.length > 0,
        matches: matches.slice(0, 10)
    };
})()''', tid)
print("Result:", res)
