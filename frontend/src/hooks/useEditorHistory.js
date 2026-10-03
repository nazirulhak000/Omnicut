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
 *
 * Slider-style bursts can opt into coalescing with set(updater, { coalesceKey }):
 * consecutive sets with the same key, each within COALESCE_WINDOW_MS of the
 * previous one, share the single undo step pushed by the first set. Undo then
 * returns to the state before the first change of the burst. A set may pass
 * { coalesceWindowMs } to widen the window for its own burst.
 */
export const COALESCE_WINDOW_MS = 400;

export function createEditorHistoryModel(initialState, options = {}) {
  const now = options.now || (() => Date.now());
  const coalesceWindowMs = options.coalesceWindowMs ?? COALESCE_WINDOW_MS;
  let state = initialState;
  const undoStack = [];
  const redoStack = [];
  let dragSnapshot = null;
  let dragActive = false;
  // { key, at } of the last set() that owns the current top undo entry.
  let lastCoalesce = null;

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

    set(updater, setOptions) {
      const previous = state;
      const next = resolve(updater);
      if (next === previous) return false;
      const key = setOptions && setOptions.coalesceKey;
      const hasKey = key !== undefined && key !== null;
      const at = hasKey ? now() : 0;
      // A burst may ask for a wider window than a slider's (typing a caption).
      const windowMs = Number.isFinite(setOptions && setOptions.coalesceWindowMs)
        ? setOptions.coalesceWindowMs
        : coalesceWindowMs;
      if (
        hasKey
        && lastCoalesce
        && lastCoalesce.key === key
        && at - lastCoalesce.at <= windowMs
        && undoStack.length > 0
      ) {
        // Same burst: keep the existing pre-burst undo entry, only advance state.
        lastCoalesce.at = at;
        state = next;
        return true;
      }
      pushUndo(previous);
      lastCoalesce = hasKey ? { key, at } : null;
      state = next;
      return true;
    },

    setSilent(updater) {
      const next = resolve(updater);
      if (next === state) return false;
      lastCoalesce = null;
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
      lastCoalesce = null;
      dragSnapshot = null;
      dragActive = false;
      return changed;
    },

    undo() {
      const previous = undoStack.pop();
      if (previous === undefined) return false;
      redoStack.push(state);
      lastCoalesce = null;
      state = previous;
      return true;
    },

    redo() {
      const next = redoStack.pop();
      if (next === undefined) return false;
      undoStack.push(state);
      lastCoalesce = null;
      state = next;
      return true;
    },

    reset(nextState) {
      undoStack.length = 0;
      redoStack.length = 0;
      dragSnapshot = null;
      dragActive = false;
      lastCoalesce = null;
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

  /**
   * Discrete change -- becomes one undo step. Pass { coalesceKey } for slider
   * bursts: same key within the coalesce window shares one undo step.
   */
  const set = useCallback((updater, options) => {
    if (model.set(updater, options)) syncState();
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
