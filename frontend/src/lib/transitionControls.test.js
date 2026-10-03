import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  MIN_TRANSITION_DURATION,
  TRANSITION_POPOVER_OPTIONS,
  boundTransitionDuration,
  clampTransitionDuration,
  formatTransitionDuration,
} from './transitionControls.js';
import { MAX_TRANSITION_DURATION, TRANSITIONS } from './timelineMath.js';

const read = (relative) => readFileSync(fileURLToPath(new URL(relative, import.meta.url)), 'utf-8');

test('popover offers every transition the renderer executes (L5-03)', () => {
  const pySource = read('../../../scripts/video_editor.py');
  const block = pySource.match(/XFADE_TRANSITIONS = \(([\s\S]*?)\)/)[1];
  const backendIds = [...block.matchAll(/"([a-z]+)"/g)].map((m) => m[1]);
  assert.equal(backendIds.length, 14);
  assert.deepEqual(TRANSITION_POPOVER_OPTIONS.map((t) => t.id), backendIds);
  assert.equal(TRANSITION_POPOVER_OPTIONS, TRANSITIONS);
});

test('Timeline popover renders the full list, not a slice', () => {
  const timeline = read('../components/editor/Timeline.jsx');
  assert.ok(timeline.includes('TRANSITION_POPOVER_OPTIONS.map('));
  assert.ok(!/TRANSITIONS\.slice\(/.test(timeline));
  assert.ok(timeline.includes('<TransitionDurationControl'));
});

test('duration range matches video_editor.py normalize_transitions (L5-04)', () => {
  const pySource = read('../../../scripts/video_editor.py');
  assert.ok(pySource.includes('dur = min(MAX_TRANSITION_DURATION, max(0.1, dur))'));
  assert.equal(MIN_TRANSITION_DURATION, 0.1);
  assert.equal(MAX_TRANSITION_DURATION, 2.0);
});

test('clampTransitionDuration bounds and snaps to the 0.05 s step', () => {
  assert.equal(clampTransitionDuration(0.01), 0.1);
  assert.equal(clampTransitionDuration(5), 2.0);
  assert.equal(clampTransitionDuration(0.35), 0.35);
  assert.equal(clampTransitionDuration(0.33), 0.35);
  assert.equal(clampTransitionDuration(1.5), 1.5);
  assert.equal(clampTransitionDuration('0.25'), 0.25);
  assert.equal(clampTransitionDuration(undefined), 0.4);
});

test('displayed duration is the value the render uses, unsnapped', () => {
  assert.equal(boundTransitionDuration(0.33), 0.33);
  assert.equal(formatTransitionDuration(0.33), '0.33s');
  assert.equal(formatTransitionDuration(0.25), '0.25s');
  assert.equal(formatTransitionDuration(9), '2.00s');
});
