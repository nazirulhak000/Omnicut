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
    print(f"Uploading file...", flush=True)
    run_cdp('DOM.setFileInputFiles', {'files': [vabs], 'nodeId': nid}, tab_id=tid)

    if not wait_for_upload_badge(tid, timeout_s=180):
        print("Upload timeout!", flush=True)
        return

    # Click Add
    eval_js('''(() => {
        const btn = document.querySelector('.anchor-tag-container button') ||
                    Array.from(document.querySelectorAll('button')).find(b => {
                        const t = (b.innerText || '').trim();
                        return t === 'Add' || t === '+ Add' || t === '+ เพิ่ม' || t === 'เพิ่ม';
                    });
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

    # Dump all products in the Showcase table
    info = eval_js('''(() => {
        const modal = document.querySelector('.product-selector-modal') || document;
        const rows = Array.from(modal.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, tbody tr'))
            .filter(r => !r.querySelector('th') && (r.innerText || '').trim().length > 0);
        
        const pagination = modal.querySelector('.TUXPagination, [class*="pagination"], [class*="Pagination"]');
        const paginationText = pagination ? pagination.innerText : 'no pagination';
        
        return {
            totalRowsOnPage: rows.length,
            pagination: paginationText,
            products: rows.map(r => {
                const text = (r.innerText || '').trim();
                const input = r.querySelector('input[type="radio"]');
                return {
                    text: text,
                    disabled: input ? input.disabled : null
                };
            })
        };
    })()''', tab_id=tid)

    print("=== ALL SHOWCASE PRODUCTS DUMP ===", flush=True)
    print(json.dumps(info, ensure_ascii=False, indent=2), flush=True)

    # Also clean up
    clean_reset_upload_page(tid)

if __name__ == '__main__':
    run()
