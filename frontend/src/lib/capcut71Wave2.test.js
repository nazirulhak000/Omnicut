import test from 'node:test';
import assert from 'node:assert/strict';

import { resolveWaveformLodColumns } from './audioPeaks.js';
import {
  KEYFRAME_EASING_OPTIONS,
  SMART_CAMERA_PRESETS,
  smartCameraPatch,
  LOG_WHEEL_CROSSOVER,
  processPrimaryWheelChannel,
} from './inspectorModel.js';
import {
  SNAP_X_GUIDES_9_16,
  SNAP_Y_GUIDES_9_16,
  smoothstep,
} from './overlayBoxGeometry.js';
import {
  BLEND_MODE_OPTIONS,
  resolveCanvasCompositeOp,
  capcutSoftLightChannel,
  capcutSpringScale,
  capcutElasticOut,
  capcutBackOut,
} from './stickerAnimation.js';

test('resolveWaveformLodColumns selects LOD bucket count for zoom', () => {
  assert.equal(resolveWaveformLodColumns(40), 600);
  assert.equal(resolveWaveformLodColumns(90), 2400);
  assert.equal(resolveWaveformLodColumns(240), 9600);
});

test('inspectorModel exports CapCut 7.1 keyframe curves and 9:16 smart camera presets', () => {
  assert.ok(KEYFRAME_EASING_OPTIONS.length >= 6);
  assert.equal(SMART_CAMERA_PRESETS.length, 4);
  const patch = smartCameraPatch({ trim_start: 0, trim_end: 6.0 }, 6.0, 'slow_push');
  assert.ok(patch);
  assert.equal(patch.keyframes.length, 2);
  assert.equal(patch.keyframes[0].zoom, 1.25);
});

test('inspectorModel exports PrimaryWheel and LogWheel shader math', () => {
  assert.deepEqual(LOG_WHEEL_CROSSOVER, { rugDown: 0.333, rugUp: 0.555 });
  assert.ok(Math.abs(processPrimaryWheelChannel(0.5, 0, 1, 1) - 0.5) < 1e-6);
});

test('overlayBoxGeometry exports 9:16 intelligent crop snap guides and smoothstep', () => {
  assert.ok(SNAP_X_GUIDES_9_16.includes(0.333));
  assert.ok(SNAP_Y_GUIDES_9_16.includes(0.72));
  assert.equal(smoothstep(0, 1, 0.5), 0.5);
});

test('stickerAnimation exports MixMode blend modes and spring/elastic/back physics', () => {
  assert.ok(BLEND_MODE_OPTIONS.length >= 6);
  assert.equal(resolveCanvasCompositeOp('screen'), 'screen');
  assert.equal(resolveCanvasCompositeOp('normal'), 'source-over');
  assert.ok(capcutSoftLightChannel(0.5, 0.5) > 0.49 && capcutSoftLightChannel(0.5, 0.5) < 0.51);
  assert.ok(capcutSpringScale(1.0) > 0.99);
  assert.equal(capcutElasticOut(1.0), 1.0);
  assert.ok(Math.abs(capcutBackOut(1.0) - 1.0) < 1e-6);
});
