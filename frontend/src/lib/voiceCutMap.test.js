import test from 'node:test';
import assert from 'node:assert/strict';

import {
  MIN_REMAINING_SECONDS,
  effectiveDuration,
  keepRanges,
  normalizeCuts,
  programToSource,
  shiftTime,
  snapToFrameGrid,
  sourceToProgram,
} from './voiceCutMap.js';

// Worked examples below are the docstring examples of scripts/voice_cut_map.py,
// so both sides are held to the same numbers.

test('snapToFrameGrid rounds ties up and never returns -0', () => {
  assert.equal(snapToFrameGrid(2.01), 2);
  assert.equal(snapToFrameGrid(2.49), 2.5);
  assert.equal(snapToFrameGrid(1 / 60), 0.03333333333333333);
  assert.equal(Object.is(snapToFrameGrid(-0.001), 0), true);
  assert.equal(snapToFrameGrid(Number.NaN), 0);
  assert.equal(snapToFrameGrid('abc'), 0);
  assert.equal(snapToFrameGrid(null), 0);
});

test('normalizeCuts docstring examples', () => {
  assert.deepEqual(
    normalizeCuts([{ id: 'a', start: 2.01, end: 2.49 }], 6.0),
    [{ id: 'a', start: 2.0, end: 2.5 }],
  );
  assert.deepEqual(
    normalizeCuts([{ id: 'a', start: 1.0, end: 2.0 }, { id: 'b', start: 1.5, end: 3.0 }], 6.0),
    [{ id: 'a', start: 1.0, end: 3.0 }],
  );
  assert.deepEqual(
    normalizeCuts([{ id: 'a', start: 5.5, end: 9.0 }], 6.0),
    [{ id: 'a', start: 5.5, end: 6.0 }],
  );
  assert.deepEqual(normalizeCuts([{ id: 'a', start: 1.0, end: 1.01 }], 6.0), []);
});

test('normalizeCuts sorts, merges touching spans, keeps extra keys and never mutates', () => {
  const input = [
    { id: 'late', start: 4, end: 5, reason: 'silence', removed: ['x'] },
    { id: 'early', start: 1, end: 2, reason: 'manual' },
    { id: 'touch', start: 2, end: 3 },
  ];
  const before = JSON.stringify(input);
  const out = normalizeCuts(input, 10);
  assert.equal(JSON.stringify(input), before);
  assert.deepEqual(out, [
    { id: 'early', start: 1, end: 3, reason: 'manual' },
    { id: 'late', start: 4, end: 5, reason: 'silence', removed: ['x'] },
  ]);
  assert.deepEqual(normalizeCuts(out, 10), out, 'idempotent');
});

test('normalizeCuts skips unusable entries and rejects an unusable duration', () => {
  assert.deepEqual(normalizeCuts([null, 3, 'x', [1, 2], { start: 'a', end: 2 }, { start: 1 }, { start: null, end: 2 }], 6), []);
  assert.deepEqual(normalizeCuts([{ id: 'n', start: '1.5', end: '2.5' }], 6), [{ id: 'n', start: 1.5, end: 2.5 }]);
  assert.deepEqual(normalizeCuts([{ start: 1, end: 2 }], 0), []);
  assert.deepEqual(normalizeCuts([{ start: 1, end: 2 }], -3), []);
  assert.deepEqual(normalizeCuts([{ start: 1, end: 2 }], 'abc'), []);
  assert.deepEqual(normalizeCuts(undefined, 6), []);
  assert.deepEqual(normalizeCuts([{ start: -2, end: 1 }], 6), [{ start: 0, end: 1 }]);
});

test('keepRanges docstring examples', () => {
  assert.deepEqual(keepRanges([{ start: 2.0, end: 2.5 }], 6.0), [
    { srcStart: 0, srcEnd: 2, progStart: 0 },
    { srcStart: 2.5, srcEnd: 6, progStart: 2 },
  ]);
  assert.deepEqual(keepRanges([], 6.0), [{ srcStart: 0, srcEnd: 6, progStart: 0 }]);
  assert.deepEqual(keepRanges([{ start: 0.0, end: 1.0 }], 6.0), [{ srcStart: 1, srcEnd: 6, progStart: 0 }]);
});

test('keepRanges: tail cut, everything cut, several cuts, invalid duration', () => {
  assert.deepEqual(keepRanges([{ start: 4, end: 6 }], 6), [{ srcStart: 0, srcEnd: 4, progStart: 0 }]);
  assert.deepEqual(keepRanges([{ start: 0, end: 6 }], 6), []);
  assert.deepEqual(keepRanges([{ start: 1, end: 2 }, { start: 3, end: 4 }], 6), [
    { srcStart: 0, srcEnd: 1, progStart: 0 },
    { srcStart: 2, srcEnd: 3, progStart: 1 },
    { srcStart: 4, srcEnd: 6, progStart: 2 },
  ]);
  assert.deepEqual(keepRanges([{ start: 1, end: 2 }], 0), []);
});

test('effectiveDuration docstring examples', () => {
  assert.equal(effectiveDuration([{ start: 2.0, end: 2.5 }], 6.0), 5.5);
  assert.equal(effectiveDuration([], 6.0), 6.0);
  assert.equal(Number(effectiveDuration([{ start: 2.0, end: 2.5 }, { start: 4.0, end: 4.2 }], 6.0).toFixed(6)), 5.3);
  assert.equal(effectiveDuration([{ start: 0, end: 99 }], 6), 0);
  assert.equal(effectiveDuration([{ start: 1, end: 2 }], 0), 0);
});

test('sourceToProgram docstring examples', () => {
  const cuts = [{ start: 2.0, end: 2.5 }];
  assert.equal(sourceToProgram(1.0, cuts), 1.0);
  assert.equal(sourceToProgram(2.25, cuts), 2.0);
  assert.equal(sourceToProgram(3.0, cuts), 2.5);
  assert.equal(sourceToProgram(2.0, cuts), 2.0, 'left edge');
  assert.equal(sourceToProgram(2.5, cuts), 2.0, 'right edge lands on the join');
  assert.equal(sourceToProgram('x', cuts), 0);
});

test('programToSource docstring examples', () => {
  const cuts = [{ start: 2.0, end: 2.5 }];
  assert.equal(programToSource(1.0, cuts), 1.0);
  assert.equal(programToSource(2.0, cuts), 2.5, 'on the join -> far side of the cut');
  assert.equal(programToSource(2.5, cuts), 3.0);
  assert.equal(programToSource(null, cuts), 0);
});

test('programToSource and sourceToProgram are inverse on kept time', () => {
  const cuts = normalizeCuts([{ start: 1, end: 1.5 }, { start: 3, end: 4 }, { start: 5, end: 5.2 }], 8);
  for (let k = 0; k <= 20; k += 1) {
    const t = k * 0.3;
    const u = programToSource(t, cuts);
    assert.ok(Math.abs(sourceToProgram(u, cuts) - t) < 1e-9, `t=${t} u=${u}`);
  }
  // inside a cut the source time collapses onto the join, and never goes backwards
  let last = -1;
  for (let k = 0; k <= 80; k += 1) {
    const p = sourceToProgram(k * 0.1, cuts);
    assert.ok(p >= last - 1e-12);
    last = p;
  }
});

test('shiftTime docstring examples', () => {
  assert.equal(shiftTime(1.0, 2.0, 2.5), 1.0);
  assert.equal(shiftTime(2.25, 2.0, 2.5), 2.0);
  assert.equal(shiftTime(3.0, 2.0, 2.5), 2.5);
  assert.equal(shiftTime(2.0, 2.0, 2.5), 2.0, 'at t0');
  assert.equal(shiftTime(2.5, 2.0, 2.5), 2.0, 'at t1');
  assert.equal(shiftTime(7, 'a', 2.5), 7, 'bad range leaves t alone');
  assert.equal(shiftTime('x', 2, 3), 0);
});

test('MIN_REMAINING_SECONDS matches the backend', () => {
  assert.equal(MIN_REMAINING_SECONDS, 1.0);
});
