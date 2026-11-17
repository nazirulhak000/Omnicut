import test from 'node:test';
import assert from 'node:assert/strict';
import {
  mapCameraTechnique,
  findFlowClipForBeat,
  DEFAULT_FLOW_ACCOUNTS_FALLBACK,
  getFlowAccounts,
  switchFlowAccount,
  updateFlowAccount,
  toggleAutoFailover,
  openFlowLoginChrome,
  getAngleShotsFlow,
} from './flowUtils.js';

test('mapCameraTechnique correctly maps Thai and English keywords', () => {
  assert.equal(mapCameraTechnique('หมุน 360 รอบสินค้า'), 'orbit');
  assert.equal(mapCameraTechnique('Close up texture โคลสอัพ'), 'macro');
  assert.equal(mapCameraTechnique('ดันกล้องเข้าหา zoom in'), 'dolly_in');
  assert.equal(mapCameraTechnique('เสยมุมต่ำ low angle'), 'reveal');
  assert.equal(mapCameraTechnique('ลอยตัว สโลว์'), 'floating');
  assert.equal(mapCameraTechnique(''), 'orbit');
  assert.equal(mapCameraTechnique('unknown direction'), 'orbit');
});

test('DEFAULT_FLOW_ACCOUNTS_FALLBACK provides 5 valid accounts with correct schema', () => {
  assert.equal(DEFAULT_FLOW_ACCOUNTS_FALLBACK.accounts.length, 5);
  assert.equal(DEFAULT_FLOW_ACCOUNTS_FALLBACK.active_account_id, 'acc_1');
  assert.equal(DEFAULT_FLOW_ACCOUNTS_FALLBACK.auto_failover, true);
  assert.equal(DEFAULT_FLOW_ACCOUNTS_FALLBACK.min_failover_credits, 25);
  assert.equal(DEFAULT_FLOW_ACCOUNTS_FALLBACK.total_pool_credits, 4810);

  const acc1 = DEFAULT_FLOW_ACCOUNTS_FALLBACK.accounts[0];
  assert.equal(acc1.id, 'acc_1');
  assert.equal(acc1.name, 'Google Pro #1');
  assert.equal(acc1.email, 'nazirulhak.000@gmail.com');
  assert.equal(acc1.user_index, 0);
  assert.equal(acc1.credits, 810);
});

test('findFlowClipForBeat finds completed and generating jobs accurately', () => {
  const beat = { beat_index: 0, text: 'Hook shot' };
  const jobsList = [
    {
      id: 'job_1',
      status: 'completed',
      scenes: [{ shot_index: 0, shot_label: 'shot_1_hook' }],
      ingested_files: ['/raw/shot_1_hook.mp4'],
    },
  ];

  const found = findFlowClipForBeat(beat, jobsList);
  assert.ok(found);
  assert.equal(found.status, 'ready');
  assert.equal(found.path, '/raw/shot_1_hook.mp4');

  const beat2 = { beat_index: 1, text: 'Feature shot' };
  const jobsList2 = [
    {
      id: 'job_2',
      status: 'running',
      scenes: [{ shot_index: 1, shot_label: 'shot_2_feature' }],
    },
  ];

  const found2 = findFlowClipForBeat(beat2, jobsList2);
  assert.ok(found2);
  assert.equal(found2.status, 'generating');
  assert.equal(found2.job.id, 'job_2');
});

test('flow accounts API helpers are exported functions', () => {
  assert.equal(typeof getFlowAccounts, 'function');
  assert.equal(typeof switchFlowAccount, 'function');
  assert.equal(typeof updateFlowAccount, 'function');
  assert.equal(typeof toggleAutoFailover, 'function');
  assert.equal(typeof openFlowLoginChrome, 'function');
  assert.equal(typeof getAngleShotsFlow, 'function');
});
