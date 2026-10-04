import test from 'node:test';
import assert from 'node:assert/strict';
import { ZOOM_LEVELS } from './timelineMath.js';
import { frameTickSpacing } from './timelineTrackModel.js';
import {
  DEFAULT_PX_PER_SEC,
  MAX_PX_PER_SEC,
  MIN_PX_PER_SEC,
  ZOOM_PRESETS,
  clampPxPerSec,
  fitPxPerSec,
  scrollLeftForAnchor,
  stepZoomPreset,
  wheelZoomFactor,
  zoomPresetIndex,
} from './timelineZoom.js';

test('presets keep the old steps as quick stops and reach frame-level zoom', () => {
  assert.deepEqual(ZOOM_PRESETS.slice(0, ZOOM_LEVELS.length), ZOOM_LEVELS);
  assert.equal(DEFAULT_PX_PER_SEC, 50);
  assert.ok(frameTickSpacing(MAX_PX_PER_SEC) >= 6);
  assert.ok(frameTickSpacing(400) > 13);
});

test('clamp keeps px/s finite and inside the range', () => {
  assert.equal(clampPxPerSec(1), MIN_PX_PER_SEC);
  assert.equal(clampPxPerSec(1e9), MAX_PX_PER_SEC);
  assert.equal(clampPxPerSec(73.5), 73.5);
  assert.equal(clampPxPerSec(NaN), DEFAULT_PX_PER_SEC);
  assert.equal(clampPxPerSec(-5), DEFAULT_PX_PER_SEC);
});

test('buttons and +/- step to the next preset from any continuous value', () => {
  assert.equal(stepZoomPreset(50, 1), 100);
  assert.equal(stepZoomPreset(50, -1), 25);
  assert.equal(stepZoomPreset(60, 1), 100);
  assert.equal(stepZoomPreset(60, -1), 50);
  assert.equal(stepZoomPreset(49.8, 1), 100, 'float drift near a preset does not repeat it');
  assert.equal(stepZoomPreset(MAX_PX_PER_SEC, 1), MAX_PX_PER_SEC);
  assert.equal(stepZoomPreset(MIN_PX_PER_SEC, -1), MIN_PX_PER_SEC);
});

test('toolbar index only reports an end at the real ends', () => {
  assert.equal(zoomPresetIndex(MIN_PX_PER_SEC), 0);
  assert.equal(zoomPresetIndex(MAX_PX_PER_SEC), ZOOM_PRESETS.length - 1);
  assert.equal(zoomPresetIndex(50), 2);
  assert.equal(zoomPresetIndex(11), 1, 'room left to zoom out keeps the button enabled');
  assert.equal(zoomPresetIndex(750), ZOOM_PRESETS.length - 2);
});

test('wheel factor: notch-sized, direction-correct, bounded', () => {
  assert.ok(wheelZoomFactor(-100) > 1.2 && wheelZoomFactor(-100) < 1.25);
  assert.ok(wheelZoomFactor(100) < 1);
  assert.equal(wheelZoomFactor(0), 1);
  assert.equal(wheelZoomFactor(-1e6), 2);
  assert.equal(wheelZoomFactor(1e6), 0.5);
  assert.ok(Math.abs(wheelZoomFactor(-3, 1) - wheelZoomFactor(-48)) < 1e-12, 'line mode = 16 px per line');
});

test('anchored zoom keeps the time under the cursor at the same screen x', () => {
  const gutter = 92;
  const before = { pxPerSec: 50, scrollLeft: 300, anchorX: 400 };
  const tBefore = (before.scrollLeft + before.anchorX - gutter) / before.pxPerSec;
  const nextPx = 137.5;
  const next = scrollLeftForAnchor({ ...before, nextPxPerSec: nextPx, gutter });
  const tAfter = (next + before.anchorX - gutter) / nextPx;
  assert.ok(Math.abs(tAfter - tBefore) < 1e-9);
  // Zooming out near the start cannot scroll before 0.
  assert.equal(scrollLeftForAnchor({ pxPerSec: 100, nextPxPerSec: 10, scrollLeft: 0, anchorX: 500, gutter }), 0);
});

test('fit uses the exact px/s, not the nearest lower preset', () => {
  assert.equal(fitPxPerSec(1000, 16), 62.5);
  assert.equal(fitPxPerSec(1000, 1000), MIN_PX_PER_SEC);
  assert.equal(fitPxPerSec(0, 10), null);
  assert.equal(fitPxPerSec(100, 0), null);
});
