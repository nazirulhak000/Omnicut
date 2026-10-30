import sys, json, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import (
    clean_reset_upload_page, wait_for_file_input, wait_for_upload_badge,
    eval_js, run_cdp, sleep_s, resolve_tab
)

def run():
    sys.stdout.reconfigure(encoding='utf-8')
    tid = resolve_tab()
    clean_reset_upload_page(tid)
    sleep_s(1)

    vabs = str((BASE_DIR / "04_Exports/Ready_to_post/ess02-pov-chat-28s.mp4").resolve())
    nid = wait_for_file_input(tid)
    print("Uploading file...", flush=True)
    run_cdp('DOM.setFileInputFiles', {'files': [vabs], 'nodeId': nid}, tab_id=tid)

    if not wait_for_upload_badge(tid, timeout_s=180):
        print("Upload timeout!", flush=True)
        return

    # Click Add
    eval_js('''(() => {
        const btn = document.querySelector('.anchor-tag-container button') ||
                    Array.from(document.querySelectorAll('button')).find(b => (b.innerText||'').trim() === 'Add');
        if (btn) btn.click();
    })()''', tab_id=tid)
    sleep_s(1.5)

    # Click Next
    eval_js('''(() => {
        const root = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal') || document;
        const nextBtn = Array.from(root.querySelectorAll('button')).reverse().find(b => (b.innerText||'').trim() === 'Next' || (b.innerText||'').trim() === 'ถัดไป');
        if (nextBtn) nextBtn.click();
    })()''', tab_id=tid)
    sleep_s(2)

    # Click Showcase
    eval_js('''(() => {
        const btn = document.querySelector('.product-selector-modal button.TUXTabBar-itemTitle[id="2"], .product-selector-modal [id="2"] button') ||
                    Array.from(document.querySelectorAll('.product-selector-modal .TUXTabBar-itemTitle')).find(b => (b.innerText||'').trim() === 'Showcase products');
        if (btn) btn.click();
    })()''', tab_id=tid)
    sleep_s(2.5)

    all_products = []
    
    # Iterate through pages 1 to 7
    for page_num in range(1, 8):
        # Click page if > 1
        if page_num > 1:
            eval_js(f'''(() => {{
                const modal = document.querySelector('.product-selector-modal') || document;
                const pages = Array.from(modal.querySelectorAll('.TUXPagination-item, [class*="Pagination"] li, [class*="pagination"] *'));
                const p = pages.find(el => (el.innerText || '').trim() === '{page_num}');
                if (p) p.click();
            }})()''', tab_id=tid)
            sleep_s(2)

        page_products = eval_js('''(() => {
            const modal = document.querySelector('.product-selector-modal') || document;
            const rows = Array.from(modal.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, tbody tr'))
                .filter(r => !r.querySelector('th') && (r.innerText || '').trim().length > 0);
            return rows.map(r => (r.innerText || '').trim().replace(/\\t/g, ' '));
        })()''', tab_id=tid)
        
        print(f"--- PAGE {page_num} ({len(page_products)} items) ---", flush=True)
        for p in page_products:
            # First line of text
            first_line = p.split('\\n')[0]
            # Find 19-digit ID if present
            import re
            m = re.search(r'17\d{17}', p)
            pid = m.group(0) if m else 'no-id'
            print(f"  [{pid}] {first_line[:50]}", flush=True)
            all_products.append({'page': page_num, 'id': pid, 'text': first_line})

    clean_reset_upload_page(tid)
    print(f"\nTOTAL SHOWCASE PRODUCTS DUMPED: {len(all_products)}", flush=True)

if __name__ == '__main__':
    run()
