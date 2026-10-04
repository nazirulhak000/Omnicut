/**
 * Ripple delete of one or more PROGRAM-time ranges across every lane.
 *
 * Design: _Docs/Plans/PLAN_RIPPLE_ANCHOR_20261004.md sections 2.1-2.7. The
 * voice file is never touched: the cut is recorded in `voiceEdit.cuts` (spans of
 * the ORIGINAL file, see voiceCutMap.js / scripts/voice_cut_map.py) and every
 * editor time (clips, captions, overlays, stickers, effects, word timings) is
 * rewritten in the editor state. SFX follow their owner (cue/overlay `sfx`),
 * BGM plays on untouched (decision D2).
 *
 * Plan-then-apply, like silenceRipple.js:
 *  - `planRippleRanges(state, ranges, opts)` is pure and returns what WOULD
 *    change plus the numbers for the confirm dialog;
 *  - `applyRipplePlan(state, plan)` is the one object to hand to a single
 *    history `set()`, so one Ctrl+Z puts everything back.
 *
 * Scope 'all'  = picture + voice + captions + overlays + stickers + effects.
 * Scope 'video' = clipList only (the old behaviour; the voice stays, so the
 * render freezes the last frame when the picture ends first).
 *
 * Several ranges are applied from the LAST to the FIRST, so the times of the
 * earlier ranges never move while the later ones are processed.
 *
 * Deliberately NOT shifted (see the "lane RC audit" tests in rippleRange.test.js):
 *  - cutout `clip.background_isolation.active_intervals` are SOURCE-footage
 *    seconds (the artifact manifest must equal them), so they travel with the
 *    clip as is; the editor's live recompute marks a changed window 'stale';
 *  - `source_credits` is not part of the editor state or the manifest.
 */

import {
  FPS,
  MIN_CLIP_DURATION,
  buildSegments,
  motionTimeAt,
  splitKeyframesAt,
  totalDuration,
} from './timelineMath.js';
import { revealTrackForCue } from './captionEdits.js';
import {
  MIN_REMAINING_SECONDS,
  effectiveDuration,
  normalizeCuts,
  programToSource,
  shiftTime,
} from './voiceCutMap.js';

export const RIPPLE_SCOPE_ALL = 'all';
export const RIPPLE_SCOPE_VIDEO = 'video';

/** A cue/overlay/sticker/effect that survives a cut shorter than this is deleted. */
export const MIN_RIPPLE_ITEM_SECONDS = 0.10;
/** What is left of the timeline (and of the voice) may not be shorter than this. */
export const MIN_RIPPLE_TOTAL_SECONDS = 1.0;

const TIME_EPS = 1e-6;
// Clip lengths are not whole frames, so the layout rounds cumulative edges and a
// cut can move a later edge by a frame or two (half a frame of jitter per
// clip). Only a larger difference is worth telling the user about.
const MAX_QUIET_DRIFT_FRAMES = 2;
const MIN_CLIP_FRAMES = Math.ceil(MIN_CLIP_DURATION * FPS - 1e-9);
// planSequenceFrames clamps a transition to `clipDuration - 0.05`; keep that
// much of a clip next to a transition so the layout is not re-clamped.
const TRANSITION_MARGIN_FRAMES = Math.ceil(0.05 * FPS - 1e-9);

/** Voice present -> cut everything together, otherwise picture only. */
export function defaultRippleScope(hasVoice) {
  return hasVoice ? RIPPLE_SCOPE_ALL : RIPPLE_SCOPE_VIDEO;
}

const isRecord = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
function finite(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string' && value.trim() !== '') {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }
  return null;
}
const toFrame = (seconds) => Math.floor(Number(seconds) * FPS + 0.5);
const roundTime = (seconds) => Math.round(seconds * 1e6) / 1e6;

let idCounter = 0;
const defaultClipId = () => `clip-${Date.now().toString(36)}-r${++idCounter}`;
const defaultCutId = () => `cut-${Date.now().toString(36)}-${(++idCounter).toString(36)}`;

// ---------------------------------------------------------------------------
// Timed items (cues, micro cues, overlays, stickers, effects)
// ---------------------------------------------------------------------------

/** `word_reveal` is worth drawing word by word only with 2+ words that advance (== word_reveal.py reveal_is_usable). */
export function revealIsUsable(reveal) {
  return Array.isArray(reveal)
    && reveal.length >= 2
    && reveal.some((word) => Number(word?.end) > Number(word?.start));
}

function mapWordTrack(track, t0, t1) {
  if (!Array.isArray(track)) return track;
  return track.map((word) => {
    if (!isRecord(word)) return word;
    const start = finite(word.start);
    const end = finite(word.end);
    if (start === null || end === null) return word;
    return { ...word, start: roundTime(shiftTime(start, t0, t1)), end: roundTime(shiftTime(end, t0, t1)) };
  });
}

/**
 * One item through one removed range [t0, t1] (d = t1 - t0). Returns
 * `{ status: 'same'|'shifted'|'trimmed'|'removed', item, textCut, revealDropped }`.
 *
 *   ends at or before t0            -> same
 *   starts at or after t1           -> shifted by -d
 *   entirely inside [t0, t1]        -> removed
 *   leaves from the left (s < t0 < e <= t1)   -> end = t0
 *   enters from the right (t0 <= s < t1 < e)  -> start = t0, end = e - d
 *   spans the whole range (s < t0, e > t1)    -> end = e - d (cues: ripple_text_cut = true)
 *   a trimmed item shorter than 0.10 s        -> removed
 */
export function rippleTimedItem(item, t0, t1, { isCue = false } = {}) {
  const same = { status: 'same', item, textCut: false, revealDropped: false };
  if (!isRecord(item)) return same;
  const start = finite(item.start);
  const end = finite(item.end);
  if (start === null || end === null) return same;
  const d = t1 - t0;
  if (end <= t0 + TIME_EPS) return same;

  let next;
  let status;
  let textCut = false;
  if (start >= t1 - TIME_EPS) {
    status = 'shifted';
    next = { ...item, start: roundTime(start - d), end: roundTime(end - d) };
  } else if (start >= t0 - TIME_EPS && end <= t1 + TIME_EPS) {
    return { status: 'removed', item, textCut: false, revealDropped: false };
  } else {
    status = 'trimmed';
    if (start < t0 - TIME_EPS && end > t1 + TIME_EPS) {
      next = { ...item, end: roundTime(end - d) };
      textCut = isCue;
    } else if (start < t0 - TIME_EPS) {
      next = { ...item, end: roundTime(t0) };
    } else {
      next = { ...item, start: roundTime(t0), end: roundTime(end - d) };
    }
    if (next.end - next.start < MIN_RIPPLE_ITEM_SECONDS - TIME_EPS) {
      return { status: 'removed', item, textCut: false, revealDropped: false };
    }
    if (textCut) next.ripple_text_cut = true;
  }

  let revealDropped = false;
  if (isCue) {
    if (Array.isArray(item.word_timings)) next.word_timings = mapWordTrack(item.word_timings, t0, t1);
    if (Array.isArray(item.word_reveal)) {
      const mapped = mapWordTrack(item.word_reveal, t0, t1);
      if (status === 'shifted') {
        next.word_reveal = mapped;
      } else {
        // A trimmed cue: the mapped words must still spell the caption inside
        // the cue's new span and still be worth revealing one by one.
        const track = revealTrackForCue(mapped, next);
        if (track && revealIsUsable(track)) {
          next.word_reveal = track;
        } else {
          delete next.word_reveal;
          revealDropped = true;
        }
      }
    }
  }
  return { status, item: next, textCut, revealDropped };
}

/**
 * Ripple a whole list. Returns `{ list, removed: [item], retimed, textCut,
 * revealDropped, changed }`; `list` is the very same array when nothing moved.
 */
export function rippleTimedList(list, t0, t1, options = {}) {
  const source = Array.isArray(list) ? list : [];
  const out = [];
  const removed = [];
  let retimed = 0;
  let textCut = 0;
  let revealDropped = 0;
  for (const item of source) {
    const result = rippleTimedItem(item, t0, t1, options);
    if (result.status === 'removed') {
      removed.push(item);
      continue;
    }
    out.push(result.item);
    if (result.status !== 'same') retimed += 1;
    if (result.textCut) textCut += 1;
    if (result.revealDropped) revealDropped += 1;
  }
  const changed = removed.length > 0 || retimed > 0;
  return { list: changed ? out : source, removed, retimed, textCut, revealDropped, changed };
}

// ---------------------------------------------------------------------------
// Clips
// ---------------------------------------------------------------------------

function playedSpan(seg) {
  const { clip } = seg;
  return ((clip.trim_end ?? seg.srcDur ?? 0) - (clip.trim_start || 0)) / (clip.speed || 1);
}

/** Keep [segStart, tCut) of a clip. Same maths as splitClipAt's left half, without its 0.2 s edge limit. */
function cutClipTail(seg, tCut) {
  const { clip } = seg;
  const speed = clip.speed || 1;
  const start = clip.trim_start || 0;
  const span = playedSpan(seg);
  const local = tCut - seg.segStart;
  const next = { ...clip };
  if (local >= span - TIME_EPS) {
    // The cut lands inside the freeze tail: the whole picture stays, the hold shrinks.
    const tail = roundTime(local - span);
    if (tail > 0) next.freeze_tail = tail;
    else delete next.freeze_tail;
  } else {
    next.trim_end = roundTime(start + local * speed);
    // The freeze belongs to the final piece of the source, which is being cut.
    delete next.freeze_tail;
  }
  if (Array.isArray(clip.keyframes) && clip.keyframes.length) {
    next.keyframes = splitKeyframesAt(clip.keyframes, motionTimeAt(seg, tCut)).left;
  }
  return next;
}

/** Keep [tCut, segEnd) of a clip. Same maths as splitClipAt's right half. */
function cutClipHead(seg, tCut) {
  const { clip } = seg;
  const speed = clip.speed || 1;
  const start = clip.trim_start || 0;
  const local = tCut - seg.segStart;
  const next = {
    ...clip,
    trim_start: roundTime(start + local * speed),
    trim_end: clip.trim_end ?? seg.srcDur,
  };
  if (Array.isArray(clip.keyframes) && clip.keyframes.length) {
    next.keyframes = splitKeyframesAt(clip.keyframes, motionTimeAt(seg, tCut)).right;
  }
  return next;
}

const forceCut = (clip) => (
  clip.transition_in && clip.transition_in !== 'cut' ? { ...clip, transition_in: 'cut' } : clip
);

/**
 * Widen [f0, f1) (frames) until it leaves a clean picture behind:
 *  - an edge inside a transition's overlap moves out to the overlap's edge;
 *  - a left remnant shorter than 0.2 s (or than its own transition + margin) and
 *    a right remnant shorter than 0.2 s are swallowed whole.
 * Returns the new frames plus how many frames each reason added.
 */
function extendRangeFrames(segs, f0Start, f1Start) {
  let f0 = f0Start;
  let f1 = f1Start;
  let transitionFrames = 0;
  let sliverFrames = 0;
  const guardLimit = (segs.length + 2) * 6;
  for (let guard = 0; guard < guardLimit; guard += 1) {
    let changed = false;
    // Transition windows first: an edge inside one is a transition problem, not
    // a sliver problem, and the report should say so.
    for (const seg of segs) {
      const s = seg.frames.start;
      const overlap = seg.frames.overlap;
      if (overlap <= 0) continue;
      const windowEnd = s + overlap;
      if (f0 > s && f0 < windowEnd) { transitionFrames += f0 - s; f0 = s; changed = true; }
      if (f1 > s && f1 < windowEnd) { transitionFrames += windowEnd - f1; f1 = windowEnd; changed = true; }
    }
    if (changed) continue;
    for (let index = 0; index < segs.length; index += 1) {
      const seg = segs[index];
      const s = seg.frames.start;
      const e = seg.frames.end;
      const overlap = seg.frames.overlap;
      // What the NEXT clip's transition covers at this clip's tail.
      const nextOverlap = index + 1 < segs.length ? segs[index + 1].frames.overlap : 0;
      if (s < f0 && f0 < e) {
        const need = Math.max(MIN_CLIP_FRAMES, overlap + TRANSITION_MARGIN_FRAMES);
        if (f0 - s < need) { sliverFrames += f0 - s; f0 = s; changed = true; }
      }
      if (s < f1 && f1 < e) {
        const contentLeft = playedSpan(seg) - (f1 - s) / FPS;
        if (e - f1 - nextOverlap < MIN_CLIP_FRAMES || contentLeft < MIN_CLIP_DURATION - TIME_EPS) {
          sliverFrames += e - f1;
          f1 = e;
          changed = true;
        }
      }
    }
    if (!changed) break;
  }
  return { f0, f1, transitionFrames, sliverFrames };
}

function rippleClipList(segs, f0, f1, makeId) {
  const t0 = f0 / FPS;
  const t1 = f1 / FPS;
  const out = [];
  const stats = { removed: 0, trimmed: 0, split: 0 };
  const idMap = {};
  let junctionDone = false;
  const afterRange = (clip) => {
    if (junctionDone) return clip;
    junctionDone = true;
    return forceCut(clip);
  };
  for (const seg of segs) {
    const s = seg.frames.start;
    const e = seg.frames.end;
    if (e <= f0) { out.push(seg.clip); continue; }
    if (s >= f1) { out.push(afterRange(seg.clip)); continue; }
    const keepLeft = s < f0;
    const keepRight = e > f1;
    if (!keepLeft && !keepRight) { stats.removed += 1; continue; }
    if (keepLeft && keepRight) {
      stats.split += 1;
      const right = { ...cutClipHead(seg, t1), id: makeId(), transition_in: 'cut' };
      idMap[right.id] = seg.clip.id;
      out.push(cutClipTail(seg, t0), afterRange(right));
    } else if (keepLeft) {
      stats.trimmed += 1;
      out.push(cutClipTail(seg, t0));
    } else {
      stats.trimmed += 1;
      out.push(afterRange(cutClipHead(seg, t1)));
    }
  }
  return { clips: out, stats, idMap };
}

// ---------------------------------------------------------------------------
// The plan
// ---------------------------------------------------------------------------

function normalizeRequestedRanges(ranges) {
  const frames = [];
  for (const range of Array.isArray(ranges) ? ranges : []) {
    let a;
    let b;
    if (Array.isArray(range)) [a, b] = range;
    else if (isRecord(range)) {
      a = range.start ?? range.t0 ?? range.cut_start;
      b = range.end ?? range.t1 ?? range.cut_end;
    }
    const start = finite(a);
    const end = finite(b);
    if (start === null || end === null) continue;
    const f0 = Math.max(0, toFrame(start));
    const f1 = toFrame(end);
    if (f1 > f0) frames.push({ f0, f1 });
  }
  frames.sort((a, b) => (a.f0 - b.f0) || (a.f1 - b.f1));
  const merged = [];
  for (const range of frames) {
    const last = merged[merged.length - 1];
    if (last && range.f0 <= last.f1) last.f1 = Math.max(last.f1, range.f1);
    else merged.push({ ...range });
  }
  return merged;
}

const blockedPlan = (scope, reason, extra = {}) => ({
  blocked: reason,
  changed: false,
  scope,
  ranges: [],
  playhead: null,
  state: {},
  summary: null,
  ...extra,
});

function emptyGroup() {
  return { removed: 0, retimed: 0 };
}

/**
 * What would deleting `ranges` (program seconds; `{start,end}`, `{t0,t1}`,
 * `{cut_start,cut_end}` or `[a,b]`) do to `state`?
 *
 * state: `{ clipList, cuesList, microCuesList, overlays, stickers, effects,
 *           style, voiceEdit, voiceEditStale }` (the editor history state).
 * opts:
 *   scope           'all' | 'video' (default `defaultRippleScope(hasVoice)`)
 *   durations       { [clip.id]: source seconds }, as buildSegments takes it
 *   hasVoice        project has a voiceover (default: a source duration is known)
 *   sourceDuration  real length of the voice file; default the stored
 *                   `voiceEdit.source.duration`, else `audioDuration`
 *   audioDuration   current voice length on the timeline (used when no cuts exist yet)
 *   reason          'manual' (default) | 'silence' -- stored on the new cut
 *   newId / newCutId  id factories (tests pass deterministic ones)
 *
 * Returns:
 *   { blocked: null | <Thai reason>, changed, scope, reason,
 *     ranges: [{ start, end, requestedStart, requestedEnd }]   // applied, ascending
 *     playhead,                                                // where the playhead goes (earliest start)
 *     state: { clipList, cuesList, microCuesList, overlays, stickers, effects,
 *              voiceEdit, voiceEditStale, voiceEditNotice[, style] },   // 'video': { clipList } only
 *     summary: { ... see below ... } }
 * summary: removedSeconds, before/after (program length), pictureBefore/After,
 *   voiceBefore/After/voiceShortenedBy, clips {removed, trimmed, split, affected},
 *   cues {removed, retimed, textCut, revealDropped}, microCues, overlays,
 *   stickers, effects ({removed, retimed}), sfxRemoved, extended {transition,
 *   sliver} (seconds), warnings [Thai].
 */
export function planRippleRanges(state, ranges, opts = {}) {
  const base = isRecord(state) ? state : {};
  const clipList = Array.isArray(base.clipList) ? base.clipList : [];
  const voiceStale = Boolean(base.voiceEditStale);
  const storedVoiceEdit = isRecord(base.voiceEdit) ? base.voiceEdit : null;
  const usableEdit = storedVoiceEdit && !voiceStale ? storedVoiceEdit : null;

  const explicitSource = finite(opts.sourceDuration);
  const storedSource = finite(usableEdit?.source?.duration);
  const fallbackSource = finite(opts.audioDuration);
  const sourceDuration = [explicitSource, storedSource, fallbackSource].find((v) => v !== null && v > 0) || 0;
  const hasVoice = opts.hasVoice !== undefined ? Boolean(opts.hasVoice) : sourceDuration > 0;
  const scope = opts.scope === RIPPLE_SCOPE_ALL || opts.scope === RIPPLE_SCOPE_VIDEO
    ? opts.scope
    : defaultRippleScope(hasVoice);
  const all = scope === RIPPLE_SCOPE_ALL;
  const voiceKnown = hasVoice && sourceDuration > 0;
  const cutVoice = all && voiceKnown;
  const reason = opts.reason === 'silence' ? 'silence' : 'manual';
  const makeId = typeof opts.newId === 'function' ? opts.newId : defaultClipId;
  const makeCutId = typeof opts.newCutId === 'function' ? opts.newCutId : defaultCutId;

  const requested = normalizeRequestedRanges(ranges);
  if (!requested.length) {
    return blockedPlan(scope, 'ไม่มีช่วงที่ตัดได้ (ช่วงสั้นกว่า 1 เฟรมหรือไม่ได้เลือก)', { reason });
  }
  if (!clipList.length) {
    return blockedPlan(scope, 'ยังไม่มีคลิปบน Timeline ให้ตัด', { reason });
  }

  const initialCuts = voiceKnown ? normalizeCuts(usableEdit?.cuts, sourceDuration) : [];
  const initialSegs = buildSegments(clipList, opts.durations || {});
  const pictureBefore = totalDuration(initialSegs);
  const voiceBefore = voiceKnown ? effectiveDuration(initialCuts, sourceDuration) : 0;

  let work = {
    clipList,
    cuesList: Array.isArray(base.cuesList) ? base.cuesList : [],
    microCuesList: Array.isArray(base.microCuesList) ? base.microCuesList : [],
    overlays: Array.isArray(base.overlays) ? base.overlays : [],
    stickers: Array.isArray(base.stickers) ? base.stickers : [],
    effects: Array.isArray(base.effects) ? base.effects : [],
    style: base.style,
    cuts: initialCuts,
    durations: { ...(opts.durations || {}) },
  };

  const stats = {
    clips: { removed: 0, trimmed: 0, split: 0 },
    cues: { removed: 0, retimed: 0, textCut: 0, revealDropped: 0 },
    microCues: emptyGroup(),
    overlays: emptyGroup(),
    stickers: emptyGroup(),
    effects: emptyGroup(),
    sfxRemoved: 0,
    microSfxRemoved: 0,
    transitionFrames: 0,
    sliverFrames: 0,
    removedFrames: 0,
    driftFrames: 0,
    voiceRemoved: 0,
    legacyStickerChanged: false,
  };
  const applied = [];

  for (let k = requested.length - 1; k >= 0; k -= 1) {
    const segs = buildSegments(work.clipList, work.durations);
    const pictureFrames = segs.length ? segs[segs.length - 1].frames.end : 0;
    const cuts = work.cuts;
    const voiceTotal = cutVoice ? effectiveDuration(cuts, sourceDuration) : 0;
    const totalFrames = all ? Math.max(pictureFrames, toFrame(voiceTotal)) : pictureFrames;
    let f0 = Math.min(requested[k].f0, totalFrames);
    let f1 = Math.min(requested[k].f1, totalFrames);
    if (f1 <= f0) continue;

    const extended = extendRangeFrames(segs, f0, f1);
    f0 = extended.f0;
    f1 = extended.f1;
    stats.transitionFrames += extended.transitionFrames;
    stats.sliverFrames += extended.sliverFrames;

    // Every clip that has to be cut needs a known source length.
    const unknown = segs.find((seg) => seg.frames.end > f0 && seg.frames.start < f1
      && !(Number.isFinite(Number(seg.clip.trim_end ?? seg.srcDur)) && Number(seg.clip.trim_end ?? seg.srcDur) > 0));
    if (unknown) return blockedPlan(scope, 'ยังโหลดความยาวต้นฉบับของคลิปไม่เสร็จ รอสักครู่แล้วลองใหม่', { reason });

    const t0 = f0 / FPS;
    const t1 = f1 / FPS;
    const clipResult = rippleClipList(segs, f0, f1, makeId);
    stats.clips.removed += clipResult.stats.removed;
    stats.clips.trimmed += clipResult.stats.trimmed;
    stats.clips.split += clipResult.stats.split;
    Object.entries(clipResult.idMap).forEach(([newId, oldId]) => {
      if (work.durations[oldId] !== undefined) work.durations[newId] = work.durations[oldId];
    });
    const next = { ...work, clipList: clipResult.clips };

    if (all) {
      const cueResult = rippleTimedList(work.cuesList, t0, t1, { isCue: true });
      const microResult = rippleTimedList(work.microCuesList, t0, t1, { isCue: true });
      const overlayResult = rippleTimedList(work.overlays, t0, t1);
      const stickerResult = rippleTimedList(work.stickers, t0, t1);
      const effectResult = rippleTimedList(work.effects, t0, t1);
      next.cuesList = cueResult.list;
      next.microCuesList = microResult.list;
      next.overlays = overlayResult.list;
      next.stickers = stickerResult.list;
      next.effects = effectResult.list;
      stats.cues.removed += cueResult.removed.length;
      stats.cues.retimed += cueResult.retimed;
      stats.cues.textCut += cueResult.textCut;
      stats.cues.revealDropped += cueResult.revealDropped + microResult.revealDropped;
      stats.microCues.removed += microResult.removed.length;
      stats.microCues.retimed += microResult.retimed;
      stats.overlays.removed += overlayResult.removed.length;
      stats.overlays.retimed += overlayResult.retimed;
      stats.stickers.removed += stickerResult.removed.length;
      stats.stickers.retimed += stickerResult.retimed;
      stats.effects.removed += effectResult.removed.length;
      stats.effects.retimed += effectResult.retimed;
      stats.sfxRemoved += cueResult.removed.filter((cue) => cue?.sfx).length
        + overlayResult.removed.filter((overlay) => overlay?.sfx).length;
      stats.microSfxRemoved += microResult.removed.filter((cue) => cue?.sfx).length;

      // Legacy single-sticker mirror: only drawn while `stickers` is empty.
      const style = work.style;
      if (!work.stickers.length && isRecord(style) && style.stickerBadge) {
        const mirror = { start: finite(style.stickerStartTime) ?? 0.5, end: finite(style.stickerEndTime) ?? 3.5 };
        const moved = rippleTimedItem(mirror, t0, t1);
        if (moved.status === 'removed') {
          next.style = { ...style, stickerBadge: '' };
          stats.legacyStickerChanged = true;
        } else if (moved.status !== 'same') {
          next.style = { ...style, stickerStartTime: moved.item.start, stickerEndTime: moved.item.end };
          stats.legacyStickerChanged = true;
        }
      }

      if (cutVoice) {
        const voiceEnd = Math.min(t1, voiceTotal);
        if (voiceEnd - t0 >= 1 / FPS - 1e-9) {
          const added = {
            id: makeCutId(),
            start: programToSource(t0, cuts),
            end: programToSource(voiceEnd, cuts),
            reason,
          };
          const takenIds = new Set(cuts.map((cut) => cut.id));
          if (takenIds.has(added.id)) added.id = `${added.id}-${takenIds.size + 1}`;
          next.cuts = normalizeCuts([...cuts, added], sourceDuration);
          stats.voiceRemoved += voiceEnd - t0;
        }
      }
    }

    // The layout after the cut has to be exactly as long as the cut says; a
    // difference would leave the voice and the picture out of step.
    const pictureRemoved = Math.max(0, Math.min(f1, pictureFrames) - f0);
    const afterSegs = buildSegments(next.clipList, next.durations);
    const afterFrames = afterSegs.length ? afterSegs[afterSegs.length - 1].frames.end : 0;
    stats.driftFrames = Math.max(stats.driftFrames, Math.abs(afterFrames - (pictureFrames - pictureRemoved)));
    stats.removedFrames += all ? f1 - f0 : pictureRemoved;
    applied.push({ start: t0, end: t1, requestedStart: requested[k].f0 / FPS, requestedEnd: requested[k].f1 / FPS });
    work = next;
  }

  if (!applied.length) {
    return blockedPlan(scope, 'ช่วงที่เลือกอยู่นอกไทม์ไลน์หรือสั้นกว่า 1 เฟรม', { reason });
  }
  applied.reverse();

  // ---- Final checks on the resulting state ---------------------------------
  if (!work.clipList.length) return blockedPlan(scope, 'ตัดแล้วจะไม่เหลือคลิปเลย', { reason });
  const finalSegs = buildSegments(work.clipList, work.durations);
  const pictureAfter = totalDuration(finalSegs);
  if (pictureAfter < MIN_RIPPLE_TOTAL_SECONDS - TIME_EPS) {
    return blockedPlan(
      scope,
      `ตัดแล้วภาพจะเหลือเพียง ${pictureAfter.toFixed(2)} วินาที ต้องเหลืออย่างน้อย ${MIN_RIPPLE_TOTAL_SECONDS} วินาที`,
      { reason },
    );
  }
  const voiceAfter = voiceKnown ? effectiveDuration(work.cuts, sourceDuration) : 0;
  if (cutVoice && stats.voiceRemoved > 0 && voiceAfter < MIN_REMAINING_SECONDS - TIME_EPS) {
    return blockedPlan(
      scope,
      `ตัดแล้วเสียงพากย์จะเหลือเพียง ${voiceAfter.toFixed(2)} วินาที ต้องเหลืออย่างน้อย ${MIN_REMAINING_SECONDS} วินาที`,
      { reason },
    );
  }

  // ---- State patch ---------------------------------------------------------
  const nextState = { clipList: work.clipList };
  let voiceEdit = base.voiceEdit ?? null;
  if (all) {
    nextState.cuesList = work.cuesList;
    nextState.microCuesList = work.microCuesList;
    nextState.overlays = work.overlays;
    nextState.stickers = work.stickers;
    nextState.effects = work.effects;
    if (stats.legacyStickerChanged) nextState.style = work.style;
  }
  const warnings = [];
  if (cutVoice && stats.voiceRemoved > 0) {
    // Keep the stored fingerprint of a usable edit; a brand new edit (or one
    // whose file was replaced) sends only the duration and the server stamps it.
    voiceEdit = {
      ...(usableEdit || {}),
      schema_version: 1,
      source: usableEdit?.source ? { ...usableEdit.source } : { duration: sourceDuration },
      cuts: work.cuts,
    };
    nextState.voiceEdit = voiceEdit;
    nextState.voiceEditStale = false;
    nextState.voiceEditNotice = null;
    if (voiceStale && storedVoiceEdit) {
      warnings.push('จุดตัดเสียงเดิมใช้ไม่ได้แล้ว (เสียงพากย์ถูกสร้างใหม่) ระบบเริ่มจุดตัดชุดใหม่');
    }
  }

  const programBefore = Math.max(pictureBefore, voiceBefore);
  const programAfter = Math.max(pictureAfter, voiceAfter);
  const removedSeconds = stats.removedFrames / FPS;
  const extendedTransition = stats.transitionFrames / FPS;
  const extendedSliver = stats.sliverFrames / FPS;
  if (extendedTransition > 0) {
    warnings.push(`ขยายช่วงให้พ้นทรานซิชัน ${extendedTransition.toFixed(2)} วินาที`);
  }
  if (extendedSliver > 0) {
    warnings.push(`ขยายช่วงอีก ${extendedSliver.toFixed(2)} วินาที เพื่อไม่ให้เหลือคลิปสั้นกว่า ${MIN_CLIP_DURATION} วินาที`);
  }
  if (stats.cues.textCut > 0) {
    warnings.push(`ซับ ${stats.cues.textCut} บรรทัดยังแสดงข้อความเต็ม แต่เสียงบางคำถูกตัด`);
  }
  if (!all && hasVoice && voiceBefore > 0 && pictureAfter < voiceBefore - 0.1) {
    warnings.push('ภาพจะสั้นกว่าเสียงพากย์ ตอนเรนเดอร์จะค้างเฟรมสุดท้ายจนจบเสียง');
  }
  if (all && hasVoice && sourceDuration <= 0) {
    warnings.push('ไม่ทราบความยาวเสียงพากย์ จึงตัดเฉพาะภาพ ซับ และข้อความ ไม่ได้ตัดเสียง');
  }
  if (stats.driftFrames > MAX_QUIET_DRIFT_FRAMES) {
    warnings.push(`ความยาวภาพหลังตัดต่างจากที่คำนวณ ${stats.driftFrames} เฟรม (ตรวจรอยต่อทรานซิชันหลังตัด)`);
  }

  const affected = stats.clips.removed + stats.clips.trimmed + stats.clips.split;
  const summary = {
    removedSeconds,
    before: programBefore,
    after: programAfter,
    pictureBefore,
    pictureAfter,
    voiceBefore,
    voiceAfter,
    voiceShortenedBy: stats.voiceRemoved,
    clips: { ...stats.clips, affected },
    cues: stats.cues,
    microCues: stats.microCues,
    overlays: stats.overlays,
    stickers: stats.stickers,
    effects: stats.effects,
    sfxRemoved: stats.sfxRemoved || (work.cuesList.length === 0 ? stats.microSfxRemoved : 0),
    extended: { transition: extendedTransition, sliver: extendedSliver },
    warnings,
  };

  return {
    blocked: null,
    changed: true,
    scope,
    reason,
    ranges: applied,
    playhead: applied[0].start,
    state: nextState,
    summary,
  };
}

/** The state after a plan: hand it to ONE history `set()` for a single undo step. */
export function applyRipplePlan(prev, plan) {
  if (!plan || plan.blocked || !plan.changed) return prev;
  return { ...prev, ...plan.state };
}

// ---------------------------------------------------------------------------
// Dialog text
// ---------------------------------------------------------------------------

/** 4.6 -> "0:04.60" */
export function formatRippleTime(seconds) {
  const s = Math.max(0, Number.isFinite(Number(seconds)) ? Number(seconds) : 0);
  // Whole centiseconds first, so 59.999 reads 1:00.00 and never 0:60.00.
  const centis = Math.round(s * 100);
  const minutes = Math.floor(centis / 6000);
  const rest = (centis - minutes * 6000) / 100;
  return `${minutes}:${rest.toFixed(2).padStart(5, '0')}`;
}

/**
 * Thai text for the confirm step: `{ title, subtitle, summary, parts,
 * warnings, confirmLabel, cancelLabel, undoHint, blocked }`.
 * Phrased as what WILL happen, like silenceRipple.describePlan.
 */
export function describeRipplePlan(plan) {
  const labels = { confirmLabel: 'ตัดช่วงนี้', cancelLabel: 'ยกเลิก', undoHint: 'กด Ctrl+Z ย้อนกลับได้ทันที' };
  if (!plan) return { title: '', subtitle: '', summary: '', parts: [], warnings: [], blocked: null, ...labels };
  if (plan.blocked || !plan.changed || !plan.summary) {
    return {
      title: '', subtitle: '', summary: plan.blocked || 'ไม่มีช่วงที่ตัดได้', parts: [], warnings: [],
      blocked: plan.blocked || 'ไม่มีช่วงที่ตัดได้', ...labels,
    };
  }
  const { summary, ranges, scope } = plan;
  const silence = plan.reason === 'silence';
  let title;
  if (ranges.length === 1) {
    const span = `${formatRippleTime(ranges[0].start)}–${formatRippleTime(ranges[0].end)}`;
    title = scope === RIPPLE_SCOPE_VIDEO ? `ตัดช่วง ${span} ออกจากภาพ?` : `ตัดช่วง ${span} ออก?`;
  } else if (silence) {
    title = `ตัดช่วงเงียบ ${ranges.length} ช่วงออก?`;
  } else {
    title = `ตัด ${ranges.length} ช่วงออก?`;
  }
  const subtitle = scope === RIPPLE_SCOPE_VIDEO
    ? 'ภาพหลังจุดนี้จะเลื่อนมาชิดกัน เสียงพากย์และซับไม่ขยับ'
    : 'ภาพ เสียงพากย์ ซับ และข้อความหลังจุดนี้จะเลื่อนมาชิดกัน';

  const parts = [];
  if (summary.voiceShortenedBy > 0) {
    parts.push(`เสียงพากย์สั้นลง ${summary.voiceShortenedBy.toFixed(2)} วินาที (${summary.voiceBefore.toFixed(2)} → ${summary.voiceAfter.toFixed(2)})`);
  } else {
    parts.push(`ภาพสั้นลง ${Math.max(0, summary.pictureBefore - summary.pictureAfter).toFixed(2)} วินาที (${summary.pictureBefore.toFixed(2)} → ${summary.pictureAfter.toFixed(2)})`);
  }
  if (summary.cues.removed) parts.push(`ลบซับ ${summary.cues.removed} บรรทัด`);
  if (summary.cues.retimed) parts.push(`ปรับเวลาซับ ${summary.cues.retimed} บรรทัด`);
  const overlayCount = summary.overlays.removed + summary.stickers.removed + summary.effects.removed;
  if (overlayCount) parts.push(`ลบข้อความ/สติกเกอร์/เอฟเฟกต์ ${overlayCount} ชิ้น`);
  const overlayMoved = summary.overlays.retimed + summary.stickers.retimed + summary.effects.retimed;
  if (overlayMoved) parts.push(`เลื่อนข้อความ/สติกเกอร์/เอฟเฟกต์ ${overlayMoved} ชิ้น`);
  if (summary.sfxRemoved) parts.push(`ลบ SFX ${summary.sfxRemoved} เสียง`);
  if (summary.clips.affected) parts.push(`ตัดคลิป ${summary.clips.affected} คลิป`);

  return {
    title,
    subtitle,
    summary: parts.join(' · '),
    parts,
    warnings: [...summary.warnings],
    blocked: null,
    ...labels,
  };
}
