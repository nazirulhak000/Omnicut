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

test('a post click that never confirmed can be closed from the scheduler only through the guarded server route', () => {
  assert.match(read('src/api.js'), /resolveUnpostedQueue[^\n]*api\.post\(`\/schedule-queue\/\$\{id\}\/resolve-unposted`, \{ evidence \}\)/);
  const source = read('src/components/ScheduleAgenda.jsx');
  assert.match(source, /\['publishing', 'confirmation_unknown'\]\.includes\(item\.posting_job_status\)/);
  assert.match(source, /await confirmDialog\('คลิปนี้กดโพสต์ไปแล้ว/);
});
