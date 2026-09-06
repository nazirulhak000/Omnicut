// OmniCut TikTok Post Helper -- background service worker (Manifest V3).
//
// Why chrome.debugger at all: browsers hard-block scripts (page JS AND
// extension content scripts) from setting <input type=file>.files -- see
// TIKTOK_AUTOPOST_PLAN.md §"ไม่มีทางลัดที่ปลอดภัยกว่า". The only surface
// that can is the Chrome DevTools Protocol's DOM.setFileInputFiles, which
// requires chrome.debugger.attach() first -- the same mechanism Playwright
// and Puppeteer use. Chrome shows an un-hideable "being debugged" banner on
// the tab the whole time this runs. That is intentional, not a bug to hide.
//
// This file only runs when the user clicks a button inside the side panel
// (sidepanel.html/.js), on a tab they already have open and already logged
// into. Nothing here schedules itself, polls in the background, or runs
// without that click.
//
// 2026-09-06: clicking the toolbar icon now opens the side panel directly
// (the old popup.html/popup.js checklist was merged into sidepanel.html as
// its own tab and deleted -- one UI surface instead of two).
importScripts('automation.js');

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((err) => {
  console.error('setPanelBehavior failed:', err);
});
//
// Selectors marked UNVERIFIED come from TIKTOK_AUTOPOST_PLAN.md §3 --
// community-documented as of the plan's writing, never confirmed against a
// real logged-in TikTok Studio session (that needs a real account, which
// this tool's author does not have access to). If a step throws here,
// that selector is almost certainly the first thing to check.

const BACKEND = 'http://127.0.0.1:8000';
const UPLOAD_URL_PATTERN = 'https://www.tiktok.com/tiktokstudio/upload*';
const PROCESSING_TIMEOUT_MS = 90_000;
const POLL_INTERVAL_MS = 2_000;

// 2026-09-06 diagnostic A/B flag -- TEMPORARY, delete once we have an answer.
// The tab crash was caught happening WHILE waitForUploadComplete() was still
// polling (before attachProductLink even started), right as TikTok's own
// cover/effects worker (clip-forge-effect-sdk) was initializing. Two
// hypotheses: (a) our repeated Runtime.evaluate calls during that window
// destabilize it, or (b) merely having chrome.debugger attached at all
// during that window is enough, independent of what we send it. Setting
// this to true replaces the active polling loop with one plain sleep
// (debugger stays attached, zero CDP calls sent) so we can tell which:
// crash persists -> (b); crash goes away -> (a), and the fix is to poll
// less aggressively or via chrome.scripting instead of CDP.
const DIAGNOSTIC_PASSIVE_WAIT = true;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchPendingJob() {
  let res;
  try {
    res = await fetch(`${BACKEND}/api/tiktok-autopost/pending`);
  } catch (err) {
    throw new Error('เชื่อมต่อ Backend (localhost:8000) ไม่สำเร็จ -- ตรวจสอบว่าเปิด start_app.bat ไว้หรือไม่');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (res.status === 404) {
      if (body.detail === 'Not Found') {
        throw new Error('Backend ยังไม่ได้รีสตาร์ทเพื่อโหลด API โพสต์ -- ให้ปิดหน้าต่าง backend แล้วรัน start_app.bat ใหม่ 1 ครั้ง');
      }
      throw new Error(body.detail || 'ยังไม่มีคลิปที่เตรียมไว้ -- กด "โพสต์ TikTok อัตโนมัติ" ในแอป OmniCut ก่อน');
    }
    throw new Error(body.detail || `โหลดคลิปที่เตรียมไว้ไม่สำเร็จ (HTTP ${res.status})`);
  }
  return res.json();
}

async function clearPendingJob() {
  try {
    await fetch(`${BACKEND}/api/tiktok-autopost/clear`, { method: 'POST' });
  } catch (e) {
    // Non-fatal -- the next prepare() overwrites it anyway.
  }
}

async function findUploadTab() {
  if (pinnedUploadTabId !== null) {
    const tab = await chrome.tabs.get(pinnedUploadTabId);
    const url = new URL(tab.url || 'about:blank');
    if (url.hostname !== 'www.tiktok.com' || !url.pathname.includes('upload')) {
      throw new Error('แท็บที่เริ่มงานออกจากหน้าอัปโหลดแล้ว กรุณาเปิดหน้าอัปโหลดใหม่');
    }
    return tab;
  }
  try {
    const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (
      activeTab?.url &&
      activeTab.url.includes('tiktok.com') &&
      (activeTab.url.includes('upload') || activeTab.url.includes('creator') || activeTab.url.includes('studio'))
    ) {
      return activeTab;
    }
  } catch (e) {
    // fallback
  }

  const patterns = [
    'https://www.tiktok.com/tiktokstudio/upload*',
    'https://www.tiktok.com/creator-center/upload*',
    '*://*.tiktok.com/*upload*',
    '*://*.tiktok.com/tiktokstudio*',
  ];
  for (const pattern of patterns) {
    try {
      const tabs = await chrome.tabs.query({ url: pattern });
      if (tabs && tabs.length > 0) return tabs[0];
    } catch (e) {}
  }

  throw new Error(
    'ไม่พบแท็บ TikTok Studio ที่เปิดหน้าอัปโหลดอยู่ -- กรุณาเปิดหน้าอัปโหลด tiktok.com/tiktokstudio/upload ใน Chrome ก่อน'
  );
}

// Thin CDP call wrapper -- every call site already knows the tabId, this
// just avoids repeating {tabId} at every call.
function cdp(tabId) {
  return (method, params) =>
    chrome.debugger.sendCommand({ tabId }, method, params);
}

// Finds the file input nodeId with a short retry loop
async function findFileInputNodeId(send) {
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    const { root } = await send('DOM.getDocument', { depth: -1, pierce: true });
    const { nodeIds } = await send('DOM.querySelectorAll', {
      nodeId: root.nodeId,
      selector: 'input[type="file"]',
    });
    if (nodeIds && nodeIds.length > 0) {
      return nodeIds[0];
    }
    await sleep(500);
  }
  throw new Error(
    'ไม่พบ <input type="file"> ในหน้า TikTok Studio -- ตรวจสอบว่าหน้าเว็บโหลดเสร็จสมบูรณ์หรือยัง'
  );
}

async function setFileInput(send, nodeId, absolutePath) {
  await send('DOM.setFileInputFiles', { files: [absolutePath], nodeId });
}

// Waits for TikTok Studio's caption editor ([contenteditable="true"]) to appear in the DOM.
async function waitForCaptionEditor(send) {
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    const { result } = await send('Runtime.evaluate', {
      expression: `(() => {
        const el = document.querySelector('[contenteditable="true"]');
        return Boolean(el && (el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0));
      })()`,
      returnByValue: true,
    });
    if (result && result.value) {
      // Allow TikTok's UI a brief moment to finish injecting its default video filename
      await sleep(1000);
      return;
    }
    await sleep(500);
  }
  throw new Error('รอช่องคำอธิบาย (Caption Editor) ไม่ทันภายใน 45 วินาที');
}

// Clears any auto-filled filename that TikTok inserted, then types the clean caption and hashtags.
async function typeCaption(send, text) {
  if (!text?.trim()) throw new Error('กรุณากรอกคำอธิบายหรือแฮชแท็ก');
  const captionQuery = OmniAutomation.page(`
    const editors = Array.from(document.querySelectorAll('[contenteditable="true"]')).filter(el =>
      visible(el) && !el.closest('[role="dialog"], [aria-modal="true"]'));
    return editors.length === 1 ? editors[0] : null;
  `);
  const focused = await OmniAutomation.evaluate(send, `(() => {
    const el = ${captionQuery};
    if (!el) return false;
    el.focus();
    const range = document.createRange();
    range.selectNodeContents(el);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    return document.activeElement === el;
  })()`);
  if (!focused) throw new Error('ไม่พบช่องแคปชันที่พร้อมกรอก หรือมีหลายช่อง กรุณาปิดหน้าต่างอื่นบน TikTok');
  // Native browser editing replaces the selection in one operation. Do not
  // mutate innerHTML/textContent or dispatch fake input events into React.
  await send('Input.insertText', {text});
  await OmniAutomation.wait(send, `(() => {
    const el = ${captionQuery};
    const normalize = value => String(value).replace(/\\s+/g, ' ').trim();
    return Boolean(el && normalize(el.innerText || el.textContent) === normalize(${JSON.stringify(text)}));
  })()`, 'TikTok ยังไม่รับแคปชันครบ กรุณาตรวจช่องคำอธิบาย', 5000);
}

// Waits for TikTok Studio video upload/processing indicator to complete
async function waitForUploadComplete(send, timeoutMs = 120_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const status = await send('Runtime.evaluate', {
      expression: `(() => {
        const allText = document.body ? (document.body.innerText || '') : '';

        // 1. Check for active upload percentage (e.g. 29.36%, 70%)
        const percentMatch = allText.match(/\\b([0-9]{1,2}(?:\\.[0-9]+)?%)/);
        if (percentMatch && !percentMatch[0].startsWith('100')) {
          return { isUploading: true, reason: 'percentage: ' + percentMatch[0] };
        }

        // 2. Check for "Uploading..." in preview -- TikTok Studio's Thai UI
        // shows "กำลังอัปโหลด..." under the cover thumbnail at this stage,
        // never the English string. This check only ever matched the
        // English text, so on a Thai session it silently never fired --
        // confirmed directly from a real screenshot at 0% upload,
        // 2026-09-06. Both variants now required.
        if (allText.includes('Uploading...') || allText.includes('กำลังอัปโหลด')) {
          return { isUploading: true, reason: 'preview-uploading' };
        }

        // 3. Check for "MB/..MB" or "เหลือ X วินาที"
        if (/\\b\\d+(?:\\.\\d+)?MB\\/\\d+(?:\\.\\d+)?MB\\b/.test(allText) || /เหลือ\\s+\\d+\\s+วินาที/.test(allText)) {
          return { isUploading: true, reason: 'transferring-mb' };
        }

        // 4. Check if bottom submit button exists and is disabled
        const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="menu"], [class*="nav"]'));
        const buttons = Array.from(document.querySelectorAll('button'));
        const submitButtons = buttons.filter(b => {
          if (isNav(b)) return false;
          const t = (b.innerText || b.textContent || '').trim();
          return t === 'โพสต์' || t === 'กำหนดเวลา' || t === 'Post' || t === 'Schedule';
        });

        const hasDisabledSubmit = submitButtons.some(b => b.disabled || b.getAttribute('aria-disabled') === 'true');
        if (hasDisabledSubmit) {
          return { isUploading: true, reason: 'submit-disabled' };
        }

        // NOTE (2026-09-06): a "check #5" here used to require the
        // "แก้ไขหน้าปก" (Edit cover) button to be present+enabled before
        // considering the upload done, on the theory that it only becomes
        // clickable once TikTok's cover-generation worker finishes. Removed
        // -- the user tested this directly on a real account and the
        // button is clickable immediately at 0% upload, so that check never
        // actually blocked anything. Don't reintroduce it without new
        // evidence of what the real "still processing" signal is.

        return { isUploading: false };
      })()`,
      returnByValue: true,
    });

    if (!status?.result?.value?.isUploading) {
      await sleep(1500);
      return true;
    }
    await sleep(2000);
  }
  return false;
}

// Switches to "นำเสนอสินค้า" (Showcase / Product Showcase) tab reliably
// A single stray extra click on a React-controlled element isn't free: this
// function used to fire pointerdown/mousedown/pointerup/mouseup/click PLUS
// .click() on the target AND its parent AND its closest [role="tab"]
// ancestor -- up to ~6 click-equivalent events on 3 different elements,
// then ALSO an unconditional native CDP mouse click on top, every single
// retry. React can lose track of its own fiber tree when it receives that
// many rapid, overlapping click events for one logical action -- this is
// the leading suspect for the `NotFoundError: removeChild` crash caught in
// a real screen recording (2026-09-06). Rewritten to fire exactly ONE click
// per attempt (plain .click() first; a single real CDP mouse click only as
// a fallback if that alone didn't land), with a settle wait to let React
// actually finish re-rendering before checking again.
async function switchToShowcaseTab(send) {
  // Strict visibility check -- offsetWidth/offsetHeight/getClientRects() can
  // all report non-zero for an element sitting in a display:none ancestor
  // panel that React never removed from the DOM (TikTok keeps inactive tab
  // panels mounted, just hidden), so this used to false-positive as "already
  // on the right tab" when it was really still looking at a stale, offscreen
  // search input from a PREVIOUS render. checkVisibility() (or the
  // getBoundingClientRect fallback) reflects the real, current CSS-computed
  // visibility instead.
  const isActive = async () => {
    const r = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
        };
        const inputs = Array.from(document.querySelectorAll('input'));
        const searchInput = inputs.find(i => {
          const p = (i.placeholder || '').toLowerCase();
          return (p.includes('ค้นหา') || p.includes('search')) && isVisible(i);
        });
        if (!searchInput) return false;

        // Negative signal: "ร้านของฉัน" (My Shop) empty-state text visible
        // anywhere on screen means we're still on the WRONG tab even if a
        // stray search input elsewhere matched above.
        const bodyText = document.body.innerText || '';
        if (bodyText.includes('ไม่มีสินค้าในร้านของคุณ')) return false;

        return true;
      })()`,
      returnByValue: true,
    });
    return Boolean(r?.result?.value);
  };

  if (await isActive()) return true;

  for (let attempt = 0; attempt < 5; attempt++) {
    const found = await send('Runtime.evaluate', {
      expression: `(() => {
        const root = document.querySelector('[role="dialog"]') || document;
        const allElements = Array.from(root.querySelectorAll('[role="tab"], button, div, span, p, a'));
        const candidates = allElements.filter(el => {
          const t = (el.innerText || el.textContent || '').trim();
          if (!t) return false;
          // Exclude parent containers that also enclose "ร้านของฉัน"
          if (t.includes('ร้านของฉัน') || t.includes('My Shop') || t.includes('จัดการสินค้า')) return false;
          return t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase' || t.includes('Showcase') || t.includes('ตู้โชว์');
        });

        const visibleCandidates = candidates.filter(el => {
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0;
        });
        if (visibleCandidates.length === 0) return null;

        // Sort ascending by bounding box area to target the most specific leaf element
        visibleCandidates.sort((a, b) => {
          const rA = a.getBoundingClientRect();
          const rB = b.getBoundingClientRect();
          return (rA.width * rA.height) - (rB.width * rB.height);
        });

        const target = visibleCandidates[0];
        const rect = target.getBoundingClientRect();
        target.scrollIntoView({ behavior: 'instant', block: 'center' });
        target.click();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
      })()`,
      returnByValue: true,
    });

    await sleep(700);
    if (await isActive()) return true;

    const point = found?.result?.value;
    if (point && point.x > 0 && point.y > 0) {
      try {
        await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: Math.round(point.x), y: Math.round(point.y) });
        await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, x: Math.round(point.x), y: Math.round(point.y) });
        await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, x: Math.round(point.x), y: Math.round(point.y) });
      } catch (e) {}
      await sleep(700);
      if (await isActive()) return true;
    }
  }
  return false;
}

// Automatically clicks "+ เพิ่ม" under "เพิ่มลิงก์", searches product by ID, and adds it.
async function attachProductLink(send, productId) {
  if (!productId) return { success: false, reason: 'ไม่มี Product ID' };

  // Step 1: Click "+ เพิ่ม" button under "เพิ่มลิงก์"
  const step1 = await send('Runtime.evaluate', {
    expression: `(() => {
      // ONE click only -- .click() alone bubbles a real click event that
      // React's delegated listeners pick up correctly. Firing .click() and
      // THEN dispatching a second synthetic mousedown/mouseup/click on the
      // same element (the old behavior here) makes the handler run twice
      // for one logical click, which is a real cause of React losing sync
      // with the DOM (see Round POST-2 crash notes, 2026-09-06).
      const trigger = (el) => {
        if (!el) return;
        el.scrollIntoView({ behavior: 'instant', block: 'center' });
        el.click();
      };

      const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="nav"], [class*="menu"]'));

      // 1. Look for "เพิ่มลิงก์" header and find "+ เพิ่ม" inside its parent container
      const allDivs = Array.from(document.querySelectorAll('div, section, p, span, h1, h2, h3, h4'));
      const header = allDivs.find(el => !isNav(el) && (el.innerText || el.textContent || '').trim() === 'เพิ่มลิงก์');
      if (header) {
        let parent = header.parentElement;
        for (let i = 0; i < 5 && parent; i++) {
          const btns = Array.from(parent.querySelectorAll('button, div[role="button"], span[role="button"]'));
          const btn = btns.find(b => {
            if (isNav(b)) return false;
            const t = (b.innerText || b.textContent || '').trim();
            return (t.includes('เพิ่ม') || t.includes('+')) && t !== 'เพิ่มลิงก์';
          });
          if (btn) {
            trigger(btn);
            return { success: true, method: 'header-parent' };
          }
          parent = parent.parentElement;
        }
      }

      // 2. Direct button search fallback (strictly excluding navigation/sidebar)
      const allButtons = Array.from(document.querySelectorAll('button, div[role="button"], span'));
      const addBtn = allButtons.find(el => {
        if (isNav(el)) return false;
        const text = (el.innerText || el.textContent || '').trim();
        return text === '+ เพิ่ม' || text === '+เพิ่ม' || (text.startsWith('+') && text.includes('เพิ่ม') && text.length < 15);
      });
      if (addBtn) {
        trigger(addBtn);
        return { success: true, method: 'direct-button' };
      }
      return { success: false };
    })()`,
    returnByValue: true,
  });

  if (!step1?.result?.value?.success) {
    return { success: false, reason: 'หาปุ่ม "+ เพิ่ม" บนหน้าเว็บไม่พบ' };
  }

  // Wait for "เพิ่มลิงก์" (ประเภทของลิงก์: สินค้า) modal
  await sleep(1500);

  // Step 2: Click "ถัดไป" in the "เพิ่มลิงก์" modal
  // From here on every step happens inside the modal that just opened --
  // scope queries to it (falls back to the whole document if TikTok
  // doesn't mark it with role="dialog", so this is never worse than a
  // full-document search, only ever narrower and cheaper when it matches).
  const step2 = await send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.querySelector('[role="dialog"]') || document;
      const buttons = Array.from(root.querySelectorAll('button, div[role="button"]'));
      const nextBtn = buttons.reverse().find(b => {
        const t = (b.innerText || b.textContent || '').trim();
        return t === 'ถัดไป' || t === 'Next';
      });
      if (nextBtn) {
        nextBtn.click();
        return true;
      }
      return false;
    })()`,
    returnByValue: true,
  });

  if (!step2?.result?.value) {
    return { success: false, reason: 'หน้าต่างเลือกประเภทลิงก์ไม่เปิด' };
  }

  // Wait for "< เพิ่มลิงก์สินค้า" modal to load
  await sleep(1800);

  // Step 3: Switch to "นำเสนอสินค้า" tab using robust multi-event & CDP click
  // Stop here (rather than warn-and-continue) if the switch didn't land --
  // continuing means typing the product ID into whatever's on the WRONG tab
  // ("ร้านของฉัน" has no real search box, so step 4/5 below would silently
  // no-op or match nothing, reported back as a confusing unrelated failure
  // instead of the actual root cause).
  const switched = await switchToShowcaseTab(send);
  if (!switched) {
    return { success: false, reason: 'สลับไปแท็บ "นำเสนอสินค้า" ไม่สำเร็จ (ยังค้างอยู่ที่ "ร้านของฉัน") -- ลองกดขั้นนี้ซ้ำอีกครั้ง' };
  }

  await sleep(1200);

  // Step 4: Type Product ID into search box and trigger search
  const searchResult = await send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.querySelector('[role="dialog"]') || document;
      const inputs = Array.from(root.querySelectorAll('input'));
      const search = inputs.find(i => {
        const p = (i.placeholder || '').toLowerCase();
        return p.includes('ค้นหา') || p.includes('search');
      });
      if (search) {
        search.focus();
        search.select();
        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
        if (nativeSetter) {
          nativeSetter.call(search, ${JSON.stringify(productId)});
        } else {
          search.value = ${JSON.stringify(productId)};
        }
        search.dispatchEvent(new Event('input', { bubbles: true }));
        search.dispatchEvent(new Event('change', { bubbles: true }));

        return true;
      }
      return false;
    })()`,
    returnByValue: true,
  });

  if (searchResult.exceptionDetails || !searchResult.result?.value) {
    return {success:false, reason:'ไม่พบช่องค้นหาสินค้าที่พร้อมกรอก'};
  }

  // Value is already set above. InsertText here appended the same ID again.
  try {
    await send('Input.dispatchKeyEvent', {
      type: 'rawKeyDown',
      key: 'Enter',
      code: 'Enter',
      windowsVirtualKeyCode: 13,
    });
    await send('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key: 'Enter',
      code: 'Enter',
      windowsVirtualKeyCode: 13,
    });
  } catch (e) {}

  // Wait for table to filter and display the item
  await sleep(2500);

  // Select only a row containing the complete search term. Never silently
  // fall back to the first product when search returned nothing.
  const productRowQuery = OmniAutomation.page(`
    if (!dialog) return null;
    const query = ${JSON.stringify(String(productId).trim())};
    const rows = Array.from(dialog.querySelectorAll('table tr, [role="row"]')).filter(row => {
      if (!visible(row) || row.querySelector('th')) return false;
      const text = label(row);
      return /^\\d+$/.test(query)
        ? text.split(/\\D+/).includes(query)
        : text.toLowerCase().includes(query.toLowerCase());
    });
    return rows.length === 1 ? rows[0] : null;
  `);
  await OmniAutomation.wait(send, `Boolean(${productRowQuery})`, 'ไม่พบสินค้าตรง ID เพียงรายการเดียว กรุณาตรวจคำค้นหา');
  const selection = await OmniAutomation.evaluate(send, `(() => {
    const row = ${productRowQuery};
    if (!row) return null;
    const radio = row.querySelector('input[type="radio"], [role="radio"]');
    if (!radio || radio.disabled || radio.getAttribute('aria-disabled') === 'true') return null;
    const names = Array.from(row.querySelectorAll('td, [role="cell"]'))
      .map(el => (el.innerText || '').trim()).filter(t => t && !/^[\\d\\s.,฿%]+$/.test(t));
    names.sort((a,b) => b.length - a.length);
    radio.scrollIntoView({block:'center'});
    if (!radio.checked && radio.getAttribute('aria-checked') !== 'true') radio.click();
    return {name:names[0] || ''};
  })()`);
  if (!selection) return {success:false, reason:'เลือกสินค้าตรง ID ไม่สำเร็จ'};
  await OmniAutomation.wait(send, `(() => {
    const row = ${productRowQuery};
    const radio = row?.querySelector('input[type="radio"], [role="radio"]');
    return Boolean(radio && (radio.checked || radio.getAttribute('aria-checked') === 'true'));
  })()`, 'TikTok ยังไม่ยืนยันการเลือกสินค้า');

  await sleep(1000);

  // Step 6: Click "ถัดไป" at the bottom right
  const step6 = await send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.querySelector('[role="dialog"]') || document;
      const buttons = Array.from(root.querySelectorAll('button, div[role="button"]'));
      const nextBtn = buttons.reverse().find(b => {
        const t = (b.innerText || b.textContent || '').trim();
        return (t === 'ถัดไป' || t === 'Next') && !b.disabled;
      });
      if (nextBtn) {
        nextBtn.click();
        return true;
      }
      return false;
    })()`,
    returnByValue: true,
  });

  if (!step6?.result?.value) {
    return { success: false, reason: 'ปุ่มถัดไปในหน้ารายการสินค้ากดไม่ได้' };
  }

  // Wait for step 2 ("ชื่อสินค้าจะปรากฏขึ้นในวิดีโอของคุณ")
  await sleep(1600);

  // Step 7: Click "เพิ่ม" (Add)
  const step7 = await send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.querySelector('[role="dialog"]') || document;
      const buttons = Array.from(root.querySelectorAll('button, div[role="button"]'));
      const addBtn = buttons.reverse().find(b => {
        const t = (b.innerText || b.textContent || '').trim();
        return (t === 'เพิ่ม' || t === 'Add') && !b.disabled && t !== 'เพิ่มลิงก์' && t !== '+ เพิ่ม';
      });
      if (addBtn) {
        addBtn.click();
        return true;
      }
      return false;
    })()`,
    returnByValue: true,
  });

  if (!step7?.result?.value || step7.exceptionDetails) {
    return {success:false, reason:'กดปุ่มเพิ่มในหน้าสุดท้ายไม่สำเร็จ'};
  }
  await OmniAutomation.wait(send, OmniAutomation.page(`
    if (dialog) return false;
    const text = document.body.innerText || '';
    const name = ${JSON.stringify(selection.name)};
    return text.includes(${JSON.stringify(String(productId))}) || Boolean(name && text.includes(name));
  `), 'ยังยืนยันสินค้าที่แนบบนหน้าโพสต์ไม่ได้ กรุณาตรวจตะกร้าบน TikTok');
  return {success:true};
}

// Switches upload form to "กำหนดเวลาโพสต์" / "ตั้งเวลา" (Schedule) option
async function switchToScheduleMode(send) {
  const { result } = await send('Runtime.evaluate', {
    expression: `(() => {
      // Exact-text match on LEAF elements only (label/span/div with no
      // matching-text children of their own) -- matching on ANY ancestor
      // whose combined innerText merely *includes* the phrase let a big
      // wrapping <div> (e.g. the whole "post settings" section, which also
      // contains the unrelated "ตำแหน่งที่ตั้ง" location field right below
      // the schedule toggle) win the search. The old code then did
      // el.querySelector('input') on that wide match -- the FIRST input
      // inside a wide container is not necessarily the schedule radio, so it
      // ended up opening the location dropdown instead (caught on a real
      // screen recording, 2026-09-06).
      const TARGETS = ['ตั้งเวลา', 'กำหนดเวลาโพสต์', 'กำหนดเวลา', 'Schedule'];
      const isLeafMatch = (el) => {
        const t = (el.innerText || el.textContent || '').trim();
        if (!TARGETS.includes(t)) return false;
        // Reject if a child element repeats the same exact text -- that
        // child is the real leaf, this element is just its container.
        return !Array.from(el.children).some(c => TARGETS.includes((c.innerText || c.textContent || '').trim()));
      };

      const candidates = Array.from(document.querySelectorAll('label, span, div, p')).filter(isLeafMatch);
      if (candidates.length === 0) return { success: false, reason: 'not-found' };

      // Prefer the smallest (most specific) match if several leaves matched.
      candidates.sort((a, b) => {
        const rA = a.getBoundingClientRect();
        const rB = b.getBoundingClientRect();
        return (rA.width * rA.height) - (rB.width * rB.height);
      });
      const target = candidates[0];

      // Click the radio/checkbox this label is FOR, or one immediately
      // adjacent to it -- never a descendant search on a wide ancestor.
      const forId = target.getAttribute('for');
      const byFor = forId ? document.getElementById(forId) : null;
      const input = byFor
        || target.closest('label')?.querySelector(':scope > input[type="radio"], :scope > input[type="checkbox"]')
        || target.parentElement?.querySelector(':scope > input[type="radio"], :scope > input[type="checkbox"]')
        || target;

      target.scrollIntoView({ behavior: 'instant', block: 'center' });
      input.click();
      return { success: true };
    })()`,
    returnByValue: true,
  });
  return Boolean(result?.value?.success);
}

// After a successful Post/Schedule click, TikTok Studio's own SPA can throw
// up its native "are you sure you want to leave? your progress will not be
// saved" navigation guard before it finishes routing to the post-manage
// page -- confirmed from a real screen recording (2026-09-06): the post/
// schedule genuinely succeeded, this dialog just sat there needing a manual
// click through. Not confirmed whether it fires every time or only
// sometimes, so this is best-effort and silent either way: poll briefly,
// click "ออก"/"Leave" if it shows up, and just return false if it never
// appears within the timeout -- never throws, since this dialog might
// legitimately not exist on a given run.
async function dismissLeaveConfirmDialogIfPresent(send, timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const { result } = await send('Runtime.evaluate', {
      expression: `(() => {
        const heading = Array.from(document.querySelectorAll('h1, h2, h3, div, p')).find(el => {
          const t = (el.innerText || el.textContent || '').trim();
          return t.includes('แน่ใจหรือไม่ว่าต้องการออก') || t.includes('Are you sure you want to leave');
        });
        if (!heading) return false;
        const dialog = heading.closest('[role="dialog"], [class*="modal"]') || document;
        const buttons = Array.from(dialog.querySelectorAll('button'));
        const leaveBtn = buttons.find(b => {
          const t = (b.innerText || b.textContent || '').trim();
          return t === 'ออก' || t === 'Leave' || t === 'leave';
        });
        if (leaveBtn) {
          leaveBtn.click();
          return true;
        }
        return false;
      })()`,
      returnByValue: true,
    });
    if (result?.value) return true;
    await sleep(300);
  }
  return false;
}

// UNVERIFIED (plan §3): selector is the plan's best-guess placeholder
// (`.btn-post:not(.disabled)`). Only runs when the user has explicitly
// opted into auto-click via the popup checkbox -- default is to stop
// right before this and let the user press Post themselves.
async function clickPostButton(send) {
  // Ensure video upload/processing is complete before attempting to click post!
  if (!await waitForUploadComplete(send, 60_000)) {
    throw new Error('TikTok ยังประมวลผลไม่เสร็จ จึงยังไม่กดโพสต์');
  }

  const { result } = await send('Runtime.evaluate', {
    expression: `(() => {
      const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="menu"], [class*="nav"], [class*="aside"]'));

      // 1. Try selector with data-e2e or class
      const directBtn = document.querySelector('button[data-e2e="post_video_button"]:not([disabled]), .btn-post:not(.disabled)');
      if (directBtn && !isNav(directBtn)) {
        directBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
        directBtn.click();
        return { success: true, method: 'direct' };
      }

      // 2. Search strictly <button> elements (NEVER div[role="button"] which is used by sidebar menu links!)
      const buttons = Array.from(document.querySelectorAll('button'));
      const validButtons = buttons.filter(b => {
        if (isNav(b)) return false;
        if (b.disabled || b.getAttribute('aria-disabled') === 'true') return false;
        const text = (b.innerText || b.textContent || '').trim();
        return text === 'โพสต์' || text === 'กำหนดเวลา' || text === 'Post' || text === 'Schedule';
      });

      if (validButtons.length > 0) {
        const postBtn = validButtons[validButtons.length - 1];
        postBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
        postBtn.click();
        return { success: true, method: 'button-text' };
      }
      return { success: false };
    })()`,
    returnByValue: true,
  });
  if (!result?.value?.success) {
    throw new Error('หาปุ่ม Post / กำหนดเวลา ที่กดได้ไม่เจอ (อาจยังประมวลผลไม่เสร็จ) -- กดเองแทน');
  }
}

// 2026-09-06: minimal, deliberately-does-nothing-else action, added after
// POST-2.10's isolation test showed the tab crash happens even with ZERO
// CDP commands sent, purely from chrome.debugger sitting attached while
// TikTok's own effects/cover engine initializes after a file is set. The
// fix that test points at: never HOLD the debugger attached through that
// window at all. This sets the file and detaches again immediately --
// attached for well under a second, nowhere near long enough to overlap
// with that engine's startup -- then leaves the rest (caption, product
// link) to the separate buttons below, each of which is its own short
// attach/act/detach cycle instead of one long session spanning the upload.
async function runUploadFileOnly() {
  const job = await fetchPendingJob();
  if (!job.video_path) {
    throw new Error('ไม่มีคลิปที่เตรียมไว้ -- กด "โพสต์ TikTok อัตโนมัติ" ในแอป OmniCut ก่อน');
  }
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    const fileNodeId = await findFileInputNodeId(send);
    await setFileInput(send, fileNodeId, job.video_path);
    return { success: true };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

// 2026-09-06: kept deliberately single-purpose (product link only, no
// scheduleMode) so each checklist step in the popup is its own isolated
// attach/act/detach cycle -- see runScheduleModeOnly() and
// runClickPostOnly() below for the steps this used to also do inline.
async function runUploadCoverOnly() {
  const job = await fetchPendingJob();
  if (!job.cover_path) throw new Error('ยังไม่มีปก กดบันทึกปกในโปรแกรมแล้วเตรียมคลิปใหม่');
  const tab = await findUploadTab();
  await chrome.debugger.attach({tabId:tab.id}, '1.3');
  try {
    const send = cdp(tab.id);
    await send('DOM.enable');
    return await OmniAutomation.uploadCover(send, job.cover_path);
  } finally {
    await chrome.debugger.detach({tabId:tab.id}).catch(() => {});
  }
}

async function runAttachProductOnly({ productId }) {
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');

    const attachResult = await attachProductLink(send, productId);

    return {
      success: attachResult.success,
      reason: attachResult.reason,
      attachedProduct: attachResult.success,
    };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

// Step-by-step checklist (2026-09-06, user request): each of these is its
// own short attach -> act -> detach cycle, run one at a time from the
// popup's checklist so the user can tell exactly which addition on top of
// a working state is the one that introduces the crash, instead of guessing
// at the whole combined flow again.
async function runScheduleModeOnly() {
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');
    const switched = await switchToScheduleMode(send);
    if (!switched) {
      return { success: false, reason: 'หาตัวเลือก "กำหนดเวลา"/"ตั้งเวลา" บนหน้าเว็บไม่พบ' };
    }
    return { success: true };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

async function runClickPostOnly() {
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');
    await clickPostButton(send);
    return { success: true, clicked:true, posted:false };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

async function runTypeCaptionOnly({ caption, hashtags }) {
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');

    await waitForCaptionEditor(send);

    const captionParts = [];
    if (caption && caption.trim()) captionParts.push(caption.trim());
    if (hashtags && hashtags.trim()) captionParts.push(hashtags.trim());
    const fullCaption = captionParts.join('\n\n');

    if (fullCaption) {
      await typeCaption(send, fullCaption);
    }
    return { success: true };
  } finally {
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {}
  }
}

// Automated preparation stops before publication. Each stage has its own session.
async function runPrepareDetails(message) {
  const job = await fetchPendingJob();
  const completed = [];
  let step = 'caption';
  try {
    const caption = message.caption ?? job.caption ?? '';
    const hashtags = message.hashtags ?? job.hashtags ?? '';
    if (![caption, hashtags].some(value => value.trim())) throw new Error('กรุณากรอกคำอธิบายหรือแฮชแท็ก');
    await runTypeCaptionOnly({caption, hashtags});
    completed.push('caption');
    step = 'product';
    const productId = message.productId || job.tiktok_product_id;
    if (!productId) throw new Error('กรุณากรอก ID สินค้า');
    const product = await runAttachProductOnly({productId});
    if (!product.success) throw new Error(product.reason);
    completed.push('product');
    step = 'cover';
    await runUploadCoverOnly();
    completed.push('cover');
    if (message.scheduleMode) {
      step = 'schedule';
      const schedule = await runScheduleModeOnly();
      if (!schedule.success) throw new Error(schedule.reason);
      completed.push('schedule');
    }
    return {success:true, completed};
  } catch (err) {
    return {success:false, completed, step, error:err.message};
  }
}

let actionRunning = false;
let pinnedUploadTabId = null;
const actions = {
  'upload-file-only': () => runUploadFileOnly(),
  'type-caption-only': message => runTypeCaptionOnly(message),
  'attach-product-only': message => runAttachProductOnly(message),
  'schedule-mode-only': () => runScheduleModeOnly(),
  'click-post-only': () => runClickPostOnly(),
  'upload-cover-only': () => runUploadCoverOnly(),
  'prepare-details': message => runPrepareDetails(message),
};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.action === 'run-autopost') {
    sendResponse({success:false, error:'กรุณาใช้ปุ่มทำต่อหลังอัปโหลดในแถบข้างรุ่นล่าสุด'});
    return false;
  }
  const action = actions[message?.action];
  if (!action) return false;
  if (actionRunning) {
    sendResponse({success:false, error:'มีขั้นตอนกำลังทำอยู่ กรุณารอให้จบก่อน'});
    return false;
  }
  actionRunning = true;
  (async () => {
    try {
      pinnedUploadTabId = (await findUploadTab()).id;
      return await action(message);
    } finally {
      pinnedUploadTabId = null;
      actionRunning = false;
    }
  })().then(sendResponse).catch(err => sendResponse({success:false, error:err.message || String(err)}));
  return true;
});
