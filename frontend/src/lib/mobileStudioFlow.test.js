import test from 'node:test';
import assert from 'node:assert/strict';
import { angleVideoUrl, catalogPageParams, filmingReturnUrl, filmingUrl, findResumableMobileTask, footageKey, isAlreadyPostedError, isAnglePosted, isNoResponseError, mergeCatalogPage, MOBILE_CATALOG_PAGE_SIZE, pollMobileTask, progressPercent } from './mobileStudioFlow.js';

const flush = () => new Promise(resolve => setImmediate(resolve));
function scheduler() {
  const pending = [];
  return { pending, schedule: fn => { pending.push(fn); return fn; }, cancel: fn => { const index = pending.indexOf(fn); if (index >= 0) pending.splice(index, 1); } };
}

test('fractional progress displays bounded whole percent', () => {
  assert.equal(progressPercent(0.53), 53);
  assert.equal(progressPercent(3), 100);
  assert.equal(progressPercent(-1), 0);
  assert.equal(progressPercent('bad'), 0);
});

test('filming round trip preserves selected product, angle and session', () => {
  const outgoing = filmingUrl('a/b?', 'prod space', 'มุม 1');
  const incoming = filmingReturnUrl(new URL(outgoing, 'https://local').search);
  const params = new URL(incoming, 'https://local').searchParams;
  assert.equal(params.get('mobile_session'), 'a/b?');
  assert.equal(params.get('product'), 'prod space');
  assert.equal(params.get('angle'), 'มุม 1');
  assert.equal(params.get('mode'), 'mobile');
  assert.equal(params.get('channel'), 'main');
  assert.equal(filmingReturnUrl('?film=1&session=desktop'), null);
});

test('a filming link opened in another tab retains the originating secondary channel', () => {
  const outgoing = filmingUrl('session-second', 'product-second', 'angle-second', 'second');
  const params = new URL(filmingReturnUrl(new URL(outgoing, 'https://local').search), 'https://local').searchParams;
  assert.equal(params.get('channel'), 'second');
  assert.equal(params.get('mobile_session'), 'session-second');
  assert.throws(() => filmingUrl('session', null, null, '../main'), { code: 'channel_scope_invalid' });
});

test('polling waits for response, stops on terminal reply, and cancels pending schedule', async () => {
  const timers = scheduler();
  let resolve;
  let calls = 0;
  const replies = [];
  const stop = pollMobileTask({ ...timers, fetchTask: () => { calls++; return new Promise(r => { resolve = r; }); }, onTask: task => { replies.push(task); return task.status !== 'completed'; }, onError: assert.fail });
  assert.equal(calls, 1);
  assert.equal(timers.pending.length, 0);
  resolve({ task: { status: 'processing' } });
  await flush();
  assert.equal(timers.pending.length, 1);
  const second = timers.pending.shift()();
  assert.equal(calls, 2);
  assert.equal(timers.pending.length, 0);
  resolve({ task: { status: 'completed' } });
  await second;
  assert.equal(replies.length, 2);
  assert.equal(timers.pending.length, 0);
  stop();
});

test('unmount or changed task ignores in-flight stale reply', async () => {
  const timers = scheduler();
  let resolve;
  const stop = pollMobileTask({ ...timers, fetchTask: () => new Promise(r => { resolve = r; }), onTask: assert.fail, onError: assert.fail });
  stop();
  resolve({ task: { status: 'completed' } });
  await flush();
  assert.equal(timers.pending.length, 0);
});

test('temporary failure recovers, repeated disconnection pauses without a new render', async () => {
  const timers = scheduler();
  let calls = 0;
  const failures = [];
  const stop = pollMobileTask({ ...timers, fetchTask: async () => { calls++; throw new Error('offline'); }, onTask: assert.fail, onError: error => failures.push(error) });
  await flush();
  await timers.pending.shift()();
  await timers.pending.shift()();
  assert.equal(calls, 3);
  assert.equal(failures.length, 1);
  assert.equal(timers.pending.length, 0);
  stop();
});

test('missing task pauses immediately', async () => {
  const timers = scheduler();
  const failures = [];
  pollMobileTask({ ...timers, fetchTask: async () => { throw { response: { status: 404 } }; }, onTask: assert.fail, onError: error => failures.push(error) });
  await flush();
  assert.equal(failures.length, 1);
  assert.equal(timers.pending.length, 0);
});

test('catalog pagination keeps a stable page size and merges pages without duplicates', () => {
  assert.equal(MOBILE_CATALOG_PAGE_SIZE, 20);
  assert.deepEqual(catalogPageParams(2), { page: 2, page_size: 20 });

  const loaded = [{ id: 'a' }, { id: 'b' }];
  const merged = mergeCatalogPage(loaded, [{ id: 'b' }, { id: 'c' }]);
  assert.deepEqual(merged.map(p => p.id), ['a', 'b', 'c']);
  assert.deepEqual(loaded.map(p => p.id), ['a', 'b']); // the loaded list is never mutated
  assert.deepEqual(mergeCatalogPage(loaded, null).map(p => p.id), ['a', 'b']);
  // items without an id cannot be deduped, so they are appended as-is
  assert.equal(mergeCatalogPage([], [{ name: 'no id' }]).length, 1);
});


test('angle DTO exposes the rendered clip as rendered_video_url (legacy video_url fallback)', () => {
  assert.equal(angleVideoUrl({ rendered_video_url: '/media/a.mp4', video_url: '/old.mp4' }), '/media/a.mp4');
  assert.equal(angleVideoUrl({ video_url: '/old.mp4' }), '/old.mp4');
  assert.equal(angleVideoUrl({}), null);
  assert.equal(angleVideoUrl(null), null);
});

test('posted state comes only from backend status or posted_at', () => {
  assert.equal(isAnglePosted({ status: 'posted' }), true);
  assert.equal(isAnglePosted({ status: 'rendered', posted_at: '2026-10-30T10:00:00' }), true);
  assert.equal(isAnglePosted({ status: 'rendered', is_rendered: true }), false);
  assert.equal(isAnglePosted(null), false);
});

test('footage key isolates product+angle pairs', () => {
  assert.equal(footageKey('p1', 'a1'), 'p1:a1');
  assert.notEqual(footageKey('p1', 'a1'), footageKey('p1', 'a2'));
  assert.equal(footageKey('p1', null), 'p1:quick_take');
  assert.equal(footageKey(null, 'a1'), null);
});

test('resume picks the live mobile render for the remembered angle only', () => {
  const tasks = [
    { id: 'done', type: 'mobile_auto_assemble_render', status: 'completed', payload: { product_id: 'p1', angle_id: 'a1' } },
    { id: 'other', type: 'render', status: 'processing', payload: { product_id: 'p1', angle_id: 'a1' } },
    { id: 'p2', type: 'mobile_auto_assemble_render', status: 'processing', payload: { product_id: 'p2', angle_id: 'b1' } },
    { id: 'live', type: 'mobile_auto_assemble_render', status: 'queued', payload: { product_id: 'p1', angle_id: 'a1' } },
  ];
  assert.equal(findResumableMobileTask(tasks, { productId: 'p1', angleId: 'a1' }).id, 'live');
  assert.equal(findResumableMobileTask(tasks, { productId: 'p9', angleId: 'zz' }), null);
  assert.equal(findResumableMobileTask(tasks).id, 'p2');
  assert.equal(findResumableMobileTask(null), null);
});

test('mark-posted treats already-posted and lost-reply retry 404 as success, nothing else', () => {
  const err = (status, detail) => ({ response: { status, data: { detail } } });
  assert.equal(isAlreadyPostedError(err(409, 'already posted')), true);
  assert.equal(isAlreadyPostedError(err(409, 'ไม่พบ export_id ที่ระบุ จึงหยุดการโพสต์เพื่อป้องกันการเลือกคลิปผิดตัว')), false);
  assert.equal(isAlreadyPostedError(err(404, 'ไม่พบไฟล์: a.mp4')), false);
  assert.equal(isAlreadyPostedError(err(404, 'ไม่พบไฟล์: a.mp4'), { previousAttemptLost: true }), true);
  assert.equal(isAlreadyPostedError(err(500, 'boom'), { previousAttemptLost: true }), false);
  assert.equal(isNoResponseError(new Error('Network Error')), true);
  assert.equal(isNoResponseError(err(500, 'x')), false);
});
