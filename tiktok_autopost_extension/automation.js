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
      const areas = Array.from(document.querySelectorAll('label.ImageUpload__uploadArea, input[type="file"], [class*="cover-modal"], [class*="CoverModal"]'));
      return areas.some(visible);
    })()`);

    if (!isModalOpen) {
      // Find "แก้ไขหน้าปก" (supports div.edit-container, button, span)
      const clickedEdit = await evaluate(send, `(() => {
        const isVisible = (el) => {
          if (!el) return false;
          const rect = el.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        };
        const exact = Array.from(document.querySelectorAll('div.edit-container')).find(isVisible);
        const targets = [exact, ...Array.from(document.querySelectorAll('[class*="edit-container"], [class*="cover-container"] div, button, div, span'))]
          .filter(Boolean)
          .filter(isVisible);
        const btn = targets.find(el => {
          const t = (el.innerText || el.textContent || '').trim();
          return t === 'แก้ไขหน้าปก' || t === 'แก้ไขปก' || t === 'Edit cover' || t.includes('แก้ไขหน้าปก');
        });
        if (btn) {
          btn.scrollIntoView({ behavior: 'instant', block: 'center' });
          btn.click();
          return true;
        }
        return false;
      })()`);

      if (!clickedEdit) {
        throw new Error('หาปุ่ม "แก้ไขหน้าปก" บนหน้า TikTok ไม่พบ');
      }

      // Wait for cover modal to open
      await wait(send, `(() => {
        const areas = Array.from(document.querySelectorAll('label.ImageUpload__uploadArea, [class*="uploadArea"]'));
        return areas.some(area => {
          if (area.checkVisibility && !area.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
          const r = area.getBoundingClientRect();
          return r.width > 0 && r.height > 0 && getComputedStyle(area).visibility !== 'hidden';
        });
      })()`, 'รอหน้าต่างแก้ไขปกเปิดไม่ทัน', 15000);
    }

    await new Promise(r => setTimeout(r, 1000));

    // 2. Find the cover image file input -- DO NOT click the upload button or label!
    // Clicking the label causes the native OS file picker to open!
    // Instead, find the input[type="file"] and set files directly via CDP DOM.setFileInputFiles!
    const fileInputQuery = `(() => {
      // 1. Inside ImageUpload uploadArea
      const dialogCandidates = Array.from(document.querySelectorAll('[role="dialog"], [aria-modal="true"], [class*="modal"], [class*="Modal"]'))
        .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
      const scope = dialogCandidates.at(-1) || document;
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
      return allInputs[0] || null;
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

    const {result, exceptionDetails} = await send('Runtime.evaluate', {expression:fileInputQuery});
    if (exceptionDetails || !result?.objectId) throw new Error('ช่องอัปโหลดปกไม่พร้อม');
    try {
      const {nodeId} = await send('DOM.requestNode', {objectId:result.objectId});
      await send('DOM.setFileInputFiles', {nodeId, files:[coverPath]});
    } finally {
      await send('Runtime.releaseObject', {objectId:result.objectId}).catch(() => {});
    }

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
      const buttons = Array.from(document.querySelectorAll('button, div[role="button"]')).filter(isVisible);
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

    await new Promise(r => setTimeout(r, 1500));
    return {success:true};
  }

  return {evaluate, wait, page, buttonQuery, clickButton, uploadCover};
})();
