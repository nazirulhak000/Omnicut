import test from 'node:test';
import assert from 'node:assert/strict';

import {
  SUBJECT_POINT_LIMIT,
  describeSubjectPointCount,
  normalizeSubjectPoints,
  subjectPointFromFramePointer,
  subjectPointMarkerStyle,
  withSubjectPoint,
} from './subjectPoints.js';

test('normalizes, clamps and caps the points the worker will receive', () => {
  assert.deepEqual(normalizeSubjectPoints([
    { x: 1.5, y: -0.2 },
    [0.4, 0.6],
    { x: 'bad', y: 0.5 },
    'nope',
    { x: 0.2, y: 0.3, label: 0 },
  ]), [
    { x: 1, y: 0, label: 1 },
    { x: 0.4, y: 0.6, label: 1 },
    { x: 0.2, y: 0.3, label: 0 },
  ]);

  const flooded = Array.from({ length: 20 }, (_, index) => ({ x: index / 40, y: 0.5 }));
  assert.equal(normalizeSubjectPoints(flooded).length, SUBJECT_POINT_LIMIT);
  assert.deepEqual(normalizeSubjectPoints('0.5,0.5'), []);
  assert.deepEqual(normalizeSubjectPoints(null), []);
  assert.deepEqual(normalizeSubjectPoints([{ x: Number.NaN, y: 0.5 }]), []);
});

test('adding a point keeps the limit and ignores a repeated pick', () => {
  const first = withSubjectPoint([], { x: 0.3, y: 0.4 });
  assert.deepEqual(first, [{ x: 0.3, y: 0.4, label: 1 }]);
  assert.deepEqual(withSubjectPoint(first, { x: 0.3001, y: 0.4001 }), first);
  assert.deepEqual(withSubjectPoint(first, { x: 0.5, y: 0.4 }).length, 2);
  assert.deepEqual(withSubjectPoint(first, { x: 'bad', y: 0.4 }), first);

  const full = Array.from({ length: SUBJECT_POINT_LIMIT }, (_, index) => ({
    x: 0.1 + index * 0.05, y: 0.5,
  }));
  assert.equal(withSubjectPoint(full, { x: 0.9, y: 0.9 }).length, SUBJECT_POINT_LIMIT);
});

test('maps a pointer inside the preview frame to a normalized point', () => {
  const rect = { left: 100, top: 50, width: 400, height: 800 };
  assert.deepEqual(subjectPointFromFramePointer({ clientX: 300, clientY: 450 }, rect), {
    x: 0.5, y: 0.5, label: 1,
  });
  // Outside the frame on every side still yields a usable, clamped point.
  assert.deepEqual(subjectPointFromFramePointer({ clientX: 0, clientY: 0 }, rect), {
    x: 0, y: 0, label: 1,
  });
  assert.deepEqual(subjectPointFromFramePointer({ clientX: 9999, clientY: 9999 }, rect), {
    x: 1, y: 1, label: 1,
  });
});

test('refuses to record a point for a hidden or degenerate frame', () => {
  assert.equal(subjectPointFromFramePointer({ clientX: 10, clientY: 10 }, { left: 0, top: 0, width: 0, height: 0 }), null);
  assert.equal(subjectPointFromFramePointer({ clientX: 10, clientY: 10 }, null), null);
  assert.equal(subjectPointFromFramePointer(null, { left: 0, top: 0, width: 10, height: 10 }), null);
});

test('marker positions and the status sentence follow the points', () => {
  assert.deepEqual(subjectPointMarkerStyle({ x: 0.25, y: 0.5 }), { left: '25%', top: '50%' });
  assert.deepEqual(subjectPointMarkerStyle({ x: 9, y: -4 }), { left: '100%', top: '0%' });
  assert.equal(describeSubjectPointCount([]), 'ยังไม่ได้จิ้มจุดสินค้า');
  assert.equal(describeSubjectPointCount([{ x: 0.1, y: 0.2 }]), 'จิ้มจุดสินค้าแล้ว 1 จุด');
});
