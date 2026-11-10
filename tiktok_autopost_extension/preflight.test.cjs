const { test } = require('node:test');
const assert = require('node:assert/strict');
const { evaluatePreflight, formatPreflight, handleOf } = require('./preflight.js');

const good = () => ({
  backend: { ok: true, status: 200, protocol_version: 2 },
  channel: { id: 'main', handle: '@mainuser' },
  worker: { success: true, url: 'https://www.tiktok.com/tiktokstudio/upload', loggedIn: true, uploadInput: true, handle: '@MainUser', viewport: { w: 1440, h: 900 },
    quota: { remainingSchedule: 12, remainingDraft: 30 } },
  mode: 'schedule_only', clipCount: 5,
});
const ids = (list) => list.map((c) => c.id);

test('everything fine -> ok with no blockers', () => {
  const r = evaluatePreflight(good());
  assert.equal(r.ok, true);
  assert.deepEqual(r.blockers, []);
  assert.deepEqual(r.warnings, []);
});

test('backend down, wrong key or wrong protocol blocks', () => {
  for (const [backend, text] of [[{ ok: false, status: 401 }, /API key/], [{ ok: false, error: 'fetch failed' }, /fetch failed/], [{ ok: true, status: 200, protocol_version: 1 }, /protocol 1/]]) {
    const r = evaluatePreflight({ ...good(), backend });
    assert.equal(r.ok, false);
    assert.match(r.blockers.find((c) => c.id === 'backend').detail, text);
  }
});

test('page unreachable, not logged in, no upload input all block', () => {
  assert.deepEqual(ids(evaluatePreflight({ ...good(), worker: { success: false, error: 'ไม่พบแท็บ' } }).blockers), ['page']);
  assert.deepEqual(ids(evaluatePreflight({ ...good(), worker: { ...good().worker, loggedIn: false } }).blockers), ['login']);
  assert.deepEqual(ids(evaluatePreflight({ ...good(), worker: { ...good().worker, uploadInput: false } }).blockers), ['upload_input']);
});

test('the logged-in account must be the channel account; unreadable is a warning, a different account blocks', () => {
  assert.equal(evaluatePreflight({ ...good(), worker: { ...good().worker, handle: '@someone_else' } }).ok, false);
  const unreadable = evaluatePreflight({ ...good(), worker: { ...good().worker, handle: null } });
  assert.equal(unreadable.ok, true);
  assert.deepEqual(ids(unreadable.warnings), ['account']);
  assert.deepEqual(ids(evaluatePreflight({ ...good(), channel: { id: 'main' } }).warnings), ['account']);
  assert.equal(handleOf('https://www.tiktok.com/@MainUser'), '@mainuser');
});

test('quota: full blocks for the mode in use only; unknown and too-few warn', () => {
  const full = { ...good(), worker: { ...good().worker, quota: { remainingSchedule: 0, remainingDraft: 30 } } };
  assert.equal(evaluatePreflight(full).ok, false);
  assert.equal(evaluatePreflight({ ...full, mode: 'draft_only' }).ok, true);
  const unknown = evaluatePreflight({ ...good(), worker: { ...good().worker, quota: null } });
  assert.equal(unknown.ok, true);
  assert.deepEqual(ids(unknown.warnings), ['quota']);
  const few = evaluatePreflight({ ...good(), clipCount: 20 });
  assert.equal(few.ok, true);
  assert.match(few.warnings[0].detail, /12 คลิปแรก/);
});

test('narrow window is only a warning; formatPreflight lists every check', () => {
  const r = evaluatePreflight({ ...good(), worker: { ...good().worker, viewport: { w: 700, h: 800 } } });
  assert.equal(r.ok, true);
  assert.deepEqual(ids(r.warnings), ['viewport']);
  assert.match(formatPreflight(r), /เตือน · ขนาดหน้าต่าง/);
  assert.equal(formatPreflight(r).split('\n').length, r.checks.length);
});

test('publishing a draft now needs no schedule slot, so a full schedule quota is not a blocker for it', () => {
  const full = { ...good(), mode: 'publish_now', worker: { ...good().worker, quota: { remainingSchedule: 0, remainingDraft: 0 } } };
  const r = evaluatePreflight(full);
  assert.equal(r.ok, true);
  assert.match(r.checks.find((c) => c.id === 'quota').detail, /ไม่ใช้ช่องตั้งเวลา/);
  assert.equal(evaluatePreflight({ ...full, mode: 'schedule_only' }).ok, false);   // a scheduled publication still needs a free slot
});
