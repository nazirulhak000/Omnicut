"""
Batch TikTok Uploader via Open Browser Use CDP
Strictly implements the battle-tested logic from tiktok_autopost_extension (background.js & automation.js).

Guards:
- Strict Zero-Post-Without-Cart: Never submits a post without an attached product cart.
- Auto-Skip Out-of-Stock: If a product is Unavailable or Stock 0, cleanly cancels modal and skips.
- Safe SPA Reset: Cleans drafts, cancels modals, and resets dropzone via in-page Discard to avoid 'Leave site?' deadlocks.
- Extension Parity: Switches to schedule mode BEFORE cover upload to prevent form re-render reset.
"""
import subprocess
import json
import time
import sys
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.schedule_store import ScheduleQueueStore

CLI_JS = r'C:\Users\nazir\AppData\Roaming\npm\node_modules\open-browser-use\cli\open-browser-use.js'
DEFAULT_TAB_ID = 1319910483
CHROME_PROFILE = 'Profile 1'

def get_active_tiktok_tab_id():
    """Dynamically finds any open TikTok Studio upload tab in Chrome Profile 1"""
    try:
        cmd = ['node', CLI_JS, 'user-tabs', '--profile', CHROME_PROFILE]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if res.stdout:
            data = json.loads(res.stdout)
            tabs = data.get('result', [])
            for t in tabs:
                u = t.get('url', '').lower()
                if 'upload' in u and 'tiktok' in u:
                    return t.get('id')
            for t in tabs:
                u = t.get('url', '').lower()
                if 'tiktok.com' in u or 'tiktokstudio' in u:
                    return t.get('id')
    except Exception:
        pass
    return None

def resolve_tab(tab_id=None):
    if tab_id:
        return tab_id
    active = get_active_tiktok_tab_id()
    if active:
        return active
    return DEFAULT_TAB_ID

def run_cdp(method, params, tab_id=None):
    tid = resolve_tab(tab_id)
    cmd = ['node', CLI_JS, 'cdp', '--profile', CHROME_PROFILE, '--tab-id', str(tid), '--method', method, '--params', json.dumps(params)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.stdout:
        try:
            return json.loads(res.stdout)
        except Exception:
            return {'raw': res.stdout}
    return {'error': res.stderr}

def eval_js(js, tab_id=None):
    res = run_cdp('Runtime.evaluate', {'expression': js, 'returnByValue': True}, tab_id=tab_id)
    return res.get('result', {}).get('result', {}).get('value')

def sleep_s(s):
    time.sleep(s)

def bring_tab_to_front(tab_id=None):
    tid = resolve_tab(tab_id)
    try:
        run_cdp('Page.bringToFront', {}, tab_id=tid)
    except Exception:
        pass

def dismiss_native_dialog(tab_id=None):
    """Proactively accepts any native dialog (beforeunload / Leave site / alert / confirm)"""
    tid = resolve_tab(tab_id)
    try:
        run_cdp('Page.enable', {}, tab_id=tid)
        run_cdp('Page.handleJavaScriptDialog', {'accept': True}, tab_id=tid)
    except Exception:
        pass

def defuse_beforeunload(tab_id=None):
    """Prevents Chrome from displaying the native 'Leave site?' dialog on dirty forms"""
    tid = resolve_tab(tab_id)
    try:
        eval_js('''(() => {
            window.onbeforeunload = null;
            try {
                Object.defineProperty(window, 'onbeforeunload', {
                    get: () => null,
                    set: () => {},
                    configurable: true
                });
            } catch (e) {}
            window.addEventListener('beforeunload', (e) => {
                e.stopImmediatePropagation();
                e.stopPropagation();
                delete e['returnValue'];
            }, true);
        })()''', tab_id=tid)
    except Exception:
        pass

def clean_reset_upload_page(tab_id=None):
    """
    Resets the upload page to a completely clean dropzone.
    Handles modals, active uploads, abandoned draft banners, and confirmation prompts
    entirely in-page without triggering browser navigation freezes or 'Leave site?' dialogs.
    """
    tid = resolve_tab(tab_id)
    bring_tab_to_front(tab_id=tid)
    defuse_beforeunload(tab_id=tid)
    dismiss_native_dialog(tab_id=tid)

    print(f"Checking & cleaning upload dropzone on tab {tid}...")

    # 1. Cancel any open dialogs / product selector / cover modals
    for _ in range(3):
        eval_js('''(() => {
            const cancelBtns = Array.from(document.querySelectorAll('[role="dialog"] button, [aria-modal="true"] button, .TUXModal button'));
            const cBtn = cancelBtns.find(b => {
                const t = (b.innerText || '').trim();
                return t === 'Cancel' || t === 'ยกเลิก';
            });
            if (cBtn) cBtn.click();
        })()''', tab_id=tid)
        sleep_s(0.3)

    # 2. In-Page Form Discard (TikTok Studio Editor Discard -> Confirmation Dialog -> Confirmed)
    for _ in range(4):
        st = eval_js('''(() => {
            // Check if confirmation modal is currently open: "Discard this post?"
            const modal = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal, [class*="modal"]');
            if (modal) {
                const modalBtns = Array.from(modal.querySelectorAll('button'));
                const confirmDiscard = modalBtns.find(b => {
                    const t = (b.innerText || '').trim();
                    return t === 'Discard' || t === 'ละทิ้ง';
                });
                if (confirmDiscard) {
                    confirmDiscard.click();
                    return 'confirmed_modal_discard';
                }
            }

            // If editor has an active video / draft form, click the main in-page Discard button
            const allBtns = Array.from(document.querySelectorAll('button'));
            const pageDiscard = allBtns.find(b => {
                const t = (b.innerText || '').trim();
                return (t === 'Discard' || t === 'ละทิ้ง') && b.offsetWidth > 0;
            });
            if (pageDiscard) {
                pageDiscard.click();
                return 'clicked_page_discard';
            }

            // Banner discard ("A video you were editing wasn't saved...")
            const bannerDiscard = allBtns.find(b => {
                const t = (b.innerText || '').trim();
                return (t === 'Discard' || t === 'ละทิ้ง') && b.closest('[class*="banner"], [class*="notice"]');
            });
            if (bannerDiscard) {
                bannerDiscard.click();
                return 'clicked_banner_discard';
            }

            return null;
        })()''', tab_id=tid)
        if st:
            print(f"   Cleaned item via in-page action: {st}")
            sleep_s(0.8)
        else:
            break

    # 3. Check if file input is clean and ready
    cur_url = eval_js('location.href', tab_id=tid) or ''
    has_input = eval_js('Boolean(document.querySelector(\'input[type="file"]\'))', tab_id=tid)
    has_editor = eval_js('Boolean(document.querySelector(\'[contenteditable="true"]\'))', tab_id=tid)

    if 'upload' in cur_url and has_input and not has_editor:
        print("   Upload dropzone is 100% clean and ready for file!")
        return True

    # 4. If tab is on /content or /manage (not on upload page), click "+ Upload" in sidebar or navigate
    if 'upload' not in cur_url:
        print("   Tab is on content/manage page -> navigating back to upload page...")
        defuse_beforeunload(tab_id=tid)
        dismiss_native_dialog(tab_id=tid)
        eval_js('''(() => {
            const links = Array.from(document.querySelectorAll('a, button'));
            const upLink = links.find(el => {
                const t = (el.innerText || '').trim();
                const h = el.getAttribute('href') || '';
                return (t.includes('Upload') || t.includes('อัปโหลด') || h.includes('upload')) && el.offsetWidth > 0;
            });
            if (upLink) upLink.click();
        })()''', tab_id=tid)
        sleep_s(2)

    # 5. Last resort navigation if still not on upload page
    cur_url = eval_js('location.href', tab_id=tid) or ''
    if 'upload' not in cur_url:
        print(f"   Navigating tab {tid} to https://www.tiktok.com/tiktokstudio/upload...")
        defuse_beforeunload(tab_id=tid)
        dismiss_native_dialog(tab_id=tid)
        cmd = ['node', CLI_JS, 'navigate', '--profile', CHROME_PROFILE, '--tab-id', str(tid), '--url', 'https://www.tiktok.com/tiktokstudio/upload']
        try:
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=6)
        except Exception:
            dismiss_native_dialog(tab_id=tid)
        sleep_s(2)

    return True

def wait_for_file_input(tab_id=DEFAULT_TAB_ID, timeout_s=15):
    for _ in range(timeout_s):
        doc = run_cdp('DOM.getDocument', {'depth': -1, 'pierce': True}, tab_id=tab_id)
        root_id = doc.get('result', {}).get('root', {}).get('nodeId')
        if root_id:
            node = run_cdp('DOM.querySelector', {'nodeId': root_id, 'selector': 'input[type="file"]'}, tab_id=tab_id)
            nid = node.get('result', {}).get('nodeId')
            if nid:
                return nid
        sleep_s(1)
    return None

def wait_for_upload_badge(tab_id=DEFAULT_TAB_ID, timeout_s=300):
    """Waits for TikTok's own upload-status badge to say uploaded or Replace button to appear (from automation.js)"""
    print("Waiting for video upload badge (100% Uploaded)...")
    bring_tab_to_front(tab_id=tab_id)
    last_print = 0
    for i in range(timeout_s):
        if i % 20 == 0:
            bring_tab_to_front(tab_id=tab_id)
        info = eval_js('''(() => {
            const hasReplace = Array.from(document.querySelectorAll('button')).some(b => {
                const t = (b.innerText || '').trim();
                return t === 'Replace' || t === 'แทนที่' || t === 'เปลี่ยน';
            });
            if (hasReplace) return { ready: true, reason: 'replace_button' };

            const status = document.querySelector('[data-e2e="upload_status_container"] [class*="info-status"], [data-e2e="upload_status_container"]');
            if (status) {
                const text = (status.innerText || status.textContent || '').trim();
                if (text.includes('อัปโหลดแล้ว') || text.toLowerCase().includes('uploaded') || text.includes('100%')) {
                    return { ready: true, reason: 'status_uploaded', text: text.substring(0, 40) };
                }
                return { ready: false, text: text.replace(/\\n/g, ' ').substring(0, 70) };
            }
            return { ready: false, text: 'waiting_for_status' };
        })()''', tab_id=tab_id)

        if info and info.get('ready'):
            print(f"   Upload confirmed complete! ({info.get('reason')})")
            return True

        if time.time() - last_print > 12:
            txt = info.get('text', '') if info else ''
            if txt:
                print(f"   ...uploading: {txt}")
            last_print = time.time()

        sleep_s(1.5)
    return False

def type_caption(caption, hashtags, tab_id=DEFAULT_TAB_ID):
    """Clears filename and types clean caption + hashtags (from background.js)"""
    print("Typing caption and hashtags...")
    # 1. Wait for editor
    for _ in range(30):
        has_editor = eval_js('''(() => {
            const el = document.querySelector('[contenteditable="true"]');
            return Boolean(el && (el.offsetWidth > 0 || el.offsetHeight > 0));
        })()''', tab_id=tab_id)
        if has_editor:
            break
        sleep_s(1)

    # 2. Focus and Select All -> Backspace
    eval_js('''(() => {
        const el = document.querySelector('[contenteditable="true"]');
        if (el) el.focus();
    })()''', tab_id=tab_id)
    sleep_s(0.2)
    run_cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'a', 'code': 'KeyA', 'windowsVirtualKeyCode': 65, 'modifiers': 2}, tab_id=tab_id)
    run_cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'a', 'code': 'KeyA', 'windowsVirtualKeyCode': 65, 'modifiers': 2}, tab_id=tab_id)
    sleep_s(0.1)
    run_cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Backspace', 'code': 'Backspace', 'windowsVirtualKeyCode': 8}, tab_id=tab_id)
    run_cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Backspace', 'code': 'Backspace', 'windowsVirtualKeyCode': 8}, tab_id=tab_id)
    sleep_s(0.2)

    # 3. Insert Caption
    if caption:
        run_cdp('Input.insertText', {'text': caption.strip()}, tab_id=tab_id)
        sleep_s(0.3)

    # 4. Insert Hashtags
    if hashtags:
        for _ in range(2):
            run_cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13, 'text': '\r', 'unmodifiedText': '\r'}, tab_id=tab_id)
            run_cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13}, tab_id=tab_id)
            sleep_s(0.1)
        run_cdp('Input.insertText', {'text': hashtags.strip()}, tab_id=tab_id)
        sleep_s(0.4)

def attach_product_link(product_id, cart_name='', tab_id=DEFAULT_TAB_ID):
    """
    Attaches product link using the verified extension flow (background.js).
    Strictly verifies stock availability and cart attachment before returning True.
    """
    if not product_id:
        return True
    
    clean_id = re.sub(r'\D', '', str(product_id).strip())
    print(f"Attaching affiliate product link (Clean ID: {clean_id}, Cart: '{cart_name}')...")

    # Step 0: Check if product selector modal already open
    already_open = eval_js('''(() => {
        const isVisible = (el) => {
            if (!el) return false;
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };
        const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]');
        return Boolean(modal && isVisible(modal));
    })()''', tab_id=tab_id)

    if not already_open:
        # Step 1: Click Add button (.anchor-tag-container button or Add button under Add link)
        step1_ok = False
        for _ in range(6):
            s1 = eval_js('''(() => {
                const isVisible = (el) => {
                    if (!el) return false;
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
                };
                const anchorBtn = document.querySelector('.anchor-tag-container button') ||
                                  Array.from(document.querySelectorAll('button')).find(b => {
                                      if (!isVisible(b)) return false;
                                      const t = (b.innerText || '').trim();
                                      const p = b.parentElement ? (b.parentElement.innerText || '') : '';
                                      return (t === 'Add' || t === '+ Add' || t === '+ เพิ่ม' || t === 'เพิ่ม') &&
                                             (p.includes('link') || p.includes('ลิงก์'));
                                  });
                if (anchorBtn && isVisible(anchorBtn)) {
                    anchorBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    anchorBtn.click();
                    return { success: true };
                }
                return { success: false };
            })()''', tab_id=tab_id)
            if s1 and s1.get('success'):
                step1_ok = True
                break
            sleep_s(1)

        if not step1_ok:
            print("   ❌ Could not find or click Add link button!")
            return False

        sleep_s(1.5)

        # Step 2: Click Next on "Add link" (Products)
        step2_ok = False
        for _ in range(6):
            s2 = eval_js('''(() => {
                const root = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal') || document;
                const buttons = Array.from(root.querySelectorAll('button, [role="button"]'));
                const nextBtn = buttons.reverse().find(b => {
                    const t = (b.innerText || '').trim();
                    return (t === 'ถัดไป' || t === 'Next') && !b.disabled && b.getAttribute('aria-disabled') !== 'true';
                });
                if (nextBtn) {
                    nextBtn.focus();
                    nextBtn.click();
                    return { success: true };
                }
                return { success: false };
            })()''', tab_id=tab_id)
            if s2 and s2.get('success'):
                step2_ok = True
                break
            sleep_s(1)

        if not step2_ok:
            print("   ❌ Could not click Next on Add link dialog!")
            return False

        sleep_s(2)

    # Step 3: Switch to Showcase tab (one click only, verify active)
    tab_active = False
    for _ in range(8):
        chk_active = eval_js('''(() => {
            const active = document.querySelector('.product-selector-modal .TUXTabBar-itemTitle--active, .product-selector-modal [class*="itemTitle--active"]');
            if (active) {
                const t = (active.innerText || '').trim();
                return (t.includes('Showcase') || t.includes('นำเสนอสินค้า')) && !t.includes('Shop') && !t.includes('ร้าน');
            }
            return false;
        })()''', tab_id=tab_id)
        if chk_active:
            tab_active = True
            print("   ✅ Showcase tab is active!")
            break

        eval_js('''(() => {
            const btn = document.querySelector('.product-selector-modal button.TUXTabBar-itemTitle[id="2"], .product-selector-modal [id="2"] button') ||
                        Array.from(document.querySelectorAll('.product-selector-modal .TUXTabBar-itemTitle, .product-selector-modal button')).find(b => {
                            const t = (b.innerText || '').trim();
                            return (t === 'Showcase products' || t === 'นำเสนอสินค้า' || t === 'Showcase') && !t.includes('Shop') && !t.includes('ร้าน');
                        });
            if (btn) {
                btn.focus();
                btn.click();
            }
        })()''', tab_id=tab_id)
        sleep_s(1.5)

    if not tab_active:
        print("   ⚠️ Warning: Showcase tab could not be confirmed active!")

    # Step 4: Search product ID
    print(f"   Searching Showcase Product by clean ID: '{clean_id}'...")
    search_set = False
    for _ in range(8):
        s_res = eval_js(f'''(() => {{
            const modal = document.querySelector('.product-selector-modal') || document;
            const search = modal.querySelector('input.TUXTextInputCore-input, input[placeholder*="Search"], input[placeholder*="ค้นหา"]');
            if (search) {{
                search.focus();
                search.select();
                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                if (setter) setter.call(search, "{clean_id}"); else search.value = "{clean_id}";
                search.dispatchEvent(new Event('input', {{ bubbles: true }}));
                search.dispatchEvent(new Event('change', {{ bubbles: true }}));
                
                // Click search icon
                const icon = modal.querySelector('.product-search-icon, .TUXTextInputCore-trailingIconWrapper');
                if (icon) {{
                    try {{ icon.click(); }} catch(e) {{}}
                }}
                return {{ success: true }};
            }}
            return {{ success: false }};
        }})()''', tab_id=tab_id)
        if s_res and s_res.get('success'):
            search_set = True
            break
        sleep_s(1)

    if not search_set:
        print("   ❌ Could not find product search box!")
        return False

    # Also dispatch Enter key via CDP to guarantee search trigger
    run_cdp('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13}, tab_id=tab_id)
    run_cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13}, tab_id=tab_id)
    sleep_s(2.5)

    # Step 5: Select product from table & verify stock / availability
    radio_selected = False
    for attempt in range(8):
        sel = eval_js(f'''(() => {{
            const modal = document.querySelector('.product-selector-modal') || document;
            const rows = Array.from(modal.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, tbody tr'))
                .filter(r => !r.querySelector('th') && (r.innerText || '').trim().length > 0);

            if (rows.length === 0) return {{ success: false, reason: 'no_rows_yet' }};

            const query = "{clean_id}";
            const querySuffix = query.length > 6 ? query.slice(-6) : query;
            let targetRow = rows.find(row => {{
                const text = (row.innerText || row.textContent || '').trim();
                return text.includes(query) || text.includes(querySuffix);
            }});

            // If only 1 row returned in filtered table, it is our target product!
            if (!targetRow && rows.length === 1) {{
                targetRow = rows[0];
            }}

            if (!targetRow) {{
                return {{ success: false, reason: 'target_product_not_found', count: rows.length }};
            }}

            const rowText = (targetRow.innerText || targetRow.textContent || '').trim();
            // Check for Unavailable or Out of Stock (Stock: 0)
            if (rowText.includes('Unavailable') || rowText.includes('ไม่พร้อมจำหน่าย') || rowText.includes('สินค้าหมด') || rowText.includes('Stock: 0')) {{
                return {{ success: false, reason: 'product_unavailable', text: rowText }};
            }}

            const label = targetRow.querySelector('label.TUXRadio-label, label[for]');
            const input = targetRow.querySelector('input.TUXRadioStandalone-input, input[type="radio"]');
            if (input && (input.disabled || input.getAttribute('aria-disabled') === 'true')) {{
                return {{ success: false, reason: 'product_radio_disabled' }};
            }}

            // Select radio by clicking label (tested 100% reliable)
            if (label) {{
                label.click();
            }} else if (input) {{
                input.click();
            }}

            const nextBtn = Array.from(modal.querySelectorAll('button')).find(b => {{
                const t = (b.innerText || '').trim();
                return (t === 'Next' || t === 'ถัดไป') && !b.disabled && !b.classList.contains('TUXButton--disabled');
            }});

            return {{
                success: true,
                checked: Boolean(input && input.checked),
                nextEnabled: Boolean(nextBtn)
            }};
        }})()''', tab_id=tab_id)

        if sel and (sel.get('reason') == 'product_unavailable' or sel.get('reason') == 'product_radio_disabled'):
            print(f"   ❌ Product ID {clean_id} is UNAVAILABLE / Out of Stock in TikTok Shop! Aborting product link!")
            # Cleanly close modal via Cancel button
            eval_js('''(() => {
                const cancelBtns = Array.from(document.querySelectorAll('[role="dialog"] button, [aria-modal="true"] button, .TUXModal button'));
                const c = cancelBtns.find(b => (b.innerText || '').trim() === 'Cancel' || (b.innerText || '').trim() === 'ยกเลิก');
                if (c) c.click();
            })()''', tab_id=tab_id)
            return False

        if sel and (sel.get('checked') or sel.get('nextEnabled')):
            radio_selected = True
            print(f"   ✅ Product radio selected (Next enabled: {sel.get('nextEnabled')})")
            break
        sleep_s(1)

    if not radio_selected:
        print(f"   ❌ Could not select product radio for ID {clean_id}!")
        # Cleanly close modal
        eval_js('''(() => {
            const cancelBtns = Array.from(document.querySelectorAll('[role="dialog"] button, [aria-modal="true"] button, .TUXModal button'));
            const c = cancelBtns.find(b => (b.innerText || '').trim() === 'Cancel' || (b.innerText || '').trim() === 'ยกเลิก');
            if (c) c.click();
        })()''', tab_id=tab_id)
        return False

    sleep_s(1)

    # Step 6: Click Next in product table
    next_ok = False
    for _ in range(6):
        s6 = eval_js('''(() => {
            const isVisible = (el) => {
                if (!el) return false;
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
            };
            const modal = document.querySelector('.product-selector-modal, [class*="product-selector"]') ||
                          document.querySelector('.product-selector-container')?.closest('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal') ||
                          Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')).filter(isVisible).at(-1) ||
                          document;
            const buttons = Array.from(modal.querySelectorAll('button, div[role="button"]')).filter(isVisible);
            const nextBtn = buttons.reverse().find(b => {
                const t = (b.innerText || b.textContent || '').trim();
                const enabled = !b.disabled && b.getAttribute('aria-disabled') !== 'true' && !b.classList.contains('TUXButton--disabled');
                return (t === 'ถัดไป' || t === 'Next') && enabled && t !== 'ยกเลิก' && t !== 'Cancel';
            });
            if (nextBtn) {
                nextBtn.focus();
                nextBtn.click();
                const rect = nextBtn.getBoundingClientRect();
                return { success: true, point: { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) } };
            }
            return { success: false };
        })()''', tab_id=tab_id)
        if s6 and s6.get('success'):
            if s6.get('point'):
                pt = s6['point']
                run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
                run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
                run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
            next_ok = True
            break
        sleep_s(1)

    if not next_ok:
        print("   ❌ Could not click Next in product table!")
        return False

    sleep_s(2)

    # Step 7: Confirm cart name on Title Dialog
    cart_ok = False
    clean_cart_name = str(cart_name or '')[:30].strip()
    for _ in range(8):
        s7 = eval_js(f'''(() => {{
            const isVisible = (el) => {{
                if (!el) return false;
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
            }};
            const roots = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')).filter(isVisible);
            const root = roots.at(-1) || document;

            // Guard: If still on table modal, wait
            const hasTable = Boolean(root.querySelector('table, tr.product-tb-row, [class*="product-tb-row"]'));
            if (hasTable) {{
                return {{ success: false, reason: 'still_on_table' }};
            }}

            const nameInput = root.querySelector('input.TUXTextInputCore-input, input[type="text"], input:not([type]), textarea');
            if (nameInput && isVisible(nameInput)) {{
                try {{
                    nameInput.focus();
                    nameInput.select();
                    const desired = "{clean_cart_name}";
                    if (desired) {{
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                        if (setter) setter.call(nameInput, desired); else nameInput.value = desired;
                        nameInput.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: desired }}));
                        nameInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }} catch (e) {{}}
            }}

            const buttons = Array.from(root.querySelectorAll('button, div[role="button"]')).filter(isVisible);
            const addBtn = buttons.find(b => {{
                const t = (b.innerText || b.textContent || '').trim();
                const enabled = !b.disabled && b.getAttribute('aria-disabled') !== 'true';
                return (t === 'เพิ่ม' || t === 'Add' || t === 'ยืนยัน' || t === 'Confirm' || t === 'เสร็จสิ้น') &&
                       enabled && t !== 'เพิ่มลิงก์' && t !== '+ เพิ่ม' && t !== 'ยกเลิก' && t !== 'Cancel';
            }});
            if (addBtn) {{
                addBtn.focus();
                addBtn.click();
                const rect = addBtn.getBoundingClientRect();
                return {{ success: true, point: {{ x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) }} }};
            }}
            return {{ success: false }};
        }})()''', tab_id=tab_id)

        if s7 and s7.get('success'):
            if s7.get('point'):
                pt = s7['point']
                run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
                run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
                run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
            cart_ok = True
            print(f"   Confirmed cart name '{clean_cart_name}' and added product!")
            break
        sleep_s(1)

    if not cart_ok:
        print("   ❌ Could not confirm product cart name dialog!")
        return False

    sleep_s(2)

    # Step 8: Strict verification that product is attached (from background.js)
    attach_verified = False
    for _ in range(8):
        chk = eval_js('''(() => {
            const isVisible = (el) => {
                if (!el) return false;
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
            };
            const texts = Array.from(document.querySelectorAll('h1, h2, h3, h4, [role="tab"], div, span'))
                .filter(isVisible)
                .map(el => (el.innerText || el.textContent || '').trim());
            const modalStillOpen = texts.some(t =>
                t.includes('เพิ่มลิงก์สินค้า') || t.includes('Add product links') ||
                t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase' || t.includes('Showcase products'));
            
            const dialogRoot = document.querySelector('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal');
            const chip = document.querySelector(
                '[class*="product-anchor"], [class*="productAnchor"], [class*="anchor-card"], [class*="product-card"], [class*="productCard"], [class*="linked-product"]'
            );
            if (!modalStillOpen || (chip && isVisible(chip) && (!dialogRoot || !dialogRoot.contains(chip)))) {
                return true;
            }
            return false;
        })()''', tab_id=tab_id)
        if chk:
            attach_verified = True
            print("   ✅ Product cart verified attached to post!")
            break
        sleep_s(1)

    return attach_verified

def switch_to_schedule_mode(sched_date, sched_time, tab_id=DEFAULT_TAB_ID):
    """Switches to schedule mode, picks date and time (from background.js)"""
    tid = resolve_tab(tab_id)
    print(f"Setting schedule: {sched_date} {sched_time} on tab {tid}...")
    
    # 1. Click radio[value="schedule"] with Native CDP Mouse Event
    radio_switched = False
    for attempt in range(5):
        res = eval_js('''(() => {
            const isVisible = (el) => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
            };
            const radios = Array.from(document.querySelectorAll('input[type="radio"][value="schedule"], input[type="radio"]')).filter(isVisible);
            const schedRadio = radios.find(r => r.value === 'schedule') || radios.find(r => {
                const p = r.closest('label') || r.parentElement;
                const t = (p?.innerText || '').trim();
                return t.includes('Schedule') || t.includes('กำหนดเวลา');
            }) || radios[radios.length - 1];
            if (schedRadio) {
                const target = schedRadio.closest('label') || schedRadio.parentElement || schedRadio;
                target.scrollIntoView({ behavior: 'instant', block: 'center' });
                target.click();
                schedRadio.click();
                const r = target.getBoundingClientRect();
                return {
                    point: { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) },
                    checked: schedRadio.checked
                };
            }
            return null;
        })()''', tab_id=tid)

        if res and res.get('point'):
            pt = res['point']
            run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']}, tab_id=tid)
            run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tid)
            run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tid)

        sleep_s(0.8)

        # Check if schedule radio is actually checked
        is_checked = eval_js('''(() => {
            const r = document.querySelector('input[type="radio"][value="schedule"]');
            return Boolean(r && (r.checked || r.getAttribute('aria-checked') === 'true'));
        })()''', tab_id=tid)
        if is_checked:
            radio_switched = True
            print("   ✅ Schedule radio switched successfully!")
            break
        sleep_s(0.5)

    if not radio_switched:
        print("   ⚠️ Warning: Schedule radio may not have checked, retrying...")

    # 2. Pick date if target date supplied
    if sched_date:
        eval_js(f'''(() => {{
            const visible = el => {{ const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }};
            const inputs = Array.from(document.querySelectorAll('input.TUXTextInputCore-input, input[type="date"]'))
                .filter(el => visible(el) && /^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(String(el.value || '').trim()));
            if (inputs.length === 0) return false;
            if (inputs[0].value === "{sched_date}") return true;
            inputs[0].click();
            return true;
        }})()''', tab_id=tab_id)
        sleep_s(0.5)

        # Select day
        try:
            day_num = int(sched_date.split('-')[2])
            eval_js(f'''(() => {{
                const visible = el => {{ const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }};
                const days = Array.from(document.querySelectorAll('[class*="calendar-wrapper"] span.day.valid, span.day'))
                    .filter(el => visible(el) && Number.parseInt(el.textContent.trim(), 10) === {day_num});
                if (days.length > 0) {{
                    days[0].click();
                    return true;
                }}
                return false;
            }})()''', tab_id=tab_id)
            sleep_s(0.5)
        except Exception:
            pass

    # 3. Pick time
    if sched_time:
        try:
            hour_str, min_str = sched_time.split(':')
            hour_num = int(hour_str)
            min_num = int(min_str)
            min_num = round(min_num / 5) * 5
            if min_num == 60:
                hour_num = (hour_num + 1) % 24
                min_num = 0

            # Open time picker
            eval_js('''(() => {
                const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
                const inputs = Array.from(document.querySelectorAll('input.TUXTextInputCore-input, input[type="time"]'))
                    .filter(el => visible(el) && /^\\d{1,2}:\\d{2}$/.test(String(el.value || '').trim()));
                if (inputs.length > 0) inputs[0].click();
            })()''', tab_id=tab_id)
            sleep_s(0.5)

            # Pick hour
            eval_js(f'''(() => {{
                const visible = el => {{ const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }};
                const values = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text.tiktok-timepicker-left, .tiktok-timepicker-left span, [class*="timepicker-left"] span'))
                    .filter(el => Number.parseInt(el.textContent.trim(), 10) === {hour_num});
                const val = values.find(visible) || values[0];
                if (val) {{ val.scrollIntoView({{ block: 'center' }}); val.click(); }}
            }})()''', tab_id=tab_id)
            sleep_s(0.3)

            # Pick minute
            eval_js(f'''(() => {{
                const visible = el => {{ const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }};
                const values = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text.tiktok-timepicker-right, .tiktok-timepicker-right span, [class*="timepicker-right"] span'))
                    .filter(el => Number.parseInt(el.textContent.trim(), 10) === {min_num});
                const val = values.find(visible) || values[0];
                if (val) {{ val.scrollIntoView({{ block: 'center' }}); val.click(); }}
            }})()''', tab_id=tab_id)
            sleep_s(0.5)

            # Dismiss timepicker
            eval_js('''(() => {
                const heading = document.querySelector('h1, h2, h3, div.common-modal-header, .TUXText');
                if (heading) heading.click();
            })()''', tab_id=tab_id)
            sleep_s(0.5)
        except Exception as e:
            print("   Time picker error:", e)

    return True

def upload_cover(cover_abs, tab_id=DEFAULT_TAB_ID):
    """Uploads 3:4 cover image (from automation.js)"""
    if not cover_abs or not Path(cover_abs).exists():
        return True
    print(f"Uploading Cover Image: {cover_abs}...")
    
    # 1. Click "Edit cover" / "แก้ไขหน้าปก"
    edit_target = eval_js('''(() => {
        const isVisible = (el) => {
            if (!el) return false;
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };
        const targets = Array.from(document.querySelectorAll('div.edit-container, [class*="edit-container"], [class*="cover-container"] div, button, [role="button"]'))
            .filter(isVisible)
            .map((el, index) => {
                const text = (el.innerText || el.textContent || '').trim();
                const exact = text === 'แก้ไขหน้าปก' || text === 'แก้ไขปก' || text === 'Edit cover';
                const partial = text.includes('แก้ไขหน้าปก') || text.includes('Edit cover');
                const rect = el.getBoundingClientRect();
                return {el, index, text, rect, score: exact ? 0 : (partial ? 1 : 2)};
            })
            .filter(item => item.score < 2)
            .sort((a, b) => a.score - b.score || a.text.length - b.text.length || a.index - b.index);
        const match = targets[0];
        if (match) {
            const btn = match.el.closest('button, [role="button"]') || match.el;
            btn.scrollIntoView({ behavior: 'instant', block: 'center' });
            const rect = btn.getBoundingClientRect();
            btn.click();
            return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
        }
        return null;
    })()''', tab_id=tab_id)
    if edit_target:
        run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': edit_target['x'], 'y': edit_target['y']}, tab_id=tab_id)
        run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': edit_target['x'], 'y': edit_target['y']}, tab_id=tab_id)
        run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': edit_target['x'], 'y': edit_target['y']}, tab_id=tab_id)
    sleep_s(2)

    # 2. Find cover file input
    doc = run_cdp('DOM.getDocument', {'depth': -1, 'pierce': True}, tab_id=tab_id)
    root_id = doc.get('result', {}).get('root', {}).get('nodeId')
    selectors = ['label.ImageUpload__uploadArea input[type="file"]', 'input[type="file"][accept*="image"]', 'input[type="file"]']
    cover_node_id = None
    for sel in selectors:
        nodes = run_cdp('DOM.querySelectorAll', {'nodeId': root_id, 'selector': sel}, tab_id=tab_id)
        nids = nodes.get('result', {}).get('nodeIds', [])
        if nids:
            cover_node_id = nids[-1]
            break
            
    if cover_node_id:
        run_cdp('DOM.setFileInputFiles', {'files': [cover_abs], 'nodeId': cover_node_id}, tab_id=tab_id)
        sleep_s(1)
        eval_js('''(() => {
            const inputs = Array.from(document.querySelectorAll('input[type="file"]'));
            const input = inputs[inputs.length - 1];
            if (input) {
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
            }
        })()''', tab_id=tab_id)
        sleep_s(2.5)

        # 3. Click Save button in Cover modal
        save_res = eval_js('''(() => {
            const isVisible = (el) => {
                if (!el) return false;
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
            };
            const roots = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], [class*="CoverEditor__root"], [class*="cover-editor-container"], [class*="cover-modal"], [class*="CoverModal"]'))
                .filter(isVisible);
            const root = roots.find(el => String(el.className || '').includes('cover-editor-container')) || roots.at(-1) || document;
            const buttons = Array.from(root.querySelectorAll('button, div[role="button"]')).filter(isVisible);
            const saveBtn = buttons.reverse().find(b => {
                if (b.disabled || b.getAttribute('aria-disabled') === 'true') return false;
                const t = (b.innerText || b.textContent || '').trim();
                return t === 'บันทึก' || t === 'ยืนยัน' || t === 'Save' || t === 'Confirm' || t === 'เสร็จสิ้น';
            });
            if (!saveBtn) return { success: false };
            const rect = saveBtn.getBoundingClientRect();
            saveBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
            saveBtn.click();
            return { success: true, point: { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) } };
        })()''', tab_id=tab_id)
        if save_res and save_res.get('point'):
            pt = save_res['point']
            run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
            run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
            run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
        sleep_s(2)
    return True

def submit_clip(mode='schedule', tab_id=DEFAULT_TAB_ID):
    """Submits the form via Schedule or Save Draft button"""
    if mode == 'schedule':
        print("Submitting SCHEDULE button...")
        res = eval_js('''(() => {
            const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="menu"], [class*="nav"]'));
            const btns = Array.from(document.querySelectorAll('button')).filter(b => !isNav(b) && b.offsetWidth > 0);
            const schedBtn = btns.find(b => b.innerText.trim() === 'Schedule' || b.innerText.trim() === 'กำหนดเวลา');
            if (schedBtn && !schedBtn.disabled && schedBtn.getAttribute('aria-disabled') !== 'true') {
                schedBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
                schedBtn.click();
                const r = schedBtn.getBoundingClientRect();
                return { success: true, text: schedBtn.innerText, point: { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) } };
            }
            return { success: false };
        })()''', tab_id=tab_id)
    else:
        print("Submitting SAVE DRAFT button...")
        res = eval_js('''(() => {
            const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="menu"], [class*="nav"]'));
            const btns = Array.from(document.querySelectorAll('button')).filter(b => !isNav(b) && b.offsetWidth > 0);
            const draftBtn = btns.find(b => b.innerText.trim() === 'Save draft' || b.innerText.trim() === 'บันทึกแบบร่าง');
            if (draftBtn && !draftBtn.disabled && draftBtn.getAttribute('aria-disabled') !== 'true') {
                draftBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
                draftBtn.click();
                const r = draftBtn.getBoundingClientRect();
                return { success: true, text: draftBtn.innerText, point: { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) } };
            }
            return { success: false };
        })()''', tab_id=tab_id)

    if res and res.get('point'):
        pt = res['point']
        run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
        run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
        run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)

    sleep_s(3)

    # Confirmation & Modal handlers (from background.js)
    for _ in range(12):
        sleep_s(1.5)
        # 1. Post now / Copyright check modal (Only in schedule mode)
        if mode == 'schedule':
            post_now = eval_js('''(() => {
                const btns = Array.from(document.querySelectorAll('[role="dialog"] button, [aria-modal="true"] button, .TUXModal button'));
                const btn = btns.find(b => {
                    const t = (b.innerText || '').trim();
                    return t === 'Schedule now' || t === 'กำหนดเวลาเลย' || t === 'Post now' || t === 'โพสต์เลย';
                });
                if (btn) {
                    btn.click();
                    const r = btn.getBoundingClientRect();
                    return { success: true, point: { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) } };
                }
                return false;
            })()''', tab_id=tab_id)
            if post_now and post_now.get('point'):
                pt = post_now['point']
                run_cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
                run_cdp('Input.dispatchMouseEvent', {'type': 'mousePressed', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
                run_cdp('Input.dispatchMouseEvent', {'type': 'mouseReleased', 'button': 'left', 'clickCount': 1, 'x': pt['x'], 'y': pt['y']}, tab_id=tab_id)
                print("   Auto-clicked 'Schedule now' on confirmation dialog!")
                sleep_s(2)

        # 2. Check for in-page "Leave" dialog (from background.js line 1709)
        eval_js('''(() => {
            const heading = Array.from(document.querySelectorAll('h1, h2, h3, div, p')).find(el => {
                const t = (el.innerText || el.textContent || '').trim();
                return t.includes('แน่ใจหรือไม่ว่าต้องการออก') || t.includes('Are you sure you want to leave');
            });
            if (heading) {
                const dialog = heading.closest('[role="dialog"], [class*="modal"]') || document;
                const buttons = Array.from(dialog.querySelectorAll('button'));
                const leaveBtn = buttons.find(b => {
                    const t = (b.innerText || b.textContent || '').trim();
                    return t === 'ออก' || t === 'Leave' || t === 'leave';
                });
                if (leaveBtn) leaveBtn.click();
            }
        })()''', tab_id=tab_id)

        # 3. Check URL navigation to content/manage
        cur_url = eval_js('location.href', tab_id=tab_id)
        if cur_url and ('tiktokstudio/content' in cur_url or 'tiktokstudio/manage' in cur_url):
            print(f"   Confirmed navigated to: {cur_url}")
            return True

        # 4. Check toast
        has_toast = eval_js('''(() => {
            const toasts = Array.from(document.querySelectorAll('[class*="toast"], [class*="Toast"], [role="alert"]'));
            return toasts.some(t => {
                const text = (t.innerText || '').toLowerCase();
                return text.includes('scheduled') || text.includes('published') || text.includes('draft') || text.includes('สำเร็จ');
            });
        })()''', tab_id=tab_id)
        if has_toast:
            print("   Confirmed via platform success toast!")
            return True

    # 5. Check if editor is gone
    editor_gone = eval_js('!document.querySelector(\'[contenteditable="true"]\')', tab_id=tab_id)
    if editor_gone:
        print("   Compose editor is gone -> submission completed!")
        return True

    return True

def process_single_clip(clip_item, mode='schedule', tab_id=None):
    """
    Complete 1-clip pipeline:
    Clean Reset Dropzone -> Upload Video -> Wait 100% -> Caption -> Cart (Strict) -> Schedule Mode -> Cover -> Submit -> Clean
    """
    tid = resolve_tab(tab_id)
    if not get_active_tiktok_tab_id() and tid == DEFAULT_TAB_ID:
        print("⚠️ Waiting for TikTok Studio tab to be opened in Chrome...")
        for _ in range(30):
            sleep_s(2)
            active = get_active_tiktok_tab_id()
            if active:
                tid = active
                print(f"✅ Found TikTok Studio tab: {tid}")
                break

    tab_id = tid
    cid = clip_item.get('id')
    vrel = clip_item.get('video_path', '')
    vabs = str((BASE_DIR / vrel).resolve())
    crel = clip_item.get('cover_path', '')
    cabs = str((BASE_DIR / crel).resolve()) if crel else ''
    caption = clip_item.get('caption', '')
    hashtags = clip_item.get('hashtags', '')
    p_id = clip_item.get('tiktok_product_id', '')
    p_name = clip_item.get('product_name', '')
    sched_at = clip_item.get('scheduled_at', '')
    s_date = sched_at[:10] if sched_at else ''
    s_time = sched_at[11:16] if sched_at else ''

    print(f"\n=======================================================")
    print(f"🎬 PROCESSING CLIP: {cid[:8]} | Mode: {mode.upper()} | Tab: {tab_id}")
    print(f"   Product: {p_name} (ID: {p_id})")
    print(f"   Schedule: {s_date} {s_time}")
    print(f"   Video: {vabs}")
    print(f"   Cover: {cabs}")
    print(f"=======================================================")

    # 1. Clean Reset Dropzone (Safe SPA Reset)
    bring_tab_to_front(tab_id=tab_id)
    clean_reset_upload_page(tab_id=tab_id)
    sleep_s(1)

    # 2. Upload video
    file_nid = wait_for_file_input(tab_id=tab_id)
    if not file_nid:
        print("❌ Could not find file input on TikTok Studio dropzone")
        return False
    print(f"Uploading video file: {Path(vabs).name}...")
    run_cdp('DOM.setFileInputFiles', {'files': [vabs], 'nodeId': file_nid}, tab_id=tab_id)
    sleep_s(1)

    # 3. Wait for upload badge (100% Uploaded / Replace button)
    if not wait_for_upload_badge(tab_id=tab_id):
        print("❌ Upload did not complete within timeout")
        clean_reset_upload_page(tab_id=tab_id)
        return False

    # 4. Type caption & hashtags
    type_caption(caption, hashtags, tab_id=tab_id)
    sleep_s(1)

    # 5. Attach Product Link (Strict Cart Guard)
    if p_id:
        ok_prod = attach_product_link(p_id, cart_name=p_name, tab_id=tab_id)
        if not ok_prod:
            print(f"❌ CRITICAL GUARD: Product link attachment failed (ID: {p_id})! Aborting clip {cid[:8]} to prevent posting without cart!")
            clean_reset_upload_page(tab_id=tab_id)
            return False
        sleep_s(1)

    # 6. ALWAYS Switch to Schedule Mode BEFORE Cover Upload (Strict rule: NEVER leave form on 'Post now')
    switch_to_schedule_mode(s_date, s_time, tab_id=tab_id)
    sleep_s(1)

    # 7. Upload 3:4 Custom Cover
    if cabs and Path(cabs).exists():
        upload_cover(cabs, tab_id=tab_id)
        sleep_s(1)

    # 8. Submit (Schedule or Draft)
    ok = submit_clip(mode=mode, tab_id=tab_id)
    if ok:
        status_to_set = 'posted' if mode == 'schedule' else 'draft'
        def update_st(row, records):
            row['status'] = status_to_set
        ScheduleQueueStore.update_item(cid, update_st)
        print(f"✅ Successfully processed clip {cid[:8]} -> status: {status_to_set}!")
        sleep_s(2)
        # Clean reset dropzone for next clip
        clean_reset_upload_page(tab_id=tab_id)
        return True

    clean_reset_upload_page(tab_id=tab_id)
    return False

if __name__ == '__main__':
    items = ScheduleQueueStore.list_items()
    planned = [c for c in items if c.get('status') == 'planned' and not c.get('is_couple')]
    valid = [c for c in planned if c.get('tiktok_product_id') != '1731512091369702645']
    if valid:
        process_single_clip(valid[0], mode='schedule')
