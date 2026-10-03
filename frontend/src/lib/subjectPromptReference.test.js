import test from 'node:test';
import assert from 'node:assert/strict';
import { subjectPromptReference } from './subjectPromptReference.js';
import { buildSegments } from './timelineMath.js';

test('a later moving frame picks from the worker window first frame', () => {
  const segments = buildSegments([{ id: 'a', source_path: 'a.mp4', trim_start: 3, trim_end: 7, speed: 2 }]);
  assert.deepEqual(subjectPromptReference(segments, 1.5), {
    clipId: 'a', sourcePath: 'a.mp4', sourceStart: 3, timelineTime: 0,
  });
});

test('overlapping trims share the earliest worker prompt frame', () => {
  const segments = buildSegments([
    { id: 'later', source_path: 'a.mp4', trim_start: 2, trim_end: 5 },
    { id: 'first', source_path: 'a.mp4', trim_start: 1, trim_end: 4 },
  ]);
  assert.deepEqual(subjectPromptReference(segments, 1), {
    clipId: 'first', sourcePath: 'a.mp4', sourceStart: 1, timelineTime: 3,
  });
  const active = subjectPromptReference(segments, 1, { config: {
    scope_mode: 'behind_text_windows', active_clip_ids: ['later'],
  } });
  assert.equal(active.clipId, 'later');
  assert.equal(active.sourceStart, 2);
  const bothActive = subjectPromptReference(segments, 1, { config: {
    scope_mode: 'behind_text_windows', active_clip_ids: ['later', 'first'],
  } });
  assert.equal(bothActive.clipId, 'later');
  assert.equal(bothActive.sourceStart, 2);
});

test('ambiguous transitions and unresolved source windows cannot supply prompts', () => {
  const segments = buildSegments([
    { id: 'a', source_path: 'a.mp4', trim_end: 2 },
    { id: 'b', source_path: 'b.mp4', trim_end: 2, transition_in: 'fade', transition_duration: 0.5 },
  ]);
  assert.equal(subjectPromptReference(segments, 1.8), null);
  assert.equal(subjectPromptReference(buildSegments([{ id: 'a', source_path: 'a.mp4' }]), 0), null);
});
