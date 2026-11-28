'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  clipFromQueueItem,
  isDueNowItem,
  skipReason,
  pickClips,
  runClip,
  runHybridBatch,
} = require('./conductor');
const { createApi, listChannels } = require('./api');
const { parseArgs, writeStateAtomic } = require('./run');

const mkItem = (over = {}) => ({
  id: 'q1',
  status: 'planned',
  export_id: 'e1',
  video_path: 'a.mp4',
  scheduled_at: '2026-11-28T10:10',
  tiktok_product_id: '123',
  caption: 'พัดลมพกพาเย็นมาก',
  hashtags: '#fan',
  hook_title: 'hook',
  ...over,
});

function fakeDeps({ replies = {}, prepare, quota, onSend } = {}) {
  const calls = [];
  const preparedPayloads = [];
  const worker = {
    send: async (action, payload) => {
      calls.push(action);
      onSend?.(action, payload);
      const r = replies[action];
      if (r instanceof Error) throw r;
      return typeof r === 'function' ? r(payload) : (r ?? { success: true });
    },
  };
  const api = {
    post: async (route, body) => {
      calls.push('POST ' + route);
      if (route.endsWith('/prepare')) {
        preparedPayloads.push(body);
        return prepare
          ? prepare(body)
          : { ok: true, status: 200, data: { protocol_version: 2, channel_id: 'main', job_id: `job_${body.queue_id}`, cover_path: 'c.jpg' } };
      }
      return { ok: true, status: 200, data: {} };
    },
    get: async (route) => {
      calls.push('GET ' + route);
      return { ok: false, status: 404, data: {} };
    },
  };
  const logs = [];
  return {
    calls,
    preparedPayloads,
    logs,
    deps: {
      worker,
      api,
      quota,
      sleep: async () => {},
      log: (l, m) => logs.push([l, m]),
      shot: async () => {},
      dumpDom: async () => {},
    },
  };
}

test('CLI: parseArgs supports --mode due_now|hybrid and --all-channels', () => {
  assert.equal(parseArgs(['--mode', 'due_now']).mode, 'due_now');
  assert.equal(parseArgs(['--mode', 'hybrid']).mode, 'hybrid');
  assert.equal(parseArgs(['--all-channels']).allChannels, true);
  assert.equal(parseArgs(['--channel', 'ch2']).channel, 'ch2');
  assert.equal(parseArgs(['--channel', 'ch2']).allChannels, false);
  assert.throws(() => parseArgs(['--mode', 'invalid']), /due_now \| hybrid/);
});

test('skipReason: due_now and intent=post_now are not skipped for <15m lead time', () => {
  const now = Date.parse('2026-11-28T10:00:00+07:00');
  const soon = clipFromQueueItem(mkItem({ scheduled_at: '2026-11-28T10:05' }));
  const slightlyPast = clipFromQueueItem(mkItem({ scheduled_at: '2026-11-28T09:57' }));
  const postNowNoSlot = clipFromQueueItem(mkItem({ scheduled_at: '', intent: 'post_now' }));

  assert.equal(skipReason(soon, { now, mode: 'schedule' }), 'slot_passed_or_too_close');
  assert.equal(skipReason(soon, { now, mode: 'due_now' }), '');
  assert.equal(skipReason(slightlyPast, { now, mode: 'due_now' }), '');
  assert.equal(skipReason(postNowNoSlot, { now, mode: 'schedule' }), '');

  // Other guards still apply
  assert.equal(skipReason(clipFromQueueItem(mkItem({ tiktok_product_id: null, intent: 'post_now' })), { now, mode: 'due_now' }), 'no_tiktok_product_id');
  assert.equal(skipReason(clipFromQueueItem(mkItem({ caption: 'ลดราคา 50%', intent: 'post_now' })), { now, mode: 'due_now' }), 'price_in_caption');
});

test('isDueNowItem & pickClips(due_now): selects [-5m, +30m] and intent=post_now only', async () => {
  const now = Date.parse('2026-11-28T10:00:00+07:00');
  const items = [
    mkItem({ id: 'too_old', scheduled_at: '2026-11-28T09:50' }),
    mkItem({ id: 'in_past_3m', status: 'ready_for_extension', scheduled_at: '2026-11-28T09:57' }),
    mkItem({ id: 'in_next_20m', scheduled_at: '2026-11-28T10:20' }),
    mkItem({ id: 'too_far', scheduled_at: '2026-11-28T10:45' }),
    mkItem({ id: 'explicit_now', scheduled_at: '2026-11-29T12:00', intent: 'post_now' }),
  ];
  assert.equal(isDueNowItem(clipFromQueueItem(items[0]), now), false);
  assert.equal(isDueNowItem(clipFromQueueItem(items[1]), now), true);
  assert.equal(isDueNowItem(clipFromQueueItem(items[2]), now), true);
  assert.equal(isDueNowItem(clipFromQueueItem(items[3]), now), false);
  assert.equal(isDueNowItem(clipFromQueueItem(items[4]), now), true);

  const api = {
    get: async (route) => (route.includes('schedule-queue') ? { ok: true, data: { items } } : { ok: false }),
  };
  const { clips, skipped } = await pickClips(api, { now, mode: 'due_now', limit: 10 });
  assert.deepEqual(clips.map(c => c.id), ['in_past_3m', 'in_next_20m', 'explicit_now']);
  assert.deepEqual(skipped.map(s => [s.id, s.reason]), [
    ['too_old', 'not_due_now'],
    ['too_far', 'not_due_now'],
  ]);
});

test('runClip in due_now mode prepares intent=post_now, scheduleMode=false, and publishes', async () => {
  let detailsPayload = null;
  let verifiedClip = null;
  const { deps, preparedPayloads } = fakeDeps({
    onSend: (action, payload) => {
      if (action === 'prepare-details') detailsPayload = payload;
    },
    replies: {
      'click-post-only': { success: true, outcome: 'published' },
    },
  });
  deps.verifyOnContentPage = async (clip) => {
    verifiedClip = clip;
    return { ok: true };
  };
  const res = await runClip(deps, clipFromQueueItem(mkItem({ scheduled_at: '2026-11-28T10:05' })), { mode: 'due_now' });
  assert.equal(res.status, 'posted');
  assert.equal(preparedPayloads[0].intent, 'post_now');
  assert.equal(preparedPayloads[0].schedule_date, null);
  assert.equal(preparedPayloads[0].schedule_time, null);
  assert.equal(detailsPayload.scheduleMode, false);
  assert.equal(detailsPayload.scheduleDate, '');
  assert.equal(verifiedClip.schedule_date, '');
  assert.equal(verifiedClip.schedule_time, '');
});

test('runHybridBatch: runs due_now (post_now) first, then schedule when quota < 30', async () => {
  const now = Date.parse('2026-11-28T10:00:00+07:00');
  const queue = [
    mkItem({ id: 'sched_1', export_id: 'e_s1', scheduled_at: '2026-11-29T10:00' }),
    mkItem({ id: 'due_1', export_id: 'e_d1', scheduled_at: '2026-11-28T10:05' }),
  ];
  const { deps, preparedPayloads } = fakeDeps({
    replies: {
      'click-post-only': () => (preparedPayloads.length === 1
        ? { success: true, outcome: 'published' }
        : { success: true, outcome: 'scheduled_on_platform' }),
    },
    quota: async () => ({ success: true, scheduledCount: 10, remainingSchedule: 20 }),
  });
  deps.api.get = async (route) => (route.includes('schedule-queue') ? { ok: true, data: { items: queue } } : { ok: false });

  const summary = await runHybridBatch(deps, { now, limit: 5, cooldownSec: [0, 0] });
  assert.equal(summary.mode, 'hybrid');
  assert.equal(summary.posted, 1);
  assert.equal(summary.scheduled, 1);
  assert.deepEqual(preparedPayloads.map(p => [p.queue_id, p.intent]), [
    ['due_1', 'post_now'],
    ['sched_1', 'schedule'],
  ]);
});

test('runHybridBatch: skips schedule phase when TikTok scheduled quota is 30/30', async () => {
  const now = Date.parse('2026-11-28T10:00:00+07:00');
  const queue = [
    mkItem({ id: 'sched_1', export_id: 'e_s1', scheduled_at: '2026-11-29T10:00' }),
    mkItem({ id: 'due_1', export_id: 'e_d1', scheduled_at: '2026-11-28T10:05' }),
  ];
  const { deps, preparedPayloads } = fakeDeps({
    replies: { 'click-post-only': { success: true, outcome: 'published' } },
    quota: async () => ({ success: true, scheduledCount: 30, remainingSchedule: 0 }),
  });
  deps.api.get = async (route) => (route.includes('schedule-queue') ? { ok: true, data: { items: queue } } : { ok: false });

  const summary = await runHybridBatch(deps, { now, limit: 5, cooldownSec: [0, 0] });
  assert.equal(summary.posted, 1);
  assert.equal(summary.scheduled, 0);
  assert.deepEqual(preparedPayloads.map(p => [p.queue_id, p.intent]), [['due_1', 'post_now']]);
});

test('multi-channel: listChannels filters active channels and createApi sends X-OmniCut-Channel', async () => {
  const seenHeaders = [];
  const api = createApi({
    apiKey: 'k1',
    channelId: 'ch_b',
    fetchImpl: async (url, init) => {
      seenHeaders.push(init.headers['X-OmniCut-Channel']);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          channels: [
            { id: 'main', enabled: true },
            { id: 'ch_b', is_active: true },
            { id: 'disabled_ch', enabled: false },
          ],
        }),
      };
    },
  });
  const channels = await listChannels(api);
  assert.deepEqual(channels, ['main', 'ch_b']);
  assert.equal(seenHeaders[0], 'ch_b');

  const fallbackApi = { get: async () => ({ ok: false, status: 500, data: {} }) };
  assert.deepEqual(await listChannels(fallbackApi), ['main']);
});

test('writeStateAtomic: writes live status schema atomically and merges updates', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'conductor-state-'));
  const file = path.join(dir, 'state.json');
  try {
    const s1 = writeStateAtomic(file, {
      running: true,
      pid: 1234,
      mode: 'hybrid',
      channel_id: 'main',
      current_queue_id: 'q1',
      last_run_at: '2026-11-28T10:00:00Z',
      chrome_cdp_ok: true,
    });
    assert.equal(s1.running, true);
    assert.equal(s1.current_queue_id, 'q1');

    const s2 = writeStateAtomic(file, {
      running: false,
      pid: null,
      current_queue_id: null,
      last_finished_at: '2026-11-28T10:02:00Z',
      last_result: { posted: 1, scheduled: 0 },
    });
    assert.equal(s2.running, false);
    assert.equal(s2.mode, 'hybrid');
    assert.equal(s2.last_run_at, '2026-11-28T10:00:00Z');
    assert.deepEqual(s2.last_result, { posted: 1, scheduled: 0 });
    assert.equal(s2.chrome_cdp_ok, true);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
