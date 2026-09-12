import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildAttachPayload,
  buildCandidateOptions,
  findOptionKey,
  metricSummary,
} from './manualMatch.js';

test('buildCandidateOptions maps library clips to labelled select options', () => {
  const options = buildCandidateOptions([
    { clip_file: 'b.mp4', hook_title: 'Hook B', product_name: 'สินค้า B' },
    { clip_file: 'a.mp4', hook_title: 'Hook A', product_name: 'สินค้า A' },
    { clip_file: 'c.mp4' },
  ]);
  assert.equal(options.length, 3);
  assert.deepEqual([...options.map((o) => o.label)].sort(), [
    'Hook A — สินค้า A',
    'Hook B — สินค้า B',
    'c.mp4',
  ]);
  assert.equal(options.find((o) => o.candidate.clip_file === 'a.mp4').key, 'a.mp4::Hook A');
});

test('buildAttachPayload only fires with a pending row and a picked option', () => {
  const candidate = { clip_file: 'x.mp4', hook_title: 'H' };
  const options = buildCandidateOptions([candidate]);
  const option = options[0];
  assert.deepEqual(
    buildAttachPayload({ id: 'p1' }, option),
    { pending_id: 'p1', candidate },
  );
  assert.equal(buildAttachPayload(null, option), null);
  assert.equal(buildAttachPayload({ id: 'p1' }, null), null);
});

test('findOptionKey round-trips a chosen option', () => {
  const candidate = { clip_file: 'k.mp4', hook_title: 'Hook' };
  const options = buildCandidateOptions([candidate]);
  assert.equal(findOptionKey(options, candidate), options[0].key);
  assert.equal(findOptionKey(options, null), '');
});

test('metricSummary renders readable numbers and skips zeros', () => {
  assert.equal(metricSummary({ views: 59, likes: 5, comments: 0 }), 'วิว 59 · ถูกใจ 5');
  assert.equal(metricSummary({}), 'ยังไม่มีตัวเลข');
  assert.equal(metricSummary(null), 'ยังไม่มีตัวเลข');
});
