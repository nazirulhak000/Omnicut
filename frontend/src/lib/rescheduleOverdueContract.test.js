import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const read = (rel) => fs.readFileSync(path.resolve(process.cwd(), rel), 'utf8');

test('overdue re-arrangement calls the real backend routes (preview, then an all-or-nothing commit)', () => {
  const api = read('src/api.js');
  assert.match(api, /previewRescheduleOverdue[^\n]*api\.post\('\/schedule-queue\/reschedule-overdue\/preview'/);
  assert.match(api, /commitRescheduleOverdue[^\n]*api\.post\('\/schedule-queue\/reschedule-overdue', \{ assignments \}\)/);
});

test('Schedule Agenda previews before it commits and sends exactly the previewed slots', () => {
  const source = read('src/components/ScheduleAgenda.jsx');
  const open = source.indexOf('const openReschedule = async');
  const confirm = source.indexOf('const confirmReschedule = async');
  assert.ok(open > 0 && confirm > open, 'preview handler must exist before the commit handler');
  assert.match(source.slice(open, confirm), /previewRescheduleOverdue\(/);
  const commitBody = source.slice(confirm, confirm + 700);
  assert.match(commitBody, /commitRescheduleOverdue\(items\.map\(\(row\) => \(\{ id: row\.id, scheduled_at: row\.new_scheduled_at \}\)\)\)/);
  assert.match(source, /row\.needs_reschedule/);
  assert.match(source, /EP:\{item\.episode_no\}/);
});
