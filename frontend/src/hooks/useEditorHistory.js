import { useCallback, useRef, useState } from 'react';

const MAX_STEPS = 50;

const clone = (v) => (typeof structuredClone === 'function' ? structuredClone(v) : JSON.parse(JSON.stringify(v)));

/**
 * Undo/redo over one editor state object ({ clipList, cuesList, style }).
 *
 * Two things this has to get right:
 *
 * 1. Drag coalescing. A trim or reorder drag fires dozens of updates; each
 *    becoming its own undo step would make Ctrl+Z useless. Continuous
 *    gestures call beginDrag() once, setSilent() as they move, then
 *    endDrag(), which pushes the single pre-drag snapshot.
 *
 * 2. No ref mutation inside a setState updater. React (StrictMode, and
 *    concurrent re-renders generally) may invoke an updater more than once,
 *    and a stack pop/push inside one silently corrupts history: undo popped
 *    the snapshot on the first invocation, then the second saw an empty
 *    stack and returned the unchanged state -- history drained while nothing
 *    was actually undone. Everything here reads a state mirror and calls
 *    setState with a plain value instead.
 */
export function useEditorHistory(initialState) {
  const [state, setStateRaw] = useState(initialState);
  const stateRef = useRef(initialState);
  const undoStack = useRef([]);
  const redoStack = useRef([]);
  const dragSnapshot = useRef(null);
  const [, bump] = useState(0);

  const commitState = (next) => {
    stateRef.current = next;
    setStateRaw(next);
    bump((n) => n + 1);
  };

  const pushUndo = (snapshot) => {
    undoStack.current.push(snapshot);
    if (undoStack.current.length > MAX_STEPS) undoStack.current.shift();
    redoStack.current = [];
  };

  const resolve = (updater) => (
    typeof updater === 'function' ? updater(stateRef.current) : updater
  );

  /** Discrete change -- becomes one undo step. */
  const set = useCallback((updater) => {
    const prev = stateRef.current;
    const next = resolve(updater);
    if (next === prev) return;
    pushUndo(clone(prev));
    commitState(next);
  }, []);

  /** Mid-gesture change -- no undo step of its own. */
  const setSilent = useCallback((updater) => {
    const next = resolve(updater);
    if (next === stateRef.current) return;
    commitState(next);
  }, []);

  const beginDrag = useCallback(() => {
    if (dragSnapshot.current === null) dragSnapshot.current = clone(stateRef.current);
  }, []);

  const endDrag = useCallback(() => {
    if (dragSnapshot.current === null) return;
    pushUndo(dragSnapshot.current);
    dragSnapshot.current = null;
    bump((n) => n + 1);
  }, []);

  const undo = useCallback(() => {
    const previous = undoStack.current.pop();
    if (previous === undefined) return;
    redoStack.current.push(clone(stateRef.current));
    commitState(previous);
  }, []);

  const redo = useCallback(() => {
    const next = redoStack.current.pop();
    if (next === undefined) return;
    undoStack.current.push(clone(stateRef.current));
    commitState(next);
  }, []);

  /** Loading a different project starts a fresh history. */
  const reset = useCallback((nextState) => {
    undoStack.current = [];
    redoStack.current = [];
    dragSnapshot.current = null;
    commitState(nextState);
  }, []);

  return {
    state,
    set,
    setSilent,
    beginDrag,
    endDrag,
    undo,
    redo,
    reset,
    canUndo: undoStack.current.length > 0,
    canRedo: redoStack.current.length > 0,
  };
}

export default useEditorHistory;
