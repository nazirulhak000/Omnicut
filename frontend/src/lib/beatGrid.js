/**
 * Beat grid helpers shared by the timeline's markers and its drag snapping.
 *
 * The grid comes from GET /api/audio/beats, which analyses the BGM file. That
 * file is usually longer than the sequence (the renderer loops it), and a
 * failed or partial analysis can hand back values that are not usable times.
 * Both consumers therefore need the same filtering, and they need it to agree:
 * a marker drawn where nothing snaps -- or a snap target with no marker -- is
 * worse than showing nothing, because it teaches the user to distrust the
 * guides.
 */

/** Shape returned for "no beats", so callers never branch on null lists. */
export const EMPTY_BEAT_GRID = { bpm: null, major: [], minor: [] };

/**
 * Normalise the API payload into `{ bpm, major, minor }`.
 *
 * Anything non-numeric is dropped rather than coerced: a NaN reaching the
 * timeline would be rendered at `left: NaNpx` and silently vanish, which
 * looks like a missing beat rather than bad data.
 */
export function normalizeBeatGrid(payload) {
  if (!payload) return { ...EMPTY_BEAT_GRID };
  // Only real numbers survive. Coercing first would turn `null`, `''` and
  // `false` into 0 -- a phantom beat at the very start of the timeline, which
  // reads as a genuine snap target rather than as dropped data.
  const clean = (list) => (Array.isArray(list) ? list : [])
    .filter((t) => typeof t === 'number' && Number.isFinite(t) && t >= 0)
    .sort((a, b) => a - b);
  const bpm = Number(payload.bpm);
  return {
    bpm: Number.isFinite(bpm) && bpm > 0 ? bpm : null,
    major: clean(payload.major_beats ?? payload.major),
    minor: clean(payload.minor_beats ?? payload.minor),
  };
}

/**
 * Beats that fall inside `span` seconds.
 *
 * `span` is the visible extent of the timeline (the longer of the sequence and
 * the audio bed). A beat past it belongs to part of the music the sequence
 * never reaches, so it is neither drawn nor offered as a snap target.
 *
 * A span of 0 or less yields nothing: with no timeline there is nowhere for a
 * marker to be.
 */
export function beatsWithinSpan(grid, span) {
  const limit = Number(span);
  if (!grid || !Number.isFinite(limit) || limit <= 0) {
    return { major: [], minor: [] };
  }
  const within = (list) => (Array.isArray(list) ? list : [])
    .filter((t) => Number.isFinite(t) && t >= 0 && t <= limit);
  return { major: within(grid.major), minor: within(grid.minor) };
}

/**
 * Every in-range beat as one flat, sorted, de-duplicated list of snap targets.
 *
 * De-duplication matters because major and minor are disjoint by construction
 * server-side, but a caller merging grids (or a future change to the split)
 * could repeat a timestamp, and a duplicated candidate biases the nearest-
 * point search toward that moment for no reason the user can see.
 */
export function beatSnapPoints(grid, span) {
  const { major, minor } = beatsWithinSpan(grid, span);
  return [...new Set([...major, ...minor])].sort((a, b) => a - b);
}

/** True when the grid holds at least one beat worth showing a control for. */
export function hasBeats(grid) {
  if (!grid) return false;
  return (grid.major?.length || 0) + (grid.minor?.length || 0) > 0;
}
