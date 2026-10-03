/**
 * Keeping a caption's `word_reveal` track honest while the user edits it.
 *
 * The track is built once in python (pythainlp word boundaries, absolute
 * seconds) and the preview reads it as-is. The render never trusts it: it
 * rebuilds the track from the cue's current text and times on every export.
 * So whenever an edit changes a cue's text or timing, the stored track has to
 * follow -- or go -- or the preview lights words the export will not have
 * (L3-02).
 *
 * Text cannot be re-tokenized here: the browser's Intl.Segmenter breaks Thai
 * differently from newmm, and the parity tests forbid letting it decide. So a
 * changed text drops the track (the preview falls back to its ordinary
 * keyword highlighting rather than drawing stale words). A pure timing change
 * keeps the words and stretches their times onto the new span, which is what
 * the render's proportional split does to the same words.
 */

const REVEAL_TIME_TOLERANCE = 0.05;

const stripText = (s) => String(s ?? '').replace(/\\N/g, '').replace(/\s+/g, '');

/** True when the track's words spell exactly the caption text (whitespace aside). */
export function revealMatchesText(reveal, text) {
  if (!Array.isArray(reveal) || reveal.length === 0) return false;
  const joined = stripText(reveal.map((w) => (w && w.text) || '').join(''));
  return joined.length > 0 && joined === stripText(text);
}

/** Map every word time from [fromStart, fromEnd] onto [toStart, toEnd]. */
export function retimeReveal(reveal, fromStart, fromEnd, toStart, toEnd) {
  if (!Array.isArray(reveal)) return reveal;
  const fromSpan = fromEnd - fromStart;
  const toSpan = toEnd - toStart;
  const map = fromSpan > 1e-9
    ? (t) => toStart + ((t - fromStart) * toSpan) / fromSpan
    : (t) => t + (toStart - fromStart);
  return reveal.map((w) => ({ ...w, start: map(Number(w.start)), end: map(Number(w.end)) }));
}

/**
 * The track the preview may draw for `cue`, or null.
 *
 * Null when the words no longer spell the caption (edited text). When the
 * words still match but sit outside the cue's span -- a cue moved by an older
 * build that did not retime its track -- the track is stretched onto the cue,
 * since the render rebuilds it on the cue's own start/end.
 */
export function revealTrackForCue(reveal, cue) {
  if (!cue || !revealMatchesText(reveal, cue.text)) return null;
  const cueStart = Number(cue.start);
  const cueEnd = Number(cue.end);
  if (!Number.isFinite(cueStart) || !Number.isFinite(cueEnd)) return reveal;
  const first = Number(reveal[0].start);
  const last = Number(reveal[reveal.length - 1].end);
  const inside = first >= cueStart - REVEAL_TIME_TOLERANCE
    && last <= cueEnd + REVEAL_TIME_TOLERANCE
    && Math.abs(last - cueEnd) <= REVEAL_TIME_TOLERANCE;
  if (inside) return reveal;
  return retimeReveal(reveal, first, last, cueStart, cueEnd);
}

function withoutReveal(cue) {
  if (!cue || !('word_reveal' in cue)) return cue;
  const { word_reveal: _dropped, ...rest } = cue;
  return rest;
}

/**
 * Bring `next.word_reveal` in line with an edit from `prev` to `next`.
 * A track the edit supplied itself (a different array) is left alone.
 */
export function reconcileCueReveal(prev, next) {
  if (!next || next === prev) return next;
  const reveal = next.word_reveal;
  if (!Array.isArray(reveal) || reveal.length === 0) return next;
  if (!prev || reveal !== prev.word_reveal) return next;
  if (!revealMatchesText(reveal, next.text)) return withoutReveal(next);
  const ps = Number(prev.start); const pe = Number(prev.end);
  const ns = Number(next.start); const ne = Number(next.end);
  if ([ps, pe, ns, ne].every(Number.isFinite) && (ps !== ns || pe !== ne)) {
    return { ...next, word_reveal: retimeReveal(reveal, ps, pe, ns, ne) };
  }
  return next;
}

/** reconcileCueReveal over a whole list, pairing cues by _uid (or id). */
export function reconcileCuesReveal(prevList, nextList) {
  if (!Array.isArray(nextList) || !Array.isArray(prevList)) return nextList;
  const byKey = new Map();
  for (const c of prevList) {
    const key = c && (c._uid ?? c.id);
    if (key !== undefined && key !== null) byKey.set(key, c);
  }
  let changed = false;
  const out = nextList.map((c) => {
    const key = c && (c._uid ?? c.id);
    const prev = key !== undefined && key !== null ? byKey.get(key) : undefined;
    const fixed = prev ? reconcileCueReveal(prev, c) : c;
    if (fixed !== c) changed = true;
    return fixed;
  });
  return changed ? out : nextList;
}

/**
 * Split `target`'s track for a cut into `text1` [start, splitTime] and
 * `text2` [splitTime, end]. Each half is null when the cut falls inside a
 * word or the words do not spell that half.
 */
export function splitCueReveal(target, text1, text2, splitTime) {
  const reveal = target && target.word_reveal;
  if (!revealMatchesText(reveal, target.text)) return [null, null];
  const need = stripText(text1).length;
  let got = 0;
  let k = 0;
  while (k < reveal.length && got < need) {
    got += stripText(reveal[k].text).length;
    k += 1;
  }
  const half1 = reveal.slice(0, k);
  const half2 = reveal.slice(k);
  if (got !== need || !half1.length || !half2.length) return [null, null];
  if (!revealMatchesText(half1, text1) || !revealMatchesText(half2, text2)) return [null, null];
  const start = Number(target.start);
  const end = Number(target.end);
  const boundary = Number(half2[0].start);
  if (!(boundary > start && boundary < end && splitTime > start && splitTime < end)) return [null, null];
  const r1 = retimeReveal(half1, start, boundary, start, splitTime);
  const r2 = retimeReveal(half2, boundary, end, splitTime, end);
  // As in build_word_reveal, the last word owns the tail of its cue.
  r1[r1.length - 1] = { ...r1[r1.length - 1], end: splitTime };
  r2[r2.length - 1] = { ...r2[r2.length - 1], end };
  return [r1, r2];
}

/** One track for two merged cues, or null when either half has none. */
export function mergeCueReveals(first, second, merged) {
  const a = first && first.word_reveal;
  const b = second && second.word_reveal;
  if (!revealMatchesText(a, first.text) || !revealMatchesText(b, second.text)) return null;
  const joined = [...a, ...b];
  if (!revealMatchesText(joined, merged.text)) return null;
  joined[joined.length - 1] = { ...joined[joined.length - 1], end: Number(merged.end) };
  return joined;
}

/** Set `word_reveal` to `reveal`, or remove the key when there is none. */
export function withReveal(cue, reveal) {
  return reveal ? { ...cue, word_reveal: reveal } : withoutReveal(cue);
}

// Typing in a text box: one sentence is one undo step. Keystrokes come
// further apart than a slider's ticks, so the window is wider than the
// 400 ms slider default.
export const CAPTION_TYPING_COALESCE_MS = 1500;
const TYPING_FIELDS = new Set(['text', 'translation']);

/** History options for a burst of typing into one field, named by `key`. */
export function typingHistoryOptions(key) {
  return { coalesceKey: `typing:${key}`, coalesceWindowMs: CAPTION_TYPING_COALESCE_MS };
}

/**
 * History options for a non-silent patchCaption call. Only a patch that
 * touches a single typed field coalesces, keyed by cue and field, so two
 * captions or text vs translation never share an undo step.
 */
export function captionPatchHistoryOptions(cueUid, patch, options) {
  if (options) return options;
  const keys = Object.keys(patch || {});
  if (keys.length !== 1 || !TYPING_FIELDS.has(keys[0])) return undefined;
  return typingHistoryOptions(`caption:${keys[0]}:${cueUid}`);
}
