import test from 'node:test';
import assert from 'node:assert/strict';

import {
  EMPTY_BEAT_GRID,
  beatSnapPoints,
  beatsWithinSpan,
  hasBeats,
  normalizeBeatGrid,
} from './beatGrid.js';

// ---------------------------------------------------------------------------
// normalizeBeatGrid
// ---------------------------------------------------------------------------

test('normalizeBeatGrid reads the API payload shape', () => {
  const grid = normalizeBeatGrid({ bpm: 120, major_beats: [0, 2], minor_beats: [0.5, 1, 1.5] });
  assert.equal(grid.bpm, 120);
  assert.deepEqual(grid.major, [0, 2]);
  assert.deepEqual(grid.minor, [0.5, 1, 1.5]);
});

test('normalizeBeatGrid accepts an already-normalised grid', () => {
  const grid = normalizeBeatGrid({ bpm: 90, major: [1], minor: [2] });
  assert.deepEqual(grid.major, [1]);
  assert.deepEqual(grid.minor, [2]);
});

test('normalizeBeatGrid returns the empty grid for null or undefined', () => {
  for (const input of [null, undefined]) {
    assert.deepEqual(normalizeBeatGrid(input), EMPTY_BEAT_GRID);
  }
});

test('normalizeBeatGrid drops non-numeric and negative timestamps', () => {
  // A NaN would render at left:NaNpx and vanish -- looking like a missing
  // beat rather than bad data, which is much harder to diagnose.
  const grid = normalizeBeatGrid({ major_beats: [1, NaN, 'x', null, -2, 3] });
  assert.deepEqual(grid.major, [1, 3]);
});

test('normalizeBeatGrid does not coerce falsy junk into a beat at zero', () => {
  // Number(null) and Number('') are both 0, so coercing before validating
  // invents a beat at the very start of the timeline -- indistinguishable
  // from a real downbeat once it reaches the snap candidates.
  const grid = normalizeBeatGrid({ major_beats: [null, '', false, undefined] });
  assert.deepEqual(grid.major, []);
});

test('normalizeBeatGrid keeps a genuine beat at zero', () => {
  assert.deepEqual(normalizeBeatGrid({ major_beats: [0, 2] }).major, [0, 2]);
});

test('normalizeBeatGrid sorts timestamps', () => {
  assert.deepEqual(normalizeBeatGrid({ minor_beats: [3, 1, 2] }).minor, [1, 2, 3]);
});

test('normalizeBeatGrid rejects an implausible bpm', () => {
  for (const bpm of [0, -5, NaN, 'fast', null]) {
    assert.equal(normalizeBeatGrid({ bpm }).bpm, null, `bpm ${bpm} should not survive`);
  }
});

test('normalizeBeatGrid tolerates missing lists', () => {
  const grid = normalizeBeatGrid({ bpm: 100 });
  assert.deepEqual(grid.major, []);
  assert.deepEqual(grid.minor, []);
});

// ---------------------------------------------------------------------------
// beatsWithinSpan
// ---------------------------------------------------------------------------

test('beatsWithinSpan keeps only beats inside the timeline', () => {
  // The BGM file outlasts the sequence (the renderer loops it), so beats past
  // the end belong to music the sequence never reaches.
  const grid = { major: [0, 4, 12], minor: [2, 6, 20] };
  const within = beatsWithinSpan(grid, 8);
  assert.deepEqual(within.major, [0, 4]);
  assert.deepEqual(within.minor, [2, 6]);
});

test('beatsWithinSpan includes a beat exactly at the end', () => {
  assert.deepEqual(beatsWithinSpan({ major: [5], minor: [] }, 5).major, [5]);
});

test('beatsWithinSpan returns nothing when there is no timeline', () => {
  const grid = { major: [1, 2], minor: [3] };
  for (const span of [0, -1, NaN, undefined, null]) {
    assert.deepEqual(beatsWithinSpan(grid, span), { major: [], minor: [] });
  }
});

test('beatsWithinSpan returns nothing for a null grid', () => {
  assert.deepEqual(beatsWithinSpan(null, 10), { major: [], minor: [] });
});

test('beatsWithinSpan filters non-finite entries defensively', () => {
  const within = beatsWithinSpan({ major: [1, Infinity, NaN], minor: [] }, 10);
  assert.deepEqual(within.major, [1]);
});

// ---------------------------------------------------------------------------
// beatSnapPoints
// ---------------------------------------------------------------------------

test('beatSnapPoints merges both beat kinds in order', () => {
  const grid = { major: [0, 4], minor: [1, 2, 3] };
  assert.deepEqual(beatSnapPoints(grid, 10), [0, 1, 2, 3, 4]);
});

test('beatSnapPoints de-duplicates repeated timestamps', () => {
  // A duplicated candidate biases the nearest-point search toward that
  // moment for no reason the user can see.
  const grid = { major: [2], minor: [2, 5] };
  assert.deepEqual(beatSnapPoints(grid, 10), [2, 5]);
});

test('beatSnapPoints respects the span limit', () => {
  assert.deepEqual(beatSnapPoints({ major: [1, 99], minor: [2] }, 5), [1, 2]);
});

test('beatSnapPoints is empty without a grid', () => {
  assert.deepEqual(beatSnapPoints(null, 10), []);
});

test('markers and snap targets stay consistent', () => {
  // The guarantee that makes the guides trustworthy: everything drawn is
  // snappable, and everything snappable is drawn. A marker with no snap (or
  // the reverse) teaches the user to distrust the timeline.
  const grid = { major: [0, 4, 12], minor: [2, 6, 20] };
  const span = 8;
  const { major, minor } = beatsWithinSpan(grid, span);
  const drawn = [...new Set([...major, ...minor])].sort((a, b) => a - b);
  assert.deepEqual(beatSnapPoints(grid, span), drawn);
});

// ---------------------------------------------------------------------------
// hasBeats
// ---------------------------------------------------------------------------

test('hasBeats distinguishes an analysed-but-empty grid from a real one', () => {
  assert.equal(hasBeats(null), false);
  assert.equal(hasBeats(EMPTY_BEAT_GRID), false);
  assert.equal(hasBeats({ major: [1], minor: [] }), true);
  assert.equal(hasBeats({ major: [], minor: [1] }), true);
});

test('hasBeats tolerates a malformed grid', () => {
  assert.equal(hasBeats({}), false);
});
