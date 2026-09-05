import test from 'node:test';
import assert from 'node:assert/strict';
import {
  EASING_FUNCTIONS,
  clampProperty,
  interpolateNumericKeyframes,
  resolveClipTransforms,
} from './keyframeModel.js';

test('EASING_FUNCTIONS compute accurate normalized values between 0.0 and 1.0', () => {
  for (const [name, fn] of Object.entries(EASING_FUNCTIONS)) {
    assert.equal(fn(0.0), 0.0, `${name} at 0.0`);
    assert.equal(fn(1.0), 1.0, `${name} at 1.0`);
  }
  assert.equal(EASING_FUNCTIONS.linear(0.5), 0.5);
  assert.equal(EASING_FUNCTIONS.ease_in(0.5), 0.25);
  assert.equal(EASING_FUNCTIONS.ease_out(0.5), 0.75);
  assert.equal(EASING_FUNCTIONS.ease_in_out(0.5), 0.5);
});

test('clampProperty respects bounds for zoom, pan, opacity, volume', () => {
  assert.equal(clampProperty('zoom', 0.2), 0.5);
  assert.equal(clampProperty('zoom', 3.5), 3.0);
  assert.equal(clampProperty('pan_x', -1.5), -1.0);
  assert.equal(clampProperty('pan_x', 2.0), 1.0);
  assert.equal(clampProperty('opacity', -0.1), 0.0);
  assert.equal(clampProperty('opacity', 1.2), 1.0);
  assert.equal(clampProperty('volume', -0.5), 0.0);
  assert.equal(clampProperty('volume', 3.0), 2.0);
});

test('interpolateNumericKeyframes handles linear, boundaries, and easing smoothly', () => {
  const kf = [
    { time: 1.0, value: 1.0 },
    { time: 3.0, value: 2.0, easing: 'linear' },
  ];

  assert.equal(interpolateNumericKeyframes(kf, 0.5), 1.0, 'before start holds first');
  assert.equal(interpolateNumericKeyframes(kf, 3.5), 2.0, 'after end holds last');
  assert.equal(interpolateNumericKeyframes(kf, 2.0), 1.5, 'midpoint is 1.5');
});

test('resolveClipTransforms resolves animated zoom, pan, and volume with clamping', () => {
  const clip = {
    zoom: 1.0,
    keyframes: [
      { time: 0.0, zoom: 1.0, pan_x: 0.0, volume: 1.0 },
      { time: 2.0, zoom: 1.5, pan_x: 0.5, volume: 0.0 },
    ],
  };

  const t0 = resolveClipTransforms(clip, 0.0);
  assert.equal(t0.zoom, 1.0);
  assert.equal(t0.pan_x, 0.0);
  assert.equal(t0.volume, 1.0);

  const tMid = resolveClipTransforms(clip, 1.0);
  assert.equal(tMid.zoom, 1.25);
  assert.equal(tMid.pan_x, 0.25);
  assert.equal(tMid.volume, 0.5);

  const tEnd = resolveClipTransforms(clip, 2.0);
  assert.equal(tEnd.zoom, 1.5);
  assert.equal(tEnd.pan_x, 0.5);
  assert.equal(tEnd.volume, 0.0);
});
