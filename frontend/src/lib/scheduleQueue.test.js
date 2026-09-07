import test from 'node:test';
import assert from 'node:assert/strict';
import { addDays, buildScheduleIso, groupScheduleItems, templateForWeek, weekStartForDate } from './scheduleQueue.js';
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

test('weekly template helpers use Monday boundaries and preserve three slots', () => {
  assert.equal(weekStartForDate('2026-09-10'), '2026-09-07');
  assert.equal(addDays('2026-09-07', 6), '2026-09-13');
  const template = templateForWeek({ days: { '0': { enabled: false, times: ['20:00', '07:00', '16:00', '12:00', '10:00'] } } }, '2026-09-07');
  assert.equal(template.days['0'].enabled, false);
  assert.deepEqual(template.days['0'].times, ['12:30', '19:00', '21:30']);
  assert.deepEqual(template.days['1'].times, ['12:30', '19:00', '21:30']);
});
