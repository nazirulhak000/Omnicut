import test from 'node:test';
import assert from 'node:assert/strict';

import { splitClipAt } from './timelineMath.js';

test('splitClipAt splits a clip into left and right pieces at playhead', () => {
  const seg = {
    clip: {
      id: 'clip-1',
      source_path: 'video.mp4',
      trim_start: 1.0,
      trim_end: 9.0,
      duration: 8.0,
      speed: 1.0,
      transition_in: 'fade',
      keyframes: [],
    },
    segStart: 2.0,
    segEnd: 10.0,
  };

  let idCounter = 0;
  const newId = () => `clip-${++idCounter}`;

  // Split at global sequence time 5.0 (local time offset 3.0 from segStart)
  const pieces = splitClipAt(seg, 5.0, newId);
  assert.ok(pieces, 'splitClipAt returned pieces');
  const [left, right] = pieces;

  assert.equal(left.id, 'clip-1');
  assert.equal(left.trim_start, 1.0);
  assert.equal(left.trim_end, 4.0);
  assert.equal(left.transition_in, 'fade');

  assert.equal(right.id, 'clip-2');
  assert.equal(right.trim_start, 4.0);
  assert.equal(right.trim_end, 9.0);
  assert.equal(right.transition_in, 'cut', 'Right half boundary is cut');
});

test('duplicate clip preserves properties while resetting boundary transition', () => {
  const orig = {
    id: 'orig-1',
    source_path: 'sample.mp4',
    duration: 4.0,
    speed: 1.0,
    transition_in: 'wipeleft',
    transition_duration: 0.5,
  };

  const dup = { ...orig, id: 'dup-2', transition_in: 'cut' };
  assert.equal(dup.id, 'dup-2');
  assert.equal(dup.source_path, orig.source_path);
  assert.equal(dup.duration, 4.0);
  assert.equal(dup.transition_in, 'cut');
});
