import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TIMELINE_DRAG_THRESHOLD_PX,
  beginDragAfterThreshold,
  capturePointer,
  releasePointer,
} from './timelineDragLifecycle.js';

test('beginDragAfterThreshold waits for 3px and starts exactly once', () => {
  const state = { startX: 100, moved: false };
  let begins = 0;

  assert.equal(TIMELINE_DRAG_THRESHOLD_PX, 3);
  assert.equal(beginDragAfterThreshold(state, 102, () => { begins += 1; }), false);
  assert.equal(state.moved, false);
  assert.equal(beginDragAfterThreshold(state, 103, () => { begins += 1; }), true);
  assert.equal(beginDragAfterThreshold(state, 110, () => { begins += 1; }), true);
  assert.equal(state.moved, true);
  assert.equal(begins, 1);
});

test('pointer lifecycle helpers tolerate synthetic events and forward capture calls', () => {
  const calls = [];
  const event = {
    pointerId: 7,
    currentTarget: {
      setPointerCapture: (id) => calls.push(['capture', id]),
      releasePointerCapture: (id) => calls.push(['release', id]),
    },
  };

  capturePointer(event);
  releasePointer(event);
  capturePointer({});
  releasePointer({});
  assert.deepEqual(calls, [['capture', 7], ['release', 7]]);
});
