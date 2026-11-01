import test from 'node:test';
import assert from 'node:assert/strict';

import {
  defaultCutoutModel,
  resolveCutoutEngineModel,
  calculateNormalizedStroke,
  STROKE_NORM_BASE,
} from './cutoutEngineModel.js';

test('legacy project with only a rembg model keeps the rembg engine', () => {
  assert.deepEqual(resolveCutoutEngineModel({ model: 'u2netp' }), { engine: 'rembg', model: 'u2netp' });
  assert.deepEqual(resolveCutoutEngineModel({ model: 'isnet-general-use' }), { engine: 'rembg', model: 'isnet-general-use' });
});

test('no engine and no model falls back to the SAM 2 default pair', () => {
  assert.deepEqual(resolveCutoutEngineModel(null), { engine: 'sam2', model: 'sam2.1_hiera_tiny' });
  assert.deepEqual(resolveCutoutEngineModel({}), { engine: 'sam2', model: 'sam2.1_hiera_tiny' });
});

test('a SAM 2 model without an engine resolves to sam2', () => {
  assert.deepEqual(resolveCutoutEngineModel({ model: 'sam2.1_hiera_small' }), { engine: 'sam2', model: 'sam2.1_hiera_small' });
});

test('an explicit engine wins and a model of another engine is replaced', () => {
  assert.deepEqual(resolveCutoutEngineModel({ engine: 'sam2', model: 'u2net' }), { engine: 'sam2', model: 'sam2.1_hiera_tiny' });
  assert.deepEqual(resolveCutoutEngineModel({ engine: 'rembg', model: 'sam2.1_hiera_tiny' }), { engine: 'rembg', model: 'u2net' });
});

test('unknown values never leak through', () => {
  assert.deepEqual(resolveCutoutEngineModel({ engine: 'magic', model: 42 }), { engine: 'sam2', model: 'sam2.1_hiera_tiny' });
  assert.equal(defaultCutoutModel('nope'), 'sam2.1_hiera_tiny');
});

test('calculateNormalizedStroke applies CapCut 7.1 DilateErode scale norm', () => {
  assert.equal(STROKE_NORM_BASE, 720.0);
  // Export resolution 1080x1920: scale norm = 1080/720 = 1.5 -> 14 * 1.5 = 21
  assert.equal(calculateNormalizedStroke(14, 1080, 1920), 21);
  // Preview resolution 540x960: scale norm = 540/720 = 0.75 -> 14 * 0.75 = 11 (rounded)
  assert.equal(calculateNormalizedStroke(14, 540, 960), 11);
  // Ratio to canvas width is identical: 21 / 1080 = 0.01944, 10.5 / 540 = 0.01944
});
