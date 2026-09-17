import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import {
  enqueueBoundedNotification,
  normalizeToastDuration,
} from '../hooks/useToast.js';

const taskContextSource = fs.readFileSync(new URL('../context/TaskContext.jsx', import.meta.url), 'utf8');
const activityCenterSource = fs.readFileSync(new URL('../components/ActivityCenter.jsx', import.meta.url), 'utf8');
const toastSource = fs.readFileSync(new URL('../components/ui/Toast.jsx', import.meta.url), 'utf8');

test('bounded notification queue preserves the visible item and retains latest pending work', () => {
  const current = { id: 'current' };
  const pending = [{ id: 'old-1' }, { id: 'old-2' }, { id: 'old-3' }];

  assert.deepEqual(
    enqueueBoundedNotification([current, ...pending], { id: 'latest' }, 4),
    [current, pending[0], pending[1], { id: 'latest' }],
  );
});

test('toast duration is normalized and retained as an actionable value', () => {
  assert.equal(normalizeToastDuration(1250), 1250);
  assert.equal(normalizeToastDuration(-50), 0);
  assert.equal(normalizeToastDuration('invalid', 2400), 2400);
  assert.match(fs.readFileSync(new URL('../hooks/useToast.js', import.meta.url), 'utf8'), /duration:\s*normalizeToastDuration/);
  assert.match(toastSource, /Number\(duration\)/);
});

test('task polling exposes stale state instead of silently treating backend failure as normal', () => {
  assert.match(taskContextSource, /status:\s*'stale'/);
  assert.match(taskContextSource, /lastSuccessfulAt:\s*prev\.lastSuccessfulAt/);
  assert.match(activityCenterSource, /ข้อมูลกิจกรรมที่แสดงอาจไม่ใช่ข้อมูลล่าสุด/);
});

test('viral milestone polling is throttled and deduplicated while background task polling runs', () => {
  assert.match(taskContextSource, /30_000/);
  assert.match(taskContextSource, /viralMilestonesInFlightRef\.current/);
  assert.match(taskContextSource, /maybeFetchViralMilestones\(\)/);
});

test('activity drawer and notifications expose basic dialog, tab, status, and keyboard semantics', () => {
  assert.match(activityCenterSource, /role="dialog"/);
  assert.match(activityCenterSource, /aria-modal="true"/);
  assert.match(activityCenterSource, /role="tablist"/);
  assert.match(activityCenterSource, /role="tabpanel"/);
  assert.match(activityCenterSource, /event\.key === 'Escape'/);
  assert.match(activityCenterSource, /role=\{isSuccess \? 'status' : 'alert'\}/);
  assert.match(toastSource, /aria-atomic="true"/);
});
