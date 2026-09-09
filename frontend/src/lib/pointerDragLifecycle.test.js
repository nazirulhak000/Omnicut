import test from 'node:test';
import assert from 'node:assert/strict';
import { bindWindowPointerLifecycle } from './pointerDragLifecycle.js';

test('pointer lifecycle binds and cleans up move, up, and cancel listeners', () => {
  const added = [];
  const removed = [];
  const target = {
    addEventListener: (...args) => added.push(args),
    removeEventListener: (...args) => removed.push(args),
  };
  const onMove = () => {};
  const onUp = () => {};

  const cleanup = bindWindowPointerLifecycle(onMove, onUp, target);
  assert.deepEqual(added, [
    ['pointermove', onMove],
    ['pointerup', onUp],
    ['pointercancel', onUp],
  ]);

  cleanup();
  assert.deepEqual(removed, added);
});
