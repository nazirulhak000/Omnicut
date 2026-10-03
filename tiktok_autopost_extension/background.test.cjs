const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function worker(extraChrome = {}) {
  const context = vm.createContext({
    console, URL, setTimeout: (fn) => { fn(); },
    chrome: {
      sidePanel: { setPanelBehavior: async () => {} },
      runtime: { onMessage: { addListener() {} } },
      ...extraChrome,
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
  assert.deepEqual(called, ['caption', 'product', 'schedule', 'cover']);
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
  assert.deepEqual(called, ['wait-for-upload', 'caption', 'product', 'schedule', 'cover']);
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

test('schedule waits for TikTok time-picker animation to settle on the exact value', async () => {
  const ctx = worker();
  const snapshots = [
    ['2026-09-26', '19:20'],
    ['2026-09-26', '19:10'],
    ['2026-09-26', '19:00'],
  ];
  let attempts = 0;
  const sendEval = async () => {
    const value = snapshots[Math.min(attempts, snapshots.length - 1)];
    attempts += 1;
    return {result: {value}};
  };

  const result = await ctx.waitForScheduleValues(sendEval, '2026-09-26', '19:00', 1000);

  assert.equal(result.success, true);
  assert.equal(attempts, 3);
  assert.deepEqual(Array.from(result.shown), ['2026-09-26', '19:00']);
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
  assert.match(automation, /attempt < 3/);
  assert.match(code, /\/api\/exports\/mark-posted/);
  assert.match(code, /marked: true/);
  assert.match(panel, /await openTikTokUploadTab\(\)/);
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

test('stats sync accepts the real Studio posts page and stamps a visible build tag', () => {
  const sideHtml = fs.readFileSync(path.join(__dirname, 'sidepanel.html'), 'utf8');
  const sideJs = fs.readFileSync(path.join(__dirname, 'sidepanel.js'), 'utf8');
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
  // Build identity: chrome://extensions + the Tools tab both prove the fresh
  // code is running, so stale cached sidepanel.js (the ghost "จำกัดโดเมน"
  // banner that never existed in this repo) can be caught by the user's eyes.
  assert.equal(manifest.version, '0.2.0');
  assert.match(sideHtml, /id="buildTag"/);
  assert.match(sideJs, /getManifest/);
  // The strict domain banner must never come back: resolution is a loose
  // tiktok.com check with a page-side location.href fallback and an error
  // that reports the URL actually seen.
  assert.doesNotMatch(sideJs, /จำกัดโดเมน/);
  assert.match(sideJs, /resolveTikTokTab/);
  assert.match(sideJs, /tiktokHrefOf/);
  assert.match(sideJs, /func: \(\) => location\.href/);
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


test('confirmed post marks the exact pending export automatically', async () => {
  const ctx = worker();
  const calls = [];
  ctx.chrome.debugger = {attach: async () => {}, detach: async () => {}};
  ctx.fetchPendingJob = async () => ({
    video_path: '04_Exports/Ready_to_post/demo.mp4',
    export_id: 'exp-1',
    product_id: 'product-1',
    angle_id: 'angle-1',
  });
  ctx.findUploadTab = async () => ({id: 7, windowId: 3, url: 'https://www.tiktok.com/tiktokstudio/upload'});
  ctx.cdp = () => async () => {};
  ctx.clickPostButton = async () => {};
  ctx.markPendingJobPosted = async (job) => { calls.push(['mark', job]); return {success:true}; };
  ctx.clearPendingJob = async () => { calls.push(['clear']); };
  ctx.openUploadPage = async (tab) => { calls.push(['upload-page', tab.id]); return tab; };

  const result = await ctx.runClickPostOnly();

  assert.equal(result.success, true);
  assert.equal(result.clicked, true);
  assert.equal(result.posted, true);
  assert.equal(result.marked, true);
  assert.equal(calls[0][0], 'mark');
  assert.equal(calls[0][1].export_id, 'exp-1');
  assert.deepEqual(calls.slice(1), [['clear'], ['upload-page', 7]]);
});

// --- post confirmation: only a POSITIVE signal counts as posted ---------------

const UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload?from=webapp';
const editorGoneEval = async () => ({ result: { value: { done: true, failed: false, reason: 'editor-gone' } } });
const stillEditingEval = async () => ({ result: { value: { done: false } } });

test('background registers a chrome.debugger.onDetach listener that records detaches per tab', () => {
  let listener = null;
  const context = worker({ debugger: { onDetach: { addListener: (fn) => { listener = fn; } } } });
  assert.equal(typeof listener, 'function');
  const before = Date.now();
  listener({ tabId: 5 }, 'canceled_by_user');
  assert.equal(context.getDebuggerDetach(5, before).reason, 'canceled_by_user');
  assert.equal(context.getDebuggerDetach(6, before), null);
  assert.equal(context.getDebuggerDetach(5, Date.now() + 1000), null);
});

test('decidePostConfirmation: only a positive URL signal confirms', () => {
  const ctx = worker();
  const d = (o) => ctx.decidePostConfirmation(o);
  assert.equal(d({ tabUrl: 'https://www.tiktok.com/tiktokstudio/content' }).outcome, 'confirmed');
  assert.equal(d({ tabUrl: UPLOAD_URL }).outcome, 'pending');
  assert.equal(d({ tabUrl: UPLOAD_URL, evalThrew: true }).outcome, 'pending');
  assert.equal(d({ tabUrl: UPLOAD_URL, evalValue: { done: true, failed: false } }).outcome, 'pending');
  assert.equal(d({ tabUrl: 'about:blank' }).outcome, 'pending');
  assert.equal(d({ tabUrl: 'https://www.tiktok.com/login' }).outcome, 'pending');
  assert.equal(d({ tabUrl: 'https://evil.example/tiktok.com' }).outcome, 'pending');
  assert.equal(d({ tabMissing: true }).reason, 'tab-gone-unverified');
  assert.equal(d({ tabUrl: UPLOAD_URL, evalValue: { done: true, failed: true, message: 'x' } }).outcome, 'failed');
  assert.equal(d({ tabUrl: UPLOAD_URL, detach: { reason: 'canceled_by_user' } }).reason, 'debugger-detached');
  // A user cancel never counts as success, even if the URL looks like it moved on.
  assert.equal(d({ tabUrl: 'https://www.tiktok.com/tiktokstudio/content', detach: { reason: 'canceled_by_user' } }).outcome, 'unconfirmed');
});

test('waitForPostConfirmation: debugger detached during the wait is unconfirmed', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };
  const send = async () => {
    ctx.recordDebuggerDetach({ tabId: 7 }, 'canceled_by_user');
    throw new Error('Debugger is not attached to the tab with id: 7.');
  };
  const res = await ctx.waitForPostConfirmation(send, 7, 5000);
  assert.equal(res.confirmed, false);
  assert.equal(res.reason, 'debugger-detached');
  assert.equal(res.detachReason, 'canceled_by_user');
});

test('waitForPostConfirmation: editor gone but URL still /upload is not confirmed', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };
  const res = await ctx.waitForPostConfirmation(editorGoneEval, 7, 50);
  assert.equal(res.confirmed, false);
  assert.equal(res.timedOut, true);
  assert.equal(res.editorGone, true);
});

test('waitForPostConfirmation: evaluate always throwing with URL on /upload is not confirmed', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };
  const res = await ctx.waitForPostConfirmation(async () => { throw new Error('Execution context was destroyed'); }, 7, 50);
  assert.equal(res.confirmed, false);
  assert.equal(res.timedOut, true);
});

test('waitForPostConfirmation: tab removed without a positive signal is not confirmed', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => { throw new Error('No tab with id: 7.'); } };
  const res = await ctx.waitForPostConfirmation(async () => { throw new Error('gone'); }, 7, 5000);
  assert.equal(res.confirmed, false);
  assert.equal(res.reason, 'tab-gone-unverified');
});

test('waitForPostConfirmation: URL leaving /upload is still confirmed (even if evaluate throws)', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: 'https://www.tiktok.com/tiktokstudio/content' }) };
  const viaEval = await ctx.waitForPostConfirmation(stillEditingEval, 7, 5000);
  assert.equal(viaEval.confirmed, true);
  assert.equal(viaEval.reason, 'navigated-away');
  const viaThrow = await ctx.waitForPostConfirmation(async () => { throw new Error('context destroyed'); }, 7, 5000);
  assert.equal(viaThrow.confirmed, true);
  assert.equal(viaThrow.reason, 'navigated-away');
});

test('waitForPostConfirmation: TikTok rejection toast is reported verbatim', async () => {
  const ctx = worker();
  ctx.chrome.tabs = { get: async () => ({ url: UPLOAD_URL }) };
  const send = async () => ({ result: { value: { done: true, failed: true, message: 'กรุณาเลือกหมวดหมู่' } } });
  const res = await ctx.waitForPostConfirmation(send, 7, 5000);
  assert.equal(res.confirmed, false);
  assert.equal(res.message, 'กรุณาเลือกหมวดหมู่');
});

function clickPostHarness({ tabUrl, onConfirmationEval }) {
  const ctx = worker();
  const calls = [];
  ctx.fetchPendingJob = async () => ({ video_path: 'clip.mp4', export_id: 'exp-1' });
  ctx.findUploadTab = async () => ({ id: 7, windowId: 3, url: UPLOAD_URL });
  ctx.waitForUploadComplete = async () => true;
  ctx.dismissLeaveConfirmDialogIfPresent = async () => false;
  ctx.chrome.tabs = { get: async () => ({ url: tabUrl }) };
  ctx.chrome.debugger = {
    attach: async () => {},
    detach: async () => {},
    sendCommand: async (_target, method) => {
      if (method !== 'Runtime.evaluate') return {};
      // First evaluate = the click; later ones = confirmation polls.
      if (!calls.includes('clicked')) {
        calls.push('clicked');
        return { result: { value: { success: true, method: 'direct' } } };
      }
      return onConfirmationEval(ctx);
    },
  };
  ctx.markPendingJobPosted = async () => { calls.push('mark'); return { success: true }; };
  ctx.clearPendingJob = async () => { calls.push('clear'); };
  ctx.openUploadPage = async () => { calls.push('upload-page'); };
  return { ctx, calls };
}

test('runClickPostOnly does not call mark-posted when the debugger is detached during confirmation', async () => {
  const { ctx, calls } = clickPostHarness({
    tabUrl: UPLOAD_URL,
    onConfirmationEval: (c) => {
      c.recordDebuggerDetach({ tabId: 7 }, 'canceled_by_user');
      throw new Error('Debugger is not attached to the tab with id: 7.');
    },
  });
  await assert.rejects(() => ctx.runClickPostOnly(), /post_not_confirmed.*ตัดการเชื่อมต่อ/);
  assert.deepEqual(calls, ['clicked']);
});

test('runClickPostOnly still marks posted on a genuine success (URL left /upload)', async () => {
  const { ctx, calls } = clickPostHarness({
    tabUrl: 'https://www.tiktok.com/tiktokstudio/content',
    onConfirmationEval: () => ({ result: { value: { done: false } } }),
  });
  const result = await ctx.runClickPostOnly();
  assert.equal(result.marked, true);
  assert.deepEqual(calls, ['clicked', 'mark', 'clear', 'upload-page']);
});
