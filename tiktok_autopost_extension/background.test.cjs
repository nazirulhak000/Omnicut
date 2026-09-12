const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function worker() {
  const context = vm.createContext({
    console, setTimeout: (fn) => { fn(); },
    chrome: {
      sidePanel: { setPanelBehavior: async () => {} },
      runtime: { onMessage: { addListener() {} } },
    },
  });
  context.importScripts = (...files) => files.forEach(file =>
    vm.runInContext(fs.readFileSync(path.join(__dirname, file), 'utf8'), context));
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8'), context);
  return context;
}

test('product search does not insert the ID a second time after setting its value', async () => {
  const ctx = worker();
  const calls = [];
  // Exercise the real orchestration with successful page responses; no TikTok requests.
  ctx.switchToShowcaseTab = async () => true;
  await ctx.attachProductLink(async (method, params) => {
    calls.push({ method, params });
    return { result: { value: { success: true } } };
  }, '1737088044189583209');
  assert.equal(calls.filter(c => c.method === 'Input.insertText').length, 0);
});

test('caption script exceptions must propagate instead of reporting success', async () => {
  const ctx = worker();
  await assert.rejects(() => ctx.typeCaption(async () => ({
    exceptionDetails: { text: 'Execution context was destroyed' },
  }), 'caption'), /Execution context|แคปชัน|คำอธิบาย/);
});

test('preparation stops on product failure before cover and schedule', async () => {
  const ctx = worker();
  const called = [];
  ctx.fetchPendingJob = async () => ({caption:'review', tiktok_product_id:'123'});
  ctx.runWaitForUploadOnly = async () => {};
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => ({success:false, reason:'product not found'});
  ctx.runUploadCoverOnly = async () => { called.push('cover'); };
  ctx.runScheduleModeOnly = async () => { called.push('schedule'); };
  const result = await ctx.runPrepareDetails({scheduleMode:true});
  assert.equal(result.success, false);
  assert.equal(result.step, 'product');
  assert.deepEqual(Array.from(result.completed), ['caption']);
  assert.deepEqual(called, ['caption']);
});

test('preparation completes in order and never calls publication', async () => {
  const ctx = worker();
  const called = [];
  ctx.fetchPendingJob = async () => ({caption:'review', tiktok_product_id:'123'});
  ctx.runWaitForUploadOnly = async () => {};
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => { called.push('product'); return {success:true}; };
  ctx.runUploadCoverOnly = async () => { called.push('cover'); return {success:true}; };
  ctx.runScheduleModeOnly = async () => { called.push('schedule'); return {success:true}; };
  ctx.runClickPostOnly = async () => { throw new Error('must not post'); };
  const result = await ctx.runPrepareDetails({scheduleMode:true});
  assert.equal(result.success, true);
  assert.deepEqual(called, ['caption', 'product', 'cover', 'schedule']);
});

test('preparation waits for the real upload to finish before doing anything else', async () => {
  // Regression: the "ทำต่อหลังอัปโหลด" shortcut becomes clickable as soon as
  // step 1 hands the file to TikTok's page, which is well before the upload
  // actually finishes -- confirmed live at 26% progress. Without this wait,
  // caption/product/cover all raced the real upload and TikTok's own
  // product-search endpoint refused results ("การตรวจสอบจะเริ่มได้หลังจาก
  // อัปโหลดไฟล์แล้วเท่านั้น").
  const ctx = worker();
  const called = [];
  ctx.fetchPendingJob = async () => ({caption:'review', tiktok_product_id:'123'});
  ctx.runWaitForUploadOnly = async () => { called.push('wait-for-upload'); };
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => { called.push('product'); return {success:true}; };
  ctx.runUploadCoverOnly = async () => { called.push('cover'); return {success:true}; };
  ctx.runScheduleModeOnly = async () => { called.push('schedule'); return {success:true}; };
  const result = await ctx.runPrepareDetails({scheduleMode:true});
  assert.equal(result.success, true);
  assert.deepEqual(called, ['wait-for-upload', 'caption', 'product', 'cover', 'schedule']);
});

test('preparation stops immediately if the upload never finishes, before touching caption/product/cover', async () => {
  const ctx = worker();
  const called = [];
  ctx.fetchPendingJob = async () => ({caption:'review', tiktok_product_id:'123'});
  ctx.runWaitForUploadOnly = async () => { throw new Error('TikTok ยังอัปโหลดวิดีโอไม่เสร็จ -- รอสักครู่แล้วลองใหม่'); };
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => { called.push('product'); return {success:true}; };
  ctx.runUploadCoverOnly = async () => { called.push('cover'); return {success:true}; };
  const result = await ctx.runPrepareDetails({scheduleMode:false});
  assert.equal(result.success, false);
  assert.match(result.error, /ยังอัปโหลดวิดีโอไม่เสร็จ/);
  assert.deepEqual(called, []);
  assert.deepEqual(Array.from(result.completed), []);
});

test('cover is rejected before any page interaction when missing', async () => {
  const ctx = worker();
  await assert.rejects(() => ctx.OmniAutomation.uploadCover(() => {
    throw new Error('must not touch page');
  }, null), /ยังไม่มีปก/);
});

test('cover upload dispatches input and change events after CDP sets the hidden file input', async () => {
  const ctx = worker();
  const calls = [];
  let filesSet = false;
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('dialogCandidates') && !params.returnByValue) {
        return {result: {objectId: 'cover-input'}};
      }
      if (expression.includes('input.files.length') && expression.includes('preview')) {
        return {result: {value: filesSet}};
      }
      return {result: {value: true}};
    }
    if (method === 'DOM.getDocument') return {root: {nodeId: 1}};
    if (method === 'DOM.querySelectorAll') return {nodeIds: [7]};
    if (method === 'DOM.resolveNode') return {object: {objectId: 'cover-input'}};
    if (method === 'Runtime.callFunctionOn') {
      return {result: {value: {fileCount: filesSet ? 1 : 0}}};
    }
    if (method === 'DOM.setFileInputFiles') {
      filesSet = true;
      return {};
    }
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  const notifyCall = calls.find(call => call.method === 'Runtime.callFunctionOn');
  const eventExpression = String(notifyCall?.params.functionDeclaration || '');
  assert.ok(eventExpression, 'must notify React about the selected cover');
  assert.match(eventExpression, /dispatchEvent\(new Event\('input'/);
  assert.match(eventExpression, /dispatchEvent\(new Event\('change'/);
});

test('cover upload resolves the DOM node directly when Runtime.requestNode cannot resolve TikTok input', async () => {
  const ctx = worker();
  const calls = [];
  let filesSet = false;
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('input.files.length') && expression.includes('preview')) {
        return {result: {value: filesSet}};
      }
      return {result: {value: true}};
    }
    if (method === 'DOM.getDocument') return {root: {nodeId: 1}};
    if (method === 'DOM.querySelectorAll') return {nodeIds: [13]};
    if (method === 'DOM.resolveNode') return {object: {objectId: 'cover-input'}};
    if (method === 'Runtime.callFunctionOn') {
      return {result: {value: {fileCount: filesSet ? 1 : 0}}};
    }
    if (method === 'DOM.setFileInputFiles') {
      filesSet = true;
      return {};
    }
    if (method === 'DOM.requestNode') return {};
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  assert.equal(calls.some(call => call.method === 'DOM.requestNode'), false);
  const setFileCall = calls.find(call => call.method === 'DOM.setFileInputFiles');
  assert.equal(setFileCall.params.nodeId, 13);
  assert.equal(Array.from(setFileCall.params.files)[0], 'D:/covers/demo_cover_3x4.jpg');
  assert.ok(calls.some(call => call.method === 'DOM.resolveNode'));
  const notifyCall = calls.find(call => call.method === 'Runtime.callFunctionOn');
  assert.match(notifyCall.params.functionDeclaration, /dispatchEvent\(new Event\('change'/);
});

test('cover upload sets the exact Cover Studio input object returned by the scoped query', async () => {
  const ctx = worker();
  const calls = [];
  let filesSet = false;
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('dialogCandidates') && params.returnByValue === false) {
        return {result: {objectId: 'exact-cover-input'}};
      }
      return {result: {value: filesSet || true}};
    }
    if (method === 'DOM.setFileInputFiles') {
      filesSet = true;
      return {};
    }
    if (method === 'Runtime.callFunctionOn') {
      return {result: {value: {fileCount: filesSet ? 1 : 0}}};
    }
    if (method === 'Runtime.releaseObject') return {};
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  const setFileCall = calls.find(call => call.method === 'DOM.setFileInputFiles');
  assert.equal(setFileCall.params.objectId, 'exact-cover-input');
  assert.equal('nodeId' in setFileCall.params, false);
  assert.ok(calls.some(call => call.method === 'Runtime.callFunctionOn'));
});

test('cover upload retries once when TikTok replaces the hidden input during file assignment', async () => {
  const ctx = worker();
  const calls = [];
  let targetNumber = 0;
  let notifyNumber = 0;
  const send = async (method, params = {}) => {
    calls.push({method, params});
    if (method === 'Runtime.evaluate') {
      const expression = String(params.expression || '');
      if (expression.includes('dialogCandidates') && params.returnByValue === false) {
        targetNumber += 1;
        return {result: {objectId: targetNumber === 1 ? 'stale-cover-input' : 'replacement-cover-input'}};
      }
      return {result: {value: true}};
    }
    if (method === 'DOM.setFileInputFiles') return {};
    if (method === 'Runtime.callFunctionOn') {
      notifyNumber += 1;
      return {result: {value: {fileCount: notifyNumber === 1 ? 0 : 1}}};
    }
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  const setCalls = calls.filter(call => call.method === 'DOM.setFileInputFiles');
  assert.deepEqual(setCalls.map(call => call.params.objectId), [
    'stale-cover-input',
    'replacement-cover-input',
  ]);
});

test('schedule time follows TikTok five-minute increments', () => {
  const ctx = worker();
  assert.equal(ctx.normalizeScheduleTime('16:08'), '16:10');
  assert.equal(ctx.normalizeScheduleTime('23:58'), '00:00');
  assert.equal(ctx.normalizeScheduleTime('09:35'), '09:35');
  assert.equal(ctx.normalizeScheduleTime('24:00'), '');
});

test('background.js does not contain invalid numeric ID selectors like #1 or #2', () => {
  const code = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');
  const invalidIdMatch = code.match(/querySelector(?:All)?\s*\(\s*['"`][^'"`]*#[0-9]/);
  assert.equal(invalidIdMatch, null, `Found invalid numeric ID selector: ${invalidIdMatch?.[0]}`);
});

test('live DOM contracts for the reported TikTok screens stay in the worker', () => {
  const code = fs.readFileSync(path.join(__dirname, 'background.js'), 'utf8');
  const automation = fs.readFileSync(path.join(__dirname, 'automation.js'), 'utf8');
  const panel = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  assert.match(code, /TUXRadioStandalone-input/);
  assert.match(code, /cartName/);
  assert.match(code, /scheduleDate/);
  assert.match(code, /tiktok-timepicker-option-text/);
  assert.match(code, /pickerOpen/);
  assert.match(code, /scrollIntoView\(\{block:'center'\}\)/g);
  assert.match(code, /calendar-wrapper.*span\.day\.valid/);
  assert.match(code, /calendar-wrapper/);
  assert.match(code, /span\.day\.valid/);
  const scheduleFn = code.slice(code.indexOf('async function switchToScheduleMode'), code.indexOf('async function setScheduleDateTime'));
  assert.match(scheduleFn, /input\[type="radio"\]\[value="schedule"\]/);
  assert.doesNotMatch(scheduleFn, /const TARGETS = \['ตั้งเวลา'/);
  const showcaseFn = code.slice(code.indexOf('async function switchToShowcaseTab'), code.indexOf('async function attachProductLink'));
  assert.doesNotMatch(showcaseFn, /dispatchEvent\(new MouseEvent/);
  assert.match(automation, /ImageUpload__uploadArea/);
  assert.match(automation, /DOM\.setFileInputFiles/);
  assert.match(automation, /CoverEditor__root/);
  assert.match(automation, /cover-editor-container/);
  assert.match(automation, /Input\.dispatchMouseEvent/);
  assert.match(automation, /editTarget/);
  assert.match(automation, /closest\('button, \[role="button"\]'\)/);
  assert.match(code, /ขั้น 5: เตรียมไฟล์ปกไม่สำเร็จ/);
  assert.match(code, /ขั้น 5: เปิด\/อัปโหลด\/บันทึกปกไม่สำเร็จ/);
  assert.match(automation, /หน้าต่าง Cover Studio ยังไม่ปิด/);
  assert.match(panel, /scheduleDateInput/);
  assert.match(panel, /scheduleTimeInput/);
  assert.match(panel, /product_name: item\.product_name/);
  assert.match(panel, /activeClip\.cover_path \|\| ''/);
  assert.match(panel, /SCHEDULE_LEAD_MINUTES = 15/);
  assert.match(panel, /minute \+= 5/);
  assert.match(panel, /classList\.add\('completed'\)/);
  const searchStep = code.slice(code.indexOf('// Step 4: Type Product ID'), code.indexOf('const searchVal'));
  assert.match(searchStep, /const search = root\.querySelector/);
  assert.doesNotMatch(searchStep, /const search = document\.querySelector/);
  assert.match(searchStep, /productContainers\.at\(-1\)/);
});

test('extension sidepanel exposes the stats-sync button in its own Tools tab', () => {
  const sideHtml = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const sideJs = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  // Stats sync lives in its own tab, not buried in the post checklist.
  assert.match(sideHtml, /id="tabBtnTools"/);
  assert.match(sideHtml, /id="panelTools"/);
  assert.match(sideHtml, /id="syncStatsBtn"/);
  assert.match(sideHtml, /ซิงก์สถิติ/);
  assert.match(sideHtml, /src="stats_parser\.js"/);
  const checklistSection = sideHtml.slice(sideHtml.indexOf('id="panelChecklist"'), sideHtml.indexOf('id="panelTools"'));
  assert.doesNotMatch(checklistSection, /syncStatsBtn/);
  // Wiring: tab switch + result is read from the injected execution.
  assert.match(sideJs, /const result = injected\?\.\[0\]\?\.result;/);
  assert.match(sideJs, /tabBtnTools\.addEventListener/);
  assert.match(sideJs, /\/api\/tiktok-stats\/import/);
  assert.match(sideJs, /parsePostsTable/);
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
  assert.ok(manifest.permissions.includes('scripting'));
});

test('extension UI exposes single consolidated TikTok upload opener and complies with clean UI standard', () => {
  const sideHtml = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const sideJs = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const popupHtml = fs.readFileSync(path.join(__dirname, 'popup.html'), 'utf8');
  const popupJs = fs.readFileSync(path.join(__dirname, 'popup.js'), 'utf8');

  // Verify single global header opener exists in sidepanel and single opener in popup
  assert.match(sideHtml, /id="headerOpenTikTokBtn"/);
  assert.match(popupHtml, /id="popupOpenTikTokBtn"/);

  // Verify redundant buttons were removed (User requested exactly one single spot)
  assert.doesNotMatch(sideHtml, /id="listOpenTikTokBtn"/);
  assert.doesNotMatch(sideHtml, /id="openTikTokBtn"/);
  assert.doesNotMatch(sideJs, /listOpenTikTokBtn/);
  assert.doesNotMatch(sideJs, /openTikTokBtn/);

  // Verify listeners and URL opener in JS
  assert.match(sideJs, /headerOpenTikTokBtn/);
  assert.match(sideJs, /tiktok\.com\/tiktokstudio\/upload/);
  assert.match(popupJs, /popupOpenTikTokBtn/);
  assert.match(popupJs, /tiktok\.com\/tiktokstudio\/upload/);

  // Verify clean UI standard: no emojis in button texts
  assert.doesNotMatch(sideHtml, /<button[^>]*>[^<]*[\u{1F300}-\u{1F9FF}][^<]*<\/button>/u);
  assert.doesNotMatch(popupHtml, /<button[^>]*>[^<]*[\u{1F300}-\u{1F9FF}][^<]*<\/button>/u);
});

