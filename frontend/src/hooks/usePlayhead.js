import { createContext, useCallback, useContext, useEffect, useRef, useSyncExternalStore } from 'react';

/**
 * EditorShell provides its playhead store here. Components keep their
 * `playhead` prop -- the *settled* time (it does not change while playing) --
 * and use these hooks for the two cases that need the live time. Without a
 * provider (fixtures, tests) both hooks fall back to the prop, which is then
 * the live time, exactly as before.
 */
export const PlayheadContext = createContext(null);

const noopSubscribe = () => () => {};

/** Live playhead for something the user watches move (needle, karaoke line). */
export function useLivePlayhead(fallback = 0) {
  const store = useContext(PlayheadContext);
  const live = useSyncExternalStore(
    store ? store.subscribe : noopSubscribe,
    store ? store.get : () => fallback,
  );
  return store ? live : fallback;
}

/**
 * A value derived from the live playhead. The component re-renders only when
 * the derived value changes (e.g. "which cue is under the playhead"), not on
 * every tick. `select` must return a primitive or a stable reference.
 */
export function useLivePlayheadSelector(select, fallback = 0) {
  const store = useContext(PlayheadContext);
  const selectRef = useRef(select);
  selectRef.current = select;
  const getSnapshot = useCallback(
    () => selectRef.current(store ? store.get() : fallback),
    [store, fallback],
  );
  return useSyncExternalStore(store ? store.subscribe : noopSubscribe, getSnapshot);
}

/**
 * Run `effect(time)` whenever the live playhead changes, without re-rendering
 * the component (scroll-follow, auto-scroll to the spoken line). It also runs
 * after mount and whenever a value in `deps` changes, like the useEffect it
 * replaces: `useEffect(() => ..., [playhead, ...deps])`.
 */
export function usePlayheadEffect(effect, fallback = 0, deps = []) {
  const store = useContext(PlayheadContext);
  const effectRef = useRef(effect);
  effectRef.current = effect;
  useEffect(() => {
    if (!store) return undefined;
    return store.subscribe(() => effectRef.current(store.get()));
  }, [store]);
  useEffect(() => {
    effectRef.current(store ? store.get() : fallback);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store, store ? null : fallback, ...deps]);
}

/** Stable function returning the playhead "right now", for event handlers. */
export function usePlayheadGetter(fallback = 0) {
  const store = useContext(PlayheadContext);
  const fallbackRef = useRef(fallback);
  fallbackRef.current = fallback;
  return useCallback(() => (store ? store.get() : fallbackRef.current), [store]);
}
