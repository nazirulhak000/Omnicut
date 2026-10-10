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

  async function resolveCoverInputTarget(send, fileInputQuery) {
    // Keep the Runtime object returned by the same scoped query that found the
    // editor input. A global DOM snapshot can contain TikTok's video input and
    // a second hidden cover input; picking the last node made CDP set one
    // element while React listened to another.
    const response = await send('Runtime.evaluate', {
      expression: fileInputQuery,
      returnByValue: false,
    });
    if (response.exceptionDetails) {
      throw new Error(`ประเมินช่องอัปโหลดปกล้มเหลว: ${response.exceptionDetails.text || 'TikTok เปลี่ยนหน้า'}`);
    }
    if (response.result?.objectId) return {objectId: response.result.objectId};

    // Keep a DOM-node fallback for TikTok builds that do not expose a wrapper
    // object from Runtime.evaluate. It still uses the editor input selector
    // first, then reports the exact node used to the caller.
    return {nodeId: await findCoverInputNodeId(send)};
  }

  async function notifyCoverInput(send, target) {
    // Resolve the exact DOM node that received DOM.setFileInputFiles. A fresh
    // document query can return a different hidden input when TikTok rerenders
    // the editor, which made the old post-upload FileList check report zero.
    let objectId = target?.objectId;
    if (!objectId && target?.nodeId) {
      const resolved = await send('DOM.resolveNode', {nodeId: target.nodeId});
      objectId = resolved?.object?.objectId;
    }
    if (!objectId) throw new Error('ไม่สามารถเชื่อมต่อช่องอัปโหลดปกหลังส่งไฟล์');
    try {
      const response = await send('Runtime.callFunctionOn', {
        objectId,
        functionDeclaration: `function() {
          if (!this.files || this.files.length === 0) return {fileCount: 0};
          this.dispatchEvent(new Event('input', {bubbles:true}));
          this.dispatchEvent(new Event('change', {bubbles:true}));
          return {fileCount: this.files.length, fileName: this.files[0]?.name || ''};
        }`,
        returnByValue: true,
      });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.text || 'TikTok ปฏิเสธไฟล์ปก');
      return Number(response.result?.value?.fileCount || 0) > 0;
    } finally {
      await send('Runtime.releaseObject', {objectId}).catch(() => {});
    }
  }

  // Waits for TikTok's own upload-status badge to say the video is fully
  // received (e.g. "อัปโหลดแล้ว (34.12MB)" with an "info-status success"
  // class and a CheckCircleFill icon under [data-e2e="upload_status_container"]
  // -- confirmed against a real logged-in session, 2026-09).
  //
  // Step 1 (runUploadFileOnly, background.js) only confirms the file was
  // handed to the page's <input type="file"> -- it deliberately does not
  // wait for TikTok to actually finish receiving/processing it, since
  // holding the debugger attached that long is what caused a tab-crash
  // investigated elsewhere in this codebase. That means step 1 turning
  // green (and therefore the "ทำต่อหลังอัปโหลด" shortcut becoming
  // clickable) is NOT the same moment as the upload reaching 100% -- a
  // real gap of tens of seconds on a normal-sized clip. Acting on the page
  // during that gap is what caused two different real failures: Cover
  // Studio's edit surface rendering its shell before the actual image
  // <input> mounts inside it, and TikTok's own product-search endpoint
  // refusing to return results ("การตรวจสอบจะเริ่มได้หลังจากอัปโหลดไฟล์
  // แล้วเท่านั้น") when queried too early.
  //
  // Rather than changing what step 1 itself waits for (which would still
  // require holding the debugger attached through that same window), each
  // caller that actually needs the upload finished waits for it here, with
  // its own short bounded poll -- the same low-risk pattern already used
  // for "did the modal open" below, not the continuous-attach pattern that
  // caused the crash.
  async function waitForUploadStatusBadge(send) {
    await wait(send, `(() => {
      const status = document.querySelector('[data-e2e="upload_status_container"] [class*="info-status"]');
      if (!status) return false;
      const text = status.innerText || status.textContent || '';
      return status.className.includes('success') && (text.includes('อัปโหลดแล้ว') || text.toLowerCase().includes('uploaded'));
    })()`, 'TikTok ยังอัปโหลดวิดีโอไม่เสร็จ -- รอสักครู่แล้วลองใหม่', 90000);
  }

  async function uploadCover(send, coverPath) {
    if (!coverPath) throw new Error('คลิปนี้ยังไม่มีปกที่บันทึกในโปรแกรม');

    // 0. See waitForUploadStatusBadge's own comment -- Cover Studio's edit
    // surface can render before the actual image <input> mounts inside it
    // if opened while the upload is still in flight.
    await waitForUploadStatusBadge(send);

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

    // DOM.setFileInputFiles updates the browser's FileList, but it does not
    // reliably emit the React-facing events that TikTok uses to create the
    // preview. Use the exact input object returned by the scoped query so the
    // following events reach the same React handler. If TikTok replaced that
    // hidden input during the first assignment, resolve the scoped input once
    // more and retry against the replacement.
    let target = await resolveCoverInputTarget(send, fileInputQuery);
    let notified = false;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const setParams = {files:[coverPath]};
      if (target.objectId) setParams.objectId = target.objectId;
      else setParams.nodeId = target.nodeId;
      await send('DOM.setFileInputFiles', setParams);
      notified = await notifyCoverInput(send, target);
      if (notified) break;
      if (attempt === 0) target = await resolveCoverInputTarget(send, fileInputQuery);
    }
    if (!notified) throw new Error('ส่งไฟล์ปกแล้ว แต่ TikTok ยังไม่รับไฟล์ในช่องอัปโหลด');

    // 3. Wait for image preview to render inside the modal
    await wait(send, `(() => {
      const preview = Array.from(document.querySelectorAll('img, canvas')).some(el => {
        const rect = el.getBoundingClientRect();
        return rect.width > 50 && rect.height > 50 && (el.tagName === 'CANVAS' || (el.complete && el.naturalWidth > 0));
      });
      return preview;
    })()`, 'TikTok ยังไม่แสดงภาพตัวอย่างปกที่อัปโหลด', 15000);

    await new Promise(r => setTimeout(r, 1000));

    // 4. Click "บันทึก" / "ยืนยัน" / "Save" / "Confirm" with retry.
    // TikTok sometimes renders the button before its handler is ready. One
    // click followed by a modal wait was flaky, so each retry both verifies
    // the modal closed and falls back to a native CDP click at the last point.
    const saveButtonExpression = `(() => {
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
      if (!saveBtn) return {success: false};
      const rect = saveBtn.getBoundingClientRect();
      saveBtn.scrollIntoView({behavior:'instant', block:'center'});
      saveBtn.click();
      return {success: true, x: rect.left + rect.width / 2, y: rect.top + rect.height / 2};
    })()`;

    const coverModalClosedExpression = `(() => {
      const visible = el => {
        if (!el) return false;
        if (el.checkVisibility && !el.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
      };
      return !Array.from(document.querySelectorAll('[class*="CoverEditor__root"], [class*="cover-editor-container"], [class*="cover-modal"], [class*="CoverModal"]')).some(visible);
    })()`;

    let lastPoint = null;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      await wait(send, `(() => {
        const isVisible = el => {
          if (!el) return false;
          const r = el.getBoundingClientRect();
          return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
        };
        return Array.from(document.querySelectorAll('[role="dialog"] button, [aria-modal="true"] button, button, div[role="button"]'))
          .some(b => isVisible(b) && !b.disabled && ['บันทึก','ยืนยัน','Save','Confirm','เสร็จสิ้น'].includes((b.innerText || b.textContent || '').trim()));
      })()`, 'รอปุ่มบันทึกปกพร้อมใช้งานไม่ทัน', 8000);

      if (attempt > 0 && lastPoint) {
        try {
          await send('Input.dispatchMouseEvent', {type:'mouseMoved', x:lastPoint.x, y:lastPoint.y});
          await send('Input.dispatchMouseEvent', {type:'mousePressed', x:lastPoint.x, y:lastPoint.y, button:'left', clickCount:1});
          await send('Input.dispatchMouseEvent', {type:'mouseReleased', x:lastPoint.x, y:lastPoint.y, button:'left', clickCount:1});
          await wait(send, coverModalClosedExpression, 'บันทึกปกแล้ว แต่หน้าต่าง Cover Studio ยังไม่ปิด', 1500);
          return {success:true};
        } catch (e) {}
      }

      const saveResult = await evaluate(send, saveButtonExpression);
      if (saveResult === true || saveResult?.success) {
        lastPoint = saveResult === true ? null : saveResult;
        try {
          await wait(send, coverModalClosedExpression, 'บันทึกปกแล้ว แต่หน้าต่าง Cover Studio ยังไม่ปิด', 3500);
          return {success:true};
        } catch (e) {
          // Keep the point and retry after TikTok finishes the first render.
        }
      }
      await new Promise(r => setTimeout(r, 500));
    }

    throw new Error('กดบันทึกปกแล้ว แต่ TikTok ยังไม่ปิดหน้าต่าง Cover Studio หลังลองซ้ำ 3 ครั้ง');
  }

  return {evaluate, wait, page, buttonQuery, clickButton, uploadCover, waitForUploadStatusBadge};
})();
