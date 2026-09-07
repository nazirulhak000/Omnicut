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
  ctx.runTypeCaptionOnly = async () => { called.push('caption'); };
  ctx.runAttachProductOnly = async () => { called.push('product'); return {success:true}; };
  ctx.runUploadCoverOnly = async () => { called.push('cover'); return {success:true}; };
  ctx.runScheduleModeOnly = async () => { called.push('schedule'); return {success:true}; };
  ctx.runClickPostOnly = async () => { throw new Error('must not post'); };
  const result = await ctx.runPrepareDetails({scheduleMode:true});
  assert.equal(result.success, true);
  assert.deepEqual(called, ['caption', 'product', 'cover', 'schedule']);
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
    if (method === 'DOM.requestNode') return {nodeId: 7};
    if (method === 'DOM.setFileInputFiles') {
      filesSet = true;
      return {};
    }
    return {};
  };

  await ctx.OmniAutomation.uploadCover(send, 'D:/covers/demo_cover_3x4.jpg');
  const eventExpression = calls
    .filter(call => call.method === 'Runtime.evaluate')
    .map(call => String(call.params.expression || ''))
    .find(expression => expression.includes("dispatchEvent(new Event('input'") );
  assert.ok(eventExpression, 'must notify React about the selected cover');
  assert.match(eventExpression, /dispatchEvent\(new Event\('change'/);
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
