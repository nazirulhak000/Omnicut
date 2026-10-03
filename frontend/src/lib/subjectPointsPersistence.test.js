import test from 'node:test';
import assert from 'node:assert/strict';
import {
  editorStateToSavePayload,
  manifestToEditorState,
  normalizeBackgroundIsolation,
  serializeRenderFeatures,
} from './editorProjectState.js';
import {
  migrateToTimelineV2,
  serializeTimelineV2ToManifest,
} from './timelineSchema.js';
import { SUBJECT_POINT_LIMIT } from './subjectPoints.js';

function cutout(extra = {}) {
  return {
    schema_version: 1,
    enabled: true,
    mode: 'cutout',
    engine: 'sam2',
    model: 'sam2.1_hiera_tiny',
    quality: 'balanced',
    fallback: 'original',
    ...extra,
  };
}

// timelineSchema.js keeps its normalizer private, so it is exercised through the
// public migrate -> serialize path that the editor uses on save.
function throughTimelineSchema(value) {
  const timeline = migrateToTimelineV2({ background_isolation: value });
  const manifest = serializeTimelineV2ToManifest(timeline, {});
  return { timeline, manifest };
}

test('subject_points survive the editor-state normalizer unchanged', () => {
  const points = [
    { x: 0.25, y: 0.75, label: 1 },
    { x: 0.5, y: 0.5, label: 0 },
  ];
  const normalized = normalizeBackgroundIsolation(cutout({ subject_points: points }));
  assert.deepEqual(normalized.subject_points, points);
});

test('subject_points round-trip load -> save payload -> reload in editorProjectState', () => {
  const points = [{ x: 0.1, y: 0.9, label: 1 }, { x: 0.6, y: 0.4, label: 1 }];
  const loaded = manifestToEditorState({ background_isolation: cutout({ subject_points: points }) });
  assert.deepEqual(loaded.backgroundIsolation.subject_points, points);

  const payload = editorStateToSavePayload(loaded);
  assert.deepEqual(payload.background_isolation.subject_points, points);

  const reloaded = manifestToEditorState(payload);
  assert.deepEqual(reloaded.backgroundIsolation.subject_points, points);
  assert.deepEqual(serializeRenderFeatures(reloaded).background_isolation.subject_points, points);
});

test('subject_points are clamped, defaulted, capped and cleaned in editorProjectState', () => {
  const noisy = [
    { x: -3, y: 4 },
    { x: '0.5', y: '0.25', label: 0 },
    { x: 'bad', y: 0.5 },
    null,
    ...Array.from({ length: 20 }, (_, index) => ({ x: index / 40, y: 0.5, label: 1 })),
  ];
  const normalized = normalizeBackgroundIsolation(cutout({ subject_points: noisy }));
  assert.equal(normalized.subject_points.length, SUBJECT_POINT_LIMIT);
  assert.deepEqual(normalized.subject_points[0], { x: 0, y: 1, label: 1 });
  assert.deepEqual(normalized.subject_points[1], { x: 0.5, y: 0.25, label: 0 });
  for (const point of normalized.subject_points) {
    assert.ok(point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1);
    assert.ok(point.label === 0 || point.label === 1);
  }
});

test('an emptied or unusable subject_points list is removed instead of saved as []', () => {
  for (const subjectPoints of [[], [null, 'x', { x: 'nope', y: 1 }], 'not-a-list', 7]) {
    const normalized = normalizeBackgroundIsolation(cutout({ subject_points: subjectPoints }));
    assert.equal(Object.hasOwn(normalized, 'subject_points'), false, JSON.stringify(subjectPoints));
    const payload = editorStateToSavePayload({ backgroundIsolation: cutout({ subject_points: subjectPoints }) });
    assert.equal(Object.hasOwn(payload.background_isolation, 'subject_points'), false);
  }
});

test('auto_prompt false is kept, true is the default and a non-boolean fails closed', () => {
  assert.equal(normalizeBackgroundIsolation(cutout({ auto_prompt: false })).auto_prompt, false);
  assert.equal(Object.hasOwn(normalizeBackgroundIsolation(cutout({ auto_prompt: true })), 'auto_prompt'), false);
  assert.equal(normalizeBackgroundIsolation(cutout({ auto_prompt: 'no' })), null);
  assert.equal(normalizeBackgroundIsolation(cutout({ auto_prompt: 0 })), null);
});

test('subject_points do not mutate the caller input and the result is a deep copy', () => {
  const input = cutout({ subject_points: [{ x: 0.3, y: 0.3, label: 1 }] });
  const snapshot = JSON.parse(JSON.stringify(input));
  const normalized = normalizeBackgroundIsolation(input);
  normalized.subject_points[0].x = 0.99;
  assert.deepEqual(input, snapshot);
});

test('subject_points survive timelineSchema migrate -> serialize', () => {
  const points = [{ x: 0.2, y: 0.8, label: 1 }, { x: 0.7, y: 0.1, label: 0 }];
  const { timeline, manifest } = throughTimelineSchema(cutout({ subject_points: points, auto_prompt: false }));
  assert.deepEqual(timeline.backgroundIsolation.subject_points, points);
  assert.equal(timeline.backgroundIsolation.auto_prompt, false);
  assert.deepEqual(manifest.background_isolation.subject_points, points);
  assert.equal(manifest.background_isolation.auto_prompt, false);
  assert.equal(Object.hasOwn(manifest, 'backgroundIsolation'), false);

  const second = throughTimelineSchema(manifest.background_isolation);
  assert.deepEqual(second.manifest.background_isolation, manifest.background_isolation);
});

test('timelineSchema applies the same subject_points cleanup as editorProjectState', () => {
  const noisy = [
    { x: 2, y: -1 },
    { x: 'bad', y: 0.5 },
    { x: '0.4', y: 0.6, label: 0 },
    ...Array.from({ length: 12 }, (_, index) => ({ x: index / 20, y: 0.2 })),
  ];
  const fromEditor = normalizeBackgroundIsolation(cutout({ subject_points: noisy }));
  const fromTimeline = throughTimelineSchema(cutout({ subject_points: noisy })).manifest.background_isolation;
  assert.deepEqual(fromTimeline.subject_points, fromEditor.subject_points);

  const emptied = throughTimelineSchema(cutout({ subject_points: [null, 'x'] })).manifest.background_isolation;
  assert.equal(Object.hasOwn(emptied, 'subject_points'), false);

  assert.equal(
    throughTimelineSchema(cutout({ auto_prompt: 'no' })).manifest.background_isolation,
    undefined,
  );
});

test('a disabled config stays inert and keeps its stored points untouched in both modules', () => {
  const disabled = { schema_version: 1, enabled: false, subject_points: [{ x: 0.5, y: 0.5, label: 1 }] };
  assert.deepEqual(normalizeBackgroundIsolation(disabled), disabled);
  assert.deepEqual(throughTimelineSchema(disabled).manifest.background_isolation, disabled);
});
