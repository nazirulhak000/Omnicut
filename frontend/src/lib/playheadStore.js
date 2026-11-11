/**
 * The editor's live playhead, outside React state.
 *
 * During playback the player reports the time ~20 times a second. Keeping
 * that in EditorShell's useState re-rendered the whole editor (timeline, asset
 * panel, inspector, toolbar) on every report. The store lets the few things
 * that must follow the playhead subscribe to it, while everything that only
 * needs the time when the user acts reads it with get().
 */
export function createPlayheadStore(initial = 0) {
  let value = initial;
  const listeners = new Set();
  return {
    get: () => value,
    set(next) {
      if (next === value) return;
      value = next;
      listeners.forEach((listener) => listener());
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
