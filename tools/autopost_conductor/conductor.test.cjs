'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { runClipGuarded, runBatch, runClip, skipReason, clipFromQueueItem, pickClips, FatalError, rowMatchesClip } = require('./conductor');
const { createStorage, urlMatches } = require('./chrome_shim');
const { readApiKey } = require('./api');
const { parseArgs } = require('./run');

const FUTURE = '2030-01-01T10:00';
const item = (over = {}) => ({
  id: 'q1', status: 'planned', export_id: 'e1', video_path: 'a.mp4', scheduled_at: FUTURE,
  tiktok_product_id: '123', caption: 'พัดลมพกพา', hashtags: '#fan', hook_title: 'hook', ...over,
});

function fakeDeps({ replies = {}, prepare, pending, onSend } = {}) {
  const calls = [];
  const worker = { send: async (action, payload) => {
    calls.push(action); onSend?.(action, payload);
    const r = replies[action];
    if (r instanceof Error) throw r;
    return typeof r === 'function' ? r(payload) : (r ?? { success: true });
  } };
  const api = {
    post: async (route, body) => {
      calls.push('POST ' + route);
      if (route.endsWith('/prepare')) return prepare ? prepare(body) : { ok: true, status: 200, data: { protocol_version: 2, channel_id: 'main', job_id: 'j1', cover_path: 'c.jpg' } };
      return { ok: true, status: 200, data: {} };
    },
    get: async route => { calls.push('GET ' + route); return pending ? pending() : { ok: false, status: 404, data: {} }; },
  };
  const logs = [];
  return { calls, logs, deps: { worker, api, sleep: async () => {}, log: (l, m) => logs.push([l, m]),
    shot: async () => {}, dumpDom: async () => {} } };
}

test('clipFromQueueItem splits scheduled_at into date and time', () => {
  const clip = clipFromQueueItem(item());
  assert.equal(clip.schedule_date, '2030-01-01');
  assert.equal(clip.schedule_time, '10:00');
});

test('skipReason: past slot, no product, price caption, no schedule', () => {
  const now = new Date('2026-11-09T10:00:00').getTime();
  assert.equal(skipReason(clipFromQueueItem(item()), { now }), '');
  assert.equal(skipReason(clipFromQueueItem(item({ scheduled_at: '2026-11-09T10:05' })), { now }), 'slot_passed_or_too_close');
  assert.equal(skipReason(clipFromQueueItem(item({ tiktok_product_id: null })), { now }), 'no_tiktok_product_id');
  assert.equal(skipReason(clipFromQueueItem(item({ caption: 'ลด 50% วันนี้' })), { now }), 'price_in_caption');
  assert.equal(skipReason(clipFromQueueItem(item({ caption: 'ต้องมี! {product_name} ดีมาก' })), { now }), 'placeholder_in_caption');
  assert.equal(skipReason(clipFromQueueItem(item({ caption: 'ลด 50% วันนี้' })), { now, allowPriceCaption: true }), '');
  assert.equal(skipReason(clipFromQueueItem(item({ scheduled_at: '' })), { now }), 'no_schedule');
});

test('pickClips keeps only planned/ready items, sorted, limited, with skip reasons', async () => {
  const api = { get: async route => route.includes('schedule-queue') ? ({ ok: true, data: { items: [
    item({ id: 'b', scheduled_at: '2030-01-02T10:00' }), item({ id: 'a' }),
    item({ id: 'done', status: 'posted' }), item({ id: 'np', tiktok_product_id: '' }),
  ] } }) : ({ ok: false }) };
  const { clips, skipped } = await pickClips(api, { limit: 1, now: new Date('2026-11-09').getTime() });
  assert.deepEqual(clips.map(c => c.id), ['a']);
  assert.deepEqual(skipped.map(s => s.reason), ['no_tiktok_product_id']);
});

test('real run goes prepare → claim → upload → wait → details → post, then maps outcome', async () => {
  const { deps, calls } = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'scheduled_on_platform' } } });
  const res = await runClip(deps, clipFromQueueItem(item()), { dryRun: false });
  assert.equal(res.status, 'scheduled');
  assert.deepEqual(calls.filter(c => !c.startsWith('GET')), [
    'POST /api/tiktok-autopost/prepare', 'claim-posting-job', 'upload-file-only', 'wait-for-upload-only',
    'prepare-details', 'click-post-only', 'retry-posting-receipt']);
});

test('dry run fills everything but NEVER clicks post, then releases the job', async () => {
  const { deps, calls } = fakeDeps();
  const res = await runClip(deps, clipFromQueueItem(item()), { dryRun: true });
  assert.equal(res.status, 'dry_run_ok');
  assert.ok(!calls.includes('click-post-only'));
  assert.ok(calls.indexOf('release-posting-job') > calls.indexOf('prepare-details'));
});

test('unconfirmed post is reconciled and reported as unknown (never as posted)', async () => {
  const { deps, calls } = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'confirmation_unknown' } } });
  const res = await runClip(deps, clipFromQueueItem(item()), {});
  assert.equal(res.status, 'unknown');
  assert.ok(calls.includes('reconcile-posting-result'));
});

test('export that already has a claimed job is skipped, never cancelled', async () => {
  const { deps, calls } = fakeDeps({
    prepare: () => ({ ok: false, status: 409, data: { code: 'posting_export_already_prepared' } }),
    pending: () => ({ ok: true, data: { job_id: 'j9', status: 'claimed', export_id: 'e1' } }),
  });
  const res = await runClip(deps, clipFromQueueItem(item()), {});
  assert.equal(res.status, 'skipped');
  assert.ok(!calls.includes('POST /api/tiktok-autopost/clear'));
  assert.ok(!calls.includes('claim-posting-job'));
});

test('stale prepared job of the same export is cleared once then re-prepared', async () => {
  let n = 0;
  const { deps, calls } = fakeDeps({
    prepare: () => (n++ === 0 ? { ok: false, status: 409, data: { code: 'posting_export_already_prepared' } }
      : { ok: true, data: { protocol_version: 2, channel_id: 'main', job_id: 'j2' } }),
    pending: () => ({ ok: true, data: { job_id: 'j9', status: 'prepared', export_id: 'e1' } }),
  });
  const res = await runClip(deps, clipFromQueueItem(item()), { dryRun: true });
  assert.equal(res.status, 'dry_run_ok');
  assert.ok(calls.includes('POST /api/tiktok-autopost/clear'));
});

test('login/captcha/account errors abort the whole run instead of being retried', async () => {
  const { deps } = fakeDeps({ replies: { 'upload-file-only': { success: false, error: 'account_handle_mismatch: ผิดบัญชี' } } });
  await assert.rejects(() => runClip(deps, clipFromQueueItem(item()), {}), FatalError);
});

test('batch: clips run strictly one at a time with park + reset before each', async () => {
  const { deps, calls } = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'published' } } });
  const clips = [clipFromQueueItem(item({ id: 'a' })), clipFromQueueItem(item({ id: 'b', export_id: 'e2' }))];
  const res = await runBatch(deps, { clips, random: () => 0 });
  assert.equal(res.posted, 2);
  const order = calls.filter(c => ['release-posting-job', 'reset-upload-page', 'POST /api/tiktok-autopost/prepare', 'click-post-only'].includes(c));
  assert.deepEqual(order, ['release-posting-job', 'reset-upload-page', 'POST /api/tiktok-autopost/prepare', 'click-post-only',
    'release-posting-job', 'reset-upload-page', 'POST /api/tiktok-autopost/prepare', 'click-post-only']);
});

test('batch: 3 failures in a row trip the breaker; a fatal error aborts immediately', async () => {
  const failing = fakeDeps({ replies: { 'upload-file-only': { success: false, error: 'selector missing' } } });
  const clips = ['a', 'b', 'c', 'd'].map(id => clipFromQueueItem(item({ id, export_id: id })));
  const res = await runBatch(failing.deps, { clips, random: () => 0 });
  assert.equal(res.failed, 3);
  assert.match(res.aborted, /ติดกัน 3/);
  const fatal = fakeDeps({ replies: { 'release-posting-job': { success: false, error: 'posting_receipt_unsent: x' } } });
  const res2 = await runBatch(fatal.deps, { clips, random: () => 0 });
  assert.match(res2.aborted, /^fatal@park/);
  assert.equal(res2.results.length, 1);
});

test('batch: shouldStop stops before the next clip', async () => {
  const { deps } = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'published' } } });
  let stop = false;
  deps.sleep = async () => { stop = true; };
  const clips = ['a', 'b'].map(id => clipFromQueueItem(item({ id, export_id: id })));
  const res = await runBatch(deps, { clips, shouldStop: () => stop, random: () => 0 });
  assert.equal(res.posted, 1);
  assert.equal(res.aborted, 'stopped_by_user');
});

test('chrome shim: url match patterns and durable storage that never writes secrets', () => {
  assert.ok(urlMatches('https://www.tiktok.com/tiktokstudio/upload', 'https://www.tiktok.com/tiktokstudio/upload*'));
  assert.ok(urlMatches('https://www.tiktok.com/tiktokstudio/content', ['*://*.tiktok.com/*']));
  assert.ok(!urlMatches('https://example.com/', ['*://*.tiktok.com/*']));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'shim-'));
  const file = path.join(dir, 's.json');
  try {
    const a = createStorage({ file, secrets: { omnicutApiKey: 'SECRET' } });
    a.set({ state: { n: 1 }, omnicutApiKey: 'ignored' });
    const b = createStorage({ file, secrets: { omnicutApiKey: 'SECRET' } });
    let got;
    b.get(['state', 'omnicutApiKey'], v => { got = v; });
    assert.deepEqual(got, { state: { n: 1 }, omnicutApiKey: 'SECRET' });
    assert.ok(!fs.readFileSync(file, 'utf8').includes('SECRET'));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('api key from env or .env file; CLI args validated', () => {
  assert.equal(readApiKey({ OMNICUT_API_KEY: 'k1' }, '/nope'), 'k1');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'env-'));
  try {
    fs.writeFileSync(path.join(dir, '.env'), 'A=1\nOMNICUT_API_KEY="k2"\n');
    assert.equal(readApiKey({}, path.join(dir, '.env')), 'k2');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  assert.equal(parseArgs(['--dry-run', '--limit', '3']).dryRun, true);
  assert.throws(() => parseArgs(['--limit', '0']));
  assert.throws(() => parseArgs(['--bogus']));
});

test('host loads the real extension worker and answers actions through the shim', async () => {
  const { createChromeShim } = require('./chrome_shim');
  const { loadWorker } = require('./host');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'host-'));
  try {
    const shim = createChromeShim({ port: 1, storageFile: path.join(dir, 's.json'), secrets: { omnicutApiKey: 'k' } });
    const worker = loadWorker({ shim });
    const ok = await worker.send('select-posting-channel', { channelId: 'main' });
    assert.equal(ok.success, true);
    assert.equal(ok.channel_id, 'main');
    const bad = await worker.send('select-posting-channel', { channelId: 'BAD CHANNEL' });
    assert.equal(bad.success, false);
    const park = await worker.send('release-posting-job', { park: true });
    assert.equal(park.success, true);
    assert.ok(fs.existsSync(path.join(dir, 's.json')), 'posting state is persisted for resume');
    assert.ok(!fs.readFileSync(path.join(dir, 's.json'), 'utf8').includes('"omnicutApiKey":"k"'));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('dry-run replaces a passed slot with a synthetic future one; real run still skips it', async () => {
  const past = item({ scheduled_at: '2020-01-01T10:00' });
  const api = { get: async route => route.includes('schedule-queue') ? ({ ok: true, data: { items: [past] } }) : ({ ok: false }) };
  const now = new Date('2026-11-09T10:00:00').getTime();
  const real = await pickClips(api, { now });
  assert.equal(real.clips.length, 0);
  assert.equal(real.skipped[0].reason, 'slot_passed_or_too_close');
  const dry = await pickClips(api, { now, dryRun: true });
  assert.equal(dry.clips.length, 1);
  assert.equal(dry.clips[0].schedule_date, '2026-11-11');
  assert.equal(dry.clips[0].schedule_overridden, true);
});

test('no custom-cover upload: dry-run keeps going with TikTok auto cover; real run fails unless allowed', async () => {
  const noCover = { success: false, step: 'cover', completed: ['caption', 'product', 'schedule'], error: 'ไม่พบ node ของช่องอัปโหลดปก' };
  const dry = fakeDeps({ replies: { 'prepare-details': noCover } });
  let dismissed = 0;
  dry.deps.dismissCoverModal = async () => { dismissed += 1; };
  const r1 = await runClip(dry.deps, clipFromQueueItem(item()), { dryRun: true });
  assert.equal(r1.status, 'dry_run_ok');
  assert.equal(r1.cover_fallback, true);
  assert.equal(dismissed, 1);

  const strict = fakeDeps({ replies: { 'prepare-details': noCover } });
  const r2 = await runClip(strict.deps, clipFromQueueItem(item()), {});
  assert.equal(r2.status, 'failed');
  assert.ok(!strict.calls.includes('click-post-only'));

  const allowed = fakeDeps({ replies: { 'prepare-details': noCover, 'click-post-only': { success: true, outcome: 'scheduled_on_platform' } } });
  allowed.deps.dismissCoverModal = async () => {};
  const r3 = await runClip(allowed.deps, clipFromQueueItem(item()), { coverFallback: true });
  assert.equal(r3.status, 'scheduled');
  assert.equal(r3.cover_fallback, true);

  // a failure BEFORE the cover step is never excused by the fallback
  const early = fakeDeps({ replies: { 'prepare-details': { success: false, step: 'product', completed: ['caption'], error: 'x' } } });
  const r4 = await runClip(early.deps, clipFromQueueItem(item()), { coverFallback: true, dryRun: true });
  assert.equal(r4.status, 'failed');
});

test('content page row matching: caption start + scheduled day/time, 12h or 24h', () => {
  const clip = { caption: 'เล่นเกมนานแค่ไหนเครื่องก็ไม่ร้อน! HOYAUP พัดลม', schedule_date: '2026-11-10', schedule_time: '07:00' };
  const mk = badge => ['00:35', 'เล่นเกมนานแค่ไหนเครื่องก็ไม่ร้อน! HOYAUP พัดลมระบายความร้อน', badge, 'Everyone', '0'].join(String.fromCharCode(10));
  const row = mk('Nov 10, 7:00 AM (GMT+7) Bangkok');
  assert.equal(rowMatchesClip(row, clip).ok, true);
  assert.equal(rowMatchesClip(mk('Nov 10, 8:00 AM (GMT+7) Bangkok'), clip).reason, 'schedule_badge_mismatch');
  assert.equal(rowMatchesClip(mk('Nov 11, 7:00 AM (GMT+7) Bangkok'), clip).reason, 'schedule_badge_mismatch');
  assert.equal(rowMatchesClip(['00:25', 'บอกลาหูฟังแบตหมดกลางคัน', 'Sep 19'].join(String.fromCharCode(10)), clip).reason, 'caption_not_found');
  assert.equal(rowMatchesClip(mk('Nov 10, 9:00 PM (GMT+7) Bangkok'), { ...clip, schedule_time: '21:00' }).ok, true);
  assert.equal(rowMatchesClip(row, { caption: 'short', schedule_date: '', schedule_time: '' }).reason, 'caption_not_found');
});

test('a post that TikTok acked but the Content page does not show is reported unknown, not success', async () => {
  const { deps } = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'scheduled_on_platform' } } });
  deps.verifyOnContentPage = async () => ({ ok: false, reason: 'row_not_found' });
  const res = await runClip(deps, clipFromQueueItem(item()), {});
  assert.equal(res.status, 'unknown');
  assert.match(res.error, /content_page_not_verified/);
  const good = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'scheduled_on_platform' } } });
  good.deps.verifyOnContentPage = async () => ({ ok: true });
  const ok = await runClip(good.deps, clipFromQueueItem(item()), {});
  assert.equal(ok.status, 'scheduled');
  assert.equal(ok.verified, true);
});

test('pickClips skips queue items whose export is missing, posted or QC-rejected', async () => {
  const queue = [item({ id: 'ok1', export_id: 'e1' }), item({ id: 'gone', export_id: 'e2' }),
    item({ id: 'done', export_id: 'e3' }), item({ id: 'bad', export_id: 'e4' })];
  const exportsList = [{ id: 'e1' }, { id: 'e3', is_posted: true }, { id: 'e4', is_qc_rejected: true }];
  const api = { get: async route => route.includes('schedule-queue') ? { ok: true, data: { items: queue } } : { ok: true, data: { exports: exportsList } } };
  const { clips, skipped } = await pickClips(api, { now: new Date('2026-11-09').getTime() });
  assert.deepEqual(clips.map(c => c.id), ['ok1']);
  assert.deepEqual(skipped.map(s => s.reason).sort(), ['export_already_posted', 'export_missing', 'export_qc_rejected']);
});

test('a 409 from prepare (stale export) is a skip, not a failure, and never reaches the browser', async () => {
  const { deps, calls } = fakeDeps({ prepare: () => ({ ok: false, status: 409, data: { detail: 'ไม่พบ export_id' } }) });
  const res = await runClip(deps, clipFromQueueItem(item()), {});
  assert.equal(res.status, 'skipped');
  assert.match(res.reason, /prepare_409/);
  assert.ok(!calls.includes('claim-posting-job'));
  const server = fakeDeps({ prepare: () => ({ ok: false, status: 500, data: {} }) });
  assert.equal((await runClip(server.deps, clipFromQueueItem(item()), {})).status, 'failed');
});

test('watchdog: a hung clip is cut off, recover() runs, and the batch moves on', async () => {
  const hang = fakeDeps({ replies: { 'upload-file-only': () => new Promise(() => {}) } });
  let recovered = 0;
  hang.deps.recover = async () => { recovered += 1; };
  const res = await runClipGuarded(hang.deps, clipFromQueueItem(item()), {}, 30);
  assert.equal(res.status, 'failed');
  assert.equal(res.step, 'timeout');
  assert.equal(recovered, 1);

  const clips = ['a', 'b'].map(id => clipFromQueueItem(item({ id, export_id: id })));
  const batch = fakeDeps({ replies: { 'upload-file-only': () => new Promise(() => {}) } });
  batch.deps.recover = async () => {};
  const out = await runBatch(batch.deps, { clips, clipBudgetMs: 20, random: () => 0 });
  assert.equal(out.failed, 2);
  assert.ok(out.results.every(r => r.step === 'timeout'));
});

test('CLI: viewport, net and budget are validated', () => {
  const a = parseArgs(['--viewport', '1366x768', '--net', 'slow', '--clip-budget-min', '5']);
  assert.equal(a.viewport, '1366x768');
  assert.equal(a.net, 'slow');
  assert.equal(a.clipBudgetMin, 5);
  assert.throws(() => parseArgs(['--viewport', 'wide']));
  assert.throws(() => parseArgs(['--net', 'fast']));
  assert.throws(() => parseArgs(['--clip-budget-min', '0']));
});

test('a pre-post hiccup is retried once from a clean page; a post-click failure is never retried', async () => {
  let n = 0;
  const flaky = fakeDeps({ replies: { 'prepare-details': () => (n++ === 0 ? { success: false, step: 'caption', completed: [], error: 'caption not accepted' } : { success: true }),
    'click-post-only': { success: true, outcome: 'scheduled_on_platform' } } });
  const clips = [clipFromQueueItem(item())];
  const res = await runBatch(flaky.deps, { clips, random: () => 0 });
  assert.equal(res.scheduled, 1);
  assert.equal(res.results[0].retried, true);
  assert.equal(flaky.calls.filter(c => c === 'upload-file-only').length, 2);

  const afterClick = fakeDeps({ replies: { 'click-post-only': { success: false, error: 'post_not_confirmed' } } });
  const out = await runBatch(afterClick.deps, { clips, random: () => 0 });
  assert.equal(afterClick.calls.filter(c => c === 'click-post-only').length, 1);
  assert.equal(out.results[0].status, 'failed');
});

test('a hung page (no CDP reply) times out instead of waiting forever, and the tab can be replaced', async () => {
  const { createChromeShim } = require('./chrome_shim');
  process.env.OMNICUT_CDP_TIMEOUT_MS = '60';
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hang-'));
  try {
    const target = { id: 'T1', type: 'page', url: 'https://www.tiktok.com/tiktokstudio/upload', title: 'x', webSocketDebuggerUrl: 'ws://fake/T1' };
    const requests = [];
    const fetchImpl = async (url, opts = {}) => {
      requests.push(`${opts.method || 'GET'} ${url.replace(/^http:\/\/127\.0\.0\.1:\d+/, '')}`);
      if (url.endsWith('/json/list')) return { json: async () => [target] };
      if (url.includes('/json/new')) return { json: async () => ({ ...target, id: 'T2' }) };
      return { json: async () => ({}) };
    };
    class SilentSocket { // opens, then never answers a command
      constructor() { this.l = {}; setTimeout(() => (this.l.open || []).forEach(f => f()), 0); }
      addEventListener(type, fn) { (this.l[type] = this.l[type] || []).push(fn); }
      send() {}
      close() { (this.l.close || []).forEach(f => f()); }
    }
    const shim = createChromeShim({ port: 1, storageFile: path.join(dir, 's.json'), WebSocketImpl: SilentSocket, fetchImpl });
    const [tab] = await shim.chrome.tabs.query({ url: '*://www.tiktok.com/*' });
    const started = Date.now();
    await assert.rejects(() => shim.evaluate(tab.id, '1'), /cdp_timeout/);
    assert.ok(Date.now() - started < 2000);
    const fresh = await shim.replaceTab(tab.id, 'https://www.tiktok.com/tiktokstudio/upload');
    assert.ok(fresh.id !== undefined);
    assert.ok(requests.some(r => r.startsWith('GET /json/close/T1')));
    assert.ok(requests.some(r => r.startsWith('PUT /json/new')));
  } finally {
    delete process.env.OMNICUT_CDP_TIMEOUT_MS;
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('between clips the browser is checked first; a lost login aborts the run, other errors only warn', async () => {
  const ok = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'published' } } });
  let checked = 0;
  ok.deps.ensureBrowser = async () => { checked += 1; };
  const clips = ['a', 'b'].map(id => clipFromQueueItem(item({ id, export_id: id })));
  await runBatch(ok.deps, { clips, random: () => 0 });
  assert.equal(checked, 2);

  const lost = fakeDeps();
  lost.deps.ensureBrowser = async () => { throw new Error('login_required: TikTok Studio ไม่พร้อม'); };
  const res = await runBatch(lost.deps, { clips, random: () => 0 });
  assert.match(res.aborted, /^fatal@browser/);
  assert.equal(res.results.length, 1);

  const flaky = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'published' } } });
  flaky.deps.ensureBrowser = async () => { throw new Error('chrome launch slow'); };
  const res2 = await runBatch(flaky.deps, { clips, random: () => 0 });
  assert.equal(res2.posted, 2);
});

test('a replaced worker is the only one that answers (a stuck old worker must not shadow it)', async () => {
  const { createChromeShim } = require('./chrome_shim');
  const { loadWorker } = require('./host');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'two-'));
  try {
    const shim = createChromeShim({ port: 1, storageFile: path.join(dir, 's.json'), secrets: { omnicutApiKey: 'k' } });
    const first = loadWorker({ shim });
    // Wedge the first worker the way a dead Chrome does: an action that never finishes.
    first.ctx.findUploadTab = () => new Promise(() => {});
    shim.dispatch({ action: 'upload-file-only' });
    const second = loadWorker({ shim });
    const reply = await Promise.race([
      second.send('select-posting-channel', { channelId: 'main' }),
      new Promise(r => setTimeout(() => r({ success: false, error: 'timed out' }), 3000)),
    ]);
    assert.equal(reply.success, true, JSON.stringify(reply));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

// ---- draft mode (--mode draft): Save draft step, no schedule, never the Post button ----

test('skipReason in draft mode: no publish time needed, a passed slot is fine, the other guards still apply', () => {
  const now = Date.parse('2030-06-01T00:00:00');
  const past = clipFromQueueItem(item({ scheduled_at: '2030-05-01T10:00' }));
  const noTime = clipFromQueueItem(item({ scheduled_at: '' }));
  assert.equal(skipReason(past, { now }), 'slot_passed_or_too_close');
  assert.equal(skipReason(past, { now, mode: 'draft' }), '');
  assert.equal(skipReason(noTime, { now }), 'no_schedule');
  assert.equal(skipReason(noTime, { now, mode: 'draft' }), '');
  assert.equal(skipReason(clipFromQueueItem(item({ caption: 'ลดราคา 50%' })), { now, mode: 'draft' }), 'price_in_caption');
  assert.equal(skipReason(clipFromQueueItem(item({ caption: 'ใช้ {product_name}' })), { now, mode: 'draft' }), 'placeholder_in_caption');
  assert.equal(skipReason(clipFromQueueItem(item({ tiktok_product_id: null })), { now, mode: 'draft' }), 'no_tiktok_product_id');
});

test('draft run: no schedule in the job, Save draft instead of Post, drafts-page proof, status drafted', async () => {
  let preparedBody;
  let detailsBody;
  const { deps, calls } = fakeDeps({
    onSend: (action, payload) => { if (action === 'prepare-details') detailsBody = payload; },
    replies: {
      'save-draft-only': { success: true, outcome: 'draft_saved', clicked: true, posted: false },
      'verify-draft-content': { success: true, verified: true },
    },
    prepare: (body) => { preparedBody = body; return { ok: true, status: 200, data: { protocol_version: 2, channel_id: 'main', job_id: 'j1', cover_path: null, caption: 'พัดลมพกพา' } }; },
  });
  const res = await runClip(deps, clipFromQueueItem(item()), { mode: 'draft' });
  assert.equal(res.status, 'drafted');
  assert.equal(res.outcome, 'draft_saved');
  assert.equal(res.verified, true);
  assert.equal(preparedBody.schedule_date, null);
  assert.equal(preparedBody.schedule_time, null);
  assert.equal(detailsBody.scheduleMode, false);
  assert.equal(detailsBody.scheduleDate, '');
  assert.ok(!calls.includes('click-post-only'), 'the Post button must never be pressed');
  assert.ok(!calls.includes('reconcile-posting-result'));
  assert.deepEqual(calls.filter(c => !c.startsWith('GET')), [
    'POST /api/tiktok-autopost/prepare', 'claim-posting-job', 'upload-file-only', 'wait-for-upload-only',
    'prepare-details', 'save-draft-only', 'retry-posting-receipt', 'verify-draft-content']);
});

test('draft run: an unverified draft is unknown, and a published outcome in draft mode is refused', async () => {
  const unverified = fakeDeps({ replies: { 'save-draft-only': { success: true, outcome: 'draft_saved' }, 'verify-draft-content': { success: true, verified: false, reason: 'draft_row_not_found' } } });
  const a = await runClip(unverified.deps, clipFromQueueItem(item()), { mode: 'draft' });
  assert.equal(a.status, 'unknown');
  assert.match(a.error, /drafts_page_not_verified/);
  const unconfirmed = fakeDeps({ replies: { 'save-draft-only': { success: true, outcome: 'confirmation_unknown' } } });
  assert.equal((await runClip(unconfirmed.deps, clipFromQueueItem(item()), { mode: 'draft' })).status, 'unknown');
  const published = fakeDeps({ replies: { 'save-draft-only': { success: true, outcome: 'published', posted: true } } });
  const c = await runClip(published.deps, clipFromQueueItem(item()), { mode: 'draft' });
  assert.notEqual(c.status, 'posted');
});

test('schedule mode is unchanged by the draft option (Post button, schedule in the job)', async () => {
  let preparedBody;
  const { deps, calls } = fakeDeps({
    replies: { 'click-post-only': { success: true, outcome: 'scheduled_on_platform' } },
    prepare: (body) => { preparedBody = body; return { ok: true, status: 200, data: { protocol_version: 2, channel_id: 'main', job_id: 'j1', cover_path: null } }; },
  });
  const res = await runClip(deps, clipFromQueueItem(item()), { mode: 'schedule' });
  assert.equal(res.status, 'scheduled');
  assert.equal(preparedBody.schedule_date, '2030-01-01');
  assert.ok(!calls.includes('save-draft-only'));
});

test('batch quota gate: never plans more clips than the live quota allows; full quota stops before any clip', async () => {
  const mk = (n) => Array.from({ length: n }, (_, i) => clipFromQueueItem(item({ id: `q${i}`, export_id: `e${i}` })));
  const run = async (quota, clips, mode = 'schedule') => {
    const { deps, calls, logs } = fakeDeps({ replies: { 'click-post-only': { success: true, outcome: 'scheduled_on_platform' }, 'save-draft-only': { success: true, outcome: 'draft_saved' }, 'verify-draft-content': { success: true, verified: true } } });
    deps.quota = async () => quota;
    deps.verifyOnContentPage = async () => ({ ok: true });
    const summary = await runBatch(deps, { clips, mode, cooldownSec: [0, 0] });
    return { summary, calls, logs };
  };
  // schedule: 28 used -> 2 left -> only the first 2 of 3 run
  let r = await run({ success: true, scheduledCount: 28, remainingSchedule: 2, draftCount: 0, remainingDraft: 30 }, mk(3));
  assert.equal(r.summary.scheduled, 2);
  assert.equal(r.summary.total, 2);
  // draft mode uses the DRAFT counter, not the schedule one
  r = await run({ success: true, scheduledCount: 30, remainingSchedule: 0, draftCount: 29, remainingDraft: 1 }, mk(3), 'draft');
  assert.equal(r.summary.drafted, 1);
  // full quota: nothing is touched
  r = await run({ success: true, scheduledCount: 30, remainingSchedule: 0 }, mk(2));
  assert.equal(r.summary.aborted, 'quota_full_schedule');
  assert.ok(!r.calls.includes('claim-posting-job'));
  r = await run({ success: true, draftCount: 30, remainingDraft: 0 }, mk(2), 'draft');
  assert.equal(r.summary.aborted, 'quota_full_draft');
  // unreadable quota: say so, keep going (the --limit is the guard)
  r = await run({ success: false, error: 'no tab' }, mk(1));
  assert.equal(r.summary.scheduled, 1);
  assert.ok(r.logs.some(([, m]) => /อ่านโควตา TikTok ไม่ได้/.test(m)));
});

test('dry run never asks for the quota (nothing is posted)', async () => {
  const { deps } = fakeDeps();
  let asked = 0;
  deps.quota = async () => { asked += 1; return {}; };
  await runBatch(deps, { clips: [clipFromQueueItem(item())], dryRun: true });
  assert.equal(asked, 0);
});

test('CLI: --mode accepts schedule|draft only', () => {
  assert.equal(parseArgs([]).mode, 'schedule');
  assert.equal(parseArgs(['--mode', 'draft']).mode, 'draft');
  assert.throws(() => parseArgs(['--mode', 'now']), /schedule \| draft/);
});

// ---- R4: conductor safety ----
const { acquireProcessLock } = require('./process_lock');
const { createApi } = require('./api');
const { ClipCancelled } = require('./conductor');

test('R4 a timed-out clip is cancelled: the abandoned run can never send click-post to the next worker', async () => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const sent = [];
  const hang = fakeDeps({ replies: { 'wait-for-upload-only': () => gate }, onSend: action => sent.push(action) });
  hang.deps.recover = async () => {};
  const res = await runClipGuarded(hang.deps, clipFromQueueItem(item()), {}, 30);
  assert.equal(res.status, 'failed');
  assert.equal(res.step, 'timeout');
  release({ success: true });                 // the zombie wait finally returns...
  await new Promise(resolve => setTimeout(resolve, 30));
  assert.ok(!sent.includes('click-post-only'), 'a cancelled run must not press Post');
  assert.ok(!sent.includes('prepare-details'), 'a cancelled run must not continue to later steps');
});

test('R4 a timeout AFTER the post command was sent is unknown (never failed/retried)', async () => {
  const hang = fakeDeps({ replies: { 'click-post-only': () => new Promise(() => {}) } });
  hang.deps.recover = async () => {};
  const res = await runClipGuarded(hang.deps, clipFromQueueItem(item()), {}, 40);
  assert.equal(res.status, 'unknown');
  assert.equal(res.step, 'timeout');
  const batch = fakeDeps({ replies: { 'click-post-only': () => new Promise(() => {}) } });
  batch.deps.recover = async () => {};
  const out = await runBatch(batch.deps, { clips: [clipFromQueueItem(item())], clipBudgetMs: 40, random: () => 0, maxClipAttempts: 2 });
  assert.equal(out.unknown, 1);
  assert.equal(out.failed, 0);
  assert.equal(batch.calls.filter(c => c === 'click-post-only').length, 1, 'never clicked twice');
});

test('R4 startup tells the operator about clips the last run could not confirm', async () => {
  const logs = [];
  const deps = { worker: { send: async () => ({ success: true }) }, sleep: async () => {}, log: (l, m) => logs.push([l, m]), shot: async () => {}, dumpDom: async () => {},
    api: { get: async () => ({ ok: true, status: 200, data: { items: [{ id: 'q9', status: 'confirmation_unknown', hook_title: 'คลิปค้าง' }] } }), post: async () => ({ ok: true, status: 200, data: {} }) } };
  await runBatch(deps, { clips: [], random: () => 0 });
  assert.ok(logs.some(([l, m]) => l === 'warn' && /คลิปค้าง/.test(m) && /ยืนยันผลไม่ได้/.test(m)));
});

test('R4 api calls time out instead of hanging forever', async () => {
  const api = createApi({ timeoutMs: 20, fetchImpl: (url, init) => new Promise((_, reject) => init.signal.addEventListener('abort', () => reject(Object.assign(new Error('aborted'), { name: 'TimeoutError' })))) });
  await assert.rejects(() => api.get('/api/x'), /api_timeout/);
});

test('R4 process lock: a live owner blocks a second conductor, a dead owner is taken over, release only removes our own', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lock-'));
  const file = path.join(dir, 'c.lock');
  const first = acquireProcessLock(file, { pid: 111 });
  assert.equal(first.ok, true);
  const blocked = acquireProcessLock(file, { pid: 222, alive: pid => pid === 111 });
  assert.equal(blocked.ok, false);
  assert.equal(blocked.owner.pid, 111);
  const takeover = acquireProcessLock(file, { pid: 333, alive: () => false });   // owner 111 is dead
  assert.equal(takeover.ok, true);
  first.release();                                  // 111 no longer owns it: the file must stay
  assert.ok(fs.existsSync(file));
  takeover.release();
  assert.ok(!fs.existsSync(file));
  fs.rmSync(dir, { recursive: true, force: true });
});
