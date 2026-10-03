import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeBackgroundIsolation } from './backgroundIsolationConfig.js';
import { normalizeBackgroundIsolation as editorNormalizer } from './editorProjectState.js';
import { migrateToTimelineV2, serializeTimelineV2ToManifest as serializeTimeline } from './timelineSchema.js';

test('shared Cutout validation preserves legacy and SAM2 configs losslessly', () => {
  for (const fields of [{}, { model: 'u2netp' }, { engine: 'rembg' },
    { model: 'sam2.1_hiera_small' }, { engine: 'sam2' },
    { engine: 'sam2', model: 'sam2.1_hiera_base_plus' }]) {
    const config = { enabled: true, ...fields, artifact: { status: 'missing', future: { keep: true } } };
    assert.deepEqual(normalizeBackgroundIsolation(config), config);
    assert.deepEqual(editorNormalizer(config), config);
    const timeline = migrateToTimelineV2({ background_isolation: config });
    assert.deepEqual(serializeTimeline(timeline).background_isolation, config);
    normalizeBackgroundIsolation(config).artifact.future.keep = false;
    assert.equal(config.artifact.future.keep, true);
  }
});

test('shared Cutout validation rejects an explicit mismatched engine/model pair', () => {
  for (const config of [
    { enabled: true, engine: 'sam2', model: 'u2net' },
    { enabled: true, engine: 'rembg', model: 'sam2.1_hiera_tiny' },
  ]) {
    assert.equal(normalizeBackgroundIsolation(config), null);
    assert.equal(editorNormalizer(config), null);
    assert.equal(Object.hasOwn(serializeTimeline(migrateToTimelineV2({ background_isolation: config })), 'background_isolation'), false);
    assert.deepEqual(normalizeBackgroundIsolation({ ...config, enabled: false }), { ...config, enabled: false });
  }
});
