import { useCallback, useState } from 'react';

const MAX_STEPS = 50;

/**
 * Undo/redo over one editor state object ({ clipList, cuesList, style }).
 *
 * Editor commands produce immutable top-level snapshots. The history model
 * keeps those snapshots by reference instead of deep-cloning every edit,
 * while still isolating the undo/redo stacks from later state replacement.
 *
 * Two things this has to get right:
 *
 * 1. Drag coalescing. A trim or reorder drag fires dozens of updates; each
 *    becoming its own undo step would make Ctrl+Z useless. Continuous
 *    gestures call beginDrag() once, setSilent() as they move, then
 *    endDrag(), which pushes the single pre-drag snapshot.
 *
 * 2. No ref mutation inside a setState updater. React (StrictMode, and
 *    concurrent re-renders generally) may invoke an updater more than once.
 *    The model resolves updates against its state mirror and the hook passes
 *    plain values to React, so history mutation happens exactly once.
 */
export function createEditorHistoryModel(initialState) {
  let state = initialState;
  const undoStack = [];
  const redoStack = [];
  let dragSnapshot = null;
  let dragActive = false;

  const resolve = (updater) => (
    typeof updater === 'function' ? updater(state) : updater
  );

  const pushUndo = (snapshot) => {
    undoStack.push(snapshot);
    if (undoStack.length > MAX_STEPS) undoStack.shift();
    redoStack.length = 0;
  };

  return {
    getState() {
      return state;
    },

    set(updater) {
      const previous = state;
      const next = resolve(updater);
      if (next === previous) return false;
      pushUndo(previous);
      state = next;
      return true;
    },

    setSilent(updater) {
      const next = resolve(updater);
      if (next === state) return false;
      state = next;
      return true;
    },

    beginDrag() {
      if (dragActive) return;
      dragActive = true;
      dragSnapshot = state;
    },

    endDrag() {
      if (!dragActive) return false;
      const changed = state !== dragSnapshot;
      if (changed) pushUndo(dragSnapshot);
      dragSnapshot = null;
      dragActive = false;
      return changed;
    },

    undo() {
      const previous = undoStack.pop();
      if (previous === undefined) return false;
      redoStack.push(state);
      state = previous;
      return true;
    },

    redo() {
      const next = redoStack.pop();
      if (next === undefined) return false;
      undoStack.push(state);
      state = next;
      return true;
    },

    reset(nextState) {
      undoStack.length = 0;
      redoStack.length = 0;
      dragSnapshot = null;
      dragActive = false;
      state = nextState;
    },

    canUndo() {
      return undoStack.length > 0;
    },

    canRedo() {
      return redoStack.length > 0;
    },
  };
}

export function useEditorHistory(initialState) {
  const [state, setStateRaw] = useState(initialState);
  const [model] = useState(() => createEditorHistoryModel(initialState));
  const [, bump] = useState(0);

  const syncState = useCallback(() => {
    setStateRaw(model.getState());
  }, [model]);

  /** Discrete change -- becomes one undo step. */
  const set = useCallback((updater) => {
    if (model.set(updater)) syncState();
  }, [model, syncState]);

  /** Mid-gesture change -- no undo step of its own. */
  const setSilent = useCallback((updater) => {
    if (model.setSilent(updater)) syncState();
  }, [model, syncState]);

  const beginDrag = useCallback(() => {
    model.beginDrag();
  }, [model]);

  const endDrag = useCallback(() => {
    // The state itself does not change here, but the undo affordance does.
    if (model.endDrag()) bump((n) => n + 1);
  }, [model]);

  const undo = useCallback(() => {
    if (model.undo()) syncState();
  }, [model, syncState]);

  const redo = useCallback(() => {
    if (model.redo()) syncState();
  }, [model, syncState]);

  /** Loading a different project starts a fresh history. */
  const reset = useCallback((nextState) => {
    model.reset(nextState);
    setStateRaw(nextState);
    bump((n) => n + 1);
  }, [model]);
  const canUndo = model.canUndo();
  const canRedo = model.canRedo();

  return {
    state,
    set,
    setSilent,
    beginDrag,
    endDrag,
    undo,
    redo,
    reset,
    canUndo,
    canRedo,
  };
}

export default useEditorHistory;
