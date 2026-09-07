// Small, testable CDP helpers. Page queries never write React-owned DOM.
globalThis.OmniAutomation = (() => {
  const visibleSource = `(el) => {
    if (!el) return false;
    if (el.checkVisibility && !el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
  }`;
  const page = (body) => `(() => {
    const visible = ${visibleSource};
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"]')).filter(visible);
    const dialog = dialogs.at(-1);
    const label = el => (el.innerText || el.textContent || '').trim();
    const enabled = el => !el.disabled && el.getAttribute('aria-disabled') !== 'true';
    ${body}
  })()`;

  async function evaluate(send, expression) {
    const response = await send('Runtime.evaluate', {expression, returnByValue:true});
    if (response.exceptionDetails) throw new Error(response.exceptionDetails.text || 'อ่านหน้า TikTok ไม่สำเร็จ');
    return response.result?.value;
  }

  async function wait(send, expression, message, timeout = 15000) {
    const end = Date.now() + timeout;
    do {
      const value = await evaluate(send, expression);
      if (value) return value;
      await new Promise(resolve => setTimeout(resolve, 350));
    } while (Date.now() < end);
    throw new Error(message);
  }

  function buttonQuery(names, inDialog = true, click = false) {
    return page(`
      const root = ${inDialog ? 'dialog' : 'document'};
      if (!root) return false;
      const matches = Array.from(root.querySelectorAll('button, [role="button"]')).filter(el =>
        visible(el) && enabled(el) && ${JSON.stringify(names)}.includes(label(el)) &&
        !el.closest('nav, aside, header'));
      if (matches.length !== 1) return false;
      ${click ? "matches[0].scrollIntoView({block:'center'}); matches[0].click();" : ''}
      return true;
    `);
  }

  async function clickButton(send, names, inDialog = true) {
    await wait(send, buttonQuery(names, inDialog), `ไม่พบปุ่ม ${names[0]} ที่พร้อมใช้งาน`);
    if (!await evaluate(send, buttonQuery(names, inDialog, true))) {
      throw new Error(`หน้าเปลี่ยนก่อนกด ${names[0]} กรุณาลองขั้นนี้ใหม่`);
    }
  }

  async function findCoverInputNodeId(send) {
    const {root} = await send('DOM.getDocument', {depth:-1, pierce:true});
    if (!root?.nodeId) throw new Error('อ่านโครงสร้างหน้า TikTok เพื่อหาช่องอัปโหลดปกไม่สำเร็จ');
    const selectors = [
      'label.ImageUpload__uploadArea input[type="file"]',
      'input[type="file"][accept*="image"]',
      'input[type="file"]',
    ];
    for (const selector of selectors) {
      const {nodeIds} = await send('DOM.querySelectorAll', {nodeId:root.nodeId, selector});
      if (nodeIds?.length) return nodeIds.at(-1);
    }
    throw new Error('ไม่พบ node ของช่องอัปโหลดปกใน Cover Studio');
  }

  async function uploadCover(send, coverPath) {
    if (!coverPath) throw new Error('คลิปนี้ยังไม่มีปกที่บันทึกในโปรแกรม');

    // 1. Check if cover editor modal is already open
    const isModalOpen = await evaluate(send, `(() => {
      const visible = el => {
        if (!el) return false;
        if (el.checkVisibility && !el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
      };
      const areas = Array.from(document.querySelectorAll('label.ImageUpload__uploadArea, input[type="file"], [class*="cover-modal"], [class*="CoverModal"], [class*="CoverEditor__root"], [class*="cover-editor-container"]'));
      return areas.some(visible);
    })()`);

    if (!isModalOpen) {
      // Find "แก้ไขหน้าปก" (the live TikTok DOM uses a plain div.edit-container).
      // Return the target's center so CDP can perform a real browser click if
      // React ignores the programmatic click below.
      const editTarget = await evaluate(send, `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          if (el.checkVisibility && !el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };
        const targets = Array.from(document.querySelectorAll('div.edit-container, [class*="edit-container"], [class*="cover-container"] div, button, [role="button"]'))
          .filter(isVisible)
          .map((el, index) => {
            const text = (el.innerText || el.textContent || '').trim();
            const exact = text === 'แก้ไขหน้าปก' || text === 'แก้ไขปก' || text === 'Edit cover';
            const partial = text.includes('แก้ไขหน้าปก');
            const rect = el.getBoundingClientRect();
            return {el, index, text, rect, score: exact ? 0 : (partial ? 1 : 2)};
          })
          .filter(item => item.score < 2)
          .sort((a, b) => a.score - b.score || a.text.length - b.text.length || a.index - b.index);
        const match = targets[0];
        if (match) {
          // Keep the exact edit-container when it is the handler target; only
          // climb to an interactive ancestor when TikTok rendered one.
          const btn = match.el.closest('button, [role="button"]') || match.el;
          btn.scrollIntoView({ behavior: 'instant', block: 'center' });
          const rect = btn.getBoundingClientRect();
          btn.click();
          return {x: rect.left + rect.width / 2, y: rect.top + rect.height / 2};
        }
        return null;
      })()`);

      if (!editTarget) {
        throw new Error('หาปุ่ม "แก้ไขหน้าปก" บนหน้า TikTok ไม่พบ');
      }

      // Wait briefly for the React state transition. If the DOM click was
      // swallowed by a delegated handler, retry once with a native CDP click
      // at the same coordinates. This does not touch the file input or open
      // the native file picker.
      let opened = false;
      try {
        await wait(send, `(() => {
          const areas = Array.from(document.querySelectorAll('label.ImageUpload__uploadArea, [class*="uploadArea"], [class*="CoverEditor__root"], [class*="cover-editor-container"]'));
          return areas.some(area => {
            if (area.checkVisibility && !area.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
            const r = area.getBoundingClientRect();
            return r.width > 0 && r.height > 0 && getComputedStyle(area).visibility !== 'hidden';
          });
        })()`, 'รอหน้าต่างแก้ไขปกเปิดไม่ทัน', 3000);
        opened = true;
      } catch {
        // Fall through to the native click retry below.
      }

      if (!opened) {
        try {
          await send('Input.dispatchMouseEvent', {type:'mouseMoved', x:editTarget.x, y:editTarget.y});
          await send('Input.dispatchMouseEvent', {type:'mousePressed', x:editTarget.x, y:editTarget.y, button:'left', clickCount:1});
          await send('Input.dispatchMouseEvent', {type:'mouseReleased', x:editTarget.x, y:editTarget.y, button:'left', clickCount:1});
        } catch {
          // The follow-up wait below reports the actionable error if CDP input
          // is unavailable or the page changed during the retry.
        }
        await wait(send, `(() => {
          const areas = Array.from(document.querySelectorAll('label.ImageUpload__uploadArea, [class*="uploadArea"], [class*="CoverEditor__root"], [class*="cover-editor-container"]'));
          return areas.some(area => {
            if (area.checkVisibility && !area.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
            const r = area.getBoundingClientRect();
            return r.width > 0 && r.height > 0 && getComputedStyle(area).visibility !== 'hidden';
          });
        })()`, 'รอหน้าต่างแก้ไขปกเปิดไม่ทัน', 12000);
      }
    }

    await new Promise(r => setTimeout(r, 1000));

    // 2. Find the cover image file input -- DO NOT click the upload button or label!
    // Clicking the label causes the native OS file picker to open!
    // Instead, find the input[type="file"] and set files directly via CDP DOM.setFileInputFiles!
    const fileInputQuery = `(() => {
      // 1. Inside ImageUpload uploadArea
      const dialogCandidates = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], [class*="modal"], [class*="Modal"], [class*="CoverEditor__root"], [class*="cover-editor-container"]'))
        .filter(el => {
          if (el.checkVisibility && !el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
          const r = el.getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        });
      const scope = dialogCandidates.find(el => String(el.className || '').includes('cover-editor-container')) || dialogCandidates.at(-1) || document;
      const uploadArea = scope.querySelector('label.ImageUpload__uploadArea, [class*="uploadArea"]')
        || document.querySelector('label.ImageUpload__uploadArea, [class*="uploadArea"]');
      if (uploadArea) {
        const forId = uploadArea.getAttribute('for');
        const input = (forId && document.getElementById(forId)) ||
          uploadArea.querySelector('input[type="file"]') ||
          uploadArea.parentElement?.querySelector('input[type="file"]');
        if (input) return input;
      }
      // 2. Any file input with accept image
      const allInputs = Array.from(scope.querySelectorAll('input[type="file"]'));
      const imgInput = allInputs.find(i => {
        const acc = (i.accept || '').toLowerCase();
        return acc.includes('image') || acc.includes('png') || acc.includes('jpg') || acc.includes('jpeg');
      });
      if (imgInput) return imgInput;
      // 3. Last file input on page
      if (allInputs.length > 1) return allInputs[allInputs.length - 1];
      if (allInputs[0]) return allInputs[0];
      // Some TikTok builds mount the input beside the editor root rather than
      // inside it. Keep the editor-scoped search first, then use the last
      // visible image input on the page as a controlled fallback.
      return Array.from(document.querySelectorAll('input[type="file"]')).reverse().find(input => {
        if (input.checkVisibility && !input.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
        const acc = (input.accept || '').toLowerCase();
        return acc.includes('image') || acc.includes('png') || acc.includes('jpg') || acc.includes('jpeg');
      }) || null;
    })()`;

    // TikTok sometimes creates the input only after the upload-area label is
    // activated. Prefer a direct input when present; otherwise click the
    // label once, then immediately take the input through CDP (no OS picker
    // interaction is required from the user).
    const hasInput = await evaluate(send, `Boolean(${fileInputQuery})`);
    if (!hasInput) {
      await evaluate(send, `(() => {
      const label = document.querySelector('label.ImageUpload__uploadArea, label[role="button"], [class*="uploadArea"]');
        if (!label) return false;
        label.click();
        return true;
      })()`);
    }
    await wait(send, `Boolean(${fileInputQuery})`, 'ไม่พบช่องอัปโหลดภาพปกในหน้าต่างแก้ไขปก');

    const nodeId = await findCoverInputNodeId(send);
    await send('DOM.setFileInputFiles', {nodeId, files:[coverPath]});

    // DOM.setFileInputFiles updates the browser's FileList, but it does not
    // reliably emit the React-facing events that TikTok uses to create the
    // preview. Notify the same hidden input explicitly without clicking the
    // label (which would open the native OS picker).
    const notified = await evaluate(send, `(() => {
      const input = ${fileInputQuery};
      if (!input || !input.files || input.files.length === 0) return false;
      input.dispatchEvent(new Event('input', {bubbles:true}));
      input.dispatchEvent(new Event('change', {bubbles:true}));
      return true;
    })()`);
    if (!notified) throw new Error('ส่งไฟล์ปกแล้ว แต่ TikTok ยังไม่รับไฟล์ในช่องอัปโหลด');

    // 3. Wait for image preview to render inside the modal
    await wait(send, `(() => {
      const input = ${fileInputQuery};
      if (!input || !input.files || input.files.length === 0) return false;
      const preview = Array.from(document.querySelectorAll('img, canvas')).some(el => {
        const rect = el.getBoundingClientRect();
        return rect.width > 50 && rect.height > 50 && (el.tagName === 'CANVAS' || (el.complete && el.naturalWidth > 0));
      });
      return preview;
    })()`, 'TikTok ยังไม่แสดงภาพตัวอย่างปกที่อัปโหลด', 15000);

    await new Promise(r => setTimeout(r, 1000));

    // 4. Click "บันทึก" / "ยืนยัน" / "Save" / "Confirm" button
    const saved = await evaluate(send, `(() => {
      const isVisible = (el) => {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
      };
      const roots = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], [class*="CoverEditor__root"], [class*="cover-editor-container"], [class*="cover-modal"], [class*="CoverModal"]'))
        .filter(isVisible);
      // TikTok renders the header (including Save) as a sibling of
      // CoverEditor__root under cover-editor-container, so prefer that
      // outer container when it exists.
      const root = roots.find(el => String(el.className || '').includes('cover-editor-container')) || roots.at(-1) || document;
      const buttons = Array.from(root.querySelectorAll('button, div[role="button"]')).filter(isVisible);
      const saveBtn = buttons.reverse().find(b => {
        if (b.disabled || b.getAttribute('aria-disabled') === 'true') return false;
        const t = (b.innerText || b.textContent || '').trim();
        return t === 'บันทึก' || t === 'ยืนยัน' || t === 'Save' || t === 'Confirm' || t === 'เสร็จสิ้น';
      });
      if (saveBtn) {
        saveBtn.click();
        return true;
      }
      return false;
    })()`);

    if (!saved) {
      throw new Error('ไม่พบปุ่ม "บันทึก" ในหน้าต่างแก้ไขปก');
    }

    await wait(send, `(() => {
      const visible = el => {
        if (!el) return false;
        if (el.checkVisibility && !el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
      };
      return !Array.from(document.querySelectorAll('[class*="CoverEditor__root"], [class*="cover-editor-container"], [class*="cover-modal"], [class*="CoverModal"]')).some(visible);
    })()`, 'บันทึกปกแล้ว แต่หน้าต่าง Cover Studio ยังไม่ปิด', 8000);
    return {success:true};
  }

  return {evaluate, wait, page, buttonQuery, clickButton, uploadCover};
})();
