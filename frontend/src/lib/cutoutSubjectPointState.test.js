import test from 'node:test';
import assert from 'node:assert/strict';

import {
  addSubjectPointToConfig,
  buildPrepareBaseConfig,
  clearSubjectPointsOnConfig,
  setSubjectPointsOnConfig,
} from './cutoutSubjectPointState.js';
import { normalizeBackgroundIsolation } from './editorProjectState.js';

const ready = () => ({
  schema_version: 1,
  enabled: true,
  mode: 'cutout',
  engine: 'sam2',
  model: 'sam2.1_hiera_tiny',
  artifact: { schema_version: 1, id: 'abc', status: 'ready' },
});

test('reference source/time persists, changes reset old coordinates, and clear drops metadata', () => {
  const ref = { sourcePath: 'a/clip.mp4', sourceStart: 2 };
  const first = addSubjectPointToConfig(ready(), { x: 0.2, y: 0.3 }, { reference: ref });
  const second = addSubjectPointToConfig(first, { x: 0.6, y: 0.7 }, { reference: ref });
  assert.equal(second.subject_points.length, 2);
  const switched = addSubjectPointToConfig(second, { x: 0.2, y: 0.3 },
    { reference: { sourcePath: 'b/clip.mp4', sourceStart: 2 } });
  assert.equal(switched.subject_points.length, 1);
  assert.equal(switched.prompt_reference_source, 'b/clip.mp4');
  assert.equal(normalizeBackgroundIsolation(switched).prompt_reference_start, 2);
  assert.equal(buildPrepareBaseConfig(switched, 'reference-job').prompt_reference_source, 'b/clip.mp4');
  const cleared = clearSubjectPointsOnConfig(switched);
  assert.equal(Object.hasOwn(cleared, 'prompt_reference_source'), false);
  assert.equal(Object.hasOwn(cleared, 'prompt_reference_start'), false);
});

test('invalid source/time metadata fails closed in saved configs', () => {
  for (const prompt_reference_start of [NaN, Infinity, -1, true]) {
    assert.equal(normalizeBackgroundIsolation({ ...ready(), prompt_reference_start }), null);
  }
  assert.equal(normalizeBackgroundIsolation({ ...ready(), prompt_reference_source: 'clip.mp4' }), null);
});

test('a new point appends and marks a ready artifact stale', () => {
  const next = addSubjectPointToConfig(ready(), { x: 0.4, y: 0.5, label: 1 });
  assert.deepEqual(next.subject_points, [{ x: 0.4, y: 0.5, label: 1 }]);
  assert.equal(next.artifact.status, 'stale');
  assert.equal(next.artifact.id, null);
  assert.equal(next.engine, 'sam2');
});

test('a second distinct point keeps the first and a duplicate changes nothing', () => {
  const first = addSubjectPointToConfig(ready(), { x: 0.4, y: 0.5, label: 1 });
  const second = addSubjectPointToConfig(first, { x: 0.6, y: 0.2, label: 1 });
  assert.equal(second.subject_points.length, 2);
  assert.equal(addSubjectPointToConfig(second, { x: 0.6, y: 0.2, label: 1 }), second);
});

test('a point on a not-yet-built cutout does not invent a stale status', () => {
  const config = { ...ready(), artifact: { schema_version: 1, id: null, status: 'missing' } };
  const next = addSubjectPointToConfig(config, { x: 0.1, y: 0.1, label: 1 });
  assert.equal(next.artifact.status, 'missing');
  assert.equal(next.subject_points.length, 1);
});

test('a per-clip ready artifact also marks the project marker stale', () => {
  const config = { ...ready(), artifact: { schema_version: 1, id: null, status: 'missing' } };
  const next = addSubjectPointToConfig(config, { x: 0.1, y: 0.1, label: 1 }, { hasReadyClipArtifact: true });
  assert.equal(next.artifact.status, 'stale');
});

test('clearing removes the key, stales a ready artifact, and is a no-op when empty', () => {
  const withPoints = addSubjectPointToConfig(ready(), { x: 0.4, y: 0.5, label: 1 });
  const cleared = clearSubjectPointsOnConfig({ ...withPoints, artifact: ready().artifact });
  assert.equal(Object.hasOwn(cleared, 'subject_points'), false);
  assert.equal(cleared.artifact.status, 'stale');
  const config = ready();
  assert.equal(clearSubjectPointsOnConfig(config), config);
});

test('a disabled or missing config never gains points', () => {
  const disabled = { schema_version: 1, enabled: false };
  assert.equal(addSubjectPointToConfig(disabled, { x: 0.5, y: 0.5, label: 1 }), disabled);
  assert.equal(addSubjectPointToConfig(null, { x: 0.5, y: 0.5, label: 1 }), null);
});

test('setSubjectPointsOnConfig does not mutate its input', () => {
  const config = ready();
  const snapshot = JSON.stringify(config);
  setSubjectPointsOnConfig(config, [{ x: 0.2, y: 0.2, label: 1 }]);
  assert.equal(JSON.stringify(config), snapshot);
});

test('the edited config survives the project normalizer', () => {
  const next = addSubjectPointToConfig(ready(), { x: 0.4, y: 0.5, label: 1 });
  const normalized = normalizeBackgroundIsolation(next);
  assert.deepEqual(normalized.subject_points, [{ x: 0.4, y: 0.5, label: 1 }]);
  assert.equal(normalized.artifact.status, 'stale');
});

test('the prepare config keeps points from an enabled project config', () => {
  const config = addSubjectPointToConfig(ready(), { x: 0.4, y: 0.5, label: 1 });
  const base = buildPrepareBaseConfig(config, 'req-1');
  assert.deepEqual(base.subject_points, [{ x: 0.4, y: 0.5, label: 1 }]);
  assert.equal(base.request_id, 'req-1');
  assert.deepEqual(base.artifact, { schema_version: 1, id: null, status: 'missing' });
});

test('the prepare config keeps points picked before the cutout was enabled', () => {
  const base = buildPrepareBaseConfig(
    { schema_version: 1, enabled: false, subject_points: [{ x: 0.3, y: 0.3, label: 1 }] },
    'req-2',
  );
  assert.equal(base.enabled, true);
  assert.deepEqual(base.subject_points, [{ x: 0.3, y: 0.3, label: 1 }]);
  assert.equal(buildPrepareBaseConfig(null, 'req-3').subject_points, undefined);
});

test('the prepare config maps an old u2netp model without touching the engine pair', () => {
  const base = buildPrepareBaseConfig({ enabled: true, engine: 'rembg', model: 'u2netp' }, 'r');
  assert.equal(base.engine, 'rembg');
  assert.equal(base.model, 'u2net');
});
