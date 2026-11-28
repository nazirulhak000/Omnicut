import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import {
  buildDayColumns,
  canDragQueueItem,
  computeBoardSummary,
  formatThaiDayHeader,
  summarizeColumnStatuses,
} from './dailyQueueBoard.js';

test('formatThaiDayHeader labels today, tomorrow, and other dates in Asia/Bangkok', () => {
  const today = formatThaiDayHeader('2026-11-28', '2026-11-28');
  assert.equal(today.isToday, true);
  assert.equal(today.isTomorrow, false);
  assert.ok(today.title.startsWith('วันนี้ · '));

  const tomorrow = formatThaiDayHeader('2026-11-29', '2026-11-28');
  assert.equal(tomorrow.isTomorrow, true);
  assert.ok(tomorrow.title.startsWith('พรุ่งนี้ · '));

  const future = formatThaiDayHeader('2026-12-01', '2026-11-28');
  assert.equal(future.isToday, false);
  assert.equal(future.isPast, false);
});

test('buildDayColumns builds 7/14/all ranges, sorts cards ascending, and gates overdue past days', () => {
  const queue = [
    { id: 'past-unposted', scheduled_at: '2026-11-26T09:00:00+07:00', status: 'planned' },
    { id: 'past-posted', scheduled_at: '2026-11-25T09:00:00+07:00', status: 'posted' },
    { id: 'today-late', scheduled_at: '2026-11-28T19:00:00+07:00', status: 'planned' },
    { id: 'today-early', scheduled_at: '2026-11-28T06:30:00+07:00', status: 'scheduled_on_platform' },
    { id: 'day-10', scheduled_at: '2026-12-07T12:00:00+07:00', status: 'planned' },
  ];

  const cols7 = buildDayColumns(queue, { rangeDays: 7, includeOverdue: false, todayKey: '2026-11-28' });
  assert.equal(cols7.length, 7);
  assert.equal(cols7[0].dateKey, '2026-11-28');
  assert.deepEqual(cols7[0].items.map((x) => x.id), ['today-early', 'today-late']);

  const colsWithOverdue = buildDayColumns(queue, { rangeDays: 7, includeOverdue: true, todayKey: '2026-11-28' });
  assert.equal(colsWithOverdue[0].dateKey, '2026-11-26');
  assert.equal(colsWithOverdue.some((c) => c.dateKey === '2026-11-25'), false);

  const cols14 = buildDayColumns(queue, { rangeDays: 14, includeOverdue: false, todayKey: '2026-11-28' });
  assert.equal(cols14.length, 14);
  assert.equal(cols14[9].items.length, 1);

  const colsAll = buildDayColumns(queue, { rangeDays: 'all', includeOverdue: false, todayKey: '2026-11-28' });
  assert.equal(colsAll.length, 10);
  assert.equal(colsAll[9].dateKey, '2026-12-07');
});

test('canDragQueueItem allows only planned and failed items', () => {
  assert.equal(canDragQueueItem({ status: 'planned' }), true);
  assert.equal(canDragQueueItem({ status: 'failed' }), true);
  assert.equal(canDragQueueItem({ status: 'scheduled_on_platform' }), false);
  assert.equal(canDragQueueItem({ status: 'posted' }), false);
});

test('summarizeColumnStatuses and computeBoardSummary compute counts and next slot accurately', () => {
  const counts = summarizeColumnStatuses([
    { status: 'posted' },
    { status: 'scheduled_on_platform' },
    { status: 'ready_for_extension' },
    { status: 'planned' },
    { status: 'failed' },
  ]);
  assert.deepEqual(counts, {
    posted: 1,
    scheduled_on_platform: 1,
    ready: 1,
    planned: 1,
    issue: 1,
  });

  const nowMs = new Date('2026-11-28T08:00:00+07:00').getTime();
  const summary = computeBoardSummary(
    [
      { id: '1', scheduled_at: '2026-11-27T09:00:00+07:00', status: 'planned' },
      { id: '2', scheduled_at: '2026-11-28T06:30:00+07:00', status: 'posted' },
      { id: '3', scheduled_at: '2026-11-28T12:30:00+07:00', status: 'scheduled_on_platform' },
      { id: '4', scheduled_at: '2026-11-29T09:00:00+07:00', status: 'planned' },
    ],
    { queue_counts: { scheduled_on_platform: 14 }, tiktok_schedule_quota_max: 30 },
    '2026-11-28',
    nowMs,
  );
  assert.equal(summary.todayCount, 2);
  assert.equal(summary.nextSlotTime, '12:30');
  assert.equal(summary.scheduledQuotaUsed, 14);
  assert.equal(summary.scheduledQuotaMax, 30);
  assert.equal(summary.overdueCount, 1);
});

test('DailyQueueBoard component follows Emil design system and multi-channel contracts', () => {
  const boardPath = path.resolve(process.cwd(), 'src/components/DailyQueueBoard.jsx');
  const source = fs.readFileSync(boardPath, 'utf8');
  assert.ok(!source.includes('transition-all'), 'DailyQueueBoard must not use transition-all');
  assert.ok(source.includes('tabular-nums'), 'DailyQueueBoard must use tabular-nums');
  assert.ok(source.includes('useChannel()'), 'DailyQueueBoard must be multi-channel aware');
  assert.ok(source.includes('visibilityState'), 'DailyQueueBoard must pause polling when hidden');
  assert.ok(source.includes("intent: 'post_now'"), 'DailyQueueBoard must support post_now intent');
});
