/**
 * Time maps for "cut the voiceover" (manifest `voice_edit`) -- JS side.
 *
 * Mirror of scripts/voice_cut_map.py (the two files are compared value by value
 * by tests/test_voice_cut_map_parity.py, 500 seeded cut sets). The voice file
 * is never touched (decision D1 = B of _Docs/Plans/PLAN_RIPPLE_ANCHOR_20261004.md):
 * the manifest keeps `voice_edit.cuts`, spans of the ORIGINAL file, and the
 * mix cuts them out with ffmpeg `atrim`.
 *
 * Two clocks:
 *   u = time in the original voice file (source time, seconds)
 *   t = program time = timeline time the user sees after the cuts
 *
 * Function pairs (Python snake_case <-> JS camelCase):
 *   normalize_cuts     <-> normalizeCuts(cuts, sourceDuration)
 *   keep_ranges        <-> keepRanges(cuts, sourceDuration)
 *   source_to_program  <-> sourceToProgram(u, cuts)
 *   program_to_source  <-> programToSource(t, cuts)
 *   effective_duration <-> effectiveDuration(cuts, sourceDuration)
 *   shift_time         <-> shiftTime(t, t0, t1)
 *
 * The ORDER of every float operation is part of the contract (sums accumulate
 * in the documented order) so both sides produce identical doubles. Rounding is
 * `Math.floor(x * 30 + 0.5) / 30` -- ties go up, the same as
 * timelineMath.js `sequenceFrameIndex` and Python `snap_to_frame`.
 *
 * Cuts are `{id, start, end, reason}` in source seconds; keys other than
 * start/end ride along untouched. keepRanges items are `{srcStart, srcEnd,
 * progStart}` here and `{src_start, src_end, prog_start}` in Python.
 */

export const VOICE_CUT_FPS = 30;

// Below one sample of any rate in use (24k / 44.1k / 48k): float noise only.
export const VOICE_CUT_EPS = 1e-9;

/** Remaining voice after the cuts may not be shorter than this (== Python MIN_REMAINING_SECONDS). */
export const MIN_REMAINING_SECONDS = 1.0;

function finiteNumber(value) {
  // Python `float()` takes numbers, booleans and numeric strings and refuses
  // None / containers; JS Number() would turn null/''/[] into 0, so gate first.
  let number;
  if (typeof value === 'number') number = value;
  else if (typeof value === 'boolean') number = value ? 1 : 0;
  else if (typeof value === 'string') {
    if (value.trim() === '') return null;
    number = Number(value);
  } else return null;
  return Number.isFinite(number) ? number : null;
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/**
 * Nearest frame, ties up: `floor(x * fps + 0.5) / fps`. Non-finite / non-numeric
 * input gives 0 and the result is never -0.
 *
 *   snapToFrameGrid(2.01) === 2
 *   snapToFrameGrid(2.49) === 2.5
 *   snapToFrameGrid(1 / 60) === 0.03333333333333333   // half a frame rounds up
 */
export function snapToFrameGrid(seconds, fps = VOICE_CUT_FPS) {
  const value = finiteNumber(seconds);
  if (value === null) return 0;
  return Math.floor(value * fps + 0.5) / fps + 0;
}

/**
 * Standard form of a cut list: snap to the 1/30 grid, clamp to
 * [0, sourceDuration], drop empty spans, sort by (start, end), merge spans that
 * overlap or touch (the first span keeps its id/reason, end = max of the two).
 *
 * Contract (same as Python normalize_cuts):
 *  - entries that are not objects, or whose start/end are not finite numbers, are skipped silently
 *  - per entry: s = snap(start), e = snap(end), s = max(s, 0), e = min(e, sourceDuration),
 *    dropped when e - s < 1e-9 (an end clamped to sourceDuration may be off-grid)
 *  - merge when next.start <= cur.end + 1e-9
 *  - sourceDuration not a number > 0 -> []
 *  - returns new objects, never mutates the input, idempotent
 *
 * Examples (sourceDuration = 6.0):
 *   normalizeCuts([{id:'a', start:2.01, end:2.49}], 6.0)           -> [{id:'a', start:2, end:2.5}]
 *   normalizeCuts([{id:'a', start:1, end:2}, {id:'b', start:1.5, end:3}], 6.0)
 *                                                                  -> [{id:'a', start:1, end:3}]   // overlap merges
 *   normalizeCuts([{id:'a', start:5.5, end:9}], 6.0)               -> [{id:'a', start:5.5, end:6}]  // clamped to the file end
 *   normalizeCuts([{id:'a', start:1, end:1.01}], 6.0)              -> []                           // empty after snapping
 */
export function normalizeCuts(cuts, sourceDuration) {
  const duration = finiteNumber(sourceDuration);
  if (duration === null || duration <= 0) return [];
  const items = [];
  for (const cut of Array.isArray(cuts) ? cuts : []) {
    if (!isRecord(cut)) continue;
    const rawStart = finiteNumber(cut.start);
    const rawEnd = finiteNumber(cut.end);
    if (rawStart === null || rawEnd === null) continue;
    const start = Math.max(snapToFrameGrid(rawStart), 0);
    const end = Math.min(snapToFrameGrid(rawEnd), duration);
    if (end - start < VOICE_CUT_EPS) continue;
    items.push({ ...cut, start, end });
  }
  items.sort((a, b) => (a.start - b.start) || (a.end - b.end));
  const merged = [];
  for (const item of items) {
    const last = merged[merged.length - 1];
    if (last && item.start <= last.end + VOICE_CUT_EPS) {
      last.end = Math.max(last.end, item.end);
    } else {
      merged.push(item);
    }
  }
  return merged;
}

/**
 * Spans of the source file that SURVIVE the cuts, with where each one lands on
 * the program clock: `[{srcStart, srcEnd, progStart}]`.
 *
 * Contract: normalizeCuts first (idempotent); walk from cursor = 0; every cut
 * with `cut.start - cursor >= 1e-9` yields `{srcStart: cursor, srcEnd: cut.start,
 * progStart: prog}` then `prog += srcEnd - srcStart`, `cursor = cut.end`; finally
 * `sourceDuration - cursor >= 1e-9` yields the tail span. progStart is a running
 * sum in that order only. Everything cut -> []; invalid duration -> [].
 *
 * Examples (sourceDuration = 6.0):
 *   keepRanges([{start:2, end:2.5}], 6.0)
 *     -> [{srcStart:0, srcEnd:2, progStart:0}, {srcStart:2.5, srcEnd:6, progStart:2}]
 *   keepRanges([], 6.0)                      -> [{srcStart:0, srcEnd:6, progStart:0}]
 *   keepRanges([{start:0, end:1}], 6.0)      -> [{srcStart:1, srcEnd:6, progStart:0}]   // head cut
 */
export function keepRanges(cuts, sourceDuration) {
  const duration = finiteNumber(sourceDuration);
  if (duration === null || duration <= 0) return [];
  const ranges = [];
  let cursor = 0;
  let prog = 0;
  for (const cut of normalizeCuts(cuts, duration)) {
    if (cut.start - cursor >= VOICE_CUT_EPS) {
      ranges.push({ srcStart: cursor, srcEnd: cut.start, progStart: prog });
      prog += cut.start - cursor;
    }
    cursor = cut.end;
  }
  if (duration - cursor >= VOICE_CUT_EPS) {
    ranges.push({ srcStart: cursor, srcEnd: duration, progStart: prog });
  }
  return ranges;
}

/**
 * Length after the cuts: `sourceDuration - sum(end - start)` of the normalized
 * cuts, summed from 0 in normalizeCuts order, floor 0, never rounded (a 31.2 s
 * file is not a whole number of frames). Invalid duration -> 0.
 *
 *   effectiveDuration([{start:2, end:2.5}], 6.0) === 5.5
 *   effectiveDuration([], 6.0) === 6
 */
export function effectiveDuration(cuts, sourceDuration) {
  const duration = finiteNumber(sourceDuration);
  if (duration === null || duration <= 0) return 0;
  let removed = 0;
  for (const cut of normalizeCuts(cuts, duration)) removed += cut.end - cut.start;
  return Math.max(0, duration - removed);
}

/**
 * Source time u -> program time t. `cuts` MUST be normalized already (sorted,
 * disjoint -- not re-checked). Walk the cuts with removed = 0:
 *   u <= cut.start -> stop;  u >= cut.end -> removed += cut.end - cut.start;
 *   inside the cut -> collapse to the join: return cut.start - removed.
 * Returns `u - removed`. Continuous at cut edges, never decreasing in u.
 *
 * Examples (cut [2.0, 2.5]):
 *   sourceToProgram(1.0, cuts) === 1      // before the cut: unchanged
 *   sourceToProgram(2.25, cuts) === 2     // inside: collapses onto the join
 *   sourceToProgram(3.0, cuts) === 2.5    // after: pulled in by 0.5
 */
export function sourceToProgram(u, cuts) {
  const value = finiteNumber(u);
  if (value === null) return 0;
  let removed = 0;
  for (const cut of Array.isArray(cuts) ? cuts : []) {
    const { start, end } = cut;
    if (value <= start) break;
    if (value >= end) removed += end - start;
    else return start - removed;
  }
  return value - removed;
}

/**
 * Program time t -> the source time u whose audio plays there. `cuts` MUST be
 * normalized. Walk with removed = 0; the cut sits at pos = cut.start - removed
 * on the program clock: t >= pos -> removed += cut.end - cut.start (a t exactly
 * on the join belongs to the AFTER side, u = cut.end); t < pos -> stop.
 * Returns `t + removed`. So sourceToProgram(programToSource(t)) === t; the other
 * direction maps a u inside a cut (or on its left edge) to the cut's right edge.
 *
 * Examples (cut [2.0, 2.5]):
 *   programToSource(1.0, cuts) === 1
 *   programToSource(2.0, cuts) === 2.5    // on the join -> the far side
 *   programToSource(2.5, cuts) === 3
 */
export function programToSource(t, cuts) {
  const value = finiteNumber(t);
  if (value === null) return 0;
  let removed = 0;
  for (const cut of Array.isArray(cuts) ? cuts : []) {
    if (value >= cut.start - removed) removed += cut.end - cut.start;
    else break;
  }
  return value + removed;
}

/**
 * Move program time `t` for a one-off removal of [t0, t1] (d = t1 - t0):
 *   t <= t0 -> t;   t0 < t < t1 -> t0 (collapses onto the join);   t >= t1 -> t - d.
 * No grid snapping (callers pass snapped t0/t1). A non-finite t gives 0; a
 * non-finite t0/t1 returns t unchanged.
 *
 *   shiftTime(1.0, 2.0, 2.5) === 1
 *   shiftTime(2.25, 2.0, 2.5) === 2
 *   shiftTime(3.0, 2.0, 2.5) === 2.5
 */
export function shiftTime(t, t0, t1) {
  const value = finiteNumber(t);
  const start = finiteNumber(t0);
  const end = finiteNumber(t1);
  if (value === null) return 0;
  if (start === null || end === null) return value;
  if (value <= start) return value;
  if (value < end) return start;
  return value - (end - start);
}
