import test from 'node:test';
import assert from 'node:assert/strict';

import { shouldCaptureSubjectPick, subjectPointFromPickClick } from './subjectPickGesture.js';

const rect = { left: 100, top: 50, width: 200, height: 400 };

test('a plain click maps to a product point inside the frame', () => {
  const point = subjectPointFromPickClick({ clientX: 200, clientY: 250 }, rect);
  assert.deepEqual(point, { x: 0.5, y: 0.5, label: 1 });
});

test('mapping stays correct for a scaled and offset frame', () => {
  const zoomed = { left: -40, top: 10, width: 400, height: 800 };
  const point = subjectPointFromPickClick({ clientX: 160, clientY: 410 }, zoomed);
  assert.deepEqual(point, { x: 0.5, y: 0.5, label: 1 });
});

test('shift or alt click marks background', () => {
  assert.equal(subjectPointFromPickClick({ clientX: 150, clientY: 100, shiftKey: true }, rect).label, 0);
  assert.equal(subjectPointFromPickClick({ clientX: 150, clientY: 100, altKey: true }, rect).label, 0);
});

test('defaultLabel parameter sets label when no shift or alt', () => {
  assert.equal(subjectPointFromPickClick({ clientX: 150, clientY: 100 }, rect, 0).label, 0);
  assert.equal(subjectPointFromPickClick({ clientX: 150, clientY: 100 }, rect, 1).label, 1);
});

test('clicks outside clamp and a degenerate rect is rejected', () => {
  assert.deepEqual(subjectPointFromPickClick({ clientX: 0, clientY: 9999 }, rect), { x: 0, y: 1, label: 1 });
  assert.equal(subjectPointFromPickClick({ clientX: 1, clientY: 1 }, { left: 0, top: 0, width: 0, height: 0 }), null);
});

test('pick capture is off outside pick mode and lets buttons through', () => {
  const target = (insideButton, passthrough = false) => ({
    closest: (selector) => (insideButton && selector === 'button' ? { hasAttribute: (name) => passthrough && name === 'data-subject-pick-passthrough' } : null),
  });
  assert.equal(shouldCaptureSubjectPick(false, target(false)), false);
  assert.equal(shouldCaptureSubjectPick(true, target(false)), true);
  assert.equal(shouldCaptureSubjectPick(true, target(true)), false);
  // The full-frame play overlay is a button but acts as the frame itself.
  assert.equal(shouldCaptureSubjectPick(true, target(true, true)), true);
});
