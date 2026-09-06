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
    await clickButton(send, ['แก้ไขหน้าปก', 'แก้ไขปก', 'Edit cover'], false);
    await wait(send, page('return Boolean(dialog);'), 'ไม่พบหน้าต่างแก้ไขปก');
    const inputQuery = page(`
      if (!dialog) return null;
      const inputs = Array.from(dialog.querySelectorAll('input[type="file"]')).filter(el =>
        /image|\\.jpe?g|\\.png/i.test(el.accept || ''));
      return inputs.length === 1 ? inputs[0] : null;
    `);
    if (!await evaluate(send, `Boolean(${inputQuery})`)) {
      await clickButton(send, ['อัปโหลด', 'อัปโหลดรูปภาพ', 'อัปโหลดหน้าปก', 'Upload', 'Upload image']);
    }
    await wait(send, `Boolean(${inputQuery})`, 'ไม่พบช่องอัปโหลดภาพปกในหน้าต่าง TikTok');
    const {result, exceptionDetails} = await send('Runtime.evaluate', {expression:inputQuery});
    if (exceptionDetails || !result?.objectId) throw new Error('ช่องอัปโหลดปกไม่พร้อม');
    try {
      const {nodeId} = await send('DOM.requestNode', {objectId:result.objectId});
      await send('DOM.setFileInputFiles', {nodeId, files:[coverPath]});
    } finally {
      await send('Runtime.releaseObject', {objectId:result.objectId}).catch(() => {});
    }
    await wait(send, page(`
      if (!dialog) return false;
      const input = Array.from(dialog.querySelectorAll('input[type="file"]')).find(el => el.files?.length);
      const preview = Array.from(dialog.querySelectorAll('img, canvas')).some(el => visible(el) &&
        (el.tagName === 'CANVAS' ? el.width > 0 && el.height > 0 : el.complete && el.naturalWidth > 0));
      return Boolean(input && preview);
    `), 'TikTok ยังไม่แสดงภาพปกที่อัปโหลด');
    await clickButton(send, ['บันทึก', 'ยืนยัน', 'Save', 'Confirm']);
    await wait(send, page('return !dialog;'), 'หน้าต่างปกยังไม่ปิด กรุณาตรวจข้อความบน TikTok');
    return {success:true};
  }

  return {evaluate, wait, page, buttonQuery, clickButton, uploadCover};
})();
