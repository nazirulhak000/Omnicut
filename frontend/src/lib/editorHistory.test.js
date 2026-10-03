import test from 'node:test';
import assert from 'node:assert/strict';

import { createEditorHistoryModel, COALESCE_WINDOW_MS } from '../hooks/useEditorHistory.js';


test('drag updates coalesce into one undo step and preserve undo/redo behavior', () => {
  const initial = { clipList: [{ id: 'a', trim_end: 1 }], cuesList: [], style: {} };
  const history = createEditorHistoryModel(initial);

  history.beginDrag();
  history.setSilent((state) => ({
    ...state,
    clipList: [{ ...state.clipList[0], trim_end: 2 }],
  }));
  history.setSilent((state) => ({
    ...state,
    clipList: [{ ...state.clipList[0], trim_end: 3 }],
  }));
  history.endDrag();

  assert.equal(history.canUndo(), true);
  assert.equal(history.undo(), true);
  assert.deepEqual(history.getState(), initial);
  assert.equal(history.canRedo(), true);
  assert.equal(history.redo(), true);
  assert.equal(history.getState().clipList[0].trim_end, 3);
});


test('a drag with no state change does not create a no-op undo step', () => {
  const initial = { clipList: [], cuesList: [], style: {} };
  const history = createEditorHistoryModel(initial);

  history.beginDrag();
  history.endDrag();

  assert.equal(history.canUndo(), false);
});


const counterState = (n) => ({ clipList: [], cuesList: [], style: { n } });
const inc = (state) => counterState(state.style.n + 1);

function clockedHistory(initial) {
  const clock = { t: 1000 };
  const history = createEditorHistoryModel(initial, { now: () => clock.t });
  return { history, clock };
}


test('20 coalesced sets with the same key collapse into one undo step', () => {
  const initial = counterState(0);
  const { history, clock } = clockedHistory(initial);

  for (let i = 0; i < 20; i += 1) {
    assert.equal(history.set(inc, { coalesceKey: 'volume' }), true);
    clock.t += 20;
  }
  assert.equal(history.getState().style.n, 20);

  assert.equal(history.undo(), true);
  assert.deepEqual(history.getState(), initial);
  assert.equal(history.canUndo(), false);

  assert.equal(history.redo(), true);
  assert.equal(history.getState().style.n, 20);
});


test('different coalesce keys create separate undo steps', () => {
  const { history, clock } = clockedHistory(counterState(0));

  history.set(inc, { coalesceKey: 'volume' });
  clock.t += 10;
  history.set(inc, { coalesceKey: 'speed' });
  clock.t += 10;
  history.set(inc, { coalesceKey: 'speed' });

  assert.equal(history.getState().style.n, 3);
  history.undo();
  assert.equal(history.getState().style.n, 1);
  history.undo();
  assert.equal(history.getState().style.n, 0);
  assert.equal(history.canUndo(), false);
});


test('a time gap beyond the window starts a new undo step', () => {
  const { history, clock } = clockedHistory(counterState(0));

  history.set(inc, { coalesceKey: 'volume' });
  clock.t += COALESCE_WINDOW_MS;
  history.set(inc, { coalesceKey: 'volume' });
  clock.t += COALESCE_WINDOW_MS + 1;
  history.set(inc, { coalesceKey: 'volume' });

  assert.equal(history.getState().style.n, 3);
  history.undo();
  assert.equal(history.getState().style.n, 2);
  history.undo();
  assert.equal(history.getState().style.n, 0);
  assert.equal(history.canUndo(), false);
});


test('a legacy set between keyed sets breaks the burst', () => {
  const { history, clock } = clockedHistory(counterState(0));

  history.set(inc, { coalesceKey: 'volume' });
  clock.t += 10;
  history.set(inc);
  clock.t += 10;
  history.set(inc, { coalesceKey: 'volume' });

  history.undo();
  assert.equal(history.getState().style.n, 2);
  history.undo();
  assert.equal(history.getState().style.n, 1);
  history.undo();
  assert.equal(history.getState().style.n, 0);
  assert.equal(history.canUndo(), false);
});


test('undo/redo and reset end a coalescing burst', () => {
  const { history, clock } = clockedHistory(counterState(0));

  history.set(inc, { coalesceKey: 'volume' });
  history.undo();
  history.redo();
  clock.t += 10;
  history.set(inc, { coalesceKey: 'volume' });
  history.undo();
  assert.equal(history.getState().style.n, 1);

  history.reset(counterState(5));
  history.set(inc, { coalesceKey: 'volume' });
  history.undo();
  assert.equal(history.getState().style.n, 5);
  assert.equal(history.canUndo(), false);
});


test('coalescing keeps the 50-step cap and a new key after the cap still works', () => {
  const { history, clock } = clockedHistory(counterState(0));

  for (let i = 0; i < 60; i += 1) {
    history.set(inc, { coalesceKey: `k${i}` });
    clock.t += 10;
  }
  let undone = 0;
  while (history.undo()) undone += 1;
  assert.equal(undone, 50);
  assert.equal(history.getState().style.n, 10);

  // A burst at the cap still counts as a single step.
  const capped = clockedHistory(counterState(0));
  for (let i = 0; i < 50; i += 1) {
    capped.history.set(inc);
  }
  for (let i = 0; i < 10; i += 1) {
    capped.history.set(inc, { coalesceKey: 'volume' });
    capped.clock.t += 10;
  }
  let steps = 0;
  while (capped.history.undo()) steps += 1;
  assert.equal(steps, 50);
  assert.equal(capped.history.getState().style.n, 1);
});


test('legacy set() without options is unchanged and never coalesces', () => {
  const { history, clock } = clockedHistory(counterState(0));

  history.set(inc);
  history.set(inc);
  history.set(inc, {});
  clock.t += 1;
  history.set(inc, { coalesceKey: null });
  assert.equal(history.getState().style.n, 4);

  let steps = 0;
  while (history.undo()) steps += 1;
  assert.equal(steps, 4);
  assert.equal(history.getState().style.n, 0);

  // No-op updates still report false and add no step.
  assert.equal(history.set((state) => state, { coalesceKey: 'x' }), false);
  assert.equal(history.canUndo(), false);
});


test('existing drag coalescing still works alongside keyed sets', () => {
  const { history } = clockedHistory(counterState(0));

  history.set(inc, { coalesceKey: 'volume' });
  history.beginDrag();
  history.setSilent(inc);
  history.setSilent(inc);
  history.endDrag();
  assert.equal(history.getState().style.n, 3);

  history.undo();
  assert.equal(history.getState().style.n, 1);
  history.undo();
  assert.equal(history.getState().style.n, 0);
  assert.equal(history.canUndo(), false);
});
