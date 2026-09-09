import test from 'node:test';
import assert from 'node:assert/strict';

import { createEditorHistoryModel } from '../hooks/useEditorHistory.js';


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
