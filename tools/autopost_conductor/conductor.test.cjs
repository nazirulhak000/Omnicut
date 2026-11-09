'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { runBatch, runClip, skipReason, clipFromQueueItem, pickClips, FatalError } = require('./conductor');
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
  assert.equal(skipReason(clipFromQueueItem(item({ caption: 'ลด 50% วันนี้' })), { now, allowPriceCaption: true }), '');
  assert.equal(skipReason(clipFromQueueItem(item({ scheduled_at: '' })), { now }), 'no_schedule');
});

test('pickClips keeps only planned/ready items, sorted, limited, with skip reasons', async () => {
  const api = { get: async () => ({ ok: true, data: { items: [
    item({ id: 'b', scheduled_at: '2030-01-02T10:00' }), item({ id: 'a' }),
    item({ id: 'done', status: 'posted' }), item({ id: 'np', tiktok_product_id: '' }),
  ] } }) };
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
