import test from 'node:test';
import assert from 'node:assert/strict';

import {
  formatShortTime,
  clampValue,
  clampScale,
  clampVolume,
  clampSpeed,
  clampRotation,
  clampFreezeTail,
  clampZoom,
  clampPan,
  clampHookDuration,
  pillForBgStyle,
  bgStyleOf,
} from './inspectorModel.js';

test('formatShortTime formats seconds into mm:ss.t', () => {
  assert.equal(formatShortTime(0), '00:00.0');
  assert.equal(formatShortTime(5.42), '00:05.4');
  assert.equal(formatShortTime(65.89), '01:05.8');
  assert.equal(formatShortTime(null), '00:00.0');
  assert.equal(formatShortTime(NaN), '00:00.0');
});

test('clampValue clamps within min and max and uses fallback on NaN', () => {
  assert.equal(clampValue(5, 0, 10), 5);
  assert.equal(clampValue(-2, 0, 10), 0);
  assert.equal(clampValue(15, 0, 10), 10);
  assert.equal(clampValue('invalid', 0, 10, 3), 3);
});

test('clampScale clamps caption scale between 0.4 and 2.2', () => {
  assert.equal(clampScale(1.0), 1.0);
  assert.equal(clampScale(0.1), 0.4);
  assert.equal(clampScale(3.0), 2.2);
});

test('clampVolume clamps audio volume between 0.0 and 1.0', () => {
  assert.equal(clampVolume(0.5), 0.5);
  assert.equal(clampVolume(-0.2), 0.0);
  assert.equal(clampVolume(1.5), 1.0);
});

test('clampSpeed clamps speed between 0.5 and 2.0', () => {
  assert.equal(clampSpeed(1.5), 1.5);
  assert.equal(clampSpeed(0.2), 0.5);
  assert.equal(clampSpeed(5.0), 2.0);
});

test('clampRotation wraps angles correctly to [0, 360)', () => {
  assert.equal(clampRotation(90), 90);
  assert.equal(clampRotation(360), 0);
  assert.equal(clampRotation(450), 90);
  assert.equal(clampRotation(-90), 270);
  assert.equal(clampRotation('bad'), 0);
});

test('clampFreezeTail clamps freeze tail duration between 0.0 and 10.0', () => {
  assert.equal(clampFreezeTail(2.5), 2.5);
  assert.equal(clampFreezeTail(-1), 0.0);
  assert.equal(clampFreezeTail(15), 10.0);
});

test('clampZoom and clampPan clamp viewport parameters properly', () => {
  assert.equal(clampZoom(1.5), 1.5);
  assert.equal(clampZoom(0.8), 1.0);
  assert.equal(clampZoom(4.0), 3.0);

  assert.equal(clampPan(0.2), 0.2);
  assert.equal(clampPan(-1.5), -1.0);
  assert.equal(clampPan(2.0), 1.0);
});

test('clampHookDuration clamps duration between min and max', () => {
  assert.equal(clampHookDuration(3.0, 1.0, 8.0), 3.0);
  assert.equal(clampHookDuration(0.5, 1.0, 8.0), 1.0);
  assert.equal(clampHookDuration(10.0, 1.0, 8.0), 8.0);
});

test('pillForBgStyle and bgStyleOf map presets roundtrip', () => {
  const pill = pillForBgStyle('pill');
  assert.ok(pill);
  assert.equal(bgStyleOf(pill), 'pill');
  assert.equal(bgStyleOf(null), 'none');
  assert.equal(pillForBgStyle('nonexistent'), null);
});
