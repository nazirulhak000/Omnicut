import sys, json, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.batch_tiktok_uploader import (
    clean_reset_upload_page, wait_for_file_input, wait_for_upload_badge,
    eval_js, run_cdp, sleep_s
)

def run():
    sys.stdout.reconfigure(encoding='utf-8')
    tid = 1319910483
    clean_reset_upload_page(tid)
    sleep_s(1)

    vabs = str((BASE_DIR / "04_Exports/Ready_to_post/ess02-pov-chat-28s.mp4").resolve())
    nid = wait_for_file_input(tid)
    print(f"Uploading file...", flush=True)
    run_cdp('DOM.setFileInputFiles', {'files': [vabs], 'nodeId': nid}, tab_id=tid)

    if not wait_for_upload_badge(tid, timeout_s=180):
        print("Upload timeout!", flush=True)
        return

    print("Opening Add Link modal...", flush=True)
    eval_js('''(() => {
        const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"]'));
        const allDivs = Array.from(document.querySelectorAll('div, section, p, span, h1, h2, h3, h4'));
        const header = allDivs.find(el => !isNav(el) && ((el.innerText || el.textContent || '').trim() === 'Add link' || (el.innerText || el.textContent || '').trim() === 'เพิ่มลิงก์'));
        if (header) {
            let parent = header.parentElement;
            for (let i = 0; i < 5 && parent; i++) {
                const btns = Array.from(parent.querySelectorAll('button, div[role="button"]'));
                const btn = btns.find(b => (b.innerText || '').includes('Add') || (b.innerText || '').includes('เพิ่ม'));
                if (btn) { btn.click(); return; }
                parent = parent.parentElement;
            }
        }
    })()''', tab_id=tid)
    sleep_s(1.5)

    eval_js('''(() => {
        const root = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal') || document;
        const btns = Array.from(root.querySelectorAll('button'));
        const nextBtn = btns.reverse().find(b => (b.innerText || '').trim() === 'Next' || (b.innerText || '').trim() === 'ถัดไป');
        if (nextBtn) nextBtn.click();
    })()''', tab_id=tid)
    sleep_s(2)

    # Inspect all tabs in the modal
    tabs_info = eval_js('''(() => {
        const root = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal') || document;
        const all = Array.from(root.querySelectorAll('*'));
        const tabs = all.filter(el => {
            const t = (el.innerText || el.textContent || '').trim();
            return (t.includes('Showcase') || t.includes('นำเสนอ') || t.includes('Shop') || t.includes('ร้าน')) && el.children.length === 0;
        });
        const tabBars = Array.from(root.querySelectorAll('[class*="TabBar"], [class*="tab"], [role="tablist"]'));
        return {
            tabs: tabs.map(t => ({
                text: t.innerText,
                tag: t.tagName,
                class: t.className,
                parentTag: t.parentElement?.tagName,
                parentClass: t.parentElement?.className,
                parentId: t.parentElement?.id,
                containerId: t.closest('[id]')?.id,
                active: t.closest('.TUXTabBar-itemTitle--active, [class*="active"]') !== null
            })),
            tabBars: tabBars.map(b => ({
                tag: b.tagName,
                class: b.className,
                html: b.outerHTML.substring(0, 400)
            }))
        };
    })()''', tab_id=tid)
    print("=== TABS INFO ===", flush=True)
    print(json.dumps(tabs_info, ensure_ascii=False, indent=2), flush=True)

    eval_js('''(() => {
        const target = Array.from(document.querySelectorAll('*')).find(el => {
            const t = (el.innerText || el.textContent || '').trim();
            return (t === 'Showcase products' || t === 'นำเสนอสินค้า' || t === 'Showcase') && el.children.length === 0 && el.offsetWidth > 0;
        });
        if (target) {
            const clickable = target.closest('button, [role="tab"], .TUXTabBar-item') || target;
            clickable.focus();
            clickable.click();
        }
    })()''', tab_id=tid)
    sleep_s(2.5)

    # Search Orsen S6: 1731512091369702645 (the one from user's screenshot!)
    prod_id = "1731512091369702645"
    print(f"Searching Orsen S6 ({prod_id})...", flush=True)
    eval_js(f'''(() => {{
        const root = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal') || document;
        const search = root.querySelector('input[placeholder*="Search"], input[placeholder*="ค้นหา"], .TUXTextInputCore-input');
        if (search) {{
            search.focus();
            search.select();
            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
            if (nativeSetter) nativeSetter.call(search, "{prod_id}");
            else search.value = "{prod_id}";
            search.dispatchEvent(new Event('input', {{ bubbles: true }}));
            search.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            const icon = root.querySelector('.TUXTextInputCore-trailingIconWrapper') ||
                         search.parentElement?.querySelector('svg, button');
            if (icon) icon.click();
        }}
    }})()''', tab_id=tid)
    sleep_s(0.5)

    run_cdp('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13}, tab_id=tid)
    run_cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13}, tab_id=tid)
    sleep_s(3)

    # Inspect modal DOM elements
    info = eval_js('''(() => {
        const root = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal') || document;
        const html = root.innerHTML;
        // Find all elements containing 'Orsen' or '1731512091369702645'
        const all = Array.from(root.querySelectorAll('*'));
        const orsenEls = all.filter(el => (el.innerText || '').includes('Orsen') && el.children.length === 0);
        const radioEls = all.filter(el => el.tagName === 'INPUT' || el.getAttribute('type') === 'radio' || el.className.includes('Radio'));
        
        return {
            modalClasses: root.className,
            orsenElsCount: orsenEls.length,
            orsenElInfo: orsenEls.map(el => ({ tag: el.tagName, class: el.className, text: el.innerText })),
            radioElsInfo: radioEls.map(el => ({ tag: el.tagName, class: el.className, type: el.type, checked: el.checked, disabled: el.disabled })),
            rawTextSample: root.innerText.slice(0, 500)
        };
    })()''', tab_id=tid)

    print("=== DUMP RESULT ===", flush=True)
    print(json.dumps(info, ensure_ascii=False, indent=2), flush=True)

    clean_reset_upload_page(tid)

if __name__ == '__main__':
    run()
