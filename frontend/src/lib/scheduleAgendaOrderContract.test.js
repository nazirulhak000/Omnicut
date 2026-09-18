import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const scheduleAgendaPath = path.resolve(process.cwd(), 'src/components/ScheduleAgenda.jsx');

test('Schedule Agenda declares postedQueue before pagination effects read it', () => {
  const source = fs.readFileSync(scheduleAgendaPath, 'utf8');
  const declaration = source.indexOf('const postedQueue = useMemo(');
  const paginationEffectUse = source.indexOf('Math.ceil(postedQueue.length / postedPageSize)');

  assert.notEqual(declaration, -1, 'postedQueue declaration must exist');
  assert.notEqual(paginationEffectUse, -1, 'postedQueue pagination effect use must exist');
  assert.ok(declaration < paginationEffectUse, 'postedQueue must be initialized before the pagination effect');
});
