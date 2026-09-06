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
// This file only runs when the user clicks this extension's popup button,
// on a tab they already have open and already logged into. Nothing here
// schedules itself, polls in the background, or runs without that click.
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
  if (!text) return;
  const { result } = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector('[contenteditable="true"]');
      if (!el) return false;
      el.focus();
      try {
        const sel = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(el);
        sel.removeAllRanges();
        sel.addRange(range);
      } catch (e) {}
      // Select all contents and delete so TikTok's auto-inserted video filename is wiped out
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      return true;
    })()`,
    returnByValue: true,
  });
  if (!result || !result.value) {
    throw new Error('พบช่องแคปชันแล้วแต่ focus ไม่สำเร็จ -- โครงสร้างหน้าอาจเปลี่ยนไป');
  }
  await sleep(250);

  // 1. Try inserting the whole text via document.execCommand('insertText') which natively handles newlines in Blink
  const execResult = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector('[contenteditable="true"]');
      if (!el) return { success: false };
      el.focus();
      const ok = document.execCommand('insertText', false, ${JSON.stringify(text)});
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      const hasContent = (el.innerText || el.textContent || '').trim().length > 0;
      return { success: Boolean(ok && hasContent) };
    })()`,
    returnByValue: true,
  });

  // 2. Fallback: line-by-line typing with clean Enter (WITHOUT text: '\r' which causes cursor carriage return)
  if (!execResult?.result?.value?.success) {
    const lines = text.split('\n');
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].length > 0) {
        await send('Input.insertText', { text: lines[i] });
        await sleep(50);
      }
      if (i < lines.length - 1) {
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
        await sleep(50);
      }
    }
  }

  // Scroll containers to top so user sees the caption from line 1 (do not collapse selection to start!)
  await sleep(150);
  await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector('[contenteditable="true"]');
      if (!el) return;
      let p = el;
      while (p && p !== document.body) {
        p.scrollTop = 0;
        p = p.parentElement;
      }
    })()`,
  });
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

        // 2. Check for "Uploading..." in preview
        if (allText.includes('Uploading...')) {
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
  const isActive = async () => {
    const r = await send('Runtime.evaluate', {
      expression: `(() => {
        const inputs = Array.from(document.querySelectorAll('input'));
        const searchInput = inputs.find(i => {
          const p = (i.placeholder || '').toLowerCase();
          return p.includes('ค้นหา') || p.includes('search');
        });
        return Boolean(searchInput && (searchInput.offsetWidth > 0 || searchInput.offsetHeight > 0 || searchInput.getClientRects().length > 0));
      })()`,
      returnByValue: true,
    });
    return Boolean(r?.result?.value);
  };

  if (await isActive()) return true;

  for (let attempt = 0; attempt < 5; attempt++) {
    const found = await send('Runtime.evaluate', {
      expression: `(() => {
        const allElements = Array.from(document.querySelectorAll('[role="tab"], button, div, span, p, a'));
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
  const switched = await switchToShowcaseTab(send);
  if (!switched) {
    console.warn('สลับแท็บนำเสนอสินค้าอาจไม่สมบูรณ์ แต่จะลองค้นหาต่อ');
  }

  await sleep(1200);

  // Step 4: Type Product ID into search box and trigger search
  await send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.querySelector('[role="dialog"]') || document;
      const inputs = Array.from(root.querySelectorAll('input'));
      const search = inputs.find(i => {
        const p = (i.placeholder || '').toLowerCase();
        return p.includes('ค้นหา') || p.includes('search');
      }) || inputs[inputs.length - 1];
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

        const p = search.parentElement;
        if (p) {
          const icon = p.querySelector('svg, button, span');
          if (icon && icon !== search) {
            icon.click();
          }
        }
        return true;
      }
      return false;
    })()`,
    returnByValue: true,
  });

  // Also send CDP insertText + Enter key to search input
  try {
    await send('Input.insertText', { text: String(productId) });
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

  // Step 5: Click first radio button / row
  const step5 = await send('Runtime.evaluate', {
    expression: `(() => {
      const root = document.querySelector('[role="dialog"]') || document;
      const rows = Array.from(root.querySelectorAll('table tr, [role="row"], tbody tr'));
      for (const row of rows) {
        if (row.querySelector('th')) continue;
        const text = row.innerText || row.textContent || '';
        if (text.includes(${JSON.stringify(String(productId).slice(-6))}) || text.includes(${JSON.stringify(String(productId))})) {
          const radio = row.querySelector('input[type="radio"], [role="radio"]') || row.querySelector('td') || row;
          radio.scrollIntoView({ behavior: 'instant', block: 'center' });
          radio.click();
          return { success: true, matchText: true };
        }
      }

      const radios = Array.from(root.querySelectorAll('input[type="radio"], [role="radio"]'));
      const visibleRadios = radios.filter(r => r.offsetWidth > 0 || r.offsetHeight > 0 || r.getClientRects().length > 0);
      if (visibleRadios.length > 0) {
        visibleRadios[0].click();
        return { success: true, count: visibleRadios.length };
      }
      for (const row of rows) {
        if (row.querySelector('th')) continue;
        const input = row.querySelector('input') || row.querySelector('span, svg, td');
        if (input) {
          input.click();
          return { success: true, rowClicked: true };
        }
      }
      return { success: false };
    })()`,
    returnByValue: true,
  });

  if (!step5?.result?.value?.success) {
    return { success: false, reason: 'ไม่พบสินค้าตาม ID ในตู้โชว์' };
  }

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

  await sleep(1000);
  return {
    success: !!step7?.result?.value,
    reason: step7?.result?.value ? 'สำเร็จ' : 'กดปุ่มเพิ่มในหน้าสุดท้ายไม่สำเร็จ',
  };
}

// Switches upload form to "กำหนดเวลาโพสต์" / "ตั้งเวลา" (Schedule) option
async function switchToScheduleMode(send) {
  await send('Runtime.evaluate', {
    expression: `(() => {
      const elements = Array.from(document.querySelectorAll('label, input[type="radio"], span, div'));
      const scheduleOption = elements.find(el => {
        const t = (el.innerText || el.textContent || '').trim();
        return t === 'ตั้งเวลา' || t === 'กำหนดเวลาโพสต์' || t === 'กำหนดเวลา' || t === 'Schedule' || t.includes('ตั้งเวลา') || t.includes('กำหนดเวลา');
      });
      if (scheduleOption) {
        const input = scheduleOption.querySelector('input') || scheduleOption;
        input.click();
        return true;
      }
      return false;
    })()`,
    returnByValue: true,
  });
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
  await waitForUploadComplete(send, 60_000);

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

async function runAttachProductOnly({ productId, scheduleMode }) {
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');

    const attachResult = await attachProductLink(send, productId);
    if (scheduleMode) {
      try {
        await switchToScheduleMode(send);
      } catch (e) {}
    }

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

async function runAutopost({ autoClickPost, attachProduct, productId, caption, hashtags, scheduleMode }) {
  const job = await fetchPendingJob().catch(() => ({}));
  const tab = await findUploadTab();
  const send = cdp(tab.id);

  await chrome.debugger.attach({ tabId: tab.id }, '1.3');
  try {
    await send('DOM.enable');
    await send('Runtime.enable');

    if (job.video_path) {
      const fileNodeId = await findFileInputNodeId(send);
      await setFileInput(send, fileNodeId, job.video_path);
    }

    await waitForCaptionEditor(send);

    // Prefer explicit caption and hashtags from popup inputs if provided, else job
    const finalCaption = (caption !== undefined && caption !== null && caption.trim() !== '')
      ? caption.trim()
      : (job.caption || '');
    const finalHashtags = (hashtags !== undefined && hashtags !== null && hashtags.trim() !== '')
      ? hashtags.trim()
      : (job.hashtags || '');

    const captionParts = [];
    if (finalCaption) captionParts.push(finalCaption);
    if (finalHashtags) captionParts.push(finalHashtags);
    const fullCaption = captionParts.join('\n\n');

    if (fullCaption) {
      await typeCaption(send, fullCaption);
    }

    // Wait for video upload to finish before proceeding to link attachment and posting
    await waitForUploadComplete(send, PROCESSING_TIMEOUT_MS);

    // Attach product link if requested
    const targetProductId = productId || job.tiktok_product_id || job.product_id;
    let attachResult = null;
    if (attachProduct && targetProductId) {
      try {
        attachResult = await attachProductLink(send, targetProductId);
      } catch (err) {
        console.warn('Product link attachment note:', err);
      }
    }

    // Switch to schedule post mode if requested
    if (scheduleMode) {
      try {
        await switchToScheduleMode(send);
      } catch (err) {
        console.warn('Schedule mode note:', err);
      }
    }

    let leaveDialogDismissed = false;
    if (autoClickPost) {
      await clickPostButton(send);
      leaveDialogDismissed = await dismissLeaveConfirmDialogIfPresent(send).catch(() => false);
    }

    await clearPendingJob();
    return {
      success: true,
      autoClickedPost: !!autoClickPost,
      attachedProduct: !!attachResult?.success,
      productReason: attachResult?.reason,
      scheduleMode: !!scheduleMode,
      leaveDialogDismissed,
    };
  } finally {
    // Always detach, even on failure
    try {
      await chrome.debugger.detach({ tabId: tab.id });
    } catch (e) {
      // Already detached -- fine.
    }
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.action === 'type-caption-only') {
    runTypeCaptionOnly({
      caption: message.caption || '',
      hashtags: message.hashtags || '',
    })
      .then((result) => sendResponse(result))
      .catch((err) => sendResponse({ success: false, error: err.message || String(err) }));
    return true;
  }
  if (message?.action === 'attach-product-only') {
    runAttachProductOnly({
      productId: message.productId || null,
      scheduleMode: !!message.scheduleMode,
    })
      .then((result) => sendResponse(result))
      .catch((err) => sendResponse({ success: false, error: err.message || String(err) }));
    return true;
  }
  if (message?.action === 'run-autopost') {
    runAutopost({
      autoClickPost: !!message.autoClickPost,
      attachProduct: !!message.attachProduct,
      productId: message.productId || null,
      caption: message.caption || '',
      hashtags: message.hashtags || '',
      scheduleMode: !!message.scheduleMode,
    })
      .then((result) => sendResponse(result))
      .catch((err) => sendResponse({ success: false, error: err.message || String(err) }));
    return true; // keep the message channel open for the async response
  }
  return false;
});
