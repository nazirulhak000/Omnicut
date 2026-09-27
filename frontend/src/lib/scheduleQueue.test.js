import test from 'node:test';
import assert from 'node:assert/strict';
import { addDays, buildScheduleIso, estimateQueueCoverage, groupScheduleItems, mergeScheduleDraft, nextTemplateSlotAfterLatest, templateForWeek, templateSlots, weekStartForDate } from './scheduleQueue.js';
import { scheduleTimeOptions, snapTimeToFiveMinutes } from './scheduleQueue.js';

test('schedule times use five-minute increments', () => {
  assert.equal(snapTimeToFiveMinutes('10:02'), '10:00');
  assert.equal(snapTimeToFiveMinutes('10:03'), '10:05');
  assert.equal(scheduleTimeOptions().length, 288);
  assert.equal(buildScheduleIso('2026-09-10', '10:03'), '2026-09-10T10:05:00+07:00');
});

test('agenda groups and sorts by scheduled timestamp', () => {
  const grouped = groupScheduleItems([
    { id: 'b', scheduled_at: '2026-09-11T08:30:00+07:00' },
    { id: 'a', scheduled_at: '2026-09-10T18:00:00+07:00' },
    { id: 'c', scheduled_at: '2026-09-10T08:30:00+07:00' },
  ]);
  assert.deepEqual(Object.keys(grouped), ['2026-09-10', '2026-09-11']);
  assert.deepEqual(grouped['2026-09-10'].map((item) => item.id), ['c', 'a']);
});

test('weekly template helpers use Monday boundaries and preserve flexible slots', () => {
  assert.equal(weekStartForDate('2026-09-10'), '2026-09-07');
  assert.equal(addDays('2026-09-07', 6), '2026-09-13');
  const template = templateForWeek({ days: { '0': { enabled: false, times: ['20:00', '07:00', '16:00', '12:00', '10:00'] } } }, '2026-09-07');
  assert.equal(template.days['0'].enabled, false);
  assert.deepEqual(template.days['0'].times, ['07:00', '10:00', '12:00', '16:00', '20:00']);
  assert.deepEqual(template.days['1'].times, ['09:00', '12:30', '16:00', '19:00', '21:30']);

  const custom = templateForWeek({ days: { '0': { enabled: true, times: ['08:00', '18:00'] } } }, '2026-09-07');
  assert.deepEqual(custom.days['0'].times, ['08:00', '18:00']);
});

test('schedule field edits retain the latest date and time together', () => {
  let draft = { date: '2026-09-08', time: '12:30' };
  draft = mergeScheduleDraft(draft, 'date', '2026-09-12');
  draft = mergeScheduleDraft(draft, 'time', '21:30');
  assert.deepEqual(draft, { date: '2026-09-12', time: '21:30' });
});

test('requeue defaults to the next empty slot from the weekly template', () => {
  const template = { days: Object.fromEntries(Array.from({ length: 7 }, (_, index) => [String(index), { enabled: true, times: ['12:00', '19:30', '21:00'] }])) };
  const queue = [
    { status: 'posted', scheduled_at: '2026-09-20T21:00:00+07:00' },
    { status: 'planned', scheduled_at: '2026-09-08T19:30:00+07:00' },
    { status: 'planned', scheduled_at: '2026-09-08T21:00:00+07:00' },
  ];
  assert.deepEqual(nextTemplateSlotAfterLatest(queue, { '2026-09-07': template }, new Date('2026-09-07T10:00:00+07:00')), { date: '2026-09-09', time: '12:00' });
  assert.equal(nextTemplateSlotAfterLatest(queue, {}, new Date('2026-09-07T10:00:00+07:00')), null);
});

test('weekly calendar generates 7 consecutive days starting from Monday', () => {
  const monday = weekStartForDate('2026-09-12');
  assert.equal(monday, '2026-09-07');
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i));
  assert.equal(days.length, 7);
  assert.equal(days[0], '2026-09-07');
  assert.equal(days[6], '2026-09-13');
  assert.equal(addDays(monday, -7), '2026-08-31');
  assert.equal(addDays(monday, 7), '2026-09-14');
});

test('template slots stay inside the selected date range', () => {
  const template = { default: { days: Object.fromEntries(Array.from({ length: 7 }, (_, index) => [String(index), { enabled: true, times: ['09:00'] }])) } };
  const slots = templateSlots('2026-09-17', '2026-09-17', template, new Date('2026-09-17T23:00:00+07:00'));
  assert.deepEqual(slots, []);
});

test('template slots ignore a latest queue timestamp outside the selected range', () => {
  const template = { default: { days: Object.fromEntries(Array.from({ length: 7 }, (_, index) => [String(index), { enabled: true, times: ['09:00', '12:30'] }])) } };
  const slots = templateSlots('2030-01-07', '2030-01-07', template, new Date('2026-09-17T10:00:00+07:00'), '2030-01-08T21:30:00+07:00');
  assert.deepEqual(slots.map((slot) => slot.date), ['2030-01-07', '2030-01-07']);
});

test('queue coverage estimates posting days from remaining template slots', () => {
  const template = { days: Object.fromEntries(Array.from({ length: 7 }, (_, index) => [String(index), { enabled: true, times: ['09:00', '12:30'] }])) };
  const result = estimateQueueCoverage({
    readyCount: 3,
    template,
    startDate: '2026-09-17',
    now: new Date('2026-09-17T08:00:00+07:00'),
    latestScheduledAt: '2026-09-17T09:00:00+07:00',
  });
  assert.equal(result.coveredDays, 2);
  assert.equal(result.endDate, '2026-09-18');
  assert.equal(result.weeklyCapacity, 14);
});

test('daily fixed-time batch slots advance by 1 day per clip at fixed time', () => {
  const startDate = '2026-10-10';
  const fixedTime = '19:30';
  const clipCount = 5;
  const slots = Array.from({ length: clipCount }, (_, i) => {
    const d = addDays(startDate, i);
    return buildScheduleIso(d, fixedTime);
  });
  assert.equal(slots.length, 5);
  assert.equal(slots[0], '2026-10-10T19:30:00+07:00');
  assert.equal(slots[1], '2026-10-11T19:30:00+07:00');
  assert.equal(slots[2], '2026-10-12T19:30:00+07:00');
  assert.equal(slots[3], '2026-10-13T19:30:00+07:00');
  assert.equal(slots[4], '2026-10-14T19:30:00+07:00');
});
