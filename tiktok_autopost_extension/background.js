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
async function typeCaption(send, captionOrText, hashtags = '') {
  let caption = captionOrText || '';
  let tags = hashtags || '';
  // Support single multiline string if hashtags omitted
  if (!tags && typeof caption === 'string' && caption.includes('\n\n')) {
    const idx = caption.indexOf('\n\n');
    tags = caption.slice(idx + 2);
    caption = caption.slice(0, idx);
  }

  const cleanCaption = String(caption || '').trim();
  const cleanTags = String(tags || '').trim();
  if (!cleanCaption && !cleanTags) throw new Error('กรุณากรอกคำอธิบายหรือแฮชแท็ก');

  const captionQuery = OmniAutomation.page(`
    const editors = Array.from(document.querySelectorAll('[contenteditable="true"]')).filter(el =>
      visible(el) && !el.closest('[role="dialog"], [aria-modal="true"]'));
    return editors.length === 1 ? editors[0] : null;
  `);

  // 1. Focus editor and clear existing text cleanly using native Ctrl+A + Backspace
  // Draft.js strictly requires native keyboard events to update its internal EditorState
  const focused = await OmniAutomation.evaluate(send, `(() => {
    const el = ${captionQuery};
    if (!el) return false;
    el.focus();
    return document.activeElement === el;
  })()`);

  if (!focused) throw new Error('ไม่พบช่องแคปชันที่พร้อมกรอก หรือมีหลายช่อง กรุณาปิดหน้าต่างอื่นบน TikTok');

  await sleep(150);

  // Clear any existing text (auto-filled filename or previous content)
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65, modifiers: 2 });
  await sleep(50);
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
  await sleep(150);

  // 2. Type clean caption first
  if (cleanCaption) {
    await send('Input.insertText', { text: cleanCaption });
    await sleep(250);
  }

  // 3. If hashtags exist, insert two line breaks and then type hashtags second
  if (cleanTags) {
    if (cleanCaption) {
      for (let i = 0; i < 2; i++) {
        await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' });
        await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
        await sleep(100);
      }
    }
    await send('Input.insertText', { text: cleanTags });
    await sleep(250);
  }

  // 4. Verify that content was accepted IN FULL (not just a 10-char prefix)
  // and that caption comes before hashtags. Draft.js can drop text mid-insert
  // if the editor loses focus, and a prefix-only check let a truncated or
  // garbled caption pass silently as long as the first ~10 chars matched.
  //
  // Normalization must be identical on both sides (what we tried to type vs.
  // what innerText reports back) or this would never pass at all: the
  // contenteditable's innerText legitimately differs from the raw input in
  // whitespace/newline handling (Draft.js renders each line as its own
  // block, so consecutive blank lines can collapse or gain trailing spaces)
  // and can contain zero-width characters the input never had. `normalize()`
  // here: trims each line, drops zero-width/BOM chars, collapses runs of
  // whitespace to a single space, and joins lines with a single '\n' --
  // applied identically to the expected and actual strings so real
  // formatting differences wash out but dropped/garbled content does not.
  const normalizeForCompare = (s) => String(s || '')
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .split('\n')
    .map((line) => line.trim().replace(/\s+/g, ' '))
    .join('\n')
    .trim();

  const normCaption = normalizeForCompare(cleanCaption);
  const normTags = normalizeForCompare(cleanTags);

  await OmniAutomation.wait(send, `(() => {
    const el = ${captionQuery};
    const raw = el ? (el.innerText || el.textContent || '') : '';
    if (!raw.trim()) return false;
    const normalize = (s) => String(s || '')
      .replace(/[\\u200B-\\u200D\\uFEFF]/g, '')
      .split('\\n')
      .map((line) => line.trim().replace(/\\s+/g, ' '))
      .join('\\n')
      .trim();
    const current = normalize(raw);
    const hasCap = ${JSON.stringify(normCaption)};
    const hasTag = ${JSON.stringify(normTags)};
    if (hasCap && !current.includes(hasCap)) return false;
    if (hasTag && !current.includes(hasTag)) return false;
    if (hasCap && hasTag) {
      return current.indexOf(hasCap) < current.indexOf(hasTag);
    }
    return true;
  })()`, 'TikTok ยังไม่รับแคปชันครบตามที่พิมพ์ (อาจถูกตัด/เพี้ยนบางส่วน) กรุณาตรวจช่องคำอธิบาย', 5000);
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
// Switches to "นำเสนอสินค้า" (Showcase / Product Showcase) tab reliably.
async function switchToShowcaseTab(send) {
  const isActive = async () => {
    const r = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
        };

        // 1. Strict check: which tab has TUXTabBar-itemTitle--active
        const activeItem = document.querySelector('.TUXTabBar-itemTitle--active, [class*="itemTitle--active"]');
        if (activeItem && isVisible(activeItem)) {
          const t = (activeItem.innerText || activeItem.textContent || '').trim();
          // Active tab must be Showcase / นำเสนอสินค้า, NEVER ร้านของฉัน / My shop
          if ((t.includes('นำเสนอสินค้า') || t.includes('Showcase')) && !t.includes('ร้าน') && !t.includes('Shop')) {
            return true;
          }
        }

        // 2. Check tab button with id="2"
        let tab2 = null;
        try {
          tab2 = document.querySelector('.TUXTabBar-item[id="2"] button, button.TUXTabBar-itemTitle[id="2"], [id="2"] button');
        } catch (e) {}
        if (tab2 && isVisible(tab2)) {
          if (tab2.classList.contains('TUXTabBar-itemTitle--active') || tab2.getAttribute('data-active') !== null) {
            return true;
          }
        }

        return false;
      })()`,
      returnByValue: true,
    });
    return Boolean(r?.result?.value);
  };

  if (await isActive()) return true;

  for (let attempt = 0; attempt < 6; attempt++) {
    const found = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
        };

        // Target: [id="2"] button or button with text "นำเสนอสินค้า"
        let primaryTarget = null;
        try {
          primaryTarget = document.querySelector('.TUXTabBar-item[id="2"] button, button.TUXTabBar-itemTitle[id="2"], [id="2"] button, .TUXTabBar-item[id="2"]');
        } catch (e) {}

        if (!primaryTarget) {
          const allElements = Array.from(document.querySelectorAll('.TUXTabBar-itemTitle, [class*="itemTitle"], button, div, span')).filter(isVisible);
          primaryTarget = allElements.find(el => {
            const t = (el.innerText || el.textContent || '').trim();
            if (!t) return false;
            if (t.includes('ร้านของฉัน') || t.includes('My Shop') || t.includes('My shop') || t.includes('จัดการสินค้า')) return false;
            return t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase products' || t.includes('Showcase products') || t === 'Showcase' || t.includes('Showcase');
          });
        }

        if (!primaryTarget) return null;

        const tabContainer = primaryTarget.closest('button, .TUXTabBar-item') || primaryTarget;
        // React/TUX tabs toggle on one logical click. Do not synthesize a
        // pointer sequence on both the item and its button; that previously
        // produced duplicate state transitions and left the modal on the
        // wrong tab.
        try { tabContainer.focus(); } catch (e) {}
        try { tabContainer.click(); } catch (e) { return null; }

        const rect = tabContainer.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
      })()`,
      returnByValue: true,
    });

    const point = found?.result?.value;
    if (point && point.x > 0 && point.y > 0) {
      try {
        await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: Math.round(point.x), y: Math.round(point.y) });
        await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', buttons: 1, clickCount: 1, x: Math.round(point.x), y: Math.round(point.y) });
        await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', buttons: 0, clickCount: 1, x: Math.round(point.x), y: Math.round(point.y) });
      } catch (e) {}
    }

    await sleep(1000);
    if (await isActive()) return true;
  }
  return false;
}

// Automatically clicks "+ เพิ่ม" under "เพิ่มลิงก์", searches product by ID, and adds it.
async function attachProductLink(send, productId, cartName = '') {
  if (!productId) return { success: false, reason: 'ไม่มี Product ID' };

  // Step 0: Check if modal "< เพิ่มลิงก์สินค้า" is ALREADY open
  const alreadyInProductModalCheck = await send('Runtime.evaluate', {
    expression: `(() => {
      const isVisible = (el) => {
        if (!el) return false;
        if (typeof el.checkVisibility === 'function') {
          return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
        }
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
      };
      const texts = Array.from(document.querySelectorAll('h1, h2, h3, h4, [role="tab"], div, span'))
        .filter(isVisible)
        .map(el => (el.innerText || el.textContent || '').trim());
      const hasShowcaseTab = texts.some(t => t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase' || t.includes('Showcase products'));
      const hasModalTitle = texts.some(t => t.includes('เพิ่มลิงก์สินค้า') || t.includes('Add product links'));
      return hasShowcaseTab || hasModalTitle;
    })()`,
    returnByValue: true,
  });

  const alreadyInProductModal = Boolean(alreadyInProductModalCheck?.result?.value);

  if (!alreadyInProductModal) {
    // Step 1: Click "+ เพิ่ม" button under "เพิ่มลิงก์"
    const step1 = await send('Runtime.evaluate', {
      expression: `(() => {
        const trigger = (el) => {
          if (!el) return;
          el.scrollIntoView({ behavior: 'instant', block: 'center' });
          el.click();
        };

        const isNav = (el) => Boolean(el.closest('aside, nav, header, [class*="sidebar"], [class*="nav"], [class*="menu"]'));

        // 1. Look for "เพิ่มลิงก์" header and find "+ เพิ่ม" inside its parent container
        const allDivs = Array.from(document.querySelectorAll('div, section, p, span, h1, h2, h3, h4'));
        const header = allDivs.find(el => !isNav(el) && ((el.innerText || el.textContent || '').trim() === 'เพิ่มลิงก์' || (el.innerText || el.textContent || '').trim() === 'Add link'));
        if (header) {
          let parent = header.parentElement;
          for (let i = 0; i < 5 && parent; i++) {
            const btns = Array.from(parent.querySelectorAll('button, div[role="button"], span[role="button"]'));
            const btn = btns.find(b => {
              if (isNav(b)) return false;
              const t = (b.innerText || b.textContent || '').trim();
              return (t.includes('เพิ่ม') || t.includes('Add') || t.includes('+')) && t !== 'เพิ่มลิงก์' && t !== 'Add link';
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
          return text === '+ เพิ่ม' || text === '+เพิ่ม' || text === '+ Add' || text === '+Add' ||
            ((text.startsWith('+') || text.includes('+')) && (text.includes('เพิ่ม') || text.includes('Add')) && text.length < 15);
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
    const step2 = await send('Runtime.evaluate', {
      expression: `(() => {
        const root = document.querySelector('[role="dialog"], [aria-modal="true"]') || document;
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
  }

  // Step 3: Switch to "นำเสนอสินค้า" tab
  const switched = await switchToShowcaseTab(send);
  if (!switched) {
    return { success: false, reason: 'สลับไปแท็บ "นำเสนอสินค้า" ไม่สำเร็จ (ยังค้างอยู่ที่ "ร้านของฉัน") -- ลองกดขั้นนี้ซ้ำอีกครั้ง' };
  }

  await sleep(1000);

  // Step 4: Type Product ID into search box and trigger search (retry up to 6 times while Showcase tab loads)
  let searchFound = false;
  for (let attempt = 0; attempt < 6; attempt++) {
    const searchResult = await send('Runtime.evaluate', {
      expression: `(() => {
        // 1. Check if Showcase is in empty state (no products added yet)
        const emptyContainer = Array.from(document.querySelectorAll('.product-empty-container, [class*="empty"], .tips-title')).find(el => {
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0;
        });
        if (emptyContainer) {
          const text = (emptyContainer.innerText || emptyContainer.textContent || '').trim();
          if (text.includes('No products in your showcase') || text.includes('ไม่มีสินค้าในตู้โชว์') || text.includes('ไม่มีสินค้าในการนำเสนอ')) {
            return { emptyShowcase: true, text };
          }
        }

        // 2. Find search input box across the modal and document
        const isSearchCandidate = (i) => {
          if (!i || i.type === 'file' || i.type === 'radio' || i.type === 'checkbox' || i.type === 'button') return false;
          const rect = i.getBoundingClientRect();
          if (rect.width === 0 || rect.height === 0) return false;
          const p = (i.placeholder || '').toLowerCase();
          return p.includes('ค้นหา') || p.includes('search') || p.includes('สินค้า');
        };

        const allInputs = Array.from(document.querySelectorAll('input'));
        // Exact selectors from live TikTok Studio DOM screenshot
        const search = document.querySelector('input.TUXTextInputCore-input, .product-search-input input, .product-search-bar input, input[placeholder="ค้นหาสินค้า"]')
          || allInputs.find(isSearchCandidate)
          || document.querySelector('input[placeholder*="ค้นหา"], input[placeholder*="Search"], input[placeholder*="สินค้า"]')
          || document.querySelector('[class*="search"] input, [class*="Search"] input, .TUXInput-input')
          || allInputs.find(i => (i.type === 'text' || !i.type) && i.getBoundingClientRect().width > 100);

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

          // Click trailing icon wrapper (.TUXTextInputCore-trailingIconWrapper)
          const icon = document.querySelector('.TUXTextInputCore-trailingIconWrapper')
            || (search.parentElement && search.parentElement.querySelector('.TUXTextInputCore-trailingIconWrapper, svg, button'))
            || (search.closest('[class*="search"], [class*="input"], div') && search.closest('[class*="search"], [class*="input"], div').querySelector('svg, button, [role="button"], span, i'));
          if (icon && icon !== search) {
            try { icon.click(); } catch(e) {}
          }
          return { success: true };
        }
        return { success: false };
      })()`,
      returnByValue: true,
    });

    const searchVal = searchResult?.result?.value;
    if (searchVal?.emptyShowcase) {
      return {
        success: false,
        reason: 'ในตู้โชว์ (Showcase) ของบัญชี TikTok นี้ยังไม่มีสินค้า กรุณาเพิ่มสินค้าลงใน Showcase ผ่านแอป TikTok (Profile > TikTok Shop) ก่อนทำขั้นตอนนี้',
      };
    }

    if (searchVal?.success) {
      searchFound = true;
      break;
    }
    await sleep(800);
  }

  if (!searchFound) {
    return { success: false, reason: 'ไม่พบช่องค้นหาสินค้าที่พร้อมกรอก (ลองตรวจสอบว่าอยู่ในแท็บ "นำเสนอสินค้า" แล้วหรือยัง)' };
  }

  // Trigger search via Enter key
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

  // Wait for search result table to load
  await sleep(2500);

  // Step 5: Select product from search results and verify radio is checked
  let selection = null;
  let lastNotFoundReason = null;
  for (let retry = 0; retry < 8; retry++) {
    const sel = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };

        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
          .filter(isVisible);
        const productContainer = document.querySelector('.product-selector-container');
        const root = productContainer?.closest('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')
          || dialogs.at(-1) || document;
        const rows = Array.from(root.querySelectorAll('tr.product-tb-row, [class*="product-tb-row"], table tr, [role="row"], tbody tr'))
          .filter(r => isVisible(r) && !r.querySelector('th'));

        if (rows.length === 0) return null;

        const query = ${JSON.stringify(String(productId).trim())};
        const querySuffix = query.length > 6 ? query.slice(-6) : query;

        // Try to find a row matching the query or its suffix
        let targetRow = rows.find(row => {
          const text = (row.innerText || row.textContent || '').trim();
          return text.includes(query) || text.includes(querySuffix);
        });

        if (!targetRow) return { success: false, reason: 'product_not_found_in_results' };

        // Exact elements from DevTools: input.TUXRadioStandalone-input, .TUXRadioStandalone, .TUXRadio
        const input = targetRow.querySelector('input.TUXRadioStandalone-input, input[type="radio"]');
        const standalone = targetRow.querySelector('.TUXRadioStandalone');
        const tuxRadio = targetRow.querySelector('.TUXRadio');
        const nameCell = targetRow.querySelector('.product-name-cell, [class*="product-name"]');

        // TUXRadio is toggle-like. The old code clicked input, wrapper, name,
        // row, then CDP coordinates, which could select and immediately
        // deselect the same item. Perform one DOM click only; the outer loop
        // may use one native CDP click as a single fallback after verification.
        const isChecked = () => Boolean(
          (input && (input.checked || input.getAttribute('aria-checked') === 'true')) ||
          targetRow.querySelector('.TUXRadioStandalone--checked, [class*="--checked"], [aria-checked="true"]')
        );
        if (!isChecked()) {
          const clickTarget = standalone || tuxRadio || input;
          if (!clickTarget) return { success: false, reason: 'radio_not_found' };
          clickTarget.focus?.();
          clickTarget.click();
        }

        const clickTarget = standalone || tuxRadio || input || targetRow;
        try { clickTarget.scrollIntoView({ behavior: 'instant', block: 'center' }); } catch (e) {}
        const rect = clickTarget.getBoundingClientRect();
        const rowRect = targetRow.getBoundingClientRect();

        // Extract product name from row
        const cells = Array.from(targetRow.querySelectorAll('td, [role="cell"], div, span, p'))
          .map(el => (el.innerText || '').trim())
          .filter(t => t && !/^[\\d\\s.,฿%+-]+$/.test(t) && t.length > 3);
        cells.sort((a, b) => b.length - a.length);

        const checked = Boolean(
          targetRow.querySelector('.TUXRadioStandalone--checked, [class*="--checked"], input:checked') ||
          (input && input.checked)
        );

        return {
          success: true,
          name: cells[0] || '',
          point: { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 },
          rowPoint: { x: rowRect.left + Math.min(rowRect.width / 2, 200), y: rowRect.top + rowRect.height / 2 },
          checked: isChecked(),
        };
      })()`,
      returnByValue: true,
    });

    const selVal = sel?.result?.value;
    if (selVal?.success) {
      // Accept a DOM click only if it actually checked the radio. If React
      // ignored it, issue one native click at the radio point. Never click
      // both radio and row: that toggles the control back to unchecked.
      if (!selVal.checked && selVal.point && selVal.point.x > 0 && selVal.point.y > 0) {
        try {
          await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: Math.round(selVal.point.x), y: Math.round(selVal.point.y) });
          await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', buttons: 1, clickCount: 1, x: Math.round(selVal.point.x), y: Math.round(selVal.point.y) });
          await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', buttons: 0, clickCount: 1, x: Math.round(selVal.point.x), y: Math.round(selVal.point.y) });
        } catch (e) {}
      }

      await sleep(600);

      // Verify that radio became checked OR Next button became enabled
      const statusCheck = await send('Runtime.evaluate', {
        expression: `(() => {
          const productContainer = document.querySelector('.product-selector-container');
          const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
            .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
          const root = productContainer?.closest('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')
            || dialogs.at(-1) || productContainer || document;
          const isChecked = Boolean(root.querySelector('.TUXRadioStandalone--checked, [class*="--checked"], input[type="radio"]:checked'));
          const buttons = Array.from(root.querySelectorAll('button, div[role="button"]'));
          const nextBtn = buttons.reverse().find(b => {
            const t = (b.innerText || b.textContent || '').trim();
            const enabled = !b.disabled && b.getAttribute('aria-disabled') !== 'true';
            return (t === 'ถัดไป' || t === 'Next') && enabled && t !== 'ยกเลิก' && t !== 'Cancel';
          });
          return { isChecked, nextEnabled: Boolean(nextBtn) };
        })()`,
        returnByValue: true,
      });

      const st = statusCheck?.result?.value;
      if (st?.isChecked || st?.nextEnabled) {
        selection = selVal;
        break;
      }
    } else if (selVal && selVal.success === false && selVal.reason) {
      lastNotFoundReason = selVal.reason;
    }
    await sleep(800);
  }

  if (!selection) {
    if (lastNotFoundReason === 'product_not_found_in_results') {
      return { success: false, reason: 'product_not_found_in_results' };
    }
    return { success: false, reason: 'เลือกสินค้าตรง ID ไม่สำเร็จ (ไม่พบรายการสินค้าในผลการค้นหา)' };
  }

  await sleep(600);

  // Step 6: Click "ถัดไป" (Next) at the bottom right
  let step6Success = false;
  for (let retry = 0; retry < 5; retry++) {
    const step6 = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };
        const productContainer = document.querySelector('.product-selector-container');
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
          .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
        const root = productContainer?.closest('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal')
          || dialogs.at(-1) || productContainer || document;
        const buttons = Array.from(root.querySelectorAll('button, div[role="button"]')).filter(isVisible);
        const nextBtn = buttons.reverse().find(b => {
          const t = (b.innerText || b.textContent || '').trim();
          const enabled = !b.disabled && b.getAttribute('aria-disabled') !== 'true';
          return (t === 'ถัดไป' || t === 'Next') && enabled && t !== 'ยกเลิก' && t !== 'Cancel';
        });
        if (nextBtn) {
          nextBtn.focus();
          nextBtn.click();
          const rect = nextBtn.getBoundingClientRect();
          return { success: true, point: { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } };
        }
        return { success: false };
      })()`,
      returnByValue: true,
    });

    const step6Val = step6?.result?.value;
    if (step6Val?.success) {
      step6Success = true;
      break;
    }
    await sleep(800);
  }

  if (!step6Success) {
    return { success: false, reason: 'ปุ่มถัดไปในหน้ารายการสินค้ากดไม่ได้ (อาจยังไม่ได้เลือกสินค้า)' };
  }

  // Wait for step 2 ("ชื่อสินค้าจะปรากฏขึ้นในวิดีโอของคุณ" / Title setting view)
  await sleep(2000);

  // Step 7: TikTok opens a second dialog for the cart display name. Wait for
  // its TUX input, optionally replace the name, then click Add once.
  let step7Val = null;
  for (let retry = 0; retry < 8; retry++) {
    const step7 = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };
        const roots = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal'))
          .filter(isVisible);
        const root = roots.at(-1) || document;

        // 1. คลุมดำตั้งชื่อ (Highlight/select all in product title input: input.TUXTextInputCore-input)
        const nameInput = root.querySelector('input.TUXTextInputCore-input, input[type="text"], input:not([type]), textarea');
        if (nameInput && isVisible(nameInput)) {
          try {
            nameInput.focus();
            nameInput.select();
            const desired = ${JSON.stringify(String(cartName || ''))};
            if (desired) {
              const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
              if (setter) setter.call(nameInput, desired); else nameInput.value = desired;
              nameInput.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: desired }));
              nameInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
          } catch (e) {}
        }

        if (!nameInput || !isVisible(nameInput)) return { success: false, reason: 'cart_name_dialog_not_ready' };

        // 2. Click "เพิ่ม" (Add button as seen in DevTools screenshot)
        const buttons = Array.from(root.querySelectorAll('button, div[role="button"]')).filter(isVisible);
        const addBtn = buttons.find(b => {
          const t = (b.innerText || b.textContent || '').trim();
          const enabled = !b.disabled && b.getAttribute('aria-disabled') !== 'true';
          return (t === 'เพิ่ม' || t === 'Add' || t === 'ยืนยัน' || t === 'Confirm' || t === 'ถัดไป') &&
                 enabled && t !== 'เพิ่มลิงก์' && t !== '+ เพิ่ม' && t !== 'ยกเลิก' && t !== 'Cancel';
        });
        if (addBtn) {
          addBtn.click();
          const rect = addBtn.getBoundingClientRect();
          return { success: true, point: { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } };
        }
        return { success: false };
      })()`,
      returnByValue: true,
    });

    step7Val = step7?.result?.value;
    if (step7Val?.success) break;
    await sleep(700);
  }

  if (!step7Val?.success) {
    return { success: false, reason: 'กดปุ่มถัดไป/เพิ่มในหน้าตั้งชื่อสินค้าไม่สำเร็จ' };
  }

  await sleep(1500);

  // Step 8: Verify the product actually attached. Finding+clicking the Add
  // button proves nothing on its own -- this is an affiliate tool, so a post
  // published with no product link attached is a total commercial loss.
  // Evidence checked for: the "< เพิ่มลิงก์สินค้า" / "เพิ่มลิงก์" modal
  // having closed, OR a product chip/badge for this item now showing in the
  // compose form underneath the caption editor.
  const attachConfirmed = await (async () => {
    const deadline = Date.now() + 8000;
    while (Date.now() < deadline) {
      const check = await send('Runtime.evaluate', {
        expression: `(() => {
          const isVisible = (el) => {
            if (!el) return false;
            if (typeof el.checkVisibility === 'function') {
              return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
            }
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
          };

          // 1. Modal closed: neither the product-link modal title nor the
          // Showcase tab (both only visible while the modal is open) remain
          // on screen.
          const texts = Array.from(document.querySelectorAll('h1, h2, h3, h4, [role="tab"], div, span'))
            .filter(isVisible)
            .map(el => (el.innerText || el.textContent || '').trim());
          const modalStillOpen = texts.some(t =>
            t.includes('เพิ่มลิงก์สินค้า') || t.includes('Add product links') ||
            t === 'นำเสนอสินค้า' || t.includes('นำเสนอสินค้า') || t === 'Showcase' || t.includes('Showcase products'));
          if (!modalStillOpen) {
            return { done: true, ok: true, reason: 'modal-closed' };
          }

          // 2. Product chip/badge visible in the compose form (outside any
          // dialog) -- e.g. a card showing the attached product's name/price
          // under the caption editor. TikTok renders this with classes like
          // "product-anchor", "productCard", "anchor-card"; fall back to any
          // visible element outside a dialog that shows the attached
          // product's name text.
          const dialogRoot = document.querySelector('[role="dialog"], [aria-modal="true"], .semi-modal, .TUXModal');
          const chip = document.querySelector(
            '[class*="product-anchor"], [class*="productAnchor"], [class*="anchor-card"], [class*="product-card"], [class*="productCard"], [class*="linked-product"]'
          );
          if (chip && isVisible(chip) && (!dialogRoot || !dialogRoot.contains(chip))) {
            return { done: true, ok: true, reason: 'chip-visible' };
          }

          return { done: false };
        })()`,
        returnByValue: true,
      });

      const val = check?.result?.value;
      if (val?.done) return val.ok;
      await sleep(500);
    }
    return false;
  })();

  if (!attachConfirmed) {
    return { success: false, reason: 'product_attach_not_confirmed: กดเพิ่มลิงก์สินค้าแล้ว แต่ไม่พบหลักฐานว่าแนบติดจริง (หน้าต่างเลือกสินค้าอาจยังไม่ปิด หรือไม่มีชิปสินค้าโผล่ในฟอร์ม) กรุณาตรวจสอบด้วยตาก่อนโพสต์' };
  }

  return { success: true, productName: selection.name };
}

// Switches upload form to "กำหนดเวลาโพสต์" / "ตั้งเวลา" (Schedule) option
async function switchToScheduleMode(send, schedule = {}) {
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

  if (!result?.value?.success) return { success: false, reason: 'not-found' };

  // Clicking whatever element resolved (byFor input, or a fallback that can
  // be a non-interactive <span>/<div> when no real form control was found)
  // is not proof the toggle actually activated -- a click on a non-
  // interactive element is a no-op. Poll for real evidence: the radio/
  // checkbox reporting checked/aria-checked, or the date/time picker fields
  // that only render once schedule mode is active.
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    const verify = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };

        const TARGETS = ['ตั้งเวลา', 'กำหนดเวลาโพสต์', 'กำหนดเวลา', 'Schedule'];
        const isLeafMatch = (el) => {
          const t = (el.innerText || el.textContent || '').trim();
          if (!TARGETS.includes(t)) return false;
          return !Array.from(el.children).some(c => TARGETS.includes((c.innerText || c.textContent || '').trim()));
        };
        const candidates = Array.from(document.querySelectorAll('label, span, div, p')).filter(isLeafMatch);
        candidates.sort((a, b) => {
          const rA = a.getBoundingClientRect();
          const rB = b.getBoundingClientRect();
          return (rA.width * rA.height) - (rB.width * rB.height);
        });
        const target = candidates[0];

        // 1. The radio/checkbox this label controls reports checked.
        if (target) {
          const forId = target.getAttribute('for');
          const byFor = forId ? document.getElementById(forId) : null;
          const input = byFor
            || target.closest('label')?.querySelector(':scope > input[type="radio"], :scope > input[type="checkbox"]')
            || target.parentElement?.querySelector(':scope > input[type="radio"], :scope > input[type="checkbox"]');
          if (input && (input.checked || input.getAttribute('aria-checked') === 'true')) return true;
          // Some TikTok radios are styled divs with a --checked class rather
          // than a native input; check the label's own ancestry for that too.
          const styledRadio = target.closest('label, div')?.querySelector('[class*="--checked"], [aria-checked="true"]');
          if (styledRadio && isVisible(styledRadio)) return true;
        }

        // 2. Date/time picker fields only render once schedule mode is on
        // (e.g. a date input, or a visible "เลือกวันที่"/"เลือกเวลา" picker
        // control that doesn't exist in immediate-post mode).
        const pickerTexts = ['เลือกวันที่', 'เลือกเวลา', 'Select date', 'Select time'];
        const hasPicker = Array.from(document.querySelectorAll('input[type="date"], input[type="time"], div, span, button'))
          .some(el => {
            if (el.tagName === 'INPUT') return isVisible(el);
            const t = (el.innerText || el.textContent || '').trim();
            return pickerTexts.includes(t) && isVisible(el);
          });
        if (hasPicker) return true;

        return false;
      })()`,
      returnByValue: true,
    });
    if (verify?.result?.value) return setScheduleDateTime(send, schedule);
    await sleep(400);
  }
  return { success: false, reason: 'schedule_toggle_not_confirmed' };
}

// TikTok renders the schedule controls as TUX buttons rather than native
// date/time inputs (the visible values look like 2026-09-07 and 02:05). Set
// them only when the caller supplied values, then verify the exact value is
// visible. An empty value intentionally means "toggle only; user chooses".
// TikTok's schedule controls are readonly TUX inputs backed by custom pickers:
// date cells expose only the day number and time uses separate hour/minute lists.
async function setScheduleDateTime(send, { date = '', time = '' } = {}) {
  const requestedDate = String(date || '').trim();
  const rawTime = String(time || '').trim();
  const requestedTime = /^(\d{1,2}):(\d{2})$/.test(rawTime)
    ? rawTime.replace(/^(\d):/, '0$1:')
    : rawTime;
  if (!requestedDate && !requestedTime) return {success: true, changed: false};

  const sendEval = expression => send('Runtime.evaluate', {expression, returnByValue: true});
  const openInput = async (pattern, error) => {
    const opened = await sendEval(`(() => {
      const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
      const inputs = Array.from(document.querySelectorAll('input.TUXTextInputCore-input, input[type="date"], input[type="time"]'))
        .filter(el => visible(el) && ${pattern}.test(String(el.value || '').trim()));
      if (inputs.length !== 1) return {success: false, count: inputs.length};
      const current = String(inputs[0].value || '').trim();
      inputs[0].click();
      return {success: true, current};
    })()`);
    if (!opened?.result?.value?.success) throw new Error(error);
    return opened.result.value.current;
  };

  try {
    if (requestedDate) {
      const target = /^(\d{4})-(\d{2})-(\d{2})$/.exec(requestedDate);
      if (!target) throw new Error('รูปแบบวันที่ต้องเป็น YYYY-MM-DD');
      const current = await openInput('/^\\d{4}-\\d{2}-\\d{2}$/', 'เปิดตัวเลือกวันที่ไม่สำเร็จ');
      const currentMatch = /^(\d{4})-(\d{2})-\d{2}$/.exec(current);
      if (currentMatch) {
        const from = Number(currentMatch[1]) * 12 + Number(currentMatch[2]);
        const to = Number(target[1]) * 12 + Number(target[2]);
        const delta = Math.max(-24, Math.min(24, to - from));
        for (let i = 0; i < Math.abs(delta); i++) {
          const moved = await sendEval(`(() => {
            const arrows = document.querySelectorAll('[class*="calendar-wrapper"] .month-header-wrapper .arrow');
            const arrow = arrows[${delta >= 0 ? 1 : 0}];
            if (!arrow) return false; arrow.click(); return true;
          })()`);
          if (!moved?.result?.value) throw new Error('เลื่อนไปเดือนที่ต้องการไม่สำเร็จ');
          await sleep(120);
        }
      }
      const day = String(Number(target[3]));
      const picked = await sendEval(`(() => {
        const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const days = Array.from(document.querySelectorAll('[class*="calendar-wrapper"] span.day.valid'))
          .filter(el => visible(el) && el.textContent.trim() === ${JSON.stringify(day)});
        if (!days.length) return false; days[0].click(); return true;
      })()`);
      if (!picked?.result?.value) throw new Error('เลือกวันที่ที่ต้องการไม่สำเร็จ');
      await sleep(250);
    }

    if (requestedTime) {
      if (!/^\d{2}:\d{2}$/.test(requestedTime)) throw new Error('รูปแบบเวลาต้องเป็น HH:mm');
      await openInput('/^\\d{1,2}:\\d{2}$/', 'เปิดตัวเลือกเวลาไม่สำเร็จ');
      const [hour, minute] = requestedTime.split(':');
      const pickedHour = await sendEval(`(() => {
        const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const values = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text.tiktok-timepicker-left'))
          .filter(el => visible(el) && el.textContent.trim() === ${JSON.stringify(hour)});
        if (!values.length) return false; values[0].click(); return true;
      })()`);
      if (!pickedHour?.result?.value) throw new Error('เลือกชั่วโมงที่ต้องการไม่สำเร็จ');
      await sleep(180);
      const pickedMinute = await sendEval(`(() => {
        const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
        const values = Array.from(document.querySelectorAll('span.tiktok-timepicker-option-text.tiktok-timepicker-right'))
          .filter(el => visible(el) && el.textContent.trim() === ${JSON.stringify(minute)});
        if (!values.length) return false; values[0].click(); return true;
      })()`);
      if (!pickedMinute?.result?.value) throw new Error('เลือกนาทีที่ต้องการไม่สำเร็จ');
      await sleep(250);
    }
  } catch (err) {
    return {success: false, reason: err.message};
  }

  const values = await sendEval(`(() => {
    const visible = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    return Array.from(document.querySelectorAll('input.TUXTextInputCore-input, input[type="date"], input[type="time"]'))
      .filter(visible).map(el => String(el.value || '').trim());
  })()`);
  const shown = values?.result?.value || [];
  const success = (!requestedDate || shown.includes(requestedDate)) && (!requestedTime || shown.includes(requestedTime));
  return success
    ? {success: true, changed: true}
    : {success: false, changed: true, reason: 'schedule_value_not_confirmed'};
}

async function setScheduleDateTimeLegacy(send, { date = '', time = '' } = {}) {
  const requested = {date: String(date || '').trim(), time: String(time || '').trim()};
  if (!requested.date && !requested.time) return {success:true, changed:false};
  const selectValue = async (value, pattern, error) => {
    const direct = await send('Runtime.evaluate', {expression:`(() => {
      const visible = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})); };
      return Array.from(document.querySelectorAll('button,[role="button"],input,[role="option"],[role="gridcell"]')).some(el => visible(el) && String(el.value || el.innerText || el.textContent || '').trim() === ${JSON.stringify(value)});
    })()`, returnByValue:true});
    if (direct?.result?.value) return true;
    const opened = await send('Runtime.evaluate', {expression:`(() => {
      const visible = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})); };
      const controls = Array.from(document.querySelectorAll('button,[role="button"],input')).filter(el => visible(el) && ${pattern}.test(String(el.value || el.innerText || el.textContent || '').trim()));
      if (controls.length !== 1) return false; controls[0].click(); return true;
    })()`, returnByValue:true});
    if (!opened?.result?.value) throw new Error(error);
    await sleep(500);
    const picked = await send('Runtime.evaluate', {expression:`(() => {
      const visible = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})); };
      const matches = Array.from(document.querySelectorAll('button,[role="option"],[role="gridcell"],div,span')).filter(el => visible(el) && (el.innerText || el.textContent || '').trim() === ${JSON.stringify(value)});
      if (matches.length !== 1) return false; matches[0].click(); return true;
    })()`, returnByValue:true});
    if (!picked?.result?.value) throw new Error(error);
    return true;
  };
  try {
    if (requested.date) await selectValue(requested.date, `/^\\d{4}-\\d{2}-\\d{2}$/`, 'เลือกวันที่ที่ต้องการไม่สำเร็จ');
    if (requested.time) await selectValue(requested.time, `/^\\d{1,2}:\\d{2}$/`, 'เลือกเวลาที่ต้องการไม่สำเร็จ');
  } catch (err) {
    return {success:false, reason:err.message};
  }
  const verify = await send('Runtime.evaluate', {expression:`(() => {
    const visible = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0 && (!el.checkVisibility || el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})); };
    const has = value => Array.from(document.querySelectorAll('button,[role="button"],input')).some(el => visible(el) && String(el.value || el.innerText || el.textContent || '').trim() === value);
    return {date: ${JSON.stringify(requested.date)} ? has(${JSON.stringify(requested.date)}) : true, time: ${JSON.stringify(requested.time)} ? has(${JSON.stringify(requested.time)}) : true};
  })()`, returnByValue:true});
  const values = verify?.result?.value;
  return values?.date && values?.time ? {success:true, changed:true} : {success:false, reason:'schedule_value_not_confirmed'};
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

// After clicking Post/Schedule, polls for evidence the click actually did
// something -- TikTok never confirms via a dedicated success signal we can
// rely on, so this looks for any of: (a) the URL navigating away from the
// upload page, (b) the compose form / caption editor disappearing, (c) a
// validation-error toast/banner TikTok shows for a REJECTED submit (caption
// too short, cover required, category missing, etc). (a) and (b) both mean
// "the click was accepted and TikTok moved on" -- we don't need to
// distinguish "posted immediately" from "scheduled" here, the caller already
// knows which one it asked for. (c) is reported back verbatim so the user
// sees TikTok's own reason. Bounded by timeoutMs; if neither success nor
// failure evidence shows up in time, this returns 'timeout' rather than ever
// assuming success -- an unconfirmed click must not be reported as a post.
async function waitForPostConfirmation(send, tabId, timeoutMs = 20_000) {
  const start = Date.now();
  let consecutiveEditorGone = 0;
  while (Date.now() - start < timeoutMs) {
    let check;
    try {
      check = await send('Runtime.evaluate', {
      expression: `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (typeof el.checkVisibility === 'function') {
            return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
          }
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };

        // 1. TikTok's own validation-error toast/banner for a rejected submit.
        const errorNodes = Array.from(document.querySelectorAll(
          '[class*="toast"], [class*="Toast"], [class*="notice"], [class*="Notice"], [class*="error"], [class*="Error"], [role="alert"]'
        )).filter(isVisible);
        for (const el of errorNodes) {
          const t = (el.innerText || el.textContent || '').trim();
          if (!t) continue;
          // Only treat it as a rejection if it actually reads like one --
          // avoid false-positives from unrelated visible elements that
          // merely have "error" somewhere in a class name.
          if (/แคปชัน|คำอธิบาย|หน้าปก|cover|caption|หมวดหมู่|category|ล้มเหลว|ไม่สำเร็จ|failed|required|กรุณา(กรอก|เลือก)/i.test(t)) {
            return { done: true, failed: true, message: t.slice(0, 300) };
          }
        }

        // 2. Compose form gone (caption editor / cover editor no longer present).
        const stillEditing = document.querySelector('[contenteditable="true"]');
        if (!stillEditing) {
          return { done: true, failed: false, reason: 'editor-gone' };
        }

        return { done: false };
      })()`,
        returnByValue: true,
      });
    } catch (e) {
      // Runtime.evaluate can reject outright if the page navigated away
      // between our poll and the CDP round-trip (execution context
      // destroyed) -- that failure mode IS the success signal (URL moved
      // on), not an error to swallow into "still pending".
      return { confirmed: true, reason: 'navigation-during-eval' };
    }

    const val = check?.result?.value;
    if (val?.done) {
      if (val.failed) {
        return { confirmed: false, message: val.message };
      }
      // "editor-gone" alone can be a one-frame flicker mid-re-render rather
      // than a real navigation away -- require it to hold across two
      // consecutive polls (~700ms apart) before trusting it, so a transient
      // DOM swap right after the click doesn't get reported as success.
      consecutiveEditorGone += 1;
      if (consecutiveEditorGone >= 2) {
        return { confirmed: true, reason: val.reason };
      }
    } else {
      consecutiveEditorGone = 0;
    }

    // URL navigating away from the upload page is also conclusive success
    // evidence, and cheaper to check without round-tripping into the page.
    try {
      const target = await chrome.tabs.get(tabId);
      if (target?.url && !target.url.includes('/tiktokstudio/upload')) {
        return { confirmed: true, reason: 'navigated-away' };
      }
    } catch (e) {
      // Tab gone entirely (closed / navigated so hard chrome.tabs.get races) --
      // treat as navigated away rather than erroring the whole flow.
      return { confirmed: true, reason: 'tab-gone' };
    }

    await sleep(700);
  }
  return { confirmed: false, timedOut: true };
}

// UNVERIFIED (plan §3): selector is the plan's best-guess placeholder
// (`.btn-post:not(.disabled)`). Only runs when the user has explicitly
// opted into auto-click via the popup checkbox -- default is to stop
// right before this and let the user press Post themselves.
async function clickPostButton(send, tabId) {
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

  // The click landed on an element -- now confirm TikTok actually acted on
  // it. TikTok's SPA can also throw up a native "leave site? changes not
  // saved" navigation guard right after a genuinely-successful click, before
  // routing away finishes; dismiss that first so it doesn't get mistaken for
  // "still on the compose form" by waitForPostConfirmation.
  await dismissLeaveConfirmDialogIfPresent(send, 4000);

  const confirmation = await waitForPostConfirmation(send, tabId, 20_000);

  if (!confirmation.confirmed) {
    if (confirmation.message) {
      throw new Error('TikTok ปฏิเสธการโพสต์: ' + confirmation.message);
    }
    throw new Error('post_not_confirmed: กดปุ่มโพสต์แล้วแต่ไม่พบสัญญาณว่าสำเร็จหรือไม่สำเร็จภายในเวลาที่กำหนด กรุณาตรวจสอบหน้า TikTok ด้วยตาก่อนลองใหม่');
  }

  // A dialog can still appear after confirmation resolves via URL/tab checks
  // (which don't wait on it) -- best-effort dismiss once more so it doesn't
  // sit there blocking the tab for the next action.
  await dismissLeaveConfirmDialogIfPresent(send, 2000);
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

async function runAttachProductOnly({ productId, cartName = '' }) {
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');

    const attachResult = await attachProductLink(send, productId, cartName);

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
async function runScheduleModeOnly({ date = '', time = '' } = {}) {
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');
    const switched = await switchToScheduleMode(send, {date, time});
    if (!switched.success) {
      if (switched.reason === 'schedule_toggle_not_confirmed') {
        return { success: false, reason: 'schedule_toggle_not_confirmed: กดตัวเลือก "กำหนดเวลา"/"ตั้งเวลา" แล้ว แต่ไม่พบหลักฐานว่าสลับโหมดสำเร็จ (ไม่พบ radio ที่ checked หรือช่องเลือกวันที่/เวลา) หากไม่แก้ไข โพสต์อาจออกทันทีแทนที่จะตั้งเวลา' };
      }
      return { success: false, reason: 'หาตัวเลือก "กำหนดเวลา"/"ตั้งเวลา" บนหน้าเว็บไม่พบ' };
    }
    return switched;
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
    // clickPostButton now throws unless it finds real evidence the post
    // went through (URL navigated away, compose form gone, or tab closed) --
    // reaching this line means it's actually confirmed, so `posted:true` is
    // no longer a guess.
    await clickPostButton(send, tab.id);
    return { success: true, clicked: true, posted: true };
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

    await typeCaption(send, caption, hashtags);
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
    const product = await runAttachProductOnly({productId, cartName: message.cartName || ''});
    if (!product.success) throw new Error(product.reason);
    completed.push('product');
    step = 'cover';
    await runUploadCoverOnly();
    completed.push('cover');
    if (message.scheduleMode) {
      step = 'schedule';
      const schedule = await runScheduleModeOnly({date: message.scheduleDate, time: message.scheduleTime});
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
  'schedule-mode-only': message => runScheduleModeOnly(message),
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
