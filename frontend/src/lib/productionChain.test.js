import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CHAIN_TASK_TYPE,
  OPEN_AUTOFILL_KEY,
  chainConfirmText,
  chainFollowUp,
  chainStartError,
  chainTargets,
  consumeScheduleAutofill,
  findProductTask,
  requestScheduleAutofill,
  taskPercent,
} from './productionChain.js';

// The record shape /api/tasks/active returns.
const task = (over = {}) => ({
  id: 't1', type: 'batch_generate_audio', status: 'processing', progress: 0.4,
  step_label: 'กำลังเตรียมเสียง', payload: { product_id: 'p1' }, ...over,
});

test('finds the running task of the open product by the fields the backend sends', () => {
  const tasks = [task({ id: 'other', payload: { product_id: 'p2' } }), task()];

  assert.equal(findProductTask(tasks, 'p1', ['batch_generate_audio'])?.id, 't1');
  assert.equal(findProductTask(tasks, 'p1', ['batch_draft']), null);
  assert.equal(findProductTask(tasks, null, ['batch_generate_audio']), null);
  assert.equal(findProductTask(null, 'p1', ['batch_generate_audio']), null);
});

test('a queued task counts as running and a finished one does not', () => {
  assert.equal(findProductTask([task({ status: 'queued' })], 'p1', ['batch_generate_audio'])?.id, 't1');
  for (const status of ['completed', 'failed', 'cancelled']) {
    assert.equal(findProductTask([task({ status })], 'p1', ['batch_generate_audio']), null);
  }
});

test('the extra check narrows a shared task type', () => {
  const tasks = [
    task({ id: 'render', type: 'batch_render', payload: { product_id: 'p1', is_draft: false } }),
    task({ id: 'draft', type: 'batch_draft', payload: { product_id: 'p1', is_draft: true } }),
  ];
  const isDraft = (t) => t.type === 'batch_draft' || Boolean(t.payload?.is_draft);

  assert.equal(findProductTask(tasks, 'p1', ['batch_draft', 'batch_render'], isDraft)?.id, 'draft');
});

test('progress is a fraction from the backend and a percentage on screen', () => {
  assert.equal(taskPercent(task({ progress: 0.4 })), 40);
  assert.equal(taskPercent(task({ progress: 1.7 })), 100);
  assert.equal(taskPercent(task({ progress: -1 })), 0);
  assert.equal(taskPercent(task({ progress: undefined })), null);
});

const ANGLES = [
  { angle_id: 'new', batch: 1, script_lines: ['สวัสดี'] },
  { angle_id: 'tts_only', batch: 1, tts_lines: ['สวัสดี'] },
  { angle_id: 'no_script', batch: 1, script_lines: ['  '] },
  { angle_id: 'draft', batch: 1, status: 'in_production', project_name: 'proj_a', script_lines: ['x'] },
  { angle_id: 'stale', batch: 1, status: 'in_production', script_lines: ['x'] },
  { angle_id: 'rendered', batch: 1, status: 'rendered', project_name: 'proj_b', script_lines: ['x'] },
  { angle_id: 'posted', batch: 1, status: 'scripted', posted_at: '2026-11-01', script_lines: ['x'] },
  { angle_id: 'lot2_new', batch: 2, script_lines: ['x'] },
  { angle_id: 'lot2_draft', batch: 2, status: 'in_production', project_name: 'proj_c', script_lines: ['x'] },
  { batch: 1, script_lines: ['no id'] },
];

test('counts what each chain would work on across every lot', () => {
  // draft: new, tts_only, stale (no project yet), lot2_new · render: draft, lot2_draft
  assert.deepEqual(chainTargets(ANGLES, 'all'), { draft: 4, render: 2 });
  assert.deepEqual(chainTargets(ANGLES), { draft: 4, render: 2 });
});

test('counts only the chosen lot, and an angle without a lot is lot 1', () => {
  assert.deepEqual(chainTargets(ANGLES, 2), { draft: 1, render: 1 });
  assert.deepEqual(chainTargets([{ angle_id: 'a', script_lines: ['x'] }], 1), { draft: 1, render: 0 });
  assert.deepEqual(chainTargets(null, 1), { draft: 0, render: 0 });
});

test('the confirmation says how many angles and where the chain stops', () => {
  assert.match(chainConfirmText('draft', 3), /สร้างดราฟต์ 3 มุม/);
  assert.match(chainConfirmText('draft', 3), /ตรวจใน Editor ก่อนเรนเดอร์/);
  assert.match(chainConfirmText('render', 2), /เรนเดอร์ดราฟต์ที่ตรวจแล้ว 2 มุม/);
  assert.match(chainConfirmText('render', 2), /ตรวจก่อนบันทึก/);
});

test('a refused start shows the server message, including the busy reply', () => {
  const busy = { response: { data: { detail: { message: 'สินค้านี้มีงานผลิตต่อเนื่องทำอยู่แล้ว', task_id: 't9' } } } };

  assert.equal(chainStartError(busy), 'สินค้านี้มีงานผลิตต่อเนื่องทำอยู่แล้ว');
  assert.equal(chainStartError({ response: { data: { detail: 'ไม่พบสินค้า' } } }), 'ไม่พบสินค้า');
  assert.equal(chainStartError(new Error('Network Error')), 'Network Error');
});

const chain = (over = {}) => task({ type: CHAIN_TASK_TYPE, status: 'completed', ...over });

test('a render chain that produced clips opens the schedule', () => {
  const done = chain({ result: { kind: 'render', rendered: [{ angle_id: 'a' }, { angle_id: 'b' }] } });

  assert.deepEqual(chainFollowUp(done), { refresh: true, openSchedule: true, rendered: 2 });
});

test('every other ending refreshes the product and stays on the page', () => {
  const stay = { refresh: true, openSchedule: false, rendered: 0 };

  assert.deepEqual(chainFollowUp(chain({ result: { kind: 'draft', drafts: { created: [{}] } } })), stay);
  assert.deepEqual(chainFollowUp(chain({ result: { kind: 'render', rendered: [] } })), stay);
  assert.deepEqual(chainFollowUp(chain({ status: 'failed', result: null, error: 'สแกนฉากล้ม' })), stay);
  assert.deepEqual(chainFollowUp(chain({ status: 'cancelled', result: null })), stay);
});

test('a chain that is still running, or another task, needs no follow-up', () => {
  const none = { refresh: false, openSchedule: false, rendered: 0 };

  assert.deepEqual(chainFollowUp(chain({ status: 'processing' })), none);
  assert.deepEqual(chainFollowUp(task({ status: 'completed' })), none);
  assert.deepEqual(chainFollowUp(null), none);
});

const memoryStorage = () => {
  const data = new Map();
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
};

test('the schedule opens its auto-fill preview once per request', () => {
  const storage = memoryStorage();

  assert.equal(consumeScheduleAutofill(storage), false);
  requestScheduleAutofill(storage);
  assert.equal(storage.getItem(OPEN_AUTOFILL_KEY), '1');
  assert.equal(consumeScheduleAutofill(storage), true);
  assert.equal(consumeScheduleAutofill(storage), false);
});

test('blocked storage never throws -- the owner opens the preview by hand', () => {
  const blocked = {
    getItem() { throw new Error('denied'); },
    setItem() { throw new Error('denied'); },
    removeItem() { throw new Error('denied'); },
  };

  assert.doesNotThrow(() => requestScheduleAutofill(blocked));
  assert.equal(consumeScheduleAutofill(blocked), false);
  assert.equal(consumeScheduleAutofill(undefined), false);
});
