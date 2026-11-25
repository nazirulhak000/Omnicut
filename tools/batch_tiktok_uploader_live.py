"""
Live Batch TikTok Uploader for Day 1 (Nov 23), Day 2 (Nov 24), Day 3 (Nov 25)
30 Clips total (10 clips/day from 06:30 to 22:15).
Uses BrowserClient (direct Playwright / CDP bridge to Chrome Profile 1).
"""
import asyncio
import json
import re
import time
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".tmp"))

from scripts.schedule_store import ScheduleQueueStore
from scripts.cart_name_cleaner import clean_cart_name, sanitize_cart_name
from browser_client import BrowserClient

TAB_ID = 1319918309

class LiveTikTokBatchUploader:
    def __init__(self, tab_id=TAB_ID):
        self.tab_id = tab_id
        self.client = None

    async def connect(self):
        self.client = BrowserClient()
        await self.client.connect()
        # Dynamically find active TikTok Studio tab
        tab_res = await self.client.command("tab list")
        text = tab_res.get("result", {}).get("content", [{}])[0].get("text", "")
        for line in text.splitlines():
            if "TikTok Studio" in line:
                parts = line.strip().split()
                if parts[0] == "*":
                    self.tab_id = int(parts[1])
                elif parts[0].isdigit():
                    self.tab_id = int(parts[0])
        print(f"Connected to BrowserClient on TikTok Studio tab {self.tab_id}")

    async def close(self):
        if self.client:
            await self.client.close()

    async def eval_js(self, js):
        clean_js = " ".join([l.strip() for l in js.splitlines()])
        cmd = f'tab select {self.tab_id}\neval {json.dumps(clean_js)}'
        res = await self.client.command(cmd)
        text = res.get("result", {}).get("content", [{}])[0].get("text", "")
        lines = text.splitlines()
        for i, l in enumerate(lines):
            if l.startswith("✓ eval "):
                val_str = "\n".join(lines[i+1:])
                if "\nPage: " in val_str:
                    val_str = val_str.split("\nPage: ")[0]
                val_str = val_str.strip()
                if val_str == "undefined" or not val_str:
                    return None
                try:
                    return json.loads(val_str)
                except Exception:
                    return val_str
        return None

    async def press_key(self, key):
        return await self.client.command(f'tab select {self.tab_id}\npress {key}')

    async def type_text(self, text):
        escaped = json.dumps(text)
        return await self.client.command(f'tab select {self.tab_id}\ntype {escaped}')

    async def upload_file(self, file_path, target='input[type=file]'):
        p = Path(file_path).resolve()
        # If file is over 45MB and is mp4, transcode to a compressed copy under 45MB
        if p.exists() and p.stat().st_size > 45 * 1024 * 1024 and p.suffix.lower() == '.mp4':
            opt_dir = BASE_DIR / ".tmp" / "upload_opt"
            opt_dir.mkdir(parents=True, exist_ok=True)
            opt_path = opt_dir / p.name
            if not opt_path.exists() or opt_path.stat().st_size > 45 * 1024 * 1024:
                print(f"  [Transcode] File is {p.stat().st_size / (1024*1024):.2f}MB (>45MB). Fast-optimizing with FFmpeg...")
                cmd = [
                    'ffmpeg', '-y', '-i', str(p),
                    '-c:v', 'libx264', '-crf', '22', '-preset', 'veryfast',
                    '-c:a', 'copy',
                    str(opt_path)
                ]
                import subprocess
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"  [Transcode] ✅ Optimized to {opt_path.stat().st_size / (1024*1024):.2f}MB")
            p = opt_path

        p_str = str(p).replace("\\", "/")
        return await self.client.command(f'tab select {self.tab_id}\nupload {target} "{p_str}"')

    async def sleep(self, seconds):
        await asyncio.sleep(seconds)

    async def clean_reset(self):
        print("  [Reset] Ensuring clean dropzone on TikTok Studio...")
        # Defuse beforeunload first
        await self.eval_js('''(() => {
            window.onbeforeunload = null;
            try { Object.defineProperty(window, 'onbeforeunload', { get: () => null, set: () => {}, configurable: true }); } catch (e) {}
            window.addEventListener('beforeunload', (e) => { e.stopImmediatePropagation(); e.stopPropagation(); delete e['returnValue']; }, true);
        })()''')

        # First, if any Discard modal is already open, click Discard inside the modal
        for _ in range(3):
            await self.eval_js('''(() => {
                const modal = document.querySelector('.common-modal-confirm-modal, [class*="confirm-modal"], [role="dialog"], [aria-modal="true"]');
                if (modal) {
                    const btns = Array.from(modal.querySelectorAll('button'));
                    const modalDiscard = btns.find(b => {
                        const t = (b.innerText || '').trim();
                        return (t === 'Discard' || t === 'ละทิ้ง') && (b.className.includes('primary') || b.className.includes('danger') || b.className.includes('TUXButton--primary'));
                    }) || btns.find(b => (b.innerText || '').trim() === 'Discard' || (b.innerText || '').trim() === 'ละทิ้ง');
                    if (modalDiscard) modalDiscard.click();
                }
            })()''')
            await self.sleep(0.5)

        # Check if already on clean dropzone
        on_dropzone = await self.eval_js('''(() => {
            const hasInput = Boolean(document.querySelector('input[type="file"]'));
            const hasEditor = Boolean(document.querySelector('[contenteditable="true"]'));
            const url = window.location.href;
            return url.includes('/upload') && hasInput && !hasEditor;
        })()''')
        if on_dropzone:
            print("  [Reset] Already on clean dropzone.")
            return True

        # Navigate via location.href
        await self.eval_js('''(() => {
            window.location.href = 'https://www.tiktok.com/tiktokstudio/upload';
        })()''')
        await self.sleep(3)

        for _ in range(15):
            # Click Discard if popped up after navigation
            await self.eval_js('''(() => {
                const modal = document.querySelector('.common-modal-confirm-modal, [class*="confirm-modal"], [role="dialog"], [aria-modal="true"]');
                if (modal) {
                    const btns = Array.from(modal.querySelectorAll('button'));
                    const modalDiscard = btns.find(b => {
                        const t = (b.innerText || '').trim();
                        return (t === 'Discard' || t === 'ละทิ้ง') && (b.className.includes('primary') || b.className.includes('danger') || b.className.includes('TUXButton--primary'));
                    }) || btns.find(b => (b.innerText || '').trim() === 'Discard' || (b.innerText || '').trim() === 'ละทิ้ง');
                    if (modalDiscard) modalDiscard.click();
                }
            })()''')
            has_input = await self.eval_js("(() => Boolean(document.querySelector('input[type=\"file\"]')))()")
            has_editor = await self.eval_js("(() => Boolean(document.querySelector('[contenteditable=\"true\"]')))()")
            if has_input and not has_editor:
                print("  [Reset] Dropzone ready.")
                return True
            await self.sleep(1)
        return False

    async def wait_for_upload(self, timeout=180):
        print("  [Upload] Waiting for video processing to complete...")
        for i in range(timeout):
            status = await self.eval_js('''(() => {
                const hasReplace = Array.from(document.querySelectorAll('button')).some(b => {
                    const t = (b.innerText || '').trim();
                    return t === 'Replace' || t === 'แทนที่' || t === 'เปลี่ยน';
                });
                const postBtn = Array.from(document.querySelectorAll('button')).find(b => {
                    const t = (b.innerText || '').trim();
                    return t === 'Post' || t === 'Schedule' || t === 'โพสต์' || t === 'กำหนดเวลา';
                });
                const hasEditor = Boolean(document.querySelector('[contenteditable="true"]'));
                return {
                    ready: (hasReplace || (postBtn && !postBtn.disabled)) && hasEditor,
                    hasReplace,
                    postReady: Boolean(postBtn && !postBtn.disabled)
                };
            })()''')
            if status and status.get('ready'):
                print("  [Upload] ✅ Video processed and form ready!")
                return True
            await self.sleep(2)
        print("  [Upload] ❌ Upload timed out!")
        return False

    async def type_caption(self, caption, hashtags):
        print("  [Caption] Typing clean caption and hashtags...")
        await self.eval_js('''(() => {
            const el = document.querySelector('[contenteditable="true"]');
            if (el) el.focus();
        })()''')
        await self.sleep(0.3)
        await self.press_key('Control+a')
        await self.sleep(0.1)
        await self.press_key('Backspace')
        await self.sleep(0.3)

        clean_cap = caption.strip()
        await self.type_text(clean_cap)
        await self.sleep(0.5)

        if hashtags:
            clean_ht = hashtags.strip()
            await self.press_key('Enter')
            await self.press_key('Enter')
            await self.sleep(0.2)
            await self.type_text(clean_ht)
            await self.sleep(0.5)
            # Dismiss hashtag autocomplete popup
            await self.press_key('Escape')
            await self.sleep(0.5)
        print("  [Caption] ✅ Caption and hashtags entered.")

    async def attach_product_link(self, product_id, cart_name, internal_pid=None):
        if not product_id:
            return True
        clean_id = re.sub(r'\D', '', str(product_id).strip())
        print(f"  [Cart] Attaching product link (ID: {clean_id}, Cart: '{cart_name}')...")

        # Step 1: Click Add link button
        added = False
        for _ in range(8):
            res = await self.eval_js('''(() => {
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
            })()''')
            if res and res.get('success'):
                added = True
                break
            await self.sleep(1)

        if not added:
            print("  [Cart] ❌ Could not find Add link button!")
            return False
        await self.sleep(1.5)

        # Step 2: Click Next on "Add link" dialog
        next_clicked = False
        for _ in range(6):
            res = await self.eval_js('''(() => {
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
            })()''')
            if res and res.get('success'):
                next_clicked = True
                break
            await self.sleep(1)

        if not next_clicked:
            print("  [Cart] ❌ Could not click Next on Add link dialog!")
            await self.press_key('Escape')
            await self.sleep(0.5)
            return False
        await self.sleep(2)

        # Step 3: Switch to Showcase tab
        for _ in range(8):
            active = await self.eval_js('''(() => {
                const active = document.querySelector('.product-selector-modal .TUXTabBar-itemTitle--active, .product-selector-modal [class*="itemTitle--active"]');
                if (active) {
                    const t = (active.innerText || '').trim();
                    return (t.includes('Showcase') || t.includes('นำเสนอสินค้า')) && !t.includes('Shop') && !t.includes('ร้าน');
                }
                return false;
            })()''')
            if active:
                break
            await self.eval_js('''(() => {
                const btn = document.querySelector('.product-selector-modal button.TUXTabBar-itemTitle[id="2"], .product-selector-modal [id="2"] button') ||
                            Array.from(document.querySelectorAll('.product-selector-modal .TUXTabBar-itemTitle, .product-selector-modal button')).find(b => {
                                const t = (b.innerText || '').trim();
                                return (t === 'Showcase products' || t === 'นำเสนอสินค้า' || t === 'Showcase') && !t.includes('Shop') && !t.includes('ร้าน');
                            });
                if (btn) {
                    btn.focus();
                    btn.click();
                }
            })()''')
            await self.sleep(1.5)

        # Step 4: Search product ID
        for _ in range(6):
            res = await self.eval_js(f'''(() => {{
                const modal = document.querySelector('.product-selector-modal') || document;
                const search = modal.querySelector('input.TUXTextInputCore-input, input[placeholder*="Search"], input[placeholder*="ค้นหา"]');
                if (search) {{
                    search.focus();
                    search.select();
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                    if (setter) setter.call(search, "{clean_id}"); else search.value = "{clean_id}";
                    search.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    search.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    const icon = modal.querySelector('.product-search-icon, .TUXTextInputCore-trailingIconWrapper');
                    if (icon) {{ try {{ icon.click(); }} catch(e) {{}} }}
                    return {{ success: true }};
                }}
                return {{ success: false }};
            }})()''')
            if res and res.get('success'):
                break
            await self.sleep(1)

        await self.press_key('Enter')
        await self.sleep(2.5)

        # Step 5: Select product from table
        selected = False
        for attempt in range(8):
            res = await self.eval_js(f'''(() => {{
                const modal = document.querySelector('.product-selector-modal') || document;
                const rows = Array.from(modal.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, tbody tr'))
                    .filter(r => !r.querySelector('th') && (r.innerText || '').trim().length > 0);
                if (rows.length === 0) return {{ success: false, reason: 'no_rows' }};

                const query = "{clean_id}";
                const querySuffix = query.length > 6 ? query.slice(-6) : query;
                let targetRow = rows.find(row => {{
                    const text = (row.innerText || row.textContent || '').trim();
                    return text.includes(query) || text.includes(querySuffix);
                }});
                if (!targetRow && rows.length === 1) targetRow = rows[0];
                if (!targetRow) return {{ success: false, reason: 'not_found' }};

                const rowText = (targetRow.innerText || targetRow.textContent || '').trim();
                if (rowText.includes('Unavailable') || rowText.includes('ไม่พร้อมจำหน่าย') || rowText.includes('สินค้าหมด') || rowText.includes('Stock: 0')) {{
                    return {{ success: false, reason: 'out_of_stock' }};
                }}

                const label = targetRow.querySelector('label.TUXRadio-label, label[for]');
                const input = targetRow.querySelector('input.TUXRadioStandalone-input, input[type="radio"]');
                if (label) label.click(); else if (input) input.click();
                return {{ success: true }};
            }})()''')
            if res and res.get('success'):
                selected = True
                print("  [Cart] ✅ Product selected from Showcase.")
                break
            elif res and res.get('reason') == 'out_of_stock':
                print("  [Cart] ⚠️ Product is OUT OF STOCK! Skipping product link.")
                await self.eval_js('''(() => {
                    const close = document.querySelector('.product-selector-modal button[aria-label="Close"], .product-selector-modal .TUXModal-closeButton');
                    if (close) close.click();
                })()''')
                return False
            await self.sleep(1)

        if not selected:
            print("  [Cart] ❌ Could not select product row!")
            await self.press_key('Escape')
            await self.sleep(0.5)
            return False

        await self.sleep(1)

        # Step 6: Click Next on product selector modal
        for _ in range(6):
            res = await self.eval_js('''(() => {
                const modals = Array.from(document.querySelectorAll('.product-selector-modal, [role="dialog"], [aria-modal="true"], .TUXModal'));
                const modal = modals[modals.length - 1] || document;
                const nextBtn = Array.from(modal.querySelectorAll('button')).find(b => {
                    const t = (b.innerText || '').trim();
                    return (t === 'Next' || t === 'ถัดไป') && !b.disabled && !b.classList.contains('TUXButton--disabled');
                });
                if (nextBtn) {
                    nextBtn.focus();
                    nextBtn.click();
                    return { success: true };
                }
                return { success: false };
            })()''')
            if res and res.get('success'):
                break
            await self.sleep(1)

        await self.sleep(2)

        # Step 7: Confirm cart name
        clean_cart = clean_cart_name(product_id=internal_pid, raw_name=cart_name)
        if not clean_cart and cart_name:
            clean_cart = sanitize_cart_name(cart_name)
        print(f"  [Cart] Confirming cart name: '{clean_cart}'...")
        for _ in range(8):
            res = await self.eval_js(f'''(() => {{
                const isVisible = (el) => {{
                    if (!el) return false;
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
                }};
                const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .TUXModal')).filter(isVisible);
                const dialog = dialogs[dialogs.length - 1];
                if (!dialog) return {{ success: false, reason: 'no_dialog' }};

                const input = dialog.querySelector('input.TUXTextInputCore-input, input[type="text"]');
                if (input) {{
                    input.focus();
                    input.select();
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                    if (setter) setter.call(input, "{clean_cart}"); else input.value = "{clean_cart}";
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}

                const addBtn = Array.from(dialog.querySelectorAll('button')).find(b => {{
                    const t = (b.innerText || '').trim();
                    return (t === 'Add' || t === 'เพิ่ม') && !b.disabled && isVisible(b);
                }});

                if (addBtn) {{
                    addBtn.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                    addBtn.focus();
                    addBtn.click();
                    return {{ success: true }};
                }}
                return {{ success: false }};
            }})()''')
            if res and res.get('success'):
                print("  [Cart] ✅ Cart name confirmed and added!")
                break
            await self.sleep(1)

        await self.sleep(2)
        return True

    async def switch_to_schedule_mode(self, sched_date, sched_time):
        print(f"  [Schedule] Setting schedule: {sched_date} {sched_time}...")
        for attempt in range(5):
            res = await self.eval_js('''(() => {
                const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
                const schedRadio = radios.find(r => r.value === 'schedule') || radios.find(r => {
                    const p = r.closest('label') || r.parentElement;
                    const t = (p?.innerText || '').trim();
                    return t.includes('Schedule') || t.includes('กำหนดเวลา');
                });
                if (schedRadio) {
                    schedRadio.click();
                    const lbl = schedRadio.closest('label') || schedRadio.parentElement;
                    if (lbl) lbl.click();
                    return { ok: true, checked: schedRadio.checked };
                }
                return { ok: false };
            })()''')
            if res and res.get('checked'):
                break
            await self.sleep(0.8)

        await self.sleep(1)

        # Date
        if sched_date:
            day_num = int(sched_date.split('-')[2])
            date_confirmed = False
            for d_att in range(4):
                # 1. Open datepicker cleanly
                open_res = await self.eval_js('''(() => {
                    const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
                    const inputs = Array.from(document.querySelectorAll('.scheduled-picker input, input.TUXTextInputCore-input, input[type="text"]'))
                        .filter(el => visible(el) && (/\\d{4}-\\d{2}-\\d{2}/.test(el.value) || el.placeholder.includes('YYYY') || (el.value.includes('202') && !el.value.includes(':'))));
                    if (inputs.length > 0) {
                        const inp = inputs[0];
                        inp.focus();
                        inp.click();
                        inp.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                        inp.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
                        inp.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                        return true;
                    }
                    return false;
                })()''')
                await self.sleep(0.8)

                # 2. Click target day in calendar
                click_day = await self.eval_js(f'''(() => {{
                    const visible = el => {{ const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }};
                    const days = Array.from(document.querySelectorAll('span.day.valid, span.day:not(.disabled), [class*="calendar"] span, [class*="day-item"]'))
                        .filter(el => visible(el) && parseInt(el.textContent.trim(), 10) === {day_num});
                    if (days.length > 0) {{
                        days[0].click();
                        return true;
                    }}
                    return false;
                }})()''')
                await self.sleep(0.8)

                # 3. Verify date input actually has sched_date
                check_date = await self.eval_js('''(() => {
                    const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
                    const inputs = Array.from(document.querySelectorAll('.scheduled-picker input, input.TUXTextInputCore-input, input[type="text"]'))
                        .filter(el => visible(el) && (/\\d{4}-\\d{2}-\\d{2}/.test(el.value) || (el.value.includes('202') && !el.value.includes(':'))));
                    return inputs.length > 0 ? inputs[0].value.trim() : null;
                })()''')

                if check_date and (check_date == sched_date or str(day_num) in check_date):
                    print(f"  [Schedule] ✅ Date verified: {check_date} (target: {sched_date})")
                    date_confirmed = True
                    break
                else:
                    print(f"  [Schedule] ⚠️ Attempt {d_att+1}/4: Date mismatch (expected {sched_date}, got '{check_date}'), retrying...")
                    await self.sleep(1.0)

            if not date_confirmed:
                raise RuntimeError(f"Failed to set target schedule date to {sched_date}! Aborting clip to prevent wrong date.")

        # Time
        if sched_time:
            hour_str, min_str = sched_time.split(':')
            hour_num = int(hour_str)
            min_num = round(int(min_str) / 5) * 5
            if min_num == 60:
                hour_num = (hour_num + 1) % 24
                min_num = 0

            # Open timepicker
            await self.eval_js('''(() => {
                const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
                const inputs = Array.from(document.querySelectorAll('input.TUXTextInputCore-input, input[type="time"], input[type="text"]'))
                    .filter(el => visible(el) && /^\\d{1,2}:\\d{2}$/.test(String(el.value || '').trim()));
                const pickerOpen = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text')).some(visible);
                if (inputs.length > 0 && !pickerOpen) inputs[0].click();
            })()''')
            await self.sleep(0.5)

            # Pick hour & minute
            await self.eval_js(f'''(() => {{
                const visible = el => {{ const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }};
                const hourVals = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text.tiktok-timepicker-left, [class*="timepicker-left"] span'))
                    .filter(el => Number.parseInt(el.textContent.trim(), 10) === {hour_num});
                const h = hourVals.find(visible) || hourVals[0];
                if (h) {{ h.scrollIntoView({{ block: 'center' }}); h.click(); }}

                const minVals = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text.tiktok-timepicker-right, [class*="timepicker-right"] span'))
                    .filter(el => Number.parseInt(el.textContent.trim(), 10) === {min_num});
                const m = minVals.find(visible) || minVals[0];
                if (m) {{ m.scrollIntoView({{ block: 'center' }}); m.click(); }}
            }})()''')
            await self.sleep(0.5)

            # Close timepicker dropdown
            await self.eval_js('''(() => {
                document.querySelector('[contenteditable="true"]')?.click();
            })()''')
            await self.sleep(0.5)

        # Verify values
        vals = await self.eval_js('''(() => {
            const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
            return Array.from(document.querySelectorAll('input.TUXTextInputCore-input, input[type="date"], input[type="time"], input[type="text"]'))
                .filter(visible).map(el => String(el.value || '').trim());
        })()''')
        print(f"  [Schedule] ✅ Confirmed inputs: {vals}")

    async def upload_cover(self, cover_path):
        if not cover_path or not Path(cover_path).exists():
            return True
        print(f"  [Cover] Uploading 3:4 cover image: {cover_path}...")
        opened = await self.eval_js('''(() => {
            const isVisible = (el) => {
                if (!el) return false;
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
            };
            const targets = Array.from(document.querySelectorAll('div.edit-container, [class*="edit-container"], [class*="cover-container"] div, button, [role="button"]'))
                .filter(isVisible)
                .map((el, index) => {
                    const text = (el.innerText || el.textContent || '').trim();
                    const exact = text === 'แก้ไขหน้าปก' || text === 'แก้ไขปก' || text === 'Edit cover' || text === 'Edit';
                    const partial = text.includes('แก้ไข') || text.includes('Edit');
                    return { el, exact, partial };
                })
                .filter(x => x.exact || x.partial);
            if (targets.length > 0) {
                const btn = targets[0].el.closest('button, [role="button"]') || targets[0].el;
                btn.click();
                return true;
            }
            return false;
        })()''')
        await self.sleep(2)

        has_modal = await self.eval_js('''(() => {
            const modal = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal');
            return Boolean(modal);
        })()''')
        if has_modal:
            await self.eval_js('''(() => {
                const tabs = Array.from(document.querySelectorAll('.TUXTabBar-itemTitle, [role="tab"], button'));
                const uploadTab = tabs.find(t => (t.innerText || '').includes('Upload cover') || (t.innerText || '').includes('อัปโหลดปก'));
                if (uploadTab) uploadTab.click();
            })()''')
            await self.sleep(1)

            has_input = await self.eval_js('''(() => {
                const modal = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal');
                const inp = modal ? modal.querySelector('input[type="file"]') : null;
                if (inp) {
                    inp.id = 'tiktok-custom-cover-input';
                    return true;
                }
                return false;
            })()''')
            if has_input:
                await self.upload_file(cover_path, target='#tiktok-custom-cover-input')
                await self.sleep(2)

            # Click Save on cover modal with confirmation that it closes
            for _ in range(5):
                await self.eval_js('''(() => {
                    const modal = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal');
                    if (!modal) return;
                    const btns = Array.from(modal.querySelectorAll('button'));
                    const save = btns.find(b => {
                        const t = (b.innerText || '').trim();
                        return (t === 'Save' || t === 'บันทึก' || t === 'Confirm' || t === 'ยืนยัน') && !b.disabled;
                    });
                    if (save) save.click();
                })()''')
                await self.sleep(1.5)
                closed = await self.eval_js("(() => !Boolean(document.querySelector('[role=\"dialog\"], [aria-modal=\"true\"], .TUXModal')))()")
                if closed:
                    break

            # If still open, force dismiss with Escape
            still_open = await self.eval_js("(() => Boolean(document.querySelector('[role=\"dialog\"], [aria-modal=\"true\"], .TUXModal')))()")
            if still_open:
                print("  [Cover] ⚠️ Cover modal still open, dismissing with Escape...")
                await self.press_key('Escape')
                await self.sleep(1)
        print("  [Cover] ✅ Cover handled.")

    async def submit_schedule(self):
        print("  [Submit] Waiting for Schedule button to be ready and enabled...")
        clicked = False
        for att in range(35):
            res = await self.eval_js('''(() => {
                const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="menu"], [class*="nav"]'));
                const btns = Array.from(document.querySelectorAll('button')).filter(b => !isNav(b) && b.offsetWidth > 0);
                const schedBtn = btns.find(b => {
                    const t = (b.innerText || b.textContent || '').trim();
                    const isSched = (t === 'Schedule' || t === 'กำหนดเวลา' || t === 'Post' || t === 'โพสต์');
                    const isDis = b.disabled || b.getAttribute('aria-disabled') === 'true' || b.classList.contains('Button__root--disabled') || b.classList.contains('TUXButton--disabled');
                    return isSched && !isDis;
                });
                if (schedBtn) {
                    schedBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    schedBtn.focus();
                    schedBtn.click();
                    return { success: true, text: schedBtn.innerText.trim() };
                }
                const anySched = btns.find(b => {
                    const t = (b.innerText || b.textContent || '').trim();
                    return t === 'Schedule' || t === 'กำหนดเวลา' || t === 'Post' || t === 'โพสต์';
                });
                const openModal = document.querySelector('[role="dialog"], [aria-modal="true"], .TUXModal');
                const alerts = Array.from(document.querySelectorAll('[role="alert"], .tiktok-form-item-explain, [class*="error-text"]'))
                    .map(el => (el.innerText || '').trim()).filter(Boolean);

                return {
                    success: false,
                    anyFound: Boolean(anySched),
                    ariaDisabled: anySched?.getAttribute('aria-disabled'),
                    disabled: anySched?.disabled,
                    hasModal: Boolean(openModal),
                    alerts: alerts
                };
            })()''')
            if res and res.get('success'):
                print(f"  [Submit] Clicked Schedule button: {res.get('text')}")
                clicked = True
                break
            if res and res.get('hasModal') and att > 4:
                print("  [Submit] Lingering modal detected, pressing Escape...")
                await self.press_key('Escape')
            if att % 5 == 0 and res and res.get('alerts'):
                print(f"  [Submit] Page alerts at attempt {att}: {res.get('alerts')}")
            await self.sleep(2)

        if not clicked:
            print(f"  [Submit] ❌ Schedule button never became enabled: {res}")
            return False

        await self.sleep(2)

        # Handle any "Post now" / Copyright / confirmation modals
        for _ in range(6):
            popped = await self.eval_js('''(() => {
                const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
                const confirmBtn = btns.find(b => {
                    const t = (b.innerText || b.textContent || '').trim();
                    return t === 'Post now' || t === 'โพสต์เลย' || t === 'Schedule anyway' || t === 'กำหนดเวลาต่อไป' || t === 'Continue' || t === 'ดำเนินการต่อ';
                });
                if (confirmBtn) {
                    confirmBtn.click();
                    return { dismissed: true, text: confirmBtn.innerText.trim() };
                }
                return null;
            })()''')
            if popped:
                print(f"  [Submit] Dismissed confirmation modal: {popped}")
                await self.sleep(2)
                break
            await self.sleep(1)

        # Wait for redirect to Content page or success toast
        for _ in range(15):
            success = await self.eval_js('''(() => {
                const url = window.location.href;
                const inContent = url.includes('/content') || url.includes('/manage');
                const toast = document.querySelector('.tux-toast, [class*="toast"], [role="status"]');
                const toastText = toast ? (toast.innerText || toast.textContent || '').trim() : '';
                const successToast = toastText.includes('scheduled') || toastText.includes('published') || toastText.includes('สำเร็จ') || toastText.includes('กำหนดเวลาแล้ว');
                return { inContent, successToast, toastText, url };
            })()''')
            if success and (success.get('inContent') or success.get('successToast')):
                print(f"  [Submit] ✅ Scheduled successfully verified! ({success.get('url')})")
                return True
            await self.sleep(2)

        print("  [Submit] ❌ Submission verification failed: Never redirected to /content and no success toast detected!")
        return False

    async def process_clip(self, clip, index, total):
        cid = clip['id']
        pname = clip.get('product_name', '')
        s_at = clip.get('scheduled_at', '')
        cart = clip.get('cart_name', '')
        vrel = clip.get('video_path', '')
        crel = clip.get('cover_path', '')
        p_id = clip.get('tiktok_product_id', '')
        caption = clip.get('caption', '')
        hashtags = clip.get('hashtags', '')

        print(f"\n{'='*70}")
        print(f"▶️ [{index}/{total}] PROCESSING CLIP: {pname[:35]}")
        print(f"   Scheduled: {s_at} | Cart: '{cart}'")
        print(f"   Video: {vrel}")
        print(f"{'='*70}")

        # 1. Reset dropzone
        ok = await self.clean_reset()
        if not ok:
            print(f"❌ Failed dropzone reset for clip {index}")
            return False

        # 2. Upload video
        vabs = str((BASE_DIR / vrel).resolve())
        print(f"  [Upload] Uploading: {vabs}")
        await self.upload_file(vabs)

        # 3. Wait for upload to complete
        uploaded = await self.wait_for_upload()
        if not uploaded:
            print(f"❌ Upload failed or timed out for clip {index}")
            return False

        # 4. Caption & hashtags
        await self.type_caption(caption, hashtags)
        await self.sleep(1)

        # 5. Product link (Showcase)
        if p_id:
            cart_ok = await self.attach_product_link(p_id, cart, internal_pid=clip.get('product_id'))
            if not cart_ok:
                print(f"  [Cart] ⚠️ Cart attachment failed or out-of-stock")
            await self.sleep(1)

        # 6. Schedule mode
        s_date = s_at[:10]
        s_time = s_at[11:16]
        await self.switch_to_schedule_mode(s_date, s_time)
        await self.sleep(1)

        # 7. Cover
        if crel:
            cabs = str((BASE_DIR / crel).resolve())
            await self.upload_cover(cabs)
            await self.sleep(1)

        # 8. Submit
        submitted = await self.submit_schedule()
        if not submitted:
            print(f"❌ Submit failed for clip {index}")
            return False

        # 9. Update backend store
        ScheduleQueueStore.update_item(cid, lambda row, recs: row.update({
            'status': 'scheduled_on_platform',
            'posted_at': None
        }))
        print(f"🎉 [{index}/{total}] CLIP {index} SCHEDULED & STORE UPDATED: {pname[:30]}")
        return True

async def run_batch():
    uploader = LiveTikTokBatchUploader()
    await uploader.connect()

    # Query target clips for Nov 23-26
    items = ScheduleQueueStore.list_items()
    target_clips = [
        x for x in items
        if any(x.get('scheduled_at', '').startswith(d) for d in ['2026-11-23', '2026-11-24', '2026-11-25', '2026-11-26'])
        and x.get('status') == 'planned'
    ]
    target_clips.sort(key=lambda x: x.get('scheduled_at', ''))

    print(f"\n🚀 STARTING BATCH SCHEDULE FOR {len(target_clips)} CLIPS (Nov 23-26)")
    for i, c in enumerate(target_clips):
        print(f"  {i+1:2d}. {c.get('scheduled_at')} | {c.get('product_name')[:30]} | cart: '{c.get('cart_name')}'")

    success_count = 0
    total = len(target_clips)

    for i, clip in enumerate(target_clips):
        idx = i + 1
        ok = await uploader.process_clip(clip, idx, total)
        if ok:
            success_count += 1
        else:
            print(f"⚠️ Clip {idx} did not succeed, proceeding to next clip...")

        # Cooldown between clips (20 seconds) unless last clip
        if idx < total:
            print(f"\n⏳ Cooldown 20s before next clip...")
            await asyncio.sleep(20)

    print(f"\n{'='*70}")
    print(f"🏁 BATCH UPLOAD FINISHED: {success_count}/{total} clips scheduled!")
    print(f"{'='*70}\n")
    await uploader.close()

if __name__ == '__main__':
    asyncio.run(run_batch())
