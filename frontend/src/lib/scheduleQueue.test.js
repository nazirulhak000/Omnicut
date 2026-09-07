import test from 'node:test';
import assert from 'node:assert/strict';
import { buildScheduleIso, groupScheduleItems, scheduleTimeOptions, snapTimeToFiveMinutes } from './scheduleQueue.js';

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
